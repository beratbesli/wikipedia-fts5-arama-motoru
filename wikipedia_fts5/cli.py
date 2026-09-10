"""Command-line entry point for building and querying a local FTS5 database."""

from __future__ import annotations

import argparse
import sqlite3
from pathlib import Path

from .engine import esnek_arama, veritabani_kur


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Türkçe Wikipedia FTS5 arama motoru")
    parser.add_argument("query", nargs="?", help="Aranacak ifade; verilmezse etkileşimli mod açılır")
    parser.add_argument("--database", type=Path, default=Path("wiki_fts.db"))
    parser.add_argument("--source", type=Path, default=Path("wiki_temiz.txt"))
    parser.add_argument("--limit", type=int, default=10)
    parser.add_argument("--build", action="store_true", help="Kaynak dosyadan veritabanını oluştur")
    parser.add_argument("--max-records", type=int, default=None, help="Azami kayıt; varsayılan tümü")
    return parser


def _open_database(args: argparse.Namespace) -> sqlite3.Connection | None:
    if args.build or not args.database.is_file():
        return veritabani_kur(
            str(args.source), str(args.database), max_satir=args.max_records
        )
    try:
        return sqlite3.connect(args.database)
    except sqlite3.Error as exc:
        raise SystemExit(f"Veritabanı açılamadı: {exc}") from exc


def _print_results(query: str, results: list[dict]) -> None:
    if not results:
        print("Sonuç bulunamadı.")
        return
    for index, result in enumerate(results, start=1):
        print(f"{index}. {result['baslik']}")
        print(f"   {result['ozet']}")


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    connection = _open_database(args)
    if connection is None:
        return 2
    try:
        if args.query:
            _print_results(args.query, esnek_arama(connection, args.query, args.limit))
            return 0
        print("Türkçe Wikipedia araması. Çıkış için q yazın.")
        while True:
            try:
                query = input("Arama > ").strip()
            except (EOFError, KeyboardInterrupt):
                print()
                return 0
            if query.casefold() in {"q", "quit", "exit", "çıkış"}:
                return 0
            _print_results(query, esnek_arama(connection, query, args.limit))
    finally:
        connection.close()


if __name__ == "__main__":
    raise SystemExit(main())
