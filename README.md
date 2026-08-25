# One UI X — Vector-SR S24 Ultra compatibility

> [!IMPORTANT]
> **Unofficial modified project.** This repository is not affiliated with, sponsored by, or endorsed by **SoClear/OneUIX**, **Vector-SR**, Samsung, Root-My-Galaxy, or their upstream developers. If a problem occurs only with this modified build, report it here rather than to upstream unless it is first reproduced on the unmodified upstream release.

Device-tested compatibility patch for **One UI X 1.7.0** on Samsung Galaxy S24 Ultra running One UI 8.5 / Android 16, tested in a **Root-My-Galaxy / KernelSU** setup with the device-tested **Vector-SR S24U hotfix v1.2 (3136)**.

## Modified-version notice

- Modified version date: **2026-08-22**
- One UI X upstream: `SoClear/OneUIX`
- Pinned upstream revision: `78e2ef1d10320aab293631f97ec636cf64d4cbea`
- Upstream version: `1.7.0 (9)`
- Modified versionName: `1.7.0-vectorsr-s24u`
- License: **GNU Affero General Public License v3.0 (AGPL-3.0)**

The original One UI X project, source history, copyrights, names, and upstream work remain credited to their original authors. This repository contains a device-specific compatibility modification and reproducible build harness; it does not claim authorship of One UI X itself.

## Tested baseline

- Device: Samsung Galaxy S24 Ultra (`SM-S928B`)
- Android: 16
- One UI: 8.5
- Root setup: [Root-My-Galaxy](https://github.com/BuSung-dev/Root-My-Galaxy) / KernelSU
- One UI X upstream: 1.7.0 at the pinned commit above
- Vector-SR baseline: device-tested Samsung Shared-UID hotfix `v1.2 (3136)`

## Root-My-Galaxy / KernelSU tested setup

This compatibility build was tested on an `SM-S928B` using a KernelSU/root environment set up with [Root-My-Galaxy](https://github.com/BuSung-dev/Root-My-Galaxy). **Root-My-Galaxy is not identified as the cause of the Vector-SR compatibility issue described here**; it is mentioned only because it is part of a known-tested setup.

If your S24 Ultra was rooted using Root-My-Galaxy and Vector-SR becomes unstable after a KernelSU soft restart — especially with repeated `NameNotFoundException: android.uid.system` / `VectorLegacyBridge` logging — use the separate [Vector-SR S24U Shared-UID Hotfix](https://github.com/peppicry/Vector-SR-S24U-Hotfix). That project addresses the Vector-side Shared-UID issue.

This One UI X build is designed to run alongside that fixed Vector-SR baseline. Its own changes restore Samsung's real-time network-speed controls and adapt the separate upload/download indicator for the tested One UI 8.5 environment.

## Required SystemUI-only restart after soft restart

On the tested `SM-S928B` setup, **Vector-SR and the One UI X app can both open normally after a KernelSU soft restart**. The specific observed problem is that One UI X functions targeting `com.android.systemui` can remain inactive until that process is restarted once.

Restart **only Samsung SystemUI**:

```sh
su -c 'kill $(pidof com.android.systemui)'
```

Android respawns `com.android.systemui` automatically. The status bar / Quick Settings can disappear briefly; once SystemUI returns, the tested setup activates the One UI X functions that depend on Vector-SR hooks in that process.

This is **not** a Vector-SR startup failure and **not** an One UI X app startup failure. It is a SystemUI-process hook activation/reinjection step. It is also **unrelated to the separate overheating investigation** and should not be used or documented as a thermal workaround.

Only the SystemUI process needs this restart. There is no need to reinstall Vector-SR, restart the One UI X app, repeat the full KernelSU soft restart, or repeatedly kill SystemUI after the functions are active.

## What this compatibility patch changes

1. Keeps both Samsung network-speed CSC gates enabled in Settings/SystemUI.
2. Forces `StatusBarNetworkSpeedController#getAvailabilityStatus()` to report AVAILABLE.
3. Recreates the missing `network_speed` switch in **Settings > Notifications > Advanced settings** when the tested One UI 8.5 build omits it.
4. Binds that switch directly to `Settings.System["network_speed"]`; on-device testing confirmed that turning it off hides the indicator and turning it on restores it.
5. Converts separate upload/download speed display from bytes/s to **bits/s** using decimal SI units: `b`, `Kb`, `Mb`, `Gb`.
6. Changes the separate upload/download refresh interval from 3000 ms to **1000 ms**.

Example: raw traffic around `12.5 MB/s` displays as approximately `100Mb`.

## Source and reproducibility

This repository stores the patch and build harness rather than pretending the upstream project is original work here:

- `patch/apply_oneuix_vector_sr_compat.py` — applies the documented modification to the pinned upstream revision.
- `scripts/build-windows.ps1` — reproducible Windows build helper.
- `UPSTREAM.md` — upstream revision, attribution, licensing, and relationship details.
- `NOTICE.md` — unofficial-build and signing notice.
- `LICENSE.txt` — complete AGPL-3.0 license text carried forward from upstream.

Each GitHub Release generates and publishes `OneUIX-VectorSR-S24U.zip` directly from these tracked repository files. The portable package contains the README, build helper, patch, complete AGPL-3.0 license, upstream attribution, and unofficial-build notice.

Each Release also publishes a **corresponding-source ZIP generated from the patched One UI X working tree before compilation**, alongside source metadata and checksums. That archive is intended to make the exact source used for the released APK directly available from the same Release.

## Release signing

Release APKs from this compatibility project are signed with the **compatibility-project maintainer's signing key**, **not** with the upstream One UI X signing key.

Expected signing-certificate SHA-256:

`42eca8748569e3269d746706171969fe87fa635e804fae3265d9a850f7476ed8`

The private signing key and its password are stored only as protected GitHub Actions secrets and are not committed to this repository. The release workflow refuses to publish an APK if the signer certificate does not match the expected fingerprint.

Because the signing key differs from upstream, Android may require uninstalling a differently signed One UI X build before installing this one.

## Build from this repository on Windows

Open PowerShell in the repository root and configure a suitable JDK. The device-tested local build succeeded with Android Studio's JBR, while CI uses Temurin 25 for the pinned upstream build configuration.

```powershell
$env:JAVA_HOME="C:\Program Files\Android\Android Studio\jbr"
$env:Path="$env:JAVA_HOME\bin;$env:Path"
Unblock-File .\scripts\build-windows.ps1
.\scripts\build-windows.ps1
```

APK output:

```text
OneUIX-compat-build\app\build\outputs\apk\release
```

Local builds are unsigned unless you sign them yourself. GitHub Release builds are signed by the repository workflow as described above.

## Installation / validation

- Keep the known-good Vector-SR 3136 baseline unchanged.
- Install this modified One UI X APK and enable its Settings + System UI scopes in Vector-SR.
- Soft reboot.
- Confirm that Vector-SR and One UI X themselves open normally; this does not yet prove the SystemUI-scoped functions are active.
- Run `su -c 'kill $(pidof com.android.systemui)'` once and wait for SystemUI to respawn.
- Open Settings > Notifications > Advanced settings.
- Confirm the real-time network-speed switch is present and controls the indicator.
- Confirm the separate upload/download readout uses `Kb/Mb/Gb` and refreshes about once per second.

## Known unrelated One UI X / One UI 8.5 hooks

The tested firmware still logs missing legacy hook targets such as `NetspeedViewController$NetworkSpeedManager$1` and `QSClockQuickStarHelper` in paths unrelated to this compatibility patch. This project deliberately does not broaden the Vector-SR hotfix to suppress or change those unrelated errors.

## License

One UI X upstream is licensed under **AGPL-3.0**. This modified work is distributed under the same license. See [`LICENSE.txt`](LICENSE.txt) and [`UPSTREAM.md`](UPSTREAM.md).

No warranty is provided. This is a device-specific compatibility project, not an official replacement for One UI X, Vector-SR, or Root-My-Galaxy.
