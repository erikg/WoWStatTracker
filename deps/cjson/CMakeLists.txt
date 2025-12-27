# cJSON library
# MIT License - https://github.com/DaveGamble/cJSON

add_library(cjson STATIC cJSON.c)
target_include_directories(cjson PUBLIC ${CMAKE_CURRENT_SOURCE_DIR})

# Disable unused features to reduce size
target_compile_definitions(cjson PRIVATE
    CJSON_HIDE_SYMBOLS
)
