#include <jni.h>
#include <string>
#include <android/log.h>
#include <android/native_window_jni.h>
#include <gst/gst.h>
#include <gst/video/video.h>
#include <pthread.h>

#define TAG "FingerDrawNative"
#define LOGD(...) __android_log_print(ANDROID_LOG_DEBUG, TAG, __VA_ARGS__)
#define LOGW(...) __android_log_print(ANDROID_LOG_WARN, TAG, __VA_ARGS__)
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

    // Call androidmedia init explicitly if possible
    // Note: In some GStreamer versions, this is handled via JNI_OnLoad or automatically.
    // For static linking, ensuring the plugin is registered is the primary step.

    // DEBUG: List ALL available elements to verify registration
    GList *features = gst_registry_get_feature_list(gst_registry_get(), GST_TYPE_ELEMENT_FACTORY);
    LOGD("--- Registered GStreamer Elements ---");
    for (GList *l = features; l != nullptr; l = l->next) {
        GstPluginFeature *f = (GstPluginFeature *)l->data;
        const gchar* name = gst_plugin_feature_get_name(f);
        LOGD("Element: %s", name);
    }
    gst_plugin_feature_list_free(features);

    pthread_create(&gst_thread, nullptr, gst_worker_thread, nullptr);
}

static void on_pad_added(GstElement *element, GstPad *pad, gpointer data) {
    GstElement *videoconvert = (GstElement *)data;
    GstPad *sinkpad = gst_element_get_static_pad(videoconvert, "sink");

    if (!sinkpad) {
        LOGE("Could not get sink pad from videoconvert");
        return;
    }

    if (gst_pad_is_linked(sinkpad)) {
        LOGD("Sink pad is already linked, ignoring new pad");
        gst_object_unref(sinkpad);
        return;
    }

    GstCaps *caps = gst_pad_query_caps(pad, NULL);
    if (!caps) {
        LOGW("Could not query caps from pad");
        gst_object_unref(sinkpad);
        return;
    }

    GstStructure *str = gst_caps_get_structure(caps, 0);
    if (!str) {
        LOGW("Caps have no structure");
        gst_caps_unref(caps);
        gst_object_unref(sinkpad);
        return;
    }

    const gchar *name = gst_structure_get_name(str);
    LOGD("decodebin added pad with caps: %s", name ? name : "NULL");

    if (name && g_str_has_prefix(name, "video/x-raw")) {
        GstElement *parent = GST_ELEMENT(gst_pad_get_parent(pad));
        gchar *parent_name = gst_element_get_name(parent);
        LOGD("decodebin selected decoder: %s", parent_name ? parent_name : "UNKNOWN");
        
        GstPadLinkReturn ret = gst_pad_link(pad, sinkpad);
        if (ret != GST_PAD_LINK_OK) {
            LOGE("Failed to link decoder %s to videoconvert: %d", parent_name, ret);
        } else {
            LOGD("Successfully linked %s to videoconvert.", parent_name);
        }
        
        g_free(parent_name);
        gst_object_unref(parent);
    } else {
        LOGD("Ignoring non-raw-video pad: %s", name ? name : "NULL");
    }

    gst_caps_unref(caps);
    gst_object_unref(sinkpad);
}

extern "C" JNIEXPORT void JNICALL
Java_com_example_fingerdraw_MainActivity_nativeInit(JNIEnv* env, jobject thiz, jint port, jstring decoderName) {
    GError *error = nullptr;

    const char *decoder_str = env->GetStringUTFChars(decoderName, 0);
    LOGD("Initializing pipeline with decoder: %s", decoder_str);

    char pipeline_str[1024];
    if (strcmp(decoder_str, "playbin") == 0 || strcmp(decoder_str, "decodebin") == 0) {
        // Use decodebin for automatic decoding. Note: no '!' after dbin because it's linked dynamically.
        snprintf(pipeline_str, sizeof(pipeline_str),
            "udpsrc port=%d buffer-size=2097152 caps=\"application/x-rtp,media=video,clock-rate=90000,encoding-name=H264,payload=96\" ! "
            "rtpjitterbuffer latency=200 ! "
            "rtph264depay ! h264parse ! "
            "decodebin name=dbin videoconvert name=conv ! "
            "glimagesink name=sink sync=false async=false force-aspect-ratio=false",
            port);
    } else {
        // Use specific decoder element
        snprintf(pipeline_str, sizeof(pipeline_str),
            "udpsrc port=%d buffer-size=2097152 caps=\"application/x-rtp,media=video,clock-rate=90000,encoding-name=H264,payload=96\" ! "
            "rtpjitterbuffer latency=200 ! "
            "rtph264depay ! h264parse ! "
            "%s ! videoconvert ! "
            "glimagesink name=sink sync=false async=false force-aspect-ratio=false",
            port, decoder_str);
    }

    pipeline = gst_parse_launch(pipeline_str, &error);

    if (pipeline && (strcmp(decoder_str, "playbin") == 0 || strcmp(decoder_str, "decodebin") == 0)) {
        GstElement *dbin = gst_bin_get_by_name(GST_BIN(pipeline), "dbin");
        GstElement *conv = gst_bin_get_by_name(GST_BIN(pipeline), "conv");
        if (dbin && conv) {
            LOGD("Connecting pad-added signal to decodebin");
            g_signal_connect(dbin, "pad-added", G_CALLBACK(on_pad_added), conv);
            gst_object_unref(dbin);
            gst_object_unref(conv);
        } else {
            LOGE("Failed to find dbin or conv elements in pipeline");
        }
    }
    
    env->ReleaseStringUTFChars(decoderName, decoder_str);

    if (error) {
        LOGE("Error creating pipeline: %s", error->message);
        g_error_free(error);
        return;
    }

    GstBus *bus = gst_element_get_bus(pipeline);
    gst_bus_add_signal_watch(bus);
    g_signal_connect(bus, "message", G_CALLBACK(on_bus_message), nullptr);
    gst_object_unref(bus);

    LOGD("Network Pipeline created successfully.");
}

extern "C" JNIEXPORT jboolean JNICALL
Java_com_example_fingerdraw_SettingsActivity_nativeVerifyCodec(JNIEnv* env, jobject thiz, jstring decoderName) {
    if (!gst_is_initialized()) {
        return JNI_FALSE;
    }
    
    const char *decoder_str = env->GetStringUTFChars(decoderName, 0);
    GstElementFactory *factory = gst_element_factory_find(decoder_str);
    env->ReleaseStringUTFChars(decoderName, decoder_str);

    if (factory) {
        gst_object_unref(factory);
        return JNI_TRUE;
    }
    return JNI_FALSE;
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
