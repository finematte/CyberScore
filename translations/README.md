# Translations (EN / PL)

Use these files to **verify and edit** all user-facing text.

## Files

- **`ui.json`** – Interface strings (buttons, labels, messages, report narrative).  
  Structure: `"en"` and `"pl"` objects with the same keys.  
  Edit the value for a key in the language you want to change.

- **`content_pl.json`** – Polish-only content for the assessment and report:
  - **`maturity_scale`** – 0–5 scale descriptions (used in the questionnaire).
  - **`areas`** – Area names and descriptions (keyed by `GOVERN`, `IDENTIFY`, `PROTECT`, `DETECT`, `RESPOND`, `RECOVER`).
  - **`questions`** – Question text and description (keyed by e.g. `GOV_Q1`, `ID_Q2`).
  - **`recommendations`** – Recommendation title, description, improvement_tips (keyed by question_id, e.g. `GOV_Q1`).

## How to change language in the app

Use the **EN | PL** buttons in the sidebar. The chosen language applies to the whole app (nav, assessment, results, about).

## Placeholders in `ui.json`

Some values use placeholders, e.g. `"welcome": "Welcome, {username}!"`.  
Do not remove the `{...}` parts; the app replaces them (e.g. `{username}`, `{n}`, `{id}`, `{err}`).
