"""Mantıksal (x, y) koordinatını DDP'de gönderilecek LED sırasına çevirir.

Panel dikey duruyor: 16 sütun genişlik, 32 satır yükseklik (iki 16x16 alt alta).
(0, 0) = görüntünün SOL ÜST köşesi.

Fiziksel kablolama (test_deseni.py ile 18.10.2026'da okundu):
  LED 0 sağ üstte, satır 0 sağdan sola; satır 1 soldan sağa (serpantin);
  LED 256 (alt panelin ilki) y=16'nın sağ ucunda — yani iki panel TEK bir
  16x32 serpantin gibi kesintisiz devam ediyor.

Bu düzen WLED'in 2D ayarına yazıldı (/json/cfg → hw.led.matrix: r=true, s=true,
16x32). 20.10.2026: panel TERS asıldı → 180° için r=false, b=true (aynı serpantin) ve WLED gerçek zamanlı veriye de bu eşlemeyi uyguluyor (if.live.rlm=true).
Dolayısıyla burada eşleme YAPILMAZ: düz satır-satır sıra gönderilir. Eşleme tek
yerde, WLED'de yaşar — efektler ve DDP aynı tabloyu kullanır.
"""
WIDTH = 16
HEIGHT = 32


def xy_to_index(x: int, y: int) -> int:
    """(x, y) -> WLED'in mantıksal piksel numarası (satır-satır, sol üstten)."""
    return y * WIDTH + x


def frame_to_bytes(pixels) -> bytes:
    """pixels[y][x] = (r, g, b) ızgarasını gönderim sırasına dizilmiş RGB baytlarına çevirir."""
    buf = bytearray(WIDTH * HEIGHT * 3)
    for y in range(HEIGHT):
        for x in range(WIDTH):
            i = xy_to_index(x, y) * 3
            buf[i:i + 3] = bytes(pixels[y][x])
    return bytes(buf)
