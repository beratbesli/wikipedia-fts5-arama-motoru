# 🔍 Wikipedia FTS5 Yerel Esnek Arama Motoru

Bu proje, büyük ölçekli metin veri setleri (örneğin 2.2 GB'lık Türkçe Wikipedia dökümü `wiki_temiz.txt`) üzerinde **milisaniyeler içinde** arama yapmayı sağlayan, **SQLite FTS5 (Full Text Search)** ve **BM25 Alaka Sıralaması** tabanlı yerel bir arama motorudur.

---

## ✨ Öne Çıkan Özellikler

- 🚀 **Bellek Dostu (Batch) İndeksleme:** 2+ GB boyutundaki büyük veri setlerini RAM'i şişirmeden partiler halinde (`5.000` satırlık batch'ler) SQLite veritabanına aktarır.
- 🎯 **BM25 Alaka Düzeyi Sıralaması:** Google ve Elasticsearch'ün temelini oluşturan BM25 algoritması ile aranan kelimelerle en çok eşleşen makaleleri otomatik olarak en üste sıralar.
- 🔄 **Konumdan Bağımsız Esnek Arama (`AND` / `OR` Kombinasyonu):**
  - Kelimelerin yan yana olma zorunluluğunu kaldırır.
  - Önce kelimelerin tümünün geçtiği (`AND`) sonuçları getirir, bulunamazsa en iyi eşleşen alternatifleri (`OR`) sıralar.
- 🧹 **MediaWiki ve Wikitext Temizleyici:** Wikipedia'nın ham biçimlendirme kodlarını (`küçükresim|...`, `<ref>`, bilgi kutusu parametreleri, HTML sembolleri) ekranda göstermeyerek son kullanıcıya doğal bir Türkçe okuma metni sunar.
- 🖥️ **İnteraktif Son Kullanıcı Arayüzü:**
  - Arama yapıldığında en alakalı **30 başlığı** liste halinde sunar.
  - Seçilen başlığın **Konu Başlığını**, **Eşleşme Durumunu**, **Vurgulu İçerik Özetini (`[Kelime]`)** ve **Makaleden Geniş Metnini** detay panelinde açar.

---

## 🛠️ Kurulum ve Kullanım

### 1. Gereksinimler
Proje sadece Python 3 standart kütüphanesini (`sqlite3`, `re`, `time`, `html`) kullanmaktadır. Ek bir paket yüklemenize gerek yoktur.

### 2. Veri Setinin Eklenmesi
Arama yapmak istediğiniz metin dosyasını proje dizinine **`wiki_temiz.txt`** adıyla yerleştirin.
*(Not: Büyük veri dosyaları `.gitignore` ile hariç tutulduğundan GitHub deposuna yüklenmez).*

### 3. Çalıştırma
Terminalinizde proje dizinine gelip aşağıdaki komutu çalıştırın:

```bash
python3 wiki_arama_motoru.py
```

İlk çalıştırmada veritabanı (`wiki_fts.db`) otomatik olarak oluşturulur ve indekslenir. Sonraki çalıştırmalarda doğrudan arama ekranı açılır.

---

## 📋 Kullanım Örneği

```text
Arama Kutusu > mustafa kemal

======================================================================
"mustafa kemal" İÇİN EN ALAKALI 30 SONUÇ BULUNDU (0.009 saniyede arandı)
======================================================================
  1. 1908 Abdurrahim Tuncak ve Mustafa Kemal Paşa, Halep, 1917 ...
  2. Davetli gözlemci subayları (Kolağası Mustafa Kemal, Fransız Albay ...
  3. 1857
  ...
----------------------------------------------------------------------
Detayını görmek istediğiniz sonucun numarasını yazın (Yeni arama için 'y', çıkış için 'q'): 1
```

---

## 🏗️ Proje Yapısı

- `wiki_arama_motoru.py`: Veritabanı kurulumunu, FTS5 sorgulama mantığını ve interaktif terminal arayüzünü içeren ana kod dosyası.
- `README.md`: Proje dokümantasyonu.
- `.gitignore`: Büyük veri setlerini ve önbellek dosyalarını depodan hariç tutan yapılandırma dosyası.
