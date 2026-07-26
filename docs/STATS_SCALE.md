# Escala de Stats: 0–127 (valors crus del .ted)

## Per què 0–127?

Cada stat al fitxer `.ted` del PES 2021 ocupa **7 bits** en el binari (bitpacking).
Amb 7 bits podem representar 2⁷ = 128 valors diferents, de 0 a 127.

Els 20 stats genèrics i els 5 stats de porter estan codificats així al disc:

```python
stat = read_bitfield(rec, byte_offset, bit_offset, 7)  # → valor 0–127
```

Aquests valors es mostren **sense cap escala** — són el valor cru que surt del fitxer.

## Per què no escalar a 0–99?

El PES al joc aplica una corba no lineal per mostrar stats 0–99 a pantalla,
però no tenim accés a aquesta corba. Un escalat lineal 0–127 → 0–99 faria
que cap jugador arribés a 99 (el màxim real al .ted és ~120), i els grans
jugadors semblarien tenir stats baixos (p. ex. velocitat 120 → 93).

Per tant, mostrem els valors crus 0–127, que són fidels al fitxer i fan
justícia als millors jugadors (velocitat 120 *es veu* com 120).

## Visualització a la UI (límit 100)

Tot i que els valors interns són 0–127, el màxim observat al `.ted` és ~99
(p. ex. Maradona `dribbling` 99, Yashin `gkAwareness` 98). Per tant, el
radar i les barres usen **100 com a límit** pràctic:

- **Barres**: `Math.min(v, 100)` per al percentatge d'ample.
- **Gràfic radar**: `max: 100`, ticks cada 20.
- **Tooltip**: mostra valor seguit de `/ 100`.
- **Nota al modal**: "Valors 0–100 (màxim observat ~99)".

## Càlcul de l'OVR

L'OVR per jugador és una **mitjana ponderada** dels 25 stats (20 genèrics + 5 de
porter) amb pesos específics per posició (vegeu `POS_WEIGHTS` a `extract_teams.py`).
Els pesos estan normalitzats per sumar 1.0. Pels porters, s'hi afegeix un 15%
de mitjana genèrica per no sobrevalorar-los respecte als jugadors de camp.

L'OVR d'equip és la mitjana aritmètica dels OVR individuals dels jugadors.

## Fórmula real de Konami (per referència)

Segons anàlisi de la comunitat (Mimo, r/pesmobile, eFootball Edge), Konami
calcula l'OVR amb aquests principis:

1. **Suma lineal per posició**: OVR = `baseline + Σ weight_i · max(0, stat_i − baseline)`
   - Coeficients específics per a cada una de les 13 posicions
   - Tots els coeficients ≥ 0 (mai un stat pot rebaixar l'OVR)
2. **"25-point rule"** (eFootball): el baseline és 25 sobre 99. Només compta
   l'excés per sobre d'aquest llindar. Stats per sota de 25 no penalitzen
   (contribueixen 0).
3. **L'alçada** del jugador també compta, especialment per GK, CB i CF.
4. **Arrodoniment a 0.5**: per sota de 0.5 arrodoneix cap avall, per sobre
   cap amunt.

Adaptat a la nostra escala 0–127, el baseline equivalent seria ~32.
No obstant, amb els nostres pesos normalitzats (suma = 1.0), aplicar el
"25-point rule" dona resultats idèntics a la mitjana ponderada actual, ja
que tots els stats rellevants estan per sobre del baseline.

Si en el futur es volguessin millorar els càlculs, caldria:
- Obtenir els coeficients exactes de Konami per a cada posició
- Incorporar l'alçada com a variable
- Ajustar el baseline a 32 per la nostra escala

## Estrelles

Els llindars d'estrelles són:

| OVR      | Estrelles |
|----------|-----------|
| < 76     | ★         |
| < 79     | ★★        |
| < 81     | ★★★       |
| < 83     | ★★★★      |
| ≥ 83     | ★★★★★     |
