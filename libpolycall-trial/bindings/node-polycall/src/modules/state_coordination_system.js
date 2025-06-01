// LibPolyCall State Coordination System
// Prevents race conditions between Node.js and Python bindings

class LibPolyCallStateCoordinator {
    constructor() {
        this.stateTransitionLocks = new Map();
        this.bindingStates = new Map();
        this.transitionQueue = [];
        this.activeTransitions = new Set();
        
        // Initialize binding state tracking
        this.bindingStates.set('node-binding', {
            currentState: 'idle',
            lastTransition: null,
            lockTimestamp: null
        });
        
        this.bindingStates.set('pypolycall-binding', {
            currentState: 'idle', 
            lastTransition: null,
            lockTimestamp: null
        });
    }
    
    /**
     * Request state transition with binding coordination
     * Prevents race conditions between bindings
     */
    async requestStateTransition(bindingType, targetState, transitionData = {}) {
        const transitionId = this.generateTransitionId(bindingType, targetState);
        
        // Check if transition is already active
        if (this.activeTransitions.has(targetState)) {
            const conflictingBinding = this.findConflictingBinding(targetState);
            return {
                success: false,
                error: 'State transition conflict',
                conflictingBinding,
                suggestedAction: 'retry_after_delay'
            };
        }
        
        // Acquire state lock
        const lockAcquired = await this.acquireStateLock(bindingType, targetState);
        if (!lockAcquired) {
            return {
                success: false,
                error: 'Unable to acquire state lock',
                suggestedAction: 'queue_transition'
            };
        }
        
        try {
            // Execute coordinated transition
            const result = await this.executeCoordinatedTransition(
                bindingType, 
                targetState, 
                transitionData,
                transitionId
            );
            
            return result;
        } finally {
            // Always release lock
            this.releaseStateLock(bindingType, targetState);
            this.activeTransitions.delete(targetState);
        }
    }
    
    /**
     * Acquire exclusive state lock for binding
     */
    async acquireStateLock(bindingType, targetState, timeout = 5000) {
        const lockKey = `${bindingType}:${targetState}`;
        const startTime = Date.now();
        
        while (Date.now() - startTime < timeout) {
            if (!this.stateTransitionLocks.has(lockKey)) {
                this.stateTransitionLocks.set(lockKey, {
                    bindingType,
                    targetState,
                    acquiredAt: Date.now(),
                    lockId: this.generateLockId()
                });
                
                this.activeTransitions.add(targetState);
                return true;
            }
            
            // Wait before retry
            await this.sleep(50);
        }
        
        return false;
    }
    
    /**
     * Release state lock
     */
    releaseStateLock(bindingType, targetState) {
        const lockKey = `${bindingType}:${targetState}`;
        this.stateTransitionLocks.delete(lockKey);
    }
    
    /**
     * Execute state transition with coordination
     */
    async executeCoordinatedTransition(bindingType, targetState, transitionData, transitionId) {
        const currentBindingState = this.bindingStates.get(bindingType);
        
        // Validate transition is allowed
        const validationResult = this.validateStateTransition(
            currentBindingState.currentState,
            targetState,
            bindingType
        );
        
        if (!validationResult.valid) {
            return {
                success: false,
                error: validationResult.error,
                currentState: currentBindingState.currentState
            };
        }
        
        // Execute transition
        const transitionResult = await this.performStateTransition(
            bindingType,
            currentBindingState.currentState,
            targetState,
            transitionData
        );
        
        if (transitionResult.success) {
            // Update binding state
            this.bindingStates.set(bindingType, {
                currentState: targetState,
                lastTransition: {
                    from: currentBindingState.currentState,
                    to: targetState,
                    timestamp: Date.now(),
                    transitionId,
                    data: transitionData
                },
                lockTimestamp: null
            });
            
            // Notify other bindings of state change
            await this.notifyBindingsOfStateChange(bindingType, targetState, transitionData);
        }
        
        return transitionResult;
    }
    
    /**
     * Validate if state transition is allowed
     */
    validateStateTransition(currentState, targetState, bindingType) {
        // Define allowed transitions per binding type
        const allowedTransitions = {
            'node-binding': {
                'idle': ['initializing', 'ready'],
                'initializing': ['ready', 'error', 'idle'],
                'ready': ['running', 'paused', 'idle'],
                'running': ['paused', 'completed', 'error'],
                'paused': ['running', 'idle'],
                'completed': ['idle'],
                'error': ['idle', 'initializing']
            },
            'pypolycall-binding': {
                'idle': ['initializing', 'ready'],
                'initializing': ['ready', 'error', 'idle'],
                'ready': ['processing', 'idle'],
                'processing': ['ready', 'error'],
                'error': ['idle', 'ready']
            }
        };
        
        const bindingTransitions = allowedTransitions[bindingType];
        if (!bindingTransitions || !bindingTransitions[currentState]) {
            return {
                valid: false,
                error: `Invalid current state: ${currentState} for ${bindingType}`
            };
        }
        
        if (!bindingTransitions[currentState].includes(targetState)) {
            return {
                valid: false,
                error: `Transition from ${currentState} to ${targetState} not allowed for ${bindingType}`
            };
        }
        
        return { valid: true };
    }
    
    /**
     * Perform actual state transition
     */
    async performStateTransition(bindingType, fromState, toState, transitionData) {
        try {
            // Call LibPolyCall core transition
            const polycallResult = await this.invokePolycallTransition(
                bindingType,
                fromState,
                toState,
                transitionData
            );
            
            return {
                success: true,
                fromState,
                toState,
                timestamp: Date.now(),
                polycallResult,
                bindingType
            };
        } catch (error) {
            return {
                success: false,
                error: error.message,
                fromState,
                toState,
                bindingType
            };
        }
    }
    
    /**
     * Invoke LibPolyCall core for state transition
     */
    async invokePolycallTransition(bindingType, fromState, toState, transitionData) {
        // This would interface with the actual LibPolyCall binary
        // For now, simulate the call
        return new Promise((resolve) => {
            setTimeout(() => {
                resolve({
                    status: 'transition_completed',
                    fromState,
                    toState,
                    bindingType,
                    polycallVersion: '1.0.0',
                    timestamp: new Date().toISOString()
                });
            }, 100);
        });
    }
    
    /**
     * Notify other bindings of state changes
     */
    async notifyBindingsOfStateChange(originatingBinding, newState, transitionData) {
        const otherBindings = Array.from(this.bindingStates.keys())
            .filter(binding => binding !== originatingBinding);
        
        for (const binding of otherBindings) {
            try {
                await this.sendStateChangeNotification(binding, {
                    originatingBinding,
                    newState,
                    transitionData,
                    timestamp: Date.now()
                });
            } catch (error) {
                console.error(`Failed to notify ${binding} of state change:`, error);
            }
        }
    }
    
    /**
     * Send state change notification to specific binding
     */
    async sendStateChangeNotification(targetBinding, notification) {
        // This would send notification to the specific binding
        // Implementation depends on binding communication mechanism
        console.log(`State change notification sent to ${targetBinding}:`, notification);
    }
    
    /**
     * Find which binding has conflicting transition
     */
    findConflictingBinding(targetState) {
        for (const [lockKey, lockData] of this.stateTransitionLocks) {
            if (lockData.targetState === targetState) {
                return lockData.bindingType;
            }
        }
        return null;
    }
    
    /**
     * Get current state for all bindings
     */
    getAllBindingStates() {
        const states = {};
        for (const [bindingType, stateData] of this.bindingStates) {
            states[bindingType] = {
                currentState: stateData.currentState,
                lastTransition: stateData.lastTransition
            };
        }
        return states;
    }
    
    /**
     * Check if any binding has active locks
     */
    hasActiveLocks() {
        return this.stateTransitionLocks.size > 0;
    }
    
    /**
     * Utility functions
     */
    generateTransitionId(bindingType, targetState) {
        return `${bindingType}_${targetState}_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    }
    
    generateLockId() {
        return `lock_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    }
    
    sleep(ms) {
        return new Promise(resolve => setTimeout(resolve, ms));
    }
}

// Export for use in LibPolyCall bindings
module.exports = LibPolyCallStateCoordinator;

// Usage example for Node.js binding
/*
const stateCoordinator = new LibPolyCallStateCoordinator();

// In PolyCallClient.js
async function transitionTo(targetState, data = {}) {
    const result = await stateCoordinator.requestStateTransition(
        'node-binding',
        targetState,
        data
    );
    
    if (!result.success) {
        throw new Error(`State transition failed: ${result.error}`);
    }
    
    return result;
}
*/
