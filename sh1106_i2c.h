/*

  sh1106_i2c.h configuration for sh1106 I2C oled screen.

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
#ifndef SH1106_I2C_H
#define SH1106_I2C_H
#include "oled_display.h"
#include "./fonts/oled_9.h"
#include "./fonts/oled_11.h"
#include "./images/logo-120x48.h"

// Define the initialization sequence array
static const uint8_t sh1106_init_sequence[] = { 
    0xAE, // Display off
    0xD5, // Set display clock divide ratio/oscillator frequency
    0x80, // Set divide ratio
    0xA8, // Set multiplex ratio
    0x3F, // 1/64 duty
    0xD3, // Set display offset
    0x00, // No offset
    0x40, // Set start line
    0x8D, // Charge pump
    0x14, // Enable charge pump
    0x20, // Set memory mode
    0x00, // Horizontal addressing mode
    0xA1, // Segment remap
    0xC8, // Com scan direction
    0xDA, // Set comp pins hardware configuration
    0x12, // Set comp pins hardware configuration
    0x81, // Set contrast
    0xCF, // Set contrast for 0xCF
    0xD9, // Set pre-charge period
    0xF1, // Set pre-charge period
    0xDB, // Set VCOMH deselect level
    0x40, // Set VCOMH deselect level
    0xA4, // Entire display on
    0xA6, // Normal display
    0x2E, // Deactivate scroll
    0xAF  // Display on
  };

// Set default display configuration
display_config_t display_config = {
  .i2c_address = 0x3C,
  .width = 128,
  .height = 64,
  .pages = 8,
  .back_buffer = NULL,
  .front_buffer = NULL,
  .buffer_size = 0,
  .command_head = 0x80,
  .data_head = 0x40,
  .init_sequence_length = sizeof(sh1106_init_sequence),
  .init_sequence = (uint8_t *)sh1106_init_sequence,
  // Default font pointers
  .display_small_font = oled_9,
  .display_medium_font = oled_9,
  .display_big_font = oled_11,
  .logo_width = LOGO_WIDTH,
  .logo_height= LOGO_HEIGH, 
  .logo_rle = false,
  .logo_bits = logo_bits
};

#define SHIFT_COMMAND_1 (2 & 0x0F)
#define SHIFT_COMMAND_2 ((2 >> 4) & 0x0F)


#endif //SH1106_I2C_H
