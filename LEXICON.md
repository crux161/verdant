# Verdant Lexicon

> **The single source of truth for names and terms** (ADR-013 and ADR-014 in [`PLAN.md`](PLAN.md)).
> Every agent, observer or builder, reads this file before starting a task. White papers, code, file names, commits and issues use these terms exactly.
> Status: v0.2 · 2026-10-20 · reference firmware: Horizon 23.0.1

---

## How to use this file

- **Use the Verdant term.** Write it in white papers, code identifiers, file names, commit messages and issues.
- **Never translate codenames.** A white paper in Standard Chinese (简体中文) still writes "Hana", "Cumulus" and so on. The 中文 column gives the descriptive term to use alongside the codename.
- **Keep literal identifiers byte-exact** (§6). Horizon and games depend on them. They are interoperability facts, not names we chose.
- **Never use deny-listed names** (§7) in Verdant identifiers, file names or new docs.
- **Missing a term?** Add it here in a PR before you use it (§8).

---

## 1. The name and its editions

**The project is called Verdant.** One word, and nothing more.
- **Never** "Verdant OS", "VerdantOS", "Project Verdant" or any other suffix or prefix.
- In prose and the user interface, write **Verdant**.
- In identifiers, paths and file names, write **`verdant`** (for example `verdant.toml`, `/verdant/`, `libverdant`).
- 中文: write "Verdant" untranslated, like every codename.

**Releases are editions**, written exactly as:

> **Verdant `<major>.<minor>` '`<codename>`'**, for example **Verdant 1.0 'moss'**

- Each **major** version gets one codename. Minor and patch releases keep it (Verdant 1.0.2 'moss', Verdant 1.1 'moss').
- The codename is lowercase and sits in single quotes after the version number.
- In identifiers and file names, use the version and codename joined by a hyphen (for example `verdant-1.0-moss`).

**Edition codenames are green plants, never flowers** (flowers belong to hardware, §2). Each edition's plant grows larger or lives longer than the one before it, as Verdant does.

| Edition | Codename | Status | Meaning |
|---|---|---|---|
| Verdant 1.0 | **moss** | Assigned: first distribution (PLAN milestone M2) | Small, hardy ground cover; the first growth |
| next | fern | Reserved | |
| next | ivy | Reserved | Climbs and spreads |
| next | laurel | Reserved | |
| next | cedar | Reserved | |
| final | **yew** | Reserved for the North Star edition (no Nintendo software process loaded) | One of the longest-lived trees; longevity after Nintendo stops |

Reserved codenames are given out in order when an edition is planned. New ones may be added between them. **Avoid:**
- names tied to Nintendo IP (for example Pokémon names such as "Oak");
- names of major OS releases (for example "Sequoia", "Ventura");
- names already used for another Verdant term.

---

## 2. Naming themes

| Kind of thing | Theme | Examples |
|---|---|---|
| The project | One name only | Verdant |
| Editions (releases) | Green plants, not flowers, growing in size and lifespan | moss, fern, ivy, laurel, cedar, yew |
| Hardware blocks and Verdant's drivers for them | Flowers | Hana |
| System services (Verdant replacements for Horizon modules) | Sky and weather | Cumulus, Nimbus, Rime, Almanac, Dusk, Gale, Jetstream, Kite, Ozone |
| Observation and test instruments | Weather instruments and optics | Radar, Doppler, Mirage |
| Places and roles in the process | Astronomy | Observatory, Observer |
| Tools and process steps | Plain descriptive English | composer, `vsp`, white paper, boundary review |

**A new codename must be:**
- short and easy to pronounce;
- a hint at the function where possible;
- unique within the project;
- **not** an Atmosphère or hekate component name (Exosphère, Mesosphère, Stratosphère, Thermosphère, Troposphère, fusee, Daybreak, Haze, Nyx, …);
- **not** a Nintendo trademark, internal name or other Nintendo IP (§7);
- **not** the name of a well-known project in the Switch scene.

---

## 3. Process and roles

| Term | 中文 | Meaning |
|---|---|---|
| **Rule 0** | 零号规则 | Nothing derived from Nintendo's code is ever committed to a Verdant codebase or distributed in any form. |
| **Observatory** | 研究工作区 | The private, encrypted, access-controlled research workspace. It holds firmware, keys, decompiled output, Ghidra databases, Mirage builds and Radar traces. Nothing in it is ever committed to Verdant or distributed. |
| **Observer** | 研究代理 | The research worker class (mostly AI agents). Observers work in the Observatory: decryption, analysis, decompilation, debugging against the original, static recompilation, oracle test suites, parity and independence measurement. **Their only output into Verdant is white papers.** |
| **Builder** | 实现代理 | The implementation worker class (mostly AI agents). Builders write Verdant's code, tests, tools and docs from white papers and public sources. **They never see the Observatory or anything in it.** |
| **White paper** | 白皮书 | A plain-language document (English or 简体中文) written by an observer that describes how a piece of Horizon 23.0.1 behaves. It contains **no code** in any language. It is the only thing that crosses from observers to builders. |
| **Erratum** | 勘误 | A white paper that corrects or adds to an earlier one, often in answer to a builder's question or a parity failure. |
| **Boundary review** | 边界审查 | A second observer's check that a white paper obeys Rule 0 and the white-paper rules before it merges. |
| **Reference firmware** | 基准固件 | Horizon **23.0.1**: the single version Verdant is built to match. |
| **VSP** (version support patch) | 版本支持补丁 | A Verdant-only patch that adds support for one other Horizon version. Whoever needs that version authors it, running the whole process themselves. |
| **Parity** | 行为一致性 | How closely a Verdant module matches Horizon 23.0.1, measured on every parity dimension (PLAN §1). |
| **Security deviation** | 安全偏差 | A deliberate, documented departure from 23.0.1 behavior where that behavior is vulnerable. It is excluded from parity scoring. |
| **Independence check** | 独立性检查 | Measurements showing Verdant code is independently written: binary similarity, scans for Nintendo byte sequences, source review. |
| **Irreducible firmware** | 不可替换固件 | Firmware for other processors whose signatures hardware enforces. It can never be replaced and stays user-sourced. |
| **User-sourced** | 用户自备 | Read from the user's own console at install time or run time. Verdant never carries it. |
| **Re-baselining** | 基准迁移 | A deliberate project decision to move the reference firmware to a newer Horizon release. It never happens automatically. |
| **Edition** | 版本代号 | A major release of Verdant with its plant codename (§1), for example Verdant 1.0 'moss'. |

---

## 4. Verdant components

| Codename | 中文 | What it is | Relates to (Horizon / community term) | Plan |
|---|---|---|---|---|
| **Cumulus** | 文件系统服务 | Verdant's file system service | Horizon FS, the `fsp-srv` family of services | Phase 3 |
| **Nimbus** | 块设备层 | Block device layer: SD, eMMC, BIS partitions, emuMMC | Part of Cumulus | P3.2 |
| **Rime** | 存档文件系统 | Save data file system | Part of Cumulus | P3.4 |
| **Hana** | 游戏卡控制芯片及驱动 | The game card controller ASIC, plus Verdant's driver and card manager for it | Community name "Lotus" / "Lotus3" | P3.5 |
| **card source** | 卡带数据源 | The abstraction that presents a logical card image to Hana's upper layers. Backends: physical card, image file, USB stream | No Horizon equivalent | P3.6 |
| **Almanac** | 设置服务 | Settings service | `set`, `set:sys`, `set:cal`, `set:fd` | P6.1.1 |
| **Dusk** | 电源状态与休眠管理 | Power state and sleep management | psc, spsm, bpc | P6.1.2 |
| **Gale** | 温控、风扇与动态电压频率调节 | Thermal, fan and DVFS control | pcv/clkrst, ptm, tc, ts | P4.3, P6.1.3 |
| **Jetstream** | 总线服务 | Bus services: I2C, GPIO, pinmux, PWM | i2c, gpio, pinmux, pwm | P6.1.4 |
| **Kite** | USB 协议栈 | USB host and device stacks | usb | P6.1.6 |
| **Ozone** | TLS 加密传输服务 | TLS service | ssl | P6.2.3 |
| **Radar** | IPC 追踪器 | On-device IPC tracer sysmodule. Builders build it; **its traces of Nintendo services are Observatory artifacts** | n/a | P2.5.1 |
| **Doppler** | 差分测试框架 | Differential harness: replays request sequences against two implementations and compares the responses | n/a | P2.5.4 |
| **Mirage** | 重编译的原版模块（测试基准） | A Horizon module statically recompiled to run on a host as a test oracle. **Observatory only; never committed or distributed** | n/a | PR.5 |
| **composer** | 组装工具 | Builds `package3` and the SD layout from module manifests | n/a | P2.3.3 |
| **libverdant** | 共享库 | Verdant's shared helpers on top of libstratosphere | n/a | P0.2.1 |

### Not yet named

Codenames for these are assigned when their epic starts:
- **Platform and network:** lbl; the network stack (bsdsocket, sfdnsres, nifm); wlan; Ethernet; ldn; time.
- **Identity and content:** es; account; friends; bcat; npns; nim; olsc; prepo.
- **Input, audio and graphics:** hid; irs; the Bluetooth stack (bluetooth, btm, btdrv); audio; hwopus; nvservices; vi.
- **Application framework:** am; ns; arp; glue; pctl; capsrv; grc; jit.
- **Applets and system data:** each system applet; the home menu; overlayDisp; starter; the System Settings app; each system data archive.

---

## 5. Hardware and platform terms

Public names from NVIDIA's Tegra documentation and vendor part numbers stay as they are. Only Nintendo-internal names are replaced.

| Common or community name | Verdant term | 中文 | Notes |
|---|---|---|---|
| Lotus, Lotus3 (game card ASIC) | **Hana** | 游戏卡控制芯片 | Sits on SDMMC2 |
| Erista, Icosa (original retail board) | `t210` · HAC-001 | 初代主板 | Tier 1 |
| Copper (original development board) | `t210-dev` | 开发板 | Unsupported |
| Mariko (T210B01 board family) | `t210b01` | 二代主板（T210B01） | |
| Iowa | HAC-001-01 | 续航版 | Tier 1 |
| Hoag | HDH-001 | Lite 版 | Tier 2 |
| Aula | HEG-001 | OLED 版 | Tier 2 |
| Calcio | `t210b01-other` | 其他 T210B01 主板 | Not a retail target (role to be confirmed) |
| Joy-Con | detachable controllers (left / right) | 可拆卸手柄 | Trademark; never in identifiers |
| dock, cradle | dock | 底座 | |
| Tegra SE, TSEC, BPMP, Host1x, SDMMC1–4, falcon | *unchanged* | | Public NVIDIA names |
| MAX77620, MAX77812, BCM4356, and other part numbers | *unchanged* | | Vendor part numbers |

---

## 6. Literal identifiers: keep byte-exact

These are interoperability facts. Code must reproduce them exactly, and white papers state them exactly.

- IPC service and port names (for example `fsp-srv`, `set:sys`)
- Program and title IDs (for example `0100000000000000`)
- IPC command IDs, and result codes (module plus description)
- File and wire format magics (`NCA3`, `PFS0`, `HFS0`, `KIP1`, `NSO0`, …) and the field layouts they introduce
- NPDM fields, system save data IDs, settings item names
- Paths that Horizon and games expect on storage (for example the SD card's `Nintendo/Contents`)

**In code,** each literal is defined once, as a constant with a Verdant name. For example, the constant is named after Cumulus, and its value is the literal service name string.

---

## 7. Deny list

These names never appear in Verdant identifiers, file names or new documents:
- **Nintendo-internal codenames:** Lotus, Erista, Icosa, Copper, Mariko, Iowa, Hoag, Aula, Calcio.
- **Nintendo SDK names:** `nn::` namespaces, SDK class and function names, and any symbol name recovered from a Nintendo binary.
- **Trademarks and Nintendo IP as identifiers:** Nintendo, Switch, Joy-Con, and names from Nintendo-owned or co-owned franchises. User-facing documentation may name the products where it must say which hardware is supported.
- **Upstream component names** (Atmosphère, hekate) used for anything other than those components.
- **Retired project names** (see Retired terms) in new material.

**Exceptions:** this file (to map the names), `upstream/` (vendored code keeps its own names), and the literal identifiers in §6.

**Enforced by:** the leak guard for code (PLAN P0.4.2) and white-paper lint (PLAN PR.6.3).

---

## 8. Adding or changing a term

1. Open a PR that edits this file. Give the term, how it fits the theme, its 中文 description, its meaning and its plan reference.
2. Check for collisions with Atmosphère, hekate and libnx names, Nintendo IP, well-known projects in the Switch scene, and existing codenames.
3. Either worker class may propose terms. Observers must keep Nintendo-derived detail out of definitions (Rule 0).
4. When renaming, move the old term to the **Retired** table so agents can still resolve it in older material.

### Retired terms

| Old term | Replaced by | Retired | Why |
|---|---|---|---|
| Skyline (project name) | **Verdant** | 2026-10-20 | Collided with two Switch projects: `skyline-dev/skyline` (a Smash Bros. Ultimate modding framework) and `skyline-emu/skyline` (an Android emulator). The alternatives Viridian and Vermilion were rejected because both are Pokémon city names. |
| `skyline.toml`, `/skyline/`, `libskyline` | `verdant.toml`, `/verdant/`, `libverdant` | 2026-10-20 | Follows the project rename |
