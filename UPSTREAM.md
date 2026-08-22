# Upstream, attribution, and licensing

This repository is an **unofficial device-specific modified build/compatibility project** around One UI X. It is not affiliated with or endorsed by the upstream developers.

## One UI X

- Upstream project: `SoClear/OneUIX`
- Pinned revision: `78e2ef1d10320aab293631f97ec636cf64d4cbea`
- Upstream version at that revision: `1.7.0 (9)`
- Upstream license: **GNU Affero General Public License v3.0 (AGPL-3.0)**
- Upstream license file: `LICENSE.txt`
- Modified-version date: **2026-08-22**
- Modified versionName: `1.7.0-vectorsr-s24u`

The original project history and copyright attribution remain with the One UI X authors and contributors. The compatibility changes in this repository are clearly identified as modifications and are distributed under AGPL-3.0. The complete license text is included at the repository root.

The patch is applied to the pinned upstream source during builds. Each Release publishes the patched corresponding source used for that APK, in addition to the reproducible patch/build harness.

## Vector-SR compatibility baseline

This project was device-tested alongside the separate `Vector-SR-S24U-Hotfix` repository using Vector-SR v1.2 (3136). Vector-SR source is not vendored into this repository and is not modified by this One UI X patch.

Vector-SR remains a separate upstream-derived GPL-3.0 project with its own attribution and license obligations.

## Support boundary

Issues caused by this modified build should be reported to this compatibility project. Upstream maintainers should not be expected to support behavior that cannot be reproduced on their unmodified releases.
