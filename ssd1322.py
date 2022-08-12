"""MicroPython SSD1322 OLED monochrom display driver."""
from math import cos, sin, pi, radians
from micropython import const  # type: ignore
from framebuf import FrameBuffer, GS8, MONO_HMSB, GS4_HMSB  # type: ignore
from utime import sleep_ms  # type: ignore
from mono_palette import MonoPalette


class Display(object):
    """Serial interface for monochrome OLED display.

    Note:  All coordinates are zero based.
    """

    # Command constants from display datasheet
    ENABLE_GRAY_SCALE_TABLE = const(0x00)
    SET_COLUMN_ADDRESS = const(0x15)
    WRITE_RAM = const(0x5C)
    READ_RAM = const(0x5D)
    SET_ROW_ADDRESS = const(0x75)
    SET_REMAP_DUAL_COM_LINE_MODE = const(0xA0)  # Re-map & Dual COM Line Mode
    SET_DISPLAY_START_LINE = const(0xA1)
    SET_DISPLAY_OFFSET = const(0xA2)
    SET_DISPLAY_MODE_ALL_OFF = const(0xA4)
    SET_DISPLAY_MODE_ALL_ON = const(0xA5)
    SET_DISPLAY_MODE_NORMAL = const(0xA6)
    SET_DISPLAY_MODE_INVERSE = const(0xA7)
    PARTIAL_DISPLAY_ENABLE = const(0xA8)
    PARTIAL_DISPLAY_DISABLE = const(0xA9)
    SET_FUNCTION_SELECTION = const(0xAB)
    DISPLAY_SLEEP_ON = const(0xAE)
    DISPLAY_SLEEP_OFF = const(0xAF)
    SET_PHASE_LENGTH = const(0xB1)
    SET_FRONT_CLOCK_DIVIDER = const(0xB3)
    DISPLAY_ENHANCEMENT_A = const(0xB4)
    SET_GPIO = const(0xB5)
    SET_SECOND_PRECHARGE_PERIOD = const(0xB6)
    SET_GRAY_SCALE_TABLE = const(0xB8)
    SELECT_DEFAULT_LINEAR_GRAY_SCALE_TABLE = const(0xB9)
    SET_PRECHARGE_VOLTAGE = const(0xBB)
    SET_VCOMH_VOLTAGE = const(0xBE)
    SET_CONTRAST_CURRENT = const(0xC1)
    MASTER_CURRENT_CONTROL = const(0xC7)
    SET_MULTIPLEX_RATIO = const(0xCA)
    DISPLAY_ENHANCEMENT_B = const(0xD1)
    SET_COMMAND_LOCK = const(0xFD)

    # Options for controlling VSL selection
    ENABLE_EXTERNAL_VSL = const(0x00)
    ENABLE_INTERNAL_VSL = const(0x02)

    # Options for grayscale quality
    NORMAL_GRAYSCALE_QUALITY = const(0xB0)
    ENHANCED_LOW_GRAY_SCALE_QUALITY = const(0XF8)

    # Options for display enhancement b
    RESERVED_ENHANCEMENT = const(0x00)
    NORMAL_ENHANCEMENT = const(0x02)

    # Options for command lock
    COMMANDS_LOCK = const(0x16)
    COMMANDS_UNLOCK = const(0x12)

    # Column and row maximums
    # NOTE: Unsure if addresses vary among displays
    COLUMN_ADDRESS = const(0x77)
    ROW_ADDRESS = const(0x7F)

    def __init__(self, spi, cs, dc, rst, width=256, height=64):
        """Constructor for Display.

        Args:
            spi (Class Spi):  SPI interface for display
            cs (Class Pin):  Chip select pin
            dc (Class Pin):  Data/Command pin
            rst (Class Pin):  Reset pin
            width (Optional int): Screen width (default 256)
            height (Optional int): Screen height (default 64)
        """
        self.spi = spi
        self.cs = cs
        self.dc = dc
        self.rst = rst
        self.width = width
        self.height = height
        self.byte_width = -(-width // 2)  # Ceiling division
        self.buffer_length = self.byte_width * height
        # Buffer
        self.gs4_buf = bytearray(self.buffer_length)
        # Frame Buffer
        self.gs4_fb = FrameBuffer(self.gs4_buf, width, height, GS4_HMSB)
        # Init palette for mono to GS4 blit
        self.palette = MonoPalette()
        self.clear_buffers()
        # Initialize GPIO pins
        self.cs.init(self.cs.OUT, value=1)
        self.dc.init(self.dc.OUT, value=0)
        self.rst.init(self.rst.OUT, value=1)

        self.reset()
        # Send initialization commands
        self.write_cmd(self.SET_COMMAND_LOCK, self.COMMANDS_UNLOCK)
        self.write_cmd(self.DISPLAY_SLEEP_ON)
        # Set clock at 80 frames per second
        self.write_cmd(self.SET_FRONT_CLOCK_DIVIDER, 0x91)
        # Set multiplex ratio to 1/64
        self.write_cmd(self.SET_MULTIPLEX_RATIO, 0x3F)
        self.write_cmd(self.SET_DISPLAY_OFFSET, 0x00)
        self.write_cmd(self.SET_DISPLAY_START_LINE, 0x00)
        # Column address 0 mapped to SEG0
        # Disable nibble remap
        # Scan from COM[N-1] to C0M0
        # Disable COM split between odd and even
        # Enable dual COM line mode
        self.write_cmd(self.SET_REMAP_DUAL_COM_LINE_MODE, 0x14, 0x11)  # 10.1.6
        # Disable GPIO pins input
        self.write_cmd(self.SET_GPIO, 0x00)
        # Enable internal VDD regulator
        self.write_cmd(self.SET_FUNCTION_SELECTION, 0x01)
        # Enable external VSL
        self.write_cmd(self.DISPLAY_ENHANCEMENT_A,
                       self.ENABLE_EXTERNAL_VSL | 0xA0,
                       self.ENHANCED_LOW_GRAY_SCALE_QUALITY | 0x05)
        # Set segment output current
        self.write_cmd(self.SET_CONTRAST_CURRENT, 0x9F)
        # Set scale factor of segment output current control
        self.write_cmd(self.MASTER_CURRENT_CONTROL, 0x0F)
        # Set default linear gray scale table
        self.write_cmd(self.SELECT_DEFAULT_LINEAR_GRAY_SCALE_TABLE)
        # Set phase 1 as 5 clocks and phase 2 as 14 clocks
        self.write_cmd(self.SET_PHASE_LENGTH, 0xE2)
        # Enhance driving scheme capability
        self.write_cmd(self.DISPLAY_ENHANCEMENT_B,
                       self.RESERVED_ENHANCEMENT | 0xA2, 0x20)
        # Set pre-charge voltage level as 0.60 * VCC
        self.write_cmd(self.SET_PRECHARGE_VOLTAGE, 0x1F)
        # Set second pre-charge period as 8 clocks
        self.write_cmd(self.SET_SECOND_PRECHARGE_PERIOD, 0x08)
        # Set common pin deselect voltage as 0.86 * VCC
        self.write_cmd(self.SET_VCOMH_VOLTAGE, 0x07)
        # Normal display mode
        self.write_cmd(self.SET_DISPLAY_MODE_NORMAL)
        self.write_cmd(self.PARTIAL_DISPLAY_DISABLE)
        self.write_cmd(self.DISPLAY_SLEEP_OFF)

        self.clear_buffers()
        self.present()

    def cleanup(self):
        """Clean up resources."""
        self.clear()
        self.sleep()
        self.spi.deinit()
        print('display off')

    def clear(self):
        """Clear display."""
        self.clear_buffers()
        self.present()

    def clear_buffers(self, gs=0):
        """Clear buffer.

        Args:
            gs (int): Grayscale 0=Black to 15=White (default grayscale table)
        """
        self.gs4_fb.fill(gs)

    def draw_bitmap_GS4(self, path, x, y, w, h, invert=False, rotate=0):
        """Load GS4_HMSB bitmap from disc and draw to screen.

        Args:
            path (string): Image file path.
            x (int): x-coord of image.
            y (int): y-coord of image.
            w (int): Width of image.
            h (int): Height of image.
            invert (bool): True = invert image, False (Default) = normal image.
            rotate(int): 0, 90, 180, 270
        Notes:
            w x h cannot exceed 2048
        """
        array_size = w * h
        with open(path, "rb") as f:
            buf = bytearray(f.read(array_size))
            fb = FrameBuffer(buf, w, h, GS4_HMSB)
            if rotate == 0 and invert is False:
                self.gs4_fb.blit(fb, x, y)
            elif rotate == 0:  # 0 degrees
                for y1 in range(h):
                    for x1 in range(w):
                        self.gs4_fb.pixel(x1 + x, y1 + y,
                                          15 - fb.pixel(x1, y1))
            elif rotate == 90:  # 90 degrees
                for y1 in range(h):
                    for x1 in range(w):
                        if invert is True:
                            self.gs4_fb.pixel(y1 + x, x1 + y,
                                              15 - fb.pixel(x1, (h - 1) - y1))
                        else:
                            self.gs4_fb.pixel(y1 + x, x1 + y,
                                              fb.pixel(x1, (h - 1) - y1))
            elif rotate == 180:  # 180 degrees
                for y1 in range(h):
                    for x1 in range(w):
                        if invert is True:
                            self.gs4_fb.pixel(x1 + x, y1 + y,
                                              15 - fb.pixel((w - 1) - x1,
                                                            (h - 1) - y1))
                        else:
                            self.gs4_fb.pixel(x1 + x, y1 + y,
                                              fb.pixel((w - 1) - x1,
                                                       (h - 1) - y1))
            elif rotate == 270:  # 270 degrees
                for y1 in range(h):
                    for x1 in range(w):
                        if invert is True:
                            self.gs4_fb.pixel(y1 + x, x1 + y,
                                              15 - fb.pixel((w - 1) - x1, y1))
                        else:
                            self.gs4_fb.pixel(y1 + x, x1 + y,
                                              fb.pixel((w - 1) - x1, y1))

            # Clean up because this function can use a lot of memory
            del fb
            del buf

    def draw_bitmap_mono(self, path, x, y, w, h, invert=False,
                         gs=15, rotate=0):
        """Load MONO_HMSB bitmap from disc and draw to screen.

        Args:
            path (string): Image file path.
            x (int): x-coord of image.
            y (int): y-coord of image.
            w (int): Width of image.
            h (int): Height of image.
            invert (bool): True = invert image, False (Default) = normal image.
            gs (int): Grayscale 0=Black to 15=White (default grayscale table)
            rotate(int): 0, 90, 180, 270
        Notes:
            w x h cannot exceed 2048
        """
        GSMAP = ((0, 15), (15, 0))
        array_size = w * h
        with open(path, "rb") as f:
            buf = bytearray(f.read(array_size))
            fb = FrameBuffer(buf, w, h, MONO_HMSB)

            if rotate == 0:  # 0 degrees (can you blit for better speed)
                if invert:
                    self.palette.bg(gs)
                    self.palette.fg(0)
                else:
                    self.palette.bg(0)
                    self.palette.fg(gs)
                self.gs4_fb.blit(fb, x, y, -1, self.palette)
            elif rotate == 90:  # 90 degrees
                for y1 in range(h):
                    for x1 in range(w):
                        self.gs4_fb.pixel(y1 + x, x1 + y,
                                          GSMAP[fb.pixel(x1,
                                                         (h - 1) - y1)]
                                               [invert])
            elif rotate == 180:  # 180 degrees
                for y1 in range(h):
                    for x1 in range(w):
                        self.gs4_fb.pixel(x1 + x, y1 + y,
                                          GSMAP[fb.pixel((w - 1) - x1,
                                                         (h - 1) - y1)]
                                               [invert])
            elif rotate == 270:  # 270 degrees
                for y1 in range(h):
                    for x1 in range(w):
                        self.gs4_fb.pixel(y1 + x, x1 + y,
                                          GSMAP[fb.pixel((w - 1) - x1,
                                                         y1)]
                                               [invert])
            # Clean up because this function can use a lot of memory
            del fb
            del buf

    def draw_bitmap_raw(self, path, x, y, w, h, invert=False, rotate=0):
        """Load raw bitmap from disc and draw to screen.

        Args:
            path (string): Image file path.
            x (int): x-coord of image.
            y (int): y-coord of image.
            w (int): Width of image.
            h (int): Height of image.
            invert (bool): True = invert image, False (Default) = normal image.
            rotate(int): 0, 90, 180, 270
        Notes:
            w x h cannot exceed 2048
        """
        if rotate == 90 or rotate == 270:
            w, h = h, w  # Swap width & height if landscape

        buf_size = w * h
        with open(path, "rb") as f:
            if rotate == 0:
                buf = bytearray(f.read(buf_size))
            elif rotate == 90:
                buf = bytearray(buf_size)
                for x1 in range(w - 1, -1, -1):
                    for y1 in range(h):
                        index = (w * y1) + x1
                        buf[index] = f.read(1)[0]
            elif rotate == 180:
                buf = bytearray(buf_size)
                for index in range(buf_size - 1, -1, -1):
                    buf[index] = f.read(1)[0]
            elif rotate == 270:
                buf = bytearray(buf_size)
                for x1 in range(1, w + 1):
                    for y1 in range(h - 1, -1, -1):
                        index = (w * y1) + x1 - 1
                        buf[index] = f.read(1)[0]
            if invert:
                for i, _ in enumerate(buf):
                    buf[i] ^= 0xFF

            fbuf = FrameBuffer(buf, w, h, GS8)
            self.gs4_fb.blit(fbuf, x, y)

    def draw_circle(self, x0, y0, r, gs=15):
        """Draw a circle.

        Args:
            x0 (int): X coordinate of center point.
            y0 (int): Y coordinate of center point.
            r (int): Radius.
            gs (int): Grayscale 0=Black to 15=White (default grayscale table)
        """
        f = 1 - r
        dx = 1
        dy = -r - r
        x = 0
        y = r
        self.draw_pixel(x0, y0 + r, gs)
        self.draw_pixel(x0, y0 - r, gs)
        self.draw_pixel(x0 + r, y0, gs)
        self.draw_pixel(x0 - r, y0, gs)
        while x < y:
            if f >= 0:
                y -= 1
                dy += 2
                f += dy
            x += 1
            dx += 2
            f += dx
            self.draw_pixel(x0 + x, y0 + y, gs)
            self.draw_pixel(x0 - x, y0 + y, gs)
            self.draw_pixel(x0 + x, y0 - y, gs)
            self.draw_pixel(x0 - x, y0 - y, gs)
            self.draw_pixel(x0 + y, y0 + x, gs)
            self.draw_pixel(x0 - y, y0 + x, gs)
            self.draw_pixel(x0 + y, y0 - x, gs)
            self.draw_pixel(x0 - y, y0 - x, gs)

    def draw_ellipse(self, x0, y0, a, b, gs=15):
        """Draw an ellipse.

        Args:
            x0, y0 (int): Coordinates of center point.
            a (int): Semi axis horizontal.
            b (int): Semi axis vertical.
            gs (int): Grayscale 0=Black to 15=White (default grayscale table)
        Note:
            The center point is the center of the x0,y0 pixel.
            Since pixels are not divisible, the axes are integer rounded
            up to complete on a full pixel.  Therefore the major and
            minor axes are increased by 1.
        """
        a2 = a * a
        b2 = b * b
        twoa2 = a2 + a2
        twob2 = b2 + b2
        x = 0
        y = b
        px = 0
        py = twoa2 * y
        # Plot initial points
        self.draw_pixel(x0 + x, y0 + y, gs)
        self.draw_pixel(x0 - x, y0 + y, gs)
        self.draw_pixel(x0 + x, y0 - y, gs)
        self.draw_pixel(x0 - x, y0 - y, gs)
        # Region 1
        p = round(b2 - (a2 * b) + (0.25 * a2))
        while px < py:
            x += 1
            px += twob2
            if p < 0:
                p += b2 + px
            else:
                y -= 1
                py -= twoa2
                p += b2 + px - py
            self.draw_pixel(x0 + x, y0 + y, gs)
            self.draw_pixel(x0 - x, y0 + y, gs)
            self.draw_pixel(x0 + x, y0 - y, gs)
            self.draw_pixel(x0 - x, y0 - y, gs)
        # Region 2
        p = round(b2 * (x + 0.5) * (x + 0.5) +
                  a2 * (y - 1) * (y - 1) - a2 * b2)
        while y > 0:
            y -= 1
            py -= twoa2
            if p > 0:
                p += a2 - py
            else:
                x += 1
                px += twob2
                p += a2 - py + px
            self.draw_pixel(x0 + x, y0 + y, gs)
            self.draw_pixel(x0 - x, y0 + y, gs)
            self.draw_pixel(x0 + x, y0 - y, gs)
            self.draw_pixel(x0 - x, y0 - y, gs)

    def draw_hline(self, x, y, w, gs=15):
        """Draw a horizontal line.

        Args:
            x (int): Starting X position.
            y (int): Starting Y position.
            w (int): Width of line.
            gs (int): Grayscale 0=Black to 15=White (default grayscale table)
        """
        if self.is_off_grid(x, y, x + w - 1, y):
            return
        self.gs4_fb.hline(x, y, w, gs)

    def draw_letter(self, x, y, letter, font,
                    invert=False, gs=15, rotate=False):
        """Draw a letter.

        Args:
            x (int): Starting X position.
            y (int): Starting Y position.
            letter (string): Letter to draw.
            font (XglcdFont object): Font.
            invert (bool): Invert Font.
            gs (int): Grayscale 0=Black to 15=White (default grayscale table)
            rotate (int): Rotation of letter
        """
        fb, w, h = font.get_letter(letter, rotate=rotate)
        # Check for errors
        if w == 0:
            return w, h
        # Offset y for 270 degrees and x for 180 degrees
        if rotate == 180:
            x -= w
        elif rotate == 270:
            y -= h

        if invert:
            self.palette.bg(gs)
            self.palette.fg(0)
        else:
            self.palette.bg(0)
            self.palette.fg(gs)
        self.gs4_fb.blit(fb, x, y, -1, self.palette)

        return w, h

    def draw_line(self, x1, y1, x2, y2, gs=15):
        """Draw a line using Bresenham's algorithm.

        Args:
            x1, y1 (int): Starting coordinates of the line
            x2, y2 (int): Ending coordinates of the line
            gs (int): Grayscale 0=Black to 15=White (default grayscale table)
        """
        # Check for horizontal line
        if y1 == y2:
            if x1 > x2:
                x1, x2 = x2, x1
            self.draw_hline(x1, y1, x2 - x1 + 1, gs)
            return
        # Check for vertical line
        if x1 == x2:
            if y1 > y2:
                y1, y2 = y2, y1
            self.draw_vline(x1, y1, y2 - y1 + 1, gs)
            return
        # Confirm coordinates in boundary
        if self.is_off_grid(min(x1, x2), min(y1, y2),
                            max(x1, x2), max(y1, y2)):
            return
        self.gs4_fb.line(x1, y1, x2, y2, gs)

    def draw_lines(self, coords, gs=15):
        """Draw multiple lines.

        Args:
            coords ([[int, int],...]): Line coordinate X, Y pairs
            gs (int): Grayscale 0=Black to 15=White (default grayscale table)
        """
        # Starting point
        x1, y1 = coords[0]
        # Iterate through coordinates
        for i in range(1, len(coords)):
            x2, y2 = coords[i]
            self.draw_line(x1, y1, x2, y2, gs)
            x1, y1 = x2, y2

    def draw_pixel(self, x, y, gs=15):
        """Draw a single pixel.

        Args:
            x (int): X position.
            y (int): Y position.
            gs (int): Grayscale 0=Black to 15=White (default grayscale table)
        """
        if self.is_off_grid(x, y, x, y):
            return
        self.gs4_fb.pixel(x, y, gs)

    def draw_polygon(self, sides, x0, y0, r, gs=15, rotate=0):
        """Draw an n-sided regular polygon.

        Args:
            sides (int): Number of polygon sides.
            x0, y0 (int): Coordinates of center point.
            r (int): Radius.
            gs (int): Grayscale 0=Black to 15=White (default grayscale table)
            rotate (Optional float): Rotation in degrees relative to origin.
        Note:
            The center point is the center of the x0,y0 pixel.
            Since pixels are not divisible, the radius is integer rounded
            up to complete on a full pixel.  Therefore diameter = 2 x r + 1.
        """
        coords = []
        theta = radians(rotate)
        n = sides + 1
        for s in range(n):
            t = 2.0 * pi * s / sides + theta
            coords.append([int(r * cos(t) + x0), int(r * sin(t) + y0)])

        # Cast to python float first to fix rounding errors
        self.draw_lines(coords, gs)

    def draw_rectangle(self, x, y, w, h, gs=15):
        """Draw a rectangle.

        Args:
            x (int): Starting X position.
            y (int): Starting Y position.
            w (int): Width of rectangle.
            h (int): Height of rectangle.
            gs (int): Grayscale 0=Black to 15=White (default grayscale table)
        """
        self.gs4_fb.rect(x, y, w, h, gs)

    def draw_sprite(self, fb, x, y, w, h, invert=False, gs=15):
        """Draw a sprite.
        Args:
            fb (FrameBuffer): Buffer to draw.
            x (int): Starting X position.
            y (int): Starting Y position.
            w (int): Width of drawing.
            h (int): Height of drawing.
            invert (bool): Invert color
            gs (int): Grayscale 0=Black to 15=White (default grayscale table)
        """
        x2 = x + w - 1
        y2 = y + h - 1
        if self.is_off_grid(x, y, x2, y2):
            return

        if invert:
            self.palette.bg(gs)
            self.palette.fg(0)
        else:
            self.palette.bg(0)
            self.palette.fg(gs)
        self.gs4_fb.blit(fb, x, y, -1, self.palette)

    def draw_text(self, x, y, text, font, invert=False, gs=15,
                  rotate=0, spacing=1):
        """Draw text.

        Args:
            x (int): Starting X position.
            y (int): Starting Y position.
            text (string): Text to draw.
            font (XglcdFont object): Font.
            gs (int): Grayscale 0=Black to 15=White (default grayscale table)
            invert (bool): Invert color
            rotate (int): Rotation of letter
            spacing (int): Pixels between letters (default: 1)
        """
        GSMAP = (0, gs)
        for letter in text:
            # Get letter array and letter dimensions
            w, h = self.draw_letter(x, y, letter, font, invert, gs, rotate)
            # Stop on error
            if w == 0 or h == 0:
                return
            if rotate == 0:
                # Fill in spacing
                if spacing:
                    self.fill_rectangle(x + w, y, spacing, h, GSMAP[invert])
                # Position x for next letter
                x += (w + spacing)
            elif rotate == 90:
                # Fill in spacing
                if spacing:
                    self.fill_rectangle(x, y + h, w, spacing, GSMAP[invert])
                # Position y for next letter
                y += (h + spacing)
            elif rotate == 180:
                # Fill in spacing
                if spacing:
                    self.fill_rectangle(x - w - spacing, y, spacing, h,
                                        GSMAP[invert])
                # Position x for next letter
                x -= (w + spacing)
            elif rotate == 270:
                # Fill in spacing
                if spacing:
                    self.fill_rectangle(x, y - h - spacing, w, spacing,
                                        GSMAP[invert])
                # Position y for next letter
                y -= (h + spacing)
            else:
                print("Invalid rotation.")
                return

    def draw_text8x8(self, x, y, text, gs=15):
        """Draw text using built-in MicroPython 8x8 bit font.

        Args:
            x (int): Starting X position.
            y (int): Starting Y position.
            text (string): Text to draw.
            gs (int): Grayscale 0=Black to 15=White (default grayscale table)
        """
        # Confirm coordinates in boundary
        if self.is_off_grid(x, y, x + 8, y + 8):
            return
        self.gs4_fb.text(text, x, y, gs)

    def draw_vline(self, x, y, h, gs=15):
        """Draw a vertical line.

        Args:
            x (int): Starting X position.
            y (int): Starting Y position.
            h (int): Height of line.
            gs (int): Grayscale 0=Black to 15=White (default grayscale table)
        """
        # Confirm coordinates in boundary
        if self.is_off_grid(x, y, x, y + h):
            return
        self.gs4_fb.vline(x, y, h, gs)

    def fill_circle(self, x0, y0, r, gs=15):
        """Draw a filled circle.

        Args:
            x0 (int): X coordinate of center point.
            y0 (int): Y coordinate of center point.
            r (int): Radius.
            gs (int): Grayscale 0=Black to 15=White (default grayscale table)
        """
        f = 1 - r
        dx = 1
        dy = -r - r
        x = 0
        y = r
        self.draw_vline(x0, y0 - r, 2 * r + 1, gs)
        while x < y:
            if f >= 0:
                y -= 1
                dy += 2
                f += dy
            x += 1
            dx += 2
            f += dx
            self.draw_vline(x0 + x, y0 - y, 2 * y + 1, gs)
            self.draw_vline(x0 - x, y0 - y, 2 * y + 1, gs)
            self.draw_vline(x0 - y, y0 - x, 2 * x + 1, gs)
            self.draw_vline(x0 + y, y0 - x, 2 * x + 1, gs)

    def fill_ellipse(self, x0, y0, a, b, gs=15):
        """Draw a filled ellipse.

        Args:
            x0, y0 (int): Coordinates of center point.
            a (int): Semi axis horizontal.
            b (int): Semi axis vertical.
            gs (int): Grayscale 0=Black to 15=White (default grayscale table)
        Note:
            The center point is the center of the x0,y0 pixel.
            Since pixels are not divisible, the axes are integer rounded
            up to complete on a full pixel.  Therefore the major and
            minor axes are increased by 1.
        """
        a2 = a * a
        b2 = b * b
        twoa2 = a2 + a2
        twob2 = b2 + b2
        x = 0
        y = b
        px = 0
        py = twoa2 * y
        # Plot initial points
        self.draw_line(x0, y0 - y, x0, y0 + y, gs)
        # Region 1
        p = round(b2 - (a2 * b) + (0.25 * a2))
        while px < py:
            x += 1
            px += twob2
            if p < 0:
                p += b2 + px
            else:
                y -= 1
                py -= twoa2
                p += b2 + px - py
            self.draw_line(x0 + x, y0 - y, x0 + x, y0 + y, gs)
            self.draw_line(x0 - x, y0 - y, x0 - x, y0 + y, gs)
        # Region 2
        p = round(b2 * (x + 0.5) * (x + 0.5) +
                  a2 * (y - 1) * (y - 1) - a2 * b2)
        while y > 0:
            y -= 1
            py -= twoa2
            if p > 0:
                p += a2 - py
            else:
                x += 1
                px += twob2
                p += a2 - py + px
            self.draw_line(x0 + x, y0 - y, x0 + x, y0 + y, gs)
            self.draw_line(x0 - x, y0 - y, x0 - x, y0 + y, gs)

    def fill_rectangle(self, x, y, w, h, gs=15):
        """Draw a filled rectangle.

        Args:
            x (int): Starting X position.
            y (int): Starting Y position.
            w (int): Width of rectangle.
            h (int): Height of rectangle.
            gs (int): Grayscale 0=Black to 15=White (default grayscale table)
        """
        if self.is_off_grid(x, y, x + w - 1, y + h - 1):
            return
        self.gs4_fb.fill_rect(x, y, w, h, gs)

    def fill_polygon(self, sides, x0, y0, r, gs=15, rotate=0):
        """Draw a filled n-sided regular polygon.

        Args:
            sides (int): Number of polygon sides.
            x0, y0 (int): Coordinates of center point.
            r (int): Radius.
            gs (int): Grayscale 0=Black to 15=White (default grayscale table)
            rotate (Optional float): Rotation in degrees relative to origin.
        Note:
            The center point is the center of the x0,y0 pixel.
            Since pixels are not divisible, the radius is integer rounded
            up to complete on a full pixel.  Therefore diameter = 2 x r + 1.
        """
        # Determine side coordinates
        coords = []
        theta = radians(rotate)
        n = sides + 1
        for s in range(n):
            t = 2.0 * pi * s / sides + theta
            coords.append([int(r * cos(t) + x0), int(r * sin(t) + y0)])
        # Starting point
        x1, y1 = coords[0]
        # Minimum Maximum X dict
        xdict = {y1: [x1, x1]}
        # Iterate through coordinates
        for row in coords[1:]:
            x2, y2 = row
            xprev, yprev = x2, y2
            # Calculate perimeter
            # Check for horizontal side
            if y1 == y2:
                if x1 > x2:
                    x1, x2 = x2, x1
                if y1 in xdict:
                    xdict[y1] = [min(x1, xdict[y1][0]), max(x2, xdict[y1][1])]
                else:
                    xdict[y1] = [x1, x2]
                x1, y1 = xprev, yprev
                continue
            # Non horizontal side
            # Changes in x, y
            dx = x2 - x1
            dy = y2 - y1
            # Determine how steep the line is
            is_steep = abs(dy) > abs(dx)
            # Rotate line
            if is_steep:
                x1, y1 = y1, x1
                x2, y2 = y2, x2
            # Swap start and end points if necessary
            if x1 > x2:
                x1, x2 = x2, x1
                y1, y2 = y2, y1
            # Recalculate differentials
            dx = x2 - x1
            dy = y2 - y1
            # Calculate error
            error = dx >> 1
            ystep = 1 if y1 < y2 else -1
            y = y1
            # Calcualte minimum and maximum x values
            for x in range(x1, x2 + 1):
                if is_steep:
                    if x in xdict:
                        xdict[x] = [min(y, xdict[x][0]), max(y, xdict[x][1])]
                    else:
                        xdict[x] = [y, y]
                else:
                    if y in xdict:
                        xdict[y] = [min(x, xdict[y][0]), max(x, xdict[y][1])]
                    else:
                        xdict[y] = [x, x]
                error -= abs(dy)
                if error < 0:
                    y += ystep
                    error += dx
            x1, y1 = xprev, yprev
        # Fill polygon
        for y, x in xdict.items():
            self.draw_hline(x[0], y, x[1] - x[0] + 2, gs)

    def is_off_grid(self, xmin, ymin, xmax, ymax):
        """Check if coordinates extend past display boundaries.

        Args:
            xmin (int): Minimum horizontal pixel.
            ymin (int): Minimum vertical pixel.
            xmax (int): Maximum horizontal pixel.
            ymax (int): Maximum vertical pixel.
        Returns:
            boolean: False = Coordinates OK, True = Error.
        """
        if xmin < 0:
            print('x-coordinate: {0} below minimum of 0.'.format(xmin))
            return True
        if ymin < 0:
            print('y-coordinate: {0} below minimum of 0.'.format(ymin))
            return True
        if xmax >= self.width:
            print('x-coordinate: {0} above maximum of {1}.'.format(
                xmax, self.width - 1))
            return True
        if ymax >= self.height:
            print('y-coordinate: {0} above maximum of {1}.'.format(
                ymax, self.height - 1))
            return True
        return False

    def load_sprite(self, path, w, h, invert=False, rotate=0):
        """Load MONO_HMSB bitmap from disc to sprite.

        Args:
            path (string): Image file path.
            w (int): Width of image.
            h (int): Height of image.
            invert (bool): True = invert image, False (Default) = normal image.
            rotate(int): 0, 90, 180, 270
        Notes:
            w x h cannot exceed 2048
        """
        array_size = w * h
        with open(path, "rb") as f:
            buf = bytearray(f.read(array_size))
            fb = FrameBuffer(buf, w, h, MONO_HMSB)

            if rotate == 0 and invert is True:  # 0 degrees
                fb2 = FrameBuffer(bytearray(array_size), w, h, MONO_HMSB)
                for y1 in range(h):
                    for x1 in range(w):
                        fb2.pixel(x1, y1, fb.pixel(x1, y1) ^ 0x01)
                fb = fb2
            elif rotate == 90:  # 90 degrees
                byte_width = (w - 1) // 8 + 1
                adj_size = h * byte_width
                fb2 = FrameBuffer(bytearray(adj_size), h, w, MONO_HMSB)
                for y1 in range(h):
                    for x1 in range(w):
                        if invert is True:
                            fb2.pixel(y1, x1,
                                      fb.pixel(x1, (h - 1) - y1) ^ 0x01)
                        else:
                            fb2.pixel(y1, x1, fb.pixel(x1, (h - 1) - y1))
                fb = fb2
            elif rotate == 180:  # 180 degrees
                fb2 = FrameBuffer(bytearray(array_size), w, h, MONO_HMSB)
                for y1 in range(h):
                    for x1 in range(w):
                        if invert is True:
                            fb2.pixel(x1, y1, fb.pixel((w - 1) - x1,
                                                       (h - 1) - y1) ^ 0x01)
                        else:
                            fb2.pixel(x1, y1,
                                      fb.pixel((w - 1) - x1, (h - 1) - y1))
                fb = fb2
            elif rotate == 270:  # 270 degrees
                byte_width = (w - 1) // 8 + 1
                adj_size = h * byte_width
                fb2 = FrameBuffer(bytearray(adj_size), h, w, MONO_HMSB)
                for y1 in range(h):
                    for x1 in range(w):
                        if invert is True:
                            fb2.pixel(y1, x1,
                                      fb.pixel((w - 1) - x1, y1) ^ 0x01)
                        else:
                            fb2.pixel(y1, x1, fb.pixel((w - 1) - x1, y1))
                fb = fb2

            return fb

    def present(self):
        """Present image to display.
        """
        x0 = 0
        x1 = self.width // 4 - 1  # 2 bytes per address, 2 pixels per byte
        y0 = 0
        y1 = self.height - 1
        self.set_address(x0, y0, x1, y1)
        self.write_data(self.gs4_buf)

    def reset(self):
        """Perform reset."""
        self.rst(0)
        sleep_ms(50)
        self.rst(1)
        sleep_ms(100)

    def set_address(self, x0, y0, x1, y1, offset=28):
        """Set column and row addresses.

        Args:
            x0 (byte): Starting X address
            y0 (byte): Starting Y address
            x1 (byte): Ending X address
            y1 (byte): Ending Y address
            offset (byte): Horizontal offset (Default 28)
        Note:
            There is a horizontal offset of 28 (pixels start from segment 112)
        """
        self.set_column_address(x0 + offset, x1 + offset)
        self.set_row_address(y0, y1)
        self.write_cmd(self.WRITE_RAM)

    def set_column_address(self, column_start, column_end):
        """Set column start and end address of display data RAM.

        Args:
            column_start (byte): Start column
            column_end (byte): End column
        """
        self.write_cmd(self.SET_COLUMN_ADDRESS, column_start, column_end)

    def set_display_enhancement_a(self, external_vsl=True,
                                  enhanced_gs_quality=True):
        """Enhance the display performance A.

        Args:
            external_vsl (bool): True (Default)=External, False=Internal
            enhanced_gs_quality (bool): True (Default)=Enhanced, False=Normal
        """
        if external_vsl:
            vsl = self.ENABLE_EXTERNAL_VSL
        else:
            vsl = self.ENABLE_INTERNAL_VSL

        if enhanced_gs_quality:
            enhanced_gs = self.ENHANCED_LOW_GRAY_SCALE_QUALITY
        else:
            enhanced_gs = self.NORMAL_GRAYSCALE_QUALITY

        self.write_cmd(self.DISPLAY_ENHANCEMENT_A,
                       vsl | 0xA0,
                       enhanced_gs | 0x05)

    def set_display_enhancement_b(self, enhanced=True):
        """Enhance the display performance B.

        Args:
            enhance (bool): True (Default)=Recommended, False=Normal
        """
        if enhanced:
            deb = self.RESERVED_ENHANCEMENT
        else:
            deb = self.NORMAL_ENHANCEMENT

        self.write_cmd(self.DISPLAY_ENHANCEMENT_B,
                       deb | 0x82,
                       0x20)

    def set_row_address(self, row_start, row_end):
        """Set row start and end address of display data RAM.

        Args:
            row_start (byte): Start row
            row_end (byte): End row
        """
        self.write_cmd(self.SET_ROW_ADDRESS, row_start, row_end)

    def sleep(self):
        """Put display to sleep."""
        self.write_cmd(self.DISPLAY_SLEEP_ON)

    def wake(self):
        """Wake display from sleep."""
        self.write_cmd(self.DISPLAY_SLEEP_OFF)

    def write_cmd(self, command, *args):
        """Write command to display.

        Args:
            command (byte): Display command code.
            *args (optional bytes): Data to transmit.
        """
        self.dc(0)
        self.cs(0)
        self.spi.write(bytearray([command]))
        self.cs(1)
        # Handle any passed data
        if len(args) > 0:
            self.write_data(bytearray(args))

    def write_data(self, data):
        """Write data to display.

        Args:
            data (bytes): Data to transmit.
        """
        self.dc(1)
        self.cs(0)
        self.spi.write(data)
        self.cs(1)
