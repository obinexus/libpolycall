cmake_minimum_required(VERSION 3.13)
project(libpolycall VERSION 1.1.0 LANGUAGES C)
# Include standardization tools
include(IncludeStandardization)
polycall_register_include_targets()
# Include core build system modules
list(APPEND CMAKE_MODULE_PATH "${CMAKE_CURRENT_SOURCE_DIR}/cmake")
include(BuildSystem)
include(Hooks)
include(ComponentBuild)
include(TestFramework)  # Explicitly include testing framework

# Initialize build system with directories
polycall_init_hook_system(
  OBJ_DIR "${CMAKE_BINARY_DIR}/obj"
  BIN_DIR "${CMAKE_BINARY_DIR}/bin"
  LIB_DIR "${CMAKE_BINARY_DIR}/lib"
  TEST_DIR "${CMAKE_BINARY_DIR}/tests"
  LOG_DIR "${CMAKE_BINARY_DIR}/logs"
  VERBOSE
)

# Initialize build system with testing enabled
polycall_init_build_system(
  VERSION "${PROJECT_VERSION}"
  ENABLE_TESTING
  ENABLE_COVERAGE
)

# Find dependencies
polycall_find_dependencies()

# Execute pre-build hooks
polycall_execute_pre_build_hooks()

# Core component definitions - discover components first to ensure proper registration
file(GLOB CORE_COMPONENTS RELATIVE "${CMAKE_CURRENT_SOURCE_DIR}/src/core" "${CMAKE_CURRENT_SOURCE_DIR}/src/core/*")
set(VALID_CORE_COMPONENTS "")

foreach(COMPONENT ${CORE_COMPONENTS})
  if(IS_DIRECTORY "${CMAKE_CURRENT_SOURCE_DIR}/src/core/${COMPONENT}")
    list(APPEND VALID_CORE_COMPONENTS ${COMPONENT})
    polycall_register_component(${COMPONENT})
    # Create component object directory
    file(MAKE_DIRECTORY "${CMAKE_BINARY_DIR}/obj/core/${COMPONENT}")
  endif()
endforeach()

message(STATUS "Discovered core components: ${VALID_CORE_COMPONENTS}")

# Add core components
add_subdirectory("src/core")

# CLI components
add_subdirectory("src/cli" EXCLUDE_FROM_ALL)

# Main executable
polycall_define_main_executable(
  NAME "polycall"
  VERSION "${PROJECT_VERSION}"
  SOURCES "${POLYCALL_SRC_DIR}/polycall.c"
  DEPENDENCIES polycall_core_static polycall_cli
)

# Define core libraries
polycall_define_core_libraries(
  VERSION "${PROJECT_VERSION}"
  COMPONENTS ${VALID_CORE_COMPONENTS}
)

# Generate unified header
polycall_generate_unified_header(
  OUTPUT "${POLYCALL_BUILD_DIR}/include/polycall.h"
  TEMPLATE "${POLYCALL_PROJECT_ROOT}/templates/polycall.h.in"
  COMPONENTS ${VALID_CORE_COMPONENTS}
)

# Package configuration
polycall_init_package_config(
  VERSION "${PROJECT_VERSION}"
  DESCRIPTION "LibPolyCall: Cross-language Platform Communication Library"
  VENDOR "OBINexusComputing"
)

# Installation setup
polycall_install_unified_header()
polycall_install_development_components()
polycall_install_executable(TARGET polycall)

# Enhanced testing setup
if(BUILD_TESTING)
  enable_testing()
  
  # Initialize test system with components
  polycall_init_test_system(
    COMPONENTS ${VALID_CORE_COMPONENTS}
    COVERAGE TRUE
  )
  
  # Setup test framework
  polycall_generate_test_stubs(
    COMPONENTS ${VALID_CORE_COMPONENTS}
    SETUP_FRAMEWORK TRUE
  )
  
  # Add testing directories
  add_subdirectory(tests)
  
  # Create test targets
  add_custom_target(test:unit
    COMMENT "Running all unit tests"
    COMMAND ${CMAKE_CTEST_COMMAND} -C ${CMAKE_BUILD_TYPE} -L unit
  )
  
  add_custom_target(test:integration
    COMMENT "Running all integration tests"
    COMMAND ${CMAKE_CTEST_COMMAND} -C ${CMAKE_BUILD_TYPE} -L integration
  )
  
  add_custom_target(test:all
    COMMENT "Running all tests"
    COMMAND ${CMAKE_CTEST_COMMAND} -C ${CMAKE_BUILD_TYPE}
  )
endif()

# Create debug/release targets
add_custom_target(debug
  COMMAND ${CMAKE_COMMAND} -DCMAKE_BUILD_TYPE=Debug ${CMAKE_SOURCE_DIR}
  COMMAND ${CMAKE_COMMAND} --build ${CMAKE_BINARY_DIR} --config Debug
  COMMENT "Building debug configuration"
)

add_custom_target(release
  COMMAND ${CMAKE_COMMAND} -DCMAKE_BUILD_TYPE=Release ${CMAKE_SOURCE_DIR}
  COMMAND ${CMAKE_COMMAND} --build ${CMAKE_BINARY_DIR} --config Release
  COMMENT "Building release configuration"
)

# Update validation targets with correct script paths
add_custom_target(validate
  DEPENDS validate_includes
  COMMENT "Validating codebase"
)

# Standardize includes target with correct script path
add_custom_target(standardize-includes
  COMMAND python3 ${POLYCALL_PROJECT_ROOT}/scripts/standardization/standardize_includes.py --project-root ${POLYCALL_PROJECT_ROOT} --verbose
  COMMENT "Standardizing include paths"
)

# Fix includes target with correct script path
add_custom_target(fix-includes
  COMMAND ${POLYCALL_PROJECT_ROOT}/scripts/include_fix/fix_all_includes.sh --project-root ${POLYCALL_PROJECT_ROOT} --verbose
  COMMENT "Fixing include paths"
)

# Create development workflow target
add_custom_target(dev_workflow
  DEPENDS validate fix-includes standardize-includes build test:all
  COMMENT "Running complete development workflow"
)

# Create development cycle target (matching Makefile)
add_custom_target(dev-cycle
  DEPENDS validate_includes fix_includes standardize-includes polycall_static polycall_shared polycall_executable test:all
  COMMENT "Running complete development cycle"
)
cmake_minimum_required(VERSION 3.10)
project(libpolycall VERSION 1.1.0 LANGUAGES C)

# Include core build system modules
set(CMAKE_MODULE_PATH "${CMAKE_CURRENT_SOURCE_DIR}/cmake")
include(BuildSystem)
include(Hooks)
include(ComponentBuild)
include(TestFramework)

# Initialize hook system
polycall_init_hook_system()

# Set library version
set(POLYCALL_VERSION_MAJOR 1)
set(POLYCALL_VERSION_MINOR 1)
set(POLYCALL_VERSION_PATCH 0)
set(POLYCALL_VERSION "${POLYCALL_VERSION_MAJOR}.${POLYCALL_VERSION_MINOR}.${POLYCALL_VERSION_PATCH}")

# Set installation paths
set(POLYCALL_INCLUDE_INSTALL_DIR "include")
set(POLYCALL_LIB_INSTALL_DIR "lib")
set(POLYCALL_BIN_INSTALL_DIR "bin")

# Add subdirectories
add_subdirectory(src)

# Enable testing if requested
if(ENABLE_TESTS)
  polycall_enable_testing()
  add_subdirectory(tests)
endif()

# Install configuration
include(GNUInstallDirs)
include(CMakePackageConfigHelpers)

# Configure and install package files
configure_package_config_file(
  ${CMAKE_CURRENT_SOURCE_DIR}/cmake/polycall-config.cmake.in
  ${CMAKE_CURRENT_BINARY_DIR}/polycall-config.cmake
  INSTALL_DESTINATION ${CMAKE_INSTALL_LIBDIR}/cmake/polycall
  PATH_VARS POLYCALL_INCLUDE_INSTALL_DIR
)

write_basic_package_version_file(
  ${CMAKE_CURRENT_BINARY_DIR}/polycall-config-version.cmake
  VERSION ${POLYCALL_VERSION}
  COMPATIBILITY SameMajorVersion
)

install(
  FILES
    ${CMAKE_CURRENT_BINARY_DIR}/polycall-config.cmake
    ${CMAKE_CURRENT_BINARY_DIR}/polycall-config-version.cmake
  DESTINATION ${CMAKE_INSTALL_LIBDIR}/cmake/polycall
  COMPONENT devel
)

# CPack configuration
include(CPack)
# Execute post-build hooks
polycall_execute_post_build_hooks()

# Additional developer utilities
include(CTest)

# Documentation generation (if Doxygen is available)
find_package(Doxygen QUIET)
if(DOXYGEN_FOUND)
  set(DOXYGEN_OUTPUT_DIRECTORY "${CMAKE_BINARY_DIR}/docs")
  set(DOXYGEN_PROJECT_NAME "LibPolyCall")
  set(DOXYGEN_PROJECT_NUMBER "${PROJECT_VERSION}")
  set(DOXYGEN_PROJECT_BRIEF "Cross-language Platform Communication Library")
  set(DOXYGEN_EXTRACT_ALL YES)
  set(DOXYGEN_EXTRACT_PRIVATE YES)
  set(DOXYGEN_EXTRACT_STATIC YES)
  
  add_custom_target(docs
    COMMAND ${DOXYGEN_EXECUTABLE} ${CMAKE_BINARY_DIR}/Doxyfile
    WORKING_DIRECTORY ${CMAKE_SOURCE_DIR}
    COMMENT "Generating API documentation with Doxygen"
    VERBATIM
  )
  
  # Generate Doxyfile
  if(EXISTS "${CMAKE_CURRENT_SOURCE_DIR}/templates/Doxyfile.in")
    configure_file(
      ${CMAKE_CURRENT_SOURCE_DIR}/templates/Doxyfile.in
      ${CMAKE_BINARY_DIR}/Doxyfile
      @ONLY
    )
  else()
    message(STATUS "Doxyfile template not found - using default configuration")
    doxygen_add_docs(docs
      ${CMAKE_SOURCE_DIR}/src
      ${CMAKE_SOURCE_DIR}/include
      COMMENT "Generating API documentation with Doxygen"
    )
  endif()
  
  message(STATUS "Doxygen found: Documentation target available")
else()
  add_custom_target(docs
    COMMAND ${CMAKE_COMMAND} -E echo "Doxygen not found - documentation generation disabled"
    COMMENT "Doxygen not found - documentation generation disabled"
  )
  message(STATUS "Doxygen not found - documentation generation disabled")
endif()

# Print build system status
message(STATUS "LibPolyCall build system configuration complete")
message(STATUS "Version: ${PROJECT_VERSION}")
message(STATUS "Build type: ${CMAKE_BUILD_TYPE}")
message(STATUS "Testing enabled: ${BUILD_TESTING}")
message(STATUS "Registered components: ${VALID_CORE_COMPONENTS}")

cmake_minimum_required(VERSION 3.10)
project(libpolycall VERSION 1.1.0 LANGUAGES C)

# Include core build system modules
set(CMAKE_MODULE_PATH "${CMAKE_CURRENT_SOURCE_DIR}/cmake")
include(BuildSystem)
include(Hooks)
include(ComponentBuild)
include(TestFramework)
include(IncludePathValidation)

# Initialize hook system
polycall_init_hook_system()

# Define project structure
set(POLYCALL_SRC_DIR "${CMAKE_CURRENT_SOURCE_DIR}/src")
set(POLYCALL_INCLUDE_DIR "${CMAKE_CURRENT_SOURCE_DIR}/include")
set(POLYCALL_TEST_DIR "${CMAKE_CURRENT_SOURCE_DIR}/tests")
set(POLYCALL_CLI_DIR "${POLYCALL_SRC_DIR}/cli")
set(POLYCALL_CORE_DIR "${POLYCALL_SRC_DIR}/core")

# Output directories
set(CMAKE_ARCHIVE_OUTPUT_DIRECTORY ${CMAKE_BINARY_DIR}/lib)
set(CMAKE_LIBRARY_OUTPUT_DIRECTORY ${CMAKE_BINARY_DIR}/lib)
set(CMAKE_RUNTIME_OUTPUT_DIRECTORY ${CMAKE_BINARY_DIR}/bin)

# Compiler settings
set(CMAKE_C_STANDARD 11)
set(CMAKE_C_STANDARD_REQUIRED ON)
add_compile_options(-Wall -Wextra -fPIC)

# Default build type
if(NOT CMAKE_BUILD_TYPE)
  set(CMAKE_BUILD_TYPE Release)
endif()

# Global include directories
include_directories(${POLYCALL_INCLUDE_DIR})

# Dependency setup
find_package(Threads REQUIRED)

# Define core components
add_subdirectory(src)

# Testing setup
option(BUILD_TESTING "Build the testing tree" OFF)
if(BUILD_TESTING)
  enable_testing()
  add_subdirectory(tests)
endif()

# Installation configuration
include(GNUInstallDirs)
include(CMakePackageConfigHelpers)

# Configure package files
configure_package_config_file(
  "cmake/polycall-config.cmake.in"
  "${CMAKE_CURRENT_BINARY_DIR}/polycall-config.cmake"
  INSTALL_DESTINATION ${CMAKE_INSTALL_LIBDIR}/cmake/polycall
  PATH_VARS CMAKE_INSTALL_INCLUDEDIR
)

write_basic_package_version_file(
  "${CMAKE_CURRENT_BINARY_DIR}/polycall-config-version.cmake"
  VERSION ${PROJECT_VERSION}
  COMPATIBILITY SameMajorVersion
)

# Install targets
install(
  EXPORT polycall-targets
  FILE polycall-targets.cmake
  NAMESPACE polycall::
  DESTINATION ${CMAKE_INSTALL_LIBDIR}/cmake/polycall
)

install(
  FILES
    "${CMAKE_CURRENT_BINARY_DIR}/polycall-config.cmake"
    "${CMAKE_CURRENT_BINARY_DIR}/polycall-config-version.cmake"
  DESTINATION ${CMAKE_INSTALL_LIBDIR}/cmake/polycall
)

install(
  DIRECTORY include/
  DESTINATION ${CMAKE_INSTALL_INCLUDEDIR}
  FILES_MATCHING PATTERN "*.h"
)

# CPack configuration
include(CPack)include(cmake/sinphase_phase_gates.cmake)
