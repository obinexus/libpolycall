#ifndef POLYCALL_MICRO_H
#define POLYCALL_MICRO_H

#include "polycall.h"
#include "polycall_protocol.h"
#include "polycall_state_machine.h"
#include "network.h"
#include <stdint.h>
#include <stdbool.h>

#ifdef __cplusplus
extern "C" {
#endif

// Constants for micro service configuration
#define POLYCALL_MICRO_MAX_SERVICES 32
#define POLYCALL_MICRO_MAX_ENDPOINTS 16
#define POLYCALL_MICRO_MAX_COMMANDS 64
#define POLYCALL_MICRO_BUFFER_SIZE 4096

// Data-oriented command structure for contiguous memory layout
typedef struct {
    uint32_t id;
    uint32_t flags;
    uint32_t payload_size;
    uint8_t payload[POLYCALL_MICRO_BUFFER_SIZE];
} PolycallCommand;

// Command array for batch processing
typedef struct {
    PolycallCommand commands[POLYCALL_MICRO_MAX_COMMANDS];
    uint32_t count;
    uint32_t capacity;
} PolycallCommandArray;

// Service state structure with minimal indirection
typedef struct {
    uint32_t id;
    uint32_t flags;
    uint32_t state;
    uint64_t last_update;
    NetworkEndpoint endpoints[POLYCALL_MICRO_MAX_ENDPOINTS];
    uint32_t endpoint_count;
    PolycallCommandArray command_queue;
    uint8_t memory_pool[POLYCALL_MICRO_BUFFER_SIZE];
} PolycallServiceState;

// Service array for contiguous state storage
typedef struct {
    PolycallServiceState services[POLYCALL_MICRO_MAX_SERVICES];
    uint32_t count;
    uint32_t active_mask;
    uint64_t last_gc;
} PolycallServiceArray;

// Micro service context with data-oriented layout
typedef struct {
    PolycallServiceArray service_array;
    PolyCall_StateMachine* state_machine;
    polycall_protocol_context_t protocol_ctx;
    uint32_t flags;
    uint64_t startup_time;
} PolycallMicroContext;

// Function pointer types for point-free style operations
typedef void (*PolycallTransform)(PolycallCommand*);
typedef bool (*PolycallPredicate)(const PolycallCommand*);
typedef void (*PolycallOperation)(PolycallServiceState*);

// Function composition structure
typedef struct {
    PolycallTransform* transforms;
    uint32_t transform_count;
} PolycallTransformChain;

// Status codes
typedef enum {
    POLYCALL_MICRO_SUCCESS = 0,
    POLYCALL_MICRO_ERROR_INIT,
    POLYCALL_MICRO_ERROR_SERVICE,
    POLYCALL_MICRO_ERROR_COMMAND,
    POLYCALL_MICRO_ERROR_PROTOCOL,
    POLYCALL_MICRO_ERROR_MEMORY
} PolycallMicroStatus;

// Core initialization and cleanup functions
PolycallMicroStatus polycall_micro_init(
    PolycallMicroContext* ctx,
    const polycall_config_t* config
);

void polycall_micro_cleanup(PolycallMicroContext* ctx);

// Service management functions
PolycallMicroStatus polycall_micro_create_service(
    PolycallMicroContext* ctx,
    uint32_t service_id,
    uint32_t flags
);

PolycallMicroStatus polycall_micro_destroy_service(
    PolycallMicroContext* ctx,
    uint32_t service_id
);

// Point-free style command processing functions
PolycallMicroStatus polycall_micro_transform_command(
    PolycallCommand* cmd,
    const PolycallTransformChain* chain
);

PolycallMicroStatus polycall_micro_filter_commands(
    PolycallCommandArray* commands,
    PolycallPredicate predicate
);

PolycallMicroStatus polycall_micro_process_commands(
    PolycallServiceState* service,
    PolycallOperation operation
);

// Batch processing functions
PolycallMicroStatus polycall_micro_batch_process(
    PolycallMicroContext* ctx,
    uint32_t service_id,
    const PolycallCommandArray* commands
);

// State management functions
PolycallMicroStatus polycall_micro_update_service_state(
    PolycallMicroContext* ctx,
    uint32_t service_id,
    uint32_t new_state
);

// Resource management functions
PolycallMicroStatus polycall_micro_collect_garbage(
    PolycallMicroContext* ctx
);

// Utility functions
const char* polycall_micro_status_string(
    PolycallMicroStatus status
);

uint32_t polycall_micro_get_active_services(
    const PolycallMicroContext* ctx
);

// Transformation chain builders
PolycallTransformChain polycall_micro_create_transform_chain(
    PolycallTransform* transforms,
    uint32_t count
);

void polycall_micro_destroy_transform_chain(
    PolycallTransformChain* chain
);

#ifdef __cplusplus
}
#endif

#endif // POLYCALL_MICRO_H