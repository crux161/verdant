# Verdant White Papers

A White Paper is the **only** artifact that crosses from Research to Development
(RULES.md, Rule W). It describes one slice of Horizon behavior precisely enough
that a developer — or a capable coding agent — can reimplement it to the point of
reproducibility **without ever opening the research workspace**.

Written by Research. Consumed by Development. The two never mix (Rule P).

## Layout

```
whitepapers/
  README.md            this file
  TEMPLATE.md          the required shape of a White Paper
  _core/               shared reference docs, cited by ID (write once, reuse)
    README.md
    CMIF-IPC.md        CORE-CMIF-IPC — Horizon IPC conventions
  <codename>/          one directory per Verdant module (LEXICON §4)
    00-overview.md     the module's entry White Paper
    NN-<topic>.md      further White Papers for that module
```

## The completeness contract

A White Paper is **done** only when a developer could implement the slice using
*only* the paper and the core docs it cites. Concretely, before a paper is marked
`ready`, its author confirms:

- every service/interface in scope is listed with its command set;
- every data structure a caller sees is given as a field table (offset, size,
  type, meaning) — behavioral layout, not copied bytes;
- every constant required for interoperability (service names, command IDs,
  result codes, enum values, item keys) is either stated or listed as an open
  item in the Verification Ledger;
- state machines, ordering, and error behavior are described;
- acceptance criteria and synthetic test vectors are given;
- all cited core docs exist;
- nothing in the paper requires reading the research workspace to act on.

If any of these cannot be met, the gap goes in the **Verification Ledger** as an
explicit open item. A paper may ship with open items; it may not ship with
*silent* gaps.

## Rules every White Paper obeys

- **No code.** No source or pseudocode in any language; no decompiler output.
  Describe behavior and interfaces (functional facts), not expression. (Rule 0, Rule W.)
- **No research leakage.** No file names, excerpts, or verbatim values from
  `RESOURCES/`. Refer to it only as "research." (Rule C.)
- **Cite provenance.** Public references by name; behavioral observations as such;
  unconfirmed firmware specifics as Verification-Ledger items.
- **Use LEXICON names.** Verdant codenames for our components; byte-exact literals
  for interoperability identifiers.

## Lifecycle

`draft` → boundary review (a second researcher checks Rules 0/C/W) → `ready` →
picked up by a Development slice → `implemented` → parity-verified → `verified`.
Status lives in the paper's front matter and is mirrored in the journal and the
ledger (PLAN P0.5.3).

## Status index

| ID | Module | Title | Status |
|----|--------|-------|--------|
| CORE-CMIF-IPC | _core | Horizon IPC (HIPC/CMIF/TIPC) conventions | draft |
| WP-ALMANAC-00 | almanac | Settings service — overview & interface surface | draft |
