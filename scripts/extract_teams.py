#!/usr/bin/env python3
"""Extract team/player data from PES 2021 .ted files (PS4, 14820 bytes)."""

import os, json, struct, sys

TEAM_DIRS = [
    "BEST OF WORLD CUPS - 195 TEAMS - PES 2021",
    "SUPER LEAGUE - PES 2021 - 194 CLASSIC TEAMS",
    "SUPER PATCH 250 TEAMS + 53 INTERNATIONAL TEAMS - PES 2021 - MESTRE KAMIKA",
    "Super Patch 80s - Option File - PES 2021 - Mestre Kamika",
    "SUPER PATCH 1990S - PES 2021 - OPTION FILE - MESTRE KAMIKA",
]

PLAYER_RECORD_LEN = 312
MAX_PLAYERS = 40
PLAYERS_START = 2328

def decrypt(raw):
    e = 5
    key = raw[64+e:80] + raw[48:64+e]
    dec = bytearray(len(raw))
    dec[:80] = raw[:48] + b'\x00' * 32
    for i in range(80, len(raw)):
        dec[i] = raw[i] ^ key[(i - 80) % 32]
    return dec

def read_string(data, offset, max_len):
    end = data.find(b'\x00', offset, offset + max_len)
    if end == -1:
        end = offset + max_len
    return data[offset:end].decode('utf-8', errors='replace').strip()

STAT_FIELDS = [
    ("attackingProwess", 12, 16), ("ballControl", 12, 23), ("tightPossession", 16, 0),
    ("lowPass", 16, 7), ("loftedPass", 16, 14), ("finishing", 16, 21),
    ("placeKicking", 20, 0), ("curl", 20, 7), ("speed", 20, 14),
    ("acceleration", 20, 21), ("jump", 24, 0), ("physicalContact", 24, 7),
    ("balance", 24, 14), ("stamina", 24, 21), ("ballWinning", 28, 0),
    ("aggression", 28, 7), ("defensiveProwess", 36, 0), ("headingAbility", 36, 14),
    ("dribbling", 40, 0), ("kickingPower", 44, 13),
]
GK_FIELDS = [
    ("gkAwareness", 28, 14), ("gkCatching", 28, 21), ("gkReach", 32, 0),
    ("gkClearing", 36, 7), ("gkReflexes", 44, 6),
]



# Position-weighted OVR: for each position index, weight per stat (0..24 = 20 generic + 5 gk)
# Order: ap,bc,tp,lp,lf,fn,pk,cr,sp,ac,jm,pc,bl,st,bw,ag,dp,hd,db,kp, gkAwa,gkCat,gkRea,gkCle,gkRef
POS_WEIGHTS = {
    0:  [0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0, 0.3,0.2,0.1,0.1,0.3],  # GK
    1:  [0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0909,0.0455,0.0455,0.1818,0.0455,0.0909,0.1364,0.0455,0.1818,0.0909,0.0,0.0453, 0,0,0,0,0],  # CB
    2:  [0.0,0.0,0.0,0.0833,0.0833,0.0,0.0,0.0,0.1667,0.0833,0.0417,0.0417,0.0417,0.125,0.0833,0.0417,0.125,0.0417,0.0,0.0416, 0,0,0,0,0],  # LB
    3:  [0.0,0.0,0.0,0.0833,0.0833,0.0,0.0,0.0,0.1667,0.0833,0.0417,0.0417,0.0417,0.125,0.0833,0.0417,0.125,0.0417,0.0,0.0416, 0,0,0,0,0],  # RB
    4:  [0.0,0.04,0.04,0.08,0.08,0.0,0.0,0.0,0.04,0.04,0.04,0.12,0.04,0.12,0.16,0.04,0.12,0.04,0.0,0.0, 0,0,0,0,0],  # DMF
    5:  [0.0435,0.0869,0.0869,0.0869,0.0869,0.0435,0.0435,0.0435,0.0435,0.0435,0.0435,0.0435,0.0869,0.0869,0.0,0.0,0.0,0.0,0.0869,0.0437, 0,0,0,0,0],  # CMF
    6:  [0.0435,0.0869,0.0869,0.0869,0.0869,0.0435,0.0,0.0435,0.1305,0.0869,0.0,0.0435,0.0435,0.1305,0.0,0.0,0.0,0.0,0.087,0.0, 0,0,0,0,0],  # LMF
    7:  [0.0435,0.0869,0.0869,0.0869,0.0869,0.0435,0.0,0.0435,0.1305,0.0869,0.0,0.0435,0.0435,0.1305,0.0,0.0,0.0,0.0,0.087,0.0, 0,0,0,0,0],  # RMF
    8:  [0.0869,0.1305,0.0869,0.0869,0.0869,0.0869,0.0435,0.0435,0.0435,0.0435,0.0,0.0435,0.0435,0.0435,0.0,0.0,0.0,0.0,0.0869,0.0436, 0,0,0,0,0],  # AMF
    9:  [0.08,0.08,0.08,0.04,0.04,0.12,0.04,0.04,0.12,0.08,0.04,0.04,0.04,0.04,0.0,0.0,0.0,0.0,0.08,0.04, 0,0,0,0,0],  # LWF
    10: [0.08,0.08,0.08,0.04,0.04,0.12,0.04,0.04,0.12,0.08,0.04,0.04,0.04,0.04,0.0,0.0,0.0,0.0,0.08,0.04, 0,0,0,0,0],  # RWF
    11: [0.1154,0.0769,0.0769,0.0385,0.0385,0.1154,0.0385,0.0385,0.0769,0.0385,0.0385,0.0385,0.0385,0.0385,0.0,0.0,0.0,0.0385,0.0769,0.0766, 0,0,0,0,0],  # SS
    12: [0.1154,0.0385,0.0385,0.0385,0.0385,0.1538,0.0385,0.0385,0.0769,0.0385,0.0385,0.0769,0.0385,0.0385,0.0,0.0,0.0,0.0769,0.0385,0.0766, 0,0,0,0,0],  # CF
}

# Height bonus per position (OVR points per 10cm above 175cm)
HEIGHT_BONUS = {
    0: 0.8,   # GK
    1: 0.4,   # CB
    4: 0.15,  # DMF
    12: 0.35, # CF
}

POSITION_PROFS = [
    ("GK", 40, 13), ("CB", 40, 15), ("LB", 40, 17), ("RB", 40, 19),
    ("DMF", 40, 21), ("CMF", 40, 23), ("LMF", 40, 25), ("RMF", 40, 27),
    ("AMF", 40, 29), ("RWF", 44, 0), ("SS", 44, 2), ("CF", 44, 4),
    ("LWF", 44, 20),
]

SKILL_NAMES = [
    "scissorsFeint", "doubleTouch", "flipFlap", "marseilleTurn",
    "sombrero", "crossOverTurn", "cutBehindAndTurn", "scotchMove",
    "stepOnSkillControl", "headingSkill", "longRangeDrive", "chipShotControl",
    "longRangeShooting", "knuckleShot", "dippingShot", "risingShot",
    "acrobaticFinishing", "heelTrick", "firstTimeShot", "oneTouchPass",
    "throughPassing", "weightedPass", "pinpointCrossing", "outsideCurler",
    "rabona", "noLookPass", "lowLoftedPass", "gkLowPunt",
    "gkHighPunt", "longThrow", "gkLongThrow", "penaltySpecialist",
    "gkPenaltySaver", "gamesmanship", "manMarking", "trackBack",
    "interception", "acrobaticClear", "captaincy", "superSub",
    "fightingSpirit", "trickster", "mazingRun", "speedingBullet",
    "incisiveRun", "longBallExpert", "earlyCross", "longRanger",
]

SKILL_BITS = [
    (48, 6), (48, 7), (48, 8), (48, 9), (48, 10), (48, 11), (48, 12), (48, 13),
    (48, 14), (48, 15), (48, 16), (48, 17), (48, 18), (48, 19), (48, 20), (48, 21),
    (48, 22), (48, 23), (48, 24), (48, 25), (48, 26), (48, 27), (48, 28), (48, 29),
    (48, 30), (48, 31),
    (52, 0), (52, 1), (52, 2), (52, 3), (52, 4), (52, 5), (52, 6), (52, 7),
    (52, 8), (52, 9), (52, 10), (52, 11), (52, 12), (52, 13), (52, 14),
    (44, 31), (48, 0), (48, 1), (48, 2), (48, 3), (48, 4), (48, 5),
]
assert len(SKILL_BITS) == 48

POS_ORDER = ["GK","CB","LB","RB","DMF","CMF","LMF","RMF","AMF","LWF","RWF","SS","CF"]

def read_bitfield(data, byte_offset, bit_offset, bit_length):
    val = 0
    first_byte = byte_offset + bit_offset // 8
    first_bit = bit_offset % 8
    for i in range(bit_length):
        byte_idx = first_byte + (first_bit + i) // 8
        bit_idx = (first_bit + i) % 8
        val |= ((data[byte_idx] >> bit_idx) & 1) << i
    return val

def extract_players(data, shirt_numbers):
    players = []
    players_start = PLAYERS_START
    for i in range(MAX_PLAYERS):
        rec_start = players_start + i * PLAYER_RECORD_LEN
        if rec_start + PLAYER_RECORD_LEN > len(data):
            break
        rec = data[rec_start:rec_start + PLAYER_RECORD_LEN]
        pid = struct.unpack_from('<I', rec, 0)[0]
        if pid == 0:
            continue
        pname = read_string(rec, 54, 61)
        club_shirt = read_string(rec, 115, 61)
        nt_shirt = read_string(rec, 176, 61)
        height = rec[10] if rec[10] != 0 else None
        weight = rec[11] if rec[11] != 0 else None
        stat_vals = {name: read_bitfield(rec, bo, bi, 7) for name, bo, bi in STAT_FIELDS}
        gk_vals = {name: read_bitfield(rec, bo, bi, 7) for name, bo, bi in GK_FIELDS}
        profs = {name: read_bitfield(rec, bo, bi, 2) for name, bo, bi in POSITION_PROFS}
        stronger_foot = read_bitfield(rec, 44, 29, 1)
        wf_usage = read_bitfield(rec, 12, 30, 2)
        wf_accuracy = read_bitfield(rec, 36, 30, 2)
        form = read_bitfield(rec, 28, 28, 3)
        injury = read_bitfield(rec, 40, 7, 2)
        skills_lo = 0
        skills_hi = 0
        skills = []
        for j, (bo, bi) in enumerate(SKILL_BITS):
            if read_bitfield(rec, bo, bi, 1):
                skills.append(SKILL_NAMES[j])
                if j < 32:
                    skills_lo |= (1 << j)
                else:
                    skills_hi |= (1 << (j - 32))
        registered_idx = read_bitfield(rec, 32, 13, 4)
        registered = POS_ORDER[registered_idx] if registered_idx < len(POS_ORDER) else registered_position(profs, pname, {**stat_vals, **gk_vals, "height": height or 175, "registeredPosition": "AMF"})
        players.append({
            "playerId": pid,
            "name": pname,
            "clubShirtName": club_shirt,
            "ntShirtName": nt_shirt,
            "height": height,
            "weight": weight,
            "shirtNumber": shirt_numbers[i] if i < len(shirt_numbers) else 99,
            "registeredPosition": registered,
            "positionProfs": profs,
            "strongerFoot": stronger_foot,
            "weakFootUsage": wf_usage,
            "weakFootAccuracy": wf_accuracy,
            "form": form,
            "injuryResistance": injury,
            "skillsLo": skills_lo,
            "skillsHi": skills_hi,
            "skills": skills,
            **stat_vals,
            **gk_vals,
        })
    return players

def registered_position(profs, name="", stats=None):
    candidates = [(pos, profs.get(pos, 0)) for pos in POS_ORDER]
    eligible = [pos for pos, v in candidates if v >= 2]
    if not eligible:
        # Cap posició té prof ≥2; tornar la de valor més alt
        return max(candidates, key=lambda x: x[1])[0]
    if len(eligible) == 1:
        return eligible[0]
    # Múltiples posicions viables: triar la que doni OVR més alt
    if stats is None:
        return eligible[0]
    best_pos = eligible[0]
    best_ovr = -1
    for pos in eligible:
        s = dict(stats)
        s["registeredPosition"] = pos
        o = player_ovr(s)
        if o > best_ovr:
            best_ovr = o
            best_pos = pos
    return best_pos

ALL_STAT_KEYS = [s[0] for s in STAT_FIELDS] + [s[0] for s in GK_FIELDS]
GENERIC_STAT_KEYS = [s[0] for s in STAT_FIELDS]

def player_ovr(stats):
    pos_name = stats["registeredPosition"]
    pos_idx = POS_ORDER.index(pos_name) if pos_name in POS_ORDER else 5
    w = POS_WEIGHTS.get(pos_idx, POS_WEIGHTS[5])
    height = stats.get("height", 175) or 175
    h_bonus = HEIGHT_BONUS.get(pos_idx, 0.0) * max(0, (height - 175) / 10)
    if pos_idx == 0:
        gk_part = sum(stats[k] * w[i] for i, k in enumerate(ALL_STAT_KEYS))
        gen_avg = sum(stats[k] for k in GENERIC_STAT_KEYS) / len(GENERIC_STAT_KEYS)
        total = 0.85 * gk_part + 0.15 * gen_avg
        total = total * 0.96
    else:
        total = sum(stats[k] * w[i] for i, k in enumerate(ALL_STAT_KEYS))
    return round(total + h_bonus, 1)

def team_ovr(players):
    if not players:
        return 0, {}
    ovrs = [player_ovr(p) for p in players]
    avg = sum(ovrs) / len(ovrs)
    per_stat = {k: round(sum(p[k] for p in players) / len(players), 1) for k in ALL_STAT_KEYS}
    return round(avg, 1), per_stat

def select_starting_xi(players, formation_positions):
    if not players:
        return players
    free = list(players)
    starters = [None] * 11
    pos_names = POS_ORDER
    used = set()

    for slot, pos_val in enumerate(formation_positions):
        if pos_val < 0 or pos_val >= len(pos_names):
            continue
        target = pos_names[pos_val]
        candidates = [i for i, p in enumerate(free) if i not in used and p["registeredPosition"] == target]
        if not candidates:
            candidates = [i for i, p in enumerate(free) if i not in used and p["positionProfs"].get(target, 0) >= 2]
        if not candidates:
            candidates = [i for i, p in enumerate(free) if i not in used and p.get("ovr", 0) > 0]
        if candidates:
            best = max(candidates, key=lambda i: free[i].get("ovr", 0))
            used.add(best)
            starters[slot] = free[best]

    starters = [s for s in starters if s is not None]
    bench = [p for i, p in enumerate(free) if i not in used]
    bench.sort(key=lambda p: p["shirtNumber"] if p["shirtNumber"] and 1 <= p["shirtNumber"] <= 99 else 999)
    return starters + bench

def extract_ted(filepath):
    with open(filepath, "rb") as f:
        raw = bytearray(f.read())
    if len(raw) != 14820:
        return None
    data = decrypt(raw)
    team_start = 80
    team_name = read_string(data, team_start + 104, 70)
    short_name = read_string(data, team_start + 174, 4)
    stadium = read_string(data, team_start + 178, 120)
    country = read_string(data, team_start + 14, 2)
    assignment = data[756:1040]
    shirt_numbers = list(struct.unpack_from('<40H', assignment, 164))
    players = extract_players(data, shirt_numbers)
    for pl in players:
        pl["ovr"] = player_ovr(pl)
    tactics = data[1040:1668]
    formation_positions = list(tactics[4:15])
    players = select_starting_xi(players, formation_positions)
    ovr, per_stat = team_ovr(players)
    return {
        "teamName": team_name,
        "shortName": short_name,
        "stadium": stadium,
        "playerCount": len(players),
        "players": players,
        "ovr": ovr,
        "perStat": per_stat,
    }

def find_ted_files(root):
    results = []
    for dirpath, _, filenames in os.walk(root):
        for f in filenames:
            if f.lower().endswith('.ted'):
                results.append(os.path.join(dirpath, f))
    return results

def main():
    base = os.path.dirname(os.path.abspath(__file__))
    DATA_DIR = os.path.join(base, "data")
    FULL_TO_FOLDER_ID = {
        'BEST OF WORLD CUPS - 195 TEAMS - PES 2021':'bestWorldCups',
        'SUPER LEAGUE - PES 2021 - 194 CLASSIC TEAMS':'superLeague',
        'SUPER PATCH 250 TEAMS + 53 INTERNATIONAL TEAMS - PES 2021 - MESTRE KAMIKA':'superPatch',
        'Super Patch 80s - Option File - PES 2021 - Mestre Kamika':'superPatch80s',
        'SUPER PATCH 1990S - PES 2021 - OPTION FILE - MESTRE KAMIKA':'superPatch90s',
    }
    os.makedirs(DATA_DIR, exist_ok=True)
    output = []
    for folder in TEAM_DIRS:
        folder_path = os.path.join(base, folder)
        if not os.path.isdir(folder_path):
            continue
        ted_files = find_ted_files(folder_path)
        teams_in_folder = []
        for ted_path in ted_files:
            rel = os.path.relpath(ted_path, folder_path)
            parts = rel.replace('\\', '/').split('/')
            result = extract_ted(ted_path)
            if result:
                teams_in_folder.append({
                    "subfolder": parts[0] if len(parts) > 1 else "",
                    "file": os.path.basename(ted_path),
                    **result,
                })
        output.append({
            "patch": folder,
            "teams": teams_in_folder,
        })
        print(f"  {folder}: {len(teams_in_folder)} teams extracted", file=sys.stderr)

    # Star ratings based on fixed OVR thresholds (0-127 scale, position-weighted)
    def star_from_ovr(ovr):
        if ovr <= 0: return 1
        if ovr <  76: return 1
        if ovr <  79: return 2
        if ovr <  81: return 3
        if ovr <  83: return 4
        return 5

    for p in output:
        for t in p["teams"]:
            t["starRating"] = star_from_ovr(t["ovr"])

    out_path = os.path.join(DATA_DIR, "ted_data.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    print(f"Done! {sum(len(p['teams']) for p in output)} total teams written to {out_path}", file=sys.stderr)

    light = []
    full_per_patch = {}
    player_index = []
    for p in output:
        patch_key = p["patch"]
        light_teams = []
        patch_full = {}
        for t in p["teams"]:
            team_key = patch_key + "::" + t["teamName"]
            light_teams.append({
                "teamKey": team_key,
                "teamName": t["teamName"],
                "playerCount": t["playerCount"],
                "starRating": t["starRating"],
            })
            full_entry = {
                "teamName": t["teamName"],
                "shortName": t["shortName"],
                "stadium": t["stadium"],
                "ovr": t["ovr"],
                "starRating": t["starRating"],
                "players": [],
            }
            for di, pl in enumerate(t["players"]):
                pl_ovr = round(player_ovr(pl), 1)
                full_entry["players"].append({
                    "n": pl["name"],
                    "s": pl["shirtNumber"],
                    "p": POS_ORDER.index(pl["registeredPosition"]),
                    "h": pl["height"],
                    "w": pl["weight"],
                    "wfU": pl["weakFootUsage"],
                    "wfA": pl["weakFootAccuracy"],
                    "sf": pl["strongerFoot"],
                    "f": pl["form"],
                    "i": pl["injuryResistance"],
                    "sl": pl["skillsLo"],
                    "sh": pl["skillsHi"],
                    "pp": sum((pl["positionProfs"].get(p,0)&3)<<(i*2) for i,p in enumerate(POS_ORDER)),
                    "o": pl_ovr,

                    "ap": pl["attackingProwess"],
                    "bc": pl["ballControl"],
                    "tp": pl["tightPossession"],
                    "lp": pl["lowPass"],
                    "lf": pl["loftedPass"],
                    "fn": pl["finishing"],
                    "pk": pl["placeKicking"],
                    "cr": pl["curl"],
                    "sp": pl["speed"],
                    "ac": pl["acceleration"],
                    "jm": pl["jump"],
                    "pc": pl["physicalContact"],
                    "bl": pl["balance"],
                    "st": pl["stamina"],
                    "bw": pl["ballWinning"],
                    "ag": pl["aggression"],
                    "dp": pl["defensiveProwess"],
                    "hd": pl["headingAbility"],
                    "db": pl["dribbling"],
                    "kp": pl["kickingPower"],
                    "ga": pl["gkAwareness"],
                    "gc": pl["gkCatching"],
                    "gr": pl["gkReach"],
                    "gl": pl["gkClearing"],
                    "gx": pl["gkReflexes"],
                })
                player_index.append({
                    "n": pl["name"],
                    "o": pl_ovr,
                    "p": POS_ORDER.index(pl["registeredPosition"]),
                    "tk": team_key,
                    "di": di,
                    "sf": pl["strongerFoot"],
                    "sl": pl["skillsLo"],
                    "sh": pl["skillsHi"],
                })
            patch_full[team_key] = full_entry
        full_per_patch[patch_key] = patch_full
        light.append({
            "patch": p["patch"],
            "teams": light_teams,
        })
    js_light = {
        "teams": light,
        "players": player_index,
    }
    light_path = os.path.join(DATA_DIR, "light.json")
    with open(light_path, "w", encoding="utf-8") as f:
        json.dump(js_light, f, ensure_ascii=False)
    print(f"  Light JSON ({os.path.getsize(light_path)//1024}KB) written to {light_path}", file=sys.stderr)

    full_dir = os.path.join(DATA_DIR, "full")
    os.makedirs(full_dir, exist_ok=True)
    for patch_name, patch_data in full_per_patch.items():
        folder_id = FULL_TO_FOLDER_ID.get(patch_name, patch_name.replace(' ', '_'))
        full_path = os.path.join(full_dir, folder_id + ".json")
        with open(full_path, "w", encoding="utf-8") as f:
            json.dump(patch_data, f, ensure_ascii=False)
        print(f"  Full JSON ({os.path.getsize(full_path)//1024}KB) written to {full_path}", file=sys.stderr)

if __name__ == "__main__":
    main()
