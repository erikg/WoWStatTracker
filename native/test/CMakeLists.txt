# WoW Stat Tracker - Unit Tests
# Uses Unity test framework

add_library(unity STATIC unity.c)
target_include_directories(unity PUBLIC ${CMAKE_CURRENT_SOURCE_DIR})

# Enable double precision support in Unity
target_compile_definitions(unity PUBLIC UNITY_INCLUDE_DOUBLE)

# Core test sources
set(TEST_SOURCES
    test_main.c
    test_util.c
    test_character.c
    test_character_store.c
    test_config.c
    test_week_id.c
)

# Add platform tests if platform layer is being built
if(WST_BUILD_PLATFORM)
    list(APPEND TEST_SOURCES test_platform.c)
endif()

# Test executable
add_executable(wst_tests ${TEST_SOURCES})

target_link_libraries(wst_tests PRIVATE
    wst_core
    unity
)

# Link platform library if building platform layer
if(WST_BUILD_PLATFORM)
    target_link_libraries(wst_tests PRIVATE wst_platform)
    target_compile_definitions(wst_tests PRIVATE WST_BUILD_PLATFORM)
endif()

target_include_directories(wst_tests PRIVATE
    ${CMAKE_SOURCE_DIR}/src/core
    ${CMAKE_SOURCE_DIR}/src/platform
)

# Register with CTest
add_test(NAME wst_tests COMMAND wst_tests)

# Set working directory for tests
set_tests_properties(wst_tests PROPERTIES
    WORKING_DIRECTORY ${CMAKE_CURRENT_BINARY_DIR}
)
