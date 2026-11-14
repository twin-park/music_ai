package com.carbgm.app;

import android.app.Notification;
import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.app.PendingIntent;
import android.app.Service;
import android.content.Intent;
import android.content.pm.ServiceInfo;
import android.content.res.AssetManager;
import android.os.Build;
import android.os.IBinder;

import java.io.BufferedReader;
import java.io.File;
import java.io.FileOutputStream;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.io.OutputStream;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.List;

/**
 * 연주를 쥐는 포그라운드 서비스 — 화면을 꺼도 · 다른 앱으로 가도 음악이 이어짐.
 *  1) APK 의 assets/data (AI 가중치 · 사운드폰트 · 피아노 · 주변 소리 · 지휘자 JSON, 약 140MB) 를 앱 폴더로 한 번 풂 (판이 바뀌면 다시)
 *  2) C++ 엔진 켜기 → MainActivity 가 Native.port() 를 보고 화면을 엶
 *  알림의 [끄기] = 서비스와 프로세스를 통째로 끔 (엔진은 프로세스와 수명이 같음)
 */
public class EngineService extends Service {
    static final String ACTION_STOP = "com.carbgm.app.STOP";
    private static final String CHANNEL = "play";
    private static final int NOTE_ID = 1;

    /** 화면에 보일 준비 상황 한 줄 */
    static volatile String status = "준비 중";
    /** 엔진 켜기 전 단계(자료 풀기 등)에서 실패하면 그 이유 */
    static volatile String failure = null;
    private static volatile boolean started = false;

    @Override
    public IBinder onBind(Intent intent) { return null; }

    @Override
    public int onStartCommand(Intent intent, int flags, int startId) {
        if (intent != null && ACTION_STOP.equals(intent.getAction())) {
            stopForeground(true);
            stopSelf();
            android.os.Process.killProcess(android.os.Process.myPid());
            return START_NOT_STICKY;
        }
        goForeground();
        if (!started) {
            started = true;
            new Thread(this::prepareAndStart, "car_bgm-start").start();
        }
        return START_NOT_STICKY;
    }

    private void goForeground() {
        NotificationManager nm = getSystemService(NotificationManager.class);
        Notification.Builder b;
        if (Build.VERSION.SDK_INT >= 26) {
            if (nm.getNotificationChannel(CHANNEL) == null) {
                NotificationChannel ch = new NotificationChannel(CHANNEL, "연주 중", NotificationManager.IMPORTANCE_LOW);
                ch.setShowBadge(false);
                nm.createNotificationChannel(ch);
            }
            b = new Notification.Builder(this, CHANNEL);
        } else {
            b = new Notification.Builder(this);
        }
        int imm = Build.VERSION.SDK_INT >= 23 ? PendingIntent.FLAG_IMMUTABLE : 0;
        PendingIntent open = PendingIntent.getActivity(this, 0, new Intent(this, MainActivity.class), imm | PendingIntent.FLAG_UPDATE_CURRENT);
        PendingIntent stop = PendingIntent.getService(this, 1, new Intent(this, EngineService.class).setAction(ACTION_STOP), imm | PendingIntent.FLAG_UPDATE_CURRENT);
        b.setSmallIcon(android.R.drawable.ic_media_play)
                .setContentTitle("차량 BGM AI")
                .setContentText("상황을 보고 음악을 고르는 중")
                .setContentIntent(open)
                .setOngoing(true)
                .addAction(new Notification.Action.Builder(android.R.drawable.ic_menu_close_clear_cancel, "끄기", stop).build());
        Notification n = b.build();
        if (Build.VERSION.SDK_INT >= 29) startForeground(NOTE_ID, n, ServiceInfo.FOREGROUND_SERVICE_TYPE_MEDIA_PLAYBACK);
        else startForeground(NOTE_ID, n);
    }

    private void prepareAndStart() {
        try {
            if (!Native.loaded()) throw new RuntimeException("엔진 라이브러리를 못 불러옴: " + Native.loadError);
            File data = installData();
            File out = new File(getFilesDir(), "악보");
            out.mkdirs();
            status = "AI · 악기 불러오는 중";
            Native.start(data.getPath(), out.getPath(), new File(getFilesDir(), "log.txt").getPath());
        } catch (Throwable t) {
            failure = String.valueOf(t.getMessage() != null ? t.getMessage() : t);
        }
    }

    /** assets/data → 앱 폴더/data (assets/data.version 이 같으면 건너뜀) */
    private File installData() throws Exception {
        AssetManager am = getAssets();
        File dst = new File(getFilesDir(), "data");
        String ver = readAll(am.open("data.version")).trim();
        File stamp = new File(dst, ".version");
        if (stamp.exists() && readAll(new java.io.FileInputStream(stamp)).trim().equals(ver)) return dst;

        List<String> files = new ArrayList<>();
        List<Long> sizes = new ArrayList<>();
        long total = 0;
        try (BufferedReader r = new BufferedReader(new InputStreamReader(am.open("data.list"), StandardCharsets.UTF_8))) {
            for (String line; (line = r.readLine()) != null; ) {
                int tab = line.indexOf('\t');
                if (tab <= 0) continue;
                files.add(line.substring(0, tab));
                long sz = Long.parseLong(line.substring(tab + 1).trim());
                sizes.add(sz);
                total += sz;
            }
        }
        long free = getFilesDir().getUsableSpace();
        if (free < total + (50L << 20))
            throw new RuntimeException(String.format("저장 공간이 모자랍니다 (필요 %dMB · 남음 %dMB)", (total >> 20) + 50, free >> 20));
        deleteTree(dst);
        byte[] buf = new byte[1 << 18];
        long done = 0;
        for (int i = 0; i < files.size(); i++) {
            File f = new File(dst, files.get(i));
            f.getParentFile().mkdirs();
            try (InputStream in = am.open("data/" + files.get(i)); OutputStream o = new FileOutputStream(f)) {
                for (int n; (n = in.read(buf)) > 0; ) {
                    o.write(buf, 0, n);
                    done += n;
                    status = "음악 자료 푸는 중 " + (total > 0 ? done * 100 / total : 100) + "% (처음 한 번만)";
                }
            }
        }
        try (OutputStream o = new FileOutputStream(stamp)) { o.write(ver.getBytes(StandardCharsets.UTF_8)); }
        return dst;
    }

    private static String readAll(InputStream in) throws Exception {
        try (InputStream i = in) {
            java.io.ByteArrayOutputStream b = new java.io.ByteArrayOutputStream();
            byte[] buf = new byte[4096];
            for (int n; (n = i.read(buf)) > 0; ) b.write(buf, 0, n);
            return new String(b.toByteArray(), StandardCharsets.UTF_8);
        }
    }

    private static void deleteTree(File f) {
        File[] kids = f.listFiles();
        if (kids != null) for (File k : kids) deleteTree(k);
        f.delete();
    }
}
