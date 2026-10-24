"""DDP paket biçimi testleri — donanımsız: python -m pytest test_ddp.py"""
import socket
import struct

from ddp import CHANNELS_PER_PACKET, DDPSender, build_packets


def test_512_led_iki_pakete_bolunur_push_yalniz_sonda():
    rgb = bytes(range(256)) * 6  # 1536 bayt = 512 LED
    pkts = build_packets(rgb, seq=3)
    assert len(pkts) == 2
    f0, s0, t0, d0, off0, len0 = struct.unpack(">BBBBIH", pkts[0][:10])
    f1, _, _, _, off1, len1 = struct.unpack(">BBBBIH", pkts[1][:10])
    assert (f0, s0, t0, d0) == (0x40, 3, 0x0B, 1)       # PUSH yok
    assert f1 == 0x41                                    # PUSH var
    assert (off0, len0) == (0, CHANNELS_PER_PACKET)
    assert (off1, len1) == (1440, 96)
    assert pkts[0][10:] + pkts[1][10:] == rgb            # veri kaybı/kayması yok


def test_gercek_udp_ile_alinir():
    rx = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    rx.bind(("127.0.0.1", 0))
    rx.settimeout(2)
    s = DDPSender("127.0.0.1", rx.getsockname()[1])
    s.send_frame(b"\x10\x20\x30" * 512)
    a, b = rx.recv(2000), rx.recv(2000)
    assert len(a) == 10 + 1440 and len(b) == 10 + 96
    assert s.seq == 2  # sıra no ilerledi, 0 atlanır
