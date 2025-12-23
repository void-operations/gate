"""
Agent Management Routes
"""

from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from typing import List
from datetime import datetime
import uuid

from database import get_db
from db_models import AgentDB, AgentStatusEnum
from models import Agent, AgentRegister, AgentUpdate, AgentStatus

router = APIRouter(prefix="/api/agents", tags=["agents"])

# Agent heartbeat timeout: consider agent offline if last_seen is older than this
# Agent sends heartbeat every 10 seconds, so 30 seconds gives 3 missed heartbeats tolerance
HEARTBEAT_TIMEOUT_SECONDS = 30


def _should_be_offline(agent_db: AgentDB) -> bool:
    """Check if agent should be considered offline based on last_seen timestamp"""
    if not agent_db.last_seen:
        return True
    
    time_since_last_seen = datetime.now() - agent_db.last_seen
    return time_since_last_seen.total_seconds() > HEARTBEAT_TIMEOUT_SECONDS


async def _get_agent_status(agent_db: AgentDB, db: AsyncSession) -> AgentStatusEnum:
    """Get agent status, updating to OFFLINE if heartbeat timeout exceeded"""
    if _should_be_offline(agent_db):
        # Update status in database if it's still marked as ONLINE
        if agent_db.status == AgentStatusEnum.ONLINE:
            agent_db.status = AgentStatusEnum.OFFLINE
            await db.commit()
            await db.refresh(agent_db)
        return AgentStatusEnum.OFFLINE
    return agent_db.status


@router.get("", response_model=List[Agent])
async def get_agents(db: AsyncSession = Depends(get_db)):
    """List all agents"""
    result = await db.execute(select(AgentDB))
    agents_db = result.scalars().all()
    
    agents = []
    for agent_db in agents_db:
        # Check and update status based on last_seen
        current_status = await _get_agent_status(agent_db, db)
        
        agents.append(
            Agent(
                id=agent_db.id,
                name=agent_db.name,
                platform=agent_db.platform,
                version=agent_db.version,
                status=AgentStatus(current_status.value),
                last_seen=agent_db.last_seen,
                ip_address=agent_db.ip_address,
            )
        )
    
    return agents


@router.get("/{agent_id}", response_model=Agent)
async def get_agent(agent_id: str, db: AsyncSession = Depends(get_db)):
    """Get specific agent"""
    result = await db.execute(select(AgentDB).where(AgentDB.id == agent_id))
    agent_db = result.scalar_one_or_none()
    
    if not agent_db:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    # Check and update status based on last_seen
    current_status = await _get_agent_status(agent_db, db)
    
    return Agent(
        id=agent_db.id,
        name=agent_db.name,
        platform=agent_db.platform,
        version=agent_db.version,
        status=AgentStatus(current_status.value),
        last_seen=agent_db.last_seen,
        ip_address=agent_db.ip_address,
    )


@router.post("/register", response_model=Agent)
async def register_agent(agent_data: AgentRegister, db: AsyncSession = Depends(get_db)):
    """Register agent / heartbeat"""
    # Check if agent exists
    result = await db.execute(select(AgentDB).where(AgentDB.name == agent_data.name))
    existing_agent = result.scalar_one_or_none()
    
    if existing_agent:
        # Update existing agent
        existing_agent.platform = agent_data.platform
        existing_agent.version = agent_data.version
        existing_agent.status = AgentStatusEnum.ONLINE
        existing_agent.last_seen = datetime.now()
        existing_agent.ip_address = agent_data.ip_address
        await db.commit()
        await db.refresh(existing_agent)
        
        return Agent(
            id=existing_agent.id,
            name=existing_agent.name,
            platform=existing_agent.platform,
            version=existing_agent.version,
            status=AgentStatus(existing_agent.status.value),
            last_seen=existing_agent.last_seen,
            ip_address=existing_agent.ip_address,
        )
    else:
        # Create new agent
        agent_id = str(uuid.uuid4())
        agent_db = AgentDB(
            id=agent_id,
            name=agent_data.name,
            platform=agent_data.platform,
            version=agent_data.version,
            status=AgentStatusEnum.ONLINE,
            last_seen=datetime.now(),
            ip_address=agent_data.ip_address,
        )
        db.add(agent_db)
        await db.commit()
        await db.refresh(agent_db)
        
        return Agent(
            id=agent_db.id,
            name=agent_db.name,
            platform=agent_db.platform,
            version=agent_db.version,
            status=AgentStatus(agent_db.status.value),
            last_seen=agent_db.last_seen,
            ip_address=agent_db.ip_address,
        )


@router.put("/{agent_id}", response_model=Agent)
async def update_agent(
    agent_id: str,
    agent_data: AgentUpdate,
    db: AsyncSession = Depends(get_db)
):
    """Update an agent"""
    result = await db.execute(select(AgentDB).where(AgentDB.id == agent_id))
    agent_db = result.scalar_one_or_none()
    
    if not agent_db:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    # Update name if provided
    if agent_data.name is not None:
        agent_db.name = agent_data.name
    
    await db.commit()
    await db.refresh(agent_db)
    
    # Check and update status based on last_seen
    current_status = await _get_agent_status(agent_db, db)
    
    return Agent(
        id=agent_db.id,
        name=agent_db.name,
        platform=agent_db.platform,
        version=agent_db.version,
        status=AgentStatus(current_status.value),
        last_seen=agent_db.last_seen,
        ip_address=agent_db.ip_address,
    )


@router.delete("/{agent_id}")
async def delete_agent(agent_id: str, db: AsyncSession = Depends(get_db)):
    """Unregister agent"""
    result = await db.execute(select(AgentDB).where(AgentDB.id == agent_id))
    agent_db = result.scalar_one_or_none()
    
    if not agent_db:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    # Use delete statement for SQLAlchemy 2.0 async
    await db.execute(delete(AgentDB).where(AgentDB.id == agent_id))
    await db.commit()
    return {"message": "Agent deleted"}

