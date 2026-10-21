<!--
Copy this file to whitepapers/<codename>/NN-<topic>.md and fill every section.
Delete the HTML comments. Obey RULES.md (0, C, P, W) and whitepapers/README.md.
No code or pseudocode. No research-workspace content. Behavior and interfaces only.
-->

---
id: WP-<MODULE>-<NN>
module: <codename>            # LEXICON §4
title: <short title>
analyzed_context: HOS <version>   # the Horizon version the behavior was studied against
reference_firmware: 23.0.1        # project reference (PLAN ADR-004); note deltas if different
status: draft                     # draft | ready | implemented | verified
author: <research agent/contributor id>
boundary_reviewer: <id or "pending">
plan_ids: [<PR.x>, <P6.x>, ...]
cites_core: [CORE-CMIF-IPC, ...]
---

## 1. Scope
<!-- Exactly which services/interfaces/behaviors this paper covers, and what it
explicitly does NOT cover (with pointers to the papers that will). -->

## 2. Role in the system
<!-- What this component is for, who calls it, what it depends on, where it sits
in the Verdant module map. One paragraph, plus a dependency list. -->

## 3. Interface surface
<!-- Every service/port in scope. For each: the interoperability service name
(byte-exact), the IPC flavor (cite CORE-CMIF-IPC), and a command table:
command id | name | purpose | inputs | outputs | buffers | notes.
Mark any command id / value not yet confirmed as (LEDGER-n). -->

## 4. Data model
<!-- The data structures a caller observes, each as a field table:
offset | size | type | name | meaning | valid range.
Behavioral layout for interoperability — never copied bytes. -->

## 5. Behavior & state
<!-- State machines, lifecycle, ordering guarantees, concurrency, events/
notifications and their order, persistence behavior. Prose and mermaid only. -->

## 6. Error behavior
<!-- Result codes (module + description) for each failure condition, and the
exact point in the sequence each is produced. (LEDGER-n) for unconfirmed. -->

## 7. Acceptance criteria
<!-- The conditions a Verdant implementation must meet to be considered a match,
mapped to the parity dimensions in PLAN §1 (functional, error, state, persistent
formats, resource, timing, conditions). -->

## 8. Test vectors
<!-- Concrete, reproducible input→expected-output cases a developer can turn into
tests, built from the synthetic keyset / fixtures (PLAN P0.4.4), never from
research material. -->

## 9. Provenance
<!-- Where each class of fact came from: public references (named), behavioral
observation, or prior White Papers. Enough that another contributor could
re-derive it. -->

## 10. Verification Ledger
<!-- Every open item: firmware-specific values to confirm, behaviors to observe,
ambiguities to resolve. Table: LEDGER-n | item | how to confirm | status.
A paper may ship with open items; it may not ship with silent gaps. -->
