# XPlasma Plus 1.0.4 Beta 3 (ergosteur fork)

An unofficial fork of [andymenard/XPlasma-Plus](https://github.com/andymenard/XPlasma-Plus) 1.0.3. It adds Plasma 6.8 support, a set of optional customizations, and fixes. Report problems with this build on [this fork's issues](https://github.com/ergosteur/XPlasma-Plus/issues), not upstream.

## Changed since Beta 2

- **The XP lock screen is gone.** It was ticked by default and broke on Plasma 6.8. The lock screen is now always Plasma's own, with XP's Welcome screen as its background when the wallpaper is installed; Plasma's lock screen keeps working across Plasma updates. Upgrading an installation that has the XP lock screen (or removing it) deletes it, and Plasma's lock screen comes back. A Plasma shell you customized yourself is left alone, and Setup says where it is.
- **IE6 Firefox: wrong Display Properties icon.** The picture-in-picture button shows XP's cascading windows now, and the screen-sharing permission and indicator show XP's screen-sharing icon (RTC Share), crossed out when blocked.

## Tested

This release's archive:

- **Kubuntu 26.04** (Plasma 6.6.7, Qt 6.10): Beta 2 with every feature including its XP lock screen, then upgraded in place to this build: the XP lock screen is removed and Plasma's lock screen shows the XP Welcome background; the fork's checks pass.

Beta 2 was tested on Fedora 45 KDE, Kubuntu 26.04 and Debian 13 (see its notes); nothing distribution-specific changed since.

## New and fixed in the 1.0.4 betas

See the [Beta 2 notes](https://github.com/ergosteur/XPlasma-Plus/releases/tag/v1.0.4-beta.2) for everything else this fork changes from 1.0.3: Plasma 6.8 support, optional customizations, and the fixes for Fedora, Debian and older Plasma versions.

## Downloads

There is one installer, `generic`. It compiles the XP taskbar and other native parts on your machine, which took about 8 minutes in testing, and installs the build tools it needs through your package manager (APT, DNF, pacman or Zypper). Upstream's prebuilt binaries don't match this fork's native code, so a distribution-specific download wouldn't be any faster.

## Verify your download

```sh
sha256sum -c SHA256SUMS
```

This build is **not signed** with upstream's release key. Its checksum is published here only.

Original XP artwork, the renamed Tahoma fonts and the wallpaper photographs keep their owners' copyrights, as in upstream's releases (see ASSET-DISTRIBUTION.md). The code is GPL-3.0-or-later. No OTA update feed is included. New versions will appear on this fork's Releases page.
