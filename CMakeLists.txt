add_library(oled_display INTERFACE)

target_sources(my_plugin INTERFACE
 ${CMAKE_CURRENT_LIST_DIR}/oled_display.c
)

target_include_directories(oled_display INTERFACE ${CMAKE_CURRENT_LIST_DIR})