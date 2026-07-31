#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
wiki_arama_motoru.py
- SQLite FTS5 kullanarak 'wiki_temiz.txt' veri setini bellek yormadan parça parça (batch) indeksler.
- 2 kelime kısıtlamasını ve yan yana olma (adjacency) zorunluluğunu tamamen kaldırır.
- Tek kelime, yan yana olmayan çoklu kelime veya tam cümle aramalarında dinamik AND/OR + BM25 sıralaması ile arama yapar.
"""

import os
import re
import sqlite3
import time

# ==========================================
# 1. VERİTABANI KURULUMU (BATCH / BELLEK DOSTU)
# ==========================================
def veritabani_kur(txt_dosyasi="wiki_temiz.txt", db_dosyasi="wiki_fts.db", max_satir=100000, batch_size=5000, yeniden_olustur=False):
    """
    'wiki_temiz.txt' dosyasını bellek yormadan parça parça okur ve SQLite FTS5 sanal tablosuna indeksler.
    
    Parametreler:
    - txt_dosyasi: Okunacak büyük metin dosyası.
    - db_dosyasi: Oluşturulacak SQLite veritabanı dosyası.
    - max_satir: Varsayılan olarak 100.000 satır (~260 MB) indekslenir. Tüm dosya için None verilebilir.
    - batch_size: Bellek şişmesini önlemek için veritabanına toplu yazım periyodu.
    - yeniden_olustur: True ise mevcut veritabanı silinip baştan kurulur.
    """
    if not os.path.exists(txt_dosyasi):
        print(f"Hata: '{txt_dosyasi}' bulunamadı!")
        return False

    if yeniden_olustur and os.path.exists(db_dosyasi):
        os.remove(db_dosyasi)

    # Veritabanı varsa ve içi doluysa tekrar yükleme yapmadan devam edebiliriz
    conn = sqlite3.connect(db_dosyasi)
    cursor = conn.cursor()
    
    # FTS5 sanal tablosunu oluştur
    # unicode61 ve remove_diacritics 0 ile Türkçe karakter desteği korunur
    cursor.execute("""
        CREATE VIRTUAL TABLE IF NOT EXISTS makaleler USING fts5(
            satir_id UNINDEXED, 
            metin, 
            tokenize='unicode61 remove_diacritics 0'
        );
    """)
    conn.commit()

    # Eğer tablo zaten doluysa bilgi verip çıkalım
    cursor.execute("SELECT COUNT(*) FROM makaleler;")
    mevcut_kayit = cursor.fetchone()[0]
    if mevcut_kayit > 0 and not yeniden_olustur:
        print(f"Kütüphane Hazır! ({mevcut_kayit:,} makale arama için hazır)")
        return conn

    print("Wikipedia kütüphanesi ilk kullanım için hazırlanıyor... Lütfen bekleyin...")
    baslangic_zamani = time.time()
    
    batch = []
    toplam_satir = 0

    with open(txt_dosyasi, "r", encoding="utf-8", errors="ignore") as f:
        for line_idx, satir in enumerate(f, start=1):
            temiz_satir = satir.strip()
            if not temiz_satir:
                continue
            
            batch.append((line_idx, temiz_satir))
            toplam_satir += 1

            # Batch dolduğunda veritabanına yaz
            if len(batch) >= batch_size:
                cursor.executemany("INSERT INTO makaleler(satir_id, metin) VALUES (?, ?)", batch)
                conn.commit()
                batch.clear()
                print(f"  -> {toplam_satir:,} makale kütüphaneye eklendi...")

            if max_satir and toplam_satir >= max_satir:
                break

    # Kalan son parti kayıtları yaz
    if batch:
        cursor.executemany("INSERT INTO makaleler(satir_id, metin) VALUES (?, ?)", batch)
        conn.commit()
        batch.clear()

    gecen_sure = time.time() - baslangic_zamani
    print(f"Kütüphane kurulumu tamamlandı! Toplam {toplam_satir:,} makale {gecen_sure:.2f} saniyede hazırlandı.")
    return conn


# ==========================================
# 2. ESNEK VE DİNAMİK ARAMA MANTIĞI (SON KULLANICI DOSTU)
# ==========================================
def esnek_arama(conn, sorgu_metni, limit=5):
    """
    Kullanıcının girdiği metindeki kelimeleri FTS5 ile esnek bir şekilde arar.
    - Kelime sayısı kısıtlaması yoktur (1 kelime, N kelime veya tam cümle).
    - Yan yana olma (adjacency) zorunluluğu yoktur; kelimeler metnin herhangi bir yerinde olabilir.
    - Önce tüm kelimelerin geçtiği arama yapılır.
    - Sonuç bulunamazsa, kelimelerden herhangi birinin geçtiği ve en çok eşleşenin
      en üste çıktığı esnek arama yapılır.
    """
    cursor = conn.cursor()

    # FTS5 sözdizimini bozacak özel karakterleri temizleyip sadece kelimeleri alalım
    kelimeler = re.findall(r'\w+', sorgu_metni.strip(), re.UNICODE)
    if not kelimeler:
        print("Uyarı: Lütfen geçerli bir arama kelimesi girin.")
        return []

    import html
    def wiki_metni_sadelestir(metin):
        """Wikipedia ham MediaWiki kodlarını (resim şablonları, ref etiketleri, HTML karakterleri) son kullanıcı için temizler."""
        if not metin:
            return ""
        # 1. HTML entitilerini çöz (&lt; -> <, &quot; -> ", &amp; -> & vb.)
        temiz = html.unescape(metin)
        # 2. <ref>...</ref> veya <ref ...> biçimindeki kaynakçı etiketlerini ve içeriklerini kaldır
        temiz = re.sub(r'<ref[^>]*>.*?</ref>', '', temiz, flags=re.IGNORECASE)
        temiz = re.sub(r'<ref[^>]*>', '', temiz, flags=re.IGNORECASE)
        temiz = re.sub(r'</ref>', '', temiz, flags=re.IGNORECASE)
        # 3. <syntaxhighlight...> </syntaxhighlight> gibi teknik HTML/XML etiketlerini kaldır
        temiz = re.sub(r'<[^>]+>', ' ', temiz)
        # 4. küçükresim|, upright=...|, sağ|, sol|, thumb| gibi MediaWiki resim ve format parametrelerini temizle
        temiz = re.sub(r'(?:küçükresim|upright=[0-9.]+|sağ|sol|left|right|thumb|px|koordinatlar|bölge_hizmet|üyeler|lider_unvanı[0-9]*|lider_adı[0-9]*|kilit_insanlar)\s*(?:=\s*[^|\]]*)?\|?', '', temiz, flags=re.IGNORECASE)
        # 5. doğum_yeri = ..., ölüm_tarihi = ... gibi bilgi kutusu (infobox) parametrelerini temizle
        temiz = re.sub(r'[a-zA-Z0-9_ğüşıöçĞÜŞİÖÇ]+\s*=\s*[^|\]]*', ' ', temiz)
        # 6. [[Bağlantı|Görünür Metin]] -> Görünür Metin, [[Görünür Metin]] -> Görünür Metin
        temiz = re.sub(r'\[\[(?:[^|\]]*\|)?([^\]]+)\]\]', r'\1', temiz)
        temiz = re.sub(r'\[\[|\]\]', '', temiz)
        # 7. -- >, --> gibi fazlalık ok sembollerini kaldır
        temiz = re.sub(r'--\s*>', '', temiz)
        # 8. || veya | sembollerini sadeleştir (köşeli parantez içindeki [kelime] vurgularına dokunma)
        temiz = re.sub(r'\|+', ' ', temiz)
        # 9. Çift veya fazla boşlukları tek boşluğa indir
        temiz = re.sub(r'\s+', ' ', temiz).strip()
        return temiz

    def baslik_uydur(tam_metin):
        """Metnin ilk cümlesinden veya başından son kullanıcı için temiz ve anlaşılır bir başlık çıkarır."""
        temiz = wiki_metni_sadelestir(tam_metin)
        ilk_cumle = temiz.split('.')[0].strip()
        if len(ilk_cumle) > 75:
            ilk_cumle = ilk_cumle[:75] + "..."
        return ilk_cumle if ilk_cumle else "Wikipedia İçeriği"

    # 1. AŞAMA: TÜM KELİMELERİN GEÇTİĞİ ESNEK ARAMA (AND - Konumdan bağımsız)
    fts_sorgu_and = " AND ".join(kelimeler)
    sql_and = """
        SELECT 
            metin, 
            snippet(makaleler, 1, '[', ']', ' ... ', 50) AS ozet
        FROM makaleler 
        WHERE makaleler MATCH ? 
        ORDER BY rank 
        LIMIT ?
    """
    try:
        cursor.execute(sql_and, (fts_sorgu_and, limit))
        sonuclar = cursor.fetchall()
        if sonuclar:
            return [{
                'baslik': baslik_uydur(row[0]),
                'ozet': wiki_metni_sadelestir(row[1]),
                'detay': wiki_metni_sadelestir(row[0])[:1500],
                'eslesme_durumu': 'Aradığınız kelimelerin tamamı metinde bulundu.'
            } for row in sonuclar]
    except sqlite3.OperationalError:
        pass

    # 2. AŞAMA: ESNEK KOMBİNASYON ARAMASI (OR + Alaka Sıralaması)
    fts_sorgu_or = " OR ".join(kelimeler)
    sql_or = """
        SELECT 
            metin, 
            snippet(makaleler, 1, '[', ']', ' ... ', 50) AS ozet
        FROM makaleler 
        WHERE makaleler MATCH ? 
        ORDER BY rank 
        LIMIT ?
    """
    try:
        cursor.execute(sql_or, (fts_sorgu_or, limit))
        sonuclar = cursor.fetchall()
        return [{
            'baslik': baslik_uydur(row[0]),
            'ozet': wiki_metni_sadelestir(row[1]),
            'detay': wiki_metni_sadelestir(row[0])[:1500],
            'eslesme_durumu': 'Aradığınız kelimelerin tamamı metinde bulundu.' if "AND" in fts_sorgu_or else 'Aradığınız kelimelerden en alakalı olanlar metinde bulundu.'
        } for row in sonuclar]
    except sqlite3.OperationalError:
        return []


# ==========================================
# 3. İNTERAKTİF KULLANICI ARAMA EKRANI (SON KULLANICI ARAYÜZÜ)
# ==========================================
def interaktif_arama():
    txt_yolu = "wiki_temiz.txt"
    db_yolu = "wiki_fts.db"
    
    print("Wikipedia Kütüphanesi Yükleniyor... Lütfen Bekleyin...")
    conn = veritabani_kur(txt_dosyasi=txt_yolu, db_dosyasi=db_yolu, max_satir=100000, batch_size=5000)
    if not conn:
        return

    print("\n" + "="*70)
    print("                  WİKİPEDİA AKILLI ARAMA ASİSTANI                  ")
    print("="*70)
    print("Merhaba! Wikipedia kütüphanesinde istediğiniz konuyu arayabilirsiniz.")
    print(" • Tek bir kelime, birden fazla kelime veya tam bir cümle yazabilirsiniz.")
    print(" • Çıkış yapmak için 'q' tuşuna basıp Enter'a basmanız yeterlidir.")
    print("="*70 + "\n")

    while True:
        try:
            kullanici_girisi = input("Arama Kutusu > ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nİyi günler dileriz! Çıkış yapılıyor...")
            break

        if kullanici_girisi.lower() in ['q', 'çıkış', 'exit', 'quit']:
            print("İyi günler dileriz! Çıkış yapılıyor...")
            break

        if not kullanici_girisi:
            continue

        baslangic = time.time()
        # En alakalı 30 başlığı getirelim
        sonuclar = esnek_arama(conn, kullanici_girisi, limit=30)
        sure_sn = time.time() - baslangic

        if not sonuclar:
            print(f"\nÜzgünüz, '{kullanici_girisi}' ile ilgili kütüphanede hiçbir içerik bulunamadı.")
            print("Lütfen farklı kelimelerle tekrar deneyin.\n")
            continue

        print(f"\n======================================================================")
        print(f"\"{kullanici_girisi}\" İÇİN EN ALAKALI {len(sonuclar)} SONUÇ BULUNDU ({sure_sn:.3f} saniyede arandı)")
        print(f"======================================================================")

        for idx, sonuc in enumerate(sonuclar, start=1):
            print(f" {idx:2d}. {sonuc['baslik']}")

        print("-" * 70)

        # Kullanıcının 1-30 arasından seçim yapıp detayını incelemesi için alt döngü
        while True:
            secim = input("\nDetayını görmek istediğiniz sonucun numarasını yazın (Yeni arama için 'y', çıkış için 'q'): ").strip().lower()
            if secim in ['y', 'yeni']:
                print()
                break
            elif secim in ['q', 'çıkış', 'exit', 'quit']:
                print("\nİyi günler dileriz! Çıkış yapılıyor...")
                conn.close()
                return

            if secim.isdigit():
                num = int(secim)
                if 1 <= num <= len(sonuclar):
                    secilen = sonuclar[num - 1]
                    print("\n" + "="*70)
                    print(f"[{num}. SONUÇ DETAYI]")
                    print("="*70)
                    print(f" • Konu Başlığı  : {secilen['baslik']}")
                    print(f" • Eşleşme Durumu: {secilen['eslesme_durumu']}")
                    print(f" • İçerik Özeti  : \"... {secilen['ozet']} ...\"")
                    print("-" * 70)
                    print(" • Makaleden Geniş Metin:")
                    print(f"   {secilen['detay']}")
                    print("="*70)
                else:
                    print(f"Lütfen 1 ile {len(sonuclar)} arasında geçerli bir numara girin.")
            else:
                print("Lütfen bir numara (örn: 1), yeni arama için 'y' veya çıkış için 'q' yazın.")

    conn.close()


if __name__ == "__main__":
    interaktif_arama()
