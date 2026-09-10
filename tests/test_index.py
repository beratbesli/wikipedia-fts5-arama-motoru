import sqlite3
from pathlib import Path

from wikipedia_fts5 import veritabani_kur


def test_builds_small_deterministic_index(tmp_path: Path) -> None:
    source = tmp_path / "wiki.txt"
    database = tmp_path / "wiki.db"
    source.write_text(
        "İstanbul, Türkiye'nin en kalabalık şehridir ve tarihî mirası çok zengindir.\n"
        "Ankara, Türkiye Cumhuriyeti'nin başkentidir ve İç Anadolu'dadır.\n",
        encoding="utf-8",
    )
    connection = veritabani_kur(str(source), str(database), max_satir=None, batch_size=1)
    assert isinstance(connection, sqlite3.Connection)
    try:
        assert connection.execute("SELECT count(*) FROM makaleler").fetchone()[0] == 2
    finally:
        connection.close()
