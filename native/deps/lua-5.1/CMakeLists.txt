# Lua 5.1 library
# MIT License - https://www.lua.org/license.html

# Core Lua library sources (excluding standalone lua.c, luac.c, print.c)
set(LUA_CORE_SRC
    src/lapi.c
    src/lcode.c
    src/ldebug.c
    src/ldo.c
    src/ldump.c
    src/lfunc.c
    src/lgc.c
    src/llex.c
    src/lmem.c
    src/lobject.c
    src/lopcodes.c
    src/lparser.c
    src/lstate.c
    src/lstring.c
    src/ltable.c
    src/ltm.c
    src/lundump.c
    src/lvm.c
    src/lzio.c
)

# Auxiliary library
set(LUA_LIB_SRC
    src/lauxlib.c
    src/linit.c
)

# Standard libraries (minimal set needed for parsing)
set(LUA_STD_SRC
    src/lbaselib.c
    src/ltablib.c
    src/lstrlib.c
)

add_library(lua STATIC
    ${LUA_CORE_SRC}
    ${LUA_LIB_SRC}
    ${LUA_STD_SRC}
)

target_include_directories(lua PUBLIC ${CMAKE_CURRENT_SOURCE_DIR}/src)

# Platform-specific defines
if(APPLE)
    target_compile_definitions(lua PRIVATE LUA_USE_MACOSX)
elseif(WIN32)
    target_compile_definitions(lua PRIVATE LUA_BUILD_AS_DLL=0)
endif()

# Suppress warnings in third-party code
if(MSVC)
    target_compile_options(lua PRIVATE /W0)
else()
    target_compile_options(lua PRIVATE -w)
endif()
