"""Dependency-free Turkish Wikipedia FTS5 search tools."""

from .engine import (
    arama_terimlerini_ayikla,
    baslik_uydur,
    esnek_arama,
    veritabani_kur,
    wiki_metni_sadelestir,
)

__all__ = [
    "arama_terimlerini_ayikla",
    "baslik_uydur",
    "esnek_arama",
    "veritabani_kur",
    "wiki_metni_sadelestir",
]

__version__ = "1.0.0"
