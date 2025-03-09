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
#if PLDISPLAY_ENABLE == OLED_DISPLAY_I2CUGIN_OLED_DISPLAY_ENABLE
    extern bool plugin_oled_display_init (void);
    plugin_oled_display_init();
#endif
```

in my_machine.h

`#define DISPLAY_ENABLE PLUGIN_OLED_DISPLAY`
then
`#define DISPLAY_TYPE DISPLAY_SSD1306_I2C`
or 
`#define DISPLAY_TYPE DISPLAY_SH1106_I2C`

Note: Be sure in plugins.h there is :

```
#define PLUGIN_OLED_DISPLAY     ((1<<5)|DISPLAY_I2C) //!< 33

// OLED Display
#define DISPLAY_SSD1306_I2C     ((1<<0)|DISPLAY_I2C) //!< 1
#define DISPLAY_SH1106_I2C      ((1<<1)|DISPLAY_I2C) //!< 3
```

### Tools

1. **Font Converter** (`font_converter.py`) - Converts TrueType fonts to OLED-compatible bitmap font arrays
2. **PNG Converter** (`png_converter.py`) - Converts PNG images to XBM format for OLED display
3. **Font Metrics Extractor** (`ttf_info_extractor.py`) - Advanced tool for analyzing font metrics and diagnosing rendering issues
4. **Font Generator** (`font_generator.py`) - Create custom bitmap fonts by editing pixel-perfect templates
