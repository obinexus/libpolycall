// main.c - PolyCall CLI Implementation
#include "polycall.h"
#include "polycall_state_machine.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define MAX_INPUT 256
#define HISTORY_SIZE 10

// Context implementation
struct polycall_context {
    char last_error[256];
    void* user_data;
};

// Global state
static PolyCall_StateMachine* g_sm = NULL;
static polycall_context_t g_ctx = NULL;
static char g_command_history[HISTORY_SIZE][MAX_INPUT];
static int g_history_count = 0;
static PolyCall_StateSnapshot g_snapshots[POLYCALL_MAX_STATES];
static bool g_has_snapshot[POLYCALL_MAX_STATES] = {false};
// State callback implementations
void on_init(polycall_context_t ctx) {
    printf("State callback: System initialized\n");
}

void on_ready(polycall_context_t ctx) {
    printf("State callback: System ready\n");
}

void on_running(polycall_context_t ctx) {
    printf("State callback: System running\n");
}

void on_paused(polycall_context_t ctx) {
    printf("State callback: System paused\n");
}

void on_error(polycall_context_t ctx) {
    printf("State callback: System error\n");
}

// Helper functions
void add_to_history(const char* command) {
    if (g_history_count < HISTORY_SIZE) {
        strncpy(g_command_history[g_history_count++], command, MAX_INPUT - 1);
    } else {
        memmove(g_command_history[0], g_command_history[1], (HISTORY_SIZE - 1) * MAX_INPUT);
        strncpy(g_command_history[HISTORY_SIZE - 1], command, MAX_INPUT - 1);
    }
}

void print_help(void) {
    printf("\nPolyCall CLI Commands:\n");
    printf("  init                    - Initialize the state machine\n");
    printf("  add_state NAME         - Add a new state\n");
    printf("  add_transition NAME FROM TO - Add a transition between states\n");
    printf("  execute NAME           - Execute a transition\n");
    printf("  lock STATE_ID          - Lock a state\n");
    printf("  unlock STATE_ID        - Unlock a state\n");
    printf("  verify STATE_ID        - Verify state integrity\n");
    printf("  snapshot STATE_ID      - Create state snapshot\n");
    printf("  restore STATE_ID       - Restore from snapshot\n");
    printf("  diagnostics STATE_ID   - Get state diagnostics\n");
    printf("  list_states            - List all states\n");
    printf("  list_transitions       - List all transitions\n");
    printf("  history                - Show command history\n");
    printf("  help                   - Show this help message\n");
    printf("  quit                   - Exit the program\n");
}

void list_states(void) {
    if (!g_sm) {
        printf("State machine not initialized\n");
        return;
    }

    printf("\nStates:\n");
    for (unsigned int i = 0; i < g_sm->num_states; i++) {
        printf("  %u: %s (locked: %s)\n", 
               i, 
               g_sm->states[i].name, 
               g_sm->states[i].is_locked ? "yes" : "no");
    }
}

void list_transitions(void) {
    if (!g_sm) {
        printf("State machine not initialized\n");
        return;
    }

    printf("\nTransitions:\n");
    for (unsigned int i = 0; i < g_sm->num_transitions; i++) {
        printf("  %s: %u -> %u\n", 
               g_sm->transitions[i].name,
               g_sm->transitions[i].from_state,
               g_sm->transitions[i].to_state);
    }
}

void show_history(void) {
    printf("\nCommand History:\n");
    for (int i = 0; i < g_history_count; i++) {
        printf("  %d: %s\n", i + 1, g_command_history[i]);
    }
}

int initialize_state_machine(void) {
    polycall_config_t config = {0};
    
    if (polycall_init_with_config(&g_ctx, &config) != POLYCALL_SUCCESS) {
        printf("Failed to initialize PolyCall context\n");
        return 0;
    }

    if (polycall_sm_create_with_integrity(g_ctx, &g_sm, NULL) != POLYCALL_SM_SUCCESS) {
        printf("Failed to create state machine\n");
        polycall_cleanup(g_ctx);
        return 0;
    }

    // Add default states
    polycall_sm_add_state(g_sm, "INIT", on_init, NULL, false);
    polycall_sm_add_state(g_sm, "READY", on_ready, NULL, false);
    polycall_sm_add_state(g_sm, "RUNNING", on_running, NULL, false);
    polycall_sm_add_state(g_sm, "PAUSED", on_paused, NULL, false);
    polycall_sm_add_state(g_sm, "ERROR", on_error, NULL, true);

    printf("State machine initialized with default states\n");
    return 1;
}

void cleanup(void) {
    if (g_sm) {
        polycall_sm_destroy(g_sm);
        g_sm = NULL;
    }
    if (g_ctx) {
        polycall_cleanup(g_ctx);
        g_ctx = NULL;
    }
}

int main(void) {
    char input[MAX_INPUT];
    char *command, *arg1, *arg2, *arg3;
    
    printf("PolyCall CLI - Type 'help' for commands\n");

    while (1) {
        printf("\n> ");
        if (!fgets(input, sizeof(input), stdin)) {
            break;
        }

        // Remove newline
        input[strcspn(input, "\n")] = 0;
        
        // Skip empty lines
        if (strlen(input) == 0) {
            continue;
        }

        add_to_history(input);

        // Parse command and arguments
        command = strtok(input, " ");
        arg1 = strtok(NULL, " ");
        arg2 = strtok(NULL, " ");
        arg3 = strtok(NULL, " ");

        if (!command) continue;

        if (strcmp(command, "quit") == 0) {
            break;
        } else if (strcmp(command, "help") == 0) {
            print_help();
        } else if (strcmp(command, "init") == 0) {
            if (g_sm) {
                printf("State machine already initialized\n");
            } else {
                initialize_state_machine();
            }
        } else if (strcmp(command, "add_state") == 0) {
            if (!g_sm) {
                printf("State machine not initialized\n");
                continue;
            }
            if (!arg1) {
                printf("Usage: add_state NAME\n");
                continue;
            }
            if (polycall_sm_add_state(g_sm, arg1, NULL, NULL, false) == POLYCALL_SM_SUCCESS) {
                printf("State '%s' added successfully\n", arg1);
            } else {
                printf("Failed to add state\n");
            }
        } else if (strcmp(command, "add_transition") == 0) {
            if (!g_sm) {
                printf("State machine not initialized\n");
                continue;
            }
            if (!arg1 || !arg2 || !arg3) {
                printf("Usage: add_transition NAME FROM_STATE TO_STATE\n");
                continue;
            }
            unsigned int from = atoi(arg2);
            unsigned int to = atoi(arg3);
            if (polycall_sm_add_transition(g_sm, arg1, from, to, NULL, NULL) == POLYCALL_SM_SUCCESS) {
                printf("Transition '%s' added successfully\n", arg1);
            } else {
                printf("Failed to add transition\n");
            }
        } else if (strcmp(command, "execute") == 0) {
            if (!g_sm) {
                printf("State machine not initialized\n");
                continue;
            }
            if (!arg1) {
                printf("Usage: execute TRANSITION_NAME\n");
                continue;
            }
            if (polycall_sm_execute_transition(g_sm, arg1) == POLYCALL_SM_SUCCESS) {
                printf("Transition '%s' executed successfully\n", arg1);
            } else {
                printf("Failed to execute transition\n");
            }
        } else if (strcmp(command, "verify") == 0) {
            if (!g_sm) {
                printf("State machine not initialized\n");
                continue;
            }
            if (!arg1) {
                printf("Usage: verify STATE_ID\n");
                continue;
            }
            unsigned int state_id = atoi(arg1);
            if (polycall_sm_verify_state_integrity(g_sm, state_id) == POLYCALL_SM_SUCCESS) {
                printf("State %u integrity verified\n", state_id);
            } else {
                printf("State integrity verification failed\n");
            }
        } else if (strcmp(command, "snapshot") == 0) {
    if (!g_sm) {
        printf("State machine not initialized\n");
        continue;
    }
    if (!arg1) {
        printf("Usage: snapshot STATE_ID\n");
        continue;
    }
    unsigned int state_id = atoi(arg1);
    if (polycall_sm_create_state_snapshot(g_sm, state_id, &g_snapshots[state_id]) == POLYCALL_SM_SUCCESS) {
        g_has_snapshot[state_id] = true;
        printf("Created snapshot of state %u\n", state_id);
    } else {
        printf("Failed to create snapshot\n");
    }
} else if (strcmp(command, "restore") == 0) {
    if (!g_sm) {
        printf("State machine not initialized\n");
        continue;
    }
    if (!arg1) {
        printf("Usage: restore STATE_ID\n");
        continue;
    }
    unsigned int state_id = atoi(arg1);
    if (!g_has_snapshot[state_id]) {
        printf("No snapshot exists for state %u\n", state_id);
        continue;
    }
    if (polycall_sm_restore_state_from_snapshot(g_sm, &g_snapshots[state_id]) == POLYCALL_SM_SUCCESS) {
        printf("Restored state %u from snapshot\n", state_id);
    } else {
        printf("Failed to restore from snapshot\n");
    }
}

        else if (strcmp(command, "lock") == 0) {
            if (!g_sm) {
                printf("State machine not initialized\n");
                continue;
            }
            if (!arg1) {
                printf("Usage: lock STATE_ID\n");
                continue;
            }
            unsigned int state_id = atoi(arg1);
            if (polycall_sm_lock_state(g_sm, state_id) == POLYCALL_SM_SUCCESS) {
                printf("State %u locked\n", state_id);
            } else {
                printf("Failed to lock state\n");
            }
        } else if (strcmp(command, "unlock") == 0) {
            if (!g_sm) {
                printf("State machine not initialized\n");
                continue;
            }
            if (!arg1) {
                printf("Usage: unlock STATE_ID\n");
                continue;
            }
            unsigned int state_id = atoi(arg1);
            if (polycall_sm_unlock_state(g_sm, state_id) == POLYCALL_SM_SUCCESS) {
                printf("State %u unlocked\n", state_id);
            } else {
                printf("Failed to unlock state\n");
            }
        } else if (strcmp(command, "diagnostics") == 0) {
            if (!g_sm) {
                printf("State machine not initialized\n");
                continue;
            }
            if (!arg1) {
                printf("Usage: diagnostics STATE_ID\n");
                continue;
            }
            unsigned int state_id = atoi(arg1);
            PolyCall_StateDiagnostics diag;
            if (polycall_sm_get_state_diagnostics(g_sm, state_id, &diag) == POLYCALL_SM_SUCCESS) {
                printf("State %u diagnostics:\n", state_id);
                printf("  Creation time: %lu\n", diag.creation_time);
                printf("  Last modified: %lu\n", diag.last_modified);
                printf("  Is locked: %s\n", diag.is_locked ? "yes" : "no");
                printf("  Checksum: %u\n", diag.current_checksum);
            } else {
                printf("Failed to get state diagnostics\n");
            }
        } else if (strcmp(command, "list_states") == 0) {
            list_states();
        } else if (strcmp(command, "list_transitions") == 0) {
            list_transitions();
        } else if (strcmp(command, "history") == 0) {
            show_history();
        } else {
            printf("Unknown command. Type 'help' for available commands\n");
        }
    }

    cleanup();
    printf("Goodbye!\n");
    return 0;
}