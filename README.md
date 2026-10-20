# ui-design-router

面向网页和 App 的设计工作流。2.1 增加从内部报表到对外产品的呈现方法，以真实对象、可理解的内容与连续操作检验设计；旧版的特定风格数值仍只作可选诊断。

入口是 [SKILL.md](SKILL.md)。[设计决定](docs/design.md) 说明改造范围；[验证记录](docs/validation.md) 说明检查结果及尚未验证的部分。

本轮实际案例：[项目雷达交互原型](examples/project-radar/index.html)、[案例说明](examples/project-radar/README.md)、[2.1 验证记录](docs/validation-2.1.md)。这是独立原型，不替换原报告站。

## Git 维护

这是独立本地仓库，未配置远端。

- `baseline-v1.1.1`：从原安装目录复制的原始版本。
- `v2.0.0`：首次流程重构。
- `v2.1.0`：基于报表式页面失败反馈，补产品表达方法和可运行案例。
- `v2.1.1`：纠正案例的产品目标偏移，保留商业判断所需的机制与趋势。
- `v2.1.2`：首次真实读图后替换占位素材，补充素材与历史数据的区分；修改后复查状态见验证记录。
- 后续直接在本仓库修改，用 `git diff` 审阅，按目的提交；安装切换后不需要复制同步。

```sh
git log --oneline --decorate
git diff baseline-v1.1.1 v2.0.0 -- SKILL.md references
```

## 切换现有安装

本机 Qoder 的 `~/.qoder/skills/ui-design-router` 已链接到 `~/.agents/skills/ui-design-router`，后者现在指向本 Git 仓库；修改仓库即可由原入口读取。其他使用该共享路径的工具也会读取新版。

2.0 的安装脚本曾把备份留在 skill 扫描目录内，导致旧版也被发现为同名 skill。2.1 将新备份放入 `~/.agents/skill-backups/`；对已安装的链接，会把旧备份迁移出去，完整保留文件。当前会话不能写该目录，请在普通终端从本仓库运行：

```sh
python3 scripts/install.py
python3 scripts/install.py --apply
```

第一条只预览；第二条执行并打印备份路径。首次安装也可用这两条命令。重复执行不会重复搬移。脚本不会删除备份，不覆盖其他符号链接；建立链接失败时恢复原目录。仅依赖 Python 标准库。

保持此仓库路径稳定；在新 Qoder 会话里读取 `ui-design-router`，确认版本为 2.1.2，且不再出现备份目录中的旧入口。旧会话可能仍持有旧指令。没有自动新增其他工具的发现入口。

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
