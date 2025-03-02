#!/usr/bin/env python3
"""
Font Converter for OLED Displays
Converts TrueType fonts to a C header file format compatible with OLED display libraries.
Uses FreeType for accurate character positioning.

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
import freetype
import numpy as np
import matplotlib.pyplot as plt
import re

def calculate_y_position(bitmap_top, bitmap_height, matrix_height):
    """
    Calculate the vertical position for a character bitmap in the matrix.
    
    Args:
        bitmap_top: The FreeType bitmap_top value (distance from baseline to top of bitmap)
        bitmap_height: The height of the bitmap
        matrix_height: The height of your character matrix
    
    Returns:
        The y position where the top of the bitmap should be placed
    """
    # Calculate baseline position in the matrix based on ascender
    baseline_position = matrix_height * 3 // 4  # Approximation if not available
    
    # Calculate where top of the bitmap should be relative to baseline
    y_position = baseline_position - bitmap_top
    
    # Ensure it's within the bounds of the matrix
    y_position = max(0, min(matrix_height - bitmap_height, y_position))
    
    return y_position

def get_safe_filename(char, char_code):
    """
    Get a safe filename for a character, avoiding invalid characters.
    """
    # Use only the character code for characters that might cause filename problems
    if not char.isalnum() and char not in '-_':
        return f"char_{char_code:03d}_0x{char_code:02X}"
    else:
        return f"char_{char_code:03d}_{char}"

def save_debug_images(char, char_bitmap, final_bitmap_bytes, debug_dir, max_height, bytes_per_col):
    """
    Save debug images showing bitmap representations of a character.
    
    Args:
        char: The character being processed
        char_bitmap: The numpy array containing the character bitmap
        final_bitmap_bytes: The final bytes that will be stored in the font file
        debug_dir: Directory to save debug images
        max_height: Height of the character matrix
        bytes_per_col: Number of bytes per column in the final data
    """
    # Create debug directory if it doesn't exist
    if not os.path.exists(debug_dir):
        os.makedirs(debug_dir)
    
    # 1. Save the raw character bitmap
    char_code = ord(char)
    safe_name = get_safe_filename(char, char_code)
    bitmap_filename = f"{debug_dir}/{safe_name}_bitmap.png"
    
    # Ensure the bitmap is in the right format for PIL
    bitmap_array = np.asarray(char_bitmap, dtype=np.uint8)
    
    # Create PIL image from numpy array
    pil_img = Image.fromarray(bitmap_array)
    pil_img.save(bitmap_filename)
    
    # 2. Recreate and save the bitmap as it would be rendered
    bitmap_width = len(final_bitmap_bytes) // bytes_per_col if bytes_per_col > 0 else 0
    
    if bitmap_width > 0:
        # Create a new image to show how the final bytes would render
        rendered_bitmap = np.zeros((max_height, bitmap_width), dtype=np.uint8)
        
        for x in range(bitmap_width):
            for byte_idx in range(bytes_per_col):
                byte_value = final_bitmap_bytes[x * bytes_per_col + byte_idx]
                for bit_idx in range(8):
                    y = byte_idx * 8 + bit_idx
                    if y < max_height and byte_value & (1 << bit_idx):
                        rendered_bitmap[y, x] = 255
        
        # Save the rendered bitmap
        rendered_filename = f"{debug_dir}/{safe_name}_rendered.png"
        rendered_img = Image.fromarray(rendered_bitmap)
        rendered_img.save(rendered_filename)
    
    print(f"Saved debug images for character '{char}' (code {char_code})")

def generate_font_data(font_path, font_size, char_range=(32, 128), variable_name=None, debug=False):
    """
    Generate font data from a TrueType font file using FreeType for accurate metrics.
    
    Args:
        font_path: Path to the TrueType font file
        font_size: Font size in pixels
        char_range: Range of characters to include (start, end)
        variable_name: Name of the variable in the output file
        debug: If True, save debug images of each character
        
    Returns:
        A tuple containing the font data and font info
    """
    if variable_name is None:
        # Generate variable name from font filename without extension
        variable_name = os.path.splitext(os.path.basename(font_path))[0]
        # Replace spaces and dashes with underscores
        variable_name = variable_name.replace(' ', '_').replace('-', '_')
        variable_name += f"_{font_size}"
    
    # Create debug directory if needed
    debug_dir = None
    if debug:
        font_basename = os.path.splitext(os.path.basename(font_path))[0]
        debug_dir = f"debug_{font_basename}_{font_size}"
        if not os.path.exists(debug_dir):
            os.makedirs(debug_dir)
        print(f"Debug mode enabled. Images will be saved to {debug_dir}/")
    
    try:
        # Load font with FreeType
        ft_face = freetype.Face(font_path)
        ft_face.set_pixel_sizes(0, font_size)
    except Exception as e:
        print(f"Error: Could not load font file {font_path} with FreeType: {e}")
        return None, None
    
    # Get font metrics
    ascender = ft_face.size.ascender / 64.0
    descender = ft_face.size.descender / 64.0
    height = ft_face.size.height / 64.0
    max_advance = ft_face.size.max_advance / 64.0
    
    print(f"Font metrics: Ascender={ascender}, Descender={descender}, Height={height}")
    
    # Calculate the maximum dimensions for all characters
    max_width = 0
    max_height = 0
    
    # Determine maximum bitmap dimensions
    for i in range(char_range[0], char_range[1]):
        char = chr(i)
        
        # Skip space character in dimension calculation
        if char == ' ':
            continue
            
        try:
            ft_face.load_char(char, freetype.FT_LOAD_RENDER)
            glyph = ft_face.glyph
            
            bitmap_width = glyph.bitmap.width
            bitmap_height = glyph.bitmap.rows
            
            if bitmap_width > 0 and bitmap_height > 0:
                max_width = max(max_width, bitmap_width)
                max_height = max(max_height, bitmap_height)
        except:
            # Skip unsupported characters
            continue
    
    # Ensure height is at least the font size
    max_height = max(max_height, int(height))
    
    # Ensure max_height is at least 8 pixels for typical OLED displays
    max_height = max(max_height, 8)
    
    # Round up max_height to multiple of 8 for byte alignment
    max_height = ((max_height + 7) // 8) * 8
    
    # Calculate bytes per column for later use
    bytes_per_col = max_height // 8
    
    print(f"Maximum bitmap dimensions: {max_width}x{max_height} pixels")
    
    # Create a list to store character data
    chars_data = []
    jump_table = []
    offset = 0
    
    # Get space character advance width
    space_width = max_width // 3  # Default fallback
    try:
        ft_face.load_char(' ', freetype.FT_LOAD_RENDER)
        space_width = int(ft_face.glyph.advance.x / 64)
        print(f"Space character width: {space_width} pixels")
    except:
        print(f"Warning: Could not determine space width, using {space_width} pixels")
    
    for i in range(char_range[0], char_range[1]):
        char = chr(i)
        
        # Special handling for space character
        if char == ' ':
            # Space character has no bitmap but needs an entry in the jump table
            jump_table.append((0, 0, 0, space_width))
            
            # Save an empty debug image for space if debug mode is on
            if debug:
                try:
                    empty_bitmap = np.zeros((max_height, space_width), dtype=np.uint8)
                    save_debug_images(char, empty_bitmap, [], debug_dir, max_height, bytes_per_col)
                except Exception as e:
                    print(f"Warning: Could not save debug image for space: {e}")
            
            continue
            
        try:
            ft_face.load_char(char, freetype.FT_LOAD_RENDER)
            glyph = ft_face.glyph
            
            bitmap = glyph.bitmap
            bitmap_width = bitmap.width
            bitmap_height = bitmap.rows
            bitmap_left = glyph.bitmap_left
            bitmap_top = glyph.bitmap_top
            advance_width = int(glyph.advance.x / 64)
            
            # For zero-width characters, use a standard width
            if bitmap_width == 0:
                # Use advance width, or 1/4 of max_width as fallback
                width = max(advance_width, max_width // 4)
                jump_table.append((0, 0, 0, width))
                
                if debug:
                    try:
                        empty_bitmap = np.zeros((max_height, width), dtype=np.uint8)
                        save_debug_images(char, empty_bitmap, [], debug_dir, max_height, bytes_per_col)
                    except Exception as e:
                        print(f"Warning: Could not save debug image for zero-width character '{char}': {e}")
                
                continue
            
            # Create a bitmap matrix of correct size - initialize to zeros
            char_bitmap = np.zeros((max_height, bitmap_width), dtype=np.uint8)
            
            # Calculate where to position the bitmap vertically
            y_position = calculate_y_position(bitmap_top, bitmap_height, max_height)
            
            # Copy the FreeType bitmap into our matrix
            if bitmap.buffer and bitmap_width > 0 and bitmap_height > 0:
                # Check if the bitmap is valid
                if len(bitmap.buffer) == bitmap_width * bitmap_height:
                    ft_bitmap = np.array(bitmap.buffer, dtype=np.uint8).reshape(bitmap_height, bitmap_width)
                    
                    # Apply thresholding - any value > 0 becomes 255
                    # This ensures clean black and white rendering
                    ft_bitmap = np.where(ft_bitmap > 0, 255, 0)
                    
                    # Paste the bitmap at the calculated position
                    char_bitmap[y_position:y_position+bitmap_height, 0:bitmap_width] = ft_bitmap
            
            # Threshold the entire bitmap to ensure it's binary (0 or 255)
            char_bitmap = np.where(char_bitmap > 0, 255, 0)
            
            # Convert to columnwise bitmap data for OLED display
            char_bytes = []
            
            for x in range(bitmap_width):
                for byte_idx in range(bytes_per_col):
                    col_byte = 0
                    for bit_idx in range(8):
                        y = byte_idx * 8 + bit_idx
                        if y < max_height and char_bitmap[y, x] > 0:
                            col_byte |= (1 << bit_idx)
                    char_bytes.append(col_byte)
            
            # Save debug images if debug mode is on
            if debug:
                try:
                    save_debug_images(char, char_bitmap, char_bytes, debug_dir, max_height, bytes_per_col)
                except Exception as e:
                    print(f"Warning: Could not save debug image for character '{char}': {e}")
            
            # Record advance width (actual character width including spacing)
            width = advance_width if advance_width > 0 else bitmap_width
            
            # Record jump table entry
            msb = (offset >> 8) & 0xFF
            lsb = offset & 0xFF
            jump_table.append((msb, lsb, len(char_bytes), width))
            
            # Update offset
            offset += len(char_bytes)
            
            # Store character data
            chars_data.append(char_bytes)
            
        except Exception as e:
            # Character not supported or other error
            print(f"Warning: Could not process character '{char}' (code {i}): {e}")
            jump_table.append((0xFF, 0xFF, 0, max_width // 2))
            
            if debug:
                try:
                    # Save an error placeholder image
                    error_bitmap = np.zeros((max_height, max_width // 2), dtype=np.uint8)
                    save_debug_images(char, error_bitmap, [], debug_dir, max_height, bytes_per_col)
                except Exception as debug_err:
                    print(f"Warning: Could not save debug image for error character '{char}': {debug_err}")
    
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
        'source_font': os.path.basename(font_path),
        'ascender': ascender,
        'descender': descender
    }
    
    # Create a summary image with all characters if in debug mode
    if debug:
        try:
            create_debug_summary(font_path, font_size, char_range, debug_dir)
        except Exception as e:
            print(f"Warning: Could not create debug summary: {e}")
    
    return font_data, font_info

def create_debug_summary(font_path, font_size, char_range, debug_dir):
    """
    Create a summary debug image showing all processed characters
    """
    rows = (char_range[1] - char_range[0] + 15) // 16  # Characters per row
    cols = min(16, char_range[1] - char_range[0])
    
    font_basename = os.path.splitext(os.path.basename(font_path))[0]
    
    plt.figure(figsize=(cols * 1.2, rows * 1.2))
    plt.suptitle(f"Font: {font_basename}, Size: {font_size}px", fontsize=16)
    
    for i, code in enumerate(range(char_range[0], char_range[1])):
        char = chr(code)
        row = i // 16
        col = i % 16
        
        ax = plt.subplot(rows, cols, i + 1)
        
        # Try to load the rendered image
        safe_name = get_safe_filename(char, code)
        rendered_path = f"{debug_dir}/{safe_name}_rendered.png"
        bitmap_path = f"{debug_dir}/{safe_name}_bitmap.png"
        
        if os.path.exists(rendered_path):
            try:
                img = plt.imread(rendered_path)
                ax.imshow(img, cmap='binary')
            except:
                ax.text(0.5, 0.5, '?', ha='center', va='center')
        elif os.path.exists(bitmap_path):
            try:
                img = plt.imread(bitmap_path)
                ax.imshow(img, cmap='binary')
            except:
                ax.text(0.5, 0.5, '?', ha='center', va='center')
        else:
            ax.text(0.5, 0.5, '?', ha='center', va='center')
            
        # Add character info
        title = f"'{char}'" if char.isprintable() and char != "'" else f"{code}"
        ax.set_title(title)
        ax.axis('off')
    
    plt.tight_layout()
    summary_path = f"{debug_dir}/summary.png"
    plt.savefig(summary_path, dpi=150)
    print(f"Saved character summary to {summary_path}")

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
    parser.add_argument('--debug', action='store_true', help='Save debug bitmap images for characters')
    
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
        variable_name=args.name,
        debug=args.debug
    )
    
    if font_data is None:
        return
    
    # Generate C header file
    generate_c_header(font_data, font_info, args.output)
    
    print(f"Font conversion complete! Output saved to {args.output}")
    print(f"Font info: {font_info['width']}x{font_info['height']} pixels, {font_info['data_size']} bytes")

if __name__ == "__main__":
    main()
