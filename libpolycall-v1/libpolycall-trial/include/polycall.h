#ifndef POLYCALL_H
#define POLYCALL_H

#include <stddef.h>
#include <stdbool.h>

#ifdef __cplusplus
extern "C" {
#endif

/* Constants */
#define POLYCALL_MAX_NAME_LENGTH 32
#define POLYCALL_MAX_STATES 32
#define POLYCALL_MAX_TRANSITIONS 64

/* Forward declarations */
struct polycall_context;
typedef struct polycall_context* polycall_context_t;

/* Type definitions */
typedef void (*PolyCall_StateAction)(polycall_context_t ctx);

/* Status codes */
typedef enum {
    POLYCALL_SUCCESS = 0,
    POLYCALL_ERROR_INVALID_PARAMETERS,
    POLYCALL_ERROR_INITIALIZATION_FAILED,
    POLYCALL_ERROR_OUT_OF_MEMORY,
    POLYCALL_ERROR
} polycall_status_t;

/* Configuration structure */
typedef struct polycall_config {
    unsigned int flags;
    size_t memory_pool_size;
    void* user_data;
} polycall_config_t;

/* API Functions */

/**
 * Initialize the PolyCall library with configuration
 * 
 * @param ctx Pointer to receive the created context
 * @param config Pointer to configuration structure
 * @return Status code indicating success or failure
 */
polycall_status_t polycall_init_with_config(
    polycall_context_t* ctx, 
    const polycall_config_t* config
);

/**
 * Clean up and release resources associated with a PolyCall context
 * 
 * @param ctx Context to clean up
 */
void polycall_cleanup(polycall_context_t ctx);

/**
 * Get the version string of the PolyCall library
 * 
 * @return Null-terminated version string
 */
const char* polycall_get_version(void);

/**
 * Get the last error message from the PolyCall library
 * 
 * @param ctx Context to get error from
 * @return Null-terminated error message string
 */
const char* polycall_get_last_error(polycall_context_t ctx);

#ifdef __cplusplus
}
#endif

#endif /* POLYCALL_H */