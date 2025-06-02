#include "polycall.h"
#include "polycall_protocol.h"
#include "polycall_state_machine.h"
#include "polycall_tokenizer.h"
#include "network.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <signal.h>
#include <pthread.h>

#ifdef _WIN32
#include <winsock2.h>
#include <ws2tcpip.h>
#endif

#define PPI_VERSION "1.0.0"
#define MAX_INPUT 256 
#define MAX_PORTS 64
#define MAX_PROGRAMS 8
#define HISTORY_SIZE 10

// Port mapping structure using data-oriented design
typedef struct {
    uint16_t host_port;
    uint16_t container_port; 
    bool is_active;
} PortMapping;

typedef struct {
    PortMapping mappings[MAX_PORTS];
    size_t count;
} PortMappingArray;

// Runtime configuration structure
typedef struct {
    bool interactive_mode;
    const char* config_file;
    // Add other configuration fields as needed
} RuntimeConfig;

// Point-free style operation types
typedef bool (*ConfigOperation)(RuntimeConfig*);
typedef void (*NetworkOperation)(NetworkProgram*);

typedef struct {
    NetworkProgram* programs[MAX_PROGRAMS];
    size_t program_count;
    polycall_context_t pc_ctx;
    PolyCall_StateMachine* state_machine;
    char command_history[HISTORY_SIZE][MAX_INPUT];
    int history_count;
    PolyCall_StateSnapshot snapshots[POLYCALL_MAX_STATES];
    bool has_snapshot[POLYCALL_MAX_STATES];
    PortMappingArray port_mappings;
    bool interactive_mode;
#ifdef _WIN32
    bool wsaInitialized;
#endif
    bool running;
} PPI_Runtime;

// Global runtime instance
static PPI_Runtime g_runtime = {0};

// Forward declarations of command handlers
static bool cmd_init(const PPI_Runtime* runtime, const char* arg1, const char* arg2, const char* arg3);
static bool cmd_add_state(const PPI_Runtime* runtime, const char* name, const char* arg2, const char* arg3);
static bool cmd_help(const PPI_Runtime* runtime, const char* arg1, const char* arg2, const char* arg3);
static bool cmd_quit(const PPI_Runtime* runtime, const char* arg1, const char* arg2, const char* arg3);

// State callbacks
static void on_init(polycall_context_t ctx) {
    (void)ctx;
    printf("State callback: System initialized\n");
}

static void on_ready(polycall_context_t ctx) {
    (void)ctx;
    printf("State callback: System ready\n");
}

static void on_running(polycall_context_t ctx) {
    (void)ctx;
    printf("State callback: System running\n");
}

static void on_paused(polycall_context_t ctx) {
    (void)ctx;
    printf("State callback: System paused\n");
}

static void on_error(polycall_context_t ctx) {
    (void)ctx;
    printf("State callback: System error\n");
    g_runtime.running = false;
}




// Command handler function type
typedef bool (*CommandHandler)(const PPI_Runtime* runtime, const char* arg1, const char* arg2, const char* arg3);

// Command structure
typedef struct {
    const char* name;
    CommandHandler handler;
    const char* description;
    const char* usage;
} Command;

// Command table
static const Command COMMANDS[] = {
    {"init", (CommandHandler)cmd_init, "Initialize the state machine", "init"},
    {"add_state", (CommandHandler)cmd_add_state, "Add a new state", "add_state NAME"},
    {"help", (CommandHandler)cmd_help, "Show help", "help"},
    {"quit", (CommandHandler)cmd_quit, "Exit program", "quit"},
};


// Forward declarations of command handlers
static bool cmd_init(const PPI_Runtime* runtime, const char* arg1, const char* arg2, const char* arg3);
static bool cmd_add_state(const PPI_Runtime* runtime, const char* name, const char* arg2, const char* arg3);
static bool cmd_help(const PPI_Runtime* runtime, const char* arg1, const char* arg2, const char* arg3);
static bool cmd_quit(const PPI_Runtime* runtime, const char* arg1, const char* arg2, const char* arg3);

static void on_network_connect(NetworkEndpoint* endpoint) {
    if (endpoint) {
        printf("\nNew connection from %s:%d\n> ", 
               endpoint->address, 
               endpoint->port);
        fflush(stdout);
    }
}

static void on_network_disconnect(NetworkEndpoint* endpoint) {
    if (endpoint) {
        printf("\nClient disconnected from %s:%d\n> ", 
               endpoint->address, 
               endpoint->port);
        fflush(stdout);
    }
}

// Command handler implementations
static bool cmd_init(const PPI_Runtime* runtime, const char* arg1, const char* arg2, const char* arg3) {
    (void)arg1; (void)arg2; (void)arg3;
    
    if (runtime->state_machine) {
        printf("State machine already initialized\n");
        return false;
    }

    if (polycall_sm_create_with_integrity(runtime->pc_ctx, &g_runtime.state_machine, NULL) 
        != POLYCALL_SM_SUCCESS) {
        printf("Failed to initialize state machine\n");
        return false;
    }

    // Add default states
    polycall_sm_add_state(g_runtime.state_machine, "INIT", on_init, NULL, false);
    polycall_sm_add_state(g_runtime.state_machine, "READY", on_ready, NULL, false);
    polycall_sm_add_state(g_runtime.state_machine, "RUNNING", on_running, NULL, false);
    polycall_sm_add_state(g_runtime.state_machine, "PAUSED", on_paused, NULL, false);
    polycall_sm_add_state(g_runtime.state_machine, "ERROR", on_error, NULL, true);

    printf("State machine initialized successfully\n");
    return true;
}
static bool cmd_quit(const PPI_Runtime* runtime, const char* arg1, const char* arg2, const char* arg3) {
    (void)runtime; (void)arg1; (void)arg2; (void)arg3;
    g_runtime.running = false;
    return true;
}

static bool cmd_add_state(const PPI_Runtime* runtime, const char* name, const char* arg2, const char* arg3) {
    (void)arg2; (void)arg3;
    
    if (!runtime->state_machine) {
        printf("State machine not initialized. Use 'init' first.\n");
        return false;
    }

    if (!name) {
        return false;
    }

    if (polycall_sm_add_state(runtime->state_machine, name, NULL, NULL, false) 
        == POLYCALL_SM_SUCCESS) {
        printf("State '%s' added successfully\n", name);
        return true;
    }
    
    printf("Failed to add state\n");
    return false;
}



// Helper functions
static void add_to_history(const char* command) {
    if (!command) return;
    size_t cmd_len = strlen(command);
    
    if (g_runtime.history_count < HISTORY_SIZE) {
        size_t copy_len = (cmd_len < MAX_INPUT - 1) ? cmd_len : MAX_INPUT - 1;
        memcpy(g_runtime.command_history[g_runtime.history_count], command, copy_len);
        g_runtime.command_history[g_runtime.history_count][copy_len] = '\0';
        g_runtime.history_count++;
    } else {
        memmove(&g_runtime.command_history[0], &g_runtime.command_history[1], 
                (HISTORY_SIZE - 1) * sizeof(g_runtime.command_history[0]));
        size_t copy_len = (cmd_len < MAX_INPUT - 1) ? cmd_len : MAX_INPUT - 1;
        memcpy(g_runtime.command_history[HISTORY_SIZE - 1], command, copy_len);
        g_runtime.command_history[HISTORY_SIZE - 1][copy_len] = '\0';
    }
}


static bool cmd_help(const PPI_Runtime* runtime, const char* arg1, const char* arg2, const char* arg3) {
    (void)runtime; (void)arg1; (void)arg2; (void)arg3;
    
    printf("\nPolyCall CLI Commands:\n");
    printf("Network Commands:\n");
    printf("  start_network          - Start network services\n");
    printf("  stop_network           - Stop network services\n");
    printf("  list_endpoints         - List all network endpoints\n");
    printf("  list_clients          - List connected clients\n");
    
    printf("\nState Machine Commands:\n");
    printf("  init                  - Initialize the state machine\n");
    printf("  add_state NAME        - Add a new state\n");
    printf("  add_transition NAME FROM TO - Add a transition\n");
    printf("  execute NAME          - Execute a transition\n");
    
    printf("\nMiscellaneous Commands:\n");
    printf("  help                - Show this help message\n");
    printf("  quit                - Exit the program\n");
    
    return true;
}

static void list_states(void) {
    if (!g_runtime.state_machine) {
        printf("State machine not initialized\n");
        return;
    }

    printf("\nStates:\n");
    for (unsigned int i = 0; i < g_runtime.state_machine->num_states; i++) {
        printf("  %u: %s (locked: %s)\n", 
               i, 
               g_runtime.state_machine->states[i].name, 
               g_runtime.state_machine->states[i].is_locked ? "yes" : "no");
    }
}

static void list_transitions(void) {
    if (!g_runtime.state_machine) {
        printf("State machine not initialized\n");
        return;
    }

    printf("\nTransitions:\n");
    for (unsigned int i = 0; i < g_runtime.state_machine->num_transitions; i++) {
        printf("  %s: %u -> %u\n", 
               g_runtime.state_machine->transitions[i].name,
               g_runtime.state_machine->transitions[i].from_state,
               g_runtime.state_machine->transitions[i].to_state);
    }
}

static void show_history(void) {
    printf("\nCommand History:\n");
    for (int i = 0; i < g_runtime.history_count; i++) {
        printf("  %d: %s\n", i + 1, g_runtime.command_history[i]);
    }
}

static void list_endpoints(void) {
    for (size_t i = 0; i < g_runtime.program_count; i++) {
        NetworkProgram* program = g_runtime.programs[i];
        if (program && program->endpoints) {
            printf("\nProgram %zu Endpoints:\n", i);
            for (size_t j = 0; j < program->count; j++) {
                NetworkEndpoint* ep = &program->endpoints[j];
                printf("  Endpoint %zu: %s:%d (%s)\n",
                       j,
                       ep->address,
                       ep->port,
                       ep->protocol == NET_TCP ? "TCP" : "UDP");
            }
        }
    }
}

static void list_clients(void) {
    for (size_t i = 0; i < g_runtime.program_count; i++) {
        NetworkProgram* program = g_runtime.programs[i];
        if (program) {
            printf("\nProgram %zu Clients:\n", i);
            pthread_mutex_lock(&program->clients_lock);
            for (int j = 0; j < NET_MAX_CLIENTS; j++) {
                pthread_mutex_lock(&program->clients[j].lock);
                if (program->clients[j].is_active) {
                    printf("  Client %d: Connected\n", j);
                }
                pthread_mutex_unlock(&program->clients[j].lock);
            }
            pthread_mutex_unlock(&program->clients_lock);
        }
    }
}

static void show_status(void) {
    printf("\nSystem Status:\n");
    printf("  State Machine: %s\n", g_runtime.state_machine ? "Initialized" : "Not initialized");
    printf("  Network Programs: %zu\n", g_runtime.program_count);
    printf("  Running: %s\n", g_runtime.running ? "Yes" : "No");
    
    if (g_runtime.state_machine) {
        printf("  Current State: %u\n", g_runtime.state_machine->current_state);
    }
    
    list_endpoints();
    list_clients();
}



// Port configuration function
static bool configure_network_port(NetworkProgram* program, uint16_t port) {
    if (!program || !program->endpoints || program->count == 0) {
        return false;
    }
    program->endpoints[0].port = port;
    return true;
}
// Forward declarations
static void register_signal_handlers(void);

// Initialize runtime
static bool initialize_runtime(void) {
    register_signal_handlers();
    
#ifdef _WIN32
    WSADATA wsaData;
    if (WSAStartup(MAKEWORD(2, 2), &wsaData) != 0) {
        fprintf(stderr, "Failed to initialize Winsock\n");
        return false;
    }
    g_runtime.wsaInitialized = true;
#endif

    polycall_config_t config = {
        .flags = 0,
        .memory_pool_size = 1024 * 1024,
        .user_data = NULL
    };

    if (polycall_init_with_config(&g_runtime.pc_ctx, &config) != POLYCALL_SUCCESS) {
        fprintf(stderr, "Failed to initialize PolyCall context\n");
#ifdef _WIN32
        WSACleanup();
#endif
        return false;
    }

g_runtime.state_machine = NULL;
g_runtime.running = true;
    return true;
}

static void on_network_receive(NetworkEndpoint* endpoint, NetworkPacket* packet) {
    if (!endpoint || !packet || !packet->data) return;
    
    printf("\nReceived data from %s:%d: %.*s\n> ", 
           endpoint->address,
           endpoint->port,
           (int)packet->size, 
           (char*)packet->data);
    fflush(stdout);
    
    NetworkPacket response = {
        .data = packet->data,
        .size = packet->size,
        .flags = 0
    };
    
    net_send(endpoint, &response);
}

// Main program loop
static void process_command(PPI_Runtime* runtime, const char* input) {
    if (!runtime || !input) return;

    char* cmd = strtok((char*)input, " ");
    char* arg1 = strtok(NULL, " ");
    char* arg2 = strtok(NULL, " ");
    char* arg3 = strtok(NULL, " ");

    if (!cmd) return;

    // Find and execute command
    for (size_t i = 0; i < sizeof(COMMANDS) / sizeof(COMMANDS[0]); i++) {
        if (strcmp(cmd, COMMANDS[i].name) == 0) {
            if (!COMMANDS[i].handler(runtime, arg1, arg2, arg3)) {
                printf("Usage: %s\n", COMMANDS[i].usage);
            }
            return;
        }
    }

    printf("Unknown command. Type 'help' for available commands\n");
}


#include "polycall.h"
#include "polycall_protocol.h"
#include "network.h"
#include <dirent.h>
#include <sys/stat.h>
#include <errno.h>

/* Directory control structure */
typedef struct {
    char base_path[256];
    DIR* current_dir;
    struct dirent* dir_entry;
    bool is_initialized;
} DirectoryControl;

/* Port mapping context */
typedef struct {
    uint16_t host_port;
    uint16_t container_port;
    char service_name[32];
    char working_dir[256];
    bool is_active;
} PortMappingContext;

/* Constants */
#define MAX_SERVICES 16
#define DEFAULT_PORT_BASE 3000
#define CONFIG_FILENAME ".polycallrc"

/* Global state */
static DirectoryControl dir_control = {0};

/* Directory control functions */
static bool init_directory_control(const char* base_path) {
    struct stat st;

    if (!base_path || stat(base_path, &st) == -1) {
        fprintf(stderr, "Invalid base path: %s\n", strerror(errno));
        return false;
    }

    if (!S_ISDIR(st.st_mode)) {
        fprintf(stderr, "Not a directory: %s\n", base_path);
        return false;
    }

    strncpy(dir_control.base_path, base_path, sizeof(dir_control.base_path) - 1);
    dir_control.current_dir = opendir(base_path);
    dir_control.is_initialized = (dir_control.current_dir != NULL);

    return dir_control.is_initialized;
}

static void cleanup_directory_control(void) {
    if (dir_control.current_dir) {
        closedir(dir_control.current_dir);
        dir_control.current_dir = NULL;
    }
    dir_control.is_initialized = false;
}

/* Port mapping operations with point-free style */
static bool validate_port_mapping(const PortMapping* mapping) {
    return mapping && mapping->host_port > 0 && mapping->container_port > 0;
}

static bool is_port_available(const PortMappingArray* mappings, uint16_t port) {
    for (size_t i = 0; i < mappings->count; i++) {
        if (mappings->mappings[i].is_active && 
            (mappings->mappings[i].host_port == port || 
             mappings->mappings[i].container_port == port)) {
            return false;
        }
    }
    return true;
}

static bool add_port_mapping(const char* service_name, uint16_t host_port, uint16_t container_port) {
    char path_buf[512];
    struct stat st;
    
    // Create temporary mapping for validation
    PortMapping temp_mapping = {
        .host_port = host_port,
        .container_port = container_port,
        .is_active = true
    };
    
    // Validate input parameters
    if (!service_name || !validate_port_mapping(&temp_mapping)) {
        return false;
    }
    
    // Check capacity
    if (g_runtime.port_mappings.count >= MAX_PORTS) {
        fprintf(stderr, "Maximum number of port mappings reached\n");
        return false;
    }
    
    // Check port availability
    if (!is_port_available(&g_runtime.port_mappings, host_port) || 
        !is_port_available(&g_runtime.port_mappings, container_port)) {
        fprintf(stderr, "Port conflict detected\n");
        return false;
    }
    
    // Create service directory
    snprintf(path_buf, sizeof(path_buf), "%s/%s", dir_control.base_path, service_name);
    if (stat(path_buf, &st) == -1 && mkdir(path_buf, 0755) == -1) {
        fprintf(stderr, "Failed to create service directory: %s\n", strerror(errno));
        return false;
    }
    
    // Add mapping
    PortMapping* mapping = &g_runtime.port_mappings.mappings[g_runtime.port_mappings.count++];
    mapping->host_port = host_port;
    mapping->container_port = container_port;
    mapping->is_active = true;
    
    // Initialize network program
    NetworkProgram* program = calloc(1, sizeof(NetworkProgram));
    if (!program) {
        g_runtime.port_mappings.count--;
        return false;
    }
    
    net_init_program(program);
    if (program->endpoints && program->count > 0) {
        program->endpoints[0].port = container_port;
        program->handlers.on_receive = on_network_receive;
        program->handlers.on_connect = on_network_connect;
        program->handlers.on_disconnect = on_network_disconnect;
        
        g_runtime.programs[g_runtime.program_count++] = program;
        printf("Mapped port %d to %d for service %s\n", 
               host_port, container_port, service_name);
        return true;
    }
    free(program);
    
    g_runtime.port_mappings.count--;
    return false;
}

/* Service discovery and initialization */
static bool discover_and_init_services(void) {
    char config_path[512];
    FILE* config;
    char line[256];
    size_t services_found = 0;

    dir_control.current_dir = opendir(dir_control.base_path);
    if (!dir_control.current_dir) {
        return false;
    }

    /* Look for service configurations */
    while ((dir_control.dir_entry = readdir(dir_control.current_dir)) != NULL) {
        if (dir_control.dir_entry->d_type != DT_DIR ||
            strcmp(dir_control.dir_entry->d_name, ".") == 0 ||
            strcmp(dir_control.dir_entry->d_name, "..") == 0) {
            continue;
        }

        /* Check for config file */
        size_t path_len = snprintf(config_path, sizeof(config_path), "%s/%s/%s",
                                 dir_control.base_path,
                                 dir_control.dir_entry->d_name,
                                 CONFIG_FILENAME);
                                 
        if (path_len >= sizeof(config_path)) {
            fprintf(stderr, "Path too long for service: %s\n", dir_control.dir_entry->d_name);
            continue;
        }

        config = fopen(config_path, "r");
        if (config) {
            uint16_t host_port = DEFAULT_PORT_BASE + services_found;
            uint16_t container_port = 8080 + services_found;

            /* Parse service configuration */
            while (fgets(line, sizeof(line), config)) {
                if (strncmp(line, "port=", 5) == 0) {
                    sscanf(line + 5, "%hu:%hu", &host_port, &container_port);
                    break;
                }
            }

            if (add_port_mapping(dir_control.dir_entry->d_name, 
                               host_port, container_port)) {
                services_found++;
            }

            fclose(config);
        }
    }

    closedir(dir_control.current_dir);
    dir_control.current_dir = NULL;

    return services_found > 0;
}

/* Configuration file functions */
static bool process_config_file(const char* filename) {
    FILE* fp;
    char line[256];
    char service[32];
    uint16_t host_port, container_port;

    fp = fopen(filename, "r");
    if (!fp) {
        return false;
    }

    while (fgets(line, sizeof(line), fp)) {
        /* Skip comments and empty lines */
        if (line[0] == '#' || line[0] == '\n') {
            continue;
        }

        /* Parse service definitions */
        if (sscanf(line, "server %31s %hu:%hu", 
                   service, &host_port, &container_port) == 3) {
            add_port_mapping(service, host_port, container_port);
        }
    }

    fclose(fp);
    return true;
}

/* API function for external use */
bool polycall_init_with_directory(const char* base_path, const char* config_file) {
    if (!init_directory_control(base_path)) {
        return false;
    }

    if (config_file && !process_config_file(config_file)) {
        fprintf(stderr, "Warning: Failed to process config file\n");
    }

    if (!discover_and_init_services()) {
        fprintf(stderr, "Warning: No services discovered\n");
    }

    return true;
}
// Cleanup runtime
static void cleanup_runtime(void) {
    cleanup_directory_control();
    
    for (size_t i = 0; i < g_runtime.program_count; i++) {
        if (g_runtime.programs[i]) {
            net_cleanup_program(g_runtime.programs[i]);
            free(g_runtime.programs[i]);
            g_runtime.programs[i] = NULL;
        }
    }
    
    if (g_runtime.state_machine) {
        polycall_sm_destroy(g_runtime.state_machine);
        g_runtime.state_machine = NULL;
    }
    
    if (g_runtime.pc_ctx) {
        polycall_cleanup(g_runtime.pc_ctx);
        g_runtime.pc_ctx = NULL;
    }

#ifdef _WIN32
    if (g_runtime.wsaInitialized) {
        WSACleanup();
        g_runtime.wsaInitialized = false;
    }
#endif
}


// Adding signal handler registration
static void cleanup_and_exit(void) {
    cleanup_runtime();
    printf("Goodbye!\n");
    exit(0);
}

static void signal_handler(int signum) {
    (void)signum;
    cleanup_and_exit();
}
static void register_signal_handlers(void) {
    signal(SIGINT, signal_handler);
    signal(SIGTERM, signal_handler);
}


int main(int argc, char* argv[]) {
    bool non_interactive = false;
    const char* config_file = NULL;
    
    // Parse command line arguments
    for (int i = 1; i < argc; i++) {
        if (strcmp(argv[i], "-f") == 0 && i + 1 < argc) {
            config_file = argv[++i];
            non_interactive = true;
        }
    }

    if (!initialize_runtime()) {
        fprintf(stderr, "Failed to initialize runtime\n");
        return 1;
    }

    if (non_interactive) {
        // Handle non-interactive mode with config file
        FILE* fp = fopen(config_file, "r");
        if (!fp) {
            fprintf(stderr, "Failed to open config file: %s\n", config_file);
            cleanup_runtime();
            return 1;
        }

        char line[MAX_INPUT];
        bool network_started = false;
        uint16_t port_number = 8080; // Default port

        while (fgets(line, sizeof(line), fp)) {
            // Remove newline and whitespace
            char* trimmed = line;
            size_t len = strlen(trimmed);
            while (len > 0 && (trimmed[len-1] == '\n' || trimmed[len-1] == '\r')) {
                trimmed[--len] = '\0';
            }

            // Skip empty lines and comments
            if (len == 0 || trimmed[0] == '#') continue;

            // Parse configuration commands
            char cmd[32], value[256];
            if (sscanf(trimmed, "%31s %255s", cmd, value) == 2) {
                if (strcmp(cmd, "port") == 0) {
                    // Handle port mapping (format: "port host:container")
                    uint16_t host_port, container_port;
                    if (sscanf(value, "%hu:%hu", &host_port, &container_port) == 2) {
                        port_number = container_port;
                    }
                } else if (strcmp(cmd, "network") == 0 && strcmp(value, "start") == 0) {
                    // Start network services
                    NetworkProgram* program = calloc(1, sizeof(NetworkProgram));
                    if (program) {
                        net_init_program(program);
                        
                        // Configure port if specified
                        if (program->endpoints && program->count > 0) {
                            program->endpoints[0].port = port_number;
                            
                            // Set up handlers
                            program->handlers.on_receive = on_network_receive;
                            program->handlers.on_connect = on_network_connect;
                            program->handlers.on_disconnect = on_network_disconnect;
                            
                            g_runtime.programs[g_runtime.program_count++] = program;
                            network_started = true;
                            printf("Network services started on port %d\n", port_number);
                        } else {
                            free(program);
                            fprintf(stderr, "Failed to start network services\n");
                        }
                    }
                }
            }
        }

        fclose(fp);

        if (!network_started) {
            fprintf(stderr, "Warning: No network services were started\n");
        }

        // Enter non-interactive event loop
        printf("Running in non-interactive mode...\n");
        g_runtime.running = true;

        while (g_runtime.running) {
            // Process all network programs
            for (size_t i = 0; i < g_runtime.program_count; i++) {
                NetworkProgram* program = g_runtime.programs[i];
                if (program) {
                    if (configure_network_port(program, port_number)) {
                        net_run(program);
                    }
                }
            }
            // Small sleep to prevent CPU spin
            usleep(1000); // 1ms sleep
        }
    } else {
        // Original interactive mode
        char input[MAX_INPUT];
        printf("PolyCall CLI v%s - Type 'help' for commands\n", PPI_VERSION);

        while (g_runtime.running) {
            printf("\n> ");
            if (!fgets(input, sizeof(input), stdin)) {
                break;
            }

            input[strcspn(input, "\n")] = 0;
            if (strlen(input) == 0) continue;

            char *command = strtok(input, " ");
            char *arg1 = strtok(NULL, " ");
            add_to_history(input);

            if (strcmp(command, "start_network") == 0) {
                NetworkProgram* program = calloc(1, sizeof(NetworkProgram));
                if (program) {
                    net_init_program(program);
                    if (program->endpoints && program->count > 0) {
                        program->handlers.on_receive = on_network_receive;
                        program->handlers.on_connect = on_network_connect;
                        program->handlers.on_disconnect = on_network_disconnect;
                        g_runtime.programs[g_runtime.program_count++] = program;
                        printf("Network services started\n");
                    } else {
                        free(program);
                        printf("Failed to start network services\n");
                    }
                }
            } else if (strcmp(command, "stop_network") == 0) {
                for (size_t i = 0; i < g_runtime.program_count; i++) {
                    if (g_runtime.programs[i]) {
                        net_cleanup_program(g_runtime.programs[i]);
                        free(g_runtime.programs[i]);
                        g_runtime.programs[i] = NULL;
                    }
                }
                g_runtime.program_count = 0;
                printf("Network services stopped\n");
            } else if (strcmp(command, "list_endpoints") == 0) {
                list_endpoints();
            } else if (strcmp(command, "list_clients") == 0) {
                list_clients();
            } else if (strcmp(command, "list_states") == 0) {
                list_states();
            } else if (strcmp(command, "list_transitions") == 0) {
                list_transitions();
            } else if (strcmp(command, "history") == 0) {
                show_history();
            } else if (strcmp(command, "status") == 0) {
                show_status();
            } else if (strcmp(command, "add_state") == 0) {
                if (!g_runtime.state_machine) {
                    printf("State machine not initialized\n");
                    continue;
                }
                if (!arg1) {
                    printf("Usage: add_state NAME\n");
                    continue;
                }
                if (polycall_sm_add_state(g_runtime.state_machine, arg1, NULL, NULL, false) 
                    == POLYCALL_SM_SUCCESS) {
                    printf("State '%s' added successfully\n", arg1);
                } else {
                    printf("Failed to add state '%s'\n", arg1);
                }
            } else {
                process_command(&g_runtime, input);
            }
        }
    }

    cleanup_runtime();
    printf("Goodbye!\n");
    return 0;
}