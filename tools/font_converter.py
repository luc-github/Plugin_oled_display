#!/usr/bin/env python3
"""
Font Converter for OLED Displays
Converts TrueType fonts to a C header file format compatible with OLED display libraries.
Uses FreeType for accurate character positioning.

## Header File Structure:
1. Font Metadata (5 bytes):
   - Byte 0: Maximum character width in pixels
   - Byte 1: Maximum character height in pixels
   - Byte 2: MSB of character count
   - Byte 3: LSB of character count (combined with byte 2 gives total character count N)
   - Byte 4: Recommended character spacing in pixels

2. Character Table (N bytes):
   - List of character codes included in the font
   - Used to check if a character is supported and find its index

3. Jump Table (4 bytes per character):
   - Bytes 0-1: MSB and LSB of data offset
   - Byte 2: Size of character bitmap in bytes
   - Byte 3: Width of character in pixels (actual bitmap width)

4. Font Data:
   - Bitmap data for all characters
   - Stored in column-wise format
   - Each column consists of (max_height + 7) // 8 bytes
   - Each bit represents one pixel (1 = on, 0 = off)
   - Bits are arranged vertically within each byte

## Usage in Client Programs:
To render a character:
1. Get font info from header:
   - Get max width, height from bytes 0-1
   - Get character count from (byte 2 << 8) | byte 3
   - Get recommended spacing from byte 4

2. Search for the character code in the character table:
   - Start at byte 5 (after metadata)
   - Check each byte until you find a matching code or reach the end
   - If found, remember its position (index) in the table

3. Use this index to find the jump table entry:
   - Jump table starts at byte (5 + N) where N is the number of characters
   - Jump table entry position = (5 + N) + (index * 4)

4. Extract from jump table entry:
   - offset = (jump_table[0] << 8) | jump_table[1]
   - size = jump_table[2]
   - width = jump_table[3]

5. For each column (x = 0 to width-1):
   - Read bytes_per_col bytes at: data_offset + (x * bytes_per_col)
   - For each byte, render 8 vertical pixels according to the bits

6. Advance cursor position by: character_width + font_spacing

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

# Spacing calculation (to be adjusted)
def calculate_default_spacing(font_size):
    if font_size <= 10:
        return 1
    elif font_size <= 40:
        return 2
    else:
        # +1 for each additionnal 10 pixels above 40
        return 2 + ((font_size - 40) // 10) + 1

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

def parse_scope_string(scope_str):
    """
    Parse the scope string into a set of character codes.
    
    Args:
        scope_str: A string containing characters to include
        
    Returns:
        A sorted list of character codes
    """
    if not scope_str:
        return None
        
    # Remove duplicates while preserving order
    unique_chars = []
    seen = set()
    for c in scope_str:
        if c not in seen:
            unique_chars.append(c)
            seen.add(c)
            
    return [ord(c) for c in unique_chars]

def generate_font_data(font_path, font_size, custom_scope=None, char_range=(32, 128), variable_name=None, debug=False, spacing=None):
    """
    Generate font data from a TrueType font file using FreeType for accurate metrics.
    
    Args:
        font_path: Path to the TrueType font file
        font_size: Font size in pixels
        custom_scope: List of character codes to include (if None, use char_range)
        char_range: Range of characters to include (start, end) if custom_scope is None
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
    
    # Get the list of characters to process
    if custom_scope is not None:
        char_codes = custom_scope
        print(f"Using custom character set with {len(char_codes)} characters")
    else:
        char_codes = list(range(char_range[0], char_range[1]))
        print(f"Using character range {char_range[0]}-{char_range[1]} ({len(char_codes)} characters)")
    
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
    
    # Store actual character widths for later use
    char_widths = {}
    
    # Determine maximum bitmap dimensions
    for char_code in char_codes:
        char = chr(char_code)
        
        # Skip space character in dimension calculation
        if char == ' ':
            continue
            
        try:
            ft_face.load_char(char, freetype.FT_LOAD_RENDER)
            glyph = ft_face.glyph
            
            bitmap_width = glyph.bitmap.width
            bitmap_height = glyph.bitmap.rows
            advance_width = int(glyph.advance.x / 64)
            
            # Store the actual width for this character
            width = advance_width if advance_width > 0 else bitmap_width
            char_widths[char] = width
            
            if bitmap_width > 0 and bitmap_height > 0:
                max_width = max(max_width, bitmap_width)
                max_height = max(max_height, bitmap_height)
        except:
            # Skip unsupported characters
            continue
    
    # Ensure height is at least the font size
    max_height = max(max_height, int(height))
    
    # Add a small margin to avoid cutting off characters
    max_height += 1
    
    # Calculate bytes per column based on actual height
    bytes_per_col = (max_height + 7) // 8
    
    print(f"Maximum bitmap dimensions: {max_width}x{max_height} pixels")
    print(f"Bytes per column: {bytes_per_col}")
    
    # Create a list to store character data
    chars_data = []
    jump_table_entries = []
    offset = 0
    
    # Get space character advance width
    space_width = max_width // 3  # Default fallback
    try:
        ft_face.load_char(' ', freetype.FT_LOAD_RENDER)
        space_width = int(ft_face.glyph.advance.x / 64)
        char_widths[' '] = space_width
        print(f"Space character width: {space_width} pixels")
    except:
        print(f"Warning: Could not determine space width, using {space_width} pixels")
    
    # Store character width information for debugging
    if debug:
        width_log_path = f"{debug_dir}/character_widths.txt"
        with open(width_log_path, 'w') as wf:
            wf.write("Character Width Information:\n")
            wf.write("==========================\n")
            wf.write("Char\tCode\tWidth (px)\n")
    
    for char_code in char_codes:
        char = chr(char_code)
        
        # Special handling for space character
        if char == ' ':
            # Space character has no bitmap but needs an entry in the jump table
            jump_table_entries.append((0, 0, 0, space_width))
            
            # Log width information
            if debug:
                with open(width_log_path, 'a') as wf:
                    wf.write(f"'{char}'\t{char_code}\t{space_width}\n")
            
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
                char_widths[char] = width
                jump_table_entries.append((0, 0, 0, width))
                
                # Log width information
                if debug:
                    with open(width_log_path, 'a') as wf:
                        wf.write(f"'{char}'\t{char_code}\t{width} (zero-width)\n")
                
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
            char_widths[char] = width
            
            # Log width information
            if debug:
                with open(width_log_path, 'a') as wf:
                    wf.write(f"'{char}'\t{char_code}\t{width}\n")
            
            # Record jump table entry - USING THE ACTUAL WIDTH
            msb = (offset >> 8) & 0xFF
            lsb = offset & 0xFF
            jump_table_entries.append((msb, lsb, len(char_bytes), width))
            
            # Update offset
            offset += len(char_bytes)
            
            # Store character data
            chars_data.append(char_bytes)
            
        except Exception as e:
            # Character not supported or other error
            print(f"Warning: Could not process character '{char}' (code {char_code}): {e}")
            fallback_width = max_width // 2
            char_widths[char] = fallback_width
            jump_table_entries.append((0xFF, 0xFF, 0, fallback_width))
            
            # Log width information
            if debug:
                with open(width_log_path, 'a') as wf:
                    wf.write(f"'{char}'\t{char_code}\t{fallback_width} (error fallback)\n")
            
            if debug:
                try:
                    # Save an error placeholder image
                    error_bitmap = np.zeros((max_height, fallback_width), dtype=np.uint8)
                    save_debug_images(char, error_bitmap, [], debug_dir, max_height, bytes_per_col)
                except Exception as debug_err:
                    print(f"Warning: Could not save debug image for error character '{char}': {debug_err}")
    
    
    # Compile font data
    font_data = []
    
    # Check if the number of characters exceeds 16-bit limit
    if len(char_codes) > 65535:
        print(f"Warning: Number of characters ({len(char_codes)}) exceeds 65535, truncating to 65535")
        char_codes = char_codes[:65535]
    if spacing is not None:
        font_spacing  = spacing
    else:
        font_spacing  = calculate_default_spacing(font_size)
    
    print(f"Using character spacing: {font_spacing } pixels")
    
    # Header: width, height, char count MSB, char count LSB
    font_data.append(max_width)
    font_data.append(max_height)
    font_data.append((len(char_codes) >> 8) & 0xFF)  # MSB of char count
    font_data.append(len(char_codes) & 0xFF)         # LSB of char count
    font_data.append(font_spacing  & 0xFF)                 # spacing
    
    # Character table - always include this
    for char_code in char_codes:
        font_data.append(char_code)
    
    # Jump table - 4 bytes per character
    for entry in jump_table_entries:
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
        'char_count': len(char_codes),
        'spacing': font_spacing, 
        'data_size': len(font_data),
        'source_font': os.path.basename(font_path),
        'ascender': ascender,
        'descender': descender,
        'char_widths': char_widths,  # Store character widths for reference
        'bytes_per_col': bytes_per_col,  # Store bytes per column for reference
        'char_codes': char_codes  # Store the actual character codes
    }
    
    # Create a summary image with all characters if in debug mode
    if debug:
        try:
            create_debug_summary(font_path, font_size, char_codes, debug_dir, char_widths)
        except Exception as e:
            print(f"Warning: Could not create debug summary: {e}")
    
    return font_data, font_info
    
def create_debug_summary(font_path, font_size, char_codes, debug_dir, char_widths=None):
    """
    Create a summary debug image showing all processed characters
    """
    rows = (len(char_codes) + 15) // 16  # Characters per row
    cols = min(16, len(char_codes))
    
    font_basename = os.path.splitext(os.path.basename(font_path))[0]
    
    plt.figure(figsize=(cols * 1.2, rows * 1.2))
    plt.suptitle(f"Font: {font_basename}, Size: {font_size}px", fontsize=16)
    
    for i, code in enumerate(char_codes):
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
        
        # Add character info including width if available
        width_info = f", w:{char_widths[char]}px" if char_widths and char in char_widths else ""
        title = f"'{char}'{width_info}" if char.isprintable() and char != "'" else f"{code}{width_info}"
        ax.set_title(title, fontsize=8)
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
        f.write(f" * Font Width: {font_info['width']} (maximum width of any character)\n")
        f.write(f" * Font Height: {font_info['height']}\n")
        f.write(f" * Character Set: Custom ({font_info['char_count']} characters)\n")
        f.write(f" * Character Spacing: {font_info['spacing']} pixels\n")
        f.write(f" * Data Size: {font_info['data_size']} bytes\n")
        f.write(f" * Source Font: {font_info['source_font']}\n")
        f.write(f" * Bytes per Column: {font_info['bytes_per_col']}\n")
        f.write(f" *\n")
        f.write(f" * Font Data Format:\n")
        f.write(f" * - First 5 bytes: max width, height, char count MSB, char count LSB, spacing\n")
        f.write(f" * - Character Table: N bytes listing the codes of included characters\n")
        f.write(f" * - Jump Table: 4 bytes per character\n")
        f.write(f" *   - byte 0-1: MSB & LSB of offset in data array\n")
        f.write(f" *   - byte 2: Size in bytes of this character's bitmap\n")
        f.write(f" *   - byte 3: Width of character in pixels\n")
        f.write(f" * - Font Data: Bitmap data for all characters\n")
        f.write(f" *\n")
        f.write(f" * To render character 'X':\n")
        f.write(f" * 1. Get font info from header:\n")
        f.write(f" *    - Get max width, height from bytes 0-1\n")
        f.write(f" *    - Get character count from (byte 2 << 8) | byte 3\n")
        f.write(f" *    - Get recommended spacing from byte 4\n")
        f.write(f" * 2. Search for character code of 'X' in the character table\n")
        f.write(f" *    (bytes 5 to 5+N-1)\n")
        f.write(f" * 3. If found at position i, calculate jump table entry position:\n")
        f.write(f" *    jump_entry = (5 + N) + (i * 4)\n")
        f.write(f" * 4. Extract from jump table entry:\n")
        f.write(f" *    - offset = (jump_table[0] << 8) | jump_table[1]\n")
        f.write(f" *    - size = jump_table[2]\n")
        f.write(f" *    - width = jump_table[3]\n")
        f.write(f" * 5. Bytes per column: {font_info['bytes_per_col']}\n")
        f.write(f" * 6. Render bitmap columns from the data section\n")
        f.write(f" * 7. Advance cursor position by: character_width + font_spacing\n")
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
        
        # Metadata header
        f.write(f"\t0x{font_info['width']:02X}, // Width: {font_info['width']} (maximum)\n")
        f.write(f"\t0x{font_info['height']:02X}, // Height: {font_info['height']}\n")
        
        # Number of characters (16 bits)
        char_count_msb = (font_info['char_count'] >> 8) & 0xFF
        char_count_lsb = font_info['char_count'] & 0xFF
        f.write(f"\t0x{char_count_msb:02X}, // Number of Chars MSB\n")
        f.write(f"\t0x{char_count_lsb:02X}, // Number of Chars LSB: {font_info['char_count']}\n\n")
        spacing_value = font_info.get('spacing', 1)  # Valeur par défaut 1 si non définie
        f.write(f"\t0x{spacing_value:02X}, // Character Spacing: {spacing_value} pixels\n\n")
        
        # Character table (always included)
        f.write("\t// Character Table: List of character codes in this font\n")
        for i, char_code in enumerate(font_info['char_codes']):
            char = chr(char_code)
            char_repr = f"'{char}'" if char.isprintable() and char != "'" else f"0x{char_code:02X}"
            f.write(f"\t0x{char_code:02X}, // {i}: {char_repr}\n")
        f.write("\n")
        
        # Jump table section
        f.write("\t// Jump Table: Format is [MSB, LSB, size, width]\n")
        
        # Calculate jump table start position
        jump_table_start = 5 + font_info['char_count']  # Skip header and character table
        
        # Write jump table entries
        for i, char_code in enumerate(font_info['char_codes']):
            entry_pos = jump_table_start + i * 4
            
            if entry_pos + 3 < len(font_data):
                # Get jump table entry from font data
                msb = font_data[entry_pos]
                lsb = font_data[entry_pos + 1]
                size = font_data[entry_pos + 2]
                width = font_data[entry_pos + 3]
                
                # Get character representation
                char = chr(char_code)
                # Generate a safe character representation for comments
                if 32 <= char_code <= 126 and char_code != 92:  # Printable ASCII excluding backslash
                    char_repr = char
                elif char_code == 92:  # Backslash needs special handling
                    char_repr = "backslash"
                else:
                    char_repr = ""
                
                offset = (msb << 8) + lsb
                
                # Include actual width in comment for clarity
                comment = f"{char_code}:{offset}"
                if char_repr:
                    comment += f" '{char_repr}'"
                comment += f" width:{width}px"
                
                f.write(f"\t0x{msb:02X}, 0x{lsb:02X}, 0x{size:02X}, 0x{width:02X},  // {comment}\n")
        
        f.write("\n\t// Font Data:\n")
        
        # Font data section (after the header, character table, and jump table)
        data_start = jump_table_start + (font_info['char_count'] * 4)  # Skip header, char table, and jump table
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
    parser.add_argument('--scope', help='Custom character set (e.g., "ABC123")')
    parser.add_argument('--debug', action='store_true', help='Save debug bitmap images for characters')
    parser.add_argument('--spacing', type=int, help='Override character spacing in pixels (default: calculated based on font size)')
    
    args = parser.parse_args()
    spacing=args.spacing
    # Parse character range
    char_range = None
    if not args.scope:
        try:
            start, end = map(int, args.range.split('-'))
            char_range = (start, end)
        except ValueError:
            print("Error: Invalid character range format. Use 'start-end' (e.g., '32-128')")
            return
    
    # Parse custom scope if provided
    custom_scope = None
    if args.scope:
        custom_scope = parse_scope_string(args.scope)
        print(f"Using custom character set: {args.scope}")
    
    # Generate output path if not specified
    if args.output is None:
        font_basename = os.path.splitext(os.path.basename(args.font_path))[0]
        args.output = f"{font_basename}_{args.font_size}.h"
    
    # Generate font data
    font_data, font_info = generate_font_data(
        args.font_path, 
        args.font_size, 
        custom_scope=custom_scope,
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
    
    # Print summary of some important character widths
    if 'char_widths' in font_info:
        important_chars = ['a', 'W', 'm', 'i', '1', '0', '%', '@']
        print("\nCharacter Width Summary:")
        print("=========================")
        for char in important_chars:
            if char in font_info['char_widths']:
                print(f"Character '{char}': {font_info['char_widths'][char]} pixels")

if __name__ == "__main__":
    main()
