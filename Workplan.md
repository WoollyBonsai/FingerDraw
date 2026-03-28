Development Environment Requirements
Android Studio: Latest stable release (required for NDK integration).

Android NDK: Installed via SDK Manager (side-by-side versions recommended).

CMake: Build system (standard for native Android projects).

GStreamer Android SDK: Download GStreamer Android Binaries (arm64-v8a architecture).

Clang/LLVM: Included with NDK for C++ compilation.

Toolchain: Linux environment with make, ninja, and appropriate linker tools.

App Creation Workflow
1. Integration
Extract the GStreamer Android SDK.

Add the gstreamer-1.0 library paths to your project's CMakeLists.txt.

Use find_library to locate GStreamer shared objects.

Link GStreamer dependencies to your native library (target_link_libraries).

2. Native Pipeline Implementation (C++)
Initialize GStreamer: gst_init(NULL, NULL).

Define the pipeline string: udpsrc ! rtph264depay ! h264parse ! amcvideodec ! ahcvideosink.

Use gst_parse_launch to create the pipeline element.

Implement on_message callbacks to monitor bus signals (EOS, ERROR, STATE_CHANGED).

3. Surface Binding (JNI)
In Kotlin MainActivity, create a SurfaceView or TextureView.

Pass the Surface object to the C++ layer using ANativeWindow_fromSurface(env, surface).

Set the window property on the ahcvideosink element via gst_video_overlay_set_window_handle.

4. Network Threading (Input Loop)
Create a dedicated C++ std::thread for input.

Open a socket listener on the Linux host port.

Deserialize incoming packets containing (x, y, pressure, state) data.

Write to /dev/uinput using standard ioctl calls to inject events into the kernel.

5. Pipeline Execution
Set pipeline state to GST_STATE_PLAYING.

Run the GMainLoop in a background C++ thread to prevent blocking the UI thread.

Handle onPause and onResume in Kotlin to set the pipeline state to NULL (cleanup) and PLAYING (re-initialize) respectively.
