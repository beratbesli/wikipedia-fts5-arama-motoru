import sqlite3

from wikipedia_fts5 import arama_terimlerini_ayikla, esnek_arama


def database() -> sqlite3.Connection:
    connection = sqlite3.connect(":memory:")
    connection.execute(
        "CREATE VIRTUAL TABLE makaleler USING fts5("
        "satir_id UNINDEXED, baslik, metin, tokenize='unicode61 remove_diacritics 0')"
    )
    rows = [
        (1, "İstanbul", "İstanbul, Türkiye'nin en kalabalık şehridir. Tarihi ve kültürel mirasıyla tanınır. " * 3),
        (2, "Ankara", "Ankara, Türkiye'nin başkenti ve İç Anadolu Bölgesi'ndeki önemli bir şehirdir. " * 4),
        (3, "İstanbul Boğazı", "İstanbul Boğazı, Karadeniz ile Marmara Denizi'ni birbirine bağlayan su yoludur. " * 4),
    ]
    connection.executemany("INSERT INTO makaleler VALUES (?, ?, ?)", rows)
    return connection


def test_turkish_normalization_and_stop_words() -> None:
    assert arama_terimlerini_ayikla("İSTANBUL ve istanbul") == ["İSTANBUL"]
    assert arama_terimlerini_ayikla("ve ile için") == []


def test_exact_title_is_ranked_first() -> None:
    connection = database()
    try:
        results = esnek_arama(connection, "İstanbul", limit=3)
    finally:
        connection.close()
    assert results
    assert results[0]["baslik"] == "İstanbul"


def test_prefix_search_and_invalid_database() -> None:
    connection = database()
    try:
        results = esnek_arama(connection, "İstanb", limit=3, on_ek_eslesmesi=True)
    finally:
        connection.close()
    assert {result["baslik"] for result in results} >= {"İstanbul"}
    invalid = sqlite3.connect(":memory:")
    try:
        assert esnek_arama(invalid, "İstanbul") == []
    finally:
        invalid.close()
