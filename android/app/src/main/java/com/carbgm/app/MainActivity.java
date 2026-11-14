package com.carbgm.app;

import android.Manifest;
import android.app.Activity;
import android.content.Intent;
import android.content.pm.PackageManager;
import android.graphics.Color;
import android.net.Uri;
import android.os.Build;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.view.Gravity;
import android.view.View;
import android.view.WindowManager;
import android.webkit.PermissionRequest;
import android.webkit.WebChromeClient;
import android.webkit.WebResourceRequest;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import android.widget.FrameLayout;
import android.widget.TextView;

import java.io.File;
import java.io.RandomAccessFile;
import java.util.ArrayList;
import java.util.List;

/**
 * 화면 하나: 엔진이 준비되면 WebView 로 http://127.0.0.1:포트/ (데스크톱판과 같은 화면) 을 엶.
 * 준비되기 전에는 가운데 한 줄로 상황만 보여 줌.
 */
public class MainActivity extends Activity {
    private static final int REQ_PERMS = 1, REQ_MIC_FOR_PAGE = 2;

    private WebView web;
    private TextView msg;
    private final Handler ui = new Handler(Looper.getMainLooper());
    private boolean opened = false;
    private PermissionRequest pendingPage;   // 페이지(getUserMedia)가 마이크를 달라고 했는데 아직 권한이 없을 때
    SpeechBridge speech;

    @Override
    protected void onCreate(Bundle saved) {
        super.onCreate(saved);
        getWindow().setStatusBarColor(Color.rgb(0x10, 0x12, 0x14));
        getWindow().setNavigationBarColor(Color.rgb(0x10, 0x12, 0x14));
        getWindow().addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON);   // 차 화면 · 시연 중엔 꺼지지 않게

        FrameLayout root = new FrameLayout(this);
        root.setBackgroundColor(Color.rgb(0x10, 0x12, 0x14));
        web = new WebView(this);
        web.setBackgroundColor(Color.rgb(0x10, 0x12, 0x14));
        web.setVisibility(View.INVISIBLE);
        root.addView(web, new FrameLayout.LayoutParams(-1, -1));
        msg = new TextView(this);
        msg.setTextColor(Color.rgb(0x3d, 0xd6, 0x8c));
        msg.setTextSize(18);
        msg.setGravity(Gravity.CENTER);
        int pad = (int) (24 * getResources().getDisplayMetrics().density);
        msg.setPadding(pad, pad, pad, pad);
        msg.setText("준비 중");
        root.addView(msg, new FrameLayout.LayoutParams(-1, -1));
        setContentView(root);

        WebSettings s = web.getSettings();
        s.setJavaScriptEnabled(true);
        s.setDomStorageEnabled(true);                 // localStorage (고른 갈래 · 펼침 기억)
        s.setMediaPlaybackRequiresUserGesture(false);
        speech = new SpeechBridge(this, web);
        web.addJavascriptInterface(speech, "AndroidSpeech");   // 화면의 🎙 = 안드로이드 음성 인식 (WebView 엔 webkitSpeechRecognition 이 없음)
        web.setWebViewClient(new WebViewClient() {
            @Override
            public boolean shouldOverrideUrlLoading(WebView v, WebResourceRequest r) {
                Uri u = r.getUrl();
                if ("127.0.0.1".equals(u.getHost())) return false;
                try { startActivity(new Intent(Intent.ACTION_VIEW, u)); } catch (Exception ignored) {}
                return true;
            }
        });
        web.setWebChromeClient(new WebChromeClient() {
            @Override
            public void onPermissionRequest(PermissionRequest req) {   // 🎙 차 안 말소리 듣기 (getUserMedia)
                runOnUiThread(() -> {
                    if (hasMic()) req.grant(new String[]{PermissionRequest.RESOURCE_AUDIO_CAPTURE});
                    else {
                        pendingPage = req;
                        requestPermissions(new String[]{Manifest.permission.RECORD_AUDIO}, REQ_MIC_FOR_PAGE);
                    }
                });
            }
        });

        // 처음 켤 때 한 번: 마이크(말소리 · 음성 요청) · 알림(연주 중 · 끄기)
        List<String> want = new ArrayList<>();
        if (!hasMic()) want.add(Manifest.permission.RECORD_AUDIO);
        if (Build.VERSION.SDK_INT >= 33 && checkSelfPermission(Manifest.permission.POST_NOTIFICATIONS) != PackageManager.PERMISSION_GRANTED)
            want.add(Manifest.permission.POST_NOTIFICATIONS);
        if (!want.isEmpty()) requestPermissions(want.toArray(new String[0]), REQ_PERMS);

        Intent svc = new Intent(this, EngineService.class);
        if (Build.VERSION.SDK_INT >= 26) startForegroundService(svc); else startService(svc);
        ui.post(this::poll);
    }

    boolean hasMic() { return checkSelfPermission(Manifest.permission.RECORD_AUDIO) == PackageManager.PERMISSION_GRANTED; }

    private void poll() {
        if (opened) return;
        String fail = EngineService.failure;
        int port = Native.loaded() ? Native.port() : -1;
        if (fail == null && !Native.loaded()) fail = "엔진 라이브러리를 못 불러옴\n" + Native.loadError;
        if (fail == null && port < 0) fail = Native.error();
        if (fail != null) {
            msg.setTextColor(Color.rgb(0xf0, 0x6a, 0x6a));
            msg.setText("시작하지 못했습니다\n\n" + fail + "\n\n" + tail(new File(getFilesDir(), "log.txt"), 1200));
            return;
        }
        if (port > 0) {
            opened = true;
            web.loadUrl("http://127.0.0.1:" + port + "/");
            web.setVisibility(View.VISIBLE);
            msg.setVisibility(View.GONE);
            return;
        }
        msg.setText(EngineService.status);
        ui.postDelayed(this::poll, 250);
    }

    private static String tail(File f, int max) {
        try (RandomAccessFile r = new RandomAccessFile(f, "r")) {
            long n = r.length(), from = Math.max(0, n - max);
            byte[] b = new byte[(int) (n - from)];
            r.seek(from);
            r.readFully(b);
            return new String(b, "UTF-8");
        } catch (Exception e) {
            return "";
        }
    }

    @Override
    public void onRequestPermissionsResult(int code, String[] perms, int[] res) {
        if (code == REQ_MIC_FOR_PAGE && pendingPage != null) {
            if (hasMic()) pendingPage.grant(new String[]{PermissionRequest.RESOURCE_AUDIO_CAPTURE});
            else pendingPage.deny();
            pendingPage = null;
        }
        speech.onPermission(hasMic());
    }

    @Override
    public void onBackPressed() {
        moveTaskToBack(true);   // 뒤로 = 앱만 내려감 · 음악은 계속 (끄기는 화면의 [끝내기] 또는 알림의 [끄기])
    }

    @Override
    protected void onDestroy() {
        speech.destroy();
        web.destroy();
        super.onDestroy();
    }
}
