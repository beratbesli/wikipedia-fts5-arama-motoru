# Wikipedia FTS5 Yerel Arama Motoru

Bu proje, Türkçe Wikipedia metinleri üzerinde yerel ve hızlı arama yapmak için geliştirilmiş bir Python uygulamasıdır. Arama altyapısı SQLite FTS5 kullanır ve sonuçları BM25 alaka sıralamasıyla listeler.

Çalışma zamanı için dış bağımlılık yoktur; Python 3 standart kütüphanesi yeterlidir.

## Özellikler

- SQLite FTS5 ile hızlı tam metin arama
- BM25 ile alaka sırasına göre sonuç listeleme
- Türkçe karakterlere duyarlı arama normalizasyonu
- Türkçe ekli kelimeler için ön ek eşleşmesi desteği
- Wikipedia wikitext temizleme ve sade metin gösterimi
- Terminalde sayfalı sonuç gezme
- Hazır SQLite veritabanı ile ilk kurulum süresini atlama

## Veri Seti

Büyük veri dosyaları GitHub deposuna eklenmez. Hazır veritabanı Hugging Face üzerinde tutulur:

https://huggingface.co/datasets/beert00/wikipedia-fts5-turkish-dataset

Kullanıma hazır dosya:

```text
wiki_fts.db
```

Bu dosyayı indirip proje klasörüne koyarsanız program doğrudan arama ekranını açar. Veritabanı yoksa program `wiki_temiz.txt` dosyasından veritabanını yeniden oluşturabilir, fakat bu işlem ilk çalıştırmada uzun sürebilir.

> **Doğrulama durumu:** Hugging Face üzerindeki etiket tek başına kaynak ve lisans
> zincirini kanıtlamaz. Kesin döküm URL'si, tarih, dönüşüm komutu ve SHA-256 değerleri
> henüz doldurulmamıştır. Bu alanlar tamamlanana kadar veri setini kaynağı doğrulanmış
> bir sürüm olarak kabul etmeyin. Kontrol listesi: [`docs/DATA_PROVENANCE.md`](docs/DATA_PROVENANCE.md).

## Kurulum

1. Repoyu indirin:

```bash
git clone https://github.com/beratbesli/wikipedia-fts5-arama-motoru.git
cd wikipedia-fts5-arama-motoru
```

2. Projeyi yalıtılmış bir ortama kurun:

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
python -m pip install .
```

3. Hugging Face sayfasından `wiki_fts.db` dosyasını indirin ve yayımlanmış SHA-256
   değeri varsa indirdiğiniz dosyayla karşılaştırın.

4. `wiki_fts.db` dosyasını proje klasörüne koyun.

Klasör yapısı şöyle olmalıdır:

```text
wikipedia-fts5-arama-motoru/
  wiki_arama_motoru.py
  wiki_fts.db
  README.md
```

## Çalıştırma

```bash
wikipedia-fts5
```

Tek sorgu çalıştırmak için:

```bash
wikipedia-fts5 "Atatürk" --database wiki_fts.db --limit 10
```

Eski `python wiki_arama_motoru.py` komutu geriye dönük uyumluluk için korunur.

## Kullanım Örneği

```text
======================================================================
                  WİKİPEDİA AKILLI ARAMA ASİSTANI
======================================================================
Aramak istediğiniz konuyu yazın. Çıkış için 'q' kullanabilirsiniz.
======================================================================

Arama Kutusu > Atatürk

======================================================================
“Atatürk” İÇİN EN ALAKALI 30 SONUÇ
Sayfa 1/3
======================================================================
  1. Atatürk'ü Anma
  2. Atatürk'e göre millet; geçmişte bir arada yaşamış
  3. Atatürk İlkeleri
  4. Samsun Atatürk Anadolu Lisesi
  5. Atatürk Orman Çiftliği
  6. İzmir Atatürk Stadyumu
  7. Atatürk Kültür Merkezi
  8. Bursa Atatürk Stadyumu
  9. Atatürk Devrimleri
 10. Atatürk Barajı ve Hidroelektrik Santrali
----------------------------------------------------------------------

Sonuç numarası; sonraki sayfa için 'n', önceki sayfa için 'p', yeni arama için 'y', çıkış için 'q':
```

## Kaynaktan Veritabanı Oluşturma

Hazır `wiki_fts.db` dosyasını kullanmak istemiyorsanız temizlenmiş Wikipedia metnini proje klasörüne şu adla koyabilirsiniz:

```text
wiki_temiz.txt
```

Program aşağıdaki komutla bu dosyadan `wiki_fts.db` veritabanını üretir. Büyük
dosyalarda bu işlem uzun sürebilir.

```bash
wikipedia-fts5 --build --source wiki_temiz.txt --database wiki_fts.db
```

## Proje Dosyaları

- `wikipedia_fts5/engine.py`: Metin temizleme, indeksleme ve arama çekirdeği
- `wikipedia_fts5/search.py`: Arama için kararlı kütüphane yüzeyi
- `wikipedia_fts5/index.py`: İndeks oluşturma yüzeyi
- `wikipedia_fts5/cli.py`: Komut satırı arayüzü
- `wiki_arama_motoru.py`: Eski çalıştırma komutuyla uyumluluk sağlayan ince başlatıcı
- `tests/`: Küçük ve deterministik FTS5 testleri
- `docs/DATA_PROVENANCE.md`: Veri kaynağı, lisans ve checksum yayınlama kapısı
- `.gitignore`: Büyük veri, veritabanı, arşiv ve önbellek dosyalarını Git dışında tutar

## Lisans Notu

Kod [MIT Lisansı](LICENSE) ile sunulur. Depoda Wikipedia verisi veya hazır veritabanı bulunmaz. Wikipedia kaynaklı içerikler kendi lisans koşullarına tabidir; özellikle atıf ve paylaşım koşulları için veri setinin Hugging Face sayfasını ve ilgili Wikipedia lisansını inceleyin. İndirilen veri setinin sürümünü ve checksum değerini kullanmadan önce doğrulayın.
