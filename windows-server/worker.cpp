#define WIN32_LEAN_AND_MEAN
#include <winsock2.h>
#include <ws2tcpip.h>
#include <windows.h>
#include <iostream>
#include <string>
#include <cstdio>

#pragma comment(lib, "user32.lib")
#pragma comment(lib, "ws2_32.lib")

#define UDP_PORT 9999

int main() {
    // 1. MANDATORY: Tell Windows we want PHYSICAL pixels, not "Scaled" ones
    // This fixes the 1.25x or 1.5x offset issues on modern laptops
    SetProcessDpiAwarenessContext(DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2);

    // 2. Initialize Subsystem
    InitializeTouchInjection(10, POINTER_FEEDBACK_DEFAULT);

    HSYNTHETICPOINTERDEVICE device = NULL;
    int active_type = 0;

    // Try Pen then Touch
    device = CreateSyntheticPointerDevice(PT_PEN, 1, POINTER_FEEDBACK_DEFAULT);
    if (device) {
        active_type = PT_PEN;
        std::cout << "[INIT] DEVICE TYPE: PT_PEN (Type 3)" << std::endl;
    } else {
        device = CreateSyntheticPointerDevice(PT_TOUCH, 1, POINTER_FEEDBACK_DEFAULT);
        if (device) {
            active_type = PT_TOUCH;
            std::cout << "[INIT] DEVICE TYPE: PT_TOUCH (Type 2)" << std::endl;
        }
    }

    if (!device) {
        std::cerr << "[FATAL] Failed to initialize any injection device. Error: " << GetLastError() << std::endl;
        return 1;
    }

    // 3. Log Screen Calibration Data
    int screenW = GetSystemMetrics(SM_CXSCREEN);
    int screenH = GetSystemMetrics(SM_CYSCREEN);
    std::cout << "[CALIBRATION] Detected Resolution: " << screenW << "x" << screenH << std::endl;
    std::cout << "[NET] Listening on UDP Port " << UDP_PORT << "..." << std::endl;

    // 4. Winsock Setup
    WSADATA wsa;
    WSAStartup(MAKEWORD(2, 2), &wsa);
    SOCKET s = socket(AF_INET, SOCK_DGRAM, IPPROTO_UDP);
    sockaddr_in server, client;
    server.sin_family = AF_INET;
    server.sin_addr.s_addr = INADDR_ANY;
    server.sin_port = htons(UDP_PORT);
    bind(s, (struct sockaddr *)&server, sizeof(server));

    char buf[512];
    int client_len = sizeof(client);
    bool is_pressed = false;

    while (true) {
    int len = recvfrom(s, buf, 511, 0, (struct sockaddr *)&client, &client_len);
    if (len > 0) {
        buf[len] = '\0';
        std::string msg(buf);
        
        float x, y, p;
        char cmd = msg[0];

        if (msg.substr(0, 4) == "ALT:") {
            int state = msg[4] - '0';
            if (state == 1) {
                keybd_event(VK_MENU, 0, 0, 0); // ALT down
            } else {
                keybd_event(VK_MENU, 0, KEYEVENTF_KEYUP, 0); // ALT up
            }
            continue;
        }
        else if (msg == "META") {
            keybd_event(VK_LWIN, 0, 0, 0);
            keybd_event(VK_LWIN, 0, KEYEVENTF_KEYUP, 0);
            continue;
        }
        else if (msg == "TAB") {
            keybd_event(VK_TAB, 0, 0, 0);
            keybd_event(VK_TAB, 0, KEYEVENTF_KEYUP, 0);
            continue;
        }

        // Parse coordinates
        if (sscanf_s(msg.c_str() + 2, "%f,%f,%f", &x, &y, &p) != 3) {
            if (cmd != 'U') continue; 
        }

        POINTER_TYPE_INFO info = {0};
        info.type = (POINTER_INPUT_TYPE)active_type;
        POINTER_INFO* pInfo = (active_type == PT_PEN) ? &info.penInfo.pointerInfo : &info.touchInfo.pointerInfo;

        pInfo->pointerType = (POINTER_INPUT_TYPE)active_type;
        pInfo->ptPixelLocation.x = (LONG)(x * screenW);
        pInfo->ptPixelLocation.y = (LONG)(y * screenH);
        pInfo->pointerId = 0;

        if (cmd == 'U') {
            // CRITICAL: The "Lift Off" sequence
            // We must remove INCONTACT and add UP. 
            // For Pen, we also keep INRANGE briefly or clear it to "remove" the pen.
            pInfo->pointerFlags = POINTER_FLAG_UP | POINTER_FLAG_INRANGE; 
            is_pressed = false;
            std::cout << "[DEBUG] Pen Lifted" << std::endl;
        } 
        else if (cmd == 'D') {
            // Initial touch
            pInfo->pointerFlags = POINTER_FLAG_DOWN | POINTER_FLAG_INCONTACT | POINTER_FLAG_INRANGE;
            is_pressed = true;
            std::cout << "[DEBUG] Pen Down" << std::endl;
        } 
        else if (cmd == 'M') {
            // Movement
            pInfo->pointerFlags = POINTER_FLAG_UPDATE | POINTER_FLAG_INCONTACT | POINTER_FLAG_INRANGE;
            is_pressed = true;
        }

        // Additional Pen-specific data
        if (active_type == PT_PEN) {
            info.penInfo.penMask = PEN_MASK_PRESSURE;
            info.penInfo.pressure = (UINT32)(p * 1024);
        }

        if (!InjectSyntheticPointerInput(device, &info, 1)) {
            // If injection fails, log it
            // std::cerr << "Injection Error: " << GetLastError() << std::endl;
        }
    }
}
    return 0;
}