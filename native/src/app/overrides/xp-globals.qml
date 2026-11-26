
    // XPlasma: XP's balloons in place of Plasma's popups, when the look
    // brings their art (widgets/xp-notify). One balloon at a time, oldest
    // first; the rest wait as icons in the tray (xpQueue), and a balloon that
    // timed out unread leaves its icon behind, dot-marked, to show it again.
    // Some senders skip XP's balloon (and its tray icon) entirely, every
    // time (xpAlwaysNative) or only while they're bursting (xpUseXPBalloon),
    // read from XpPopup.qml's wantsBalloon/sync(). Still recorded in
    // Plasma's own notification history as always -- just no XP-styled
    // toast for it. (A per-notification switch to Plasma's own popup, not
    // just no XP one, would need DelegateChooser's "when:" on the
    // Instantiator's delegate -- unavailable before Qt 6.9, which none of
    // this fork's supported Plasma versions ship yet.)
    property int xpArtVersion: 0
    property KSvg.Svg xpArt: KSvg.Svg {
        imagePath: "widgets/xp-notify"
        onRepaintNeeded: globals.xpArtVersion++
    }
    // ...unless the installer's "Plasma notification popups" customization
    // is on ([Notifications] balloons=false in xplasma-customizationsrc, the
    // installer's own file). Read once, when the shell starts: the installer
    // writes it before the desktop apply restarts the shell.
    property Settings xpNotificationSettings: Settings {
        location: StandardPaths.writableLocation(StandardPaths.ConfigLocation) + "/xplasma-customizationsrc"
        category: "Notifications"
        property bool balloons: true
    }
    readonly property bool xpBalloons: xpNotificationSettings.balloons && xpArtVersion >= 0 && xpArt.hasElement("close-normal")
    onXpBalloonsChanged: {
        xpCurrentId = -1;
        Qt.callLater(xpAdvance);
    }

    property var xpQueue: []            // [{id, icon, unread, applicationName, desktopEntry, sender, snapshot}]
    property var xpIcons: ({})          // notification id -> the tray item its balloon points at
    property int xpCurrentId: -1        // whose balloon is on screen
    property QtObject xpRecalled: null  // a balloon shown again from its icon

    // Senders whose balloon always goes to Plasma's own popup (stacking,
    // grouping, Do Not Disturb), never XP's: XP's shared tray balloon was
    // really a system mechanism (new hardware, low battery, updates ready).
    // Chatty apps of that era mostly drew their own toast windows instead of
    // using it; on Linux every app shares the same notification pipe, so
    // there's no telling those apart for free -- this rebuilds the split by
    // hand, by sender. (Aliases vary by how an app is packaged -- native,
    // Flatpak, Snap -- so more than one spelling is listed for most.)
    readonly property var xpNativeSenders: new Set([
        // Browsers: their own notices, and any website's (a browser is the
        // sender either way, so there's no telling those apart either).
        "firefox", "org.mozilla.firefox", "firefox-esr", "firefox-developer-edition", "firefox-nightly",
        "chromium", "chromium-browser", "org.chromium.chromium",
        "google-chrome", "google-chrome-stable", "com.google.chrome",
        "microsoft-edge", "microsoft-edge-stable", "com.microsoft.edge",
        "brave-browser", "com.brave.browser",
        "vivaldi-stable", "vivaldi", "com.vivaldi.vivaldi",
        "opera", "com.opera.opera",
        "waterfox", "net.waterfox.waterfox",
        "librewolf", "io.gitlab.librewolf-community",
        "org.kde.falkon",
        "org.gnome.epiphany",
        "torbrowser", "org.torproject.torbrowser-launcher",
        // Messaging and chat.
        "discord", "com.discordapp.discord",
        "slack", "com.slack.slack",
        "teams", "teams-for-linux", "com.microsoft.teams", "com.github.ismaelmartinez.teams_for_linux",
        "element-desktop", "im.riot.app",
        "beeper", "com.beeper.desktop",
        "whatsapp-for-linux", "whatsie", "io.github.mstaniewski.whatsie", "com.rtosta.zapzap",
        "telegramdesktop", "org.telegram.desktop",
        "signal-desktop", "org.signal.signal",
        "skype", "com.skype.client",
        "mattermost-desktop", "com.mattermost.desktop",
        "zoom", "us.zoom.zoom",
        "franz", "ferdium",
        "caprine", "com.sindresorhus.caprine",
        // IRC: low signal per message, exactly what bursts.
        "hexchat", "org.kde.konversation", "quasselclient", "org.gnome.polari",
    ])
    // A Chromium-family browser's own generated id for an installed PWA
    // ("chrome-<id>-Default" and friends): any site, by prefix alone, so an
    // Instagram or Google Chat install doesn't need naming individually.
    readonly property var xpNativePrefixes: [
        "chrome-", "chromium-", "brave-browser-", "vivaldi-", "msedge-", "microsoft-edge-", "opera-",
    ]
    // applicationName fallback (alnum-only, lowercased -- see xpSimpleName):
    // for a browser that reports the site's own name instead of its own, or
    // any sender whose desktopEntry doesn't match the lists above.
    readonly property var xpNativeNames: new Set([
        "firefox", "chromium", "googlechrome", "microsoftedge", "msedge", "bravebrowser", "brave",
        "vivaldi", "opera", "waterfox", "librewolf", "falkon", "epiphany", "gnomeweb", "torbrowser",
        "discord", "slack", "microsoftteams", "teams", "element", "matrix", "beeper",
        "whatsapp", "telegram", "telegramdesktop", "signal", "skype", "mattermost", "zoom",
        "franz", "ferdium", "caprine", "messenger", "facebookmessenger",
        "hexchat", "konversation", "quassel", "quasselclient", "polari",
        "instagram", "googlechat", "googlemessages", "messages",
    ])
    function xpSimpleName(s) {
        return (s || "").toString().toLowerCase().replace(/[^a-z0-9]/g, "");
    }
    function xpAlwaysNative(desktopEntry, applicationName) {
        const entry = (desktopEntry || "").toLowerCase();
        if (entry && (xpNativeSenders.has(entry) || xpNativePrefixes.some(p => entry.startsWith(p))))
            return true;
        return xpNativeNames.has(xpSimpleName(applicationName));
    }
    function xpSenderKey(desktopEntry, applicationName) {
        return (desktopEntry || "").toLowerCase() || ("name:" + xpSimpleName(applicationName));
    }
    // Anyone else, bursting: more of its notifications are still queued (not
    // yet read, dismissed or timed-out-and-recalled) than this. Falls back
    // to XP again on its own once the backlog's cleared -- no separate
    // cooldown to track.
    readonly property int xpBurstThreshold: 4
    property var xpSenderCounts: ({})   // sender key -> how many of its notifications are still queued
    function xpUseXPBalloon(desktopEntry, applicationName) {
        if (xpAlwaysNative(desktopEntry, applicationName))
            return false;
        const key = xpSenderKey(desktopEntry, applicationName);
        return (xpSenderCounts[key] || 0) < xpBurstThreshold;
    }

    function xpEntry(id) {
        return xpQueue.find(e => e.id === id);
    }
    function xpEnqueue(popup) {
        if (xpEntry(popup.notificationId))
            return;
        const sender = xpSenderKey(popup.desktopEntry, popup.applicationName);
        xpQueue = xpQueue.concat([{
            id: popup.notificationId,
            icon: popup.trayIcon,
            unread: false,
            applicationName: popup.applicationName,
            desktopEntry: popup.desktopEntry,
            sender: sender,
        }]);
        const counts = Object.assign({}, xpSenderCounts);
        counts[sender] = (counts[sender] || 0) + 1;
        xpSenderCounts = counts;
    }
    function xpForget(id) {
        const e = xpEntry(id);
        if (!e)
            return;
        xpQueue = xpQueue.filter(entry => entry.id !== id);
        if (xpSenderCounts[e.sender] > 0) {
            const counts = Object.assign({}, xpSenderCounts);
            if (--counts[e.sender] <= 0)
                delete counts[e.sender];
            xpSenderCounts = counts;
        }
    }
    // Timed out unread: the icon stays, dot-marked, with what to show again.
    function xpExpired(popup) {
        const snapshot = {
            summary: popup.summary,
            body: popup.body,
            image: popup.image,
            iconName: popup.iconName,
            applicationIconName: popup.applicationIconName,
            applicationName: popup.applicationName,
            desktopEntry: popup.desktopEntry,
            urgency: popup.urgency,
            urls: popup.urls,
            jobError: popup.jobError,
        };
        xpQueue = xpQueue.map(e => e.id === popup.notificationId ? Object.assign({}, e, {unread: true, snapshot: snapshot}) : e);
    }
    // A notification leaving the history -- dismissed from it, or the history
    // cleared -- takes its icon with it, dot-marked or not: an icon for a
    // notification the list no longer has would be one only a click could
    // remove. (A transient one was never kept in the history; its icon stays
    // until clicked, as it did.)
    property QtObject xpHistory: NotificationManager.Notifications {
        showExpired: true
        showDismissed: true
        showJobs: false
        groupMode: NotificationManager.Notifications.GroupDisabled
    }
    property QtObject xpHistoryWatch: Connections {
        target: globals.xpHistory
        function onRowsAboutToBeRemoved(parent, first, last) {
            for (let row = first; row <= last; ++row) {
                const index = globals.xpHistory.index(row, 0);
                if (globals.xpHistory.data(index, NotificationManager.Notifications.TransientRole))
                    continue;
                globals.xpForget(globals.xpHistory.data(index, NotificationManager.Notifications.IdRole));
            }
        }
    }
    // A popup gone: its icon too, unless it's left dot-marked.
    function xpDropped(id) {
        const e = xpEntry(id);
        if (e && !e.unread)
            xpForget(id);
        Qt.callLater(xpAdvance);
    }
    function xpRegisterIcon(id, item) {
        const icons = Object.assign({}, xpIcons);
        icons[id] = item;
        xpIcons = icons;
    }
    function xpUnregisterIcon(id, item) {
        if (xpIcons[id] !== item)
            return;
        const icons = Object.assign({}, xpIcons);
        delete icons[id];
        xpIcons = icons;
    }
    // The next balloon: the one on screen stays; otherwise the oldest waiting.
    function xpAdvance() {
        if (!xpBalloons) {
            xpCurrentId = -1;
            return;
        }
        if (xpRecalled) {
            xpCurrentId = xpRecalled.notificationId;
            return;
        }
        let next = -1;
        for (let i = 0; i < popupInstantiator.count; ++i) {
            const popup = popupInstantiator.objectAt(i);
            if (!popup || !popup.wantsBalloon || popup.notificationId === undefined)
                continue;
            if (popup.notificationId === xpCurrentId)
                return;
            if (next < 0 || popup.notificationId < next)
                next = popup.notificationId;
        }
        xpCurrentId = next;
    }
    function xpRecall(id) {
        const e = xpEntry(id);
        if (!e || !e.snapshot)
            return;
        if (xpRecalled)
            xpEndRecall(false);
        xpRecalled = xpRecallComponent.createObject(globals, Object.assign({notificationId: id, recalled: true}, e.snapshot));
        xpAdvance();
    }
    function xpEndRecall(read) {
        if (!xpRecalled)
            return;
        if (read)
            xpForget(xpRecalled.notificationId);
        xpRecalled.destroy();
        xpRecalled = null;
        xpAdvance();
    }
    property Component xpRecallComponent: Component {
        XpPopup {
            onReadRequested: globals.xpEndRecall(true)
            onCloseRequested: globals.xpEndRecall(true)
            onExpireRequested: globals.xpEndRecall(false)
        }
    }
