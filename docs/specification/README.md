# Revised specification: source and build

[THE_VAULT_Cahier_des_charges_v1.3.pdf](../THE_VAULT_Cahier_des_charges_v1.3.pdf) is the revised French specification for release v0.1.3 and Android 0.1.3, build 3. It includes the startup-exit and capture-recovery changes. The original [edition 1.1](../THE_VAULT_Cahier_des_charges_v1.1.pdf) and [18-page initial PDF](../../The_Vaulte_Cahier_des_charges.pdf) are preserved unchanged.

The revised document covers the current architecture, existing-PC MATLAB activation, automatic LAN pairing, differences from the original requirements, security limits, installation, configuration, guided testing, recorded evidence and unfinished acceptance work. It distinguishes implemented behavior from verified behavior and planned targets.

## Edit and regenerate

Edit [specification-v1.3.json](specification-v1.3.json), the UTF-8 content source. Each entry is one logical page; a generated cover precedes them. Supported blocks are paragraphs, headings, tables, bullets, commands, notes, the linked table of contents, and a vector architecture diagram. Paragraphs containing links may use ReportLab `<link href="https://…">label</link>` markup.

From the repository root, use a separate environment so document dependencies do not affect the running app:

```powershell
uv venv --python 3.11 .tools/docs-venv
uv pip install --python .tools/docs-venv/Scripts/python.exe -r docs/requirements.txt
.tools/docs-venv/Scripts/python.exe scripts/build_specification.py
```

On macOS/Linux, replace `.tools/docs-venv/Scripts/python.exe` with `.tools/docs-venv/bin/python`. The PDF generator uses the bundled DejaVu fonts in `docs/fonts`, creates internal navigation and PDF bookmarks, and fails if a page overflows. It does not need MATLAB, a network connection or private server credentials. `--source` and `--output` allow explicit paths. The font licence is included in [LICENSE_DEJAVU](../fonts/LICENSE_DEJAVU); the unmodified fonts come from [Matplotlib's font distribution](https://github.com/matplotlib/matplotlib/tree/main/lib/matplotlib/mpl-data/fonts/ttf).

## Review the result

Open the PDF and check all 23 pages, especially tables and commands. Review page count, text presence, links, outlines and text boundaries, and inspect rendered pages. Review terminology against the code and [validation record](../validation.md) after functional changes; a clean PDF build alone does not validate its claims.

Keep [README.md](../../README.md) and [TESTING.md](../../TESTING.md) consistent with the PDF. Do not change a test from “pending” to “verified” without its evidence and conditions. Preserve the original document and do not publish `.env`, certificates/private keys, licences, signing material, account databases or biometric captures.
