"""
Example server for PyPolyCall.

This example demonstrates how to create a simple server using PyPolyCall.
"""

import asyncio
import json
import logging
from typing import Dict, Any, List

from pypolycall import create_client, PolyCallException
from pypolycall.client.router import Router
from pypolycall.network.endpoint import EndpointType
from pypolycall.core.context import CoreContext
from pypolycall.protocol.protocol_handler import ProtocolHandler

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger("pypolycall.server_example")


class BookStore:
    """Simple book data store."""
    
    def __init__(self):
        """Initialize the book store with some sample data."""
        self.books: Dict[str, Dict[str, Any]] = {}
        
        # Add sample books
        self._add_sample_books()
    
    def _add_sample_books(self):
        """Add some sample books."""
        self.add_book({
            "title": "The Great Gatsby",
            "author": "F. Scott Fitzgerald",
            "year": 1925,
            "genre": "Novel"
        })
        
        self.add_book({
            "title": "To Kill a Mockingbird",
            "author": "Harper Lee",
            "year": 1960,
            "genre": "Novel"
        })
        
        self.add_book({
            "title": "1984",
            "author": "George Orwell",
            "year": 1949,
            "genre": "Dystopian"
        })
    
    def add_book(self, book_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Add a book to the store.
        
        Args:
            book_data: Book data
        
        Returns:
            Added book with ID
        """
        # Generate ID
        book_id = str(len(self.books) + 1)
        
        # Add ID to book data
        book = {
            "id": book_id,
            **book_data,
            "created_at": asyncio.get_event_loop().time()
        }
        
        # Store book
        self.books[book_id] = book
        
        return book
    
    def get_book(self, book_id: str) -> Dict[str, Any]:
        """
        Get a book by ID.
        
        Args:
            book_id: Book ID
        
        Returns:
            Book data
        
        Raises:
            KeyError: If book not found
        """
        if book_id not in self.books:
            raise KeyError(f"Book with ID {book_id} not found")
        
        return self.books[book_id]
    
    def get_all_books(self) -> List[Dict[str, Any]]:
        """
        Get all books.
        
        Returns:
            List of books
        """
        return list(self.books.values())
    
    def update_book(self, book_id: str, book_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update a book.
        
        Args:
            book_id: Book ID
            book_data: New book data
        
        Returns:
            Updated book
        
        Raises:
            KeyError: If book not found
        """
        if book_id not in self.books:
            raise KeyError(f"Book with ID {book_id} not found")
        
        # Update book
        self.books[book_id].update(book_data)
        self.books[book_id]["updated_at"] = asyncio.get_event_loop().time()
        
        return self.books[book_id]
    
    def delete_book(self, book_id: str) -> None:
        """
        Delete a book.
        
        Args:
            book_id: Book ID
        
        Raises:
            KeyError: If book not found
        """
        if book_id not in self.books:
            raise KeyError(f"Book with ID {book_id} not found")
        
        del self.books[book_id]


class PolyCallServer:
    """Simple PolyCall server."""
    
    def __init__(self, host: str = "localhost", port: int = 8084):
        """
        Initialize the server.
        
        Args:
            host: Server host
            port: Server port
        """
        self.host = host
        self.port = port
        
        # Create bookstore
        self.bookstore = BookStore()
        
        # Create client
        self.core_ctx = CoreContext("polycall_server")
        self.protocol = ProtocolHandler(self.core_ctx)
        self.client = create_client({
            "host": host,
            "port": port,
            "endpoint_type": EndpointType.SERVER
        })
        
        # Create router
        self.router = self.client.router
        
        # Register routes
        self._register_routes()
    
    def _register_routes(self):
        """Register routes for the server."""
        # Book routes
        self.router.add_route("/books", {
            "GET": self._get_books,
            "POST": self._create_book
        })
        
        self.router.add_route("/books/{id}", {
            "GET": self._get_book,
            "PUT": self._update_book,
            "DELETE": self._delete_book
        })
        
        # Status route
        self.router.get("/status")(self._get_status)
        
        # Add middleware
        self.router.use(self.router.logging_middleware())
        self.router.use(self.router.error_handler())
    
    async def _get_books(self, ctx):
        """Get all books."""
        books = self.bookstore.get_all_books()
        return {
            "success": True,
            "data": books,
            "count": len(books)
        }
    
    async def _create_book(self, ctx):
        """Create a new book."""
        try:
            book_data = ctx["data"]
            
            # Validate input
            if "title" not in book_data or "author" not in book_data:
                return {
                    "success": False,
                    "error": "Title and author are required"
                }
            
            # Add book
            book = self.bookstore.add_book(book_data)
            
            return {
                "success": True,
                "data": book
            }
            
        except Exception as e:
            logger.error(f"Error creating book: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _get_book(self, ctx):
        """Get a book by ID."""
        try:
            book_id = ctx["params"]["id"]
            book = self.bookstore.get_book(book_id)
            
            return {
                "success": True,
                "data": book
            }
            
        except KeyError:
            return {
                "success": False,
                "error": f"Book with ID {ctx['params']['id']} not found"
            }
        except Exception as e:
            logger.error(f"Error getting book: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _update_book(self, ctx):
        """Update a book."""
        try:
            book_id = ctx["params"]["id"]
            book_data = ctx["data"]
            
            # Update book
            book = self.bookstore.update_book(book_id, book_data)
            
            return {
                "success": True,
                "data": book
            }
            
        except KeyError:
            return {
                "success": False,
                "error": f"Book with ID {ctx['params']['id']} not found"
            }
        except Exception as e:
            logger.error(f"Error updating book: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _delete_book(self, ctx):
        """Delete a book."""
        try:
            book_id = ctx["params"]["id"]
            
            # Delete book
            self.bookstore.delete_book(book_id)
            
            return {
                "success": True,
                "message": f"Book with ID {book_id} deleted"
            }
            
        except KeyError:
            return {
                "success": False,
                "error": f"Book with ID {ctx['params']['id']} not found"
            }
        except Exception as e:
            logger.error(f"Error deleting book: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _get_status(self, ctx):
        """Get server status."""
        return {
            "success": True,
            "status": "running",
            "version": "0.1.0",
            "book_count": len(self.bookstore.books),
            "uptime": asyncio.get_event_loop().time()
        }
    
    async def start(self):
        """Start the server."""
        logger.info(f"Starting PolyCall server on {self.host}:{self.port}...")
        
        # Set up event handlers
        self.client.endpoint.on('client_connected', 
                               lambda addr: logger.info(f"Client connected: {addr}"))
        self.client.endpoint.on('client_disconnected', 
                               lambda addr: logger.info(f"Client disconnected: {addr}"))
        self.client.endpoint.on('error', 
                               lambda error: logger.error(f"Network error: {error}"))
        
        # Start server
        success = await self.client.endpoint.listen()
        
        if success:
            logger.info(f"Server started successfully on {self.host}:{self.port}")
            logger.info("Routes:")
            self.router.print_routes()
        else:
            logger.error("Failed to start server")
            return False
        
        return True


async def run_server():
    """Run the server."""
    server = PolyCallServer()
    
    if await server.start():
        # Wait forever
        try:
            while True:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            logger.info("Server shutdown requested")
        finally:
            # Stop server
            await server.client.endpoint.stop()
            logger.info("Server stopped")


if __name__ == "__main__":
    # Run the server
    asyncio.run(run_server())