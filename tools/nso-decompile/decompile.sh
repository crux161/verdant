#!/usr/bin/env bash
# decompile.sh — decompile an NSO (or ELF) into assembly and C, and prove
# the assembly reconstructs the binary byte-for-byte.
#
# Pipeline
#   NSO input  -> nso2elf.py      -> binary.elf  (+ layout.json)
#   ELF input  -> used as-is      (+ layout.json synthesized from readelf)
#   reasm.py   -> asm/rebuild.s, rebuilt/rebuilt.elf, sections/
#                 (byte-identical verification with self-healing .inst)
#   llvm-objdump -> disasm/full.lst (human-readable listing)
#   Ghidra     -> ghidra/c/*.c (per-function decompilation), symbols.csv
#
# Usage:
#   decompile.sh <input.nso|input.elf> [outdir] [--no-ghidra] [--only-ghidra]
#
# Default outdir: <input_dir>/decompiled/<input_basename>/
#
# Requirements: python3, llvm-objdump/objcopy/mc/readelf, ld.lld (brew llvm,
# brew lld), and optionally Ghidra (brew install --cask ghidra).
#
# NOTE (RULES.md): outputs are research material — keep them inside
# RESOURCES/ and never commit them.
set -euo pipefail

TOOLDIR="$(cd "$(dirname "$0")" && pwd)"

GHIDRA_SUPPORT=""
candidates=""
# $GHIDRA_HOME (official release) wins: homebrew's cask ships no native
# decompiler, so analyzeHeadless runs there but every decompile fails.
if [ -n "$GHIDRA_HOME" ] && [ -x "$GHIDRA_HOME/support/analyzeHeadless" ]; then
    candidates="$GHIDRA_HOME/support"
fi
if command -v ghidraRun >/dev/null 2>&1; then
    R="$(python3 -c "import os,sys;print(os.path.realpath(sys.argv[1]))" \
        "$(command -v ghidraRun)")"
    # homebrew symlinks bin/ghidraRun; analyzeHeadless lives in libexec/support
    candidates="$candidates $(dirname "$R")/support $(dirname "$R")/../libexec/support"
fi
for d in $candidates "$HOME/Downloads/ghidra-sre/ghidra_12.2_PUBLIC/support" \
         /opt/homebrew/opt/ghidra/libexec/support \
         /usr/local/opt/ghidra/libexec/support; do
    if [ -x "$d/analyzeHeadless" ]; then GHIDRA_SUPPORT="$d"; break; fi
done

usage() { sed -n '2,26p' "$0" | sed 's/^# \{0,1\}//'; exit 1; }
die()  { echo "error: $*" >&2; exit 1; }

INPUT=""
OUTDIR=""
NO_GHIDRA=0
ONLY_GHIDRA=0
for arg in "$@"; do
    case "$arg" in
        --no-ghidra)   NO_GHIDRA=1 ;;
        --only-ghidra) ONLY_GHIDRA=1 ;;
        -*) usage ;;
        *) if [ -z "$INPUT" ]; then INPUT="$arg"
           elif [ -z "$OUTDIR" ]; then OUTDIR="$arg"
           else usage; fi ;;
    esac
done
[ -n "$INPUT" ] || usage

INPUT="$(cd "$(dirname "$INPUT")" && pwd)/$(basename "$INPUT")"
[ -f "$INPUT" ] || die "no such file: $INPUT"
[ -z "$OUTDIR" ] && OUTDIR="$(dirname "$INPUT")/decompiled/$(basename "$INPUT")"
mkdir -p "$OUTDIR"
OUTDIR="$(cd "$OUTDIR" && pwd)"

for tool in python3 llvm-objdump llvm-objcopy llvm-mc llvm-readelf ld.lld; do
    command -v "$tool" >/dev/null 2>&1 || die "missing required tool: $tool"
done
[ -n "$GHIDRA_SUPPORT" ] && echo "ghidra: $GHIDRA_SUPPORT/analyzeHeadless"

# ---------------------------------------------------------------- stage 1 --
if [ "$ONLY_GHIDRA" = 1 ]; then
    [ -f "$OUTDIR/binary.elf" ] || die "no binary.elf in $OUTDIR (run without --only-ghidra first)"
    INPUT="$OUTDIR/binary.elf"
fi

MAGIC="$(head -c 4 "$INPUT" 2>/dev/null | xxd -p)"

if [ "$ONLY_GHIDRA" = 1 ]; then
    :   # stages 1-3 already done; skip straight to Ghidra
elif [ "$MAGIC" = "4e534f30" ]; then                       # "NSO0"
    # nso2elf handles compression itself (LZ4 via python-lz4); it verifies
    # each segment against the header's embedded SHA256 before writing.
    python3 -I "$TOOLDIR/nso2elf.py" "$INPUT" "$OUTDIR/binary.elf"
    cp "$OUTDIR/binary.elf.json" "$OUTDIR/layout.json"
    python3 -I "$TOOLDIR/nso2elf.py" --base 0 "$INPUT" "$OUTDIR/rebased.elf"
elif [ "$MAGIC" = "7f454c46" ]; then                     # "\x7fELF"
    cp "$INPUT" "$OUTDIR/binary.elf"
    python3 -I - "$OUTDIR/binary.elf" "$OUTDIR/layout.json" \
                 "$OUTDIR/rebased.elf" <<'PY'
import json, struct, subprocess, sys
elf, layout_json, rebased = sys.argv[1:]
data = bytearray(open(elf, 'rb').read())
# parse section headers
out = subprocess.run(['llvm-readelf', '-S', '-W', elf],
                     capture_output=True, text=True).stdout
secs = {}
for line in out.splitlines():
    p = line.split()
    if len(p) >= 7 and p[0].startswith('['):
        try:
            secs[p[2]] = {'addr': int(p[4], 16), 'off': int(p[5], 16),
                          'size': int(p[6], 16)}
        except ValueError:
            pass
def s(name):  return secs.get(name, {'addr': 0, 'off': 0, 'size': 0})
text = s('.text')
if text['size'] == 0:
    sys.exit('error: ELF has no .text section')
base = text['addr']
ro, da, bss = s('.rodata'), s('.data'), s('.bss')
meta = {'base': base, 'entry': base,
        'segments': [
            {'name': 'text',   'vaddr': text['addr'], 'size': text['size'],
             'file_ofs': text['off']},
            {'name': 'rodata', 'vaddr': ro['addr'] or da['addr'],
             'size': ro['size'], 'file_ofs': ro['off']},
            {'name': 'data',   'vaddr': da['addr'] or text['addr'],
             'size': da['size'], 'file_ofs': da['off']}],
        'bss_size': bss['size'],
        'bss_vaddr': bss['addr'] or (da['addr'] + da['size'])}
json.dump(meta, open(layout_json, 'w'), indent=2)
# rebase: shift alloc vaddrs down by .text vaddr
e_phoff, e_phentsize, e_phnum = struct.unpack_from('<QHxxH', data, 0x20)
e_shoff, e_shentsize, e_shnum = struct.unpack_from('<QHxxH', data, 0x28)
for i in range(e_phnum):
    off = e_phoff + i * e_phentsize
    if struct.unpack_from('<I', data, off)[0] == 1:        # PT_LOAD
        for fld in (0x10, 0x18):
            v = struct.unpack_from('<Q', data, off + fld)[0]
            struct.pack_into('<Q', data, off + fld, v - base)
for i in range(e_shnum):
    off = e_shoff + i * e_shentsize
    flags = struct.unpack_from('<Q', data, off + 0x8)[0]
    if flags & 0x2:                                         # SHF_ALLOC
        v = struct.unpack_from('<Q', data, off + 0x10)[0]
        struct.pack_into('<Q', data, off + 0x10, v - base)
open(rebased, 'wb').write(data)
print('synthesized layout.json and rebased.elf for ELF input')
PY
else
    die "unrecognized magic 0x$MAGIC (want NSO0 or ELF)"
fi

[ -f "$OUTDIR/layout.json" ] || die "layout.json not produced"
if [ "$ONLY_GHIDRA" = 1 ]; then
    NO_GHIDRA=0
else
    # ------------------------------------------------------------ stage 2 --
    mkdir -p "$OUTDIR/disasm"
    llvm-readelf -a "$OUTDIR/binary.elf" > "$OUTDIR/disasm/readelf.txt"
    llvm-objdump -d "$OUTDIR/binary.elf" > "$OUTDIR/disasm/full.lst"

    # ------------------------------------------------------------ stage 3 --
    echo "== reassembly (byte-exact verification) =="
    python3 -I "$TOOLDIR/reasm.py" "$OUTDIR/binary.elf" "$OUTDIR/rebased.elf" \
        "$OUTDIR/layout.json" "$OUTDIR" \
        | tee "$OUTDIR/reasm.log"

    # strings in the data sections (sections/*.bin come from reasm.py)
    python3 -I - "$OUTDIR/layout.json" "$OUTDIR" <<'PY'
import json, re, sys
meta = json.load(open(sys.argv[1]))
outdir = sys.argv[2]
out = []
for seg in meta['segments']:
    if seg['name'] == 'text':
        continue
    path = f"{outdir}/sections/{seg['name']}.bin"
    try:
        blob = open(path, 'rb').read()
    except FileNotFoundError:
        continue
    for m in re.finditer(rb'[\x20-\x7e]{4,}', blob):
        out.append(f"{seg['vaddr'] + m.start():08x}  "
                   f"{m.group().decode()}")
open(f"{outdir}/disasm/strings.txt", 'w').write('\n'.join(out) + '\n')
print(f"strings: {len(out)} runs in rodata/data")
PY

    # ------------------------------------------------------------- report ----
    python3 -I - "$OUTDIR" <<'PY'
import hashlib, json, sys
outdir = sys.argv[1]
meta = json.load(open(f"{outdir}/layout.json"))
verify = json.load(open(f"{outdir}/rebuilt/verify.json"))
lines = ["# Decompilation report", "",
         f"input: {meta.get('input', 'binary.elf')}",
         f"module_id: {meta.get('module_id', 'n/a')[:32]}",
         "", "## Layout", "",
         "| segment | vaddr | size | sha256 |", "|---|---|---|---|"]
for seg in meta['segments']:
    blob = open(f"{outdir}/sections/{seg['name']}.bin", 'rb').read()
    lines.append(f"| {seg['name']} | {seg['vaddr']:#x} | "
                 f"{len(blob):#x} | {hashlib.sha256(blob).hexdigest()[:16]}… |")
lines += ["", f"bss: {meta['bss_size']:#x} bytes at {meta['bss_vaddr']:#x}",
          "", "## Verification", "",
          "The assembly in asm/rebuild.s reassembles to a byte-identical "
          "binary:", "", "```",
          "REBUILD: " + verify['status']]
for k in ('instructions', 'labels', 'inst_fallbacks', 'fix_rounds'):
    lines.append(f"  {k}: {verify[k]}")
lines += ["```", "",
          "Rebuild it yourself:", "```",
          "cd " + outdir,
          "llvm-mc --triple=aarch64-unknown-elf -filetype=obj \\",
          "    asm/rebuild.s -o asm/rebuild.o",
          "ld.lld -T asm/rebuild.ld -e _nsotext_start asm/rebuild.o \\",
          "    -o rebuilt/rebuilt.elf",
          "```"]
open(f"{outdir}/REPORT.md", 'w').write('\n'.join(lines) + '\n')
print("wrote REPORT.md")
PY
fi

# ---------------------------------------------------------------- stage 4 --
if [ "$NO_GHIDRA" = 1 ]; then
    echo "ghidra stage skipped (--no-ghidra)"
    exit 0
fi
if [ -z "$GHIDRA_SUPPORT" ]; then
    echo "warning: ghidra not found — skipping C decompilation"
    exit 0
fi
echo "== ghidra decompilation =="
mkdir -p "$OUTDIR/ghidra-project"   # analyzeHeadless needs the parent to exist
"$GHIDRA_SUPPORT/analyzeHeadless" "$OUTDIR/ghidra-project" ghidra \
    -import "$OUTDIR/binary.elf" -overwrite \
    -scriptPath "$TOOLDIR" \
    -preScript ghidra_make_functions.java \
    -postScript ghidra_export_all.java "$OUTDIR/ghidra" \
    2>&1 | tail -25
echo "ghidra outputs: $OUTDIR/ghidra/c/"
