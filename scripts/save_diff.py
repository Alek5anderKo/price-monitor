#!/usr/bin/env python3
"""Пишет вывод git diff в diff.txt в кодировке UTF-8. Запускать из корня репозитория."""
import subprocess
import sys

DIFF_FILE = "diff.txt"
ENCODING = "utf-8"

if __name__ == "__main__":
    try:
        result = subprocess.run(
            ["git", "diff"],
            capture_output=True,
            text=True,
            encoding=ENCODING,
            check=False,
        )
        out = result.stdout or ""
        err = result.stderr or ""
    except Exception as e:
        out = ""
        err = str(e)
        result = None

    with open(DIFF_FILE, "w", encoding=ENCODING) as f:
        f.write(out)
        if err:
            f.write("\n\n# stderr:\n")
            f.write(err)

    if result is not None and result.returncode not in (0, None):
        sys.exit(result.returncode)
