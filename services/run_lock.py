"""Простая блокировка через файл: защита от одновременного запуска двух экземпляров.
Если lock-файл старше MAX_AGE секунд, считается зависшим и удаляется."""
import os
import sys
import time

LOCK_FILE = "run.lock"
MAX_AGE = 1800  # 30 минут


def acquire_lock():
    """Захватывает блокировку. При существующем свежем lock завершает процесс. При старом lock удаляет его и создаёт новый."""
    if os.path.exists(LOCK_FILE):
        age = time.time() - os.path.getmtime(LOCK_FILE)
        if age < MAX_AGE:
            print("Another run is active (lock file exists). Exiting.")
            sys.exit(1)
        print("Old lock found, removing...")
        os.remove(LOCK_FILE)

    with open(LOCK_FILE, "w", encoding="utf-8") as f:
        f.write(str(time.time()))


def release_lock():
    """Снимает блокировку. Удаляет lock-файл, если он существует. Вызывать в finally."""
    if os.path.exists(LOCK_FILE):
        try:
            os.remove(LOCK_FILE)
        except OSError:
            pass
