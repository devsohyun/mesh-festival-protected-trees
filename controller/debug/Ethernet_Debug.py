import network
from machine import SPI, Pin
import time

spi = SPI(0, baudrate=2000000,
          mosi=Pin(19), miso=Pin(16), sck=Pin(18))

nic = network.WIZNET5K(spi, Pin(17), Pin(20))

# Hard reset
Pin(20, Pin.OUT).value(0)
time.sleep(0.5)
Pin(20, Pin.OUT).value(1)
time.sleep(0.5)

nic.active(True)
time.sleep(2)

print("Link:", nic.isconnected())
print("Config:", nic.ifconfig())