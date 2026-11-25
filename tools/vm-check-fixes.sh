#!/usr/bin/env bash
# Report, inside the test VM, whether the fork's fixes and customizations are in place.
# Run over SSH after an install or a theme change:  ssh HOST 'bash -s' < tools/vm-check-fixes.sh
# Prints one line per check: OK / FAIL / n/a, then a summary. Read-only.
I=~/.local/share/icons; P=$I/xplasma-icons; E=$I/xplasma-xp-extended; O=$I/xplasma-fixes
ok=0 bad=0
check() { # name, command (true = OK)
  if ( eval "$2" ) >/dev/null 2>&1; then printf 'OK    %s\n' "$1"; ok=$((ok+1)); else printf 'FAIL  %s\n' "$1"; bad=$((bad+1)); fi
}
tweak() { python3 -c "import json,sys;print(json.load(open('$HOME/.local/share/xplasma/state.json'))['settings'].get('installerTweaks',{}).get(sys.argv[1],False))" "$1"; }
link_or_file() { [ -L "$1" ] || [ -e "$1" ]; }
feature() { python3 -c "import json,sys;sys.exit(sys.argv[1] not in json.load(open('$HOME/.local/share/kde-xp-suite/installation.json'))['features'])" "$1"; }
# Read settings as the desktop session does: distributions add config directories
# (Kubuntu's font defaults live in /usr/share/kubuntu-default-settings), and an SSH
# shell doesn't have them. A value equal to such a default isn't stored in ~/.config.
pid=$(pgrep -u "$USER" -x plasmashell | head -1)
[ -n "$pid" ] && export XDG_CONFIG_DIRS="$(tr '\0' '\n' < /proc/$pid/environ | sed -n 's/^XDG_CONFIG_DIRS=//p')"

echo "look: $(python3 -c "import json;s=json.load(open('$HOME/.local/share/xplasma/state.json'))['settings'];print(s.get('appliedPackageId'))")"
echo "theme: $(kreadconfig6 --file xplasmarc --group Theme --key Source)  variant: $(kreadconfig6 --file xplasmarc --group Theme --key Variant)"
echo "icon theme: $(kreadconfig6 --file kdeglobals --group Icons --key Theme)"

# icon corrections (overlay merged into the regenerated Primary)
check "icon overlay exists" "[ -f $O/index.theme ]"
same() { # overlay entry rel: Primary has the very same link or bytes
  if [ -L "$O/$1" ]; then [ -L "$P/$1" ] && [ "$(readlink "$O/$1")" = "$(readlink "$P/$1")" ]; else cmp -s "$O/$1" "$P/$1"; fi; }
n=0; m=0; bell=0
while read -r rel; do [ -n "$rel" ] || continue; n=$((n+1)); same "$rel" && m=$((m+1)); case $rel in */notifications.*) same "$rel" && bell=1;; esac
done < <(cd $O && find . -mindepth 3 \( -type f -o -type l \) | sed 's|^\./||')
check "overlay icons identical in Primary ($m/$n)" "[ $n -gt 0 ] && [ $m -eq $n ]"
r=0; while read -r rel; do [ -n "$rel" ] && link_or_file "$P/$rel" && r=$((r+1)); done < $O/REMOVED.txt
check "overlay removals still removed ($r left)" "[ $r -eq 0 ]"
check "bell is our drawn bell (notifications)" "[ $bell = 1 ]"
check "clipboard -> Paste clipboard" "[ -n \"\$(ls $P/*/status/klipper.* 2>/dev/null)\" ]"
check "Save As has its own icon" "ls $E/*/actions/document-save-as.png >/dev/null && ! cmp -s $E/32x32/actions/document-save-as.png $E/32x32/actions/document-save.png"
check "no XP media transport/zoom icons" "[ -z \"\$(ls $P/*/*/media-playlist-shuffle.* $E/*/*/media-playlist-shuffle.* $P/*/*/zoom-in.* $E/*/*/zoom-in.* 2>/dev/null)\" ]"
check "Primary declares every overlay directory" "for d in \$(grep -o '^\\[[^]]*\\]' $O/index.theme | tr -d '[]'); do grep -q \"^Directories=.*\$d\" $P/index.theme || exit 1; done"

# customizations
[ "$(tweak keep_firefox_icon)" = True ] && check "Firefox keeps its own icon" "[ -z \"\$(ls $P/*/applications/firefox.* $E/*/applications/firefox.* 2>/dev/null)\" ]"
[ "$(tweak show_desktop_button)" = True ] && check "Show Desktop: icon + first in Quick Launch" "ls $P/*/actions/xpshowdesktop.png && grep -q 'launcherUrls=file://.*xp-show-desktop.desktop' ~/.config/plasma-org.kde.plasma.desktop-appletsrc"
[ "$(tweak bell_always_shown)" = True ] && check "bell always shown in tray" "grep -q 'shownItems=.*org.kde.plasma.notifications' ~/.config/plasma-org.kde.plasma.desktop-appletsrc"
sm=$(python3 -c "import json;print(json.load(open('$HOME/.local/share/xplasma/state.json'))['settings'].get('fontSmoothing','(default) standard'))")
echo "font smoothing: $sm"
[ "$sm" = cleartype ] && check "ClearType: XP fonts never one-bit, RGB" "! grep -q 'name=\"antialias\"><bool>false' ~/.config/fontconfig/xplasma-xp-text.conf && grep -q '<const>rgb</const>' ~/.config/fontconfig/xplasma-xp-text.conf"
[ "$sm" = cleartype ] && check "ClearType is KDE's font setting too" "[ \"\$(kreadconfig6 --file kdeglobals --group General --key XftSubPixel)\" = rgb ] && [ \"\$(kreadconfig6 --file kdeglobals --group General --key XftAntialias)\" = true ]"
[ "$sm" = standard ] && check "Standard: small XP sizes one-bit, greyscale" "grep -q 'name=\"antialias\"><bool>false' ~/.config/fontconfig/xplasma-xp-text.conf && ! grep -q '<const>rgb</const>' ~/.config/fontconfig/xplasma-xp-text.conf"
[ "$sm" = none ] && check "None: no smoothing anywhere" "grep -q 'Screen font smoothing: none' ~/.config/fontconfig/xplasma-xp-text.conf && [ \"\$(kreadconfig6 --file kdeglobals --group General --key XftAntialias)\" = false ]"
[ "$(tweak breeze_text_cursor)" = True ] && check "Breeze I-beam + crosshair (XP ones left out)" "t=\$(kreadconfig6 --file kcminputrc --group Mouse --key cursorTheme); [ ! -e $I/\$t/cursors/text ] && [ ! -e $I/\$t/cursors/crosshair ] && grep -q 'Inherits=breeze_cursors' $I/\$t/index.theme"
[ "$(tweak plasma_notifications)" = True ] && check "Plasma notification popups (balloons=false)" "[ \"\$(kreadconfig6 --file xplasma-customizationsrc --group Notifications --key balloons)\" = false ]"
[ "$(tweak own_fixed_font)" = True ] && check "fixed font not forced to Lucida Console" "! kreadconfig6 --file kdeglobals --group General --key fixedFont | grep -q '^Lucida Console'"
[ "$(tweak dolphin_toolbar)" = True ] && check "Dolphin toolbar (ours, merged) + menu bar shown, not a first run" "python3 -c \"import sys,xml.etree.ElementTree as E;t=[a.get('name') for b in E.parse(sys.argv[1]).getroot().iter('ToolBar') if b.get('name')=='mainToolBar' for a in b.iter('Action')];sys.exit(t[:3]!=['go_back','go_forward','go_up'] or 'url_navigators' not in t)\" ~/.local/share/kxmlgui5/dolphin/dolphinui.rc && [ \"\$(kreadconfig6 --file dolphinrc --group MainWindow --key MenuBar)\" != Disabled ] && [ \"\$(kreadconfig6 --file dolphinrc --group General --key Version)\" -ge 200 ]"
feature lock && echo "n/a   Plasma lock screen background (XP lock screen installed instead)" || check "Plasma lock screen shows XP's Welcome screen" "[ \"\$(kreadconfig6 --file kscreenlockerrc --group Greeter --group Wallpaper --group org.kde.image --group General --key Image)\" = file://$HOME/.local/share/xplasma/assets/wallpapers/xp-welcome-lock.png ] && [ ! -e ~/.local/share/plasma/shells/org.kde.plasma.desktop ]"
check "taskbar theme's Complementary reads dark behind light text" "f=~/.local/share/plasma/desktoptheme/\$(kreadconfig6 --file plasmarc --group Theme --key name)/colors; python3 -c \"import sys,re;s=open(sys.argv[1]).read();b=s[s.index('[Colors:Complementary]'):];bg=[int(x) for x in re.search(r'BackgroundNormal=([0-9,]+)',b).group(1).split(',')];fg=[int(x) for x in re.search(r'ForegroundNormal=([0-9,]+)',b).group(1).split(',')];sys.exit(not (max(bg)<=127 or (max(fg)+min(fg))/2<128))\" \$f"
check "desktop icon cell 82px rule" "grep -q 'XPlasma: XP kept \"My Documents\" on one line' ~/.local/share/plasma/plasmoids/org.kde.desktopcontainment/contents/ui/FolderView.qml"
check "caption animation plugin loads (no version error this boot)" "! journalctl --user -b -q | grep -q 'xp-caption-animation.*built for a different version'"
echo "== $ok OK, $bad FAIL"
