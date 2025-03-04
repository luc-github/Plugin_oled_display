# Font and Image Converter for OLED Displays

This repository contains tools for converting TrueType fonts and PNG images into C header file formats compatible with OLED display libraries, particularly for use with Arduino, ESP32, and other embedded systems.

## Tools Included

1. **Font Converter** (`font_converter.py`) - Converts TrueType fonts to OLED-compatible bitmap font arrays
2. **PNG Converter** (`png_converter.py`) - Converts PNG images to XBM format for OLED display
3. **Font Metrics Extractor** (`ttf_info_extractor.py`) - Advanced tool for analyzing font metrics and diagnosing rendering issues

## Features

### Font Converter
- Converts any TrueType font to a bitmap format optimized for OLED displays
- Custom character sets support (specific characters) and character ranges
- Compatible with common OLED display libraries like Adafruit_SSD1306 and U8g2
- Automatic character spacing calculation based on font size
- Generates compact byte arrays to minimize memory usage
- Debug mode to visualize character rendering
- Proper baseline alignment for all character types

### PNG Converter
- Converts PNG images to XBM format (X BitMap)
- Generates C header files compatible with OLED display libraries
- Automatic 1-bit (black and white) conversion
- Properly formatted output with consistent line breaks
- Includes appropriate license headers and include guards

## Installation

### Basic Requirements

- Python 3.6 or newer
- Pillow library (PIL fork)

```bash
pip install Pillow
```

For Font Converter, additional libraries:
```bash
pip install freetype-py matplotlib numpy
```

### Make the scripts executable (Unix/Linux/macOS):
```bash
chmod +x font_converter.py
chmod +x png_converter.py
```

## Usage

### Font Converter

#### Basic Usage

```bash
python font_converter.py path/to/font.ttf font_size
```

For example:
```bash
python font_converter.py Roboto-Regular.ttf 14
```

This will generate a `Roboto-Regular_14.h` file in the current directory.

#### Advanced Options

```bash
python font_converter.py path/to/font.ttf font_size --output output.h --name MyFont --range 32-255 --debug --spacing 1
```

Available options:
- `--output` or `-o`: Specify the output file path
- `--name`: Set the variable name in the C header (defaults to the font filename)
- `--range`: Set the character range to include (default is 32-128)
- `--scope`: Define a custom set of specific characters (e.g., "ABC123")
- `--spacing`: Override the default character spacing (in pixels)
- `--debug`: Generate debug images showing how each character is rendered

### PNG Converter

#### Basic Usage

```bash
python png_converter.py input.png output.h
```

For example:
```bash
python png_converter.py logo.png logo-120x48.h
```

This will generate a `logo-120x48.h` file in the current directory with the image data formatted as an XBM file.

#### Advanced Options

```bash
python png_converter.py input.png output.h variable_name
```

Where:
- `input.png`: The PNG image to convert
- `output.h`: The output header file
- `variable_name` (optional): The name for the variable in the header (defaults to the input filename)

## Debug Mode (Font Converter)

When you run the font converter with the `--debug` flag, it will:

1. Create a directory named `debug_[fontname]_[size]/` containing:
   - Individual bitmap images for each character
   - A summary image showing all characters in the specified range
   - A text file with character width information

2. For each character, two PNG files are generated:

   - **[char]_bitmap.png**: Shows the raw bitmap of the character as positioned in the matrix.
   - **[char]_rendered.png**: Shows the final bitmap representation of the character exactly as it will be encoded.

3. The difference between these files helps identify issues:
   - If the _bitmap.png looks correct but the _rendered.png doesn't, there might be an issue in the conversion process
   - If both look wrong, the issue is likely in the initial character positioning or font loading

## Detailed Encoding and Decoding Process

### Font Conversion: Encoding Process

The font converter transforms TrueType fonts to a specialized bitmap format using the following steps:

1. **Font Loading and Metrics Analysis**:
   - The script loads the TTF font using FreeType and calculates essential metrics
   - It determines the maximum width and height needed across all characters
   - The bytes per column value is calculated as `(max_height + 7) // 8`
   - A recommended character spacing is calculated based on font size

2. **Character Processing**:
   - For each character in the specified range or custom set:
     - Render the character using FreeType
     - Position the character bitmap correctly using baseline calculations
     - Convert to a fixed-height matrix (all characters use the same height)
     - Record the character's actual width (important for proper spacing)

3. **Bitmap Encoding**:
   - Each character is encoded in a column-wise format
   - For each column of pixels:
     - Pack groups of 8 vertical pixels into individual bytes
     - The least significant bit represents the top-most pixel
     - Each column consists of `bytes_per_column` bytes
   - This format optimizes for OLED displays that often access data in vertical strips

4. **Character Table Creation** (for custom character sets):
   - A table is created listing the code of each character included in the font
   - This allows for efficient lookup of arbitrary character sets

5. **Jump Table Creation**:
   - A jump table is created with 4 bytes per character:
     - Bytes 0-1: MSB and LSB of the offset to the character's bitmap data
     - Byte 2: Size of the character's bitmap in bytes
     - Byte 3: Width of the character in pixels

6. **Header File Generation**:
   - Write font metadata:
     - Byte 0: Maximum character width
     - Byte 1: Maximum character height
     - Byte 2-3: Character count (16-bit value)
     - Byte 4: Recommended character spacing
   - Write the character table (list of character codes)
   - Write the jump table
   - Write the bitmap data for all characters
   - Add detailed documentation for using the font

### Font Conversion: Decoding Process (for Client Programs)

To render text using the converted font, client programs should follow these steps:

1. **Initialize**:
   - Read the font metadata (first 5 bytes):
     - max_width = data[0]
     - height = data[1]
     - char_count = (data[2] << 8) | data[3]  // 16-bit character count
     - spacing = data[4]  // Recommended character spacing
   - Calculate bytes_per_column = (height + 7) // 8

2. **Character Lookup**:
   - For each character to render:
     - Search for the character code in the character table (starting at byte 5)
     - If found at position i, calculate jump table entry position:
       - jump_entry = (5 + char_count) + (i * 4)
     - Extract from the entry:
       - msb = data[jump_entry]
       - lsb = data[jump_entry + 1]
       - size = data[jump_entry + 2]
       - width = data[jump_entry + 3]
     - Calculate data offset: `data_offset = (msb << 8) | lsb`

3. **Character Rendering**:
   - Calculate number of columns: `columns = size / bytes_per_column`
   - For each column (x from 0 to width-1):
     - For each byte in column (y_byte from 0 to bytes_per_column-1):
       - Read the byte at: `data_offset + (x * bytes_per_column) + y_byte`
       - For each bit in byte (bit from 0 to 7):
         - If the bit is set (1), draw a pixel at position:
           - screen_x = cursor_x + x
           - screen_y = cursor_y + (y_byte * 8) + bit
   - Advance cursor by: character's width + spacing

### Example: Rendering a Character from a Custom Character Set

1. Search for the character code in the character table
2. If found at position i, find jump table entry at: (5 + char_count) + (i * 4)
3. Extract:
   - msb, lsb = data[entry_pos], data[entry_pos + 1]
   - size = data[entry_pos + 2]
   - width = data[entry_pos + 3]
4. Calculate data offset: (msb << 8) | lsb
5. Render the columns of the character using the bytes at the calculated offset
6. Advance cursor position by: width + spacing

### PNG Conversion: Encoding Process

The PNG converter transforms PNG images to XBM format using these steps:

1. **Image Loading and Preparation**:
   - Open the PNG file
   - Convert to 1-bit (black and white) format
   - Get image dimensions (width, height)

2. **XBM Format Conversion**:
   - Calculate bytes_per_row = (width + 7) // 8
   - For each pixel row:
     - For each byte in the row:
       - Pack 8 horizontal pixels into one byte
       - XBM format uses 1 for black (on) pixels, 0 for white (off)
       - Pixels are stored with the least significant bit first

3. **Header File Generation**:
   - Write appropriate license header
   - Define WIDTH and HEIGHT constants
   - Write the byte array in proper C format
   - Format the output with consistent line breaks (every 12 elements)

### PNG Conversion: Decoding Process (for Client Programs)

To display the XBM image, client programs should:

1. **Initialize**:
   - Read the image dimensions from the header:
     - width = LOGO_WIDTH
     - height = LOGO_HEIGHT

2. **Image Rendering**:
   - For each row (y from 0 to height-1):
     - Calculate row offset: `row_offset = y * ((width + 7) / 8)`
     - For each pixel column (x from 0 to width-1):
       - Calculate byte position: `byte_pos = row_offset + (x / 8)`
       - Calculate bit position: `bit_pos = x % 8`
       - Check if pixel is set: `logo_bits[byte_pos] & (1 << bit_pos)`
       - If the bit is set, draw a pixel at (x, y)

## Output File Format

### Font Converter Output

The generated header file contains:

1. A descriptive comment header with font information and usage instructions
2. A `const char` array in PROGMEM containing:
   - 5 bytes of font metadata (width, height, char count MSB, char count LSB, spacing)
   - Character table (list of character codes)
   - 4 bytes per character in the jump table
   - The bitmap data for all characters

Structure:
```
[max_width][height][char_count_MSB][char_count_LSB][spacing][char_table...][jump_table...][bitmap_data...]
```

### PNG Converter Output

The generated XBM file contains:

1. A license header
2. Width and height definitions
3. A `const char` array containing the bitmap data
4. Proper header guards

Example:
```c
#ifndef _LOGO_120X48_H_
#define _LOGO_120X48_H_
#define LOGO_WIDTH 120
#define LOGO_HEIGH 48
static const char logo_bits[] = {
  0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
  0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
  /* additional data lines */
};
#endif // _LOGO_120X48_H_
```

## Integration with OLED Libraries

### Using Fonts

```c
#include "Roboto_14.h"

// Set the font
display.setFont(Roboto_14);
```

### Example: Rendering Text with the Custom Font

```c
void renderText(const char* text, int x, int y) {
  int cursor_x = x;
  int cursor_y = y;
  
  // Get font metadata
  uint8_t max_width = pgm_read_byte(&Roboto_14[0]);
  uint8_t height = pgm_read_byte(&Roboto_14[1]);
  uint16_t char_count = (pgm_read_byte(&Roboto_14[2]) << 8) | pgm_read_byte(&Roboto_14[3]);
  uint8_t spacing = pgm_read_byte(&Roboto_14[4]);
  
  // Calculate bytes per column
  uint8_t bytes_per_col = (height + 7) / 8;
  
  // Character table starts at byte 5
  uint16_t char_table_start = 5;
  
  // Render each character
  while (*text) {
    char c = *text++;
    
    // Find character in character table
    int16_t char_index = -1;
    for (uint16_t i = 0; i < char_count; i++) {
      if (pgm_read_byte(&Roboto_14[char_table_start + i]) == c) {
        char_index = i;
        break;
      }
    }
    
    // Skip if character is not found
    if (char_index == -1) continue;
    
    // Calculate jump table position
    uint16_t jump_table_start = char_table_start + char_count;
    uint16_t jump_pos = jump_table_start + (char_index * 4);
    
    // Get character data
    uint8_t msb = pgm_read_byte(&Roboto_14[jump_pos]);
    uint8_t lsb = pgm_read_byte(&Roboto_14[jump_pos + 1]);
    uint8_t size = pgm_read_byte(&Roboto_14[jump_pos + 2]);
    uint8_t width = pgm_read_byte(&Roboto_14[jump_pos + 3]);
    
    // Calculate data offset
    uint16_t data_offset = (msb << 8) | lsb;
    uint16_t bitmap_start = jump_table_start + (char_count * 4);
    uint16_t bitmap_offset = bitmap_start + data_offset;
    
    // Render character
    for (uint8_t x = 0; x < width; x++) {
      for (uint8_t byte_idx = 0; byte_idx < bytes_per_col; byte_idx++) {
        uint8_t byte_val = pgm_read_byte(&Roboto_14[bitmap_offset + (x * bytes_per_col) + byte_idx]);
        for (uint8_t bit_idx = 0; bit_idx < 8; bit_idx++) {
          if (byte_idx * 8 + bit_idx < height) {
            if (byte_val & (1 << bit_idx)) {
              // Draw pixel at this position
              display.drawPixel(cursor_x + x, cursor_y + byte_idx * 8 + bit_idx, 1);
            }
          }
        }
      }
    }
    
    // Move cursor to next character position
    cursor_x += width + spacing;
  }
}
```

### Using XBM Images

```c
#include "logo-120x48.h"

// Draw the image at position x=0, y=0
display_draw_xbm(0, 0, LOGO_WIDTH, LOGO_HEIGH, logo_bits);
```

### Example: Drawing an XBM Image

```c
void drawXBM(int16_t x, int16_t y, const uint8_t *bitmap, uint16_t w, uint16_t h) {
  int16_t byteWidth = (w + 7) / 8;
  
  for (int16_t j = 0; j < h; j++) {
    for (int16_t i = 0; i < w; i++) {
      if (pgm_read_byte(&bitmap[j * byteWidth + i / 8]) & (1 << (i % 8))) {
        display.drawPixel(x + i, y + j, 1);
      }
    }
  }
}

// Usage:
drawXBM(0, 0, logo_bits, LOGO_WIDTH, LOGO_HEIGH);
```

## Font Metrics Extractor (Advanced Debugging)

The repository also includes a font metrics extraction tool that provides detailed information about font characteristics.

### Usage

```bash
python ttf_info_extractor.py path/to/font.ttf font_size
```

## Troubleshooting

- For fonts: If characters appear cut off, try increasing the font size
- For fonts: If characters appear too close or too far apart, use the `--spacing` parameter
- For PNG conversion: If the image looks distorted, ensure the input image has appropriate dimensions for your display
- Memory issues: Reduce image size or character range to save memory
- Use debug mode in the font converter to diagnose alignment issues
- Check character widths in the debug output if spacing issues occur

### Font Template Generator

In addition to converting TrueType fonts, this repository includes a template-based font creation tool that allows you to design your own bitmap fonts using simple text files.

#### How It Works

The Font Template Generator operates in two main modes:

1. **Template Generation** - Creates template files for each ASCII character
2. **Font Generation** - Converts the edited templates into a header file

This approach is perfect for:
- Custom designing pixel-perfect font characters
- Modifying existing fonts character by character
- Creating specialized symbols or characters
- Font design without any TrueType font editing software

#### Template Generation

```bash
python font_template_generator.py [font_name] [font_size] --generatetemplate
```

For example:
```bash
python font_template_generator.py oled 10 --generatetemplate
```

This command creates a directory named `oled_10/` containing template files for each printable ASCII character. Each file is named after the ASCII code (for example, `65.txt` for 'A') and contains:

- The character itself on the first line
- A matrix of 'O' characters representing pixels
- The matrix height equals the specified font size
- The matrix width is approximately 60% of the height

Example template file for the letter 'Y' (ASCII 89):
```
Y
OOOOOOO
OOOOOOO
OOOOOOO
OOOOOOO
OOOOOOO
OOOOOOO
OOOOOOO
OOOOOOO
OOOOOOO
OOOOOOO
```

#### Editing Templates

To design your characters, edit the template files by replacing 'O' characters with 'X' to represent pixels that should be lit:

```
Y
XOOOOOX
OXOOOXO
OOXOXOO
OOXOXOO
OOOXOOO
OOOXOOO
OOOXOOO
OOOXOOO
OOOXOOO
OOOXOOO
```

In this representation:
- 'O' represents an unlit pixel (off)
- 'X' represents a lit pixel (on)
- The width of each character can vary as needed
- The height remains constant (equal to the font size)

#### Generating Font Header

Once you've edited your templates, generate the font header file:

```bash
python font_template_generator.py [font_name] [font_size] --generatefont [--debug]
```

For example:
```bash
python font_template_generator.py oled 10 --generatefont --debug
```

This command:
1. Reads all template files from the `[font_name]_[font_size]` directory
2. Converts them to the bitmap format for OLED displays
3. Creates a C header file compatible with OLED libraries
4. Optionally generates debug images if `--debug` is specified

The resulting header file follows the same format as those generated by the Font Converter, with:
- Font metadata
- Character table
- Jump table
- Bitmap data

#### Advanced Options

```bash
python font_template_generator.py [font_name] [font_size] --generatefont --debug --output custom_font.h
```

Available options:
- `--output` or `-o`: Specify the output header file path
- `--debug`: Generate debug images showing how each character is rendered

#### Debug Information

When using the `--debug` option, the generator creates:
1. A `debug_[font_name]_[font_size]/` directory containing:
   - Individual bitmap images for each character
   - A summary image showing all characters
   - Width information for each character

This helps verify that your character designs look as expected when rendered.

#### Example Workflow

1. **Generate templates**:
   ```bash
   python font_template_generator.py custom 12 --generatetemplate
   ```

2. **Edit the templates** in the `custom_12/` directory, customizing each character

3. **Generate the font header**:
   ```bash
   python font_template_generator.py custom 12 --generatefont --debug
   ```

4. **Use in your project**:
   ```c
   #include "custom_12.h"
   
   // Set the font
   display.setFont(custom_12);
   ```

#### Tips for Template Editing

- Create a common style across all characters for a consistent look
- Keep character widths reasonable for better spacing
- Use monospace alignment when editing the templates
- Test frequently with the debug option to see how your characters render
- Start with important characters first (A-Z, 0-9) before working on symbols
- Consider creating specialized versions for small font sizes where detail is limited

The Template Generator provides a simple yet powerful way to create custom fonts pixel by pixel, giving you complete control over your display's typeface.

## License

These tools are provided under the GNU Lesser General Public License v3.0 (LGPL-3.0).
See [LGPL-3.0](https://www.gnu.org/licenses/lgpl-3.0.en.html) for more details.

Copyright (C) 2025 Luc LEBOSSE
