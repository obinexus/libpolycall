# Compiler and flags
CC := gcc
CFLAGS := -Wall -Wextra -I./include -fPIC
LDFLAGS :=
EXE_LDFLAGS ?= $(LDFLAGS)
USE_OPENSSL ?= 0
ifeq ($(OS),Windows_NT)
COMPILER_VERSION := $(shell $(CC) -dumpfullversion -dumpversion 2>NUL)
COMPILER_TARGET := $(shell $(CC) -dumpmachine 2>NUL)
COMPILER_PATH := $(shell where $(CC) 2>NUL)
else
COMPILER_VERSION := $(shell $(CC) -dumpfullversion -dumpversion 2>/dev/null)
COMPILER_TARGET := $(shell $(CC) -dumpmachine 2>/dev/null)
COMPILER_PATH := $(shell command -v $(CC) 2>/dev/null)
endif

# Platform-specific settings
ifeq ($(OS),Windows_NT)
PLATFORM := windows
LDFLAGS += -lws2_32
CFLAGS += -D_WIN32 -D__USE_MINGW_ANSI_STDIO=1
SHARED_EXT := dll
SHARED_LDFLAGS := -shared
EXE_EXT := .exe
# $(OS) is Windows_NT regardless of which shell make will run recipes with.
# Under MSYS2/Git-Bash/Cygwin, recipes run through a POSIX sh, so cmd.exe
# batch syntax (if not exist/del/...) fails there. Only use batch syntax
# when no POSIX uname is on PATH (i.e. genuine cmd.exe or PowerShell).
WIN_UNAME := $(shell uname -s 2>NUL)
ifeq (,$(findstring MINGW,$(WIN_UNAME))$(findstring MSYS,$(WIN_UNAME))$(findstring CYGWIN,$(WIN_UNAME)))
CMD_SHELL := 1
endif
else
UNAME_S := $(shell uname -s 2>/dev/null || echo Unknown)
ifeq ($(UNAME_S),Darwin)
PLATFORM := macos
SHARED_EXT := dylib
SHARED_LDFLAGS := -dynamiclib
EXE_EXT :=
else ifeq ($(UNAME_S),Linux)
PLATFORM := linux
SHARED_EXT := so
SHARED_LDFLAGS := -shared
EXE_EXT :=
else
PLATFORM := unix
SHARED_EXT := so
SHARED_LDFLAGS := -shared
EXE_EXT :=
endif
LDFLAGS += -pthread
endif

ifeq ($(USE_OPENSSL),1)
LDFLAGS += -lssl -lcrypto
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
TOOLCHAIN_STAMP := $(BUILD_DIR)/.toolchain
OBJECT_CHECK := $(BUILD_DIR)/.object-check.o

# Source files
MAIN_SRC := $(SRC_DIR)/main.c
SRCS := $(filter-out $(MAIN_SRC),$(wildcard $(SRC_DIR)/*.c))
OBJS := $(SRCS:$(SRC_DIR)/%.c=$(BUILD_DIR)/%.o)

# Main executable
MAIN_OBJ := $(BUILD_DIR)/main.o
EXECUTABLE := polycall$(EXE_EXT)
DEPS := $(OBJS:.o=.d) $(MAIN_OBJ:.o=.d)

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
all: dirs verify-objects $(STATIC_LIB) $(SHARED_LIB) $(BIN_DIR)/$(EXECUTABLE)

# Create necessary directories
.PHONY: dirs
ifdef CMD_SHELL
dirs:
	@if not exist $(BUILD_DIR) mkdir $(BUILD_DIR)
	@if not exist $(LIB_DIR) mkdir $(LIB_DIR)
	@if not exist $(BIN_DIR) mkdir $(BIN_DIR)
else
dirs:
	@mkdir -p $(BUILD_DIR) $(LIB_DIR) $(BIN_DIR)
endif

# Debug build
.PHONY: debug
debug: CFLAGS += $(DEBUG_FLAGS)
debug: all

# Release build
.PHONY: release
release: CFLAGS += $(RELEASE_FLAGS)
release: all

# Static release executable for minimal container runtimes
.PHONY: static
static: static-check
static: CFLAGS += $(RELEASE_FLAGS)
static: EXE_LDFLAGS += -static
static: all

.PHONY: static-check
static-check:
ifeq ($(PLATFORM),linux)
	@echo "Building static executable for Linux"
else ifeq ($(PLATFORM),macos)
	@echo "make static is unsupported on macOS because fully static executables are not available with the standard toolchain"
	@exit 1
else ifeq ($(PLATFORM),windows)
ifdef CMD_SHELL
	@$(CC) -dumpmachine 2>NUL | findstr /i "mingw" >NUL || (echo make static requires a MinGW GCC toolchain on Windows & exit 1)
else
	@$(CC) -dumpmachine 2>/dev/null | grep -qi mingw || (echo "make static requires a MinGW GCC toolchain on Windows"; exit 1)
endif
else
	@echo "make static is unsupported on this Unix platform"
	@exit 1
endif

# Compile source files
$(BUILD_DIR)/%.o: $(SRC_DIR)/%.c $(TOOLCHAIN_STAMP)
	$(CC) $(CFLAGS) -MMD -MP -c $< -o $@

# Compile main executable
$(BUILD_DIR)/main.o: $(MAIN_SRC) $(TOOLCHAIN_STAMP)
	$(CC) $(CFLAGS) -MMD -MP -c $< -o $@

# Rebuild objects whenever compiler, target platform, architecture, or flags change.
.PHONY: FORCE
FORCE:

ifdef CMD_SHELL
$(TOOLCHAIN_STAMP): FORCE | dirs
	@if not exist build mkdir build
	@echo CC=$(CC)>build\.toolchain.tmp
	@echo COMPILER_PATH=$(COMPILER_PATH)>>build\.toolchain.tmp
	@echo COMPILER_VERSION=$(COMPILER_VERSION)>>build\.toolchain.tmp
	@echo COMPILER_TARGET=$(COMPILER_TARGET)>>build\.toolchain.tmp
	@echo PLATFORM=$(PLATFORM)>>build\.toolchain.tmp
	@echo CFLAGS=$(CFLAGS);>>build\.toolchain.tmp
	@if not exist build\.toolchain (del /q build\*.o build\*.d 2>NUL & move /Y build\.toolchain.tmp build\.toolchain >NUL) else (fc /b build\.toolchain build\.toolchain.tmp >NUL || (echo Toolchain changed; removing stale build artifacts. & del /q build\*.o build\*.d lib\*.a lib\*.dll bin\polycall*.exe 2>NUL & move /Y build\.toolchain.tmp build\.toolchain >NUL))
	@if exist build\.toolchain.tmp del /q build\.toolchain.tmp
else
$(TOOLCHAIN_STAMP): FORCE | dirs
	@printf '%s\n' \
		'CC=$(CC)' \
		'COMPILER_PATH=$(COMPILER_PATH)' \
		'COMPILER_VERSION=$(COMPILER_VERSION)' \
		'COMPILER_TARGET=$(COMPILER_TARGET)' \
		'PLATFORM=$(PLATFORM)' \
		'CFLAGS=$(CFLAGS)' > $(TOOLCHAIN_STAMP).tmp
	@if test ! -f $(TOOLCHAIN_STAMP) || [ "$$(cat $(TOOLCHAIN_STAMP))" != "$$(cat $(TOOLCHAIN_STAMP).tmp)" ]; then \
		echo "Toolchain changed; removing stale build artifacts."; \
		rm -f $(BUILD_DIR)/*.o $(BUILD_DIR)/*.d \
			$(LIB_DIR)/*.a $(LIB_DIR)/*.so $(LIB_DIR)/*.dylib \
			$(BIN_DIR)/polycall; \
		mv $(TOOLCHAIN_STAMP).tmp $(TOOLCHAIN_STAMP); \
	else \
		rm -f $(TOOLCHAIN_STAMP).tmp; \
	fi
endif

.PHONY: objects
objects: $(OBJS) $(MAIN_OBJ)

# A relocatable link detects corrupt or foreign-format objects before final link.
.PHONY: verify-objects
verify-objects: $(OBJS) $(MAIN_OBJ)
ifdef CMD_SHELL
	@echo Verifying Windows object files...
	@$(CC) -r -nostdlib -o build\.object-check.o $(OBJS) $(MAIN_OBJ)
	@del /q build\.object-check.o
else
	@$(CC) -r -nostdlib -o $(OBJECT_CHECK) $(OBJS) $(MAIN_OBJ) 2>/dev/null || \
		(echo "Stale object files detected; recompiling all objects."; \
		rm -f $(BUILD_DIR)/*.o $(BUILD_DIR)/*.d; \
		$(MAKE) --no-print-directory objects)
	@$(CC) -r -nostdlib -o $(OBJECT_CHECK) $(OBJS) $(MAIN_OBJ)
	@rm -f $(OBJECT_CHECK)
endif

$(STATIC_LIB) $(SHARED_LIB): | verify-objects

# Create static library
$(STATIC_LIB): $(OBJS)
	ar rcs $@ $^

# Create shared library
$(SHARED_LIB): $(OBJS)
	$(CC) $(SHARED_LDFLAGS) -o $@ $^ $(LDFLAGS)

# Link executable
$(BIN_DIR)/$(EXECUTABLE): $(MAIN_OBJ) $(STATIC_LIB)
	$(CC) $(MAIN_OBJ) $(STATIC_LIB) -o $@ $(EXE_LDFLAGS)

# Install (Unix-like systems only)
.PHONY: install
install: all
ifeq ($(PLATFORM),windows)
	@echo "make install is not supported on Windows"
else
	@mkdir -p $(INSTALL_INC_DIR)
	@mkdir -p $(INSTALL_LIB_DIR)
	@mkdir -p $(INSTALL_BIN_DIR)
	cp $(INC_DIR)/*.h $(INSTALL_INC_DIR)
	cp $(STATIC_LIB) $(SHARED_LIB) $(INSTALL_LIB_DIR)
	cp $(BIN_DIR)/$(EXECUTABLE) $(INSTALL_BIN_DIR)
ifeq ($(PLATFORM),linux)
	ldconfig
endif
endif

# Uninstall (Unix-like systems only)
.PHONY: uninstall
uninstall:
ifeq ($(PLATFORM),windows)
	@echo "make uninstall is not supported on Windows"
else
	rm -rf $(INSTALL_INC_DIR)
	rm -f $(INSTALL_LIB_DIR)/$(LIB_NAME).*
	rm -f $(INSTALL_BIN_DIR)/$(EXECUTABLE)
endif

# Clean build files
.PHONY: clean
ifdef CMD_SHELL
clean:
	@if exist $(BUILD_DIR) rmdir /s /q $(BUILD_DIR)
	@if exist "$(LIB_DIR)\*.a" del /q "$(LIB_DIR)\*.a"
	@if exist "$(LIB_DIR)\*.dll" del /q "$(LIB_DIR)\*.dll"
	@if exist "$(BIN_DIR)\polycall*.exe" del /q "$(BIN_DIR)\polycall*.exe"
else
clean:
	rm -rf $(BUILD_DIR)
	rm -f $(LIB_DIR)/*.a $(LIB_DIR)/*.so $(LIB_DIR)/*.dylib
	rm -f $(BIN_DIR)/polycall
endif

# Remove every compiled artifact and regenerate libraries and the CLI.
.PHONY: rebuild
rebuild: clean
	$(MAKE) --no-print-directory all

# Clean everything including installed files
.PHONY: distclean
distclean: clean uninstall

# Ensure output directories exist before generating artifacts
$(OBJS) $(MAIN_OBJ) $(STATIC_LIB) $(SHARED_LIB) $(BIN_DIR)/$(EXECUTABLE): | dirs

# Include dependency files
-include $(DEPS)

# Help target
.PHONY: help
help:
	@echo "Available targets:"
	@echo "  all        - Build everything (default)"
	@echo "  debug      - Build with debug flags"
	@echo "  release    - Build with release flags"
	@echo "  static     - Build a static executable on supported platforms"
	@echo "  clean      - Remove build files"
	@echo "  rebuild    - Clean and recompile all libraries and the CLI"
	@echo "  install    - Install libraries and headers (unsupported on Windows)"
	@echo "  uninstall  - Remove installed files (unsupported on Windows)"
	@echo "  distclean  - Remove all generated files"
	@echo "  help       - Show this help message"
	@echo ""
	@echo "Options:"
	@echo "  USE_OPENSSL=1 - Link libssl/libcrypto when crypto APIs are used"

