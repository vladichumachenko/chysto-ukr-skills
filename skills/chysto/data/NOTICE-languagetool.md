# LanguageTool-derived data

`lt-replace.tsv` is derived from the Ukrainian module of LanguageTool
(https://github.com/languagetool-org/languagetool), commit `c5b1ab8731dc63b4492f109acafe027be8e21290`:

- `replace.txt` → rows with `level=error`
- `replace_soft.txt` → rows with `level=advice`
- `grammar-barbarism.xml` → corrected `<example>` phrases, `level=error`, rule name as `note`

Transformations: lower-cased patterns, split suggestions on `|`, text after `;` kept as `note`,
duplicates merged (an error entry wins over an advice entry).

LanguageTool is licensed under the GNU Lesser General Public License v2.1 or later;
`lt-replace.tsv` is distributed under the same licence (see `LICENSE-LGPL-2.1.txt`).
