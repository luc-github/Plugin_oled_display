#!/usr/bin/env python3
"""
Enhanced TTF Font Metrics Extractor
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

----------------------------------
Extracts and displays comprehensive font metrics for specific characters from a TrueType font.

Usage:
    python ttf_info_extractor.py font_path font_size

Example:
    python ttf_info_extractor.py arialmt.ttf 8

Requirements:
    pip install pillow fonttools freetype-py matplotlib numpy
"""

import sys
import os
from PIL import Image, ImageDraw, ImageFont
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
from fontTools.ttLib import TTFont
import freetype

def extract_font_info(font_path, font_size):
    """
    Extract and display comprehensive font metrics for specific characters.
    
    Args:
        font_path: Path to the TrueType font file
        font_size: Font size in pixels
    """
    try:
        # Load the font using PIL
        pil_font = ImageFont.truetype(font_path, font_size)
    except IOError:
        print(f"Error: Could not load font file {font_path}")
        return
    
    # Load font with FontTools for more detailed metrics
    try:
        ttfont = TTFont(font_path)
        has_fonttools = True
    except Exception as e:
        print(f"Warning: FontTools extraction failed: {e}")
        has_fonttools = False
    
    # Load font with FreeType for pixel-specific metrics
    try:
        ft_face = freetype.Face(font_path)
        ft_face.set_pixel_sizes(0, font_size)
        has_freetype = True
    except Exception as e:
        print(f"Warning: FreeType extraction failed: {e}")
        has_freetype = False
    
    # Characters to analyze
    characters = ['a', 'b', 'p', 'A', 'L', ',', '.', ';', ':', '\'', '"', '-']
    
    # Print font information
    print(f"Font: {os.path.basename(font_path)}")
    print(f"Size: {font_size}px")
    
    # Extract global font metrics
    print("\nGlobal Font Metrics:")
    print("-" * 80)
    
    if has_fonttools:
        try:
            os2 = ttfont['OS/2']
            head = ttfont['head']
            hhea = ttfont['hhea']
            
            units_per_em = head.unitsPerEm
            scale_factor = font_size / units_per_em
            
            print(f"Units per em: {units_per_em}")
            print(f"Scale factor for {font_size}px: {scale_factor:.4f}")
            
            print(f"Ascender (design units): {hhea.ascent}")
            print(f"Descender (design units): {hhea.descent}")
            print(f"Line gap (design units): {hhea.lineGap}")
            
            if hasattr(os2, 'sxHeight'):
                print(f"x-height (design units): {os2.sxHeight}")
            if hasattr(os2, 'sCapHeight'):
                print(f"Cap height (design units): {os2.sCapHeight}")
            
            # Calculate pixel values
            ascent_px = round(hhea.ascent * scale_factor)
            descent_px = round(hhea.descent * scale_factor)
            line_gap_px = round(hhea.lineGap * scale_factor)
            
            print(f"Ascender (pixels): {ascent_px}")
            print(f"Descender (pixels): {descent_px}")
            print(f"Line gap (pixels): {line_gap_px}")
            print(f"Total line height (pixels): {ascent_px - descent_px + line_gap_px}")
        except Exception as e:
            print(f"Error extracting metrics with FontTools: {e}")
    
    if has_freetype:
        try:
            print("\nFreeType Metrics (pixels):")
            ft_ascender = ft_face.size.ascender / 64.0
            ft_descender = ft_face.size.descender / 64.0
            ft_height = ft_face.size.height / 64.0
            ft_max_advance = ft_face.size.max_advance / 64.0
            
            print(f"Ascender: {ft_ascender:.2f}")
            print(f"Descender: {ft_descender:.2f}")
            print(f"Line height: {ft_height:.2f}")
            print(f"Max advance width: {ft_max_advance:.2f}")
        except Exception as e:
            print(f"Error extracting metrics with FreeType: {e}")
    
    # Create figure for visualization
    fig_width = min(15, 1.5 * len(characters))
    fig, axes = plt.subplots(2, len(characters), figsize=(fig_width, 8))
    
    # Print character metrics
    print("\nCharacter Metrics:")
    print("-" * 100)
    header = f"{'Char':<6} {'Code':<6} {'Bounding Box':<40} {'Width':<8} {'Height':<8}"
    if has_freetype:
        header += f" {'Advance':<8} {'Bitmap Size':<12} {'Bitmap Offset':<15}"
    print(header)
    print("-" * 100)
    
    # Get baseline position for display
    if has_freetype:
        baseline_offset = int(ft_ascender)
    else:
        # Estimate baseline from the bottom of uppercase letters
        test_char = 'X'
        bbox = pil_font.getbbox(test_char)
        baseline_offset = bbox[3] if bbox else font_size * 3 // 4
    
    for i, char in enumerate(characters):
        # Get character metrics from PIL
        bbox = pil_font.getbbox(char)
        
        # Get freetype metrics if available
        ft_metrics = {}
        if has_freetype:
            try:
                ft_face.load_char(char, freetype.FT_LOAD_RENDER)
                glyph = ft_face.glyph
                ft_metrics['advance'] = glyph.advance.x / 64.0
                ft_metrics['bitmap_width'] = glyph.bitmap.width
                ft_metrics['bitmap_height'] = glyph.bitmap.rows
                ft_metrics['bitmap_left'] = glyph.bitmap_left
                ft_metrics['bitmap_top'] = glyph.bitmap_top
            except Exception:
                ft_metrics = {}
        
        if bbox:
            width = bbox[2] - bbox[0]
            height = bbox[3] - bbox[1]
            
            # Print metrics
            metrics_str = f"{char:<6} {ord(char):<6} {str(bbox):<40} {width:<8} {height:<8}"
            if ft_metrics:
                metrics_str += f" {ft_metrics['advance']:<8.2f} "
                metrics_str += f"{ft_metrics['bitmap_width']}x{ft_metrics['bitmap_height']:<8} "
                metrics_str += f"({ft_metrics['bitmap_left']},{ft_metrics['bitmap_top']})"
            print(metrics_str)
            
            # Create image for this character with baseline
            img_size = max(font_size * 3, 40)
            img = Image.new('RGB', (img_size, img_size), color=(255, 255, 255))
            draw = ImageDraw.Draw(img)
            
            # Draw grid
            for j in range(0, img_size, 2):
                draw.line([(0, j), (img_size, j)], fill=(240, 240, 240), width=1)
                draw.line([(j, 0), (j, img_size)], fill=(240, 240, 240), width=1)
            
            # Draw baseline
            baseline_y = img_size // 2
            draw.line([(0, baseline_y), (img_size, baseline_y)], fill=(255, 0, 0), width=1)
            
            # Draw x-height line if available
            if has_fonttools and hasattr(os2, 'sxHeight'):
                x_height_px = round(os2.sxHeight * scale_factor)
                x_height_y = baseline_y - x_height_px
                draw.line([(0, x_height_y), (img_size, x_height_y)], fill=(0, 200, 0), width=1)
            
            # Draw cap-height line if available
            if has_fonttools and hasattr(os2, 'sCapHeight'):
                cap_height_px = round(os2.sCapHeight * scale_factor)
                cap_height_y = baseline_y - cap_height_px
                draw.line([(0, cap_height_y), (img_size, cap_height_y)], fill=(0, 100, 200), width=1)
            
            # Draw character at baseline
            char_x = img_size // 4
            draw.text((char_x, baseline_y), char, font=pil_font, fill=(0, 0, 0))
            
            # Draw bounding box
            box_color = (0, 0, 255)
            draw.rectangle([
                (char_x + bbox[0], baseline_y + bbox[1]),
                (char_x + bbox[2], baseline_y + bbox[3])
            ], outline=box_color)
            
            # Draw freetype bitmap box if available
            if ft_metrics:
                bitmap_color = (200, 0, 200)
                bitmap_left = char_x + ft_metrics['bitmap_left']
                # FreeType's bitmap_top is relative to baseline
                bitmap_top = baseline_y - ft_metrics['bitmap_top']
                draw.rectangle([
                    (bitmap_left, bitmap_top),
                    (bitmap_left + ft_metrics['bitmap_width'], 
                     bitmap_top + ft_metrics['bitmap_height'])
                ], outline=bitmap_color)
            
            # Convert to numpy array for matplotlib
            img_array = np.array(img)
            
            # Display in first row
            axes[0, i].imshow(img_array)
            axes[0, i].set_title(f"'{char}' ({ord(char)})")
            axes[0, i].axis('off')
            
            # Create bitmap visualization
            if has_freetype:
                # Use the actual FreeType rendered bitmap
                ft_face.load_char(char, freetype.FT_LOAD_RENDER)
                glyph = ft_face.glyph
                bitmap = glyph.bitmap
                
                if bitmap.width > 0 and bitmap.rows > 0:
                    # Convert FreeType bitmap to numpy array
                    bitmap_array = np.array(bitmap.buffer, dtype=np.uint8).reshape(
                        bitmap.rows, bitmap.width)
                else:
                    # Empty bitmap (like space)
                    bitmap_array = np.zeros((font_size, font_size // 2), dtype=np.uint8)
            else:
                # Manually create bitmap since FreeType isn't available
                bitmap_size = max(width, height) + 4
                bitmap = Image.new('1', (bitmap_size, bitmap_size), 0)
                bitmap_draw = ImageDraw.Draw(bitmap)
                
                # Position character in bitmap
                x_pos = 2 - bbox[0]
                y_pos = 2
                bitmap_draw.text((x_pos, y_pos), char, font=pil_font, fill=1)
                bitmap_array = np.array(bitmap)
            
            # Display bitmap in second row
            axes[1, i].imshow(bitmap_array, cmap='binary')
            axes[1, i].set_title(f"Bitmap")
            axes[1, i].axis('off')
            
            # Add grid to bitmap view
            for x in range(0, bitmap_array.shape[1], 1):
                axes[1, i].axvline(x - 0.5, color='gray', linewidth=0.5, alpha=0.3)
            for y in range(0, bitmap_array.shape[0], 1):
                axes[1, i].axhline(y - 0.5, color='gray', linewidth=0.5, alpha=0.3)
            
        else:
            print(f"{char:<6} {ord(char):<6} No bounding box available")
            axes[0, i].text(0.5, 0.5, "No data", ha='center', va='center')
            axes[1, i].text(0.5, 0.5, "No data", ha='center', va='center')
            axes[0, i].axis('off')
            axes[1, i].axis('off')
    
    # Add legend and explanation
    legend_elements = [
        plt.Line2D([0], [0], color='red', lw=2, label='Baseline'),
        plt.Line2D([0], [0], color='blue', lw=2, label='PIL Bounding Box')
    ]
    
    if has_fonttools:
        if hasattr(os2, 'sxHeight'):
            legend_elements.append(plt.Line2D([0], [0], color='green', lw=2, label='x-height'))
        if hasattr(os2, 'sCapHeight'):
            legend_elements.append(plt.Line2D([0], [0], color=(0, 0.5, 1), lw=2, label='Cap height'))
    
    if has_freetype:
        legend_elements.append(plt.Line2D([0], [0], color='purple', lw=2, label='FreeType Bitmap'))
    
    fig.legend(handles=legend_elements, loc='upper center', bbox_to_anchor=(0.5, 0.03), 
               ncol=len(legend_elements), frameon=False)
    
    # Adjust layout and save
    plt.tight_layout(rect=[0, 0.07, 1, 0.97])
    output_file = f"font_metrics_{os.path.splitext(os.path.basename(font_path))[0]}_{font_size}.png"
    plt.savefig(output_file, dpi=150)
    print(f"\nVisualization saved to: {output_file}")
    
    # Show the plot
    plt.show()

def main():
    if len(sys.argv) != 3:
        print("Usage: python ttf_info_extractor.py font_path font_size")
        sys.exit(1)
    
    font_path = sys.argv[1]
    try:
        font_size = int(sys.argv[2])
    except ValueError:
        print("Error: Font size must be an integer")
        sys.exit(1)
    
    extract_font_info(font_path, font_size)

if __name__ == "__main__":
    main()
