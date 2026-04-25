cmake_minimum_required(VERSION 3.22.1)
project(fingerdraw)

set(GSTREAMER_ANDROID_ROOT "/home/woolly/Development/Gstreamer")
set(GSTREAMER_ARCH "arm64") 

set(GST_DIR "${GSTREAMER_ANDROID_ROOT}/${GSTREAMER_ARCH}")

include_directories(
    ${GST_DIR}/include/gstreamer-1.0
    ${GST_DIR}/lib/gstreamer-1.0/include
    ${GST_DIR}/include/glib-2.0
    ${GST_DIR}/lib/glib-2.0/include
)

# Function to link static GStreamer plugins
function(link_gst_plugin TARGET PLUGIN_NAME)
    target_link_libraries(${TARGET} ${GST_DIR}/lib/gstreamer-1.0/libgst${PLUGIN_NAME}.a)
endfunction()

add_library(fingerdraw-native SHARED
    native-lib.cpp
)

# Link Plugins
link_gst_plugin(fingerdraw-native coreelements)
link_gst_plugin(fingerdraw-native udp)
link_gst_plugin(fingerdraw-native rtp)
link_gst_plugin(fingerdraw-native rtpmanager)
link_gst_plugin(fingerdraw-native videoparsersbad)
link_gst_plugin(fingerdraw-native androidmedia)
link_gst_plugin(fingerdraw-native opengl)
link_gst_plugin(fingerdraw-native videoconvertscale)
link_gst_plugin(fingerdraw-native typefindfunctions)
link_gst_plugin(fingerdraw-native playback)
link_gst_plugin(fingerdraw-native openh264) # Added OpenH264 Software Decoder

# Link Main GStreamer Libraries
target_link_libraries(fingerdraw-native
    ${GST_DIR}/lib/libgstbase-1.0.a
    ${GST_DIR}/lib/libgstvideo-1.0.a
    ${GST_DIR}/lib/libgstrtp-1.0.a
    ${GST_DIR}/lib/libgstnet-1.0.a
    ${GST_DIR}/lib/libgstgl-1.0.a
    ${GST_DIR}/lib/libgraphene-1.0.a
    ${GST_DIR}/lib/libgstcodecparsers-1.0.a
    ${GST_DIR}/lib/libgstcontroller-1.0.a
    ${GST_DIR}/lib/libgstpbutils-1.0.a
    ${GST_DIR}/lib/libgsttag-1.0.a
    ${GST_DIR}/lib/libgstallocators-1.0.a
    ${GST_DIR}/lib/libgstphotography-1.0.a
    ${GST_DIR}/lib/libgstaudio-1.0.a
    ${GST_DIR}/lib/libgstreamer-1.0.a
    ${GST_DIR}/lib/libgio-2.0.a
    ${GST_DIR}/lib/libglib-2.0.a
    ${GST_DIR}/lib/libgobject-2.0.a
    ${GST_DIR}/lib/libgmodule-2.0.a
)

# Link External Dependencies
target_link_libraries(fingerdraw-native
    android
    log
    GLESv2
    EGL
    ${GST_DIR}/lib/libintl.a
    ${GST_DIR}/lib/libffi.a
    ${GST_DIR}/lib/libpcre2-8.a
    ${GST_DIR}/lib/libiconv.a
    ${GST_DIR}/lib/liborc-0.4.a
    ${GST_DIR}/lib/libjpeg.a
    ${GST_DIR}/lib/libpng16.a
    ${GST_DIR}/lib/libopenh264.a # External lib for openh264 plugin
    ${GST_DIR}/lib/libz.a
    z
    m
)
