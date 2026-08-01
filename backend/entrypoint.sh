#!/bin/sh
# Один вхід для контейнера: дочекатись бази, накотити міграції, залити сідер,
# підняти сервер. Порядок важливий — сідер працює по вже мігрованій схемі.
set -e

python -m app.wait_for_db
alembic upgrade head
python -m app.seed
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
