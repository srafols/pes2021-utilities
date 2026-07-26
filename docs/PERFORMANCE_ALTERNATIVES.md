# Avaluació d'Alternatives de Càrrega de Dades

> **Decisió final:** El projecte implementa l'opció 3 (JSON per patch via `fetch()`).
> Els fitxers `.js` originals (`ted_data_light.js`, `ted_data_full.js`) s'han substituït
> per `data/light.json` + `data/full/*.json`. Cal un servidor HTTP per funcionar.

> Datasets: `data/light.json` (3.8 MB), `data/full/*.json` (~1–3 MB per patch)
> Restricció original: funcionar des de `file://`. L'actual implementació usa `fetch()` i requereix HTTP.

---

## 1. Opció actual — JS object literals via `<script>`

S'empaqueten com a `var TED_DATA = {...}` i `var TED_FULL = {...}`, carregats amb
etiquetes `<script src="...">`.

**Pros:**
- Funciona a `file://` sense excepcions
- Càrrega síncrona i previsible
- Sense eines de build ni dependències extra
- Debug directe a la consola del navegador

**Contres:**
- El JS engine ha de tokenitzar 14 MB de JS, no només parsejar JSON
- Ocupació de memòria: un objecte JS ocupa ~4× la mida del JSON equivalent
- `ted_data_full.js` (9.7 MB) es carrega sempre sencer al primer clic a un equip
- L'Scripting blockeja el main thread durant el parse (0.5–1.5 s per 9.7 MB)

---

## 2. Scripts fragmentats per patch (Recomanat)

En lloc d'un sol `ted_data_full.js` de 9.7 MB, partir-lo en un fitxer per patch:

```
ted_data_full_bestWorldCups.js   ~1.2 MB
ted_data_full_superLeague.js     ~1.3 MB
ted_data_full_superPatch.js      ~2.5 MB
ted_data_full_superPatch80s.js   ~1.8 MB
ted_data_full_superPatch90s.js   ~2.9 MB
```

`ted_data_light.js` es podria reduir traient `sl`/`sh` del `playerIndex` (ja
existeixen al full data), estalviant ~700 KB.

**Pros:**
- Compatible 100% amb `file://` (etiquetes `<script>`)
- Es carrega només el fitxer del patch de l'equip clicat
- Canvi de codi mínim: `loadFullData(cb)` rep `patchId` i injecta el `<script>` correcte
- Redueix la càrrega inicial de 14 MB → 4.2 MB (light)

**Contres:**
- Més fitxers a generar i gestionar
- En un sorteig multi-patch, es podrien arribar a carregar tots els fitxers

**Implementació aproximada:**
```javascript
const FULL_PATCH_FILES = {
  bestWorldCups:  'ted_data_full_bestWorldCups.js',
  superLeague:    'ted_data_full_superLeague.js',
  superPatch:     'ted_data_full_superPatch.js',
  superPatch80s:  'ted_data_full_superPatch80s.js',
  superPatch90s:  'ted_data_full_superPatch90s.js',
};
let loadedPatches = new Set();
function loadPatchData(patchId, cb) {
  if (loadedPatches.has(patchId)) { cb(); return; }
  const s = document.createElement('script');
  s.src = FULL_PATCH_FILES[patchId];
  s.onload = () => { loadedPatches.add(patchId); cb(); };
  document.head.appendChild(s);
}
```

---

## 3. Binary format (ArrayBuffer + DataView)

Dissenyar un format binari amb offsets fixos, strings de longitud prefixada, i
valors numèrics crus (int32, uint16, uint8). Carregar-lo com a base64 dins d'un
script, o com a ArrayBuffer via una etiqueta `<script>` especial.

**Pros:**
- Parsing ~10× més ràpid que JSON (còpia directa de bytes, sense al·locació d'strings)
- Petjada de memòria menor (els números no s'emmagatzemen com a doubles JS)
- Funciona a `file://` si s'usa un script inline base64

**Contres:**
- Cal generar el binari des de Python (script extra)
- Llegibilitat nul·la (no es pot inspeccionar a la consola)
- Strings en llatí-1 vs UTF-8: cal definir una codificació fixa
- Més complexitat a l'hora d'afegir camps nous
- El base64 afegeix ~33% d'overhead

---

## 4. WASM + SQLite (sql.js / sqlite3.wasm)

Carregar el motor WASM de SQLite i una base de dades `.db` pregenerada.

**Pros:**
- Consultes SQL potents (cerques combinades, ordenació, agregats)
- No cal carregar tot el dataset a memòria (només els resultats de la query)

**Contres:**
- **NO funciona** a `file://` en la majoria de navegadors (cal `fetch()` o
  `WebAssembly.instantiateStreaming()` que fallen per CORS)
- Es podria embeure el `.wasm` en base64 (~2 MB extra), però el `.db` també
  s'hauria de carregar via `fetch()` o obrir via `SQL.open()` (fitxer local)
- La càrrega inicial és LENTA: compilar WASM + obrir DB + executar queries
- Per 14 MB de dades i cerques simples (nom + filtres), el benefici és marginal
- Dependència externa (sql.js al CDN o embegut)

**Rendiment esperat:** Pitjor que l'opció actual per al cas d'ús.

---

## 5. JSON via XMLHttpRequest / fetch

Carregar fitxers `.json` purs (sense embolcall `var TED_DATA =`) i parsejar-los.

**Pros:**
- `JSON.parse()` és 2–5× més ràpid que parsejar JS (no cal tokenitzar)
- Fitxers més petits (sense el `var TED_DATA =` prefix)

**Contres:**
- **NO funciona** a `file://` — `XMLHttpRequest` i `fetch` fallen per CORS/Politica
  d'origen en tots els navegadors moderns (Chrome, Firefox, Safari)
- Es podria obrir amb `file://` a Chrome amb flag `--allow-file-access-from-files`,
  però no és una solució viable per a l'usuari final

---

## 6. IndexedDB

Emmagatzemar les dades a IndexedDB després de la primera càrrega.

**Pros:**
- Accés ràpid a subconjunts de dades (cerca per índex)
- No cal recarregar els JS a cada refresh

**Contres:**
- **NO funciona** a `file://` en Firefox ni Safari (sí a Chrome)
- La càrrega inicial requeriria processar tot el dataset per emmagatzemar-lo
- No evita la càrrega inicial dels JS (o caldria un worker, que tampoc funciona
  a `file://`)

---

## Resum

| Opció | Velocitat càrrega | file:// | Complexitat codi | Manteniment | Recomanació |
|-------|:-----------------:|:-------:|:----------------:|:-----------:|:-----------:|
| **Actual** | acceptable | sí | cap | fàcil | ✓ |
| **Scripts fragmentats** | molt bona | sí | baixa | fàcil | ⭐ més recomanat |
| Binary format | excel·lent | sí | mitjana | mitjà | ⭐ alternativa |
| WASM + SQLite | lenta inicial | no fiable | alta | difícil | ✗ |
| JSON via fetch | bona | no | baixa | fàcil | ✗ |
| IndexedDB | bona | no | mitjana | mitjà | ✗ |

**Conclusió:** La fragmentació per patches ofereix el millor balanç de rendiment,
compatibilitat i esforç d'implementació. El format binari seria la següent passa
si es volguessin reduir els temps de parseig al mínim.
