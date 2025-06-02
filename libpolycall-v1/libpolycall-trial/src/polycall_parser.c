#include "polycall_parser.h"
#include <stdlib.h>
#include <string.h>
#include <stdio.h>
#include <stdarg.h>

// Internal constants
#define INITIAL_NODE_CAPACITY 1024
#define MAX_ERROR_LENGTH 256
#define DEFAULT_MAX_DEPTH 256
#define DEFAULT_MAX_NODES 65536

// Memory pool for efficient node allocation
typedef struct {
    PolycallASTNode* nodes;
    size_t capacity;
    size_t used;
} NodePool;

// Internal parser state
typedef struct {
    const PolycallToken* current_token;
    uint32_t token_index;
    uint32_t depth;
    NodePool pool;
    char error_buffer[MAX_ERROR_LENGTH];
} ParserState;

// Default parser configuration
static const PolycallParserConfig DEFAULT_CONFIG = {
    .max_depth = DEFAULT_MAX_DEPTH,
    .max_nodes = DEFAULT_MAX_NODES,
    .optimization_level = 0,
    .strict_mode = true,
    .user_data = NULL
};

// Node pool management
static NodePool create_node_pool(size_t capacity) {
    NodePool pool = {
        .nodes = calloc(capacity, sizeof(PolycallASTNode)),
        .capacity = capacity,
        .used = 0
    };
    return pool;
}

static void destroy_node_pool(NodePool* pool) {
    if (pool) {
        free(pool->nodes);
        pool->nodes = NULL;
        pool->capacity = 0;
        pool->used = 0;
    }
}

static PolycallASTNode* allocate_node(NodePool* pool) {
    if (!pool || pool->used >= pool->capacity) return NULL;
    return &pool->nodes[pool->used++];
}

// Node counter callback
static void count_node(PolycallASTNode* node, void* count) {
    if (node && count) {
        (*(uint32_t*)count)++;
    }
}
// Error handling function
static void set_parser_error(PolycallParser* parser, const char* format, ...) {
    if (!parser) return;
    
    va_list args;
    va_start(args, format);
    vsnprintf(parser->error.message, MAX_ERROR_LENGTH - 1, format, args);
    va_end(args);
    
    if (parser->tokenizer) {
        const PolycallTokenArray* tokens = polycall_tokenizer_get_tokens(parser->tokenizer);
        if (tokens && tokens->count > 0) {
            parser->error.line = tokens->tokens[tokens->count - 1].line;
            parser->error.column = tokens->tokens[tokens->count - 1].column;
        }
    }
}


// Token processing
static bool advance_token(ParserState* state, const PolycallTokenArray* tokens) {
    if (!state || !tokens || state->token_index >= tokens->count) return false;
    
    state->current_token = &tokens->tokens[state->token_index++];
    return true;
}

static bool expect_token(ParserState* state, const PolycallTokenArray* tokens, PolycallTokenType type) {
    if (!state->current_token || state->current_token->type != type) {
        return false;
    }
    return advance_token(state, tokens);
}

// AST node creation
PolycallASTNode* polycall_ast_create_node(PolycallASTType type, const PolycallValue* value) {
    PolycallASTNode* node = calloc(1, sizeof(PolycallASTNode));
    if (!node) return NULL;
    
    node->type = type;
    if (value) {
        node->value = *value;
    }
    
    return node;
}

void polycall_ast_destroy_node(PolycallASTNode* node) {
    if (!node) return;
    
    for (uint32_t i = 0; i < node->child_count; i++) {
        polycall_ast_destroy_node(node->children[i]);
    }
    
    free(node->children);
    free(node);
}

// Parser creation and destruction
PolycallParser* polycall_parser_create(const PolycallParserConfig* config) {
    PolycallParser* parser = calloc(1, sizeof(PolycallParser));
    if (!parser) return NULL;
    
    parser->config = config ? config : &DEFAULT_CONFIG;
    parser->error.message = calloc(MAX_ERROR_LENGTH, sizeof(char));
    
    // Initialize tokenizer with default configuration
    parser->tokenizer = polycall_tokenizer_create(NULL);
    if (!parser->tokenizer) {
        polycall_parser_destroy(parser);
        return NULL;
    }
    
    return parser;
}

void polycall_parser_destroy(PolycallParser* parser) {
    if (!parser) return;
    
    if (parser->tokenizer) {
        polycall_tokenizer_destroy(parser->tokenizer);
    }

    if (parser->ast) {

        polycall_ast_destroy_node(parser->ast->root);

        free(parser->ast->nodes);

        free(parser->ast);

    }

    
    free(parser->error.message);
    free(parser);
}

// Parsing functions
static PolycallASTNode* parse_expression(ParserState* state, const PolycallTokenArray* tokens) {
    if (!state->current_token) return NULL;
    
    PolycallASTNode* node = NULL;
    
    switch (state->current_token->type) {
        case TOKEN_NUMBER:
        case TOKEN_STRING:
        case TOKEN_IDENTIFIER:
            node = allocate_node(&state->pool);
            if (node) {
                node->type = AST_EXPRESSION;
                node->value = state->current_token->value;
                advance_token(state, tokens);
            }
            break;
            
        default:
            break;
    }
    
    return node;
}

static PolycallASTNode* parse_statement(ParserState* state, const PolycallTokenArray* tokens) {
    if (!state->current_token) return NULL;
    
    PolycallASTNode* node = allocate_node(&state->pool);
    if (!node) return NULL;
    
    node->type = AST_STATEMENT;
    
    // Parse expression statement
    PolycallASTNode* expr = parse_expression(state, tokens);
    if (expr) {
        node->children = calloc(1, sizeof(PolycallASTNode*));
        node->children[0] = expr;
        node->child_count = 1;
        expr->parent = node;
    }
    
    return node;
}

static PolycallASTNode* parse_block(ParserState* state, const PolycallTokenArray* tokens) {
    if (!expect_token(state, tokens, TOKEN_SEPARATOR)) return NULL;
    
    PolycallASTNode* node = allocate_node(&state->pool);
    if (!node) return NULL;
    
    node->type = AST_BLOCK;
    node->children = calloc(16, sizeof(PolycallASTNode*));  // Initial capacity
    
    while (state->current_token && 
           state->current_token->type != TOKEN_SEPARATOR) {
        
        PolycallASTNode* stmt = parse_statement(state, tokens);
        if (stmt) {
            node->children[node->child_count++] = stmt;
            stmt->parent = node;
        }
    }
    
    expect_token(state, tokens, TOKEN_SEPARATOR);
    return node;
}

static PolycallASTNode* parse_function(ParserState* state, const PolycallTokenArray* tokens) {
    if (!expect_token(state, tokens, TOKEN_IDENTIFIER)) return NULL;
    
    PolycallASTNode* node = allocate_node(&state->pool);
    if (!node) return NULL;
    
    node->type = AST_FUNCTION;
    node->value = state->current_token->value;
    
    // Parse parameter list
    expect_token(state, tokens, TOKEN_SEPARATOR);
    while (state->current_token && 
           state->current_token->type != TOKEN_SEPARATOR) {
        advance_token(state, tokens);
    }
    expect_token(state, tokens, TOKEN_SEPARATOR);
    
    // Parse function body
    PolycallASTNode* body = parse_block(state, tokens);
    if (body) {
        node->children = calloc(1, sizeof(PolycallASTNode*));
        node->children[0] = body;
        node->child_count = 1;
        body->parent = node;
    }
    
    return node;
}

static PolycallAST* parse_tokens(PolycallParser* parser, const PolycallTokenArray* tokens) {
    if (!parser || !tokens) return NULL;
    
    PolycallAST* ast = calloc(1, sizeof(PolycallAST));
    if (!ast) return NULL;
    
    ParserState state = {
        .current_token = tokens->count > 0 ? &tokens->tokens[0] : NULL,
        .token_index = 0,
        .depth = 0,
        .pool = create_node_pool(parser->config->max_nodes)
    };
    
    // Parse program
    ast->root = allocate_node(&state.pool);
    if (ast->root) {
        ast->root->type = AST_PROGRAM;
        ast->root->children = calloc(16, sizeof(PolycallASTNode*));  // Initial capacity
        
        while (state.current_token && 
               state.current_token->type != TOKEN_EOF) {
            
            PolycallASTNode* node = parse_function(&state, tokens);
            if (node) {
                ast->root->children[ast->root->child_count++] = node;
                node->parent = ast->root;
            }
        }
    }
    
    // Build flat node array for efficient traversal
    ast->capacity = state.pool.used;
    ast->nodes = calloc(ast->capacity, sizeof(PolycallASTNode*));
    if (ast->nodes) {
        for (size_t i = 0; i < state.pool.used; i++) {
            ast->nodes[i] = &state.pool.nodes[i];
        }
        ast->node_count = state.pool.used;
    }
    
    destroy_node_pool(&state.pool);
    return ast;
}

// Public parsing functions
PolycallAST* polycall_parser_parse_string(
    PolycallParser* parser,
    const char* input,
    size_t length
) {
    if (!parser || !input || length == 0) return NULL;
    
    // Tokenize input
    if (!polycall_tokenizer_set_input(parser->tokenizer, input, length)) {
        set_parser_error(parser, "Failed to set parser input");
        return NULL;
    }
    
    TokenizerOperations ops = {0};  // Define tokenizer operations
    if (!polycall_tokenizer_process(parser->tokenizer, &ops)) {
        set_parser_error(parser, "Tokenization failed");
        return NULL;
    }
    
    // Parse tokens
    const PolycallTokenArray* tokens = polycall_tokenizer_get_tokens(parser->tokenizer);
    return parse_tokens(parser, tokens);
}

PolycallAST* polycall_parser_parse_file(PolycallParser* parser, const char* filename) {
    if (!parser || !filename) return NULL;
    
    FILE* file = fopen(filename, "rb");
    if (!file) {
        set_parser_error(parser, "Failed to open file: %s", filename);
        return NULL;
    }
    
    // Read file content
    fseek(file, 0, SEEK_END);
    size_t size = ftell(file);
    fseek(file, 0, SEEK_SET);
    
    char* buffer = malloc(size + 1);
    if (!buffer) {
        fclose(file);
        set_parser_error(parser, "Failed to allocate memory for file content");
        return NULL;
    }
    
    size_t read = fread(buffer, 1, size, file);
    fclose(file);
    
    if (read != size) {
        free(buffer);
        set_parser_error(parser, "Failed to read file content");
        return NULL;
    }
    
    buffer[size] = '\0';
    
    // Parse file content
    PolycallAST* ast = polycall_parser_parse_string(parser, buffer, size);
    free(buffer);
    return ast;
}

// Point-free style operations
PolycallASTNode* polycall_ast_map(const PolycallASTNode* node, ASTTransform transform) {
    if (!node || !transform) return NULL;
    return transform(node);
}

PolycallAST* polycall_ast_filter(const PolycallAST* ast, ASTPredicate predicate) {
    if (!ast || !predicate) return NULL;
    
    PolycallAST* filtered = calloc(1, sizeof(PolycallAST));
    if (!filtered) return NULL;
    
    filtered->capacity = ast->node_count;
    filtered->nodes = calloc(filtered->capacity, sizeof(PolycallASTNode*));
    
    if (filtered->nodes) {
        for (uint32_t i = 0; i < ast->node_count; i++) {
            if (predicate(ast->nodes[i])) {
                filtered->nodes[filtered->node_count++] = ast->nodes[i];
            }
        }
    }
    
    return filtered;
}

void polycall_ast_visit(PolycallASTNode* node, ASTVisitor visitor, void* user_data) {
    if (!node || !visitor) return;
    
    visitor(node, user_data);
    
    for (uint32_t i = 0; i < node->child_count; i++) {
        polycall_ast_visit(node->children[i], visitor, user_data);
    }
}

// Transform chain operations
PolycallASTTransforms* polycall_ast_create_transforms(ASTTransform* transforms, uint32_t count) {
    if (!transforms || count == 0) return NULL;
    
    PolycallASTTransforms* chain = calloc(1, sizeof(PolycallASTTransforms));
    if (!chain) return NULL;
    
    chain->transforms = calloc(count, sizeof(ASTTransform));
    if (!chain->transforms) {
        free(chain);
        return NULL;
    }
    
    memcpy(chain->transforms, transforms, count * sizeof(ASTTransform));
    chain->count = count;
    
    return chain;
}

void polycall_ast_destroy_transforms(PolycallASTTransforms* transforms) {
    if (!transforms) return;
    free(transforms->transforms);
    free(transforms);
}
PolycallAST* polycall_ast_apply_transforms(
    const PolycallAST* ast,
    const PolycallASTTransforms* transforms
) {
    if (!ast || !transforms || !transforms->transforms) return NULL;
    
    // Create a copy of the AST for transformation
    PolycallAST* result = calloc(1, sizeof(PolycallAST));
    if (!result) return NULL;
    
    result->capacity = ast->node_count;
    result->nodes = calloc(result->capacity, sizeof(PolycallASTNode*));
    if (!result->nodes) {
        free(result);
        return NULL;
    }
    
    // Apply transforms in sequence
    for (uint32_t i = 0; i < ast->node_count; i++) {
        const PolycallASTNode* current = ast->nodes[i];
        PolycallASTNode* transformed = (PolycallASTNode*)current;
        
        // Apply each transform in the chain
        for (uint32_t t = 0; t < transforms->count; t++) {
            if (transforms->transforms[t]) {
                transformed = transforms->transforms[t](transformed);
                if (!transformed) break;
            }
        }
        
        if (transformed) {
            result->nodes[result->node_count++] = transformed;
        }
    }
    
    // Reconstruct tree structure if needed
    if (result->node_count > 0) {
        result->root = result->nodes[0];
    }
    
    return result;
}

// AST query functions implementation
PolycallASTNode* polycall_ast_find_node(const PolycallAST* ast, PolycallASTType type) {
    if (!ast || !ast->nodes) return NULL;
    
    for (uint32_t i = 0; i < ast->node_count; i++) {
        if (ast->nodes[i]->type == type) {
            return ast->nodes[i];
        }
    }
    
    return NULL;
}

PolycallASTNode** polycall_ast_find_nodes(
    const PolycallAST* ast,
    PolycallASTType type,
    uint32_t* count
) {
    if (!ast || !ast->nodes || !count) return NULL;
    
    // First pass: count matching nodes
    *count = 0;
    for (uint32_t i = 0; i < ast->node_count; i++) {
        if (ast->nodes[i]->type == type) {
            (*count)++;
        }
    }
    
    if (*count == 0) return NULL;
    
    // Allocate result array
    PolycallASTNode** result = calloc(*count, sizeof(PolycallASTNode*));
    if (!result) {
        *count = 0;
        return NULL;
    }
    
    // Second pass: collect matching nodes
    uint32_t index = 0;
    for (uint32_t i = 0; i < ast->node_count && index < *count; i++) {
        if (ast->nodes[i]->type == type) {
            result[index++] = ast->nodes[i];
        }
    }
    
    return result;
}
// Node visit for optimization callback
static void collect_optimized_node(PolycallASTNode* node, void* ast) {
    if (node && ast) {
        PolycallAST* opt = (PolycallAST*)ast;
        opt->nodes[opt->node_count++] = node;
    }
}

// Validation functions
static bool validate_node_structure(const PolycallASTNode* node, uint32_t depth, size_t max_depth) {
    if (!node || depth > max_depth) return false;
    
    // Validate parent-child relationships
    for (uint32_t i = 0; i < node->child_count; i++) {
        if (!node->children[i] || node->children[i]->parent != node) {
            return false;
        }
        
        // Recursively validate children
        if (!validate_node_structure(node->children[i], depth + 1, max_depth)) {
            return false;
        }
    }
    
    return true;
}


bool polycall_ast_validate(const PolycallAST* ast) {
    if (!ast || !ast->root) return false;
    
    // Validate node count consistency
    uint32_t counted_nodes = 0;
    polycall_ast_visit((PolycallASTNode*)ast->root, count_node, &counted_nodes);
    
    if (counted_nodes != ast->node_count) return false;
    
    // Validate tree structure
    return validate_node_structure(ast->root, 0, DEFAULT_MAX_DEPTH);
}
// Error reporting
const char* polycall_parser_get_error(const PolycallParser* parser) {
    return parser ? parser->error.message : "Invalid parser";
}

// AST optimization functions
static PolycallASTNode* optimize_node(PolycallASTNode* node, uint32_t level) {
    if (!node) return NULL;
    
    // Apply optimizations based on level
    switch (level) {
        case 1:  // Basic optimizations
            // Remove redundant nodes
            if (node->type == AST_BLOCK && node->child_count == 1) {
                PolycallASTNode* child = node->children[0];
                free(node->children);
                free(node);
                return optimize_node(child, level);
            }
            break;
            
        case 2:  // Intermediate optimizations
            // Constant folding
            if (node->type == AST_EXPRESSION) {
                // Implement constant folding logic
            }
            break;
            
        case 3:  // Advanced optimizations
            // Control flow optimization
            if (node->type == AST_CONTROL_FLOW) {
                // Implement control flow optimization
            }
            break;
    }
    
    // Recursively optimize children
    for (uint32_t i = 0; i < node->child_count; i++) {
        node->children[i] = optimize_node(node->children[i], level);
    }
    
    return node;
}

PolycallAST* polycall_ast_optimize(const PolycallAST* ast, uint32_t level) {
    if (!ast || !ast->root) return NULL;
    
    // Create optimized copy of AST
    PolycallAST* optimized = calloc(1, sizeof(PolycallAST));
    if (!optimized) return NULL;
    
    // Copy and optimize nodes
    optimized->capacity = ast->capacity;
    optimized->nodes = calloc(optimized->capacity, sizeof(PolycallASTNode*));
    if (!optimized->nodes) {
        free(optimized);
        return NULL;
    }
    
    // Deep copy and optimize root node
    optimized->root = optimize_node(polycall_ast_create_node(ast->root->type, &ast->root->value), level);
    if (!optimized->root) {
        free(optimized->nodes);
        free(optimized);
        return NULL;
    }
    
    // Build optimized node array
    polycall_ast_visit(optimized->root, collect_optimized_node, optimized);
    
    return optimized;
}

// Tree manipulation helpers
bool polycall_ast_add_child(PolycallASTNode* parent, PolycallASTNode* child) {
    if (!parent || !child) return false;
    
    // Resize children array if needed
    size_t new_size = parent->child_count + 1;
    PolycallASTNode** new_children = realloc(parent->children,
                                            new_size * sizeof(PolycallASTNode*));
    
    if (!new_children) return false;
    
    parent->children = new_children;
    parent->children[parent->child_count++] = child;
    child->parent = parent;
    
    return true;
}

// Node attribute manipulation
void polycall_ast_set_attributes(PolycallASTNode* node, PolycallASTAttributes attrs) {
    if (node) {
        node->attrs = attrs;
    }
}

PolycallASTAttributes polycall_ast_get_attributes(const PolycallASTNode* node) {
    return node ? node->attrs : AST_ATTR_NONE;
}

// Source location tracking
void polycall_ast_set_location(PolycallASTNode* node, uint32_t line, uint32_t column) {
    if (node) {
        node->line = line;
        node->column = column;
    }
}

void polycall_ast_get_location(const PolycallASTNode* node, uint32_t* line, uint32_t* column) {
    if (node && line && column) {
        *line = node->line;
        *column = node->column;
    }
}