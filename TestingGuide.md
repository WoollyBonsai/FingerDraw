# Testing and Development Guide for FingerDraw

This guide provides recommendations for setting up an efficient development and testing environment for the FingerDraw application.

## Recommended: Android Emulator with Android Studio

The official Android Emulator, part of Android Studio, is the most powerful and feature-rich solution for testing Android applications. On a powerful PC, it will offer excellent performance and a seamless debugging experience.

### Why use the Android Emulator?

*   **Deep Integration:** It's fully integrated with Android Studio, allowing you to run and debug your app with a single click.
*   **Google Play Services:** It can run full versions of Android with Google Play Services, which is important for testing many apps.
*   **Rich Feature Set:** You can simulate various network conditions, GPS locations, gestures, and sensor data.
*   **Easy Networking:** It has a special networking setup that makes it easy to connect to servers running on your local machine.

### Setting up the Android Emulator

1.  **Install Android Studio:**
    *   Download and install Android Studio from the [official website](https://developer.android.com/studio). The installation process is straightforward.

2.  **Open the Project in Android Studio:**
    *   Once Android Studio is installed, open it.
    *   Select "Open an Existing Project" and navigate to the `android-client` directory in your FingerDraw project.
    *   Android Studio will take some time to sync the project and download the necessary Gradle dependencies.

3.  **Create a Virtual Device (Emulator):**
    *   In Android Studio, go to **Tools > Device Manager**.
    *   Click on **Create Device**.
    *   Choose a device definition (e.g., "Pixel 6") and click **Next**.
    *   Select a system image. A recent API level (e.g., 33 or 34) is recommended. Click the "Download" link next to the image if you don't have it already.
    *   Click **Next** and then **Finish** to create the virtual device.

4.  **Run the App in the Emulator:**
    *   Once the virtual device is created, you will see it in the toolbar at the top of the Android Studio window.
    *   Make sure your new virtual device is selected.
    *   Click the green "Run" button (a triangle icon) or press `Shift + F10`.
    *   Android Studio will build the app, install it on the emulator, and run it.

### Connecting to Your Local Server

When your server is running on the same machine as the Android Emulator, you can't use `localhost` or `127.0.0.1` directly from the Android app, because that would refer to the emulator's own loopback address.

Instead, the Android Emulator provides a special IP address to connect to the host machine's `localhost`:

**Use the IP address `10.0.2.2` in the FingerDraw app to connect to your local server.**

For example, if your server is running on `localhost:8000`, you would enter `10.0.2.2` in the IP address field of the FingerDraw app running in the emulator.

## Using Waydroid for Testing

You mentioned you have Waydroid installed. Waydroid can be a very fast and efficient way to test, especially for quick checks.

### Connecting to Your Local Server from Waydroid

With Waydroid, networking is usually bridged with your host machine. This means you should be able to connect to your local server using your computer's actual local network IP address.

1.  **Find your computer's IP address:**
    *   Open a terminal and run `ip a` or `ifconfig`.
    *   Look for your network interface (e.g., `eth0` or `wlan0`) and find the `inet` address. It will likely be something like `192.168.1.100`.

2.  **Run your Linux server:**
    *   Start the FingerDraw Linux server. It will print the IP address it's running on. This should be the same IP you found above.

3.  **Connect from Waydroid:**
    *   Open the FingerDraw app in Waydroid.
    *   Enter your computer's local IP address (e.g., `192.168.1.100`) into the IP address field.

### Potential Waydroid Issues

*   **Networking:** While usually seamless, Waydroid's networking can sometimes be tricky. If you have connection issues, you might need to check Waydroid's documentation or community forums for troubleshooting networking problems.
*   **Google Play Services:** Waydroid does not come with Google Play Services by default, which can cause some apps to crash or not work correctly. For the FingerDraw app, this is not an issue.

## Summary

*   For the best development and debugging experience, use the **Android Emulator with Android Studio**.
*   To connect from the emulator to your local server, use the IP address **`10.0.2.2`**.
*   For quick tests, **Waydroid** is a great option.
*   To connect from Waydroid to your local server, use your **computer's local network IP address**.
