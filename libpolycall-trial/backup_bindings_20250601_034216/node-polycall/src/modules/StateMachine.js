// StateMachine.js - PolyCall State Machine Implementation
const EventEmitter = require('events');
const State = require('./State');

class StateMachine extends EventEmitter {
    constructor(options = {}) {
        super();
        this.states = new Map();
        this.transitions = new Map();
        this.currentState = null;
        this.history = [];
        this.maxHistoryLength = options.maxHistoryLength || 100;
        this.options = {
            allowSelfTransitions: false,
            validateStateChange: true,
            recordHistory: true,
            ...options
        };
    }

    // State management
    addState(name, options = {}) {
        if (this.states.has(name)) {
            throw new Error(`State ${name} already exists`);
        }

        const state = new State(name, options);
        this.states.set(name, state);

        // Listen for state events
        state.on('locked', () => this.emit('state:locked', state));
        state.on('unlocked', () => this.emit('state:unlocked', state));
        state.on('error', (error) => this.emit('state:error', error, state));

        // Set initial state if none exists
        if (!this.currentState && !options.defer) {
            this.currentState = state;
            this.emit('state:initial', state);
        }

        return state;
    }

    getState(name) {
        if (!this.states.has(name)) {
            throw new Error(`State ${name} does not exist`);
        }
        return this.states.get(name);
    }

    getCurrentState() {
        return this.currentState;
    }

    // Transition management
    addTransition(fromState, toState, options = {}) {
        const from = typeof fromState === 'string' ? fromState : fromState.name;
        const to = typeof toState === 'string' ? toState : toState.name;

        if (!this.states.has(from)) {
            throw new Error(`Source state ${from} does not exist`);
        }
        if (!this.states.has(to)) {
            throw new Error(`Target state ${to} does not exist`);
        }

        const transitionKey = `${from}->${to}`;
        const transition = {
            from,
            to,
            guard: options.guard || (() => true),
            before: options.before || (() => {}),
            after: options.after || (() => {}),
            ...options
        };

        this.transitions.set(transitionKey, transition);
        this.states.get(from).addTransition(to);

        return this;
    }

    // State transition execution
    async executeTransition(toState) {
        const targetState = typeof toState === 'string' ? this.getState(toState) : toState;

        if (!this.currentState) {
            throw new Error('No current state');
        }

        const transitionKey = `${this.currentState.name}->${targetState.name}`;
        const transition = this.transitions.get(transitionKey);

        if (!transition) {
            throw new Error(`No transition defined from ${this.currentState.name} to ${targetState.name}`);
        }

        if (!this.options.allowSelfTransitions && this.currentState === targetState) {
            throw new Error('Self-transitions are not allowed');
        }

        // Verify states are not locked
        if (this.currentState.isLocked || targetState.isLocked) {
            throw new Error('Cannot transition when states are locked');
        }

        try {
            // Check guard condition
            if (!await transition.guard(this.currentState, targetState)) {
                throw new Error('Transition guard condition failed');
            }

            // Execute transition
            const fromState = this.currentState;
            
            // Before transition
            this.emit('transition:start', fromState, targetState);
            await transition.before(fromState, targetState);

            // Perform transition
            this.currentState = targetState;

            // After transition
            await transition.after(fromState, targetState);
            this.emit('transition:complete', fromState, targetState);

            // Record in history
            if (this.options.recordHistory) {
                this.recordTransition(fromState, targetState);
            }

            return true;
        } catch (error) {
            this.emit('transition:error', error, this.currentState, targetState);
            throw error;
        }
    }

    // History management
    recordTransition(fromState, toState) {
        const record = {
            timestamp: Date.now(),
            from: fromState.name,
            to: toState.name
        };

        this.history.push(record);
        if (this.history.length > this.maxHistoryLength) {
            this.history.shift();
        }
    }

    getHistory() {
        return [...this.history];
    }

    clearHistory() {
        this.history = [];
    }

    // State verification
    verifyState(name) {
        const state = this.getState(name);
        return state.verify();
    }

    verifyAllStates() {
        const results = new Map();
        for (const [name, state] of this.states) {
            results.set(name, state.verify());
        }
        return results;
    }

    // Snapshot management
    createSnapshot() {
        return {
            timestamp: Date.now(),
            currentState: this.currentState ? this.currentState.name : null,
            states: Array.from(this.states.entries()).map(([name, state]) => ({
                name,
                snapshot: state.createSnapshot()
            })),
            history: this.getHistory()
        };
    }

    async restoreFromSnapshot(snapshot) {
        if (!snapshot || !snapshot.states) {
            throw new Error('Invalid snapshot format');
        }

        // Clear current state
        this.currentState = null;
        this.states.clear();
        this.history = snapshot.history || [];

        // Restore states
        for (const stateData of snapshot.states) {
            const state = new State(stateData.name);
            await state.restoreFromSnapshot(stateData.snapshot);
            this.states.set(state.name, state);

            if (snapshot.currentState === state.name) {
                this.currentState = state;
            }
        }

        this.emit('restored', snapshot);
        return this;
    }

    // Utility methods
    getStateNames() {
        return Array.from(this.states.keys());
    }

    getTransitions() {
        return Array.from(this.transitions.entries()).map(([key, transition]) => ({
            from: transition.from,
            to: transition.to
        }));
    }

    reset() {
        this.currentState = null;
        this.states.clear();
        this.transitions.clear();
        this.history = [];
        this.emit('reset');
    }

    toString() {
        return `StateMachine(current: ${this.currentState ? this.currentState.name : 'none'}, states: ${this.states.size})`;
    }
}

module.exports = StateMachine;