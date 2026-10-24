"""Ek GIF'ler (21.10): mevsimlik, oyun ve film temaları. gif_uret.GIFLER'e kendini ekler.

Hepsi kendi piksel çizimimiz (32x16). Kullanım: python gif_uret.py  (bu modül otomatik yüklenir)
"""
import colorsys
import math
import random

from PIL import Image

import font5x7

W, H = 32, 16


def _kar_ve_ev(n=60, seed=21):
    """Kar yağışı: düşen kar taneleri, ışıkları yanan iki küçük ev, karla kaplı zemin."""
    rnd = random.Random(seed)
    taneler = [(rnd.randrange(W), rnd.uniform(0, 1), rnd.choice((1, 2))) for _ in range(26)]
    kareler = []
    for t in range(n):
        im = Image.new("RGB", (W, H), (0, 0, 18))
        for x in range(W):                                   # karlı zemin
            for y in (14, 15):
                im.putpixel((x, y), (200, 210, 230))
        for x0 in (4, 20):                                   # evler: çatı + gövde + sarı pencere
            for dy in range(3):
                for dx in range(-dy, dy + 1):
                    im.putpixel((x0 + 3 + dx, 8 + dy), (230, 230, 245))
            for y in range(11, 14):
                for x in range(x0, x0 + 7):
                    im.putpixel((x, y), (120, 60, 30))
            parla = 200 + int(55 * (0.5 + 0.5 * math.sin(t / n * 4 * math.pi + x0)))
            im.putpixel((x0 + 2, 12), (255, parla, 60))
            im.putpixel((x0 + 4, 12), (255, parla, 60))
        for x, faz, hiz in taneler:                          # hız 1/2 -> n karede tam tur
            y = int((faz * 16 + t * hiz * 16 / n * 2) % 16)
            xs = (x + int(math.sin(t / n * 2 * math.pi * 2 + faz * 6) * 1.2)) % W
            if y < 14:
                im.putpixel((xs, y), (255, 255, 255))
        kareler.append(im)
    return kareler


def _yilbasi_agaci(n=40, seed=22):
    """Yılbaşı ağacı: yanıp sönen renkli ışıklar, tepede parlayan yıldız, etrafta kar."""
    rnd = random.Random(seed)
    isiklar = [(rnd.uniform(0, 1), rnd.uniform(0, 1), rnd.randrange(4)) for _ in range(14)]
    RENK = [(255, 0, 0), (255, 200, 0), (0, 120, 255), (255, 0, 200)]
    kareler = []
    for t in range(n):
        im = Image.new("RGB", (W, H))
        for y in range(2, 14):                               # üçgen ağaç
            gen = (y - 1) // 2 + 1
            for x in range(16 - gen, 16 + gen):
                im.putpixel((x, y), (0, 120 + (x + y) % 3 * 25, 30))
        for y in (14, 15):                                   # gövde
            im.putpixel((15, y), (110, 60, 20))
            im.putpixel((16, y), (110, 60, 20))
        for fx, fy, r in isiklar:                            # ışıklar ağacın içinde
            y = 3 + int(fy * 10)
            gen = (y - 1) // 2 + 1
            x = 16 - gen + int(fx * (2 * gen - 1))
            if (t // 4 + r) % 3:
                im.putpixel((x, y), RENK[(r + t // 8) % 4])
        yildiz = (255, 230, 80) if t % 10 < 7 else (255, 255, 200)
        nokta = [(15, 0), (16, 0), (15, 1), (16, 1)] + ([(14, 1), (17, 1)] if t % 10 >= 7 else [])
        for x, y in nokta:                                   # tepede 2x2 yıldız, arada parıldar
            im.putpixel((x, y), yildiz)
        for x, y in ((3, 4), (8, 11), (26, 3), (29, 10), (5, 13), (24, 13)):
            if (t + x) % 6 < 4:
                im.putpixel((x, (y + t // 3) % 14), (230, 230, 255))
        kareler.append(im)
    return kareler


def _mutlu_yillar(seed=23):
    """Havai fişeklerin önünden kayan 'MUTLU YILLAR 2027' (kırmızı-altın)."""
    rnd = random.Random(seed)
    serit = font5x7.render("MUTLU YILLAR 2027", (255, 210, 60), H)
    bant = Image.new("RGB", (serit.width + 2 * W, H))
    bant.paste(serit, (W, 0))
    adim = serit.width + W
    patlama = [(rnd.randint(3, 28), rnd.randint(2, 6), rnd.randrange(adim),
                colorsys.hsv_to_rgb(rnd.random(), 1, 1)) for _ in range(8)]
    kareler = []
    for t in range(adim):
        im = Image.new("RGB", (W, H))
        for cx, cy, t0, rgb in patlama:
            yas = (t - t0) % adim
            if yas < 14:
                r, f = yas * 0.5, (1 - yas / 14)
                for a in range(10):
                    ang = a / 10 * 2 * math.pi
                    x, y = round(cx + r * math.cos(ang) * 1.3), round(cy + r * math.sin(ang))
                    if 0 <= x < W and 0 <= y < H:
                        im.putpixel((x, y), tuple(int(c * 255 * f) for c in rgb))
        on = bant.crop((t, 0, t + W, H))
        im.paste(on, (0, 0), on.convert("L").point(lambda v: 255 if v else 0))
        kareler.append(im)
    return kareler


def _balkabagi(n=48, seed=24):
    """Cadılar bayramı balkabağı: oyulmuş yüz, içinde titreyen mum ışığı."""
    rnd = random.Random(seed)
    titreme = [0.6 + 0.4 * rnd.random() for _ in range(n)]
    kareler = []
    for t in range(n):
        im = Image.new("RGB", (W, H))
        f = titreme[t]
        for y in range(3, 15):
            for x in range(8, 24):
                if ((x - 15.5) / 8) ** 2 + ((y - 9) / 6) ** 2 <= 1:
                    dilim = (x - 8) % 4 == 0
                    im.putpixel((x, y), (150, 55, 0) if dilim else (190, 75, 0))   # koyu kabuk: yüz öne çıksın
        for x, y in ((15, 2), (16, 2), (16, 1), (17, 1)):     # sap
            im.putpixel((x, y), (40, 140, 30))
        isik = (255, int(235 * f), int(150 * f))             # sarı-beyaz mum ışığı
        for x, y in ((11, 7), (12, 7), (12, 6), (19, 7), (20, 7), (19, 6),     # üçgen gözler
                     (15, 9), (16, 9),                                            # burun
                     (11, 11), (12, 12), (13, 12), (14, 11), (15, 12), (16, 12),  # dişli ağız
                     (17, 11), (18, 12), (19, 12), (20, 11)):
            im.putpixel((x, y), tuple(int(c * f) for c in isik))
        kareler.append(im)
    return kareler


# --------------------------------------------------------------------------- oyunlar
PARCALAR = {  # tetromino şekilleri ve renkleri
    "I": ([(0, 0), (1, 0), (2, 0), (3, 0)], (0, 220, 255)), "O": ([(0, 0), (1, 0), (0, 1), (1, 1)], (255, 220, 0)),
    "T": ([(0, 0), (1, 0), (2, 0), (1, 1)], (180, 0, 255)), "L": ([(0, 0), (0, 1), (0, 2), (1, 2)], (255, 130, 0)),
    "S": ([(1, 0), (2, 0), (0, 1), (1, 1)], (0, 230, 60)), "Z": ([(0, 0), (1, 0), (1, 1), (2, 1)], (255, 30, 30)),
}


def _tetris(seed=25):
    """Tetris tarzı: parçalar yukarıdan düşüp dibe dizilir; dolan satır parlayıp silinir,
    yığın dolunca temizlenip baştan başlar (yatay ekranda 'yukarı' = sol üst değil, gerçek üst)."""
    rnd = random.Random(seed)
    alan = {}
    kareler = []

    def ciz(dusen=None, renk=None, parlak=()):
        im = Image.new("RGB", (W, H))
        for x in (9, 22):                                    # kuyu duvarları
            for y in range(H):
                im.putpixel((x, y), (60, 60, 70))
        for (x, y), c in alan.items():
            im.putpixel((x, y), (255, 255, 255) if y in parlak else c)
        for x, y in dusen or []:
            if 0 <= y < H:
                im.putpixel((x, y), renk)
        return im

    for _ in range(14):                                      # 14 parça
        ad = rnd.choice(list(PARCALAR))
        sekil, renk = PARCALAR[ad]
        x0 = rnd.randint(10, 21 - max(x for x, _ in sekil))
        y0 = -2
        while True:
            hucre = [(x0 + x, y0 + y + 1) for x, y in sekil]
            if any(y >= H or (x, y) in alan for x, y in hucre):
                break
            y0 += 1
            kareler.append(ciz([(x0 + x, y0 + y) for x, y in sekil], renk))
        for x, y in sekil:
            if y0 + y < 0:                                   # taştı: temizle
                alan.clear()
                break
            alan[(x0 + x, y0 + y)] = renk
        dolu = [y for y in range(H) if all((x, y) in alan for x in range(10, 22))]
        if dolu:
            for _ in range(3):
                kareler.append(ciz(parlak=dolu))
            for y in dolu:
                for x in range(10, 22):
                    alan.pop((x, y), None)
            for y in sorted(dolu):                           # üsttekiler aşağı kayar
                alan = {(x, yy + (1 if yy < y else 0)): c for (x, yy), c in alan.items()}
            kareler.append(ciz())
    return kareler


def _uzay_istilacilari(n=48):
    """Uzay istilacıları tarzı: iki sıra uzaylı sağa-sola yürür, altta gemi ateş eder."""
    UZAYLI = [["..#..#..", "...##...", "..####..", ".##..##.", "########", "#.#..#.#"],
              ["..#..#..", "#..##..#", "#.####.#", "###..###", ".######.", ".#....#."]]
    kareler = []
    for t in range(n):
        im = Image.new("RGB", (W, H))
        ofs = [0, 1, 2, 3, 2, 1][(t // 4) % 6] - 1
        poz = (t // 4) % 2
        for satir, renk in ((0, (120, 255, 120)), (7, (255, 120, 255))):
            for k in range(3):
                for gy, row in enumerate(UZAYLI[poz]):
                    for gx, c in enumerate(row):
                        x, y = 2 + k * 10 + gx + ofs, satir + gy
                        if c == "#" and 0 <= x < W and y < 13:
                            im.putpixel((x, y), renk)
        gx = 4 + int(11.5 + 11.5 * math.sin(t / n * 2 * math.pi))     # gemi
        for x, y in ((gx, 14), (gx - 1, 15), (gx, 15), (gx + 1, 15)):
            if 0 <= x < W:
                im.putpixel((x, y), (0, 200, 255))
        mermi_y = 13 - (t % 8) * 2
        if mermi_y >= 0:
            im.putpixel((gx, mermi_y), (255, 255, 0))
        kareler.append(im)
    return kareler


def _pong(n=56):
    """Pong: iki raket topu karşılıklı karşılar, ortada kesik çizgi."""
    kareler = []
    for t in range(n):
        im = Image.new("RGB", (W, H))
        for y in range(0, H, 2):
            im.putpixel((15, y), (70, 70, 70))
        # top: x 1..30 arası gidip gelir (n=56 -> 2 vuruş), y üçgen dalga
        f = t / n
        bx = round(1 + 29 * abs(((f * 2) % 2) - 1))          # 1..30 arası gidip gelir
        by = round(1 + 13 * abs(((f * 3.5) % 2) - 1))
        im.putpixel((max(1, min(30, bx)), by), (255, 255, 255))
        for x, hedef in ((0, by), (31, by)):
            y0 = max(0, min(H - 4, hedef - 2 + (1 if x else -1)))
            for y in range(y0, y0 + 4):
                im.putpixel((x, y), (0, 200, 255) if x == 0 else (255, 80, 80))
        kareler.append(im)
    return kareler


# --------------------------------------------------------------------------- film temaları
def _isin_kilici(n=48):
    """Işın kılıcı düellosu: mavi ve kırmızı kılıç açılır, çarpışır, kıvılcım saçar."""
    kareler = []
    for t in range(n):
        im = Image.new("RGB", (W, H))
        acilma = min(1.0, t / 8)
        sallanma = math.sin(t / n * 2 * math.pi * 2)
        for (sx, sy), yon, renk in (((4, 13), 1, (40, 120, 255)), ((27, 13), -1, (255, 30, 30))):
            for x, y in ((sx, sy), (sx, sy + 1), (sx + yon, sy + 1)):   # kabza
                im.putpixel((x, min(H - 1, y)), (150, 150, 150))
            uz = int(12 * acilma)
            for k in range(1, uz + 1):
                x = sx + yon * round(k * (0.85 + 0.15 * sallanma))
                y = sy - round(k * 0.75)
                if 0 <= x < W and 0 <= y < H:
                    im.putpixel((x, y), (230, 240, 255))                 # beyaz çekirdek
                    for dx in (-1, 1):
                        if 0 <= x + dx < W:
                            eski = im.getpixel((x + dx, y))
                            if eski == (0, 0, 0):
                                im.putpixel((x + dx, y), renk)
        if acilma >= 1 and abs(sallanma) > 0.7:                           # çarpışma kıvılcımı
            for dx, dy in ((0, 0), (1, -1), (-1, -1), (1, 1), (-1, 1), (0, -2), (2, 0), (-2, 0)):
                x, y = 15 + dx, 5 + dy
                if 0 <= x < W and 0 <= y < H:
                    im.putpixel((x, y), (255, 255, 160))
        kareler.append(im)
    return kareler


def _kara_delik(n=60):
    """Kara delik: dönen, eğik turuncu-beyaz toplanma diski, ortada tamamen karanlık olay ufku,
    üstte bükülmüş ışık halkası."""
    kareler = []
    for t in range(n):
        p = t / n * 2 * math.pi
        im = Image.new("RGB", (W, H))
        for y in range(H):
            for x in range(W):
                dx, dy = (x - 15.5) / 1.0, (y - 7.5) / 0.45            # eğik disk
                r = math.hypot(dx, dy)
                if 5 < r < 15:
                    aci = math.atan2(dy, dx)
                    parlak = (0.6 + 0.4 * math.sin(aci * 3 - p * 2)) * (0.35 + 0.65 * (1 - (r - 5) / 10))
                    doppler = 1.0 + 0.5 * math.cos(aci)                   # yaklaşan taraf parlak
                    v = max(0.0, min(1.0, parlak * doppler * 1.3))
                    im.putpixel((x, y), (255 if v > 0.15 else int(1700 * v), int(200 * v), int(110 * v * v)))
                halka = math.hypot((x - 15.5) / 1.3, (y - 7.5))
                if 4.6 < halka < 5.6 and y < 8:                           # bükülmüş ışık halkası
                    v = 0.6 + 0.4 * math.sin(p + x * 0.4)
                    im.putpixel((x, y), (int(255 * v), int(200 * v), int(120 * v)))
                if math.hypot((x - 15.5) / 1.3, (y - 7.5)) < 4.2:         # olay ufku
                    im.putpixel((x, y), (0, 0, 0))
        kareler.append(im)
    return kareler


YENI = {
    "kar-yagisi.gif": (_kar_ve_ev, 90),
    "yilbasi-agaci.gif": (_yilbasi_agaci, 120),
    "mutlu-yillar.gif": (_mutlu_yillar, 60),
    "cadilar-bayrami.gif": (_balkabagi, 90),
    "tetris.gif": (_tetris, 70),
    "uzay-istilacilari.gif": (_uzay_istilacilari, 90),
    "pong.gif": (_pong, 60),
    "isin-kilici.gif": (_isin_kilici, 70),
    "kara-delik.gif": (_kara_delik, 70),
}
