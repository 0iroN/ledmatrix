"""LED matris servisi — HA'dan gelen komutları DDP karelerine çevirir (Pi'de çalışır).

Uçlar (hepsi JSON):
  GET  /liste                 -> {"dosyalar": [...]}  resimler/ klasöründeki resim/GIF'ler
  GET  /durum                 -> şu an ne gösteriliyor
  GET  /saglik                -> 200 servis + WLED cevap veriyor, 503 ESP32'ye ulaşılamıyor
                                 (araçlar sitesindeki Matrix Led rozeti bunu yoklar)
  POST /goster  {"dosya": "kedi.gif", "parlaklik": 0.3}
  POST /yazi    {"metin": "MERHABA", "renk": "ff8c00"}
  POST /renk    {"renk": "ff0000"}
  POST /parlaklik {"parlaklik": 0.5}  -> gösterileni yeni parlaklıkla yeniden üretir
  POST /dur                   -> gönderimi keser; WLED ~2,5 sn sonra kendi efektine döner
  PUT  /yukle?ad=kedi.gif     -> gövde = dosyanın baytları (GET / sayfası bunu kullanır)
  GET  /editor                -> LED çizim/önizleme editörü (editor.html)
  GET  /yilan                 -> telefondan yılan oyunu (yilan.html); POST /oyun/basla, /oyun/yon {"yon": u|d|l|r}, /oyun/bitir
  GET  /onizleme?dosya=x.gif  -> dosyanın ekranda görüneceği 32x16 kareler (hex)
  POST /piksel  {"frames": [{"px": hex, "dur": s}], "parlaklik": 0.3}  -> panelde göster
  POST /kaydet  {"ad": "cizim", "frames": [...], "uzerine_yaz": false} -> resimler/'e PNG/GIF
  POST /sahne/yazici {"durum": "running", "yuzde": 47, "kalan_saat": 1.2, "parlaklik": 0.3}
                -> 3D yazıcı sahnesi (sahne.py); idle gelince eski içerik + şerit geri döner
  POST /sahne/uyari {"seviye": "kritik"|"uyari"|"temizle", "metin": "...", "sure": 300}
                -> kırmızı kayan yazı + şerit yanıp söner; nöbetçi ve Pi bekçisi çağırır
  POST /sahne/pomodoro {"dakika": 25, "mola": 5}   (dakika 0 = durdur)
  POST /sahne/mesaj    {"metin": "...", "tekrar": 3} -> geçici sarı kayan yazı, sonra eski hâl
  POST /sahne/gundogumu {"dakika": 20}               -> sabah ışığı (dakika 0 = durdur)
  GET/POST /dongu/gifler {"dosya", "dongude"} -> bilgi döngüsünün rastgele GIF havuzu (hariç liste)
                {"hepsi": true|false} -> hepsini döngüye al / hepsini çıkar
  POST /bilgi   {"hava": "sunny", "sicaklik": 14.2, "pm25": 9}  -> döngü sayfalarının verisi
  POST /sahne/dongu {"acik": true, "parlaklik": 0.3} -> saat / hava / PM2.5 / rastgele GIF
                döngüsü (gece 23-07 kısık); elle seçilen içerik döngüyü kapatır

Bir gösterim başlayınca DUR denene ya da yenisi gelene kadar sürer (süre yok).
Yalnız LAN ve WireGuard VPN'den erişilir (ufw: yerel ağ + VPN).
Kimlik doğrulama YOK.
"""
import json
import os
import re
import threading
import time
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from PIL import Image

import goster
import sahne
from ddp import DDPSender
from harita import HEIGHT, WIDTH, frame_to_bytes

WLED_IP = os.environ.get("WLED_IP", "wled.local")
PORT = int(os.environ.get("PORT", "8790"))
RESIM_DIR = Path(os.environ.get("RESIM_DIR", Path(__file__).with_name("resimler")))
UZANTILAR = {".png", ".gif", ".jpg", ".jpeg", ".webp", ".bmp"}
MAX_YUKLEME = 10 * 1024 * 1024
EDITOR = Path(__file__).with_name("editor.html")
YILAN = Path(__file__).with_name("yilan.html")
VARSAYILAN_PARLAKLIK = 0.3


class Oynatici:
    """Tek bir arka plan iş parçacığı: elindeki kareleri döngüde gönderir."""

    def __init__(self, ip: str):
        self.sender = DDPSender(ip)
        self.lock = threading.Lock()
        self.frames = None          # [(rgb, süre), ...] ya da None = sus
        self.uretici = None         # parlaklik -> frames; parlaklık değişince yeniden üretmek için
        self.aciklama = "boşta"
        self.surum = 0              # her yeni gösterimde artar, eski döngüyü keser
        threading.Thread(target=self._dongu, daemon=True).start()

    def oynat(self, uretici, aciklama: str, bri: float):
        frames = uretici(bri)       # kilit dışında: büyük GIF'te saniyeler sürebilir
        wled_hazirla()
        with self.lock:
            self.frames, self.uretici, self.aciklama = frames, uretici, aciklama
            self.surum += 1

    def parlaklik(self, bri: float) -> bool:
        """Gösterilen içeriği yeni parlaklıkla yeniden üretir; boştaysa False."""
        with self.lock:
            uretici, aciklama = self.uretici, self.aciklama
        if uretici is None:
            return False
        self.oynat(uretici, aciklama, bri)
        return True

    def dur(self):
        with self.lock:
            self.frames, self.uretici, self.aciklama = None, None, "boşta"
            self.surum += 1

    def _dongu(self):
        while True:
            with self.lock:
                frames, surum = self.frames, self.surum
            if not frames:
                time.sleep(0.1)
                continue
            for rgb, dur in frames:
                if self.surum != surum:
                    break
                self.sender.send_frame(rgb)
                # durağan karede de tazele: WLED veri kesilince gerçek zamanlı moddan çıkar
                time.sleep(min(dur, 1.0))


def wled_hazirla():
    """WLED'de "yalnız ana segment" (if.live.mso) açık: şerit ayrı segmentte kendi efektini
    sürdürsün diye. Bu modda gerçek zamanlı kare segment karışımından geçer, yani WLED'in
    ANA aç/kapa ve ana parlaklığı matrisi de etkiler (19.10 ölçüldü: bri 255 -> 5000 mA,
    64 -> 2367 mA, kapalı -> sönük). Parlaklığı biz yönettiğimiz için göstermeden önce
    ana anahtar açık + tam parlaklık + matris segmenti açık. Şeridin kendi açık/kapalı
    durumuna (segment 1) DOKUNULMAZ."""
    try:
        req = urllib.request.Request(
            f"http://{WLED_IP}/json/state", method="POST",
            data=json.dumps({"on": True, "bri": 255, "seg": [{"id": 0, "on": True}]}).encode(),
            headers={"Content-Type": "application/json"})
        urllib.request.urlopen(req, timeout=2).read()
    except OSError as e:  # WLED geçici yoksa gösterim yine denensin
        print(f"WLED hazırlanamadı: {e}", flush=True)


def hex_renk(s: str):
    s = (s or "").strip().lstrip("#")
    if not re.fullmatch(r"[0-9a-fA-F]{6}", s):
        raise ValueError(f"renk 6 haneli hex olmalı, gelen: {s!r}")
    return tuple(int(s[i:i + 2], 16) for i in (0, 2, 4))


def sayi(v) -> float:
    """HA durumları metin gelir; 'unknown'/'unavailable'/boş -> 0."""
    try:
        return float(v)
    except (TypeError, ValueError):
        return 0.0


def parlaklik(d: dict) -> float:
    return max(0.0, min(1.0, float(d.get("parlaklik", VARSAYILAN_PARLAKLIK))))


def guvenli_ad(ad: str) -> Path:
    """Yol gezintisini (../) engeller, yalnız resimler/ altındaki düz dosya adı."""
    ad = os.path.basename(ad or "")
    p = RESIM_DIR / ad
    if not ad or p.suffix.lower() not in UZANTILAR:
        raise ValueError(f"geçersiz dosya adı: {ad!r}")
    return p


def liste():
    return sorted(p.name for p in RESIM_DIR.iterdir()
                  if p.is_file() and p.suffix.lower() in UZANTILAR)


def dongu_disi() -> set:
    try:
        return set(json.loads((RESIM_DIR / "dongu_disi.json").read_text(encoding="utf-8")))
    except (OSError, ValueError):
        return set()


def dongu_disi_yaz(haric: set):
    tmp = RESIM_DIR / "dongu_disi.json.tmp"
    tmp.write_text(json.dumps(sorted(haric), ensure_ascii=False), encoding="utf-8")
    os.replace(tmp, RESIM_DIR / "dongu_disi.json")


# Editör kare biçimi: {"px": "rrggbb" * 512 (yatay 32x16, satır satır, sol üstten),
#                      "dur": saniye}
MAX_KARE = 200
VW, VH = goster.VIEW_W, goster.VIEW_H


def kare_to_hex(img: Image.Image) -> str:
    return img.convert("RGB").tobytes().hex()


def hex_to_kare(px: str) -> Image.Image:
    if not isinstance(px, str) or not re.fullmatch(r"[0-9a-fA-F]{%d}" % (VW * VH * 6), px):
        raise ValueError(f"px {VW * VH * 6} haneli hex olmalı")
    return Image.frombytes("RGB", (VW, VH), bytes.fromhex(px))


def kareler_oku(d: dict):
    kareler = d.get("frames")
    if not isinstance(kareler, list) or not 1 <= len(kareler) <= MAX_KARE:
        raise ValueError(f"frames 1-{MAX_KARE} kare olmalı")
    return [(hex_to_kare(k.get("px")), max(0.02, min(10.0, float(k.get("dur", 0.1)))))
            for k in kareler]


def kaydet(ad: str, kareler, uzerine_yaz: bool) -> Path:
    """Tek kare -> PNG, çok kare -> GIF. Tam 32x16 kaydedilir = piksel sanatı,
    gösterilirken hiçbir işleme uğramaz (goster.is_pixel_art)."""
    kok = Path(os.path.basename(ad or "")).stem
    kok = re.sub(r"[^\w\-. ]", "_", kok).strip() or "cizim"
    p = RESIM_DIR / (kok + (".png" if len(kareler) == 1 else ".gif"))
    if p.exists() and not uzerine_yaz:
        raise FileExistsError(p.name)
    tmp = p.with_suffix(p.suffix + ".tmp")
    if len(kareler) == 1:
        kareler[0][0].save(tmp, "PNG")
    else:
        imgs = [k for k, _ in kareler]
        imgs[0].save(tmp, "GIF", save_all=True, append_images=imgs[1:], loop=0,
                     duration=[int(s * 1000) for _, s in kareler], optimize=False, disposal=1)
    os.replace(tmp, p)
    return p


SAYFA = """<!doctype html><meta charset=utf-8><meta name=viewport content="width=device-width,initial-scale=1">
<title>Matrix Led — dosyalar</title>
<style>body{font-family:system-ui,sans-serif;max-width:560px;margin:1.5em auto;padding:0 16px;background:#141414;color:#e6e6e6}
a{color:#4aa3d0}button{background:#262626;color:#eee;border:1px solid #3a3a3a;border-radius:7px;padding:5px 10px}
li{display:flex;align-items:center;gap:8px;padding:6px 0;border-bottom:1px solid #262626}li span{flex:1;word-break:break-all}
label{font-size:13px;color:#aaa;white-space:nowrap}.k{color:#888;font-size:13px}</style>
<h2>Matrix Led — dosyalar</h2>
<p><a href="/editor">→ Çizim / önizleme editörü</a> · <a href="/yilan">→ Yılan</a></p>
<input type=file id=f accept="image/*" multiple> <button onclick=yukle()>Yükle</button>
<p id=s class=k></p>
<p class=k>"döngüde" işaretli GIF'ler bilgi döngüsünün rastgele GIF sayfasında çıkar. İşareti kaldırınca dosya silinmez, yalnız döngüye girmez.</p>
<p><button onclick="hepsi(true)">Tüm GIF'leri döngüye al</button> <button onclick="hepsi(false)">Hepsini çıkar</button></p>
<ul id=l style="list-style:none;padding:0"></ul>
<script>
const post=(y,b)=>fetch(y,{method:'POST',body:JSON.stringify(b)}).then(r=>r.json());
async function yenile(){const d=(await (await fetch('/liste')).json()).dosyalar;
 const g=Object.fromEntries((await (await fetch('/dongu/gifler')).json()).gifler.map(x=>[x.dosya,x.dongude]));
 l.replaceChildren(...d.map(ad=>{const li=document.createElement('li');const sp=document.createElement('span');sp.textContent=ad;
  const b=document.createElement('button');b.textContent='göster';b.onclick=()=>post('/goster',{dosya:ad});li.append(sp,b);
  if(ad in g){const lb=document.createElement('label');const c=document.createElement('input');c.type='checkbox';c.checked=g[ad];
   c.onchange=async()=>{const r=await post('/dongu/gifler',{dosya:ad,dongude:c.checked});s.textContent=ad+(r.dongude?' döngüye alındı':' döngüden çıkarıldı')};
   lb.append(c,' döngüde');li.append(lb)}return li}))}
async function hepsi(v){for(const c of l.querySelectorAll('input[type=checkbox]')){if(c.checked!==v){c.checked=v;await c.onchange()}}}
async function yukle(){for(const x of f.files){s.textContent='yükleniyor: '+x.name;
 const r=await fetch('/yukle?ad='+encodeURIComponent(x.name),{method:'PUT',body:x});
 s.textContent=r.ok?'tamam: '+x.name:'hata: '+await r.text()}yenile()}
yenile()</script>"""


class Handler(BaseHTTPRequestHandler):
    def _yanit(self, kod, govde, tip="application/json; charset=utf-8"):
        veri = govde if isinstance(govde, bytes) else json.dumps(govde, ensure_ascii=False).encode()
        self.send_response(kod)
        self.send_header("Content-Type", tip)
        self.send_header("Content-Length", str(len(veri)))
        self.end_headers()
        self.wfile.write(veri)

    def _govde(self, limit=64 * 1024) -> bytes:
        n = int(self.headers.get("Content-Length") or 0)
        if n > limit:
            raise ValueError(f"gövde çok büyük ({n} bayt)")
        return self.rfile.read(n)

    def _json(self, limit=64 * 1024) -> dict:
        b = self._govde(limit)
        return json.loads(b) if b else {}

    def do_GET(self):
        u = urlparse(self.path)
        yol = u.path
        if yol == "/":
            return self._yanit(200, SAYFA.encode(), "text/html; charset=utf-8")
        if yol == "/yilan":
            return self._yanit(200, YILAN.read_bytes(), "text/html; charset=utf-8")
        if yol == "/editor":
            return self._yanit(200, EDITOR.read_bytes(), "text/html; charset=utf-8")
        if yol == "/onizleme":
            try:
                p = guvenli_ad(parse_qs(u.query).get("dosya", [""])[0])
                if not p.exists():
                    return self._yanit(404, {"hata": f"dosya yok: {p.name}"})
                kareler = goster.view_frames(str(p))[:MAX_KARE]
            except (ValueError, OSError) as e:
                return self._yanit(400, {"hata": str(e)})
            return self._yanit(200, {"w": VW, "h": VH, "dosya": p.name,
                                     "frames": [{"px": kare_to_hex(v), "dur": dur}
                                                for v, dur in kareler]})
        if yol == "/dongu/gifler":
            haric = dongu_disi()
            return self._yanit(200, {"gifler": [{"dosya": d, "dongude": d not in haric}
                                                for d in liste() if d.lower().endswith(".gif")]})
        if yol == "/liste":
            return self._yanit(200, {"dosyalar": liste()})
        if yol == "/durum":
            return self._yanit(200, {"gosterilen": oynatici.aciklama, "wled": WLED_IP})
        if yol == "/saglik":
            # /durum ESP32'ye hiç dokunmaz: matrisin fişi çekikken bile 200 döner. Rozet onu
            # yoklasaydı yalancı yeşil yanardı. "Sağlıklı" = bekci_led.py ile aynı tanım
            # (servis + WLED). WLED'in kapalı (on=false) olması arıza değil, yeşil kalır.
            try:
                info = sahne.wled(WLED_IP, yol="/json/info")
            except Exception as e:
                return self._yanit(503, {"servis": True, "wled": False, "hata": str(e)})
            return self._yanit(200, {"servis": True, "wled": True, "surum": info.get("ver"),
                                     "gosterilen": oynatici.aciklama})
        self._yanit(404, {"hata": "yok"})

    def do_POST(self):
        yol = urlparse(self.path).path
        try:
            d = self._json(limit=4 * 1024 * 1024 if yol in ("/piksel", "/kaydet") else 64 * 1024)
            if yol in ("/piksel", "/goster", "/yazi", "/renk", "/dur"):
                sahneler.dongu_durdur()        # elle seçilen içerik bilgi döngüsünü kapatır
            if yol == "/bilgi":                # HA: hava, sicaklik, pm25
                sahneler.bilgi.update({k: d[k] for k in ("hava", "sicaklik", "pm25", "kapilar") if k in d})
                return self._yanit(200, {"tamam": True, "bilgi": sahneler.bilgi})
            if yol == "/dongu/gifler":            # {"dosya": "x.gif", "dongude": false}
                if "hepsi" in d:                  # {"hepsi": true} hepsini al, false hepsini çıkar (HA düğmeleri)
                    haric = set() if d["hepsi"] else {x for x in liste() if x.lower().endswith(".gif")}
                    dongu_disi_yaz(haric)
                    return self._yanit(200, {"tamam": True, "haric": len(haric)})
                ad = guvenli_ad(d.get("dosya")).name
                haric = dongu_disi()
                (haric.discard if d.get("dongude", True) else haric.add)(ad)
                dongu_disi_yaz(haric)
                return self._yanit(200, {"tamam": True, "dosya": ad, "dongude": ad not in haric})
            if yol == "/sahne/dongu":
                if d.get("acik", True):
                    sahneler.dongu_baslat(parlaklik(d), RESIM_DIR, d.get("sayfalar"))
                else:
                    sahneler.dongu_durdur()
                return self._yanit(200, {"tamam": True, "dongu": sahneler.dongu_acik})
            if yol == "/piksel":
                kareler = kareler_oku(d)
                oynatici.oynat(lambda b: [(goster.view_to_bytes(v, b), s) for v, s in kareler],
                               "editör çizimi", parlaklik(d))
            elif yol == "/kaydet":
                try:
                    p = kaydet(d.get("ad"), kareler_oku(d), bool(d.get("uzerine_yaz")))
                except FileExistsError as e:
                    return self._yanit(409, {"hata": f"{e} zaten var", "dosya": str(e)})
                return self._yanit(200, {"tamam": True, "dosya": p.name})
            elif yol == "/goster":
                p = guvenli_ad(d.get("dosya"))
                if not p.exists():
                    return self._yanit(404, {"hata": f"dosya yok: {p.name}"})
                oynatici.oynat(lambda b, p=str(p): goster.load_frames(p, b),
                               f"resim: {p.name}", parlaklik(d))
            elif yol == "/yazi":
                metin = str(d.get("metin", "")).strip()[:200]
                if not metin:
                    raise ValueError("metin boş")
                rgb = hex_renk(d.get("renk", "ff8c00"))
                oynatici.oynat(lambda b: goster.text_frames(metin, b, rgb),
                               f"yazı: {metin}", parlaklik(d))
            elif yol == "/renk":
                rgb = hex_renk(d.get("renk"))
                img = Image.new("RGB", (WIDTH, HEIGHT), rgb)
                oynatici.oynat(lambda b: [(frame_to_bytes(goster.to_grid(img, b)), 1.0)],
                               "renk: #%02x%02x%02x" % rgb, parlaklik(d))
            elif yol == "/parlaklik":
                if "parlaklik" not in d:
                    raise ValueError("parlaklik eksik (0-1)")
                oynatici.parlaklik(parlaklik(d))
            elif yol in ("/sahne/pomodoro", "/sahne/mesaj", "/sahne/gundogumu"):
                if yol.endswith("pomodoro"):
                    sonuc = sahneler.pomodoro(sayi(d.get("dakika", 25)), sayi(d.get("mola", 5)), parlaklik(d))
                elif yol.endswith("mesaj"):
                    sonuc = sahneler.mesaj(str(d.get("metin", "")), int(sayi(d.get("tekrar", 3))), parlaklik(d))
                else:
                    sonuc = sahneler.gundogumu(sayi(d.get("dakika", 20)), parlaklik(d))
                return self._yanit(200, {"tamam": True, "sahne": sonuc})
            elif yol == "/oyun/basla":
                return self._yanit(200, {"tamam": True, "sahne": sahneler.yilan_basla(parlaklik(d))})
            elif yol == "/oyun/yon":
                return self._yanit(200, {"tamam": True, "sonuc": sahneler.yilan_yon(str(d.get("yon", "")))})
            elif yol == "/oyun/bitir":
                if sahneler.aktif == "oyun":
                    sahneler.bitir(parlaklik(d))
                return self._yanit(200, {"tamam": True})
            elif yol == "/sahne/uyari":
                sonuc = sahneler.uyari(str(d.get("seviye", "kritik")), str(d.get("metin", "")),
                                       sayi(d.get("sure")) or 300.0, parlaklik(d))
                return self._yanit(200, {"tamam": True, "sahne": sonuc})
            elif yol == "/sahne/yazici":
                durum_metni = sahneler.yazici(str(d.get("durum", "")), sayi(d.get("yuzde")),
                                              sayi(d.get("kalan_saat")), parlaklik(d))
                return self._yanit(200, {"tamam": True, "sahne": durum_metni})
            elif yol == "/dur":
                sahneler.bitir(parlaklik(d))   # sahnedeysek şeridi eski hâline al
                oynatici.dur()
            else:
                return self._yanit(404, {"hata": "yok"})
        except (ValueError, TypeError, AttributeError, json.JSONDecodeError, OSError) as e:
            return self._yanit(400, {"hata": str(e)})
        self._yanit(200, {"tamam": True, "gosterilen": oynatici.aciklama})

    def do_PUT(self):
        u = urlparse(self.path)
        if u.path != "/yukle":
            return self._yanit(404, {"hata": "yok"})
        try:
            p = guvenli_ad(parse_qs(u.query).get("ad", [""])[0])
            veri = self._govde(MAX_YUKLEME)
            tmp = p.with_suffix(p.suffix + ".tmp")
            tmp.write_bytes(veri)
            Image.open(tmp).verify()          # resim değilse reddet
            os.replace(tmp, p)
        except Exception as e:  # bozuk resim, büyük dosya, kötü ad — hepsi 400
            if "tmp" in locals() and tmp.exists():
                tmp.unlink()
            return self._yanit(400, {"hata": str(e)})
        self._yanit(200, {"tamam": True, "dosya": p.name})

    def log_message(self, fmt, *args):  # journald'a kısa satır
        print(f"{self.address_string()} {fmt % args}", flush=True)


if __name__ == "__main__":
    RESIM_DIR.mkdir(exist_ok=True)
    oynatici = Oynatici(WLED_IP)
    sahneler = sahne.Sahneler(oynatici, WLED_IP)
    print(f"ledmatrix servisi :{PORT} -> WLED {WLED_IP}, resimler: {RESIM_DIR}", flush=True)
    ThreadingHTTPServer(("0.0.0.0", PORT), Handler).serve_forever()
