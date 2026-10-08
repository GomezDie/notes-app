"""Cut a vertical Short (1080x1920) from a long-form render.

Layout: blurred, zoomed copy of the clip fills the frame; the 16:9 clip sits in
the middle; a hook line at the top; big burned-in captions underneath; a
call-to-action for the full episode at the end.

    python3 shorts.py long.mp4 timing.json FIRST LAST "HOOK TEXT" "CTA TEXT" out.mp4
"""
import json
import subprocess
import sys

TAIL = 1.2  # seconds kept after the last sentence


def ass_time(t):
    t = max(0.0, t)
    return f"{int(t // 3600)}:{int(t // 60 % 60):02d}:{t % 60:05.2f}"


def ass_escape(s):
    return s.replace("{", "(").replace("}", ")").replace("\n", "\\N")


def chunk(text, max_words=5):
    """Split a sentence into short caption chunks (Shorts read best ~3-5 words)."""
    words = text.split()
    return [" ".join(words[i:i + max_words]) for i in range(0, len(words), max_words)]


def caption_chunks(sentence, max_words=4):
    """(text, start, end) chunks. Uses word timestamps when the timing file has
    them (breaking after punctuation), else splits the sentence evenly."""
    words = sentence.get("words")
    if not words:
        parts = chunk(sentence["text"], max_words + 1)
        a, b = sentence["start"], sentence["end"]
        step = (b - a) / len(parts)
        return [(p, a + k * step, a + (k + 1) * step) for k, p in enumerate(parts)]
    out, cur = [], []
    for w in words:
        cur.append(w)
        if len(cur) >= max_words or w["w"].rstrip("\u201d\"").endswith((",", ".", "?", "!", ":", "\u2026")):
            out.append(cur)
            cur = []
    if cur:
        out.append(cur)
    res = []
    for k, g in enumerate(out):
        end = out[k + 1][0]["s"] if k + 1 < len(out) else g[-1]["e"]
        res.append((" ".join(w["w"] for w in g), g[0]["s"], max(end, g[-1]["e"])))
    return res


def build_ass(sentences, t0, clip_dur, hook, cta):
    head = """[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
WrapStyle: 0

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Cap,Liberation Sans,84,&H00FFFFFF,&H00FFFFFF,&H00000000,&H64000000,1,0,0,0,100,100,0,0,1,6,2,5,60,60,0,1
Style: Hook,Liberation Serif,76,&H005CA4C9,&H005CA4C9,&H00000000,&H00000000,1,0,0,0,100,100,1,0,1,5,0,8,60,60,230,1
Style: Cta,Liberation Sans,54,&H00FFFFFF,&H00FFFFFF,&H00000000,&H96000000,1,0,0,0,100,100,2,0,3,18,0,2,80,80,260,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    ev = [f"Dialogue: 0,{ass_time(0)},{ass_time(clip_dur - 2.6)},Hook,,0,0,0,,{ass_escape(hook)}"]
    for s in sentences:
        for text, a, b in caption_chunks(s):
            ev.append(f"Dialogue: 1,{ass_time(a - t0)},{ass_time(b - t0)},Cap,,0,0,0,,"
                      f"{{\\pos(540,1420)\\fad(60,0)}}{ass_escape(text)}")
    ev.append(f"Dialogue: 2,{ass_time(clip_dur - 2.6)},{ass_time(clip_dur)},Cta,,0,0,0,,"
              f"{{\\fad(200,0)}}{ass_escape(cta)}")
    return head + "\n".join(ev) + "\n"


def main():
    src, timing_path, first, last, hook, cta, out = sys.argv[1:8]
    first, last = int(first), int(last)
    timing = json.load(open(timing_path))["sentences"]
    sents = timing[first:last + 1]
    t0 = max(0.0, sents[0]["start"] - 0.35)
    t1 = sents[-1]["end"] + TAIL
    dur = t1 - t0
    ass_path = out.rsplit(".", 1)[0] + ".ass"
    open(ass_path, "w", encoding="utf-8").write(build_ass(sents, t0, dur, hook, cta))
    vf = ("[0:v]split[a][b];"
          "[a]scale=-2:1920,crop=1080:1920,boxblur=30:2,eq=brightness=-0.18[bg];"
          "[b]crop=1600:1080,scale=1080:-2[fg];"
          "[bg][fg]overlay=0:(H-h)/2-60,"
          f"ass={ass_path},fade=t=out:st={dur - 0.4:.2f}:d=0.4[v]")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-ss", f"{t0:.2f}", "-t", f"{dur:.2f}",
                    "-i", src, "-filter_complex", vf, "-map", "[v]", "-map", "0:a",
                    "-af", f"afade=t=in:d=0.15,afade=t=out:st={dur - 0.5:.2f}:d=0.5",
                    "-c:v", "libx264", "-preset", "veryfast", "-crf", "19", "-pix_fmt", "yuv420p",
                    "-c:a", "aac", "-b:a", "160k", "-r", "30", out], check=True)
    print(f"{out}: {dur:.1f}s ({first}-{last})")


if __name__ == "__main__":
    main()
