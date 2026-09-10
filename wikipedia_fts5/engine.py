#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""SQLite FTS5 tabanlı, çevrimdışı Türkçe Wikipedia arama motoru."""

import html
import os
import re
import sqlite3
import time


PROJE_DIZINI = os.path.dirname(os.path.abspath(__file__))
VURGU_AC = "\ue000"
VURGU_KAPAT = "\ue001"
SEMA_SURUMU = "2"
TURKCE_HARF_DONUSUMU = str.maketrans({"I": "ı", "İ": "i"})

# Büyük dökümler işlenirken her makale için yeniden derlenmemeleri gereken desenler.
KELIME_DESENI = re.compile(r"\w+", re.UNICODE)
OZET_KELIME_DESENI = re.compile(r"\w+(?:['’]\w+)*", re.UNICODE)
TABLO_ISARETI_DESENI = re.compile(
    r"(?:\{\||\|\}|\|\s*-|!!|\b(?:rowspan|colspan|width)\s*=)", re.IGNORECASE
)
BASLANGIC_ARTIGI_DESENI = re.compile(r"^(?:--\s*>|}})\s*")
BILGI_KUTUSU_ALANI_DESENI = re.compile(
    r"(?:^|\|)\s*[\wçğıöşüÇĞİÖŞÜ -]{1,45}\s*=", re.UNICODE
)
HTML_YORUM_DESENI = re.compile(r"<!--.*?-->", re.DOTALL)
YETIM_BILGI_KUTUSU_BASLIGI_DESENI = re.compile(r"^([^,.|{}]{2,100}),{1,2}[^{}]{0,250}}}\s*")
THUMB_DIV_DESENI = re.compile(
    r"<div\b[^>]*class=[\"'][^\"']*thumb[^\"']*[\"'][^>]*>.*?"
    r"</div>\s*</div>\s*</div>",
    re.IGNORECASE | re.DOTALL,
)
REF_BLOK_DESENI = re.compile(r"<ref\b[^>]*>.*?</ref\s*>", re.IGNORECASE | re.DOTALL)
REF_TEK_DESENI = re.compile(r"<ref\b[^>]*/\s*>", re.IGNORECASE)
REF_ETIKET_DESENI = re.compile(r"</?ref\b[^>]*>", re.IGNORECASE)
MEDYA_BLOK_DESENI = re.compile(
    r"<(?:math|gallery|timeline|imagemap|score)\b[^>]*>.*?"
    r"</(?:math|gallery|timeline|imagemap|score)\s*>",
    re.IGNORECASE | re.DOTALL,
)
SATIR_SONU_DESENI = re.compile(r"<br\s*/?>", re.IGNORECASE)
HTML_ETIKET_DESENI = re.compile(r"<[^>]+>")
YARIM_HTML_ETIKET_DESENI = re.compile(r"<[A-Za-z/][^>]*$")
DOSYA_BAGLANTISI_DESENI = re.compile(
    r"\[\[(?:Dosya|File|Image):.*?\]\]", re.IGNORECASE | re.DOTALL
)
KÜÇÜKRESIM_BAGLANTISI_DESENI = re.compile(
    r"(?:küçükresim|thumbnail|thumb)(?:\|[^\[\]\n]{0,200})?\[\[[^\[\]]{0,500}\]\]",
    re.IGNORECASE | re.DOTALL,
)
KÜÇÜKRESIM_ARTIGI_DESENI = re.compile(
    r"(?:küçükresim|thumbnail|thumb)(?:\|[\wçğıöşüÇĞİÖŞÜ .='-]{0,50})*\|?\s*"
    r"[^.!?]{0,220}?\b(?:görünümü|görüntüsü|fotoğrafı|resmi|portresi|haritası|şeması|logosu|konumu|tablosu)\b\s*",
    re.IGNORECASE,
)
KATEGORI_BAGLANTISI_DESENI = re.compile(
    r"\[\[(?:Kategori|Category):.*?\]\]", re.IGNORECASE | re.DOTALL
)
YETIM_ALAN_DESENI = re.compile(r"\|\s*[\wçğıöşüÇĞİÖŞÜ -]{1,45}\s*=\s*[^|{}]*")
IC_BAGLANTI_DESENI = re.compile(r"\[\[([^\[\]]+)\]\]")
DOSYA_VE_KATEGORI_ON_EKI_DESENI = re.compile(
    r"^(?:Kategori|Category|Dosya|File|Image):", re.IGNORECASE
)
ETIKETLI_DIS_BAGLANTI_DESENI = re.compile(
    r"\[(?:https?|ftp)://[^\s\]]+\s+([^\]]+)\]", re.IGNORECASE
)
DIS_BAGLANTI_DESENI = re.compile(r"\[(?:https?|ftp)://[^\]]+\]", re.IGNORECASE)
URL_DESENI = re.compile(r"\b(?:https?|ftp)://\S+", re.IGNORECASE)
WWW_DESENI = re.compile(r"\bwww\.\S+", re.IGNORECASE)
VIKIPEDI_KOPYA_NOTU_DESENI = re.compile(
    r"Bu sayfa,?\s+Türkçe Vikipedi(?:'den|den) kopyalandığı tarihten sonraki değişimleri göstermez\.?",
    re.IGNORECASE,
)
KATEGORI_KUYRUGU_DESENI = re.compile(r"\b(?:Kategori|Category)\s*:.*$", re.IGNORECASE)
DOSYA_ARTIGI_DESENI = re.compile(r"\b(?:Dosya|File|Image)\s*:\s*\S+", re.IGNORECASE)
DAVRANIS_ANAHTARI_DESENI = re.compile(
    r"__(?:NOTOC|TOC|FORCETOC|NOINDEX|INDEX)__", re.IGNORECASE
)
BOLUM_BASLIGI_DESENI = re.compile(r"={2,}\s*([^=]+?)\s*={2,}")
VIKI_VURGU_DESENI = re.compile(r"'{2,5}")
KAÇIS_ARTIGI_DESENI = re.compile(r"\\+[A-Za-z][\w-]*")
ALT_ALANI_DESENI = re.compile(r"(?<!\w)alt\s*=\s*(?=\||\s|$)", re.IGNORECASE)
RESIM_PARAMETRESI_DESENI = re.compile(
    r"(?<!\w)(?:küçükresim|thumbnail|thumb|upright(?:\s*=\s*[\d.]+)?|sağ|sol|left|right)(?!\w)\s*\|?",
    re.IGNORECASE,
)
PIKSEL_DESENI = re.compile(r"(?<!\w)\d+\s*px(?!\w)", re.IGNORECASE)
BOYUT_DESENI = re.compile(r"(?<!\w)\d+\s*x\s*\d+\s*(?:px|pik)(?!\w)", re.IGNORECASE)
TABLO_NITELIGI_DESENI = re.compile(
    r"\b(?:width|height|rowspan|colspan|align|class|style)\s*=\s*(?:[\"'][^\"']*[\"']|[^\s|!]+)",
    re.IGNORECASE,
)
LISTE_ISARETI_DESENI = re.compile(r"(?:^|\s)[*#;]+\s*")
GIRINTI_DESENI = re.compile(r"\s:{1,3}\s")
VIKI_AYRACI_DESENI = re.compile(r"\{+|}+|\[\[|\]\]|\{\||\|}")
DIGER_AYRAÇ_DESENI = re.compile(r"\|+|~~+")
YORUM_KAPANISI_DESENI = re.compile(r"(?:--\s*>|-->)+")
NOKTALAMA_BOSLUGU_DESENI = re.compile(r"\s+([,.;:!?])")
YINELENEN_NOKTALAMA_DESENI = re.compile(r"([,;:])(?:\s*\1)+")
VIRGUL_NOKTA_DESENI = re.compile(r",\s*\.")
UZUN_NOKTA_DESENI = re.compile(r"\.{3,}")
BOSLUK_DESENI = re.compile(r"\s+")
YINELENEN_ILK_KELIME_DESENI = re.compile(r"^(\w{2,})\s+\1\b", re.IGNORECASE | re.UNICODE)
CUMLE_DESENI = re.compile(r"(?<=[.!?])\s+")
CUMLE_SONU_DESENI = re.compile(r"[.!?…](?=\s|$)")
KISALTMA_DESENI = re.compile(r"\b(?:d|ö|bkz|vb|vs|dr|prof|doç|sn)\.$", re.IGNORECASE)
BASLIK_ISARETI_DESENI = re.compile(r"^[\W_]+", re.UNICODE)
BASLIK_YILI_DESENI = re.compile(r"^\d{3,4}\s+(?=[A-ZÇĞİÖŞÜ])")
BASLIK_RESIM_ARTIGI_DESENI = re.compile(
    r"^(?:harita|resim|şekil)\s*bağı\s*[-–—]?\s*", re.IGNORECASE
)
BASLIK_TAKMA_AD_DESENI = re.compile(
    r"\s+(?:ya da|veya)\s+(?:tarih[iî]\s+)?(?:adı|ismi)(?:yla|yle)?\b", re.IGNORECASE
)
BASLIK_VEYA_DESENI = re.compile(r"\s+(?:ya da|veya)\s+", re.IGNORECASE)
TANIM_BASLANGICI_DESENI = re.compile(
    r"^(?:bir\b|adıyla\b|adlı\b|olarak\b|türüdür\b|dalıdır\b|kişidir\b)"
)
TANIM_SONU_DESENI = re.compile(r"\b\w+(?:dır|dir|dur|dür|tır|tir|tur|tür)\b[^.!?]{0,20}[.!?]?$")
ZAYIF_BASLIK_DESENI = re.compile(
    r"^(?:bu|buna|bunun|burada|böylece|ancak|daha sonra|sonrasında|ilki|"
    r"ilkbahar|yaz|sonbahar|kış|\d{3,4}\s*[-–—])\b"
)
VIRGULLU_TANIM_DESENI = re.compile(r"^(.{2,110}?)(?:\s*\([^)]{0,120}\))*\s*,\s+(.+)$")
PARANTEZLI_BASLIK_DESENI = re.compile(
    r"^([A-ZÇĞİÖŞÜ0-9][\wçğıöşüÇĞİÖŞÜ .'-]{1,80}?)\s*\("
)
KÜÇÜKRESIM_BASLANGICI_DESENI = re.compile(
    r"^\s*(?:küçükresim|thumbnail|thumb)\b", re.IGNORECASE
)
DENGELI_BLOK_DESENLERI = {
    ("{{", "}}"): re.compile(r"\{\{(?:(?!\{\{|\}\}).)*\}\}", re.DOTALL),
    ("{|", "|}"): re.compile(r"\{\|(?:(?!\{\||\|}).)*\|}", re.DOTALL),
}

# Tek başına arandığında anlamlı sonuç üretmeyen yaygın Türkçe görev sözcükleri.
TURKCE_DURAK_KELIMELERI = {
    "acaba", "ama", "ancak", "artık", "asla", "aslında", "az", "bana", "bazı",
    "belki", "ben", "beni", "benim", "beri", "bile", "bir", "biraz", "biz",
    "bize", "bizi", "bizim", "bu", "buna", "bunda", "bundan", "bunlar", "bunu",
    "çok", "çünkü", "da", "daha", "de", "değil", "diye", "en", "fakat", "gibi",
    "hem", "hep", "hepsi", "her", "hiç", "için", "ile", "ise", "işte", "kadar",
    "karşın", "kendi", "ki", "kim", "mı", "mi", "mu", "mü", "nasıl", "ne",
    "neden", "nerede", "o", "olan", "olarak", "oldu", "olduğu", "olmak", "olur",
    "ona", "onlar", "onu", "pek", "rağmen", "sadece", "şey", "siz", "şu", "tüm",
    "ve", "veya", "ya", "yani", "yerine", "yine", "yoksa", "zaten",
}


def _arama_norm(metin):
    """Karşılaştırma amacıyla Türkçe metni kararlı biçimde normalleştirir."""
    return (metin or "").translate(TURKCE_HARF_DONUSUMU).casefold()


def arama_terimlerini_ayikla(sorgu_metni):
    """FTS sorgusuna girecek anlamlı, benzersiz terimleri döndürür."""
    if not isinstance(sorgu_metni, str):
        return []

    terimler = KELIME_DESENI.findall(sorgu_metni.strip())
    sonuc = []
    gorulen = set()
    for terim in terimler:
        normal = _arama_norm(terim)
        if normal in TURKCE_DURAK_KELIMELERI or normal in gorulen:
            continue
        gorulen.add(normal)
        sonuc.append(terim)
    return sonuc


def _dengeli_bloklari_sil(metin, acilis, kapanis):
    """İç içe geçmiş şablon benzeri blokları güvenli biçimde kaldırır."""
    # Önce en içteki tam çiftleri sil. Kapanışı kayıp bir şablonda bütün makale
    # kuyruğunu atmak yerine yalnızca kalan ayraçları kaldır.
    desen = DENGELI_BLOK_DESENLERI.get((acilis, kapanis))
    if desen is None:
        desen = re.compile(
            re.escape(acilis)
            + r"(?:(?!"
            + re.escape(acilis)
            + "|"
            + re.escape(kapanis)
            + r").)*"
            + re.escape(kapanis),
            flags=re.DOTALL,
        )
    temiz = metin
    for _ in range(30):
        yeni = desen.sub(" ", temiz)
        if yeni == temiz:
            break
        temiz = yeni
    return temiz.replace(acilis, " ").replace(kapanis, " ")


def _baslangictaki_bilgi_kutusunu_sil(metin):
    """Dökümde açılışı kaybolmuş bilgi kutusu alanlarını makale girişinden ayırır."""
    temiz = metin.lstrip()
    temiz = BASLANGIC_ARTIGI_DESENI.sub("", temiz)

    # Bazı satırlar açılış '{{' olmadan onlarca '| alan = değer' ile başlıyor.
    for _ in range(4):
        kapanis = temiz.find("}}")
        if kapanis < 0 or kapanis > 12000:
            break
        on_ek = temiz[:kapanis]
        alan_sayisi = len(BILGI_KUTUSU_ALANI_DESENI.findall(on_ek))
        if alan_sayisi >= 2 or (alan_sayisi >= 1 and on_ek.count("|") >= 3):
            temiz = temiz[kapanis + 2 :].lstrip()
            continue
        break
    return temiz


def _vurgulari_dengele(metin):
    """Yalnızca tam eşleşmiş özel vurgu çiftlerini kullanıcı biçimine çevirir."""
    sonuc = []
    acik = False
    for karakter in metin:
        if karakter == VURGU_AC:
            if not acik:
                sonuc.append("[")
                acik = True
        elif karakter == VURGU_KAPAT:
            if acik:
                sonuc.append("]")
                acik = False
        else:
            sonuc.append(karakter)
    if acik:
        for i in range(len(sonuc) - 1, -1, -1):
            if sonuc[i] == "[":
                del sonuc[i]
                break
    return "".join(sonuc)


def wiki_metni_sadelestir(metin):
    """Ham MediaWiki metnini okunabilir, tek satırlı düz metne dönüştürür."""
    if not metin:
        return ""
    if not isinstance(metin, str):
        metin = str(metin)

    tablo_isaretli = bool(TABLO_ISARETI_DESENI.search(metin))
    temiz = metin.replace("\ufeff", " ")
    for _ in range(3):
        yeni = html.unescape(temiz)
        if yeni == temiz:
            break
        temiz = yeni

    temiz = "".join(
        karakter if karakter in "\t\n\r" or ord(karakter) >= 32 else " "
        for karakter in temiz
    )
    temiz = HTML_YORUM_DESENI.sub(" ", temiz)
    temiz = _baslangictaki_bilgi_kutusunu_sil(temiz)
    temiz = YETIM_BILGI_KUTUSU_BASLIGI_DESENI.sub(r"\1 ", temiz)

    temiz = THUMB_DIV_DESENI.sub(" ", temiz)

    # İçerikleri kullanıcıya değer katmayan bloklar.
    temiz = REF_BLOK_DESENI.sub(" ", temiz)
    temiz = REF_TEK_DESENI.sub(" ", temiz)
    temiz = REF_ETIKET_DESENI.sub(" ", temiz)
    temiz = MEDYA_BLOK_DESENI.sub(" ", temiz)
    temiz = SATIR_SONU_DESENI.sub(". ", temiz)
    temiz = HTML_ETIKET_DESENI.sub(" ", temiz)
    temiz = YARIM_HTML_ETIKET_DESENI.sub(" ", temiz)

    # Dosya/resim bağlantılarını, bağlantı normalleştirmesinden önce bütünüyle at.
    temiz = DOSYA_BAGLANTISI_DESENI.sub(" ", temiz)
    temiz = KÜÇÜKRESIM_BAGLANTISI_DESENI.sub(" ", temiz)
    temiz = KÜÇÜKRESIM_ARTIGI_DESENI.sub(" ", temiz)
    temiz = KATEGORI_BAGLANTISI_DESENI.sub(" ", temiz)

    # Kapanış ayraçları dururken yetim '| alan = değer' parçalarını temizle;
    # aksi halde alan değeri yanlışlıkla makale girişine kadar uzayabilir.
    temiz = YETIM_ALAN_DESENI.sub(" ", temiz)

    temiz = _dengeli_bloklari_sil(temiz, "{{", "}}")
    temiz = _dengeli_bloklari_sil(temiz, "{|", "|}")

    # İç içe bağlantıları içeriden dışarıya doğru düzleştir.
    for _ in range(8):
        if not IC_BAGLANTI_DESENI.search(temiz):
            break

        def baglanti_metni(eslesme):
            icerik = eslesme.group(1).strip()
            if DOSYA_VE_KATEGORI_ON_EKI_DESENI.match(icerik):
                return " "
            return icerik.rsplit("|", 1)[-1].strip()

        temiz = IC_BAGLANTI_DESENI.sub(baglanti_metni, temiz)

    temiz = ETIKETLI_DIS_BAGLANTI_DESENI.sub(r"\1", temiz)
    temiz = DIS_BAGLANTI_DESENI.sub(" ", temiz)
    temiz = URL_DESENI.sub(" ", temiz)
    temiz = WWW_DESENI.sub(" ", temiz)
    temiz = VIKIPEDI_KOPYA_NOTU_DESENI.sub(" ", temiz)

    # Dökümün sonundaki kategori dizilerini ve kalan dosya belirteçlerini kaldır.
    temiz = KATEGORI_KUYRUGU_DESENI.sub(" ", temiz)
    temiz = DOSYA_ARTIGI_DESENI.sub(" ", temiz)
    temiz = DAVRANIS_ANAHTARI_DESENI.sub(" ", temiz)

    # Başlık, tablo, liste, resim ve güzergâh şablonlarından kalan işaretler.
    temiz = BOLUM_BASLIGI_DESENI.sub(r". \1. ", temiz)
    temiz = VIKI_VURGU_DESENI.sub("", temiz)
    temiz = KAÇIS_ARTIGI_DESENI.sub(" ", temiz)
    temiz = ALT_ALANI_DESENI.sub(" ", temiz)
    temiz = RESIM_PARAMETRESI_DESENI.sub(" ", temiz)
    temiz = PIKSEL_DESENI.sub(" ", temiz)
    temiz = BOYUT_DESENI.sub(" ", temiz)
    temiz = TABLO_NITELIGI_DESENI.sub(" ", temiz)
    temiz = LISTE_ISARETI_DESENI.sub(" ", temiz)
    temiz = GIRINTI_DESENI.sub(". ", temiz)
    temiz = VIKI_AYRACI_DESENI.sub(" ", temiz)
    temiz = temiz.replace("[", " ").replace("]", " ")
    temiz = DIGER_AYRAÇ_DESENI.sub(" ", temiz)
    if tablo_isaretli:
        temiz = temiz.replace("!", " ")
    temiz = temiz.replace("↑", " ")
    temiz = YORUM_KAPANISI_DESENI.sub(" ", temiz)
    temiz = NOKTALAMA_BOSLUGU_DESENI.sub(r"\1", temiz)
    temiz = YINELENEN_NOKTALAMA_DESENI.sub(r"\1", temiz)
    temiz = VIRGUL_NOKTA_DESENI.sub(",", temiz)
    temiz = UZUN_NOKTA_DESENI.sub("…", temiz)
    temiz = BOSLUK_DESENI.sub(" ", temiz).strip(" \t\r\n|,;:-")
    temiz = YINELENEN_ILK_KELIME_DESENI.sub(r"\1", temiz)
    return _vurgulari_dengele(temiz)


def _altyazi_veya_junk_cumle(cumle):
    normal = _arama_norm(cumle)
    isaretler = (
        "küçükresim", "resimde", "fotoğraf", "fotoğrafı", "görüntüsü", "görülüyor",
        "logosu", "portresi", "haritası", "haritadan", "şeması", "diyagram",
        "ekran yakalama", "bayrağı", "arması",
    )
    return any(isaret in normal for isaret in isaretler)


def _baslik_adayi_temizle(aday):
    aday = BASLIK_ISARETI_DESENI.sub("", aday).strip()
    aday = BASLIK_YILI_DESENI.sub("", aday)
    aday = BASLIK_RESIM_ARTIGI_DESENI.sub("", aday)
    aday = BASLIK_TAKMA_AD_DESENI.split(aday, maxsplit=1)[0]
    aday = BASLIK_VEYA_DESENI.split(aday, maxsplit=1)[0]
    aday = BOSLUK_DESENI.sub(" ", aday).strip(" ,;:-–—()[]")
    kelimeler = aday.split()
    if len(kelimeler) >= 2:
        for uzunluk in range(1, (len(kelimeler) // 2) + 1):
            ilk = [_arama_norm(kelime) for kelime in kelimeler[:uzunluk]]
            ikinci = [_arama_norm(kelime) for kelime in kelimeler[uzunluk : uzunluk * 2]]
            if ilk == ikinci:
                aday = " ".join(kelimeler[uzunluk:])
                break
    return aday


def _tanim_devami_mi(devam):
    normal = _arama_norm(devam).strip()
    if TANIM_BASLANGICI_DESENI.match(normal):
        return True
    return bool(TANIM_SONU_DESENI.search(normal))


def _zayif_baslik_baslangici(cumle):
    normal = _arama_norm(cumle).lstrip()
    return bool(
        ZAYIF_BASLIK_DESENI.match(normal)
    )


def _temiz_metinden_baslik(temiz):
    """Önceden temizlenmiş giriş cümlelerinden güvenli bir başlık çıkarır."""
    if not temiz:
        return "Başlıksız ansiklopedi maddesi"

    cumleler = [c.strip() for c in CUMLE_DESENI.split(temiz) if c.strip()]
    adaylar = []
    for sira, cumle in enumerate(cumleler[:8]):
        if len(cumle) < 3 or _altyazi_veya_junk_cumle(cumle):
            continue

        eslesme = VIRGULLU_TANIM_DESENI.match(cumle)
        if eslesme:
            aday = _baslik_adayi_temizle(eslesme.group(1))
            if _zayif_baslik_baslangici(aday):
                continue
            devam = _arama_norm(eslesme.group(2))
            puan = 8 - (sira * 1.5)
            if _tanim_devami_mi(devam):
                puan += 3
            if 1 <= len(aday.split()) <= 12 and 2 <= len(aday) <= 100:
                puan += min(_arama_norm(temiz[:1200]).count(_arama_norm(aday)), 3)
                adaylar.append((puan, aday))

        parantez = PARANTEZLI_BASLIK_DESENI.match(cumle)
        if parantez:
            aday = _baslik_adayi_temizle(parantez.group(1))
            if _zayif_baslik_baslangici(aday):
                continue
            if 1 <= len(aday.split()) <= 10:
                tekrar = min(_arama_norm(temiz[:1200]).count(_arama_norm(aday)), 3)
                adaylar.append((7 - (sira * 1.5) + tekrar, aday))

    if adaylar:
        # Eşit puanda metinde daha önce görülen aday gerçek madde adı olmaya daha yakındır.
        baslik = max(adaylar, key=lambda oge: oge[0])[1]
        return baslik.rstrip(".")

    for cumle in cumleler:
        if _altyazi_veya_junk_cumle(cumle) or _zayif_baslik_baslangici(cumle):
            continue
        cumle = _baslik_adayi_temizle(cumle)
        if not cumle:
            continue
        if len(cumle) <= 140:
            return cumle.rstrip(".")
        sinir = max(cumle.rfind(";", 0, 140), cumle.rfind(":", 0, 140))
        if sinir >= 30:
            return cumle[:sinir].strip().rstrip(".")
        kelime_siniri = cumle.rfind(" ", 0, 137)
        if kelime_siniri >= 30:
            return cumle[:kelime_siniri].rstrip(" ,;:-") + "…"

    return "Başlıksız ansiklopedi maddesi"


def baslik_uydur(tam_metin):
    """Ham metinden kısa, işaretsiz ve kelime ortasında kesilmeyen başlık çıkarır."""
    return _temiz_metinden_baslik(wiki_metni_sadelestir(tam_metin))


def metni_guvenli_kisalt(metin, en_fazla_karakter=1500):
    """Metni tercihen cümle, değilse kelime sınırında kısaltır."""
    temiz = (metin or "").strip()
    if len(temiz) <= en_fazla_karakter:
        return temiz

    parca = temiz[: en_fazla_karakter + 1]
    cumle_sonlari = []
    for eslesme in CUMLE_SONU_DESENI.finditer(parca):
        if eslesme.end() > en_fazla_karakter:
            continue
        if eslesme.end() < int(en_fazla_karakter * 0.55):
            continue
        oncesi = parca[max(0, eslesme.start() - 12) : eslesme.end()]
        if eslesme.group(0) == "." and KISALTMA_DESENI.search(oncesi):
            continue
        cumle_sonlari.append(eslesme.end())
    if cumle_sonlari:
        sonuc = parca[: cumle_sonlari[-1]].strip()
        if sonuc.count("(") <= sonuc.count(")"):
            return sonuc

    kelime_siniri = parca.rfind(" ", 0, en_fazla_karakter)
    if kelime_siniri > 0:
        sonuc = parca[:kelime_siniri].rstrip(" ,;:-")
        if sonuc.count("(") > sonuc.count(")"):
            acilis = sonuc.rfind("(")
            if acilis >= int(en_fazla_karakter * 0.55):
                sonuc = sonuc[:acilis].rstrip(" ,;:-")
        return sonuc + "…"
    return temiz


def icerik_ozeti_olustur(
    temiz_metin,
    terimler,
    en_fazla_kelime=50,
    on_ek_eslesmesi=False,
):
    """İlk ilgili bölgeden, dengeli vurgular içeren yaklaşık 50 kelimelik özet üretir."""
    if not temiz_metin:
        return ""
    kelime_eslesmeleri = list(OZET_KELIME_DESENI.finditer(temiz_metin))
    if not kelime_eslesmeleri:
        return metni_guvenli_kisalt(temiz_metin, 250)

    arananlar = {_arama_norm(terim) for terim in terimler}
    ilgili_sira = next(
        (
            sira
            for sira, eslesme in enumerate(kelime_eslesmeleri)
            if _arama_norm(eslesme.group(0)) in arananlar
            or (
                on_ek_eslesmesi
                and any(_arama_norm(eslesme.group(0)).startswith(aranan) for aranan in arananlar)
            )
        ),
        0,
    )
    baslangic_sirasi = max(0, ilgili_sira - 8)
    bitis_sirasi = min(len(kelime_eslesmeleri), baslangic_sirasi + en_fazla_kelime)
    if bitis_sirasi - baslangic_sirasi < en_fazla_kelime:
        baslangic_sirasi = max(0, bitis_sirasi - en_fazla_kelime)

    baslangic = kelime_eslesmeleri[baslangic_sirasi].start()
    bitis = kelime_eslesmeleri[bitis_sirasi - 1].end()
    ozet = temiz_metin[baslangic:bitis].strip(" ,;:-")

    if terimler:
        bitis_deseni = r"\w*" if on_ek_eslesmesi else ""
        desen = re.compile(
            r"(?<!\w)((?:"
            + "|".join(sorted((re.escape(t) for t in terimler), key=len, reverse=True))
            + r")"
            + bitis_deseni
            + r")(?!\w)",
            flags=re.IGNORECASE | re.UNICODE,
        )
        ozet = desen.sub(lambda e: "[" + e.group(0) + "]", ozet)

    if baslangic > 0:
        ozet = "… " + ozet
    if bitis < len(temiz_metin):
        ozet += " …"
    return ozet


def _fts_terim_varyantlari(terim):
    """Türkçe i/ı yazım farkları için güvenli FTS terim seçenekleri üretir."""
    normal = _arama_norm(terim)
    varyantlar = [terim, normal]
    if "ı" in normal:
        varyantlar.append(normal.replace("ı", "i"))
        varyantlar.append(normal.replace("ı", "I"))
    if "i" in normal:
        varyantlar.append(normal.replace("i", "ı"))
        varyantlar.append(normal.replace("i", "İ"))
    return list(dict.fromkeys(varyantlar))


def _fts_ifadesi(terimler, operator, on_ek_eslesmesi=False):
    """Kullanıcı metnini FTS5 işleçlerinden yalıtılmış bir sorguya dönüştürür."""
    gruplar = []
    for terim in terimler:
        guvenli_varyantlar = []
        for varyant in _fts_terim_varyantlari(terim):
            guvenli = '"' + varyant.replace('"', '""') + '"'
            if on_ek_eslesmesi and len(varyant) >= 3:
                guvenli += "*"
            guvenli_varyantlar.append(guvenli)
        grup = " OR ".join(guvenli_varyantlar)
        gruplar.append("(" + grup + ")" if len(guvenli_varyantlar) > 1 else grup)
    return (" " + operator + " ").join(gruplar)


def _aday_puani(
    ham_metin,
    temiz_metin,
    baslik,
    terimler,
    fts_puani,
    sira,
    tum_terimler_eslesiyor=False,
    on_ek_eslesmesi=False,
):
    kelimeler = KELIME_DESENI.findall(temiz_metin)
    if len(temiz_metin) < 120 or len(kelimeler) < 20:
        return None
    if KÜÇÜKRESIM_BASLANGICI_DESENI.match(ham_metin) and len(kelimeler) < 45:
        return None

    ham_ornek = ham_metin[:32000]
    ham_uzunluk = max(1, len(ham_ornek))
    isaret_orani = sum(ham_ornek.count(isaret) for isaret in ("|", "{", "}", "[", "]", "\\")) / ham_uzunluk
    if isaret_orani > 0.16 and len(kelimeler) < 45:
        return None

    normal_metin = _arama_norm(temiz_metin)
    normal_ham_baslangic = _arama_norm(ham_metin[:800])
    if (
        "vikipedi:" in normal_ham_baslangic
        or "wikipedia:" in normal_ham_baslangic
        or normal_ham_baslangic.startswith("bu örnek sayfa")
        or "ilk cümle dil bilgisi kurallarına uygun" in normal_ham_baslangic
        or normal_metin.startswith("vikipedi topluluğuna")
        or ("(utc)" in normal_metin[:1200] and "mesaj" in normal_metin[:1200])
    ):
        return None
    normal_baslik = _arama_norm(baslik)
    normal_terimler = [_arama_norm(terim) for terim in terimler]
    normal_metin_kelimeleri = set(KELIME_DESENI.findall(normal_metin))
    normal_baslik_kelimeleri = set(KELIME_DESENI.findall(normal_baslik))
    ifade = " ".join(normal_terimler)
    tablo_isareti_sayisi = sum(
        ham_metin[:6000].count(isaret)
        for isaret in ("!!", "|-", "width=", "rowspan=", "colspan=")
    )
    if tablo_isareti_sayisi >= 8 and normal_baslik != ifade and normal_baslik not in normal_terimler:
        return None
    if tum_terimler_eslesiyor:
        eslesen = len(normal_terimler)
    else:
        eslesen = sum(
            1
            for terim in normal_terimler
            if terim in normal_metin_kelimeleri
            or (
                on_ek_eslesmesi
                and any(kelime.startswith(terim) for kelime in normal_metin_kelimeleri)
            )
        )
    baslikta_tam = sum(1 for terim in normal_terimler if terim in normal_baslik_kelimeleri)
    baslikta_on_ek = sum(
        1
        for terim in normal_terimler
        if terim not in normal_baslik_kelimeleri
        and on_ek_eslesmesi
        and any(kelime.startswith(terim) for kelime in normal_baslik_kelimeleri)
    )

    puan = (
        (eslesen * 5.0)
        + (baslikta_tam * 7.0)
        + (baslikta_on_ek * 3.0)
        + min(len(kelimeler) / 120.0, 3.0)
    )
    if ifade and ifade == normal_baslik:
        puan += 22.0
    elif ifade and ifade in normal_baslik:
        puan += 10.0
    if normal_baslik in normal_terimler:
        puan += 14.0
    if ifade and ifade in normal_metin[:500]:
        puan += 4.0

    ilk_konumlar = [normal_metin.find(terim) for terim in normal_terimler]
    if ilk_konumlar and all(konum >= 0 for konum in ilk_konumlar):
        yayilim = max(ilk_konumlar) - min(ilk_konumlar)
        puan += max(0.0, 8.0 - (yayilim / 100.0))

    if "şu anlamlara gelebilir" in normal_metin or "anlam ayrımı" in normal_metin:
        puan -= 12.0
    if "bu dizin ile maddelerin" in normal_metin or "ilk iki harfine göre" in normal_metin:
        puan -= 15.0
    if baslik == "Başlıksız ansiklopedi maddesi":
        puan -= 10.0

    # BM25 yalnızca eşit kalitedeki adaylarda belirleyici olsun; kısa/junk satırları öne taşımasın.
    bm25_katkisi = min(max(-float(fts_puani or 0.0), 0.0), 25.0) * 0.08
    return puan + bm25_katkisi - (sira * 0.0001)


def _ayni_veya_yakin_sonuc(baslik, detay, gorulen_basliklar, gorulen_icerikler):
    baslik_kelimeleri = tuple(KELIME_DESENI.findall(_arama_norm(baslik)))
    baslik_anahtari = " ".join(baslik_kelimeleri)
    icerik_anahtari = " ".join(KELIME_DESENI.findall(_arama_norm(detay[:350])))
    if baslik_anahtari in gorulen_basliklar or (icerik_anahtari and icerik_anahtari in gorulen_icerikler):
        return True

    yeni_kume = set(baslik_kelimeleri)
    if len(yeni_kume) >= 4:
        for eski in gorulen_basliklar:
            eski_kume = set(eski.split())
            birlesim = yeni_kume | eski_kume
            if birlesim and len(yeni_kume & eski_kume) / len(birlesim) >= 0.92:
                return True
    return False


def esnek_arama(conn, sorgu_metni, limit=5, on_ek_eslesmesi=True):
    """Önce AND, sonuç yoksa OR sorgusu çalıştırıp temiz ve kaliteli sonuçlar döndürür."""
    terimler = arama_terimlerini_ayikla(sorgu_metni)
    if not terimler or conn is None:
        return []
    try:
        limit = max(1, min(int(limit), 100))
    except (TypeError, ValueError):
        limit = 5

    aday_limiti = min(max(limit * 5, 80), 240)
    sql = """
        SELECT
            baslik,
            metin,
            bm25(makaleler, 0.0, 5.0, 1.0) AS fts_puani,
            snippet(makaleler, 2, '', '', ' … ', 64) AS ozet_ham
        FROM makaleler
        WHERE makaleler MATCH ?
        ORDER BY fts_puani
        LIMIT ?
    """

    for asama, operator in (("tam", "AND"), ("esnek", "OR")):
        try:
            cursor = conn.cursor()
            cursor.execute(
                sql,
                (_fts_ifadesi(terimler, operator, on_ek_eslesmesi), aday_limiti),
            )
            satirlar = cursor.fetchall()
        except (sqlite3.Error, TypeError, ValueError):
            return []

        if not satirlar:
            continue

        adaylar = []
        for sira, (baslik, ham_metin, fts_puani, ozet_ham) in enumerate(satirlar):
            try:
                temiz_on_metin = wiki_metni_sadelestir(ham_metin[:32000])
                baslik = baslik or "Başlıksız ansiklopedi maddesi"
                kalite = _aday_puani(
                    ham_metin,
                    temiz_on_metin,
                    baslik,
                    terimler,
                    fts_puani,
                    sira,
                    tum_terimler_eslesiyor=(asama == "tam"),
                    on_ek_eslesmesi=on_ek_eslesmesi,
                )
                if kalite is None:
                    continue
                adaylar.append((kalite, fts_puani, baslik, temiz_on_metin, ozet_ham))
            except (TypeError, ValueError, re.error):
                continue

        if not adaylar:
            continue

        adaylar.sort(key=lambda oge: (oge[0], -float(oge[1] or 0.0)), reverse=True)
        sonuclar = []
        gorulen_basliklar = set()
        gorulen_icerikler = set()
        for _, _, baslik, temiz_metin, ozet_ham in adaylar:
            try:
                ozet_kaynagi = wiki_metni_sadelestir(ozet_ham)
            except (TypeError, ValueError, re.error):
                continue
            if len(KELIME_DESENI.findall(ozet_kaynagi)) < 12:
                ozet_kaynagi = temiz_metin
            detay = metni_guvenli_kisalt(temiz_metin, 1500)
            if _ayni_veya_yakin_sonuc(baslik, detay, gorulen_basliklar, gorulen_icerikler):
                continue
            baslik_anahtari = " ".join(KELIME_DESENI.findall(_arama_norm(baslik)))
            icerik_anahtari = " ".join(KELIME_DESENI.findall(_arama_norm(detay[:350])))
            gorulen_basliklar.add(baslik_anahtari)
            if icerik_anahtari:
                gorulen_icerikler.add(icerik_anahtari)

            sonuclar.append(
                {
                    "baslik": baslik,
                    "ozet": icerik_ozeti_olustur(
                        ozet_kaynagi,
                        terimler,
                        50,
                        on_ek_eslesmesi=on_ek_eslesmesi,
                    ),
                    "detay": detay,
                    "eslesme_durumu": (
                        "Aradığınız anlamlı kelimelerin tamamı bu maddede bulundu."
                        if asama == "tam"
                        else "Aradığınız kelimelerden en yakın eşleşenler bu maddede bulundu."
                    ),
                }
            )
            if len(sonuclar) >= limit:
                break
        if sonuclar:
            return sonuclar
    return []


def _batch_ekle(conn, batch):
    """Bir partiyi ekler; tek bozuk kayıt varsa sağlam kayıtları yine de korur."""
    if not batch:
        return 0, 0
    hazir_batch = []
    atlanan = 0
    for kayit in batch:
        try:
            if len(kayit) == 2:
                satir_id, metin = kayit
                baslik = baslik_uydur(metin)
            elif len(kayit) == 3:
                satir_id, baslik, metin = kayit
            else:
                raise ValueError
            hazir_batch.append((satir_id, baslik, metin))
        except (TypeError, ValueError, re.error):
            atlanan += 1

    if not hazir_batch:
        return 0, atlanan

    try:
        conn.executemany(
            "INSERT INTO makaleler(satir_id, baslik, metin) VALUES (?, ?, ?)",
            hazir_batch,
        )
        conn.commit()
        return len(hazir_batch), atlanan
    except sqlite3.Error:
        conn.rollback()

    eklenen = 0
    for kayit in hazir_batch:
        try:
            conn.execute(
                "INSERT INTO makaleler(satir_id, baslik, metin) VALUES (?, ?, ?)",
                kayit,
            )
            conn.commit()
            eklenen += 1
        except sqlite3.Error:
            conn.rollback()
            atlanan += 1
    return eklenen, atlanan


def _makaleler_tablosunu_hazirla(conn):
    """FTS5 tablosunu güncel başlık sütunuyla hazırlar; eski şemayı bildirir."""
    olustur = """
        CREATE VIRTUAL TABLE IF NOT EXISTS makaleler USING fts5(
            satir_id UNINDEXED,
            baslik,
            metin,
            tokenize='unicode61 remove_diacritics 0'
        )
    """
    conn.execute(olustur)
    sutunlar = [satir[1] for satir in conn.execute("PRAGMA table_info(makaleler)")]
    if sutunlar == ["satir_id", "baslik", "metin"]:
        return False

    conn.execute("DROP TABLE makaleler")
    conn.execute(olustur)
    return True


def veritabani_kur(
    txt_dosyasi="wiki_temiz.txt",
    db_dosyasi="wiki_fts.db",
    max_satir=100000,
    batch_size=5000,
    yeniden_olustur=False,
):
    """UTF-8 Wikipedia dökümünü kayıp ve parti sınırı hatası olmadan FTS5'e indeksler."""
    try:
        batch_size = int(batch_size)
        if batch_size <= 0 or (max_satir is not None and int(max_satir) <= 0):
            raise ValueError
        if max_satir is not None:
            max_satir = int(max_satir)
    except (TypeError, ValueError):
        print("Kütüphane ayarları geçerli değil. Lütfen dosya ayarlarını kontrol edin.")
        return False

    if not os.path.isfile(txt_dosyasi):
        print("Wikipedia metin dosyası bulunamadı. Lütfen 'wiki_temiz.txt' dosyasını proje klasörüne ekleyin.")
        return False

    conn = None
    try:
        if yeniden_olustur and os.path.exists(db_dosyasi):
            os.remove(db_dosyasi)
        conn = sqlite3.connect(db_dosyasi)
        sema_yenilendi = _makaleler_tablosunu_hazirla(conn)
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS indeks_durumu(
                anahtar TEXT PRIMARY KEY,
                deger TEXT NOT NULL
            )
            """
        )
        conn.commit()

        mevcut_kayit = conn.execute("SELECT COUNT(*) FROM makaleler").fetchone()[0]
        durum = dict(conn.execute("SELECT anahtar, deger FROM indeks_durumu").fetchall())
        kaynak_boyutu = str(os.path.getsize(txt_dosyasi))
        istenen_limit = "TUMU" if max_satir is None else str(max_satir)
        tamamlandi = durum.get("tamamlandi") == "1"
        kaynak_ayni = durum.get("kaynak_boyutu") == kaynak_boyutu
        onceki_limit = durum.get("limit")
        sema_guncel = durum.get("sema_surumu") == SEMA_SURUMU

        yeterli_legacy_indeks = (
            mevcut_kayit > 0
            and not durum
            and max_satir is not None
            and mevcut_kayit >= max_satir
        )
        yeterli_tamamlanmis_indeks = (
            mevcut_kayit > 0
            and tamamlandi
            and kaynak_ayni
            and sema_guncel
            and not sema_yenilendi
            and (
                onceki_limit == "TUMU"
                or (max_satir is not None and mevcut_kayit >= max_satir)
                or onceki_limit == istenen_limit
            )
        )
        if not yeniden_olustur and (yeterli_legacy_indeks or yeterli_tamamlanmis_indeks):
            if yeterli_legacy_indeks:
                conn.executemany(
                    "INSERT OR REPLACE INTO indeks_durumu(anahtar, deger) VALUES (?, ?)",
                    (
                        ("tamamlandi", "1"),
                        ("kaynak_boyutu", kaynak_boyutu),
                        ("limit", str(mevcut_kayit)),
                        ("sema_surumu", SEMA_SURUMU),
                    ),
                )
                conn.commit()
            print(f"Kütüphane hazır! ({mevcut_kayit:,} makale arama için hazır)")
            return conn

        if mevcut_kayit:
            conn.execute("DELETE FROM makaleler")
        conn.executemany(
            "INSERT OR REPLACE INTO indeks_durumu(anahtar, deger) VALUES (?, ?)",
            (
                ("tamamlandi", "0"),
                ("kaynak_boyutu", kaynak_boyutu),
                ("limit", istenen_limit),
                ("sema_surumu", SEMA_SURUMU),
            ),
        )
        conn.commit()
    except (OSError, sqlite3.Error):
        if conn is not None:
            try:
                conn.close()
            except sqlite3.Error:
                pass
        print("Wikipedia kütüphanesi açılamadı. Lütfen dosya izinlerini ve boş alanı kontrol edin.")
        return False

    print("Wikipedia kütüphanesi ilk kullanım için hazırlanıyor. Lütfen bekleyin…")
    baslangic_zamani = time.time()
    batch = []
    toplam_satir = 0
    atlanan_satir = 0

    try:
        with open(txt_dosyasi, "rb") as kaynak:
            for line_idx, ham_satir in enumerate(kaynak, start=1):
                try:
                    temiz_satir = ham_satir.decode("utf-8").strip()
                except UnicodeDecodeError:
                    atlanan_satir += 1
                    continue
                if not temiz_satir:
                    continue

                batch.append((line_idx, temiz_satir))
                kalan = None if max_satir is None else max_satir - toplam_satir
                parti_hedefi = batch_size if kalan is None else min(batch_size, kalan)
                if len(batch) >= parti_hedefi:
                    eklenen, atlanan = _batch_ekle(conn, batch)
                    toplam_satir += eklenen
                    atlanan_satir += atlanan
                    batch.clear()
                    print(f"  {toplam_satir:,} makale hazırlandı…")
                    if max_satir is not None and toplam_satir >= max_satir:
                        break

        if batch and (max_satir is None or toplam_satir < max_satir):
            if max_satir is not None:
                batch = batch[: max_satir - toplam_satir]
            eklenen, atlanan = _batch_ekle(conn, batch)
            toplam_satir += eklenen
            atlanan_satir += atlanan

        conn.execute("INSERT INTO makaleler(makaleler) VALUES('optimize')")
        conn.executemany(
            "INSERT OR REPLACE INTO indeks_durumu(anahtar, deger) VALUES (?, ?)",
            (
                ("tamamlandi", "1"),
                ("kaynak_boyutu", str(os.path.getsize(txt_dosyasi))),
                ("limit", istenen_limit),
                ("sema_surumu", SEMA_SURUMU),
            ),
        )
        conn.commit()
    except (OSError, sqlite3.Error):
        try:
            conn.close()
        except sqlite3.Error:
            pass
        print("Kütüphane hazırlanırken bir dosya sorunu oluştu. Daha sonra yeniden deneyebilirsiniz.")
        return False

    gecen_sure = time.time() - baslangic_zamani
    ek_bilgi = f" ({atlanan_satir:,} okunamayan kayıt atlandı)" if atlanan_satir else ""
    print(f"Kütüphane kurulumu tamamlandı! {toplam_satir:,} makale {gecen_sure:.2f} saniyede hazırlandı{ek_bilgi}.")
    return conn


def _sonuc_sayfasini_goster(sorgu_metni, sonuclar, sayfa, sayfa_boyutu=10):
    """Sonuçların yalnızca istenen sayfasını gösterir ve geçerli sayfayı döndürür."""
    toplam_sayfa = max(1, (len(sonuclar) + sayfa_boyutu - 1) // sayfa_boyutu)
    sayfa = max(0, min(sayfa, toplam_sayfa - 1))
    baslangic = sayfa * sayfa_boyutu
    bitis = min(baslangic + sayfa_boyutu, len(sonuclar))

    print("\n" + "=" * 70)
    print(f"“{sorgu_metni}” İÇİN EN ALAKALI {len(sonuclar)} SONUÇ")
    print(f"Sayfa {sayfa + 1}/{toplam_sayfa}")
    print("=" * 70)
    for idx in range(baslangic, bitis):
        print(f" {idx + 1:2d}. {sonuclar[idx]['baslik']}")
    print("-" * 70)
    return sayfa


def interaktif_arama():
    """Numaralı sonuç listesi ve ayrıntı görünümü sunan kullanıcı arayüzü."""
    txt_yolu = os.path.join(PROJE_DIZINI, "wiki_temiz.txt")
    db_yolu = os.path.join(PROJE_DIZINI, "wiki_fts.db")
    conn = None

    try:
        print("Wikipedia Kütüphanesi Yükleniyor…")
        conn = veritabani_kur(txt_yolu, db_yolu, max_satir=100000, batch_size=5000)
        if not conn:
            return

        print("\n" + "=" * 70)
        print("                  WİKİPEDİA AKILLI ARAMA ASİSTANI")
        print("=" * 70)
        print("Aramak istediğiniz konuyu yazın. Çıkış için 'q' kullanabilirsiniz.")
        print("=" * 70)

        while True:
            try:
                kullanici_girisi = input("\nArama Kutusu > ").strip()
            except (KeyboardInterrupt, EOFError):
                print("\nİyi günler dileriz!")
                return

            if kullanici_girisi.lower() in {"q", "çıkış", "exit", "quit"}:
                print("İyi günler dileriz!")
                return

            tum_kelimeler = KELIME_DESENI.findall(kullanici_girisi)
            if not tum_kelimeler:
                print("Lütfen harf veya rakam içeren bir arama yazın.")
                continue
            if not arama_terimlerini_ayikla(kullanici_girisi):
                print("Aramanız yalnızca çok genel kelimelerden oluşuyor. Lütfen konuyu belirten bir kelime ekleyin.")
                continue

            sonuclar = esnek_arama(conn, kullanici_girisi, limit=30)
            if not sonuclar:
                print(f"\n'{kullanici_girisi}' için bir içerik bulunamadı.")
                print("Yazımı kontrol edip farklı kelimelerle yeniden deneyebilirsiniz.")
                continue

            sayfa = _sonuc_sayfasini_goster(kullanici_girisi, sonuclar, 0)
            toplam_sayfa = (len(sonuclar) + 9) // 10

            while True:
                try:
                    secim = input(
                        "\nSonuç numarası; sonraki sayfa için 'n', önceki sayfa için 'p', "
                        "yeni arama için 'y', çıkış için 'q': "
                    ).strip().lower()
                except (KeyboardInterrupt, EOFError):
                    print("\nİyi günler dileriz!")
                    return

                if secim in {"y", "yeni"}:
                    break
                if secim in {"q", "çıkış", "exit", "quit"}:
                    print("İyi günler dileriz!")
                    return
                if secim in {"n", "sonraki"}:
                    if sayfa + 1 >= toplam_sayfa:
                        print("Zaten son sonuç sayfasındasınız.")
                    else:
                        sayfa = _sonuc_sayfasini_goster(
                            kullanici_girisi,
                            sonuclar,
                            sayfa + 1,
                        )
                    continue
                if secim in {"p", "önceki"}:
                    if sayfa == 0:
                        print("Zaten ilk sonuç sayfasındasınız.")
                    else:
                        sayfa = _sonuc_sayfasini_goster(
                            kullanici_girisi,
                            sonuclar,
                            sayfa - 1,
                        )
                    continue
                if not secim.isdigit():
                    print("Lütfen bir sonuç numarası ya da 'n', 'p', 'y', 'q' seçeneklerinden birini yazın.")
                    continue

                numara = int(secim)
                if not 1 <= numara <= len(sonuclar):
                    print(f"Lütfen 1 ile {len(sonuclar)} arasında bir numara girin.")
                    continue

                secilen = sonuclar[numara - 1]
                print("\n" + "=" * 70)
                print(f"{numara}. SONUÇ")
                print("=" * 70)
                print(f"Konu Başlığı   : {secilen['baslik']}")
                print(f"Eşleşme Durumu : {secilen['eslesme_durumu']}")
                print(f"İçerik Özeti   : {secilen['ozet']}")
                print("-" * 70)
                print("Makaleden Geniş Metin:")
                print(secilen["detay"])
                print("=" * 70)
    finally:
        if conn is not None:
            try:
                conn.close()
            except sqlite3.Error:
                pass

