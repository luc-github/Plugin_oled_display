add_library(plugin_display INTERFACE)

target_sources(plugin_display INTERFACE
 ${CMAKE_CURRENT_LIST_DIR}/plugin_display.c
 ${CMAKE_CURRENT_LIST_DIR}/oled_display.c
)

target_include_directories(plugin_display INTERFACE ${CMAKE_CURRENT_LIST_DIR})
