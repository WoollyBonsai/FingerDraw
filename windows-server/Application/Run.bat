@echo off
set "ROOT=%~dp0"
:: Add our local bin to the system PATH for this session only
set "PATH=%ROOT%bin;%PATH%"
:: Tell GStreamer exactly where the plugins are
set "GST_PLUGIN_PATH=%ROOT%lib\gstreamer-1.0"

:: Start the app
start "" "%ROOT%main.exe"