# PES 2021 Utilities 🎯 — Raffle & Player Viewer

Team raffle and player exploration tool for PES 2021 PS4 custom patches.

> ⚠️ Requires an HTTP server — `fetch()` won't work on `file://`.

## 🚀 Quick Start (choose one)

```bash
# Python 3
python3 -m http.server 8000

# Node.js
npx serve .

# PHP
php -S localhost:8000
```

Then open **http://localhost:8000**.

## 📁 Project Structure

```
├── index.html             # Raffle page + team panel + player modal
├── scripts/
│   └── extract_teams.py   # Decrypts .ted → JSON data files
├── data/
│   ├── light.json         # Team list + player index (3.8 MB, loaded at startup)
│   └── full/
│       ├── bestWorldCups.json     # ~1.4 MB
│       ├── superLeague.json       # ~1.2 MB
│       ├── superPatch.json        # ~2.8 MB
│       ├── superPatch80s.json     # ~1.2 MB
│       └── superPatch90s.json     # ~1.4 MB  (per-patch, lazy-loaded)
├── AGENTS.md               # Agent guide
├── .opencode/              # Editor config + skills
└── docs/
    ├── TED_FORMAT.md       # .ted file format reference
    ├── BIT_PARSING.md      # Bit parsing convention
    ├── STATS_SCALE.md      # Stat scale explanation
    └── PERFORMANCE_ALTERNATIVES.md
```

## 📦 Data Loading

- `data/light.json` loaded via `fetch()` on startup — contains team list + player index for search
- Per-patch JSONs loaded on demand when clicking a team or player — only the relevant patch (~1–3 MB)

## 🔧 Data Extraction

```bash
python3 scripts/extract_teams.py "/path/to/patches"   # or set PES_PATCH_BASE
```

Processes `.ted` files (14820 bytes, PES 2021 PS4) and outputs `data/ted_data.json`, `data/light.json`, and `data/full/*.json`.

## ✨ Features

- 🎲 **Team raffle** with animated spin and sound (Web Audio API)
- 🔍 **Player search** with accent-insensitive matching, filters by position/patch/foot/skill
- 📋 **Team detail panel** with real tactic-slot formation canvas (shape label + bench), squad table, spider chart (Chart.js)
- 👤 **Player modal** with 20-stats radar chart and skill tags
- 📖 **Skills glossary** with Catalan names and descriptions

## 📋 Requirements

- 🐍 Python 3.x for data extraction
- 🌐 Any HTTP server for the web page (required for `fetch()`)

## 📄 License

MIT
