---
name: pes-ted-extract
description: |
  Use ONLY when the task involves PES 2021 .ted file parsing, decrypting, extracting player/team data,
  regenerating ted_data.json/ted_data_light.js/ted_data_full.js, or fixing the index.html visualization.
  Use when working with patch folders, XOR decryption, bit-packed stat fields, or the OVR calculation formula.
  Do NOT use for general football discussion unrelated to .ted file format or extraction.
---

# PES 2021 · .ted Extraction & Web Visualization Skill

Full workflow from decryption to web rendering. All files in `/home/sergi/Escriptori/pes2021 patch`.

---

## 1. Repo structure

```
extract_teams.py        # Singular entrypoint
index.html              # Raffle page + team panel (open directly, no server)
ted_data.json           # Full extraction output (27 MB)
ted_data_light.js       # Startup data (4.2 MB) — loaded via <script>
ted_data_full.js        # Lazy-loaded per-player data (9.7 MB)
TED_FORMAT.md           # Full .ted format reference (offsets, bitfields)
BIT_PARSING.md          # LSB-first bit parsing convention
AGENTS.md               # Agent guide (OVR, stats, gotchas)
STATS_SCALE.md          # OVR scale and star thresholds
```

Three patch directories (`.ted` files inside, some nested).

---

## 2. .ted decryption (PES 2021 PS4, 14820 bytes)

```python
e = 5
key = raw[69:80] + raw[48:69]  # 32-byte key from two slices
dec = bytearray(len(raw))
dec[:80] = raw[:48] + b'\x00' * 32
for i in range(80, len(raw)):
    dec[i] = raw[i] ^ key[(i - 80) % 32]
```

- Only 14820-byte files are PES 2021 PS4 (14760 = PES 2020 PS3/PC).
- Bytes `[0:48]` are plaintext header, `[80:]` are XOR-masked.
- `e=5` is PES 2021 specific; other versions differ.

---

## 3. Player record layout

| Field | Byte | Bits | Type |
|-------|------|------|------|
| `playerId` | 0 | 32 | uint32 LE |
| `playerName` | 54 | 61 | string |
| `height` | 10 | 8 | uint8 |
| `weight` | 11 | 8 | uint8 |
| `registeredPosition` | 32 | 13‑16 (4) | LSB-first |
| `strongerFoot` | 44 | 29 (1) | 0=dretà, 1=esquerrà |
| `weakFootUsage` | 12 | 30‑31 (2) | |
| `weakFootAccuracy` | 36 | 30‑31 (2) | |
| `form` | 28 | 28‑30 (3) | |
| `injuryResistance` | 40 | 7‑8 (2) | |

Stats (7-bit each) at various offsets — see `STAT_FIELDS` in `extract_teams.py:31-39`.
Skills: 48× 1-bit flags at `SKILL_BITS` in `extract_teams.py:95-103`.

---

## 4. How to add a new patch folder

1. Drop the folder containing `.ted` files into the project root.
2. Add its name to `TEAM_DIRS` in `extract_teams.py`:
   ```python
   TEAM_DIRS = [
       "BEST OF WORLD CUPS - 195 TEAMS - PES 2021",
       "SUPER LEAGUE - PES 2021 - 194 CLASSIC TEAMS",
       "SUPER PATCH 250 TEAMS + 53 INTERNATIONAL TEAMS - PES 2021 - MESTRE KAMIKA",
       "YOUR NEW PATCH",
   ]
   ```
3. Regenerate data:
   ```bash
   python3 extract_teams.py
   # ~2 min for 693 files
   ```
4. If a `.ted` uses a different format (e.g. 14760 bytes = PES 2020), the script skips it automatically.

---

## 5. Adding a new field to the extraction

1. Find the correct byte/bit offset in `TED_FORMAT.md` or TEditor source.
2. Add the `read_bitfield()` call in `extract_players()` (`extract_teams.py:118-174`).
3. Add the compact key to the `full_entry["players"]` dict (lines 323-364).
4. If needed for search, add to `player_index` (lines 366-374).
5. Update the frontend in `index.html` to read and display the new field.
6. Regenerate: `python3 extract_teams.py`

### Foot preference example (strongerFoot at byte 44, bit 29):

In `extract_players()`:
```python
stronger_foot = read_bitfield(rec, 44, 29, 1)
```

Store in player dict:
```python
"strongerFoot": stronger_foot,
```

Add to compact JSON:
```python
"sf": pl["strongerFoot"],
```

Frontend (index.html):
```javascript
const footDir = pl.sf !== undefined ? (pl.sf === 1 ? 2 : 1) : pl.wfU;
```

---

## 6. `read_bitfield()` — LSB-first convention

```python
def read_bitfield(data, byte_offset, bit_offset, bit_length):
    val = 0
    first_byte = byte_offset + bit_offset // 8
    first_bit = bit_offset % 8
    for i in range(bit_length):
        byte_idx = first_byte + (first_bit + i) // 8
        bit_idx = (first_bit + i) % 8
        val |= ((data[byte_idx] >> bit_idx) & 1) << i
    return val
```

- LSB-0 within bytes, LSB-first within the field.
- Using MSB-first gives plausible-looking but wrong values.

---

## 7. OVR calculation (position-weighted)

See full formula in `AGENTS.md:80-103`. Key points:

- 20 generic stats + 5 GK stats, each 0‑127 raw (converted to 0‑99 internally).
- Position weights in `POS_WEIGHTS` dict (lines 69-83 of extract_teams.py).
- Height bonus for GK, CB, DMF, CF.
- GK OVR: 85% GK-specific + 15% generic average.
- Star thresholds: `<76→1★`, `<79→2★`, `<81→3★`, `<83→4★`, `≥83→5★`.

---

## 8. Web visualization

- `index.html` loads `ted_data_light.js` via `<script>` tag.
- No server needed — open directly in browser (`file://`).
- Team panel opens on click (slide-in from right, 580 px).
- Player modal uses Chart.js (cdn.jsdelivr.net/npm/chart.js@4.4.7).
- Full player data lazily loaded: `loadFullData()` injects `<script src="ted_data_full.js">`.

### Key frontend code locations (approximate — search the function name):

| Feature | Function / pattern | Approx line |
|---------|-------------------|-------------|
| Skill decoding | `const bits=(pl.sh` | 1445 |
| Foot display | `const footDir=pl.sf` | 1408 |
| Player modal render | `renderPlayerModal` | 1402 |
| Search filter | `doSearch` | 1186 |
| Position tags | `renderPosTags` | 1111 |
| Squad table render | `let html='<div class="panel-card"><h3>Plantilla</h3>` | 1294 |
| Glossary render | `renderGlossary` | 1131 |

---

## 9. Troubleshooting

| Symptom | Likely cause |
|---------|--------------|
| Stats look wrong (e.g. Messi has ap=10) | Bit-endianness: using MSB-first instead of LSB-first |
| File skipped | Not 14820 bytes (PES 2020 = 14760) |
| Wrong OVR | `registeredPosition` mismatch — check byte 32 bit 13 |
| Wrong foot | Using `wfU` instead of `sf` (strongerFoot at byte 44 bit 29) |
| Player count wrong | Player record length changed (PES 2020 uses 2268 start) |
| Skills don't match | Skill bit positions out of sync — check SKILL_BITS order matches SKILL_NAMES |

---

## 10. Verification checklist after changes

1. Run `python3 extract_teams.py` without errors.
2. Verify file sizes: light ~2.9 MB, full ~6.7 MB.
3. Check key players (Messi, CR7, Neymar) have correct stats, position, foot.
4. Open `index.html` in browser — verify search, filters, team panel, player modal.
5. Check mobile layout at 640px and 400px widths.
