# PES 2021 .ted File Format (PS4)

This document describes the structure of PES 2021 `.ted` team files for PS4 (14820 bytes), based on reverse-engineering the TEditor source code and empirical testing.

---

## 1. File Size & Platform Detection

| Size | Platform | Game |
|------|----------|------|
| 14820 | PS4 | PES 2021 |
| 14760 | PS3/PC | PES 2020 |

---

## 2. Decryption (XOR Masking)

The file is partially XOR-encrypted. Bytes `[0:48]` are plaintext header; the rest is masked.

### Key derivation

```
e = 5
key = data[69:80] + data[48:69]   # 32 bytes total
```

- `e` is 5 for PES 2021 (may differ for other versions).
- Key is formed by concatenating two slices of the raw encrypted data.

### Decryption

```python
dec = bytearray(len(raw))
dec[:80] = raw[:48] + b'\x00' * 32     # first 80 bytes: copy header, zero the key area
for i in range(80, len(raw)):
    dec[i] = raw[i] ^ key[(i - 80) % 32]
```

- Only bytes `[80:]` need XOR.
- The XOR index cycles modulo 32 relative to byte 80.

---

## 3. Top-Level Layout

All offsets are **absolute** byte positions in the decrypted file.

| Section | Start | Length | Contents |
|---------|-------|--------|----------|
| `header` | 0 | 48 | Game version, data pack version |
| `team` | 80 | 588 | Team metadata (name, stadium, colors, images) |
| `coach` | 668 | 88 | Coach info |
| `playerAssignment` | 756 | 284 | Squad (40 player IDs + shirt numbers) |
| `tactics` | 1040 | 628 | 3 presets, formations, player orders |
| `uniforms` | 1668 | 132 | 5 uniform kits |
| `players` | 2328 | 312×40 | 40× player records (active entries may be fewer) |
| `metadata` | 14808 | 12 | Career start team, loan info |

---

## 4. Team Info Section (start=80, length=588)

```python
team_info = data[80:668]
```

| Field | Offset | Length | Type | Notes |
|-------|--------|--------|------|-------|
| `teamId` | 0 | 4 | uint32 | |
| `coachId` | 4 | 4 | uint32 | |
| `stadiumId` | 10 | 2 | sint16 | |
| `countryId` | 14 | 2 | uint16 | |
| `callnameId` | 16 | 2 | sint16 | |
| `teamName` | 104 | 70 | string | Null-terminated, ASCII |
| `shortName` | 174 | 4 | string | 3-letter code |
| `stadiumName` | 178 | 120 | string | |
| `emblemImageFileName` | 423 | 32 | string | e.g. `"BRAZIL 2002.png"` |
| `stadiumImageFileName` | 456 | 32 | string | |

---

## 5. Player Record (start=2328, length=312, array of 40)

Each player record is 312 bytes. Empty slots have `playerId = 0`.

### String fields

| Field | Offset | Length | Type |
|-------|--------|--------|------|
| `playerId` | 0 | 4 | uint32 |
| `callnameId` | 4 | 4 | uint32 |
| `playerName` | 54 | 61 | string (null-terminated) |
| `clubShirtName` | 115 | 61 | string |
| `ntShirtName` | 176 | 61 | string |

### Scalar fields

| Field | Offset | Type |
|-------|--------|------|
| `height` | 10 | uint8 (cm) |
| `weight` | 11 | uint8 (kg) |
| `goalCelebration1` | 12 | uint8 |
| `goalCelebration2` | 13 | uint8 |

### Bit-packed stats (7-bit fields)

Stats are 7-bit values (0–127) packed across byte boundaries.

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

Example: reading a stat at `rec_start + 12`, bit 16, length 7:

```python
ap = read_bitfield(dec, rec_start + 12, 16, 7)
```

| Stat | Byte Offset | Bit Offset | Bits |
|------|-------------|------------|------|
| `attackingProwess` | 12 | 16 | 7 |
| `ballControl` | 12 | 23 | 7 |
| `weakFootUsage` | 12 | 30 | 2 |
| `tightPossession` | 16 | 0 | 7 |
| `lowPass` | 16 | 7 | 7 |
| `loftedPass` | 16 | 14 | 7 |
| `finishing` | 16 | 21 | 7 |
| `placeKicking` | 20 | 0 | 7 |
| `curl` | 20 | 7 | 7 |
| `speed` | 20 | 14 | 7 |
| `acceleration` | 20 | 21 | 7 |
| `jump` | 24 | 0 | 7 |
| `physicalContact` | 24 | 7 | 7 |
| `balance` | 24 | 14 | 7 |
| `stamina` | 24 | 21 | 7 |
| `ballWinning` | 28 | 0 | 7 |
| `aggression` | 28 | 7 | 7 |
| `gkAwareness` | 28 | 14 | 7 |
| `gkCatching` | 28 | 21 | 7 |
| `form` | 28 | 28 | 3 |
| `gkReach` | 32 | 0 | 7 |
| `defensiveProwess` | 36 | 0 | 7 |
| `gkClearing` | 36 | 7 | 7 |
| `headingAbility` | 36 | 14 | 7 |
| `dribbling` | 40 | 0 | 7 |
| `injuryResistance` | 40 | 7 | 2 |
| `attitude` | 40 | 9 | 2 |
| `gkReflexes` | 44 | 6 | 7 |
| `kickingPower` | 44 | 13 | 7 |
| `weakFootAccuracy` | 36 | 30 | 2 |

### Registered position & position proficiency

| Field | Byte Offset | Bit Offset | Bits |
|-------|-------------|------------|------|
| `registeredPosition` | 32 | 13 | 4 |
| `positionGk` | 40 | 13 | 2 |
| `positionCb` | 40 | 15 | 2 |
| `positionLb` | 40 | 17 | 2 |
| `positionRb` | 40 | 19 | 2 |
| `positionDmf` | 40 | 21 | 2 |
| `positionCmf` | 40 | 23 | 2 |
| `positionLmf` | 40 | 25 | 2 |
| `positionRmf` | 40 | 27 | 2 |
| `positionAmf` | 40 | 29 | 2 |
| `positionRwf` | 44 | 0 | 2 |
| `positionLwf` | 44 | 20 | 2 |
| `positionSs` | 44 | 2 | 2 |
| `positionCf` | 44 | 4 | 2 |

Position values: 0=none, 1=C, 2=B, 3=A (proficiency level).

### Special skills (1-bit flags)

| Field | Byte | Bit |
|-------|------|-----|
| `scissorsFeint` | 48 | 6 |
| `doubleTouch` | 48 | 7 |
| `flipFlap` | 48 | 8 |
| `marseilleTurn` | 48 | 9 |
| `sombrero` | 48 | 10 |
| `crossOverTurn` | 48 | 11 |
| `cutBehindAndTurn` | 48 | 12 |
| `scotchMove` | 48 | 13 |
| `stepOnSkillControl` | 48 | 14 |
| `headingSkill` | 48 | 15 |
| `longRangeDrive` | 48 | 16 |
| `chipShotControl` | 48 | 17 |
| `longRangeShooting` | 48 | 18 |
| `knuckleShot` | 48 | 19 |
| `dippingShot` | 48 | 20 |
| `risingShot` | 48 | 21 |
| `acrobaticFinishing` | 48 | 22 |
| `heelTrick` | 48 | 23 |
| `firstTimeShot` | 48 | 24 |
| `oneTouchPass` | 48 | 25 |
| `throughPassing` | 48 | 26 |
| `weightedPass` | 48 | 27 |
| `pinpointCrossing` | 48 | 28 |
| `outsideCurler` | 48 | 29 |
| `rabona` | 48 | 30 |
| `noLookPass` | 48 | 31 |
| `lowLoftedPass` | 52 | 0 |
| `gkLowPunt` | 52 | 1 |
| `gkHighPunt` | 52 | 2 |
| `longThrow` | 52 | 3 |
| `gkLongThrow` | 52 | 4 |
| `penaltySpecialist` | 52 | 5 |
| `gkPenaltySaver` | 52 | 6 |
| `gamesmanship` | 52 | 7 |
| `manMarking` | 52 | 8 |
| `trackBack` | 52 | 9 |
| `interception` | 52 | 10 |
| `acrobaticClear` | 52 | 11 |
| `captaincy` | 52 | 12 |
| `superSub` | 52 | 13 |
| `fightingSpirit` | 52 | 14 |

### Playing style & combo skills

| Field | Byte | Bit | Bits |
|-------|------|-----|------|
| `playingStyle` | 32 | 18 | 5 |
| `trickster` | 44 | 31 | 1 |
| `mazingRun` | 48 | 0 | 1 |
| `speedingBullet` | 48 | 1 | 1 |
| `incisiveRun` | 48 | 2 | 1 |
| `longBallExpert` | 48 | 3 | 1 |
| `earlyCross` | 48 | 4 | 1 |
| `longRanger` | 48 | 5 | 1 |

### Animation & appearance

| Field | Byte | Bit | Bits |
|-------|------|-----|------|
| `reputation` | 32 | 28 | 3 |
| `strongerFoot` | 44 | 29 | 1 | 0=dretà, 1=esquerrà |
| `dribHunch` | 36 | 21 | 3 |
| `dribArmMove` | 16 | 28 | 4 |
| `runHunch` | 36 | 24 | 3 |
| `runArmMove` | 20 | 28 | 4 |
| `dribMotion` | 40 | 11 | 2 |
| `ckMotion` | 24 | 28 | 4 |
| `fkMotion` | 32 | 23 | 5 |
| `pkMotion` | 36 | 27 | 3 |

---

## 6. Player Assignment Section (start=756, length=284)

Links player IDs to shirt numbers and positions.

```python
assignment = data[756:1040]
```

| Field | Offset | Length | Notes |
|-------|--------|--------|-------|
| `teamId` | 0 | 4 | |
| `playerIds` | 4 | 4×40 | Array of 40 uint32 player IDs |
| `shirtNumbers` | 164 | 2×40 | Array of 40 uint16 shirt numbers |
| `areTransferred` | 244 | 1×40 | Array of 40 uint8 flags |

The 33 bytes at `244..276` (absolute `1000..1040`) are the tail of the
`areTransferred` flag array — they are **not** formation data.

### Formation positions (11 slots)

The starting-XI tactic slots live in the **tactics** section, not in the
assignment block:

```python
tactics = data[1040:1668]
formation = list(tactics[4:15])  # absolute bytes 1044..1054, one code per slot
```

Verified against 60 random `.ted` files: every value is in `0..12` and there
is exactly one `0` (GK). The remaining `tactics` bytes hold 3 presets, player
orders and instructions; only the first preset's formation is read.

Position values (same indexing as `POS_ORDER`): 0=GK, 1=CB, 2=LB, 3=RB, 4=DMF,
5=CMF, 6=LMF, 7=RMF, 8=AMF, 9=LWF, 10=RWF, 11=SS, 12=CF.

---

## 7. Computing a Star Rating from Stats

A simple team strength rating can be derived from the average of three key stats across all active players:

```python
avg_ap = avg("attackingProwess")
avg_sp = avg("speed")
avg_dp = avg("defensiveProwess")
ovr = (avg_ap + avg_sp + avg_dp) / 3   # range ~42–64 for PES 2021 teams
```

To assign 1–5 stars globally across all teams:

```python
step = (max_ovr - min_ovr) / 5
star = int((ovr - min_ovr) / step) + 1
star = max(1, min(5, star))
```

---

## 8. Full Extraction Script

See `extract_teams.py` in the same directory. It:

1. Walks all patch folders
2. Decrypts each `.ted` file (14820 bytes only)
3. Reads `teamName`, `playerCount`, per-player stat fields
4. Computes OVR and star rating per team
5. Outputs `data/ted_data.json` (full data), `data/light.json` (team list + player index), and `data/full/*.json` (per-patch player data)

---

## 9. Version Differences

The TEditor codebase defines multiple format versions:

| Format | File Size | Platform | Game | Key Split (e) |
|--------|-----------|----------|------|---------------|
| `pes2017` | — | — | PES 2017 | — |
| `pes2018` | — | — | PES 2018 | — |
| `pes2019` | — | PS4/PC | PES 2019 | — |
| `pes2020` | 14760 | PS3/PC | PES 2020 | — |
| `pes2021` | 14820 | PS4 | PES 2021 | 5 |

Players section start also differs: `pes2020` uses byte 2268, `pes2021` uses byte 2328.
