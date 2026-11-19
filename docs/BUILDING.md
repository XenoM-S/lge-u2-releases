# Building for the LG Optimus L9 family (u2)

These builds come from an Android 5.1.1 (CyanogenMod 12.1) source tree, using
the LineageOS-maintained `cm-12.1` manifest branches. When LineageOS forked
CyanogenMod it kept these old manifest branches syncable and lineage-branded,
while the `cm_*` lunch targets stayed in place until LineageOS 15.

## Requirements

- 64-bit Linux host, preferably Ubuntu 20.04 with roughly 100 GB of
  free disk for the source tree and output. If you are building for all devices,
  you want to have roughly 200-350 GB with a 50 GB ccache to speed up the build
  process.
- Host needs at least 4 CPU cores and 16 GB of RAM. (ROMS made in the release repo
  are build on a Ubuntu 20.04 VM with 8 cores and 32 GB of RAM, takes about
  20+ minutes for each device model with these specs).
- The standard CM-12.1 build packages (baseline list below; package names vary
  by distribution release — adjust as needed):

      sudo apt-get install -y git ccache gnupg flex bison gperf imagemagick build-essential \
        zip curl zlib1g-dev gcc-multilib g++-multilib libc6-dev-i386 \
        lib32ncurses-dev lib32readline-dev liblz4-tool libssl-dev x11proto-core-dev libx11-dev lib32z1-dev \
        libwxgtk3.0-dev libgl1-mesa-dev libxml2 libxml2-utils lzop xsltproc unzip \
        schedtool squashfs-tools zlib1g-dev

- **Java 7** (JDK 1.7) — CM-12.1 does not build with newer JDKs. Ubuntu 20.04
  no longer ships `openjdk-7` in the default repositories, so use for example
  Azul Zulu Community 7, or openjdk-7 packages from an older Ubuntu release.
  Like so: 

      sudo apt install -y gnupg ca-certificates curl
      echo "deb [signed-by=/usr/share/keyrings/azul.gpg] https://repos.azul.com/zulu/deb stable main" \
      | sudo tee /etc/apt/sources.list.d/zulu.list
      sudo apt update
      sudo apt install -y zulu7-jdk
     
  `java -version` must report 1.7 before building.
- **Python 2.7** — the CM-12.1 release tools (OTA packaging) are Python 2.
  Make sure `python` resolves to 2.7, e.g.:

      sudo apt install python2
      sudo ln -sf /usr/bin/python2 /usr/local/bin/python

## Get the source

    mkdir -p ~/android/lineage && cd ~/android/lineage
    repo init -u https://github.com/LineageOS/android.git -b cm-12.1

Add the device, kernel and vendor repos via the local manifest:

    mkdir -p .repo/local_manifests
    curl -o .repo/local_manifests/u2.xml \
      https://raw.githubusercontent.com/XenoM-S/lge-u2-releases/cm-11.0/local_manifests/u2.xml

    repo sync -c --no-clone-bundle

## Build

    source build/envsetup.sh
    lunch cm_p760-userdebug     # or cm_p765 / cm_p768 / cm_p769
    brunch cm_p760-userdebug    # or cm_p765 / cm_p768 / cm_p769

The kernel is compiled from source (`kernel/lge/omap4-common`) as part of the
build. The OTA zip lands in `out/target/product/<device>/`.

## Zip naming

The published zips are named `lineage-12.1-<date>-UNOFFICIAL-<device>.zip`. That
naming and the `LINEAGE_VERSION` version string come from the LineageOS
`cm-12.1` branches of the build system itself, not from any local
modifications. Building with the manifest above plus `local_manifests/u2.xml`
therefore reproduces the released zips exactly — no extra forks are needed.

Note the lunch targets stay `cm_p7xx-userdebug` (not `lineage_p7xx`): the
`cm_*` product naming was kept by LineageOS up to and including the 14.1
branch, and only LineageOS 15 introduced `lineage_*` targets.
