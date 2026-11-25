#!/usr/bin/env bash
# Run an XPlasma Plus installer in a libvirt test VM, from a clean snapshot.
#
#   tools/vm-test.sh --vm NAME [--bundle PATH] [--features LIST] [--tweaks LIST] [--theme NAME]
#                    [--options "--hidpi-icons ..."] [--prepare 'command'] [--no-revert] [--check] [--remove]
#
# --bundle   a release tarball (xplasma-plus-*-installer-*.tar.gz, checked against a
#            SHA256SUMS beside it when there is one) or an extracted bundle directory.
#            Without it, a dev bundle is built from this checkout (tools/dev-bundle.py,
#            XP_BASE = an extracted official release for the private inputs).
# --prepare  a command to run in the guest (over SSH) before installing, e.g. what the
#            installer would ask a user to do first ('sudo apt-get install -y pkexec').
# --check    afterwards, run tools/vm-check-fixes.sh in the guest.
# --remove   afterwards, Remove the installation and show what changed on the system
#            side (display manager, SDDM, Plymouth, system themes) between the two.
#
# The VM is described by environment variables, usually from a file that stays
# outside the repository: --vm NAME sources ${XDG_CONFIG_HOME:-~/.config}/xplasma-vm-test/NAME.env
#   XP_VM=domain-name               libvirt domain (on XP_VM_URI, default qemu:///system)
#   XP_VM_SNAPSHOT=snapshot         offline snapshot of a fresh, updated KDE desktop
#   XP_VM_HOST=user@address         SSH target: key login, passwordless sudo, and a polkit
#                                   rule letting that user run pkexec without a password
#   XP_VM_PASSWORD_CMD='command'    prints the guest user's password, to log in at the
#                                   greeter (piped straight into the VM, never echoed)
#   XP_VMCTL=path/to/vmctl.py       screenshot/keyboard/mouse helper for libvirt guests
#                                   (screenshot via virsh, keys via send-key, pointer via QMP)
#   XP_VM_FEATURES=list             default --features for this VM (e.g. without login)
#   XP_BASE=dir                     extracted official release, for dev bundles
# The install runs as a transient user unit in the guest's session; its log is
# ~/xp-install.log in the guest. Exit status: the installer's (and Remove's).
set -euo pipefail
ROOT=$(cd "$(dirname "$0")/.." && pwd)
ALL=apps,behavior,boot,caption_animation,desktop,desktop_icons,firefox,fonts,icons,lock,login,pointers,session,sounds,taskbar,theme_manager,user_pictures,wallpaper,welcome_splash
FEATURES="" TWEAKS="" THEME=Royale OPTIONS="" PREPARE="" BUNDLE="" REVERT=1 CHECK=0 REMOVE=0
while [ $# -gt 0 ]; do case $1 in
  --vm) f=${XDG_CONFIG_HOME:-$HOME/.config}/xplasma-vm-test/$2.env; [ -f "$f" ] || { echo "no $f" >&2; exit 2; }
        set -a; . "$f"; set +a; shift;;
  --bundle) BUNDLE=$(realpath "$2"); shift;; --features) FEATURES=$2; shift;; --tweaks) TWEAKS=$2; shift;;
  --theme) THEME=$2; shift;; --options) OPTIONS=$2; shift;; --prepare) PREPARE=$2; shift;;
  --no-revert) REVERT=0;; --check) CHECK=1;; --remove) REMOVE=1;;
  -h|--help) sed -n '2,/^set -e/p' "$0" | sed '$d; s/^# \{0,1\}//'; exit 0;;
  *) echo "unknown option $1" >&2; exit 2;; esac; shift; done
: "${XP_VM:?set XP_VM (or use --vm NAME)}" "${XP_VM_HOST:?set XP_VM_HOST}"
URI=${XP_VM_URI:-qemu:///system} FEATURES=${FEATURES:-${XP_VM_FEATURES:-$ALL}}
ssh_() { ssh -o BatchMode=yes -o ConnectTimeout=5 "$XP_VM_HOST" "$@"; }
say() { printf '== [%s] %s\n' "$XP_VM" "$*"; }
logged_in() { ssh_ 'loginctl list-sessions --no-legend | grep -q " seat0 .* user "'; }

if [ $REVERT = 1 ]; then
  : "${XP_VM_SNAPSHOT:?set XP_VM_SNAPSHOT}"
  say "reverting to $XP_VM_SNAPSHOT"
  [ "$(virsh -c "$URI" domstate "$XP_VM")" = "shut off" ] || virsh -c "$URI" destroy "$XP_VM" >/dev/null
  virsh -c "$URI" snapshot-revert "$XP_VM" "$XP_VM_SNAPSHOT" >/dev/null
  virsh -c "$URI" start "$XP_VM" >/dev/null
fi
say "waiting for SSH"
for _ in $(seq 1 60); do ssh_ true 2>/dev/null && break; sleep 3; done

# The installer to run, as ~/xp-test in the guest.
if [ -z "$BUNDLE" ]; then
  : "${XP_BASE:?set XP_BASE to an extracted official release, or pass --bundle}"
  say "building a dev bundle from this checkout"
  python3 "$ROOT/tools/dev-bundle.py" --base "$XP_BASE" --out "${TMPDIR:-/tmp}/xp-dev-bundle" 2>&1 | grep -v -e DeprecationWarning -e getdata
  BUNDLE=${TMPDIR:-/tmp}/xp-dev-bundle
fi
if [ -d "$BUNDLE" ]; then
  say "copying $BUNDLE"
  rsync -a --delete --exclude __pycache__ "$BUNDLE/" "$XP_VM_HOST:xp-test/"
else
  sums=$(dirname "$BUNDLE")/SHA256SUMS
  say "copying $(basename "$BUNDLE")"
  scp -q "$BUNDLE" "$XP_VM_HOST:xp-test.tar.gz"
  if [ -f "$sums" ]; then
    expected=$(awk -v f="$(basename "$BUNDLE")" '$2==f{print $1}' "$sums")
    [ -n "$expected" ] && ssh_ "echo '$expected  xp-test.tar.gz' | sha256sum -c --quiet" && say "checksum OK"
  fi
  ssh_ 'rm -rf xp-test xp-test.new && mkdir xp-test.new && tar xzf xp-test.tar.gz -C xp-test.new --strip-components=1 && mv xp-test.new xp-test'
fi
ssh_ 'python3 -c "import json;print(json.load(open(\"xp-test/edition.json\"))[\"label\"])"' | sed "s/^/== [$XP_VM] edition: /" || true

if ! logged_in; then
  : "${XP_VM_PASSWORD_CMD:?set XP_VM_PASSWORD_CMD to log in at the greeter}" "${XP_VMCTL:?set XP_VMCTL to log in at the greeter}"
  say "logging in at the greeter"
  for _ in $(seq 1 30); do ssh_ 'loginctl list-sessions --no-legend | grep -q greeter' && break; sleep 2; done
  sleep 8
  size=$("$XP_VMCTL" "$XP_VM" size); w=${size%x*}; h=${size#*x}
  # The password field of Plasma Login Manager's and SDDM's Breeze greeters. The first
  # click also wakes SDDM's clock screen; then clear whatever a key may have typed.
  "$XP_VMCTL" "$XP_VM" click $((w * 620 / 1280)) $((h * 478 / 800)); sleep 2
  "$XP_VMCTL" "$XP_VM" key ctrl+a backspace; sleep 1
  bash -c "$XP_VM_PASSWORD_CMD" | "$XP_VMCTL" "$XP_VM" type
  sleep 2; "$XP_VMCTL" "$XP_VM" key enter
  for _ in $(seq 1 40); do logged_in && break; sleep 2; done
  logged_in || { say "login FAILED"; exit 1; }
  sleep 15   # let plasmashell finish loading its panels
fi

run_unit() { # name, backend arguments; waits; prints the log's phases and errors
  ssh_ "systemctl --user reset-failed $1 2>/dev/null; rm -f ~/$1.log; cd ~/xp-test && systemd-run --user --unit=$1 --same-dir \
    -p StandardOutput=file:/home/\$USER/$1.log -p StandardError=inherit python3 -u backend.py $2" >/dev/null
  local start=$SECONDS
  while ssh_ "systemctl --user is-active -q $1" 2>/dev/null; do sleep 15; done
  ssh_ "systemctl --user reset-failed $1 2>/dev/null; true"
  say "$1 took $(( (SECONDS - start) / 60 )) min"
  ssh_ "grep -E '^@@|^ERROR|^Customization' ~/$1.log" | sed 's/^@@/  /' || true
}
system_state() { # the system-side pieces an installation changes
  ssh_ 'readlink -f /etc/systemd/system/display-manager.service
    for f in /etc/sddm.conf /etc/sddm.conf.d/*; do [ -e "$f" ] && grep -H -E "^Current=|^CursorTheme=" "$f"; done
    ls -d /usr/share/sddm/themes/* /usr/share/plymouth/themes/xp-* /usr/share/icons/xp-* /etc/xdg/autostart/xp-* /usr/local/libexec/xp-* /etc/fonts/conf.d/*xp* 2>/dev/null
    update-alternatives --query default.plymouth 2>/dev/null | grep ^Value; grep -h "^Theme" /etc/plymouth/plymouthd.conf 2>/dev/null
    true'
}

[ -n "$PREPARE" ] && { say "prepare: $PREPARE"; ssh_ "$PREPARE" 2>&1 | tail -3; }
say "installing: features=$FEATURES tweaks=${TWEAKS:-none} theme=$THEME"
run_unit xp-install "install --features '$FEATURES' --theme '$THEME' ${TWEAKS:+--tweaks '$TWEAKS'} $OPTIONS"
# The installer's own last word, not the unit's status.
if ! ssh_ 'grep -qE "Installed successfully|Upgraded successfully" ~/xp-install.log && ! grep -q "^ERROR" ~/xp-install.log'; then
  say "installation FAILED (see ~/xp-install.log in the guest)"; exit 1
fi
say "installed successfully"
[ $CHECK = 1 ] && ssh_ 'bash -s' < "$ROOT/tools/vm-check-fixes.sh" | sed "s/^/[$XP_VM] /"
if [ $REMOVE = 1 ]; then
  before=$(system_state)
  say "removing"
  run_unit xp-remove uninstall
  ssh_ 'grep -q "^ERROR" ~/xp-remove.log' && { say "Remove FAILED (see ~/xp-remove.log in the guest)"; exit 1; }
  say "system side, installed -> removed:"
  diff <(echo "$before") <(system_state) | sed "s/^/[$XP_VM]   /" || true
fi
exit 0
