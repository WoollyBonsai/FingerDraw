woolly@fedora:~/Work/FingerDraw/linux-server$ adb logcat --pid=$(adb shell pidof -s com.example.fingerdraw)
--------- beginning of main
01-18 20:39:05.247 18592 18592 E Zygote  : process_name_ptr:18592 com.example.fingerdraw
01-18 20:39:05.266 18592 18592 I mple.fingerdraw: Late-enabling -Xcheck:jni
01-18 20:39:05.332 18592 18592 I mple.fingerdraw: Using CollectorTypeCC GC.
01-18 20:39:05.361 18592 18592 D nativeloader: Load libframework-connectivity-tiramisu-jni.so using APEX ns com_android_tethering for caller /apex/com.android.tethering/javalib/framework-connectivity-t.jar: ok
01-18 20:39:05.374 18592 18592 W System.err: android.system.ErrnoException: open failed: ENOENT (No such file or directory)
01-18 20:39:05.375 18592 18592 W System.err: 	at libcore.io.Linux.open(Native Method)
01-18 20:39:05.375 18592 18592 W System.err: 	at libcore.io.ForwardingOs.open(ForwardingOs.java:574)
01-18 20:39:05.376 18592 18592 W System.err: 	at libcore.io.BlockGuardOs.open(BlockGuardOs.java:274)
01-18 20:39:05.376 18592 18592 W System.err: 	at libcore.io.ForwardingOs.open(ForwardingOs.java:574)
01-18 20:39:05.376 18592 18592 W System.err: 	at android.app.ActivityThread$AndroidOs.open(ActivityThread.java:8381)
01-18 20:39:05.377 18592 18592 W System.err: 	at android.system.Os.open(Os.java:508)
01-18 20:39:05.377 18592 18592 W System.err: 	at android.os.perfdebug.PerfDebugMonitorImpl.monitorVersionControl(PerfDebugMonitorImpl.java:206)
01-18 20:39:05.377 18592 18592 W System.err: 	at android.os.perfdebug.PerfDebugMonitorImpl.prepareMonitor(PerfDebugMonitorImpl.java:187)
01-18 20:39:05.377 18592 18592 W System.err: 	at android.app.ActivityThread.main(ActivityThread.java:8468)
01-18 20:39:05.378 18592 18592 W System.err: 	at java.lang.reflect.Method.invoke(Native Method)
01-18 20:39:05.378 18592 18592 W System.err: 	at com.android.internal.os.RuntimeInit$MethodAndArgsCaller.run(RuntimeInit.java:561)
01-18 20:39:05.378 18592 18592 W System.err: 	at com.android.internal.os.ZygoteInit.main(ZygoteInit.java:954)
01-18 20:39:05.378 18592 18592 I MessageMonitor: Load libmiui_runtime
01-18 20:39:05.415 18592 18592 D CompatibilityChangeReporter: Compat change id reported: 171979766; UID 10351; state: ENABLED
01-18 20:39:05.737 18592 18592 D nativeloader: Configuring clns-4 for other apk /data/app/~~rWSh_2uOwOcBHmXCuPOh5g==/com.example.fingerdraw-i67PK96_vMTzQ-opZP9GCg==/base.apk. target_sdk_version=34, uses_libraries=, library_path=/data/app/~~rWSh_2uOwOcBHmXCuPOh5g==/com.example.fingerdraw-i67PK96_vMTzQ-opZP9GCg==/lib/arm64, permitted_path=/data:/mnt/expand:/data/user/0/com.example.fingerdraw
01-18 20:39:05.751 18592 18592 D nativeloader: Load libframework-connectivity-jni.so using APEX ns com_android_tethering for caller /apex/com.android.tethering/javalib/framework-connectivity.jar: ok
01-18 20:39:05.753 18592 18592 I Perf    : Connecting to perf service.
01-18 20:39:05.765 18592 18592 V GraphicsEnvironment: ANGLE Developer option for 'com.example.fingerdraw' set to: 'default'
01-18 20:39:05.766 18592 18592 V GraphicsEnvironment: ANGLE GameManagerService for com.example.fingerdraw: false
01-18 20:39:05.769 18592 18592 V GraphicsEnvironment: App is not on the allowlist for updatable production driver.
01-18 20:39:05.778 18592 18592 I ForceDarkHelperStubImpl: initialize for com.example.fingerdraw , ForceDarkOrigin
01-18 20:39:05.779 18592 18592 D nativeloader: Load libforcedarkimpl.so using system ns (caller=/system_ext/framework/miui-framework.jar): ok
01-18 20:39:05.779 18592 18592 D mple.fingerdraw: JNI_OnLoad success
01-18 20:39:05.780 18592 18592 I MiuiForceDarkConfig: setConfig density:2.750000, mainRule:0, secondaryRule:0, tertiaryRule:0
01-18 20:39:05.787 18592 18592 D NetworkSecurityConfig: Using Network Security Config from resource network_security_config debugBuild: true
01-18 20:39:05.789 18592 18592 D NetworkSecurityConfig: Using Network Security Config from resource network_security_config debugBuild: true
01-18 20:39:05.842 18592 18592 W libc    : Access denied finding property "ro.vendor.df.effect.conflict"
01-18 20:39:05.857 18592 18592 D IS_CTS_MODE: false
01-18 20:39:05.857 18592 18592 D MULTI_WINDOW_ENABLED: false
01-18 20:39:05.860 18592 18592 D DecorView[]: getWindowModeFromSystem  windowmode is 1
--------- beginning of system
01-18 20:39:05.937 18592 18592 W Looper  : PerfMonitor looperActivity : package=com.example.fingerdraw/.MainActivity time=128ms latency=389ms  procState=-1  historyMsgCount=1
01-18 20:39:05.939 18592 18592 W Looper  : PerfMonitor looperActivity : package=com.example.fingerdraw/.MainActivity time=1ms latency=516ms  procState=-1  historyMsgCount=2
01-18 20:39:05.942 18592 18592 D FramePredict: FramePredict init: false
01-18 20:39:06.189 18592 18592 W mple.fingerdraw: Method boolean androidx.compose.runtime.snapshots.SnapshotStateList.conditionalUpdate(kotlin.jvm.functions.Function1) failed lock verification and will run slower.
01-18 20:39:06.189 18592 18592 W mple.fingerdraw: Common causes for lock verification issues are non-optimized dex code
01-18 20:39:06.189 18592 18592 W mple.fingerdraw: and incorrect proguard optimizations.
01-18 20:39:06.189 18592 18592 W mple.fingerdraw: Method java.lang.Object androidx.compose.runtime.snapshots.SnapshotStateList.mutate(kotlin.jvm.functions.Function1) failed lock verification and will run slower.
01-18 20:39:06.189 18592 18592 W mple.fingerdraw: Method void androidx.compose.runtime.snapshots.SnapshotStateList.update(kotlin.jvm.functions.Function1) failed lock verification and will run slower.
01-18 20:39:06.382 18592 18684 I AdrenoGLES-0: QUALCOMM build                   : 3e33337ce3, I07ee46fc66
01-18 20:39:06.382 18592 18684 I AdrenoGLES-0: Build Date                       : 10/08/21
01-18 20:39:06.382 18592 18684 I AdrenoGLES-0: OpenGL ES Shader Compiler Version: EV031.35.01.10
01-18 20:39:06.382 18592 18684 I AdrenoGLES-0: Local Branch                     : 
01-18 20:39:06.382 18592 18684 I AdrenoGLES-0: Remote Branch                    : 
01-18 20:39:06.382 18592 18684 I AdrenoGLES-0: Remote Branch                    : 
01-18 20:39:06.382 18592 18684 I AdrenoGLES-0: Reconstruct Branch               : 
01-18 20:39:06.382 18592 18684 I AdrenoGLES-0: Build Config                     : S P 10.0.7 AArch64
01-18 20:39:06.382 18592 18684 I AdrenoGLES-0: Driver Path                      : /vendor/lib64/egl/libGLESv2_adreno.so
01-18 20:39:06.389 18592 18684 I AdrenoGLES-0: PFP: 0x016ee201, ME: 0x00000000
01-18 20:39:06.395 18592 18592 D VRI[MainActivity]: vri.reportNextDraw android.view.ViewRootImpl.performTraversals:4013 android.view.ViewRootImpl.doTraversal:2725 android.view.ViewRootImpl$TraversalRunnable.run:9812 android.view.Choreographer$CallbackRecord.run:1505 android.view.Choreographer$CallbackRecord.run:1513 
01-18 20:39:06.395 18592 18592 D VRI[MainActivity]: vri.Setup new sync id=0 syncSeqId=0
01-18 20:39:06.402 18592 18684 W libc    : Access denied finding property "vendor.migl.debug"
01-18 20:39:06.405 18592 18684 E libEGL  : pre_cache appList: com.sina.weibo,com.ss.android.article.news,com.taobao.taobao,com.smile.gifmaker,com.ss.android.ugc.aweme,com.tencent.mm,tv.danmaku.bili,,
01-18 20:39:06.424 18592 18684 D mple.fingerdraw: MiuiProcessManagerServiceStub setSchedFifo
01-18 20:39:06.425 18592 18684 I MiuiProcessManagerImpl: setSchedFifo pid:18592, mode:3
01-18 20:39:06.427 18592 18684 E libboost: fail to open node: No such file or directory
01-18 20:39:06.439 18592 18684 E perf_hint: Session creation failed, mPreferredRateNanos: -1
01-18 20:39:06.439 18592 18592 W Looper  : PerfMonitor doFrame : time=498ms vsyncFrame=0 latency=133ms procState=-1 historyMsgCount=4
01-18 20:39:06.441 18592 18592 D VRI[MainActivity]: vri.reportDrawFinished syncSeqId=0 android.view.ViewRootImpl.lambda$createSyncIfNeeded$4$android-view-ViewRootImpl:4081 android.view.ViewRootImpl$$ExternalSyntheticLambda2.run:6 android.os.Handler.handleCallback:942 android.os.Handler.dispatchMessage:99 android.os.Looper.loopOnce:211 
01-18 20:39:06.478 18592 18592 I Choreographer: Skipped 58 frames!  The application may be doing too much work on its main thread.
01-18 20:39:06.533 18592 18592 W Looper  : PerfMonitor doFrame : time=55ms vsyncFrame=0 latency=485ms procState=-1 historyMsgCount=6
01-18 20:39:06.538 18592 18592 D DecorView[]: onWindowFocusChanged hasWindowFocus true
01-18 20:39:06.538 18592 18592 I HandWritingStubImpl: refreshLastKeyboardType: 1
01-18 20:39:06.539 18592 18592 I HandWritingStubImpl: getCurrentKeyboardType: 1
01-18 20:39:06.554 18592 18592 I HandWritingStubImpl: getCurrentKeyboardType: 1
01-18 20:39:06.897 18592 18609 I mple.fingerdraw: Compiler allocated 4857KB to compile void android.view.ViewRootImpl.performTraversals()
01-18 20:39:11.425 18592 18735 D ProfileInstaller: Installing profile for com.example.fingerdraw
01-18 20:39:28.715 18592 18592 W MirrorManager: this model don't Support
01-18 20:39:28.821 18592 18754 I mple.fingerdraw: hiddenapi: Accessing hidden method Ldalvik/system/CloseGuard;->get()Ldalvik/system/CloseGuard; (runtime_flags=CorePlatformApi, domain=core-platform, api=unsupported,core-platform-api) from Lokhttp3/internal/platform/AndroidPlatform$CloseGuard; (domain=app, TargetSdkVersion=34) using reflection: allowed
01-18 20:39:28.821 18592 18754 I mple.fingerdraw: hiddenapi: Accessing hidden method Ldalvik/system/CloseGuard;->open(Ljava/lang/String;)V (runtime_flags=CorePlatformApi, domain=core-platform, api=unsupported,core-platform-api) from Lokhttp3/internal/platform/AndroidPlatform$CloseGuard; (domain=app, TargetSdkVersion=34) using reflection: allowed
01-18 20:39:28.821 18592 18754 I mple.fingerdraw: hiddenapi: Accessing hidden method Ldalvik/system/CloseGuard;->warnIfOpen()V (runtime_flags=CorePlatformApi, domain=core-platform, api=unsupported,core-platform-api) from Lokhttp3/internal/platform/AndroidPlatform$CloseGuard; (domain=app, TargetSdkVersion=34) using reflection: allowed
01-18 20:39:28.868 18592 18592 D CompatibilityChangeReporter: Compat change id reported: 210923482; UID 10351; state: ENABLED
01-18 20:39:28.900 18592 18592 D CompatibilityChangeReporter: Compat change id reported: 171228096; UID 10351; state: ENABLED
01-18 20:39:28.904 18592 18592 D ScrollerOptimizationManager: registerConfigChangedListener
01-18 20:39:28.952 18592 18592 D ScrollerOptimizationManager: registerConfigChangedListener
01-18 20:39:29.001 18592 18592 I ExoPlayerImpl: Init f70a84 [AndroidXMedia3/1.2.0] [peux, 2201116SI, Xiaomi, 33]
01-18 20:39:29.025 18592 18592 W AidlConversion: aidl2legacy_AudioChannelLayout_audio_channel_mask_t: no legacy output audio_channel_mask_t found for AudioChannelLayout{layoutMask: 16}
01-18 20:39:29.034 18592 18592 I mple.fingerdraw: hiddenapi: Accessing hidden method Landroid/media/AudioTrack;->getLatency()I (runtime_flags=0, domain=platform, api=unsupported) from Landroidx/media3/exoplayer/audio/AudioTrackPositionTracker; (domain=app, TargetSdkVersion=34) using reflection: allowed
01-18 20:39:29.097 18592 18592 D MainActivity: Player state changed: 2
01-18 20:39:29.117 18592 18592 D SurfaceView: UPDATE null, mIsCastMode = false
01-18 20:39:29.133 18592 18592 W Looper  : PerfMonitor doFrame : time=337ms vsyncFrame=0 latency=15ms procState=-1 historyMsgCount=1
01-18 20:39:29.137 18592 18592 I Choreographer: Skipped 39 frames!  The application may be doing too much work on its main thread.
01-18 20:39:29.138 18592 18592 W Looper  : PerfMonitor doFrame : time=0ms vsyncFrame=0 latency=332ms procState=-1 historyMsgCount=7
01-18 20:39:29.150 18592 18592 D SurfaceView: UPDATE Surface(name=SurfaceView[com.example.fingerdraw/com.example.fingerdraw.MainActivity])/@0x8d3e27c, mIsProjectionMode = false
01-18 20:39:29.198 18592 18773 D MainActivity: Connected to socket.io server
01-18 20:40:04.199 18592 18767 E ExoPlayerImplInternal: Playback error
01-18 20:40:04.199 18592 18767 E ExoPlayerImplInternal:   androidx.media3.exoplayer.ExoPlaybackException: Source error
01-18 20:40:04.199 18592 18767 E ExoPlayerImplInternal:       at androidx.media3.exoplayer.ExoPlayerImplInternal.handleIoException(ExoPlayerImplInternal.java:701)
01-18 20:40:04.199 18592 18767 E ExoPlayerImplInternal:       at androidx.media3.exoplayer.ExoPlayerImplInternal.handleMessage(ExoPlayerImplInternal.java:673)
01-18 20:40:04.199 18592 18767 E ExoPlayerImplInternal:       at android.os.Handler.dispatchMessage(Handler.java:102)
01-18 20:40:04.199 18592 18767 E ExoPlayerImplInternal:       at android.os.Looper.loopOnce(Looper.java:211)
01-18 20:40:04.199 18592 18767 E ExoPlayerImplInternal:       at android.os.Looper.loop(Looper.java:300)
01-18 20:40:04.199 18592 18767 E ExoPlayerImplInternal:       at android.os.HandlerThread.run(HandlerThread.java:67)
01-18 20:40:04.199 18592 18767 E ExoPlayerImplInternal:   Caused by: androidx.media3.datasource.UdpDataSource$UdpDataSourceException: java.net.SocketTimeoutException: Poll timed out
01-18 20:40:04.199 18592 18767 E ExoPlayerImplInternal:       at androidx.media3.datasource.UdpDataSource.read(UdpDataSource.java:140)
01-18 20:40:04.199 18592 18767 E ExoPlayerImplInternal:       at androidx.media3.datasource.StatsDataSource.read(StatsDataSource.java:94)
01-18 20:40:04.199 18592 18767 E ExoPlayerImplInternal:       at androidx.media3.extractor.DefaultExtractorInput.readFromUpstream(DefaultExtractorInput.java:293)
01-18 20:40:04.199 18592 18767 E ExoPlayerImplInternal:       at androidx.media3.extractor.DefaultExtractorInput.advancePeekPosition(DefaultExtractorInput.java:166)
01-18 20:40:04.199 18592 18767 E ExoPlayerImplInternal:       at androidx.media3.extractor.DefaultExtractorInput.peekFully(DefaultExtractorInput.java:148)
01-18 20:40:04.199 18592 18767 E ExoPlayerImplInternal:       at androidx.media3.extractor.DefaultExtractorInput.peekFully(DefaultExtractorInput.java:157)
01-18 20:40:04.199 18592 18767 E ExoPlayerImplInternal:       at androidx.media3.extractor.flv.FlvExtractor.sniff(FlvExtractor.java:107)
01-18 20:40:04.199 18592 18767 E ExoPlayerImplInternal:       at androidx.media3.exoplayer.source.BundledExtractorsAdapter.init(BundledExtractorsAdapter.java:78)
01-18 20:40:04.199 18592 18767 E ExoPlayerImplInternal:       at androidx.media3.exoplayer.source.ProgressiveMediaPeriod$ExtractingLoadable.load(ProgressiveMediaPeriod.java:1041)
01-18 20:40:04.199 18592 18767 E ExoPlayerImplInternal:       at androidx.media3.exoplayer.upstream.Loader$LoadTask.run(Loader.java:417)
01-18 20:40:04.199 18592 18767 E ExoPlayerImplInternal:       at java.util.concurrent.ThreadPoolExecutor.runWorker(ThreadPoolExecutor.java:1154)
01-18 20:40:04.199 18592 18767 E ExoPlayerImplInternal:       at java.util.concurrent.ThreadPoolExecutor$Worker.run(ThreadPoolExecutor.java:652)
01-18 20:40:04.199 18592 18767 E ExoPlayerImplInternal:       at java.lang.Thread.run(Thread.java:1563)
01-18 20:40:04.199 18592 18767 E ExoPlayerImplInternal:   Caused by: java.net.SocketTimeoutException: Poll timed out
01-18 20:40:04.199 18592 18767 E ExoPlayerImplInternal:       at libcore.io.IoBridge.poll(IoBridge.java:866)
01-18 20:40:04.199 18592 18767 E ExoPlayerImplInternal:       at java.net.PlainDatagramSocketImpl.doRecv(PlainDatagramSocketImpl.java:151)
01-18 20:40:04.199 18592 18767 E ExoPlayerImplInternal:       at java.net.PlainDatagramSocketImpl.receive0(PlainDatagramSocketImpl.java:142)
01-18 20:40:04.199 18592 18767 E ExoPlayerImplInternal:       at java.net.AbstractPlainDatagramSocketImpl.receive(AbstractPlainDatagramSocketImpl.java:164)
01-18 20:40:04.199 18592 18767 E ExoPlayerImplInternal:       at java.net.DatagramSocket.receive(DatagramSocket.java:849)
01-18 20:40:04.199 18592 18767 E ExoPlayerImplInternal:       at androidx.media3.datasource.UdpDataSource.read(UdpDataSource.java:138)
01-18 20:40:04.199 18592 18767 E ExoPlayerImplInternal:       ... 12 more
01-18 20:40:04.204 18592 18592 E MainActivity: Player error
01-18 20:40:04.204 18592 18592 E MainActivity: androidx.media3.exoplayer.ExoPlaybackException: Source error
01-18 20:40:04.204 18592 18592 E MainActivity: 	at androidx.media3.exoplayer.ExoPlayerImplInternal.handleIoException(ExoPlayerImplInternal.java:701)
01-18 20:40:04.204 18592 18592 E MainActivity: 	at androidx.media3.exoplayer.ExoPlayerImplInternal.handleMessage(ExoPlayerImplInternal.java:673)
01-18 20:40:04.204 18592 18592 E MainActivity: 	at android.os.Handler.dispatchMessage(Handler.java:102)
01-18 20:40:04.204 18592 18592 E MainActivity: 	at android.os.Looper.loopOnce(Looper.java:211)
01-18 20:40:04.204 18592 18592 E MainActivity: 	at android.os.Looper.loop(Looper.java:300)
01-18 20:40:04.204 18592 18592 E MainActivity: 	at android.os.HandlerThread.run(HandlerThread.java:67)
01-18 20:40:04.204 18592 18592 E MainActivity: Caused by: androidx.media3.datasource.UdpDataSource$UdpDataSourceException: java.net.SocketTimeoutException: Poll timed out
01-18 20:40:04.204 18592 18592 E MainActivity: 	at androidx.media3.datasource.UdpDataSource.read(UdpDataSource.java:140)
01-18 20:40:04.204 18592 18592 E MainActivity: 	at androidx.media3.datasource.StatsDataSource.read(StatsDataSource.java:94)
01-18 20:40:04.204 18592 18592 E MainActivity: 	at androidx.media3.extractor.DefaultExtractorInput.readFromUpstream(DefaultExtractorInput.java:293)
01-18 20:40:04.204 18592 18592 E MainActivity: 	at androidx.media3.extractor.DefaultExtractorInput.advancePeekPosition(DefaultExtractorInput.java:166)
01-18 20:40:04.204 18592 18592 E MainActivity: 	at androidx.media3.extractor.DefaultExtractorInput.peekFully(DefaultExtractorInput.java:148)
01-18 20:40:04.204 18592 18592 E MainActivity: 	at androidx.media3.extractor.DefaultExtractorInput.peekFully(DefaultExtractorInput.java:157)
01-18 20:40:04.204 18592 18592 E MainActivity: 	at androidx.media3.extractor.flv.FlvExtractor.sniff(FlvExtractor.java:107)
01-18 20:40:04.204 18592 18592 E MainActivity: 	at androidx.media3.exoplayer.source.BundledExtractorsAdapter.init(BundledExtractorsAdapter.java:78)
01-18 20:40:04.204 18592 18592 E MainActivity: 	at androidx.media3.exoplayer.source.ProgressiveMediaPeriod$ExtractingLoadable.load(ProgressiveMediaPeriod.java:1041)
01-18 20:40:04.204 18592 18592 E MainActivity: 	at androidx.media3.exoplayer.upstream.Loader$LoadTask.run(Loader.java:417)
01-18 20:40:04.204 18592 18592 E MainActivity: 	at java.util.concurrent.ThreadPoolExecutor.runWorker(ThreadPoolExecutor.java:1154)
01-18 20:40:04.204 18592 18592 E MainActivity: 	at java.util.concurrent.ThreadPoolExecutor$Worker.run(ThreadPoolExecutor.java:652)
01-18 20:40:04.204 18592 18592 E MainActivity: 	at java.lang.Thread.run(Thread.java:1563)
01-18 20:40:04.204 18592 18592 E MainActivity: Caused by: java.net.SocketTimeoutException: Poll timed out
01-18 20:40:04.204 18592 18592 E MainActivity: 	at libcore.io.IoBridge.poll(IoBridge.java:866)
01-18 20:40:04.204 18592 18592 E MainActivity: 	at java.net.PlainDatagramSocketImpl.doRecv(PlainDatagramSocketImpl.java:151)
01-18 20:40:04.204 18592 18592 E MainActivity: 	at java.net.PlainDatagramSocketImpl.receive0(PlainDatagramSocketImpl.java:142)
01-18 20:40:04.204 18592 18592 E MainActivity: 	at java.net.AbstractPlainDatagramSocketImpl.receive(AbstractPlainDatagramSocketImpl.java:164)
01-18 20:40:04.204 18592 18592 E MainActivity: 	at java.net.DatagramSocket.receive(DatagramSocket.java:849)
01-18 20:40:04.204 18592 18592 E MainActivity: 	at androidx.media3.datasource.UdpDataSource.read(UdpDataSource.java:138)
01-18 20:40:04.204 18592 18592 E MainActivity: 	... 12 more
01-18 20:40:04.205 18592 18592 D MainActivity: Player state changed: 1
01-18 20:40:21.306 18592 18592 D DecorView[]: onWindowFocusChanged hasWindowFocus false
01-18 20:40:21.998 18592 18592 W MiuiMagicPointerUtilsStubHeadImpl: MiuiMagicPointerUtilsStubHeadImpl has been initialized !!

