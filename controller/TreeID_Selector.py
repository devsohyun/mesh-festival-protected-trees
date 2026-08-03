# ============================================================
# Protected Trees Explorer — Tree ID Selector
# MicroPython / Raspberry Pi Pico
#
# Rotary encoder scrolls a tree ID (1-345) on the OLED.
# Confirm button plays a "shift to top + CONFIRMED" animation,
# then holds the confirmed ID static until the rotary turns again.
#
# The confirmed ID is sent to TouchDesigner either over USB serial
# or over OSC/UDP (via the W5500 Ethernet module) — flip COMM_MODE
# below depending on what connection is available at the venue.
# ============================================================

from machine import I2C, SPI, Pin
import time
import framebuf
import struct

# ------------------------------------------------------------
# Communication mode — set this depending on what's available
# on site. "SERIAL" is the safe default (USB cable to the machine
# running TouchDesigner, read via a Serial DAT). "OSC" sends UDP
# packets over the W5500 Ethernet module instead.
# ------------------------------------------------------------
COMM_MODE = "SERIAL"   # "SERIAL" or "OSC"

# ------------------------------------------------------------
# OSC / network settings (only used when COMM_MODE == "OSC")
# ------------------------------------------------------------
USE_DHCP     = True                # False to use the static IP settings below
STATIC_IP    = ("192.168.1.200", "255.255.255.0", "192.168.1.1", "8.8.8.8")
TD_HOST_IP   = "192.168.1.100"     # IP of the machine running TouchDesigner
TD_HOST_PORT = 8000                 # port of TouchDesigner's OSC In CHOP/DAT
OSC_ADDRESS  = "/tree_id"

# ------------------------------------------------------------
# Pin definitions (same as CustomPCB_Debug.py)
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
# Tree ID range
# ------------------------------------------------------------
MIN_ID = 1
MAX_ID = 345
START_ID = 1

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

    def fill_rect(self, x, y, w, h, col=1):
        self.framebuf.fill_rect(x, y, w, h, col)

    def invert(self, invert):
        # Hardware invert (0xA7) / normal (0xA6) — flips the whole panel
        # without touching the framebuffer contents.
        self._cmd(0xA7 if invert else 0xA6)

    def show(self):
        self._cmd(0x21); self._cmd(0); self._cmd(self.width - 1)
        self._cmd(0x22); self._cmd(0); self._cmd(self.pages - 1)
        self.i2c.writeto(self.addr, b'\x40' + self.buffer)


# ------------------------------------------------------------
# Big-number rendering
# Renders text at 1x into an offscreen buffer, then blits it to
# the OLED scaled up (each source pixel becomes an SxS block).
# ------------------------------------------------------------
def draw_scaled_text(oled, s, x, y, scale, col=1):
    src_w = len(s) * 8
    src_h = 8
    tmp_buf = bytearray((src_h // 8) * src_w)  # src_h is a multiple of 8 (MONO_VLSB requirement)
    tmp = framebuf.FrameBuffer(tmp_buf, src_w, src_h, framebuf.MONO_VLSB)
    tmp.fill(0)
    tmp.text(s, 0, 0, 1)

    for sy in range(src_h):
        for sx in range(src_w):
            if tmp.pixel(sx, sy):
                oled.fill_rect(x + sx * scale, y + sy * scale, scale, scale, col)


def text_pixel_size(s, scale):
    return len(s) * 8 * scale, 8 * scale


# ------------------------------------------------------------
# Setup
# ------------------------------------------------------------
i2c = I2C(1, scl=Pin(PIN_SCL), sda=Pin(PIN_SDA), freq=400000)
oled = SSD1306_I2C(128, 64, i2c)

confirm_btn = Pin(PIN_CONFIRM_BTN, Pin.IN, Pin.PULL_UP)
rot_a       = Pin(PIN_ROT_A, Pin.IN, Pin.PULL_UP)
rot_b       = Pin(PIN_ROT_B, Pin.IN, Pin.PULL_UP)

WIDTH, HEIGHT = 128, 64
BIG_SCALE = 4

CENTER_Y = (HEIGHT - 8 * BIG_SCALE) // 2   # number position (same while browsing and confirmed)

CONFIRM_DEBOUNCE_MS = 250


def draw_number(tree_id, y, clear=True):
    if clear:
        oled.fill(0)
    s = str(tree_id)
    w, _ = text_pixel_size(s, BIG_SCALE)
    x = (WIDTH - w) // 2
    draw_scaled_text(oled, s, x, y, BIG_SCALE)


def draw_browse_screen(tree_id):
    draw_number(tree_id, CENTER_Y)
    oled.show()


def draw_confirmed_labels_screen(tree_id):
    top_label = "Tree ID"
    bottom_label = "Confirmed"
    top_y = CENTER_Y - 8 - 6
    bottom_y = CENTER_Y + 8 * BIG_SCALE + 6

    draw_number(tree_id, CENTER_Y)
    oled.text(top_label, (WIDTH - len(top_label) * 8) // 2, top_y, 1)
    oled.text(bottom_label, (WIDTH - len(bottom_label) * 8) // 2, bottom_y, 1)
    oled.show()


def draw_confirmed_screen(tree_id):
    # Final idle state after confirmation — number only, no labels.
    draw_number(tree_id, CENTER_Y)
    oled.show()


LABEL_HOLD_S = 3.0


def play_confirm_animation(tree_id):
    """Show the confirmed layout (number + Tree ID / Confirmed labels),
    flash the whole screen inverted three times, then after a few
    seconds drop back to just the number."""
    draw_confirmed_labels_screen(tree_id)

    for i in range(3):
        oled.invert(True)
        time.sleep(0.25)
        oled.invert(False)
        time.sleep(0.25)

    time.sleep(LABEL_HOLD_S)
    draw_confirmed_screen(tree_id)


def build_osc_message(address, int_value):
    """Build a minimal OSC message: address pattern + ",i" type tag + int32 arg."""
    def pad4(b):
        b += b"\x00"
        while len(b) % 4 != 0:
            b += b"\x00"
        return b

    addr_bytes = pad4(address.encode())
    type_tag_bytes = pad4(b",i")
    value_bytes = struct.pack(">i", int_value)
    return addr_bytes + type_tag_bytes + value_bytes


osc_socket = None


def setup_osc_network():
    """Bring up the W5500 over SPI and open a UDP socket for OSC sends."""
    global osc_socket
    try:
        import network
        import socket

        spi = SPI(0, baudrate=2000000,
                  mosi=Pin(PIN_MOSI), miso=Pin(PIN_MISO), sck=Pin(PIN_SCLK))
        nic = network.WIZNET5K(spi, Pin(PIN_CS), Pin(PIN_RST))

        Pin(PIN_RST, Pin.OUT).value(0)
        time.sleep(0.5)
        Pin(PIN_RST, Pin.OUT).value(1)
        time.sleep(0.5)

        nic.active(True)
        time.sleep(1)

        if USE_DHCP:
            nic.ifconfig("dhcp")
        else:
            nic.ifconfig(STATIC_IP)

        deadline = time.ticks_ms() + 10000
        while not nic.isconnected():
            if time.ticks_diff(deadline, time.ticks_ms()) < 0:
                break
            time.sleep(0.2)

        osc_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        print("OSC network ready, IP:", nic.ifconfig()[0])
    except Exception as e:
        print("OSC network setup FAILED:", e)
        osc_socket = None


def send_id_to_touchdesigner(tree_id):
    if COMM_MODE == "SERIAL":
        print(tree_id)
    elif COMM_MODE == "OSC":
        if osc_socket is None:
            print("OSC socket not available, skipping send")
            return
        try:
            msg = build_osc_message(OSC_ADDRESS, tree_id)
            osc_socket.sendto(msg, (TD_HOST_IP, TD_HOST_PORT))
        except Exception as e:
            print("OSC send FAILED:", e)


# ------------------------------------------------------------
# Main loop
# ------------------------------------------------------------
STATE_BROWSE   = 0
STATE_CONFIRMED = 1

state = STATE_BROWSE
current_id = START_ID
last_rot_a = rot_a.value()
last_confirm_time = 0

if COMM_MODE == "OSC":
    setup_osc_network()

draw_browse_screen(current_id)

while True:
    # --- rotary encoder (quadrature decode) ---
    # Only react on A's falling edge: each detent produces one full
    # high->low->high pulse on A, so reacting to both edges double-counts.
    a = rot_a.value()
    if a == 0 and last_rot_a == 1:
        step = 1 if rot_b.value() != a else -1
        last_rot_a = a

        current_id += step
        if current_id > MAX_ID:
            current_id = MAX_ID
        elif current_id < MIN_ID:
            current_id = MIN_ID

        state = STATE_BROWSE
        draw_browse_screen(current_id)
    elif a == 1:
        last_rot_a = a

    # --- confirm button ---
    now = time.ticks_ms()
    if (state == STATE_BROWSE
            and confirm_btn.value() == 0
            and time.ticks_diff(now, last_confirm_time) > CONFIRM_DEBOUNCE_MS):
        last_confirm_time = now

        play_confirm_animation(current_id)
        send_id_to_touchdesigner(current_id)

        state = STATE_CONFIRMED
        draw_confirmed_screen(current_id)

    time.sleep_ms(2)
