"""Kablolama düzenini bulmak için işaret LED'leri yakar (eşleme KULLANMAZ, ham sıra).

Kullanım:  python test_deseni.py <wled_ip>
Panelde göreceklerin:
  LED 0   KIRMIZI   -> şeridin başı
  LED 1   YEŞİL     -> ikinci LED hangi yönde?
  LED 15  MAVİ      -> ilk 16'lık dizinin sonu
  LED 16  SARI      -> 17. LED: bir alt satırın aynı ucu mu, ters ucu mu?
  LED 17  MOR
  LED 256 BEYAZ     -> alt panelin ilk LED'i
Hepsi kısık parlaklıkta (güç derdi yok).
"""
import sys
import time

from ddp import DDPSender

N = 512
MARKERS = {0: (40, 0, 0), 1: (0, 40, 0), 15: (0, 0, 40),
           16: (40, 30, 0), 17: (30, 0, 40), 256: (30, 30, 30)}


def main():
    if len(sys.argv) != 2:
        sys.exit("kullanım: python test_deseni.py <wled_ip>")
    sys.stdout.reconfigure(encoding="utf-8")  # Windows konsolu cp1252: 'ı' basamıyor
    buf = bytearray(N * 3)
    for idx, rgb in MARKERS.items():
        buf[idx * 3:idx * 3 + 3] = bytes(rgb)
    sender = DDPSender(sys.argv[1])
    print("Desen gönderiliyor (Ctrl+C ile çık)...")
    try:
        while True:  # WLED gerçek zamanlı modu ~2,5 sn veri gelmezse bırakır, tazele
            sender.send_frame(bytes(buf))
            time.sleep(0.5)
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
