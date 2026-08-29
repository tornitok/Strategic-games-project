"""Запуск пакета как `python -m sgame`."""

import sys

from .cli import main

if __name__ == "__main__":
    sys.exit(main())
