# Project Skyline: Engineering Roadmap

An open-source, modular, post-EOL operating system stack for Nintendo Switch hardware (and compatible Tegra X1 derivatives), designed to preserve commercial game compatibility while enabling modern hardware extensions, custom storage, and community-maintained security updates.

---

## 1. Executive Summary & Design Philosophy

**Project Skyline** avoids reinventing the wheel by building directly upon proven, community-developed open-source foundations—specifically **Atmosphère**, **Mesosphère**, and **Hekate**. Rather than writing an OS from scratch, Skyline unbundles, refactors, and extends Horizon’s microservices into a clean, modular runtime environment. 

### Core Objectives
* **Unmodified Compatibility:** Execute commercial `.xci` and `.nsp` game binaries natively on raw ARM64 silicon via their original hardware interfaces.
* **Open-Source Core:** Replace proprietary microkernel components with **Mesosphère** for deterministic scheduling, memory management, and robust IPC isolation.
* **Hardware Extensibility:** Decouple rigid vendor limitations to support modern peripherals, USB/NVMe storage expansion, custom cooling curves, and alternative cartridge reader hardware.
* **Post-EOL Longevity:** Provide independent security patches, offline profile management, and network redirection independent of Nintendo infrastructure.

---

## 2. Architectural Blueprint

```
                     [ Commercial Game Card / .xci ]
                                   │
                                   ▼
             [ Re-engineered Lotus ASIC & Tegra SE Driver ]
                                   │
                                   ▼
          [ Mesosphère Microkernel (AArch64 Scheduling & IPC) ]
                                   │
         ┌─────────────────────────┴─────────────────────────┐
         ▼                                                   ▼
[ Modular Userland Services ]                       [ Hardware Extensions ]
- fsp-srv (Storage / USB / NVMe Proxy)              - Custom Fan & Power Curves
- pm / sm (Process & Service Managers)              - Modern Controller / BT Stacks
- custom net/auth layers                            - FPGA / USB Cartridge Readers
```

---

## 3. Phased Development Roadmap

### Phase 1: Foundation & Bootchain Bootstrapping
* **Goal:** Establish a reliable, custom boot pipeline from cold boot to execution environment.
* **Key Tasks:**
  * Utilize **Hekate/Nyx** as the primary stage-1 bootloader and payload loader.
  * Configure custom payload entry points (`.bin` binaries executed via RCM or chip payloads).
  * Initialize memory controllers, clock trees, and foundational power rails via Tegra X1 registers.
  * Integrate **Exosphère** to handle TrustZone initialization and secure monitor configuration.

### Phase 2: Microkernel & IPC Integration (`Mesosphère`)
* **Goal:** Stand up the core operating system runtime and service routing layer.
* **Key Tasks:**
  * Deploy **Mesosphère** as the open-source microkernel replacing Nintendo's stock kernel binary.
  * Implement standard `svc` (Supervisor Call) wrappers for thread synchronization, memory mapping (`svcControlMemory`), and port creation.
  * Port Horizon's **HIPC/TIPC** inter-process communication protocol to handle message dispatching between isolated userland microservices.
  * Stand up `sm` (Service Manager) and `pm` (Process Manager) equivalents to govern system service registry and process lifecycles.

### Phase 3: Hardware Drivers & Storage Passthrough (`Lotus` & Security)
* **Goal:** Enable native game card reading and cryptographic block decryption without proprietary black-box dependencies.
* **Key Tasks:**
  * Extract and adapt the **`lotus`** ASIC driver logic to manage game card power sequencing (1.8V/3.3V) and SPI/SDIO command communication.
  * Interface with the **Tegra Security Engine (SE)** to handle hardware-accelerated AES-128 sector decryption and master key derivation using pre-provisioned system keys (`prod.keys`).
  * Implement an abstraction layer (`fsp-srv`) that bridges raw decrypted game card blocks to standard file system requests (`.xci`/`.nsp`).
  * Support alternative physical reader paths (e.g., streaming over USB from an external FPGA reader).

### Phase 4: Modular Userland & Peripheral Extensions
* **Goal:** Unlock hardware mods, faster storage, and modern peripheral support.
* **Key Tasks:**
  * Rewrite or patch the storage proxy (`fsp-srv`) to support high-speed NVMe drives attached via PCIe/USB-C, bypassing MicroSD bottlenecks.
  * Modernize networking (`nim` / `bsd`) and Bluetooth (`btm`) stacks to support modern USB Wi-Fi dongles and low-latency audio codecs.
  * Implement custom Thermal & DVFS (Dynamic Voltage and Frequency Scaling) sysmodules to optimize performance under custom cooling loops.

### Phase 5: Commercial Compatibility & Post-EOL Hardening
* **Goal:** Lock in robust game execution stability and independent system maintenance.
* **Key Tasks:**
  * Build automated regression test suites running popular commercial titles across diverse system states.
  * Decouple local save management, account authentication, and LAN multiplayer from Nintendo Network servers.
  * Establish a continuous integration pipeline for building, signing, and flashing modular sysmodules safely.