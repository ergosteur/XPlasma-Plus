"""Optional customizations on top of the selected features.

Each tweak is off by default and only applies when the features it adjusts are
selected. The chosen set is saved with the installation (asset_options['tweaks'])
so an upgrade or rebuild keeps it, and is published to the native runtime as
settings['installerTweaks'] in ~/.local/share/xplasma/state.json for tweaks the
native side implements.
"""
import json
import shutil

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
    {'id': 'smooth_text',
     'label': 'Smooth XP fonts at all sizes',
     'help': 'XP drew Tahoma, Trebuchet MS and Lucida Console without antialiasing at small sizes, and the XP '
             'fonts do the same here. Smooth them instead; their XP hinting and spacing stay.',
     'requires': ['fonts']},
    {'id': 'keep_firefox_icon',
     'label': "Keep Firefox's own icon",
     'help': "The XP icons give Firefox Internet Explorer's icon. Keep Firefox's own instead. "
             '(The IE6 Firefox browser keeps its IE icon either way.)',
     'requires': ['icons']},
    {'id': 'breeze_text_cursor',
     'label': 'Breeze text cursor (I-beam)',
     'help': "XP's thin black text cursor is hard to see on dark text areas such as terminals. "
             "Use Breeze's outlined one; the other XP pointers stay.",
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
]
FIREFOX_ICONS = ('firefox', 'org.mozilla.firefox')
CONFIG = 'xplasma-customizationsrc'   # ~/.config; read by the patched desktop QML
IDS = {t['id'] for t in TWEAKS}
BY_ID = {t['id']: t for t in TWEAKS}


def parse(text):
    """Comma-separated ids from the command line -> sorted list; unknown ids are an error."""
    chosen = sorted({x.strip() for x in (text or '').split(',') if x.strip()})
    unknown = [x for x in chosen if x not in IDS]
    if unknown:
        raise ValueError('Unknown customization: ' + ', '.join(unknown))
    return chosen


def active(chosen, selected):
    """The chosen tweaks whose required features are all selected."""
    return [t for t in sorted(chosen) if t in IDS and set(BY_ID[t]['requires']) <= set(selected)]


def publish(settings, chosen, selected):
    """Record every tweak's effective state for the native runtime."""
    on = set(active(chosen, selected))
    settings['installerTweaks'] = {t['id']: t['id'] in on for t in TWEAKS}


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
