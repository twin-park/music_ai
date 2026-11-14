package com.carbgm.app;

/** C++ 엔진 (android/jni/jni.cpp) — 한 프로세스에 한 번만 켜짐 */
final class Native {
    static Throwable loadError;

    static {
        try {
            System.loadLibrary("c++_shared");
            System.loadLibrary("fluidsynth");   // 엔진이 dlopen("libfluidsynth.so") 할 때 이미 올라와 있게
            System.loadLibrary("carbgm");
        } catch (Throwable t) {
            loadError = t;
        }
    }

    private Native() {}

    static boolean loaded() { return loadError == null; }

    /** 0 = 켜기 시작 · 1 = 이미 켜짐 */
    static native int start(String dataDir, String outDir, String logPath);

    /** > 0 = 화면 포트 · 0 = 준비 중 · < 0 = 실패 (error()) */
    static native int port();

    static native String error();
}
