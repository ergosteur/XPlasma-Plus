"""Plasma's own lock screen gets XP's Welcome screen, so its white text stays readable."""
import sys, tempfile, unittest
from pathlib import Path
from unittest.mock import Mock
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import lockscreen


class LockWallpaper(unittest.TestCase):
    def test_welcome_background_is_set_without_touching_plasma(self):
        run = Mock()
        with tempfile.TemporaryDirectory() as d:
            home = Path(d)
            lockscreen.apply(home, home / 'templates', 'kwriteconfig6', run, log=Mock())
            calls = [c.args[0] for c in run.call_args_list]
            self.assertTrue(all(c[:3] == ['kwriteconfig6', '--file', 'kscreenlockerrc'] for c in calls))
            image = home / '.local/share/xplasma/assets/wallpapers/xp-welcome-lock.png'
            try:
                import PIL  # noqa: F401
            except ImportError:
                self.assertIn('org.kde.color', calls[0])
                return
            self.assertTrue(image.is_file())
            self.assertEqual(calls[1][-1], image.as_uri())
            self.assertFalse((home / '.local/share/plasma/shells').exists())   # no copies of Plasma's QML
            from PIL import Image
            img = Image.open(image)
            self.assertEqual(img.getpixel((10, 10)), (0x00, 0x30, 0x9c))           # top band
            self.assertEqual(img.getpixel((960, 540)), lockscreen.WELCOME_BLUE)     # the blue

    def test_only_with_the_wallpaper_and_without_the_xp_lock_screen(self):
        text = (ROOT / 'backend.py').read_text()
        self.assertIn("if 'wallpaper' in selected and 'lock' not in selected:lock_screen_wallpaper(home,state)", text)


if __name__ == '__main__':
    unittest.main()
