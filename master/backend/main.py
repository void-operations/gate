"""
Master Backend - Agent Management Web Server
FastAPI-based RESTful API server
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from typing import List, Optional
from datetime import datetime
from pathlib import Path
import uvicorn
from models import (
    Agent, AgentRegister, AgentStatus,
    Release, ReleaseCreate,
    Deployment, DeploymentCreate, DeploymentStatus
)

app = FastAPI(title="Master Agent Manager", version="1.0.0")

# CORS configuration (for frontend connection)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, restrict to specific domains
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve static files (frontend build)
# Try different paths for different environments
frontend_dist_paths = [
    Path(__file__).parent.parent / "frontend" / "dist",
    Path("/app/frontend/dist"),  # Docker path
    Path("frontend/dist"),  # Alternative path
]

frontend_dist = None
for path in frontend_dist_paths:
    if path.exists():
        frontend_dist = path
        break

if frontend_dist:
    app.mount("/static", StaticFiles(directory=str(frontend_dist)), name="static")


# Temporary storage (should use database in production)
agents_db: dict[str, Agent] = {}
releases_db: dict[str, Release] = {}
deployments_db: dict[str, Deployment] = {}
deployment_history: list[Deployment] = []


# Root endpoint
@app.get("/")
async def root():
    """Root endpoint"""
    return {"message": "Master Agent Manager API", "version": "1.0.0"}


# ==================== Agent Management ====================

@app.get("/api/agents", response_model=List[Agent])
async def get_agents():
    """List all agents"""
    return list(agents_db.values())


@app.get("/api/agents/{agent_id}", response_model=Agent)
async def get_agent(agent_id: str):
    """Get specific agent"""
    if agent_id not in agents_db:
        raise HTTPException(status_code=404, detail="Agent not found")
    return agents_db[agent_id]


@app.post("/api/agents/register", response_model=Agent)
async def register_agent(agent_data: AgentRegister):
    """Register agent / heartbeat"""
    agent_id = f"{agent_data.platform}-{agent_data.name}"
    
    agent = Agent(
        id=agent_id,
        name=agent_data.name,
        platform=agent_data.platform,
        version=agent_data.version,
        status=AgentStatus.ONLINE,
        last_seen=datetime.now(),
        ip_address=agent_data.ip_address
    )
    
    agents_db[agent_id] = agent
    return agent


@app.delete("/api/agents/{agent_id}")
async def unregister_agent(agent_id: str):
    """Unregister agent"""
    if agent_id not in agents_db:
        raise HTTPException(status_code=404, detail="Agent not found")
    del agents_db[agent_id]
    return {"message": "Agent unregistered"}


# ==================== Release Management ====================

@app.get("/api/releases", response_model=List[Release])
async def get_releases():
    """List all releases"""
    return list(releases_db.values())


@app.get("/api/releases/{release_id}", response_model=Release)
async def get_release(release_id: str):
    """Get specific release"""
    if release_id not in releases_db:
        raise HTTPException(status_code=404, detail="Release not found")
    return releases_db[release_id]


@app.post("/api/releases", response_model=Release)
async def create_release(release_data: ReleaseCreate):
    """Create/add a release"""
    release_id = release_data.tag_name
    
    if release_id in releases_db:
        raise HTTPException(status_code=400, detail="Release already exists")
    
    release = Release(
        id=release_id,
        tag_name=release_data.tag_name,
        name=release_data.name,
        version=release_data.version,
        release_date=datetime.now(),
        download_url=release_data.download_url,
        description=release_data.description,
        assets=release_data.assets
    )
    
    releases_db[release_id] = release
    return release


@app.delete("/api/releases/{release_id}")
async def delete_release(release_id: str):
    """Delete/remove a release"""
    if release_id not in releases_db:
        raise HTTPException(status_code=404, detail="Release not found")
    del releases_db[release_id]
    return {"message": "Release deleted"}


# ==================== Deployment Management ====================

@app.get("/api/deployments", response_model=List[Deployment])
async def get_deployments():
    """List all deployments"""
    return list(deployments_db.values())


@app.get("/api/deployments/history", response_model=List[Deployment])
async def get_deployment_history(limit: int = 50):
    """Get deployment history"""
    return deployment_history[-limit:]


@app.get("/api/deployments/{deployment_id}", response_model=Deployment)
async def get_deployment(deployment_id: str):
    """Get specific deployment"""
    if deployment_id not in deployments_db:
        raise HTTPException(status_code=404, detail="Deployment not found")
    return deployments_db[deployment_id]


@app.post("/api/deployments", response_model=Deployment)
async def create_deployment(deployment_data: DeploymentCreate):
    """Create a deployment (can deploy multiple releases to an agent at once)"""
    # Validate agent exists
    if deployment_data.agent_id not in agents_db:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    agent = agents_db[deployment_data.agent_id]
    
    # Validate all releases exist
    release_tags = []
    for release_id in deployment_data.release_ids:
        if release_id not in releases_db:
            raise HTTPException(status_code=404, detail=f"Release {release_id} not found")
        release_tags.append(releases_db[release_id].tag_name)
    
    # Create deployment
    deployment_id = f"deploy-{agent.id}-{datetime.now().strftime('%Y%m%d%H%M%S')}"
    
    deployment = Deployment(
        id=deployment_id,
        agent_id=deployment_data.agent_id,
        agent_name=agent.name,
        release_ids=deployment_data.release_ids,
        release_tags=release_tags,
        status=DeploymentStatus.PENDING,
        created_at=datetime.now()
    )
    
    deployments_db[deployment_id] = deployment
    deployment_history.append(deployment)
    
    # TODO: Implement actual deployment logic
    # This would involve:
    # 1. Connecting to the agent
    # 2. Sending deployment commands
    # 3. Monitoring deployment progress
    # 4. Updating deployment status
    
    return deployment


# ==================== Health Check ====================

@app.get("/api/health")
async def health_check():
    """Health check"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "agents_count": len(agents_db),
        "releases_count": len(releases_db),
        "deployments_count": len(deployments_db)
    }


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True  # Development mode
    )
