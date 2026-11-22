#!/usr/bin/env bash
# Run this checkout's installer in a libvirt test VM from a clean snapshot.
#
#   tools/vm-test.sh [--no-revert] [--features LIST] [--tweaks LIST] [--theme NAME]
#
# Needs: a libvirt domain with an offline snapshot of a fresh KDE desktop, SSH key
# access to the guest user, passwordless sudo + polkit (pkexec) for that user in the
# guest, and a host-side command that prints the guest user's password (to log in at
# the greeter; never echoed). Configure with environment variables:
#   XP_VM=fedora  XP_VM_SNAPSHOT=clean-f45-kde  XP_VM_HOST=192.168.122.59
#   XP_VM_PASSWORD_CMD='...prints the password...'   (required unless already logged in)
#   XP_BASE=~/Downloads/XPlasma-Plus-1.0.3           (extracted official release bundle)
#   XP_VMCTL=~/.claude/skills/libvirt-vm-control/vmctl.py
# The install runs as a transient user unit in the guest's session; its log is
# ~/xp-install.log in the guest. Exit status: the installer's.
set -euo pipefail
VM=${XP_VM:-fedora} SNAP=${XP_VM_SNAPSHOT:-clean-f45-kde} HOST=${XP_VM_HOST:-192.168.122.59}
BASE=${XP_BASE:-$HOME/Downloads/XPlasma-Plus-1.0.3} VMCTL=${XP_VMCTL:-$HOME/.claude/skills/libvirt-vm-control/vmctl.py}
URI=qemu:///system ROOT=$(cd "$(dirname "$0")/.." && pwd)
FEATURES=apps,behavior,boot,caption_animation,desktop,desktop_icons,firefox,fonts,icons,pointers,session,sounds,taskbar,theme_manager,user_pictures,wallpaper,welcome_splash
TWEAKS="" THEME="Luna Blue" REVERT=1
while [ $# -gt 0 ]; do case $1 in
  --no-revert) REVERT=0;; --features) FEATURES=$2; shift;; --tweaks) TWEAKS=$2; shift;; --theme) THEME=$2; shift;;
  *) echo "unknown option $1" >&2; exit 2;; esac; shift; done
ssh_() { ssh -o BatchMode=yes -o ConnectTimeout=5 "$HOST" "$@"; }
say() { printf '== %s\n' "$*"; }

if [ $REVERT = 1 ]; then
  say "reverting $VM to $SNAP"
  [ "$(virsh -c $URI domstate "$VM")" = "shut off" ] || virsh -c $URI destroy "$VM" >/dev/null
  virsh -c $URI snapshot-revert "$VM" "$SNAP" >/dev/null
  virsh -c $URI start "$VM" >/dev/null
fi
say "waiting for SSH"
for _ in $(seq 1 60); do ssh_ true 2>/dev/null && break; sleep 3; done
say "building the dev bundle"
python3 "$ROOT/tools/dev-bundle.py" --base "$BASE" --out "${TMPDIR:-/tmp}/xp-dev-bundle" --push "$HOST:xp-dev" 2>&1 | grep -v -e DeprecationWarning -e getdata
if ! ssh_ 'loginctl list-sessions --no-legend | grep -q " seat0 .* user "'; then
  : "${XP_VM_PASSWORD_CMD:?set XP_VM_PASSWORD_CMD to log in at the greeter}"
  say "logging in at the greeter"
  for _ in $(seq 1 30); do ssh_ 'loginctl list-sessions --no-legend | grep -q greeter' && break; sleep 2; done
  sleep 5
  size=$("$VMCTL" "$VM" size); w=${size%x*}; h=${size#*x}
  "$VMCTL" "$VM" click $((w * 620 / 1280)) $((h * 478 / 800))   # Plasma Login Manager's password field
  bash -c "$XP_VM_PASSWORD_CMD" | "$VMCTL" "$VM" type
  "$VMCTL" "$VM" key enter
  for _ in $(seq 1 40); do ssh_ 'loginctl list-sessions --no-legend | grep -q " seat0 .* user "' && break; sleep 2; done
  sleep 10   # let plasmashell finish loading its panels
fi
say "installing: features=$FEATURES tweaks=${TWEAKS:-none} theme=$THEME"
ssh_ "systemctl --user reset-failed xp-install 2>/dev/null; rm -f ~/xp-install.log; cd ~/xp-dev && systemd-run --user --unit=xp-install --same-dir \
  -p StandardOutput=file:/home/\$USER/xp-install.log -p StandardError=inherit \
  python3 -u backend.py install --features '$FEATURES' --theme '$THEME' --tweaks '$TWEAKS'" >/dev/null
while ssh_ 'systemctl --user is-active -q xp-install' 2>/dev/null; do sleep 15; done
ssh_ 'systemctl --user reset-failed xp-install 2>/dev/null; true'
ssh_ 'grep -E "^@@|^ERROR|^Customization" ~/xp-install.log' | sed 's/^@@/  /' || true
# The installer's own last word, not the unit's status.
if ssh_ 'grep -qE "Installed successfully|Upgraded successfully" ~/xp-install.log && ! grep -q "^ERROR" ~/xp-install.log'; then
  say "installed successfully"; exit 0
fi
say "installation FAILED (see ~/xp-install.log in the guest)"; exit 1
