#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""SQLite FTS5 tabanlı, çevrimdışı Türkçe Wikipedia arama motoru."""

import html
import os
import re
import sqlite3
import shutil
import subprocess
import time


PROJE_DIZINI = os.path.dirname(os.path.abspath(__file__))
VURGU_AC = "\ue000"
VURGU_KAPAT = "\ue001"

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
    return (metin or "").casefold().replace("i\u0307", "i")


def arama_terimlerini_ayikla(sorgu_metni):
    """FTS sorgusuna girecek anlamlı, benzersiz terimleri döndürür."""
    if not isinstance(sorgu_metni, str):
        return []

    terimler = re.findall(r"\w+", sorgu_metni.strip(), flags=re.UNICODE)
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
    temiz = re.sub(r"^(?:--\s*>|}})\s*", "", temiz)

    # Bazı satırlar açılış '{{' olmadan onlarca '| alan = değer' ile başlıyor.
    for _ in range(4):
        kapanis = temiz.find("}}")
        if kapanis < 0 or kapanis > 12000:
            break
        on_ek = temiz[:kapanis]
        alan_sayisi = len(
            re.findall(
                r"(?:^|\|)\s*[\wçğıöşüÇĞİÖŞÜ -]{1,45}\s*=",
                on_ek,
                flags=re.UNICODE,
            )
        )
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

    tablo_isaretli = bool(
        re.search(r"(?:\{\||\|}|\|\s*-|!!|\b(?:rowspan|colspan|width)\s*=)", metin, re.IGNORECASE)
    )
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
    temiz = re.sub(r"<!--.*?-->", " ", temiz, flags=re.DOTALL)
    temiz = _baslangictaki_bilgi_kutusunu_sil(temiz)
    temiz = re.sub(
        r"^([^,.|{}]{2,100}),{1,2}[^{}]{0,250}}}\s*",
        r"\1 ",
        temiz,
    )

    temiz = re.sub(
        r"<div\b[^>]*class=[\"'][^\"']*thumb[^\"']*[\"'][^>]*>.*?"
        r"</div>\s*</div>\s*</div>",
        " ",
        temiz,
        flags=re.IGNORECASE | re.DOTALL,
    )

    # İçerikleri kullanıcıya değer katmayan bloklar.
    temiz = re.sub(r"<ref\b[^>]*>.*?</ref\s*>", " ", temiz, flags=re.IGNORECASE | re.DOTALL)
    temiz = re.sub(r"<ref\b[^>]*/\s*>", " ", temiz, flags=re.IGNORECASE)
    temiz = re.sub(r"</?ref\b[^>]*>", " ", temiz, flags=re.IGNORECASE)
    temiz = re.sub(
        r"<(?:math|gallery|timeline|imagemap|score)\b[^>]*>.*?</(?:math|gallery|timeline|imagemap|score)\s*>",
        " ",
        temiz,
        flags=re.IGNORECASE | re.DOTALL,
    )
    temiz = re.sub(r"<br\s*/?>", ". ", temiz, flags=re.IGNORECASE)
    temiz = re.sub(r"<[^>]+>", " ", temiz)
    temiz = re.sub(r"<[A-Za-z/][^>]*$", " ", temiz)

    # Dosya/resim bağlantılarını, bağlantı normalleştirmesinden önce bütünüyle at.
    temiz = re.sub(
        r"\[\[(?:Dosya|File|Image):.*?\]\]",
        " ",
        temiz,
        flags=re.IGNORECASE | re.DOTALL,
    )
    temiz = re.sub(
        r"(?:küçükresim|thumbnail|thumb)(?:\|[^\[\]\n]{0,200})?\[\[[^\[\]]{0,500}\]\]",
        " ",
        temiz,
        flags=re.IGNORECASE | re.DOTALL,
    )
    temiz = re.sub(
        r"(?:küçükresim|thumbnail|thumb)(?:\|[\wçğıöşüÇĞİÖŞÜ .='-]{0,50})*\|?\s*"
        r"[^.!?]{0,220}?\b(?:görünümü|görüntüsü|fotoğrafı|resmi|portresi|haritası|şeması|logosu|konumu|tablosu)\b\s*",
        " ",
        temiz,
        flags=re.IGNORECASE,
    )
    temiz = re.sub(
        r"\[\[(?:Kategori|Category):.*?\]\]",
        " ",
        temiz,
        flags=re.IGNORECASE | re.DOTALL,
    )

    # Kapanış ayraçları dururken yetim '| alan = değer' parçalarını temizle;
    # aksi halde alan değeri yanlışlıkla makale girişine kadar uzayabilir.
    temiz = re.sub(
        r"\|\s*[\wçğıöşüÇĞİÖŞÜ -]{1,45}\s*=\s*[^|{}]*",
        " ",
        temiz,
    )

    temiz = _dengeli_bloklari_sil(temiz, "{{", "}}")
    temiz = _dengeli_bloklari_sil(temiz, "{|", "|}")

    # İç içe bağlantıları içeriden dışarıya doğru düzleştir.
    baglanti = re.compile(r"\[\[([^\[\]]+)\]\]")
    for _ in range(8):
        if not baglanti.search(temiz):
            break

        def baglanti_metni(eslesme):
            icerik = eslesme.group(1).strip()
            if re.match(r"^(?:Kategori|Category|Dosya|File|Image):", icerik, re.IGNORECASE):
                return " "
            return icerik.rsplit("|", 1)[-1].strip()

        temiz = baglanti.sub(baglanti_metni, temiz)

    temiz = re.sub(r"\[(?:https?|ftp)://[^\s\]]+\s+([^\]]+)\]", r"\1", temiz, flags=re.IGNORECASE)
    temiz = re.sub(r"\[(?:https?|ftp)://[^\]]+\]", " ", temiz, flags=re.IGNORECASE)
    temiz = re.sub(r"\b(?:https?|ftp)://\S+", " ", temiz, flags=re.IGNORECASE)
    temiz = re.sub(r"\bwww\.\S+", " ", temiz, flags=re.IGNORECASE)
    temiz = re.sub(
        r"Bu sayfa,?\s+Türkçe Vikipedi(?:'den|den) kopyalandığı tarihten sonraki değişimleri göstermez\.?",
        " ",
        temiz,
        flags=re.IGNORECASE,
    )

    # Dökümün sonundaki kategori dizilerini ve kalan dosya belirteçlerini kaldır.
    temiz = re.sub(r"\b(?:Kategori|Category)\s*:.*$", " ", temiz, flags=re.IGNORECASE)
    temiz = re.sub(r"\b(?:Dosya|File|Image)\s*:\s*\S+", " ", temiz, flags=re.IGNORECASE)
    temiz = re.sub(r"__(?:NOTOC|TOC|FORCETOC|NOINDEX|INDEX)__", " ", temiz, flags=re.IGNORECASE)

    # Başlık, tablo, liste, resim ve güzergâh şablonlarından kalan işaretler.
    temiz = re.sub(r"={2,}\s*([^=]+?)\s*={2,}", r". \1. ", temiz)
    temiz = re.sub(r"'{2,5}", "", temiz)
    temiz = re.sub(r"\\+[A-Za-z][\w-]*", " ", temiz)
    temiz = re.sub(r"(?<!\w)alt\s*=\s*(?=\||\s|$)", " ", temiz, flags=re.IGNORECASE)
    temiz = re.sub(
        r"(?<!\w)(?:küçükresim|thumbnail|thumb|upright(?:\s*=\s*[\d.]+)?|sağ|sol|left|right)(?!\w)\s*\|?",
        " ",
        temiz,
        flags=re.IGNORECASE,
    )
    temiz = re.sub(r"(?<!\w)\d+\s*px(?!\w)", " ", temiz, flags=re.IGNORECASE)
    temiz = re.sub(r"(?<!\w)\d+\s*x\s*\d+\s*(?:px|pik)(?!\w)", " ", temiz, flags=re.IGNORECASE)
    temiz = re.sub(
        r"\b(?:width|height|rowspan|colspan|align|class|style)\s*=\s*(?:[\"'][^\"']*[\"']|[^\s|!]+)",
        " ",
        temiz,
        flags=re.IGNORECASE,
    )
    temiz = re.sub(r"(?:^|\s)[*#;]+\s*", " ", temiz)
    temiz = re.sub(r"\s:{1,3}\s", ". ", temiz)
    temiz = re.sub(r"\{+|}+|\[\[|\]\]|\{\||\|}", " ", temiz)
    temiz = temiz.replace("[", " ").replace("]", " ")
    temiz = re.sub(r"\|+|~~+", " ", temiz)
    if tablo_isaretli:
        temiz = temiz.replace("!", " ")
    temiz = temiz.replace("↑", " ")
    temiz = re.sub(r"(?:--\s*>|-->)+", " ", temiz)
    temiz = re.sub(r"\s+([,.;:!?])", r"\1", temiz)
    temiz = re.sub(r"([,;:])(?:\s*\1)+", r"\1", temiz)
    temiz = re.sub(r",\s*\.", ",", temiz)
    temiz = re.sub(r"\.{3,}", "…", temiz)
    temiz = re.sub(r"\s+", " ", temiz).strip(" \t\r\n|,;:-")
    temiz = re.sub(r"^(\w{2,})\s+\1\b", r"\1", temiz, flags=re.IGNORECASE | re.UNICODE)
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
    aday = re.sub(r"^[\W_]+", "", aday, flags=re.UNICODE).strip()
    aday = re.sub(r"^\d{3,4}\s+(?=[A-ZÇĞİÖŞÜ])", "", aday)
    aday = re.sub(r"^(?:harita|resim|şekil)\s*bağı\s*[-–—]?\s*", "", aday, flags=re.IGNORECASE)
    aday = re.split(
        r"\s+(?:ya da|veya)\s+(?:tarih[iî]\s+)?(?:adı|ismi)(?:yla|yle)?\b",
        aday,
        maxsplit=1,
        flags=re.IGNORECASE,
    )[0]
    aday = re.split(r"\s+(?:ya da|veya)\s+", aday, maxsplit=1, flags=re.IGNORECASE)[0]
    aday = re.sub(r"\s+", " ", aday).strip(" ,;:-–—()[]")
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
    if re.match(r"^(?:bir\b|adıyla\b|adlı\b|olarak\b|türüdür\b|dalıdır\b|kişidir\b)", normal):
        return True
    return bool(re.search(r"\b\w+(?:dır|dir|dur|dür|tır|tir|tur|tür)\b[^.!?]{0,20}[.!?]?$", normal))


def _zayif_baslik_baslangici(cumle):
    normal = _arama_norm(cumle).lstrip()
    return bool(
        re.match(
            r"^(?:bu|buna|bunun|burada|böylece|ancak|daha sonra|sonrasında|ilki|"
            r"ilkbahar|yaz|sonbahar|kış|\d{3,4}\s*[-–—])\b",
            normal,
        )
    )


def _temiz_metinden_baslik(temiz):
    """Önceden temizlenmiş giriş cümlelerinden güvenli bir başlık çıkarır."""
    if not temiz:
        return "Başlıksız ansiklopedi maddesi"

    cumleler = [c.strip() for c in re.split(r"(?<=[.!?])\s+", temiz) if c.strip()]
    adaylar = []
    for sira, cumle in enumerate(cumleler[:8]):
        if len(cumle) < 3 or _altyazi_veya_junk_cumle(cumle):
            continue

        eslesme = re.match(r"^(.{2,110}?)(?:\s*\([^)]{0,120}\))*\s*,\s+(.+)$", cumle)
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

        parantez = re.match(r"^([A-ZÇĞİÖŞÜ0-9][\wçğıöşüÇĞİÖŞÜ .'-]{1,80}?)\s*\(", cumle)
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
    for eslesme in re.finditer(r"[.!?…](?=\s|$)", parca):
        if eslesme.end() > en_fazla_karakter:
            continue
        if eslesme.end() < int(en_fazla_karakter * 0.55):
            continue
        oncesi = parca[max(0, eslesme.start() - 12) : eslesme.end()]
        if eslesme.group(0) == "." and re.search(
            r"\b(?:d|ö|bkz|vb|vs|dr|prof|doç|sn)\.$",
            oncesi,
            flags=re.IGNORECASE,
        ):
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


def icerik_ozeti_olustur(temiz_metin, terimler, en_fazla_kelime=50):
    """İlk ilgili bölgeden, dengeli vurgular içeren yaklaşık 50 kelimelik özet üretir."""
    if not temiz_metin:
        return ""
    kelime_eslesmeleri = list(re.finditer(r"\w+(?:['’]\w+)*", temiz_metin, flags=re.UNICODE))
    if not kelime_eslesmeleri:
        return metni_guvenli_kisalt(temiz_metin, 250)

    arananlar = {_arama_norm(terim) for terim in terimler}
    ilgili_sira = next(
        (
            sira
            for sira, eslesme in enumerate(kelime_eslesmeleri)
            if _arama_norm(eslesme.group(0)) in arananlar
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
        desen = re.compile(
            r"(?<!\w)(" + "|".join(sorted((re.escape(t) for t in terimler), key=len, reverse=True)) + r")(?!\w)",
            flags=re.IGNORECASE | re.UNICODE,
        )
        ozet = desen.sub(lambda e: "[" + e.group(0) + "]", ozet)

    if baslangic > 0:
        ozet = "… " + ozet
    if bitis < len(temiz_metin):
        ozet += " …"
    return ozet


def _fts_ifadesi(terimler, operator):
    guvenli = ['"' + terim.replace('"', '""') + '"' for terim in terimler]
    return (" " + operator + " ").join(guvenli)


def _aday_puani(
    ham_metin,
    temiz_metin,
    baslik,
    terimler,
    fts_puani,
    sira,
    tum_terimler_eslesiyor=False,
):
    kelimeler = re.findall(r"\w+", temiz_metin, flags=re.UNICODE)
    if len(temiz_metin) < 120 or len(kelimeler) < 20:
        return None
    if re.match(r"^\s*(?:küçükresim|thumbnail|thumb)\b", ham_metin, re.IGNORECASE) and len(kelimeler) < 45:
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
        normal_ham = _arama_norm(ham_metin)
        eslesen = sum(
            1
            for terim in normal_terimler
            if re.search(r"(?<!\w)" + re.escape(terim) + r"(?!\w)", normal_ham)
        )
    baslikta = sum(1 for terim in normal_terimler if re.search(r"(?<!\w)" + re.escape(terim) + r"(?!\w)", normal_baslik))

    puan = (eslesen * 5.0) + (baslikta * 7.0) + min(len(kelimeler) / 120.0, 3.0)
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
    baslik_kelimeleri = tuple(re.findall(r"\w+", _arama_norm(baslik), flags=re.UNICODE))
    baslik_anahtari = " ".join(baslik_kelimeleri)
    icerik_anahtari = " ".join(re.findall(r"\w+", _arama_norm(detay[:350]), flags=re.UNICODE))
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


def esnek_arama(conn, sorgu_metni, limit=5):
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
            metin,
            bm25(makaleler, 0.0, 1.0) AS fts_puani,
            snippet(makaleler, 1, '', '', ' … ', 64) AS ozet_ham
        FROM makaleler
        WHERE makaleler MATCH ?
        ORDER BY fts_puani
        LIMIT ?
    """

    for asama, operator in (("tam", "AND"), ("esnek", "OR")):
        try:
            cursor = conn.cursor()
            cursor.execute(sql, (_fts_ifadesi(terimler, operator), aday_limiti))
            satirlar = cursor.fetchall()
        except (sqlite3.Error, TypeError, ValueError):
            return []

        if not satirlar:
            continue

        adaylar = []
        for sira, (ham_metin, fts_puani, ozet_ham) in enumerate(satirlar):
            try:
                temiz_on_metin = wiki_metni_sadelestir(ham_metin[:32000])
                baslik = _temiz_metinden_baslik(temiz_on_metin)
                kalite = _aday_puani(
                    ham_metin,
                    temiz_on_metin,
                    baslik,
                    terimler,
                    fts_puani,
                    sira,
                    tum_terimler_eslesiyor=(asama == "tam"),
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
            if len(re.findall(r"\w+", ozet_kaynagi, flags=re.UNICODE)) < 12:
                ozet_kaynagi = temiz_metin
            detay = metni_guvenli_kisalt(temiz_metin, 1500)
            if _ayni_veya_yakin_sonuc(baslik, detay, gorulen_basliklar, gorulen_icerikler):
                continue
            baslik_anahtari = " ".join(re.findall(r"\w+", _arama_norm(baslik), flags=re.UNICODE))
            icerik_anahtari = " ".join(re.findall(r"\w+", _arama_norm(detay[:350]), flags=re.UNICODE))
            gorulen_basliklar.add(baslik_anahtari)
            if icerik_anahtari:
                gorulen_icerikler.add(icerik_anahtari)

            sonuclar.append(
                {
                    "baslik": baslik,
                    "ozet": icerik_ozeti_olustur(ozet_kaynagi, terimler, 50),
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
    try:
        conn.executemany("INSERT INTO makaleler(satir_id, metin) VALUES (?, ?)", batch)
        conn.commit()
        return len(batch), 0
    except sqlite3.Error:
        conn.rollback()

    eklenen = 0
    atlanan = 0
    for kayit in batch:
        try:
            conn.execute("INSERT INTO makaleler(satir_id, metin) VALUES (?, ?)", kayit)
            conn.commit()
            eklenen += 1
        except sqlite3.Error:
            conn.rollback()
            atlanan += 1
    return eklenen, atlanan


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
        conn.execute(
            """
            CREATE VIRTUAL TABLE IF NOT EXISTS makaleler USING fts5(
                satir_id UNINDEXED,
                metin,
                tokenize='unicode61 remove_diacritics 0'
            )
            """
        )
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
                    (("tamamlandi", "1"), ("kaynak_boyutu", kaynak_boyutu), ("limit", str(mevcut_kayit))),
                )
                conn.commit()
            print(f"Kütüphane hazır! ({mevcut_kayit:,} makale arama için hazır)")
            return conn

        if mevcut_kayit:
            conn.execute("DELETE FROM makaleler")
        conn.executemany(
            "INSERT OR REPLACE INTO indeks_durumu(anahtar, deger) VALUES (?, ?)",
            (("tamamlandi", "0"), ("kaynak_boyutu", kaynak_boyutu), ("limit", istenen_limit)),
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

        conn.executemany(
            "INSERT OR REPLACE INTO indeks_durumu(anahtar, deger) VALUES (?, ?)",
            (("tamamlandi", "1"), ("kaynak_boyutu", str(os.path.getsize(txt_dosyasi))), ("limit", istenen_limit)),
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


def otomatik_git_yedekle():
    """Kod değişikliklerini sessizce commit eder ve origin/main'e arka planda gönderir."""
    ortak = {
        "cwd": PROJE_DIZINI,
        "capture_output": True,
        "text": True,
        "encoding": "utf-8",
        "errors": "replace",
        "timeout": 8,
        "check": False,
    }
    try:
        durum = subprocess.run(["git", "status", "--porcelain"], **ortak)
        if durum.returncode != 0 or not durum.stdout.strip():
            return
        ekle = subprocess.run(["git", "add", "."], **ortak)
        if ekle.returncode != 0:
            return
        tarih_saat = time.strftime("%Y-%m-%d %H:%M:%S")
        kaydet = subprocess.run(
            ["git", "commit", "-m", f"Otomatik guncelleme: {tarih_saat}"],
            **ortak,
        )
        if kaydet.returncode != 0:
            return
        subprocess.Popen(
            ["git", "push", "origin", "main"],
            cwd=PROJE_DIZINI,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except (OSError, subprocess.SubprocessError, ValueError):
        return


def interaktif_arama():
    """Numaralı sonuç listesi ve ayrıntı görünümü sunan kullanıcı arayüzü."""
    txt_yolu = os.path.join(PROJE_DIZINI, "wiki_temiz.txt")
    db_yolu = os.path.join(PROJE_DIZINI, "wiki_fts.db")
    conn = None
    otomatik_git_yedekle()

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

            tum_kelimeler = re.findall(r"\w+", kullanici_girisi, flags=re.UNICODE)
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

            print("\n" + "=" * 70)
            print(f"“{kullanici_girisi}” İÇİN EN ALAKALI {len(sonuclar)} SONUÇ")
            print("=" * 70)
            for idx, sonuc in enumerate(sonuclar, start=1):
                print(f" {idx:2d}. {sonuc['baslik']}")
            print("-" * 70)

            while True:
                try:
                    secim = input(
                        "\nAyrıntı için sonuç numarası, yeni arama için 'y', çıkış için 'q': "
                    ).strip().lower()
                except (KeyboardInterrupt, EOFError):
                    print("\nİyi günler dileriz!")
                    return

                if secim in {"y", "yeni"}:
                    break
                if secim in {"q", "çıkış", "exit", "quit"}:
                    print("İyi günler dileriz!")
                    return
                if not secim.isdigit():
                    print("Lütfen bir sonuç numarası, 'y' veya 'q' yazın.")
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
        otomatik_git_yedekle()


def _git_komutunu_bul():
    """Windows dahil tum ortamlarda git calistirabilir yolunu dondurur."""
    git_komutu = shutil.which("git")
    if git_komutu:
        return git_komutu

    adaylar = [
        os.path.join(os.environ.get("ProgramFiles", ""), "Git", "cmd", "git.exe"),
        os.path.join(os.environ.get("ProgramFiles(x86)", ""), "Git", "cmd", "git.exe"),
        os.path.join(os.environ.get("LOCALAPPDATA", ""), "Programs", "Git", "cmd", "git.exe"),
    ]
    for aday in adaylar:
        if aday and os.path.isfile(aday):
            return aday
    return None


def otomatik_git_yedekle(arka_planda_yolla=True):
    """Degisiklikleri commit eder ve gerekirse arka planda origin/main'e yollar."""
    git_komutu = _git_komutunu_bul()
    if not git_komutu:
        return False

    ortak = {
        "cwd": PROJE_DIZINI,
        "capture_output": True,
        "text": True,
        "encoding": "utf-8",
        "errors": "replace",
        "timeout": 8,
        "check": False,
    }

    try:
        durum = subprocess.run([git_komutu, "status", "--porcelain"], **ortak)
        if durum.returncode != 0 or not durum.stdout.strip():
            return False

        ekle = subprocess.run([git_komutu, "add", "-A", "."], **ortak)
        if ekle.returncode != 0:
            return False

        tarih_saat = time.strftime("%Y-%m-%d %H:%M:%S")
        kaydet = subprocess.run(
            [git_komutu, "commit", "-m", f"Otomatik guncelleme: {tarih_saat}"],
            **ortak,
        )
        if kaydet.returncode != 0:
            return False

        if arka_planda_yolla:
            subprocess.Popen(
                [git_komutu, "push", "origin", "main"],
                cwd=PROJE_DIZINI,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            return True

        push_sonuc = subprocess.run(
            [git_komutu, "push", "origin", "main"],
            cwd=PROJE_DIZINI,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
            timeout=60,
        )
        return push_sonuc.returncode == 0
    except (OSError, subprocess.SubprocessError, ValueError):
        return False


if __name__ == "__main__":
    interaktif_arama()
