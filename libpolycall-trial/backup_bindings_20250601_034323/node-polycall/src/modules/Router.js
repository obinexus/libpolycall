// Router.js
const EventEmitter = require('events');
const { URL } = require('url');

class Router extends EventEmitter {
    constructor() {
        super();
        this.routes = new Map();
    }

    /**
     * Register a route with method-specific handlers
     */
    addRoute(path, handlers) {
        // If handlers is a function, treat it as a generic handler
        if (typeof handlers === 'function') {
            this.routes.set(path, {
                handler: handlers,
                methods: new Set(['GET', 'POST'])  // Default methods
            });
            return;
        }

        // If handlers is an object with method-specific handlers
        if (typeof handlers === 'object') {
            const supportedMethods = Object.keys(handlers).map(m => m.toUpperCase());
            
            this.routes.set(path, {
                handler: async (ctx) => {
                    const method = ctx.method.toUpperCase();
                    const methodHandler = handlers[method];
                    
                    if (!methodHandler) {
                        throw new Error(`Method ${method} not allowed`);
                    }
                    
                    return methodHandler(ctx);
                },
                methods: new Set(supportedMethods)
            });
        }
    }

    /**
     * Find a matching route for the given path
     */
    findRoute(path) {
        // Normalize the path
        path = this.normalizePath(path);

        // Try direct match first
        if (this.routes.has(path)) {
            return this.routes.get(path);
        }

        // If no direct match, return null
        return null;
    }

    /**
     * Handle an incoming request
     */
    async handleRequest(path, method, data = {}) {
        const route = this.findRoute(path);
        
        if (!route) {
            throw new Error(`No route found for: ${path}`);
        }

        if (!route.methods.has(method.toUpperCase())) {
            throw new Error(`Method ${method} not allowed for ${path}`);
        }

        const context = {
            path,
            method: method.toUpperCase(),
            data,
            params: {},
            query: this.parseQueryString(path)
        };

        try {
            // Execute the route handler
            if (typeof route.handler === 'function') {
                return await route.handler(context);
            } else {
                throw new Error('Invalid route handler');
            }
        } catch (error) {
            this.emit('error', error);
            throw error;
        }
    }

    /**
     * Parse query string from path
     */
    parseQueryString(path) {
        try {
            const url = new URL(path, 'http://localhost');
            const params = {};
            url.searchParams.forEach((value, key) => {
                params[key] = value;
            });
            return params;
        } catch {
            return {};
        }
    }

    /**
     * Normalize a path string
     */
    normalizePath(path) {
        if (!path.startsWith('/')) {
            path = '/' + path;
        }
        // Remove trailing slash unless it's the root path
        if (path.length > 1 && path.endsWith('/')) {
            path = path.slice(0, -1);
        }
        return path;
    }

    /**
     * Print registered routes (for debugging)
     */
    printRoutes() {
        console.log('\nRegistered Routes:');
        for (const [path, route] of this.routes) {
            const methods = Array.from(route.methods).join(',');
            console.log(`${methods} ${path}`);
        }
    }


}
module.exports = Router;