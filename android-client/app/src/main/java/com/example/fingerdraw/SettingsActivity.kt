package com.example.fingerdraw

import android.os.Bundle
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import com.example.fingerdraw.databinding.ActivitySettingsBinding

class SettingsActivity : AppCompatActivity() {

    private lateinit var binding: ActivitySettingsBinding
    private var isGStreamerInitialized = false

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivitySettingsBinding.inflate(layoutInflater)
        setContentView(binding.root)

        try {
            org.freedesktop.gstreamer.GStreamer.init(this)
            isGStreamerInitialized = true
        } catch (e: Exception) {
            e.printStackTrace()
        }

        val prefs = getSharedPreferences("FingerDrawPrefs", MODE_PRIVATE)
        binding.etApiPort.setText(prefs.getInt("api_port", 8000).toString())
        binding.etVideoPort.setText(prefs.getInt("video_port", 5000).toString())
        binding.etInputPort.setText(prefs.getInt("input_port", 9999).toString())
        binding.etDecoder.setText(prefs.getString("decoder", "openh264dec"))

        binding.btnVerifyCodec.setOnClickListener {
            val decoderName = binding.etDecoder.text.toString().trim()
            if (decoderName.isEmpty()) {
                binding.tvCodecStatus.text = "Decoder name cannot be empty."
                return@setOnClickListener
            }

            if (isGStreamerInitialized) {
                val exists = nativeVerifyCodec(decoderName)
                if (exists) {
                    binding.tvCodecStatus.text = "Success: Codec '$decoderName' is present and working!"
                    binding.tvCodecStatus.setTextColor(android.graphics.Color.GREEN)
                } else {
                    binding.tvCodecStatus.text = "Error: Codec '$decoderName' not found or failed to initialize. Try 'openh264dec' or 'decodebin' instead."
                    binding.tvCodecStatus.setTextColor(android.graphics.Color.RED)
                }
            } else {
                binding.tvCodecStatus.text = "GStreamer is not initialized."
                binding.tvCodecStatus.setTextColor(android.graphics.Color.RED)
            }
        }

        binding.btnSaveSettings.setOnClickListener {
            try {
                val apiPort = binding.etApiPort.text.toString().toInt()
                val videoPort = binding.etVideoPort.text.toString().toInt()
                val inputPort = binding.etInputPort.text.toString().toInt()
                val decoder = binding.etDecoder.text.toString().trim()

                prefs.edit()
                    .putInt("api_port", apiPort)
                    .putInt("video_port", videoPort)
                    .putInt("input_port", inputPort)
                    .putString("decoder", if (decoder.isEmpty()) "openh264dec" else decoder)
                    .apply()

                Toast.makeText(this, "Settings Saved", Toast.LENGTH_SHORT).show()
                finish()
            } catch (e: Exception) {
                Toast.makeText(this, "Invalid port values", Toast.LENGTH_SHORT).show()
            }
        }
    }

    private external fun nativeVerifyCodec(decoderName: String): Boolean

    companion object {
        init {
            System.loadLibrary("fingerdraw-native")
        }
    }
}
