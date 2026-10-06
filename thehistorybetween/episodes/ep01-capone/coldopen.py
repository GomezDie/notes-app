"""Ep. 1 cold open: "2122 North Clark Street" (~1:55).

    python3 coldopen.py stills 3 20 60 ...   # preview frames at given seconds
    python3 coldopen.py render               # full 1080p render -> build/
"""
import json
import math
import os
import sys

from PIL import Image, ImageDraw, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "pipeline"))
from gfx import (BLUE, DIM, GOLD, H, INK, INK2, PAPER, RED, W, WATER, Ctx,  # noqa: E402
                 KenBurns, build_schedule, canvas, clamp, darken, ease, ease_out, fade,
                 font, lerp, make_music, mix, overlay, render, tracked, typewriter)

A = os.path.join(HERE, "assets")
B = os.path.join(HERE, "build")
STREET = os.path.join(A, "img01_street.png")


def grade_cold(img):
    return Image.blend(img, Image.new("RGB", img.size, (20, 26, 34)), 0.12)


street = KenBurns(STREET, z0=1.0, z1=1.18, x0=0.5, x1=0.55, y0=0.55, y1=0.6, grade=grade_cold)
street_dark = KenBurns(STREET, z0=1.1, z1=1.25, x0=0.45, x1=0.5, y0=0.5, y1=0.5,
                       grade=lambda im: im.filter(ImageFilter.GaussianBlur(6)))


# ---------------------------------------------------------------- 0-1 street
def s_street(c):
    img = street.frame(c.lt / (c.dur + 1.5))
    k = 1 - fade(c.t, 0.0, 1.2)  # fade up from black
    if k > 0:
        img = darken(img, k)

    def stamp(d, _):
        a = c.on(1, 0.4)
        if a <= 0:
            return
        d.rectangle((90, 820, 720, 990), fill=(10, 10, 9, int(200 * a)))
        d.rectangle((90, 820, 96, 990), fill=RED + (int(255 * a),))
        prog = clamp(c.since(1) / 1.6)
        lines = ["CHICAGO, ILLINOIS", "THURSDAY, FEBRUARY 14, 1929", "10:30 A.M."]
        total = sum(len(l) for l in lines)
        shown, y = int(total * prog), 845
        for i, l in enumerate(lines):
            part = l[:max(0, shown)]
            shown -= len(l)
            f = font("mono_b", 40) if i == 1 else font("mono", 30)
            d.text((125, y), part, font=f, fill=PAPER if i == 1 else mix(PAPER, INK, 0.3))
            y += 52 if i == 1 else 46
    return overlay(img, stamp)


# ---------------------------------------------------------------- 2-8 map
SHORE = [(2.0, -4), (1.4, -2.5), (0.95, -1.2), (0.75, 0), (0.95, 0.75), (0.55, 1.1), (0.25, 1.8),
         (-0.15, 2.7), (-0.45, 3.6), (-0.75, 4.6), (-0.95, 5.6), (-1.1, 7)]
CLARK = [(-0.35, -1.2), (-0.35, 0.6), (-0.6, 1.6), (-0.85, 2.65), (-1.1, 3.5), (-1.35, 4.3), (-1.55, 5.4)]
RIVER = [(0.85, 0.32), (-0.45, 0.32), (-0.55, 0.9), (-0.8, 1.5), (-1.1, 2.1)]
PIN = (-0.85, 2.65)
LP = [(-0.55, 1.55), (0.45, 1.5), (0.25, 1.8), (-0.15, 2.7), (-0.45, 3.6), (-0.75, 4.6),
      (-1.2, 4.5), (-0.95, 3.6), (-0.7, 2.65)]


def polyline_point(pts, p):
    """Point at fraction p of a polyline's length."""
    segs = [math.dist(a, b) for a, b in zip(pts, pts[1:])]
    target, acc = sum(segs) * clamp(p), 0
    for (a, b), L in zip(zip(pts, pts[1:]), segs):
        if acc + L >= target:
            u = (target - acc) / L
            return (lerp(a[0], b[0], u), lerp(a[1], b[1], u)), pts[:pts.index(a) + 1]
        acc += L
    return pts[-1], pts


def clark_to_pin(p):
    """Route along Clark up to the garage."""
    route = CLARK[:3] + [PIN]
    return polyline_point(route, p)


def s_map(c):
    z = ease((c.t - c.s(5)) / 1.6)
    cx, cy = lerp(-0.4, -0.75, z), lerp(1.4, 2.6, z)
    sc = lerp(150, 430, z)

    def P(pt):
        return (W / 2 + (pt[0] - cx) * sc, H / 2 - (pt[1] - cy) * sc)

    img = canvas()
    d = ImageDraw.Draw(img)
    # street grid every half mile
    g = (40, 36, 30)
    for i in range(-20, 21):
        x = i * 0.5
        d.line([P((x, -6)), P((x, 9))], fill=g, width=1 if i % 2 else 2)
        d.line([P((-8, x)), P((6, x))], fill=g, width=1 if i % 2 else 2)
    # park, lake, river
    d.polygon([P(p) for p in LP], fill=(30, 38, 28))
    lake = SHORE + [(9, 9), (9, -9)]
    d.polygon([P(p) for p in lake], fill=WATER)
    d.line([P(p) for p in SHORE], fill=(70, 95, 115), width=3)
    d.line([P(p) for p in RIVER], fill=(55, 80, 100), width=max(3, int(sc / 40)))
    d.line([P(p) for p in CLARK], fill=(120, 110, 92), width=max(4, int(sc / 30)))
    # labels
    lf = font("sans_b", 22 if z < 0.5 else 26)
    tracked(d, P((2.3, 1.2)), "LAKE MICHIGAN", lf, (90, 120, 145), 6, "ma")
    tracked(d, P((0.15, -0.55)), "THE LOOP", lf, DIM, 4, "ma")
    tracked(d, P((-0.35, 3.15)), "LINCOLN PARK", lf, (110, 130, 100), 4, "ma")
    lx, ly = P((-1.3, 3.7))
    tracked(d, (lx - 30, ly), "N. CLARK ST.", lf, PAPER, 4, "ra")

    # the Cadillac travelling north
    p = clamp((c.t - c.s(2) - 0.3) / (c.s(5) - c.s(2) + 0.3))
    pos, passed = clark_to_pin(ease(p))
    trail = [P(q) for q in passed] + [P(pos)]
    if len(trail) > 1:
        d.line(trail, fill=GOLD, width=5)
    x, y = P(pos)
    d.ellipse((x - 11, y - 11, x + 11, y + 11), fill=PAPER, outline=GOLD, width=4)

    def cards(d2, _):
        # spec card: what the car looks like
        a = c.on(3, 0.5) * (1 - c.on(5, 0.4))
        if a > 0:
            x0, y0 = 120, 690
            d2.rounded_rectangle((x0, y0, x0 + 560, y0 + 250), 14, fill=INK2 + (int(235 * a),))
            d2.text((x0 + 30, y0 + 24), "THE CAR", font=font("sans_b", 22), fill=GOLD + (int(255 * a),))
            d2.text((x0 + 30, y0 + 60), "Black Cadillac touring car", font=font("serif_b", 34),
                    fill=PAPER + (int(255 * a),))
            for i, item in enumerate(["siren", "gong", "gun rack"]):
                ai = a * c.on(3, 0.3, offset=0.35 * i)
                d2.text((x0 + 30 + i * 170, y0 + 120), "\u2022 " + item,
                        font=font("sans", 28), fill=PAPER + (int(255 * ai),))
            ap = a * c.on(4, 0.4)
            d2.rounded_rectangle((x0 + 30, y0 + 175, x0 + 400, y0 + 225), 8, fill=BLUE + (int(255 * ap),))
            d2.text((x0 + 46, y0 + 186), "LOOKS LIKE: POLICE CAR", font=font("sans_b", 24),
                    fill=(255, 255, 255, int(255 * ap)))
        # pin + garage label
        a = c.on(5, 0.5, offset=1.2)
        if a > 0:
            px, py = P(PIN)
            r = 16 + 40 * ((c.t * 0.8) % 1)
            d2.ellipse((px - r, py - r, px + r, py + r), outline=RED + (int(160 * a * (1 - (c.t * 0.8) % 1)),), width=3)
            d2.ellipse((px - 14, py - 14, px + 14, py + 14), fill=RED + (int(255 * a),))
            bx, by = px + 40, py - 120
            d2.rounded_rectangle((bx, by, bx + 520, by + 160), 10, fill=INK2 + (int(240 * a),))
            d2.text((bx + 22, by + 14), "2122 N. CLARK STREET", font=font("sans_b", 22), fill=GOLD + (int(255 * a),))
            sign = "S.M.C. CARTAGE CO."
            d2.text((bx + 22, by + 46), typewriter(sign, (c.t - c.s(6)) / 0.9),
                    font=font("mono_b", 32), fill=PAPER + (int(255 * a),))
            # "moving & storage" ... struck through
            a2 = c.on(6, 0.4, offset=1.0)
            if a2 > 0:
                tx, ty = bx + 22, by + 110
                d2.text((tx, ty), "moving & storage", font=font("serif_i", 30), fill=PAPER + (int(220 * a2),))
                s = clamp((c.t - c.s(7)) / 0.5)
                if s > 0:
                    w = d2.textlength("moving & storage", font=font("serif_i", 30))
                    d2.line((tx - 6, ty + 20, tx - 6 + (w + 12) * s, ty + 20), fill=RED + (255,), width=5)
        # dossier
        a = c.on(8, 0.6)
        if a > 0:
            x0 = lerp(-640, 60, ease_out(a))
            y0 = 250
            d2.rounded_rectangle((x0, y0, x0 + 600, y0 + 560), 16, fill=(18, 16, 14, 245),
                                 outline=GOLD + (200,), width=2)
            d2.text((x0 + 36, y0 + 34), "DOSSIER", font=font("mono_b", 22), fill=RED + (255,))
            d2.text((x0 + 36, y0 + 72), "The North Side Gang", font=font("serif_b", 46), fill=PAPER + (255,))
            rows = [("BOSS", "George “Bugs” Moran"), ("TURF", "Chicago’s North Side"),
                    ("BUSINESS", "Bootleg liquor"), ("STANDING IN THE WAY OF", "?")]
            y = y0 + 160
            for k, (key, val) in enumerate(rows):
                ak = clamp((c.t - c.s(8) - 0.5 - k * 0.6) / 0.4)
                d2.text((x0 + 36, y), key, font=font("sans_b", 20), fill=DIM + (int(255 * ak),))
                d2.text((x0 + 36, y + 28), val, font=font("serif", 34 if val != "?" else 64),
                        fill=(GOLD if val == "?" else PAPER) + (int(255 * ak),))
                y += 92
    return overlay(img, cards)


# ---------------------------------------------------------------- 9-10 four men
def person(d, x, y, s, color, cap=False, a=255):
    d.ellipse((x - 26 * s, y - 150 * s, x + 26 * s, y - 98 * s), fill=color + (a,))
    d.rounded_rectangle((x - 40 * s, y - 90 * s, x + 40 * s, y + 60 * s), int(18 * s), fill=color + (a,))
    if cap:
        d.rectangle((x - 30 * s, y - 160 * s, x + 30 * s, y - 138 * s), fill=(30, 50, 80, a))
        d.rectangle((x - 36 * s, y - 140 * s, x + 36 * s, y - 132 * s), fill=(20, 30, 50, a))
    else:  # fedora
        d.rectangle((x - 22 * s, y - 166 * s, x + 22 * s, y - 140 * s), fill=(55, 50, 44, a))
        d.rectangle((x - 40 * s, y - 142 * s, x + 40 * s, y - 134 * s), fill=(55, 50, 44, a))


def s_men(c):
    img = canvas()

    def draw(d, _):
        tracked(d, (W / 2, 160), "OUT OF THE CAR", font("sans_b", 28), GOLD, 8, "ma")
        for k in range(4):
            a = clamp((c.lt - 0.2 - k * 0.25) / 0.4)
            police = k in (1, 2)
            col = mix((120, 112, 100), BLUE, c.on(10, 0.5)) if police else (120, 112, 100)
            x = W / 2 + (k - 1.5) * 240
            person(d, x, 640 + (1 - ease(a)) * 40, 1.6, col, cap=police and c.since(10) > 0, a=int(255 * a))
        a = c.on(10, 0.5, offset=0.3)
        if a > 0:
            d.line((W / 2 - 330, 820, W / 2 + 330, 820), fill=BLUE + (int(255 * a),), width=3)
            tracked(d, (W / 2, 850), "2 IN POLICE UNIFORM", font("sans_b", 36), PAPER + (int(255 * a),), 6, "ma")
    return overlay(img, draw)


# ---------------------------------------------------------------- 11-17 floor plan
MEN_START = [(620, 560), (700, 470), (820, 600), (900, 500), (980, 640), (560, 680), (760, 700)]
MEN_WALL = [(520 + k * 85, 330) for k in range(7)]


def s_plan(c):
    img = canvas()

    def draw(d, _):
        x0, y0, x1, y1 = 380, 260, 1540, 860
        d.rectangle((x0, y0, x1, y1), outline=PAPER, width=6)
        d.line((1240, y1, 1420, y1), fill=INK, width=10)  # door gap
        d.text((1330, y1 + 20), "DOOR", font=font("sans_b", 22), fill=DIM, anchor="ma")
        tracked(d, (x0, y0 - 60), "2122 N. CLARK ST. — FLOOR PLAN (SIMPLIFIED)", font("sans_b", 22), DIM, 4)
        d.text((x0 + 10, y0 - 30), "BACK WALL", font=font("sans_b", 18), fill=GOLD)
        d.rounded_rectangle((1180, 330, 1460, 520), 10, outline=DIM, width=3)
        d.text((1320, 425), "TRUCK", font=font("sans_b", 26), fill=DIM, anchor="mm")
        # seven men
        line_up = ease((c.t - c.s(16)) / (c.s(18) - c.s(16) - 0.6))
        for k, (s, e) in enumerate(zip(MEN_START, MEN_WALL)):
            a = clamp((c.lt - 0.3 - k * 0.15) / 0.3)
            wob = 6 * math.sin(c.t * 1.3 + k) * (1 - line_up)
            x, y = lerp(s[0], e[0], line_up) + wob, lerp(s[1], e[1], line_up)
            d.ellipse((x - 22, y - 22, x + 22, y + 22), fill=PAPER + (int(255 * a),))
        a = c.on(11, 0.4, offset=0.6)
        d.text((x0 + 30, y1 - 70), "7 MEN INSIDE", font=font("sans_b", 32), fill=PAPER + (int(255 * a),))
        # four arrivals at the door
        a = c.on(12, 0.6)
        if a > 0:
            for k in range(4):
                x = 1270 + k * 45
                y = lerp(y1 + 60, y1 - 90, ease(a))
                col = BLUE if k in (1, 2) else (120, 112, 100)
                d.ellipse((x - 18, y - 18, x + 18, y + 18), fill=col + (int(255 * a),))
        # side notes
        notes = [(13, "PROHIBITION, 1920–1933: raids were routine"), (14, "→ usually a fine"),
                 (15, "→ maybe a bribe")]
        # side notes appear in a strip under the plan
        strip = [n for n in notes if c.t >= c.s(n[0])]
        if strip:
            a = (1 - c.on(17, 0.5))
            txt = "   ".join(t for _, t in strip)
            d.text((W / 2, 950), txt, font=font("serif_i", 34), fill=PAPER + (int(255 * a),), anchor="ma")
        a = c.on(17, 0.5)
        if a > 0:
            d.text((W / 2, 950), "Facing the wall.", font=font("serif_i", 40), fill=GOLD + (int(255 * a),), anchor="ma")
    return overlay(img, draw)


# ---------------------------------------------------------------- 18-21 gunfire
def s_fire(c):
    img = Image.new("RGBA", (W, H), (6, 6, 5, 255))
    # two short, dim red pulses (kept gentle for photosensitive viewers)
    pulse = max(0.0, 1 - abs(c.since(18) - 0.15) / 0.15) * 0.35 + max(0.0, 1 - abs(c.since(18) - 0.55) / 0.15) * 0.2
    if pulse > 0:
        img = Image.blend(img, Image.new("RGBA", (W, H), RED + (255,)), pulse * 0.5)

    def draw(d, _):
        lines = [(19, "2 × THOMPSON SUBMACHINE GUNS"), (20, "2 × SHOTGUNS")]
        for k, (si, txt) in enumerate(lines):
            a = c.on(si, 0.25)
            tracked(d, (W / 2, 300 + k * 110), txt, font("sans_b", 58), PAPER + (int(255 * a),), 6, "ma")
        a = c.on(21, 0.2)
        if a > 0:
            n = int(70 * ease_out(clamp(c.since(21) / 1.4)))
            tracked(d, (W / 2, 560), f"≈ {n}", font("serif_b", 200), RED + (int(255 * a),), 4, "ma")
            tracked(d, (W / 2, 800), "ROUNDS FIRED IN SECONDS", font("sans_b", 34), DIM + (int(255 * a),), 8, "ma")
    return overlay(img, draw)


# ---------------------------------------------------------------- 22-25, 27 roster
VICTIMS = [("Peter Gusenberg", ""), ("Albert Kachellek", "alias James Clark"), ("Adam Heyer", ""),
           ("Albert Weinshank", ""), ("Reinhardt Schwimmer", "optometrist"), ("John May", "mechanic"),
           ("Frank Gusenberg", "")]


def s_roster(c):
    img = canvas()

    def draw(d, _):
        tracked(d, (W / 2, 120), "THE SEVEN MEN IN THE GARAGE", font("sans_b", 28), GOLD, 8, "ma")
        x0, y = 560, 220
        for k, (name, note) in enumerate(VICTIMS):
            a = clamp((c.lt - k * 0.12) / 0.3)
            frank = k == 6
            col = GOLD if frank and c.t >= c.s(23) and c.t < c.s(27) + 1.2 else PAPER
            d.text((x0, y), name, font=font("serif_b", 50), fill=col + (int(255 * a),))
            if note:
                d.text((x0 + d.textlength(name, font=font("serif_b", 50)) + 24, y + 18), note,
                       font=font("serif_i", 28), fill=DIM + (int(255 * a),))
            w = d.textlength(name, font=font("serif_b", 50))
            strike_t = c.s(22) + 0.4 + k * 0.22 if not frank else c.s(27) + 0.6
            s = clamp((c.t - strike_t) / 0.3)
            if s > 0:
                d.line((x0 - 10, y + 32, x0 - 10 + (w + 20) * s, y + 32), fill=RED, width=6)
            if frank:
                a1 = c.on(23, 0.4) * (1 - clamp((c.t - c.s(27) - 0.4) / 0.4))
                tag = "STILL ALIVE"
                if c.t >= c.s(24):
                    tag = "STILL ALIVE · 14 BULLETS"
                d.text((x0 + w + 30, y + 14), tag, font=font("sans_b", 30), fill=GOLD + (int(255 * a1),))
                a2 = c.on(27, 0.4, offset=0.8)
                d.text((x0 + w + 30, y + 14), "DIED ~3 HOURS LATER", font=font("sans_b", 30),
                       fill=RED + (int(255 * a2),))
            y += 92
        a = c.on(25, 0.5) * (1 - c.on(27, 0.3)) if c.t < c.s(27) else 0
        if a > 0:
            d.text((W / 2, 900), "Detective: “Who shot you?”", font=font("serif_i", 40),
                   fill=PAPER + (int(255 * a),), anchor="ma")
    return overlay(img, draw)


# ---------------------------------------------------------------- 26 quote
def s_quote(c):
    img = Image.new("RGBA", (W, H), (8, 8, 7, 255))

    def draw(d, _):
        a = fade(c.lt, 0.1, 0.5)
        d.text((W / 2, 430), "“Nobody shot me.”", font=font("serif_i", 140), fill=PAPER + (int(255 * a),), anchor="mm")
        a2 = fade(c.lt, 0.8, 0.5)
        d.line((W / 2 - 60, 580, W / 2 + 60, 580), fill=RED + (int(255 * a2),), width=4)
        tracked(d, (W / 2, 620), "FRANK GUSENBERG · FEBRUARY 14, 1929", font("sans_b", 28), DIM + (int(255 * a2),), 6, "ma")
    return overlay(img, draw)


# ---------------------------------------------------------------- 28-29 alibi
def geo(lat, lon):
    x = (lon + 87.63) * math.cos(math.radians(34)) * 40 + 700
    y = (41.88 - lat) * 40 + 210
    return x, y


def s_alibi(c):
    img = canvas()

    def draw(d, _):
        for lat in range(24, 46, 2):  # graticule
            d.line([geo(lat, -95), geo(lat, -74)], fill=(36, 33, 28), width=1)
        for lon in range(-95, -73, 2):
            d.line([geo(46, lon), geo(24, lon)], fill=(36, 33, 28), width=1)
        chi, mia = geo(41.88, -87.63), geo(25.79, -80.13)
        p = ease(clamp((c.lt - 0.4) / 2.2))
        ctrl = (chi[0] + 380, (chi[1] + mia[1]) / 2 - 60)
        pts = []
        for i in range(int(60 * p) + 1):
            u = i / 60
            pts.append(((1 - u) ** 2 * chi[0] + 2 * (1 - u) * u * ctrl[0] + u * u * mia[0],
                        (1 - u) ** 2 * chi[1] + 2 * (1 - u) * u * ctrl[1] + u * u * mia[1]))
        if len(pts) > 1:
            d.line(pts, fill=GOLD, width=4)
        for (x, y), name, sub, col in [(chi, "CHICAGO", "the massacre", RED), (mia, "MIAMI BEACH", "Capone’s estate", GOLD)]:
            d.ellipse((x - 14, y - 14, x + 14, y + 14), fill=col)
            d.text((x - 30, y - 18), name, font=font("sans_b", 36), fill=PAPER, anchor="ra")
            d.text((x - 30, y + 26), sub, font=font("serif_i", 28), fill=DIM, anchor="ra")
        a = fade(c.lt, 2.4, 0.5)
        d.text((ctrl[0] + 40, ctrl[1] + 20), "≈ 1,200 MILES", font=font("sans_b", 44), fill=PAPER + (int(255 * a),))
        a = c.on(29, 0.25)
        if a > 0:
            stamp = Image.new("RGBA", (560, 200), (0, 0, 0, 0))
            sd = ImageDraw.Draw(stamp)
            sd.rounded_rectangle((10, 10, 550, 190), 18, outline=RED + (int(255 * a),), width=10)
            sd.text((280, 100), "ALIBI", font=font("sans_b", 120), fill=RED + (int(255 * a),), anchor="mm")
            stamp = stamp.rotate(-12, expand=True, resample=Image.BICUBIC)
            s = lerp(1.4, 1.0, ease_out(clamp(c.since(29) / 0.3)))
            stamp = stamp.resize((int(stamp.width * s), int(stamp.height * s)))
            _.paste(stamp, (1420 - stamp.width // 2, 800 - stamp.height // 2), stamp)
    return overlay(img, draw)


# ---------------------------------------------------------------- 30-31 name
def s_name(c):
    img = darken(street_dark.frame(c.p), 0.82)

    def draw(d, _):
        tracked(d, (W / 2, 330), "HIS NAME IS", font("sans_b", 28), GOLD, 10, "ma")
        name = "ALPHONSE CAPONE"
        shown = typewriter(name, (c.lt - 0.3) / 1.0)
        tracked(d, (W / 2, 400), shown, font("serif_b", 140), PAPER, 10, "ma")
        a = c.on(31, 0.5)
        if a > 0:
            tracked(d, (W / 2, 620), "AGE 30  ·  “SCARFACE”  ·  CHICAGO", font("sans_b", 36),
                    PAPER + (int(255 * a),), 8, "ma")
            a2 = c.on(31, 0.5, offset=1.6)
            d.text((W / 2, 720), "the most famous gangster in America", font=font("serif_i", 46),
                   fill=GOLD + (int(255 * a2),), anchor="ma")
    return overlay(img, draw)


# ---------------------------------------------------------------- 32 headlines
HEADLINES = ["7 SLAIN IN GANG MASSACRE", "KILLERS POSED AS POLICE", "“WAR” ON CHICAGO GANGS DEMANDED"]


def s_headlines(c):
    img = canvas()

    def draw(d, layer):
        for k, text in enumerate(HEADLINES):
            a = clamp((c.lt - 0.2 - k * 0.55) / 0.3)
            if a <= 0:
                continue
            card = Image.new("RGBA", (1200, 300), (0, 0, 0, 0))
            cd = ImageDraw.Draw(card)
            cd.rectangle((0, 0, 1200, 300), fill=(226, 216, 192, 255))
            cd.rectangle((24, 24, 1176, 30), fill=(40, 36, 30, 255))
            cd.text((600, 46), "EXTRA · FEBRUARY 1929", font=font("serif", 30), fill=(40, 36, 30), anchor="ma")
            cd.rectangle((24, 92, 1176, 96), fill=(40, 36, 30, 255))
            cd.text((600, 190), text, font=font("serif_b", 62), fill=(20, 18, 15), anchor="mm")
            card = card.rotate([-4, 3, -1.5][k], expand=True, resample=Image.BICUBIC)
            s = lerp(1.25, 1.0, ease_out(a))
            card = card.resize((int(card.width * s), int(card.height * s)))
            pos = (W // 2 - card.width // 2 + [-120, 110, 0][k], 120 + k * 250 - card.height // 2 + 150)
            layer.paste(card, (max(0, pos[0]), max(0, pos[1])), card)
        tracked(d, (W / 2, 1010), "ILLUSTRATIVE HEADLINES", font("sans", 18), DIM, 6, "ma")
    return overlay(img, draw)


# ---------------------------------------------------------------- 33 question
def s_question(c):
    img = canvas()

    def draw(d, _):
        lines = ["How do you catch a man", "who never pulls the trigger?"]
        reveal = clamp((c.t - c.s(33) - 2.4) / 2.6)
        a1 = clamp(reveal * 2)
        a2 = clamp(reveal * 2 - 1)
        d.text((W / 2, 410), lines[0], font=font("serif", 92), fill=PAPER + (int(255 * a1),), anchor="mm")
        d.text((W / 2, 540), lines[1], font=font("serif_b", 92), fill=PAPER + (int(255 * a2),), anchor="mm")
        u = clamp((c.t - c.s(33) - 5.6) / 0.6)
        if u > 0:
            w = d.textlength(lines[1], font=font("serif_b", 92))
            d.line((W / 2 - w / 2, 610, W / 2 - w / 2 + w * u, 610), fill=RED, width=6)
        a0 = 1 - reveal
        tracked(d, (W / 2, 300), "THE QUESTION", font("sans_b", 30), GOLD + (int(255 * a0),), 10, "ma")
    return overlay(img, draw)


# ---------------------------------------------------------------- 34 answer
def s_answer(c):
    img = canvas()

    def draw(d, _):
        tracked(d, (300, 200), "IT WILL TAKE", font("sans_b", 30), GOLD, 10, "la")
        dur = c.timing[34]["end"] - c.s(34)
        items = [(0.12, "a Treasury agent"), (0.30, "a nervous bookkeeper"), (0.50, "a few forgotten ledgers"),
                 (0.68, None)]
        for k, (frac, txt) in enumerate(items):
            a = clamp((c.t - c.s(34) - dur * frac) / 0.4)
            y = 290 + k * 150
            d.text((300, y), f"{k + 1:02d}", font=font("mono_b", 40), fill=DIM + (int(255 * a),))
            if txt:
                d.text((420, y - 14), txt, font=font("serif", 76), fill=PAPER + (int(255 * a),))
            else:
                d.text((420, y - 14), "the most boring crime in", font=font("serif", 76), fill=PAPER + (int(255 * a),))
                d.text((420, y + 72), "the American legal code:", font=font("serif", 76), fill=PAPER + (int(255 * a),))
                bx = 420 + d.textlength("the American legal code: ", font=font("serif", 76))
                d.rectangle((bx, y + 82, bx + 470, y + 158), fill=RED + (int(255 * a),))
                tracked(d, (bx + 235, y + 96), "REDACTED", font("mono_b", 34), INK + (int(255 * a),), 8, "ma")
    return overlay(img, draw)


# ---------------------------------------------------------------- 35 title
def s_title(c):
    img = darken(street.frame(0.6 + 0.4 * c.p), lerp(0.55, 0.78, c.p))

    def draw(d, _):
        a = fade(c.lt, 0.4, 0.8)
        tracked(d, (W / 2, 360), "THE HUNT FOR", font("sans_b", 46), GOLD + (int(255 * a),), 22, "ma")
        a2 = fade(c.lt, 0.9, 0.9)
        tracked(d, (W / 2, 430), "AL CAPONE", font("serif_b", 210), PAPER + (int(255 * a2),), 14, "ma")
        a3 = fade(c.lt, 2.4, 0.8)
        d.line((W / 2 - 80, 700, W / 2 + 80, 700), fill=RED + (int(255 * a3),), width=4)
        tracked(d, (W / 2, 730), "THEHISTORYBETWEEN", font("sans_b", 26), DIM + (int(255 * a3),), 12, "ma")
    img = overlay(img, draw)
    out = max(0.0, (c.lt - (c.dur - 1.2)) / 1.2)  # fade to black at the very end
    return darken(img, ease(out)) if out > 0 else img


SCENES = [(0, s_street), (2, s_map), (9, s_men), (11, s_plan), (18, s_fire), (22, s_roster),
          (26, s_quote), (27, s_roster), (28, s_alibi), (30, s_name), (32, s_headlines),
          (33, s_question), (34, s_answer), (35, s_title)]


def main():
    os.makedirs(B, exist_ok=True)
    timing_path = os.path.join(A, "timing.json")
    voice = os.path.join(A, "vo_take1.mp3")
    if sys.argv[1:2] == ["stills"]:
        timing = json.load(open(timing_path))["sentences"]
        total = json.load(open(timing_path))["duration"] + 3.5
        sched = build_schedule(SCENES, timing, total)
        for ts in map(float, sys.argv[2:]):
            a, b, fn = next(s for s in sched if ts < s[1])
            fn(Ctx(timing, ts, a, b)).convert("RGB").save(os.path.join(B, f"still_{ts:06.2f}.jpg"), quality=85)
        return
    music = os.path.join(B, "music_bed.wav")
    dur = json.load(open(timing_path))["duration"] + 3.5
    make_music(music, dur)
    render(SCENES, timing_path, voice, music, os.path.join(B, "ep01_coldopen_1080p.mp4"),
           srt_path=os.path.join(B, "ep01_coldopen.srt"))


if __name__ == "__main__":
    main()
