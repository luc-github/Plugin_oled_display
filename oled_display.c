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

#include "driver.h"
#include "grbl/hal.h"
#include "grbl/task.h"
#include "grbl/system.h"
#include "grbl/plugins.h"
#include "grbl/report.h"

#if DISPLAY_ENABLE == 33
#include "oled_display.h"

#ifndef DISPLAY_DRIVER
#define DISPLAY_DRIVER DISPLAY_DRIVER_SH1106
#endif //DISPLAY_DRIVER 

// Include configuration for display type
#if DISPLAY_DRIVER == DISPLAY_DRIVER_SSD1306
#include "ssd1306_i2c.h"
#endif //DISPLAY_DRIVER == DISPLAY_DRIVER_SSD1306

#if DISPLAY_DRIVER == DISPLAY_DRIVER_SH1106
#include "sh1106_i2c.h"
#endif //DISPLAY_DRIVER == DISPLAY_DRIVER_SH1106

// --------------------------------------------------------
// Types and Constants
// --------------------------------------------------------

/**
 * Font information structure
 */
typedef struct {
    uint8_t width;          // Maximum character width
    uint8_t height;         // Character height
    uint16_t char_count;    // Number of characters in font (16-bit value)
    uint8_t spacing;        // Recommended character spacing
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
static const uint8_t BITS_PER_BYTE = 8;            // Number of bits in a byte
static const uint8_t FONT_HEADER_SIZE = 5;         // Size of font header in bytes
static const uint8_t JUMPTABLE_BYTES_PER_CHAR = 4; // Size of jump table entry per character

// Jump table entry structure
static const uint8_t JUMPTABLE_MSB_OFFSET = 0;     // Offset for MSB in jump table
static const uint8_t JUMPTABLE_LSB_OFFSET = 1;     // Offset for LSB in jump table
static const uint8_t JUMPTABLE_SIZE_OFFSET = 2;    // Offset for size in jump table
static const uint8_t JUMPTABLE_WIDTH_OFFSET = 3;   // Offset for width in jump table

static bool disp_connected = false;
static i2c_transfer_t i2c_data = {
   .cmd_bytes = 1,
   .no_block = On
};

// Global variables
static const char* current_font = NULL;
static display_color_t current_fg_color = DISPLAY_COLOR_WHITE;
static display_color_t current_bg_color = DISPLAY_COLOR_BLACK;


// Macro
#ifndef ARDUINO
#define pgm_read_byte(ptr) (*(ptr))
#endif

// --------------------------------------------------------
// Function Prototypes
// --------------------------------------------------------
// Interface functions

static bool display_send_command(uint8_t command);
static bool display_send_data(uint8_t * command, size_t size);

// Helper functions
font_info_t get_font_info(const char* font);
char_info_t get_char_info(const char* font, char c);
bool display_draw_pixel_safe(int16_t x, int16_t y);
uint8_t utf8_to_ascii(unsigned char c);
char* utf8_string_to_ascii(const char* str);



// --------------------------------------------------------
// Helper Functions
// --------------------------------------------------------

static bool display_send_command(uint8_t command) {
    // Prepare the data transfer structure
    // with a command head of display_config.command_head
    i2c_data.count = 1;
    i2c_data.data = &command;
    i2c_data.cmd = display_config.command_head;
    return i2c_transfer(&i2c_data, false);
}

static bool display_send_data(  uint8_t* data, size_t size) {
    // Prepare the data transfer structure
    // with a data head of display_config.data_head 
    i2c_data.count = size;
    i2c_data.data = data;
    i2c_data.cmd = display_config.data_head;
    return i2c_transfer(&i2c_data, false);
}

/**
 * Extract font information from font data
 */
font_info_t get_font_info(const char* font) {
    font_info_t info = {0};
    
    if (font == NULL) return info;
    
    info.width = pgm_read_byte(&font[0]);
    info.height = pgm_read_byte(&font[1]);
    info.char_count = (pgm_read_byte(&font[2]) << 8) | pgm_read_byte(&font[3]);
    info.spacing = pgm_read_byte(&font[4]);
    
    return info;
}

/**
 * Find a character in the character table
 * Returns index of character if found, -1 otherwise
 */
int16_t find_char_in_table(const char* font, char c) {
    if (font == NULL) return -1;
    
    font_info_t font_info = get_font_info(font);
    uint8_t char_code = (uint8_t)c;
    
    // Character table starts after the header
    uint16_t char_table_offset = FONT_HEADER_SIZE;
    
    // Search for the character in the table
    for (uint16_t i = 0; i < font_info.char_count; i++) {
        uint8_t table_char = pgm_read_byte(&font[char_table_offset + i]);
        if (table_char == char_code) {
            return i; // Found the character
        }
    }
    
    return -1; // Character not found
}

/**
 * Get character information from font
 */
char_info_t get_char_info(const char* font, char c) {
    char_info_t info = {0};
    info.is_defined = false;
    
    if (font == NULL) return info;
    
    font_info_t font_info = get_font_info(font);
    
    // Find the character in the character table
    int16_t char_index = find_char_in_table(font, c);
    
    // Check if character was found
    if (char_index < 0) {
        info.width = font_info.width / 2; // Use default width for undefined chars
        return info;
    }
    
    // Calculate jump table entry position
    uint16_t jump_table_offset = FONT_HEADER_SIZE + font_info.char_count + (char_index * JUMPTABLE_BYTES_PER_CHAR);
    
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
    uint16_t offset = (offset_msb << 8) | offset_lsb;
    info.bitmap_offset = FONT_HEADER_SIZE + font_info.char_count + (font_info.char_count * JUMPTABLE_BYTES_PER_CHAR) + offset;
    
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
    current_fg_color = color;
    if (color == DISPLAY_COLOR_WHITE){
        current_bg_color = DISPLAY_COLOR_BLACK;
    } else {
        current_bg_color = DISPLAY_COLOR_WHITE;
    }
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
    switch (current_fg_color) {
        case DISPLAY_COLOR_WHITE:
            *bufferLocation |= (1 << bit);  // All pixels are white
            break;
        case DISPLAY_COLOR_BLACK:
            *bufferLocation &= ~(1 << bit); // All pixels are black
            break;
    }
}

/**
 * Set the current font by size
 */
void display_set_font(display_font_size_t font_size) {
    switch (font_size) {
        case DISPLAY_FONT_SMALL:
            current_font = display_config.display_small_font;
            break;
        case DISPLAY_FONT_MEDIUM:
            current_font = display_config.display_medium_font;
            break;
        case DISPLAY_FONT_BIG:
            current_font = display_config.display_big_font;
            break;
        default:
            current_font = display_config.display_small_font;  // Default to small font
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
 * Fill a circle (using Bresenham's algorithm)
 */
void display_fill_circle(int16_t x0, int16_t y0, int16_t radius) {
    int16_t x = radius;
    int16_t y = 0;
    int16_t err = 0;
    
    while (x >= y) {
        // Draw horizontal lines from the center to each octant point
        display_draw_line(x0 - x, y0 + y, x0 + x, y0 + y);
        display_draw_line(x0 - y, y0 + x, x0 + y, y0 + x);
        display_draw_line(x0 - x, y0 - y, x0 + x, y0 - y);
        display_draw_line(x0 - y, y0 - x, x0 + y, y0 - x);
        
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

uint16_t get_font_height(){
    return get_font_info(current_font).height;
}

/**
 * Draw a single character with the specified font
 */
int16_t display_draw_char(int16_t x, int16_t y, char c, const char* font) {
    if (font == NULL) {
        return 0;
    }
    
    // Get font and character information
    font_info_t font_info = get_font_info(font);
    char_info_t char_info = get_char_info(font, c);

    // If character is not defined OR has no bitmap data, just return its width
    if (!char_info.is_defined || char_info.bytes == 0) {
        return char_info.width +  font_info.spacing;
    }
    
    // Calculate bytes per column and number of columns
    uint8_t bytes_per_column = (font_info.height + 7) / 8;
    uint8_t data_columns = char_info.bytes / bytes_per_column;
    
    // Draw the character pixel by pixel
    for (uint8_t j = 0; j < data_columns; j++) {
        // For each vertical byte in this column
        for (uint8_t k = 0; k < bytes_per_column; k++) {
            // Get byte from font data
            uint16_t byte_offset = char_info.bitmap_offset + (j * bytes_per_column) + k;
            uint8_t column_byte = pgm_read_byte(&font[byte_offset]);
            
            if (column_byte == 0) continue; // Skip empty bytes for optimization
            
            // Draw each bit of the column byte
            for (uint8_t bit = 0; bit < BITS_PER_BYTE; bit++) {
                // Make sure we're not drawing beyond the font height
                if ((k * BITS_PER_BYTE + bit) >= font_info.height) 
                    continue;
                    
                // Check if this bit is set in the column byte
                if (column_byte & (1 << bit)) {
                    // Calculate y position
                    int16_t y_pixel = y + (k * BITS_PER_BYTE) + bit;
                    
                    // Draw pixel if within display bounds
                    if (y_pixel >= 0 && y_pixel < display_config.height) {
                        display_set_pixel(x + j, y_pixel);
                    }
                }
            }
        }
    }
    
    // Return the width plus spacing
    return char_info.width + font_info.spacing;
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
            cursor_y += font_info.height +  font_info.spacing;
            continue;
        }
        
        // Get character information
        char_info_t char_info = get_char_info(font, c);
        
        // Check if we need to wrap
        if (cursor_x + char_info.width > display_config.width) {
            cursor_x = initial_x;
            cursor_y += font_info.height + font_info.spacing;
            
            // Check if we've reached bottom of screen
            if (cursor_y > display_config.height - font_info.height) {
                break;
            }
        }
        
        // Skip rendering if completely off-screen
        if (cursor_x + char_info.width < 0 || cursor_y + font_info.height < 0 || cursor_y >= display_config.height) {
            cursor_x += char_info.width + font_info.spacing;
            continue;
        }
        
        // Draw the character and advance cursor
        int16_t char_width = display_draw_char(cursor_x, cursor_y, c, font);
        cursor_x += char_width;
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
        current_font = display_config.display_small_font;
    }

    // Convert to ASCII if text might be UTF-8
    char* ascii_text = utf8_string_to_ascii(text);
    
    // Calculate string dimensions
    font_info_t font_info = get_font_info(current_font);
    uint16_t text_width = get_string_width_with_font(ascii_text, strlen(ascii_text), current_font);
    
    // Clear the area where the string will be drawn
    
    display_color_t original_color = current_fg_color;
    display_set_color(current_bg_color);
    display_fill_rect(x-1, y-1, text_width+2, font_info.height+2);
    display_set_color(original_color);
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
    font_info_t font_info = get_font_info(font);
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
        total_width += char_info.width +  font_info.spacing;
    }
    
    // Remove the last character spacing if there was at least one character
    if (total_width > 0 && length > 0) {
        total_width -=  font_info.spacing;
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
        current_font = display_config.display_small_font;
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
            success &= display_send_command(0x00 | SHIFT_COMMAND_1);        // Set lower column start address
            success &= display_send_command(0x10 | SHIFT_COMMAND_2);
            
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
        success &= display_send_command(0x00 | SHIFT_COMMAND_1);        // Set lower column start address
        success &= display_send_command(0x10 | SHIFT_COMMAND_2);
        
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
 * Initialize the display hardware
 */
bool display_oled_init(void) {
    bool success = true;

    // Set the I2C address
    i2c_data.address = display_config.i2c_address;
    
    // Set font size
    display_set_font(DISPLAY_FONT_SMALL);

    // Calculate number of pages (8 pixels per page) from height
    if (display_config.pages == 0) {
        display_config.pages = (display_config.height + 7) / 8; 
    }
    i2c_cap_t cap = i2c_start();
    // Check if display is connected
    if (cap.started && i2c_probe(display_config.i2c_address)) {
        disp_connected = true;
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
                
                // Draw welcome screen
                display_draw_rect(0, 0, display_config.width, display_config.height); 
                display_draw_xbm((display_config.width - display_config.logo_width)/2, (display_config.height - display_config.logo_height)/2, display_config.logo_width, display_config.logo_height, display_config.logo_bits); 
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


// give status of display
bool display_connected(){
    return disp_connected;
}

const char * display_name(void){
    return display_config.name;
}

#endif //DISPLAY_ENABLE == 33
