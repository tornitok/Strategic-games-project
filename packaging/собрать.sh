#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")/.."

.venv/bin/pytest -q
.venv/bin/pyinstaller --noconfirm --clean packaging/sgame.spec

APP="dist/Стратегическая игра.app"

# Расширенные атрибуты (метки Finder, карантин) мешают подписи, а без подписи
# приложение на Apple Silicon просто не запустится. Два прохода не лишние:
# за один вызов атрибуты каталогов вычищаются не полностью.
xattr -cr "$APP"
xattr -cr "$APP"
codesign --force --deep --sign - "$APP"
codesign --verify --deep "$APP" && echo "Подпись (ad-hoc) на месте"

cd dist && rm -f "Стратегическая игра.zip" && zip -qry "Стратегическая игра.zip" "Стратегическая игра.app"
echo "Готово: dist/Стратегическая игра.zip"
