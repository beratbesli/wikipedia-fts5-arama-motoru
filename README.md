# Wikipedia FTS5 Yerel Arama Motoru

Bu proje, Türkçe Wikipedia metinleri üzerinde yerel ve hızlı arama yapmak için geliştirilmiş bir Python uygulamasıdır. Arama altyapısı SQLite FTS5 kullanır ve sonuçları BM25 alaka sıralamasıyla listeler.

Proje dış bağımlılık kullanmaz. Python 3 standart kütüphanesi yeterlidir.

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

## Kurulum

1. Repoyu indirin:

```bash
git clone https://github.com/beratbesli/wikipedia-fts5-arama-motoru.git
cd wikipedia-fts5-arama-motoru
```

2. Hugging Face sayfasından `wiki_fts.db` dosyasını indirin.

3. `wiki_fts.db` dosyasını proje klasörüne koyun.

Klasör yapısı şöyle olmalıdır:

```text
wikipedia-fts5-arama-motoru/
  wiki_arama_motoru.py
  wiki_fts.db
  README.md
```

## Çalıştırma

Windows:

```powershell
python wiki_arama_motoru.py
```

Linux veya macOS:

```bash
python3 wiki_arama_motoru.py
```

## Kaynaktan Veritabanı Oluşturma

Hazır `wiki_fts.db` dosyasını kullanmak istemiyorsanız temizlenmiş Wikipedia metnini proje klasörüne şu adla koyabilirsiniz:

```text
wiki_temiz.txt
```

Program ilk çalıştırmada bu dosyadan `wiki_fts.db` veritabanını üretir. Büyük dosyalarda bu işlem birkaç dakika sürebilir.

## Testler

Testleri çalıştırmak için:

```bash
python -m unittest test_wiki_arama_motoru.py
```

## Proje Dosyaları

- `wiki_arama_motoru.py`: Ana arama motoru, veritabanı kurulumu ve terminal arayüzü
- `test_wiki_arama_motoru.py`: Birim testleri
- `.gitignore`: Büyük veri, veritabanı, arşiv ve önbellek dosyalarını Git dışında tutar

## Lisans Notu

Bu proje kodu GitHub üzerinde paylaşılır. Wikipedia kaynaklı içerikler kendi lisans koşullarına tabidir. Veri setini kullanırken Hugging Face dataset sayfasındaki lisans ve açıklama bilgilerini dikkate alın.
