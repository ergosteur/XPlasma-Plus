#!/usr/bin/env python3
"""Fix up the XPlasma icon themes: new icons, hidden XP art, Breeze fall-through.

Run by the installer (tools/icon-fixes/overlay.py captures what it changes); safe to re-run (idempotent).
  python3 -I build.py [--dry-run] [-v]

What it does, all inside ~/.local/share/icons/xplasma-icons (XPlasma Primary KDE reads first):
  1. GENERATE icons: folder variants (badge on the pack's folder), script-language file types,
     packages / AppImage / .msi.  Built from the pack's own CC0 recreations (xplasma-xp-extended) at
     each size, plus five recreations drawn for this repo (svg/), rendered per size (no scaling up).
  2. EXPOSE XP art the theme hides (see docs "Icon lookup quirks"): a short name in XPlasma Primary
     (folder, text-x-generic...) makes KDE skip the exact-named XP icon in the layer below.
  3. PIN Breeze icons by exact name where we want Breeze (user decisions) or where an XP short
     name would swallow an unrelated Breeze icon (Kdenlive toolbar, image/audio/video glyphs...).
Everything is a PNG we write or a symlink; nothing outside XPlasma Primary is modified.
"""
import collections, os, re, shutil, subprocess, sys
from pathlib import Path
from PIL import Image, ImageChops
import io
sys.path.insert(0, str(Path(__file__).resolve().parent))
import xp_marks  # noqa: E402  (the red X for "off" states)

HERE = Path(__file__).resolve().parent
ICONS = Path.home() / ".local/share/icons"
PRIM, EXT = ICONS / "xplasma-icons", ICONS / "xplasma-xp-extended"
FALLBACK = Path("/usr/share/icons/breeze")   # what XPlasma Primary inherits after the XP layers (was Papirus until 2026-11-02)
SIZES = [16, 22, 24, 32, 48, 64, 128]
DRY = "--dry-run" in sys.argv
VERBOSE = "-v" in sys.argv

# --------------------------------------------------------------------------------------------
# Decisions (see docs/fedora-as-built.md "XPlasma Plus post-install", step 7)
# --------------------------------------------------------------------------------------------
# folder name -> (kind, source, fraction of the folder size, corner)
#   art: alias of an XP recreation in xplasma-xp-extended;  svg: drawn in svg/;  only: use as the icon itself
FOLDERS = {
    "folder-templates": ("art", "document-new", .55, "SE"),
    "folder-games": ("art", "applications-games", .55, "SE"),
    "folder-important": ("art", "emblem-important", .55, "SE"),
    "folder-development": ("art", "applications-development", .55, "SE"),   # Command Prompt
    "folder-git": ("art", "applications-development", .55, "SE"),
    "folder-script": ("script", "cyan", .58, "SE"),
    "folder-code": ("script", "yellow", .58, "SE"),
    "folder-locked": ("art", "auth-sim-locked", .55, "SE"),                # Padlock
    "folder-unlocked": ("art", "dialog-password", .55, "SE"),              # Key
    "folder-saved-search": ("art", "edit-find", .65, "SW"),                # Search
    "folder-print": ("art", "document-print", .70, "SE"),                  # Printer
    "folder-chat": ("art", "internet-chat", .60, "SE"),                    # Windows Messenger
    "folder-download": ("art", "internet-web-browser", .58, "SE"),    # Internet Explorer
    "folder-downloads": ("art", "internet-web-browser", .58, "SE"),
    "folder-recent": ("recent", None, .60, "SE"),
    "folder-open-recent": ("recent", None, .60, "SE"),
    "folder-favorites": ("only", "bookmarks", 1, None),                    # XP's plain Favorites star
    "folder-bookmark": ("only", "bookmarks", 1, None),
    "folder-bookmarks": ("only", "bookmarks", 1, None),
    "folder-appimage": ("only", "applications-all", 1, None),              # Start Menu Programs folder
}
for n in ("folder-cloud", "folder-owncloud", "folder-onedrive", "folder-gdrive"):
    FOLDERS[n] = ("svg", "globe-arrow", .60, "SE")

# Existing pack mappings that are wrong, replaced on purpose (the only names allowed to overwrite a
# pack-owned file): name -> (XP recreation alias, context)
OVERRIDES = {
    # XPlasma Primary's own white page stack beat the XP "Copy" recreation; edit-paste was mapped to Copy
    "edit-copy": ("edit-copy", "actions"), "edit-copy-symbolic": ("edit-copy", "actions"),
    "edit-paste": ("edit-paste-in-place", "actions"), "edit-paste-symbolic": ("edit-paste-in-place", "actions"),
    # mounted network shares in Dolphin's sidebar (Solid's fstab entries use network-server): the XP
    # Network Folder art the pack also uses for folder-network / folder-remote, not "Remote Desktop Server"
    "network-server": ("folder-network", "places"), "network-server-symbolic": ("folder-network", "places"),
    # Solid overlays Dolphin's Places panel with these: the pack maps both to the Local Disk picture, so every
    # device got a tiny drive drawn on it. Owner's choice: nothing when mounted, Papirus's orange X when not.
    # XPlasma Primary's own drive-harddisk at <=32px is the flat Removable Disk slab, only 48px+ is the real XP Local
    # Disk; XPlasma Extended has the right art at every size. (drive-harddisk-root is Solid's name for the root filesystem)
    # the tray clipboard (Klipper / the Plasma clipboard applet) used the pack's Copy picture or its own white page;
    # the clipboard should be the Paste clipboard, same as edit-paste everywhere
    "klipper": ("edit-paste-in-place", "status"), "klipper-symbolic": ("edit-paste-in-place", "status"),
    "clipboard": ("edit-paste-in-place", "status"), "clipboard-symbolic": ("edit-paste-in-place", "status"),
    "clipboard-empty": ("edit-paste-in-place", "status"), "clipboard-empty-symbolic": ("edit-paste-in-place", "status"),
    "org.kde.plasma.clipboard": ("edit-paste-in-place", "applications"),
    # `configure` (Plasma's "Configure..." button, e.g. the Networks panel) was the Control Panel clipboard, a picture the pack
    # hung on ~300 names; the pack's own XP-styled sliders glyph (xp-c753b0b36d79.png, alias adjustlevels-symbolic) is the
    # proper one (Breeze's configure is also sliders)
    "configure": ("adjustlevels-symbolic", "actions"), "configure-symbolic": ("adjustlevels-symbolic", "actions"),
    # Dolphin's Split button (view-split-left-right) and, once split, Close (view-left-close / view-right-close) were the
    # green Back/Forward arrows; the pack's own XP-styled pane-with-arrow glyph (xp-d0c63656973c.png, alias
    # view-split-effect) is closest to Breeze's, mirrored for the right-hand pane (owner's pick)
    "view-split-left-right": ("view-split-effect", "actions"), "view-split-left-right-symbolic": ("view-split-effect", "actions"),
    "view-left-close": ("view-split-effect", "actions"), "view-left-close-symbolic": ("view-split-effect", "actions"),
    "view-right-close": ("MIRROR:view-split-effect", "actions"), "view-right-close-symbolic": ("MIRROR:view-split-effect", "actions"),
    # the Home place (Dolphin sidebar, file dialogs): the pack's My Documents folder; owner wants the Internet Explorer house
    "user-home": ("go-home", "places"),
    # Dolphin's Configure > View > Details tab uses view-list-tree, which the pack maps to its Folder View picture (two folders)
    "view-list-tree": ("view-list-details", "actions"),     # the pack's own Detail View art (Extended alias view-list-details)
    # Dolphin's Details view button: the owner's own drawing based on XP's Tiles view (art/view-list-tiles.png, 128 px with
    # alpha; smaller sizes are Lanczos downscales, nothing is scaled up)
    "view-list-details": ("FILE:view-list-tiles.png", "actions"),
    "drive-harddisk": ("drive-harddisk", "devices"), "drive-harddisk-root": ("drive-harddisk", "devices"),
    "emblem-mounted": ("BLANK", "emblems"),    # emblem-unmounted: Papirus's orange X (FALLTHROUGH_EXACT), owner's pick
    # Network settings (kcm_networkmanagement): the pack's own picture here, repointed to XP's actual
    # "Network and Internet" (two monitors + globe) -- not "Network Connections" (globe + plug), which is
    # a different XP picture reused below for Dolphin's remote:/ "Network Services".
    "preferences-system-network": ("FILE:network-and-internet.png", "categories"),
    "preferences-system-network-symbolic": ("FILE:network-and-internet.png", "categories"),
    # remote:/ "Network Services" (zeroconf): a custom name so it doesn't collide with preferences-system-network
    # above; see smb-network.desktop / zeroconf.desktop's user-level Icon= overrides in ~/.local/share/remoteview.
    "xp-network-services": ("FILE:network-connections.png", "places"),
    # krdc (and anything else using the generic remote-desktop-client concept): was the pack's Network Folder
    # picture (a shared folder), not a remote desktop client at all. XP's "Remote Desktop" (satellite dish + monitor).
    "krdc": ("FILE:remote-desktop.png", "applications"),
    # Filelight (disk usage): was a plain drive, not XP's own "Disk Cleanup" (broom sweeping a drive) picture.
    "filelight": ("FILE:disk-cleanup.png", "applications"),
    # App Permissions kcm (kcm_app-permissions): shared preferences-security with an unrelated padlock concept;
    # XP's "Security Question" (shield with a question mark) fits a permissions prompt much better. Checked: no
    # other installed .desktop uses this icon name, so nothing else is affected.
    "preferences-security": ("FILE:security-question.png", "categories"),
    "preferences-security-symbolic": ("FILE:security-question.png", "categories"),
    # KDE Partition Manager: on xp-deleted.txt, fell through to Breeze. XP's "Disk Management".
    "partitionmanager": ("FILE:disk-management.png", "applications"),
    # Printer settings category (kcm_printer_manager): was the same plain-printer picture individual printer
    # devices use (separate file, not a symlink, so changing this doesn't touch those) -- XP's own "Printers and
    # Faxes" (folder + printer) distinguishes the settings category from an actual printer. Individual printer
    # device icons (icon name `printer`) are untouched, per the owner.
    "preferences-devices-printer": ("FILE:printers-and-faxes.png", "categories"),
    # MTP devices (remote:/ "MTP Devices", mtp-network.desktop) and the generic multimedia-player device icon: on
    # xp-deleted.txt, fell through to Breeze. First tried XP's "Portable Media Devices" (a folder + MP3 player);
    # owner's call once both were live: XP's plain "MP3 Player" fits the actual device concept better.
    "multimedia-player": ("FILE:mp3-player.png", "devices"),
    "multimedia-player-symbolic": ("FILE:mp3-player.png", "devices"),
    # Remote Desktop settings (kcm_krdpserver): was the pack's own picture; XP's "Remote Assistance" (hand + mouse).
    "preferences-system-network-remote": ("FILE:remote-assistance.png", "categories"),
    "preferences-system-network-remote-symbolic": ("FILE:remote-assistance.png", "categories"),
    # KDE Wallet -- both the app (kwalletmanager/kwalletd/ksecretd) and its kcm use this one icon name already,
    # so one fix covers both. XP's "Authorization Manager" (person + key) fits a password manager far better
    # than the pack's own picture.
    "kwalletmanager": ("FILE:authorization-manager.png", "applications"),
    "kwalletmanager-symbolic": ("FILE:authorization-manager.png", "applications"),
    # System Settings > Session (kcm_smserver): its own Icon= is literally `system-log-out`, which is also what
    # our XP logout dialog's actual Log Out button uses (Logout.qml) -- repointing that name would break the
    # button, so give the Session kcm its own custom name instead; see kcm_smserver.desktop's user-level
    # Icon= override in ~/.local/share/applications. XP's "Change Language".
    "xp-session-settings": ("FILE:change-language.png", "categories"),
    # Dolphin's Places panel "Recent Files" entry was on xp-deleted.txt, fell through to Breeze. This used to be
    # a programmatic document-new + clock-badge composite (recent_badge(), still used by FOLDERS' "recent" kind
    # for folder-flavoured names like folder-open-recent/"Recent Locations"), now replaced with XP's real
    # "Recent Documents" picture.
    "document-open-recent": ("FILE:recent-documents.png", "actions"),
    # Media/device type icons: the pack's role-matching put several of these on pictures that don't fit at all
    # (confirmed via ALIAS-PROVENANCE.json) -- media-flash-memory-stick was literally "Removable Media.png" (a
    # plain drive), and media-optical-recordable/-symbolic were "Record.png", the same red record-button picture
    # also (correctly) used for audio-input-microphone and the mic-sensitivity status icons -- a external-drive
    # and a microphone are not an SD card or a writable CD. Real XP pictures for each, mostly distinct to tell
    # similar disc types apart (plain DVD for blank/generic, DVD-ROM for the pressed-disc "video" concept):
    "media-flash-memory-stick": ("FILE:memory-stick.png", "devices"),
    "media-flash-sd-mmc": ("FILE:sd-card.png", "devices"),
    "media-optical-audio": ("FILE:audio-cd.png", "devices"),
    "media-optical-dvd": ("FILE:dvd.png", "devices"), "media-optical-dvd-symbolic": ("FILE:dvd.png", "devices"),
    "media-optical-mixed-cd": ("FILE:cd-rom.png", "devices"),
    "media-optical-recordable": ("FILE:cd-r.png", "devices"), "media-optical-recordable-symbolic": ("FILE:cd-r.png", "devices"),
    "media-optical-video": ("FILE:dvd-rom.png", "devices"),
    # computer-laptop was an exact-name mismatch onto "Undock PC.png" (a dock-eject glyph, nothing like a
    # laptop); XP's "IR File Transfer" (a laptop with its own art) is the closest real laptop picture available.
    "computer-laptop": ("FILE:ir-file-transfer.png", "devices"),
    # media-optical-bd / media-optical-blu-ray: left alone -- no Blu-ray picture exists in this CC0 pack (XP
    # predates mainstream Blu-ray), so there's nothing better to put here yet.
    # view-refresh is correctly mapped to the real XP "IE Refresh" picture (role "view-refresh", exact) -- left as
    # the page + green arrows, since this name's real uses are all static refresh buttons (Skanpage's own
    # "view-refresh" uses, confirmed via `strings` on its binary, turned out to be its static "Reselect
    # Scanner"/"Reload devices list" actions, not its spinner). The actual "Scan in progress" busy indicator is a
    # generic Qt Quick Controls BusyIndicator (org.kde.desktop style's BusyIndicator.qml -- shared by every
    # Kirigami/QQC2 app, not Skanpage-specific), which rotates a Kirigami.Icon with
    # `source: "process-working-symbolic"`. ALIAS-PROVENANCE.json confirms process-working/-symbolic are also
    # mapped to "IE Refresh.png" (role view-refresh, reused) -- same page shape, same problem, but this is the one
    # actually spinning. No other XP picture in the pack is rotation-friendly either (checked "Synchronize.png",
    # "Sync.png" -- both have a page or other asymmetric shape too). First try: XP's own hourglass cursor (frame 0
    # of ~/.local/share/xplasma/extracted/hourglas.ani, extracted by hand). Looked right static, but the static
    # sand drawing doesn't move with the rotation, so a spinning hourglass just looks odd rather than conveying
    # "busy". Owner's call: not XP, but the same era and a far better fit for something that's *supposed* to spin
    # forever. compy-686 used macOS's beachball, which can't be redistributed; this fork pins Breeze's own
    # process-working spinner instead (FALLTHROUGH_EXACT below), radially symmetric and already on every KDE system.
    # image-x-generic is pack-owned (unlike the rest of IMAGE_NAMES below, which aren't and get XP's real JPG/GIF
    # pictures straight from write_png in the main loop) -- same JPG picture here too, via the one mechanism
    # that's allowed to replace a pack-owned file. A duplicate of assets/jpg.png (used by raster_asset() for the
    # main loop) since this mechanism only reads from art/.
    "image-x-generic": ("FILE:jpg.png", "mimetypes"),
    # Power & Battery tray applet (powerdevil's org.kde.plasma.battery): with no internal battery (this is a desktop)
    # its icon is `battery-full`, which the pack maps to a blue Win9x-style "on battery" cell -- wrong era and wrong
    # state for a mains-powered PC. XP's own Power Options picture (battery + plug, the pack's alias
    # preferences-system-power-management, already what the applet's popup header shows) instead. Real battery
    # levels use the battery-0xx / battery-level-* names and peripherals their own (upower's mouse:
    # battery-full-charged-symbolic), so neither is affected.
    "battery-full": ("preferences-system-power-management", "status"),
    "battery-full-symbolic": ("preferences-system-power-management", "status"),
}

# XP art for these folders already exists and is simply hidden: expose (other folder-* variants are
# plain yellow folders, nothing to gain)
FOLDER_EXPOSE = {"folder-publicshare", "folder-image", "folder-images", "folder-picture",
                 "folder-image-people", "folder-video"}

# script file types: the pack's own "Java Script" page (yellow scroll on a blue page) with the scroll's hue
# rotated: language -> (target hue in degrees, brightness factor); yellow is the unmodified art
HUES = {"yellow": None, "cyan": (185, 1.0), "blue": (215, 1.0), "red": (355, 1.0), "purple": (275, 1.0),
        "navy": (235, .72), "ps": (222, .55)}
SCRIPTS = {
    "cyan": "application-x-shellscript text-x-shellscript text-x-sh text-x-script application-script "
            "application-x-executable-script application-x-csh application-x-bat text-x-msdos-batch "
            "application-x-awk text-vbscript text-vbscript.encode application-x-gdscript text-x-gdscript",
    "yellow": "text-javascript application-javascript application-x-javascript text-x-javascript",
    "blue": "application-x-perl text-x-perl",
    "red": "application-x-ruby text-x-ruby",
    "purple": "application-x-php text-x-php",
    "navy": "text-x-lua application-x-lua",
    "ps": "application-x-powershell text-x-powershell",
}
# instant-messaging presence icons: the pack's Windows Messenger figures recoloured per state (the pack maps all of
# user-* to the generic User Accounts picture and pidgin-tray-* to unrelated SVGs). state -> (hue, sat, val, alpha); the
# shading is kept, both figures take the state's hue. Owner approved the palette 2026-11-02.
STATUS_TINT = {"online": (122, 1.0, 1.0, 1.0), "away": (38, 1.0, 1.0, 1.0), "xa": (30, .85, .9, 1.0),
               "busy": (2, 1.0, .95, 1.0), "invisible": (210, .15, 1.0, .55), "offline": (0, 0.0, .85, 1.0),
               "neutral": None}                      # None = the original two-tone art
STATUS_NAMES = {"online": "user-available user-online pidgin-tray-available im-user-online",
                "away": "user-away user-idle pidgin-tray-away im-user-away",
                "xa": "user-away-extended pidgin-tray-xa im-user-away-extended",
                "busy": "user-busy pidgin-tray-busy im-user-busy",
                "invisible": "user-invisible pidgin-tray-invisible im-invisible-user",
                "offline": "user-offline pidgin-tray-offline im-user-offline",
                "neutral": "pidgin-tray-pending im-user"}     # not a presence state: the original two-tone art
# packages (.rpm .deb .flatpak .msi) share the Windows Installer icon; AppImage has its own
PACKAGES = ("application-x-rpm application-x-redhat-package-manager application-vnd.debian.binary-package "
            "application-x-deb application-x-debian-package application-vnd.flatpak application-vnd.xdgapp "
            "application-vnd.flatpak.ref application-vnd.flatpak.repo application-x-msi").split()
APPIMAGE = "application-vnd.appimage application-x-iso9660-appimage".split()

# fall through to Papirus (exact-name pins). Where Papirus lacks the exact name, its own fallback is used.
FALLTHROUGH_EXACT = set((
    # the busy spinner (see process-working above): Breeze's, which is made to rotate
    "process-working process-working-symbolic "
    "text-css text-html text-csv text-x-csrc text-x-changelog text-x-makefile text-markdown text-x-markdown "
    # Python (user: Papirus has the official-looking one; we can't confirm the logo is free to bundle)
    "text-x-python text-x-python2 text-x-python3 application-x-python-bytecode "
    # compiled-language source
    "text-x-c++src text-x-chdr text-x-c++hdr text-x-java text-x-go text-rust text-x-rust text-x-haskell "
    "text-x-fortran text-fortran text-csharp text-x-csharp text-x-adasrc text-x-objcsrc text-x-objchdr "
    "text-x-pascal text-x-vala text-x-scala text-x-kotlin text-x-swift "
    # disk images (CD/ISO images moved out below, now drawn from XP's own "CD-R" picture; these are virtual hard
    # disk / raw image formats, which that picture doesn't fit, so they still fall through)
    "application-vnd.efi.img "
    "application-x-raw-disk-image application-x-qemu-disk application-x-vdi-disk application-x-vmdk-disk "
    "application-x-virtualbox-vdi application-x-virtualbox-vmdk application-x-discjuggler-cd-image "
    "x-office-document x-office-spreadsheet x-office-presentation x-office-drawing x-office-address-book "
    "x-office-calendar "
    # the pack maps the hamburger menu to its Programs ("Add/Remove Programs") picture
    "open-menu open-menu-symbolic application-menu application-menu-symbolic overflow-menu overflow-menu-symbolic "
    "hamburger-menu hamburger-menu-symbolic "
    # Dolphin's Places panel overlay for unmounted devices (mounted: transparent, see OVERRIDES)
    "emblem-unmounted").split())
FALLTHROUGH_RE = [r"^application-pdf$", r"^application-x-pdf$", r"^application-msword", r"^application-vnd\.ms-",
                  r"^application-vnd\.openxmlformats-officedocument\.", r"^application-vnd\.oasis\.opendocument\.",
                  r"^application-vnd\.sun\.xml\.", r"^application-vnd\.visio", r"^application-x-krita"]
FALLTHROUGH_FAMILIES = ("audio", "video")              # file types only (mime names), not toolbar glyphs
FALLTHROUGH_RE += [r"^image-.*(psd|photoshop|xcf|krita|openraster)", r"^libreoffice-", r"^message(-|$)", r"^odf$",
                   r"^podcast$", r"^virtualbox-", r"^x-office-", r"^x-mail-", r"^x-media-", r"^vnd\.ms-",
                   r"^x-kde-", r"^application-(spreadsheet|presentation)$"]

# Papirus names an XP short name would swallow, where the XP icon is unrelated (Class C absorbers)
PIN_ABSORBERS = {"kdenlive", "tokodon", "fcitx", "fcitx-rime", "ibus", "image-x-generic", "audio-x-generic",
                 "video-x-generic", "object", "bluetooth", "phone-symbolic"}

# --------------------------------------------------------------------------------------------
# KDE's fallback model (validated against scripts/icon-lookup-audit.py: reproduces all 678 hidden icons)
# --------------------------------------------------------------------------------------------
SUF = re.compile(r"^(.*?)((?:-symbolic)?(?:-rtl|-ltr)?)$")
GENERIC_FIRST = {"text", "image", "audio", "video"}


def chain(n):
    yield n
    base, suf = SUF.match(n).groups()
    parts = base.split("-")
    if suf:
        for k in range(len(parts) - 1, 0, -1):
            yield "-".join(parts[:k]) + suf
    allp = n.split("-")
    for k in range(len(allp) - 1, 0, -1):
        yield "-".join(allp[:k])
    if parts[0] in GENERIC_FIRST:
        yield parts[0] + "-x-generic"


def first_match(names, n):
    return next((c for c in chain(n) if c in names), None)


def scan(root, exts=(".png", ".svg")):
    """{name: {(size, ctx): path}} for a theme laid out as <size>x<size>/<ctx>/<name>.<ext>"""
    out = collections.defaultdict(dict)
    for p in root.glob("*x*/*/*"):
        if p.suffix in exts and re.fullmatch(r"\d+x\d+", p.parent.parent.name):
            out[p.stem][(int(p.parent.parent.name.split("x")[0]), p.parent.name)] = p
    return out


def scan_papirus():
    """Breeze (the name is historical): {name: {(size, ctx): path}} for <ctx>/<size>/<name>.svg; @2x/@3x skipped"""
    out = collections.defaultdict(dict)
    for p in FALLBACK.glob("*/*/*.svg"):
        ctx, size = p.parent.parent.name, p.parent.name
        if size.isdigit():
            out[p.stem][(int(size), ctx)] = p
    return out


PRIM_CTX_FROM_PAPIRUS = {"apps": "applications", "applets": "status", "animations": "status", "preferences": "categories"}

# --------------------------------------------------------------------------------------------
# Index of what XPlasma Primary declares (KDE only scans declared <size>/<context> dirs)
# --------------------------------------------------------------------------------------------
declared = set(re.search(r"^Directories=(.*)$", (PRIM / "index.theme").read_text(), re.M).group(1).split(","))


def dest_dir(size, ctx):
    d = f"{size}x{size}/{ctx}"
    return PRIM / d if d in declared else None


stats = collections.Counter()
OWNED_SKIPPED = set()
# pack-owned names we may replace with a Papirus pin (none at the moment)
# pack-owned names we replace on purpose: the bell is drawn for this repo (svg/bell.svg, plus xp_marks.py's red X when off; see BELL below)
ALLOW_OWNED = {"notifications", "notification-active", "notification-inactive", "notification-disabled",
               "notifications-disabled", "process-working", "process-working-symbolic"}
# names the pack itself put in XPlasma Primary at install time: never overwrite those
import json
# (the native generator's own record of them, xplasma-icons/xplasma-icons.json; older packs kept a copy in
# maintenance/icon-coverage/xplasma-icons.json.before)
_meta = next((p for p in (PRIM / "xplasma-icons.json",
                          Path.home() / ".local/share/xplasma/maintenance/icon-coverage/xplasma-icons.json.before")
              if p.is_file()), None)
PACK_OWNED = set(json.loads(_meta.read_text()).get("icons", {})) if _meta else set()


def place(dirpath, name, ext):
    """path to write; removes any existing .png/.svg of that name first (an older .png would beat a new .svg)"""
    for e in (".png", ".svg"):
        old = dirpath / f"{name}{e}"
        if (old.is_symlink() or old.exists()) and not DRY:
            old.unlink()
    return dirpath / f"{name}{ext}"


def write_png(name, ctx, size, img):
    d = dest_dir(size, ctx)
    if d is None or name in PACK_OWNED:
        stats["skipped-pack-owned"] += name in PACK_OWNED
        OWNED_SKIPPED.add(name) if name in PACK_OWNED else None
        return
    if not DRY:
        d.mkdir(parents=True, exist_ok=True)
    t = place(d, name, ".png")
    if not DRY:
        img.save(t)
    stats["generated"] += 1


def link(name, ctx, size, source):
    d = dest_dir(size, ctx)
    if d is None or (name in PACK_OWNED and name not in ALLOW_OWNED):
        stats["skipped-pack-owned"] += name in PACK_OWNED
        OWNED_SKIPPED.add(name) if name in PACK_OWNED else None
        return False
    if not DRY:
        d.mkdir(parents=True, exist_ok=True)
    t = place(d, name, source.suffix)
    if not DRY:
        t.symlink_to(os.path.relpath(source, d) if str(source).startswith(str(ICONS)) else source)
    return True


# --------------------------------------------------------------------------------------------
# Art helpers
# --------------------------------------------------------------------------------------------
# --------------------------------------------------------------------------------------------
# Media transport and zoom: Breeze's flat set (compy-686 postinstall step 4; runs first, as it did there)
# --------------------------------------------------------------------------------------------
# The pack's are wrong or inconsistent: media-playlist-shuffle/-repeat are the green Play icon, skip-backward is the
# orange Back arrow beside skip-forward's green >> tile, seek is green circle arrows, pause is bare blue bars, and
# nearly every zoom-* is one orange tile. XP's own transport controls were plain shapes and Breeze's flat ones suit
# that better, so these names are removed from both XP themes and fall through. Plain zoom.png goes too, or KDE
# strips zoom-in -> zoom inside the XP theme. Kept in XP colour: the media controller's tray state icons
# (media-playback-playing/-paused/-stopped), recreated from the pack's own pictures if an earlier run removed them.
FLAT = re.compile(r"^(media-(playback|skip|seek|record|playlist|repeat)-.*|media-record.*|zoom-.*|zoom)$")
TRAY_STATE = {"playing": "xp-f67e5cab", "paused": "xp-6aa302ae", "stopped": "xp-5b68262c"}
flat_removed = flat_restored = 0
for theme in (PRIM, EXT):
    for path in sorted(theme.glob("*x*/*/*")):
        stem = path.name.rsplit(".", 1)[0]
        if not FLAT.match(stem) or re.match(r"^media-playback-(playing|paused|stopped)", stem):
            continue
        if path.is_symlink() or path.is_file():
            if not DRY:
                path.unlink()
            flat_removed += 1
for status in sorted(EXT.glob("*x*/status")):
    for state, prefix in TRAY_STATE.items():
        for suffix in ("", "-symbolic"):
            name = f"media-playback-{state}{suffix}.png"
            if (status / name).is_symlink() or (status / name).exists():
                continue
            src = next(iter(sorted(status.glob(prefix + "*.png")) + sorted((status.parent / "actions").glob(prefix + "*.png"))), None)
            if src is None:
                continue
            if not DRY:
                if src.parent != status and not (status / src.name).exists():
                    shutil.copy2(src, status / src.name)
                (status / name).symlink_to(src.name)
            flat_restored += 1
print(f"flat media/zoom: removed {flat_removed} XP entries (-> Breeze); tray state icons recreated {flat_restored}")

# --------------------------------------------------------------------------------------------
# A distinct Save As (compy-686 postinstall step 5)
# --------------------------------------------------------------------------------------------
# The pack gives Save, Save As, Export and Save All one floppy. Save As gets the floppy with XP's notepad-and-pencil
# (document-edit) as a badge in the bottom-right corner, 55% of the icon size, rebuilt from both each run.
save_as = 0
for actions in sorted(EXT.glob("*x*/actions")):
    size = int(actions.parent.name.split("x")[0])
    for suffix in ("", "-symbolic"):
        base, over = actions / f"document-save{suffix}.png", actions / f"document-edit{suffix}.png"
        if not (base.exists() and over.exists()):
            continue
        img = Image.open(os.path.realpath(base)).convert("RGBA")
        badge = Image.open(os.path.realpath(over)).convert("RGBA").resize((size * 55 // 100,) * 2, Image.Resampling.LANCZOS)
        img.alpha_composite(badge, (img.width - badge.width, img.height - badge.height))
        target = actions / f"document-save-as{suffix}.png"
        if not DRY:
            if target.is_symlink():
                target.unlink()
            img.save(target)
        save_as += 1
print(f"Save As icon: floppy + pencil badge ({save_as} files)")

# Aliases the owner judged wrong (xp-deleted.txt): removed from XPlasma Extended at every size before anything is scanned,
# so they also stop shadowing/absorbing other names in the lookup model below
DELETED_LIST = HERE / "xp-deleted.txt"
removed_by_list = 0
if DELETED_LIST.is_file():
    for line in DELETED_LIST.read_text().splitlines():
        if not line.strip() or line.startswith("#") or "/" not in line:
            continue
        ctx, name = line.strip().split("/", 1)
        for path in EXT.glob(f"*x*/{ctx}/{name}.*"):
            if path.suffix in (".png", ".svg") and (path.is_symlink() or path.exists()):
                if not DRY:
                    path.unlink()
                removed_by_list += 1
print(f"removed by xp-deleted.txt: {removed_by_list} files")

ext_idx = scan(EXT, (".png",))
prim_idx = scan(PRIM)   # names of XPlasma Primary before this run's additions are counted below
pap_idx = scan_papirus()
prim_names, ext_names, pap_names = set(prim_idx), set(ext_idx), set(pap_idx)


def art(alias, size):
    paths = ext_idx.get(alias, {})
    for (s, _), p in paths.items():
        if s == size:
            return Image.open(os.path.realpath(p)).convert("RGBA")
    raise KeyError(f"no XP art '{alias}' at {size}px")


def svg(text, size):
    png = subprocess.run(["rsvg-convert", "-w", str(size), "-h", str(size)], input=text.encode(),
                         capture_output=True, check=True).stdout
    return Image.open(io.BytesIO(png)).convert("RGBA")


def svg_file(name, size):
    return svg((HERE / "svg" / f"{name}.svg").read_text(), size)


def raster_asset(name, size):
    return Image.open(HERE / "assets" / f"{name}.png").convert("RGBA").resize((size, size), Image.Resampling.LANCZOS)


def script_art(palette, size):
    base = art("application-javascript", size)
    if HUES[palette] is None:
        return base
    target, bright = HUES[palette]
    h, sat, val = base.convert("RGB").convert("HSV").split()
    lo, hi = round(25 / 360 * 255), round(75 / 360 * 255)             # the scroll's yellow/orange range
    mask = ImageChops.multiply(h.point(lambda x: 255 if lo <= x <= hi else 0),
                               sat.point(lambda x: 255 if x > 70 else 0))
    delta = round(target / 360 * 255) - round(50 / 360 * 255)         # the scroll sits near 50 degrees
    h2 = Image.composite(h.point(lambda x: (x + delta) % 256), h, mask)
    v2 = Image.composite(val.point(lambda x: int(x * bright)), val, mask) if bright != 1.0 else val
    out = Image.merge("HSV", (h2, sat, v2)).convert("RGB").convert("RGBA")
    out.putalpha(base.getchannel("A"))
    return out


def status_art(state, size):
    img = art("internet-chat", size)                        # Windows Messenger
    t = STATUS_TINT[state]
    if t is None:
        return img
    hue, sat, val, alpha = t
    h, s, v = img.convert("RGB").convert("HSV").split()
    out = Image.merge("HSV", (h.point(lambda x: round(hue / 360 * 255)), s.point(lambda x: int(x * sat)),
                              v.point(lambda x: int(min(255, x * val))))).convert("RGB").convert("RGBA")
    out.putalpha(img.getchannel("A").point(lambda x: int(x * alpha)))
    return out


def image_file_art(size, kind="photo"):
    """the real XP picture for this image kind -- each is already a full page-with-picture design, no
    compositing needed (an earlier version built one by badging a small image-viewer glyph onto a blank page;
    owner's call: these are better)"""
    if kind == "bmp":
        return art("image-bmp", size)                     # XP's paintbrush page: only .bmp used it
    name = "gif" if kind == "gif" else "jpg"               # gif: XP's "GIF" page (shapes); else "JPG" (photo)
    return raster_asset(name, size)


def iso_file_art(size):
    """blank page with XP's "CD-R" disc centred on it, same composite style as image_file_art()"""
    page = art("document-new", size)
    disc = Image.open(HERE / "art" / "cd-r.png").convert("RGBA")
    b = max(5, round(size * .46))
    page.alpha_composite(disc.resize((b, b), Image.Resampling.LANCZOS), (round(size * .27), round(size * .29)))
    return page


def badge_on(base, over, frac, corner):
    s = base.size[0]
    b = max(4, round(s * frac))
    if over.size[0] != b:
        over = over.resize((b, b), Image.Resampling.LANCZOS)
    out = base.copy()
    m = round(s * 0.01)
    x = s - b - m if "E" in corner else m
    y = s - b - m if "S" in corner else m
    out.alpha_composite(over, (x, y))
    return out


def recent_badge(size):
    doc = art("document-new", size)
    clock = art("preferences-system-time", size).resize((round(size * .55),) * 2, Image.Resampling.LANCZOS)
    doc.alpha_composite(clock, (size - clock.size[0], size - clock.size[1]))
    return doc


mime_names = set()
for line in Path("/usr/share/mime/types").read_text().split():
    mime_names.add(line.replace("/", "-"))
for line in Path("/usr/share/mime/aliases").read_text().splitlines():
    mime_names.add(line.split()[0].replace("/", "-"))


# image file types: XP's real "JPG" (photo) picture by default, "GIF" (shapes) for GIF/SVG; Papirus keeps the
# editor formats (PSD, XCF, Krita, OpenRaster). image-x-generic included now too (was excluded when this used a
# composite; XP's real JPG picture is a fine generic default, not just a JPEG-specific one).
IMAGE_PAPIRUS_RE = re.compile(r"psd|photoshop|xcf|krita|openraster")
BMP_RE = re.compile(r"(^|-)(bmp|bitmap)$|ms-bmp|win-bitmap|win-bmp")
GIF_RE = re.compile(r"^image-gif$|^image-svg\+xml")
IMAGE_NAMES = sorted(n for n in mime_names if n.startswith("image-") and not IMAGE_PAPIRUS_RE.search(n))

# --------------------------------------------------------------------------------------------
# 1. generate
# --------------------------------------------------------------------------------------------
generated = set()
for size in SIZES:
    folder = art("folder", size)
    for name, (kind, src, frac, corner) in FOLDERS.items():
        if kind == "only":
            img = art(src, size)
        else:
            over = {"art": lambda: art(src, size), "svg": lambda: svg_file(src, round(size * frac)),
                    "script": lambda: script_art(src, size),
                    "recent": lambda: recent_badge(size)}[kind]()
            img = badge_on(folder, over, frac, corner)
        write_png(name, "places", size, img)
        generated.add(name)
    for pal, names in SCRIPTS.items():
        img = script_art(pal, size)
        for n in names.split():
            write_png(n, "mimetypes", size, img)
            generated.add(n)
    img = svg_file("msi", size)
    for n in PACKAGES:
        write_png(n, "mimetypes", size, img)
        generated.add(n)
    img = svg_file("installer-box", size)
    for n in APPIMAGE:
        write_png(n, "mimetypes", size, img)
        generated.add(n)
    for n in IMAGE_NAMES:
        kind = "bmp" if BMP_RE.search(n) else "gif" if GIF_RE.search(n) else "photo"
        write_png(n, "mimetypes", size, image_file_art(size, kind))
        generated.add(n)
    for state, names in STATUS_NAMES.items():
        img = status_art(state, size)
        for n in names.split():
            for variant in (n, n + "-symbolic"):
                write_png(variant, "actions" if n.startswith("im-") else "status", size, img)   # KDE's im-* live in actions
                generated.add(variant)
print(f"generated: {len(generated)} names")

# overrides: replace every size XPlasma Primary has for these names, and the declared sizes
for name, (alias, ctx) in OVERRIDES.items():
    have = {}
    for (size, c), p in prim_idx.get(name, {}).items():
        have[(size, c)] = p
    todo = {(sz, ctx) for sz in SIZES} | set(have)
    for size, c in sorted(todo):
        d = PRIM / f"{size}x{size}/{c}"
        if not d.is_dir():
            continue
        src_size = next((x for x in SIZES if x >= size), SIZES[-1])
        if alias == "BLANK":
            img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        elif alias.startswith("FILE:"):
            img = Image.open(HERE / "art" / alias[5:]).convert("RGBA")
        elif alias.startswith("MIRROR:"):
            img = art(alias[7:], src_size).transpose(Image.Transpose.FLIP_LEFT_RIGHT)
        else:
            img = art(alias, src_size)
        if img.size[0] != size:
            img = img.resize((size, size), Image.Resampling.LANCZOS)
        for ext in (".png", ".svg"):
            t = d / f"{name}{ext}"
            if (t.is_symlink() or t.exists()) and not DRY:
                t.unlink()
        if not DRY:
            img.save(d / f"{name}.png")
        stats["overrides"] += 1
generated |= set(OVERRIDES)

# Dolphin names a directory's icon after its mime type, inode-directory. XPlasma Primary's own file for it is the XP
# folder (same picture as `folder`), which an earlier version of this tool wrongly replaced with Papirus's blue folder
# (XPlasma Extended maps that name to a document, which is what made it look like a fall-through candidate). Restore it
# from Primary's own folder.png, size by size. name -> (source name, context)
RESTORE_FROM_FOLDER = {"inode-directory": "places", "inode-directory-symbolic": "mimetypes"}
for name, ctx in RESTORE_FROM_FOLDER.items():
    for src in sorted(PRIM.glob("*x*/places/folder.png")):
        d = PRIM / src.parent.parent.name / ctx
        if d.is_dir() and not DRY:
            t = place(d, name, ".png")
            Image.open(src).convert("RGBA").save(t)
            stats["restored"] += 1
generated |= set(RESTORE_FROM_FOLDER)
print(f"restored from folder.png: {stats['restored']} files")

# `document-open` (the raster icon Kate etc. actually request for their Open toolbar button/menu item) was on
# xp-deleted.txt -- part of the owner's bulk cleanup of bad aliases -- so it fell all the way through to Breeze's
# folder-open.svg. Real XP's own Open button used the same open-folder picture as the places `folder-open` icon
# (already correct, not on the deleted list), so reuse that picture here too rather than leave it on Breeze.
# `document-open-symbolic` stays deleted/on Breeze deliberately, matching the general symbolic-icons-stay-flat policy.
restored_open = 0
for src in sorted(PRIM.glob("*x*/places/folder-open.png")):
    d = PRIM / src.parent.parent.name / "actions"
    if d.is_dir() and not DRY:
        t = place(d, "document-open", ".png")
        Image.open(src).convert("RGBA").save(t)
        restored_open += 1
generated.add("document-open")
print(f"restored document-open from folder-open.png: {restored_open} files")


# Dolphin's remote:/ "Shared Folders (SMB)" entry used `network-workgroup`, which is "My Network Places" (a
# single computer with a network badge, see the fix above for the Places sidebar's "Network" entry) -- the
# wrong XP picture for browsing a workgroup's member computers, which XP drew as three networked computers
# around a hub ("Workgroup.png", assets/workgroup.png here, from the same CC0 Windows XP High Resolution Icon
# Pack the rest of this theme is built from). No existing KDE icon name means "a workgroup of computers" as
# distinct from "my network places", so this is a custom name; ~/.local/share/remoteview/smb-network.desktop
# (a user-level override of the system one) points Icon= at it.
for size in SIZES:
    write_png("xp-workgroup", "places", size, raster_asset("workgroup", size))
generated.add("xp-workgroup")
print(f"xp-workgroup (Workgroup.png, for smb-network.desktop's Icon= override): {len(SIZES)} files")

# .iso files (application/vnd.efi.iso, confirmed via `xdg-mime query filetype` -- its aliases
# application-x-cd-image and application-x-iso9660-image too): the pack mapped these to its Generic Text
# Document / Bitmap pictures, nonsensical enough that an earlier pass put them on FALLTHROUGH_EXACT rather than
# show them. Checked ALIAS-PROVENANCE.json first: XP's "CD-R" picture (art/cd-r.png) isn't used by anything
# else. Composited onto the generic document page (iso_file_art(), same style as image_file_art()) rather than
# used alone, since it's a disc-image *file*, not an actual disc. Other disk-image formats (virtual hard disks,
# raw images) stay on FALLTHROUGH_EXACT -- a CD picture doesn't fit those.
for name in ("application-vnd.efi.iso", "application-x-cd-image", "application-x-iso9660-image"):
    for size in SIZES:
        write_png(name, "mimetypes", size, iso_file_art(size))
    generated.add(name)
print(f"iso_file_art (CD-R.png composited on document-new, for .iso and its aliases): {len(SIZES) * 3} files")
print(f"overridden: {len(OVERRIDES)} names, {stats['overrides']} files")

# --------------------------------------------------------------------------------------------
# fill: icons the pack ships in XPlasma Primary at 16px only (the network-wired/-wireless status set). KDE finds
# Primary's exact-name file first and scales the 16px picture up (pixelated in Plasma's Networks list), although
# XPlasma Extended has the real art at every size. Add the missing sizes to Primary from Extended; its own 16px
# originals stay for the tray.
# --------------------------------------------------------------------------------------------
BIG_SIZES = [22, 24, 32, 48, 64, 128]
filled = 0
for name, by_size in sorted(prim_idx.items()):
    sizes = {sz for sz, _ in by_size}
    if name not in ext_idx or name in generated or max(sizes) >= 32:
        continue
    ctx = sorted(c for _, c in by_size)[0]
    for sz in BIG_SIZES:
        src = next((p for (s_, _), p in ext_idx[name].items() if s_ == sz), None)
        d = dest_dir(sz, ctx)
        if src is None or d is None or sz in sizes:
            continue
        target = d / f"{name}.png"
        if target.is_symlink() or target.exists():
            continue
        if not DRY:
            d.mkdir(parents=True, exist_ok=True)
            target.symlink_to(os.path.relpath(os.path.realpath(src), d))
        filled += 1
print(f"filled missing sizes in Primary from Extended: {filled} files")

# --------------------------------------------------------------------------------------------
# purge: families whose XPlasma Extended mappings are all unwanted (owner decision): Office placeholders, and every
# image-* alias except the two pictures the image-file icons are built from (the paintbrush and the landscape)
# --------------------------------------------------------------------------------------------
PROV = json.loads((EXT / "ALIAS-PROVENANCE.json").read_text())
PURGE_RE = [r"^x-office-"]
# every alias whose picture is one of these pack pictures (matched by source name via ALIAS-PROVENANCE.json, not hash),
# except the names listed. Bitmap.png = the paintbrush page (XP used it for .bmp only, the pack hung it on all image types,
# disk images, AppImage, insert-image); Graph View.png = a chart in a window (spreadsheet/planning apps);
# Wordpad.png = notepad and pen (word processors, applications-office), but RTF really was WordPad's;
# Script Component.png = the cyan scroll with a gear: leftovers, Primary's recoloured JavaScript page replaces it.
PURGE_SOURCES = {"Bitmap.png": {"image-bmp"},          # the paintbrush stays for .bmp (and image-file icons are built from it)
                 "Graph View.png": set(),
                 "Script Component.png": set(),        # cyan scroll + gear: every name using it has our recoloured script icon
                 "Wordpad.png": {"application-rtf", "text-rtf"}}
PURGE_BY_NAME = {k: PURGE_SOURCES[v["source"].split("/")[-1]] for k, v in PROV.items()
                 if isinstance(v, dict) and v.get("source", "").split("/")[-1] in PURGE_SOURCES}


def purged(n):
    base = re.sub(r"-symbolic$", "", n)
    if n in PACK_OWNED or (base in PURGE_BY_NAME and base in PURGE_BY_NAME[base]):
        return False
    return base in PURGE_BY_NAME or any(re.search(r, base) for r in PURGE_RE)


gone = 0
for n in sorted(list(ext_idx)):
    if purged(n):
        for path in ext_idx[n].values():
            if path.is_symlink() or path.exists():
                if not DRY:
                    path.unlink()
                gone += 1
        del ext_idx[n]
        ext_names.discard(n)
stale = 0
for p in PRIM.glob("*x*/*/*"):                       # earlier exposures of those names (symlinks into Extended)
    n = re.sub(r"\.(png|svg)$", "", p.name)
    if p.is_symlink() and purged(n) and n not in generated and "xplasma-xp-extended" in os.path.realpath(p):
        if not DRY:
            p.unlink()
        stale += 1
print(f"purged from Extended: {gone} files; stale exposures removed from Primary: {stale}")

# --------------------------------------------------------------------------------------------
# 2./3. expose hidden XP art, pin Papirus
# --------------------------------------------------------------------------------------------
# the pack maps ~270 mimetype names (even inode-directory) to its generic text-document picture: let Papirus
# draw those instead (the generic fallback itself stays XP)
PROV = json.loads((EXT / "ALIAS-PROVENANCE.json").read_text())
GENERIC_SRC = {k for k, v in PROV.items() if isinstance(v, dict) and v.get("context") == "mimetypes"
               and v.get("source", "").endswith("Generic Text Document.png")}
KEEP_GENERIC = {"text-x-generic", "text-plain", "unknown", "application-octet-stream", "application-x-generic"}


def is_fallthrough(n):
    base = re.sub(r"-symbolic$", "", n)
    # PACK_OWNED (the pack's install-time snapshot), not "is it in Primary now": our own pins live in Primary too
    if base in GENERIC_SRC and base not in KEEP_GENERIC and base not in PACK_OWNED:
        return True
    if base in FALLTHROUGH_EXACT or any(re.search(r, base) for r in FALLTHROUGH_RE):
        return True
    fam = base.split("-")[0]
    return fam in FALLTHROUGH_FAMILIES and base in mime_names


def papirus_source(n):
    p = first_match(pap_names, n)
    return p


def pin(n, via=None):
    """symlink Papirus's file for name `via or n` in every declared <size>/<ctx> dir"""
    if ".sv" in n:                      # the pack has a junk alias "text-x-generic.svapplication-x-awk"
        return 0
    src_name = papirus_source(via or n)
    if not src_name:
        return 0
    cands = pap_idx[src_name]
    made = 0
    for size in SIZES:
        # nearest-size file, preferring the context Papirus itself uses
        (s, ctx), path = min(cands.items(), key=lambda kv: (abs(kv[0][0] - size), kv[0][1] not in
                             ("mimetypes", "places", "actions", "apps", "status", "devices", "categories")))
        pctx = PRIM_CTX_FROM_PAPIRUS.get(ctx, ctx)
        if link(n, pctx, size, path):
            made += 1
    return made


# the pack's own files for the ALLOW_OWNED names go first (every context and size, -symbolic too), so that only
# our bell below answers for them
for n in sorted(ALLOW_OWNED):
    for v in (n, n + "-symbolic"):
        for path in list(PRIM.glob(f"*/*/{v}.png")) + list(PRIM.glob(f"*/*/{v}.svg")):
            if not DRY:
                path.unlink()

# the tray bell: the pack draws the XP warning triangle. Ours is a golden bell in the style of the Favorites star
# (svg/bell.svg), with XP's red X in the corner when notifications are off (Do Not Disturb), rendered per size.
BELL = {"bell": ("notifications", "notification-active", "notification-inactive"),
        "bell-off": ("notifications-disabled", "notification-disabled")}
for art_name, names in BELL.items():
    for size in SIZES:
        img = svg_file("bell", size)
        if art_name == "bell-off":
            img = xp_marks.with_red_x(img)
        for n in names:
            for v in (n, n + "-symbolic"):
                for ctx in ("status", "actions"):
                    d = dest_dir(size, ctx)
                    if d is None:
                        continue
                    if not DRY:
                        img.save(place(d, v, ".png"))
                    stats["generated"] += 1
generated |= {v for ns in BELL.values() for n in ns for v in (n, n + "-symbolic")}

hidden, intercepted = [], []
for n in ext_names:
    if n in prim_names or n in generated:
        continue
    c = first_match(prim_names, n)
    if c and c != n:
        hidden.append(n)
for n in pap_names - ext_names - prim_names:
    if n in generated:
        continue
    c = first_match(prim_names, n) or first_match(ext_names, n)
    if c and c != n:
        intercepted.append((n, c))

# pins from the Papirus days (the theme no longer inherits it): remove, the pins below are made again from Breeze
for path in PRIM.glob("*/*/*"):
    if path.is_symlink() and os.readlink(path).startswith("/usr/share/icons/Papirus") and not DRY:
        path.unlink()
exposed = pinned = 0
skipped_folder = 0
REPORT = collections.defaultdict(list)
FALL_NAMES = []
intercepted_names = {n for n, _ in intercepted}
for n in sorted(set(ext_names) | pap_names | FALLTHROUGH_EXACT):
    if n in generated or not is_fallthrough(n):
        continue
    if n in ext_names or n in intercepted_names:     # XP would show its own art / swallow Papirus's
        made = pin(n)
        if made:
            pinned += 1
            REPORT['pin-fallthrough'].append(n)
        # only drop the XP alias when Breeze has that exact name (not just its generic family icon); otherwise XP's stays
        if n in ext_names and n not in PACK_OWNED and (made or n in pap_names):
            FALL_NAMES.append(n)
for n in sorted(hidden):
    if is_fallthrough(n):
        continue
    if n.startswith("folder-") and re.sub(r"-(symbolic|rtl)+$", "", n) not in FOLDER_EXPOSE:
        skipped_folder += 1
        continue
    for (size, ctx), path in ext_idx[n].items():
        if size in SIZES and link(n, ctx, size, Path(os.path.realpath(path))):
            pass
    exposed += 1
    REPORT['expose'].append(n)
# names Breeze lacks but has under another name (otherwise they would resolve to nothing once XP's wrong alias is gone)
VIA = {"list-refresh": "view-refresh", "application-spreadsheet": "x-office-spreadsheet", "application-presentation": "x-office-presentation",
       # the menu glyphs: the pack shows its "Programs" picture (CD with a swirl) on every one of them
       "open-menu": "open-menu-symbolic", "hamburger-menu": "open-menu-symbolic",
       "hamburger-menu-symbolic": "open-menu-symbolic"}
for n, via in VIA.items():
    if pin(n, via):
        pinned += 1
        REPORT['pin-via'].append(n)
        if n in ext_names and n not in PACK_OWNED and n not in FALL_NAMES:
            FALL_NAMES.append(n)
# Names the pack maps to its generic "Programs" picture (CD with a swirl): the glyph names above are done; for the rest
# (mostly KDE app ids) an icon the app or Breeze ships itself is better, so the picture only stays where nothing else
# has that name. Category names and start-here stay on it.
PROGRAMS_KEEP = re.compile(r"^(applications-(accessories|other|utilities)|start-here)")
HICOLOR = {p.stem for p in Path("/usr/share/icons/hicolor").glob("*/apps/*")}
for n, v in PROV.items():
    if not (isinstance(v, dict) and v.get("source", "").endswith("/Programs.png")) or PROGRAMS_KEEP.match(n):
        continue
    if n in ext_names and n not in PACK_OWNED and n not in FALL_NAMES and n not in generated:
        if n in pap_names or n in HICOLOR:
            if n in pap_names and pin(n):
                pinned += 1
                REPORT['pin-programs'].append(n)
            FALL_NAMES.append(n)
# Symbolic names must be line drawings. The pack gives 547 of them its full-colour XP picture (reason semantic/exact);
# Breeze has a symbolic drawing for every one. Pin Breeze's into Primary (it is searched first, and an XP long/short
# name in Extended would otherwise still win by KDE's dash-stripping) and drop the colour alias. XP-styled glyphs
# (reason xp-styled-kde-glyph, control-glyph, tray-state) are the pack's deliberate look and stay.
SYMBOLIC_FIXED = []
for n in sorted(ext_names):
    v = PROV.get(n, {})
    if (n.endswith("-symbolic") and isinstance(v, dict) and v.get("reason") in ("semantic", "exact")
            and n in pap_names and n not in generated and n not in PACK_OWNED):
        if pin(n):
            pinned += 1
            SYMBOLIC_FIXED.append(n)
            if n not in FALL_NAMES:
                FALL_NAMES.append(n)
print(f"symbolic names switched to Breeze's line drawing: {len(SYMBOLIC_FIXED)}")
# names deleted via xp-deleted.txt: where Breeze has the exact name, pin it so nothing shorter in XP wins
DELETED_PINNED = 0
if DELETED_LIST.is_file():
    for line in DELETED_LIST.read_text().splitlines():
        if line.strip() and not line.startswith("#") and "/" in line:
            n = line.strip().split("/", 1)[1]
            if n in pap_names and n not in generated and n not in PACK_OWNED and pin(n):
                DELETED_PINNED += 1
print(f"deleted names pinned to Breeze: {DELETED_PINNED}")
for n, absorber in sorted(intercepted):
    if absorber in PIN_ABSORBERS and not is_fallthrough(n):
        if pin(n):
            pinned += 1
            REPORT['pin-'+absorber].append(n)
# the names we let fall through no longer have an XP alias to confuse anyone (the pack re-creates them on a
# reinstall; this script removes them again)
deleted = 0
for n in FALL_NAMES:
    for path in ext_idx[n].values():
        if path.is_symlink() or path.exists():
            if not DRY:
                path.unlink()
            deleted += 1
for n in RESTORE_FROM_FOLDER:                      # Extended maps these to the generic document; Primary's folder wins
    for path in ext_idx.get(n, {}).values():
        if path.is_symlink() or path.exists():
            if not DRY:
                path.unlink()
            deleted += 1
for n in sorted(generated):                        # names we draw ourselves: drop Extended's generic-document leftovers too
    base = re.sub(r"-symbolic$", "", n)
    if base in GENERIC_SRC and base not in KEEP_GENERIC and base not in PACK_OWNED:
        for path in ext_idx.get(n, {}).values():
            if path.is_symlink() or path.exists():
                if not DRY:
                    path.unlink()
                deleted += 1
print(f"fall-through names: {len(FALL_NAMES)}; XP aliases removed: {deleted}")
print(f"hidden XP icons: {len(hidden)} -> exposed {exposed}, folder colour variants skipped {skipped_folder}")
print(f"Papirus pinned: {pinned}; skipped pack-owned names: {sorted(OWNED_SKIPPED) or 'none'}")

if "--report" in sys.argv:
    Path(sys.argv[sys.argv.index("--report") + 1]).write_text(json.dumps(REPORT, indent=1))
if not DRY and shutil.which("gtk-update-icon-cache"):
    for theme in (PRIM, EXT):
        subprocess.run(["gtk-update-icon-cache", "-f", "-q", str(theme)], check=False)
print("dry run: nothing written" if DRY else "done")
