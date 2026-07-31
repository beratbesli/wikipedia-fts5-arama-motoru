"""Repo degisikliklerini izleyen ve GitHub'a otomatik yollayan yardimci arac."""

import os
import time

from wiki_arama_motoru import otomatik_git_yedekle


def main():
    bekleme_suresi = float(os.environ.get("WIKI_GIT_SYNC_INTERVAL", "5"))
    print("Otomatik Git izleyici basladi. Cikmak icin Ctrl+C kullanin.")
    while True:
        otomatik_git_yedekle(arka_planda_yolla=False)
        time.sleep(bekleme_suresi)


if __name__ == "__main__":
    main()
