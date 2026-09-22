import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from app.db.base import Base
import app.models  # load all models
from sqlalchemy.dialects.sqlite import JSON

# Patch JSONB for SQLite testing
from sqlalchemy.dialects.postgresql import JSONB
import sqlalchemy.types
sqlalchemy.types.JSONB = JSON

async def test_db_schema():
    # Use in-memory SQLite for testing schema validity
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    
    # We must replace JSONB columns for sqlite to work
    for table in Base.metadata.tables.values():
        for column in table.columns:
            if isinstance(column.type, JSONB):
                column.type = JSON()
                
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        print("SUCCESS: SQLAlchemy models compiled and created successfully.")
    except Exception as e:
        print(f"FAILURE: {e}")
        import sys
        sys.exit(1)

if __name__ == '__main__':
    asyncio.run(test_db_schema())
