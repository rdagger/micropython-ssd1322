"""SSD1322 demo (bouncing boxes)."""
from machine import Pin, SPI  # type: ignore
from random import random, seed
from ssd1322 import Display
from utime import sleep_us, ticks_cpu, ticks_us, ticks_diff  # type: ignore


class Box(object):
    """Bouncing box."""

    def __init__(self, screen_width, screen_height, size, display):
        """Initialize box.
        Args:
            screen_width (int): Width of screen.
            screen_height (int): Width of height.
            size (int): Square side length.
            display (SSD1351): OLED display object.
        """
        self.size = size
        self.w = screen_width
        self.h = screen_height
        self.display = display

        # Generate non-zero random speeds between -5.0 and 5.0
        r = random() * 10.0
        self.x_speed = 5.0 - r if r < 5.0 else r - 10.0
        r = random() * 10.0
        self.y_speed = 5.0 - r if r < 5.0 else r - 10.0
        # Generate random gray scale coloring
        r = random() * 14 + 1
        self.gs = int(r)

        self.x = self.w / 2.0
        self.y = self.h / 2.0
        self.prev_x = self.x
        self.prev_y = self.y

    def update_pos(self):
        """Update box position and speed."""
        x = self.x
        y = self.y
        size = self.size
        w = self.w
        h = self.h
        x_speed = abs(self.x_speed)
        y_speed = abs(self.y_speed)
        self.prev_x = x
        self.prev_y = y

        if x + size >= w - x_speed:
            self.x_speed = -x_speed
        elif x - size <= x_speed + 1:
            self.x_speed = x_speed

        if y + size >= h - y_speed:
            self.y_speed = -y_speed
        elif y - size <= y_speed + 1:
            self.y_speed = y_speed

        self.x = x + self.x_speed
        self.y = y + self.y_speed

    def draw(self):
        """Draw box."""
        x = int(self.x)
        y = int(self.y)
        size = self.size
        prev_x = int(self.prev_x)
        prev_y = int(self.prev_y)
        self.display.fill_rectangle(prev_x - size,
                                    prev_y - size,
                                    size, size, gs=0)
        self.display.fill_rectangle(x - size,
                                    y - size,
                                    size, size, gs=self.gs)
        self.display.present()


def test():
    """Bouncing box."""
    try:
        spi = SPI(0, baudrate=25000000, sck=Pin(18), mosi=Pin(19))
        display = Display(spi, dc=Pin(20), cs=Pin(17), rst=Pin(21))
        display.clear()

        sizes = [12, 9, 8, 6, 5, 4]
        seed(ticks_cpu())
        boxes = [Box(256, 64, sizes[i], display) for i in range(6)]

        while True:
            timer = ticks_us()
            for b in boxes:
                b.update_pos()
                b.draw()
            # Attempt to set framerate to 30 FPS
            timer_dif = 33333 - ticks_diff(ticks_us(), timer)
            if timer_dif > 0:
                sleep_us(timer_dif)

    except KeyboardInterrupt:
        display.cleanup()


test()
