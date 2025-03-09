add_library(plugin_oled_display INTERFACE)

target_sources(plugin_display INTERFACE
 ${CMAKE_CURRENT_LIST_DIR}/plugin_oled_display.c
 ${CMAKE_CURRENT_LIST_DIR}/oled_display.c
)

target_include_directories(plugin_oled_display INTERFACE ${CMAKE_CURRENT_LIST_DIR})
