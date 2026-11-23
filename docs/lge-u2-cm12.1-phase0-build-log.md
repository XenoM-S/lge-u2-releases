# LG Optimus L9 (u2) — cm-12.1 "Phase 0" build log

Running log of every compile blocker fixed while getting the first CyanogenMod 12.1
(Android 5.1.1) build to compile for the LG Optimus L9 family (P760 / P765 / P768 / P769 —
LGE "u2" platform: TI OMAP4430, PowerVR SGX540).

## Environment

- Build host: `ST-RBE-20` (Proxmox VM, Ubuntu 20.04, 32 GB RAM)
- Tree: `/mnt/builds/lineage-12` — target `p760`, build command `brunch p760`
- Kernel: `kernel/lge/omap4-common` (GitHub: `XenoM-S/lge-kernel-omap4`, Linux 3.0.x LGE tree)
- Device trees: `device/lge/u2-common` + `device/lge/p760` (ported from the cm-11.0 trees)
- Previous release: cm-11.0 is frozen (tag `cm-11.0-20261117`, XDA thread live)

## Standing gotchas (re-check every build session)

1. **flex 2.5.39 SIGABRT** — `export LC_ALL=C` must be re-exported in *every* fresh build
   shell before building; the fix does not survive opening a new terminal.
2. **`BOARD_SEPOLICY_UNION` is a whitelist, not an ordering** — every union-listed name must
   exist in `BOARD_SEPOLICY_DIRS`; if a stub is no longer needed, truncate it, don't delete it.
3. **Compile success != boot success** — the hwcomposer 1.1 port is still pending (Phase 1).

## Blocker log

### 1. SELinux: run Phase 0 permissive
Decision: `androidboot.selinux=permissive` added via `BOARD_KERNEL_CMDLINE` for the first
bootable build. Enforcing comes later, after boot is stable.

### 2. TI OMAP_ENHANCEMENT headers under Lollipop
Lollipop reorganized the UAPI header layout into bionic; KK-era TI code (dsscomp / omap /
SGX glue) needed a merged-header strategy plus `TARGET_SPECIFIC_HEADER_PATH` shadowing to
compile against the new world.

### 3. flex SIGABRT
flex fix, part 1: flex 2.5.39 aborts in UTF-8 locales while generating parsers 
during the build.
Fix: `export LC_ALL=C` in every fresh build shell.
flex fix, part 2: the prebuilts flex-2.5.39 binary itself was replaced with a 
symlink to host flex 2.6.4 (committed in prebuilts/misc); the java version 
check in build/core/main.mk was likewise relaxed for Zulu 7's "openjdk 
version" output (committed in build).

### 4. sepolicy POLICYVERS
Pinned / pre-checked `POLICYVERS=26` against the 3.0 kernel so the generated policy file is
one the kernel can actually load.

### 5. sepolicy union semantics + duplicate declarations
- Symptom: `No sepolicy file found for X` / checkpolicy duplicate type-declaration errors.
- Root cause: the union is a name whitelist (files must exist in a policy dir); all external
  `.te` files glue alphabetically first, then device `.te` files in `BOARD_SEPOLICY_DIRS`
  order — declarations must appear exactly once, rules may repeat freely.
- Fix: truncated union-listed stubs, deduplicated declarations; built the sandbox tool
  `sepolicy_audit.py` (declaration parsing, unknown type/attribute/class detection,
  duplicate detection, macro reference checks).

### 6. Audio HAL — audio device API 3.0 break
- Symptom: KK audio HALs hard-fail: `audio_in_acoustics_t` no longer exists;
  `get_input_buffer_size`, `open_input_stream`, `open_output_stream` signatures changed.
- Root cause: cm-12.1 `hardware/libhardware/include/hardware/audio.h` is
  `AUDIO_DEVICE_API_VERSION_CURRENT` 3.0; L AudioFlinger refuses modules < 2.0 and
  requires `get_supported_devices`.
- Fix: port pattern — rename old function bodies, add thin 3.0 wrappers that unpack
  `struct audio_config` into the old pointer-out parameters, implement
  `get_supported_devices`. Applied to both HAL sources (`audio_hw.c` + `hdmi_audio_hw.c`).

### 7. hwcomposer.u2 — undeclared `FB_FLAG_RATIO_4_3` / `FB_FLAG_RATIO_16_9` (2026-11-23)
- Symptom: `hwc.c:884/887` errors inside `set_best_hdmi_mode()`; the rest of the module
  (`sw_vsync.c`, `rgz_2d.c`, `dock_image.c`) compiles with warnings only. The framework
  string-translation warnings in the same log are unrelated noise.
- Root cause: LG added custom HDMI aspect-ratio bits to the kernel's `linux/fb.h`:
  `FB_FLAG_RATIO_4_3 = 64`, `FB_FLAG_RATIO_16_9 = 128`, `FB_FLAG_PIXEL_REPEAT = 256`.
  The kernel tags each HDMI modedb entry with these bits so userspace can mirror with the
  correct aspect ratio. KitKat gave userspace two redundant sources of fb.h: the device
  kernel's `headers_install` output was added to every module's include path, and KK-era
  bionic's own kernel headers came from TI-enhanced kernels (cm-11.0 bionic's
  `libc/kernel/common/linux/fb.h` literally contains these defines — verified). Lollipop
  removed both sources, so hwc.c now sees bionic's mainline-generated
  `libc/kernel/uapi/linux/fb.h` — which has the `fb_videomode.flag` field (reached via
  dsscomp.h's "copy of fb_videomode") but none of LG's flag values.
- Values verified against the actual kernel source before patching: 64/128 are bits 6/7,
  deliberately above the upstream `FB_MODE_IS_*` namespace (bits 0-5) that shares the same
  field. Guessing 1/2 would have compiled and silently made every HDMI mode look 4:3.
- Fix: guarded re-declaration of the two flags in `hwc.c` (idempotent patch, backup kept).
  `FB_FLAG_PIXEL_REPEAT` exists in the kernel but is unused by userspace, so it is not
  re-declared.
- Artifact: `u2-hwc-fb-ratio-flags.patch`; if the tree drifts later, regenerate with
  `git diff` inside `device/lge/u2-common` after applying.
- The remaining ~156 lines of the build block are unused-parameter/variable warnings —
  checked for implicit declarations, pointer/type conflicts and undefined references; none.

### 8. camera.u2 — undeclared `CAMERA_CMD_SETUP_EXTENDED_OPERATIONS` (2026-11-24)
- Symptom: single error at `CameraHal_Module.cpp:528` inside `camera_send_command()`.
  The other ~30 lines are warnings: unused parameters, sign-compares, and missing field
  initializers on `camera_module_t` (`set_callbacks`, `get_vendor_tag_ops`, `open_legacy`,
  `reserved`) — cosmetic here, because the module declares camera module API 1.0
  (`version_major: 1` in `HAL_MODULE_INFO_SYM`), which Lollipop's CameraService still
  serves on the legacy path without `set_callbacks`.
- Root cause: TI's OMAP_ENHANCEMENT camera extension. Command 1024 lets the camera
  service hand the HAL a `camera_device_extended_ops_t` function table (extended preview
  ops / buffer source / reprocess entry points). In KK the tree shadowed TI copies of
  `system/camera.h` + `hardware/camera.h` over AOSP's via `TARGET_SPECIFIC_HEADER_PATH`,
  so the constant was visible. In the 12.1 port the TI struct + helper inline
  (`camera_cmd_send_command_args_to_pointer`) still resolve via the TI `hardware/camera.h`
  copy, but the constant from the shadowed `system/camera.h` (line 245) no longer reaches
  the build.
- Family sweep before patching: all sibling TI additions verified —
  `CAMERA_CMD_PREVIEW_INITIALIZATION/DEINITIALIZATION` (`OMAP_ENHANCEMENT_VTC`:
  undefined in this build, uses compile out in both header and CameraHal.cpp), CPCAM
  `camera_frame_metadata_t` fields and their uses in `CameraMetadataResult`/`OMXMetadata`
  (all inside `#ifdef OMAP_ENHANCEMENT_CPCAM`, which the board flags never define —
  same as KK). The extended-ops command is the only live missing symbol.
- Fix: guarded `#define CAMERA_CMD_SETUP_EXTENDED_OPERATIONS 1024` in
  `camera/inc/CameraHal.h` — the umbrella header every camera TU includes, so all ~29
  source files see it, including TUs that had not compiled yet.
- Artifact: `u2-camera-cmd-extended-ops.patch`.
- Watch item: `camera/Android.mk` links static `libcpcamcamera_client` when
  `OMAP_ENHANCEMENT_CPCAM` is defined; board flags keep it undefined (as in KK), so no
  TI frameworks/av static lib is needed at link time.

### 9. camera.u2 — missing `linux/videodev.h` (V4L1 header removed) (2026-11-24)
- Symptom: `fatal error: linux/videodev.h: No such file or directory` at
  `V4LCameraAdapter.cpp:39`. All OMX adapter TUs compiled with warnings only — the
  extended-ops fix (entry 8) unblocked the whole OMX half of the module.
- Root cause: dead include, not a real dependency. The file's own doc comment says it
  maps the HAL to V4L2, and `V4LCameraAdapter.h:22` includes `<linux/videodev2.h>`.
  A tree-wide sweep for V4L1 symbols (`video_capability`, `video_picture`, `video_mmap`,
  `VIDIOCG*`...) found zero uses — the only "VIDIO" in the module is a comment that even
  misspells the V4L2 ioctl name. cm-11.0 compiled only because KK-era bionic's
  `libc/kernel/common/linux/videodev.h` was a fossil sanitized from a pre-2011 kernel
  (346 lines, verified on GitHub); mainline kernels dropped V4L1 in 2.6.39 (2011) and
  Lollipop's regenerated bionic UAPI dropped the header with them.
- Fix: replaced the include with an explanatory comment in `V4LCameraAdapter.cpp`. No
  shim header needed — nothing used V4L1. Lesson recorded: a missing header does not
  mean you must create it; first check whether anything actually uses it.
- Include sweep: `<linux/videodev.h>` + `<linux/videodev2.h>` are the only kernel
  headers in the whole camera module — no further obsolete includes hiding.
- Artifact: `u2-v4l-drop-videodev-include.patch`.

## Roadmap

1. More Phase 0 compile blockers as they surface (camera/OMX glue, lights, sensors, ...).
2. Phase 1: hwcomposer 1.1 port — mandatory for a bootable 12.1; SurfaceFlinger's composer
   path requires it.
3. TWRP via `azwhikaru/Action-TWRP-Builder`.
4. LineageOS 13.0 afterwards; 14.1 / 15.1 feasibility later.
5. Full documentation write-up (this log is the seed).

## Sources opened for entry 7

- `kernel/lge/omap4-common` `include/linux/fb.h` (cm-11.0 branch):
  https://raw.githubusercontent.com/XenoM-S/lge-kernel-omap4/cm-11.0/include/linux/fb.h
- bionic UAPI `linux/fb.h` (cm-12.1):
  https://raw.githubusercontent.com/LineageOS/android_bionic/cm-12.1/libc/kernel/uapi/linux/fb.h
- bionic kernel `linux/fb.h` (cm-11.0 — contains the flags, proving the KK source path):
  https://raw.githubusercontent.com/LineageOS/android_bionic/cm-11.0/libc/kernel/common/linux/fb.h
