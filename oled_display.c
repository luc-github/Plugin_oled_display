/*

  oled_display.c - plugin for displaying informations on oled screen.

  Part of grblHAL

  Copyright (c) 2025 Luc LEBOSSE

  grblHAL is free software: you can redistribute it and/or modify
  it under the terms of the GNU General Public License as published by
  the Free Software Foundation, either version 3 of the License, or
  (at your option) any later version.

  grblHAL is distributed in the hope that it will be useful,
  but WITHOUT ANY WARRANTY; without even the implied warranty of
  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
  GNU General Public License for more programmed.

  You should have received a copy of the GNU General Public License
  along with grblHAL. If not, see <http://www.gnu.org/licenses/>.

*/
#ifdef ARDUINO
#include "../driver.h"
#include "../grbl/hal.h"
#include "../grbl/task.h"
#include "../grbl/system.h"
#else
#include "driver.h"
#include "grbl/hal.h"
#include "grbl/task.h"
#include "grbl/system.h"
#endif //ARDUINO
#include "grbl/report.h"

#define POLLING_DELAY 800

#if defined(OLED_DISPLAY_ENABLE)
#include "oled_display.h"
// Include according to the display type
#include "ssd1306_i2c.h"
#if ETHERNET_ENABLE || WIFI_ENABLE
#ifdef ARDUINO
#include "../networking/networking.h"
#else 
#include "networking/networking.h"
#endif //ARDUINO
#endif //ETHERNET_ENABLE || WIFI_ENABLE

// --------------------------------------------------------
// Types and Constants
// --------------------------------------------------------

/**
 * Display color enumeration
 */
typedef enum {
    DISPLAY_COLOR_BLACK = 0,    // Pixel off
    DISPLAY_COLOR_WHITE = 1,    // Pixel on
    DISPLAY_COLOR_INVERSE = 2   // Invert pixel
} display_color_t;

/**
 * Font information structure
 */
typedef struct {
    uint8_t width;          // Maximum character width
    uint8_t height;         // Character height
    uint8_t first_char;     // First character code in font
    uint8_t char_count;     // Number of characters in font
} font_info_t;

/**
 * Character information structure
 */
typedef struct {
    uint16_t bitmap_offset; // Offset to bitmap data
    uint8_t width;          // Character width
    uint8_t bytes;          // Size in bytes
    bool is_defined;        // Whether character is defined in font
} char_info_t;

// Define font sizes
typedef enum {
    DISPLAY_FONT_SMALL,
    DISPLAY_FONT_MEDIUM,
    DISPLAY_FONT_BIG
} display_font_size_t;

// Define data to display
typedef struct {
    const char *state;
#if ETHERNET_ENABLE || WIFI_ENABLE
    char ip[30];
#endif //ETHERNET_ENABLE || WIFI_ENABLE
    float pos[N_AXIS];
    char pos_str[N_AXIS][STRLEN_COORDVALUE + 1];
    bool end_stop[N_AXIS];
} oled_screen_data_t;

// Constants
static const uint8_t CHAR_SPACING = 1;             // Spacing between characters
static const uint8_t BITS_PER_BYTE = 8;            // Number of bits in a byte
static const uint8_t FONT_HEADER_SIZE = 4;         // Size of font header in bytes
static const uint8_t JUMPTABLE_BYTES_PER_CHAR = 4; // Size of jump table entry per character

// Jump table entry structure
static const uint8_t JUMPTABLE_MSB_OFFSET = 0;     // Offset for MSB in jump table
static const uint8_t JUMPTABLE_LSB_OFFSET = 1;     // Offset for LSB in jump table
static const uint8_t JUMPTABLE_SIZE_OFFSET = 2;    // Offset for size in jump table
static const uint8_t JUMPTABLE_WIDTH_OFFSET = 3;   // Offset for width in jump table

// Global variables
static on_report_options_ptr on_report_options;
static on_state_change_ptr on_state_change;
static const char* current_font = NULL;
static display_color_t current_color = DISPLAY_COLOR_WHITE;
static oled_screen_data_t screen1;
static bool display_connected = false;

#if ETHERNET_ENABLE || WIFI_ENABLE
static on_network_event_ptr on_event;
#endif

// --------------------------------------------------------
// Function Prototypes
// --------------------------------------------------------

// Interface functions
static void report_options(bool newopt);
static void onStateChanged(sys_state_t state);
static bool display_send_command(uint8_t command);
static bool display_send_data(uint8_t* data, size_t size);
static void polling_task(void *data);
static bool display_init(void);

// Helper functions
uint8_t pgm_read_byte(const char* ptr);
font_info_t get_font_info(const char* font);
char_info_t get_char_info(const char* font, char c);
bool display_draw_pixel_safe(int16_t x, int16_t y);
uint8_t utf8_to_ascii(unsigned char c);
char* utf8_string_to_ascii(const char* str);

// Drawing functions
void display_set_color(display_color_t color);
void display_set_pixel(int16_t x, int16_t y);
void display_set_font(display_font_size_t font_size);
void display_draw_line(int16_t x0, int16_t y0, int16_t x1, int16_t y1);
void display_draw_rect(int16_t x, int16_t y, int16_t width, int16_t height);
void display_fill_rect(int16_t x, int16_t y, int16_t width, int16_t height);
void display_draw_circle(int16_t x0, int16_t y0, int16_t radius);
void display_draw_xbm(int16_t x, int16_t y, int16_t width, int16_t height, const char *xbm);
int16_t display_draw_char(int16_t x, int16_t y, char c, const char* font);
int16_t display_draw_string_with_font(int16_t x, int16_t y, const char* text, const char* font);
int16_t display_draw_string(int16_t x, int16_t y, const char* text);
uint16_t get_string_width_with_font(const char* text, uint16_t length, const char* font);
uint16_t get_string_width(const char* text);
bool display_refresh(void);
bool display_clear(void);
bool display_clear_immediate(void);

// Public initialization function
void oled_display_init(void);

// External functions
extern bool i2c_send_with_control_byte(uint_fast16_t i2c_address, uint8_t control_byte, uint8_t *data, size_t size, bool block);
extern bool i2c_probe(uint_fast16_t i2c_address);

// --------------------------------------------------------
// Network Event Handling
// --------------------------------------------------------

#if ETHERNET_ENABLE || WIFI_ENABLE

static void network_event(const char *interface, network_status_t status)
{
    if(on_event){
        on_event(interface, status);
    }
    if((status.changed.ap_started && status.flags.ap_started) || status.changed.ip_aquired) {
        network_info_t *info;

        if((info = networking.get_info(interface))) {
            strcpy(screen1.ip, info->status.ip);
        }
    }
}
#endif //ETHERNET_ENABLE || WIFI_ENABLE

// --------------------------------------------------------
// Report and State Change Handlers
// --------------------------------------------------------

static void report_options(bool newopt)
{
    if (on_report_options){
        on_report_options(newopt);
    }
    if(newopt) {
        hal.stream.write(",DISPLAY");
    } else {
        report_plugin("Oled Display", PLUGGIN_OLED_DISPLAY_VERSION);
    }
}

static void onStateChanged(sys_state_t state)
{
    if(on_state_change){
        on_state_change(state);
    }
    switch(state) {
        case STATE_IDLE:
            screen1.state = "Idle";
            break;
        case STATE_CHECK_MODE:
            screen1.state = "Check";
            break;
        case STATE_HOMING:
            screen1.state = "Home";
            break;
        case STATE_JOG:
            screen1.state = "Jog";
            break;
        case STATE_CYCLE:
            screen1.state = "Run";
            break;
        case STATE_HOLD:
            screen1.state = "Hold";
            break;
        case STATE_SAFETY_DOOR:
            screen1.state = "Door";
            break;
        case STATE_SLEEP:
            screen1.state = "Sleep";
            break;
        case STATE_ESTOP:
        case STATE_ALARM:
            screen1.state = "Alarm";
            break;
        case STATE_TOOL_CHANGE:
        default:
            break;
    };
}

// --------------------------------------------------------
// Helper Functions
// --------------------------------------------------------

uint8_t pgm_read_byte(const char* ptr) {
#ifdef ARDUINO
    return pgm_read_byte(ptr);
#else
    return *ptr;
#endif
}

static bool display_send_command(uint8_t command) {
    return i2c_send_with_control_byte(display_config.i2c_address, display_config.command_byte, &command, 1, true);
}

static bool display_send_data(uint8_t* data, size_t size) {
    return i2c_send_with_control_byte(display_config.i2c_address, display_config.data_byte, data, size, true);
}

/**
 * Extract font information from font data
 */
font_info_t get_font_info(const char* font) {
    font_info_t info = {0};
    
    if (font == NULL) return info;
    
    info.width = pgm_read_byte(&font[0]);
    info.height = pgm_read_byte(&font[1]);
    info.first_char = pgm_read_byte(&font[2]);
    info.char_count = pgm_read_byte(&font[3]);
    
    return info;
}

/**
 * Get character information from font
 */
char_info_t get_char_info(const char* font, char c) {
    char_info_t info = {0};
    info.is_defined = false;
    
    if (font == NULL) return info;
    
    font_info_t font_info = get_font_info(font);
    
    // Check if character is in range
    if (c < font_info.first_char || c >= font_info.first_char + font_info.char_count) {
        info.width = font_info.width; // Use default width for undefined chars
        return info;
    }
    
    // Calculate character index and jump table offset
    uint16_t char_index = c - font_info.first_char;
    uint16_t jump_table_offset = FONT_HEADER_SIZE + (char_index * JUMPTABLE_BYTES_PER_CHAR);
    
    // Read jump table entry
    uint8_t offset_msb = pgm_read_byte(&font[jump_table_offset + JUMPTABLE_MSB_OFFSET]);
    uint8_t offset_lsb = pgm_read_byte(&font[jump_table_offset + JUMPTABLE_LSB_OFFSET]);
    info.bytes = pgm_read_byte(&font[jump_table_offset + JUMPTABLE_SIZE_OFFSET]);
    info.width = pgm_read_byte(&font[jump_table_offset + JUMPTABLE_WIDTH_OFFSET]);
    
    // Check if character is defined
    if (offset_msb == 0xFF && offset_lsb == 0xFF) {
        return info;
    }
    
    info.is_defined = true;
    
    // Calculate bitmap offset
    uint16_t jump_table_size = font_info.char_count * JUMPTABLE_BYTES_PER_CHAR;
    info.bitmap_offset = FONT_HEADER_SIZE + jump_table_size + ((offset_msb << 8) | offset_lsb);
    
    return info;
}

/**
 * Draw a single pixel safely
 */
bool display_draw_pixel_safe(int16_t x, int16_t y) {
    if (x < 0 || x >= display_config.width || y < 0 || y >= display_config.height) {
        return false;
    }
    
    display_set_pixel(x, y);
    return true;
}

// --------------------------------------------------------
// UTF-8 Handling
// --------------------------------------------------------

/**
 * Convert a UTF-8 character to ASCII
 */
uint8_t utf8_to_ascii(unsigned char c) {
    static uint8_t last_char = 0;
    
    if (c < 128) { // Standard ASCII-set 0..0x7F handling
        last_char = 0;
        return c;
    }
    
    uint8_t last = last_char;   // Get last char
    last_char = c;
    
    switch (last) {    // Conversion depending on first UTF8-character
        case 0xC2: return (c);
        case 0xC3: return (c | 0xC0);
        case 0x82: if (c == 0xAC) return (0x80);  // Special case Euro-symbol
    }
    
    return 0; // Otherwise: return zero, if character has to be ignored
}

/**
 * Convert a UTF-8 string to ASCII
 */
char* utf8_string_to_ascii(const char* str) {
    if (str == NULL) return NULL;
    
    uint16_t length = strlen(str) + 1;
    
    // Copy the string into a char array
    char* s = (char*) malloc(length * sizeof(char));
    if (!s) {
        // Return original if we can't allocate
        return (char*) str;
    }
    
    strcpy(s, str);
    
    uint16_t k = 0;
    for (uint16_t i = 0; i < length - 1; i++) {
        char c = utf8_to_ascii(s[i]);
        if (c != 0) {
            s[k++] = c;
        }
    }
    
    s[k] = 0; // Null terminator
    
    return s;
}

// --------------------------------------------------------
// Drawing Functions
// --------------------------------------------------------

/**
 * Set the color for drawing operations
 */
void display_set_color(display_color_t color) {
    current_color = color;
}

/**
 * Draw a pixel at given position
 */
void display_set_pixel(int16_t x, int16_t y) {
    // Check if pixel is in range
    if (x < 0 || x >= display_config.width || y < 0 || y >= display_config.height) {
        return;
    }
    
    // Calculate page and pixel location
    uint8_t page = y / BITS_PER_BYTE;
    uint8_t bit = y % BITS_PER_BYTE;
    uint8_t *bufferLocation = &display_config.back_buffer[page * display_config.width + x];
    
    // Set the bit based on current color
    switch (current_color) {
        case DISPLAY_COLOR_WHITE:
            *bufferLocation |= (1 << bit);  // All pixels are white
            break;
        case DISPLAY_COLOR_BLACK:
            *bufferLocation &= ~(1 << bit); // All pixels are black
            break;
        case DISPLAY_COLOR_INVERSE:
            *bufferLocation ^= (1 << bit);  // All pixels are inverted
            break;
    }
}

/**
 * Set the current font by size
 */
void display_set_font(display_font_size_t font_size) {
    switch (font_size) {
        case DISPLAY_FONT_SMALL:
            current_font = display_small_font;
            break;
        case DISPLAY_FONT_MEDIUM:
            current_font = display_medium_font;
            break;
        case DISPLAY_FONT_BIG:
            current_font = display_big_font;
            break;
        default:
            current_font = display_small_font;  // Default to small font
            break;
    }
}

/**
 * Draw a line (Bresenham's algorithm)
 */
void display_draw_line(int16_t x0, int16_t y0, int16_t x1, int16_t y1) {
    int16_t dx = abs(x1 - x0);
    int16_t sx = x0 < x1 ? 1 : -1;
    int16_t dy = -abs(y1 - y0);
    int16_t sy = y0 < y1 ? 1 : -1;
    int16_t err = dx + dy;
    int16_t e2;

    while (true) {
        display_set_pixel(x0, y0);
        if (x0 == x1 && y0 == y1) break;
        e2 = 2 * err;
        if (e2 >= dy) {
            if (x0 == x1) break;
            err += dy;
            x0 += sx;
        }
        if (e2 <= dx) {
            if (y0 == y1) break;
            err += dx;
            y0 += sy;
        }
    }
}

/**
 * Draw a rectangle outline
 */
void display_draw_rect(int16_t x, int16_t y, int16_t width, int16_t height) {
    display_draw_line(x, y, x + width - 1, y);                  // Top line
    display_draw_line(x + width - 1, y, x + width - 1, y + height - 1); // Right line
    display_draw_line(x + width - 1, y + height - 1, x, y + height - 1); // Bottom line
    display_draw_line(x, y + height - 1, x, y);                  // Left line
}

/**
 * Fill a rectangle
 */
void display_fill_rect(int16_t x, int16_t y, int16_t width, int16_t height) {
    // Check boundaries
    if (x >= display_config.width || y >= display_config.height || width <= 0 || height <= 0)
        return;
    
    // Clipping to screen boundaries
    if (x < 0) {
        width += x;
        x = 0;
    }
    if (y < 0) {
        height += y;
        y = 0;
    }
    if (x + width > display_config.width) {
        width = display_config.width - x;
    }
    if (y + height > display_config.height) {
        height = display_config.height - y;
    }
    
    // Fill line by line
    for (int16_t j = y; j < y + height; j++) {
        for (int16_t i = x; i < x + width; i++) {
            display_set_pixel(i, j);
        }
    }
}

/**
 * Draw the outline of a circle (Bresenham's algorithm)
 */
void display_draw_circle(int16_t x0, int16_t y0, int16_t radius) {
    int16_t x = radius;
    int16_t y = 0;
    int16_t err = 0;

    while (x >= y) {
        display_set_pixel(x0 + x, y0 + y);
        display_set_pixel(x0 + y, y0 + x);
        display_set_pixel(x0 - y, y0 + x);
        display_set_pixel(x0 - x, y0 + y);
        display_set_pixel(x0 - x, y0 - y);
        display_set_pixel(x0 - y, y0 - x);
        display_set_pixel(x0 + y, y0 - x);
        display_set_pixel(x0 + x, y0 - y);

        y += 1;
        if (err <= 0) {
            err += 2 * y + 1;
        }
        if (err > 0) {
            x -= 1;
            err -= 2 * x + 1;
        }
    }
}

/**
 * Draw an XBM image
 */
void display_draw_xbm(int16_t x, int16_t y, int16_t width, int16_t height, const char *xbm) {
    int16_t byteWidth = (width + 7) / 8;
    uint8_t byte = 0;

    for (int16_t j = 0; j < height; j++) {
        for (int16_t i = 0; i < width; i++) {
            if (i & 7) {
                byte >>= 1;
            } else {
                byte = pgm_read_byte(&xbm[j * byteWidth + i / 8]);
            }
            
            if (byte & 0x01) {
                display_set_pixel(x + i, y + j);
            }
        }
    }
}

/**
 * Draw a single character with the specified font
 */
int16_t display_draw_char(int16_t x, int16_t y, char c, const char* font) {
  if (font == NULL) return 0;
  
  // Get font and character information
  font_info_t font_info = get_font_info(font);
  char_info_t char_info = get_char_info(font, c);
  
  // If character is not defined, just return its width
  if (!char_info.is_defined) {
      return char_info.width + CHAR_SPACING;
  }
  
  // Calculate how many vertical bytes this character requires
  uint8_t bytes_per_column = (font_info.height + 7) / 8;
  
  // Draw the character pixel by pixel
  for (uint8_t j = 0; j < char_info.width; j++) {
      // Skip if column is out of bounds
      if (x + j < 0 || x + j >= display_config.width) continue;
      
      // For each vertical byte in this column
      for (uint8_t k = 0; k < bytes_per_column; k++) {
          // Get byte from font data - FIXED OFFSET CALCULATION
          uint8_t column_byte = pgm_read_byte(&font[char_info.bitmap_offset + j * bytes_per_column + k]);
          if (column_byte == 0) continue; // Skip empty bytes for optimization
          
          // Calculate the vertical pixel position
          int16_t y_pos = y + k * BITS_PER_BYTE;
          
          // Draw each bit of the column byte
          for (uint8_t bit = 0; bit < BITS_PER_BYTE; bit++) {
              if (column_byte & (1 << bit)) {
                  int16_t y_pixel = y_pos + bit;
                  display_draw_pixel_safe(x + j, y_pixel);
              }
          }
      }
  }
  
  return char_info.width + CHAR_SPACING;
}

/**
 * Draw a string with the specified font
 */
int16_t display_draw_string_with_font(int16_t x, int16_t y, const char* text, const char* font) {
    if (text == NULL || font == NULL) return 0;
    
    font_info_t font_info = get_font_info(font);
    int16_t cursor_x = x;
    int16_t cursor_y = y;
    int16_t initial_x = x;
    
    // Iterate through the text
    for (uint16_t i = 0; text[i] != '\0'; i++) {
        char c = text[i];
        
        // Handle newline character
        if (c == '\n') {
            cursor_x = initial_x;
            cursor_y += font_info.height + CHAR_SPACING;
            continue;
        }
        
        // Get character information
        char_info_t char_info = get_char_info(font, c);
        
        // Check if we need to wrap
        if (cursor_x + char_info.width > display_config.width) {
            cursor_x = initial_x;
            cursor_y += font_info.height + CHAR_SPACING;
            
            // Check if we've reached bottom of screen
            if (cursor_y > display_config.height - font_info.height) {
                break;
            }
        }
        
        // Skip rendering if completely off-screen
        if (cursor_x + char_info.width < 0 || cursor_y + font_info.height < 0 || cursor_y >= display_config.height) {
            cursor_x += char_info.width + CHAR_SPACING;
            continue;
        }
        
        // Draw the character and advance cursor
        if (char_info.is_defined) {
            cursor_x += display_draw_char(cursor_x, cursor_y, c, font);
        } else {
            cursor_x += char_info.width + CHAR_SPACING;
        }
    }
    
    // Return the width of the string (distance from initial x position)
    return cursor_x - initial_x;
}

/**
 * Draw a string with the current font
 */
int16_t display_draw_string(int16_t x, int16_t y, const char* text) {
    if (text == NULL) return 0;
    
    // Use default font if none is set
    if (current_font == NULL) {
        current_font = display_small_font;
    }
    
    // Convert to ASCII if text might be UTF-8
    char* ascii_text = utf8_string_to_ascii(text);
    
    // Draw the string
    int16_t width = display_draw_string_with_font(x, y, ascii_text, current_font);
    
    // Free the allocated string if different from original
    if (ascii_text != text) {
        free(ascii_text);
    }
    
    return width;
}

/**
 * Get the width of a string with the specified font
 */
uint16_t get_string_width_with_font(const char* text, uint16_t length, const char* font) {
    if (text == NULL || length == 0 || font == NULL) return 0;
    
    uint16_t total_width = 0;
    
    // Iterate through the text up to given length
    for (uint16_t i = 0; i < length && text[i] != '\0'; i++) {
        char c = text[i];
        
        // Handle newline character
        if (c == '\n') {
            break; // Width calculation assumes single line
        }
        
        // Get character information
        char_info_t char_info = get_char_info(font, c);
        
        // Add the character width to the total
        total_width += char_info.width + CHAR_SPACING;
    }
    
    // Remove the last character spacing if there was at least one character
    if (total_width > 0) {
        total_width -= CHAR_SPACING;
    }
    
    return total_width;
}

/**
 * Get the width of a string with current font
 */
uint16_t get_string_width(const char* text) {
    if (text == NULL) return 0;
    
    // Use default font if none is set
    if (current_font == NULL) {
        current_font = display_small_font;
    }
    
    return get_string_width_with_font(text, strlen(text), current_font);
}

/**
 * Refresh the screen
 */
bool display_refresh(void) {
    bool success = true;
    
    // Compare with the front_buffer to detect differences
    bool pages_changed[8] = {false}; // Max 8 pages
    bool any_change = false;
    
    for (uint8_t page = 0; page < display_config.pages; page++) {
        // Check if the page has changed
        if (memcmp(display_config.front_buffer + (page * display_config.width), 
                  display_config.back_buffer + (page * display_config.width), 
                  display_config.width) != 0) {
            pages_changed[page] = true;
            any_change = true;
        }
    }

    // if no change, do nothing
    if (!any_change) {
        return true;
    }
    
    // Update only the pages that have changed
    for (uint8_t page = 0; page < display_config.pages; page++) {
        if (pages_changed[page]) {
            // Set the page
            success &= display_send_command(0xB0 | page);
            
            // Reset the column
            success &= display_send_command(0x00);
            success &= display_send_command(0x10);
            
            // Send the data
            success &= display_send_data(display_config.back_buffer + (page * display_config.width), display_config.width);
        }
    }
    
    // if success, copy the display_config.back_buffer to the front_buffer
    if (success) {
        memcpy(display_config.front_buffer, display_config.back_buffer, display_config.buffer_size);
    }
    
    return success;
}

/**
 * Clear the display (back buffer only)
 */
bool display_clear(void) {
    // Clear only the back_buffer
    memset(display_config.back_buffer, 0, display_config.buffer_size);
    
    // No need to update the screen immediately
    // The next call to display_refresh will take care of it
    return true;
}

/**
 * Clear the display immediately (both buffers)
 */
bool display_clear_immediate(void) {
    bool success = true;
    
    // Clear only the back_buffer
    memset(display_config.back_buffer, 0, display_config.buffer_size);
    
    // Clear the physical screen
    for (uint8_t page = 0; page < display_config.pages; page++) {
        // Set the page
        success &= display_send_command(0xB0 | page);
        
        // Reset the column
        success &= display_send_command(0x00);
        success &= display_send_command(0x10);
        
        // Send the data to clear the page
        success &= display_send_data(display_config.back_buffer + (page * display_config.width), display_config.width);
    }
    
    // Update the front buffer as well
    if (success) {
        memset(display_config.front_buffer, 0, display_config.buffer_size);
    }
    
    return success;
}

/**
 * Polling task for updating display data
 */
static void polling_task(void *data) {
    if (data) {
        display_clear();
    }
    
    // Add next polling
    task_add_delayed(polling_task, NULL, POLLING_DELAY);
    
    // Get endstop status
    if (settings.status_report.pin_state) {
        axes_signals_t lim_pin_state = limit_signals_merge(hal.limits.get_state());
        uint_fast16_t idx = 0;

        lim_pin_state.mask &= AXES_BITMASK;
        while (lim_pin_state.mask && idx < 3) {
            if (lim_pin_state.mask & 0x01) {
                screen1.end_stop[idx] = true;
            } else {
                screen1.end_stop[idx] = false;
            }
            report_info(screen1.end_stop[idx] ? "1" : "0");
            idx++;
            lim_pin_state.mask >>= 1;
        }
    }
    
    // Get positions
    system_convert_array_steps_to_mpos(screen1.pos, sys.position);
    for (uint8_t i = 0; i < N_AXIS; i++) {
        if (settings.flags.report_inches) {
            strcpy(screen1.pos_str[i], ftoa(screen1.pos[i] * INCH_PER_MM, N_DECIMAL_COORDVALUE_INCH));
        } else {
            strcpy(screen1.pos_str[i], ftoa(screen1.pos[i], N_DECIMAL_COORDVALUE_MM));
        }
        
        report_info((void *)screen1.pos_str[i]);
    }

    // Draw information on display
    display_set_font(DISPLAY_FONT_SMALL);
    
#if ETHERNET_ENABLE || WIFI_ENABLE
    // IP address
    //display_draw_string(64, 0, screen1.ip);
    display_draw_string(0, 0, "0");
    report_info((void *)screen1.ip);
#endif //ETHERNET_ENABLE || WIFI_ENABLE
    
    // Machine state
    display_set_font(DISPLAY_FONT_BIG);
    //display_draw_string(0, 15, screen1.state);
    display_draw_string(0, 15, "0");
    report_info((void *)screen1.state);
    
    // Update the display
    display_refresh();
}

/**
 * Initialize the display hardware
 */
static bool display_init(void) {
    bool success = true;
    
    // Set font size
    display_set_font(DISPLAY_FONT_SMALL);

    // Calculate number of pages (8 pixels per page) from height
    if (display_config.pages == 0) {
        display_config.pages = (display_config.height + 7) / 8; 
    }
    
    // Check if display is connected
    if ((display_connected = i2c_probe(display_config.i2c_address))) {
        // Send initialization sequence
        for (uint8_t i = 0; i < display_config.init_sequence_length; i++) {
            // Send the command
            success &= display_send_command(display_config.init_sequence[i]);
            
            // If failed, report and return
            if (!success) {
                report_warning("Failed to send display init command");
                break;
            }
        }

        if (success) {
            // Allocate memory for the display buffers
            display_config.buffer_size = display_config.width * display_config.pages;
            display_config.back_buffer = (uint8_t *)malloc(display_config.buffer_size);
            display_config.front_buffer = (uint8_t *)malloc(display_config.buffer_size);
            
            if (display_config.back_buffer == NULL || display_config.front_buffer == NULL) {
                report_warning("Failed to allocate display buffer");
                success = false;
            }
        }
        
        // Clear the display if initialization succeeded
        if (success) {
            if ((success = display_clear())) {
                report_info("Display initialized");
                
                // Draw welcome screen
                display_draw_rect(0, 0, 128, 64); 
                display_draw_xbm(4, 8, logo_width, logo_height, logo_bits); 
                display_refresh();
            } else {
                report_warning("Failed to clear display");
            }
        }
    } else {
        report_warning("Display not connected");
        success = false;
    }

    return success;
}

/**
 * Initialize the OLED display plugin
 */
void oled_display_init(void) {
    // Initialize screen data
    screen1.state = "IDLE";
#if ETHERNET_ENABLE || WIFI_ENABLE
    strcpy(screen1.ip, "0.0.0.0");
#endif
    memset(screen1.pos, 0, sizeof(screen1.pos));
    memset(screen1.end_stop, 0, sizeof(screen1.end_stop));
    memset(screen1.pos_str, 0, sizeof(screen1.pos_str));

    // Hook report options
    on_report_options = grbl.on_report_options;
    grbl.on_report_options = report_options;
    
    // Initialize hardware display
    if (display_init()) {
        // Hook state change
        on_state_change = grbl.on_state_change;
        grbl.on_state_change = onStateChanged;

#if ETHERNET_ENABLE || WIFI_ENABLE
        // Hook IP event
        on_event = networking.event;
        networking.event = network_event;
#endif

        // Start polling task
        uint8_t clearscreen = 1;
        task_add_delayed(polling_task, &clearscreen, POLLING_DELAY);
    }
}

#endif //OLED_DISPLAY_ENABLE