"""Простая блокировка через файл: защита от одновременного запуска двух экземпляров."""
import logging
import os

LOCK_FILE = "price_monitor.lock"
_held = False
logger = logging.getLogger(__name__)


def acquire():
    """Пытается захватить блокировку. Возвращает True при успехе, False если уже запущен другой экземпляр."""
    global _held
    try:
        with open(LOCK_FILE, "x") as f:
            f.write(str(os.getpid()))
        _held = True
        return True
    except FileExistsError:
        return False


def release():
    """Снимает блокировку. Вызывать в finally. Удаляет файл только если блокировка была захвачена этим процессом."""
    global _held
    if not _held:
        return
    try:
        os.remove(LOCK_FILE)
    except OSError as e:
        logger.warning("Could not remove lock file %s: %s", LOCK_FILE, e)
    finally:
        _held = False
