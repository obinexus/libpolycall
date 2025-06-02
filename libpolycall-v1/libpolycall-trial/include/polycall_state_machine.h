#ifndef POLYCALL_STATE_MACHINE_H
#define POLYCALL_STATE_MACHINE_H

#include <time.h>
#include <stdlib.h>
#include <stdio.h>
#include <string.h>
#include <stdint.h>
#include <stdbool.h>
#include <stddef.h>
#include "polycall.h"

#ifdef __cplusplus
extern "C" {
#endif

// State structure with integrity data
typedef struct PolyCall_State {
    char name[POLYCALL_MAX_NAME_LENGTH];
    PolyCall_StateAction on_enter;
    PolyCall_StateAction on_exit;
    bool is_final;
    unsigned int id;
    uint32_t checksum;
    uint64_t timestamp;
    unsigned int version;
    bool is_locked;
} PolyCall_State;

// Transition structure with validation
typedef struct PolyCall_Transition {
    char name[POLYCALL_MAX_NAME_LENGTH];
    unsigned int from_state;
    unsigned int to_state;
    PolyCall_StateAction action;
    bool is_valid;
    bool (*guard_condition)(const PolyCall_State*, const PolyCall_State*);
    uint32_t guard_checksum;
} PolyCall_Transition;

// State integrity verification function type
typedef bool (*PolyCall_StateIntegrityCheck)(const PolyCall_State* state);

// State machine structure
typedef struct PolyCall_StateMachine {
    PolyCall_State states[POLYCALL_MAX_STATES];
    PolyCall_Transition transitions[POLYCALL_MAX_TRANSITIONS];
    unsigned int current_state;
    unsigned int num_states;
    unsigned int num_transitions;
    polycall_context_t ctx;
    bool is_initialized;
    PolyCall_StateIntegrityCheck integrity_check;
    uint32_t machine_checksum;
    struct {
        unsigned int failed_transitions;
        unsigned int integrity_violations;
        uint64_t last_verification;
    } diagnostics;
} PolyCall_StateMachine;

// Status codes
typedef enum {
    POLYCALL_SM_SUCCESS = 0,
    POLYCALL_SM_ERROR_INVALID_STATE,
    POLYCALL_SM_ERROR_INVALID_TRANSITION,
    POLYCALL_SM_ERROR_MAX_STATES_REACHED,
    POLYCALL_SM_ERROR_MAX_TRANSITIONS_REACHED,
    POLYCALL_SM_ERROR_INVALID_CONTEXT,
    POLYCALL_SM_ERROR_NOT_INITIALIZED,
    POLYCALL_SM_ERROR_INTEGRITY_CHECK_FAILED,
    POLYCALL_SM_ERROR_STATE_LOCKED,
    POLYCALL_SM_ERROR_VERSION_MISMATCH
} polycall_sm_status_t;

// State snapshot structure
typedef struct PolyCall_StateSnapshot {
    PolyCall_State state;
    uint64_t timestamp;
    uint32_t checksum;
} PolyCall_StateSnapshot;

// Diagnostic structure
typedef struct PolyCall_StateDiagnostics {
    unsigned int state_id;
    uint64_t creation_time;
    uint64_t last_modified;
    unsigned int transition_count;
    unsigned int integrity_check_count;
    bool is_locked;
    uint32_t current_checksum;
} PolyCall_StateDiagnostics;

// API functions
polycall_sm_status_t polycall_sm_create_with_integrity(
    polycall_context_t ctx, 
    PolyCall_StateMachine** sm,
    PolyCall_StateIntegrityCheck integrity_check
);

polycall_sm_status_t polycall_sm_add_state(
    PolyCall_StateMachine* sm,
    const char* name,
    PolyCall_StateAction on_enter,
    PolyCall_StateAction on_exit,
    bool is_final
);

polycall_sm_status_t polycall_sm_add_transition(
    PolyCall_StateMachine* sm,
    const char* name,
    unsigned int from_state,
    unsigned int to_state,
    PolyCall_StateAction action,
    bool (*guard_condition)(const PolyCall_State*, const PolyCall_State*)
);

polycall_sm_status_t polycall_sm_execute_transition(
    PolyCall_StateMachine* sm,
    const char* transition_name
);

polycall_sm_status_t polycall_sm_verify_state_integrity(
    PolyCall_StateMachine* sm,
    unsigned int state_id
);

polycall_sm_status_t polycall_sm_lock_state(
    PolyCall_StateMachine* sm,
    unsigned int state_id
);

polycall_sm_status_t polycall_sm_unlock_state(
    PolyCall_StateMachine* sm,
    unsigned int state_id
);

polycall_sm_status_t polycall_sm_get_state_version(
    const PolyCall_StateMachine* sm,
    unsigned int state_id,
    unsigned int* version
);

polycall_sm_status_t polycall_sm_create_state_snapshot(
    const PolyCall_StateMachine* sm,
    unsigned int state_id,
    PolyCall_StateSnapshot* snapshot
);

polycall_sm_status_t polycall_sm_restore_state_from_snapshot(
    PolyCall_StateMachine* sm,
    const PolyCall_StateSnapshot* snapshot
);

polycall_sm_status_t polycall_sm_get_state_diagnostics(
    const PolyCall_StateMachine* sm,
    unsigned int state_id,
    PolyCall_StateDiagnostics* diagnostics
);

void polycall_sm_destroy(PolyCall_StateMachine* sm);



#ifdef __cplusplus
}
#endif

#endif // POLYCALL_STATE_MACHINE_H