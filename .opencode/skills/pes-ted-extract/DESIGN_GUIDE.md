# Design Guide — PES 2021 Utilities

## CSS Custom Properties (Design Tokens)

All colors, radii, shadows, and fonts are defined as CSS variables in the `:root` block at the top of `<style>` in `index.html`. Change any value in one place to update the entire UI.

### 🎨 Palette

| Variable | Default | Purpose |
|----------|---------|---------|
| `--bg-page` | `#0a0f0a` | Page background |
| `--bg-card` | `#141914` | Card/panel/section backgrounds |
| `--bg-surface` | `#0a0f0a` | Elevated surface (result cards, modal content) |
| `--bg-surface-alt` | `#1a221a` | Alternative surface (squad track, select bg) |
| `--bg-hover` | `#1a261a` | Hover state backgrounds |
| `--bg-overlay` | `rgba(0,0,0,.7)` | Overlay behind modals/panels |
| `--text-primary` | `#f0f8f0` | Primary text (headings, body) |
| `--text-secondary` | `#c8d8c8` | Secondary text (patch headers, table body) |
| `--text-muted` | `#6a8a6a` | Muted text (meta, labels, stats) |
| `--text-dim` | `#5a7a5a` | Dim text (section titles, form labels) |
| `--text-faint` | `#4a5a4a` | Faint text (counts, placeholders) |

### 🔵 Accents

| Variable | Default | Purpose |
|----------|---------|---------|
| `--accent` | `#3b82f6` | Primary accent (buttons, borders, highlights) |
| `--accent-hover` | `#2563eb` | Accent hover state |
| `--accent-glow` | `rgba(59,130,246,.15)` | Subtle accent glow (shadows, focus rings) |
| `--accent-glow-3` | `rgba(59,130,246,.3)` | Stronger accent glow |

### 🔲 Borders

| Variable | Default | Purpose |
|----------|---------|---------|
| `--border` | `#1e2a1e` | Default borders |
| `--border-light` | `#2a3a2a` | Lighter borders (inputs, modals) |
| `--border-hover` | `#3a5a3a` | Hover border state |

### 📊 Stat Categories

| Variable | Default | Purpose |
|----------|---------|---------|
| `--stat-phy` | `#c0392b` | Physical stats (speed, stamina...) |
| `--stat-tec` | `#2980b9` | Technical stats (passing, dribbling...) |
| `--stat-men` | `#6366f1` | Mental stats (defense, aggression...) |
| `--stat-gk` | `#27ae60` | Goalkeeper stats |
| `--stat-phy-to` | `#e74c3c` | Physical gradient end |
| `--stat-tec-to` | `#3498db` | Technical gradient end |
| `--stat-men-to` | `#818cf8` | Mental gradient end |
| `--stat-gk-to` | `#2ecc71` | Goalkeeper gradient end |

### 📐 Layout & Typography

| Variable | Default | Purpose |
|----------|---------|---------|
| `--radius-sm` | `10px` | Small border-radius (cards, inputs) |
| `--radius-md` | `14px` | Medium border-radius (sections) |
| `--radius-lg` | `18px` | Large border-radius (modals) |
| `--shadow-card` | `0 4px 20px rgba(0,0,0,.4)` | Card shadows |
| `--shadow-hover` | `0 8px 30px var(--accent-glow)` | Card hover shadow |
| `--font-mono` | `SFMono-Regular,Consolas,'Liberation Mono',monospace` | Monospace font |

---

## How to Change the Theme

### Example: Switch to a red/amber accent palette

```css
:root {
  --accent: #e74c3c;
  --accent-hover: #c0392b;
  --accent-glow: rgba(231,76,60,.15);
  --accent-glow-3: rgba(231,76,60,.3);
}
```

### Example: Lighter background theme

```css
:root {
  --bg-page: #1a2a1a;
  --bg-card: #223022;
  --bg-surface: #1a2a1a;
  --bg-surface-alt: #2a3a2a;
  --text-primary: #e8f0e8;
}
```

---

## How to Add a New Player Field

### 1. Extraction (`scripts/extract_teams.py`)

Add the `read_bitfield()` call in `extract_players()` (around line 120):

```python
new_field = read_bitfield(rec, byte_offset, bit_offset, bit_length)
```

Add to the player dict and to the compact JSON output in `main()`.

### 2. Frontend — Constants (`index.html`)

Add to `STAT_NAMES_FULL` if it's a stat:

```javascript
const STAT_NAMES_FULL = [
  ...
  ['xx', 'fieldName'],
];
```

Add label to `STAT_LABELS`:

```javascript
const STAT_LABELS = {
  ...
  xx: 'Label',
};
```

Add category to `STAT_CATS`:

```javascript
const STAT_CATS = {
  ...
  xx: 'phy',  // 'phy' | 'tec' | 'men' | 'gk'
};
```

### 3. Frontend — Stats bars

If the field is a stat, it automatically appears in:
- The player modal stat grid (20-stats or 25-stats for GK)
- The spider/radar chart
- The team strengths/weaknesses panel

### 4. Frontend — Squad table

To add a column to the squad table:

1. Add the column definition in `renderSquad()`:

```javascript
const cols = [
  ...
  {k:'xx', l:'Label'},
];
```

2. Add the value extraction and sorting case:

```javascript
case'xx': va = a.xx || 0; vb = b.xx || 0; break;
```

3. Add the cell render in the `sorted.forEach` loop.

---

## Data Flow

```
.ted file  →  extract_teams.py  →  data/ted_data.json  (full)
                                  →  data/light.json     (index)
                                  →  data/full/*.json    (per-patch, lazy-loaded)

index.html  →  fetch('data/light.json')  →  team list + player index
            →  fetch('data/full/<id>.json')  →  full player data (on demand)
```

- `light.json` contains `{ teams: [...], players: [...] }` — loaded at startup
- `full/*.json` contains `{ "patch::teamName": { ... } }` — lazy-loaded per patch
- Each player record uses compact keys (1-2 chars) to reduce file size
