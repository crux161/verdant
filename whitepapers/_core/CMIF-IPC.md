---
id: CORE-CMIF-IPC
title: Horizon IPC conventions (HIPC / CMIF / TIPC)
status: draft
author: research
cites_core: []
---

# CORE-CMIF-IPC — Horizon IPC conventions

Shared reference for every White Paper's **Interface surface** section. Describes
the conventions a reader needs to interpret a command table. It does not restate
per-service commands — those live in each module's paper. This is a behavioral /
protocol reference drawn from public interoperability documentation
(SwitchBrew) and the open libstratosphere `sf` framework.

## 1. Sessions, ports, and services

- A **service** is registered under a short name (≤ 8 bytes, byte-exact) with the
  service manager `sm`. Clients ask `sm` for the name and receive a **session**
  handle to an **IPC object** that exposes commands.
- Commands are dispatched by a numeric **command ID** on that object. A command
  may return new session handles to **sub-objects** (sub-interfaces), which expose
  their own command sets.

## 2. Two wire formats: CMIF and TIPC

Horizon uses two request encodings over the same kernel IPC primitive. White
papers name which one a service uses; the developer needs only the behavioral
distinction below.

- **CMIF** (the older, dominant format): requests carry a 4-byte magic (`"SFCI"`
  on request, `"SFCO"` on response), a command ID, and a body of aligned
  arguments. Supports **domains** (see §4).
- **TIPC** (newer, lighter): command ID is carried in the kernel message tag;
  smaller framing; no domain layer. Used by a subset of services.

A White Paper's command table states: service name, format (CMIF or TIPC), and
per command the ID, the input arguments, the outputs, and any buffers/handles.

## 3. Argument passing

- **Raw arguments** are fixed-size, naturally aligned values in the request/
  response body. A White Paper gives them as a field table (offset, size, type).
- **Buffers** carry variable-size data and are described by *descriptor type*:
  - **type A** — input, mapped;
  - **type B** — output, mapped;
  - **type X** — input, pointer;
  - **type C** — output, pointer.
  White papers refer to these by letter and state direction and meaning.
- **Handles** may be **copied** (receiver gets an independent handle) or **moved**
  (sender loses it). White papers state copy vs move per handle.

## 4. Domains

A session may be converted into a **domain**: multiple sub-objects are then
multiplexed over one session, each addressed by a small **object ID**, and
sub-objects are freed explicitly. Behaviorally, a White Paper notes when an
interface hands out sub-objects and whether callers typically domain-convert.

## 5. Result codes

- A result is a 32-bit value split into a **module** number and a **description**
  number; success is a dedicated all-clear value.
- White papers give failures as `(module, description)` pairs with the condition
  that produces each and the point in the sequence it is returned. Unconfirmed
  values are Verification-Ledger items, never guessed.

## 6. What a White Paper must still specify per service

This core doc fixes the *grammar*. Each paper supplies the *vocabulary*:
the byte-exact service name(s), the format, the full command table, the observable
data structures, the state machine, and the result codes — enough to reimplement
without reading research material.

## Provenance

Public interoperability documentation of Horizon IPC (SwitchBrew) and the
open-source libstratosphere `sf` framework (Atmosphère, GPL-2.0). No
research-workspace material.
