#!/usr/bin/env python3
"""Backward-compatible launcher; prefer the ``wikipedia-fts5`` command."""

from wikipedia_fts5.cli import main


if __name__ == "__main__":
    raise SystemExit(main())
