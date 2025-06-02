#ifndef POLYCALL_PROTOCOL_H
#define POLYCALL_PROTOCOL_H

#include "polycall.h"
#include "polycall_state_machine.h"
#include "network.h"
#include <stdint.h>
#include <stdbool.h>

// Protocol version
#define POLYCALL_PROTOCOL_VERSION 1

// Protocol message types
typedef enum {
    POLYCALL_MSG_HANDSHAKE = 0x01,
    POLYCALL_MSG_AUTH = 0x02,
    POLYCALL_MSG_COMMAND = 0x03,
    POLYCALL_MSG_RESPONSE = 0x04,
    POLYCALL_MSG_ERROR = 0x05,
    POLYCALL_MSG_HEARTBEAT = 0x06
} polycall_message_type_t;

// Protocol states
typedef enum {
    POLYCALL_STATE_INIT = 0,
    POLYCALL_STATE_HANDSHAKE,
    POLYCALL_STATE_AUTH,
    POLYCALL_STATE_READY,
    POLYCALL_STATE_ERROR,
    POLYCALL_STATE_CLOSED
} polycall_protocol_state_t;

// Protocol flags
typedef enum {
    POLYCALL_FLAG_NONE = 0x00,
    POLYCALL_FLAG_ENCRYPTED = 0x01,
    POLYCALL_FLAG_COMPRESSED = 0x02,
    POLYCALL_FLAG_URGENT = 0x04,
    POLYCALL_FLAG_RELIABLE = 0x08
} polycall_protocol_flags_t;

// Protocol message header
typedef struct {
    uint8_t version;
    uint8_t type;
    uint16_t flags;
    uint32_t sequence;
    uint32_t payload_length;
    uint32_t checksum;
} polycall_message_header_t;

// Protocol session context
typedef struct {
    polycall_context_t pc_ctx;
    PolyCall_StateMachine* state_machine;
    NetworkEndpoint* endpoint;
    uint32_t next_sequence;
    polycall_protocol_state_t state;
    void* user_data;
} polycall_protocol_context_t;

// Protocol callbacks
typedef struct {
    void (*on_handshake)(polycall_protocol_context_t* ctx);
    void (*on_auth_request)(polycall_protocol_context_t* ctx, const char* credentials);
    void (*on_command)(polycall_protocol_context_t* ctx, const char* command, size_t length);
    void (*on_error)(polycall_protocol_context_t* ctx, const char* error);
    void (*on_state_change)(polycall_protocol_context_t* ctx, polycall_protocol_state_t old_state, 
                           polycall_protocol_state_t new_state);
} polycall_protocol_callbacks_t;

// Protocol configuration
typedef struct {
    polycall_protocol_callbacks_t callbacks;
    polycall_protocol_flags_t flags;
    size_t max_message_size;
    uint32_t timeout_ms;
    void* user_data;
} polycall_protocol_config_t;

// Initialize protocol context
bool polycall_protocol_init(
    polycall_protocol_context_t* ctx,
    polycall_context_t pc_ctx,
    NetworkEndpoint* endpoint,
    const polycall_protocol_config_t* config
);

// Clean up protocol context
void polycall_protocol_cleanup(polycall_protocol_context_t* ctx);

// Send protocol message
bool polycall_protocol_send(
    polycall_protocol_context_t* ctx,
    polycall_message_type_t type,
    const void* payload,
    size_t payload_length,
    polycall_protocol_flags_t flags
);

// Process incoming protocol message
bool polycall_protocol_process(
    polycall_protocol_context_t* ctx,
    const void* data,
    size_t length
);

// Update protocol state
void polycall_protocol_update(polycall_protocol_context_t* ctx);

// Get current protocol state
polycall_protocol_state_t polycall_protocol_get_state(
    const polycall_protocol_context_t* ctx
);

// State transition validation
bool polycall_protocol_can_transition(
    const polycall_protocol_context_t* ctx,
    polycall_protocol_state_t target_state
);

// Protocol handshake helpers
bool polycall_protocol_start_handshake(polycall_protocol_context_t* ctx);
bool polycall_protocol_complete_handshake(polycall_protocol_context_t* ctx);

// Protocol authentication helpers
bool polycall_protocol_authenticate(
    polycall_protocol_context_t* ctx,
    const char* credentials,
    size_t credentials_length
);

// Protocol error handling
const char* polycall_protocol_get_error(const polycall_protocol_context_t* ctx);
void polycall_protocol_set_error(
    polycall_protocol_context_t* ctx,
    const char* error
);

// Protocol utility functions
uint32_t polycall_protocol_calculate_checksum(
    const void* data,
    size_t length
);

bool polycall_protocol_verify_checksum(
    const polycall_message_header_t* header,
    const void* payload,
    size_t payload_length
);

// Protocol state machine transitions
#define POLYCALL_TRANSITION_TO_HANDSHAKE "to_handshake"
#define POLYCALL_TRANSITION_TO_AUTH "to_auth"
#define POLYCALL_TRANSITION_TO_READY "to_ready"
#define POLYCALL_TRANSITION_TO_ERROR "to_error"
#define POLYCALL_TRANSITION_TO_CLOSED "to_closed"

// Protocol version compatibility check
bool polycall_protocol_version_compatible(uint8_t remote_version);

// Protocol message construction helpers
polycall_message_header_t polycall_protocol_create_header(
    polycall_message_type_t type,
    size_t payload_length,
    polycall_protocol_flags_t flags
);

// Protocol state observers
bool polycall_protocol_is_connected(const polycall_protocol_context_t* ctx);
bool polycall_protocol_is_authenticated(const polycall_protocol_context_t* ctx);
bool polycall_protocol_is_error(const polycall_protocol_context_t* ctx);

#endif // POLYCALL_PROTOCOL_H