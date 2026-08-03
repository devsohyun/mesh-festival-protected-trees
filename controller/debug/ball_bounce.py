# ============================================================
# Protected Trees Explorer — Bouncing Ball Demo
# MicroPython / Thonny
# ============================================================

from machine import I2C, Pin
import time
import framebuf

# ------------------------------------------------------------
# Pin definitions (from CustomPCB_Debug.py)
# ------------------------------------------------------------
PIN_SDA = 2
PIN_SCL = 3

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

    def pixel(self, x, y, col=1):
        self.framebuf.pixel(x, y, col)

    def hline(self, x, y, w, col=1):
        self.framebuf.hline(x, y, w, col)

    def fill_rect(self, x, y, w, h, col=1):
        self.framebuf.fill_rect(x, y, w, h, col)

    def fill_circle(self, cx, cy, r, col=1):
        for dy in range(-r, r + 1):
            dx = int((r * r - dy * dy) ** 0.5)
            self.framebuf.hline(cx - dx, cy + dy, dx * 2 + 1, col)

    def show(self):
        self._cmd(0x21); self._cmd(0); self._cmd(self.width - 1)
        self._cmd(0x22); self._cmd(0); self._cmd(self.pages - 1)
        self.i2c.writeto(self.addr, b'\x40' + self.buffer)

# ------------------------------------------------------------
# Setup
# ------------------------------------------------------------
i2c = I2C(1, scl=Pin(PIN_SCL), sda=Pin(PIN_SDA), freq=400000)
oled = SSD1306_I2C(128, 64, i2c)

WIDTH = 128
HEIGHT = 64
BALL_R = 7
FLOOR_Y = HEIGHT - 1

x = WIDTH // 2
y = BALL_R
vy = 0.0
GRAVITY = 0.6
BOUNCE_DAMPING = 0.9

# ------------------------------------------------------------
# Main loop
# ------------------------------------------------------------
while True:
    vy += GRAVITY
    y += vy

    if y + BALL_R >= FLOOR_Y:
        y = FLOOR_Y - BALL_R
        vy = -vy * BOUNCE_DAMPING
        if abs(vy) < 1:
            vy = -8  # keep it bouncing

    oled.fill(0)
    oled.hline(0, FLOOR_Y, WIDTH, 1)
    oled.fill_circle(int(x), int(y), BALL_R, 1)
    oled.show()

    time.sleep(0.03)
