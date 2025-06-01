const http = require('http');
const Router = require('../src/modules/Router');
const StateMachine = require('../src/modules/StateMachine');
const State = require('../src/modules/State');

// Initialize router
const router = new Router();

// Data store
const store = {
    books: new Map()
};

// Define route handlers
const bookHandlers = {
    GET: async (ctx) => {
        const books = Array.from(store.books.values());
        return { success: true, data: books };
    },
    
    POST: async (ctx) => {
        const book = ctx.data;
        
        // Validate input
        if (!book.title || !book.author) {
            throw new Error('Book must have title and author');
        }
        
        // Create new book
        const id = Date.now().toString();
        const newBook = {
            id,
            title: book.title,
            author: book.author,
            createdAt: new Date()
        };
        
        // Save book
        store.books.set(id, newBook);
        return { success: true, data: newBook };
    }
};

// Register routes
router.addRoute('/books', bookHandlers);

// CORS middleware
function handleCORS(req, res) {
    res.setHeader('Access-Control-Allow-Origin', '*');
    res.setHeader('Access-Control-Allow-Methods', 'GET, POST, OPTIONS');
    res.setHeader('Access-Control-Allow-Headers', 'Content-Type');
    
    if (req.method === 'OPTIONS') {
        res.writeHead(204);
        res.end();
        return true;
    }
    return false;
}

// Request body parser
async function parseBody(req) {
    return new Promise((resolve, reject) => {
        let body = '';
        req.on('data', chunk => body += chunk);
        req.on('end', () => {
            try {
                resolve(body ? JSON.parse(body) : {});
            } catch (error) {
                reject(new Error('Invalid JSON'));
            }
        });
        req.on('error', reject);
    });
}

// Create HTTP server
const server = http.createServer(async (req, res) => {
    try {
        // Handle CORS
        if (handleCORS(req, res)) return;

        // Parse request body
        const body = await parseBody(req);

        // Handle request through router
        const result = await router.handleRequest(
            req.url,
            req.method,
            body
        );

        // Send success response
        res.writeHead(200, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify(result));

    } catch (error) {
        // Determine status code based on error
        const status = error.message.includes('not found') ? 404 : 
                      error.message.includes('not allowed') ? 405 : 
                      500;

        // Send error response
        res.writeHead(status, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify({
            success: false,
            error: error.message
        }));
    }
});

// Start server
const PORT = 8084;
server.listen(PORT, () => {
    console.log(`Server running at http://localhost:${PORT}`);
    router.printRoutes();
});