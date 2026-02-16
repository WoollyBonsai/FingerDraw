import 'package:flutter/material.dart';
import 'package:media_kit/media_kit.dart';
import 'package:media_kit_video/media_kit_video.dart';
import 'package:socket_io_client/socket_io_client.dart' as IO;

void main() {
  WidgetsFlutterBinding.ensureInitialized();
  MediaKit.ensureInitialized();
  runApp(const MyApp());
}

class MyApp extends StatelessWidget {
  const MyApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Finger Draw',
      theme: ThemeData.dark(),
      home: const MyHomePage(title: 'Finger Draw'),
    );
  }
}

class MyHomePage extends StatefulWidget {
  const MyHomePage({super.key, required this.title});

  final String title;

  @override
  State<MyHomePage> createState() => _MyHomePageState();
}

class _MyHomePageState extends State<MyHomePage> {
  late final Player player;
  late final VideoController controller;
  final SocketIOManager socketManager = SocketIOManager();

  // Hardcoded server IP for now
  final String serverIp = "192.168.1.100"; // Replace with your server's IP

  @override
  void initState() {
    super.initState();
    player = Player(
      configuration: const PlayerConfiguration(
        vo: 'gpu',
        bufferSize: 0,
      ),
    );
    controller = VideoController(player);

    player.open(
      Media(
        'rtp://$serverIp:5000',
        extras: {
          'profile': 'low-latency',
          'untimed': 'yes',
          'demuxer-lavf-o': 'fflags=+nobuffer+fastseek+flush_packets',
          'rtsp-transport': 'udp',
        },
      ),
      play: true,
    );
    socketManager.connect(serverIp);
  }

  @override
  void dispose() {
    player.dispose();
    socketManager.dispose();
    super.dispose();
  }

  void _handlePanStart(DragStartDetails details) {
    // TODO: get screen dimensions from server
    final RenderBox box = context.findRenderObject() as RenderBox;
    final Offset localPosition = box.globalToLocal(details.globalPosition);
    final double x = localPosition.dx / box.size.width;
    final double y = localPosition.dy / box.size.height;
    socketManager.mouseDown(x, y, 1.0);
  }

  void _handlePanUpdate(DragUpdateDetails details) {
    final RenderBox box = context.findRenderObject() as RenderBox;
    final Offset localPosition = box.globalToLocal(details.globalPosition);
    final double x = localPosition.dx / box.size.width;
    final double y = localPosition.dy / box.size.height;
    socketManager.mouseMove(x, y, 1.0);
  }

  void _handlePanEnd(DragEndDetails details) {
    socketManager.mouseUp();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Text(widget.title),
      ),
      body: GestureDetector(
        onPanStart: _handlePanStart,
        onPanUpdate: _handlePanUpdate,
        onPanEnd: _handlePanEnd,
        child: Video(
          controller: controller,
          width: double.infinity,
          height: double.infinity,
          fit: BoxFit.contain,
        ),
      ),
    );
  }
}

class SocketIOManager {
  late IO.Socket socket;

  void connect(String serverIp) {
    socket = IO.io('http://$serverIp:8000', <String, dynamic>{
      'transports': ['websocket'],
      'autoConnect': true,
    });

    socket.onConnect((_) {
      print('Connected to server');
    });

    socket.onDisconnect((_) {
      print('Disconnected from server');
    });
  }

  void mouseDown(double x, double y, double pressure) {
    socket.emit('mouse_down', [x, y, pressure]);
  }

  void mouseMove(double x, double y, double pressure) {
    socket.emit('mouse_move', [x, y, pressure]);
  }

  void mouseUp() {
    socket.emit('mouse_up');
  }

  void dispose() {
    socket.dispose();
  }
}