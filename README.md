# Plugin_oled_display
grblHAL plugin for oled display - this is still a work in progress - be patient

### Boot
<img src="https://raw.githubusercontent.com/luc-github/Plugin_oled_display/refs/heads/main/pictures/boot.jpg" alt="drawing" width="200"/>

### 3 Axis
<img src="https://raw.githubusercontent.com/luc-github/Plugin_oled_display/refs/heads/main/pictures/3axis.jpg" alt="drawing" width="200"/>

### 4 Axis
<img src="https://raw.githubusercontent.com/luc-github/Plugin_oled_display/refs/heads/main/pictures/4axis.jpg" alt="drawing" width="200"/>

### 5 Axis
<img src="https://raw.githubusercontent.com/luc-github/Plugin_oled_display/refs/heads/main/pictures/5axis.jpg" alt="drawing" width="200"/>

### 6 Axis
<img src="https://raw.githubusercontent.com/luc-github/Plugin_oled_display/refs/heads/main/pictures/6axis.jpg" alt="drawing" width="200"/>

### Installation

* Add in plugins_init.h

```
#if DISPLAY_ENABLE == PLUGIN_OLED_DISPLAY
    extern bool plugin_oled_display_init (void);
    plugin_oled_display_init();
#endif
```

* In my_machine.h

`#define DISPLAY_ENABLE 33 //PLUGIN_OLED_DISPLAY`
then
`#define DISPLAY_TYPE 1 //DISPLAY_SSD1306_I2C`
or 
`#define DISPLAY_TYPE 3 //DISPLAY_SH1106_I2C`

Note: Be sure in plugins.h there is :

```
#define PLUGIN_OLED_DISPLAY     ((1<<5)|DISPLAY_I2C) //!< 33

// OLED Display
#define DISPLAY_SSD1306_I2C     ((1<<0)|DISPLAY_I2C) //!< 1
#define DISPLAY_SH1106_I2C      ((1<<1)|DISPLAY_I2C) //!< 3
```
* Copy plugin repository to  main 

ESP32/main/plugin_oled_display

* Edit ESP32/main/CMakeLists.txt
    - Set a variable for the path of the plugin source code
    
```
set(PLUGIN_OLED_DISPLAY_SOURCE
 plugin_oled_display/plugin_oled_display.c
 plugin_oled_display/oled_display.c
)
```
    - Add the paths to the global source code
    
```
list (APPEND SRCS ${PLUGIN_OLED_DISPLAY_SOURCE})

```

So you should get something like this:

```
set(USB_SOURCE
 usb_serial.c
)

set(PLUGIN_OLED_DISPLAY_SOURCE
 plugin_oled_display/plugin_oled_display.c
 plugin_oled_display/oled_display.c
)

if(EXISTS ${CMAKE_CURRENT_LIST_DIR}/../3rdParty.cmake)
include(${CMAKE_CURRENT_LIST_DIR}/../3rdParty.cmake)
endif()

if("${target}" STREQUAL "esp32s3")
list (APPEND SRCS ${USB_SOURCE})
list (APPEND SRCS ${I2S_S3_SOURCE})
else()
list (APPEND SRCS ${I2S_SOURCE})
endif()

list (APPEND SRCS ${MY_PLUGIN_SOURCE})
list (APPEND SRCS ${NETWORKING_SOURCE})
list (APPEND SRCS ${KEYPAD_SOURCE})
list (APPEND SRCS ${TRINAMIC_SPI_SOURCE})
list (APPEND SRCS ${TRINAMIC_UART_SOURCE})
list (APPEND SRCS ${WEBUI_SOURCE})
list (APPEND SRCS ${SDCARD_SOURCE})
list (APPEND SRCS ${BLUETOOTH_SOURCE})
list (APPEND SRCS ${MODBUS_SOURCE})
list (APPEND SRCS ${SPINDLE_SOURCE})
list (APPEND SRCS ${EEPROM_SOURCE})
list (APPEND SRCS ${LASER_SOURCE})
list (APPEND SRCS ${MISC_PLUGINS_SOURCE})
list (APPEND SRCS ${EMBROIDERY_SOURCE})
list (APPEND SRCS ${OPENPNP_SOURCE})
list (APPEND SRCS ${PLUGIN_OLED_DISPLAY_SOURCE})
```

### Tools

1. **Font Converter** (`font_converter.py`) - Converts TrueType fonts to OLED-compatible bitmap font arrays
2. **PNG Converter** (`png_converter.py`) - Converts PNG images to XBM format for OLED display
3. **Font Metrics Extractor** (`ttf_info_extractor.py`) - Advanced tool for analyzing font metrics and diagnosing rendering issues
4. **Font Generator** (`font_generator.py`) - Create custom bitmap fonts by editing pixel-perfect templates
