# XPlasma Plus 1.0.4 Beta 4 (ergosteur fork)

An unofficial fork of [andymenard/XPlasma-Plus](https://github.com/andymenard/XPlasma-Plus) 1.0.3. It adds Plasma 6.8 support, a set of optional customizations, and fixes. Report problems with this build on [this fork's issues](https://github.com/ergosteur/XPlasma-Plus/issues), not upstream.

## Changed since Beta 3

- **Notifications now route around XP's balloon for the senders that don't suit it.** Browsers' own notices, any website's push notifications, and messaging/chat/IRC apps always skip the XP-styled toast; any other sender does too once it has more notifications queued than a burst threshold. The notification is still recorded in Plasma's own history as usual, it just doesn't pop an XP balloon. The tray's notification icons now share one icon per sender while several of its notifications are still queued, instead of piling up one icon per notification.
- **Unread notification tray icons** now show a small steady red dot in the corner instead of continuously blinking, which got noisy with more than one or two waiting.
- **Upgrade fix:** re-running Setup over an existing install to turn on a font or icon customization (ClearType, "keep Firefox's own icon") without changing the overall theme used to record the setting as on but silently never apply it. A fast path meant only for Display Properties' live colour preview was also kicking in from the installer's one-shot apply, which forced fonts/icons off regardless of what had actually changed. The installer's apply no longer takes that shortcut.
- **Smaller fixes:** "keep Firefox's own icon" now also covers the generic browser icon aliases, not just the Firefox-specific ones; a stale upstream repo link in the installer's failure dialog is corrected; dark mode no longer silently revives the retired "crisp text" pixel-font feature from a stale saved flag; plus a few internal-only correctness fixes (tray-state icon detection, reusing an already-detected config writer, a test script bug) with no user-visible effect.

## Tested

This release's archive:

- **Fedora 45 KDE** (Plasma 6.8): freshly built from this commit, installed end-to-end in a clean VM (theme Royale, every feature) and removed again; the fork's checks pass (14 OK, 0 FAIL).

The underlying fixes, before packaging:

- **Debian 13, Kubuntu 26.04, Fedora 45:** the notification changes, via real installer runs with live triggered notifications.
- **Fedora 45:** the upgrade fix, via a real upgrade over an existing install (`vm-check-fixes.sh` went from 19 OK/4 FAIL to 22 OK/1 FAIL; the one remaining "failure" is a test-sequence artifact, not a real bug).
- **Kubuntu 26.04:** the same upgrade path on a fresh install, which already worked and still does.

## New and fixed in the 1.0.4 betas

See the [Beta 3 notes](https://github.com/ergosteur/XPlasma-Plus/releases/tag/v1.0.4-beta.3) for everything else this fork changes from 1.0.3: Plasma 6.8 support, optional customizations, and the fixes for Fedora, Debian and older Plasma versions.

## Downloads

There is one installer, `generic`. It compiles the XP taskbar and other native parts on your machine, which took about 8 minutes in testing, and installs the build tools it needs through your package manager (APT, DNF, pacman or Zypper). Upstream's prebuilt binaries don't match this fork's native code, so a distribution-specific download wouldn't be any faster.

## Verify your download

```sh
sha256sum -c SHA256SUMS
```

This build is **not signed** with upstream's release key. Its checksum is published here only.

Original XP artwork, the renamed Tahoma fonts and the wallpaper photographs keep their owners' copyrights, as in upstream's releases (see ASSET-DISTRIBUTION.md). The code is GPL-3.0-or-later. No OTA update feed is included. New versions will appear on this fork's Releases page.
