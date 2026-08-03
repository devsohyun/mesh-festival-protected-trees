# Protected Trees

Interactive installation for **Mesh Festival 2026**. A physical controller lets an
audience member pick one of Seoul's officially protected/old trees by ID; TouchDesigner
then generates and displays a procedural shape of that specific tree, driven by its real
municipal data (age, height, trunk girth, crown spread, vitality, etc.).

## How it works

1. A **Raspberry Pi Pico controller** (rotary encoder + confirm button + OLED) lets the
   audience scroll through tree IDs `1–345` and confirm one.
2. The confirmed ID is sent to the machine running **TouchDesigner** — over USB serial
   by default, or optionally OSC/UDP over Ethernet (see [Communication mode](#communication-mode)).
3. TouchDesigner looks up that ID in a local dataset of Seoul's protected trees (originally
   sourced from the [Seoul Open Data Plaza](http://data.seoul.go.kr/) API), extracts the
   relevant fields, and feeds them into an L-system to render that tree's shape.

## Repo layout

```
builds/     TouchDesigner project files (.toe)
controller/ MicroPython firmware for the Raspberry Pi Pico controller
data/       Local snapshot of the Seoul protected-trees dataset (Korean + English)
```

### `builds/`

- `protected_trees_v2.0_json.toe` — current build; reads tree data from the local JSON
  files in `data/` (works offline, no live API dependency).
- `protected_trees_v1.0_api.toe` — earlier version that queried the Seoul Open API
  directly per tree ID. Kept for reference.

### `controller/`

- `TreeID_Selector.py` — the controller firmware. Handles:
  - Rotary encoder input (quadrature decoded, one detent = one step, clamped 1–345)
  - OLED display: live browsing number, confirm animation (labels + inverted flash),
    then a static confirmed screen until the next rotary movement
  - Sending the confirmed ID to TouchDesigner — set `COMM_MODE` at the top of the file
    to `"SERIAL"` (default) or `"OSC"` depending on what connection is available at
    the venue
- `debug/` — standalone hardware bring-up scripts (OLED/buttons/encoder/Ethernet checks,
  a bouncing-ball demo). Not part of the show build; useful when re-testing a PCB.

**Deploying to the Pico:** save `TreeID_Selector.py` onto the Pico's flash as `main.py`
(Thonny → File → Save As → Raspberry Pi Pico) so it runs standalone on power-up, with
no computer or Thonny required at the festival.

### `data/`

- `trees_data_kr.json` — local snapshot of the Seoul Open API's protected/old-tree
  dataset (346 trees), original Korean-language values.
- `trees_data_en.json` — same structure and row order, machine-translated/romanized
  into English for display purposes.

Both files share the shape:

```json
{
  "DESCRIPTION": { "UNQ_NO": "고유번호", ... },
  "DATA": [ { "unq_no": 19, "gu_nm": "용산구", ... }, ... ]
}
```

`unq_no` is the tree ID the controller sends (1–345).

## Communication mode

`TreeID_Selector.py` supports two ways to get the confirmed tree ID into TouchDesigner:

| Mode | How | Setup |
|---|---|---|
| `"SERIAL"` (default) | USB cable, Pico → host running TD. Sends the bare ID number as a line of text. | TD side: Serial DAT, baud **115200**, port set to the Pico's USB serial device. |
| `"OSC"` | UDP over the W5500 Ethernet module, address `/tree_id`. | Fill in `TD_HOST_IP` / `TD_HOST_PORT` and DHCP/static IP settings at the top of the file. |

Serial is the confirmed-working path; OSC is there as a fallback/alternative if a
network connection turns out to be available on site.

## Known data caveats

- Some numeric fields (age, height, trunk girth, crown spread, vitality) are `0`/`null`
  for trees the city hasn't fully surveyed. The TouchDesigner side substitutes a random
  in-range value for these so the rendered tree doesn't collapse to a degenerate shape —
  see `manager_script`'s `onTableChange` / `is_empty_or_zero`.
- The `ownr` (owner) and `mngr` (manager) fields include private individuals' names and
  home addresses, not just institutions — this is part of the source open dataset as
  published, carried through into both `trees_data_kr.json` and `trees_data_en.json`.

## Hardware

- Raspberry Pi Pico
- Custom PCB with rotary encoder + confirm button + SSD1306 OLED (I2C)
- Optional: W5500 Ethernet module (SPI) for OSC mode

See pin definitions at the top of `controller/TreeID_Selector.py` /
`controller/debug/CustomPCB_Debug.py`.
