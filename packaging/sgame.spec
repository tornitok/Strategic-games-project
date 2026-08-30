# PyInstaller spec: onedir + .app.
#
# Пути в spec-файле разрешаются относительно самого spec-файла, поэтому корень
# проекта вычисляется явно. Ресурсы перечислены руками, а не через
# collect_data_files: внутри PyInstaller пакет sgame не импортируется, и
# функция сбора молча вернула бы пустой список — приложение собралось бы без
# шаблонов и упало при первом запросе. Пути назначения повторяют структуру
# пакета, потому что код читает ресурсы через importlib.resources.

import os

ROOT = os.path.abspath(os.path.join(SPECPATH, ".."))

datas = [
    (os.path.join(ROOT, "sgame", "web", "templates"), "sgame/web/templates"),
    (os.path.join(ROOT, "sgame", "web", "static"), "sgame/web/static"),
    (os.path.join(ROOT, "sgame", "scenarios"), "sgame/scenarios"),
]

a = Analysis(
    [os.path.join(SPECPATH, "launcher.py")],
    pathex=[ROOT],
    datas=datas,
    hiddenimports=[
        "uvicorn.logging",
        "uvicorn.protocols.http.h11_impl",
        "uvicorn.protocols.websockets.auto",
        "uvicorn.lifespan.on",
    ],
)
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, exclude_binaries=True, name="StrategicGame", console=False)
coll = COLLECT(exe, a.binaries, a.datas, name="StrategicGame")
app = BUNDLE(
    coll,
    name="StrategicGame.app",
    bundle_identifier="ru.local.strategicgame",
    info_plist={
        "CFBundleName": "Стратегическая игра",
        "CFBundleDisplayName": "Стратегическая игра",
        "LSBackgroundOnly": False,
    },
)
