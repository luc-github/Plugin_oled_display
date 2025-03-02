/*

  oled_display.h - plugin for for handling olde display

  Part of grblHAL

  Copyright (c) 2025 Luc LEBOSSE 

  Grbl is free software: you can redistribute it and/or modify
  it under the terms of the GNU General Public License as published by
  the Free Software Foundation, either version 3 of the License, or
  (at your option) any later version.

  Grbl is distributed in the hope that it will be useful,
  but WITHOUT ANY WARRANTY; without even the implied warranty of
  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
  GNU General Public License for more details.

  You should have received a copy of the GNU General Public License
  along with Grbl.  If not, see <http://www.gnu.org/licenses/>.

*/

#pragma once

#include <stdint.h>   // for  int16_t, uint8_t and others types int
#include <stdbool.h>  // for bool type
#include <stddef.h>  // NULL

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

// Define font sizes
typedef enum {
  DISPLAY_FONT_SMALL,
  DISPLAY_FONT_MEDIUM,
  DISPLAY_FONT_BIG
} display_font_size_t;

// Define display configuration structure
typedef struct  {
  uint8_t i2c_address;
  uint8_t width;
  uint8_t height;
  uint8_t pages;
  uint8_t * back_buffer; // Preparation Buffer
  uint8_t * front_buffer; // Current Buffer
  uint16_t buffer_size;
  uint8_t command_byte;
  uint8_t data_byte;
  uint8_t init_sequence_length;
  uint8_t * init_sequence; 
  const char* display_small_font;
  const char* display_medium_font;
  const char* display_big_font;
  uint16_t logo_width;
  uint16_t logo_height; 
  bool logo_rle;
  const char * logo_bits;
} display_config_t;

// Global variables
extern display_config_t display_config;

// --------------------------------------------------------
// Function Prototypes to export
// --------------------------------------------------------
bool display_init(void);
void display_set_color(display_color_t color);
void display_set_pixel(int16_t x, int16_t y);
void display_set_font(display_font_size_t font_size);
void display_draw_line(int16_t x0, int16_t y0, int16_t x1, int16_t y1);
void display_draw_rect(int16_t x, int16_t y, int16_t width, int16_t height);
void display_fill_rect(int16_t x, int16_t y, int16_t width, int16_t height);
void display_draw_circle(int16_t x0, int16_t y0, int16_t radius);
void display_fill_circle(int16_t x0, int16_t y0, int16_t radius);
void display_draw_xbm(int16_t x, int16_t y, int16_t width, int16_t height, const char *xbm);
int16_t display_draw_char(int16_t x, int16_t y, char c, const char* font);
int16_t display_draw_string_with_font(int16_t x, int16_t y, const char* text, const char* font);
int16_t display_draw_string(int16_t x, int16_t y, const char* text);
uint16_t get_string_width_with_font(const char* text, uint16_t length, const char* font);
uint16_t get_string_width(const char* text);
bool display_refresh(void);
bool display_clear(void);
bool display_clear_immediate(void);

