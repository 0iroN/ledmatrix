# ledmatrix — 16x32 WS2812B matris (ESP32 + WLED + HA)

Mimari: **ESP32 = WLED (aptal ekran + hazır efektler)**, **Pi = gönderici (resim/GIF -> DDP)**,
**HA = düğmeler** (WLED entegrasyonu + Pi'deki göndericiyi çağıran script). Fotoğraf
değiştirmek için ESP32'yi yeniden flaşlamak gerekmez.

## Bağlantı

```
5V 25A adaptör (+) ──┬──────────────► Panel ÜST  5V  (veri girişi olan uç, sağ üst)
                     └──────────────► Panel ALT  5V  (iki panelin birleştiği yer, ek besleme)
adaptör (−) ─────────┬──────────────► Panel ÜST GND
                     ├──────────────► Panel ALT GND
                     └──────────────► ESP32 GND   (ORTAK TOPRAK ŞART)
adaptör girişine:      1000 µF / ≥10 V elektrolitik (+ → 5V)

ESP32 GPIO16 ──[330 Ω]──► 74AHCT125 (1A) ──► Panel DIN
               (74AHCT125: VCC=5V, GND, 1OE=GND)  — yoksa önce doğrudan dene
ESP32 5V/VIN ◄── adaptör 5V  (USB ile programlarken bu hattı ayır)
```

**Güç uyarısı:** 25 A adaptör paneli yakabilecek kadar güçlü; panelin ince kabloları
o akımı taşımaz. WLED'de LED ayarlarında **otomatik parlaklık sınırı (ABL) = 5000 mA**
ile başla. 512 LED tam beyaz hiçbir zaman gerekmez.

## WLED kurulumu

1. Chrome/Edge ile `https://install.wled.me` → ESP32'yi USB ile tak → Install.
2. ESP32'nin açtığı `WLED-AP` ağına bağlan (şifre `wled1234`) → ev Wi-Fi'ını gir.
3. Config → LED Preferences: GPIO **16**, uzunluk **512**, tip WS281x, sıra GRB, ABL 5000 mA.
4. Modemde ESP32'ye **sabit IP** ver (gönderici IP ile konuşuyor).
5. Config → 2D Configuration: matris 16 x 32 — panel düzenini test_deseni.py sonucuna göre gir
   (WLED'in kendi efektleri düzgün dursun diye).

## Pikselleri sınama (sıra bu)

```
pip install pillow
python test_deseni.py <esp_ip>      # kablolama düzenini öğren
# düzeni WLED 2D ayarına gir (bu panel: sağ üstten, serpantin, 16x32)
python kose_testi.py <esp_ip>       # köşeler doğru mu
python goster.py <esp_ip> --renk ff0000 --sure 5
python goster.py <esp_ip> resim.png
python goster.py <esp_ip> animasyon.gif --sure 0
```

Not: WLED gerçek zamanlı veride 2D eşlemeyi yalnız `realtimeRespectLedMaps` açıkken
uygular (`getMappedPixelIndex`, FX.h). Bu cihazda (16.0.1) açık geliyor:
`/json/cfg` → `if.live.rlm = true` (18.10.2026 okundu). Yani WLED'de 2D matris
tanımlanınca DDP verisi de onun eşlemesinden geçer — eşleme İKİ yerde yapılmamalı.
2D tanımsızken (şu an) tablo boştur, test_deseni.py ham sırayı görür.

## Canlı kurulum (19.10.2026)

> Adresler yer tutucudur: `ledmatrix.local` = servisi çalıştıran makine (Pi),
> `wled.local` = WLED denetleyicisi. Kendi ağındaki IP/host adlarıyla değiştir
> (`WLED_IP` ortam değişkeni, `ha/` YAML dosyaları, `ledmatrix.service`).

- **Pi servisi:** `/opt/ledmatrix/server.py`, systemd `ledmatrix.service`, port **8790**
  (ufw: yalnız yerel ağ + VPN). Resimler `/opt/ledmatrix/resimler/`.
  Yükleme sayfası: `http://ledmatrix.local:8790/`. Güncelleme: dosyaları scp + `sudo systemctl restart ledmatrix`.
- **HA (Excalibur):** `config/packages/ledmatrix.yaml` (bu depoda `ha/packages/`) ve YAML panosu
  `config/dashboards/led_matris.yaml` → kenar çubuğunda **LED Matris**. `configuration.yaml`'a
  `homeassistant: packages:` + `lovelace: dashboards:` eklendi.
- **Editör:** `http://ledmatrix.local:8790/editor` — dosyayı panelde görüneceği hâliyle önizle,
  LED LED boya/kapat, kare ekle, panelde canlı dene, 32x16 PNG/GIF olarak kaydet.
  Tam 32x16 dosyalar "piksel sanatı" sayılır: gösterilirken kırpma/küçültme/kontrast YOK.
- **Ayrı şerit (19.10):** aynı ESP32, **GPIO17 (TX2)**, WLED bus 2 = LED 512'den itibaren
  **144** (20.10). Şerit uzatılınca WLED > LED Preferences'ta bus 2 uzunluğunu ve segment 1'in
  stop değerini birlikte güncelle, sonra boot preset 1'i yeniden kaydet. Segment 0 "Matris" (ana), segment 1 "Serit". WLED
  `Use main segment only` açık → Pi'nin kareleri yalnız matrise gider, şerit kendi
  efektinde kalır. HA: `light.wled_segment_1`. Güç sınırı toplam 8000 mA (matris 5000, şerit 3000).
  **Şeridin GND'si doğrudan ESP32 GND'sine** — matris üzerinden alınınca saniyede bir beyaz çakıyordu.
  Bu modda WLED'in ana aç/kapa ve ana parlaklığı matrisi de etkiler; servis her gösterimde
  ana anahtarı açık + tam parlaklığa çeker (`server.py wled_hazirla`).
- **Sahneler (21.10, `sahne.py`):** öncelik sırası uyarı > 3D yazıcı > bilgi döngüsü > elle
  seçilen içerik. Sahne bitince önceki matris içeriği ve şeridin WLED durumu geri yüklenir.
  - 3D yazıcı: HA otomasyonu Bambu A1 durum/yüzde/kalan süreyi `/sahne/yazici`'ye yollar.
  - Bilgi döngüsü: saat, hava, atölye PM2.5, rastgele GIF; gece 23–07 kısık (`/sahne/dongu`, `/bilgi`).
  - Uyarı: nöbetçi (yüksek önemli olay) ve Pi bekçisi (Excalibur düştü) `/sahne/uyari`'yi çağırır.
- **21.10 eklemeleri:** `bekci_led.py` (Pi cron */5, servis/WLED düşerse Telegram), döngü
  sayfa süreleri HA'dan (`input_select.ledmatrix_sayfa_*`, "kapalı" = gizle), hareketli hava,
  yılan oyunu `http://ledmatrix.local:8790/yilan`, eve gelince karşılama (HA anahtarı).
  **Not:** `sahne.py` modül fonksiyonlarıyla bitiyor — yeni `Sahneler` metodunu dosya sonuna
  değil sınıfın içine (`def kayan_kareler` öncesine) ekle.
- **Hazır GIF'ler:** `python gif_uret.py` → `gifler/` (32x16 piksel sanatı). Yeni animasyon
  eklemek için `GIFLER` sözlüğüne bir fonksiyon ekle, üret, `/yukle` ile Pi'ye gönder.
  Koyu tonları parlak tut: panel gama 2.2 uygular, %25'in altı LED'de kaybolur.
- **Döngü GIF listesi HA'da (22.10):** panoda "Bilgi döngüsü — rastgele GIF listesi" kartı:
  seçme kutusu (✅ döngüde · ⬜ dışında), seçili GIF'i al / çıkar, hepsini al / çıkar, dışarıda
  kalanların listesi. Kaynak `sensor.matrix_led_dongu_gif` (`GET /dongu/gifler`, 60 sn);
  düğmeden sonra sensör hemen tazelenir. Aynı liste `http://ledmatrix.local:8790/` sayfasında da var.
- **Sağlık ucu (22.10):** `GET /saglik` → 200 servis + WLED cevap veriyor, 503 ESP32'ye
  ulaşılamıyor. Araçlar sitesindeki Matrix Led kartının rozeti bunu yoklar (Caddy
  `/matris-saglik`). `/durum` rozet için uygun DEĞİL: ESP32'ye dokunmaz, fiş çekikken de 200.
- **Adlar (20.10):** WLED segmentleri "Matrix Led" / "Masa Üstü Neo Led"; HA'da aynı adlar
  (entity_id'ler değişmedi: `light.wled`, `light.wled_segment_1`).
- Aynı anda tek gönderici: Pi servisi çalışırken bilgisayardan `goster.py` çalıştırma, kareler karışır.
