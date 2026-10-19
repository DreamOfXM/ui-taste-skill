# ui-design-router

面向网页和 App 的设计工作流。2.0 将核心任务、视觉方向、信息组织、交互体验和用户品味纳入同一流程；旧版的特定风格数值改为可选诊断。

入口是 [SKILL.md](SKILL.md)。[设计决定](docs/design.md) 说明改造范围；[验证记录](docs/validation.md) 说明检查结果及尚未验证的部分。

## Git 维护

这是独立本地仓库，未配置远端。

- `baseline-v1.1.1`：从原安装目录复制的原始版本。
- `v2.0.0`：此次重构版本。
- 后续直接在本仓库修改，用 `git diff` 审阅，按目的提交；安装切换后不需要复制同步。

```sh
git log --oneline --decorate
git diff baseline-v1.1.1 v2.0.0 -- SKILL.md references
```

## 切换现有安装

本机 Qoder 的 `~/.qoder/skills/ui-design-router` 已链接到 `~/.agents/skills/ui-design-router`。切换脚本将后者的原目录保留为带时间戳的备份，再链接到此 Git 仓库；Qoder 现有链接不变。其他使用该共享路径的工具也会读取新版。

本次编辑会话没有写入共享安装目录的权限，所以仓库完成不等于已切换。请在普通终端从本仓库运行：

```sh
python3 scripts/install.py
python3 scripts/install.py --apply
```

第一条只预览；第二条执行并打印备份路径。重复执行不会重复搬移。脚本不会删除备份，不覆盖其他符号链接；建立链接失败时恢复原目录。仅依赖 Python 标准库。

切换后保持此仓库路径稳定；在新 Qoder 会话里读取 `ui-design-router`，确认版本为 2.0.0。旧会话可能仍持有旧指令。没有自动新增其他工具的发现入口。

## 恢复原安装

把下面的路径替换为切换时打印的实际备份路径：

```sh
python3 scripts/install.py --restore /完整路径/ui-design-router.backup-时间戳
python3 scripts/install.py --restore /完整路径/ui-design-router.backup-时间戳 --apply
```

恢复只替换本脚本指向仓库的链接，Git 仓库和提交历史均保留。审阅旧内容也可以直接 `git show baseline-v1.1.1:SKILL.md`，无需切换安装。

## 验证

```sh
python3 -m unittest discover -s tests -v
```

测试在临时目录检查安装预览、切换、重复执行、恢复及失败回滚，不操作真实安装目录。文档与行为检查见验证记录；实际审美效果仍需真实页面和用户反馈验证。
