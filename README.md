# MicroPython Display Driver for SSD1322 Grayscale OLED
The library supports drawing lines, shapes, text, sprites and images.  All code is documented and there are demo examples.  Tested on 5.5 inch green OLED display SPI module with 256x64 resolution using Raspberry Pi Pico W.

Sample XGLCD fonts are included in the fonts folder.  Additional fonts can generated from TTF fonts using a free utility called MikroElektronika [GLCD Font Creator](https://www.mikroe.com/glcd-font-creator).

There are sample images in monocrhome (monoHMSB) and grayscale (GS4) format.  I’ve included python apps in the utils folder to convert images in common formats such as JPEG and PNG to monoHMSB and GS4.

demo_images.py example draws monochrome and grayscale images:

![Clovers2](https://user-images.githubusercontent.com/106355/184423207-1d61f55c-17f1-47bb-a7bb-2b1c0c019024.JPG)

Please note the horizontal bands in the pictures are due to filming issues:

![Faces](https://user-images.githubusercontent.com/106355/184423230-60b559da-0b67-493a-b81a-a1f4c4926f49.JPG)


demo_fonts.py example:

![Fonts](https://user-images.githubusercontent.com/106355/184423316-ede48e21-9a62-48b0-a566-a59ea09d9a3e.JPG)


demo_grayscale.py example draws 16 different shades of gray:

![Grayscale](https://user-images.githubusercontent.com/106355/184423419-bccafb6b-f3db-4814-8516-1f28a76da975.png)


demo_qr.py example draws a QR code which is readable by phones, tablets and webcams:

![QR Code](https://user-images.githubusercontent.com/106355/184423549-ce90bbda-57bd-4ea9-b697-d8067ce0c18d.JPG)


demo_shapes.py example:

![Shapes](https://user-images.githubusercontent.com/106355/184427925-70d99f23-e648-4cd6-973a-81b0ab498f93.JPG)


