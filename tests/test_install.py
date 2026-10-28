import contextlib
import importlib.util
import io
import json
import shutil
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch


spec = importlib.util.spec_from_file_location(
    'skill_install', Path(__file__).resolve().parents[1] / 'scripts' / 'install.py')
installer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(installer)


class InstallTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        root = Path(self.temp.name).resolve()
        self.repo = root / 'repo'
        self.target = root / 'skills' / 'ui-taste-skill'
        for path, text in [(self.repo, 'new'), (self.target, 'old')]:
            path.mkdir(parents=True)
            (path / 'SKILL.md').write_text(text)
            (path / '_meta.json').write_text(json.dumps({'name': 'ui-taste-skill'}))
        self.output = contextlib.redirect_stdout(io.StringIO())
        self.output.__enter__()
        self.addCleanup(self.output.__exit__, None, None, None)

    def test_preview_changes_nothing(self):
        before = sorted(p.relative_to(self.target.parent) for p in self.target.parent.rglob('*'))
        backup = installer.install(self.repo, self.target)
        self.assertFalse(backup.exists())
        self.assertFalse(self.target.is_symlink())
        self.assertEqual(before, sorted(p.relative_to(self.target.parent) for p in self.target.parent.rglob('*')))

    def test_install_repeat_and_restore(self):
        backup = installer.install(self.repo, self.target, apply=True)
        self.assertEqual(self.target.resolve(), self.repo)
        self.assertEqual((self.target / 'SKILL.md').read_text(), 'new')
        self.assertEqual((backup / 'SKILL.md').read_text(), 'old')
        self.assertIsNone(installer.install(self.repo, self.target, apply=True))
        self.assertEqual(len(list(installer.backup_root(self.target).glob('*.backup-*'))), 1)
        self.assertEqual(list(self.target.parent.glob('*.backup-*')), [])
        installer.restore(self.repo, self.target, backup)
        self.assertTrue(self.target.is_symlink())
        installer.restore(self.repo, self.target, backup, apply=True)
        self.assertFalse(self.target.is_symlink())
        self.assertEqual((self.target / 'SKILL.md').read_text(), 'old')
        self.assertTrue(self.repo.is_dir())

    def test_qoder_link_follows_switch(self):
        qoder = Path(self.temp.name) / 'qoder-ui-taste-skill'
        qoder.symlink_to(self.target, target_is_directory=True)
        installer.install(self.repo, self.target, apply=True)
        self.assertEqual(qoder.resolve(), self.repo)
        self.assertEqual((qoder / 'SKILL.md').read_text(), 'new')

    def test_link_failure_restores_old_directory(self):
        with patch.object(Path, 'symlink_to', side_effect=PermissionError('denied')):
            with self.assertRaises(PermissionError):
                installer.install(self.repo, self.target, apply=True)
        self.assertFalse(self.target.is_symlink())
        self.assertEqual((self.target / 'SKILL.md').read_text(), 'old')
        self.assertEqual(list(self.target.parent.glob('*.backup-*')), [])

    def test_restore_failure_relinks_repository(self):
        backup = installer.install(self.repo, self.target, apply=True)
        with patch.object(Path, 'rename', side_effect=PermissionError('denied')):
            with self.assertRaises(PermissionError):
                installer.restore(self.repo, self.target, backup, apply=True)
        self.assertEqual(self.target.resolve(), self.repo)
        self.assertEqual((backup / 'SKILL.md').read_text(), 'old')

    def test_other_symlink_is_preserved(self):
        other = self.target.with_name('other')
        self.target.rename(other)
        self.target.symlink_to(other, target_is_directory=True)
        with self.assertRaises(ValueError):
            installer.install(self.repo, self.target, apply=True)
        self.assertEqual(self.target.resolve(), other)

    def test_restore_rejects_nonbackup(self):
        installer.install(self.repo, self.target, apply=True)
        with self.assertRaises(ValueError):
            installer.restore(self.repo, self.target, self.repo, apply=True)
        self.assertEqual(self.target.resolve(), self.repo)

    def test_restore_preserves_replaced_installation(self):
        backup = installer.install(self.repo, self.target, apply=True)
        self.target.unlink()
        self.target.mkdir()
        with self.assertRaises(ValueError):
            installer.restore(self.repo, self.target, backup, apply=True)
        self.assertTrue(backup.is_dir())
        self.assertFalse(self.target.is_symlink())

    def test_install_rejects_self_replacement(self):
        with self.assertRaises(ValueError):
            installer.install(self.target, self.target, apply=True)
        self.assertEqual((self.target / 'SKILL.md').read_text(), 'old')

    def test_install_rejects_unrelated_directory(self):
        (self.target / '_meta.json').write_text(json.dumps({'name': 'other'}))
        with self.assertRaises(ValueError):
            installer.install(self.repo, self.target, apply=True)
        self.assertEqual((self.target / 'SKILL.md').read_text(), 'old')

    def test_existing_link_archives_legacy_backup_outside_discovery(self):
        legacy = self.target.with_name(self.target.name + '.backup-legacy')
        shutil.copytree(self.target, legacy)
        installer.install(self.repo, self.target, apply=True)
        archived = installer.backup_root(self.target) / legacy.name
        self.assertFalse(legacy.exists())
        self.assertEqual((archived / 'SKILL.md').read_text(), 'old')
        # Recreate a legacy backup to exercise upgrade of an existing symlink.
        shutil.copytree(archived, legacy)
        archived.rename(archived.with_name(archived.name + '-previous'))
        installer.install(self.repo, self.target)
        self.assertTrue(legacy.is_dir())
        installer.install(self.repo, self.target, apply=True)
        self.assertFalse(legacy.exists())
        self.assertEqual((archived / 'SKILL.md').read_text(), 'old')
        self.assertEqual(self.target.resolve(), self.repo)


if __name__ == '__main__':
    unittest.main()
