@echo off
set GST_PATH=C:\Program Files\gstreamer\1.0\msvc_x86_64

cl /EHsc /MD /std:c++17 Application\main.cpp ^
    /I "%GST_PATH%\include\gstreamer-1.0" ^
    /I "%GST_PATH%\include\glib-2.0" ^
    /I "%GST_PATH%\lib\glib-2.0\include" ^
    /link /LIBPATH:"%GST_PATH%\lib" ^
    gstreamer-1.0.lib ^
    glib-2.0.lib ^
    gobject-2.0.lib ^
    user32.lib ^
    shell32.lib ^
    ws2_32.lib ^
    /OUT:Application\main.exe