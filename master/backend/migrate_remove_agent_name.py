"""
Migration script to remove agent_name column from deployments table
This migration changes deployments to use FK relationship instead of storing agent_name as string
"""
import asyncio
import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy import text

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "sqlite+aiosqlite:///./master.db"
)

IS_SQLITE = DATABASE_URL.startswith("sqlite+aiosqlite")


async def migrate():
    """Remove agent_name column from deployments table"""
    engine = create_async_engine(DATABASE_URL, echo=True)
    
    async with engine.begin() as conn:
        if IS_SQLITE:
            # SQLite doesn't support DROP COLUMN directly
            # Need to recreate table without agent_name column
            print("SQLite detected - recreating deployments table without agent_name...")
            
            # Step 1: Create new table without agent_name
            await conn.execute(text("""
                CREATE TABLE deployments_new (
                    id TEXT NOT NULL PRIMARY KEY,
                    agent_id TEXT NOT NULL,
                    release_ids TEXT NOT NULL,
                    release_tags TEXT NOT NULL,
                    status TEXT NOT NULL,
                    created_at DATETIME NOT NULL,
                    started_at DATETIME,
                    completed_at DATETIME,
                    error_message TEXT
                )
            """))
            
            # Step 2: Copy data (excluding agent_name)
            await conn.execute(text("""
                INSERT INTO deployments_new 
                (id, agent_id, release_ids, release_tags, status, created_at, started_at, completed_at, error_message)
                SELECT 
                    id, agent_id, release_ids, release_tags, status, created_at, started_at, completed_at, error_message
                FROM deployments
            """))
            
            # Step 3: Drop old table
            await conn.execute(text("DROP TABLE deployments"))
            
            # Step 4: Rename new table
            await conn.execute(text("ALTER TABLE deployments_new RENAME TO deployments"))
            
            # Step 5: Recreate indexes
            await conn.execute(text("CREATE INDEX idx_deployment_agent_status_created ON deployments(agent_id, status, created_at)"))
            await conn.execute(text("CREATE INDEX idx_deployment_status ON deployments(status)"))
            await conn.execute(text("CREATE INDEX idx_deployment_created_at ON deployments(created_at)"))
            
            print("✅ Migration completed for SQLite")
        else:
            # PostgreSQL: Can use ALTER TABLE DROP COLUMN
            print("PostgreSQL detected - dropping agent_name column...")
            await conn.execute(text("ALTER TABLE deployments DROP COLUMN IF EXISTS agent_name"))
            print("✅ Migration completed for PostgreSQL")
    
    await engine.dispose()
    print("Migration script completed successfully!")


if __name__ == "__main__":
    print("Starting migration: Remove agent_name column from deployments table")
    print("This will change deployments to use FK relationship with agents table")
    response = input("Continue? (yes/no): ")
    if response.lower() == "yes":
        asyncio.run(migrate())
    else:
        print("Migration cancelled")

