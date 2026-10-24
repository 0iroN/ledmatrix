"""Canlı "sahneler": HA'dan gelen veriyle anlık çizilen ekranlar (GIF değil).

Sahne başlarken matriste o an ne gösteriliyorsa ve şeridin WLED durumu SAKLANIR;
sahne bitince ikisi de geri yüklenir. Böylece 3D yazıcı baskısı bitince ekran
kendiliğinden eski GIF'ine, şerit eski efektine döner.
"""
import json
import os
import threading
import urllib.request

from PIL import Image

import font5x7
import goster

W, H = goster.VIEW_W, goster.VIEW_H
SERIT_SEG = 1
SERIT_LED = 144


def wled(ip: str, govde: dict | None = None, yol="/json/state") -> dict:
    req = urllib.request.Request(f"http://{ip}{yol}", method="POST" if govde else "GET",
                                 data=json.dumps(govde).encode() if govde else None,
                                 headers={"Content-Type": "application/json"})
    return json.loads(urllib.request.urlopen(req, timeout=3).read() or b"{}")


def iki_satir(ust: str, alt: str, renk_ust, renk_alt, cubuk: float | None = None, cubuk_renk=(0, 0, 0)):
    """32x16: üstte bir satır (y 0-6), altta bir satır (y 8-14), en altta isteğe bağlı
    1 piksellik ilerleme çubuğu (y 15)."""
    im = Image.new("RGB", (W, H))
    for metin, renk, y0 in ((ust, renk_ust, 0), (alt, renk_alt, 8)):
        if not metin:
            continue
        s = font5x7.render(metin, renk, 7)
        s = s.crop((0, 0, min(s.width, W), 7))
        im.paste(s, ((W - s.width) // 2, y0), s.convert("L").point(lambda v: 255 if v else 0))
    if cubuk is not None:
        dolu = round(W * max(0.0, min(1.0, cubuk)))
        for x in range(W):
            im.putpixel((x, 15), cubuk_renk if x < dolu else (12, 12, 12))
    return im


def sure_metni(saat: float) -> str:
    dk = max(0, round(saat * 60))
    return f"{dk // 60}:{dk % 60:02d}"


# Baskı durumu -> (renk, şerit rengi)
YAZICI_RENK = {
    "prepare": (255, 140, 0),
    "running": (40, 160, 255),
    "pause": (255, 210, 0),
    "finish": (0, 255, 60),
    "failed": (255, 0, 0),
}


# ---------------------------------------------------------------- bilgi döngüsü çizimleri
def saat_kareleri(simdi):
    """Üstte SS:DD (iki nokta yanıp söner), altta gün + tarih."""
    ust = simdi.strftime("%H:%M")
    alt = f"{simdi.day:02d}.{simdi.month:02d}"
    renk = (255, 170, 60)
    acik = iki_satir(ust, alt, renk, (120, 160, 255))
    kapali = iki_satir(ust.replace(":", " "), alt, renk, (120, 160, 255))
    return [(acik, 0.5), (kapali, 0.5)]


def _hava_ikonu(im, durum: str, x0=1, y0=2, t=0):
    """12x12 civarı piksel ikon; bilinmeyen durum = bulut. t = animasyon karesi (0-7)."""
    SARI, BEYAZ, GRI, MAVI, AY = (255, 200, 0), (230, 230, 240), (140, 140, 150), (60, 140, 255), (230, 230, 170)

    def p(x, y, c):
        if 0 <= x0 + x < W and 0 <= y0 + y < H:
            im.putpixel((x0 + x, y0 + y), c)

    def gunes(cx, cy, r=2):
        for y in range(-r, r + 1):
            for x in range(-r, r + 1):
                if x * x + y * y <= r * r + 1:
                    p(cx + x, cy + y, SARI)
        isinlar = ((0, -4), (0, 4), (-4, 0), (4, 0)) if t % 2 == 0 else ((-3, -3), (3, 3), (-3, 3), (3, -3))
        for dx, dy in isinlar:
            p(cx + dx, cy + dy, SARI)

    def bulut(cx, cy, c=BEYAZ):
        for x, y in [(-3, 1), (-2, 1), (-1, 1), (0, 1), (1, 1), (2, 1), (3, 1), (4, 1),
                     (-2, 0), (-1, 0), (0, 0), (1, 0), (2, 0), (3, 0), (-1, -1), (0, -1), (1, -1),
                     (2, -1), (0, -2), (1, -2)]:
            p(cx + x, cy + y, c)

    if durum == "sunny":
        gunes(5, 5)
    elif durum == "clear-night":
        for x, y in [(4, 2), (5, 2), (3, 3), (4, 3), (3, 4), (3, 5), (3, 6), (4, 7), (5, 7), (6, 7), (7, 6)]:
            p(x, y, AY)
        for i, (x, y) in enumerate([(9, 1), (10, 5), (7, 9)]):
            if (i + t) % 3:
                p(x, y, BEYAZ)
    elif durum == "partlycloudy":
        gunes(4, 4)
        bulut(6, 8)
    elif durum in ("rainy", "pouring", "lightning-rainy"):
        bulut(5, 3, GRI)
        for x, y in [(3, 6), (6, 7), (9, 6), (4, 9), (7, 10)]:
            p(x, 6 + (y - 6 + t) % 6, MAVI)
        if durum == "lightning-rainy":
            for x, y in [(6, 5), (5, 6), (6, 6), (5, 7)]:
                p(x, y, SARI)
    elif durum in ("snowy", "snowy-rainy"):
        bulut(5, 3, GRI)
        for x, y in [(3, 7), (6, 8), (9, 7), (4, 10), (8, 10)]:
            p(x + (t // 2) % 2, 6 + (y - 6 + t // 2) % 6, BEYAZ)
    elif durum == "fog":
        for y in (3, 5, 7, 9):
            for x in range(1 + (y % 4), 11):
                p(x, y, GRI)
    else:                                   # cloudy, windy ve bilinmeyenler
        bulut(5 + (t // 4) % 2, 5, GRI if durum == "cloudy" else BEYAZ)


def hava_karesi(durum: str, sicaklik):
    """8 karelik hareketli ikon (yağmur/kar düşer, güneş ışınları döner, yıldızlar kırpar)."""
    try:
        metin = f"{round(float(sicaklik))}°"
    except (TypeError, ValueError):
        metin = "?"
    s = font5x7.render(metin, (255, 255, 255), 7)
    kareler = []
    for t in range(8):
        im = Image.new("RGB", (W, H))
        _hava_ikonu(im, durum or "", t=t)
        im.paste(s, (W - s.width - 1, 5), s.convert("L").point(lambda v: 255 if v else 0))
        kareler.append((im, 0.25))
    return kareler


def pm25_rengi(v: float):
    """ABD EPA PM2.5 sınıflarına yakın eşikler: iyi / orta / hassas / kötü."""
    return ((0, 230, 60) if v <= 12 else (255, 210, 0) if v <= 35
            else (255, 120, 0) if v <= 55 else (255, 0, 0))


def pm25_karesi(deger):
    try:
        v = float(deger)
    except (TypeError, ValueError):
        return [(iki_satir("PM2.5", "?", (180, 180, 180), (180, 180, 180)), 1.0)]
    renk = pm25_rengi(v)
    return [(iki_satir("PM2.5", f"{round(v)}", (180, 180, 180), renk, min(1.0, v / 75), renk), 1.0)]


class Sahneler:
    """Oynatici'nin üstünde ince bir katman: sahne başlarken önceki içeriği saklar."""

    def __init__(self, oynatici, wled_ip: str):
        self.o = oynatici
        self.ip = wled_ip
        self.aktif = None                 # "yazici" ya da None
        self.onceki_matris = None         # (uretici, aciklama) ya da None (boştaydı)
        self.onceki_serit = None          # WLED segment 1 durumu (dict)
        self.zamanlayici = None
        self.lock = threading.Lock()
        # bilgi döngüsü
        self.bilgi = {}                   # HA'nın gönderdiği: hava, sicaklik, pm25
        self.dongu_acik = False
        self.dongu_bri = 0.3
        self.dongu_is = None
        self.gif_klasoru = None

    # ---------------------------------------------------------------- ortak
    # Yüksek sayı kazanır. Bilgi döngüsü sahne değildir: herhangi bir sahne varken bekler.
    ONCELIK = {"uyari": 4, "pomodoro": 3, "mesaj": 3, "oyun": 3, "yazici": 2, "gundogumu": 2}

    def _girebilir(self, ad: str) -> bool:
        return self.aktif is None or self.ONCELIK[ad] >= self.ONCELIK.get(self.aktif, 0)

    def _baslat(self, ad: str):
        """İlk kez giriliyorsa önceki matris + şerit durumunu sakla."""
        if self.aktif == ad:
            return
        if self.aktif is None:
            with self.o.lock:
                self.onceki_matris = ((self.o.uretici, self.o.aciklama)
                                      if self.o.uretici else None)
            try:
                seg = wled(self.ip)["seg"][SERIT_SEG]
                self.onceki_serit = {k: seg[k] for k in
                                     ("on", "bri", "fx", "pal", "sx", "ix", "col") if k in seg}
            except (OSError, KeyError, IndexError, ValueError) as e:
                print(f"şerit durumu okunamadı: {e}", flush=True)
                self.onceki_serit = None
        self.aktif = ad

    def bitir(self, bri: float):
        """Sahneden çık: matrisi ve şeridi eski hâline döndür."""
        with self.lock:
            if self.zamanlayici:
                self.zamanlayici.cancel()
                self.zamanlayici = None
            if self.aktif is None:
                return
            self.aktif = None
            if self.dongu_acik:
                pass                      # döngü açıksa matrisi döngü iş parçacığı yeniden çizer
            elif self.onceki_matris:
                uretici, aciklama = self.onceki_matris
                self.o.oynat(uretici, aciklama, bri)
            else:
                self.o.dur()
            if self.onceki_serit:
                try:
                    wled(self.ip, {"seg": [{"id": SERIT_SEG, "frz": False, **self.onceki_serit}]})
                except OSError as e:
                    print(f"şerit geri yüklenemedi: {e}", flush=True)
            self.onceki_matris = self.onceki_serit = None

    def _serit_cubuk(self, oran: float, renk, yanip_son=False):
        if yanip_son:      # bitti/hata: WLED'in kendi Blink efekti (fx 1), tek renk
            wled(self.ip, {"seg": [{"id": SERIT_SEG, "on": True, "frz": False, "fx": 1, "sx": 200,
                                    "col": [list(renk), [0, 0, 0], [0, 0, 0]]}]})
            return
        dolu = round(SERIT_LED * max(0.0, min(1.0, oran)))
        hexr = "%02X%02X%02X" % renk
        i = ([0, dolu, hexr] if dolu else []) + ([dolu, SERIT_LED, "0A0A0A"] if dolu < SERIT_LED else [])
        wled(self.ip, {"seg": [{"id": SERIT_SEG, "on": True, "i": i}]})

    # ---------------------------------------------------------------- uyarı (en yüksek öncelik)
    def uyari(self, seviye: str, metin: str, sure: float, bri: float) -> str:
        """Nöbetçi / bekçi uyarısı: matriste kırmızı kayan yazı, şerit kırmızı yanıp söner.
        `sure` saniye sonra (ya da seviye='temizle' gelince) eski hâline döner."""
        if seviye == "temizle":
            if self.aktif == "uyari":
                self.bitir(bri)
            return "uyarı temizlendi"
        renk = (255, 0, 0) if seviye == "kritik" else (255, 140, 0)
        with self.lock:
            self._baslat("uyari")
            if self.zamanlayici:
                self.zamanlayici.cancel()
        metin = (metin or "UYARI").strip()[:120]
        self.o.oynat(lambda b, m=metin, r=renk: goster.text_frames("! " + m + " !", b, r, step_s=0.05),
                     f"uyarı: {metin}", bri)
        try:
            self._serit_cubuk(1.0, renk, yanip_son=True)
        except OSError as e:
            print(f"şerit uyarısı yazılamadı: {e}", flush=True)
        with self.lock:
            self.zamanlayici = threading.Timer(max(10.0, min(3600.0, sure)), self.bitir, args=(bri,))
            self.zamanlayici.daemon = True
            self.zamanlayici.start()
        return f"uyarı: {metin}"

    # ---------------------------------------------------------------- 3D yazıcı
    def yazici(self, durum: str, yuzde: float, kalan_saat: float, bri: float) -> str:
        durum = (durum or "").lower()
        if not self._girebilir("yazici"):  # uyarı / pomodoro / mesaj sürerken araya girmez
            return f"{self.aktif} sürüyor, yazıcı bekliyor"
        with self.lock:
            if durum in ("idle", "offline", "unknown", "unavailable", ""):
                aktif = self.aktif == "yazici"
            else:
                aktif = None
        if aktif is not None:          # baskı yok: sahnedeysek çık
            if aktif:
                self.bitir(bri)
            return "yazıcı boşta"
        with self.lock:
            self._baslat("yazici")
            if self.zamanlayici:
                self.zamanlayici.cancel()
                self.zamanlayici = None
        renk = YAZICI_RENK.get(durum, (200, 200, 200))
        oran = yuzde / 100
        if durum == "finish":
            ust, alt = "BITTI", "%100"
        elif durum == "failed":
            ust, alt = "HATA", f"%{int(yuzde)}"
        elif durum == "pause":
            ust, alt = f"%{int(yuzde)}", "DURDU"
        elif durum == "prepare":
            ust, alt = "ISIN", sure_metni(kalan_saat) if kalan_saat else ""   # ısınma/kalibrasyon
        else:
            ust, alt = f"%{int(yuzde)}", sure_metni(kalan_saat)
        bitis = durum in ("finish", "failed")

        def uret(b, ust=ust, alt=alt, renk=renk, oran=oran, bitis=bitis):
            kare = iki_satir(ust, alt, renk, (230, 230, 230), oran, renk)
            if not bitis:
                return [(goster.view_to_bytes(kare, b), 1.0)]
            # bitti/hata: yazı yanıp söner
            return [(goster.view_to_bytes(kare, b), 0.5),
                    (goster.view_to_bytes(Image.new("RGB", (W, H)), b), 0.3)]

        self.o.oynat(uret, f"3D yazıcı: {durum} %{int(yuzde)}", bri)
        try:
            self._serit_cubuk(oran, renk, yanip_son=bitis)
        except OSError as e:
            print(f"şerit çubuğu yazılamadı: {e}", flush=True)
        if bitis:                      # 2 dk göster, sonra eski hâline dön
            with self.lock:
                self.zamanlayici = threading.Timer(120, self.bitir, args=(bri,))
                self.zamanlayici.daemon = True
                self.zamanlayici.start()
        return f"yazıcı: {durum} %{int(yuzde)}"

    # ---------------------------------------------------------------- bilgi döngüsü
    SAYFALAR = (("saat", 10), ("hava", 6), ("pm25", 6), ("takvim", 8), ("saglik", 6),
                ("minecraft", 5), ("gif", 15))     # süre: en az; kayan yazı bitene kadar uzar
    GECE = (23, 7)              # 23:00-07:00 arası parlaklık GECE_CARPAN ile kısılır
    GECE_CARPAN = 0.25

    def dongu_baslat(self, bri: float, gif_klasoru, sayfalar=None):
        """sayfalar: {"saat": 10, "minecraft": 0, ...} — 0 = kapalı; verilmeyen sayfa varsayılanını korur."""
        self.dongu_bri, self.gif_klasoru = bri, gif_klasoru
        if isinstance(sayfalar, dict):
            varsayilan = dict(type(self).SAYFALAR)
            self.SAYFALAR = tuple((ad, max(0.0, float(sayfalar.get(ad, sure)))) for ad, sure in varsayilan.items())
        self.dongu_acik = True
        if not (self.dongu_is and self.dongu_is.is_alive()):
            self.dongu_is = threading.Thread(target=self._dongu, daemon=True)
            self.dongu_is.start()

    def dongu_durdur(self):
        self.dongu_acik = False

    def _bri(self):
        import datetime
        s = datetime.datetime.now().hour
        gece = s >= self.GECE[0] or s < self.GECE[1]
        return self.dongu_bri * (self.GECE_CARPAN if gece else 1.0)

    def _sayfa(self, ad):
        """[(32x16 görüntü, süre)] ya da None (veri yoksa sayfa atlanır)."""
        import datetime
        import random
        if ad == "saat":
            return saat_kareleri(datetime.datetime.now())
        if ad == "hava" and self.bilgi.get("hava") not in (None, "", "unknown", "unavailable"):
            return hava_karesi(self.bilgi["hava"], self.bilgi.get("sicaklik"))
        if ad == "pm25" and self.bilgi.get("pm25") not in (None, "", "unknown", "unavailable"):
            return pm25_karesi(self.bilgi["pm25"])
        if ad == "takvim":
            return self._takvim_sayfasi()
        if ad == "saglik":
            return saglik_sayfasi()
        if ad == "minecraft":
            return self._minecraft_sayfasi()
        if ad == "gif" and self.gif_klasoru:
            haric = set()
            try:                                     # editör/yükleme sayfasından düzenlenen hariç listesi
                haric = set(json.loads((self.gif_klasoru / "dongu_disi.json").read_text(encoding="utf-8")))
            except (OSError, ValueError):
                pass
            dosyalar = [p for p in self.gif_klasoru.iterdir()
                        if p.suffix.lower() == ".gif" and p.name not in haric]
            if dosyalar:
                return goster.view_frames(str(random.choice(dosyalar)))
        return None

    def _dongu(self):
        import time
        while self.dongu_acik:
            if not any(s > 0 for _, s in self.SAYFALAR):
                time.sleep(2)
                continue
            for ad, sure in self.SAYFALAR:
                if not self.dongu_acik:
                    break
                if sure <= 0:                       # HA'dan kapatılmış sayfa
                    continue
                if self.aktif is not None:          # yazıcı sahnesi öncelikli
                    time.sleep(2)
                    continue
                try:
                    kareler = self._sayfa(ad)
                except Exception as e:              # tek sayfa bozuk diye döngü ölmesin
                    print(f"döngü sayfası '{ad}' çizilemedi: {e}", flush=True)
                    kareler = None
                if not kareler:
                    continue
                self.o.oynat(lambda b, kv=kareler: [(goster.view_to_bytes(v, b), d) for v, d in kv],
                             f"döngü: {ad}", self._bri())
                bitis = time.monotonic() + max(sure, sum(d for _, d in kareler))
                while self.dongu_acik and self.aktif is None and time.monotonic() < bitis:
                    time.sleep(0.25)

    # ---------------------------------------------------------------- zamanlı sahneler
    def _calistir(self, ad: str, adim, sure_sn: float, bitis_bekle: float = 0.0, bri: float = 0.3):
        """`adim(gecen_sn, toplam_sn)` her saniye çağrılır (matris + şerit çizer).
        Süre bitince `bitis_bekle` sn daha son hâli tutar, sonra eski hâline döner.
        Başka bir sahne araya girerse (aktif değişirse) iş parçacığı kendiliğinden biter."""
        import time

        def dongu():
            bas = time.monotonic()
            while self.aktif == ad:
                gecen = time.monotonic() - bas
                if gecen >= sure_sn + bitis_bekle:
                    if self.aktif == ad:
                        self.bitir(bri)
                    return
                try:
                    adim(min(gecen, sure_sn), sure_sn)
                except Exception as e:          # tek kare bozuk diye sahne ölmesin
                    print(f"{ad} adımı çizilemedi: {e}", flush=True)
                time.sleep(1.0)

        threading.Thread(target=dongu, daemon=True).start()

    def _matris_tek(self, im, aciklama, bri):
        self.o.oynat(lambda b, im=im: [(goster.view_to_bytes(im, b), 1.0)], aciklama, bri)

    def pomodoro(self, calisma_dk: float, mola_dk: float, bri: float) -> str:
        """Odak sayacı: turuncu geri sayım (çalışma), sonra yeşil geri sayım (mola).
        Şerit kalan süre kadar dolu; aşama değişince 3 sn yanıp söner."""
        if calisma_dk <= 0:
            if self.aktif == "pomodoro":
                self.bitir(bri)
            return "pomodoro durduruldu"
        if not self._girebilir("pomodoro"):
            return f"{self.aktif} sürüyor"
        with self.lock:
            self._baslat("pomodoro")
        cal, mol = calisma_dk * 60, max(0.0, mola_dk) * 60
        durum = {"asama": None}

        def adim(gecen, toplam):
            if gecen < cal:
                asama, kalan, uzunluk, renk = "ODAK", cal - gecen, cal, (255, 120, 0)
            else:
                asama, kalan, uzunluk, renk = "MOLA", toplam - gecen, mol or 1, (0, 220, 80)
            kalan = max(0, kalan)
            dk, sn = int(kalan // 60), int(kalan % 60)
            self._matris_tek(iki_satir(f"{dk:02d}:{sn:02d}", asama, renk, (200, 200, 200),
                                       kalan / uzunluk, renk), f"pomodoro: {asama} {dk:02d}:{sn:02d}", bri)
            if durum["asama"] != asama:            # aşama değişti: kısa yanıp sönme
                durum["asama"] = asama
                self._serit_cubuk(1.0, renk, yanip_son=True)
                durum["flas"] = gecen
            elif gecen - durum.get("flas", 0) >= 3 and int(gecen) % 5 == 0:
                self._serit_cubuk(kalan / uzunluk, renk)

        self._calistir("pomodoro", adim, cal + mol, bitis_bekle=3, bri=bri)
        return f"pomodoro: {calisma_dk:g} dk odak + {mola_dk:g} dk mola"

    def mesaj(self, metin: str, tekrar: int, bri: float) -> str:
        """Geçici mesaj: sarı kayan yazı `tekrar` kez geçer, şerit sarı nabız atar, sonra
        eski hâline döner (kalıcı 'Yazı'dan farkı bu)."""
        metin = (metin or "").strip()[:120]
        if not metin:
            raise ValueError("metin boş")
        if not self._girebilir("mesaj"):
            return f"{self.aktif} sürüyor"
        with self.lock:
            self._baslat("mesaj")
        kareler = goster.text_frames(metin, 1.0, (255, 200, 0), step_s=0.05)
        bir_tur = sum(d for _, d in kareler)
        self.o.oynat(lambda b, m=metin: goster.text_frames(m, b, (255, 200, 0), step_s=0.05),
                     f"mesaj: {metin}", bri)
        try:
            wled(self.ip, {"seg": [{"id": SERIT_SEG, "on": True, "frz": False, "fx": 2, "sx": 160,
                                    "col": [[255, 200, 0], [0, 0, 0], [0, 0, 0]]}]})   # fx 2 = Breathe
        except OSError as e:
            print(f"şerit mesaj nabzı yazılamadı: {e}", flush=True)
        self._calistir("mesaj", lambda g, t: None, bir_tur * max(1, min(10, tekrar)), bri=bri)
        return f"mesaj: {metin}"

    def gundogumu(self, dakika: float, bri: float) -> str:
        """Sabah ışığı: şerit `dakika` boyunca koyu kırmızıdan turuncuya, sonra sıcak beyaza
        yavaşça açılır; matriste yükselen güneş. Bitince 15 dk sıcak beyaz kalır."""
        if dakika <= 0:
            if self.aktif == "gundogumu":
                self.bitir(bri)
            return "gün doğumu durduruldu"
        if not self._girebilir("gundogumu"):
            return f"{self.aktif} sürüyor"
        with self.lock:
            self._baslat("gundogumu")
        DURAK = [(0.0, (40, 0, 0)), (0.35, (255, 40, 0)), (0.7, (255, 140, 30)), (1.0, (255, 220, 160))]

        def renk(f):
            for (a, ca), (b, cb) in zip(DURAK, DURAK[1:]):
                if f <= b:
                    t = (f - a) / (b - a)
                    return tuple(int(x + (y - x) * t) for x, y in zip(ca, cb))
            return DURAK[-1][1]

        def adim(gecen, toplam):
            f = gecen / toplam
            c = renk(f)
            im = Image.new("RGB", (W, H))
            ufuk = 15 - int(f * 9)                       # güneş yükselir
            for y in range(H):
                for x in range(W):
                    gok = max(0.0, 1 - abs(y - ufuk) / 10) * f
                    im.putpixel((x, y), tuple(int(v * gok * 0.5) for v in c))
                    if (x - 15.5) ** 2 + (y - ufuk) ** 2 <= 9:
                        im.putpixel((x, y), (255, int(150 + 100 * f), int(60 * f)))
            self._matris_tek(im, f"gün doğumu %{int(f * 100)}", bri * (0.2 + 0.8 * f))
            if int(gecen) % 5 == 0:
                wled(self.ip, {"seg": [{"id": SERIT_SEG, "on": True, "frz": False, "fx": 0,
                                        "bri": max(1, int(255 * f)), "col": [list(c), [0, 0, 0], [0, 0, 0]]}]})

        self._calistir("gundogumu", adim, dakika * 60, bitis_bekle=15 * 60, bri=bri)
        return f"gün doğumu: {dakika:g} dk"

    # ---------------------------------------------------------------- takvim / minecraft sayfaları
    def _takvim_sayfasi(self):
        """Sıradaki (tamamlanmamış) takvim kapısı: kayan yazı, yeşil > 3 gün, sarı <= 3, kırmızı
        bugün/gecikti. Gecikmede günde bir kez uyarı sahnesi (Telegram'ı heartbeat atar)."""
        import datetime
        bugun = datetime.date.today()
        bekleyen = [k for k in self.bilgi.get("kapilar") or [] if not k.get("tamam") and k.get("son")]
        if not bekleyen:
            return None
        k = min(bekleyen, key=lambda k: k["son"])
        son = datetime.date.fromisoformat(k["son"])
        kalan = (son - bugun).days
        ad = str(k.get("ad", "?")).upper()       # .upper(): ASCII 'i' -> 'I' (font İ'ye çevirmesin)
        if kalan > 0:
            metin, renk = f"{ad} {son:%d.%m}: {kalan} GÜN", (0, 220, 80) if kalan > 3 else (255, 200, 0)
        elif kalan == 0:
            metin, renk = f"{ad}: SON GÜN BUGÜN", (255, 60, 0)
        else:
            metin, renk = f"{ad}: {-kalan} GÜN GECİKTİ", (255, 0, 0)
            if getattr(self, "_takvim_uyari_gunu", None) != bugun:
                self._takvim_uyari_gunu = bugun
                threading.Thread(target=self.uyari, args=("kritik", "GECİKEN ADIM: " + ad, 120, self.dongu_bri),
                                 daemon=True).start()
        return kayan_kareler(metin, renk)

    def _minecraft_sayfasi(self):
        """ATM11 sunucusu: 'MC' + oyuncu/kapasite. Sunucu kapalıysa sayfa atlanır.
        Oyuncu sayısı artınca önce Creeper animasyonu bir kez oynar."""
        durum = mc_ping(os.environ.get("MC_HOST", "127.0.0.1"), int(os.environ.get("MC_PORT", "25565")))
        if not durum:
            return None
        cevrim, azami = durum
        kare = iki_satir("MC", f"{cevrim}/{azami}", (90, 200, 60), (230, 230, 230) if cevrim else (120, 120, 120))
        kareler = [(kare, 1.0)]
        onceki = getattr(self, "_mc_onceki", None)
        self._mc_onceki = cevrim
        creeper = self.gif_klasoru / "minecraft-creeper.gif" if self.gif_klasoru else None
        if onceki is not None and cevrim > onceki and creeper and creeper.exists():
            kareler = goster.view_frames(str(creeper)) + kareler
        return kareler

    # ---------------------------------------------------------------- yılan oyunu
    def yilan_basla(self, bri: float) -> str:
        """Telefondan oynanan yılan: kenarlardan sarılır, kendine çarpınca biter; 90 sn
        dokunulmazsa kendiliğinden kapanır. Şerit puanı gösterir (yem başına dolar)."""
        import random
        import time
        if not self._girebilir("oyun"):
            return f"{self.aktif} sürüyor"
        with self.lock:
            self._baslat("oyun")
        oyun = {"govde": [(10, 8), (9, 8), (8, 8)], "yon": (1, 0), "siradaki": (1, 0),
                "yem": (20, 8), "puan": 0, "son_dokunus": time.monotonic()}
        self.oyun = oyun

        def yeni_yem():
            bos = [(x, y) for x in range(W) for y in range(H) if (x, y) not in oyun["govde"]]
            return random.choice(bos)

        def ciz():
            im = Image.new("RGB", (W, H))
            im.putpixel(oyun["yem"], (255, 30, 30))
            for i, (x, y) in enumerate(oyun["govde"]):
                im.putpixel((x, y), (120, 255, 120) if i == 0 else (0, 170, 60))
            self._matris_tek(im, f"yılan: {oyun['puan']} puan", bri)

        def dongu():
            while self.aktif == "oyun":
                if time.monotonic() - oyun["son_dokunus"] > 90:
                    break
                oyun["yon"] = oyun["siradaki"]
                hx, hy = oyun["govde"][0]
                bas = ((hx + oyun["yon"][0]) % W, (hy + oyun["yon"][1]) % H)
                if bas in oyun["govde"][:-1]:
                    break
                oyun["govde"].insert(0, bas)
                if bas == oyun["yem"]:
                    oyun["puan"] += 1
                    oyun["yem"] = yeni_yem()
                    try:
                        self._serit_cubuk(min(1.0, oyun["puan"] / 30), (0, 220, 80))
                    except OSError:
                        pass
                else:
                    oyun["govde"].pop()
                ciz()
                time.sleep(max(0.08, 0.2 - oyun["puan"] * 0.004))     # yedikçe hızlanır
            if self.aktif == "oyun":
                self._matris_tek(iki_satir("SKOR", str(oyun["puan"]), (255, 200, 0), (255, 255, 255)),
                                 f"yılan bitti: {oyun['puan']}", bri)
                time.sleep(3)
                if self.aktif == "oyun":
                    self.bitir(bri)

        ciz()
        threading.Thread(target=dongu, daemon=True).start()
        return "yılan başladı"

    def yilan_yon(self, yon: str) -> str:
        """u/d/l/r — kendi üstüne geri dönüş (180°) yok sayılır."""
        import time
        oyun = getattr(self, "oyun", None)
        if self.aktif != "oyun" or not oyun:
            return "oyun yok"
        y = {"u": (0, -1), "d": (0, 1), "l": (-1, 0), "r": (1, 0)}.get(yon)
        if y and (y[0] + oyun["yon"][0], y[1] + oyun["yon"][1]) != (0, 0):
            oyun["siradaki"] = y
        oyun["son_dokunus"] = time.monotonic()
        return "tamam"


def kayan_kareler(metin: str, renk, adim_s: float = 0.05):
    """Yatay 32x16 görüntü olarak sağdan sola kayan yazı (32'ye sığarsa ortalanmış tek kare)."""
    serit = font5x7.render(metin, renk, H)
    if serit.width <= W:
        im = Image.new("RGB", (W, H))
        im.paste(serit, ((W - serit.width) // 2, 0))
        return [(im, 1.0)]
    bant = Image.new("RGB", (serit.width + 2 * W, H))
    bant.paste(serit, (W, 0))
    return [(bant.crop((x, 0, x + W, H)), adim_s) for x in range(serit.width + W)]


def saglik_sayfasi():
    """Pi + Excalibur: 'PI35°' / 'EX52°'. Sıcaklık < 60 yeşil, < 75 sarı, üstü kırmızı;
    çevrimdışı ya da disk >= %90 -> kırmızı. Veri: aynı Pi'deki vitals paneli."""
    try:
        d = json.loads(urllib.request.urlopen("http://127.0.0.1:8700/api/hosts", timeout=3).read())
    except (OSError, ValueError):
        return None
    satirlar = []
    for h in d.get("hosts", [])[:2]:
        kisa = {"pi": "PI", "excalibur": "EX"}.get(h.get("host_id"), str(h.get("host_id", "?"))[:2].upper())
        son = h.get("latest") or {}
        sicak = (son.get("cpu") or {}).get("temp_c")
        disk = max([x.get("percent", 0) for x in son.get("disks", [])[:1]] or [0])
        if not h.get("online") or sicak is None:
            satirlar.append((f"{kisa}---", (255, 0, 0)))
            continue
        renk = (0, 220, 80) if sicak < 60 else (255, 200, 0) if sicak < 75 else (255, 0, 0)
        if disk >= 90:
            renk = (255, 0, 0)
        satirlar.append((f"{kisa}{round(sicak)}°", renk))
    if not satirlar:
        return None
    ust = satirlar[0]
    alt = satirlar[1] if len(satirlar) > 1 else ("", (0, 0, 0))
    return [(iki_satir(ust[0], alt[0], ust[1], alt[1]), 1.0)]


def mc_ping(host: str, port: int, timeout: float = 3.0):
    """Minecraft 'server list ping' (1.7+ durum protokolü) -> (çevrimiçi, azami) ya da None."""
    import socket
    import struct

    def varint(n):
        out = b""
        while True:
            b = n & 0x7F
            n >>= 7
            out += bytes([b | (0x80 if n else 0)])
            if not n:
                return out

    def oku_varint(s):
        n = sayi = 0
        while True:
            b = s.recv(1)
            if not b:
                raise OSError("bağlantı kapandı")
            n |= (b[0] & 0x7F) << (7 * sayi)
            sayi += 1
            if not b[0] & 0x80:
                return n

    try:
        with socket.create_connection((host, port), timeout=timeout) as s:
            s.settimeout(timeout)
            h = host.encode()
            el = b"\x00" + varint(767) + varint(len(h)) + h + struct.pack(">H", port) + varint(1)
            s.sendall(varint(len(el)) + el + b"\x01\x00")
            uzunluk = oku_varint(s)
            veri = b""
            while len(veri) < uzunluk:
                parca = s.recv(uzunluk - len(veri))
                if not parca:
                    break
                veri += parca
        i = 1                                       # paket id (0x00) atla
        n = sayi = 0
        while True:                                 # json uzunluğu (varint)
            b = veri[i]
            i += 1
            n |= (b & 0x7F) << (7 * sayi)
            sayi += 1
            if not b & 0x80:
                break
        oyuncular = json.loads(veri[i:i + n].decode("utf-8", "replace")).get("players", {})
        return int(oyuncular.get("online", 0)), int(oyuncular.get("max", 0))
    except (OSError, ValueError, IndexError):
        return None
