# Implementación — Semilla por dados → wordlist

Plan de tareas para añadir el método de generación de semillas por tiradas de dados
directas a la wordlist BIP-39. El algoritmo y la prueba de uniformidad viven en
`docs/dice_wordlist.md`; esta lista es el seguimiento de la implementación.

## Principios (de cara a la PR)

- **Núcleo aislado:** la matemática/verificación es un helper puro, sin estado y sin
  dependencias de UI, en `seedsigner/helpers/mnemonic_generation.py`. Es la pieza que
  se verifica (tests + `tools/dice_wordlist.py`).
- **UI aditiva:** solo se añaden clases nuevas. No se cambia el comportamiento
  existente; la única edición en código existente es la entrada del menú.
- **Estilo del proyecto:** Views finas que devuelven `Destination`, pantallas
  `@dataclass`, strings con l10n (`ButtonOption` / `_()` / `_mft`), tests pytest.

## Tareas

- [x] **T1 — Helper (núcleo puro).** En `mnemonic_generation.py`:
  - Constantes `DICE_WORDLIST__*` (6 dados, 6 caras, 2048 palabras, divisor 22, bordes 45055/45056).
  - `dice_wordlist_roll_value(roll) -> int`
  - `dice_wordlist_roll_index(roll) -> int | None`
  - `dice_wordlist_roll_word(roll, lang) -> str | None`
  - `generate_mnemonic_from_dice_wordlist(rolls, num_words, lang) -> list[str]`
  - Reutiliza `calculate_checksum` para la última palabra.
  - *Criterio:* funciones puras; validan entrada (`ValueError`); sin imports de UI.

- [x] **T2 — Tests del helper.** En `tests/test_mnemonic_generation.py` (estilo plano):
  - Vectores canónicos 12/24 (frase exacta + `mnemonic_is_valid`).
  - Bordes: `(1,1,1,1,1,1)`→`abandon`, `(6,5,5,4,4,2)`→`zoo`; rechazos `(6,5,5,4,4,3)`, `(6,6,6,6,6,6)`.
  - Uniformidad: los 45056 values válidos dan cada índice 0..2047 exactamente 22 veces.
  - `ValueError` para input inválido (longitud, dígitos, nº de palabras).
  - *Criterio:* `pytest tests/test_mnemonic_generation.py` verde.

- [x] **T3 — Pantalla de entrada.** `ToolsDiceWordlistRollScreen(KeyboardScreen)` en
  `tools_screens.py`: teclado de 6 caras, `return_after_n_chars=6`, título `"Word {}/{}"`.
  - *Criterio:* mismo estilo que `ToolsDiceEntropyEntryScreen`; compila.

- [x] **T4 — Vistas.** En `tools_views.py`:
  - `ToolsDiceWordlistMnemonicLengthView` (selector 12/24).
  - `ToolsDiceWordlistEntryView` (bucle roll→evaluar→feedback→repetir N; luego
    `calculate_checksum`→`Seed`→`SeedWordsWarningView` con `clear_history=True`).
  - Feedback con `LargeIconStatusScreen` (palabra en vivo [SUCCESS] / rechazo [WARNING]);
    aviso breve en la última palabra; `show_back_button=False`.
  - Añadir import de `LargeIconStatusScreen`; import perezoso de la pantalla en `run()`.
  - *Criterio:* compila; flujo coherente.

- [x] **T5 — Menú.** En `ToolsMenuView`: `DICE_WORDLIST = ButtonOption("New seed (dice words)", DICE_SIX)`,
  añadir a `button_data`, y el `elif` → `ToolsDiceWordlistMnemonicLengthView`.
  - *Criterio:* la opción aparece y enlaza.

- [x] **T6 — l10n.** Cadenas nuevas envueltas (`_()` / `ButtonOption` / `_mft` +
  `# TRANSLATOR_NOTE:`). Verificado con `python setup.py extract_messages` que las 7
  cadenas nuevas son detectadas correctamente.
  - **Decisión (aislamiento de PR):** no se commitea el `.pot` regenerado. El
    `l10n/messages.pot` actual estaba desactualizado; la regeneración, además de mis
    cadenas, arrastra strings ajenos (drift preexistente: `"Version"`, `"{}/{}"`,
    `"Collecting entropy frames"` + reorden de strings de psbt). El runtime funciona
    con fallback a inglés (gettext devuelve la cadena tal cual si no hay traducción).
  - *Paso pre-merge:* `python setup.py extract_messages` para añadir las cadenas nuevas
    a `l10n/messages.pot` (y resolver el drift preexistente por separado).
  - No commitear el submódulo `seedsigner-translations`.

- [x] **T7 — Test de flujo.** En `tests/test_flows_tools.py` (`FlowTest`/`FlowStep`),
  tres tests: happy path 12p; rama de rechazo (roll inválido → re-roll → válido); y 24
  palabras. El harness de `tests/base.py` admite `screen_return_values` (lista de
  retornos sucesivos, uno por llamada a `run_screen()`), necesario porque
  `ToolsDiceWordlistEntryView` llama a `run_screen()` varias veces en un solo `run()`
  (una por palabra + pantalla de feedback).
  - *Criterio:* `pytest tests/test_flows_tools.py` verde.

- [x] **T8 — Verificación.** `pytest` + `python tools/dice_wordlist.py --selftest`.
  - *Criterio:* todo verde en lo afectado; sin regresiones.

---

## Resultados de verificación

> Contajes *point-in-time* (varían con el entorno). Los fallos citados son
> **ambientales y preexistentes** (verificado contra el baseline con `git stash`), no
> causados por el cambio.

- **Helper (T2):** `tests/test_mnemonic_generation.py` → **16 passed** (incluye el test de
  propiedad "solo cambia la última palabra / bits altos preservados" y los vectores canónicos 12/24).
- **Flujo (T7):** `test__dice_wordlist__new_seed__flow`, `..._flow__rejection` y
  `..._flow__24_words` → **passed** (menú → selector → entrada → `SeedWordsWarningView`).
- **Pantalla (T3):** instancia y dataclass válidos; título "Word N/M"; teclado de 6 caras.
- **Selftest:** `python tools/dice_wordlist.py --selftest` → **ALL TESTS PASSED** (importa del
  helper: vectores canónicos, bordes, uniformidad).
- **Suite completa:** los fallos restantes son **ambientales y preexistentes**, no causados por el cambio:
  - Falta la lib nativa `libzbar0` (tests de escaneo QR/PSBT: `Unable to find zbar shared library`).
  - Submódulo `seedsigner-translations` no checkout (tests l10n en español).
  - Test de conexión de cámara (hardware de la Pi).
  - En el entorno canónico (`docker/setup.sh` → `pip3 install -e .`, en la Pi) esas deps existen y los tests pasarían.

## Cambios en archivos (resumen)

| Archivo | Cambio |
|---|---|
| `src/seedsigner/helpers/mnemonic_generation.py` | + constantes `DICE_WORDLIST__*`, + 4 funciones puras; fix: `calculate_checksum` pasa `wordlist` a `mnemonic_from_bytes` |
| `src/seedsigner/gui/screens/tools_screens.py` | + `ToolsDiceWordlistRollScreen(KeyboardScreen)` |
| `src/seedsigner/gui/screens/screen.py` | `LargeIconStatusScreen`: + flag `status_headline_untranslated` (un headline que es dato no se traduce) |
| `src/seedsigner/views/tools_views.py` | + import `LargeIconStatusScreen`, + 2 Views, + entrada de menú (labels desambiguados); validación de `num_words`; la palabra mostrada sin traducir; nota de "dados justos" |
| `tests/test_mnemonic_generation.py` | + 8 tests del helper (incl. test de propiedad) |
| `tests/test_flows_tools.py` | + 3 tests de flujo (happy path, rechazo, 24 palabras) |
| `tests/base.py` | `FlowStep`: + `screen_return_values` (retornos sucesivos por llamada a `run_screen()`) |
| `tools/dice_wordlist.py` | tool de verificación: ahora importa del helper (fuente única, como `tools/mnemonic.py`) |
| `docs/dice_wordlist.md` | algoritmo + vectores + sección "Assumptions and threat model" |
| `docs/dice_wordlist_implementation.md` | este documento |

> `l10n/messages.pot` y el submódulo de traducciones **no** se modifican (ver T6).
