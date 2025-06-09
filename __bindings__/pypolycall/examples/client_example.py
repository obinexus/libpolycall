"""
Example client for PyPolyCall.

This example demonstrates basic usage of the PyPolyCall client.
"""

import asyncio
import json
import logging
from typing import Dict, Any

from pypolycall import create_client, PolyCallException

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger("pypolycall.example")


async def test_connection(client):
    """Test connection to the PolyCall server."""
    logger.info("Testing connection...")
    
    try:
        await client.connect()
        logger.info("Connection successful!")
        return True
    except Exception as e:
        logger.error(f"Connection failed: {e}")
        return False


async def test_authentication(client):
    """Test authentication with the PolyCall server."""
    logger.info("Testing authentication...")
    
    try:
        result = await client.authenticate({
            "username": "test",
            "password": "test"
        })
        
        if result:
            logger.info("Authentication successful!")
        else:
            logger.warning("Authentication failed!")
        
        return result
    except Exception as e:
        logger.error(f"Authentication error: {e}")
        return False


async def test_command(client, command: str, data: Dict[str, Any] = None):
    """Test executing a command on the PolyCall server."""
    logger.info(f"Testing command: {command}")
    
    try:
        result = await client.execute_command(command, data or {})
        logger.info(f"Command result: {json.dumps(result, indent=2)}")
        return result
    except Exception as e:
        logger.error(f"Command execution failed: {e}")
        return None


async def test_state_management(client):
    """Test state management features."""
    logger.info("Testing state management...")
    
    try:
        # Get all states
        states = await client.get_all_states()
        logger.info(f"Current states: {json.dumps(states, indent=2)}")
        
        # Transition to 'ready' state
        result = await client.transition_to('ready')
        logger.info(f"Transition result: {json.dumps(result, indent=2)}")
        
        return result
    except Exception as e:
        logger.error(f"State management failed: {e}")
        return None


async def run_example():
    """Run the complete example."""
    # Create client
    client = create_client({
        "host": "localhost",
        "port": 8084,
        "reconnect": True,
        "max_retries": 3
    })
    
    # Set up event handlers
    client.on('connected', lambda: logger.info("Connected event received"))
    client.on('disconnected', lambda: logger.info("Disconnected event received"))
    client.on('authenticated', lambda: logger.info("Authenticated event received"))
    client.on('error', lambda error: logger.error(f"Error event received: {error}"))
    client.on('state:changed', lambda data: logger.info(f"State changed: {data}"))
    
    try:
        # Test connection
        if not await test_connection(client):
            return
        
        # Test authentication
        if not await test_authentication(client):
            return
        
        # Run tests
        await test_command(client, "status")
        await test_command(client, "get_config", {"section": "network"})
        await test_state_management(client)
        
        # Disconnect
        logger.info("Disconnecting...")
        await client.disconnect()
        logger.info("Disconnected!")
        
    except PolyCallException as e:
        logger.error(f"PolyCall error: {e}")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")


if __name__ == "__main__":
    # Run the example
    asyncio.run(run_example())