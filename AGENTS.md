# PES 2021 Team Patch — Agent Guide

## Repo structure

```
index.html                # Raffle page + team detail panel (needs HTTP server)
scripts/extract_teams.py  # Decrypts .ted → JSON data files
data/
  light.json              # Team list + player index (3.8 MB, loaded first)
  full/*.json             # Per-patch player data (~1-3 MB, lazy-loaded)
docs/                     # Format docs (TED_FORMAT, BIT_PARSING, etc.)
.opencode/                # Editor config + skills
```

## .ted decryption (PES 2021 PS4, 14820 bytes)

```python
e = 5
key = raw[64+e:80] + raw[48:64+e]   # 32-byte key from two slices
dec = bytearray(len(raw))
dec[:80] = raw[:48] + b'\x00' * 32
for i in range(80, len(raw)):
    dec[i] = raw[i] ^ key[(i - 80) % 32]
```

- Only 14820-byte files are PES 2021 PS4 (14760 = PES 2020 PS3/PC).
- Bytes `[0:48]` are plaintext header, `[80:]` are XOR-masked.
- `e=5` is PES 2021 specific; other versions differ.

## Player records

- Start at byte **2328** (PES 2021 PS4; PES 2020 uses 2268).
- Record length: 312 bytes, array of 40. Empty slots have `playerId=0`.
- `playerName` at offset 54 (61 B), `clubShirtName` at 115, `ntShirtName` at 176.
- Shirt numbers: `assignment[164:244]`, 40× uint16 LE.
- Stats are 7-bit fields packed across byte boundaries. See `docs/BIT_PARSING.md` for the correct `read_bitfield()` convention, and `docs/TED_FORMAT.md` for field offsets.

## The 20 stat fields used for OVR (excluding GK stats)

`attackingProwess`, `ballControl`, `tightPossession`, `lowPass`, `loftedPass`, `finishing`, `placeKicking`, `curl`, `speed`, `acceleration`, `jump`, `physicalContact`, `balance`, `stamina`, `ballWinning`, `aggression`, `defensiveProwess`, `headingAbility`, `dribbling`, `kickingPower`

(packed at various byte/bit offsets — see `STAT_FIELDS` in `extract_teams.py:31-39`)

## Extracted player fields (ted_data_full.js — compact keys)

| Full key | Compact | Type | Description |
|----------|---------|------|-------------|
| `name` | `n` | string | Player name |
| `shirtNumber` | `s` | int | 1–99 |
| `registeredPosition` | `p` | int | Index into `POS_ORDER` |
| `height` | `h` | int | cm |
| `weight` | `w` | int | kg |
| `weakFootUsage` | `wfU` | int | 1–2 |
| `weakFootAccuracy` | `wfA` | int | 1–2 |
| `strongerFoot` | `sf` | int | 0=dretà, 1=esquerrà (bit a byte 44 bit 29 del record) |
| `form` | `f` | int | 0–6 |
| `injuryResistance` | `i` | int | 0–2 |
| `skillsLo` | `sl` | int | Skill bitmask low 32 (bits 0–31) |
| `skillsHi` | `sh` | int | Skill bitmask high 16 (bits 32–47) |
| `attackingProwess` | `ap` | int | 0–127 |
| …20 stats… | — | int | Each stored as a single‑letter key |

## Skill bitmask decoding (client-side, index.html:1347-1349)

```javascript
const bits = (pl.sh >>> 0) * 4294967296 + (pl.sl >>> 0);
for (let i = 0; i < 48; i++) {
    if (bits & (1 << i)) skills.push(SKILL_NAMES[i]);
}
```

The `SKILL_NAMES` array order matches the documented byte/bit positions:
- `[0..25]` → byte 48, bits 6–31
- `[26..40]` → byte 52, bits 0–14
- `[41..47]` → (44,31), (48,0), (48,1), (48,2), (48,3), (48,4), (48,5)

## Star rating calculation

```python
# Converteix stat 0-127 a 0-99 (lineal)
def to99(v): return min(99, round(v * 99 / 127))

BASELINE = 25                       # 25-point rule de Konami (0-99 scale)
adj_i  = max(0, to99(stat_i) - BASELINE)
c      = POS_COEFS[pos]             # coeficients per posició (suma ~1.28)
coef_sum = sum(c)

player_ovr_99 = BASELINE * coef_sum + sum(c_i * adj_i) + height_bonus
height_bonus  = HEIGHT_BONUS[pos] * max(0, (height - 175) / 10)

# GK: 85% pes específic + 15% mitjana genèrica per no sobrevalorar
player_ovr_99_gk = (BASELINE * coef_sum
                   + 0.85 * sum(c_i * adj_i for GK stats)
                   + 0.15 * mean(adj for generic stats))

# Convertir a escala 0-127 per compatibilitat amb el display
player_ovr = player_ovr_99 * 127 / 99

team_ovr = mean(all player_ovrs)
# Thresholds actuals: <76→1★, <79→2★, <81→3★, <83→4★, ≥83→5★
```

- Els coeficients (`POS_COEFS`) estan escalats des dels pesos normalitzats
  originals: `coef_i = w_i × 127/99`. La fórmula amb 25-point rule + intercept
  és matemàticament equivalent a la mitjana ponderada original.
- **Height bonus**: GK (+0.8/10cm), CB (+0.4), DMF (+0.15), CF (+0.35).
  S'aplica sobre 0-99 abans de la conversió a 127.
- GK stats (`gkAwareness`…`gkReflexes`) inclosos al weighted sum (0% per no-GK).

### Fórmula real de Konami (per referència)

Segons l'anàlisi de **Mimo** (regressió sobre PESDB, MAE=0.03-0.09):

```
OVR = intercept + Σ(coef_i × max(0, stat_99_i − 25)) + h_coef × height_cm
```

On:
- **Intercept** és negatiu (ex. -55 per CF), no igual al baseline.
- **Coeficients** són específics per posició, descoberts per regressió no-negativa.
- **Σ(coef_i) ≠ 1.0**: la suma dels coeficients per CF és ~1.6, no normalitzada.
- **Alçada** com a variable independent (coef ~0.1 per CF, major per GK/CB).
- **Arrodoniment a 0.5**.
- L'escala és 0-99 (Konami) → convertim a 0-127 pel nostre display.

Per replicar exactament la fórmula de Konami, caldria:
1. Obtenir els coeficients de regressió de Mimo (no disponibles públicament com a text)
2. O alternativament, fer regressió sobre dades de PESDB amb "Rating as X"
3. Ajustar HEIGHT_BONUS i POS_COEFS amb aquests valors

Vegeu `docs/STATS_SCALE.md` per més detall sobre escales i llindars.

## Regenerating data

```bash
python3 scripts/extract_teams.py
# Outputs: ted_data.json, ted_data_light.js, ted_data_full.js
```

Takes ~2 minutes for all 693 files.

## Web page

- `index.html` loads `ted_data_light.js` via `<script src=…>` (works on `file://`).
- No server needed — open directly in a browser.
- Team detail panel (slide‑in from right, 580 px) opens on click from team list or result cards.
- Full per‑player data lazily loaded: `loadFullData()` injects `<script src="ted_data_full.js">` on first click.
- Language: Catalan.

## Features

- **Raffle** with animated spin (blur + glow effects), lottery sound (Web Audio API: drum ticks + fanfare), and stagger-animated result cards.
- **Player search** with accent-insensitive matching, filters by position/patch/foot/skill (multi-select), sorted by OVR descending.
- **Skills glossary / Help** — click "📖 Guia" to browse all 48 skills with Catalan names and descriptions, organized by category; click skills to add/remove filter tags (multi-select). Players must have ALL selected skills to match.
- **Team detail panel** with:
  - Strengths/weaknesses (top/bottom 3 team stats)
  - Formation grid (11 starters grouped by category)
  - Sortable squad table (click column headers)
  - Player spider chart (20-stats radar on Canvas)
  - Bar charts for all stats with category-colored fills

## Key gotchas

- **No OVR in .ted** — must be calculated from individual bit-packed stats.
- **Per-team star ratings are approximate** — based on equal-weight average of 20 generic stats, not Konami's position-weighted formula.
- **Bit convention: LSB-0 within bytes, LSB-first within field.** The documented offsets in `docs/TED_FORMAT.md` are correct, but they must be read with `read_bitfield()` as defined in `docs/BIT_PARSING.md`. Using MSB-first gives wrong values.
- **Foot preference:** extracted via `strongerFoot` at byte 44 bit 29 (1 bit: 0=dretà, 1=esquerrà). Fallback to `weakFootUsage` if `sf` is unavailable. Verified against Argentina 2022 and Chelsea squads — ~95%+ accuracy vs real-world data.
- `extract_teams.py` only processes files exactly 14820 bytes.
- Patch 3 has nested subdirectories (`01 - LEGENDS…/`, `02 - SELECOES…/`); `os.walk` handles this.
- The `docs/TED_FORMAT.md` has exhaustive field tables for all bit-packed data; use it when adding new extraction fields.
- Stats (7-bit), position proficiencies (2-bit), weakFoot (2-bit), form (3-bit), injury (2-bit), and skills (1-bit) all use the same `read_bitfield()` convention.
- Skills are stored as compact bitmasks (`sl`/`sh`), not string arrays, saving ~1.3 MB in `ted_data_full.js`.
- **`registeredPosition`** es llegeix directament del camp raw a byte 32 bit 13 (4 bits), no es calcula de les proficiencies. Això evita ~30% de discrepàncies contra la posició real del joc.
- Position proficiencies (13×2-bit) are extracted but not included in `ted_data_full.js` (the derived `registeredPosition` is used instead).

## Player modal (search → Chart.js radar chart)

- Clicking a search result opens a centered modal (`#playerModalOverlay`) with full player stats.
- Uses **Chart.js** (`cdn.jsdelivr.net/npm/chart.js@4.4.7`) for the 20-stat radar chart.
- Stats are rendered in a 2-column grid with category-colored bars (phy=red, tec=blue, men=gold).
- Skills decoded from bitmasks and shown as tags.
- The team panel's inline spider chart was also replaced with Chart.js.
- Chart instances are destroyed on modal/panel close to prevent memory leaks.
- Player index in light data includes `di` (index within team) for direct lookup in full data, and `sf` (0=dretà, 1=esquerrà) for foot filtering.
