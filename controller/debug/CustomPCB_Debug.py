# ============================================================
# Protected Trees Explorer — Full Debug Script
# MicroPython / Thonny
# ============================================================

from machine import I2C, SPI, Pin
import time
import framebuf

# ------------------------------------------------------------
# SET THIS based on whether W5500 is connected to a router
# ------------------------------------------------------------
ROUTER_AVAILABLE = False

# ------------------------------------------------------------
# Pin definitions (corrected from schematic)
# ------------------------------------------------------------
PIN_SDA         = 2
PIN_SCL         = 3
PIN_CONFIRM_BTN = 5
PIN_ROT_A       = 6
PIN_ROT_B       = 7
PIN_ROT_BTN     = 8
PIN_MISO        = 16
PIN_CS          = 17
PIN_SCLK        = 18
PIN_MOSI        = 19
PIN_RST         = 20

# ------------------------------------------------------------
# Inline SSD1306 driver (no library needed)
# ------------------------------------------------------------
class SSD1306_I2C:
    def __init__(self, width, height, i2c, addr=0x3C):
        self.width = width
        self.height = height
        self.i2c = i2c
        self.addr = addr
        self.pages = height // 8
        self.buffer = bytearray(self.pages * width)
        self.framebuf = framebuf.FrameBuffer(self.buffer, width, height, framebuf.MONO_VLSB)
        self._init_display()

    def _cmd(self, cmd):
        self.i2c.writeto(self.addr, bytes([0x80, cmd]))

    def _init_display(self):
        for cmd in [0xAE, 0x20, 0x00, 0xA1, 0xC8, 0xDA, 0x12,
                    0x81, 0xFF, 0xA4, 0xA6, 0xD5, 0x80, 0x8D, 0x14, 0xAF]:
            self._cmd(cmd)

    def fill(self, col):
        self.framebuf.fill(col)

    def text(self, string, x, y, col=1):
        self.framebuf.text(string, x, y, col)

    def show(self):
        self._cmd(0x21); self._cmd(0); self._cmd(self.width - 1)
        self._cmd(0x22); self._cmd(0); self._cmd(self.pages - 1)
        self.i2c.writeto(self.addr, b'\x40' + self.buffer)

# ------------------------------------------------------------
# OLED helper
# ------------------------------------------------------------
def oled_show(line1="", line2="", line3="", line4=""):
    oled.fill(0)
    oled.text(line1[:16], 0, 0)
    oled.text(line2[:16], 0, 16)
    oled.text(line3[:16], 0, 32)
    oled.text(line4[:16], 0, 48)
    oled.show()

# ------------------------------------------------------------
# STEP 1 — OLED
# ------------------------------------------------------------
print("\n=== Protected Trees Debug ===")
print("Step 1: OLED...")

try:
    i2c = I2C(1, scl=Pin(PIN_SCL), sda=Pin(PIN_SDA), freq=400000)
    devices = i2c.scan()
    if 0x3C not in devices:
        print("OLED FAIL — not found on I2C scan:", devices)
        oled = None
    else:
        oled = SSD1306_I2C(128, 64, i2c)
        oled_show("Protected Trees", "Debug Mode", "OLED: OK")
        print("OLED OK")
except Exception as e:
    print("OLED ERROR:", e)
    oled = None

time.sleep(1)

# ------------------------------------------------------------
# STEP 2 — Buttons
# ------------------------------------------------------------
print("Step 2: Buttons...")
confirm_btn = Pin(PIN_CONFIRM_BTN, Pin.IN, Pin.PULL_UP)
rot_btn     = Pin(PIN_ROT_BTN,     Pin.IN, Pin.PULL_UP)

if oled:
    oled_show("Test Buttons", "Press CONFIRM", "and ROT BTN", "Ctrl+C to skip")

confirm_ok = False
rot_btn_ok = False
deadline = time.ticks_ms() + 10000  # 10 second window

print("Press both buttons within 10 seconds (Ctrl+C to skip)...")
try:
    while not (confirm_ok and rot_btn_ok):
        if time.ticks_diff(deadline, time.ticks_ms()) < 0:
            break
        if confirm_btn.value() == 0 and not confirm_ok:
            confirm_ok = True
            print("Confirm BTN: OK")
            if oled: oled_show("Confirm BTN", "OK!", "Now press", "ROT BTN")
            time.sleep(0.3)
        if rot_btn.value() == 0 and not rot_btn_ok:
            rot_btn_ok = True
            print("Rotary BTN: OK")
            if oled: oled_show("Rotary BTN", "OK!")
            time.sleep(0.3)
except KeyboardInterrupt:
    print("Buttons skipped")

print("Confirm BTN:", "OK" if confirm_ok else "NOT DETECTED")
print("Rotary BTN:", "OK" if rot_btn_ok else "NOT DETECTED")

# ------------------------------------------------------------
# STEP 3 — Rotary encoder
# ------------------------------------------------------------
print("Step 3: Rotary encoder — turn it within 10 seconds...")
if oled: oled_show("Test Encoder", "Turn it!", "", "Ctrl+C to skip")

rot_a    = Pin(PIN_ROT_A, Pin.IN, Pin.PULL_UP)
rot_b    = Pin(PIN_ROT_B, Pin.IN, Pin.PULL_UP)
last_a   = rot_a.value()
pos      = 0
enc_ok   = False
deadline = time.ticks_ms() + 10000

try:
    while not enc_ok:
        if time.ticks_diff(deadline, time.ticks_ms()) < 0:
            break
        a = rot_a.value()
        if a != last_a:
            pos += 1 if rot_b.value() != a else -1
            last_a = a
            enc_ok = True
            print("Rotary encoder: OK — position:", pos)
            if oled: oled_show("Encoder OK!", "Pos: " + str(pos))
except KeyboardInterrupt:
    print("Encoder skipped")

print("Rotary encoder:", "OK" if enc_ok else "NOT DETECTED")

# ------------------------------------------------------------
# STEP 4 — W5500
# ------------------------------------------------------------
print("Step 4: W5500 Ethernet...")

try:
    import network

    spi = SPI(0, baudrate=2000000,
              mosi=Pin(PIN_MOSI),
              miso=Pin(PIN_MISO),
              sck=Pin(PIN_SCLK))

    nic = network.WIZNET5K(spi, Pin(PIN_CS), Pin(PIN_RST))

    # Hard reset BEFORE active
    Pin(PIN_RST, Pin.OUT).value(0)
    time.sleep(0.5)
    Pin(PIN_RST, Pin.OUT).value(1)
    time.sleep(0.5)

    nic.active(True)
    time.sleep(2)

    if ROUTER_AVAILABLE:
        print("Connecting via DHCP...")
        if oled: oled_show("W5500", "DHCP...", "Please wait")

        nic.ifconfig("dhcp")
        timeout = time.ticks_ms() + 10000
        while not nic.isconnected():
            if time.ticks_diff(timeout, time.ticks_ms()) < 0:
                break
            print(".", end="")
            time.sleep(0.5)
        print()

        if nic.isconnected():
            ip = nic.ifconfig()[0]
            print("W5500 DHCP OK — IP:", ip)
            if oled: oled_show("W5500 OK!", "IP:", ip)
        else:
            print("W5500 DHCP FAILED — check cable/router")
            if oled: oled_show("W5500", "DHCP FAILED", "Check cable")
    else:
        link = nic.isconnected()
        print("W5500 SPI OK — link:", "UP" if link else "DOWN (no cable)")
        if oled: oled_show("W5500 SPI OK", "Link:", "UP" if link else "DOWN-no cable")

except Exception as e:
    print("W5500 ERROR:", e)
    if oled: oled_show("W5500 ERROR", str(e)[:16])

# ------------------------------------------------------------
# SUMMARY
# ------------------------------------------------------------
print("\n=== SUMMARY ===")
print("OLED:         ", "OK" if oled else "FAIL")
print("Confirm BTN:  ", "OK" if confirm_ok else "FAIL")
print("Rotary BTN:   ", "OK" if rot_btn_ok else "FAIL")
print("Rotary encoder:", "OK" if enc_ok else "FAIL")
print("(W5500 see above)")

if oled:
    oled_show(
        "OLED:" + ("OK" if oled else "FAIL"),
        "CONF:" + ("OK" if confirm_ok else "FAIL"),
        "ENC:" + ("OK" if enc_ok else "FAIL"),
        "W5500: see serial"
    )