**English** · [Українська](README.uk.md)

# chysto — clean Ukrainian, same author

`chysto` (Ukrainian *чисто*, "clean") is an agent skill that cleans a Ukrainian text of
russisms, calques of Russian set phrases, surzhyk, and IT jargon borrowed from Russian slang.
It keeps the meaning and the author's voice, and shows every change with a reason.

This is version 1. The repository is meant to grow into a small set of skills for Ukrainian
writing.

## What it does

Given a Markdown file or the URL of a published article, the skill produces two files:

- **`<name>.review.html`** — the text with every change inline: deleted words struck through in
  red, new words in green, debatable suggestions underlined in yellow. Each change has a
  numbered footnote: its type (russism, calque, jargon, restructure), its level (error or
  advice), the reason, and the source.
- **`<name>.fixed.md`** — the corrected text. Code, formulas, links and Markdown structure are
  left byte for byte.

## Principles

- **Meaning is untouchable.** An edit that shifts the meaning is not made.
- **The author's style stays.** Short sentences, irony, colloquial Ukrainian and the author's own
  imagery are style, not errors.
- **Minimal edit.** Only what can be named as a mistake is changed. A sentence is restructured
  only for a named defect (ambiguity, a calqued construction, a broken logical link, overload).
- **Errors vs advice.** Clear russisms and calques are fixed; purist replacements of words that
  modern usage accepts (e.g. «за замовчуванням» → «типово») are only suggested.
- **Jargon goes English.** Russian-slang IT jargon becomes the English term in Latin script:
  «прод» → production, «викатка» → rollout, «вливаю PR» → «роблю merge PR».
- **English terms and code are never touched.**

## Where it is used

Technical articles and blog posts written in Ukrainian, drafts translated from Russian (by a
person or by a machine), documentation, and any project that keeps Ukrainian texts next to its
code.

## Install

```bash
npx skills add vladichumachenko/chysto-ukr-skills --skill chysto
```

The scripts need only Python 3.9+ — no packages to install.

## Use

Ask your agent to clean a Ukrainian file or article URL, for example "check this article with
chysto". The skill fetches the article if needed, scans it, decides the edits, and writes the
two files next to the source.

To protect your own vocabulary (slang, imagery, product names), put a `chysto-keep.txt` in the
project root, one word or phrase per line. The skill never flags those.

The scripts can be run by hand as well:

```bash
python3 skills/chysto/scripts/fetch.py URL -o article.md
python3 skills/chysto/scripts/scan.py article.md -o candidates.json
# the agent (or you) writes edits.json from the candidates
python3 skills/chysto/scripts/render.py article.md edits.json
```

## Sources

- **LanguageTool**, Ukrainian module (https://github.com/languagetool-org/languagetool),
  commit `c5b1ab8`: replacement tables for russisms and the corrected examples of its barbarism
  rules — `skills/chysto/data/lt-replace.tsv`, about 10,400 entries. Licensed under LGPL 2.1;
  see `skills/chysto/data/NOTICE-languagetool.md`.
- **С. Іваницький, Ф. Шумлянський, «Російсько-український словник»** (Vinnytsia, 1918;
  about 35,000 entries), digitised from a scan of the 2006 reprint — only the dictionary
  entries, which are in the public domain: `skills/chysto/data/slovnik1918.tsv`. The dictionary
  was compiled to separate Ukrainian vocabulary from Russian and gives rows of synonyms with
  stress marks. Much of its vocabulary is archaic today, so it supplies candidates, not
  replacements.
- **The chysto lists** — calques of set phrases and jargon rules collected from real technical
  articles: `chysto-calques.tsv`, `chysto-jargon.tsv`. While writing them, replacements were
  checked against С. Караванський, «Російсько-український словник складної лексики», and
  «Російсько-український словник ділової мови» (1930), both available on
  [r2u.org.ua](https://r2u.org.ua). Their content is not included in this repository.

The modern norm used for decisions is the СУМ-20 dictionary and the 2019 orthography
(Правопис 2019).

## Limitations

- Word matching uses simple ending stripping, not a full morphological dictionary: the scan
  finds candidates broadly, and the agent decides.
- The 1918 dictionary was digitised with OCR; about 6 % of entries are marked as low-confidence.
- Version 1 handles vocabulary, set phrases, jargon and restructuring for named defects. It does
  not check spelling, punctuation or typography on their own.

## Roadmap

Terminology checks, style hints for technical writing, and translation helpers are candidates
for later versions.

## Author and licences

Vladyslav Chumachenko.

- Code and the chysto lists: MIT (`LICENSE`).
- `lt-replace.tsv`: LGPL 2.1, derived from LanguageTool.
- `slovnik1918.tsv`: public domain (1918 dictionary).
