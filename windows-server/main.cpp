#define WIN32_LEAN_AND_MEAN  // Must be first
#include <winsock2.h>        // Must be before windows.h
#include <ws2tcpip.h>        // Must be before windows.h
#include <windows.h>
#include <gst/gst.h>
#include <iostream>
#include <string>

#pragma comment(lib, "ws2_32.lib")
#pragma comment(lib, "user32.lib")
#pragma comment(lib, "shell32.lib")

// --- GLOBAL STATE ---
GstElement* pipeline = nullptr;
const int BRAIN_PORT = 8000;

// --- 1. GSTREAMER PIPELINE ---
void start_pipeline(const char* target_ip) {
    if (pipeline) {
        gst_element_set_state(pipeline, GST_STATE_NULL);
        gst_object_unref(pipeline);
    }

    std::string pipe_str =
        "d3d11screencapturesrc capture-api=dxgi do-timestamp=true ! "
        "queue leaky=downstream max-size-buffers=1 ! "
        "d3d11convert ! "
        "video/x-raw(memory:D3D11Memory),width=1280,height=720,framerate=60/1 ! "
        "d3d11download ! "
        "video/x-raw,format=I420 ! "
        "x264enc bitrate=3000 tune=zerolatency speed-preset=ultrafast ! "
        "rtph264pay config-interval=1 ! "
        "udpsink host=" + std::string(target_ip) + " port=5000 sync=false";

    GError* error = NULL;
    pipeline = gst_parse_launch(pipe_str.c_str(), &error);

    if (error) {
        std::cerr << "[GST ERROR] " << error->message << std::endl;
        g_error_free(error);
        return;
    }

    gst_element_set_state(pipeline, GST_STATE_PLAYING);
    std::cout << "[STREAM] Pipeline live to " << target_ip << ":5000" << std::endl;
}

// --- 2. WORKER AUTOMATION ---
void launch_worker() {
    STARTUPINFOW si = { sizeof(si) };
    PROCESS_INFORMATION pi;
    wchar_t commandLine[] = L"worker.exe";

    if (!CreateProcessW(NULL, commandLine, NULL, NULL, FALSE, 0, NULL, NULL, &si, &pi)) {
        std::cerr << "[SYSTEM] Failed to launch worker.exe. Error: " << GetLastError() << std::endl;
    } else {
        std::cout << "[SYSTEM] Worker.exe started (PID: " << pi.dwProcessId << ")" << std::endl;
        CloseHandle(pi.hProcess);
        CloseHandle(pi.hThread);
    }
}

// --- 3. MAIN ---
int main(int argc, char* argv[]) {
    gst_init(&argc, &argv);
    std::cout << "--- FINGERDRAW NATIVE ENGINE v3.0 ---" << std::endl;

    launch_worker();

    WSADATA wsa;
    if (WSAStartup(MAKEWORD(2, 2), &wsa) != 0) {
        std::cerr << "[NET] Winsock init failed." << std::endl;
        return 1;
    }

    SOCKET server_fd = socket(AF_INET, SOCK_STREAM, IPPROTO_TCP);
    sockaddr_in server_addr;
    server_addr.sin_family = AF_INET;
    server_addr.sin_addr.s_addr = INADDR_ANY;
    server_addr.sin_port = htons(BRAIN_PORT);

    if (bind(server_fd, (struct sockaddr*)&server_addr, sizeof(server_addr)) == SOCKET_ERROR) {
        std::cerr << "[NET] Bind failed. Port 8000 busy?" << std::endl;
        return 1;
    }

    listen(server_fd, 3);
    std::cout << "[READY] Waiting for Android on port " << BRAIN_PORT << "..." << std::endl;

    while (true) {
        sockaddr_in client_addr;
        int addr_len = sizeof(client_addr);
        SOCKET client_sock = accept(server_fd, (struct sockaddr*)&client_addr, &addr_len);

        if (client_sock != INVALID_SOCKET) {
            char client_ip[INET_ADDRSTRLEN];
            inet_ntop(AF_INET, &client_addr.sin_addr, client_ip, INET_ADDRSTRLEN);
            std::cout << "[NET] Handshake from Android IP: " << client_ip << std::endl;

            start_pipeline(client_ip);
            // Connection stays open to prevent Android timeout
        }
    }

    WSACleanup();
    return 0;
}