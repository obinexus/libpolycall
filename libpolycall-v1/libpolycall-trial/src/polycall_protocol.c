#include "polycall_protocol.h"
#include <string.h>
#include <stdlib.h>
#include <time.h>

#define MAX_ERROR_LENGTH 256
#define PROTOCOL_BUFFER_SIZE 4096
#define PROTOCOL_MAGIC 0x504C43 // "PLC"
#define PROTOCOL_TIMEOUT_MS 5000
#define MAX_SEQUENCE_NUMBER 0xFFFFFFFF

// Internal protocol error states
static char protocol_error_buffer[MAX_ERROR_LENGTH] = {0};

// Internal protocol context structure
typedef struct {
    polycall_protocol_context_t base;  // Base context
    polycall_protocol_callbacks_t callbacks;  // Callback functions
    char last_error[MAX_ERROR_LENGTH];  // Error buffer
} protocol_context_internal_t;

// Internal protocol error states
// Protocol message validation helper
static bool validate_message_header(const polycall_message_header_t* header) {
    if (!header) return false;
    
    // Check version compatibility
    if (header->version != POLYCALL_PROTOCOL_VERSION) {
        snprintf(protocol_error_buffer, MAX_ERROR_LENGTH,
                "Protocol version mismatch: expected %d, got %d",
                POLYCALL_PROTOCOL_VERSION, header->version);
        return false;
    }
    
    // Validate message type
    if (header->type < POLYCALL_MSG_HANDSHAKE || header->type > POLYCALL_MSG_HEARTBEAT) {
        snprintf(protocol_error_buffer, MAX_ERROR_LENGTH,
                "Invalid message type: %d", header->type);
        return false;
    }
    
    return true;
}

// Protocol state transition helper
static bool transition_protocol_state(
    protocol_context_internal_t* ctx,
    polycall_protocol_state_t new_state
) {
    if (!ctx || !ctx->base.state_machine) return false;
    
    polycall_protocol_state_t old_state = ctx->base.state;
    const char* transition_name = NULL;
    
    // Determine appropriate transition
    switch (new_state) {
        case POLYCALL_STATE_HANDSHAKE:
            transition_name = POLYCALL_TRANSITION_TO_HANDSHAKE;
            break;
        case POLYCALL_STATE_AUTH:
            transition_name = POLYCALL_TRANSITION_TO_AUTH;
            break;
        case POLYCALL_STATE_READY:
            transition_name = POLYCALL_TRANSITION_TO_READY;
            break;
        case POLYCALL_STATE_ERROR:
            transition_name = POLYCALL_TRANSITION_TO_ERROR;
            break;
        case POLYCALL_STATE_CLOSED:
            transition_name = POLYCALL_TRANSITION_TO_CLOSED;
            break;
        default:
            return false;
    }
    
    // Execute state machine transition
    if (polycall_sm_execute_transition(ctx->base.state_machine, transition_name) 
        != POLYCALL_SM_SUCCESS) {
        return false;
    }
    
    ctx->base.state = new_state;
    
    // Notify state change
    if (ctx->base.state != old_state && ctx->callbacks.on_state_change) {
        ctx->callbacks.on_state_change(&ctx->base, old_state, new_state);
    }
    
    return true;
}

// Initialize protocol context
bool polycall_protocol_init(
    polycall_protocol_context_t* ctx,
    polycall_context_t pc_ctx,
    NetworkEndpoint* endpoint,
    const polycall_protocol_config_t* config
) {
    if (!ctx || !pc_ctx || !endpoint || !config) {
        snprintf(protocol_error_buffer, MAX_ERROR_LENGTH, "Invalid parameters");
        return false;
    }
    
    protocol_context_internal_t* internal_ctx = calloc(1, sizeof(protocol_context_internal_t));
    if (!internal_ctx) {
        snprintf(protocol_error_buffer, MAX_ERROR_LENGTH, "Memory allocation failed");
        return false;
    }

    // Initialize base context
    internal_ctx->base.pc_ctx = pc_ctx;
    internal_ctx->base.endpoint = endpoint;
    internal_ctx->base.state = POLYCALL_STATE_INIT;
    internal_ctx->base.next_sequence = 1;
    internal_ctx->base.user_data = config->user_data;
    
    // Copy callbacks
    memcpy(&internal_ctx->callbacks, &config->callbacks, sizeof(polycall_protocol_callbacks_t));
    
    // Initialize state machine
    polycall_sm_status_t sm_status = polycall_sm_create_with_integrity(
        pc_ctx,
        &internal_ctx->base.state_machine,
        NULL  // No integrity check for now
    );
    
    if (sm_status != POLYCALL_SM_SUCCESS) {
        snprintf(protocol_error_buffer, MAX_ERROR_LENGTH,
                "Failed to create protocol state machine");
        free(internal_ctx);
        return false;
    }
    
    // Copy internal context back to provided context
    memcpy(ctx, &internal_ctx->base, sizeof(polycall_protocol_context_t));
    
    return true;
}

void polycall_protocol_cleanup(polycall_protocol_context_t* ctx) {
    if (!ctx) return;
    
    protocol_context_internal_t* internal_ctx = (protocol_context_internal_t*)ctx;
    
    // Clean up state machine
    if (ctx->state_machine) {
        polycall_sm_destroy(ctx->state_machine);
        ctx->state_machine = NULL;
    }
    
    // Clean up context
    free(internal_ctx);
}

// Protocol message handling
bool polycall_protocol_send(
    polycall_protocol_context_t* ctx,
    polycall_message_type_t type,
    const void* payload,
    size_t payload_length,
    polycall_protocol_flags_t flags
) {
    if (!ctx || !ctx->endpoint || !payload || payload_length == 0) {
        return false;
    }
    
    // Create message header
    polycall_message_header_t header = {
        .version = POLYCALL_PROTOCOL_VERSION,
        .type = type,
        .flags = flags,
        .sequence = ctx->next_sequence++,
        .payload_length = payload_length,
        .checksum = 0
    };
    
    // Calculate checksum
    header.checksum = polycall_protocol_calculate_checksum(payload, payload_length);
    
    // Prepare network packet
    uint8_t buffer[PROTOCOL_BUFFER_SIZE];
    
    // Copy header and payload to buffer
    size_t total_size = sizeof(header) + payload_length;
    if (total_size > PROTOCOL_BUFFER_SIZE) {
        snprintf(protocol_error_buffer, MAX_ERROR_LENGTH,
                "Message too large: %zu bytes", total_size);
        return false;
    }
    
    memcpy(buffer, &header, sizeof(header));
    memcpy(buffer + sizeof(header), payload, payload_length);
    
    NetworkPacket packet = {
        .data = buffer,
        .size = total_size,
        .flags = 0
    };
    
    return net_send(ctx->endpoint, &packet) == (ssize_t)total_size;
}


bool polycall_protocol_process(
    polycall_protocol_context_t* ctx,
    const void* data,
    size_t length
) {
    if (!ctx || !data || length < sizeof(polycall_message_header_t)) {
        return false;
    }
    
    protocol_context_internal_t* internal_ctx = (protocol_context_internal_t*)ctx;
    const polycall_message_header_t* header = (const polycall_message_header_t*)data;
    const void* payload = (const uint8_t*)data + sizeof(polycall_message_header_t);
    size_t payload_length = length - sizeof(polycall_message_header_t);
    
    // Validate message
    if (!validate_message_header(header)) {
        return false;
    }
    
    // Verify checksum
    if (!polycall_protocol_verify_checksum(header, payload, payload_length)) {
        snprintf(protocol_error_buffer, MAX_ERROR_LENGTH, "Checksum verification failed");
        return false;
    }
    
    // Process message based on type
    switch (header->type) {
        case POLYCALL_MSG_HANDSHAKE:
            if (internal_ctx->callbacks.on_handshake) {
                internal_ctx->callbacks.on_handshake(&internal_ctx->base);
            }
            break;
            
        case POLYCALL_MSG_AUTH:
            if (internal_ctx->callbacks.on_auth_request) {
                internal_ctx->callbacks.on_auth_request(&internal_ctx->base, payload);
            }
            break;
            
        case POLYCALL_MSG_COMMAND:
            if (internal_ctx->callbacks.on_command) {
                internal_ctx->callbacks.on_command(&internal_ctx->base, payload, payload_length);
            }
            break;
            
        case POLYCALL_MSG_ERROR:
            if (internal_ctx->callbacks.on_error) {
                internal_ctx->callbacks.on_error(&internal_ctx->base, payload);
            }
            break;
            
        case POLYCALL_MSG_HEARTBEAT:
            // Process heartbeat
            break;
            
        default:
            return false;
    }
    
    return true;
}

void polycall_protocol_update(polycall_protocol_context_t* ctx) {
    if (!ctx) return;
    
    protocol_context_internal_t* internal_ctx = (protocol_context_internal_t*)ctx;
    
    // Process any pending state transitions
    switch (ctx->state) {
        case POLYCALL_STATE_INIT:
            if (polycall_protocol_can_transition(ctx, POLYCALL_STATE_HANDSHAKE)) {
                polycall_protocol_start_handshake(ctx);
            }
            break;
            
        case POLYCALL_STATE_HANDSHAKE:
            if (polycall_protocol_can_transition(ctx, POLYCALL_STATE_AUTH)) {
                transition_protocol_state(internal_ctx, POLYCALL_STATE_AUTH);
            }
            break;
            
        case POLYCALL_STATE_AUTH:
            if (polycall_protocol_can_transition(ctx, POLYCALL_STATE_READY)) {
                transition_protocol_state(internal_ctx, POLYCALL_STATE_READY);
            }
            break;
            
        default:
            break;
    }
}


// Get current protocol state
polycall_protocol_state_t polycall_protocol_get_state(
    const polycall_protocol_context_t* ctx
) {
    return ctx ? ctx->state : POLYCALL_STATE_ERROR;
}

// Protocol state transition validation
bool polycall_protocol_can_transition(
    const polycall_protocol_context_t* ctx,
    polycall_protocol_state_t target_state
) {
    if (!ctx || !ctx->state_machine) return false;
    
    // Check if target state is valid based on current state
    switch (ctx->state) {
        case POLYCALL_STATE_INIT:
            return target_state == POLYCALL_STATE_HANDSHAKE;
            
        case POLYCALL_STATE_HANDSHAKE:
            return target_state == POLYCALL_STATE_AUTH;
            
        case POLYCALL_STATE_AUTH:
            return target_state == POLYCALL_STATE_READY;
            
        case POLYCALL_STATE_READY:
            return target_state == POLYCALL_STATE_ERROR ||
                   target_state == POLYCALL_STATE_CLOSED;
            
        case POLYCALL_STATE_ERROR:
            return target_state == POLYCALL_STATE_CLOSED;
            
        default:
            return false;
    }
}

bool polycall_protocol_start_handshake(polycall_protocol_context_t* ctx) {
    if (!ctx || ctx->state != POLYCALL_STATE_INIT) return false;
    
    protocol_context_internal_t* internal_ctx = (protocol_context_internal_t*)ctx;
    
    // Create handshake payload
    struct {
        uint32_t magic;
        uint8_t version;
        uint16_t flags;
    } handshake = {
        .magic = PROTOCOL_MAGIC,
        .version = POLYCALL_PROTOCOL_VERSION,
        .flags = 0
    };
    
    // Send handshake message
    if (!polycall_protocol_send(ctx, POLYCALL_MSG_HANDSHAKE,
                               &handshake, sizeof(handshake),
                               POLYCALL_FLAG_RELIABLE)) {
        return false;
    }
    
    return transition_protocol_state(internal_ctx, POLYCALL_STATE_HANDSHAKE);
}

bool polycall_protocol_complete_handshake(polycall_protocol_context_t* ctx) {
    if (!ctx || ctx->state != POLYCALL_STATE_HANDSHAKE) return false;
    protocol_context_internal_t* internal_ctx = (protocol_context_internal_t*)ctx;
    return transition_protocol_state(internal_ctx, POLYCALL_STATE_AUTH);
}

bool polycall_protocol_authenticate(
    polycall_protocol_context_t* ctx,
    const char* credentials,
    size_t credentials_length
) {
    if (!ctx || !credentials || credentials_length == 0) return false;
    
    protocol_context_internal_t* internal_ctx = (protocol_context_internal_t*)ctx;
    
    // Send authentication message
    if (!polycall_protocol_send(ctx, POLYCALL_MSG_AUTH,
                               credentials, credentials_length,
                               POLYCALL_FLAG_ENCRYPTED | POLYCALL_FLAG_RELIABLE)) {
        return false;
    }
    
    return transition_protocol_state(internal_ctx, POLYCALL_STATE_READY);
}




void polycall_protocol_set_error(polycall_protocol_context_t* ctx, const char* error) {
    if (!ctx || !error) return;
    protocol_context_internal_t* internal_ctx = (protocol_context_internal_t*)ctx;
    snprintf(internal_ctx->last_error, MAX_ERROR_LENGTH, "%s", error);
    transition_protocol_state(internal_ctx, POLYCALL_STATE_ERROR);
}

// Protocol utility functions
uint32_t polycall_protocol_calculate_checksum(
    const void* data,
    size_t length
) {
    if (!data || length == 0) return 0;
    
    const uint8_t* bytes = (const uint8_t*)data;
    uint32_t checksum = 0;
    
    for (size_t i = 0; i < length; i++) {
        checksum = ((checksum << 5) | (checksum >> 27)) + bytes[i];
    }
    
    return checksum;
}

bool polycall_protocol_verify_checksum(
    const polycall_message_header_t* header,
    const void* payload,
    size_t payload_length
) {
    if (!header || !payload || payload_length == 0) return false;
    
    uint32_t calculated = polycall_protocol_calculate_checksum(payload, payload_length);
    return calculated == header->checksum;
}



// Protocol version compatibility check
bool polycall_protocol_version_compatible(uint8_t remote_version) {
    return remote_version == POLYCALL_PROTOCOL_VERSION;
}

// Create protocol message header
polycall_message_header_t polycall_protocol_create_header(
    polycall_message_type_t type,
    size_t payload_length,
    polycall_protocol_flags_t flags
) {
    polycall_message_header_t header = {
        .version = POLYCALL_PROTOCOL_VERSION,
        .type = type,
        .flags = flags,
        .sequence = 0,  // Will be set by send function
        .payload_length = payload_length,
        .checksum = 0   // Will be calculated by send function
    };
    
    return header;
}

// Protocol state observers
bool polycall_protocol_is_connected(const polycall_protocol_context_t* ctx) {
    if (!ctx) return false;
    return ctx->state >= POLYCALL_STATE_HANDSHAKE && 
           ctx->state < POLYCALL_STATE_ERROR;
}

bool polycall_protocol_is_authenticated(const polycall_protocol_context_t* ctx) {
    if (!ctx) return false;
    return ctx->state >= POLYCALL_STATE_READY && 
           ctx->state < POLYCALL_STATE_ERROR;
}

bool polycall_protocol_is_error(const polycall_protocol_context_t* ctx) {
    if (!ctx) return true;
    return ctx->state == POLYCALL_STATE_ERROR;
}