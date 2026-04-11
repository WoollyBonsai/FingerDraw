package com.example.fingerdraw

import android.content.Context
import android.graphics.Color
import android.net.wifi.WifiManager
import android.os.Bundle
import android.util.Log
import android.view.*
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import androidx.core.view.WindowCompat
import androidx.core.view.WindowInsetsCompat
import androidx.core.view.WindowInsetsControllerCompat
import com.example.fingerdraw.databinding.ActivityMainBinding
import io.socket.client.IO
import io.socket.client.Socket
import java.net.DatagramPacket
import java.net.DatagramSocket
import java.net.InetAddress
import java.net.URISyntaxException
import java.util.concurrent.Executors
import kotlin.math.max
import kotlin.math.min

class MainActivity : AppCompatActivity(), SurfaceHolder.Callback {

    private lateinit var binding: ActivityMainBinding
    private var isGStreamerInitialized = false
    
    private var wifiLock: WifiManager.WifiLock? = null
    private var multicastLock: WifiManager.MulticastLock? = null

    // Network
    private var mSocket: Socket? = null
    private var serverUrl = "" 
    private var serverIpOnly = ""
    private val udpPort = 9999
    
    // UDP Input
    private val executor = Executors.newSingleThreadExecutor()
    private var udpSocket: DatagramSocket? = null

    // Interaction State
    private var isPenMode = false
    private var isAltPressed = false
    private var scaleFactor = 1.0f
    private var translateX = 0.0f
    private var translateY = 0.0f
    private lateinit var scaleDetector: ScaleGestureDetector
    private lateinit var gestureDetector: GestureDetector

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        val ip = intent.getStringExtra("SERVER_IP") ?: ""
        if (ip.isEmpty()) {
            finish()
            return
        }
        serverIpOnly = ip
        serverUrl = "http://$ip:8000"

        binding = ActivityMainBinding.inflate(layoutInflater)
        setContentView(binding.root)

        binding.touchOverlay.setBackgroundColor(Color.TRANSPARENT)

        setupImmersiveMode()
        setupLocks()
        setupSocket()
        setupUdp()
        setupInteractions()

        // Send initial HELO to trigger IP detection on server
        binding.root.postDelayed({
            sendUdp("HELO:I_AM_${getLocalIpAddress()}")
        }, 1000)

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

    private fun getLocalIpAddress(): String {
        return try {
            val wifiManager = applicationContext.getSystemService(Context.WIFI_SERVICE) as WifiManager
            val ipAddress = wifiManager.connectionInfo.ipAddress
            String.format(
                "%d.%d.%d.%d",
                ipAddress and 0xff,
                ipAddress shr 8 and 0xff,
                ipAddress shr 16 and 0xff,
                ipAddress shr 24 and 0xff
            )
        } catch (e: Exception) {
            "0.0.0.0"
        }
    }

    private fun setupSocket() {
        try {
            val opts = IO.Options()
            opts.forceNew = true
            opts.reconnection = true
            
            mSocket = IO.socket(serverUrl, opts)
            
            mSocket?.on(Socket.EVENT_CONNECT) {
                Log.d("FingerDraw", "CONNECTED to Socket.IO server at $serverUrl")
                sendUdp("HELO:CONNECTED_VIA_SOCKETIO")
                runOnUiThread {
                    Toast.makeText(this, "Connected to Server", Toast.LENGTH_SHORT).show()
                }
            }
            
            mSocket?.on("disconnect_ack") {
                Log.d("FingerDraw", "Server acknowledged disconnect. Closing...")
                runOnUiThread {
                    finish()
                }
            }

            mSocket?.on(Socket.EVENT_CONNECT_ERROR) { args ->
                Log.e("FingerDraw", "Connection Error: ${args[0]}")
            }

            mSocket?.connect()
        } catch (e: URISyntaxException) {
            Log.e("FingerDraw", "Socket.IO URI error", e)
        }
    }

    private fun setupUdp() {
        executor.execute {
            try {
                udpSocket = DatagramSocket()
                Log.d("FingerDraw", "UDP Socket initialized")
            } catch (e: Exception) {
                Log.e("FingerDraw", "UDP Init Error", e)
            }
        }
    }

    private fun sendUdp(msg: String) {
        executor.execute {
            try {
                val data = msg.toByteArray()
                val address = InetAddress.getByName(serverIpOnly)
                val packet = DatagramPacket(data, data.size, address, udpPort)
                udpSocket?.send(packet)
            } catch (e: Exception) {
                // Ignore
            }
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
            Log.d("FingerDraw", "Requesting disconnect from server...")
            mSocket?.emit("disconnect_request")
            // Timeout safety: if server doesn't respond in 2 seconds, just close
            binding.root.postDelayed({
                if (!isFinishing) finish()
            }, 2000)
        }

        binding.btnRestartStream.setOnClickListener {
            Log.d("FingerDraw", "Requesting stream restart...")
            mSocket?.emit("restart_stream")
            Toast.makeText(this, "Restarting Stream...", Toast.LENGTH_SHORT).show()
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
            setPenMode(true)
        }

        binding.btnPointer.setOnClickListener {
            setPenMode(false)
        }

        binding.btnAlt.setOnClickListener {
            isAltPressed = !isAltPressed
            val color = if (isAltPressed) Color.parseColor("#4CAF50") else Color.TRANSPARENT
            binding.btnAlt.setBackgroundColor(color)
            sendUdp("ALT:${if (isAltPressed) 1 else 0}")
        }

        binding.btnMeta.setOnClickListener {
            sendUdp("META")
        }

        binding.btnTab.setOnClickListener {
            sendUdp("TAB")
        }

        setPenMode(false)

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

    private fun setPenMode(enabled: Boolean) {
        isPenMode = enabled
        if (isPenMode) {
            binding.btnPen.setBackgroundColor(Color.parseColor("#4CAF50"))
            binding.btnPointer.setBackgroundColor(Color.TRANSPARENT)
        } else {
            binding.btnPen.setBackgroundColor(Color.TRANSPARENT)
            binding.btnPointer.setBackgroundColor(Color.parseColor("#4CAF50"))
        }
    }

    private fun handlePenTouch(event: MotionEvent) {
        val w = binding.touchOverlay.width.toFloat()
        val h = binding.touchOverlay.height.toFloat()
        
        if (w <= 0 || h <= 0) return

        // Inverse transform to find coordinates on the original unscaled video
        val xInitial = (event.x - translateX - w / 2f) / scaleFactor + w / 2f
        val yInitial = (event.y - translateY - h / 2f) / scaleFactor + h / 2f
        
        val xNorm = xInitial / w
        val yNorm = yInitial / h
        val pressure = event.pressure

        val finalX = max(0f, min(xNorm, 1f))
        val finalY = max(0f, min(yNorm, 1f))

        when (event.action) {
            MotionEvent.ACTION_DOWN -> sendUdp("D:$finalX,$finalY,$pressure")
            MotionEvent.ACTION_MOVE -> sendUdp("M:$finalX,$finalY,$pressure")
            MotionEvent.ACTION_UP -> sendUdp("U")
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
        udpSocket?.close()
        executor.shutdown()
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
