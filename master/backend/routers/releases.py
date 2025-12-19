"""
Release Management Routes
"""

from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from typing import List
from datetime import datetime
import re

from database import get_db
from db_models import ReleaseDB
from models import Release, ReleaseCreate

router = APIRouter(prefix="/api/releases", tags=["releases"])


@router.get("", response_model=List[Release])
async def get_releases(db: AsyncSession = Depends(get_db)):
    """List all releases"""
    result = await db.execute(select(ReleaseDB))
    releases_db = result.scalars().all()
    
    return [
        Release(
            id=release.id,
            tag_name=release.tag_name,
            name=release.name,
            version=release.version or "",
            release_date=release.release_date,
            download_url=release.download_url,
            description=release.description,
            assets=release.assets or [],
        )
        for release in releases_db
    ]


@router.get("/{release_id}", response_model=Release)
async def get_release(release_id: str, db: AsyncSession = Depends(get_db)):
    """Get specific release"""
    result = await db.execute(select(ReleaseDB).where(ReleaseDB.id == release_id))
    release_db = result.scalar_one_or_none()
    
    if not release_db:
        raise HTTPException(status_code=404, detail="Release not found")
    
    return Release(
        id=release_db.id,
        tag_name=release_db.tag_name,
        name=release_db.name,
        version=release_db.version or "",
        release_date=release_db.release_date,
        download_url=release_db.download_url,
        description=release_db.description,
        assets=release_db.assets or [],
    )


@router.post("", response_model=Release)
async def create_release(release_data: ReleaseCreate, db: AsyncSession = Depends(get_db)):
    """Create/add a release from GitHub URL"""
    # Extract owner and repo from GitHub URL
    # Example: https://github.com/jameskwon07/3project/releases/
    github_url = release_data.github_url.rstrip('/')
    pattern = r'https://github\.com/([^/]+)/([^/]+)'
    match = re.match(pattern, github_url)
    
    if not match:
        raise HTTPException(status_code=400, detail="Invalid GitHub URL format")
    
    owner, repo = match.groups()
    
    # Use repo name as the unique ID and display name
    release_id = repo
    release_name = repo
    
    # Check if release already exists
    result = await db.execute(select(ReleaseDB).where(ReleaseDB.id == release_id))
    existing_release = result.scalar_one_or_none()
    
    if existing_release:
        raise HTTPException(status_code=400, detail=f"Release for repository '{repo}' already exists")
    
    # TODO: Fetch actual releases from GitHub API using github_token
    # For now, create a placeholder release that will be populated when versions are fetched
    release_db = ReleaseDB(
        id=release_id,
        tag_name=repo,  # Use repo name as tag_name
        name=release_name,
        version="",  # Will be populated when fetching versions
        release_date=datetime.now(),
        description=f"GitHub: {owner}/{repo}",
        download_url=github_url,
        assets=[],  # Will be populated when fetching versions
    )
    
    db.add(release_db)
    await db.commit()
    await db.refresh(release_db)
    
    return Release(
        id=release_db.id,
        tag_name=release_db.tag_name,
        name=release_db.name,
        version=release_db.version or "",
        release_date=release_db.release_date,
        download_url=release_db.download_url,
        description=release_db.description,
        assets=release_db.assets or [],
    )


@router.delete("/{release_id}")
async def delete_release(release_id: str, db: AsyncSession = Depends(get_db)):
    """Delete/remove a release"""
    result = await db.execute(select(ReleaseDB).where(ReleaseDB.id == release_id))
    release_db = result.scalar_one_or_none()
    
    if not release_db:
        raise HTTPException(status_code=404, detail="Release not found")
    
    # Use delete statement for SQLAlchemy 2.0 async
    await db.execute(delete(ReleaseDB).where(ReleaseDB.id == release_id))
    await db.commit()
    return {"message": "Release deleted"}

