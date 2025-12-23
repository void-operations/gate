"""
Release Management Routes
"""

from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Optional
from sqlalchemy import select, delete
from typing import List
from datetime import datetime
import re
import httpx
from pydantic import BaseModel

from database import get_db
from db_models import ReleaseDB, SettingsDB
from models import Release, ReleaseCreate, ReleaseUpdate

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


@router.put("/{release_id}", response_model=Release)
async def update_release(
    release_id: str,
    release_data: ReleaseUpdate,
    db: AsyncSession = Depends(get_db)
):
    """Update a release"""
    result = await db.execute(select(ReleaseDB).where(ReleaseDB.id == release_id))
    release_db = result.scalar_one_or_none()
    
    if not release_db:
        raise HTTPException(status_code=404, detail="Release not found")
    
    # Update fields if provided
    if release_data.name is not None:
        release_db.name = release_data.name
    if release_data.description is not None:
        release_db.description = release_data.description
    if release_data.download_url is not None:
        release_db.download_url = release_data.download_url
    
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


class GitHubReleaseVersion(BaseModel):
    """GitHub release version information"""
    tag_name: str
    name: str
    published_at: str
    html_url: str
    assets: List[dict] = []


async def get_github_token_from_db(db: AsyncSession) -> Optional[str]:
    """Get GitHub token from database"""
    result = await db.execute(select(SettingsDB).where(SettingsDB.key == "github_token"))
    settings_db = result.scalar_one_or_none()
    return settings_db.value if settings_db and settings_db.value else None


@router.get("/{release_id}/versions", response_model=List[GitHubReleaseVersion])
async def get_release_versions(release_id: str, db: AsyncSession = Depends(get_db)):
    """Get available versions from GitHub releases for a specific release"""
    # Get release from database
    result = await db.execute(select(ReleaseDB).where(ReleaseDB.id == release_id))
    release_db = result.scalar_one_or_none()
    
    if not release_db:
        raise HTTPException(status_code=404, detail="Release not found")
    
    # Extract owner and repo from GitHub URL
    github_url = release_db.download_url.rstrip('/')
    pattern = r'https://github\.com/([^/]+)/([^/]+)'
    match = re.match(pattern, github_url)
    
    if not match:
        raise HTTPException(status_code=400, detail="Invalid GitHub URL format")
    
    owner, repo = match.groups()
    
    # Get GitHub token
    github_token = await get_github_token_from_db(db)
    
    # Fetch releases from GitHub API
    headers = {}
    if github_token:
        headers["Authorization"] = f"token {github_token}"
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                f"https://api.github.com/repos/{owner}/{repo}/releases",
                headers=headers,
                timeout=10.0
            )
            
            if response.status_code == 404:
                raise HTTPException(status_code=404, detail="GitHub repository not found")
            elif response.status_code == 401:
                raise HTTPException(status_code=401, detail="GitHub authentication failed. Please check your GitHub token.")
            elif not response.is_success:
                raise HTTPException(
                    status_code=response.status_code,
                    detail=f"Failed to fetch GitHub releases: {response.text}"
                )
            
            releases_data = response.json()
            
            # Convert to response model
            versions = []
            for release in releases_data:
                versions.append(GitHubReleaseVersion(
                    tag_name=release.get("tag_name", ""),
                    name=release.get("name", release.get("tag_name", "")),
                    published_at=release.get("published_at", ""),
                    html_url=release.get("html_url", ""),
                    assets=release.get("assets", [])
                ))
            
            return versions
            
        except httpx.TimeoutException:
            raise HTTPException(status_code=504, detail="GitHub API request timeout")
        except httpx.RequestError as e:
            raise HTTPException(status_code=503, detail=f"Failed to connect to GitHub API: {str(e)}")

