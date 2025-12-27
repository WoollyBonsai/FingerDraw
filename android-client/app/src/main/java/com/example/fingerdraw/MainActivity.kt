
package com.example.fingerdraw

import android.content.Context
import android.content.SharedPreferences
import android.os.Bundle
import android.view.HapticFeedbackConstants
import android.view.MotionEvent
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.gestures.detectDragGestures
import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.foundation.layout.*
import androidx.compose.material3.Button
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.TextField
import androidx.compose.runtime.*
import androidx.compose.ui.ExperimentalComposeUiApi
import androidx.compose.ui.Modifier
import androidx.compose.ui.input.pointer.pointerInput
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.LocalView
import androidx.compose.ui.viewinterop.AndroidView
import androidx.compose.ui.unit.dp
import androidx.media3.common.MediaItem
import androidx.media3.common.PlaybackException
import androidx.media3.common.Player
import androidx.media3.datasource.DataSource
import androidx.media3.datasource.UdpDataSource
import androidx.media3.exoplayer.ExoPlayer
import androidx.media3.exoplayer.source.MediaSource
import androidx.media3.exoplayer.source.ProgressiveMediaSource
import androidx.media3.ui.PlayerView
import io.socket.client.IO
import io.socket.client.Socket
import kotlinx.coroutines.launch
import android.util.Log
import com.example.fingerdraw.ui.theme.FingerDrawTheme

@OptIn(ExperimentalMaterial3Api::class, ExperimentalComposeUiApi::class)
class MainActivity : ComponentActivity() {

    private var socket: Socket? = null
    private lateinit var sharedPreferences: SharedPreferences
    private var exoPlayer: ExoPlayer? = null

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        sharedPreferences = getSharedPreferences("FingerDrawPrefs", Context.MODE_PRIVATE)

        setContent {
            val context = LocalContext.current
            val view = LocalView.current
            val currentThemeName = sharedPreferences.getString("app_theme", AppTheme.SYSTEM.name)
            val currentTheme = AppTheme.valueOf(currentThemeName ?: AppTheme.SYSTEM.name)
            val darkTheme = when (currentTheme) {
                AppTheme.SYSTEM -> isSystemInDarkTheme()
                AppTheme.LIGHT -> false
                AppTheme.DARK -> true
            }

            var ipAddress by remember { mutableStateOf(sharedPreferences.getString("last_ip_address", "") ?: "") }
            var isConnected by remember { mutableStateOf(false) }

            val scope = rememberCoroutineScope()

            FingerDrawTheme(darkTheme = darkTheme) {
                Surface(
                    modifier = Modifier.fillMaxSize(),
                    color = MaterialTheme.colorScheme.background
                ) {
                    // ExoPlayer (Media3) Lifecycle Management
                    DisposableEffect(isConnected) {
                        if (isConnected) {
                            val serverIp = ipAddress.split(":").first()
                            exoPlayer = ExoPlayer.Builder(context).build()
                            val playerListener = object : Player.Listener {
                                override fun onPlaybackStateChanged(playbackState: Int) {
                                    Log.d("MainActivity", "Player state changed: $playbackState")
                                }
                                override fun onPlayerError(error: PlaybackException) {
                                    Log.e("MainActivity", "Player error", error)
                                }
                            }
                            exoPlayer?.addListener(playerListener)
                            
                            // For RTP over UDP, Media3 handles it automatically
                            val rtpUri = "rtp://0.0.0.0:5000" // Listen on all interfaces
                            val dataSourceFactory: DataSource.Factory =
                                DataSource.Factory { UdpDataSource() }
                            val mediaSource = ProgressiveMediaSource.Factory(dataSourceFactory)
                                .createMediaSource(MediaItem.fromUri(rtpUri))

                            exoPlayer?.setMediaSource(mediaSource)
                            exoPlayer?.prepare()
                            exoPlayer?.playWhenReady = true
                        } else {
                            exoPlayer?.release()
                            exoPlayer = null
                        }

                        onDispose {
                            exoPlayer?.release()
                            exoPlayer = null
                            socket?.emit("stop_stream")
                        }
                    }

                    Column(modifier = Modifier.fillMaxSize()) {
                        if (!isConnected) {
                            // Connection UI
                            Row(
                                modifier = Modifier.fillMaxWidth().padding(16.dp),
                                horizontalArrangement = Arrangement.SpaceBetween
                            ) {
                                TextField(
                                    value = ipAddress,
                                    onValueChange = { ipAddress = it },
                                    label = { Text("Server IP Address") },
                                    modifier = Modifier.weight(1f)
                                )
                                Spacer(modifier = Modifier.width(8.dp))
                                Button(onClick = {
                                    scope.launch {
                                        connectToServer(ipAddress.split(":").first())
                                    }
                                    isConnected = true
                                    with(sharedPreferences.edit()) {
                                        putString("last_ip_address", ipAddress)
                                        apply()
                                    }
                                }) {
                                    Text("Connect")
                                }
                            }
                        } else {
                            // PlayerView and Input Overlay
                            Box(modifier = Modifier.fillMaxSize()) {
                                AndroidView(
                                    factory = { ctx ->
                                        PlayerView(ctx).apply {
                                            useController = false
                                            player = exoPlayer
                                        }
                                    },
                                    modifier = Modifier
                                        .fillMaxSize()
                                        .pointerInput(Unit) {
                                            detectDragGestures(
                                                onDragStart = { offset ->
                                                    view.performHapticFeedback(HapticFeedbackConstants.LONG_PRESS)
                                                    val normalizedX = offset.x / size.width
                                                    val normalizedY = offset.y / size.height
                                                    socket?.emit("mouse_down", normalizedX, normalizedY)
                                                },
                                                onDragEnd = {
                                                    socket?.emit("mouse_up")
                                                },
                                                onDragCancel = {
                                                    socket?.emit("mouse_up")
                                                },
                                                onDrag = { change, dragAmount ->
                                                    val normalizedX = change.position.x / size.width
                                                    val normalizedY = change.position.y / size.height
                                                    socket?.emit("mouse_move", normalizedX, normalizedY)
                                                }
                                            )
                                        }
                                )
                            }
                        }
                    }
                }
            }
        }
    }

    private fun connectToServer(ip: String) {
        try {
            val opts = IO.Options()
            opts.forceNew = true
            opts.transports = arrayOf("websocket")
            socket = IO.socket("http://$ip:8000", opts).connect()
            socket?.on(Socket.EVENT_CONNECT) {
                Log.d("MainActivity", "Connected to socket.io server")
            }
            socket?.on(Socket.EVENT_DISCONNECT) {
                Log.d("MainActivity", "Disconnected from socket.io server")
            }
            socket?.on(Socket.EVENT_CONNECT_ERROR) { args ->
                Log.e("MainActivity", "Socket connection error: ${args.getOrNull(0)}")
            }
        } catch (e: Exception) {
            Log.e("MainActivity", "Error connecting to server", e)
        }
    }

    override fun onDestroy() {
        super.onDestroy()
        socket?.disconnect()
        exoPlayer?.release()
    }
}
