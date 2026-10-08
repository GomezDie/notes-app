"""Native vertical Short (1080x1920) from a JSON spec + narration + word timings.

    python3 vshort.py shorts/001-nobody-shot-me/spec.json            # render
    python3 vshort.py shorts/001-nobody-shot-me/spec.json --stills 3 20 40

spec.json (paths relative to the spec's folder unless absolute):
{
  "title": "Shot 14 times. His last words were a lie.",
  "hook": "SHOT 14 TIMES.\\nHIS LAST WORDS:",       # top of screen, first ~3 s
  "voice": "vo.mp3", "words": "words.json",          # ElevenLabs TTS + Scribe words.json
  "music": "../../episodes/ep01-capone/assets/music_score.mp3", "music_offset": 5.6,
  "min_duration": 61.5,                              # TikTok pays only for videos > 60 s
  "beats": [                                          # each beat starts at a phrase in the narration
    {"at": "February", "type": "clip", "src": "...street.mp4", "focus": 0.55,
     "label": ["CHICAGO", "FEBRUARY 14, 1929"]},
    {"at": "open fire", "type": "flash"},
    {"at": "Two Thompson", "type": "stat", "lines": ["2 x THOMPSON SUBMACHINE GUNS", "2 x SHOTGUNS"],
     "big": "~70", "big_label": "ROUNDS IN SECONDS", "bg": "...casings.mp4"},
    {"at": "Nobody shot me", "type": "quote", "text": "Nobody shot me.", "attr": "FRANK GUSENBERG, 1929"},
    {"at": "Follow", "type": "end", "text": "THE HUNT FOR AL CAPONE", "sub": "Part 2 on TheHistoryBetween"}
  ]
}
Beat types: clip | still | card | quote | stat | lineup | flash | stamp | end.
Any beat may add "label": [title, sub] (top-left block) or "stamp": "TEXT" (red rubber stamp).
"""
import json
import math
import os
import re
import subprocess
import sys

from PIL import Image, ImageDraw

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gfx import (BLUE, DIM, GOLD, INK, INK2, PAPER, RED, BlendDraw, clamp, ease,  # noqa: E402
                 ease_out, fade, font, lerp, mix, mux, tracked, typewriter, wrap)
from shorts import caption_chunks  # noqa: E402

VW, VH, FPS = 1080, 1920, 30
CAP_Y = 1290          # captions (clear of TikTok/Shorts bottom UI)
TOP_SAFE = 230        # clear of top UI


def norm(t):
    return re.sub(r"[^a-z0-9]", "", t.lower())


class VClip:
    """Clip cover-cropped to 9:16 (focus = horizontal position 0..1), frames cached as JPEGs."""

    def __init__(self, path, cache, focus=0.5, min_speed=0.75):
        self.path, self.focus, self.min_speed = path, focus, min_speed
        self.cache = os.path.join(cache, os.path.splitext(os.path.basename(path))[0] + f"_v{int(focus * 100)}")
        out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", path],
                             capture_output=True, text=True).stdout.strip()
        self.dur = float(out)
        self.speed = None
        self.cur = (None, None)

    def _extract(self, speed):
        d = f"{self.cache}_s{int(speed * 100)}"
        if not (os.path.isdir(d) and os.listdir(d)):
            os.makedirs(d, exist_ok=True)
            vf = f"setpts=PTS/{speed:.3f},"
            vf += "minterpolate=fps=30:mi_mode=blend," if speed < 0.99 else "fps=30,"
            vf += ("scale='if(gt(a,9/16),-2,1080)':'if(gt(a,9/16),1920,-2)':flags=lanczos,"
                   f"crop=1080:1920:(iw-1080)*{self.focus:.3f}:(ih-1920)/2,unsharp=5:5:0.5")
            subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", self.path, "-vf", vf, "-q:v", "3",
                            os.path.join(d, "%05d.jpg")], check=True)
        self.dir, self.frames = d, sorted(os.listdir(d))

    def frame(self, t, scene_dur):
        speed = clamp(self.dur / max(scene_dur, 0.1), self.min_speed, 1.0)
        if speed != self.speed:
            self.speed = speed
            self._extract(speed)
        i = int(t * FPS)
        hold = max(0, i - (len(self.frames) - 1))
        name = self.frames[min(i, len(self.frames) - 1)]
        if self.cur[0] != name:
            self.cur = (name, Image.open(os.path.join(self.dir, name)).convert("RGB"))
        img = self.cur[1]
        if hold:
            z = 1 + 0.02 * hold / FPS
            cw, ch = VW / z, VH / z
            img = img.resize((VW, VH), Image.BILINEAR, box=((VW - cw) / 2, (VH - ch) / 2, (VW + cw) / 2, (VH + ch) / 2))
        return img


class VStill:
    """Still image cover-cropped to 9:16 with a slow push-in."""

    def __init__(self, path, focus=0.5):
        img = Image.open(path).convert("RGB")
        s = max(VW * 1.15 / img.width, VH * 1.15 / img.height)
        self.src = img.resize((int(img.width * s), int(img.height * s)), Image.LANCZOS)
        self.focus = focus

    def frame(self, t, scene_dur):
        z = 1.0 + 0.10 * ease(t / max(scene_dur, 0.1))
        s0 = min(self.src.width / VW, self.src.height / VH)  # largest 9:16 box that fits
        cw, ch = VW * s0 / z, VH * s0 / z
        cx = lerp(cw / 2, self.src.width - cw / 2, self.focus)
        cy = self.src.height / 2
        return self.src.resize((VW, VH), Image.BILINEAR, box=(cx - cw / 2, cy - ch / 2, cx + cw / 2, cy + ch / 2))


def darken(img, k):
    return Image.blend(img, Image.new("RGB", img.size, INK), clamp(k)) if k > 0 else img


def bg_canvas():
    img = Image.new("RGB", (VW, VH), INK)
    d = ImageDraw.Draw(img)
    for r in range(900, 0, -30):  # soft warm glow in the middle
        k = (1 - r / 900) * 0.5
        d.ellipse((VW / 2 - r, VH * 0.42 - r, VW / 2 + r, VH * 0.42 + r), fill=mix(INK, (42, 35, 27), k))
    return img


BG = None


class Short:
    def __init__(self, spec_path):
        self.base = os.path.dirname(os.path.abspath(spec_path))
        self.spec = json.load(open(spec_path))
        self.build = os.path.join(self.base, "build")
        os.makedirs(self.build, exist_ok=True)
        words = json.load(open(self.p(self.spec["words"])))["words"]
        self.words = [{"w": w["text"], "s": w["start"], "e": w["end"]} for w in words if w.get("type", "word") == "word"]
        self.vo_end = self.words[-1]["e"]
        self.total = max(self.vo_end + self.spec.get("tail", 2.0), self.spec.get("min_duration", 61.5))
        self.chunks = []
        for text, a, b in caption_chunks({"words": self.words}, max_words=3):
            self.chunks.append((text, a, b))
        self.beats = self._place_beats()

    def p(self, rel):
        return rel if os.path.isabs(rel) else os.path.normpath(os.path.join(self.base, rel))

    def _find(self, phrase, start_idx):
        toks = [norm(t) for t in phrase.split()]
        ws = [norm(w["w"]) for w in self.words]
        for i in range(start_idx, len(ws) - len(toks) + 1):
            if all(ws[i + k].startswith(toks[k]) for k in range(len(toks))):
                return i
        raise SystemExit(f"beat phrase not found in narration: {phrase!r}")

    def _place_beats(self):
        out, idx = [], 0
        for k, b in enumerate(self.spec["beats"]):
            i = self._find(b["at"], idx)
            idx = i
            start = 0.0 if k == 0 else max(0.0, self.words[i]["s"] - 0.12)
            b = dict(b, start=start)
            for key in ("src", "bg"):
                if key in b:
                    path = self.p(b[key])
                    obj = VClip(path, os.path.join(self.build, "frames"), b.get("focus", 0.5)) \
                        if path.endswith(".mp4") else VStill(path, b.get("focus", 0.5))
                    b["_" + key] = obj
            out.append(b)
        for k, b in enumerate(out):
            b["end"] = out[k + 1]["start"] if k + 1 < len(out) else self.total
        return out

    # ------------------------------------------------------------------ drawing
    def draw_beat(self, b, t):
        lt, dur = t - b["start"], b["end"] - b["start"]
        typ = b["type"]
        global BG
        if BG is None:
            BG = bg_canvas()
        if typ in ("clip", "still"):
            img = b["_src"].frame(lt, dur)
            img = darken(img, b.get("dim", 0.0))
        elif "_bg" in b:
            img = darken(b["_bg"].frame(lt, dur), b.get("dim", 0.55))
        else:
            img = BG.copy()
        if typ == "flash":
            img = Image.new("RGB", (VW, VH), (6, 6, 5))
            pulse = max(0.0, 1 - abs(lt - 0.12) / 0.14) * 0.3 + max(0.0, 1 - abs(lt - 0.5) / 0.14) * 0.18
            img = Image.blend(img, Image.new("RGB", (VW, VH), RED), pulse)
        d = BlendDraw(img)
        cy = VH * 0.40
        if typ == "card":
            a = fade(lt, 0.1, 0.4)
            if b.get("kicker"):
                tracked(d, (VW / 2, cy - 170), b["kicker"], font("sans_b", 34), GOLD + (int(255 * a),), 8, "ma")
            y = cy - 90
            for line in [l for part in b["text"].split("\n") for l in wrap(d, part, font("serif_b", 84), VW - 160)]:
                d.text((VW / 2, y), line, font=font("serif_b", 84), fill=PAPER + (int(255 * a),), anchor="ma")
                y += 100
            if b.get("sub"):
                d.text((VW / 2, y + 30), b["sub"], font=font("serif_i", 46), fill=GOLD + (int(255 * fade(lt, 0.6, 0.4)),), anchor="ma")
        elif typ == "quote":
            a = fade(lt, 0.1, 0.5)
            y = cy - 120
            for line in wrap(d, "“" + b["text"] + "”", font("serif_i", 120), VW - 140):
                d.text((VW / 2, y), line, font=font("serif_i", 120), fill=PAPER + (int(255 * a),), anchor="ma")
                y += 140
            a2 = fade(lt, 0.7, 0.4)
            d.line((VW / 2 - 60, y + 40, VW / 2 + 60, y + 40), fill=RED + (int(255 * a2),), width=4)
            tracked(d, (VW / 2, y + 70), b.get("attr", ""), font("sans_b", 30), DIM + (int(255 * a2),), 6, "ma")
        elif typ == "stat":
            y = cy - 220
            for k, line in enumerate(b.get("lines", [])):
                a = fade(lt, 0.15 + k * b.get("line_gap", 1.1), 0.25)
                tracked(d, (VW / 2, y), line, font("sans_b", 46), PAPER + (int(255 * a),), 4, "ma")
                y += 80
            if b.get("big"):
                a = fade(lt, b.get("big_at", 2.0), 0.2)
                d.text((VW / 2, y + 40), b["big"], font=font("serif_b", 240), fill=RED + (int(255 * a),), anchor="ma")
                tracked(d, (VW / 2, y + 320), b.get("big_label", ""), font("sans_b", 36), PAPER + (int(255 * a),), 8, "ma")
        elif typ == "lineup":
            n, a = b.get("n", 7), fade(lt, 0.1, 0.3)
            x0, x1, top, bot = 120, VW - 120, cy - 300, cy + 250
            d.rectangle((x0, top, x1, bot), outline=PAPER + (int(255 * a),), width=5)
            tracked(d, (x0 + 10, top - 50), "BACK WALL", font("sans_b", 26), GOLD + (int(255 * a),), 4)
            u = ease((lt - 0.4) / 1.6)
            for k in range(n):
                sx, sy = x0 + 150 + (k * 97) % 600, top + 260 + (k * 53) % 200
                ex, ey = x0 + 70 + k * (x1 - x0 - 140) / (n - 1), top + 50
                x, y = lerp(sx, ex, u), lerp(sy, ey, u)
                d.ellipse((x - 26, y - 26, x + 26, y + 26), fill=PAPER + (int(255 * a),))
            tracked(d, (VW / 2, bot + 40), b.get("caption", f"{n} MEN, FACING THE WALL"), font("sans_b", 38),
                    PAPER + (int(255 * a),), 6, "ma")
        elif typ == "end":
            a = fade(lt, 0.2, 0.6)
            tracked(d, (VW / 2, cy - 150), b.get("kicker", "THE HISTORY BETWEEN"), font("sans_b", 34), GOLD + (int(255 * a),), 12, "ma")
            y = cy - 70
            for line in [l for part in b["text"].split("\n") for l in wrap(d, part, font("serif_b", 104), VW - 140)]:
                d.text((VW / 2, y), line, font=font("serif_b", 104), fill=PAPER + (int(255 * fade(lt, 0.5, 0.6)),), anchor="ma")
                y += 118
            if b.get("sub"):
                d.text((VW / 2, y + 40), b["sub"], font=font("serif_i", 44), fill=mix(PAPER, INK, 0.2) + (int(255 * fade(lt, 1.1, 0.5)),), anchor="ma")
        if b.get("label"):
            self.label(d, b["label"], fade(lt, 0.3, 0.4) * (1 - fade(t, b["end"] - 0.3, 0.3)))
        if b.get("stamp"):
            self.stamp(img, b["stamp"], lt - b.get("stamp_at", 0.6))
        return img

    def label(self, d, lab, a):
        if a <= 0:
            return
        title, sub = (lab + [""])[:2]
        y = TOP_SAFE + 250
        w = max(d.textlength(title, font=font("sans_b", 34)) + 5 * len(title), d.textlength(sub, font=font("serif_i", 36))) + 70
        d.rectangle((50, y, 50 + w, y + 120), fill=(10, 10, 9, int(200 * a)))
        d.rectangle((50, y, 57, y + 120), fill=GOLD + (int(255 * a),))
        tracked(d, (82, y + 18), title, font("sans_b", 34), PAPER + (int(255 * a),), 5)
        d.text((82, y + 66), sub, font=font("serif_i", 36), fill=mix(PAPER, INK, 0.2) + (int(255 * a),))

    def stamp(self, img, text, lt):
        a = clamp(lt / 0.2)
        if a <= 0:
            return
        f = font("sans_b", 110)
        tw = int(ImageDraw.Draw(img).textlength(text, font=f)) + 80
        st = Image.new("RGBA", (tw, 200), (0, 0, 0, 0))
        sd = ImageDraw.Draw(st)
        sd.rounded_rectangle((8, 8, tw - 8, 192), 18, outline=RED + (int(255 * a),), width=10)
        sd.text((tw / 2, 100), text, font=f, fill=RED + (int(255 * a),), anchor="mm")
        st = st.rotate(-10, expand=True, resample=Image.BICUBIC)
        s = lerp(1.35, 1.0, ease_out(clamp(lt / 0.25))) * min(1.0, (VW - 120) / st.width)
        st = st.resize((int(st.width * s), int(st.height * s)))
        img.paste(st, (VW // 2 - st.width // 2, int(VH * 0.46) - st.height // 2), st)

    def overlay_ui(self, img, t):
        d = BlendDraw(img)
        # hook, first ~3 s
        a = 1 - fade(t, 2.9, 0.4)
        if a > 0 and self.spec.get("hook"):
            d.rectangle((0, 0, VW, TOP_SAFE + 210), fill=(8, 8, 7, int(150 * a)))
            y = TOP_SAFE - 20
            for line in self.spec["hook"].split("\n"):
                d.text((VW / 2, y), line, font=font("serif_b", 78), fill=GOLD + (int(255 * a),), anchor="ma")
                y += 90
        # captions: current chunk, current word in gold
        for text, s, e in self.chunks:
            if s - 0.05 <= t < e:
                words = text.split()
                wt = [w for w in self.words if s - 0.01 <= w["s"] < e]
                f = font("sans_b", 74)
                lines = wrap(d, text, f, VW - 140)
                y = CAP_Y
                k = 0
                for line in lines:
                    lw = d.textlength(line, font=f)
                    x = VW / 2 - lw / 2
                    for word in line.split():
                        cur = k < len(wt) and wt[k]["s"] <= t
                        nxt = k + 1 < len(wt) and wt[k + 1]["s"] <= t
                        col = GOLD if (cur and not nxt) else (255, 255, 255)
                        d.text((x, y), word, font=f, fill=col, stroke_width=6, stroke_fill=(0, 0, 0))
                        x += d.textlength(word + " ", font=f)
                        k += 1
                    y += 92
                break
        # channel tag
        tracked(d, (VW / 2, VH - 300), "THE HISTORY BETWEEN", font("sans_b", 24), (255, 255, 255, 150), 10, "ma")
        return img

    def frame(self, t):
        k = next(i for i, b in enumerate(self.beats) if t < b["end"] or i == len(self.beats) - 1)
        b = self.beats[k]
        img = self.draw_beat(b, t)
        xf = 0.25
        if k > 0 and t - b["start"] < xf and b["type"] != "flash" and self.beats[k - 1]["type"] != "flash":
            prev = self.draw_beat(self.beats[k - 1], t)
            img = Image.blend(prev, img, ease((t - b["start"]) / xf))
        if t > self.total - 0.5:
            img = darken(img, ease((t - (self.total - 0.5)) / 0.5))
        return self.overlay_ui(img, t)

    def render(self, out=None):
        out = out or os.path.join(self.build, "short.mp4")
        tmp = out + ".video.mp4"
        n = int(self.total * FPS)
        ff = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
                               "-s", f"{VW}x{VH}", "-r", str(FPS), "-i", "-",
                               "-vf", "noise=alls=4,vignette=angle=PI/5", "-c:v", "libx264", "-preset", "veryfast",
                               "-crf", "20", "-pix_fmt", "yuv420p", tmp], stdin=subprocess.PIPE)
        for f in range(n):
            ff.stdin.write(self.frame(f / FPS).tobytes())
        ff.stdin.close()
        ff.wait()
        music = self.spec.get("music")
        mux(tmp, self.p(self.spec["voice"]), self.p(music) if music else None, out, self.total,
            self.spec.get("music_offset", 0.0), self.spec.get("music_gain", 0.6))
        os.remove(tmp)
        print(f"{out}: {self.total:.1f}s")
        return out


def main():
    s = Short(sys.argv[1])
    if "--stills" in sys.argv:
        for ts in map(float, sys.argv[sys.argv.index("--stills") + 1:]):
            s.frame(ts).save(os.path.join(s.build, f"still_{ts:05.1f}.jpg"), quality=85)
        for b in s.beats:
            print(f"{b['start']:6.2f}-{b['end']:6.2f} {b['type']:6} {b['at']}")
        return
    s.render()


if __name__ == "__main__":
    main()
