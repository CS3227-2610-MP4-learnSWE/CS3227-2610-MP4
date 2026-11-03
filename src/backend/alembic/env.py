import os
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from alembic import context
from sqlalchemy import create_engine, pool
from teacher_materials.models import Base

config = context.config
target_metadata = Base.metadata
url = os.environ.get("DATABASE_URL", config.get_main_option("sqlalchemy.url"))

if context.is_offline_mode():
    context.configure(url=url, target_metadata=target_metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()
else:
    with create_engine(url, poolclass=pool.NullPool, isolation_level="READ COMMITTED").connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()
