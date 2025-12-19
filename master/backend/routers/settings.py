"""
Settings Management Routes
"""

from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from datetime import datetime

from database import get_db
from db_models import SettingsDB

router = APIRouter(prefix="/api/settings", tags=["settings"])


@router.get("/github-token")
async def get_github_token(db: AsyncSession = Depends(get_db)):
    """Get GitHub token (returns masked token if exists)"""
    result = await db.execute(select(SettingsDB).where(SettingsDB.key == "github_token"))
    settings_db = result.scalar_one_or_none()
    
    if settings_db and settings_db.value:
        # Return masked token for security (show only last 4 characters)
        token = settings_db.value
        masked_token = "***" + token[-4:] if len(token) > 4 else "***"
        return {"has_token": True, "token_preview": masked_token}
    return {"has_token": False}


@router.post("/github-token")
async def set_github_token(token_data: dict, db: AsyncSession = Depends(get_db)):
    """Add or update GitHub token"""
    if "token" not in token_data:
        raise HTTPException(status_code=400, detail="Token is required")
    
    token_value = token_data["token"]
    
    # Check if token exists
    result = await db.execute(select(SettingsDB).where(SettingsDB.key == "github_token"))
    settings_db = result.scalar_one_or_none()
    
    if settings_db:
        # Update existing token
        settings_db.value = token_value
        settings_db.updated_at = datetime.now()
    else:
        # Create new token entry
        settings_db = SettingsDB(key="github_token", value=token_value)
        db.add(settings_db)
    
    await db.commit()
    return {"message": "GitHub token saved successfully"}


@router.delete("/github-token")
async def delete_github_token(db: AsyncSession = Depends(get_db)):
    """Remove GitHub token"""
    result = await db.execute(select(SettingsDB).where(SettingsDB.key == "github_token"))
    settings_db = result.scalar_one_or_none()
    
    if settings_db:
        # Use delete statement for SQLAlchemy 2.0 async
        await db.execute(delete(SettingsDB).where(SettingsDB.key == "github_token"))
        await db.commit()
    
    return {"message": "GitHub token removed successfully"}

