import ast,json,re,tempfile,unittest
from pathlib import Path
BASE=Path(__file__).resolve().parents[1]
class TaskbarDefaultsTests(unittest.TestCase):
 def test_exactly_three_launchers_with_optional_ie6_browser(self):
  tree=ast.parse((BASE/'backend.py').read_text());function=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='taskbar_defaults')
  commands=[];restarts=[]
  def run(args,capture=False,check=True):
   commands.append(args)
   return 'xplasma-applet-order 2 26;30;29;27\n' if capture else 0   # (as Plasma before 6.6 answers)
  def restart(while_stopped=None):
   restarts.append(len(commands));while_stopped()
  import shutil
  ns={'Path':Path,'json':json,'shutil':shutil,'kdbus':lambda:'qdbus','run':run,'log':lambda m:None,
      'detect':lambda:{'systemd':True},'restart_plasmashell':restart}
  exec(compile(ast.Module(body=[function],type_ignores=[]),'backend.py','exec'),ns)
  with tempfile.TemporaryDirectory() as tmp:
   home=Path(tmp);entries=home/'.local/share/applications';entries.mkdir(parents=True)
   for name in ['systemsettings.desktop','org.kde.dolphin.desktop','firefox.desktop','firefox-esr-ie6.desktop']:(entries/name).write_text('[Desktop Entry]\n')
   for selected,browser in [({'firefox'},'firefox-esr-ie6.desktop'),(set(),'firefox.desktop')]:
    ns['taskbar_defaults'](home,selected)
    script=next(c[-1] for c in reversed(commands) if c[-2].endswith('evaluateScript'));urls=json.loads(re.search(r'writeConfig\("launcherUrls",(\[.*?\])\)',script).group(1))
    self.assertEqual(urls,[(entries/name).as_uri() for name in ['systemsettings.desktop','org.kde.dolphin.desktop',browser]])
    self.assertIn('quick.index=start.index+1',script)
    self.assertIn('writeConfig("launchers",[])',script)
    # Plasma before 6.6: the panel's AppletOrder places it, read when the shell restarts.
    self.assertIn('print("xplasma-applet-order "+p.id',script)
    # ...written into the panel's config while the shell is stopped.
    self.assertEqual(commands[-1][-7:],['--group','2','--group','General','--key','AppletOrder','26;30;29;27'])
   self.assertEqual(len(restarts),2)
if __name__=='__main__':unittest.main()
