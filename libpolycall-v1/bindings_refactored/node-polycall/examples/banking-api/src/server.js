const express = require('express');
const cors = require('cors');
const { PolyCallClient } = require('../../../core/src/index');

class BankingAPIServer {
    constructor() {
        this.app = express();
        this.port = process.env.PORT || 3000;
        this.polycallClient = new PolyCallClient({
            host: 'localhost',
            port: 433,
            binding: 'node-polycall'
        });
        
        this.setupMiddleware();
        this.setupRoutes();
    }
    
    setupMiddleware() {
        this.app.use(cors());
        this.app.use(express.json());
        this.app.use(express.urlencoded({ extended: true }));
    }
    
    setupRoutes() {
        // Account management
        this.app.get('/accounts', this.getAccounts.bind(this));
        this.app.post('/accounts', this.createAccount.bind(this));
        this.app.get('/accounts/:id', this.getAccount.bind(this));
        
        // Transaction processing
        this.app.get('/transactions', this.getTransactions.bind(this));
        this.app.post('/transactions', this.createTransaction.bind(this));
        
        // Balance inquiries
        this.app.get('/balances/:accountId', this.getBalance.bind(this));
        
        // Health check
        this.app.get('/health', (req, res) => {
            res.json({ status: 'healthy', service: 'banking-api' });
        });
    }
    
    async getAccounts(req, res) {
        try {
            await this.polycallClient.transitionTo('processing');
            // Banking logic here
            res.json({ accounts: [], message: 'LibPolyCall banking API' });
        } catch (error) {
            res.status(500).json({ error: error.message });
        }
    }
    
    async createAccount(req, res) {
        try {
            const accountData = req.body;
            // Create account with LibPolyCall state management
            res.status(201).json({ account: accountData, created: true });
        } catch (error) {
            res.status(500).json({ error: error.message });
        }
    }
    
    async getAccount(req, res) {
        try {
            const { id } = req.params;
            // Fetch account with LibPolyCall
            res.json({ accountId: id, balance: 0 });
        } catch (error) {
            res.status(500).json({ error: error.message });
        }
    }
    
    async getTransactions(req, res) {
        try {
            // Fetch transactions
            res.json({ transactions: [] });
        } catch (error) {
            res.status(500).json({ error: error.message });
        }
    }
    
    async createTransaction(req, res) {
        try {
            const transactionData = req.body;
            // Process transaction
            res.status(201).json({ transaction: transactionData, processed: true });
        } catch (error) {
            res.status(500).json({ error: error.message });
        }
    }
    
    async getBalance(req, res) {
        try {
            const { accountId } = req.params;
            // Get balance
            res.json({ accountId, balance: 0, currency: 'USD' });
        } catch (error) {
            res.status(500).json({ error: error.message });
        }
    }
    
    async start() {
        try {
            await this.polycallClient.connect();
            this.app.listen(this.port, () => {
                console.log(`🏦 Banking API Server running on port ${this.port}`);
                console.log(`🔗 LibPolyCall binding: node-polycall`);
            });
        } catch (error) {
            console.error('Failed to start banking server:', error);
        }
    }
}

const server = new BankingAPIServer();
server.start();