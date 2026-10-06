"""TheHistoryBetween motion-graphics engine.

Scenes are plain Python functions that draw one frame with Pillow. The engine
times them against narration sentences (see align.py), crossfades between
scenes, pipes raw frames to ffmpeg, then adds grain, vignette, narration,
music bed and subtitles.
"""
import functools
import json
import math
import os
import subprocess

from PIL import Image, ImageDraw, ImageFilter, ImageFont

W, H, FPS = 1920, 1080, 30

# --- brand -----------------------------------------------------------------
INK = (14, 13, 11)          # background
INK2 = (28, 25, 21)         # panels
PAPER = (233, 225, 207)     # primary text
DIM = (150, 140, 120)       # secondary text
GOLD = (201, 164, 92)       # accent
RED = (179, 38, 30)         # danger / emphasis
BLUE = (86, 120, 160)       # police / water
WATER = (24, 36, 48)

FONT_DIR = "/usr/share/fonts/truetype/liberation"
FONTS = {
    "serif": "LiberationSerif-Regular.ttf",
    "serif_b": "LiberationSerif-Bold.ttf",
    "serif_i": "LiberationSerif-Italic.ttf",
    "mono": "LiberationMono-Regular.ttf",
    "mono_b": "LiberationMono-Bold.ttf",
    "sans": "LiberationSans-Regular.ttf",
    "sans_b": "LiberationSans-Bold.ttf",
}


@functools.lru_cache(maxsize=None)
def font(name, size):
    return ImageFont.truetype(os.path.join(FONT_DIR, FONTS[name]), size)


# --- easing / timing ---------------------------------------------------------
def clamp(x, a=0.0, b=1.0):
    return max(a, min(b, x))


def lerp(a, b, t):
    return a + (b - a) * t


def ease(t):  # smoothstep-like ease in/out
    t = clamp(t)
    return t * t * (3 - 2 * t)


def ease_out(t):
    t = clamp(t)
    return 1 - (1 - t) ** 3


def fade(t, start, dur=0.5):
    """0 -> 1 between start and start+dur."""
    return ease((t - start) / dur)


def mix(c1, c2, t):
    return tuple(int(lerp(a, b, t)) for a, b in zip(c1, c2))


def alpha(c, a):
    return c + (int(255 * clamp(a)),)


# --- drawing helpers ---------------------------------------------------------
@functools.lru_cache(maxsize=None)
def background():
    """Near-black with a soft warm centre glow."""
    img = Image.new("RGB", (W // 8, H // 8), INK)
    px = img.load()
    for y in range(H // 8):
        for x in range(W // 8):
            d = math.hypot((x - W / 16) / (W / 16), (y - H / 16) / (H / 16))
            k = clamp(1 - d) * 0.6
            px[x, y] = mix(INK, (40, 34, 26), k)
    return img.resize((W, H), Image.BICUBIC)


def canvas():
    return background().copy().convert("RGBA")


def tracked(draw, xy, text, fnt, fill, tracking=0, anchor="la"):
    """Draw text with letter spacing. anchor: 'la' left, 'ma' centre, 'ra' right."""
    widths = [draw.textlength(ch, font=fnt) for ch in text]
    total = sum(widths) + tracking * (len(text) - 1)
    x, y = xy
    if anchor[0] == "m":
        x -= total / 2
    elif anchor[0] == "r":
        x -= total
    for ch, w in zip(text, widths):
        draw.text((x, y), ch, font=fnt, fill=fill, anchor="l" + anchor[1])
        x += w + tracking
    return total


def typewriter(text, progress):
    n = int(round(len(text) * clamp(progress)))
    return text[:n]


class BlendDraw:
    """ImageDraw wrapper whose text() honours the fill's alpha. Pillow blends
    RGBA shapes onto RGB images but draws text fully opaque."""

    def __init__(self, img):
        self.img = img
        self.d = ImageDraw.Draw(img, "RGBA")

    def __getattr__(self, name):
        return getattr(self.d, name)

    def text(self, xy, text, fill=None, font=None, anchor=None, **kw):
        a = fill[3] if fill is not None and len(fill) == 4 else 255
        if a <= 0 or not text:
            return
        if a >= 255:
            return self.d.text(xy, text, fill=fill[:3], font=font, anchor=anchor, **kw)
        x0, y0, x1, y1 = (int(v) for v in self.d.textbbox(xy, text, font=font, anchor=anchor))
        x0, y0 = x0 - 2, y0 - 2
        if x1 <= x0 or y1 <= y0:
            return
        mask = Image.new("L", (x1 - x0 + 4, y1 - y0 + 4), 0)
        ImageDraw.Draw(mask).text((xy[0] - x0, xy[1] - y0), text, fill=a, font=font, anchor=anchor, **kw)
        self.img.paste(fill[:3], (x0, y0, x0 + mask.width, y0 + mask.height), mask)


def overlay(base, draw_fn):
    """Run draw_fn(draw, image) on an RGB copy of base. The draw handle blends
    RGBA colours (text included), and image.paste(card, pos, card) composites
    pre-rendered RGBA cards."""
    img = base.convert("RGB")
    draw_fn(BlendDraw(img), img)
    return img


def wrap(draw, text, fnt, max_w):
    words, lines, cur = text.split(), [], ""
    for w in words:
        trial = (cur + " " + w).strip()
        if draw.textlength(trial, font=fnt) <= max_w:
            cur = trial
        else:
            lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


class KenBurns:
    """Slow push/pan over a still image, pre-scaled once for speed."""

    def __init__(self, path, z0=1.0, z1=1.12, x0=0.5, x1=0.5, y0=0.5, y1=0.5, grade=None):
        img = Image.open(path).convert("RGB")
        self.src = img.resize((int(W * 1.35), int(H * 1.35)), Image.LANCZOS)
        if grade:
            self.src = grade(self.src)
        self.z0, self.z1, self.x0, self.x1, self.y0, self.y1 = z0, z1, x0, x1, y0, y1

    def frame(self, p):
        p = ease(p)
        cw = self.src.width / lerp(self.z0, self.z1, p)
        ch = cw * H / W
        cx = lerp(self.x0, self.x1, p) * self.src.width
        cy = lerp(self.y0, self.y1, p) * self.src.height
        x = clamp(cx - cw / 2, 0, self.src.width - cw)
        y = clamp(cy - ch / 2, 0, self.src.height - ch)
        return self.src.resize((W, H), Image.BILINEAR, box=(x, y, x + cw, y + ch)).convert("RGBA")


def darken(img, k):
    return Image.blend(img.convert("RGB"), Image.new("RGB", img.size, INK), k).convert("RGBA")


# --- timeline / rendering -----------------------------------------------------
class Ctx:
    def __init__(self, timing, t, scene_start, scene_end):
        self.timing, self.t = timing, t
        self.lt = t - scene_start
        self.dur = scene_end - scene_start
        self.p = clamp(self.lt / max(self.dur, 0.01))

    def s(self, i):
        """Start time (global) of sentence i."""
        return self.timing[i]["start"]

    def since(self, i):
        return self.t - self.s(i)

    def on(self, i, dur=0.5, offset=0.0):
        """0->1 ease starting when sentence i starts."""
        return fade(self.t, self.s(i) + offset, dur)


def build_schedule(scenes, timing, total):
    """scenes: list of (first_sentence_index, draw_fn). Returns [(start, end, fn)]."""
    out = []
    for k, (si, fn) in enumerate(scenes):
        start = 0.0 if k == 0 else timing[si]["start"] - 0.25
        end = total if k == len(scenes) - 1 else timing[scenes[k + 1][0]]["start"] - 0.25
        out.append((start, end, fn))
    return out


def render(scenes, timing_path, audio_path, music_path, out_path, tail=3.5,
           xfade=0.35, srt_path=None, preview_every=None):
    timing = json.load(open(timing_path))["sentences"]
    audio_dur = json.load(open(timing_path))["duration"]
    total = audio_dur + tail
    sched = build_schedule(scenes, timing, total)
    nframes = int(total * FPS)
    tmp = out_path + ".video.mp4"
    ff = subprocess.Popen(
        ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
         "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
         "-vf", "noise=alls=5,vignette=angle=PI/5",
         "-c:v", "libx264", "-preset", "veryfast", "-crf", "19", "-pix_fmt", "yuv420p", tmp],
        stdin=subprocess.PIPE)
    for f in range(nframes):
        t = f / FPS
        k = next(i for i, (a, b, _) in enumerate(sched) if t < b or i == len(sched) - 1)
        a, b, fn = sched[k]
        img = fn(Ctx(timing, t, a, b))
        if k > 0 and t - a < xfade:  # crossfade from previous scene
            pa, pb, pfn = sched[k - 1]
            prev = pfn(Ctx(timing, t, pa, pb))
            img = Image.blend(prev.convert("RGB"), img.convert("RGB"), ease((t - a) / xfade))
        img = img.convert("RGB")
        if preview_every and f % preview_every == 0:
            img.save(f"{out_path}.f{f:05d}.jpg", quality=80)
        ff.stdin.write(img.tobytes())
        if f % (FPS * 10) == 0:
            print(f"  frame {f}/{nframes}", flush=True)
    ff.stdin.close()
    ff.wait()
    mux(tmp, audio_path, music_path, out_path, total)
    os.remove(tmp)
    if srt_path:
        write_srt(timing, srt_path)


def mux(video, voice, music, out, total):
    """Narration on top, music ducked underneath, loudness-normalised for YouTube."""
    inputs = ["-i", video, "-i", voice]
    if music:
        inputs += ["-i", music]
        fc = ("[1:a]aresample=48000,aformat=channel_layouts=stereo,apad,asplit[v][key];"
              "[2:a]aresample=48000,volume=0.9[m];"
              "[m][key]sidechaincompress=threshold=0.03:ratio=6:attack=20:release=400[duck];"
              "[duck][v]amix=inputs=2:duration=first:normalize=0,"
              f"atrim=0:{total:.2f},loudnorm=I=-14:TP=-1.5:LRA=11[a]")
    else:
        fc = f"[1:a]apad,atrim=0:{total:.2f},loudnorm=I=-14:TP=-1.5:LRA=11[a]"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", *inputs, "-filter_complex", fc,
                    "-map", "0:v", "-map", "[a]", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
                    "-shortest", out], check=True)


def srt_time(t):
    ms = int(round(t * 1000))
    return f"{ms // 3600000:02d}:{ms // 60000 % 60:02d}:{ms // 1000 % 60:02d},{ms % 1000:03d}"


def write_srt(timing, path, display=None):
    """display: optional list of on-screen caption strings (defaults to sentence text)."""
    with open(path, "w", encoding="utf-8") as f:
        for k, s in enumerate(timing):
            text = display[k] if display else s["text"]
            f.write(f"{k + 1}\n{srt_time(s['start'])} --> {srt_time(s['end'] + 0.15)}\n{text}\n\n")


def make_music(path, dur):
    """Placeholder ambient bed (low drone + filtered noise) until real music is licensed."""
    fc = (f"sine=f=73.42:d={dur},volume=0.35[a];"
          f"sine=f=110:d={dur},volume=0.18,tremolo=f=0.15:d=0.6[b];"
          f"sine=f=146.83:d={dur},volume=0.08,tremolo=f=0.11:d=0.8[c];"
          f"anoisesrc=c=brown:d={dur}:a=0.25,lowpass=f=180[n];"
          f"[a][b][c][n]amix=inputs=4:normalize=0,lowpass=f=900,"
          f"afade=t=in:d=3,afade=t=out:st={dur - 4}:d=4,volume=0.22")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-filter_complex", fc, "-t", str(dur), "-ar", "48000", "-ac", "2", path], check=True)
