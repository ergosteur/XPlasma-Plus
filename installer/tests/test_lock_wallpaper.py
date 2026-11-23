"""Plasma's own lock screen gets XP's Bliss, so its white text stays readable."""
import ast, tempfile, unittest
from pathlib import Path
from unittest.mock import Mock
ROOT = Path(__file__).resolve().parents[1]


class LockWallpaper(unittest.TestCase):
    def load(self):
        tree = ast.parse((ROOT / 'backend.py').read_text())
        node = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'lock_screen_wallpaper')
        ns = dict(Path=Path, config=Mock(), run=Mock(), detect=lambda: {'writer': 'kwriteconfig6'})
        exec(compile(ast.Module(body=[node], type_ignores=[]), 'backend.py', 'exec'), ns)
        return ns

    def test_bliss_becomes_the_lock_screen_wallpaper(self):
        ns = self.load()
        with tempfile.TemporaryDirectory() as d:
            home = Path(d)
            ns['lock_screen_wallpaper'](home)   # no Bliss installed: nothing changes
            ns['config'].assert_not_called()
            bliss = home / '.local/share/xplasma/assets/wallpapers/Bliss.jpg'
            bliss.parent.mkdir(parents=True)
            bliss.write_bytes(b'jpg')
            ns['lock_screen_wallpaper'](home)
            ns['config'].assert_called_with('kscreenlockerrc', 'Greeter', 'WallpaperPlugin', 'org.kde.image')
            args = ns['run'].call_args.args[0]
            self.assertEqual(args[-1], bliss.as_uri())
            self.assertIn('org.kde.image', args)

    def test_only_with_the_wallpaper_and_without_the_xp_lock_screen(self):
        text = (ROOT / 'backend.py').read_text()
        self.assertIn("if 'wallpaper' in selected and 'lock' not in selected:lock_screen_wallpaper(home)", text)


if __name__ == '__main__':
    unittest.main()
