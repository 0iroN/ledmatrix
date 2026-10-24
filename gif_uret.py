"""32x16 LED matris için hazır GIF'ler üretir (piksel sanatı: panelde birebir gösterilir).

Kullanım:  python gif_uret.py [çıktı_klasörü]      (varsayılan: gifler/)
Her animasyon kendi kendine kusursuz döngü yapacak şekilde kare sayısı seçildi.
"""
import colorsys
import math
import random
import sys
from pathlib import Path

from PIL import Image

import font5x7

W, H = 32, 16


def kaydet(ad, kareler, ms, klasor):
    """Kare kare palet (titreşimsiz) — GIF'in 256 renk sınırında renkler kaymasın."""
    p = [k.quantize(colors=255, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE)
         for k in kareler]
    yol = klasor / ad
    p[0].save(yol, save_all=True, append_images=p[1:], duration=ms, loop=0,
              optimize=False, disposal=1)
    print(f"{ad:24s} {len(kareler):3d} kare x {ms} ms")


def karart(c, f):
    return tuple(int(v * f) for v in c)


# ---------------------------------------------------------------- Matrix temalı
def matrix_yagmur(n=64, seed=1, renk=(0, 255, 70)):
    """Dijital yağmur: her sütunda düşen parlak baş + sönen iz. Hızlar 1/2 ve
    yol uzunluğu 32 -> 64 karede herkes tam tur atar, döngü dikişsiz."""
    rnd = random.Random(seed)
    sutunlar = [(rnd.randrange(32), rnd.choice((1, 1, 2)), rnd.randint(4, 10)) for _ in range(W)]
    kareler = []
    for t in range(n):
        im = Image.new("RGB", (W, H))
        for x, (ofs, hiz, iz) in enumerate(sutunlar):
            bas = (ofs + t * hiz) % 32 - 8          # -8..23: ekrana yukarıdan girer
            for k in range(iz):
                y = bas - k
                if 0 <= y < H:
                    # iz yavaş sönsün: panel gama 2.2 uygular, koyu tonlar LED'de kaybolur
                    c = (200, 255, 200) if k == 0 else karart(renk, 0.25 + 0.75 * (1 - k / iz) ** 0.7)
                    im.putpixel((x, y), c)
        kareler.append(im)
    return kareler


def matrix_yazi(metin="WAKE UP, NEO...", seed=2):
    """Arkada sönük dijital yağmur, önde kayan yeşil yazı."""
    serit = font5x7.render(metin, (120, 255, 140), H)
    bant = Image.new("RGB", (serit.width + 2 * W, H))
    bant.paste(serit, (W, 0))
    adim = serit.width + W
    n = adim + (64 - adim % 64) % 64             # yağmurun 64'lük döngüsüne denk
    yagmur = matrix_yagmur(64, seed, renk=(0, 90, 30))
    kareler = []
    for t in range(n):
        im = yagmur[t % 64].copy()
        x = t % adim
        on = bant.crop((x, 0, x + W, H))
        maske = on.convert("L").point(lambda v: 255 if v else 0)
        im.paste(on, (0, 0), maske)
        kareler.append(im)
    return kareler


def matrix_hap(seed=3):
    """Kırmızı hap / mavi hap: yağmurun önünde iki hap, sırayla parlıyor."""
    hap = [".####.", "######", "######", ".####."]
    yagmur = matrix_yagmur(64, seed, renk=(0, 80, 25))
    kareler = []
    for t in range(64):
        im = yagmur[t].copy()
        nabiz = 0.55 + 0.45 * math.sin(t / 64 * 2 * math.pi * 2)
        for x0, renk, faz in ((6, (255, 20, 20), 0), (20, (30, 80, 255), math.pi)):
            f = 0.35 + 0.65 * (0.5 + 0.5 * math.sin(t / 64 * 2 * math.pi + faz))
            for gy, row in enumerate(hap):
                for gx, c in enumerate(row):
                    if c == "#":
                        im.putpixel((x0 + gx, 6 + gy), karart(renk, f))
            im.putpixel((x0 + 1, 7), karart((255, 255, 255), f * nabiz))   # parıltı
        kareler.append(im)
    return kareler


# ---------------------------------------------------------------- diğer türler
def ates(n=48, seed=4):
    """Klasik 'doom fire': alttan ısı, yukarı doğru soğuyarak yükselir."""
    rnd = random.Random(seed)
    isi = [[0.0] * W for _ in range(H + 2)]
    pal = lambda v: (min(255, int(v * 3 * 255)), min(255, int(max(0, v * 3 - 1) * 255)),
                     min(255, int(max(0, v * 3 - 2) * 255)))
    kareler = []
    for t in range(n + 30):                      # ilk 30 kare ısınma, kaydedilmez
        for x in range(W):
            isi[H + 1][x] = rnd.uniform(0.6, 1.0)
        for y in range(H + 1):
            for x in range(W):
                kaynak = isi[y + 1][(x + rnd.choice((-1, 0, 1))) % W]
                isi[y][x] = max(0.0, kaynak - rnd.uniform(0.02, 0.09))
        if t >= 30:
            im = Image.new("RGB", (W, H))
            for y in range(H):
                for x in range(W):
                    im.putpixel((x, y), pal(isi[y + 1][x]))
            kareler.append(im)
    return kareler


def havai_fisek(n=72, seed=5):
    rnd = random.Random(seed)
    patlamalar = [(rnd.randint(5, 26), rnd.randint(3, 8), rnd.randrange(n),
                   colorsys.hsv_to_rgb(rnd.random(), 1, 1)) for _ in range(6)]
    kareler = []
    for t in range(n):
        im = Image.new("RGB", (W, H))
        for cx, cy, t0, rgb in patlamalar:
            yas = (t - t0) % n
            if yas < 8:                           # yükselen roket
                y = H - 1 - int((H - 1 - cy) * yas / 8)
                im.putpixel((cx, y), (255, 200, 120))
            elif yas < 26:                        # patlama halkası, sönerek
                r = (yas - 8) * 0.45
                f = (1 - (yas - 8) / 18) ** 1.3
                for a in range(12):
                    ang = a / 12 * 2 * math.pi
                    x, y = round(cx + r * math.cos(ang)), round(cy + r * math.sin(ang) + (yas - 8) * 0.12)
                    if 0 <= x < W and 0 <= y < H:
                        im.putpixel((x, y), tuple(int(c * 255 * f) for c in rgb))
        kareler.append(im)
    return kareler


def yildizlar(n=48, seed=6):
    """Hiperuzay: merkezden dışa akan yıldızlar, hızlandıkça parlar."""
    rnd = random.Random(seed)
    yild = [(rnd.uniform(0, 2 * math.pi), rnd.uniform(0, 1)) for _ in range(40)]
    kareler = []
    for t in range(n):
        im = Image.new("RGB", (W, H))
        for ang, faz in yild:
            d = ((faz + t / n) % 1.0) ** 2 * 20
            x, y = round(15.5 + d * math.cos(ang) * 1.6), round(7.5 + d * math.sin(ang))
            if 0 <= x < W and 0 <= y < H:
                v = int(140 + 115 * min(1, d / 12))
                im.putpixel((x, y), (v, v, min(255, v + 40)))
        kareler.append(im)
    return kareler


def plazma(n=60):
    kareler = []
    for t in range(n):
        im = Image.new("RGB", (W, H))
        p = t / n * 2 * math.pi
        for y in range(H):
            for x in range(W):
                v = (math.sin(x / 4 + p) + math.sin(y / 3 - p) + math.sin((x + y) / 6 + p)
                     + math.sin(math.hypot(x - 16, y - 8) / 3 - p)) / 4
                r, g, b = colorsys.hsv_to_rgb((v + 1) / 2, 1, 1)
                im.putpixel((x, y), (int(r * 255), int(g * 255), int(b * 255)))
        kareler.append(im)
    return kareler


def hayat_oyunu(n=90, seed=7):
    """Conway'in Hayat Oyunu (kenarlar sarılı); durağanlaşınca yeniden tohumlar."""
    rnd = random.Random(seed)
    yeni = lambda: [[rnd.random() < 0.33 for _ in range(W)] for _ in range(H)]
    g, onceki, kareler = yeni(), [], []
    for t in range(n):
        im = Image.new("RGB", (W, H))
        hue = t / n
        for y in range(H):
            for x in range(W):
                if g[y][x]:
                    r, gg, b = colorsys.hsv_to_rgb((hue + x / 64) % 1, 0.8, 1)
                    im.putpixel((x, y), (int(r * 255), int(gg * 255), int(b * 255)))
        kareler.append(im)
        komsu = lambda x, y: sum(g[(y + dy) % H][(x + dx) % W]
                                 for dy in (-1, 0, 1) for dx in (-1, 0, 1) if dx or dy)
        g2 = [[(komsu(x, y) == 3) or (g[y][x] and komsu(x, y) == 2) for x in range(W)]
              for y in range(H)]
        if g2 in onceki[-2:]:
            g2 = yeni()
        onceki.append(g)
        g = g2
    return kareler


def ekolayzer(n=48, seed=8):
    rnd = random.Random(seed)
    bant = [(rnd.uniform(0.5, 1.0), rnd.randint(1, 3), rnd.uniform(0, 2 * math.pi)) for _ in range(8)]
    kareler = []
    for t in range(n):
        im = Image.new("RGB", (W, H))
        for i, (a, k, faz) in enumerate(bant):
            h = int(2 + (H - 3) * a * (0.5 + 0.5 * math.sin(t / n * 2 * math.pi * k + faz)))
            for y in range(H - h, H):
                f = (H - 1 - y) / (H - 1)
                c = (int(255 * f * 1.6) if f > 0.5 else int(255 * f * 2), int(255 * (1 - f)), 0)
                c = (min(255, c[0]), min(255, c[1]), 0)
                for x in range(i * 4, i * 4 + 3):
                    im.putpixel((x, y), c)
        kareler.append(im)
    return kareler


def kalp_ritmi(n=64):
    """EKG çizgisi soldan sağa yazılır, iz söner; ritim tepesinde küçük kalp atar."""
    dalga = [0] * 32
    for i, d in zip(range(10, 17), (0, -1, 2, -6, 5, -1, 0)):
        dalga[i] = d
    kareler = []
    for t in range(n):
        im = Image.new("RGB", (W, H))
        kafa = t % 32
        for k in range(32):
            x = (kafa - k) % 32
            f = (1 - k / 32) ** 2
            y = 9 + dalga[x]
            im.putpixel((x, max(0, min(H - 1, y))), (0, int(255 * f), int(60 * f)))
        if 12 <= kafa <= 20:
            for (x, y) in ((27, 2), (29, 2), (26, 3), (27, 3), (28, 3), (29, 3), (30, 3),
                           (27, 4), (28, 4), (29, 4), (28, 5)):
                im.putpixel((x, y), (255, 0, 40))
        kareler.append(im)
    return kareler


def kuzey_isiklari(n=80, seed=9):
    """Aurora: gece göğünde dalgalanan yeşil-turkuaz-mor perdeler, titreşen yıldızlar,
    altta dağ siluetleri. Tüm hareketler n karede tam periyot -> dikişsiz döngü."""
    rnd = random.Random(seed)
    yildiz = [(rnd.randrange(W), rnd.randrange(9), rnd.uniform(0, 2 * math.pi)) for _ in range(14)]
    dag = [13 - int(2.5 * (0.5 + 0.5 * math.sin(x / 5.0)) + 1.5 * (0.5 + 0.5 * math.sin(x / 2.3 + 1)))
           for x in range(W)]
    kareler = []
    for t in range(n):
        p = t / n * 2 * math.pi
        im = Image.new("RGB", (W, H))
        for x, y, faz in yildiz:
            v = int(90 + 120 * (0.5 + 0.5 * math.sin(p * 3 + faz)))
            im.putpixel((x, y), (v, v, v))
        # Gerçek aurora gibi: parlak yeşil ALT kenar, yukarı doğru uzanan dikey ışınlar,
        # tepede mora sönüş. İki perde farklı hız/fazla üst üste biner.
        for perde, (hiz, guc) in enumerate(((1, 1.0), (2, 0.7))):
            for x in range(W):
                taban = 7.5 + 1.8 * math.sin(x / 5.0 + p * hiz + perde * 2.5) + 0.7 * math.sin(x / 2.1 - p * hiz)
                isin = 0.35 + 0.65 * (0.5 + 0.5 * math.sin(x * 1.3 + p * 3 * hiz + perde)) ** 2   # ışın titreşimi
                parlak = (0.5 + 0.5 * math.sin(x / 3.4 - p * (hiz + 1) + perde)) * guc * isin
                for y in range(H):
                    d = taban - y                          # tabandan yukarı mesafe
                    if -1 <= d <= 7:
                        f = parlak * (1.0 if 0 <= d <= 1.5 else 0.6 if d < 0 else (1 - (d - 1.5) / 5.5) ** 1.3)
                        k = min(1, max(0, (d - 2) / 5))    # 0 = yeşil, 1 = mor
                        renk = (int(0 + 170 * k), int(255 - 215 * k), int(90 + 165 * k))
                        c = tuple(int(v * f) for v in renk)
                        eski = im.getpixel((x, y))
                        im.putpixel((x, y), tuple(min(255, e + c_) for e, c_ in zip(eski, c)))
        for x in range(W):                                # dağlar + çam ağaçları siyah siluet
            for y in range(dag[x], H):
                im.putpixel((x, y), (0, 0, 0))
        for x in (4, 11, 23, 28):
            for y in range(dag[x] - 3, dag[x]):
                genis = (y - (dag[x] - 3)) // 2
                for dx in range(-genis, genis + 1):
                    if 0 <= x + dx < W:
                        im.putpixel((x + dx, y), (0, 0, 0))
        kareler.append(im)
    return kareler


# Minecraft tarzı bloklar (kendi çizimimiz, 1 piksel = 1 blok)
CIM, TOPRAK, TAS, KUTUK, YAPRAK = (60, 200, 40), (130, 80, 35), (110, 110, 110), (100, 65, 25), (30, 140, 20)


def minecraft_dunya(n=64, seed=10, govde=3, yaprak=3):
    """Soldan sağa kayan blok dünyası: çimen/toprak/taş katmanları, ağaçlar, bulutlar,
    gökte kare güneş. Arazi 64 blok genişliğinde ve 64 karede 1 blok/kare kayar -> döngü.
    govde/yaprak: ağacın kütük ve yaprak yüksekliği (Steve ölçeğine göre ayarlanır)."""
    rnd = random.Random(seed)
    L = 64
    yuk = []
    h = 11
    for _ in range(L):
        h = max(9, min(13, h + rnd.choice((-1, 0, 0, 1))))
        yuk.append(h)
    yuk[-1] = yuk[-2] = yuk[0]                            # dikiş yerinde basamak olmasın
    agac = {7, 25, 41, 56}
    bulut = [(x, rnd.randint(1, 3), rnd.randint(3, 6)) for x in (5, 30, 50)]
    kareler = []
    for t in range(n):
        im = Image.new("RGB", (W, H), (90, 150, 255))
        for x in range(4):                               # güneş (sabit)
            for y in range(4):
                im.putpixel((25 + x, 1 + y), (255, 230, 60))
        for bx, by, bw in bulut:                         # bulutlar yarım hızla
            for i in range(bw):
                x = (bx + i - t // 2) % L
                if x < W:
                    im.putpixel((x, by), (245, 245, 255))
                    if 0 < i < bw - 1:
                        im.putpixel((x, by - 1), (245, 245, 255))
        for sx in range(W):
            wx = (sx + t) % L
            ust = yuk[wx]
            for y in range(ust, H):
                im.putpixel((sx, y), CIM if y == ust else TOPRAK if y < ust + 2 else TAS)
            if wx in agac:
                for y in range(ust - govde, ust):
                    im.putpixel((sx, y), KUTUK)
                for dx in (-1, 0, 1):
                    for y in range(max(0, ust - govde - yaprak), ust - govde):
                        if 0 <= sx + dx < W:
                            im.putpixel((sx + dx, y), YAPRAK)
        kareler.append(im)
    return kareler


def minecraft_creeper(seed=11):
    """Creeper yüzü (16x16, yeşil desenli): bekler, beyaz yanıp sönerek 'tıslar',
    patlar, kıvılcımlar söner, baştan."""
    rnd = random.Random(seed)
    yuz = ["........", "........", ".##..##.", ".##..##.", "...##...", "..####..", "..####..", "..#..#.."]
    doku = [[rnd.choice(((80, 190, 60), (60, 160, 45), (110, 210, 90), (45, 130, 35))) for _ in range(8)]
            for _ in range(8)]

    def kafa(beyaz=0.0):
        im = Image.new("RGB", (W, H))
        for gy in range(8):
            for gx in range(8):
                c = (0, 0, 0) if yuz[gy][gx] == "#" else doku[gy][gx]
                c = tuple(int(v + (255 - v) * beyaz) for v in c)
                for dy in (0, 1):
                    for dx in (0, 1):
                        im.putpixel((8 + gx * 2 + dx, gy * 2 + dy), c)
        return im

    kareler = [kafa() for _ in range(20)]                # bekle
    for i in range(12):                                  # tıslama: hızlanan beyaz yanıp sönme
        kareler.append(kafa(0.85 if i % 2 == 0 else 0.0))
    for r in range(8):                                   # patlama
        im = Image.new("RGB", (W, H))
        for _ in range(60 - r * 6):
            a, d = rnd.uniform(0, 2 * math.pi), rnd.uniform(0, r * 2.2 + 1)
            x, y = round(15.5 + d * math.cos(a) * 1.5), round(7.5 + d * math.sin(a))
            if 0 <= x < W and 0 <= y < H:
                f = 1 - r / 8
                im.putpixel((x, y), (255, int(200 * f), int(60 * f * f)))
        kareler.append(im)
    kareler += [Image.new("RGB", (W, H))] * 6
    return kareler


def _arazi(seed=10, L=64):
    """minecraft_dunya ile aynı arazi yükseklikleri (aynı tohum -> aynı dünya)."""
    rnd = random.Random(seed)
    yuk, h = [], 11
    for _ in range(L):
        h = max(9, min(13, h + rnd.choice((-1, 0, 0, 1))))
        yuk.append(h)
    yuk[-1] = yuk[-2] = yuk[0]
    return yuk


def minecraft_steve(n=64, boy=5):          # 5 = Osman'ın seçimi (20.10)
    """Blok dünyasında yürüyen Steve tarzı karakter (kendi çizimimiz).
    Dünya kayar, karakter ortada kalır; bacak ve kollar her 2 karede değişir.
    boy: 8 (4x8, ilk sürüm), 6 (3x6) ya da 5 (3x5). Küçük boylarda ağaçlar uzar ki
    Steve ağaçtan belirgin şekilde kısa kalsın (oyunda ~2 blok, ağaç ~6 blok)."""
    SAC, TEN, GOZ, TISORT, PANT, AYAK = (70, 45, 20), (210, 160, 120), (60, 60, 210), (0, 175, 175), (50, 50, 170), (90, 90, 90)

    def sprite(adim):
        bacak = [PANT, None, PANT] if adim else [None, PANT, None]
        if boy == 8:
            return [[SAC] * 4, [TEN] * 4, [TEN, GOZ, TEN, GOZ], [TISORT] * 4,
                    [TEN if adim else TISORT, TISORT, TISORT, TISORT if adim else TEN], [TISORT] * 4,
                    [PANT, None, None, PANT] if adim else [None, PANT, PANT, None],
                    [AYAK, None, None, AYAK] if adim else [None, AYAK, AYAK, None]]
        kafa = [[SAC, SAC, SAC], [TEN, GOZ, TEN]]
        kol = [TEN if adim else TISORT, TISORT, TISORT if adim else TEN]
        if boy == 6:
            return kafa + [[TISORT] * 3, kol, bacak,
                           [AYAK, None, AYAK] if adim else [None, AYAK, None]]
        return kafa + [kol, bacak, [AYAK, None, AYAK] if adim else [None, AYAK, None]]   # boy 5

    agac = {8: (3, 3), 6: (4, 4), 5: (4, 4)}[boy]
    dunya = minecraft_dunya(n, govde=agac[0], yaprak=agac[1])
    yuk = _arazi()
    sx = 9
    kareler = []
    for t, im in enumerate(dunya):
        im = im.copy()
        ust = yuk[(sx + 1 + t) % 64]                     # ayakların bastığı sütun
        sp = sprite((t // 2) % 2)
        for gy, satir in enumerate(sp):
            y = ust - len(sp) + gy
            for gx, c in enumerate(satir):
                if c and 0 <= y < H:
                    im.putpixel((sx + gx, y), c)
        kareler.append(im)
    return kareler


ALTIN = (255, 190, 40)


def elden_ring_erdtree(n=60, seed=12):
    """Altın Ağaç: karanlıkta parlayan dev altın ağaç, nabız gibi parıldayan taç,
    yavaşça süzülen altın yapraklar (n karede tam döngü)."""
    rnd = random.Random(seed)
    yapraklar = [(rnd.uniform(4, 28), rnd.uniform(0, 1), rnd.uniform(0, 2 * math.pi)) for _ in range(10)]
    kareler = []
    for t in range(n):
        p = t / n * 2 * math.pi
        im = Image.new("RGB", (W, H))
        nabiz = 0.75 + 0.25 * math.sin(p)
        for y in range(H):                               # taç: geniş, üstte yayvan parıltı
            for x in range(W):
                d = math.hypot((x - 15.5) / 1.9, (y - 4.5) / 1.1)
                if d < 6:
                    f = min(1.0, 0.25 + 1.1 * (1 - d / 6) ** 0.8) * nabiz   # gama'ya karşı parlak tut
                    titre = 0.85 + 0.15 * math.sin(x * 2.1 + y * 1.7 + p * 2)
                    im.putpixel((x, y), tuple(int(c * f * titre) for c in ALTIN))
        for y in range(6, H):                            # gövde ve kökler
            gen = 1 if y < 12 else 2 + (y - 12)
            for x in range(16 - gen, 16 + gen):
                if 0 <= x < W:
                    im.putpixel((x, y), (200, 140, 30) if abs(x - 15.5) < gen - 0.5 else (120, 80, 15))
        for x0, faz, salin in yapraklar:                 # süzülen yapraklar
            y = ((faz + t / n) % 1) * (H + 2) - 1
            x = x0 + 1.5 * math.sin(p * 2 + salin)
            xi, yi = round(x), round(y)
            if 0 <= xi < W and 0 <= yi < H:
                im.putpixel((xi, yi), (255, 220, 110))
        kareler.append(im)
    return kareler


def elden_ring_grace(n=48, seed=13):
    """Lütuf Noktası: yerde titreyen altın alev, yükselen kıvılcımlar,
    alevden çıkan ince yol gösteren ışınlar."""
    rnd = random.Random(seed)
    kivilcim = [(rnd.uniform(12, 20), rnd.uniform(0, 1), rnd.uniform(0.6, 1.4)) for _ in range(12)]
    kareler = []
    for t in range(n):
        p = t / n * 2 * math.pi
        im = Image.new("RGB", (W, H))
        for x in range(W):                               # zemin
            im.putpixel((x, 15), (25, 20, 10))
        for y in range(7, 15):                           # alev: dibi geniş, ucu dar, titrek
            yuks = (15 - y) / 8
            gen = 2.6 * (1 - yuks) + 0.4
            sap = 0.8 * math.sin(p * 2 + y * 0.9) * yuks
            for x in range(W):
                d = abs(x - 15.5 - sap)
                if d < gen:
                    f = (1 - d / gen) * (1 - yuks * 0.5)
                    c = (255, int(150 + 90 * (1 - yuks)), int(40 * (1 - yuks)))
                    im.putpixel((x, y), tuple(int(v * min(1, f * 1.4)) for v in c))
        for x0, faz, hiz in kivilcim:                    # yükselen kıvılcımlar
            y = 14 - ((faz + t / n * hiz) % 1) * 15
            x = x0 + math.sin(p + faz * 6)
            if 0 <= round(x) < W and 0 <= round(y) < H:
                im.putpixel((round(x), round(y)), (255, 230, 120))
        for i, (dx, dy) in enumerate(((1, -0.35), (-1, -0.2))):   # yol gösteren ince ışınlar
            for k in range(1, 12):
                x, y = round(15.5 + dx * k), round(11 + dy * k)
                if 0 <= x < W and 0 <= y < H:
                    f = (1 - k / 12) * (0.4 + 0.3 * math.sin(p * 2 + i + k * 0.5))
                    eski = im.getpixel((x, y))
                    im.putpixel((x, y), tuple(min(255, e + int(c * f)) for e, c in zip(eski, ALTIN)))
        kareler.append(im)
    return kareler


def elden_ring_you_died():
    """Kararan ekranda, kırmızı bir bantla belirip sönen iki satır 'YOU DIED'."""
    yazi = Image.new("RGB", (W, H))
    for metin, y0 in (("YOU", 0), ("DIED", 8)):
        s = font5x7.render(metin, (200, 20, 20), 7 + 0)
        # render 7 satırlık tuvalde gövde y=0'dan başlar
        yazi.paste(s, ((W - s.width) // 2, y0), s.convert("L").point(lambda v: 255 if v else 0))
    kareler = []
    egri = [i / 14 for i in range(15)] + [1.0] * 25 + [1 - i / 14 for i in range(15)] + [0.0] * 10
    for f in egri:
        im = Image.new("RGB", (W, H))
        for y in range(H):                               # arka bant: ortası hafif kızıl
            v = int(30 * f * (1 - abs(y - 7.5) / 8))
            for x in range(W):
                im.putpixel((x, y), (v, 0, 0))
        katman = yazi.point(lambda c, f=f: int(c * f))
        im.paste(katman, (0, 0), yazi.convert("L").point(lambda v: 255 if v else 0))
        kareler.append(im)
    return kareler


ORI_MAVI = (90, 200, 255)


def ori_isik(n=72, seed=14):
    """Ori: karanlık ormanda sekiz çizerek uçan parlak ruh, arkasında sönen ışık izi,
    çevrede yavaş yanıp sönen ateşböcekleri."""
    rnd = random.Random(seed)
    agaclar = [(x, rnd.randint(7, 11)) for x in range(0, W, 5)]
    bocek = [(rnd.randrange(W), rnd.randrange(3, 13), rnd.uniform(0, 2 * math.pi)) for _ in range(8)]
    yol = lambda t: (15.5 + 12 * math.sin(t / n * 2 * math.pi), 7 + 4 * math.sin(t / n * 4 * math.pi))
    kareler = []
    for t in range(n):
        p = t / n * 2 * math.pi
        im = Image.new("RGB", (W, H))
        for x0, ust in agaclar:                          # koyu mavi orman siluetleri
            for y in range(ust, H):
                for x in (x0, x0 + 1):
                    if x < W:
                        im.putpixel((x, y), (0, 12, 35))
            for dx in range(-1, 3):
                if 0 <= x0 + dx < W:
                    im.putpixel((x0 + dx, ust), (0, 30, 50))
        for x, y, faz in bocek:
            v = 0.5 + 0.5 * math.sin(p * 2 + faz)
            if v > 0.35:
                im.putpixel((x, y), (int(180 * v), int(255 * v), int(120 * v)))
        for k in range(14, 0, -1):                       # iz: geçmiş konumlar, sönerek
            x, y = yol(t - k * 0.8)
            f = (1 - k / 15) ** 1.6
            xi, yi = round(x), round(y)
            if 0 <= xi < W and 0 <= yi < H:
                eski = im.getpixel((xi, yi))
                im.putpixel((xi, yi), tuple(min(255, e + int(c * f)) for e, c in zip(eski, ORI_MAVI)))
        x, y = yol(t)                                    # Ori: beyaz çekirdek + mavi hale
        for dx, dy, c in ((0, 0, (255, 255, 255)), (1, 0, ORI_MAVI), (-1, 0, ORI_MAVI),
                          (0, 1, ORI_MAVI), (0, -1, ORI_MAVI)):
            xi, yi = round(x) + dx, round(y) + dy
            if 0 <= xi < W and 0 <= yi < H:
                im.putpixel((xi, yi), c)
        kareler.append(im)
    return kareler


def ori_ruh_agaci(n=60, seed=15):
    """Ruh Ağacı: nabız gibi parlayan mavi-beyaz ağaç, köklerden yukarı süzülen ışık
    tanecikleri."""
    rnd = random.Random(seed)
    tanecik = [(rnd.uniform(6, 26), rnd.uniform(0, 1), rnd.uniform(0.5, 1.2)) for _ in range(12)]
    kareler = []
    for t in range(n):
        p = t / n * 2 * math.pi
        nabiz = 0.6 + 0.4 * (0.5 + 0.5 * math.sin(p))
        im = Image.new("RGB", (W, H))
        for y in range(H):
            for x in range(W):
                d = math.hypot((x - 15.5) / 2.2, (y - 4) / 1.2)          # taç
                if d < 5:
                    f = min(1.0, 0.25 + 1.1 * (1 - d / 5) ** 0.8) * nabiz
                    im.putpixel((x, y), (int(60 * f), int(170 * f), int(255 * f)))
        for y in range(5, H):                                             # gövde + kökler
            gen = 1 if y < 11 else 1 + (y - 10)
            for x in range(16 - gen, 16 + gen):
                if 0 <= x < W:
                    merkez = abs(x - 15.5) < 1
                    f = nabiz if merkez else 0.45 * nabiz
                    im.putpixel((x, y), (int(170 * f), int(230 * f), int(255 * f)))
        for x0, faz, hiz in tanecik:
            y = 15 - ((faz + t / n * hiz) % 1) * 16
            x = x0 + 0.8 * math.sin(p * 2 + faz * 9)
            xi, yi = round(x), round(y)
            if 0 <= xi < W and 0 <= yi < H:
                im.putpixel((xi, yi), (200, 240, 255))
        kareler.append(im)
    return kareler


GIFLER = {
    "minecraft-steve.gif": (minecraft_steve, 110),
    "elden-ring-erdtree.gif": (elden_ring_erdtree, 80),
    "elden-ring-grace.gif": (elden_ring_grace, 70),
    "elden-ring-you-died.gif": (elden_ring_you_died, 80),
    "ori-isik.gif": (ori_isik, 60),
    "ori-ruh-agaci.gif": (ori_ruh_agaci, 70),
    "kuzey-isiklari.gif": (kuzey_isiklari, 70),
    "minecraft-dunya.gif": (minecraft_dunya, 110),
    "minecraft-creeper.gif": (minecraft_creeper, 90),
    "matrix-yagmur.gif": (matrix_yagmur, 70),
    "matrix-wake-up-neo.gif": (matrix_yazi, 60),
    "matrix-hap.gif": (matrix_hap, 70),
    "ates.gif": (ates, 60),
    "havai-fisek.gif": (havai_fisek, 70),
    "hiperuzay.gif": (yildizlar, 50),
    "plazma.gif": (plazma, 60),
    "hayat-oyunu.gif": (hayat_oyunu, 120),
    "ekolayzer.gif": (ekolayzer, 60),
    "kalp-ritmi.gif": (kalp_ritmi, 50),
}

import gif_ek_2  # noqa: E402  (21.10 ek GIF'ler: mevsimlik / oyun / film)
GIFLER.update(gif_ek_2.YENI)
import gif_ek_3  # noqa: E402  (22.10: akvaryum, fırtına, Dünya, kedi, DNA, atom)
GIFLER.update(gif_ek_3.YENI)

if __name__ == "__main__":
    klasor = Path(sys.argv[1] if len(sys.argv) > 1 else Path(__file__).with_name("gifler"))
    klasor.mkdir(exist_ok=True)
    for ad, (fn, ms) in GIFLER.items():
        kaydet(ad, fn(), ms, klasor)
