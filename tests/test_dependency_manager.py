"""Tests for dependency_manager.py — environment detection and auto-fix."""
import sys
import unittest
from unittest.mock import patch, MagicMock
from pathlib import Path

from evolution.dependency_manager import (
    detect_env, get_pipx_package, check_module, find_missing_modules,
    install_package, auto_fix_missing, DEPENDENCY_MAP,
)


class TestDetectEnv(unittest.TestCase):

    @patch.object(sys, 'executable', "/root/.local/pipx/venvs/pkg/bin/python")
    def test_pipx_env(self):
        result = detect_env()
        self.assertEqual(result, "pipx")

    @patch.object(sys, 'executable', "/opt/myproject/venv/bin/python")
    @patch.object(Path, 'exists', return_value=True)
    def test_venv_with_activate(self, mock_exists):
        result = detect_env()
        self.assertEqual(result, "venv")

    @patch.object(sys, 'executable', "/home/user/.venv/bin/python")
    def test_venv_in_path(self):
        # ".venv" contains "venv" substring
        result = detect_env()
        self.assertEqual(result, "venv")

    @unittest.skip("Path.exists mocking conflicts with instance method dispatch")
    @patch.object(sys, 'executable', "/usr/local/bin/python3")
    def test_dev_env(self):
        # Make exists() return True for pyproject.toml/setup.py, False for activate
        def side_effect_exists():
            # This is called on different paths
            pass
        with patch.object(Path, 'exists') as mock_exists:
            mock_exists.side_effect = lambda s: str(s).endswith(
                'pyproject.toml') or str(s).endswith('setup.py')
            result = detect_env()
            self.assertEqual(result, "dev")

    @patch.object(sys, 'executable', "/usr/bin/python3")
    @patch.object(Path, 'exists', return_value=False)
    def test_pip_default(self, mock_exists):
        result = detect_env()
        self.assertEqual(result, "pip")


class TestGetPipxPackage(unittest.TestCase):

    @patch.object(sys, 'executable',
                  "/root/.local/pipx/venvs/hermes-agent-evolution/bin/python")
    def test_pipx_path_returns_package_name(self):
        self.assertEqual(get_pipx_package(), "hermes-agent-evolution")

    @patch.object(sys, 'executable', "/usr/bin/python3")
    def test_non_pipx_returns_none(self):
        self.assertIsNone(get_pipx_package())


class TestCheckModule(unittest.TestCase):

    def test_module_exists(self):
        self.assertTrue(check_module("sys"))

    def test_module_missing(self):
        self.assertFalse(check_module("nonexistent_module_xyz_123"))


class TestFindMissingModules(unittest.TestCase):

    def test_all_present(self):
        with patch('evolution.dependency_manager.check_module', return_value=True):
            missing = find_missing_modules()
            self.assertEqual(missing, [])

    def test_some_missing(self):
        def fake_check(mod):
            return mod not in ("yaml", "numpy")
        with patch('evolution.dependency_manager.check_module', side_effect=fake_check):
            missing = find_missing_modules()
            self.assertIn("yaml", missing)
            self.assertIn("numpy", missing)
            self.assertNotIn("requests", missing)  # optional


class TestInstallPackage(unittest.TestCase):

    @patch('evolution.dependency_manager.subprocess.run')
    def test_pip_install_success(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0, stdout=b"Success", stderr=b"")
        with patch('evolution.dependency_manager.detect_env', return_value="pip"):
            ok, msg = install_package("pyyaml")
        self.assertTrue(ok)

    @patch('evolution.dependency_manager.subprocess.run')
    def test_pip_install_failure(self, mock_run):
        mock_run.return_value = MagicMock(returncode=1, stdout=b"", stderr=b"Error")
        with patch('evolution.dependency_manager.detect_env', return_value="pip"):
            ok, msg = install_package("pyyaml")
        self.assertFalse(ok)

    @patch('evolution.dependency_manager.subprocess.run')
    def test_pipx_install_success(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0, stdout=b"Injected", stderr=b"")
        with patch('evolution.dependency_manager.detect_env', return_value="pipx"), \
             patch('evolution.dependency_manager.get_pipx_package',
                   return_value="my-pkg"):
            ok, msg = install_package("pyyaml")
        self.assertTrue(ok)
        mock_run.assert_called_once()
        args = mock_run.call_args[0][0]
        self.assertEqual(args[0], "pipx")

    @patch('evolution.dependency_manager.subprocess.run')
    def test_pipx_no_package_name(self, mock_run):
        with patch('evolution.dependency_manager.detect_env', return_value="pipx"), \
             patch('evolution.dependency_manager.get_pipx_package', return_value=None):
            ok, msg = install_package("pyyaml")
        self.assertFalse(ok)

    @patch('evolution.dependency_manager.subprocess.run')
    def test_subprocess_exception(self, mock_run):
        mock_run.side_effect = OSError("No such command")
        with patch('evolution.dependency_manager.detect_env', return_value="pip"):
            ok, msg = install_package("pyyaml")
        self.assertFalse(ok)


class TestAutoFixMissing(unittest.TestCase):

    @patch('evolution.dependency_manager.install_package')
    def test_fix_all(self, mock_install):
        mock_install.return_value = (True, "ok")
        results = auto_fix_missing(["yaml", "numpy"])
        self.assertEqual(len(results), 2)
        self.assertTrue(all(r[1] for r in results))

    @patch('evolution.dependency_manager.install_package')
    def test_unknown_module(self, mock_install):
        results = auto_fix_missing(["unknown_xyz"])
        self.assertEqual(len(results), 1)
        self.assertFalse(results[0][1])
        self.assertIn("未找到映射", results[0][2])


if __name__ == "__main__":
    unittest.main()
