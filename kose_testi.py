"""Eşleme doğrulaması: 4 köşe + bir ok, harita.py ÜZERİNDEN gönderilir.

Kullanım:  python kose_testi.py <wled_ip>
Doğruysa: sol üst KIRMIZI, sağ üst YEŞİL, sol alt MAVİ, sağ alt BEYAZ,
ortada yukarıyı gösteren sarı bir ok.
"""
import sys
import time

from ddp import DDPSender
from harita import HEIGHT, WIDTH, frame_to_bytes

K = 40  # kısık


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    if len(sys.argv) not in (2, 3):
        sys.exit("kullanım: python kose_testi.py <wled_ip> [zemin 0-255]")
    z = int(sys.argv[2]) if len(sys.argv) == 3 else 0  # >0: siyah yerine çok sönük gri
    px = [[(z, z, z)] * WIDTH for _ in range(HEIGHT)]
    px[0][0] = (K, 0, 0)
    px[0][WIDTH - 1] = (0, K, 0)
    px[HEIGHT - 1][0] = (0, 0, K)
    px[HEIGHT - 1][WIDTH - 1] = (K, K, K)
    for y in range(8, 24):          # okun gövdesi
        px[y][7] = px[y][8] = (K, K // 2, 0)
    for d in range(1, 5):           # okun başı
        px[8 + d][7 - d] = px[8 + d][8 + d] = (K, K // 2, 0)
    rgb = frame_to_bytes(px)
    sender = DDPSender(sys.argv[1])
    print("Köşe testi gönderiliyor (Ctrl+C ile çık)...")
    try:
        while True:
            sender.send_frame(rgb)
            time.sleep(0.5)
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
