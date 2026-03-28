#include <jni.h>
#include <string>
#include <android/log.h>
#include <android/native_window_jni.h>
#include <gst/gst.h>
#include <gst/video/video.h>
#include <pthread.h>

#define TAG "FingerDrawNative"
#define LOGD(...) __android_log_print(ANDROID_LOG_DEBUG, TAG, __VA_ARGS__)
#define LOGE(...) __android_log_print(ANDROID_LOG_ERROR, TAG, __VA_ARGS__)

static GstElement *pipeline = nullptr;
static ANativeWindow *native_window = nullptr;
static GMainLoop *main_loop = nullptr;
static pthread_t gst_thread;

static void on_bus_message(GstBus *bus, GstMessage *msg, gpointer data) {
    switch (GST_MESSAGE_TYPE(msg)) {
        case GST_MESSAGE_ERROR: {
            GError *err;
            gchar *debug;
            gst_message_parse_error(msg, &err, &debug);
            LOGE("GStreamer error: %s", err->message);
            g_error_free(err);
            g_free(debug);
            break;
        }
        case GST_MESSAGE_STATE_CHANGED: {
            GstState old_state, new_state, pending;
            gst_message_parse_state_changed(msg, &old_state, &new_state, &pending);
            if (GST_MESSAGE_SRC(msg) == GST_OBJECT(pipeline)) {
                LOGD("Pipeline state changed from %s to %s", gst_element_state_get_name(old_state), gst_element_state_get_name(new_state));
            }
            break;
        }
        default:
            break;
    }
}

static void* gst_worker_thread(void* data) {
    LOGD("GStreamer worker thread started.");
    main_loop = g_main_loop_new(nullptr, FALSE);
    g_main_loop_run(main_loop);
    LOGD("GStreamer worker thread exiting.");
    return nullptr;
}

extern "C" {
    GST_PLUGIN_STATIC_DECLARE(coreelements);
    GST_PLUGIN_STATIC_DECLARE(udp);
    GST_PLUGIN_STATIC_DECLARE(rtp);
    GST_PLUGIN_STATIC_DECLARE(rtpmanager);
    GST_PLUGIN_STATIC_DECLARE(videoparsersbad);
    GST_PLUGIN_STATIC_DECLARE(androidmedia);
    GST_PLUGIN_STATIC_DECLARE(opengl);
    GST_PLUGIN_STATIC_DECLARE(videoconvertscale);
    GST_PLUGIN_STATIC_DECLARE(typefindfunctions);
    GST_PLUGIN_STATIC_DECLARE(playback);
    GST_PLUGIN_STATIC_DECLARE(openh264);
}

extern "C" JNIEXPORT void JNICALL
Java_org_freedesktop_gstreamer_GStreamer_nativeInit(JNIEnv* env, jclass clazz, jobject context) {
    gst_init(nullptr, nullptr);
    
    GST_PLUGIN_STATIC_REGISTER(coreelements);
    GST_PLUGIN_STATIC_REGISTER(udp);
    GST_PLUGIN_STATIC_REGISTER(rtp);
    GST_PLUGIN_STATIC_REGISTER(rtpmanager);
    GST_PLUGIN_STATIC_REGISTER(videoparsersbad);
    GST_PLUGIN_STATIC_REGISTER(androidmedia);
    GST_PLUGIN_STATIC_REGISTER(opengl);
    GST_PLUGIN_STATIC_REGISTER(videoconvertscale);
    GST_PLUGIN_STATIC_REGISTER(typefindfunctions);
    GST_PLUGIN_STATIC_REGISTER(playback);
    GST_PLUGIN_STATIC_REGISTER(openh264);

    // DEBUG: List ALL available elements to verify registration
    GList *features = gst_registry_get_feature_list(gst_registry_get(), GST_TYPE_ELEMENT_FACTORY);
    LOGD("--- Registered GStreamer Elements ---");
    for (GList *l = features; l != nullptr; l = l->next) {
        GstPluginFeature *f = (GstPluginFeature *)l->data;
        LOGD("Element: %s", gst_plugin_feature_get_name(f));
    }
    gst_plugin_feature_list_free(features);

    pthread_create(&gst_thread, nullptr, gst_worker_thread, nullptr);
}

extern "C" JNIEXPORT void JNICALL
Java_com_example_fingerdraw_MainActivity_nativeInit(JNIEnv* env, jobject thiz) {
    GError *error = nullptr;

    // Use openh264dec as a reliable software decoder
    const char *pipeline_str = 
        "udpsrc port=5000 caps=\"application/x-rtp,media=video,clock-rate=90000,encoding-name=H264,payload=96\" ! "
        "rtpjitterbuffer latency=100 ! "
        "rtph264depay ! h264parse ! "
        "openh264dec ! videoconvert ! "
        "glimagesink name=sink sync=false async=false";

    pipeline = gst_parse_launch(pipeline_str, &error);
    if (error) {
        LOGE("Error creating pipeline: %s", error->message);
        g_error_free(error);
        return;
    }

    GstBus *bus = gst_element_get_bus(pipeline);
    gst_bus_add_signal_watch(bus);
    g_signal_connect(bus, "message", G_CALLBACK(on_bus_message), nullptr);
    gst_object_unref(bus);

    LOGD("Network Pipeline created successfully with OpenH264.");
}

extern "C" JNIEXPORT void JNICALL
Java_com_example_fingerdraw_MainActivity_nativeFinalize(JNIEnv* env, jobject thiz) {
    if (pipeline) {
        gst_element_set_state(pipeline, GST_STATE_NULL);
        gst_object_unref(pipeline);
        pipeline = nullptr;
    }
    if (main_loop) {
        g_main_loop_quit(main_loop);
        g_main_loop_unref(main_loop);
        main_loop = nullptr;
    }
}

extern "C" JNIEXPORT void JNICALL
Java_com_example_fingerdraw_MainActivity_nativePlay(JNIEnv* env, jobject thiz) {
    if (pipeline) {
        LOGD("Setting pipeline to PLAYING...");
        gst_element_set_state(pipeline, GST_STATE_PLAYING);
    }
}

extern "C" JNIEXPORT void JNICALL
Java_com_example_fingerdraw_MainActivity_nativePause(JNIEnv* env, jobject thiz) {
    if (pipeline) {
        LOGD("Setting pipeline to PAUSED...");
        gst_element_set_state(pipeline, GST_STATE_PAUSED);
    }
}

extern "C" JNIEXPORT void JNICALL
Java_com_example_fingerdraw_MainActivity_nativeSurfaceInit(JNIEnv* env, jobject thiz, jobject surface) {
    native_window = ANativeWindow_fromSurface(env, surface);
    if (pipeline && native_window) {
        GstElement *sink = gst_bin_get_by_name(GST_BIN(pipeline), "sink");
        if (sink) {
            gst_video_overlay_set_window_handle(GST_VIDEO_OVERLAY(sink), (guintptr)native_window);
            gst_object_unref(sink);
            LOGD("Surface bound to sink.");
        }
    }
}

extern "C" JNIEXPORT void JNICALL
Java_com_example_fingerdraw_MainActivity_nativeSurfaceFinalize(JNIEnv* env, jobject thiz) {
    if (pipeline) {
        GstElement *sink = gst_bin_get_by_name(GST_BIN(pipeline), "sink");
        if (sink) {
            gst_video_overlay_set_window_handle(GST_VIDEO_OVERLAY(sink), (guintptr)NULL);
            gst_object_unref(sink);
        }
    }
    if (native_window) {
        ANativeWindow_release(native_window);
        native_window = nullptr;
    }
}
