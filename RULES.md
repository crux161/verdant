# Verdant — Rules

> Binding rules for everyone and everything working in this repository, human or agent.
> These sit above convenience. If a rule and a task conflict, the rule wins.
> Companion docs: [PLAN.md](PLAN.md) (what we build), [LEXICON.md](LEXICON.md) (names), [whitepapers/README.md](whitepapers/README.md) (the research→development contract).

---

## Rule 0 — Never ship Nintendo's code

Nothing derived from Nintendo's code is ever committed to a Verdant codebase or
distributed in any form: no firmware, keys, binaries, decompiled or disassembled
listings, lifted IR, recompiled binaries, analysis databases, or byte sequences
copied out of Nintendo binaries (including search patterns). Reverse engineering
exists to *understand*, never to *copy*.

## Rule C — Containment (the `RESOURCES/` workspace)

`RESOURCES/` is the **research workspace** (the Observatory in [PLAN.md](PLAN.md)).

1. **Nothing leaves it.** No file, excerpt, hash of proprietary content, or
   verbatim value from inside `RESOURCES/` is copied anywhere else, under any
   circumstance.
2. **It is never committed and never pushed.** It is force-ignored by
   [.gitignore](.gitignore). That ignore entry is a safety belt, not the policy —
   the policy is this rule.
3. **All research happens only inside it.** Any handling of research material —
   unpacking, analysis, decompilation, instrumentation, and *all testing against
   research material* — occurs only inside `RESOURCES/`. Research tooling runs
   there and writes its scratch output there.
4. **Outside `RESOURCES/`, its contents are called "research."** No committed
   document names, quotes, or characterizes the specific proprietary artifacts.
   "The research shows service X returns …" — never "the firmware binary at …".

## Rule P — Research and Development never mix

A single task — and the agent, session, and pull request that carry it — is
**either Research or Development, never both.**

- **Research** reads the research workspace and public references; it produces
  **White Papers** only (see Rule W). It writes no product code.
- **Development** reads White Papers and public sources; it writes Verdant's code,
  tests, tools, and docs. It never reads the research workspace.

No person or agent performs a Development task for a module whose research
workspace material they have handled. (The clean-room partition in
[PLAN.md](PLAN.md) §1 / P0.6 is the full form of this rule.)

## Rule W — White Papers are the only bridge

Research hands work to Development **only** through a White Paper
([whitepapers/](whitepapers/)).

1. **Self-sufficiency.** The White Paper a developer receives must contain
   everything needed to implement its slice to the point of reproducibility —
   **without exception and without any access to the research workspace.** If a
   developer would have to open `RESOURCES/` to finish, the White Paper is
   incomplete and must be sent back.
2. **Behavior, not code.** A White Paper describes *what a component does* —
   interfaces, data layouts, constants required for interoperability, formats,
   result codes, state machines, algorithms in prose, ordering/timing/error
   behavior, acceptance criteria, and synthetic test vectors. It contains **no
   code or pseudocode in any language**, no decompiler output, and no transcribed
   proprietary data (Rule 0).
3. **Shared core docs.** Common material lives once in
   [whitepapers/_core/](whitepapers/_core/) and is referenced by ID, so slices do
   not repeat it and multiple contributors stay consistent.
4. **Provenance.** Every White Paper records where its facts come from. Clean-room
   practice: facts are drawn from public interoperability references and from
   behavioral observation; firmware-specific values that still need confirmation
   are listed in the paper's **Verification Ledger** as open items, never guessed
   silently.

## Rule L — Licensing & provenance

Verdant core is GPL-2.0-only. GPL-3.0 components run only as separate programs,
never linked in. Every vendored upstream records its origin, commit, and license.
See [PLAN.md](PLAN.md) ADR-005 / P0.4.

## Rule N — Names

Use the terms in [LEXICON.md](LEXICON.md) exactly. Never use deny-listed names
(Nintendo-internal codenames, SDK symbols, trademarks) in Verdant identifiers or
committed docs. Keep literal interoperability identifiers byte-exact.

## Rule J — Journal

Every slice of work (research or development) is logged in
[JOURNAL/](JOURNAL/) as it is taken up, worked, and closed. The journal is the
project's running record: what was done, by which side, against which plan IDs,
and what is left open.

---

*Changing a rule is itself a Development-side governance task: edit this file in a
PR that explains why. Rules 0 and C are not weakened without recorded legal
review (PLAN P0.1.4).*
