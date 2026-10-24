"""DDP (Distributed Display Protocol) gönderici — WLED'e UDP ile ham piksel basar.

Başlık biçimi WLED kaynağından alındı (wled00/src/dependencies/e131/ESPAsyncE131.h):
  bayt 0    bayraklar  0x40 = sürüm 1, | 0x01 = PUSH (kareyi şimdi göster)
  bayt 1    sıra no    (alt 4 bit)
  bayt 2    veri tipi  0x0B = RGB, kanal başına 8 bit
  bayt 3    hedef      1 = varsayılan ekran
  bayt 4-7  kanal ofseti (32 bit, büyük uçlu)
  bayt 8-9  veri uzunluğu (16 bit, büyük uçlu)
Paket başına en çok 1440 kanal (= 480 LED). 512 LED'lik kare 2 pakete bölünür;
PUSH bayrağı yalnız SONUNCUDA olur — yoksa kare yarım yarım çizilir (yırtılma).
"""
import socket
import struct

DDP_PORT = 4048
FLAGS_VER1 = 0x40
FLAGS_PUSH = 0x01
TYPE_RGB24 = 0x0B
ID_DISPLAY = 1
CHANNELS_PER_PACKET = 1440


def build_packets(rgb: bytes, seq: int = 0) -> list[bytes]:
    """Bir karenin RGB baytlarını DDP paketlerine böler."""
    packets = []
    for offset in range(0, len(rgb), CHANNELS_PER_PACKET):
        chunk = rgb[offset:offset + CHANNELS_PER_PACKET]
        last = offset + CHANNELS_PER_PACKET >= len(rgb)
        flags = FLAGS_VER1 | (FLAGS_PUSH if last else 0)
        header = struct.pack(">BBBBIH", flags, seq & 0x0F, TYPE_RGB24, ID_DISPLAY,
                             offset, len(chunk))
        packets.append(header + chunk)
    return packets


class DDPSender:
    def __init__(self, host: str, port: int = DDP_PORT):
        self.addr = (host, port)
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.seq = 1  # 0 = "sıra no kullanılmıyor" anlamına gelir, 1-15 döndür

    def send_frame(self, rgb: bytes) -> None:
        for pkt in build_packets(rgb, self.seq):
            self.sock.sendto(pkt, self.addr)
        self.seq = self.seq % 15 + 1
