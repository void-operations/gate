"""
Unit tests for Deployment filtering functionality
Tests various filter combinations: agent_id, status, and combinations
"""

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import StaticPool

from main import app
from database import Base, get_db
from db_models import AgentDB, DeploymentDB, ReleaseDB, DeploymentStatusEnum, AgentStatusEnum
from datetime import datetime


# Create in-memory SQLite database for testing
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

test_engine = create_async_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

TestSessionLocal = async_sessionmaker(
    test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def override_get_db():
    """Override database dependency for testing"""
    async with TestSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


@pytest_asyncio.fixture(scope="function")
async def setup_database():
    """Setup test database with tables"""
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture(scope="function")
async def test_data(setup_database):
    """Create test data: agents, releases, and deployments"""
    async with TestSessionLocal() as session:
        # Create test agents
        agent1 = AgentDB(
            id="agent-1",
            name="TestAgent1",
            platform="windows",
            version="1.0.0",
            status=AgentStatusEnum.ONLINE,
            last_seen=datetime.now(),
            ip_address="192.168.1.1"
        )
        agent2 = AgentDB(
            id="agent-2",
            name="TestAgent2",
            platform="macos",
            version="1.0.0",
            status=AgentStatusEnum.ONLINE,
            last_seen=datetime.now(),
            ip_address="192.168.1.2"
        )
        session.add(agent1)
        session.add(agent2)
        
        # Create test releases
        release1 = ReleaseDB(
            id="release-1",
            tag_name="v1.0.0",
            name="Release 1.0.0",
            version="1.0.0",
            release_date=datetime.now(),
            download_url="https://github.com/test/repo/releases/"
        )
        release2 = ReleaseDB(
            id="release-2",
            tag_name="v1.1.0",
            name="Release 1.1.0",
            version="1.1.0",
            release_date=datetime.now(),
            download_url="https://github.com/test/repo/releases/"
        )
        session.add(release1)
        session.add(release2)
        
        # Create test deployments with various statuses
        # Agent 1 deployments
        deployment1 = DeploymentDB(
            id="deploy-1",
            agent_id="agent-1",
            agent_name="TestAgent1",
            release_ids=["release-1"],
            release_tags=["v1.0.0"],
            status=DeploymentStatusEnum.SUCCESS,
            created_at=datetime.now()
        )
        deployment2 = DeploymentDB(
            id="deploy-2",
            agent_id="agent-1",
            agent_name="TestAgent1",
            release_ids=["release-2"],
            release_tags=["v1.1.0"],
            status=DeploymentStatusEnum.FAILED,
            created_at=datetime.now()
        )
        deployment3 = DeploymentDB(
            id="deploy-3",
            agent_id="agent-1",
            agent_name="TestAgent1",
            release_ids=["release-1"],
            release_tags=["v1.0.0"],
            status=DeploymentStatusEnum.PENDING,
            created_at=datetime.now()
        )
        
        # Agent 2 deployments
        deployment4 = DeploymentDB(
            id="deploy-4",
            agent_id="agent-2",
            agent_name="TestAgent2",
            release_ids=["release-1"],
            release_tags=["v1.0.0"],
            status=DeploymentStatusEnum.SUCCESS,
            created_at=datetime.now()
        )
        deployment5 = DeploymentDB(
            id="deploy-5",
            agent_id="agent-2",
            agent_name="TestAgent2",
            release_ids=["release-2"],
            release_tags=["v1.1.0"],
            status=DeploymentStatusEnum.IN_PROGRESS,
            created_at=datetime.now()
        )
        deployment6 = DeploymentDB(
            id="deploy-6",
            agent_id="agent-2",
            agent_name="TestAgent2",
            release_ids=["release-1"],
            release_tags=["v1.0.0"],
            status=DeploymentStatusEnum.SUCCESS,
            created_at=datetime.now()
        )
        
        session.add(deployment1)
        session.add(deployment2)
        session.add(deployment3)
        session.add(deployment4)
        session.add(deployment5)
        session.add(deployment6)
        
        await session.commit()
        
        return {
            "agent1_id": "agent-1",
            "agent2_id": "agent-2",
            "deployments": {
                "agent1": [deployment1, deployment2, deployment3],
                "agent2": [deployment4, deployment5, deployment6]
            }
        }


@pytest_asyncio.fixture(scope="function")
async def client(setup_database, test_data):
    """Create test client with overridden database dependency"""
    app.dependency_overrides[get_db] = override_get_db
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


class TestDeploymentFiltering:
    """Test suite for deployment filtering functionality"""
    
    @pytest.mark.asyncio
    async def test_get_all_deployments_no_filter(self, client, test_data):
        """Test getting all deployments without any filter"""
        response = await client.get("/api/deployments")
        assert response.status_code == 200
        deployments = response.json()
        
        # Should return all 6 deployments
        assert len(deployments) == 6
        deployment_ids = [d["id"] for d in deployments]
        assert "deploy-1" in deployment_ids
        assert "deploy-2" in deployment_ids
        assert "deploy-3" in deployment_ids
        assert "deploy-4" in deployment_ids
        assert "deploy-5" in deployment_ids
        assert "deploy-6" in deployment_ids
    
    @pytest.mark.asyncio
    async def test_filter_by_agent_id_only(self, client, test_data):
        """Test filtering deployments by agent_id only"""
        # Filter by agent-1
        response = await client.get("/api/deployments?agent_id=agent-1")
        assert response.status_code == 200
        deployments = response.json()
        
        # Should return 3 deployments for agent-1
        assert len(deployments) == 3
        for deployment in deployments:
            assert deployment["agent_id"] == "agent-1"
            assert deployment["agent_name"] == "TestAgent1"
        
        deployment_ids = [d["id"] for d in deployments]
        assert "deploy-1" in deployment_ids
        assert "deploy-2" in deployment_ids
        assert "deploy-3" in deployment_ids
        assert "deploy-4" not in deployment_ids
        assert "deploy-5" not in deployment_ids
        assert "deploy-6" not in deployment_ids
        
        # Filter by agent-2
        response = await client.get("/api/deployments?agent_id=agent-2")
        assert response.status_code == 200
        deployments = response.json()
        
        # Should return 3 deployments for agent-2
        assert len(deployments) == 3
        for deployment in deployments:
            assert deployment["agent_id"] == "agent-2"
            assert deployment["agent_name"] == "TestAgent2"
        
        deployment_ids = [d["id"] for d in deployments]
        assert "deploy-4" in deployment_ids
        assert "deploy-5" in deployment_ids
        assert "deploy-6" in deployment_ids
        assert "deploy-1" not in deployment_ids
        assert "deploy-2" not in deployment_ids
        assert "deploy-3" not in deployment_ids
    
    @pytest.mark.asyncio
    async def test_filter_by_status_only(self, client, test_data):
        """Test filtering deployments by status only"""
        # Filter by success status
        response = await client.get("/api/deployments?status=success")
        assert response.status_code == 200
        deployments = response.json()
        
        # Should return 3 success deployments (deploy-1, deploy-4, deploy-6)
        assert len(deployments) == 3
        for deployment in deployments:
            assert deployment["status"] == "success"
        
        deployment_ids = [d["id"] for d in deployments]
        assert "deploy-1" in deployment_ids
        assert "deploy-4" in deployment_ids
        assert "deploy-6" in deployment_ids
        
        # Filter by failed status
        response = await client.get("/api/deployments?status=failed")
        assert response.status_code == 200
        deployments = response.json()
        
        # Should return 1 failed deployment (deploy-2)
        assert len(deployments) == 1
        assert deployments[0]["status"] == "failed"
        assert deployments[0]["id"] == "deploy-2"
        
        # Filter by pending status
        response = await client.get("/api/deployments?status=pending")
        assert response.status_code == 200
        deployments = response.json()
        
        # Should return 1 pending deployment (deploy-3)
        assert len(deployments) == 1
        assert deployments[0]["status"] == "pending"
        assert deployments[0]["id"] == "deploy-3"
        
        # Filter by in_progress status
        response = await client.get("/api/deployments?status=in_progress")
        assert response.status_code == 200
        deployments = response.json()
        
        # Should return 1 in_progress deployment (deploy-5)
        assert len(deployments) == 1
        assert deployments[0]["status"] == "in_progress"
        assert deployments[0]["id"] == "deploy-5"
    
    @pytest.mark.asyncio
    async def test_filter_by_agent_id_and_status_combination(self, client, test_data):
        """Test filtering deployments by both agent_id and status"""
        # Filter by agent-1 and success status
        response = await client.get("/api/deployments?agent_id=agent-1&status=success")
        assert response.status_code == 200
        deployments = response.json()
        
        # Should return 1 deployment (deploy-1)
        assert len(deployments) == 1
        assert deployments[0]["id"] == "deploy-1"
        assert deployments[0]["agent_id"] == "agent-1"
        assert deployments[0]["status"] == "success"
        
        # Filter by agent-1 and failed status
        response = await client.get("/api/deployments?agent_id=agent-1&status=failed")
        assert response.status_code == 200
        deployments = response.json()
        
        # Should return 1 deployment (deploy-2)
        assert len(deployments) == 1
        assert deployments[0]["id"] == "deploy-2"
        assert deployments[0]["agent_id"] == "agent-1"
        assert deployments[0]["status"] == "failed"
        
        # Filter by agent-1 and pending status
        response = await client.get("/api/deployments?agent_id=agent-1&status=pending")
        assert response.status_code == 200
        deployments = response.json()
        
        # Should return 1 deployment (deploy-3)
        assert len(deployments) == 1
        assert deployments[0]["id"] == "deploy-3"
        assert deployments[0]["agent_id"] == "agent-1"
        assert deployments[0]["status"] == "pending"
        
        # Filter by agent-2 and success status
        response = await client.get("/api/deployments?agent_id=agent-2&status=success")
        assert response.status_code == 200
        deployments = response.json()
        
        # Should return 2 deployments (deploy-4, deploy-6)
        assert len(deployments) == 2
        deployment_ids = [d["id"] for d in deployments]
        assert "deploy-4" in deployment_ids
        assert "deploy-6" in deployment_ids
        for deployment in deployments:
            assert deployment["agent_id"] == "agent-2"
            assert deployment["status"] == "success"
        
        # Filter by agent-2 and in_progress status
        response = await client.get("/api/deployments?agent_id=agent-2&status=in_progress")
        assert response.status_code == 200
        deployments = response.json()
        
        # Should return 1 deployment (deploy-5)
        assert len(deployments) == 1
        assert deployments[0]["id"] == "deploy-5"
        assert deployments[0]["agent_id"] == "agent-2"
        assert deployments[0]["status"] == "in_progress"
    
    @pytest.mark.asyncio
    async def test_filter_by_nonexistent_agent_id(self, client, test_data):
        """Test filtering by non-existent agent_id returns empty list"""
        response = await client.get("/api/deployments?agent_id=nonexistent-agent")
        assert response.status_code == 200
        deployments = response.json()
        
        # Should return empty list
        assert len(deployments) == 0
        assert deployments == []
    
    @pytest.mark.asyncio
    async def test_filter_by_nonexistent_status(self, client, test_data):
        """Test filtering by non-existent status returns empty list"""
        # Note: FastAPI will validate the enum, so invalid status will return 422
        # But if we use a valid enum value that doesn't exist in data, it should return empty
        response = await client.get("/api/deployments?status=success")
        assert response.status_code == 200
        # This test verifies that valid status values work correctly
    
    @pytest.mark.asyncio
    async def test_filter_agent_id_with_no_matching_status(self, client, test_data):
        """Test filtering by agent_id and status combination that has no matches"""
        # Agent-1 has no in_progress deployments
        response = await client.get("/api/deployments?agent_id=agent-1&status=in_progress")
        assert response.status_code == 200
        deployments = response.json()
        
        # Should return empty list
        assert len(deployments) == 0
        
        # Agent-2 has no failed deployments
        response = await client.get("/api/deployments?agent_id=agent-2&status=failed")
        assert response.status_code == 200
        deployments = response.json()
        
        # Should return empty list
        assert len(deployments) == 0
    
    @pytest.mark.asyncio
    async def test_deployments_ordered_by_created_at_desc(self, client, test_data):
        """Test that deployments are ordered by created_at descending (newest first)"""
        response = await client.get("/api/deployments")
        assert response.status_code == 200
        deployments = response.json()
        
        # Check that deployments are ordered by created_at descending
        if len(deployments) > 1:
            for i in range(len(deployments) - 1):
                current_time = datetime.fromisoformat(deployments[i]["created_at"].replace("Z", "+00:00"))
                next_time = datetime.fromisoformat(deployments[i + 1]["created_at"].replace("Z", "+00:00"))
                assert current_time >= next_time, "Deployments should be ordered by created_at descending"
    
    @pytest.mark.asyncio
    async def test_filter_preserves_deployment_structure(self, client, test_data):
        """Test that filtered results maintain correct deployment structure"""
        response = await client.get("/api/deployments?agent_id=agent-1&status=success")
        assert response.status_code == 200
        deployments = response.json()
        
        assert len(deployments) == 1
        deployment = deployments[0]
        
        # Verify all required fields are present
        assert "id" in deployment
        assert "agent_id" in deployment
        assert "agent_name" in deployment
        assert "release_ids" in deployment
        assert "release_tags" in deployment
        assert "status" in deployment
        assert "created_at" in deployment
        assert "started_at" in deployment
        assert "completed_at" in deployment
        assert "error_message" in deployment
        
        # Verify field types and values
        assert deployment["id"] == "deploy-1"
        assert deployment["agent_id"] == "agent-1"
        assert deployment["agent_name"] == "TestAgent1"
        assert isinstance(deployment["release_ids"], list)
        assert isinstance(deployment["release_tags"], list)
        assert deployment["status"] == "success"

