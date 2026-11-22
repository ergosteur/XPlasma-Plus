"""Optional customizations: parsing, feature gating, publishing, and the tray bell script."""
import json, sys, unittest
from pathlib import Path
from unittest.mock import Mock
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import tweaks


class Tweaks(unittest.TestCase):
    def test_every_tweak_is_described_and_requires_known_features(self):
        import json
        known = {f['id'] for f in json.loads((Path(tweaks.__file__).parent / 'features.json').read_text())}
        for t in tweaks.TWEAKS:
            self.assertTrue(t['label'] and t['help'], t['id'])
            self.assertTrue(set(t['requires']) <= known, t['id'])

    def test_parse_sorts_dedupes_and_rejects_unknown(self):
        self.assertEqual(tweaks.parse(' bell_always_shown,bell_always_shown '), ['bell_always_shown'])
        self.assertEqual(tweaks.parse(''), [])
        self.assertEqual(tweaks.parse(None), [])
        with self.assertRaises(ValueError):
            tweaks.parse('bell_always_shown,nope')

    def test_tweak_only_applies_with_its_features(self):
        self.assertEqual(tweaks.active(['bell_always_shown'], {'icons'}), [])
        self.assertEqual(tweaks.active(['bell_always_shown'], {'taskbar'}), ['bell_always_shown'])

    def test_publish_records_every_tweak_state(self):
        settings = {}
        tweaks.publish(settings, ['bell_always_shown'], {'icons'})
        self.assertEqual(settings['installerTweaks'], {t['id']: False for t in tweaks.TWEAKS})
        tweaks.publish(settings, ['bell_always_shown'], {'taskbar'})
        self.assertTrue(settings['installerTweaks']['bell_always_shown'])

    def test_bell_script_runs_only_when_active(self):
        script = Mock()
        tweaks.apply(['bell_always_shown'], {'icons'}, Mock(), script, Mock())
        script.assert_not_called()
        tweaks.apply(['bell_always_shown'], {'taskbar'}, Mock(), script, Mock())
        text = script.call_args.args[0]
        self.assertIn('org.kde.plasma.systemtray', text)
        self.assertIn('shownItems', text)


    def test_show_desktop_launcher_is_written_and_pinned_first(self):
        import tempfile
        script = Mock()
        with tempfile.TemporaryDirectory() as d:
            home = Path(d)
            tweaks.apply(['show_desktop_button'], {'taskbar'}, Mock(), script, Mock(), home=home, qdbus='/usr/bin/qdbus6')
            script.assert_not_called()   # needs the icons feature for its XP icon
            tweaks.apply(['show_desktop_button'], {'taskbar', 'icons'}, Mock(), script, Mock(), home=home, qdbus='/usr/bin/qdbus6')
            entry = home / '.local/share/applications/xp-show-desktop.desktop'
            text = entry.read_text()
            self.assertIn('Icon=xpshowdesktop', text)
            self.assertIn('Exec=/usr/bin/qdbus6 org.kde.kglobalaccel /component/kwin', text)
            self.assertIn('"Show Desktop"', text)
            pin = script.call_args.args[0]
            self.assertIn(json.dumps(entry.as_uri()), pin)
            self.assertIn('urls.unshift(url)', pin)

    def test_keep_firefox_icon_removes_only_firefox_from_the_expanded_layer(self):
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            home = Path(d)
            apps = home / '.local/share/icons/xplasma-xp-extended/32x32/applications'
            apps.mkdir(parents=True)
            for name in ['firefox.png', 'org.mozilla.firefox.png', 'internet-web-browser.png', 'firefox-esr.png']:
                (apps / name).write_bytes(b'x')
            tweaks.apply(['keep_firefox_icon'], {'icons'}, Mock(), Mock(), Mock(), home=home)
            self.assertEqual(sorted(p.name for p in apps.iterdir()), ['firefox-esr.png', 'internet-web-browser.png'])

    def test_native_tweaks_are_published_for_the_runtime(self):
        settings = {}
        tweaks.publish(settings, ['smooth_text', 'keep_firefox_icon'], {'fonts', 'icons'})
        self.assertTrue(settings['installerTweaks']['smooth_text'])
        self.assertTrue(settings['installerTweaks']['keep_firefox_icon'])
        tweaks.publish(settings, ['smooth_text'], {'icons'})
        self.assertFalse(settings['installerTweaks']['smooth_text'])

    def test_notification_style_is_written_both_ways_before_the_shell_restarts(self):
        from unittest.mock import patch
        run = Mock()
        with patch.object(tweaks.shutil, 'which', return_value='/usr/bin/kwriteconfig6'):
            tweaks.prepare(['plasma_notifications'], {'icons'}, run)
            run.assert_not_called()   # no XP taskbar, nothing to say
            tweaks.prepare(['plasma_notifications'], {'taskbar'}, run)
            self.assertEqual(run.call_args.args[0][-1], 'false')
            self.assertIn('xplasma-customizationsrc', run.call_args.args[0])
            self.assertIn('balloons', run.call_args.args[0])
            tweaks.prepare([], {'taskbar'}, run)
            self.assertEqual(run.call_args.args[0][-1], 'true')

if __name__ == '__main__':
    unittest.main()
