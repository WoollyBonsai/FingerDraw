
package com.example.fingerdraw

import android.content.Context
import android.content.SharedPreferences
import android.graphics.Bitmap
import android.graphics.BitmapFactory
import android.os.Bundle
import android.util.Base64
import android.view.MotionEvent
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.Image
import androidx.compose.foundation.gestures.detectDragGestures
import androidx.compose.foundation.gestures.rememberTransformableState
import androidx.compose.foundation.gestures.transformable
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
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.asImageBitmap
import androidx.compose.ui.graphics.graphicsLayer
import androidx.compose.ui.input.pointer.pointerInput
import androidx.compose.ui.input.pointer.pointerInteropFilter
import androidx.compose.ui.layout.onSizeChanged
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.tooling.preview.Preview
import androidx.compose.ui.unit.dp
import com.example.fingerdraw.ui.theme.FingerDrawTheme
import io.socket.client.IO
import io.socket.client.Socket
import java.net.URISyntaxException
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import android.util.Log
import org.json.JSONObject


@OptIn(ExperimentalMaterial3Api::class, ExperimentalComposeUiApi::class)
class MainActivity : ComponentActivity() {

    private var socket: Socket? = null
    private lateinit var sharedPreferences: SharedPreferences

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        sharedPreferences = getSharedPreferences("FingerDrawPrefs", Context.MODE_PRIVATE)

        setContent {
            val context = LocalContext.current
            val currentThemeName = sharedPreferences.getString("app_theme", AppTheme.SYSTEM.name)
            val currentTheme = AppTheme.valueOf(currentThemeName ?: AppTheme.SYSTEM.name)

            val darkTheme = when (currentTheme) {
                AppTheme.SYSTEM -> isSystemInDarkTheme()
                AppTheme.LIGHT -> false
                AppTheme.DARK -> true
            }

            FingerDrawTheme(darkTheme = darkTheme) {
                // A surface container using the 'background' color from the theme
                Surface(
                    modifier = Modifier.fillMaxSize(),
                    color = MaterialTheme.colorScheme.background
                ) {
                    var screenBitmap by remember { mutableStateOf<Bitmap?>(null) }
                    var ipAddress by remember { mutableStateOf(sharedPreferences.getString("last_ip_address", "") ?: "") }
                    var isConnected by remember { mutableStateOf(false) }

                    var scale by remember { mutableStateOf(1f) }
                    var offset by remember { mutableStateOf(Offset.Zero) }
                    var imageDisplayWidth by remember { mutableStateOf(1) }
                    var imageDisplayHeight by remember { mutableStateOf(1) }

                    val secondaryButtonAction = remember {
                        val actionName = sharedPreferences.getString("stylus_secondary_button_action", StylusAction.RIGHT_CLICK.name)
                        StylusAction.valueOf(actionName ?: StylusAction.RIGHT_CLICK.name)
                    }

                    val streamQuality = remember {
                        val quality = sharedPreferences.getInt("stream_quality", 75)
                        quality
                    }


                    val state = rememberTransformableState { zoomChange, offsetChange, rotationChange ->
                        scale *= zoomChange
                        offset += offsetChange
                    }
                    val scope = rememberCoroutineScope()

                    Column(modifier = Modifier.fillMaxSize()) {
                        if (!isConnected) {
                            Row(
                                modifier = Modifier
                                    .fillMaxWidth()
                                    .padding(16.dp),
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
                                    val cleanedIp = ipAddress.split(":").first()
                                    scope.launch {
                                        connectToServer(cleanedIp, streamQuality) { bitmap -> screenBitmap = bitmap }
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
                        }

                        if (isConnected && screenBitmap != null) {
                            val serverImageWidth = screenBitmap!!.width.toFloat()
                            val serverImageHeight = screenBitmap!!.height.toFloat()

                            Box(modifier = Modifier.fillMaxSize()) {
                                Image(
                                    bitmap = screenBitmap!!.asImageBitmap(),
                                    contentDescription = "Screen Share",
                                    modifier = Modifier
                                        .fillMaxSize()
                                        .onSizeChanged { size ->
                                            imageDisplayWidth = size.width
                                            imageDisplayHeight = size.height
                                        }
                                        .graphicsLayer(
                                            scaleX = scale,
                                            scaleY = scale,
                                            translationX = offset.x,
                                            translationY = offset.y
                                        )
                                        .transformable(state = state)
                                        .pointerInteropFilter { motionEvent ->
                                            val pointerIndex = motionEvent.actionIndex
                                            val isStylus = motionEvent.getToolType(pointerIndex) == MotionEvent.TOOL_TYPE_STYLUS

                                            if (isStylus) {
                                                when (motionEvent.actionMasked) {
                                                    MotionEvent.ACTION_DOWN -> {
                                                        val buttonState = motionEvent.buttonState
                                                        if (buttonState and MotionEvent.BUTTON_SECONDARY != 0) {
                                                            when (secondaryButtonAction) {
                                                                StylusAction.RIGHT_CLICK -> socket?.emit("right_click")
                                                                StylusAction.MIDDLE_CLICK -> socket?.emit("middle_click")
                                                                StylusAction.UNDO -> socket?.emit("undo")
                                                                StylusAction.REDO -> socket?.emit("redo")
                                                                else -> {}
                                                            }
                                                            return@pointerInteropFilter true // Consume the event
                                                        }
                                                    }
                                                }
                                            }
                                            false // Don't consume the event if it's not a stylus button
                                        }
                                        .pointerInput(scale, offset, imageDisplayWidth, imageDisplayHeight) {
                                            detectDragGestures(
                                                onDragStart = { startOffset ->
                                                    val transformedX = (startOffset.x - offset.x) / scale
                                                    val transformedY = (startOffset.y - offset.y) / scale
                                                    val serverX = transformedX * (serverImageWidth / imageDisplayWidth)
                                                    val serverY = transformedY * (serverImageHeight / imageDisplayHeight)
                                                    socket?.emit("mouse_down", serverX, serverY)
                                                },
                                                onDragEnd = {
                                                    socket?.emit("mouse_up")
                                                },
                                                onDragCancel = {
                                                    socket?.emit("mouse_up")
                                                },
                                                onDrag = { change, dragAmount ->
                                                    change.consume()
                                                    val transformedX = (change.position.x - offset.x) / scale
                                                    val transformedY = (change.position.y - offset.y) / scale
                                                    val serverX = transformedX * (serverImageWidth / imageDisplayWidth)
                                                    val serverY = transformedY * (serverImageHeight / imageDisplayHeight)
                                                    socket?.emit("mouse_move", serverX, serverY)
                                                }
                                            )
                                        }
                                )

                                Column(
                                    modifier = Modifier
                                        .align(androidx.compose.ui.Alignment.BottomEnd)
                                        .padding(16.dp),
                                    horizontalAlignment = androidx.compose.ui.Alignment.End
                                ) {
                                    // Undo button
                                    Button(
                                        onClick = { socket?.emit("undo") },
                                        modifier = Modifier.padding(bottom = 8.dp)
                                    ) {
                                        Text("Undo")
                                    }
                                    // Redo button
                                    Button(
                                        onClick = { socket?.emit("redo") },
                                        modifier = Modifier.padding(bottom = 8.dp)
                                    ) {
                                        Text("Redo")
                                    }
                                    // Right-click button
                                    Button(
                                        onClick = { socket?.emit("right_click") }
                                    ) {
                                        Text("Right Click")
                                    }
                                }
                            }
                        } else if (isConnected && screenBitmap == null) {
                            Text("Connecting and waiting for screen stream...")
                        } else {
                            Text("Please enter server IP and connect.")
                        }
                    }
                }
            }
        }
    }

    private suspend fun connectToServer(ip: String, streamQuality: Int, onScreenUpdate: (Bitmap) -> Unit) {
        withContext(Dispatchers.IO) {
            try {
                Log.d("MainActivity", "Connecting to IP: '$ip'")
                val opts = IO.Options()
                opts.forceNew = true
                opts.transports = arrayOf("websocket")
                socket = IO.socket("http://$ip:8000", opts)
                socket?.connect()
                socket?.on(Socket.EVENT_CONNECT) {
                    println("connected to socket.io server")
                    socket?.emit("start_stream", streamQuality) // Request to start streaming with quality
                }?.on("screen_frame") { args ->
                    val data = args[0] as JSONObject
                    val imageBase64 = data.getString("image")
                    val decodedString = Base64.decode(imageBase64, Base64.DEFAULT)
                    val bitmap = BitmapFactory.decodeByteArray(decodedString, 0, decodedString.size)
                    runOnUiThread {
                        onScreenUpdate(bitmap)
                    }
                }?.on(Socket.EVENT_DISCONNECT) {
                    println("disconnected from socket.io server")
                }?.on(Socket.EVENT_CONNECT_ERROR) { args ->
                    println("Socket connection error: ${args[0]}")
                }
            } catch (e: URISyntaxException) {
                e.printStackTrace()
            } catch (e: RuntimeException) {
                Log.e("MainActivity", "RuntimeException in connectToServer", e)
                e.printStackTrace()
            }
        }
    }

    override fun onDestroy() {
        super.onDestroy()
        socket?.disconnect()
    }
}

@Composable
fun Greeting(name: String, modifier: Modifier = Modifier) {
    Text(
        text = "Hello $name!",
        modifier = modifier
    )
}

@Preview(showBackground = true)
@Composable
fun GreetingPreview() {
    FingerDrawTheme {
        Greeting("Android")
    }
}
