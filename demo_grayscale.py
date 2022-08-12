"""SSD1322 demo (grayscale)."""
from time import sleep
from machine import Pin, SPI  # type: ignore
from ssd1322 import Display


def test():
    """Test code."""
    spi = SPI(0, baudrate=25000000, sck=Pin(18), mosi=Pin(19))
    display = Display(spi, dc=Pin(20), cs=Pin(17), rst=Pin(21))

    for x in range(0, 256, 16):
        background = x // 16
        foreground = 15 - background
        display.fill_rectangle(x, 0, 16, 64, background)
        label = str(background)
        x2 = x + 4 if len(label) == 1 else x
        display.draw_text8x8(x2, 28, label, foreground)

    display.present()

    sleep(15)
    display.cleanup()
    print('Done.')


test()
