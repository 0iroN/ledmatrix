"""Ek GIF'ler (22.10): akvaryum, fırtına, dönen Dünya, kedi, DNA sarmalı, atom.
gif_uret.GIFLER'e kendini ekler. Hepsi kendi 32x16 piksel çizimimiz."""
import math
import random

from PIL import Image

W, H = 32, 16


def _akvaryum(n=64, seed=31):
    """Yüzen balıklar, yükselen kabarcıklar, dipte sallanan yosun."""
    rnd = random.Random(seed)
    baliklar = [(rnd.randint(2, 11), rnd.choice((1, -1)), c, rnd.uniform(0, 6))
                for c in ((255, 140, 0), (255, 220, 0), (255, 60, 120), (80, 200, 255))]
    kabarcik = [(rnd.randrange(W), rnd.uniform(0, 1)) for _ in range(6)]
    kareler = []
    for t in range(n):
        p = t / n * 2 * math.pi
        im = Image.new("RGB", (W, H), (0, 10, 40))
        for x in range(W):                                   # kum
            im.putpixel((x, 15), (150, 120, 60))
        for x0 in (3, 9, 24, 29):                            # yosun
            for y in range(10, 15):
                sx = x0 + round(math.sin(p * 2 + y * 0.8 + x0) * 0.8 * (15 - y) / 5)
                im.putpixel((sx % W, y), (30, 160, 50))
        for y, yon, renk, faz in baliklar:                   # n karede bir tur yüzer
            x = (faz * 5 + yon * t * (W + 6) / n) % (W + 6) - 3
            yy = y + round(math.sin(p * 2 + faz))
            for dx, c in ((0, renk), (yon, renk), (-yon, renk), (-2 * yon, tuple(v // 2 for v in renk))):
                xi = round(x) + dx
                if 0 <= xi < W:
                    im.putpixel((xi, yy), c)
            gx = round(x) + yon                              # göz
            if 0 <= gx < W:
                im.putpixel((gx, yy), (255, 255, 255))
        for x, faz in kabarcik:
            y = 14 - int(((faz + t / n * 2) % 1) * 15)
            im.putpixel(((x + round(math.sin(p * 3 + faz * 7))) % W, y), (170, 220, 255))
        kareler.append(im)
    return kareler


def _firtina(n=48, seed=32):
    """Koyu bulutlardan eğik yağmur, ara ara ekranı aydınlatan şimşek."""
    rnd = random.Random(seed)
    damla = [(rnd.randrange(W + 8), rnd.uniform(0, 1)) for _ in range(30)]
    simsek = {12: 1.0, 13: 0.5, 30: 0.8, 31: 1.0, 32: 0.4}
    yol = [(20, 3)]
    while yol[-1][1] < 15:
        x, y = yol[-1]
        yol.append((x + rnd.choice((-1, 0, 1)), y + 1))
    kareler = []
    for t in range(n):
        f = simsek.get(t, 0.0)
        im = Image.new("RGB", (W, H), tuple(int(v * f) for v in (60, 60, 90)))
        for y in range(3):                                   # bulutlar
            for x in range(W):
                if (x * 3 + y * 5) % 7 < 5:
                    im.putpixel((x, y), (70 + int(120 * f), 70 + int(120 * f), 85 + int(120 * f)))
        for x0, faz in damla:                                # eğik yağmur, n karede 3 tur
            y = 3 + int(((faz + t / n * 3) % 1) * 13)
            x = (x0 - (y - 3) // 2) % W
            im.putpixel((x, y), (90, 140, 255))
        if f >= 0.8:
            for x, y in yol:
                if 0 <= x < W:
                    im.putpixel((x, y), (255, 255, 200))
        kareler.append(im)
    return kareler


def _donen_dunya(n=64):
    """Dönen Dünya: basit kıta haritası küreye sarılıp döner, sol tarafı gölgede."""
    harita = ["................................",
              "....##.........###......####....",
              "...####.......#####....######...",
              "..######......####....#######...",
              "...#####.......##......#####....",
              "....###........###......###.....",
              ".....##.......####.......#..##..",
              "......#........##..........###..",
              "...............#................",
              "................................"]
    kareler = []
    for t in range(n):
        im = Image.new("RGB", (W, H))
        for y in range(H):
            for x in range(W):
                dx, dy = (x - 15.5) / 7.5, (y - 7.5) / 7.5
                if dx * dx + dy * dy > 1:
                    continue
                dz = math.sqrt(max(0.0, 1 - dx * dx - dy * dy))
                lon = math.atan2(dx, dz) / math.pi * 0.5 + t / n          # dönüş
                lat = (dy + 1) / 2
                hx, hy = int((lon % 1) * 32), min(9, int(lat * 10))
                kara = harita[hy][hx] == "#"
                isik = max(0.25, min(1.0, 0.35 + 0.65 * (dx * 0.6 + dz * 0.8)))   # sağdan aydınlık
                c = (40, 170, 60) if kara else (20, 80, 220)
                if hy in (0, 9):
                    c = (230, 230, 240)                                     # kutuplar
                im.putpixel((x, y), tuple(int(v * isik) for v in c))
        kareler.append(im)
    return kareler


def _kedi(n=32):
    """Soldan sağa yürüyen kedi (2 adım karesi), kuyruğu sallanır, göz kırpar."""
    GOVDE = ["#...#....", "#####....", "#o#o#...#", "#####..#.", ".########", ".########", ".#.#..#.#"]
    GOVDE2 = ["#...#....", "#####....", "#o#o#...#", "#####..#.", ".########", ".########", "#.#..#.#."]
    kareler = []
    for t in range(n):
        im = Image.new("RGB", (W, H))
        for x in range(W):
            im.putpixel((x, 14), (60, 40, 25))
        sekil = GOVDE if (t // 2) % 2 == 0 else GOVDE2
        x0 = int(t / n * (W + 10)) - 10
        for gy, row in enumerate(sekil):
            for gx, c in enumerate(row[::-1]):               # sağa baksın diye çevir
                x, y = x0 + gx, 7 + gy
                if not (0 <= x < W and 0 <= y < 14) or c == ".":
                    continue
                if c == "o":
                    im.putpixel((x, y), (120, 255, 120) if t % 12 else (200, 130, 50))
                else:
                    im.putpixel((x, y), (200, 130, 50))
        kareler.append(im)
    return kareler


def _dna(n=40):
    """DNA çift sarmalı: iki iplik sinüs gibi döner, aralarında renkli baz basamakları."""
    BAZ = [(255, 80, 80), (80, 200, 255), (255, 210, 0), (120, 255, 120)]
    kareler = []
    for t in range(n):
        im = Image.new("RGB", (W, H))
        p = t / n * 2 * math.pi
        for x in range(W):
            a = x / W * 4 * math.pi + p
            y1, y2 = 7.5 + 5.5 * math.sin(a), 7.5 - 5.5 * math.sin(a)
            on1 = math.cos(a) > 0                            # öndeki iplik parlak
            if x % 3 == 0:
                for y in range(round(min(y1, y2)) + 1, round(max(y1, y2))):
                    im.putpixel((x, y), tuple(v // 2 for v in BAZ[(x // 3) % 4]))
            im.putpixel((x, round(y1)), (230, 230, 255) if on1 else (90, 90, 140))
            im.putpixel((x, round(y2)), (90, 90, 140) if on1 else (230, 230, 255))
        kareler.append(im)
    return kareler


def _yorunge_nokta(u, aci):
    """Kare uzayda a=7, b=2.2'lik elipsi aci kadar döndür, sonra yatayda 1.9 kat ger
    (32x16 ekranda yuvarlak görünsün). Önceki sürüm döndürmeyi gerilmiş uzayda yapıyordu,
    üç yörünge üst üste biniyordu."""
    x, y = 7 * math.cos(u), 2.2 * math.sin(u)
    return (x * math.cos(aci) - y * math.sin(aci)) * 1.9, x * math.sin(aci) + y * math.cos(aci)


def _atom(n=60):
    """Atom: ortada titreyen çekirdek, üç eğik yörüngede dönen elektronlar ve izleri."""
    kareler = []
    yorunge = [(0.0, 1), (math.pi / 3, 2), (2 * math.pi / 3, 1)]
    for t in range(n):
        im = Image.new("RGB", (W, H))
        p = t / n * 2 * math.pi
        for aci, hiz in yorunge:                             # yörünge çizgileri (sönük)
            for k in range(48):
                u = k / 48 * 2 * math.pi
                xr, yr = _yorunge_nokta(u, aci)
                xi, yi = round(15.5 + xr), round(7.5 + yr)
                if 0 <= xi < W and 0 <= yi < H:
                    im.putpixel((xi, yi), (30, 50, 90))
            for iz in range(4):                              # elektron + iz
                u = p * hiz - iz * 0.18
                xr, yr = _yorunge_nokta(u, aci)
                xi, yi = round(15.5 + xr), round(7.5 + yr)
                if 0 <= xi < W and 0 <= yi < H:
                    v = 1 - iz / 4
                    im.putpixel((xi, yi), (int(80 * v), int(220 * v), int(255 * v)))
        for dx, dy in ((0, 0), (1, 0), (0, 1), (1, 1)):     # çekirdek
            r = 200 + int(55 * math.sin(p * 4 + dx + dy))
            im.putpixel((15 + dx, 7 + dy), (r, 60, 40) if (dx + dy) % 2 else (r, 160, 40))
        kareler.append(im)
    return kareler


YENI = {
    "akvaryum.gif": (_akvaryum, 80),
    "firtina.gif": (_firtina, 80),
    "donen-dunya.gif": (_donen_dunya, 90),
    "kedi.gif": (_kedi, 110),
    "dna-sarmali.gif": (_dna, 70),
    "atom.gif": (_atom, 60),
}
