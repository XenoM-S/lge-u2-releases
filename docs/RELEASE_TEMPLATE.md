# Release notes template

Copy the block below into the GitHub Release description for each build wave.
Tag convention: `cm-12.1-YYYYMMDD`, created on the lge-u2-releases commit that
documents the wave. Attach the device zips plus one `SHA256SUMS` file — never
commit zips into git.

Collect the source SHAs right after the build:

    for r in device/lge/u2-common kernel/lge/omap4-common vendor/lge/u2 \
             device/lge/p760 device/lge/p765 device/lge/p768 device/lge/p769; do
      echo "$r -> $(git -C ~/android/lineage/$r rev-parse --short HEAD)  $(git -C ~/android/lineage/$r log -1 --format=%s)"
    done

---

**Unofficial Lineage 11.0 build — 【YYYYMMDD】**

- LG-P760: `lineage-12.1-【YYYYMMDD】-UNOFFICIAL-p760.zip`
- LG-P765: `lineage-12.1-【YYYYMMDD】-UNOFFICIAL-p765.zip`
- LG-P768: `lineage-12.1-【YYYYMMDD】-UNOFFICIAL-p768.zip`
- LG-P769: `lineage-12.1-【YYYYMMDD】-UNOFFICIAL-p769.zip`

### Sources used for this build

Shared across all four devices:

- `device/lge/u2-common` @ 【short SHA】
- `kernel/lge/omap4-common` @ 【short SHA】
- `vendor/lge/u2` @ 【short SHA】

Per-device:

- `device/lge/p760` @ 【short SHA】
- `device/lge/p765` @ 【short SHA】
- `device/lge/p768` @ 【short SHA】
- `device/lge/p769` @ 【short SHA】

### SHA256

```
【paste contents of SHA256SUMS】
```

### Notes / known issues

- 【fill in per wave, e.g. p765/p768/p769 built but awaiting community test reports】
