package com.example.fingerdraw

import android.content.Context
import android.graphics.Color
import android.net.wifi.WifiManager
import android.os.Bundle
import android.util.Log
import android.view.*
import androidx.appcompat.app.AppCompatActivity
import androidx.core.view.WindowCompat
import androidx.core.view.WindowInsetsCompat
import androidx.core.view.WindowInsetsControllerCompat
import com.example.fingerdraw.databinding.ActivityMainBinding
import io.socket.client.IO
import io.socket.client.Socket
import java.net.URISyntaxException
import kotlin.math.max
import kotlin.math.min

class MainActivity : AppCompatActivity(), SurfaceHolder.Callback {

    private lateinit var binding: ActivityMainBinding
    private var isGStreamerInitialized = false
    
    private var wifiLock: WifiManager.WifiLock? = null
    private var multicastLock: WifiManager.MulticastLock? = null

    // Socket.IO
    private var mSocket: Socket? = null
    // UPDATED TO YOUR PC'S ACTUAL IP
    private val serverUrl = "http://172.16.217.118:8000" 

    // Interaction State
    private var isPenMode = false
    private var scaleFactor = 1.0f
    private var translateX = 0.0f
    private var translateY = 0.0f
    private lateinit var scaleDetector: ScaleGestureDetector
    private lateinit var gestureDetector: GestureDetector

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        binding = ActivityMainBinding.inflate(layoutInflater)
        setContentView(binding.root)

        setupImmersiveMode()
        setupLocks()
        setupSocket()
        setupInteractions()

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
    }

    private fun setupSocket() {
        try {
            val opts = IO.Options()
            opts.forceNew = true
            opts.reconnection = true
            
            mSocket = IO.socket(serverUrl, opts)
            
            mSocket?.on(Socket.EVENT_CONNECT) {
                Log.d("FingerDraw", "CONNECTED to Socket.IO server at $serverUrl")
            }
            
            mSocket?.on(Socket.EVENT_CONNECT_ERROR) { args ->
                Log.e("FingerDraw", "Connection Error: ${args[0]}")
            }

            mSocket?.connect()
            Log.d("FingerDraw", "Socket connection initiated to $serverUrl")
        } catch (e: URISyntaxException) {
            Log.e("FingerDraw", "Socket.IO URI error", e)
        }
    }

    private fun setupImmersiveMode() {
        WindowCompat.setDecorFitsSystemWindows(window, false)
        WindowInsetsControllerCompat(window, binding.root).let { controller ->
            controller.hide(WindowInsetsCompat.Type.systemBars())
            controller.systemBarsBehavior = WindowInsetsControllerCompat.BEHAVIOR_SHOW_TRANSIENT_BARS_BY_SWIPE
        }
    }

    private fun setupLocks() {
        val wifiManager = applicationContext.getSystemService(Context.WIFI_SERVICE) as WifiManager
        wifiLock = wifiManager.createWifiLock(WifiManager.WIFI_MODE_FULL_HIGH_PERF, "FingerDrawWifiLock")
        multicastLock = wifiManager.createMulticastLock("FingerDrawMulticastLock")
    }

    private fun setupInteractions() {
        binding.btnDisconnect.setOnClickListener {
            mSocket?.disconnect()
            finish()
        }

        binding.btnPin.setOnClickListener {
            binding.topBar.visibility = View.GONE
            binding.btnOpenTaskbar.visibility = View.VISIBLE
        }
        
        binding.btnOpenTaskbar.setOnClickListener {
            binding.topBar.visibility = View.VISIBLE
            binding.btnOpenTaskbar.visibility = View.GONE
        }

        binding.btnPen.setOnClickListener {
            isPenMode = !isPenMode
            if (isPenMode) {
                binding.btnPen.setBackgroundColor(Color.parseColor("#4CAF50"))
                Log.d("FingerDraw", "Pen Mode: ON")
            } else {
                binding.btnPen.setBackgroundColor(Color.TRANSPARENT)
                Log.d("FingerDraw", "Pen Mode: OFF")
            }
        }

        scaleDetector = ScaleGestureDetector(this, object : ScaleGestureDetector.SimpleOnScaleGestureListener() {
            override fun onScale(detector: ScaleGestureDetector): Boolean {
                if (!isPenMode) {
                    scaleFactor *= detector.scaleFactor
                    scaleFactor = max(1.0f, min(scaleFactor, 5.0f))
                    applyTransform()
                    return true
                }
                return false
            }
        })

        gestureDetector = GestureDetector(this, object : GestureDetector.SimpleOnGestureListener() {
            override fun onScroll(e1: MotionEvent?, e2: MotionEvent, distanceX: Float, distanceY: Float): Boolean {
                if (!isPenMode && scaleFactor > 1.0f) {
                    translateX -= distanceX
                    translateY -= distanceY
                    applyTransform()
                    return true
                }
                return false
            }
        })

        binding.touchOverlay.setOnTouchListener { _, event ->
            if (isPenMode) {
                handlePenTouch(event)
            } else {
                scaleDetector.onTouchEvent(event)
                gestureDetector.onTouchEvent(event)
            }
            true
        }
    }

    private fun handlePenTouch(event: MotionEvent) {
        val x = event.x / binding.touchOverlay.width
        val y = event.y / binding.touchOverlay.height
        val pressure = event.pressure

        when (event.action) {
            MotionEvent.ACTION_DOWN -> {
                mSocket?.emit("mouse_down", x, y, pressure)
            }
            MotionEvent.ACTION_MOVE -> {
                mSocket?.emit("mouse_move", x, y, pressure)
            }
            MotionEvent.ACTION_UP -> {
                mSocket?.emit("mouse_up")
            }
        }
    }

    private fun applyTransform() {
        val maxTranslationX = (scaleFactor - 1.0f) * binding.surfaceVideo.width / 2f
        val maxTranslationY = (scaleFactor - 1.0f) * binding.surfaceVideo.height / 2f
        
        translateX = max(-maxTranslationX, min(translateX, maxTranslationX))
        translateY = max(-maxTranslationY, min(translateY, maxTranslationY))

        binding.surfaceVideo.scaleX = scaleFactor
        binding.surfaceVideo.scaleY = scaleFactor
        binding.surfaceVideo.translationX = translateX
        binding.surfaceVideo.translationY = translateY
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
        mSocket?.disconnect()
        if (isGStreamerInitialized) {
            nativeFinalize()
        }
    }

    override fun surfaceCreated(holder: SurfaceHolder) {
        if (isGStreamerInitialized) {
            nativeSurfaceInit(holder.surface)
        }
    }

    override fun surfaceChanged(holder: SurfaceHolder, format: Int, width: Int, height: Int) {}

    override fun surfaceDestroyed(holder: SurfaceHolder) {
        if (isGStreamerInitialized) {
            nativeSurfaceFinalize()
        }
    }

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
