# CMakeLists.txt for LibPolyCall unit/core/polycall tests
cmake_minimum_required(VERSION 3.13)

# Get all test sources in this directory
file(GLOB polycall_TEST_SOURCES "*.c")

# Function to add a unit test
function(add_polycall_test TEST_NAME TEST_SOURCE)
    # Create executable
    add_executable(${TEST_NAME} ${TEST_SOURCE})
    
    # Link against test framework and component libraries/stubs
    target_link_libraries(${TEST_NAME} PRIVATE
        polycall_test_framework
        polycall_static
    )
    
    # Add include directories
    target_include_directories(${TEST_NAME} PRIVATE
        ${CMAKE_SOURCE_DIR}/include
        ${CMAKE_SOURCE_DIR}/include/__tests__
        ${CMAKE_SOURCE_DIR}/src
        ${CMAKE_CURRENT_SOURCE_DIR}/../../../
    )
    
    # Add as test
    add_test(NAME ${TEST_NAME} COMMAND ${TEST_NAME})
    
    # Add run target
    add_custom_target(run_${TEST_NAME}
        COMMAND ${CMAKE_CURRENT_BINARY_DIR}/${TEST_NAME}
        DEPENDS ${TEST_NAME}
        COMMENT "Running test ${TEST_NAME}"
    )
    
    # Add to component tests list
    add_dependencies(unit_core_polycall_tests ${TEST_NAME})
endfunction()

# Create target for polycall unit tests
add_custom_target(unit_core_polycall_tests
    COMMENT "polycall unit tests target"
)

# Add all tests in this directory
foreach(TEST_SOURCE ${polycall_TEST_SOURCES})
    # Get test name from file name
    get_filename_component(TEST_NAME ${TEST_SOURCE} NAME_WE)
    
    # Create full test name with component prefix
    set(FULL_TEST_NAME "test_core_polycall_${TEST_NAME}")
    
    # Add the test
    add_polycall_test(${FULL_TEST_NAME} ${TEST_SOURCE})
endforeach()

# Create a target that runs all polycall tests
add_custom_target(run_core_polycall_tests
    DEPENDS unit_core_polycall_tests
    COMMENT "Running all polycall tests"
)

# Add this component's tests to the unit_core_tests target
add_dependencies(unit_core_tests unit_core_polycall_tests)
