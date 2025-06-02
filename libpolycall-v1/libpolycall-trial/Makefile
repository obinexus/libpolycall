# Compiler and flags
CC := gcc
CFLAGS := -Wall -Wextra -I./include -fPIC
LDFLAGS := -pthread -lssl -lcrypto

# Platform-specific settings
ifeq ($(OS),Windows_NT)
    LDFLAGS += -lws2_32
    CFLAGS += -D_WIN32
    SHARED_EXT := dll
    EXE_EXT := .exe
else
    SHARED_EXT := so
    EXE_EXT :=
endif

# Debug/Release flags
DEBUG_FLAGS := -g -DDEBUG
RELEASE_FLAGS := -O2 -DNDEBUG

# Directories
SRC_DIR := src
INC_DIR := include
BUILD_DIR := build
LIB_DIR := lib
BIN_DIR := bin

# Source files
SRCS := $(wildcard $(SRC_DIR)/*.c)
OBJS := $(SRCS:$(SRC_DIR)/%.c=$(BUILD_DIR)/%.o)
DEPS := $(OBJS:.o=.d)

# Main executable
MAIN_SRC := main.c
MAIN_OBJ := $(BUILD_DIR)/main.o
EXECUTABLE := polycall$(EXE_EXT)

# Library name
LIB_NAME := libpolycall
STATIC_LIB := $(LIB_DIR)/$(LIB_NAME).a
SHARED_LIB := $(LIB_DIR)/$(LIB_NAME).$(SHARED_EXT)

# Installation paths
PREFIX := /usr/local
INSTALL_INC_DIR := $(PREFIX)/include/$(LIB_NAME)
INSTALL_LIB_DIR := $(PREFIX)/lib
INSTALL_BIN_DIR := $(PREFIX)/bin

# Default target
.PHONY: all
all: dirs $(STATIC_LIB) $(SHARED_LIB) $(BIN_DIR)/$(EXECUTABLE)

# Create necessary directories
.PHONY: dirs
dirs:
	@mkdir -p $(BUILD_DIR) $(LIB_DIR) $(BIN_DIR)

# Debug build
.PHONY: debug
debug: CFLAGS += $(DEBUG_FLAGS)
debug: all

# Release build
.PHONY: release
release: CFLAGS += $(RELEASE_FLAGS)
release: all

# Compile source files
$(BUILD_DIR)/%.o: $(SRC_DIR)/%.c
	$(CC) $(CFLAGS) -MMD -MP -c $< -o $@

# Compile main executable
$(BUILD_DIR)/main.o: $(MAIN_SRC)
	$(CC) $(CFLAGS) -MMD -MP -c $< -o $@

# Create static library
$(STATIC_LIB): $(OBJS)
	ar rcs $@ $^

# Create shared library
$(SHARED_LIB): $(OBJS)
	$(CC) -shared -o $@ $^ $(LDFLAGS)

# Link executable
$(BIN_DIR)/$(EXECUTABLE): $(MAIN_OBJ) $(STATIC_LIB)
	$(CC) $^ -o $@ $(LDFLAGS) -L$(LIB_DIR) -l:$(LIB_NAME).a

# Install (Unix-like systems only)
.PHONY: install
install: all
ifneq ($(OS),Windows_NT)
	@mkdir -p $(INSTALL_INC_DIR)
	@mkdir -p $(INSTALL_LIB_DIR)
	@mkdir -p $(INSTALL_BIN_DIR)
	cp $(INC_DIR)/*.h $(INSTALL_INC_DIR)
	cp $(STATIC_LIB) $(SHARED_LIB) $(INSTALL_LIB_DIR)
	cp $(BIN_DIR)/$(EXECUTABLE) $(INSTALL_BIN_DIR)
	ldconfig
endif

# Uninstall (Unix-like systems only)
.PHONY: uninstall
uninstall:
ifneq ($(OS),Windows_NT)
	rm -rf $(INSTALL_INC_DIR)
	rm -f $(INSTALL_LIB_DIR)/$(LIB_NAME).*
	rm -f $(INSTALL_BIN_DIR)/$(EXECUTABLE)
endif

# Clean build files
.PHONY: clean
clean:
	rm -rf $(BUILD_DIR) $(LIB_DIR) $(BIN_DIR)

# Clean everything including installed files
.PHONY: distclean
distclean: clean uninstall

# Include dependency files
-include $(DEPS)

# Help target
.PHONY: help
help:
	@echo "Available targets:"
	@echo "  all        - Build everything (default)"
	@echo "  debug      - Build with debug flags"
	@echo "  release    - Build with release flags"
	@echo "  clean      - Remove build files"
	@echo "  install    - Install libraries and headers (Unix-like only)"
	@echo "  uninstall  - Remove installed files (Unix-like only)"
	@echo "  distclean  - Remove all generated files"
	@echo "  help       - Show this help message"