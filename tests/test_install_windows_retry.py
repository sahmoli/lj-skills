import importlib.util
from pathlib import Path
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("retry_installer", ROOT / "scripts/install_skills.py")
installer = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(installer)


class WindowsCopyRetryTests(unittest.TestCase):
    def windows_error(self, number):
        error = OSError("simulated Windows filesystem error")
        error.winerror = number
        return error

    def test_transient_sharing_error_is_retried_then_succeeds(self):
        with patch.object(installer.os, "name", "nt"), \
                patch.object(installer.os, "replace", side_effect=[self.windows_error(32), None]) as move, \
                patch.object(installer.time, "sleep") as sleep:
            installer.replace_staged_directory("staged", "target")
            self.assertEqual(move.call_count, 2)
            sleep.assert_called_once_with(0.05)

    def test_unrelated_error_is_preserved_without_retry(self):
        with patch.object(installer.os, "name", "nt"), \
                patch.object(installer.os, "replace", side_effect=self.windows_error(3)) as move, \
                patch.object(installer.time, "sleep") as sleep:
            with self.assertRaises(OSError):
                installer.replace_staged_directory("staged", "target")
            move.assert_called_once()
            sleep.assert_not_called()

    def test_persistent_access_error_has_a_bounded_retry(self):
        with patch.object(installer.os, "name", "nt"), \
                patch.object(installer.os, "replace", side_effect=self.windows_error(5)) as move, \
                patch.object(installer.time, "sleep") as sleep:
            with self.assertRaises(OSError):
                installer.replace_staged_directory("staged", "target")
            self.assertEqual(move.call_count, 6)
            self.assertEqual(sleep.call_count, 5)


if __name__ == "__main__":
    unittest.main()
