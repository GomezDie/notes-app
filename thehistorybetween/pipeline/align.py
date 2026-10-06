"""Align narration sentences to an audio file without a speech model.

Detects pauses with ffmpeg's silencedetect, then picks one pause per sentence
boundary (monotonic dynamic programming) so that sentence lengths in time track
their lengths in characters. Good enough for cutting scenes and captions; swap
in word-level timestamps (e.g. a transcription API) when one is available.

    python3 align.py narration.mp3 sentences.txt out.json
"""
import json
import re
import subprocess
import sys


def detect_pauses(audio, noise_db=-35, min_dur=0.25):
    out = subprocess.run(
        ["ffmpeg", "-hide_banner", "-i", audio, "-af",
         f"silencedetect=noise={noise_db}dB:d={min_dur}", "-f", "null", "-"],
        capture_output=True, text=True).stderr
    starts = [float(x) for x in re.findall(r"silence_start: ([\d.]+)", out)]
    ends = [float(x) for x in re.findall(r"silence_end: ([\d.]+)", out)]
    dur = float(re.search(r"Duration: (\d+):(\d+):([\d.]+)", out).groups()[2]) + \
        60 * int(re.search(r"Duration: (\d+):(\d+)", out).group(2))
    pauses = list(zip(starts, ends))
    speech_start = pauses[0][1] if pauses and pauses[0][0] < 0.05 else 0.0
    if pauses and pauses[0][0] < 0.05:
        pauses = pauses[1:]
    speech_end = dur
    if pauses and pauses[-1][1] >= dur - 0.05:
        speech_end = pauses[-1][0]
        pauses = pauses[:-1]
    return speech_start, speech_end, pauses, dur


def syllables(text):
    """Rough English syllable count: vowel groups per word, min 1."""
    n = 0
    for w in re.findall(r"[a-zA-Z']+", text.lower()):
        g = len(re.findall(r"[aeiouy]+", w))
        if w.endswith("e") and g > 1 and not w.endswith(("le", "ee")):
            g -= 1
        n += max(1, g)
    return n


def align(sentences, speech_start, speech_end, pauses):
    """Choose one pause per sentence boundary so every sentence is spoken at
    close to the narrator's average syllable rate (DP over boundary pauses)."""
    syl = [syllables(s) for s in sentences]
    n, m = len(sentences) - 1, len(pauses)
    if m < n:
        raise SystemExit(f"only {m} pauses for {n} sentence boundaries")
    speech = (speech_end - speech_start) - 0.0
    rate = sum(syl) / speech  # syllables per second, first guess

    def cost(k, t0, t1):  # sentence k spoken between t0 and t1
        want = syl[k] / rate
        return ((t1 - t0) - want) ** 2 / max(want, 0.5)

    for _ in range(3):  # re-estimate the rate from the chosen alignment
        INF = float("inf")
        best = [[INF] * m for _ in range(n)]
        back = [[-1] * m for _ in range(n)]
        for j in range(m):
            best[0][j] = cost(0, speech_start, pauses[j][0])
        for i in range(1, n):
            for j in range(i, m):
                for jp in range(i - 1, j):
                    c = best[i - 1][jp] + cost(i, pauses[jp][1], pauses[j][0])
                    if c < best[i][j]:
                        best[i][j], back[i][j] = c, jp
        j = min(range(n - 1, m), key=lambda k: best[n - 1][k] + cost(n, pauses[k][1], speech_end))
        picks = []
        for i in range(n - 1, -1, -1):
            picks.append(j)
            j = back[i][j]
        picks.reverse()
        bounds = [speech_start] + [x for j in picks for x in pauses[j]] + [speech_end]
        spoken = sum(bounds[2 * k + 1] - bounds[2 * k] for k in range(n + 1))
        rate = sum(syl) / spoken

    out = []
    for k, s in enumerate(sentences):
        a, b = bounds[2 * k], bounds[2 * k + 1]
        out.append({"i": k, "text": s, "start": round(a, 3), "end": round(b, 3),
                    "syl_per_s": round(syl[k] / max(b - a, 0.1), 1)})
    return out


def main():
    audio, sent_file, out_file = sys.argv[1:4]
    sentences = [l.strip() for l in open(sent_file, encoding="utf-8") if l.strip()]
    s0, s1, pauses, dur = detect_pauses(audio)
    timeline = align(sentences, s0, s1, pauses)
    json.dump({"audio": audio, "duration": dur, "sentences": timeline},
              open(out_file, "w"), indent=1, ensure_ascii=False)
    for x in timeline:
        print(f"{x['start']:7.2f}-{x['end']:7.2f}  {x['text'][:70]}")


if __name__ == "__main__":
    main()
