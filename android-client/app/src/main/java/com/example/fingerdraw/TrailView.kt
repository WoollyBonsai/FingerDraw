package com.example.fingerdraw

import android.content.Context
import android.graphics.Canvas
import android.graphics.Color
import android.graphics.Paint
import android.graphics.Path
import android.util.AttributeSet
import android.view.View

class TrailView @JvmOverloads constructor(
    context: Context, attrs: AttributeSet? = null, defStyleAttr: Int = 0
) : View(context, attrs, defStyleAttr) {

    private data class TrailPoint(val x: Float, val y: Float, val timestamp: Long)
    
    private val points = mutableListOf<TrailPoint>()
    private val paint = Paint().apply {
        color = Color.parseColor("#6600FF00") // Faint green sparkle trail
        style = Paint.Style.STROKE
        strokeWidth = 10f
        strokeJoin = Paint.Join.ROUND
        strokeCap = Paint.Cap.ROUND
        isAntiAlias = true
    }

    fun addPoint(x: Float, y: Float) {
        points.add(TrailPoint(x, y, System.currentTimeMillis()))
        invalidate()
    }
    
    fun actionUp() {
        // Points fade out naturally based on timestamp
        invalidate()
    }

    override fun onDraw(canvas: Canvas) {
        super.onDraw(canvas)
        if (points.isEmpty()) return
        
        val now = System.currentTimeMillis()
        // Keep points up to 400ms to allow a small fading trail
        val threshold = 400L
        points.removeAll { now - it.timestamp > threshold }
        
        if (points.size >= 2) {
            val path = Path()
            path.moveTo(points[0].x, points[0].y)
            for (i in 1 until points.size) {
                path.lineTo(points[i].x, points[i].y)
            }
            
            // Adjust opacity based on the age of the oldest point to fade out
            val oldestAge = now - points[0].timestamp
            val alpha = Math.max(0, 255 - (oldestAge * 255 / threshold).toInt())
            paint.alpha = (alpha * 0.4).toInt() // Max opacity 40%
            
            canvas.drawPath(path, paint)
        }
        
        if (points.isNotEmpty()) {
            postInvalidateDelayed(16) // ~60fps fade out
        }
    }
}
