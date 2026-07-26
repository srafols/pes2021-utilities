# Bit Parsing Convention for .ted files

## The `read_bitfield()` function

All bit-packed fields in .ted files use this convention:

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

## Convention

- **LSB-0 bit numbering within bytes** — bit 0 is the least significant bit of a byte.
- **LSB-first within the field** — the first bit read (at the documented offset) goes to position 0 of the result.
- Fields are packed sequentially across byte boundaries with no gaps.

## How it differs from common alternatives

| Convention | Bit 0 of field at (24, 0, 7) |
|---|---|
| **This spec (LSB-0, LSB-first)** | `byte[24]` bit 0 → result bit 0 |
| MSB-0, MSB-first | `byte[24]` bit 7 → result bit 6 |
| MSB-0, LSB-first | `byte[24]` bit 7 → result bit 0 |
| LSB-0, MSB-first | `byte[24]` bit 0 → result bit 6 |

The offsets in `TED_FORMAT.md` (same directory) are correct for this convention. Using MSB-first will give plausible-looking but wrong values.

## Example: attackingProwess at (24, 0, 7)

```
Reading 7 bits starting at byte 24, bit 0:

i=0 → byte[24] bit 0 → bit 0 of result
i=1 → byte[24] bit 1 → bit 1 of result
  …
i=6 → byte[24] bit 6 → bit 6 of result

Result = (byte[24] & 0x7F)  (7-bit value)
```

## Example: form at (28, 28, 3)

28 bits = 3 full bytes + 4 bits. So:
- Byte 31 contains bits 24–31, so bit 28 = byte[31], bit 4
- `i=0` → `byte[31]` bit 4 → result bit 0
- `i=1` → `byte[31]` bit 5 → result bit 1
- `i=2` → `byte[31]` bit 6 → result bit 2

## Fields using this convention

| Field size | Examples |
|---|---|
| 7-bit | All 20 stats + 5 GK stats |
| 2-bit | Position proficiencies (GK, CB, LB, RB, DMF, CMF, LMF, RMF, AMF, RWF, SS, CF, LWF), weakFootUsage, weakFootAccuracy, attitude |
| 3-bit | form, playingStyle, reputation |
| 1-bit | Skills (48 individual skill flags), registeredPosition? |
| 2-bit | injuryResistance |

## Skills: special handling

Skills are stored in the .ted as individual 1-bit flags at documented positions (see `TED_FORMAT.md` in this folder). The extraction script reads each one individually and packs them into a 48-bit bitmask (`skillsLo` + `skillsHi`) for compact storage.

Client-side decoding (index.html):
```javascript
const bits = (pl.sh << 32) | pl.sl;
for (let j = 0; j < 48; j++) {
    if (bits & (1 << j)) skills.push(SKILL_NAMES[j]);
}
```

Bit `j` in the mask corresponds to skill index `j` in `SKILL_NAMES`, which matches the order of byte/bit positions documented in `TED_FORMAT.md` (same directory).

## Verification

For Ronaldo (Brazil 2002), expected stat ranges:

| Stat | Expected range | Got |
|---|---|---|
| attackingProwess | ~90–98 | 94 |
| finishing | ~93–99 | 95 |
| speed | ~80–90 | 86 |
| acceleration | ~80–90 | 86 |
| dribbling | ~82–92 | 87 |
| ballControl | ~87–97 | 92 |

If any stat is systematically outside ±10 of expected legend values, the bit convention is wrong.
