#!/usr/bin/env python3
"""
PyPolyCall Router Tests
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import asyncio
from modules.router import Router

async def test_router():
    """Test router functionality"""
    router = Router()
    
    # Test route registration
    def hello_handler(ctx):
        return {'message': f'Hello from {ctx.method} {ctx.path}'}
    
    router.add_route('/hello', hello_handler)
    
    # Test request handling
    result = await router.handle_request('/hello', 'GET')
    print("✅ Router test passed:", result)

if __name__ == "__main__":
    asyncio.run(test_router())
