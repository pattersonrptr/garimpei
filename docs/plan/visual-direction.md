# Visual direction (Phase 0)

Decision record, Nov 2026. Chosen by the author from two rounds of mock-ups.

## Decision

**Verdict first, used offers highlighted, gold palette.**

- **Structure** (from "Verdict"): product page opens with a large answer
  ("Buy now" / "Wait") and a bar showing where today's price sits in the last
  90 days.
- **Used highlight** (from "Used in focus"): a savings block right under the
  verdict ("Used from R$ 28.50, 48% less than new R$ 54.90"), then two columns,
  used and new. The new price is the anchor.
- **Look** (from "Garimpo"): gold bar, ink buttons, grotesque headings,
  large prices.

Discarded: a bookstore look with serif headings (categories other than books
are coming), and a dense table-first page (too close to existing comparators).

Known trade-off: gold is also Buscapé's color. Accepted by the author. What
separates Garimpei is the verdict and the used highlight, not the color.

## Tokens

| Token | Value | Use |
|---|---|---|
| `gold` | `#FFC928` | Brand, top bar, text on ink buttons |
| `ink` | `#1A1712` | Text, verdict block, buttons |
| `paper` | `#FFFDF6` | Page background |
| `sand` | `#ECE5D2` | Cards, borders, savings block |
| `muted` | `#6A6355` | Secondary text |
| `good` | `#1F7A3D` | Good price, savings |
| `bad` | `#C2452F` | Expensive end of the bar |

| Token | Value |
|---|---|
| Display font (headings, prices) | Bricolage Grotesque 800 |
| Text font | DM Sans 400 / 500 / 700 |
| Radius | 12px (cards 12-18px) |
| Spacing scale | 4 · 8 · 12 · 16 · 24 · 32 |

## Rules

- Gold is for brand and the top bar. Buttons and the verdict block are ink with
  gold text.
- Green and red only mean good or expensive price, never decoration.
- Position bar: green (lowest) → gold → red (highest), white marker at the
  current price.
- No used offers: the savings block disappears and the verdict stands alone.
- Not enough history: the verdict says "still collecting data", never a guess.
- Always show "updated X hours ago".

## Open

- Dark theme: not defined; decide when building the Next.js app (Phase 3).
- Logo: keep the purple pirate flag or redraw it with the gold.
- Author's own reference prints: not received; compare when they arrive.
