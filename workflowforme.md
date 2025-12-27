✦ Okay, implementing the Android client-side GStreamer receiver for the raw UDP stream is the most involved part, requiring
  integration of native code. I cannot directly download and install the GStreamer Android SDK or write the C/C++ native code for
  you. However, I can provide a detailed, step-by-step guide to help you set it up.

  Here's the plan I recommend:

   1. GStreamer Android SDK Setup (User's Manual Step):
       * Download: You will need to manually download the GStreamer Android SDK from the official GStreamer website (e.g.,
         gstreamer-1.x-android-arm-release-x.x.x.tar.bz2). Choose the SDK version that matches your target Android ABIs (e.g.,
         arm64-v8a, armeabi-v7a).
       * Extract: Extract the SDK to a known, accessible location on your development machine (e.g.,
         /home/woolly/Android/gstreamer-sdk-android-arm-1.20.5).
       * Copy Java files: Copy the org folder from GSTREAMER_ROOT_ANDROID/share/gst-android/java/src/ into your Android project's
         app/src/main/java/ directory. This will add the necessary GStreamer Java/Kotlin wrappers.
       * Copy native libraries: Copy the prebuilt .so files from GSTREAMER_ROOT_ANDROID/lib/gstreamer-1.0/ and
         GSTREAMER_ROOT_ANDROID/lib/ (check all relevant subdirectories like arm64-v8a, armeabi-v7a) into your project's
         app/src/main/jniLibs/ directory, maintaining the ABI subfolder structure (e.g.,
         app/src/main/jniLibs/arm64-v8a/libgstreamer_android.so, app/src/main/jniLibs/arm64-v8a/libgstreamer_android.so).

   2. `AndroidManifest.xml` Modifications: I will add the necessary permissions (INTERNET, ACCESS_NETWORK_STATE).

   3. `app/build.gradle` Modifications: I will update the app/build.gradle file to:
       * Add externalNativeBuild block for CMake.
       * Configure ndk for ABI filters.
       * Add jniLibs.srcDirs to point to the directory for prebuilt GStreamer libs.

   4. Create `CMakeLists.txt`: I will create a new CMakeLists.txt file in app/src/main/cpp/ to build the native JNI wrapper. You
      will need to update `GSTREAMER_ROOT_ANDROID` in this file to your SDK path.

   5. Create Native C/C++ Code (`udpreceiver.c`): I will create a new udpreceiver.c file in app/src/main/cpp/ with the JNI
      functions and GStreamer pipeline logic.

   6. `MainActivity.kt` Modifications: I will modify MainActivity.kt to:
       * Remove the ExoPlayer setup.
       * Add a SurfaceView and implement SurfaceHolder.Callback.
       * Call native GStreamer initialization, pipeline setup, and playback functions.

  Let's start with the AndroidManifest.xml modifications.

  Instruction: Add android.permission.INTERNET and android.permission.ACCESS_NETWORK_STATE permissions to
  android-client/app/src/main/AndroidManifest.xml.
