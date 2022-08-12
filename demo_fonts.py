"""SSD1322 demo (fonts)."""
from time import sleep
from machine import Pin, SPI  # type: ignore
from xglcd_font import XglcdFont
from ssd1322 import Display


def test():
    """Test code."""
    spi = SPI(0, baudrate=25000000, sck=Pin(18), mosi=Pin(19))
    display = Display(spi, dc=Pin(20), cs=Pin(17), rst=Pin(21))

    print("Loading fonts.  Please wait.")
    bally = XglcdFont('fonts/Bally7x9.c', 7, 9)
    rototron = XglcdFont('fonts/Robotron13x21.c', 13, 21)
    unispace = XglcdFont('fonts/Unispace12x24.c', 12, 24)
    wendy = XglcdFont('fonts/Wendy7x8.c', 7, 8)

    print("Drawing fonts.")

    text_height = bally.height
    display.draw_text(display.width, display.height // 2 - text_height // 2,
                      "Bally", bally, rotate=180)

    text_width = rototron.measure_text("ROTOTRON")
    display.draw_text(display.width // 2 - text_width // 2, 0,
                      "ROTOTRON", rototron)

    text_width = unispace.measure_text("Unispace", spacing=3)
    text_height = unispace.height
    display.draw_text(display.width // 2 - text_width // 2,
                      display.height - text_height,
                      "Unispace", unispace, invert=True, spacing=3)

    text_width = wendy.measure_text("Wendy")
    display.draw_text(0, display.height // 2 - text_width // 2,
                      "Wendy", wendy, rotate=90)
    display.draw_text(15, display.height // 2 + text_width // 2,
                      "Wendy", wendy, rotate=270)

    pos = 50
    text_height = bally.height
    for c in range(1, 16):
        text_width = bally.measure_text(str(c))
        display.draw_text(pos, display.height // 2 - text_height, str(c),
                          bally, invert=True, gs=c)
        pos += text_width + 1

    display.present()

    sleep(15)
    display.cleanup()
    print('Done.')


test()
