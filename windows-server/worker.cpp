#define WIN32_LEAN_AND_MEAN
#include <winsock2.h>
#include <ws2tcpip.h>
#include <windows.h>
#include <iostream>
#include <string>
#include <vector>
#include <cstdio>

#pragma comment(lib, "user32.lib")
#pragma comment(lib, "ws2_32.lib")

#define UDP_PORT 9999

int main() {
    // 1. Initialize Windows Input Subsystem
    InitializeTouchInjection(10, POINTER_FEEDBACK_DEFAULT);
    HSYNTHETICPOINTERDEVICE penDevice = CreateSyntheticPointerDevice(PT_PEN, 1, POINTER_FEEDBACK_DEFAULT);
    
    if (!penDevice) {
        std::cerr << "CRITICAL: Failed to create pen device. Run as ADMIN." << std::endl;
        return 1;
    }

    // 2. Initialize Winsock
    WSADATA wsa;
    if (WSAStartup(MAKEWORD(2, 2), &wsa) != 0) {
        std::cerr << "Winsock Init Failed." << std::endl;
        return 1;
    }

    SOCKET s = socket(AF_INET, SOCK_DGRAM, IPPROTO_UDP);
    if (s == INVALID_SOCKET) {
        std::cerr << "Socket creation failed." << std::endl;
        return 1;
    }
    
    sockaddr_in server, client;
    server.sin_family = AF_INET;
    server.sin_addr.s_addr = INADDR_ANY;
    server.sin_port = htons(UDP_PORT);
    
    if (bind(s, (struct sockaddr *)&server, sizeof(server)) == SOCKET_ERROR) {
        std::cerr << "Bind failed. Port 9999 might be in use." << std::endl;
        return 1;
    }

    printf("--- FINGERDRAW C++ INPUT WORKER ---\n");
    printf("Status: ACTIVE | Port: %d | Mode: PT_PEN\n", UDP_PORT);

    char buf[512];
    int client_len = sizeof(client);
    bool is_pressed = false;

    // 3. Main Input Loop
    while (true) {
        int len = recvfrom(s, buf, 511, 0, (struct sockaddr *)&client, &client_len);
        if (len > 0) {
            buf[len] = '\0';
            std::string msg(buf);
            
            size_t colon = msg.find(':');
            char cmd = msg[0];

            POINTER_TYPE_INFO info = {0};
            info.type = PT_PEN;
            info.penInfo.pointerInfo.pointerType = PT_PEN;

            if ((cmd == 'D' || cmd == 'M') && colon != std::string::npos) {
                float x, y, p;
                // Parse "D:x,y,p"
                if (sscanf_s(msg.c_str() + 2, "%f,%f,%f", &x, &y, &p) == 3) {
                    info.penInfo.pointerInfo.ptPixelLocation.x = (LONG)(x * GetSystemMetrics(SM_CXVIRTUALSCREEN));
                    info.penInfo.pointerInfo.ptPixelLocation.y = (LONG)(y * GetSystemMetrics(SM_CYVIRTUALSCREEN));
                    info.penInfo.penMask = PEN_MASK_PRESSURE;
                    info.penInfo.pressure = (UINT32)(p * 1024);
                    
                    info.penInfo.pointerInfo.pointerFlags = POINTER_FLAG_INRANGE | POINTER_FLAG_INCONTACT;
                    info.penInfo.pointerInfo.pointerFlags |= (is_pressed ? POINTER_FLAG_UPDATE : POINTER_FLAG_DOWN);
                    is_pressed = true;
                    InjectSyntheticPointerInput(penDevice, &info, 1);
                }
            } 
            else if (cmd == 'U') {
                info.penInfo.pointerInfo.pointerFlags = POINTER_FLAG_UP | POINTER_FLAG_INRANGE;
                is_pressed = false;
                InjectSyntheticPointerInput(penDevice, &info, 1);
            }
        }
    }

    closesocket(s);
    WSACleanup();
    return 0;
}