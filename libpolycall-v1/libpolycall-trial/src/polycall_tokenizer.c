#include "polycall_tokenizer.h"
#include <stdlib.h>
#include <string.h>
#include <ctype.h>

// Default configuration values
#define DEFAULT_BUFFER_SIZE 4096
#define DEFAULT_TOKEN_LENGTH 256
#define DEFAULT_IDENTIFIER_LENGTH 64
#define DEFAULT_STRING_LENGTH 1024

// Error messages
static const char* ERROR_BUFFER_OVERFLOW = "Buffer overflow";
static const char* ERROR_INVALID_INPUT = "Invalid input";

// Default configuration
const PolycallTokenizerConfig POLYCALL_TOKENIZER_DEFAULT_CONFIG = {
    .limits = {
        .buffer = DEFAULT_BUFFER_SIZE,
        .token = DEFAULT_TOKEN_LENGTH,
        .identifier = DEFAULT_IDENTIFIER_LENGTH,
        .string = DEFAULT_STRING_LENGTH
    },
    .flags = 0
};

// Internal helper functions for state management
static void set_error_state(PolycallTokenizer* tokenizer, const char* message) {
    if (!tokenizer) return;
    
    tokenizer->state.current = TOKENIZER_STATE_ERROR;
    if (tokenizer->state.error_message) {
        free(tokenizer->state.error_message);
    }
    tokenizer->state.error_message = strdup(message);
    tokenizer->state.error_count++;
}

static void reset_state(PolycallTokenizer* tokenizer) {
    if (!tokenizer) return;
    
    tokenizer->state.current = TOKENIZER_STATE_READY;
    tokenizer->position.line = 1;
    tokenizer->position.column = 1;
    tokenizer->input.position = 0;
    
    if (tokenizer->state.error_message) {
        free(tokenizer->state.error_message);
        tokenizer->state.error_message = NULL;
    }
}

// Token pattern matching implementation
static bool is_identifier_start(char c) {
    return isalpha(c) || c == '_';
}

static bool is_identifier_part(char c) {
    return isalnum(c) || c == '_';
}

// Pattern matching functions
bool polycall_tokenizer_match_identifier(const char* input, size_t* length) {
    if (!input || !length) return false;
    
    if (!is_identifier_start(*input)) return false;
    
    size_t pos = 1;
    while (is_identifier_part(input[pos])) pos++;
    
    *length = pos;
    return true;
}

bool polycall_tokenizer_match_number(const char* input, size_t* length) {
    if (!input || !length) return false;
    
    size_t pos = 0;
    
    // Handle optional sign
    if (input[pos] == '+' || input[pos] == '-') pos++;
    // Must have at least one digit
    if (!isdigit(input[pos])) return false;
    
    // Match digits before decimal
    while (isdigit(input[pos])) pos++;
    
   // Handle decimal point and following digits
    if (input[pos] == '.') {
        pos++;
        if (!isdigit(input[pos])) return false;
        while (isdigit(input[pos])) pos++;
    }
    
    // Handle scientific notation
    if ((input[pos] == 'e' || input[pos] == 'E') && pos > 0) {
        size_t exp_pos = pos + 1;
        if (input[exp_pos] == '+' || input[exp_pos] == '-') exp_pos++;
        if (!isdigit(input[exp_pos])) return false;  // Must have digits after E
        while (isdigit(input[exp_pos])) exp_pos++;
        pos = exp_pos;
    }
    
    *length = pos;
    return true;
}

bool polycall_tokenizer_match_string(const char* input, size_t* length) {
    if (!input || !length || *input != '"') return false;
    
    size_t pos = 1;
    bool escaped = false;
    
    while (input[pos] && (escaped || input[pos] != '"')) {
        if (escaped) {
            escaped = false;
        } else if (input[pos] == '\\') {
            escaped = true;
        }
        pos++;
    }
    
    if (input[pos] == '"') {
        *length = pos + 1;
        return true;
    }
    
    return false;
}

bool polycall_tokenizer_match_operator(const char* input, size_t* length) {
    if (!input || !length) return false;
    
    static const char* operators[] = {
        "++", "--", "+=", "-=", "*=", "/=", 
        "==", "!=", ">=", "<=", "&&", "||",
        "+", "-", "*", "/", "%", 
        "=", "<", ">", "!", "&", "|", 
        NULL
    };
    
    for (const char** op = operators; *op; op++) {
        size_t op_len = strlen(*op);
        if (strncmp(input, *op, op_len) == 0) {
            *length = op_len;
            return true;
        }
    }
    
    return false;
}

// Tokenizer management functions
PolycallTokenizer* polycall_tokenizer_create(const PolycallTokenizerConfig* config) {
    PolycallTokenizer* tokenizer = calloc(1, sizeof(PolycallTokenizer));
    if (!tokenizer) return NULL;
    
    const PolycallTokenizerConfig* actual_config = 
        config ? config : &POLYCALL_TOKENIZER_DEFAULT_CONFIG;
    
    // Allocate input buffer
    tokenizer->input.buffer = malloc(actual_config->limits.buffer);
    if (!tokenizer->input.buffer) {
        free(tokenizer);
        return NULL;
    }
    
    tokenizer->input.size = actual_config->limits.buffer;
    tokenizer->config = actual_config;
    
    // Initialize token array
    tokenizer->tokens = polycall_token_create_array(
        actual_config->limits.buffer / actual_config->limits.token
    );
    
    if (!tokenizer->tokens) {
        free(tokenizer->input.buffer);
        free(tokenizer);
        return NULL;
    }
    
    reset_state(tokenizer);
    return tokenizer;
}

void polycall_tokenizer_destroy(PolycallTokenizer* tokenizer) {
    if (!tokenizer) return;
    
    if (tokenizer->input.buffer) {
        free(tokenizer->input.buffer);
    }
    
    if (tokenizer->tokens) {
        polycall_token_destroy_array(tokenizer->tokens);
    }
    
    if (tokenizer->state.error_message) {
        free(tokenizer->state.error_message);
    }
    
    free(tokenizer);
}
void polycall_tokenizer_reset(PolycallTokenizer* tokenizer) {
    if (!tokenizer) return;
    
    reset_state(tokenizer);
    
    // Clear token array directly instead of using separate function
    if (tokenizer->tokens) {
        tokenizer->tokens->count = 0;
        tokenizer->tokens->error_count = 0;
        tokenizer->tokens->position.line = 1;
        tokenizer->tokens->position.column = 1;
    }
}

bool polycall_tokenizer_set_input(
    PolycallTokenizer* tokenizer,
    const char* input,
    size_t length
) {
    if (!tokenizer || !input || length == 0) {
        return false;
    }
    
    if (length > tokenizer->input.size) {
        set_error_state(tokenizer, ERROR_BUFFER_OVERFLOW);
        return false;
    }
    
    memcpy(tokenizer->input.buffer, input, length);
    tokenizer->input.buffer[length] = '\0';
    tokenizer->input.position = 0;
    
    reset_state(tokenizer);
    return true;
}

// Token creation and processing
static PolycallToken create_token(
    PolycallTokenizer* tokenizer,
    PolycallTokenType type,
    const char* start,
    size_t length
) {
    PolycallToken token = {
        .type = type,
        .value = { .type = VALUE_NONE },
        .flags = TOKEN_FLAG_NONE,
        .line = tokenizer->position.line,
        .column = tokenizer->position.column,
        .length = length
    };
    
    // Set value based on token type
    switch (type) {
        case TOKEN_IDENTIFIER:
            token.value.type = VALUE_IDENTIFIER;
            token.value.data.string_value.data = start;
            token.value.data.string_value.length = length;
            break;
            
        case TOKEN_NUMBER:
            token.value.type = VALUE_FLOAT;
            token.value.data.float_value = strtod(start, NULL);
            if (strchr(start, '.') == NULL) {
                token.value.type = VALUE_INTEGER;
                token.value.data.int_value = strtoll(start, NULL, 10);
            }
            break;
            
        case TOKEN_STRING:
            token.value.type = VALUE_STRING;
            token.value.data.string_value.data = start + 1;  // Skip opening quote
            token.value.data.string_value.length = length - 2;  // Remove quotes
            break;
            
        default:
            break;
    }
    
    return token;
}
bool polycall_tokenizer_process(
    PolycallTokenizer* tokenizer,
    const TokenizerOperations* ops
) {
    if (!tokenizer || !ops) return false;
    
    tokenizer->state.current = TOKENIZER_STATE_SCANNING;
    
    while (tokenizer->input.position < tokenizer->input.size) {
        const char* current = tokenizer->input.buffer + tokenizer->input.position;
        
        // Skip whitespace
        if (isspace(*current)) {
            if (*current == '\n') {
                tokenizer->position.line++;
                tokenizer->position.column = 1;
            } else {
                tokenizer->position.column++;
            }
            tokenizer->input.position++;
            continue;
        }
        
        // Try each pattern matcher
        bool matched = false;
        for (size_t i = 0; i < ops->count; i++) {
            size_t length = 0;
            if (ops->patterns[i].match(current, &length)) {
                PolycallToken token = create_token(
                    tokenizer,
                    ops->patterns[i].produces,
                    current,
                    length
                );
                
                // Apply consumer if available
                if (ops->consumers[i].accepts == token.type) {
                    ops->consumers[i].consume(&token);
                }
                
                // Add token to the array using the array's add function
                if (tokenizer->tokens) {
                    if (tokenizer->tokens->count < tokenizer->tokens->capacity) {
                        tokenizer->tokens->tokens[tokenizer->tokens->count++] = token;
                    }
                }
                
                tokenizer->input.position += length;
                tokenizer->position.column += length;
                matched = true;
                break;
            }
        }
        
        if (!matched) {
            set_error_state(tokenizer, ERROR_INVALID_INPUT);
            return false;
        }
    }
    
    // Add EOF token
    PolycallToken eof_token = {
        .type = TOKEN_EOF,
        .value = { .type = VALUE_NONE },
        .flags = TOKEN_FLAG_NONE,
        .line = tokenizer->position.line,
        .column = tokenizer->position.column,
        .length = 0
    };
    
    if (tokenizer->tokens && tokenizer->tokens->count < tokenizer->tokens->capacity) {
        tokenizer->tokens->tokens[tokenizer->tokens->count++] = eof_token;
    }
    
    tokenizer->state.current = TOKENIZER_STATE_READY;
    return true;
}

// Operation management
TokenizerOperations* polycall_tokenizer_create_ops(
    TokenPattern* patterns,
    TokenConsumer* consumers,
    size_t count
) {
    if (!patterns || !consumers || count == 0) return NULL;
    
    TokenizerOperations* ops = malloc(sizeof(TokenizerOperations));
    if (!ops) return NULL;
    
    ops->patterns = malloc(sizeof(TokenPattern) * count);
    ops->consumers = malloc(sizeof(TokenConsumer) * count);
    
    if (!ops->patterns || !ops->consumers) {
        polycall_tokenizer_destroy_ops(ops);
        return NULL;
    }
    
    memcpy(ops->patterns, patterns, sizeof(TokenPattern) * count);
    memcpy(ops->consumers, consumers, sizeof(TokenConsumer) * count);
    ops->count = count;
    
    return ops;
}

TokenizerOperations* polycall_tokenizer_compose_ops(
    const TokenizerOperations* ops1,
    const TokenizerOperations* ops2
) {
    if (!ops1 || !ops2) return NULL;
    
    size_t total_count = ops1->count + ops2->count;
    TokenizerOperations* result = malloc(sizeof(TokenizerOperations));
    if (!result) return NULL;
    
    result->patterns = malloc(sizeof(TokenPattern) * total_count);
    result->consumers = malloc(sizeof(TokenConsumer) * total_count);
    
    if (!result->patterns || !result->consumers) {
        polycall_tokenizer_destroy_ops(result);
        return NULL;
    }
    
    // Combine operations
    memcpy(result->patterns, ops1->patterns, sizeof(TokenPattern) * ops1->count);
    memcpy(result->patterns + ops1->count, ops2->patterns, sizeof(TokenPattern) * ops2->count);
    
    memcpy(result->consumers, ops1->consumers, sizeof(TokenConsumer) * ops1->count);
    memcpy(result->consumers + ops1->count, ops2->consumers, sizeof(TokenConsumer) * ops2->count);
    
    result->count = total_count;
    return result;
}

void polycall_tokenizer_destroy_ops(TokenizerOperations* ops) {
    if (!ops) return;
    
    if (ops->patterns) free(ops->patterns);
    if (ops->consumers) free(ops->consumers);
    free(ops);
}

// State accessors
const PolycallTokenArray* polycall_tokenizer_get_tokens(
    const PolycallTokenizer* tokenizer
) {
    return tokenizer ? tokenizer->tokens : NULL;
}

const char* polycall_tokenizer_get_error(
    const PolycallTokenizer* tokenizer
) {
    return tokenizer ? tokenizer->state.error_message : NULL;
}

PolycallTokenizerState polycall_tokenizer_get_state(
    const PolycallTokenizer* tokenizer
) {
    return tokenizer ? tokenizer->state.current : TOKENIZER_STATE_ERROR;
}