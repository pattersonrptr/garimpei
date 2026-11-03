#!/bin/bash

while ! nc -z db 5432; do
  echo "Waiting for database $db..."
  sleep 1
done

sleep 5

# Migrations are versioned in alembic/versions. Databases created by the old
# "delete and autogenerate on every boot" flow are stamped onto the baseline.
python3 src/scripts/adopt_migration_baseline.py
alembic upgrade head

# Initialize development database with default superuser
echo "Initializing development database..."
python3 src/scripts/init_dev_db.py

# Fix sequences after seed inserts with explicit IDs
echo "Syncing database sequences..."
python3 -c "
from sqlalchemy import create_engine, text
import os
engine = create_engine(os.environ['DATABASE_URL'])
with engine.connect() as conn:
    tables = conn.execute(text(
        \"SELECT tablename FROM pg_tables WHERE schemaname = 'public' AND tablename != 'alembic_version'\"
    )).fetchall()
    for (table,) in tables:
        seq = f'{table}_id_seq'
        try:
            conn.execute(text(f\"SELECT setval('{seq}', COALESCE((SELECT MAX(id) FROM {table}), 1))\"))
        except Exception:
            pass
    conn.commit()
print('✓ Sequences synced')
"

uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload
