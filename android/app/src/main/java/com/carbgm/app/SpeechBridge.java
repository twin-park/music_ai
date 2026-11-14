package com.carbgm.app;

import android.Manifest;
import android.app.Activity;
import android.content.Intent;
import android.os.Bundle;
import android.speech.RecognitionListener;
import android.speech.RecognizerIntent;
import android.speech.SpeechRecognizer;
import android.webkit.JavascriptInterface;
import android.webkit.WebView;

import org.json.JSONObject;

import java.util.ArrayList;

/**
 * 화면(web/index.html)의 🎙 → 안드로이드 SpeechRecognizer.
 * 페이지에서는 window.AndroidSpeech.start(lang, interim) / stop(), 결과는 window.__androidSpeech(종류, 글, 끝?) 로 돌려줌.
 * index.html 이 이걸 webkitSpeechRecognition 꼴로 감싸서, 화면 코드는 데스크톱(크롬)과 같음.
 */
final class SpeechBridge {
    private final Activity act;
    private final WebView web;
    private SpeechRecognizer sr;
    private String waitLang;          // 마이크 권한을 묻는 중에 누른 경우
    private boolean waitInterim;

    SpeechBridge(Activity a, WebView w) { act = a; web = w; }

    @JavascriptInterface
    public boolean available() { return SpeechRecognizer.isRecognitionAvailable(act); }

    @JavascriptInterface
    public void start(String lang, boolean interim) {
        act.runOnUiThread(() -> {
            if (act.checkSelfPermission(Manifest.permission.RECORD_AUDIO) != android.content.pm.PackageManager.PERMISSION_GRANTED) {
                waitLang = lang; waitInterim = interim;
                act.requestPermissions(new String[]{Manifest.permission.RECORD_AUDIO}, 3);
                return;
            }
            begin(lang, interim);
        });
    }

    @JavascriptInterface
    public void stop() { act.runOnUiThread(() -> { if (sr != null) sr.stopListening(); }); }

    void onPermission(boolean granted) {
        if (waitLang == null) return;
        String l = waitLang; waitLang = null;
        if (granted) begin(l, waitInterim);
        else { emit("error", "not-allowed", false); emit("end", "", false); }
    }

    private void begin(String lang, boolean interim) {
        destroy();
        sr = SpeechRecognizer.createSpeechRecognizer(act);
        sr.setRecognitionListener(new RecognitionListener() {
            private boolean ended = false;
            private void end() { if (!ended) { ended = true; emit("end", "", false); destroy(); } }
            @Override public void onReadyForSpeech(Bundle b) {}
            @Override public void onBeginningOfSpeech() {}
            @Override public void onRmsChanged(float v) {}
            @Override public void onBufferReceived(byte[] b) {}
            @Override public void onEndOfSpeech() {}
            @Override public void onEvent(int t, Bundle b) {}
            @Override public void onError(int e) { emit("error", "code-" + e, false); end(); }
            @Override public void onPartialResults(Bundle b) { String t = first(b); if (t != null && !t.isEmpty()) emit("result", t, false); }
            @Override public void onResults(Bundle b) { String t = first(b); if (t != null) emit("result", t, true); end(); }
        });
        Intent it = new Intent(RecognizerIntent.ACTION_RECOGNIZE_SPEECH);
        it.putExtra(RecognizerIntent.EXTRA_LANGUAGE_MODEL, RecognizerIntent.LANGUAGE_MODEL_FREE_FORM);
        it.putExtra(RecognizerIntent.EXTRA_LANGUAGE, lang == null || lang.isEmpty() ? "ko-KR" : lang);
        it.putExtra(RecognizerIntent.EXTRA_PARTIAL_RESULTS, interim);
        it.putExtra(RecognizerIntent.EXTRA_MAX_RESULTS, 1);
        sr.startListening(it);
    }

    private static String first(Bundle b) {
        ArrayList<String> r = b == null ? null : b.getStringArrayList(SpeechRecognizer.RESULTS_RECOGNITION);
        return r == null || r.isEmpty() ? null : r.get(0);
    }

    private void emit(String type, String text, boolean fin) {
        String js = "window.__androidSpeech&&window.__androidSpeech(" + JSONObject.quote(type) + "," + JSONObject.quote(text) + "," + fin + ")";
        web.post(() -> web.evaluateJavascript(js, null));
    }

    void destroy() {
        if (sr != null) { sr.destroy(); sr = null; }
    }
}
