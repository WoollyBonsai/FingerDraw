package com.example.fingerdraw

import android.content.Context
import android.net.wifi.WifiManager
import android.os.Bundle
import android.util.Log
import android.view.Surface
import android.view.SurfaceHolder
import androidx.appcompat.app.AppCompatActivity
import com.example.fingerdraw.databinding.ActivityMainBinding

class MainActivity : AppCompatActivity(), SurfaceHolder.Callback {

    private lateinit var binding: ActivityMainBinding
    private var isGStreamerInitialized = false
    
    private var wifiLock: WifiManager.WifiLock? = null
    private var multicastLock: WifiManager.MulticastLock? = null

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        binding = ActivityMainBinding.inflate(layoutInflater)
        setContentView(binding.root)

        // Initialize GStreamer
        try {
            org.freedesktop.gstreamer.GStreamer.init(this)
            isGStreamerInitialized = true
            Log.d("FingerDraw", "GStreamer initialized")
            nativeInit()
        } catch (e: Exception) {
            Log.e("FingerDraw", "GStreamer init failed", e)
        }

        binding.surfaceVideo.holder.addCallback(this)
        setupLocks()
    }
    
    private fun setupLocks() {
        val wifiManager = applicationContext.getSystemService(Context.WIFI_SERVICE) as WifiManager
        wifiLock = wifiManager.createWifiLock(WifiManager.WIFI_MODE_FULL_HIGH_PERF, "FingerDrawWifiLock")
        multicastLock = wifiManager.createMulticastLock("FingerDrawMulticastLock")
    }

    override fun onResume() {
        super.onResume()
        wifiLock?.acquire()
        multicastLock?.acquire()
        if (isGStreamerInitialized) {
            nativePlay()
        }
    }

    override fun onPause() {
        super.onPause()
        if (wifiLock?.isHeld == true) wifiLock?.release()
        if (multicastLock?.isHeld == true) multicastLock?.release()
        if (isGStreamerInitialized) {
            nativePause()
        }
    }

    override fun onDestroy() {
        super.onDestroy()
        if (isGStreamerInitialized) {
            nativeFinalize()
        }
    }

    // --- SurfaceHolder.Callback ---
    override fun surfaceCreated(holder: SurfaceHolder) {
        Log.d("FingerDraw", "Surface created: ${holder.surface}")
        if (isGStreamerInitialized) {
            // Important: On some devices, we need to pass the Surface after a small delay
            // or ensure it's fully ready.
            nativeSurfaceInit(holder.surface)
        }
    }

    override fun surfaceChanged(holder: SurfaceHolder, format: Int, width: Int, height: Int) {
        Log.d("FingerDraw", "Surface changed: $width x $height")
    }

    override fun surfaceDestroyed(holder: SurfaceHolder) {
        Log.d("FingerDraw", "Surface destroyed")
        if (isGStreamerInitialized) {
            nativeSurfaceFinalize()
        }
    }

    // --- Native Methods ---
    private external fun nativeInit()
    private external fun nativeFinalize()
    private external fun nativePlay()
    private external fun nativePause()
    private external fun nativeSurfaceInit(surface: Surface)
    private external fun nativeSurfaceFinalize()

    companion object {
        init {
            System.loadLibrary("fingerdraw-native")
        }
    }
}
