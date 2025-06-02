#ifndef POLYCALL_PARSER_H
#define POLYCALL_PARSER_H

#include "polycall_token.h"
#include "polycall_tokenizer.h"
#include <stddef.h>
#include <stdbool.h>

#ifdef __cplusplus
extern "C" {
#endif

// AST node types as bit flags for efficient type checking
typedef enum {
    AST_NONE          = 0x00,
    AST_PROGRAM       = 0x01,
    AST_FUNCTION      = 0x02,
    AST_VARIABLE      = 0x04,
    AST_EXPRESSION    = 0x08,
    AST_STATEMENT     = 0x10,
    AST_BLOCK         = 0x20,
    AST_CONTROL_FLOW  = 0x40,
    AST_ERROR         = 0x80
} PolycallASTType;

// Node attributes as bit flags
typedef enum {
    AST_ATTR_NONE     = 0x00,
    AST_ATTR_PUBLIC   = 0x01,
    AST_ATTR_PRIVATE  = 0x02,
    AST_ATTR_STATIC   = 0x04,
    AST_ATTR_CONST    = 0x08,
    AST_ATTR_VOLATILE = 0x10,
    AST_ATTR_EXPORTED = 0x20
} PolycallASTAttributes;

// AST node structure optimized for cache alignment
typedef struct PolycallASTNode {
    PolycallASTType type;           // 4 bytes - Node type
    PolycallASTAttributes attrs;    // 4 bytes - Node attributes
    PolycallValue value;            // 24 bytes - Node value
    uint32_t line;                  // 4 bytes - Source location
    uint32_t column;                // 4 bytes - Source location
    uint32_t child_count;           // 4 bytes - Number of children
    struct PolycallASTNode** children; // 8 bytes - Child nodes
    struct PolycallASTNode* parent;   // 8 bytes - Parent node
} PolycallASTNode;                  // Total: 60 bytes

// AST structure for batch operations
typedef struct {
    PolycallASTNode* root;          // Root node
    PolycallASTNode** nodes;        // Flat array of all nodes
    uint32_t node_count;            // Number of nodes
    uint32_t capacity;              // Node array capacity
    uint32_t error_count;           // Number of error nodes
} PolycallAST;

// Parser configuration for customization
typedef struct {
    size_t max_depth;               // Maximum parse tree depth
    size_t max_nodes;               // Maximum number of nodes
    uint32_t optimization_level;     // Optimization level
    bool strict_mode;               // Strict parsing mode
    void* user_data;                // User context data
} PolycallParserConfig;

// Point-free style transformation types
typedef PolycallASTNode* (*ASTTransform)(const PolycallASTNode*);
typedef bool (*ASTPredicate)(const PolycallASTNode*);
typedef void (*ASTVisitor)(PolycallASTNode*, void*);

// Transform chain for composition
typedef struct {
    ASTTransform* transforms;        // Array of transforms
    uint32_t count;                 // Number of transforms
} PolycallASTTransforms;

// Parser context with data locality
typedef struct {
    PolycallTokenizer* tokenizer;   // Tokenizer instance
    PolycallAST* ast;               // Current AST
    const PolycallParserConfig* config; // Parser configuration
    struct {
        char* message;              // Error message
        uint32_t line;              // Error location
        uint32_t column;            // Error location
    } error;
} PolycallParser;

// Core parsing functions
PolycallParser* polycall_parser_create(const PolycallParserConfig* config);
void polycall_parser_destroy(PolycallParser* parser);

// File parsing functions
PolycallAST* polycall_parser_parse_file(PolycallParser* parser, const char* filename);
PolycallAST* polycall_parser_parse_string(PolycallParser* parser, const char* input, size_t length);

// AST manipulation functions
PolycallASTNode* polycall_ast_create_node(PolycallASTType type, const PolycallValue* value);
void polycall_ast_destroy_node(PolycallASTNode* node);
bool polycall_ast_add_child(PolycallASTNode* parent, PolycallASTNode* child);

// Point-free style operations
PolycallASTNode* polycall_ast_map(const PolycallASTNode* node, ASTTransform transform);
PolycallAST* polycall_ast_filter(const PolycallAST* ast, ASTPredicate predicate);
void polycall_ast_visit(PolycallASTNode* node, ASTVisitor visitor, void* user_data);

// Transform chain operations
PolycallASTTransforms* polycall_ast_create_transforms(ASTTransform* transforms, uint32_t count);
void polycall_ast_destroy_transforms(PolycallASTTransforms* transforms);
PolycallAST* polycall_ast_apply_transforms(const PolycallAST* ast, const PolycallASTTransforms* transforms);

// Validation and analysis
bool polycall_ast_validate(const PolycallAST* ast);
const char* polycall_parser_get_error(const PolycallParser* parser);

// AST query functions
PolycallASTNode* polycall_ast_find_node(const PolycallAST* ast, PolycallASTType type);
PolycallASTNode** polycall_ast_find_nodes(const PolycallAST* ast, PolycallASTType type, uint32_t* count);

// Optimization functions
PolycallAST* polycall_ast_optimize(const PolycallAST* ast, uint32_t level);

#ifdef __cplusplus
}
#endif

#endif // POLYCALL_PARSER_H