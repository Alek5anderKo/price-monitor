"""Простая блокировка через файл: защита от одновременного запуска двух экземпляров.
Если lock-файл старше MAX_AGE секунд, считается зависшим и удаляется."""
import logging
import os
import sys
import time

logger = logging.getLogger(__name__)

# Default path when acquire_lock() / release_lock() are called without arguments (backward compatible).
LOCK_FILE = "run.lock"
MAX_AGE = 1800  # 30 минут


def _resolved_lock_path(lock_file):
    if lock_file is None or str(lock_file).strip() == "":
        return LOCK_FILE
    return os.path.normpath(str(lock_file).strip())


def _ensure_lock_parent_dir(lock_path):
    """Создать каталог locks/, если lock_file лежит под каталогом locks (в т.ч. вложенным)."""
    abs_path = os.path.abspath(lock_path)
    parts = abs_path.split(os.sep)
    if "locks" not in parts:
        return
    parent = os.path.dirname(abs_path)
    if parent:
        os.makedirs(parent, exist_ok=True)


def acquire_lock(lock_file=None):
    """
    Захватывает блокировку. При существующем свежем lock — лог и sys.exit(1) без traceback.
    При старом lock удаляет его и создаёт новый.

    lock_file: путь к файлу блокировки; None — совместимость со старым поведением (run.lock).
    """
    path = _resolved_lock_path(lock_file)
    _ensure_lock_parent_dir(path)

    if os.path.exists(path):
        age = time.time() - os.path.getmtime(path)
        if age < MAX_AGE:
            logger.warning(
                "Another run is active (lock file exists): %s. Exiting without traceback.",
                path,
            )
            sys.exit(1)
        logger.info("Stale lock found (age %ss >= %ss), removing: %s", int(age), MAX_AGE, path)
        try:
            os.remove(path)
        except OSError:
            pass

    with open(path, "w", encoding="utf-8") as f:
        f.write(str(time.time()))


def release_lock(lock_file=None):
    """
    Снимает блокировку для того же пути, что и acquire_lock(lock_file=...).
    lock_file=None — снимает блокировку по умолчанию (run.lock).
    Вызывать в finally.
    """
    path = _resolved_lock_path(lock_file)
    if os.path.exists(path):
        try:
            os.remove(path)
        except OSError:
            pass
