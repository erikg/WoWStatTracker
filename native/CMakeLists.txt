cmake_minimum_required(VERSION 3.20)
project(WoWStatTracker VERSION 1.2.0 LANGUAGES C)

# C standard
set(CMAKE_C_STANDARD 11)
set(CMAKE_C_STANDARD_REQUIRED ON)

# Build options
option(WST_BUILD_TESTS "Build unit tests" ON)
option(WST_ENABLE_LTO "Enable Link Time Optimization" ON)

# Platform detection
if(APPLE)
    set(WST_PLATFORM_MACOS ON)
    enable_language(OBJC)
elseif(WIN32)
    set(WST_PLATFORM_WINDOWS ON)
endif()

# Release build optimizations
if(CMAKE_BUILD_TYPE STREQUAL "Release")
    if(WST_ENABLE_LTO)
        set(CMAKE_INTERPROCEDURAL_OPTIMIZATION ON)
    endif()
    if(MSVC)
        add_compile_options(/O2 /GL)
        add_link_options(/LTCG)
    else()
        add_compile_options(-O2 -fvisibility=hidden)
    endif()
endif()

# Strip symbols in release
if(CMAKE_BUILD_TYPE STREQUAL "Release" AND NOT MSVC)
    add_link_options(-s)
endif()

# Dependencies
add_subdirectory(deps/cjson)
add_subdirectory(deps/lua-5.1)

# Core library (platform-agnostic)
add_library(wst_core STATIC
    src/core/util.c
    src/core/character.c
    src/core/character_store.c
    src/core/config.c
    src/core/notification.c
    src/core/week_id.c
    src/core/paths.c
    src/core/lua_parser.c
)

target_include_directories(wst_core PUBLIC
    ${CMAKE_CURRENT_SOURCE_DIR}/src/core
    ${CMAKE_CURRENT_SOURCE_DIR}/deps/cjson
    ${CMAKE_CURRENT_SOURCE_DIR}/deps/lua-5.1/src
)

target_link_libraries(wst_core PUBLIC cjson lua)

# Build options for phases
option(WST_BUILD_PLATFORM "Build platform abstraction layer (Phase 2)" OFF)
option(WST_BUILD_GUI "Build GUI application (Phase 3/4)" OFF)

# Platform-specific sources (Phase 2)
if(WST_BUILD_PLATFORM)
    if(WST_PLATFORM_MACOS)
        add_library(wst_platform STATIC
            src/platform/macos/platform_macos.m
        )
        target_include_directories(wst_platform PUBLIC
            ${CMAKE_CURRENT_SOURCE_DIR}/src/platform
            ${CMAKE_CURRENT_SOURCE_DIR}/src/core
        )
        target_link_libraries(wst_platform PUBLIC wst_core)
        find_library(FOUNDATION Foundation REQUIRED)
        find_library(APPKIT AppKit REQUIRED)
        target_link_libraries(wst_platform PUBLIC ${FOUNDATION} ${APPKIT})
    elseif(WST_PLATFORM_WINDOWS)
        add_library(wst_platform STATIC
            src/platform/windows/platform_windows.c
        )
        target_include_directories(wst_platform PUBLIC
            ${CMAKE_CURRENT_SOURCE_DIR}/src/platform
        )
        target_link_libraries(wst_platform PUBLIC wst_core winhttp)
    endif()
endif()

# Main executable (Phase 3/4)
if(WST_BUILD_GUI)
    # GUI requires platform layer
    if(NOT WST_BUILD_PLATFORM)
        message(FATAL_ERROR "WST_BUILD_GUI requires WST_BUILD_PLATFORM=ON")
    endif()

    if(WST_PLATFORM_MACOS)
        add_executable(WoWStatTracker MACOSX_BUNDLE
            src/gui/macos/main.m
            src/gui/macos/AppDelegate.m
            src/gui/macos/MainWindowController.m
            src/gui/macos/CharacterTableView.m
        )

        target_include_directories(WoWStatTracker PRIVATE
            ${CMAKE_CURRENT_SOURCE_DIR}/src/core
            ${CMAKE_CURRENT_SOURCE_DIR}/src/platform
            ${CMAKE_CURRENT_SOURCE_DIR}/src/gui/macos
        )

        set_target_properties(WoWStatTracker PROPERTIES
            MACOSX_BUNDLE_INFO_PLIST ${CMAKE_CURRENT_SOURCE_DIR}/packaging/macos/Info.plist.in
            MACOSX_BUNDLE_BUNDLE_NAME "WoW Stat Tracker"
            MACOSX_BUNDLE_BUNDLE_VERSION ${PROJECT_VERSION}
            MACOSX_BUNDLE_SHORT_VERSION_STRING ${PROJECT_VERSION}
            MACOSX_BUNDLE_GUI_IDENTIFIER "com.wowstat.WoWStatTracker"
        )

        find_library(COCOA Cocoa REQUIRED)
        target_link_libraries(WoWStatTracker PRIVATE wst_platform ${COCOA})

    elseif(WST_PLATFORM_WINDOWS)
        add_executable(WoWStatTracker WIN32
            src/gui/windows/main.c
            src/gui/windows/main_window.c
            src/gui/windows/dialogs.c
            src/gui/windows/resource.rc
        )

        target_include_directories(WoWStatTracker PRIVATE
            ${CMAKE_CURRENT_SOURCE_DIR}/src/core
            ${CMAKE_CURRENT_SOURCE_DIR}/src/platform
            ${CMAKE_CURRENT_SOURCE_DIR}/src/gui/windows
        )

        target_link_libraries(WoWStatTracker PRIVATE
            wst_platform
            comctl32
            uxtheme
            dwmapi
            shlwapi
        )

        # Use static runtime on Windows
        set_property(TARGET WoWStatTracker PROPERTY
            MSVC_RUNTIME_LIBRARY "MultiThreaded$<$<CONFIG:Debug>:Debug>"
        )
    endif()
endif()

# Installation rules
if(WST_BUILD_GUI)
    if(WST_PLATFORM_MACOS)
        # Install app bundle to /Applications
        install(TARGETS WoWStatTracker
            BUNDLE DESTINATION .
            COMPONENT Runtime
        )

        # Install addon to Resources
        install(DIRECTORY ${CMAKE_CURRENT_SOURCE_DIR}/../WoWStatTracker_Addon
            DESTINATION WoWStatTracker.app/Contents/Resources
            COMPONENT Runtime
            OPTIONAL
        )

    elseif(WST_PLATFORM_WINDOWS)
        # Install executable
        install(TARGETS WoWStatTracker
            RUNTIME DESTINATION .
            COMPONENT Runtime
        )

        # Install addon
        install(DIRECTORY ${CMAKE_CURRENT_SOURCE_DIR}/../WoWStatTracker_Addon
            DESTINATION .
            COMPONENT Runtime
            OPTIONAL
        )
    endif()

    # CPack configuration
    set(CPACK_PACKAGE_NAME "WoWStatTracker")
    set(CPACK_PACKAGE_VENDOR "WoW Stat Tracker")
    set(CPACK_PACKAGE_DESCRIPTION_SUMMARY "Track your World of Warcraft character statistics")
    set(CPACK_PACKAGE_VERSION ${PROJECT_VERSION})
    set(CPACK_PACKAGE_VERSION_MAJOR ${PROJECT_VERSION_MAJOR})
    set(CPACK_PACKAGE_VERSION_MINOR ${PROJECT_VERSION_MINOR})
    set(CPACK_PACKAGE_VERSION_PATCH ${PROJECT_VERSION_PATCH})
    set(CPACK_RESOURCE_FILE_LICENSE "${CMAKE_CURRENT_SOURCE_DIR}/../LICENSE")

    if(WST_PLATFORM_MACOS)
        set(CPACK_GENERATOR "DragNDrop")
        set(CPACK_DMG_VOLUME_NAME "WoW Stat Tracker")
        set(CPACK_DMG_FORMAT "UDZO")
    elseif(WST_PLATFORM_WINDOWS)
        set(CPACK_GENERATOR "ZIP;WIX")
        set(CPACK_WIX_UPGRADE_GUID "12345678-1234-1234-1234-123456789ABC")
        set(CPACK_WIX_PRODUCT_ICON "${CMAKE_CURRENT_SOURCE_DIR}/packaging/windows/icon.ico")
    endif()

    include(CPack)
endif()

# Unit tests
if(WST_BUILD_TESTS)
    enable_testing()
    add_subdirectory(test)
endif()
