#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import contextlib
import io
import os
import re
import sqlite3
import tempfile
import unittest
from unittest import mock

import wiki_arama_motoru as wiki


class MetinTemizlemeTestleri(unittest.TestCase):
    def test_gercekci_infobox_ve_wikikod_temizlenir(self):
        ham = (
            "| doğum_yeri = Ankara | meslek = Yazar }} "
            "'''Örnek Kişi''' (1900-1980), Türk yazardır. "
            "{{Bilgi kutusu|gereksiz={{iç şablon}}}} "
            "[[Ankara|başkentte]] yaşadı.<ref name='x'>Kaynak</ref> "
            "[[Dosya:ornek.jpg|küçükresim|Portre]] &amp; üretkendi. "
            "Kategori:Türk yazarlar"
        )
        temiz = wiki.wiki_metni_sadelestir(ham)
        self.assertIn("Örnek Kişi", temiz)
        self.assertIn("başkentte yaşadı", temiz)
        self.assertIn("& üretkendi", temiz)
        for artik in ("{{", "}}", "[[", "]]", "<ref", "Kategori:", "Dosya:", "|"):
            self.assertNotIn(artik, temiz)

    def test_baslik_infobox_ve_takma_ad_artigindan_cikar(self):
        ham = (
            "1162 | doğum_yeri = Onon | dini = Tengricilik }} "
            "Cengiz Han,, başka bir yazımla anılır.}} "
            "(doğum adıyla Temuçin, 1162-1227), Moğol hükümdarıdır."
        )
        self.assertEqual(wiki.baslik_uydur(ham), "Cengiz Han")

    def test_ozet_kelime_sinirinda_ve_dengeli_vurguyla_biter(self):
        metin = " ".join(f"kelime{i}" for i in range(80)) + " İstanbul Boğazı son cümlededir."
        ozet = wiki.icerik_ozeti_olustur(metin, ["İstanbul", "Boğazı"], 50)
        self.assertEqual(ozet.count("["), ozet.count("]"))
        self.assertLessEqual(len(re.findall(r"\w+", ozet, flags=re.UNICODE)), 50)
        self.assertTrue(ozet.endswith(".") or ozet.endswith(" …"))

    def test_genis_metin_cumle_ve_parantez_sinirini_korur(self):
        metin = ("Bu eksiksiz bir cümledir. " * 80) + "(yarım kalan açıklama burada sürer)"
        kisaltilmis = wiki.metni_guvenli_kisalt(metin, 300)
        self.assertLessEqual(len(kisaltilmis), 300)
        self.assertTrue(kisaltilmis.endswith((".", "!", "?", "…")))
        self.assertLessEqual(kisaltilmis.count("("), kisaltilmis.count(")"))


class AramaTestleri(unittest.TestCase):
    def setUp(self):
        self.conn = sqlite3.connect(":memory:")
        self.conn.execute(
            """
            CREATE VIRTUAL TABLE makaleler USING fts5(
                satir_id UNINDEXED,
                baslik,
                metin,
                tokenize='unicode61 remove_diacritics 0'
            )
            """
        )
        satirlar = [
            (
                1,
                "İstanbul Boğazı",
                "İstanbul Boğazı ya da tarihî ismiyle Bosporus, Asya ile Avrupa'yı ayıran ve "
                "Marmara Denizi ile Karadeniz'i bağlayan uluslararası bir su yoludur. "
                "İstanbul kentinin iki yakası boyunca çok sayıda tarihî yapı bulunur.",
            ),
            (
                2,
                "Boğaz",
                "Boğaz şu anlamlara gelebilir: Boğaz organ, Çanakkale Boğazı, İstanbul Boğazı, "
                "Bering Boğazı ve başka kısa liste maddeleri burada sıralanır.",
            ),
            (3, "İstanbul Boğazı rota", "| inline = 1 | map = rota }} \\utCONTg ~~ İstanbul Boğazı"),
            (
                4,
                "Çığ",
                "Çığ, eğimli arazideki kar kütlesinin hızla aşağı kayması olayıdır. "
                "Büyük çığlar can ve mal kaybına yol açabilir ve dağlık bölgelerde görülür.",
            ),
            (
                5,
                "Ruhun ölümsüzlüğü",
                "Ruhun ölümsüzlüğü, pek çok felsefe ve inanç geleneğinde tartışılan bir düşüncedir. "
                "Konu insan yaşamı, ölüm ve varoluş üzerine farklı görüşler içerir.",
            ),
            (6, "Ölüm", "ölüm ölüm etkin plak ilişkili web önemli"),
            (
                7,
                "Kitaplar",
                "Kitaplar, bilgi ve öyküleri yazılı biçimde okurlara ulaştıran önemli kültür ürünleridir. "
                "Kütüphanelerde korunan eserler eğitim, araştırma, düşünce ve sanat yaşamına uzun yıllar katkı sağlar.",
            ),
        ]
        self.conn.executemany("INSERT INTO makaleler(satir_id, baslik, metin) VALUES (?, ?, ?)", satirlar)
        self.conn.commit()

    def tearDown(self):
        self.conn.close()

    def test_tam_baslik_liste_satirindan_once_gelir(self):
        sonuclar = wiki.esnek_arama(self.conn, "İstanbul Boğazı", 10)
        self.assertTrue(sonuclar)
        self.assertEqual(sonuclar[0]["baslik"], "İstanbul Boğazı")
        self.assertTrue(all("\\utCONT" not in sonuc["detay"] for sonuc in sonuclar))

    def test_or_aramasi_bos_metadata_satirini_filtreler(self):
        sonuclar = wiki.esnek_arama(self.conn, "çığ ölümsüzlüğü", 10)
        basliklar = [sonuc["baslik"] for sonuc in sonuclar]
        self.assertIn("Çığ", basliklar)
        self.assertTrue(any("ölümsüzlüğü" in baslik.casefold() for baslik in basliklar))
        self.assertFalse(any("etkin plak" in sonuc["detay"] for sonuc in sonuclar))
        self.assertTrue(all("en yakın eşleşenler" in sonuc["eslesme_durumu"] for sonuc in sonuclar))

    def test_bos_noktalama_durak_kelime_ve_kapali_baglanti(self):
        self.assertEqual(wiki.esnek_arama(self.conn, "!!!", 5), [])
        self.assertEqual(wiki.esnek_arama(self.conn, "ve ile bir", 5), [])
        self.conn.close()
        self.assertEqual(wiki.esnek_arama(self.conn, "İstanbul", 5), [])
        self.conn = sqlite3.connect(":memory:")

    def test_saklanan_baslik_dogrudan_okunur(self):
        with mock.patch.object(
            wiki,
            "_temiz_metinden_baslik",
            side_effect=AssertionError("Arama sırasında başlık yeniden çıkarılmamalı"),
        ):
            sonuclar = wiki.esnek_arama(self.conn, "İstanbul Boğazı", 5)
        self.assertEqual(sonuclar[0]["baslik"], "İstanbul Boğazı")

    def test_fts5_ozel_isaretleri_guvenle_islenir(self):
        sonuclar = wiki.esnek_arama(self.conn, '\"İstanbul\" AND OR NOT *', 5)
        self.assertTrue(sonuclar)
        self.assertEqual(sonuclar[0]["baslik"], "İstanbul Boğazı")
        self.assertEqual(wiki.esnek_arama(self.conn, 'AND OR NOT * \"\"', 5), [])

    def test_turkce_on_ek_eslesmesi_cekime_girmis_sozcugu_bulur(self):
        sonuclar = wiki.esnek_arama(self.conn, "kitap", 5)
        self.assertTrue(sonuclar)
        self.assertEqual(sonuclar[0]["baslik"], "Kitaplar")
        self.assertIn("[Kitaplar]", sonuclar[0]["ozet"])

    def test_turkce_buyuk_kucuk_harf_normalizasyonu(self):
        self.assertEqual(wiki._arama_norm("IĞDIR"), wiki._arama_norm("ığdır"))
        self.assertEqual(wiki._arama_norm("İSTANBUL"), wiki._arama_norm("istanbul"))


class IndeksVeArayuzTestleri(unittest.TestCase):
    def test_batch_sinirlari_ve_bozuk_utf8(self):
        with tempfile.TemporaryDirectory() as gecici:
            txt = os.path.join(gecici, "ornek.txt")
            db = os.path.join(gecici, "ornek.db")
            with open(txt, "wb") as dosya:
                dosya.write("Birinci geçerli makale.\n".encode("utf-8"))
                dosya.write("İkinci geçerli makale.\n".encode("utf-8"))
                dosya.write(b"bozuk-utf8-\xff\n")
                dosya.write("Üçüncü geçerli makale.\n".encode("utf-8"))
                dosya.write("Dördüncü geçerli makale.\n".encode("utf-8"))
                dosya.write("Beşinci geçerli makale.\n".encode("utf-8"))

            with contextlib.redirect_stdout(io.StringIO()):
                conn = wiki.veritabani_kur(txt, db, max_satir=None, batch_size=2, yeniden_olustur=True)
            try:
                self.assertIsInstance(conn, sqlite3.Connection)
                self.assertEqual(conn.execute("SELECT COUNT(*) FROM makaleler").fetchone()[0], 5)
                self.assertEqual(
                    [satir[0] for satir in conn.execute("SELECT satir_id FROM makaleler ORDER BY rowid")],
                    [1, 2, 4, 5, 6],
                )
                self.assertEqual(
                    [satir[1] for satir in conn.execute("PRAGMA table_info(makaleler)")],
                    ["satir_id", "baslik", "metin"],
                )
                self.assertEqual(
                    conn.execute("SELECT baslik FROM makaleler WHERE satir_id = 1").fetchone()[0],
                    "Birinci geçerli makale",
                )
                durum = dict(conn.execute("SELECT anahtar, deger FROM indeks_durumu"))
                self.assertEqual(durum["tamamlandi"], "1")
                self.assertEqual(durum["sema_surumu"], wiki.SEMA_SURUMU)
            finally:
                if isinstance(conn, sqlite3.Connection):
                    conn.close()

    def test_git_hatasi_kullaniciya_yansimaz(self):
        with mock.patch.object(wiki.subprocess, "run", side_effect=OSError("git yok")):
            wiki.otomatik_git_yedekle()

    def test_git_index_kilidi_varken_sessizce_bekler(self):
        with tempfile.TemporaryDirectory() as gecici:
            git_dizini = os.path.join(gecici, ".git")
            os.mkdir(git_dizini)
            with open(os.path.join(git_dizini, "index.lock"), "w", encoding="utf-8"):
                pass
            with (
                mock.patch.object(wiki, "PROJE_DIZINI", gecici),
                mock.patch.object(wiki.subprocess, "run") as calistir,
            ):
                self.assertFalse(wiki.otomatik_git_yedekle())
            calistir.assert_not_called()

    def test_git_islem_sirasinda_olusan_kilidi_yoksayar(self):
        sonuclar = [
            mock.Mock(returncode=0),
            mock.Mock(returncode=0, stdout=" wiki_arama_motoru.py\n", stderr=""),
            mock.Mock(returncode=128, stdout="", stderr="fatal: .git/index.lock already exists"),
        ]
        with (
            mock.patch.object(wiki, "_git_indeks_kilitli_mi", return_value=False),
            mock.patch.object(wiki.subprocess, "run", side_effect=sonuclar),
            mock.patch.object(wiki.subprocess, "Popen") as baslat,
        ):
            self.assertFalse(wiki.otomatik_git_yedekle())
        baslat.assert_not_called()

    def test_arayuz_girdileri_dostca_dogrular(self):
        conn = sqlite3.connect(":memory:")
        conn.execute(
            "CREATE VIRTUAL TABLE makaleler USING fts5(satir_id UNINDEXED, baslik, metin, tokenize='unicode61 remove_diacritics 0')"
        )
        conn.execute(
            "INSERT INTO makaleler VALUES (?, ?, ?)",
            (
                1,
                "Bilgisayar",
                "Bilgisayar, verileri işleyen programlanabilir elektronik bir aygıttır. "
                "Modern bilgisayarlar pek çok görevi hızlı ve güvenilir biçimde tamamlar. "
                "Donanım ve yazılım parçaları birlikte çalışarak bilgiyi saklar, düzenler ve kullanıcıya sunar.",
            ),
        )
        conn.commit()
        girdiler = iter(["!!!", "ve ile bir", "bilgisayar", "abc", "99", "1", "y", "q"])
        cikti = io.StringIO()
        with (
            mock.patch.object(wiki, "otomatik_git_yedekle"),
            mock.patch.object(wiki, "veritabani_kur", return_value=conn),
            mock.patch("builtins.input", side_effect=lambda _="": next(girdiler)),
            contextlib.redirect_stdout(cikti),
        ):
            wiki.interaktif_arama()
        metin = cikti.getvalue()
        self.assertIn("Lütfen harf veya rakam içeren", metin)
        self.assertIn("yalnızca çok genel kelimelerden oluşuyor", metin)
        self.assertIn("Lütfen bir sonuç numarası", metin)
        self.assertIn("Lütfen 1 ile 1 arasında", metin)
        self.assertIn("Konu Başlığı", metin)
        self.assertIn("İçerik Özeti", metin)
        self.assertIn("Makaleden Geniş Metin", metin)

    def test_arayuz_sonuclari_onarlik_sayfalarda_gezer(self):
        conn = sqlite3.connect(":memory:")
        sonuclar = [
            {
                "baslik": f"Başlık {sira}",
                "eslesme_durumu": "Aradığınız konu bu maddede bulundu.",
                "ozet": f"Özet {sira}",
                "detay": f"Ayrıntı {sira}",
            }
            for sira in range(1, 24)
        ]
        girdiler = iter(["deneme", "p", "n", "n", "n", "23", "y", "q"])
        cikti = io.StringIO()
        with (
            mock.patch.object(wiki, "otomatik_git_yedekle"),
            mock.patch.object(wiki, "veritabani_kur", return_value=conn),
            mock.patch.object(wiki, "esnek_arama", return_value=sonuclar),
            mock.patch("builtins.input", side_effect=lambda _="": next(girdiler)),
            contextlib.redirect_stdout(cikti),
        ):
            wiki.interaktif_arama()

        metin = cikti.getvalue()
        self.assertIn("Sayfa 1/3", metin)
        self.assertIn("Sayfa 2/3", metin)
        self.assertIn("Sayfa 3/3", metin)
        self.assertIn("Zaten ilk sonuç sayfasındasınız", metin)
        self.assertIn("Zaten son sonuç sayfasındasınız", metin)
        self.assertIn("Başlık 11", metin)
        self.assertIn("Başlık 21", metin)
        self.assertIn("23. SONUÇ", metin)


if __name__ == "__main__":
    unittest.main()
