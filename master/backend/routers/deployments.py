"""
Deployment Management Routes
"""

from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, asc
from sqlalchemy.orm import selectinload
from typing import List, Optional
from datetime import datetime

from database import get_db
from db_models import AgentDB, ReleaseDB, DeploymentDB, DeploymentStatusEnum
from models import Deployment, DeploymentCreate, DeploymentComplete, DeploymentStatus

router = APIRouter(prefix="/api/deployments", tags=["deployments"])


@router.get("", response_model=List[Deployment])
async def get_deployments(
    agent_id: Optional[str] = None,
    status: Optional[DeploymentStatus] = None,
    db: AsyncSession = Depends(get_db)
):
    """
    List all deployments with optional filtering
    - agent_id: Filter by agent ID
    - status: Filter by deployment status (pending, in_progress, success, failed)
    """
    query = select(DeploymentDB)
    
    # Apply filters
    if agent_id:
        query = query.where(DeploymentDB.agent_id == agent_id)
    
    if status:
        query = query.where(DeploymentDB.status == DeploymentStatusEnum(status.value))
    
    # Order by created_at descending (newest first)
    query = query.order_by(desc(DeploymentDB.created_at))
    
    # Join with Agent to get current agent name
    query = query.options(selectinload(DeploymentDB.agent))
    result = await db.execute(query)
    deployments_db = result.scalars().all()
    
    return [
        Deployment(
            id=deployment.id,
            agent_id=deployment.agent_id,
            agent_name=deployment.agent.name if deployment.agent else "Unknown",
            release_ids=deployment.release_ids or [],
            release_tags=deployment.release_tags or [],
            status=DeploymentStatus(deployment.status.value),
            created_at=deployment.created_at,
            started_at=deployment.started_at,
            completed_at=deployment.completed_at,
            error_message=deployment.error_message,
        )
        for deployment in deployments_db
    ]


@router.get("/history", response_model=List[Deployment])
async def get_deployment_history(limit: int = 50, db: AsyncSession = Depends(get_db)):
    """Get deployment history"""
    result = await db.execute(
        select(DeploymentDB)
        .options(selectinload(DeploymentDB.agent))
        .order_by(desc(DeploymentDB.created_at))
        .limit(limit)
    )
    deployments_db = result.scalars().all()
    
    return [
        Deployment(
            id=deployment.id,
            agent_id=deployment.agent_id,
            agent_name=deployment.agent.name if deployment.agent else "Unknown",
            release_ids=deployment.release_ids or [],
            release_tags=deployment.release_tags or [],
            status=DeploymentStatus(deployment.status.value),
            created_at=deployment.created_at,
            started_at=deployment.started_at,
            completed_at=deployment.completed_at,
            error_message=deployment.error_message,
        )
        for deployment in deployments_db
    ]


@router.get("/pending/{agent_id}", response_model=Optional[Deployment])
async def get_pending_deployment(agent_id: str, db: AsyncSession = Depends(get_db)):
    """
    Get pending deployment for an agent (Agent polling endpoint)
    Returns the oldest PENDING deployment for the agent, or None if no pending deployment exists
    """
    # Verify agent exists
    result = await db.execute(select(AgentDB).where(AgentDB.id == agent_id))
    agent_db = result.scalar_one_or_none()
    
    if not agent_db:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    # Get oldest PENDING deployment for this agent
    result = await db.execute(
        select(DeploymentDB)
        .options(selectinload(DeploymentDB.agent))
        .where(DeploymentDB.agent_id == agent_id)
        .where(DeploymentDB.status == DeploymentStatusEnum.PENDING)
        .order_by(asc(DeploymentDB.created_at))
        .limit(1)
    )
    deployment_db = result.scalar_one_or_none()
    
    if not deployment_db:
        return None
    
    # Update status to IN_PROGRESS and set started_at
    deployment_db.status = DeploymentStatusEnum.IN_PROGRESS
    deployment_db.started_at = datetime.now()
    await db.commit()
    await db.refresh(deployment_db)
    
    return Deployment(
        id=deployment_db.id,
        agent_id=deployment_db.agent_id,
        agent_name=deployment_db.agent.name if deployment_db.agent else "Unknown",
        release_ids=deployment_db.release_ids or [],
        release_tags=deployment_db.release_tags or [],
        status=DeploymentStatus(deployment_db.status.value),
        created_at=deployment_db.created_at,
        started_at=deployment_db.started_at,
        completed_at=deployment_db.completed_at,
        error_message=deployment_db.error_message,
    )


@router.get("/{deployment_id}", response_model=Deployment)
async def get_deployment(deployment_id: str, db: AsyncSession = Depends(get_db)):
    """Get specific deployment"""
    result = await db.execute(
        select(DeploymentDB)
        .options(selectinload(DeploymentDB.agent))
        .where(DeploymentDB.id == deployment_id)
    )
    deployment_db = result.scalar_one_or_none()
    
    if not deployment_db:
        raise HTTPException(status_code=404, detail="Deployment not found")
    
    return Deployment(
        id=deployment_db.id,
        agent_id=deployment_db.agent_id,
        agent_name=deployment_db.agent.name if deployment_db.agent else "Unknown",
        release_ids=deployment_db.release_ids or [],
        release_tags=deployment_db.release_tags or [],
        status=DeploymentStatus(deployment_db.status.value),
        created_at=deployment_db.created_at,
        started_at=deployment_db.started_at,
        completed_at=deployment_db.completed_at,
        error_message=deployment_db.error_message,
    )


@router.post("", response_model=Deployment)
async def create_deployment(deployment_data: DeploymentCreate, db: AsyncSession = Depends(get_db)):
    """Create a deployment (can deploy multiple releases to an agent at once)"""
    # Validate agent exists
    result = await db.execute(select(AgentDB).where(AgentDB.id == deployment_data.agent_id))
    agent_db = result.scalar_one_or_none()
    
    if not agent_db:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    # Validate all releases exist and use selected versions if provided
    release_tags = []
    if deployment_data.release_versions and len(deployment_data.release_versions) == len(deployment_data.release_ids):
        # Use provided version tags
        release_tags = deployment_data.release_versions
    else:
        # Fallback to release tag_name if versions not provided
        for release_id in deployment_data.release_ids:
            result = await db.execute(select(ReleaseDB).where(ReleaseDB.id == release_id))
            release_db = result.scalar_one_or_none()
            if not release_db:
                raise HTTPException(status_code=404, detail=f"Release {release_id} not found")
            release_tags.append(release_db.tag_name)
    
    # Create deployment
    deployment_id = f"deploy-{agent_db.id}-{datetime.now().strftime('%Y%m%d%H%M%S')}"
    
    deployment_db = DeploymentDB(
        id=deployment_id,
        agent_id=deployment_data.agent_id,
        release_ids=deployment_data.release_ids,
        release_tags=release_tags,
        status=DeploymentStatusEnum.PENDING,
        created_at=datetime.now()
    )
    
    db.add(deployment_db)
    await db.commit()
    await db.refresh(deployment_db)
    
    # Load agent relationship for response
    await db.refresh(deployment_db, ['agent'])
    
    # Deployment is created in PENDING state
    # Agent will poll /api/deployments/pending/{agent_id} to retrieve and execute it
    
    return Deployment(
        id=deployment_db.id,
        agent_id=deployment_db.agent_id,
        agent_name=deployment_db.agent.name if deployment_db.agent else "Unknown",
        release_ids=deployment_db.release_ids or [],
        release_tags=deployment_db.release_tags or [],
        status=DeploymentStatus(deployment_db.status.value),
        created_at=deployment_db.created_at,
        started_at=deployment_db.started_at,
        completed_at=deployment_db.completed_at,
        error_message=deployment_db.error_message,
    )


@router.post("/{deployment_id}/complete")
async def complete_deployment(
    deployment_id: str,
    completion_data: DeploymentComplete,
    db: AsyncSession = Depends(get_db)
):
    """
    Report deployment completion (Agent reports deployment result)
    """
    # Get deployment
    result = await db.execute(select(DeploymentDB).where(DeploymentDB.id == deployment_id))
    deployment_db = result.scalar_one_or_none()
    
    if not deployment_db:
        raise HTTPException(status_code=404, detail="Deployment not found")
    
    # Validate status
    if completion_data.status not in [DeploymentStatus.SUCCESS, DeploymentStatus.FAILED]:
        raise HTTPException(
            status_code=400,
            detail="Status must be either 'success' or 'failed'"
        )
    
    # Update deployment status
    deployment_db.status = DeploymentStatusEnum(completion_data.status.value)
    deployment_db.completed_at = datetime.now()
    if completion_data.error_message:
        deployment_db.error_message = completion_data.error_message
    
    await db.commit()
    await db.refresh(deployment_db)
    
    return {
        "message": "Deployment status updated",
        "deployment_id": deployment_id,
        "status": completion_data.status.value
    }

