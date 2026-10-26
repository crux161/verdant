#!/usr/bin/env python3
"""reasm.py — disassemble an NSO-derived ELF into reassemblable assembly and
prove it reconstructs the binary byte-for-byte.

Pipeline
--------
1. Dump .text/.rodata/.data from the ELF (raw section images).
2. Disassemble a base-0 copy of the ELF (llvm-objdump).  Every operand
   llvm-objdump prints as a bare `0x…` address is a pc-relative target, so it
   is rewritten as a `.L<addr>` label; the assembler then computes
   target-pc correctly (llvm-mc treats bare constants as *offsets*, not
   addresses).  Bytes that do not disassemble become `.inst 0x…`.
3. Labels whose targets fall inside .rodata/.data/.bss are emitted there by
   splitting the .incbin/.space blobs; cross-section references resolve as
   relocations at link time.
4. Assemble (llvm-mc) → link (ld.lld) at the authentic vaddrs → dump the
   rebuilt sections and cmp them against the originals.
5. Any line that fails to assemble or round-trips to different bytes is
   replaced by its raw `.inst 0x…` encoding and the loop repeats, so the
   rebuild always converges to a byte-identical result.

Usage: reasm.py <binary.elf> <rebased.elf> <layout.json> <outdir>
"""

import json
import os
import re
import subprocess
import sys

# mnemonics whose trailing bare-0x operand is a pc-relative address target
CONVERT = {"b", "bl", "cbz", "cbnz", "tbz", "tbnz", "adr", "adrp",
           "ldr", "ldrsw", "prfm"}
MAX_FIX_ROUNDS = 64


def run(cmd, **kw):
    p = subprocess.run(cmd, capture_output=True, text=True, **kw)
    return p.returncode, p.stdout, p.stderr


def die(msg):
    sys.exit(f"error: {msg}")


# ---------------------------------------------------------------- layout ----
class Layout:
    """Section layout: 0-based vaddrs and contents, from layout.json."""

    def __init__(self, meta):
        self.base = meta["base"]
        self.bss_size = meta["bss_size"]
        self.sec = {}  # name -> {"addr": vaddr0, "size": n, "blob": bytes}
        for seg in meta["segments"]:
            self.sec[seg["name"]] = {"addr": seg["vaddr"] - self.base,
                                     "size": seg["size"], "blob": b""}
        self.sec["bss"] = {"addr": meta["bss_vaddr"] - self.base,
                           "size": self.bss_size,
                           "blob": b"\x00" * self.bss_size}

    def classify(self, target):
        """Which section holds a 0-based address?  None if outside all."""
        for name, s in self.sec.items():
            if s["addr"] <= target < s["addr"] + s["size"]:
                return name
        return None


# -------------------------------------------------------------- disassembly -
def disassemble(rebased_elf, raw):
    """Run llvm-objdump on the base-0 ELF, parse .text into [(addr, insn)].

    llvm-objdump elides runs of zero padding as `...`; those words are
    emitted as byte-exact `.inst 0x0` fallbacks so every word of the section
    is accounted for."""
    rc, out, err = run(["llvm-objdump", "-d", "--no-show-raw-insn",
                        "--no-symbolize-operands", rebased_elf])
    if rc != 0:
        die(f"llvm-objdump failed: {err.strip()}")

    lines, seen = [], False
    ellipsis = False
    prev = None
    for line in out.splitlines():
        if line.startswith("Disassembly of section"):
            seen = line == "Disassembly of section .text:"
            continue
        if not seen or not line.strip():
            continue
        if re.match(r"^\s*\.{3}\s*$", line):
            ellipsis = True
            continue
        m = re.match(r"\s*([0-9a-f]+):\s+(.*)", line)
        if not m:
            continue
        ins = re.sub(r"\s+<[^>]*>\s*$", "", m.group(2))
        ins = re.sub(r"\s*//.*$", "", ins)
        addr = int(m.group(1), 16)
        if ellipsis and prev:
            for a in range(prev[0] + 4, addr, 4):
                if a + 4 <= len(raw):
                    w = raw[a:a + 4]
                    lines.append((a, f".inst "
                                     f"0x{int.from_bytes(w, 'little'):08x}"))
        ellipsis = False
        lines.append((addr, ins))
        prev = (addr, ins)
    return lines


def rewrite(text_words, lines):
    """Label-rewrite pass.  parsed is a list of mutable dicts
    {"addr", "ins", "idx"}; returns (parsed, targets, inst_fallbacks)."""
    parsed, targets, insts = [], set(), 0
    for idx, (addr, ins) in enumerate(lines):
        if idx >= len(text_words):        # ran past the section; ignore
            break
        if "<unknown>" in ins:
            ins = f".inst 0x{int.from_bytes(text_words[idx], 'little'):08x}"
            insts += 1
        else:
            m = re.match(r"^([a-z][a-z0-9.]*)(.*?)\s+0x([0-9a-f]+)$", ins)
            if m and (m.group(1) in CONVERT or
                      m.group(1).startswith("b.")):  # b.eq, b.ls, …
                target = int(m.group(3), 16)
                parts = [p for p in (m.group(1), m.group(2).strip(),
                                     f".L{target:x}") if p]
                ins = "\t".join(parts)
                targets.add(target)
        parsed.append({"addr": addr, "ins": ins, "idx": idx})
    return parsed, targets, insts


def inst_fallback(parsed, text_words, idx):
    """Replace parsed instruction at word idx with its raw .inst encoding."""
    for p in parsed:
        if p["idx"] == idx:
            w = text_words[idx]
            p["ins"] = f".inst 0x{int.from_bytes(w, 'little'):08x}"
            return True
    return False


# ---------------------------------------------------------------- emission --
def emit(parsed, layout, targets):
    """Emit rebuild.s.  Returns (text, line_map): line -> ('insn', word_idx)
    or ('label', target)."""
    s = [".text",
         ".globl _nsotext_start",
         "_nsotext_start:"]
    line_map = {}

    def add(line, tag=None):
        s.append(line)
        if tag:
            line_map[len(s)] = tag

    text_end = layout.sec["rodata"]["addr"]
    text_labels = {t for t in targets if t < text_end}
    for p in parsed:
        if p["addr"] in text_labels:
            add(f".L{p['addr']:x}:", ("label", p["addr"]))
        add(p["ins"], ("insn", p["idx"]))

    for name in ("rodata", "data", "bss"):
        sec = layout.sec[name]
        if sec["size"] == 0:
            continue
        attrs = {"rodata": '.section .rodata,"a",@progbits',
                 "data": '.section .data,"aw",@progbits',
                 "bss": '.section .bss,"aw",@nobits'}[name]
        add(attrs)
        add(f".globl _nso{name}_start")
        add(f"_nso{name}_start:")
        cut = sorted(t for t in targets
                     if sec["addr"] <= t < sec["addr"] + sec["size"])
        pos = 0
        for t in cut:
            n = t - sec["addr"]
            if name == "bss":
                add(f".space {n - pos}")
            else:
                add(f'.incbin "sections/{name}.bin", {pos}, {n - pos}')
            add(f".L{t:x}:", ("label", t))
            pos = n
        if name == "bss":
            add(f".space {sec['size'] - pos}")
        else:
            add(f'.incbin "sections/{name}.bin", {pos}, {sec["size"] - pos}')

    return "\n".join(s) + "\n", line_map


# ------------------------------------------------------------- assemble/link -
def link_script(layout):
    def at(name):
        return f"{layout.sec[name]['addr'] + layout.base:#x}"
    return "\n".join([
        "OUTPUT_ARCH(aarch64)",
        "SECTIONS {",
        f"  . = {layout.base:#x};",
        "  .text   : { *(.text) }",
        f"  . = {at('rodata')};",
        "  .rodata : { *(.rodata) }",
        f"  . = {at('data')};",
        "  .data   : { *(.data) }",
        f"  . = {at('bss')};",
        "  .bss    : { *(.bss) }",
        "}",
    ])


def assemble_and_link(outdir):
    rc, out, err = run(["llvm-mc", "--triple=aarch64-unknown-elf",
                        "-filetype=obj", "asm/rebuild.s", "-o",
                        "asm/rebuild.o"], cwd=outdir)
    if rc != 0:
        return False, err
    rc, out, err = run(["ld.lld", "-T", "asm/rebuild.ld", "-e",
                        "_nsotext_start", "asm/rebuild.o", "-o",
                        "rebuilt/rebuilt.elf"], cwd=outdir)
    if rc != 0:
        return False, "ld.lld: " + err
    return True, ""


def first_mismatch(a, b):
    for i in range(min(len(a), len(b))):
        if a[i] != b[i]:
            return i
    return -1 if len(a) == len(b) else min(len(a), len(b))


def find_usage_line(text, sym):
    """First line that *uses* (does not define) symbol `sym`.  Label names
    differ only in hex digits, so match on non-hex boundaries."""
    defn = sym + ":"
    pat = re.compile(r"(?<![0-9a-fA-F])" + re.escape(sym) +
                     r"(?![0-9a-fA-F])")
    for n, line in enumerate(text.splitlines(), 1):
        if line.strip() == defn:
            continue
        if pat.search(line):
            return n
    return None


def fix_round(parsed, text_words, outdir, layout, targets, insts):
    """Assemble/link/verify loop; self-heals with .inst until byte-identical.
    Returns a result dict."""
    for attempt in range(MAX_FIX_ROUNDS):
        s, line_map = emit(parsed, layout, targets)
        with open(os.path.join(outdir, "asm/rebuild.s"), "w") as f:
            f.write(s)
        ok, err = assemble_and_link(outdir)

        if not ok:
            fixed = False
            m = re.search(r"rebuild\.s:(\d+):", err)
            if m and int(m.group(1)) in line_map:
                tag = line_map[int(m.group(1))]
                if tag[0] == "insn" and inst_fallback(parsed, text_words,
                                                      tag[1]):
                    insts += 1
                    fixed = True
            if not fixed:
                um = re.search(r"undefined (?:temporary )?symbol[: ]"
                               r"(\.L[0-9a-f]+)", err, re.IGNORECASE)
                if um:
                    line = find_usage_line(s, um.group(1))
                    if line and line in line_map and \
                            line_map[line][0] == "insn" and \
                            inst_fallback(parsed, text_words,
                                          line_map[line][1]):
                        insts += 1
                        fixed = True
            if not fixed:
                die(f"assembly/link failed and could not be "
                    f"self-healed:\n{err}")
            continue

        # Verify each section byte-for-byte against the originals.
        retry = False
        all_ok = True
        for name, sec in (("text", layout.sec["text"]),
                          ("rodata", layout.sec["rodata"]),
                          ("data", layout.sec["data"])):
            if sec["size"] == 0:
                continue
            rc, out, err = run(["llvm-objcopy", "--dump-section",
                                f".{name}=sections/rebuilt.{name}.bin",
                                "rebuilt/rebuilt.elf"], cwd=outdir)
            if rc != 0:
                die(f"objcopy .{name} failed: {err.strip()}")
            with open(os.path.join(outdir,
                                   f"sections/rebuilt.{name}.bin"),
                      "rb") as f:
                new = f.read()
            off = first_mismatch(sec["blob"], new)
            if off != -1:
                all_ok = False
                if name == "text" and off < len(text_words) * 4:
                    # first differing byte may sit inside a 4-byte word
                    idx = off // 4
                    if inst_fallback(parsed, text_words, idx):
                        insts += 1
                        retry = True
                        continue
                die(f".{name} mismatch at {off:#x} and cannot be "
                    f"self-healed (layout or link-script bug)")
        if retry:
            continue

        # .bss: must exist as NOBITS with the right size.
        if layout.bss_size > 0:
            rc, out, err = run(["llvm-readelf", "-S", "-W",
                                "rebuilt/rebuilt.elf"], cwd=outdir)
            bss_ok = False
            for line in out.splitlines():
                m = re.match(r"\s*\[\s*\d+\]\s+\.bss\s+NOBITS\s+"
                             r"[0-9a-f]+\s+[0-9a-f]+\s+([0-9a-f]+)", line)
                if m and int(m.group(1), 16) == layout.bss_size:
                    bss_ok = True
            if not bss_ok:
                die(".bss missing or wrong size in rebuilt ELF")
        if all_ok:
            return {"status": "PASS", "inst_fallbacks": insts,
                    "instructions": len(parsed),
                    "labels": len(targets),
                    "fix_rounds": attempt + 1}
    die("did not converge after %d fix rounds" % MAX_FIX_ROUNDS)


# ------------------------------------------------------------------- main --
def main():
    if len(sys.argv) != 5:
        sys.exit(f"usage: {sys.argv[0]} <binary.elf> <rebased.elf> "
                 f"<layout.json> <outdir>")
    elf, rebased, layout_json, outdir = map(os.path.abspath, sys.argv[1:])

    with open(layout_json) as f:
        layout = Layout(json.load(f))

    os.makedirs(os.path.join(outdir, "sections"), exist_ok=True)
    os.makedirs(os.path.join(outdir, "asm"), exist_ok=True)
    os.makedirs(os.path.join(outdir, "rebuilt"), exist_ok=True)

    # 1. raw section images
    for name in ("text", "rodata", "data"):
        if layout.sec[name]["size"] == 0:
            layout.sec[name]["blob"] = b""
            continue
        rc, out, err = run(["llvm-objcopy", "--dump-section",
                            f".{name}=sections/{name}.bin", elf],
                           cwd=outdir)
        if rc != 0:
            die(f"objcopy .{name}: {err.strip()}")
        with open(os.path.join(outdir, f"sections/{name}.bin"), "rb") as f:
            layout.sec[name]["blob"] = f.read()

    text_words = [layout.sec["text"]["blob"][i:i + 4]
                  for i in range(0, len(layout.sec["text"]["blob"]), 4)]

    # 2. disassemble + rewrite targets to labels
    lines = disassemble(rebased, layout.sec["text"]["blob"])
    parsed, targets, insts = rewrite(text_words, lines)
    print(f"disassembled {len(parsed)} instructions, "
          f"{len(targets)} pc-relative targets, "
          f"{insts} .inst fallbacks")

    # 3. assemble → link → verify, self-healing with .inst
    with open(os.path.join(outdir, "asm/rebuild.ld"), "w") as f:
        f.write(link_script(layout))
    res = fix_round(parsed, text_words, outdir, layout, targets, insts)

    print("REBUILD: " + res["status"])
    for k in ("instructions", "labels", "inst_fallbacks", "fix_rounds"):
        print(f"  {k}: {res[k]}")
    with open(os.path.join(outdir, "rebuilt/verify.json"), "w") as f:
        json.dump(res, f, indent=2)
    return 0 if res["status"] == "PASS" else 1


if __name__ == "__main__":
    main()
