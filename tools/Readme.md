I'll update the README to include the PNG converter tool. Here's the updated version:

```markdown
# Font and Image Converter for OLED Displays

This repository contains tools for converting TrueType fonts and PNG images into C header file formats compatible with OLED display libraries, particularly for use with Arduino, ESP32, and other embedded systems.

## Tools Included

1. **Font Converter** (`font_converter.py`) - Converts TrueType fonts to OLED-compatible bitmap font arrays
2. **PNG Converter** (`png_converter.py`) - Converts PNG images to XBM format for OLED display
3. **Font Metrics Extractor** (`ttf_info_extractor.py`) - Advanced tool for analyzing font metrics and diagnosing rendering issues

## Features

### Font Converter
- Converts any TrueType font to a bitmap format optimized for OLED displays
- Custom character ranges support
- Compatible with common OLED display libraries like Adafruit_SSD1306 and U8g2
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
python font_converter.py path/to/font.ttf font_size --output output.h --name MyFont --range 32-255 --debug
```

Available options:
- `--output` or `-o`: Specify the output file path
- `--name`: Set the variable name in the C header (defaults to the font filename)
- `--range`: Set the character range to include (default is 32-128)
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

2. For each character, two PNG files are generated:

   - **[char]_bitmap.png**: Shows the raw bitmap of the character as positioned in the matrix.
   - **[char]_rendered.png**: Shows the final bitmap representation of the character exactly as it will be encoded.

3. The difference between these files helps identify issues:
   - If the _bitmap.png looks correct but the _rendered.png doesn't, there might be an issue in the conversion process
   - If both look wrong, the issue is likely in the initial character positioning or font loading

## Output File Format

### Font Converter Output

The generated header file contains:

1. A descriptive comment header with font information
2. A `const char` array in PROGMEM containing font metadata and bitmap data

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

### Using XBM Images

```c
#include "logo-120x48.h"

// Draw the image at position x=0, y=0
display_draw_xbm(0, 0, LOGO_WIDTH, LOGO_HEIGH, logo_bits);
```

## Font Metrics Extractor (Advanced Debugging)

The repository also includes a font metrics extraction tool that provides detailed information about font characteristics.

### Usage

```bash
python ttf_info_extractor.py path/to/font.ttf font_size
```

## Troubleshooting

- For fonts: If characters appear cut off, try increasing the font size
- For PNG conversion: If the image looks distorted, ensure the input image has appropriate dimensions for your display
- Memory issues: Reduce image size or character range to save memory
- Use debug mode in the font converter to diagnose alignment issues

## License

These tools are provided under the GNU Lesser General Public License v3.0 (LGPL-3.0).
See [LGPL-3.0](https://www.gnu.org/licenses/lgpl-3.0.en.html) for more details.

Copyright (C) 2025 Luc LEBOSSE
```

This updated README now properly explains both tools, with clear usage instructions and examples for both the Font Converter and the new PNG Converter.
