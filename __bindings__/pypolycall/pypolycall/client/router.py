"""
Router implementation for PyPolyCall.

This module provides request routing functionality for the PyPolyCall client,
allowing it to handle API requests in a structured way.
"""

import asyncio
import re
import logging
import json
import urllib.parse
from typing import Dict, List, Optional, Union, Any, Callable, Tuple, Pattern, Match

from ..core.types import CoreError
from ..core.error import set_error, ErrorSource, PolyCallException

# Configure logger
logger = logging.getLogger("pypolycall.router")

# Type aliases
RouteHandler = Callable[[Dict[str, Any]], Any]
MiddlewareFunc = Callable[[Dict[str, Any], Callable[[Dict[str, Any]], Any]], Any]


class Router:
    """Request router for PyPolyCall."""
    
    def __init__(self):
        """Initialize the router."""
        self.routes: Dict[str, Dict[str, RouteHandler]] = {}
        self.param_routes: List[Tuple[Pattern[str], Dict[str, RouteHandler]]] = []
        self.middleware: List[MiddlewareFunc] = []
    
    def add_route(
        self,
        path: str,
        handler: Union[RouteHandler, Dict[str, RouteHandler]]
    ) -> None:
        """
        Add a route to the router.
        
        Args:
            path: Route path
            handler: Handler function or dict of method-specific handlers
        """
        # Normalize path
        path = self._normalize_path(path)
        
        # Check if path contains parameters
        if '{' in path or ':' in path:
            # Convert to regex pattern
            pattern = self._path_to_pattern(path)
            
            # Create handler dict if needed
            if callable(handler):
                handler_dict = {'GET': handler, 'POST': handler}
            else:
                handler_dict = {method.upper(): h for method, h in handler.items()}
            
            # Add to param routes
            self.param_routes.append((pattern, handler_dict))
            
        else:
            # Static route
            if callable(handler):
                self.routes[path] = {'GET': handler, 'POST': handler}
            else:
                self.routes[path] = {method.upper(): h for method, h in handler.items()}
    
    def _path_to_pattern(self, path: str) -> Pattern[str]:
        """
        Convert a path with parameters to a regex pattern.
        
        Args:
            path: Path with parameters
        
        Returns:
            Regex pattern for the path
        """
        # Replace {param} or :param with named capture groups
        path_regex = re.sub(r'{([^}]+)}', r'(?P<\1>[^/]+)', path)
        path_regex = re.sub(r':([^/]+)', r'(?P<\1>[^/]+)', path_regex)
        
        # Add start/end anchors
        path_regex = f'^{path_regex}$'
        
        return re.compile(path_regex)
    
    def _extract_params(self, path: str, pattern: Pattern[str]) -> Dict[str, str]:
        """
        Extract parameters from a path using a regex pattern.
        
        Args:
            path: Request path
            pattern: Regex pattern
        
        Returns:
            Dict of parameters
        """
        match = pattern.match(path)
        if not match:
            return {}
        
        return match.groupdict()
    
    def _normalize_path(self, path: str) -> str:
        """
        Normalize a path.
        
        Args:
            path: Path to normalize
        
        Returns:
            Normalized path
        """
        # Add leading slash if missing
        if not path.startswith('/'):
            path = f'/{path}'
        
        # Remove trailing slash unless it's the root path
        if path != '/' and path.endswith('/'):
            path = path[:-1]
        
        return path
    
    def _parse_query_string(self, path: str) -> Dict[str, str]:
        """
        Parse query string from a path.
        
        Args:
            path: Path with query string
        
        Returns:
            Dict of query parameters
        """
        try:
            # Split path and query string
            if '?' in path:
                path, query = path.split('?', 1)
                return dict(urllib.parse.parse_qsl(query))
            
            return {}
            
        except Exception as e:
            logger.warning(f"Failed to parse query string: {e}")
            return {}
    
    def use(self, middleware: MiddlewareFunc) -> None:
        """
        Add middleware to the router.
        
        Args:
            middleware: Middleware function
        """
        self.middleware.append(middleware)
    
    async def handle_request(
        self,
        path: str,
        method: str = 'GET',
        data: Optional[Dict[str, Any]] = None
    ) -> Any:
        """
        Handle a request.
        
        Args:
            path: Request path
            method: Request method
            data: Request data
        
        Returns:
            Response data
        
        Raises:
            PolyCallException: If route not found or method not allowed
        """
        # Normalize method
        method = method.upper()
        
        # Parse query string
        query_params = self._parse_query_string(path)
        
        # Remove query string from path
        if '?' in path:
            path = path.split('?', 1)[0]
        
        # Normalize path
        path = self._normalize_path(path)
        
        # Create context
        context = {
            'path': path,
            'method': method,
            'data': data or {},
            'params': {},
            'query': query_params,
            'response': None,
            'error': None
        }
        
        # Find route
        route_handler = None
        
        # Try static routes first
        if path in self.routes:
            handlers = self.routes[path]
            if method in handlers:
                route_handler = handlers[method]
            elif 'ANY' in handlers:
                route_handler = handlers['ANY']
        
        # Try parameter routes if no match
        if not route_handler:
            for pattern, handlers in self.param_routes:
                match = pattern.match(path)
                if match:
                    if method in handlers:
                        route_handler = handlers[method]
                        context['params'] = match.groupdict()
                    elif 'ANY' in handlers:
                        route_handler = handlers['ANY']
                        context['params'] = match.groupdict()
                    break
        
        if not route_handler:
            # Check if route exists but method not allowed
            if path in self.routes:
                raise PolyCallException(
                    CoreError.UNSUPPORTED_OPERATION,
                    f"Method {method} not allowed for {path}"
                )
            
            # Route not found
            raise PolyCallException(
                CoreError.NOT_FOUND,
                f"Route {path} not found"
            )
        
        # Apply middleware
        if self.middleware:
            # Chain middleware
            async def execute_middleware(index: int, ctx: Dict[str, Any]) -> Any:
                if index >= len(self.middleware):
                    return await route_handler(ctx)
                
                middleware_func = self.middleware[index]
                
                # Define next function to call next middleware
                async def next_middleware(ctx: Dict[str, Any]) -> Any:
                    return await execute_middleware(index + 1, ctx)
                
                # Call middleware
                return await middleware_func(ctx, next_middleware)
            
            # Start middleware chain
            return await execute_middleware(0, context)
        
        # No middleware, call handler directly
        return await asyncio.coroutine(route_handler)(context)
    
    def route(self, path: str, methods: Optional[List[str]] = None) -> Callable[[RouteHandler], RouteHandler]:
        """
        Decorator for adding routes.
        
        Args:
            path: Route path
            methods: HTTP methods to handle
        
        Returns:
            Decorator function
        """
        if methods is None:
            methods = ['GET']
        
        def decorator(handler: RouteHandler) -> RouteHandler:
            # Create method dict
            method_dict = {method.upper(): handler for method in methods}
            
            # Add route
            self.add_route(path, method_dict)
            
            return handler
        
        return decorator
    
    def get(self, path: str) -> Callable[[RouteHandler], RouteHandler]:
        """
        Decorator for adding GET routes.
        
        Args:
            path: Route path
        
        Returns:
            Decorator function
        """
        return self.route(path, ['GET'])
    
    def post(self, path: str) -> Callable[[RouteHandler], RouteHandler]:
        """
        Decorator for adding POST routes.
        
        Args:
            path: Route path
        
        Returns:
            Decorator function
        """
        return self.route(path, ['POST'])
    
    def put(self, path: str) -> Callable[[RouteHandler], RouteHandler]:
        """
        Decorator for adding PUT routes.
        
        Args:
            path: Route path
        
        Returns:
            Decorator function
        """
        return self.route(path, ['PUT'])
    
    def delete(self, path: str) -> Callable[[RouteHandler], RouteHandler]:
        """
        Decorator for adding DELETE routes.
        
        Args:
            path: Route path
        
        Returns:
            Decorator function
        """
        return self.route(path, ['DELETE'])
    
    def any(self, path: str) -> Callable[[RouteHandler], RouteHandler]:
        """
        Decorator for adding routes that handle any method.
        
        Args:
            path: Route path
        
        Returns:
            Decorator function
        """
        return self.route(path, ['GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'OPTIONS', 'HEAD'])
    
    def logging_middleware(self) -> MiddlewareFunc:
        """
        Create a logging middleware.
        
        Returns:
            Middleware function
        """
        async def middleware(ctx: Dict[str, Any], next_middleware: Callable[[Dict[str, Any]], Any]) -> Any:
            logger.info(f"Request: {ctx['method']} {ctx['path']}")
            
            try:
                # Call next middleware or handler
                result = await next_middleware(ctx)
                
                logger.info(f"Response for {ctx['method']} {ctx['path']}: Success")
                return result
                
            except Exception as e:
                logger.error(f"Response for {ctx['method']} {ctx['path']}: Error - {str(e)}")
                raise
        
        return middleware
    
    def error_handler(self) -> MiddlewareFunc:
        """
        Create an error handling middleware.
        
        Returns:
            Middleware function
        """
        async def middleware(ctx: Dict[str, Any], next_middleware: Callable[[Dict[str, Any]], Any]) -> Any:
            try:
                # Call next middleware or handler
                return await next_middleware(ctx)
                
            except PolyCallException as e:
                # Handle known exceptions
                ctx['error'] = {
                    'code': e.code,
                    'message': e.message
                }
                
                logger.error(f"PolyCall error: {e.message}")
                
                return {
                    'error': True,
                    'code': e.code,
                    'message': e.message
                }
                
            except Exception as e:
                # Handle unknown exceptions
                ctx['error'] = {
                    'code': CoreError.INTERNAL,
                    'message': str(e)
                }
                
                logger.error(f"Internal error: {str(e)}")
                
                return {
                    'error': True,
                    'code': CoreError.INTERNAL,
                    'message': str(e)
                }
        
        return middleware
    
    def print_routes(self) -> None:
        """Print all registered routes."""
        print("\nRegistered Routes:")
        
        # Print static routes
        for path, handlers in self.routes.items():
            methods = ", ".join(handlers.keys())
            print(f"{methods} {path}")
        
        # Print parameter routes
        for pattern, handlers in self.param_routes:
            methods = ", ".join(handlers.keys())
            print(f"{methods} {pattern.pattern}")
        
        print("")