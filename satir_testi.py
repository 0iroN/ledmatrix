"""Her mantıksal satırı ayrı renkte yakar — eşleme + veri yolunun tam röntgeni.

Kullanım:  python satir_testi.py <wled_ip>
Satır 0 kırmızı, sonra turuncu-sarı-yeşil-mavi-mor diye gökkuşağı; 32 satırın
hepsi tam dolu olmalı. Sönük satır = o bölgeye veri ulaşmıyor; yanlış sıradaki
renk = eşleme hatası.
"""
import colorsys
import sys
import time

from ddp import DDPSender
from harita import HEIGHT, WIDTH, frame_to_bytes

K = 50  # kısık


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    if len(sys.argv) != 2:
        sys.exit("kullanım: python satir_testi.py <wled_ip>")
    px = []
    for y in range(HEIGHT):
        r, g, b = colorsys.hsv_to_rgb(y / HEIGHT * 0.85, 1, 1)
        px.append([(int(r * K), int(g * K), int(b * K))] * WIDTH)
    rgb = frame_to_bytes(px)
    sender = DDPSender(sys.argv[1])
    print("Satır testi gönderiliyor (Ctrl+C ile çık)...")
    try:
        while True:
            sender.send_frame(rgb)
            time.sleep(0.5)
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
