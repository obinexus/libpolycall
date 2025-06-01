# router.py - PyPolyCall Router Implementation
from urllib.parse import urlparse, parse_qs
from typing import Dict, Any, Callable, Set, Optional
import asyncio
from dataclasses import dataclass


@dataclass
class RouteContext:
    """Request context for route handlers"""
    path: str
    method: str
    data: Dict[str, Any]
    params: Dict[str, Any]
    query: Dict[str, Any]


class Router:
    """PyPolyCall Router - Python equivalent of Router.js"""
    
    def __init__(self):
        self.routes: Dict[str, Dict] = {}
        
    def add_route(self, path: str, handlers):
        """Register a route with method-specific handlers"""
        
        # If handlers is a function, treat it as a generic handler
        if callable(handlers):
            self.routes[path] = {
                'handler': handlers,
                'methods': {'GET', 'POST'}  # Default methods
            }
            return
            
        # If handlers is a dict with method-specific handlers
        if isinstance(handlers, dict):
            supported_methods = set(method.upper() for method in handlers.keys())
            
            async def route_handler(ctx: RouteContext):
                method = ctx.method.upper()
                method_handler = handlers.get(method)
                
                if not method_handler:
                    raise ValueError(f"Method {method} not allowed")
                    
                return await method_handler(ctx) if asyncio.iscoroutinefunction(method_handler) else method_handler(ctx)
            
            self.routes[path] = {
                'handler': route_handler,
                'methods': supported_methods
            }
    
    def find_route(self, path: str) -> Optional[Dict]:
        """Find a matching route for the given path"""
        # Normalize the path
        path = self.normalize_path(path)
        
        # Try direct match first
        if path in self.routes:
            return self.routes[path]
            
        # If no direct match, return None
        return None
    
    async def handle_request(self, path: str, method: str, data: Dict[str, Any] = None) -> Any:
        """Handle an incoming request"""
        if data is None:
            data = {}
            
        route = self.find_route(path)
        
        if not route:
            raise ValueError(f"No route found for: {path}")
            
        if method.upper() not in route['methods']:
            raise ValueError(f"Method {method} not allowed for {path}")
        
        context = RouteContext(
            path=path,
            method=method.upper(),
            data=data,
            params={},
            query=self.parse_query_string(path)
        )
        
        try:
            # Execute the route handler
            handler = route['handler']
            if callable(handler):
                if asyncio.iscoroutinefunction(handler):
                    return await handler(context)
                else:
                    return handler(context)
            else:
                raise ValueError('Invalid route handler')
        except Exception as error:
            # Emit error event (would need event system)
            raise error
    
    def parse_query_string(self, path: str) -> Dict[str, Any]:
        """Parse query string from path"""
        try:
            parsed_url = urlparse(path)
            query_params = parse_qs(parsed_url.query)
            
            # Flatten single-item lists
            params = {}
            for key, value_list in query_params.items():
                params[key] = value_list[0] if len(value_list) == 1 else value_list
                
            return params
        except:
            return {}
    
    def normalize_path(self, path: str) -> str:
        """Normalize a path string"""
        if not path.startswith('/'):
            path = '/' + path
            
        # Remove trailing slash unless it's the root path
        if len(path) > 1 and path.endswith('/'):
            path = path[:-1]
            
        return path
    
    def print_routes(self):
        """Print registered routes (for debugging)"""
        print('\nRegistered Routes:')
        for path, route in self.routes.items():
            methods = ','.join(route['methods']) print(f"{methods} {path}")
