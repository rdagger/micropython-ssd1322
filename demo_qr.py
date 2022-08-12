"""SSD1322 demo (QR Code)."""
from time import sleep
from machine import Pin, SPI  # type: ignore
from ssd1322 import Display
from xglcd_font import XglcdFont
from uQR import QRCode


def test():
    """Test code."""
    spi = SPI(0, baudrate=25000000, sck=Pin(18), mosi=Pin(19))
    display = Display(spi, dc=Pin(20), cs=Pin(17), rst=Pin(21))

    neato = XglcdFont('fonts/NeatoReduced5x7.c', 5, 7)

    # Initialize QR code
    qr = QRCode()
    qr.add_data('https://www.rototron.info')
    matrix = qr.get_matrix()

    # Draw QR code to display
    for y in range(len(matrix)):
        for x in range(len(matrix[0])):
            gs = 6 if matrix[int(y)][int(x)] else 0
            display.draw_pixel(x + 30, y + 10, gs) 

    # Draw caption
    display.draw_text(0, 56, "www.rototron.info", neato)

    display.present()

    sleep(10)
    display.cleanup()
    print('Done.')


test()
