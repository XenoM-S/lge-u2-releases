# Lineage 12.1 (Android 5.1.1) for the LG Optimus L9 family (u2)

Unofficial, community builds of Android 5.1.1 (CyanogenMod 12.1 base, built
from the LineageOS-maintained `cm-12.1` manifest branches) for the LG Optimus
L9 family — LGE "u2" platform, TI OMAP4430 + PowerVR SGX540.

| Device | Model | Build target | Status |
| ------ | ----- | ------------ | ------ |
| Optimus L9 | LG-P760 | `cm_p760-userdebug` | Build staging |
| Optimus L9 | LG-P765 | `cm_p765-userdebug` | Build staging |
| Optimus L9 | LG-P768 | `cm_p768-userdebug` | Build staging |
| Optimus L9 | LG-P769 | `cm_p769-userdebug` | Build staging |

All four variants share the same hardware platform and the same kernel, vendor
blob set and shared device layer; each device tree only carries per-variant
configuration.

## Downloads

See [Releases](https://github.com/XenoM-S/lge-u2-releases/releases). Each
release contains one zip per device plus a `SHA256SUMS` file, and the release
notes list the exact source commit SHAs the wave was built from. Use the zip
that matches your exact model.

## Installing

See [docs/INSTALLING.md](docs/INSTALLING.md).

## Building from source

See [docs/BUILDING.md](docs/BUILDING.md). The device, kernel and vendor repos
you need are pinned in
[local_manifests/u2.xml](local_manifests/u2.xml).

## Source repositories

| Component | Repository |
| --------- | ---------- |
| Device trees | [p760](https://github.com/XenoM-S/android_device_lge_p760) · [p765](https://github.com/XenoM-S/android_device_lge_p765) · [p768](https://github.com/XenoM-S/android_device_lge_p768) · [p769](https://github.com/XenoM-S/android_device_lge_p769) |
| Shared device layer | [android_device_lge_u2-common](https://github.com/XenoM-S/android_device_lge_u2-common) |
| Kernel | [lge-kernel-omap4](https://github.com/XenoM-S/lge-kernel-omap4) |
| Proprietary blobs | [proprietary_vendor_lge_u2](https://github.com/XenoM-S/proprietary_vendor_lge_u2) |

## Credits

- [dhiru1602](https://github.com/dhiru1602) — original CM11 device trees for
  the Optimus L9 family and the vendor blob extraction that this project is
  built on.
- LGE / AOSP — proprietary blobs and platform code remain the property of
  their respective copyright holders.
- Adding the p765/p768/p769 build targets and the accompanying fixes was
  assisted by an AI coding assistant (GLM); all changes were reviewed, built
  and (for p760) tested by XenoM-S.

XDA thread: [ Fill in when ready ]
