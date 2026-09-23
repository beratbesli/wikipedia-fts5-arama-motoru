import os
import sqlite3
from pathlib import Path

from wikipedia_fts5 import veritabani_kur
from wikipedia_fts5 import engine


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


def test_rebuilds_when_source_changes_without_size_or_mtime_change(tmp_path: Path) -> None:
    source = tmp_path / "wiki.txt"
    database = tmp_path / "wiki.db"
    source.write_text("Alpha is a long test article about one city and its history.\n", encoding="utf-8")
    first = veritabani_kur(str(source), str(database), max_satir=None)
    assert first
    first.close()

    before = source.stat()
    source.write_text("Bravo is a long test article about one city and its history.\n", encoding="utf-8")
    assert source.stat().st_size == before.st_size
    os.utime(source, ns=(before.st_atime_ns, before.st_mtime_ns))

    second = veritabani_kur(str(source), str(database), max_satir=None)
    assert second
    try:
        assert second.execute("SELECT metin FROM makaleler").fetchone()[0].startswith("Bravo")
    finally:
        second.close()


def test_failed_rebuild_preserves_searchable_old_index(tmp_path: Path, monkeypatch) -> None:
    source = tmp_path / "wiki.txt"
    database = tmp_path / "wiki.db"
    source.write_text("Alpha is the original searchable article.\n", encoding="utf-8")
    first = veritabani_kur(str(source), str(database), max_satir=None)
    assert first
    first.close()

    source.write_text("Bravo is the replacement searchable article.\n", encoding="utf-8")

    def fail_batch(_connection, _batch):
        raise OSError("simulated disk failure")

    monkeypatch.setattr(engine, "_batch_ekle", fail_batch)
    assert veritabani_kur(str(source), str(database), max_satir=None, yeniden_olustur=True) is False

    with sqlite3.connect(database) as old_index:
        assert old_index.execute("SELECT metin FROM makaleler").fetchone()[0].startswith("Alpha")
    assert not list(tmp_path.glob(".wiki-fts-*.db"))
