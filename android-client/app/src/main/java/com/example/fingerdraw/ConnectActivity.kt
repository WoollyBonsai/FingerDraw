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

                val options = arrayOf("Screencast", "Web Notebook")
                android.app.AlertDialog.Builder(this)
                    .setTitle("Choose Connection Type")
                    .setItems(options) { _, which ->
                        if (which == 0) {
                            val intent = Intent(this, MainActivity::class.java)
                            intent.putExtra("SERVER_IP", ip)
                            startActivity(intent)
                        } else {
                            val intent = Intent(this, NotebookActivity::class.java)
                            intent.putExtra("URL", "http://$ip:8000/static/index.html")
                            startActivity(intent)
                        }
                    }
                    .show()
            }
        }

        binding.btnLocalNotebook.setOnClickListener {
            val intent = Intent(this, NotebookActivity::class.java)
            intent.putExtra("URL", "file:///android_asset/web/index.html")
            startActivity(intent)
        }

        binding.btnSettings.setOnClickListener {
            startActivity(Intent(this, SettingsActivity::class.java))
        }
    }
}
