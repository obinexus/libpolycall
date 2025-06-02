#include "polycall_micro.h"
#include <string.h>
#include <time.h>

// Internal helper functions for data-oriented operations
static void reset_command_array(PolycallCommandArray* array) {
    if (!array) return;
    memset(array->commands, 0, sizeof(PolycallCommand) * POLYCALL_MICRO_MAX_COMMANDS);
    array->count = 0;
    array->capacity = POLYCALL_MICRO_MAX_COMMANDS;
}

static void reset_service_state(PolycallServiceState* state) {
    if (!state) return;
    memset(state, 0, sizeof(PolycallServiceState));
    reset_command_array(&state->command_queue);
}

static uint64_t get_current_timestamp(void) {
    return (uint64_t)time(NULL);
}

// Initialize the micro service context
PolycallMicroStatus polycall_micro_init(
    PolycallMicroContext* ctx,
    const polycall_config_t* config
) {
    if (!ctx || !config) return POLYCALL_MICRO_ERROR_INIT;
    
    // Initialize service array with contiguous memory layout
    memset(&ctx->service_array, 0, sizeof(PolycallServiceArray));
    ctx->service_array.count = 0;
    ctx->service_array.active_mask = 0;
    ctx->service_array.last_gc = get_current_timestamp();
    
    // Initialize state machine
    if (polycall_sm_create_with_integrity(config->user_data, &ctx->state_machine, NULL) 
        != POLYCALL_SM_SUCCESS) {
        return POLYCALL_MICRO_ERROR_INIT;
    }
    
    // Initialize protocol context with network endpoint
    NetworkEndpoint endpoint = {0};
    endpoint.protocol = NET_TCP;
    endpoint.role = NET_SERVER;
    
    polycall_protocol_config_t proto_config = {
        .flags = 0,
        .max_message_size = POLYCALL_MICRO_BUFFER_SIZE,
        .timeout_ms = 5000,
        .user_data = config->user_data
    };
    
    if (!polycall_protocol_init(&ctx->protocol_ctx, config->user_data, &endpoint, &proto_config)) {
        polycall_sm_destroy(ctx->state_machine);
        return POLYCALL_MICRO_ERROR_PROTOCOL;
    }
    
    ctx->flags = config->flags;
    ctx->startup_time = get_current_timestamp();
    
    return POLYCALL_MICRO_SUCCESS;
}

// Cleanup resources
void polycall_micro_cleanup(PolycallMicroContext* ctx) {
    if (!ctx) return;
    
    // Cleanup all services
    for (uint32_t i = 0; i < ctx->service_array.count; i++) {
        if (ctx->service_array.active_mask & (1U << i)) {
            polycall_micro_destroy_service(ctx, ctx->service_array.services[i].id);
        }
    }
    
    // Cleanup protocol and state machine
    polycall_protocol_cleanup(&ctx->protocol_ctx);
    polycall_sm_destroy(ctx->state_machine);
    
    memset(ctx, 0, sizeof(PolycallMicroContext));
}

// Create a new service instance
PolycallMicroStatus polycall_micro_create_service(
    PolycallMicroContext* ctx,
    uint32_t service_id,
    uint32_t flags
) {
    if (!ctx || ctx->service_array.count >= POLYCALL_MICRO_MAX_SERVICES) {
        return POLYCALL_MICRO_ERROR_SERVICE;
    }
    
    // Find available slot using bit manipulation
    uint32_t slot = 0;
    uint32_t mask = ctx->service_array.active_mask;
    while (mask & (1U << slot)) slot++;
    
    if (slot >= POLYCALL_MICRO_MAX_SERVICES) {
        return POLYCALL_MICRO_ERROR_SERVICE;
    }
    
    // Initialize service state in contiguous memory
    PolycallServiceState* service = &ctx->service_array.services[slot];
    reset_service_state(service);
    
    service->id = service_id;
    service->flags = flags;
    service->last_update = get_current_timestamp();
    
    // Update active mask and count
    ctx->service_array.active_mask |= (1U << slot);
    ctx->service_array.count++;
    
    return POLYCALL_MICRO_SUCCESS;
}

// Destroy a service instance
PolycallMicroStatus polycall_micro_destroy_service(
    PolycallMicroContext* ctx,
    uint32_t service_id
) {
    if (!ctx) return POLYCALL_MICRO_ERROR_SERVICE;
    
    // Find service using contiguous memory layout
    for (uint32_t i = 0; i < POLYCALL_MICRO_MAX_SERVICES; i++) {
        if ((ctx->service_array.active_mask & (1U << i)) && 
            ctx->service_array.services[i].id == service_id) {
            
            // Clear service state
            reset_service_state(&ctx->service_array.services[i]);
            
            // Update active mask and count
            ctx->service_array.active_mask &= ~(1U << i);
            ctx->service_array.count--;
            
            return POLYCALL_MICRO_SUCCESS;
        }
    }
    
    return POLYCALL_MICRO_ERROR_SERVICE;
}

// Transform command using point-free style
PolycallMicroStatus polycall_micro_transform_command(
    PolycallCommand* cmd,
    const PolycallTransformChain* chain
) {
    if (!cmd || !chain || !chain->transforms) {
        return POLYCALL_MICRO_ERROR_COMMAND;
    }
    
    // Apply transforms in sequence
    for (uint32_t i = 0; i < chain->transform_count; i++) {
        if (chain->transforms[i]) {
            chain->transforms[i](cmd);
        }
    }
    
    return POLYCALL_MICRO_SUCCESS;
}

// Filter commands using predicate
PolycallMicroStatus polycall_micro_filter_commands(
    PolycallCommandArray* commands,
    PolycallPredicate predicate
) {
    if (!commands || !predicate) {
        return POLYCALL_MICRO_ERROR_COMMAND;
    }
    
    uint32_t write_idx = 0;
    
    // Filter in-place using predicate
    for (uint32_t read_idx = 0; read_idx < commands->count; read_idx++) {
        if (predicate(&commands->commands[read_idx])) {
            if (write_idx != read_idx) {
                memcpy(&commands->commands[write_idx], 
                       &commands->commands[read_idx],
                       sizeof(PolycallCommand));
            }
            write_idx++;
        }
    }
    
    commands->count = write_idx;
    return POLYCALL_MICRO_SUCCESS;
}

// Process commands using operation
PolycallMicroStatus polycall_micro_process_commands(
    PolycallServiceState* service,
    PolycallOperation operation
) {
    if (!service || !operation) {
        return POLYCALL_MICRO_ERROR_COMMAND;
    }
    
    // Apply operation to service state
    operation(service);
    service->last_update = get_current_timestamp();
    
    return POLYCALL_MICRO_SUCCESS;
}

// Batch process commands for a service
PolycallMicroStatus polycall_micro_batch_process(
    PolycallMicroContext* ctx,
    uint32_t service_id,
    const PolycallCommandArray* commands
) {
    if (!ctx || !commands) {
        return POLYCALL_MICRO_ERROR_COMMAND;
    }
    
    // Find service using contiguous memory layout
    PolycallServiceState* service = NULL;
    for (uint32_t i = 0; i < POLYCALL_MICRO_MAX_SERVICES; i++) {
        if ((ctx->service_array.active_mask & (1U << i)) && 
            ctx->service_array.services[i].id == service_id) {
            service = &ctx->service_array.services[i];
            break;
        }
    }
    
    if (!service) {
        return POLYCALL_MICRO_ERROR_SERVICE;
    }
    
    // Process commands in batches
    for (uint32_t i = 0; i < commands->count; i++) {
        const PolycallCommand* cmd = &commands->commands[i];
        
        // Validate command
        if (cmd->payload_size > POLYCALL_MICRO_BUFFER_SIZE) {
            continue;
        }
        
        // Add to service command queue
        if (service->command_queue.count < service->command_queue.capacity) {
            memcpy(&service->command_queue.commands[service->command_queue.count],
                   cmd, sizeof(PolycallCommand));
            service->command_queue.count++;
        }
    }
    
    service->last_update = get_current_timestamp();
    return POLYCALL_MICRO_SUCCESS;
}

// Update service state
PolycallMicroStatus polycall_micro_update_service_state(
    PolycallMicroContext* ctx,
    uint32_t service_id,
    uint32_t new_state
) {
    if (!ctx) return POLYCALL_MICRO_ERROR_SERVICE;
    
    // Find and update service state
    for (uint32_t i = 0; i < POLYCALL_MICRO_MAX_SERVICES; i++) {
        if ((ctx->service_array.active_mask & (1U << i)) && 
            ctx->service_array.services[i].id == service_id) {
            ctx->service_array.services[i].state = new_state;
            ctx->service_array.services[i].last_update = get_current_timestamp();
            return POLYCALL_MICRO_SUCCESS;
        }
    }
    
    return POLYCALL_MICRO_ERROR_SERVICE;
}

// Garbage collection
PolycallMicroStatus polycall_micro_collect_garbage(PolycallMicroContext* ctx) {
    if (!ctx) return POLYCALL_MICRO_ERROR_MEMORY;
    
    uint64_t current_time = get_current_timestamp();
    uint64_t timeout = 3600; // 1 hour timeout
    
    // Clean up inactive services
    for (uint32_t i = 0; i < POLYCALL_MICRO_MAX_SERVICES; i++) {
        if (ctx->service_array.active_mask & (1U << i)) {
            PolycallServiceState* service = &ctx->service_array.services[i];
            
            if (current_time - service->last_update > timeout) {
                polycall_micro_destroy_service(ctx, service->id);
            }
        }
    }
    
    ctx->service_array.last_gc = current_time;
    return POLYCALL_MICRO_SUCCESS;
}

// Get status string
const char* polycall_micro_status_string(PolycallMicroStatus status) {
    switch (status) {
        case POLYCALL_MICRO_SUCCESS: return "Success";
        case POLYCALL_MICRO_ERROR_INIT: return "Initialization error";
        case POLYCALL_MICRO_ERROR_SERVICE: return "Service error";
        case POLYCALL_MICRO_ERROR_COMMAND: return "Command error";
        case POLYCALL_MICRO_ERROR_PROTOCOL: return "Protocol error";
        case POLYCALL_MICRO_ERROR_MEMORY: return "Memory error";
        default: return "Unknown error";
    }
}

// Get active services count
uint32_t polycall_micro_get_active_services(const PolycallMicroContext* ctx) {
    if (!ctx) return 0;
    return ctx->service_array.count;
}

// Create transformation chain
PolycallTransformChain polycall_micro_create_transform_chain(
    PolycallTransform* transforms,
    uint32_t count
) {
    PolycallTransformChain chain = {0};
    
    if (transforms && count > 0) {
        chain.transforms = transforms;
        chain.transform_count = count;
    }
    
    return chain;
}

// Destroy transformation chain
void polycall_micro_destroy_transform_chain(PolycallTransformChain* chain) {
    if (chain) {
        chain->transforms = NULL;
        chain->transform_count = 0;
    }
}