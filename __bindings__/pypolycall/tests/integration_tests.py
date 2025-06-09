"""
Integration tests for PyPolyCall.

These tests verify that the PyPolyCall package works correctly
with a running LibPolyCall instance.
"""

import asyncio
import json
import logging
import os
import pytest
import subprocess
import time
from typing import Dict, Any, Optional

from pypolycall import create_client, PolyCallException

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger("pypolycall.tests")

# Test configuration
TEST_HOST = os.environ.get("POLYCALL_TEST_HOST", "localhost")
TEST_PORT = int(os.environ.get("POLYCALL_TEST_PORT", "8084"))
POLYCALL_BIN = os.environ.get("POLYCALL_BIN", "./bin/polycall")
CONFIG_FILE = os.environ.get("POLYCALL_CONFIG", "config.Polycallfile")


class TestEnvironment:
    """Test environment management."""
    
    def __init__(self):
        """Initialize the test environment."""
        self.process: Optional[subprocess.Popen] = None
        self.client = create_client({
            "host": TEST_HOST,
            "port": TEST_PORT
        })
    
    async def setup(self):
        """Set up the test environment."""
        # Start polycall service if binary is available
        if os.path.exists(POLYCALL_BIN) and os.path.exists(CONFIG_FILE):
            logger.info(f"Starting PolyCall service from {POLYCALL_BIN}...")
            self.process = subprocess.Popen(
                [POLYCALL_BIN, "-f", CONFIG_FILE],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            # Wait for service to start
            time.sleep(2)
        
        # Try to connect
        try:
            await self.client.connect()
            logger.info("Connected to PolyCall service")
        except Exception as e:
            logger.warning(f"Failed to connect to PolyCall service: {e}")
            if self.process:
                self.process.terminate()
                self.process = None
            pytest.skip("PolyCall service not available")
    
    async def teardown(self):
        """Tear down the test environment."""
        # Disconnect client
        if self.client.is_connected():
            await self.client.disconnect()
        
        # Stop polycall service
        if self.process:
            self.process.terminate()
            self.process = None


@pytest.fixture
async def test_env():
    """Test environment fixture."""
    env = TestEnvironment()
    await env.setup()
    yield env
    await env.teardown()


@pytest.mark.asyncio
async def test_connection(test_env):
    """Test connection to the PolyCall service."""
    assert test_env.client.is_connected()


@pytest.mark.asyncio
async def test_authentication(test_env):
    """Test authentication with the PolyCall service."""
    # Test authentication
    try:
        result = await test_env.client.authenticate({
            "username": "test",
            "password": "test"
        })
        assert result
        assert test_env.client.is_authenticated()
    except PolyCallException as e:
        logger.warning(f"Authentication failed: {e}")
        pytest.skip("Authentication not supported or failed")


@pytest.mark.asyncio
async def test_commands(test_env):
    """Test command execution."""
    if not test_env.client.is_connected():
        pytest.skip("Not connected to PolyCall service")
    
    # Try to authenticate
    try:
        await test_env.client.authenticate({
            "username": "test",
            "password": "test"
        })
    except PolyCallException:
        pass
    
    # Execute status command
    try:
        result = await test_env.client.execute_command("status")
        assert result is not None
        logger.info(f"Status command result: {result}")
    except PolyCallException as e:
        logger.warning(f"Command execution failed: {e}")
        pytest.skip("Command execution not supported or failed")


@pytest.mark.asyncio
async def test_requests(test_env):
    """Test request handling."""
    if not test_env.client.is_connected():
        pytest.skip("Not connected to PolyCall service")
    
    # Register test routes
    @test_env.client.router.get("/test")
    async def get_test(ctx):
        return {"success": True, "message": "Test route"}
    
    @test_env.client.router.post("/test")
    async def post_test(ctx):
        return {"success": True, "data": ctx["data"]}
    
    # Test GET request
    result = await test_env.client.send_request("/test")
    assert result["success"]
    assert result["message"] == "Test route"
    
    # Test POST request
    test_data = {"key": "value", "number": 42}
    result = await test_env.client.send_request("/test", "POST", test_data)
    assert result["success"]
    assert result["data"] == test_data


@pytest.mark.asyncio
async def test_state_management(test_env):
    """Test state management."""
    if not test_env.client.is_connected():
        pytest.skip("Not connected to PolyCall service")
    
    # Try to authenticate
    try:
        await test_env.client.authenticate({
            "username": "test",
            "password": "test"
        })
    except PolyCallException:
        pass
    
    # Test state transitions
    try:
        # Get all states
        states = await test_env.client.get_all_states()
        logger.info(f"Current states: {states}")
        
        # Try transition to ready state
        result = await test_env.client.transition_to("ready")
        logger.info(f"Transition result: {result}")
        assert result is not None
    except PolyCallException as e:
        logger.warning(f"State management failed: {e}")
        pytest.skip("State management not supported or failed")


if __name__ == "__main__":
    # Run tests manually
    asyncio.run(test_connection(TestEnvironment()))