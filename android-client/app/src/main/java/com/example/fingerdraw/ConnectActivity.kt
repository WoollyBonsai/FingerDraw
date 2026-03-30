package com.example.fingerdraw

import android.content.Intent
import android.os.Bundle
import androidx.appcompat.app.AppCompatActivity
import com.example.fingerdraw.databinding.ActivityConnectBinding

class ConnectActivity : AppCompatActivity() {

    private lateinit var binding: ActivityConnectBinding

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityConnectBinding.inflate(layoutInflater)
        setContentView(binding.root)

        val prefs = getSharedPreferences("FingerDrawPrefs", MODE_PRIVATE)
        val lastIp = prefs.getString("server_ip", "")
        binding.etServerIp.setText(lastIp)

        binding.btnConnect.setOnClickListener {
            val ip = binding.etServerIp.text.toString().trim()
            if (ip.isNotEmpty()) {
                prefs.edit().putString("server_ip", ip).apply()
                
                val intent = Intent(this, MainActivity::class.java)
                intent.putExtra("SERVER_IP", ip)
                startActivity(intent)
                finish()
            }
        }
    }
}
