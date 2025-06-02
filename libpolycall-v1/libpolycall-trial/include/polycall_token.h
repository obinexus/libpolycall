#ifndef POLYCALL_TOKEN_H
#define POLYCALL_TOKEN_H

#include <stdint.h>
#include <stdbool.h>

#ifdef __cplusplus
extern "C" {
#endif

// Value types with strict type safety
typedef enum {
    VALUE_NONE = 0,
    VALUE_INTEGER,
    VALUE_FLOAT,
    VALUE_STRING,
    VALUE_IDENTIFIER
} PolycallValueType;

// Value storage using tagged union for type safety
typedef struct {
    PolycallValueType type;
    union {
        int64_t int_value;
        double float_value;
        struct {
            const char* data;
            uint32_t length;
        } string_value;
    } data;
} PolycallValue;

// Token types as bit flags for efficient comparison
typedef enum {
    TOKEN_INVALID     = 0x00,
    TOKEN_IDENTIFIER  = 0x01,
    TOKEN_NUMBER      = 0x02,
    TOKEN_STRING      = 0x04,
    TOKEN_OPERATOR    = 0x08,
    TOKEN_KEYWORD     = 0x10,
    TOKEN_SEPARATOR   = 0x20,
    TOKEN_COMMENT     = 0x40,
    TOKEN_EOF         = 0x80
} PolycallTokenType;

// Token metadata flags
typedef enum {
    TOKEN_FLAG_NONE      = 0x00,
    TOKEN_FLAG_START     = 0x01,
    TOKEN_FLAG_END       = 0x02,
    TOKEN_FLAG_ERROR     = 0x04,
    TOKEN_FLAG_MODIFIED  = 0x08,
    TOKEN_FLAG_RESERVED  = 0x10
} PolycallTokenFlags;

// Token structure optimized for cache alignment
typedef struct {
    PolycallValue value;          // 24 bytes - Value with type tag
    PolycallTokenType type;       // 4 bytes - Token type
    uint32_t flags;               // 4 bytes - Metadata flags
    uint32_t line;                // 4 bytes - Source location
    uint32_t column;              // 4 bytes - Source location
    uint32_t length;              // 4 bytes - Token length
} PolycallToken;                  // Total: 44 bytes aligned

// Contiguous token storage for batch processing
typedef struct {
    PolycallToken* tokens;        // Token array
    uint32_t count;               // Current count
    uint32_t capacity;            // Maximum capacity
    uint32_t error_count;         // Error tracking
    struct {                      // Position tracking
        uint32_t line;
        uint32_t column;
    } position;
} PolycallTokenArray;

// Point-free operation types
typedef PolycallToken (*TokenOperation)(const PolycallToken*);
typedef bool (*TokenPredicate)(const PolycallToken*);

// Operation chain for composition
typedef struct {
    TokenOperation* operations;    // Operation array
    uint32_t count;               // Operation count
} PolycallTokenOperations;

// Core token functions using point-free style
PolycallTokenArray* polycall_token_create_array(uint32_t capacity);
void polycall_token_destroy_array(PolycallTokenArray* array);

// Token operations
PolycallToken polycall_token_map(const PolycallToken* token, TokenOperation op);
PolycallTokenArray* polycall_token_filter(const PolycallTokenArray* array, TokenPredicate pred);
PolycallTokenArray* polycall_token_chain(const PolycallTokenArray* array, const PolycallTokenOperations* ops);

// Value operations
PolycallValue polycall_value_create(PolycallValueType type, const void* data);
void polycall_value_destroy(PolycallValue* value);
bool polycall_value_equals(const PolycallValue* a, const PolycallValue* b);

#ifdef __cplusplus
}
#endif

#endif // POLYCALL_TOKEN_H