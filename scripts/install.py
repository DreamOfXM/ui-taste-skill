#!/usr/bin/env python3
"""Preview or switch the shared skill directory to this Git checkout."""

import argparse
from datetime import datetime
import json
from pathlib import Path
import sys


def check_skill(path):
    if not (path / 'SKILL.md').is_file():
        raise ValueError(f'缺少 SKILL.md: {path}')
    meta = json.loads((path / '_meta.json').read_text())
    if meta.get('name') != 'ui-design-router':
        raise ValueError(f'不是 ui-design-router: {path}')


def backup_root(target):
    # Keep old SKILL.md files outside the directory scanned for active skills.
    return target.parent.parent / 'skill-backups'


def archive_legacy(target, apply=False):
    for old in sorted(target.parent.glob(target.name + '.backup-*')):
        if old.is_symlink() or not old.is_dir():
            continue
        check_skill(old)
        destination = backup_root(target) / old.name
        if destination.exists() or destination.is_symlink():
            raise ValueError(f'归档目标已存在，保持原备份: {destination}')
        print(f'将旧备份移出 skill 扫描目录: {old} -> {destination}')
        if apply:
            destination.parent.mkdir(parents=True, exist_ok=True)
            old.rename(destination)


def install(repo, target, apply=False):
    check_skill(repo)
    if not target.is_symlink() and (repo.resolve() == target.resolve()
                                   or target.resolve() in repo.resolve().parents):
        raise ValueError('仓库不能位于待替换的安装目录内，保持原状。')
    if target.is_symlink():
        if target.resolve() == repo.resolve():
            archive_legacy(target, apply)
            print(f'已使用本仓库，无需重复切换: {target}')
            if not apply:
                print('仅预览，未修改；添加 --apply 才执行备份归档。')
            return None
        raise ValueError(f'安装位置是其他符号链接，保持原状: {target}')
    if not target.parent.is_dir():
        raise ValueError(f'安装父目录不存在: {target.parent}')
    backup = None
    if target.exists():
        check_skill(target)
        stamp = datetime.now().strftime('%Y%m%d-%H%M%S-%f')
        backup = backup_root(target) / (target.name + '.backup-' + stamp)
        if backup.exists() or backup.is_symlink():
            raise ValueError(f'备份位置已存在: {backup}')
        print(f'备份原目录: {target} -> {backup}')
    print(f'建立链接: {target} -> {repo}')
    if not apply:
        print('仅预览，未修改；添加 --apply 才执行。')
        return backup
    if backup:
        backup.parent.mkdir(parents=True, exist_ok=True)
        target.rename(backup)
    try:
        target.symlink_to(repo, target_is_directory=True)
    except OSError:
        if backup:
            backup.rename(target)
        raise
    print('切换完成。已打开的会话可能保留旧指令，请在新会话中验证。')
    if backup:
        print(f'备份保留在: {backup}')
    archive_legacy(target, apply=True)
    return backup


def restore(repo, target, backup, apply=False):
    backup = backup.expanduser().absolute()
    if (backup.parent not in (target.parent, backup_root(target)) or backup.is_symlink()
            or not backup.name.startswith(target.name + '.backup-')):
        raise ValueError('恢复目录必须是 skill-backups 内或旧安装位置旁的原始备份目录。')
    check_skill(backup)
    if not target.is_symlink() or target.resolve() != repo.resolve():
        raise ValueError('当前安装位置不是指向本仓库的链接，保持原状。')
    print(f'恢复原目录: {backup} -> {target}；Git 仓库保留')
    if not apply:
        print('仅预览，未修改；添加 --apply 才执行。')
        return
    target.unlink()
    try:
        backup.rename(target)
    except OSError:
        target.symlink_to(repo, target_is_directory=True)
        raise
    print('恢复完成。')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apply', action='store_true', help='执行切换；默认只预览')
    parser.add_argument('--restore', type=Path, help='从切换时保留的备份恢复')
    args = parser.parse_args()
    repo = Path(__file__).resolve().parents[1]
    target = Path.home() / '.agents' / 'skills' / 'ui-design-router'
    try:
        if args.restore:
            restore(repo, target, args.restore, args.apply)
        else:
            install(repo, target, args.apply)
    except (OSError, ValueError) as exc:
        print(f'未完成: {exc}', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
