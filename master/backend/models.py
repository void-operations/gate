"""
Data models for Master backend
Following Clean Architecture principles
"""

from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
from enum import Enum


class AgentStatus(str, Enum):
    """Agent status enumeration"""
    ONLINE = "online"
    OFFLINE = "offline"
    ERROR = "error"


class DeploymentStatus(str, Enum):
    """Deployment status enumeration"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    SUCCESS = "success"
    FAILED = "failed"


class Agent(BaseModel):
    """Agent model"""
    id: str
    name: str
    platform: str  # "windows" or "macos"
    version: str
    status: AgentStatus
    last_seen: datetime
    ip_address: Optional[str] = None


class AgentRegister(BaseModel):
    """Agent registration request model"""
    name: str
    platform: str
    version: str
    ip_address: Optional[str] = None


class AgentUpdate(BaseModel):
    """Agent update request model"""
    name: Optional[str] = None


class Release(BaseModel):
    """Release model (GitHub Release)"""
    id: str  # GitHub release ID or tag name
    tag_name: str
    name: str
    version: str
    release_date: datetime
    download_url: Optional[str] = None
    description: Optional[str] = None
    assets: List[str] = []  # List of artifact file names


class ReleaseCreate(BaseModel):
    """Release creation request model"""
    github_url: str


class ReleaseUpdate(BaseModel):
    """Release update request model"""
    name: Optional[str] = None
    description: Optional[str] = None
    download_url: Optional[str] = None


class Deployment(BaseModel):
    """Deployment model"""
    id: str
    agent_id: str
    agent_name: str
    release_ids: List[str]  # Multiple releases can be deployed at once
    release_tags: List[str]  # Release tag names for display
    status: DeploymentStatus
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None


class DeploymentCreate(BaseModel):
    """Deployment creation request model"""
    agent_id: str
    release_ids: List[str]  # Can deploy multiple releases at once
    release_versions: Optional[List[str]] = None  # Selected version tags for each release (matches release_ids order)


class DeploymentComplete(BaseModel):
    """Deployment completion request model"""
    status: DeploymentStatus  # SUCCESS or FAILED
    error_message: Optional[str] = None


class DeploymentHistory(BaseModel):
    """Deployment history entry"""
    deployment_id: str
    agent_id: str
    agent_name: str
    releases: List[str]
    status: DeploymentStatus
    timestamp: datetime
    error_message: Optional[str] = None
