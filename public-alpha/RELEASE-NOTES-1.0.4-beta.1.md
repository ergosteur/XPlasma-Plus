# XPlasma Plus 1.0.4 Beta 1 (ergosteur fork)

An unofficial fork of [andymenard/XPlasma-Plus](https://github.com/andymenard/XPlasma-Plus) 1.0.3. It adds Plasma 6.8 support, a set of optional customizations, and fixes. Report problems with this build on [this fork's issues](https://github.com/ergosteur/XPlasma-Plus/issues), not upstream.

## Tested

- **Fedora 45 KDE** (Plasma 6.8.3, Qt 6.11): fresh install, and switching from 1.0.3 by removing 1.0.3 first and then installing this build.
- **Kubuntu 26.04** (Plasma 6.6.7, Qt 6.10): fresh install with every feature, including the XP login screen, lock screen and boot splash, and then Remove.

Installing this build over 1.0.3 in place (Upgrade installation) has not been tested. Removing 1.0.3 first has been.

## New

- **Plasma 6.8:** the XP taskbar, tray, notifications and panel build for 6.8, and the caption animation supports KWin 6.8. 1.0.3 couldn't build the caption animation on 6.8.
- **XP-styled keyboard-layout indicator** for the tray.
- **Optional customizations**, under their own heading in Setup. Each is off unless you tick it:
  - Always show the notifications bell in the system tray
  - Show Desktop button in Quick Launch
  - Smooth screen fonts with ClearType. This is the same setting as Display Properties' font smoothing, which replaces "Crisp XP text".
  - Keep Firefox's own icon
  - Breeze text, crosshair and other thin black pointers. XP drew these by inverting the screen, which Linux cursors can't do, so they came out as thin black lines.
  - Plasma's notification popups instead of XP balloons
  - Keep your own fixed-width font
  - Dolphin: Explorer-like toolbar and menu bar
- **Plasma's own lock screen** (when the XP lock screen isn't selected) gets XP's Welcome screen as its background, so its text is readable.

## Fixes

- XP icon theme corrections that stay in place across theme changes.
- Desktop icon cells are wide enough that "My Documents" stays on one line.
- Notification balloons no longer leave their tray icon behind after the notification leaves the history.
- The taskbar theme's dark areas stay dark behind light text.
- The Zune and Embedded colour variants of Royale use Royale's fonts, in dark mode too.

## Downloads

There is one installer, `generic`. It compiles the XP taskbar and other native parts on your machine, which took about 8 minutes in testing, and installs the build tools it needs through your package manager (APT, DNF, pacman or Zypper). Upstream's prebuilt binaries don't match this fork's native code, so a distribution-specific download wouldn't be any faster.

## Verify your download

```sh
sha256sum -c SHA256SUMS
```

This build is **not signed** with upstream's release key. Its checksum is published here only.

Original XP artwork, the renamed Tahoma fonts and the wallpaper photographs keep their owners' copyrights, as in upstream's releases (see ASSET-DISTRIBUTION.md). The code is GPL-3.0-or-later. No OTA update feed is included. New versions will appear on this fork's Releases page.
