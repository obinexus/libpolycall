#include "polycall.h"
#include <stdlib.h>
#include <string.h>

#define POLYCALL_VERSION "1.0.0"
#define MAX_ERROR_LENGTH 256

/* Internal context structure */
struct polycall_context {
    char last_error[MAX_ERROR_LENGTH];
    void* user_data;
    size_t memory_pool_size;
    unsigned int flags;
    bool is_initialized;
};

/* Static helper functions */
static void set_error(polycall_context_t ctx, const char* error) {
    if (ctx && error) {
        strncpy(ctx->last_error, error, MAX_ERROR_LENGTH - 1);
        ctx->last_error[MAX_ERROR_LENGTH - 1] = '\0';
    }
}

/* API Implementation */

polycall_status_t polycall_init_with_config(
    polycall_context_t* ctx, 
    const polycall_config_t* config
) {
    if (!ctx) {
        // Use the error function
        set_error(NULL, "Invalid context pointer");
        return POLYCALL_ERROR_INVALID_PARAMETERS;
    }

    /* Allocate context */
    struct polycall_context* new_ctx = malloc(sizeof(struct polycall_context));
    if (!new_ctx) {
        return POLYCALL_ERROR_OUT_OF_MEMORY;
    }

    /* Initialize context with defaults */
    memset(new_ctx, 0, sizeof(struct polycall_context));
    new_ctx->memory_pool_size = 1024 * 1024; /* 1MB default */
    new_ctx->flags = 0;

    /* Apply configuration if provided */
    if (config) {
        new_ctx->flags = config->flags;
        new_ctx->memory_pool_size = config->memory_pool_size > 0 ? 
                                  config->memory_pool_size : new_ctx->memory_pool_size;
        new_ctx->user_data = config->user_data;
    }

    /* Mark as initialized */
    new_ctx->is_initialized = true;
    new_ctx->last_error[0] = '\0';

    *ctx = new_ctx;
    return POLYCALL_SUCCESS;
}

void polycall_cleanup(polycall_context_t ctx) {
    if (ctx) {
        /* Add any cleanup of internal resources here */
        ctx->is_initialized = false;
        free(ctx);
    }
}

const char* polycall_get_version(void) {
    return POLYCALL_VERSION;
}

const char* polycall_get_last_error(polycall_context_t ctx) {
    if (!ctx) {
        return "Invalid context";
    }
    return ctx->last_error;
}