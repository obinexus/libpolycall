


// Test cases for TDD
void test_state_machine_initialization(void) {
    polycall_context_t ctx;
    PolyCall_StateMachine* sm;
    
    // Test 1: Basic initialization
    assert(initialize_state_machine(&ctx, &sm) == POLYCALL_SM_SUCCESS);
    assert(sm->num_states == sizeof(DEFAULT_STATES) / sizeof(DEFAULT_STATES[0]));
    
    // Test 2: State verification
    for (size_t i = 0; i < sizeof(DEFAULT_STATES) / sizeof(DEFAULT_STATES[0]); i++) {
        bool found = false;
        for (unsigned int j = 0; j < sm->num_states; j++) {
            if (strcmp(sm->states[j].name, DEFAULT_STATES[i].name) == 0) {
                found = true;
                break;
            }
        }
        assert(found);
    }
    
    // Test 3: Transition verification
    assert(sm->num_transitions > 0);
    
    // Cleanup
    polycall_sm_destroy(sm);
    polycall_cleanup(ctx);
}