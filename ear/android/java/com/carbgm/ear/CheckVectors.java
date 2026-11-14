package com.carbgm.ear;

import java.io.IOException;
import java.nio.ByteBuffer;
import java.nio.ByteOrder;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.ArrayList;
import java.util.List;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

/**
 * 시험 벡터로 자바 쪽(Prosody · EarWords)이 파이썬과 같은지 확인.
 *   java com.carbgm.ear.CheckVectors <묶음 폴더>   (thresholds.json · test/expected.txt · test/test_vectors/*.wav)
 * 모델 출력(sounds · emotion)은 expected.txt 의 값을 씀 — 모델 자체는 ONNX/TFLite 결과를 expected.json 과 따로 견주면 됨.
 */
public final class CheckVectors {
    static float[] readWav16(Path p) throws IOException {
        ByteBuffer b = ByteBuffer.wrap(Files.readAllBytes(p)).order(ByteOrder.LITTLE_ENDIAN);
        int pos = 12;
        while (pos + 8 <= b.limit()) {                       // RIFF 조각 따라가며 data 찾기
            String id = new String(new byte[] {b.get(pos), b.get(pos + 1), b.get(pos + 2), b.get(pos + 3)}, StandardCharsets.US_ASCII);
            int size = b.getInt(pos + 4);
            if (id.equals("data")) {
                float[] x = new float[size / 2];
                for (int i = 0; i < x.length; i++) x[i] = b.getShort(pos + 8 + 2 * i) / 32768f;
                return x;
            }
            pos += 8 + size + (size & 1);
        }
        throw new IOException("data 조각 없음: " + p);
    }

    static float[] nums(String line) {
        String[] t = line.trim().split("\\s+");
        float[] v = new float[t.length - 1];
        for (int i = 1; i < t.length; i++) v[i - 1] = Float.parseFloat(t[i]);
        return v;
    }

    public static void main(String[] args) throws IOException {
        Path dir = Paths.get(args.length > 0 ? args[0] : ".");
        String thj = new String(Files.readAllBytes(dir.resolve("thresholds.json")), StandardCharsets.UTF_8);
        float[] th = new float[EarWords.SOUND_IDS.length];
        for (int i = 0; i < th.length; i++) {
            Matcher m = Pattern.compile("\"" + EarWords.SOUND_IDS[i] + "\"\\s*:\\s*([0-9.eE+-]+)").matcher(thj);
            th[i] = m.find() ? Float.parseFloat(m.group(1)) : 0.5f;
        }
        List<String> L = Files.readAllLines(dir.resolve("test").resolve("expected.txt"), StandardCharsets.UTF_8);
        int fails = 0, n = 0;
        for (int i = 0; i + 4 < L.size(); i += 5) {
            String name = L.get(i).substring(5).trim();
            float[] sounds = nums(L.get(i + 1)), emo = nums(L.get(i + 2)), pe = nums(L.get(i + 3));
            String expWords = L.get(i + 4).length() > 6 ? L.get(i + 4).substring(6).trim() : "";
            float[] x = readWav16(dir.resolve("test").resolve("test_vectors").resolve(name + ".wav"));
            long t0 = System.nanoTime();
            Prosody.Result p = Prosody.compute(x);
            double ms = (System.nanoTime() - t0) / 1e6;
            double[] got = {p.loudDb, p.loudVar, p.pitchVar, p.rate, p.voicedRatio, p.pitchMed};
            String[] nm = {"loud_db", "loud_var", "pitch_var", "rate", "voiced_ratio", "pitch_med"};
            StringBuilder diff = new StringBuilder();
            for (int k = 0; k < got.length; k++) {
                double tol = 1e-3 * Math.max(1, Math.abs(pe[k])) + 1e-3;
                if (Math.abs(got[k] - pe[k]) > tol) diff.append(String.format(" %s 자바 %.5f 파이썬 %.5f", nm[k], got[k], pe[k]));
            }
            List<EarWords.Word> ws = EarWords.toWords(sounds, th, emo, p);
            List<String> parts = new ArrayList<>();
            for (EarWords.Word w : ws) parts.add(w.word + ":" + w.score + ":" + w.kind);
            String gotWords = String.join(" | ", parts);
            boolean ok = diff.length() == 0 && gotWords.equals(expWords);
            if (!ok) fails++;
            n++;
            System.out.printf("%s %-13s 말투 %.1fms%s%n   단어 %s%n", ok ? "같음" : "다름", name, ms, diff, gotWords.isEmpty() ? "(없음)" : gotWords);
            if (!gotWords.equals(expWords)) System.out.println("   파이썬 " + expWords);
        }
        System.out.printf("%d개 중 %d개 같음%n", n, n - fails);
        if (fails > 0) System.exit(1);
    }
}
