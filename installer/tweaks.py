"""Optional customizations on top of the selected features.

Each tweak is off by default and only applies when the features it adjusts are
selected. The chosen set is saved with the installation (asset_options['tweaks'])
so an upgrade or rebuild keeps it, and is published to the native runtime as
settings['installerTweaks'] in ~/.local/share/xplasma/state.json for tweaks the
native side implements.
"""
import json
import os
import shutil
import subprocess
import time
from pathlib import Path

TWEAKS = [
    {'id': 'bell_always_shown',
     'label': 'Always show the notifications bell in the system tray',
     'help': 'Plasma hides the bell (notification history, Do Not Disturb) unless a notification is waiting. '
             'Keep it visible next to the clock.',
     'requires': ['taskbar']},
    {'id': 'show_desktop_button',
     'label': 'Show Desktop button in Quick Launch',
     'help': "XP's Quick Launch Show Desktop button, first in the row, with XP's own icon. "
             "It toggles Plasma's Show Desktop (minimise or restore all windows).",
     'requires': ['taskbar', 'icons']},
    {'id': 'cleartype',
     'label': 'Smooth screen fonts with ClearType',
     'help': "XP's ClearType font smoothing (Display Properties > Appearance), for every application: "
             'RGB subpixel smoothing at every size, including the small XP interface fonts XP otherwise drew '
             'unsmoothed. Can be changed later in XPlasma Plus Properties.',
     'requires': ['fonts']},
    {'id': 'keep_firefox_icon',
     'label': "Keep Firefox's own icon",
     'help': "The XP icons give Firefox Internet Explorer's icon. Keep Firefox's own instead. "
             '(The IE6 Firefox browser keeps its IE icon either way.)',
     'requires': ['icons']},
    {'id': 'breeze_text_cursor',
     'label': 'Breeze text, crosshair and other thin black pointers',
     'help': "XP drew its I-beam and crosshair by inverting the screen, which Linux can't: they come out "
             "as thin black lines, hard to see on dark areas such as terminals or a screenshot's region "
             "selection. Use Breeze's outlined ones for every such pointer; the other XP pointers stay.",
     'requires': ['pointers']},
    {'id': 'plasma_notifications',
     'label': "Plasma's notification popups instead of XP balloons",
     'help': "Show notifications as Plasma's own popups (with their history, actions and grouping) instead of "
             "XP's yellow balloons. The XP tray, copy dialog and buttons are unchanged.",
     'requires': ['taskbar']},
    {'id': 'own_fixed_font',
     'label': 'Keep your own fixed-width font',
     'help': 'The XP fonts make Lucida Console 10 the fixed-width font (terminals, editors) and set it again on '
             'every theme change. Keep the one chosen in System Settings instead.',
     'requires': ['fonts']},
    {'id': 'dolphin_toolbar',
     'label': 'Dolphin: Explorer-like toolbar and menu bar',
     'help': "Dolphin's main toolbar as Back, Forward, Up | Search, View, Location bar, Split, Terminal, "
             'New Folder, Stash, Menu, and its menu bar shown (File, Edit, View...) as in XP\'s Explorer.',
     'requires': []},
]
FIREFOX_ICONS = ('firefox', 'org.mozilla.firefox', 'web-browser', 'internet-web-browser')
CONFIG = 'xplasma-customizationsrc'   # ~/.config; read by the patched desktop QML
IDS = {t['id'] for t in TWEAKS}
BY_ID = {t['id']: t for t in TWEAKS}


ALIASES = {'smooth_text': 'cleartype'}   # earlier names, still accepted (a saved installation's)


def parse(text):
    """Comma-separated ids from the command line -> sorted list; unknown ids are an error."""
    chosen = sorted({ALIASES.get(x.strip(), x.strip()) for x in (text or '').split(',') if x.strip()})
    unknown = [x for x in chosen if x not in IDS]
    if unknown:
        raise ValueError('Unknown customization: ' + ', '.join(unknown))
    return chosen


def active(chosen, selected):
    """The chosen tweaks (old ids resolved via ALIASES) whose required features are all selected."""
    resolved = {ALIASES.get(t, t) for t in chosen}
    return [t for t in sorted(resolved) if t in IDS and set(BY_ID[t]['requires']) <= set(selected)]


def publish(settings, chosen, selected):
    """Record every tweak's effective state for the native runtime."""
    on = set(active(chosen, selected))
    settings['installerTweaks'] = {t['id']: t['id'] in on for t in TWEAKS}
    # ClearType is Display Properties' font smoothing: chosen here, it is the desktop's
    # setting from now on (Properties can change it later; unticked here, it's left alone).
    if 'cleartype' in on:
        settings['fontSmoothing'] = 'cleartype'


def prepare(chosen, selected, run):
    """Settings the desktop reads when Plasma's shell starts: written before the
    native apply restarts it. Written both ways, so unticking a tweak undoes it."""
    if 'taskbar' not in selected:
        return
    writer = shutil.which('kwriteconfig6') or shutil.which('kwriteconfig5')
    if not writer:
        return
    balloons = 'false' if 'plasma_notifications' in active(chosen, selected) else 'true'
    # Its own file: the native apply rewrites xplasmarc from scratch. The key is
    # the QML Settings property's own name (xp-globals.qml).
    run([writer, '--file', CONFIG, '--group', 'Notifications', '--key', 'balloons', '--type', 'bool', balloons])


BELL_SCRIPT = '''panels().forEach(function(p){p.widgets().forEach(function(w){
 if(w.type!=="org.kde.plasma.systemtray")return;
 w.currentConfigGroup=["General"];
 var shown=String(w.readConfig("shownItems","")).split(",").filter(function(x){return x;});
 var hidden=String(w.readConfig("hiddenItems","")).split(",").filter(function(x){return x&&x!=="org.kde.plasma.notifications";});
 if(shown.indexOf("org.kde.plasma.notifications")<0)shown.push("org.kde.plasma.notifications");
 w.writeConfig("shownItems",shown);w.writeConfig("hiddenItems",hidden);w.reloadConfig();
});});'''


SHOW_DESKTOP_FILE = 'xp-show-desktop.desktop'
SHOW_DESKTOP_SCRIPT = '''var url=URL;panels().forEach(function(p){p.widgets("org.kde.plasma.quicklaunch").forEach(function(w){
 w.currentConfigGroup=["General"];
 var urls=String(w.readConfig("launcherUrls","")).split(",").filter(function(u){return u;});
 if(urls.indexOf(url)<0){urls.unshift(url);w.writeConfig("launcherUrls",urls);w.reloadConfig();}
});});'''


def show_desktop_entry(qdbus):
    return ('[Desktop Entry]\nType=Application\nName=Show Desktop\nComment=Minimise or restore all windows\n'
            'Icon=xpshowdesktop\n'
            'Exec=' + qdbus + ' org.kde.kglobalaccel /component/kwin org.kde.kglobalaccel.Component.invokeShortcut "Show Desktop"\n'
            'Categories=Utility;\nNoDisplay=true\nX-XPlasma-Customization=show_desktop_button\n')


def dolphin_settings_version(home):
    """[General] Version in the user's dolphinrc, 0 when Dolphin has never saved one."""
    group = None
    try:
        lines = (Path(home) / '.config/dolphinrc').read_text(errors='replace').splitlines()
    except OSError:
        return 0
    for line in lines:
        line = line.strip()
        if line.startswith('['):
            group = line
        elif group == '[General]' and line.startswith('Version='):
            try:
                return int(line.split('=', 1)[1])
            except ValueError:
                return 0
    return 0


def dolphin_first_run(qdbus, log, timeout=20):
    """Start Dolphin offscreen and close it, so its one-time first run is done.
    True when it closed by itself (its settings saved). Skipped while a Dolphin runs."""
    dolphin = shutil.which('dolphin')
    if not dolphin or not shutil.which(qdbus) or subprocess.run(['pgrep', '-x', 'dolphin'], capture_output=True).returncode == 0:
        return False
    env = {**os.environ, 'QT_QPA_PLATFORM': 'offscreen'}
    proc = subprocess.Popen([dolphin, '--new-window'], env=env, stdin=subprocess.DEVNULL,
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
    service, window = f'org.kde.dolphin-{proc.pid}', '/dolphin/Dolphin_1'
    closed = False
    try:
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline and proc.poll() is None:
            if subprocess.run([qdbus, service, window, 'org.qtproject.Qt.QWidget.close'],
                              capture_output=True, timeout=5).returncode == 0:
                proc.wait(timeout=10)
                closed = True
                break
            time.sleep(0.5)
    except (subprocess.TimeoutExpired, OSError):
        pass
    finally:
        if proc.poll() is None:
            proc.kill()
            proc.wait()
    if not closed:
        log('Dolphin could not be started once in the background; its first start will hide the menu bar (View it again with Ctrl+M).')
    return closed


DOLPHIN_TOOLBAR = ['go_back', 'go_forward', 'go_up', None, 'toggle_search', 'view_settings', 'url_navigators',
                   'split_view', 'show_terminal_panel', 'create_dir', 'split_stash', 'hamburger_menu']


def dolphin_ui():
    # A deliberately old version: KXmlGui then merges this toolbar into whatever
    # dolphinui.rc the installed Dolphin ships, instead of replacing its menus.
    items = ''.join('  <Separator/>\n' if a is None else f'  <Action name="{a}"/>\n' for a in DOLPHIN_TOOLBAR)
    return ('<!DOCTYPE gui SYSTEM "kpartgui.dtd">\n<gui name="dolphin" version="1" translationDomain="kxmlgui6">\n'
            ' <ToolBar name="mainToolBar" noMerge="1" alreadyVisited="1">\n'
            '  <text context="@title:menu" translationDomain="dolphin">Main Toolbar</text>\n' + items +
            ' </ToolBar>\n</gui>\n')


def apply(chosen, selected, run, shell_script, log, home=None, qdbus='qdbus6'):
    """Apply the installer-side tweaks. run/shell_script/log come from backend.py."""
    on = set(active(chosen, selected))
    if 'bell_always_shown' in on:
        shell_script(BELL_SCRIPT)
        log('Customization: notifications bell always shown in the tray.')
    if 'show_desktop_button' in on and home is not None:
        entry = home / '.local/share/applications' / SHOW_DESKTOP_FILE
        entry.parent.mkdir(parents=True, exist_ok=True)
        entry.write_text(show_desktop_entry(qdbus))
        shell_script(SHOW_DESKTOP_SCRIPT.replace('URL', json.dumps(entry.as_uri())))
        log('Customization: Show Desktop added to Quick Launch.')
    if 'keep_firefox_icon' in on and home is not None:
        # (The generated XP icon theme leaves these names out itself; the expanded
        # layer is a prebuilt copy, so its entries are removed here.)
        layer = home / '.local/share/icons/xplasma-xp-extended'
        removed = [p for p in sorted(layer.glob('*/applications/*'))
                   if p.name.rsplit('.', 1)[0] in FIREFOX_ICONS and (p.is_file() or p.is_symlink())]
        for p in removed:
            p.unlink()
        if removed and shutil.which('gtk-update-icon-cache'):
            run(['gtk-update-icon-cache', '-f', '-q', str(layer)], check=False)
        log('Customization: Firefox keeps its own icon.')
    if 'dolphin_toolbar' in on and home is not None:
        ui = home / '.local/share/kxmlgui5/dolphin/dolphinui.rc'
        ui.parent.mkdir(parents=True, exist_ok=True)
        ui.write_text(dolphin_ui())
        # A Dolphin that has never run (no [General] Version below 200) hides its menu
        # bar on its first start and saves that over ours. Its first run is done here
        # instead, unseen, so its other first-run choices (side panels closed) stay.
        if dolphin_settings_version(home) < 200:
            dolphin_first_run(qdbus, log)
        writer = shutil.which('kwriteconfig6') or shutil.which('kwriteconfig5')
        if writer:
            run([writer, '--file', 'dolphinrc', '--group', 'MainWindow', '--key', 'MenuBar', 'Enabled'])
        log('Customization: Dolphin toolbar and menu bar set (takes effect when Dolphin next starts).')
