"""Resim / GIF / düz renk / yazı -> matris (DDP ile WLED'e).

Ekran YATAY kullanılıyor: 32 geniş x 16 yüksek. WLED ise paneli dikey (16x32)
tanıyor; görüntü göndermeden önce 270° döndürülür (VIEW -> panel).

Kullanım:
  python goster.py <wled_ip> resim.png            # sabit resim (süre dolana kadar tutar)
  python goster.py <wled_ip> kedi.gif             # animasyon, döngüde
  python goster.py <wled_ip> --renk ff8800        # düz renk
  python goster.py <wled_ip> --yazi OSMAN         # yazı (yön testi için de)
  seçenekler: --sure 30 (sn, 0 = sonsuz)   --parlaklik 0.3 (0-1)

Süre dolunca gönderim durur; WLED birkaç saniye içinde kendi efektine geri döner.
"""
import argparse
import time

from PIL import Image, ImageOps, ImageSequence

import font5x7
from ddp import DDPSender
from harita import HEIGHT, WIDTH, frame_to_bytes

VIEW_W, VIEW_H = 32, 16  # Osman'ın baktığı yatay ekran


def fit_view(img: Image.Image, crop: bool = False) -> Image.Image:
    """Oranı koruyarak yatay 32x16 görüntüye sığdırır (döndürmeden).

    Şeffaf pikseller SİYAH olur (LED'de siyah = sönük; arka plan yanmaz).
    crop=True: şeffaf kenar boşlukları kırpılır — 2816x1536'lık bir logonun içeriği
    ortada küçük bir bölgedeyse, kırpmadan küçültünce logo 32x16'da kaybolur.
    (Animasyonda kare kare kırpılmaz, yoksa görüntü zıplar.)
    """
    rgba = img.convert("RGBA")
    if crop:
        bbox = rgba.getchannel("A").getbbox()
        if bbox:
            rgba = rgba.crop(bbox)
    img = Image.new("RGB", rgba.size)
    img.paste(rgba, mask=rgba.getchannel("A"))
    img.thumbnail((VIEW_W, VIEW_H), Image.LANCZOS)
    canvas = Image.new("RGB", (VIEW_W, VIEW_H))
    canvas.paste(img, ((VIEW_W - img.width) // 2, (VIEW_H - img.height) // 2))
    return canvas


def fit(img: Image.Image, crop: bool = False) -> Image.Image:
    """fit_view + panele çevirme."""
    return to_panel(fit_view(img, crop))


def is_pixel_art(img: Image.Image) -> bool:
    """Tam 32x16 dosya = bu ekran için çizilmiş (editörden ya da elle).
    Ona dokunulmaz: kırpma, küçültme, kontrast germe YOK — her piksel olduğu gibi."""
    return img.size == (VIEW_W, VIEW_H)


def view_frames(path: str):
    """Dosyayı ekranda görüneceği hâliyle verir: [(32x16 RGB görüntü, süre_sn), ...]."""
    src = Image.open(path)
    tek_kare = getattr(src, "n_frames", 1) == 1
    out = []
    for f in ImageSequence.Iterator(src):
        dur = f.info.get("duration", 100) / 1000 or 0.1
        if is_pixel_art(f):
            rgba = f.convert("RGBA")
            v = Image.new("RGB", rgba.size)
            v.paste(rgba, mask=rgba.getchannel("A"))
        else:
            v = fit_view(f, crop=tek_kare)
            if tek_kare:
                # koyu logolar (ör. lacivert yazı) LED'de neredeyse sönük kalır: en
                # parlak pikseli 255'e gerer, renk tonunu korur
                v = ImageOps.autocontrast(v, preserve_tone=True)
        out.append((v, dur))
    return out


def view_to_bytes(view: Image.Image, bri: float) -> bytes:
    return frame_to_bytes(to_grid(to_panel(view), bri))


def to_panel(view: Image.Image) -> Image.Image:
    """Yatay görüntü (32x16) -> panelin dikey çerçevesi (16x32).

    Osman'ın tarifinden: panel(x, y) = görüntü(X=y, Y=15-x); ROTATE_270 bunu
    birebir veriyor (18.10.2026'da piksel piksel karşılaştırıldı).
    """
    return view.transpose(Image.Transpose.ROTATE_270)


def text_frames(text: str, bri: float, rgb=(255, 140, 0), step_s: float = 0.06):
    """5x7 fontla yazı. 32 px'e sığıyorsa ortalanmış tek kare; sığmıyorsa sağdan
    sola kayan yazı (piksel başına step_s saniye)."""
    strip = font5x7.render(text, rgb, VIEW_H)
    if strip.width <= VIEW_W:
        canvas = Image.new("RGB", (VIEW_W, VIEW_H))
        canvas.paste(strip, ((VIEW_W - strip.width) // 2, 0))
        return [(frame_to_bytes(to_grid(to_panel(canvas), bri)), 1.0)]
    band = Image.new("RGB", (strip.width + 2 * VIEW_W, VIEW_H))
    band.paste(strip, (VIEW_W, 0))
    return [(frame_to_bytes(to_grid(to_panel(band.crop((x, 0, x + VIEW_W, VIEW_H))), bri)),
             step_s)
            for x in range(strip.width + VIEW_W)]


# Ekran renkleri (sRGB) gama kodlu, LED'in PWM'i doğrusal. WLED kendi renklerine 2.2
# gama uygular ama gerçek zamanlı (DDP) veriye UYGULAMAZ (cfg if.live.no-gc = true).
# Düzeltmesiz: editördeki kırmızı (255,0,40) %5'te (12,0,2) gider, o küçük mavi payı
# LED'de baskın çıkar -> pembe. Düzeltmeyle (13,0,0) -> kırmızı.
GAMMA = 2.2


def _lut(bri: float):
    return [round(255 * (v / 255) ** GAMMA * bri) for v in range(256)]


def to_grid(img: Image.Image, bri: float):
    """Panel görüntüsü -> gama düzeltilmiş, parlaklığı uygulanmış piksel ızgarası.
    Parlaklık gamadan SONRA çarpılır: LED'in doğrusal ışık alanında ölçekleme."""
    lut = _lut(bri)
    px = img.load()
    return [[tuple(lut[c] for c in px[x, y]) for x in range(WIDTH)]
            for y in range(HEIGHT)]


def load_frames(path: str, bri: float):
    """[(rgb_bayt, süre_sn), ...] döndürür. Durağan resim = tek kare."""
    return [(view_to_bytes(v, bri), dur) for v, dur in view_frames(path)]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("ip")
    ap.add_argument("dosya", nargs="?")
    ap.add_argument("--renk", help="hex, ör. ff8800")
    ap.add_argument("--yazi", help="kısa yazı, ör. OSMAN")
    ap.add_argument("--sure", type=float, default=30)
    ap.add_argument("--parlaklik", type=float, default=0.3)
    a = ap.parse_args()

    if a.yazi:
        frames = text_frames(a.yazi, a.parlaklik)
    elif a.renk:
        rgb = tuple(int(a.renk[i:i + 2], 16) for i in (0, 2, 4))
        frames = [(frame_to_bytes(to_grid(Image.new("RGB", (WIDTH, HEIGHT), rgb),
                                          a.parlaklik)), 1.0)]
    elif a.dosya:
        frames = load_frames(a.dosya, a.parlaklik)
    else:
        ap.error("dosya ya da --renk ver")

    sender = DDPSender(a.ip)
    bitis = time.monotonic() + a.sure if a.sure > 0 else float("inf")
    while time.monotonic() < bitis:
        for rgb, dur in frames:
            sender.send_frame(rgb)
            # durağan resimde bile tazele: WLED veri kesilince gerçek zamanlı moddan çıkar
            time.sleep(min(dur, 1.0))
            if time.monotonic() >= bitis:
                break


if __name__ == "__main__":
    main()
