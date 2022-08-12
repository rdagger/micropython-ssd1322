"""Palette for mono to GS4 blit."""
from framebuf import FrameBuffer, GS4_HMSB  # type: ignore


class MonoPalette(FrameBuffer):
    def __init__(self):
        buf = bytearray(1)
        super().__init__(buf, 2, 1, GS4_HMSB)
        self.fg(15)  # default foreground is white
        self.bg(0)  # default background is black

    def fg(self, color):  # Set foreground color
        self.pixel(1, 0, color)

    def bg(self, color):
        self.pixel(0, 0, color)
