# This fork: releases and testing

ergosteur's fork of [andymenard/XPlasma-Plus](https://github.com/andymenard/XPlasma-Plus). Work happens on
`installer-options` (the default branch); releases are pre-releases on this fork's
[Releases](https://github.com/ergosteur/XPlasma-Plus/releases) page. Nothing goes upstream until it has been tested here.

## Making a release

Releases are one **generic** installer. The fork's native code doesn't match upstream's prebuilt binaries, so every
installer compiles the XP parts on the user's machine anyway (about 4 to 9 minutes in testing).

1. Set `version` and `label` in `installer/edition.json` and `public-alpha/edition.json` (`X.Y.Z` or
   `X.Y.Z-alpha|beta|rc.N`; the label shows at the foot of Setup).
2. Write `public-alpha/RELEASE-NOTES-<version>.md`: what changed and what was tested. Commit both, so the archive is
   exactly a commit.
3. Build from upstream's extracted **generic** 1.0.3 release, which carries the private inputs (Windows artwork, fonts,
   the Firefox payload):

       tools/fork-release.py --base ~/Downloads/XPlasma-Plus-1.0.3 --out ~/xp-release

   It refreshes the bundle from the checkout (`tools/dev-bundle.py`), writes the release notes, build record and
   checksum manifest, and packages it with `public-alpha/package.py`, which verifies every file inside the archive.
   The result is `~/xp-release/out/`: `xplasma-plus-<version>-installer-generic.tar.gz` and `SHA256SUMS`. Rebuilding
   the same commit gives the same files; only the bundled source archive's gzip timestamp differs.
4. Test that archive on clean VMs (below), every distribution family you claim in the notes.
5. Tag the commit and publish:

       git tag -a v<version> <commit> -m "XPlasma Plus <label>" && git push origin v<version>
       gh release create v<version> --prerelease --title "XPlasma Plus <label>" \
         --notes-file public-alpha/RELEASE-NOTES-<version>.md ~/xp-release/out/*.tar.gz ~/xp-release/out/SHA256SUMS

   Then download it back and run `sha256sum -c SHA256SUMS`. Releases aren't signed: upstream's key isn't ours.

## Testing in VMs

`tools/vm-test.sh` installs into a libvirt VM from a clean snapshot, logs in at the greeter (Plasma Login Manager or
SDDM), runs the installer as the desktop user, and optionally checks the result and removes it again. Each VM is
described in a file outside the repository, `~/.config/xplasma-vm-test/<name>.env` (see the script's header for the
variables: domain, snapshot, SSH target, a command that prints the login password, the screen helper):

    tools/vm-test.sh --vm kubuntu --bundle ~/xp-release/out/xplasma-plus-<version>-installer-generic.tar.gz --check
    tools/vm-test.sh --vm debian --bundle ... --prepare 'sudo apt-get install -y pkexec' --check --remove
    tools/vm-test.sh --vm fedora --tweaks cleartype,dolphin_toolbar --check      # dev bundle from the checkout

A test VM needs: a fresh, updated KDE install; SSH key login; passwordless sudo; and, **for test VMs only**, a polkit
rule letting that user run pkexec without a password, so nothing waits on a prompt:

    // /etc/polkit-1/rules.d/49-test-vm-nopasswd.rules
    polkit.addRule(function(action, subject) { if (subject.user == "USER") { return polkit.Result.YES; } });

`tools/vm-check-fixes.sh` (run inside the guest; `--check` does it) reports the fork's fixes and customizations one
line each. Read settings as the session does: it takes the session's `XDG_CONFIG_DIRS` from plasmashell, since
distributions keep defaults there (Kubuntu's fonts) that an SSH shell wouldn't see.

What has been covered so far: Fedora 45 (Plasma 6.8, also with Fedora Budgie's `sddm-wayland-miriway`), Kubuntu 26.04
(Plasma 6.6) and Debian 13 (Plasma 6.3, the installer's older patched-QML path). Things those found, so they stay found:

- A Dolphin that has never run hides its menu bar on its first start; the installer does that first run offscreen.
- Debian keeps `update-initramfs` in `/usr/sbin`, and its KDE install has no `pkexec`.
- Fonts must be written in QFont's 16-field form; Plasma 6.3's libraries reject Qt 6.9's 19-field one.
- Before Plasma 6.6, a panel widget's scripting `index` does nothing; the panel's `AppletOrder` is written instead.
- SDDM greeter display servers conflict with each other (`sddm-wayland-plasma` vs `sddm-wayland-miriway`).
- Calamares installs (Kubuntu, Debian) leave the account picture as the distribution logo, and Debian's debconf
  without GRUB's install disk (`grub-pc/install_devices`), which breaks the first `apt full-upgrade` of a fresh VM.
- Don't run Qt GUI programs (`plasmashell --version`, `dolphin --version`) over SSH in an Ubuntu guest: they abort
  without a display and leave Apport crash reports that show up on the desktop.
- `DelegateChooser`'s `when:` property (arbitrary per-row conditions, as opposed to `roleValue` matching) needs
  Qt 6.9; Fedora 45, Kubuntu 26.04 and Debian 13 are all below that. Its `Qt.labs.qmlmodels` module needs its own
  import alongside `QtQml.Models` either way (`DelegateChoice` moved there; `DelegateChooser` hasn't), matching how
  KDE's own `ClipboardMenu.qml` imports both.
- Running `tools/vm-test.sh` against more than one VM at once without `--bundle`: they all build into the same
  default `/tmp/xp-dev-bundle` and can stomp each other's copy mid-rsync (`rsync` exit 24, "files vanished"), or
  worse, not error and silently copy a mixed-up bundle. Give each a distinct `--bundle` path, or run them one at a
  time.
- An upgrade that re-selects the same theme with a newly-enabled font/icon customization (ClearType, keep Firefox's
  icon) didn't apply it: `applyLook()`'s `colorOnly` shortcut (meant for Display Properties' live colour preview)
  also kicked in from the installer whenever the look/taskbar/decoration all looked already in place, which forced
  `o.fonts`/`o.icons` off regardless of what changed. The installer's own `apply` call now always passes
  `--no-color-only`.
