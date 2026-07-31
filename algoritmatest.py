import random
from collections import defaultdict

# ==========================================
# 1. VERİYİ TEMİZLE VE BİRLEŞTİR (GENERATOR İLE)
# ==========================================
def kelime_uretici(dosya_listesi):
    for dosya_adi in dosya_listesi:
        try:
            with open(dosya_adi, "r", encoding="utf-8") as f:
                for satir in f:
                    # Satırı kelimelere böl ve her bir kelimeyi tek tek "yield" ile gönder
                    for kelime in satir.split():
                        yield kelime
        except FileNotFoundError:
            print(f"Uyarı: '{dosya_adi}' bulunamadı, lütfen dosya adını kontrol edin.")

# Şimdilik sadece 100 MB'lık veri dosyasını test ediyoruz
dosyalar = ["veri.txt"]

# ==========================================
# 2. İSTATİSTİKİ HAFIZAYI OLUŞTUR
# ==========================================
sozluk = defaultdict(list)
kelime_akis = kelime_uretici(dosyalar)

print("'veri.txt' okunuyor ve sözlük oluşturuluyor. Lütfen bekleyin...")

try:
    w1 = next(kelime_akis)
    w2 = next(kelime_akis)
    
    for w3 in kelime_akis:
        sozluk[(w1, w2)].append(w3)
        w1, w2 = w2, w3
        
except StopIteration:
    print("Dosyada yeterli kelime bulunamadı.")

print(f"Sözlük başarıyla oluşturuldu! Toplam eşsiz 2'li kombinasyon sayısı: {len(sozluk)}")

# Hızlı arama ve dinamik eşleştirme için kelime indeksi oluşturuluyor
kelime_indeksi = defaultdict(list)
for w1, w2 in sozluk.keys():
    kelime_indeksi[w1].append((w1, w2))
    kelime_indeksi[w2].append((w1, w2))


# ==========================================
# 3. CÜMLE ÜRETİM MOTORUNU YAZ (KULLANICI GİRİŞLİ)
# ==========================================
if not sozluk:
    print("Sözlük boş olduğu için metin üretilemiyor.")
else:
    print("\n--- METİN ÜRETİMİNE HAZIR ---")
    print("Sistem, girdiğiniz metni (tek kelime, iki kelime veya cümle) alıp veri setindeki en uygun kombinasyonlarla devamını getirecek.")
    
    while True:
        kullanici_girisi = input("\nBaşlamak için bir metin (kelime veya cümle) yazın (Çıkmak için 'q' tuşuna basın): ")
        
        if kullanici_girisi.strip().lower() == 'q':
            print("Çıkış yapılıyor...")
            break
            
        girilen_kelimeler = kullanici_girisi.split()
        
        # 1. Kelime sayısı kısıtlamasını kaldır: Sadece girdi verilip verilmediğini kontrol et
        if not girilen_kelimeler:
            print("Uyarı: Lütfen en az bir kelime girin!")
            continue
            
        uretilen_cumle = list(girilen_kelimeler)
        mevcut_durum = None
        
        # 2 & 3. Adjacency zorunluluğunu kaldır ve dinamik eşleştirme yap
        # A) Girilen metnin son iki kelimesi veri setinde yan yana geçiyorsa doğrudan kullan
        if len(girilen_kelimeler) >= 2 and (girilen_kelimeler[-2], girilen_kelimeler[-1]) in sozluk:
            mevcut_durum = (girilen_kelimeler[-2], girilen_kelimeler[-1])
            
        # B) Son iki kelime eşleşmediyse, cümle içindeki herhangi bir ardışık ikiliyi sondan başa doğru ara
        if not mevcut_durum and len(girilen_kelimeler) >= 2:
            for i in range(len(girilen_kelimeler) - 2, -1, -1):
                cift = (girilen_kelimeler[i], girilen_kelimeler[i+1])
                if cift in sozluk:
                    mevcut_durum = cift
                    print(f"Bilgi: Girdi içindeki '{cift[0]} {cift[1]}' ikilisi üzerinden bağlantı kuruldu.")
                    break
                    
        # C) Hiçbir ardışık ikili bulunamadıysa veya tek kelime girildiyse, kelime bazlı dinamik arama yap
        if not mevcut_durum:
            for kelime in reversed(girilen_kelimeler):
                if kelime in kelime_indeksi:
                    # Kelimenin ilk eleman olduğu çiftleri önceliklendir (böylece akış doğal devam eder)
                    ciftler_k1 = [c for c in kelime_indeksi[kelime] if c[0] == kelime]
                    if ciftler_k1:
                        secilen_cift = random.choice(ciftler_k1)
                        # Eğer seçilen çiftin ikinci kelimesi cümlede henüz yoksa ekle
                        if len(uretilen_cumle) < 2 or (uretilen_cumle[-2], uretilen_cumle[-1]) != secilen_cift:
                            uretilen_cumle.append(secilen_cift[1])
                        mevcut_durum = secilen_cift
                    else:
                        secilen_cift = random.choice(kelime_indeksi[kelime])
                        mevcut_durum = secilen_cift
                    print(f"Bilgi: '{kelime}' kelimesi üzerinden veri setindeki '{secilen_cift[0]} {secilen_cift[1]}' bağlantısı yakalandı.")
                    break
                    
        # D) Girilen kelimelerin hiçbiri veri setinde yoksa esnek başlangıç (rastgele bir çift) seç
        if not mevcut_durum:
            secilen_cift = random.choice(list(sozluk.keys()))
            mevcut_durum = secilen_cift
            print(f"Bilgi: Girilen kelimeler veri setinde bulunamadı. '{secilen_cift[0]} {secilen_cift[1]}' kombinasyonu ile esnek bağlantı kuruldu.")
            
        # Hedef kelime sayısını girdinin uzunluğuna göre dinamik belirle
        hedef_kelime_sayisi = max(40, len(uretilen_cumle) + 30)
        
        while len(uretilen_cumle) < hedef_kelime_sayisi:
            if mevcut_durum in sozluk:
                secilen_kelime = random.choice(sozluk[mevcut_durum])
                uretilen_cumle.append(secilen_kelime)
                mevcut_durum = (mevcut_durum[1], secilen_kelime)
            else:
                break
                
        sonuc = " ".join(uretilen_cumle)
        
        print("\n--- ÜRETİLEN METİN ---")
        print(sonuc)