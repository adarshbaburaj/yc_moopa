package com.moopa.halo;

import android.animation.ValueAnimator;
import android.app.Notification;
import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.app.Service;
import android.content.Context;
import android.content.Intent;
import android.content.pm.ServiceInfo;
import android.graphics.Canvas;
import android.graphics.Matrix;
import android.graphics.Paint;
import android.graphics.PixelFormat;
import android.graphics.RectF;
import android.graphics.SweepGradient;
import android.os.Build;
import android.os.IBinder;
import android.view.RoundedCorner;
import android.view.View;
import android.view.WindowInsets;
import android.view.WindowManager;
import android.view.animation.LinearInterpolator;

/** Draws an animated glowing border over every app while Moopa works. Touches pass through. */
public class HaloService extends Service {
    private static final String CHANNEL = "halo";
    private WindowManager wm;
    private HaloView view;

    @Override
    public IBinder onBind(Intent intent) {
        return null;
    }

    @Override
    public int onStartCommand(Intent intent, int flags, int startId) {
        startAsForeground();  // required promptly after start-foreground-service, even for "hide"
        String action = intent == null ? "show" : intent.getAction();
        if ("hide".equals(action)) {
            removeHalo();
            stopForeground(STOP_FOREGROUND_REMOVE);
            stopSelf();
        } else {
            showHalo();
        }
        return START_NOT_STICKY;
    }

    @Override
    public void onDestroy() {
        removeHalo();
        super.onDestroy();
    }

    private void startAsForeground() {
        NotificationManager nm = getSystemService(NotificationManager.class);
        if (nm.getNotificationChannel(CHANNEL) == null) {
            NotificationChannel ch = new NotificationChannel(CHANNEL, "Moopa is working",
                    NotificationManager.IMPORTANCE_MIN);
            ch.setShowBadge(false);
            nm.createNotificationChannel(ch);
        }
        Notification n = new Notification.Builder(this, CHANNEL)
                .setContentTitle("Moopa is working on your phone")
                .setSmallIcon(android.R.drawable.star_on)
                .setOngoing(true)
                .build();
        if (Build.VERSION.SDK_INT >= 34) {
            startForeground(1, n, ServiceInfo.FOREGROUND_SERVICE_TYPE_SPECIAL_USE);
        } else {
            startForeground(1, n);
        }
    }

    private void showHalo() {
        if (view != null) return;
        wm = (WindowManager) getSystemService(WINDOW_SERVICE);
        view = new HaloView(this);
        WindowManager.LayoutParams lp = new WindowManager.LayoutParams(
                WindowManager.LayoutParams.MATCH_PARENT,
                WindowManager.LayoutParams.MATCH_PARENT,
                WindowManager.LayoutParams.TYPE_APPLICATION_OVERLAY,
                WindowManager.LayoutParams.FLAG_NOT_FOCUSABLE
                        | WindowManager.LayoutParams.FLAG_NOT_TOUCHABLE
                        | WindowManager.LayoutParams.FLAG_LAYOUT_IN_SCREEN
                        | WindowManager.LayoutParams.FLAG_LAYOUT_NO_LIMITS
                        | WindowManager.LayoutParams.FLAG_HARDWARE_ACCELERATED,
                PixelFormat.TRANSLUCENT);
        // Android 12+: touches only pass through an untrusted overlay at <= 0.8 opacity.
        lp.alpha = 0.8f;
        if (Build.VERSION.SDK_INT >= 30) {
            lp.setFitInsetsTypes(0);
            lp.layoutInDisplayCutoutMode = WindowManager.LayoutParams.LAYOUT_IN_DISPLAY_CUTOUT_MODE_ALWAYS;
        }
        lp.setTitle("MoopaHalo");
        wm.addView(view, lp);
    }

    private void removeHalo() {
        if (view != null && wm != null) {
            view.stop();
            wm.removeView(view);
        }
        view = null;
    }

    /** A rotating violet/blue/pink gradient border, drawn as layered strokes for a soft glow. */
    static class HaloView extends View {
        private static final int[] COLORS = {0xFF7C3AED, 0xFF3B82F6, 0xFFEC4899, 0xFFA855F7, 0xFF7C3AED};
        private static final float[] WIDTHS_DP = {44f, 28f, 16f, 7f};
        private static final int[] ALPHAS = {28, 60, 120, 255};
        private final Paint paint = new Paint(Paint.ANTI_ALIAS_FLAG);
        private final Matrix matrix = new Matrix();
        private final RectF rect = new RectF();
        private final float density;
        private SweepGradient shader;
        private float angle;
        private float breath = 1f;
        private ValueAnimator anim;

        HaloView(Context c) {
            super(c);
            density = c.getResources().getDisplayMetrics().density;
            paint.setStyle(Paint.Style.STROKE);
            setImportantForAccessibility(IMPORTANT_FOR_ACCESSIBILITY_NO);
            anim = ValueAnimator.ofFloat(0f, 360f);
            anim.setDuration(2800);
            anim.setRepeatCount(ValueAnimator.INFINITE);
            anim.setInterpolator(new LinearInterpolator());
            anim.addUpdateListener(new ValueAnimator.AnimatorUpdateListener() {
                @Override
                public void onAnimationUpdate(ValueAnimator a) {
                    angle = (float) a.getAnimatedValue();
                    breath = 0.8f + 0.2f * (float) Math.sin(Math.toRadians(angle * 2));
                    invalidate();
                }
            });
            anim.start();
        }

        void stop() {
            if (anim != null) anim.cancel();
        }

        private float cornerRadius() {
            if (Build.VERSION.SDK_INT >= 31) {
                WindowInsets in = getRootWindowInsets();
                if (in != null) {
                    RoundedCorner rc = in.getRoundedCorner(RoundedCorner.POSITION_TOP_LEFT);
                    if (rc != null && rc.getRadius() > 0) return rc.getRadius();
                }
            }
            return 40f * density;
        }

        @Override
        protected void onDraw(Canvas canvas) {
            int w = getWidth(), h = getHeight();
            if (w == 0 || h == 0) return;
            if (shader == null) shader = new SweepGradient(w / 2f, h / 2f, COLORS, null);
            matrix.setRotate(angle, w / 2f, h / 2f);
            shader.setLocalMatrix(matrix);
            paint.setShader(shader);
            float r = cornerRadius();
            for (int i = 0; i < WIDTHS_DP.length; i++) {
                float sw = WIDTHS_DP[i] * density;
                paint.setStrokeWidth(sw);
                paint.setAlpha((int) (ALPHAS[i] * breath));
                // centre the stroke on the screen edge so only the inner half shows: a glow inward
                rect.set(0, 0, w, h);
                canvas.drawRoundRect(rect, r, r, paint);
            }
        }
    }
}
