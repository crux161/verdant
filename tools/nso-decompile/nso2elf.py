#!/usr/bin/env python3
"""nso2elf.py — convert a (decompressed) Nintendo Switch NSO to an ELF64 image.

NSO header layout (per switchbrew.org/wiki/NSO):

  0x00  magic "NSO0"         0x04 version       0x08 reserved      0x0C flags
  0x10  text  {file_ofs, mem_ofs, size}
  0x1C  module_name_offset (= sizeof(header))
  0x20  rodata{file_ofs, mem_ofs, size}
  0x2C  module_name_size
  0x30  data  {file_ofs, mem_ofs, size}
  0x3C  bss_size
  0x40  module_id (0x20 bytes)
  0x60  compressed sizes: text, rodata, data (== sizes when uncompressed)
  0x6C  reserved (0x1C)
  0x88  embedded_ofs/size   (relative to .rodata)
  0x90  dynstr_ofs/size     (relative to .rodata)
  0x98  dynsym_ofs/size     (relative to .rodata)
  0xA0  text   SHA256      0xC0 rodata SHA256      0xE0 data SHA256
  0x100 segments follow

Flags: bit0-2 = text/rodata/data compressed (LZ4), bit3-5 = hashes present,
       bit6 = execute-only-memory (fw 20+), bit7 = ZBIC compression (fw 22+).

The ELF is laid out so segment file offsets are unchanged: ELF header +
3 program headers (0xE8 bytes) fit before the first segment at >= 0x100,
and the NSO segment bytes are copied verbatim.  Section headers, .shstrtab
and a small .symtab are appended after the data segment.

Usage: nso2elf.py [--base 0x8000000] <input.nso> <output.elf>

--base sets the .text virtual address.  The default (0x8000000) is the
authentic Switch load address; reasm.py passes --base 0 so that
PC-relative targets in the disassembly are 0-based (the assembler output
links back at the authentic address without relocations).
"""

import hashlib
import json
import os
import struct
import sys

MAGIC = b"NSO0"
BASE = 0x8000000  # Switch NSO base virtual address for .text

FLAG_TEXT_COMPRESSED = 1 << 0
FLAG_RO_COMPRESSED = 1 << 1
FLAG_DATA_COMPRESSED = 1 << 2
FLAG_TEXT_HASH = 1 << 3
FLAG_RO_HASH = 1 << 4
FLAG_DATA_HASH = 1 << 5
FLAG_XOM = 1 << 6
FLAG_ZBIC = 1 << 7


def u32(data, off):
    return struct.unpack_from("<I", data, off)[0]


def u64(data, off):
    return struct.unpack_from("<Q", data, off)[0]


def round_up(x, a):
    return (x + a - 1) // a * a


def parse_nso(path):
    data = open(path, "rb").read()
    if data[:4] != MAGIC:
        sys.exit(f"error: {path} is not an NSO (bad magic {data[:4]!r})")

    flags = u32(data, 0x0C)
    segs = []
    for i, name in enumerate(("text", "rodata", "data")):
        segs.append({
            "name": name,
            "file_ofs": u32(data, 0x10 + i * 0x10),
            "mem_ofs": u32(data, 0x14 + i * 0x10),
            "size": u32(data, 0x18 + i * 0x10),
        })
    name_size = u32(data, 0x2C)
    bss_size = u32(data, 0x3C)
    module_id = data[0x40:0x60]
    comp_sizes = [u32(data, 0x60 + i * 4) for i in range(3)]
    embedded = (u32(data, 0x88), u32(data, 0x8C))
    dynstr = (u32(data, 0x90), u32(data, 0x94))
    dynsym = (u32(data, 0x98), u32(data, 0x9C))
    hashes = [data[0xA0 + i * 0x20: 0xA0 + (i + 1) * 0x20] for i in range(3)]

    info = {
        "input": os.path.abspath(path),
        "size": len(data),
        "flags": flags,
        "segments": segs,
        "bss_size": bss_size,
        "module_name_size": name_size,
        "module_id": module_id.hex(),
        "comp_sizes": comp_sizes,
        "embedded": embedded,
        "dynstr": dynstr,
        "dynsym": dynsym,
        "hashes": [h.hex() for h in hashes],
    }
    return data, info


def verify(seg, stored_hash, data, flags_bit):
    if not (flags_bit):
        return "absent"
    actual = hashlib.sha256(data).digest()
    return "ok" if actual == stored_hash else "MISMATCH"


def decompress_ro_or_text(seg, data, name, zbic):
    raw = data[seg["file_ofs"]:]
    if zbic:
        sys.exit(f"error: ZBIC-compressed {name} is not supported; "
                 f"use a pre-decompressed NSO")
    try:
        import lz4.block
    except ImportError:
        sys.exit(f"error: {name} segment is LZ4-compressed but python 'lz4' "
                 f"module is missing (pip install lz4), or pass a "
                 f"decompressed NSO instead")
    try:
        return lz4.block.decompress(raw, uncompressed_size=seg["size"])
    except Exception as e:  # noqa: BLE001
        sys.exit(f"error: failed to LZ4-decompress {name}: {e}")


def build_elf(data, info, base):
    """Assemble an ELF64 file with segment bytes at their NSO offsets."""
    flags = info["flags"]
    segs = info["segments"]
    bss_size = info["bss_size"]

    # Decompress segments if needed; recompute their file offsets.
    files = []  # (vaddr, size, bytes, mem_size)
    next_off = 0x100
    for i, seg in enumerate(segs):
        comp = flags & (1 << i)
        if comp:
            blob = decompress_ro_or_text(seg, data, seg["name"],
                                         flags & FLAG_ZBIC)
        else:
            blob = data[seg["file_ofs"]: seg["file_ofs"] + seg["size"]]
            if len(blob) != seg["size"]:
                sys.exit(f"error: {seg['name']} segment truncated "
                         f"({len(blob)} < {seg['size']})")
        seg["file_ofs"] = next_off
        seg["vaddr"] = base + seg["mem_ofs"]
        next_off = round_up(next_off + seg["size"], 0x1000)
        files.append(blob)

    # Integrity: SHA256 per segment against the header hashes.
    for i, (seg, blob) in enumerate(zip(segs, files)):
        verdict = verify(seg, data[0xA0 + i * 0x20: 0xA0 + (i + 1) * 0x20],
                         blob, flags & (FLAG_TEXT_HASH << i))
        print(f"  [{seg['name']}] file={seg['file_ofs']:#x} "
              f"mem={seg['mem_ofs']:#x} vaddr={seg['vaddr']:#x} "
              f"size={seg['size']:#x} sha256={verdict}")
        if verdict == "MISMATCH":
            sys.exit("error: segment hash mismatch — header does not match "
                     "content; aborting")

    bss_vaddr = segs[2]["vaddr"] + segs[2]["size"]

    # --- ELF header ------------------------------------------------------
    e_ident = b"\x7fELF" + bytes([2, 1, 1, 0]) + b"\x00" * 8
    ehdr = struct.pack(
        "<16sHHIQQQIHHHHHH",
        e_ident, 2, 183, 1, base, 0x40, 0, 0, 0x40, 0x38, 3, 0x40, 7, 6,
    )
    # e_entry = base (text start; NSO has no entry field)

    phdrs = b""
    for seg, blob, p_flags in ((segs[0], files[0], 5),   # RX
                               (segs[1], files[1], 4),   # R
                               (segs[2], files[2], 6)):  # RW
        memsz = seg["size"] + (bss_size if seg["name"] == "data" else 0)
        phdrs += struct.pack(
            "<IIQQQQQQ", 1, p_flags, seg["file_ofs"], seg["vaddr"],
            seg["vaddr"], len(blob), memsz, 0x100,
        )

    # --- copy segment bytes at their NSO offsets -------------------------
    image = bytearray()
    image += ehdr + phdrs
    image += b"\x00" * (0x100 - len(image))
    for seg, blob in zip(segs, files):
        while len(image) < seg["file_ofs"]:
            image += b"\x00"
        image += blob

    # --- section headers + strings + symtab (appended at EOF) ------------
    shstr = b"\x00.text\x00.rodata\x00.data\x00.bss\x00.symtab\x00.shstrtab\x00"
    shstr_off = len(image)
    image += shstr

    symtab = bytearray()
    symtab += struct.pack("<IBBHQQ", 0, 0, 0, 0, 0, 0)  # NULL
    # one STT_SECTION symbol per section (shndx 1..4)
    for shndx in range(1, 5):
        symtab += struct.pack("<IBBHQQ", 0, 3, 0, shndx, 0, 0)
    symtab += struct.pack("<IBBHQQ", 0, 4, 0, 0xFFF1, 0, 0)  # STT_FILE
    symtab_off = len(image)
    image += symtab

    shoff = len(image)
    shdrs = b"\x00" * 0x40  # NULL section
    secs = [
        # (name, type, flags, addr, offset, size, link, entsize)
        (".text", 1, 6, segs[0]["vaddr"], segs[0]["file_ofs"], segs[0]["size"]),
        (".rodata", 1, 2, segs[1]["vaddr"], segs[1]["file_ofs"], segs[1]["size"]),
        (".data", 1, 3, segs[2]["vaddr"], segs[2]["file_ofs"], segs[2]["size"]),
        (".bss", 8, 3, bss_vaddr, segs[2]["file_ofs"] + segs[2]["size"],
         bss_size),
    ]
    for name, sh_type, sh_flags, addr, off, size in secs:
        shdrs += struct.pack("<IIQQQQIIQQ", shstr.index(name.encode()), sh_type,
                             sh_flags, addr, off, size, 0, 0, 4, 0)
    shdrs += struct.pack("<IIQQQQIIQQ", shstr.index(b".symtab"), 2, 0, 0,
                         symtab_off, len(symtab), 6, 1, 8, 24)
    shdrs += struct.pack("<IIQQQQIIQQ", shstr.index(b".shstrtab"), 3, 0, 0,
                         shstr_off, len(shstr), 0, 0, 1, 0)
    image += shdrs

    image[0x28:0x30] = struct.pack("<Q", shoff)  # patch e_shoff
    return bytes(image), info


def main():
    args = sys.argv[1:]
    base = BASE
    if args and args[0] == "--base":
        base = int(args[1], 0)
        args = args[2:]
    if len(args) != 2:
        sys.exit(f"usage: {sys.argv[0]} [--base 0x8000000] "
                 f"<input.nso> <output.elf>")
    nso_path, elf_path = args

    data, info = parse_nso(nso_path)
    print(f"NSO: {info['input']} ({info['size']} bytes) "
          f"flags={info['flags']:#x} base={base:#x}")
    for seg in info["segments"]:
        print(f"  header: {seg['name']} file_ofs={seg['file_ofs']:#x} "
              f"mem_ofs={seg['mem_ofs']:#x} size={seg['size']:#x}")
    print(f"  bss_size={info['bss_size']:#x}  "
          f"module_id={info['module_id'][:16]}…")

    image, info = build_elf(data, info, base)
    with open(elf_path, "wb") as f:
        f.write(image)
    print(f"wrote {elf_path} ({len(image)} bytes)")

    # Sidecar metadata for the pipeline.
    meta = {
        "base": base,
        "entry": base,
        "segments": [dict(seg) for seg in info["segments"]],
        "bss_size": info["bss_size"],
        "bss_vaddr": info["segments"][2]["vaddr"] + info["segments"][2]["size"],
        "dynstr": info["dynstr"],
        "dynsym": info["dynsym"],
        "embedded": info["embedded"],
        "module_id": info["module_id"],
        "sha256_verified": True,
    }
    with open(elf_path + ".json", "w") as f:
        json.dump(meta, f, indent=2)
    print(f"wrote {elf_path}.json")


if __name__ == "__main__":
    main()
