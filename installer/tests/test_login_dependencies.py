import importlib.util,unittest
from pathlib import Path
spec=importlib.util.spec_from_file_location('login_dependencies',Path(__file__).resolve().parents[1]/'dependencies.py');deps=importlib.util.module_from_spec(spec);spec.loader.exec_module(deps)
class LoginDependencies(unittest.TestCase):
 def test_prebuilt_installs_still_include_welcome_status_bindings(self):
  for cached in (True,False):
   packages=deps.packages('apt',{'desktop','login'},native_ready=cached)
   self.assertIn('python3-pyside6.qtcore',packages)
   self.assertIn('python3-pyside6.qtdbus',packages)
 def test_login_dependency_not_required_for_desktop_only(self):
  self.assertNotIn('python3-pyside6.qtdbus',deps.packages('apt',{'desktop'},native_ready=True))
 def test_dnf_keeps_an_installed_greeter_display_server(self):
  # Fedora Budgie's sddm-wayland-miriway conflicts with sddm-wayland-plasma.
  from unittest.mock import patch
  for installed,expected in ((True,False),(False,True)):
   calls=[]
   with patch.object(deps,'greeter_displayserver_installed',return_value=installed):
    deps.install('dnf',{'login'},calls.append,native_ready=True)
   self.assertEqual('sddm-wayland-plasma' in calls[0],expected)
   self.assertIn('sddm',calls[0])
if __name__=='__main__':unittest.main()
