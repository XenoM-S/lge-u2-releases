# Installing

> Community ROM for the LG Optimus L9 family. Flash only the zip that matches
> your exact model (P760 / P765 / P768 / P769). Cross-flashing between models
> is not supported and not tested.

1. **Custom recovery.** You need a working custom recovery on the device. The
   original CM11 threads for the Optimus L9 (u2 platform) describe how to
   install recovery on this hardware — see the XDA thread linked from the
   README.
2. **Back up.** Take a full nandroid backup from recovery before flashing
   anything.
3. When coming from another ROM: factory reset, and wipe cache + dalvik.
4. Flash the device zip (`lineage-11-<date>-UNOFFICIAL-<device>.zip`) from the
   [Releases](https://github.com/XenoM-S/lge-u2-releases/releases) page.
5. Optional: flash a CM11/KitKat-compatible GApps package of your choice.
6. Reboot. The first boot takes several minutes (dexopt) — be patient.

## Reporting issues

Report in the XDA thread and include: exact device model, the ROM you came
from, the recovery used, and a `logcat` (or at least a dmesg) if the device
does not boot.
