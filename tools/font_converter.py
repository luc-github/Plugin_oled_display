#!/usr/bin/env python3
"""
Font Converter for OLED Displays
Converts TrueType fonts to a C header file format compatible with OLED display libraries.

Copyright (C) 2025 Luc LEBOSSE

This library is free software; you can redistribute it and/or
modify it under the terms of the GNU Lesser General Public
License as published by the Free Software Foundation; either
version 3 of the License, or (at your option) any later version.

This library is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
Lesser General Public License for more details.

You should have received a copy of the GNU Lesser General Public
License along with this library; if not, write to the Free Software
Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301  USA
"""

import argparse
from PIL import Image, ImageDraw, ImageFont
import os
import math
import datetime

def generate_font_data(font_path, font_size, char_range=(32, 128), variable_name=None):
    """
    Generate font data from a TrueType font file.
    
    Args:
        font_path: Path to the TrueType font file
        font_size: Font size in pixels
        char_range: Range of characters to include (start, end)
        variable_name: Name of the variable in the output file
        
    Returns:
        A tuple containing the font data and font info
    """
    if variable_name is None:
        # Generate variable name from font filename without extension
        variable_name = os.path.splitext(os.path.basename(font_path))[0]
        # Replace spaces and dashes with underscores
        variable_name = variable_name.replace(' ', '_').replace('-', '_')
        variable_name += f"_{font_size}"
    
    try:
        # Load the font
        font = ImageFont.truetype(font_path, font_size)
    except IOError:
        print(f"Error: Could not load font file {font_path}")
        return None, None
    
    # Create an image for temporary rendering
    temp_img = Image.new('1', (100, 100), 0)
    temp_draw = ImageDraw.Draw(temp_img)
    
    # Calculate the maximum dimensions
    max_width = 0
    max_height = 0
    for i in range(char_range[0], char_range[1]):
        char = chr(i)
        bbox = font.getbbox(char)
        if bbox:
            width = bbox[2] - bbox[0]
            height = bbox[3] - bbox[1]
            max_width = max(max_width, width)
            max_height = max(max_height, height)
    
    # Add a small margin for safety
    max_height += 1
    
    # Create a list to store character data
    chars_data = []
    jump_table = []
    offset = 0
    
    for i in range(char_range[0], char_range[1]):
        char = chr(i)
        bbox = font.getbbox(char)
        
        if not bbox:
            # Character not supported, use placeholder
            jump_table.append((0xFF, 0xFF, 0, max_width))
            continue
        
        # Calculate character dimensions
        width = bbox[2] - bbox[0]
        height = bbox[3] - bbox[1]
        
        # Create a new image for this character
        char_img = Image.new('1', (width + 2, max_height + 2), 0)  # Add some padding
        char_draw = ImageDraw.Draw(char_img)
        
        # Draw the character
        char_draw.text((1 - bbox[0], 1 - bbox[1]), char, font=font, fill=1)
        
        # Convert to binary data
        char_bytes = []
        bytes_per_col = math.ceil(max_height / 8.0)
        
        for x in range(width):
            cols = []
            for byte_idx in range(bytes_per_col):
                col_byte = 0
                for bit_idx in range(8):
                    y = byte_idx * 8 + bit_idx
                    if y < max_height and x < width and char_img.getpixel((x + 1, y + 1)):
                        col_byte |= (1 << bit_idx)
                cols.append(col_byte)
            char_bytes.extend(cols)
        
        # Record jump table entry
        msb = (offset >> 8) & 0xFF
        lsb = offset & 0xFF
        jump_table.append((msb, lsb, len(char_bytes), width))
        
        # Update offset
        offset += len(char_bytes)
        
        # Store character data
        chars_data.append(char_bytes)
    
    # Compile font data
    font_data = []
    
    # Header: width, height, first char, number of chars
    font_data.append(max_width)
    font_data.append(max_height)
    font_data.append(char_range[0])
    font_data.append(char_range[1] - char_range[0])
    
    # Jump table
    for entry in jump_table:
        font_data.extend(entry)
    
    # Character data
    for char_bytes in chars_data:
        font_data.extend(char_bytes)
    
    # Font info for reference
    font_info = {
        'name': variable_name,
        'size': font_size,
        'width': max_width,
        'height': max_height,
        'first_char': char_range[0],
        'char_count': char_range[1] - char_range[0],
        'data_size': len(font_data),
        'source_font': os.path.basename(font_path)
    }
    
    return font_data, font_info

def generate_c_header(font_data, font_info, output_path):
    """
    Generate a C header file with the font data.
    
    Args:
        font_data: The font data array
        font_info: Information about the font
        output_path: Path to save the header file
    """
    with open(output_path, 'w') as f:
        # Write header with generation note and copyright info
        current_date = datetime.datetime.now().strftime("%Y-%m-%d")
        f.write(f"/*\n")
        f.write(f" * Font Name: {font_info['name']}\n")
        f.write(f" * Font Size: {font_info['size']}\n")
        f.write(f" * Font Width: {font_info['width']}\n")
        f.write(f" * Font Height: {font_info['height']}\n")
        f.write(f" * First Character: {font_info['first_char']} ({chr(font_info['first_char'])})\n")
        f.write(f" * Character Count: {font_info['char_count']}\n")
        f.write(f" * Data Size: {font_info['data_size']} bytes\n")
        f.write(f" * Source Font: {font_info['source_font']}\n")
        f.write(f" *\n")
        f.write(f" * This file was automatically generated by font_converter on {current_date}\n")
        f.write(f" * Created by Luc LEBOSSE\n")
        f.write(f" *\n")
        f.write(f" * This font data is licensed under the GNU LGPL v3 License.\n")
        f.write(f" */\n\n")
        
        # Define guard
        guard_name = f"{font_info['name'].upper()}_H"
        f.write(f"#ifndef {guard_name}\n")
        f.write(f"#define {guard_name}\n\n")
        
        # Begin array definition
        f.write(f"const char {font_info['name']}[] PROGMEM = {{\n")
        
        # Width, height, first char, char count
        f.write(f"\t0x{font_info['width']:02X}, // Width: {font_info['width']}\n")
        f.write(f"\t0x{font_info['height']:02X}, // Height: {font_info['height']}\n")
        f.write(f"\t0x{font_info['first_char']:02X}, // First Char: {font_info['first_char']}\n")
        f.write(f"\t0x{font_info['char_count']:02X}, // Numbers of Chars: {font_info['char_count']}\n\n")
        
        # Jump table section
        f.write("\t// Jump Table:\n")
        
        jump_table_size = font_info['char_count'] * 4
        for i in range(0, jump_table_size, 4):
            if i + 4 <= len(font_data):
                msb = font_data[i + 4]
                lsb = font_data[i + 5]
                size = font_data[i + 6]
                width = font_data[i + 7]
                
                char_index = i // 4
                char_code = font_info['first_char'] + char_index
                
                # Generate a safe character representation for comments
                char_repr = ""
                if 32 <= char_code <= 126:  # Printable ASCII characters excluding backslash
                    if char_code == 92:  # Backslash needs special handling
                        char_repr = "backslash"
                    else:
                        char_repr = chr(char_code)
                
                offset = (msb << 8) + lsb
                
                f.write(f"\t0x{msb:02X}, 0x{lsb:02X}, 0x{size:02X}, 0x{width:02X},  // {char_code}:{offset} {char_repr}\n")
        
        f.write("\n\t// Font Data:\n")
        
        # Font data section (after the header and jump table)
        data_start = 4 + jump_table_size
        line_length = 0
        f.write("\t")
        
        for i in range(data_start, len(font_data)):
            f.write(f"0x{font_data[i]:02X}")
            line_length += 1
            
            if i < len(font_data) - 1:
                f.write(",")
                
                if line_length >= 10:  # Start a new line after 10 bytes
                    f.write("\n\t")
                    line_length = 0
                else:
                    f.write(" ")
        
        # Close array and guard
        f.write("\n};\n\n")
        f.write(f"#endif // {guard_name}\n")

def main():
    parser = argparse.ArgumentParser(description='Convert TrueType fonts to OLED display compatible format')
    parser.add_argument('font_path', help='Path to the TrueType font file')
    parser.add_argument('font_size', type=int, help='Font size in pixels')
    parser.add_argument('--output', '-o', help='Output header file path')
    parser.add_argument('--name', help='Variable name for the font in the output file')
    parser.add_argument('--range', help='Character range in format "start-end" (e.g., "32-128")', default="32-128")
    
    args = parser.parse_args()
    
    # Parse character range
    try:
        start, end = map(int, args.range.split('-'))
        char_range = (start, end)
    except ValueError:
        print("Error: Invalid character range format. Use 'start-end' (e.g., '32-128')")
        return
    
    # Generate output path if not specified
    if args.output is None:
        font_basename = os.path.splitext(os.path.basename(args.font_path))[0]
        args.output = f"{font_basename}_{args.font_size}.h"
    
    # Generate font data
    font_data, font_info = generate_font_data(
        args.font_path, 
        args.font_size, 
        char_range=char_range,
        variable_name=args.name
    )
    
    if font_data is None:
        return
    
    # Generate C header file
    generate_c_header(font_data, font_info, args.output)
    
    print(f"Font conversion complete! Output saved to {args.output}")
    print(f"Font info: {font_info['width']}x{font_info['height']} pixels, {font_info['data_size']} bytes")

if __name__ == "__main__":
    main()
