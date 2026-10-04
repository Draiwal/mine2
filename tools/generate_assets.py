#!/usr/bin/env python3
"""Генерирует 3D-модели (JSON-кубоиды), текстуры, скины, звуки (.ogg), рецепты и lang для мода.
Запуск:  python3 tools/generate_assets.py   (нужны Pillow, numpy, scipy, ffmpeg с libvorbis)."""
import os, json, math, subprocess, tempfile, random
import numpy as np
from PIL import Image, ImageDraw
from scipy import signal
from scipy.io import wavfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RES = f'{ROOT}/src/main/resources'
A = f'{RES}/assets/gtacombat'
D = f'{RES}/data/gtacombat'
for p in ('models/item', 'textures/item', 'sounds', 'lang'):
    os.makedirs(f'{A}/{p}', exist_ok=True)
os.makedirs(f'{D}/recipes', exist_ok=True)

# ============================================================ ТЕКСТУРЫ-ПАЛИТРЫ (скины)
# 16x16, сетка 4x4 ячеек по 4px. Индекс ячейки = цвет детали (см. CELL_*)
C_FRAME, C_SLIDE, C_GRIP, C_DARK, C_ACCENT, C_LIGHT, C_GLASS, C_LASER, C_WOOD = range(9)
SKINS = [
    # 0 Classic Black
    [(62,64,70),(44,46,52),(34,34,38),(22,22,25),(190,40,40),(150,155,165),(60,130,210),(255,40,40),(98,66,42)],
    # 1 Desert Tan
    [(176,150,110),(196,170,125),(108,88,60),(58,48,38),(235,235,235),(205,195,175),(70,140,220),(255,60,40),(124,88,52)],
    # 2 Gold Plated
    [(214,176,56),(236,198,72),(28,28,30),(64,52,20),(255,246,170),(255,232,125),(90,165,255),(255,60,40),(84,52,32)],
    # 3 Urban Camo
    [(74,88,62),(92,106,76),(48,56,40),(28,32,26),(210,210,200),(150,160,150),(70,140,210),(255,50,40),(88,62,40)],
]
rnd = random.Random(42)
for si, pal in enumerate(SKINS):
    img = Image.new('RGBA', (16, 16), (128, 128, 128, 255))
    for idx in range(16):
        base = pal[idx] if idx < len(pal) else (128, 128, 128)
        cx, cy = (idx % 4) * 4, (idx // 4) * 4
        for x in range(4):
            for y in range(4):
                n = rnd.randint(-6, 6)
                col = tuple(max(0, min(255, c + n)) for c in base)
                if si == 3 and idx in (C_FRAME, C_SLIDE) and rnd.random() < 0.3:   # камуфляж
                    col = rnd.choice([(52, 64, 44), (110, 120, 88), (70, 78, 56)])
                img.putpixel((cx + x, cy + y), col + (255,))
    img.save(f'{A}/textures/item/palette_{si}.png')

def uvcell(c):
    x, y = (c % 4) * 4, (c // 4) * 4
    return [x + 1, y + 1, x + 3, y + 3]

def element(part):
    x0, y0, z0, x1, y1, z1, c = part
    face = {"uv": uvcell(c), "texture": "#p"}
    return {"from": [x0, y0, z0], "to": [x1, y1, z1],
            "faces": {k: dict(face) for k in ("north", "south", "east", "west", "up", "down")}}

# ============================================================ ДИЗАЙН ОРУЖИЯ
# Координаты "дизайна": рукоять в точке (8,8,8), ствол смотрит в -Z, верх = +Y.
P = lambda *a: tuple(a)
GUNS = {
 'pistol': dict(view=0.8, muzzle=(10.7, -1), top=(12.8, 1.5, 9.5), under=(7.8, 2.0), mag=(7.1, 8.9, 2.5, 8.4, 11.2), parts=[
    P(7,9.5,0,9,12,11.5,C_SLIDE), P(7.6,10.2,-1,8.4,11.3,0,C_DARK), P(7.2,7.8,1.5,8.8,9.5,10.5,C_FRAME),
    P(7.1,5,7.8,8.9,7.8,10.8,C_GRIP), P(7.1,2.5,8.4,8.9,5,11.2,C_GRIP), P(7.6,7,4.5,8.4,7.8,7.8,C_DARK),
    P(7.8,6.2,6,8.2,7.4,6.6,C_DARK), P(7.5,12,10,8.5,12.8,11.3,C_DARK), P(7.7,12,0.3,8.3,12.7,1.3,C_DARK),
    P(6.9,10,3,7,11.5,9,C_ACCENT), P(9,10,3,9.1,11.5,9,C_ACCENT)]),
 'revolver': dict(view=0.8, muzzle=(10.4, -5), top=(12.6, 1, 8), under=(9.6, -2), mag=(7.1, 8.9, 2.5, 9.5, 12.3), parts=[
    P(7.4,9.6,-5,8.6,11.2,6,C_DARK), P(7.7,11.2,-5,8.3,11.8,5,C_ACCENT), P(7.1,8.5,5,8.9,11.5,9.5,C_FRAME),
    P(6.9,8.8,2.5,9.1,11.4,6,C_LIGHT), P(7.1,4.5,8.5,8.9,8.5,11,C_WOOD), P(7.1,2.5,9.5,8.9,4.5,12.3,C_WOOD),
    P(7.7,11.5,9.2,8.3,12.6,10.2,C_DARK), P(7.6,6.8,6.2,8.4,8.5,8.6,C_DARK), P(7.7,11.8,-4.8,8.3,12.5,-4.2,C_DARK)]),
 'smg': dict(view=0.6, muzzle=(10.1, -8), top=(12.2, -1, 8), under=(8, -3), mag=(7.3, 8.7, 1, 1.8, 4.2), parts=[
    P(7,8,-2,9,11.5,10,C_FRAME), P(7.6,9.5,-8,8.4,10.7,-2,C_DARK), P(7.2,9,-6,8.8,11,-2,C_SLIDE),
    P(7.5,11.5,-2,8.5,12.2,9,C_DARK), P(7.4,9,10,8.6,10.5,16,C_DARK), P(7.1,3.5,7,8.9,8,9.8,C_GRIP),
    P(7.1,2.5,7.6,8.9,3.5,10.4,C_GRIP), P(7.3,1,1.8,8.7,8,4.2,C_DARK), P(7.3,6.5,-1,8.7,8,2,C_GRIP),
    P(7.8,11.5,-7.5,8.2,12.4,-7,C_DARK), P(7.7,12.2,8,8.3,12.9,8.8,C_DARK), P(6.9,9,-5,7,10.5,0,C_ACCENT)]),
 'rifle': dict(view=0.42, muzzle=(10.2, -14), top=(12.3, -6, 9), under=(8.4, -6), mag=(7.3, 8.7, 3, 3, 6.5), parts=[
    P(7,8,0,9,11.5,12,C_FRAME), P(7.1,8.4,-8,8.9,11,0,C_SLIDE), P(7.6,9.6,-12,8.4,10.8,-8,C_DARK),
    P(7.3,9.3,-14,8.7,11,-12,C_DARK), P(7.5,11.5,-8,8.5,12.3,11,C_DARK), P(7.2,6.5,12,8.8,10.5,20,C_GRIP),
    P(7,6,19.6,9,10.8,21,C_DARK), P(7.2,4,8.5,8.8,8,10.5,C_GRIP), P(7.3,3,3,8.7,8,6.5,C_DARK),
    P(7.8,11.5,-13,8.2,12.8,-12.6,C_DARK), P(7.6,12.3,9,8.4,13,10,C_DARK), P(6.95,9,-7,7.1,10.4,-1,C_ACCENT)]),
 'shotgun': dict(view=0.42, muzzle=(10.5, -16), top=(11.5, 3, 9), under=(8.8, -10), mag=(7.5, 8.5, 8.8, -16, -12), parts=[
    P(7.5,10,-16,8.5,11,2,C_DARK), P(7.5,8.8,-12,8.5,9.8,2,C_DARK), P(7.2,8.4,-8,8.8,10.2,-2,C_WOOD),
    P(7,8,2,9,11.5,10,C_FRAME), P(7.2,6.5,10,8.8,10.5,19,C_WOOD), P(7,6,18.8,9,10.8,20,C_DARK),
    P(7.8,11,-15,8.2,11.8,-14.6,C_DARK), P(7.3,6.8,4,8.7,8,7.5,C_DARK)]),
 'sniper': dict(view=0.36, muzzle=(10.1, -17), top=None, under=(8.2, -8), mag=(7.4, 8.6, 5.5, 4, 8), parts=[
    P(7.1,8.2,0,8.9,11.2,12,C_FRAME), P(7.6,9.6,-15,8.4,10.6,0,C_DARK), P(7.4,9.4,-11,8.6,10.8,-4,C_SLIDE),
    P(7.3,9.2,-17,8.7,11,-15,C_DARK), P(7.2,5.5,12,8.8,10.6,22,C_GRIP), P(7.3,10.6,13,8.7,11.4,19,C_GRIP),
    P(7,5.2,21.5,9,10.8,22.8,C_DARK), P(7.2,4,8.5,8.8,8.2,10.5,C_GRIP), P(8.9,9.8,6,10.4,10.6,7,C_LIGHT),
    P(10.2,9.4,5.8,11,11,7.2,C_DARK), P(7.4,5.5,4,8.6,8.2,8,C_DARK), P(7.2,5.5,-12,7.6,8.8,-11.4,C_DARK),
    P(8.4,5.5,-12,8.8,8.8,-11.4,C_DARK),
    # встроенный прицел
    P(7.3,11.4,1,8.7,12.8,11,C_DARK), P(7.35,11.5,0.8,8.65,12.7,1,C_GLASS), P(7.35,11.5,11,8.65,12.7,11.2,C_GLASS),
    P(7.6,11.2,3,8.4,11.4,9,C_DARK), P(7.8,12.8,5.4,8.2,13.4,6.6,C_DARK)]),
}

def attachments(g, mask):
    out = []
    my, mz = g['muzzle']
    if mask & 1:    # глушитель
        out += [P(7.1, my-0.9, mz-6, 8.9, my+0.9, mz, C_DARK), P(6.95, my-1.05, mz-1.2, 9.05, my+1.05, mz-0.4, C_LIGHT),
                P(6.95, my-1.05, mz-3.4, 9.05, my+1.05, mz-2.6, C_LIGHT), P(6.95, my-1.05, mz-5.6, 9.05, my+1.05, mz-4.8, C_LIGHT)]
    if mask & 2:    # расширенный магазин
        x0, x1, yb, z0, z1 = g['mag']
        out += [P(x0, yb-2.6, z0, x1, yb, z1, C_DARK), P(x0-0.1, yb-3.0, z0-0.1, x1+0.1, yb-2.6, z1+0.1, C_ACCENT)]
    if mask & 4 and g['top']:   # прицел
        ty, z0, z1 = g['top']; mid = (z0+z1)/2
        out += [P(7.6, ty, z0+1, 8.4, ty+0.9, z1-1, C_DARK), P(7.3, ty+0.9, z0, 8.7, ty+2.4, z1, C_DARK),
                P(7.35, ty+1.0, z0-0.25, 8.65, ty+2.3, z0, C_GLASS), P(7.35, ty+1.0, z1, 8.65, ty+2.3, z1+0.25, C_GLASS),
                P(7.8, ty+2.4, mid-0.6, 8.2, ty+3.0, mid+0.6, C_LIGHT)]
    if mask & 8:    # рукоять
        uy, uz = g['under']
        out += [P(7.5, uy-3.2, uz, 8.5, uy, uz+1.6, C_GRIP), P(7.4, uy-3.6, uz+0.2, 8.6, uy-3.2, uz+1.8, C_DARK)]
    return out

def bbox(parts):
    return (min(p[0] for p in parts), min(p[1] for p in parts), min(p[2] for p in parts),
            max(p[3] for p in parts), max(p[4] for p in parts), max(p[5] for p in parts))

def rot_xyz(rx, ry, rz):
    rx, ry, rz = map(math.radians, (rx, ry, rz))
    Rx = np.array([[1,0,0],[0,math.cos(rx),-math.sin(rx)],[0,math.sin(rx),math.cos(rx)]])
    Ry = np.array([[math.cos(ry),0,math.sin(ry)],[0,1,0],[-math.sin(ry),0,math.cos(ry)]])
    Rz = np.array([[math.cos(rz),-math.sin(rz),0],[math.sin(rz),math.cos(rz),0],[0,0,1]])
    return Rz @ Ry @ Rx

def build_display(g, dz):
    allp = g['parts']
    x0, y0, z0, x1, y1, z1 = bbox(allp)
    L = z1 - z0
    s_fp = g['view']
    s_tp = max(0.4, min(0.8, 16 / L))
    # GUI: повернуть боком и отцентровать
    rx, ry = 22, -72
    s_gui = min(1.3, 21 / L)
    R = rot_xyz(rx, ry, 0)
    c = np.array([(x0+x1)/2 - 8, (y0+y1)/2 - 8, (z0+z1)/2 - 8 + dz]) * s_gui
    t_gui = (-(R @ c)).tolist()
    # ground / fixed: тоже центрируем (в единицах 1/16 блока)
    c2 = np.array([(x0+x1)/2 - 8, (y0+y1)/2 - 8, (z0+z1)/2 - 8 + dz]) * 0.5
    Rf = rot_xyz(0, -90, 0)
    t_fix = (-(Rf @ c2)).tolist()
    return {
        "firstperson_righthand": {"rotation": [0,0,0], "translation": [0,0,-s_fp*dz], "scale": [s_fp]*3},
        "firstperson_lefthand":  {"rotation": [0,0,0], "translation": [0,0,-s_fp*dz], "scale": [s_fp]*3},
        "thirdperson_righthand": {"rotation": [0,0,0], "translation": [0,0,-s_tp*dz], "scale": [s_tp]*3},
        "thirdperson_lefthand":  {"rotation": [0,0,0], "translation": [0,0,-s_tp*dz], "scale": [s_tp]*3},
        "gui":    {"rotation": [rx, ry, 0], "translation": [round(v,3) for v in t_gui], "scale": [s_gui]*3},
        "ground": {"rotation": [0,0,0], "translation": [0,2,0], "scale": [0.5]*3},
        "fixed":  {"rotation": [0,-90,0], "translation": [round(v,3) for v in t_fix], "scale": [0.5]*3},
    }

for name, g in GUNS.items():
    # dz: сдвиг по Z, чтобы все элементы влезли в допустимые -16..32 (для любой комбинации обвесов)
    minz = min(bbox(g['parts'] + attachments(g, m))[2] for m in range(16))
    maxz = max(bbox(g['parts'] + attachments(g, m))[5] for m in range(16))
    dz = max(0.0, -16 - minz + 0.5)
    assert maxz + dz <= 32, (name, maxz + dz)
    disp = build_display(g, dz)
    overrides = []
    for skin in range(4):
        for mask in range(16):
            n = skin * 16 + mask
            parts = g['parts'] + attachments(g, mask)
            els = []
            for (x0,y0,z0,x1,y1,z1,c) in parts:
                els.append(element((x0,y0,z0+dz,x1,y1,z1+dz,c)))
            model = {"textures": {"p": f"gtacombat:item/palette_{skin}", "particle": f"gtacombat:item/palette_{skin}"},
                     "elements": els, "display": disp}
            fn = f'{name}.json' if n == 0 else f'{name}_{n}.json'
            if n == 0:
                model["overrides"] = overrides
            json.dump(model, open(f'{A}/models/item/{fn}', 'w'))
            if n > 0:
                overrides.append({"predicate": {"custom_model_data": n}, "model": f"gtacombat:item/{name}_{n}"})

# ============================================================ ИКОНКИ (патроны, обвесы, вспышка)
def icon(fn, draw):
    img = Image.new('RGBA', (16, 16), (0, 0, 0, 0)); d = ImageDraw.Draw(img); draw(d); img.save(f'{A}/textures/item/{fn}.png')

def cart(body, tip, w=2):
    def f(d):
        for i in range(3):
            x = 3 + i * 4
            d.rectangle([x, 7, x + w, 13], fill=body); d.rectangle([x, 4, x + w, 6], fill=tip); d.rectangle([x, 13, x + w, 14], fill=(110, 80, 30))
    return f
icon('ammo_light', cart((218, 170, 60), (150, 150, 155)))
icon('ammo_rifle', cart((230, 190, 80), (90, 90, 95)))
def shell(d):
    for i in range(3):
        x = 2 + i * 4
        d.rectangle([x, 4, x + 2, 11], fill=(190, 45, 40)); d.rectangle([x, 11, x + 2, 13], fill=(215, 175, 60))
icon('ammo_shell', shell)
icon('att_suppressor', lambda d: (d.rectangle([2, 6, 14, 10], fill=(60, 62, 68)), [d.line([x, 6, x, 10], fill=(150, 155, 165)) for x in (5, 8, 11)]))
icon('att_ext_mag', lambda d: (d.rectangle([5, 1, 10, 14], fill=(52, 54, 60)), d.rectangle([5, 12, 10, 14], fill=(190, 40, 40)), d.line([6, 2, 6, 11], fill=(90, 92, 98))))
icon('att_scope', lambda d: (d.rectangle([2, 5, 14, 9], fill=(50, 52, 58)), d.rectangle([1, 5, 2, 9], fill=(60, 130, 210)), d.rectangle([14, 5, 15, 9], fill=(60, 130, 210)), d.rectangle([7, 3, 9, 5], fill=(150, 155, 165)), d.rectangle([6, 9, 10, 11], fill=(50, 52, 58))))
icon('att_grip', lambda d: (d.rectangle([6, 1, 10, 4], fill=(30, 30, 34)), d.rectangle([5, 4, 11, 13], fill=(44, 44, 50)), [d.line([5, y, 11, y], fill=(80, 80, 88)) for y in (6, 8, 10, 12)]))
def flash(d):
    d.polygon([(8,0),(10,6),(16,8),(10,10),(8,16),(6,10),(0,8),(6,6)], fill=(255,214,90,255))
    d.polygon([(8,3),(9,7),(13,8),(9,9),(8,13),(7,9),(3,8),(7,7)], fill=(255,250,215,255))
icon('muzzle_flash', flash)

M = f'{A}/models/item'
for n in ('ammo_light', 'ammo_rifle', 'ammo_shell', 'muzzle_flash'):
    json.dump({"parent": "minecraft:item/generated", "textures": {"layer0": f"gtacombat:item/{n}"}}, open(f'{M}/{n}.json', 'w'))
for n in ('suppressor', 'ext_mag', 'scope', 'grip'):
    json.dump({"parent": "minecraft:item/generated", "textures": {"layer0": f"gtacombat:item/att_{n}"}}, open(f'{M}/att_{n}.json', 'w'))

# ============================================================ ЗВУКИ (синтез)
SR = 44100
rng = np.random.default_rng(7)
def env(n, a, dec):
    t = np.arange(n) / SR; e = np.exp(-t / dec); k = int(a * SR)
    if k > 0: e[:k] *= np.linspace(0, 1, k)
    return e
def noise(n): return rng.standard_normal(n)
def lp(x, fc): b, a = signal.butter(2, min(fc, SR/2-100) / (SR/2), 'low'); return signal.lfilter(b, a, x)
def hp(x, fc): b, a = signal.butter(2, fc / (SR/2), 'high'); return signal.lfilter(b, a, x)
def bp(x, lo, hi): b, a = signal.butter(2, [lo/(SR/2), hi/(SR/2)], 'band'); return signal.lfilter(b, a, x)
def reverb(x, wet, delays=(0.023, 0.041, 0.067, 0.097, 0.131), fb=0.55):
    y = x.copy()
    for i, d in enumerate(delays):
        n = int(d * SR); t = np.zeros_like(x); t[n:] += x[:-n] * fb ** (i + 1); y += t * wet * 2
    return y
def norm(x, peak=0.9):
    x = x - np.mean(x); return x / (np.max(np.abs(x)) + 1e-9) * peak
def save(name, x):
    x = np.clip(norm(x), -1, 1)
    with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as f: tmp = f.name
    wavfile.write(tmp, SR, (x * 32767).astype(np.int16))
    subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-i', tmp, '-ac', '1', '-ar', '44100', '-c:a', 'libvorbis', '-q:a', '4',
                    f'{A}/sounds/{name}.ogg'], check=True)
    os.remove(tmp)

def gunshot(dur, thump, crack_fc, body_fc, decay, tail):
    n = int(dur * SR); t = np.arange(n) / SR; nz = noise(n)
    crack = hp(nz, crack_fc) * env(n, 0.0004, 0.010)
    body = lp(nz, body_fc) * env(n, 0.001, decay)
    ph = 2 * np.pi * np.cumsum(thump * np.exp(-t * 28) + thump * 0.35) / SR
    boom = np.sin(ph) * env(n, 0.001, decay * 1.6)
    x = np.tanh((crack * 0.9 + body * 1.0 + boom * 1.3) * 2.2)
    return reverb(x, tail)

SHOTS = {  # dur, thump, crack_fc, body_fc, decay, tail
    'pistol': (0.5, 140, 2600, 4500, 0.055, 0.22), 'revolver': (0.9, 85, 1800, 3500, 0.11, 0.38),
    'smg': (0.32, 170, 3000, 5200, 0.032, 0.18), 'rifle': (0.6, 110, 2200, 4200, 0.065, 0.32),
    'shotgun': (0.85, 65, 1500, 3000, 0.12, 0.42), 'sniper': (1.6, 55, 1200, 2600, 0.19, 0.65)}
for gname, prm in SHOTS.items():
    for v in (1, 2): save(f'shot_{gname}_{v}', gunshot(*prm))
for v in (1, 2):    # глушитель
    n = int(0.3 * SR); x = lp(noise(n), 2200) * env(n, 0.002, 0.03) * 0.6
    x[: int(0.01*SR)] += hp(noise(int(0.01*SR)), 3000) * 0.5
    t = np.arange(n) / SR; x += np.sin(2*np.pi*600*t) * env(n, 0.001, 0.012) * 0.25
    save(f'shot_silenced_{v}', reverb(x, 0.08))

def click(res=(1800, 3400), dec=0.02, amp=1.0, n=int(0.15 * SR)):
    t = np.arange(n) / SR; x = hp(noise(n), 900) * env(n, 0.0002, 0.004)
    ring = sum(np.sin(2*np.pi*f*t) * env(n, 0.0002, dec) for f in res) * 0.35
    return (x + ring) * amp
def thud(n=int(0.15 * SR), fc=900, dec=0.03): return lp(noise(n), fc) * env(n, 0.0005, dec)
def seq(total, ev):
    out = np.zeros(int(total * SR))
    for t0, s in ev:
        i = int(t0 * SR); m = min(len(s), len(out) - i); out[i:i+m] += s[:m]
    return out
save('mag_out', seq(0.4, [(0, click((1200, 2600))), (0.09, thud(fc=700, dec=0.05) * 0.8)]))
save('mag_in',  seq(0.35, [(0, thud(fc=1100, dec=0.03) * 1.1), (0.045, click((2000, 3800), amp=0.8))]))
rack = bp(noise(int(0.12*SR)), 1500, 5000) * env(int(0.12*SR), 0.01, 0.05) * 0.35
save('slide', seq(0.45, [(0, click((1500, 3000), amp=0.9)), (0.01, rack), (0.14, click((2200, 4200), amp=1.1)), (0.15, thud(fc=1500, dec=0.02) * 0.5)]))
save('dry', seq(0.2, [(0, click((2400, 4400), dec=0.015, amp=1.0))]))
save('equip', seq(0.35, [(0, click((1600, 2800), amp=0.7)), (0.05, bp(noise(int(0.18*SR)), 800, 3000) * env(int(0.18*SR), 0.03, 0.06) * 0.3), (0.2, click((2200, 3600), amp=0.6))]))

def ping(freqs, dur=0.18, dec=0.04):
    n = int(dur * SR); t = np.arange(n) / SR
    return sum(np.sin(2*np.pi*f*t) * env(n, 0.0005, dec) for f in freqs)
save('hit', ping((1700, 2550), 0.12, 0.025))
save('headshot', seq(0.3, [(0, ping((2400, 3600, 1200), 0.15, 0.035)), (0.07, ping((3200, 4800), 0.2, 0.05) * 0.9)]))
save('kill', seq(0.45, [(0, ping((1000, 1500, 2000), 0.4, 0.12))]))

sounds = {}
for g in SHOTS: sounds[f'shot_{g}'] = [f'shot_{g}_1', f'shot_{g}_2']
sounds['shot_silenced'] = ['shot_silenced_1', 'shot_silenced_2']
for n in ('mag_out', 'mag_in', 'slide', 'dry', 'equip', 'hit', 'headshot', 'kill'): sounds[n] = [n]
sj = {}
for ev, files in sounds.items():
    dist = 24 if 'silenced' in ev else (96 if ev.startswith('shot_') else 16)
    sj[ev] = {"sounds": [{"name": f"gtacombat:{f}", "attenuation_distance": dist} for f in files]}
json.dump(sj, open(f'{A}/sounds.json', 'w'), indent=1)

# ============================================================ LANG
GN = {'pistol': ('Pistol', 'Пистолет'), 'revolver': ('Heavy Revolver', 'Тяжёлый револьвер'), 'smg': ('Micro SMG', 'Микро-ПП'),
      'rifle': ('Assault Rifle', 'Штурмовая винтовка'), 'shotgun': ('Pump Shotgun', 'Помповый дробовик'), 'sniper': ('Sniper Rifle', 'Снайперская винтовка')}
en = {"itemGroup.gtacombat": "GTA Combat", "item.gtacombat.ammo_light": "Light Ammo", "item.gtacombat.ammo_rifle": "Rifle Ammo",
      "item.gtacombat.ammo_shell": "Shotgun Shells", "item.gtacombat.att_suppressor": "Suppressor", "item.gtacombat.att_ext_mag": "Extended Magazine",
      "item.gtacombat.att_scope": "Scope", "item.gtacombat.att_grip": "Foregrip", "item.gtacombat.muzzle_flash": "Muzzle Flash",
      "skin.gtacombat.0": "Skin: Classic Black", "skin.gtacombat.1": "Skin: Desert Tan", "skin.gtacombat.2": "Skin: Gold Plated", "skin.gtacombat.3": "Skin: Urban Camo",
      "key.categories.gtacombat": "GTA Combat", "key.gtacombat.reload": "Reload", "key.gtacombat.wheel": "Weapon wheel (hold)",
      "key.gtacombat.attach": "Attach (offhand) / Detach (Shift)", "key.gtacombat.skin": "Cycle weapon skin",
      "hud.gtacombat.reloading": "RELOADING...", "hud.gtacombat.no_ammo": "No ammo",
      "hud.gtacombat.attach_hint": "Hold an attachment in your offhand", "hud.gtacombat.attached": "Attachment installed"}
ru = {"itemGroup.gtacombat": "GTA Combat", "item.gtacombat.ammo_light": "Лёгкие патроны", "item.gtacombat.ammo_rifle": "Винтовочные патроны",
      "item.gtacombat.ammo_shell": "Дробь", "item.gtacombat.att_suppressor": "Глушитель", "item.gtacombat.att_ext_mag": "Расширенный магазин",
      "item.gtacombat.att_scope": "Оптический прицел", "item.gtacombat.att_grip": "Тактическая рукоять", "item.gtacombat.muzzle_flash": "Вспышка выстрела",
      "skin.gtacombat.0": "Скин: Классика", "skin.gtacombat.1": "Скин: Пустыня", "skin.gtacombat.2": "Скин: Золото", "skin.gtacombat.3": "Скин: Городской камуфляж",
      "key.categories.gtacombat": "GTA Combat", "key.gtacombat.reload": "Перезарядка", "key.gtacombat.wheel": "Колесо оружия (удерживать)",
      "key.gtacombat.attach": "Установить (обвес в левой руке) / Снять (Shift)", "key.gtacombat.skin": "Сменить скин оружия",
      "hud.gtacombat.reloading": "ПЕРЕЗАРЯДКА...", "hud.gtacombat.no_ammo": "Нет патронов",
      "hud.gtacombat.attach_hint": "Возьмите обвес в левую руку", "hud.gtacombat.attached": "Обвес установлен"}
for k, (e, r) in GN.items(): en[f'item.gtacombat.{k}'] = e; ru[f'item.gtacombat.{k}'] = r
json.dump(en, open(f'{A}/lang/en_us.json', 'w'), indent=1, ensure_ascii=False)
json.dump(ru, open(f'{A}/lang/ru_ru.json', 'w'), indent=1, ensure_ascii=False)

# ============================================================ РЕЦЕПТЫ
def shaped(name, pattern, key, result, count=1):
    json.dump({"type": "minecraft:crafting_shaped", "pattern": pattern, "key": {k: {"item": v} for k, v in key.items()},
               "result": {"item": f"gtacombat:{result}", "count": count}}, open(f'{D}/recipes/{name}.json', 'w'), indent=1)
def shapeless(name, items, result, count):
    json.dump({"type": "minecraft:crafting_shapeless", "ingredients": [{"item": i} for i in items],
               "result": {"item": f"gtacombat:{result}", "count": count}}, open(f'{D}/recipes/{name}.json', 'w'), indent=1)
I, R, S, G, Dm = 'minecraft:iron_ingot', 'minecraft:redstone', 'minecraft:stick', 'minecraft:gold_ingot', 'minecraft:diamond'
shapeless('ammo_light', ['minecraft:gunpowder', 'minecraft:iron_nugget', 'minecraft:iron_nugget'], 'ammo_light', 8)
shapeless('ammo_rifle', ['minecraft:gunpowder', 'minecraft:gunpowder', I], 'ammo_rifle', 6)
shapeless('ammo_shell', ['minecraft:gunpowder', 'minecraft:paper', 'minecraft:iron_nugget', 'minecraft:iron_nugget'], 'ammo_shell', 4)
shaped('pistol', ['II ', 'IRI', ' S '][:3], {'I': I, 'R': R, 'S': S}, 'pistol')
shaped('revolver', ['III', 'IRG', ' S '], {'I': I, 'R': R, 'G': G, 'S': S}, 'revolver')
shaped('smg', ['IIR', 'III', ' I '], {'I': I, 'R': R}, 'smg')
shaped('rifle', ['IIR', 'III', 'S I'], {'I': I, 'R': R, 'S': S}, 'rifle')
shaped('shotgun', ['III', 'S R', 'S  '], {'I': I, 'R': R, 'S': S}, 'shotgun')
shaped('sniper', ['  D', 'III', 'S R'], {'I': I, 'D': Dm, 'R': R, 'S': S}, 'sniper')
shaped('att_suppressor', ['III', 'I I', 'III'], {'I': I}, 'att_suppressor')
shaped('att_ext_mag', ['I I', 'IRI', 'III'], {'I': I, 'R': R}, 'att_ext_mag')
shaped('att_scope', ['IGI', 'DDD', 'IGI'][:3], {'I': I, 'G': 'minecraft:glass_pane', 'D': 'minecraft:copper_ingot'}, 'att_scope')
shaped('att_grip', [' I ', ' I ', 'SIS'], {'I': I, 'S': S}, 'att_grip')
print('assets generated')
