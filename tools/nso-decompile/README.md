# nso-decompile

A research pipeline that turns a (decompressed) Nintendo Switch NSO — or any
AArch64 ELF — into reassemblable assembly and per-function C, and **proves**
the assembly reconstructs the binary byte-for-byte.

```
NSO ──nso2elf.py──▶ binary.elf          hash-verified ELF64 image
                    (or pass an ELF directly — layout is synthesized)
binary.elf ──reasm.py──▶ asm/rebuild.s  reassembles to a byte-identical
                                          binary (+ rebuilt/rebuilt.elf)
binary.elf ──llvm-objdump──▶ disasm/full.lst   human listing
binary.elf ──analyzeHeadless──▶ ghidra/c/*.c    per-function C
```

`decompile.sh` orchestrates all of it. For the Ghidra stage, a pre-script
(`ghidra_make_functions.java`) sweep-disassembles `.text` and creates
functions at the entry and every branch/call target — required because
stripped NSO images carry no symbols, so auto-analysis alone finds no
functions.

## Requirements

- python3
- LLVM tools on PATH: `llvm-objdump`, `llvm-objcopy`, `llvm-mc`,
  `llvm-readelf` (`brew install llvm`), and `ld.lld` (`brew install lld`)
- optional: python `lz4` module, for LZ4-compressed NSOs
- optional: Ghidra for the C stage. **Use the official release zip** (from
  github.com/NationalSecurityAgency/ghidra/releases) — the Homebrew cask
  ships no native decompiler, so its analyzeHeadless can analyze but every
  decompilation fails with `os/mac_arm_64/decompile does not exist`. Point
  `GHIDRA_HOME` at the extracted official directory (e.g.
  `~/Downloads/ghidra-sre/ghidra_12.2_PUBLIC`); it is also probed
  automatically at that location.

## Usage

```
./decompile.sh <input.nso|input.elf> [outdir] [--no-ghidra] [--only-ghidra]
```

Default outdir: `<input_dir>/decompiled/<input_basename>/`.

```
./decompile.sh firmware/main.elf --no-ghidra   # fast: NSO→ELF→asm+proof
./decompile.sh firmware/main.elf               # …plus the Ghidra C stage
./decompile.sh firmware/main.elf out --only-ghidra  # redo just the C stage
```

## Outputs (in outdir)

```
binary.elf          NSO converted to ELF64 — segments at their original
                    offsets, each SHA256-verified against the header hashes
rebased.elf         same image at base 0 (disassembly input)
layout.json         segment layout metadata
sections/*.bin      raw .text/.rodata/.data images
asm/rebuild.s       the reassemblable assembly
asm/rebuild.ld      linker script (links back at the authentic vaddrs)
rebuilt/rebuilt.elf the rebuilt binary
rebuilt/verify.json verification result
disasm/full.lst     full disassembly with raw bytes, authentic addresses
disasm/strings.txt  printable strings in .rodata/.data with vaddrs
ghidra/c/*.c        one C file per decompiled function (if Ghidra present)
ghidra/symbols.csv  symbol table
REPORT.md           layout table, hashes, verification summary
```

## How the reassembly proof works

1. `reasm.py` disassembles the base-0 ELF. Every operand llvm-objdump
   prints as a bare `0x…` is a pc-relative target and is rewritten as a
   `.L<addr>` label — llvm-mc treats bare constants as *offsets*, not
   addresses, so the label form makes the assembler compute target−pc
   correctly.
2. Labels targeting .rodata/.data/.bss are emitted inside those sections by
   splitting the `.incbin`/`.space` blobs; cross-section references become
   link-time relocations.
3. Assemble (llvm-mc) → link (ld.lld) at the authentic vaddrs → dump each
   section and byte-compare against the original. Any instruction that
   fails to assemble or round-trips to different bytes is replaced by its
   raw `.inst 0x…` encoding and the loop repeats, so the rebuild always
   converges to a byte-identical result.

Verified result (firmware 23.0.0, pgl.nss): `REBUILD: PASS` — 51,933
instructions, 4,640 labels, 6 `.inst` fallbacks, 5 fix rounds; all sections
byte-identical.

## Rules

Per RULES.md: this tooling is for research inside RESOURCES/. Nothing
derived from Nintendo's code — the NSO, the ELF, disassembly, or decompiled
C — is ever committed or distributed. Keep all outputs under RESOURCES/.
