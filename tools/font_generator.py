#!/usr/bin/env python3
"""
Font Template Generator and Converter
Creates template matrices for font design and converts them to OLED-compatible header files.

This script has two main functions:
1. Generate template files with matrices for each printable ASCII character.
2. Convert edited template files into a C header file compatible with OLED displays.

Usage:
  python font_template_generator.py [font_name] [font_size] [--generatetemplate] [--generatefont] [--debug]

Examples:
  python font_template_generator.py oled 10 --generatetemplate
  python font_template_generator.py oled 10 --generatefont --debug

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

import os
import argparse
import math
import datetime
from PIL import Image, ImageDraw
import numpy as np
import matplotlib.pyplot as plt

def calculate_default_spacing(font_size):
    """Calculate recommended spacing based on font size"""
    if font_size <= 10:
        return 1
    elif font_size <= 40:
        return 2
    else:
        # +1 for each additional 10 pixels beyond 40
        return 2 + ((font_size - 40) // 10) + 1

def generate_template_files(font_name, font_size, template_dir):
    """
    Generate template files for each printable ASCII character.
    
    Args:
        font_name (str): Name of the font
        font_size (int): Size of the font in pixels (height)
        template_dir (str): Directory to save the template files
    """
    # Create the template directory if it doesn't exist
    if not os.path.exists(template_dir):
        os.makedirs(template_dir)
        print(f"Created directory: {template_dir}")

    # Calculate width (60% of height, rounded)
    width = math.ceil(font_size * 0.6)
    
    # Range of printable ASCII characters (32-126)
    for char_code in range(32, 127):
        char = chr(char_code)
        filename = f"{char_code}.txt"
        filepath = os.path.join(template_dir, filename)
        
        # Create the template file
        with open(filepath, 'w') as f:
            # First line is the character
            f.write(f"{char}\n")
            
            # Followed by the matrix of 'O' characters
            for _ in range(font_size):
                f.write('O' * width + '\n')
            
            # Add an extra newline at the end
            f.write('\n')
        
        print(f"Created template for character '{char}' (ASCII {char_code}) in {filename}")

def get_safe_filename(char, char_code):
    """Get a safe filename for debug images"""
    if not char.isalnum() and char not in '-_':
        return f"char_{char_code:03d}_0x{char_code:02X}"
    else:
        return f"char_{char_code:03d}_{char}"

def parse_template_file(filepath, font_size):
    """
    Parse a template file to extract the character bitmap.
    
    Args:
        filepath (str): Path to the template file
        font_size (int): Expected height of the font
        
    Returns:
        tuple: (Character, numpy bitmap array, width, height)
    """
    try:
        with open(filepath, 'r') as f:
            lines = f.readlines()
        
        # First line should be the character
        char = lines[0].strip()
        
        # Next lines should be the bitmap
        bitmap_lines = [line.rstrip() for line in lines[1:font_size+1]]
        
        # Find max width
        width = max(len(line) for line in bitmap_lines)
        
        # Create bitmap array
        bitmap = np.zeros((font_size, width), dtype=np.uint8)
        
        for y, line in enumerate(bitmap_lines):
            for x, pixel in enumerate(line):
                if x < width:
                    # 'X' represents a lit pixel, anything else is off
                    bitmap[y, x] = 255 if pixel == 'X' else 0
        
        return char, bitmap, width, font_size
        
    except Exception as e:
        print(f"Error parsing template file {filepath}: {str(e)}")
        return None, None, 0, 0

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
    
    # Create PIL image from numpy array
    pil_img = Image.fromarray(char_bitmap)
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

def create_debug_summary(font_name, font_size, char_codes, debug_dir, char_widths=None):
    """
    Create a summary debug image showing all processed characters
    """
    rows = (len(char_codes) + 15) // 16  # Characters per row
    cols = min(16, len(char_codes))
    
    plt.figure(figsize=(cols * 1.2, rows * 1.2))
    plt.suptitle(f"Font: {font_name}, Size: {font_size}px", fontsize=16)
    
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

def generate_font_from_templates(font_name, font_size, template_dir, output_file, debug=False):
    """
    Generate a font header file from template files.
    
    Args:
        font_name (str): Name of the font
        font_size (int): Size of the font in pixels (height)
        template_dir (str): Directory containing template files
        output_file (str): Path to the output header file
        debug (bool): Whether to generate debug images
    """
    # Check if template directory exists
    if not os.path.exists(template_dir):
        print(f"Error: Template directory '{template_dir}' does not exist.")
        return False
    
    # Create debug directory if needed
    debug_dir = None
    if debug:
        debug_dir = f"debug_{font_name}_{font_size}"
        if not os.path.exists(debug_dir):
            os.makedirs(debug_dir)
        print(f"Debug mode enabled. Images will be saved to {debug_dir}/")
    
    # Determine bytes per column
    max_height = font_size
    bytes_per_col = (max_height + 7) // 8
    
    # Calculate spacing based on font size
    spacing = calculate_default_spacing(font_size)
    
    # Initialize data structures
    char_codes = []
    chars_data = []
    jump_table_entries = []
    char_widths = {}
    max_width = 0
    offset = 0
    
    # Store character width information for debugging
    if debug:
        width_log_path = f"{debug_dir}/character_widths.txt"
        with open(width_log_path, 'w') as wf:
            wf.write("Character Width Information:\n")
            wf.write("==========================\n")
            wf.write("Char\tCode\tWidth (px)\n")
    
    # Process all template files
    for char_code in range(32, 127):
        filepath = os.path.join(template_dir, f"{char_code}.txt")
        
        if os.path.exists(filepath):
            char = chr(char_code)
            char_codes.append(char_code)
            
            char_str, bitmap, width, height = parse_template_file(filepath, font_size)
            
            if bitmap is None:
                print(f"Warning: Could not process template for character '{char}' (code {char_code})")
                
                # Use fallback width
                fallback_width = math.ceil(font_size * 0.6)
                char_widths[char] = fallback_width
                jump_table_entries.append((0xFF, 0xFF, 0, fallback_width))
                
                # Log width information
                if debug:
                    with open(width_log_path, 'a') as wf:
                        wf.write(f"'{char}'\t{char_code}\t{fallback_width} (fallback)\n")
                continue
            
            # Update max width
            max_width = max(max_width, width)
            char_widths[char] = width
            
            # Log width information
            if debug:
                with open(width_log_path, 'a') as wf:
                    wf.write(f"'{char}'\t{char_code}\t{width}\n")
            
            # Convert to columnwise bitmap data for OLED display
            char_bytes = []
            
            for x in range(width):
                for byte_idx in range(bytes_per_col):
                    col_byte = 0
                    for bit_idx in range(8):
                        y = byte_idx * 8 + bit_idx
                        if y < max_height and x < width and bitmap[y, x] > 0:
                            col_byte |= (1 << bit_idx)
                    char_bytes.append(col_byte)
            
            # Save debug images if debug mode is on
            if debug:
                try:
                    save_debug_images(char, bitmap, char_bytes, debug_dir, max_height, bytes_per_col)
                except Exception as e:
                    print(f"Warning: Could not save debug image for character '{char}': {e}")
            
            # Record jump table entry
            msb = (offset >> 8) & 0xFF
            lsb = offset & 0xFF
            jump_table_entries.append((msb, lsb, len(char_bytes), width))
            
            # Update offset
            offset += len(char_bytes)
            
            # Store character data
            chars_data.append(char_bytes)
    
    # Compile font data
    font_data = []
    
    # Verify the number of characters doesn't exceed the limit
    if len(char_codes) > 65535:
        print(f"Warning: Number of characters ({len(char_codes)}) exceeds 65535, truncating to 65535")
        char_codes = char_codes[:65535]
    
    # Header: width, height, char count MSB, char count LSB, spacing
    font_data.append(max_width)
    font_data.append(max_height)
    font_data.append((len(char_codes) >> 8) & 0xFF)  # MSB of char count
    font_data.append(len(char_codes) & 0xFF)         # LSB of char count
    font_data.append(spacing)                        # Spacing
    
    # Character table
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
        'name': font_name + "_" + str(font_size),
        'size': font_size,
        'width': max_width,
        'height': max_height,
        'char_count': len(char_codes),
        'spacing': spacing,
        'data_size': len(font_data),
        'source_font': "Template",
        'bytes_per_col': bytes_per_col,
        'char_codes': char_codes,
        'char_widths': char_widths
    }
    
    # Create a summary image with all characters if in debug mode
    if debug:
        try:
            create_debug_summary(font_name, font_size, char_codes, debug_dir, char_widths)
        except Exception as e:
            print(f"Warning: Could not create debug summary: {e}")
    
    # Generate C header file
    generate_c_header(font_data, font_info, output_file)
    
    return True

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
        f.write(f" * This file was automatically generated by font_template_generator on {current_date}\n")
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
        f.write(f"\t0x{char_count_lsb:02X}, // Number of Chars LSB: {font_info['char_count']}\n")
        f.write(f"\t0x{font_info['spacing']:02X}, // Character Spacing: {font_info['spacing']} pixels\n\n")
        
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
    parser = argparse.ArgumentParser(description='Generate font template files and convert them to header files.')
    parser.add_argument('font_name', help='Name of the font')
    parser.add_argument('font_size', type=int, help='Size of the font in pixels (height)')
    parser.add_argument('--generatetemplate', action='store_true', help='Generate template files')
    parser.add_argument('--generatefont', action='store_true', help='Generate font header file from templates')
    parser.add_argument('--debug', action='store_true', help='Generate debug images and information')
    parser.add_argument('--output', '-o', help='Output header file path')
    
    args = parser.parse_args()
    
    # Create template directory name
    template_dir = f"{args.font_name}_{args.font_size}"
    
    # Determine output file path
    output_file = args.output if args.output else f"{args.font_name}_{args.font_size}.h"
    
    if args.generatetemplate:
        # Generate template files
        generate_template_files(args.font_name, args.font_size, template_dir)
        print(f"\nTemplate generation complete. Template files saved in '{template_dir}/' directory.")
        print(f"Font dimensions: {args.font_size} pixels (height) x {math.ceil(args.font_size * 0.6)} pixels (width)")
        print("\nEdit the template files by replacing 'O' with 'X' to define pixels, then run with --generatefont to create the font file.")
    
    if args.generatefont:
        # Generate font header file from templates
        success = generate_font_from_templates(args.font_name, args.font_size, template_dir, output_file, args.debug)
        
        if success:
            print(f"\nFont generation complete. Font header file saved as '{output_file}'.")
            print("The font can now be used in your OLED display projects.")
            
            if args.debug:
                print(f"Debug information saved in 'debug_{args.font_name}_{args.font_size}/' directory.")
    
    if not args.generatetemplate and not args.generatefont:
        print("No action specified. Use --generatetemplate to create template files or --generatefont to generate a font file.")

if __name__ == "__main__":
    main()
