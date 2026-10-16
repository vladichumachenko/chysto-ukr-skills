# Edit types and levels

Every edit has a `type` and a `level`. The review page shows them to the author in Ukrainian
(русизм, калька, жаргон, перебудова; помилка, порада).

## rusism — a Russian word in Ukrainian spelling, or a word used in its Russian meaning

| before | after | note |
|---|---|---|
| задачі кладуться | завдання потрапляють | task = «завдання»; «задача» is a maths problem |
| слідуючий крок | наступний крок | «слідуючий» ← «следующий» |
| співпадає | збігається | «співпадати» ← «совпадать» |

## calque — a Russian (or English) set phrase translated word by word

| before | after | Russian / English source |
|---|---|---|
| щоб двічі не вставати | одразу скажу | чтобы дважды не вставать |
| не взяте зі стелі | не висмоктане з пальця | взято с потолка |
| з найкращих міркувань | з найкращих намірів | из лучших побуждений |

## jargon — IT slang borrowed from Russian; becomes the English term in Latin script

| before | after |
|---|---|
| покласти прод | зламати production |
| зупинило викатку | зупинило rollout |
| вливаю PR | роблю merge PR |

Never replace it with a Ukrainian equivalent («розгортання»). Rewrite the phrase so the
undeclined English word fits.

## restructure — a sentence rewritten for a named defect

See `restructure-rules.md`. The reason must name the defect.

## Levels

- **error** — clearly wrong; applied to `fixed.md`.
- **advice** — debatable but accepted by modern norm (СУМ-20, common usage); shown only.
  Examples: «за замовчуванням» → «типово», «приймати рішення» → «ухвалювати рішення»,
  «в першу чергу» → «насамперед».

Rule of thumb: if a purist source (Караванський, LanguageTool `replace_soft.txt`) proposes
replacing a form that СУМ-20 records as normative, it is advice.
