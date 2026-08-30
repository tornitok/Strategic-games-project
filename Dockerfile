# Движок стратегических игр: сборка в отдельном слое, в образ едет только venv.
FROM python:3.13-slim AS build

ENV PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /src

# Зависимости ставим до копирования кода: правка сценария не пересобирает слой.
COPY pyproject.toml README.md ./
RUN python -m venv /venv \
    && /venv/bin/pip install \
        "pydantic>=2.7" "pyyaml>=6" "fastapi>=0.110" "uvicorn>=0.29" \
        "jinja2>=3.1" "python-multipart>=0.0.9" "segno>=1.6"

COPY sgame ./sgame
RUN /venv/bin/pip install --no-deps .


FROM python:3.13-slim AS runtime

ENV PATH="/venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    SGAME_DATA_DIR=/data \
    SGAME_PORT=8000

# Партии, настройки и загруженные сценарии переживают пересоздание контейнера.
RUN useradd --create-home --uid 10001 sgame \
    && mkdir -p /data \
    && chown sgame:sgame /data

COPY --from=build /venv /venv

USER sgame
WORKDIR /home/sgame
VOLUME ["/data"]
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD python -c "import os,urllib.request; \
urllib.request.urlopen('http://127.0.0.1:' + os.environ['SGAME_PORT'] + '/').read(1)"

# --network слушает 0.0.0.0 и включает режим класса: коды команд и QR.
# --no-browser: открывать нечего, браузер снаружи.
CMD ["sh", "-c", "exec python -m sgame run --network --no-browser --port ${SGAME_PORT}"]
