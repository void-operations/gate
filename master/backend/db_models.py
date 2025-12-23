"""
SQLAlchemy database models
"""
from sqlalchemy import Column, String, DateTime, Text, JSON, Enum as SQLEnum, Index, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime
from typing import Optional
import enum

from database import Base


class AgentStatusEnum(str, enum.Enum):
    """Agent status enumeration"""
    ONLINE = "online"
    OFFLINE = "offline"
    ERROR = "error"


class DeploymentStatusEnum(str, enum.Enum):
    """Deployment status enumeration"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    SUCCESS = "success"
    FAILED = "failed"


class AgentDB(Base):
    """Agent database model"""
    __tablename__ = "agents"

    id = Column(String, primary_key=True, index=True)
    name = Column(String, nullable=False, index=True)
    platform = Column(String, nullable=False)  # "windows" or "macos"
    version = Column(String, nullable=False)
    status = Column(SQLEnum(AgentStatusEnum), nullable=False, default=AgentStatusEnum.OFFLINE)
    last_seen = Column(DateTime, nullable=False, default=func.now(), onupdate=func.now())
    ip_address = Column(String, nullable=True)

    def __repr__(self):
        return f"<AgentDB(id={self.id}, name={self.name}, platform={self.platform})>"


class ReleaseDB(Base):
    """Release database model"""
    __tablename__ = "releases"

    id = Column(String, primary_key=True, index=True)
    tag_name = Column(String, nullable=False)
    name = Column(String, nullable=False)
    version = Column(String, nullable=True)  # Will be populated when fetching versions
    release_date = Column(DateTime, nullable=False, default=func.now())
    download_url = Column(Text, nullable=True)
    description = Column(Text, nullable=True)
    assets = Column(JSON, nullable=True, default=list)  # List of artifact file names

    def __repr__(self):
        return f"<ReleaseDB(id={self.id}, name={self.name}, tag_name={self.tag_name})>"


class DeploymentDB(Base):
    """Deployment database model"""
    __tablename__ = "deployments"

    id = Column(String, primary_key=True, index=True)
    agent_id = Column(String, ForeignKey('agents.id', ondelete='CASCADE'), nullable=False, index=True)
    release_ids = Column(JSON, nullable=False)  # List of release IDs
    release_tags = Column(JSON, nullable=False)  # List of release tag names
    status = Column(SQLEnum(DeploymentStatusEnum), nullable=False, default=DeploymentStatusEnum.PENDING)
    created_at = Column(DateTime, nullable=False, default=func.now())
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    error_message = Column(Text, nullable=True)
    
    # Relationship to Agent
    agent = relationship("AgentDB", backref="deployments")
    
    # Indexes for efficient querying
    # Composite index for common query: WHERE agent_id = ? AND status = ? ORDER BY created_at
    __table_args__ = (
        Index('idx_deployment_agent_status_created', 'agent_id', 'status', 'created_at'),
        Index('idx_deployment_status', 'status'),  # For filtering by status
        Index('idx_deployment_created_at', 'created_at'),  # For ordering by created_at
    )

    def __repr__(self):
        return f"<DeploymentDB(id={self.id}, agent_id={self.agent_id}, status={self.status})>"


class SettingsDB(Base):
    """Settings database model (for GitHub token storage)"""
    __tablename__ = "settings"

    key = Column(String, primary_key=True, index=True)
    value = Column(Text, nullable=False)
    updated_at = Column(DateTime, nullable=False, default=func.now(), onupdate=func.now())

    def __repr__(self):
        return f"<SettingsDB(key={self.key})>"

