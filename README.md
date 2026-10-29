# UI Taste Skill

[English](README.en.md) · 简体中文

让 AI 编程助手先确定界面的视觉方向，再把布局、排印与交互做完整。

[安装](#安装) · [试一个任务](#试一个任务) · [查看示范](#查看示范)

[![字间展陈方向：六组字体标本以大字号构图，右侧详情提供试写与收藏](assets/reference-evidence/studio-gallery-desktop.png)](assets/reference-evidence/studio-gallery-desktop.png)

「字间」教学示范：展陈方向用字号与疏密组织六份字体标本；同样内容的[工作面方向](assets/reference-evidence/studio-instrument-desktop.png)压紧目录、放大当前标本，把重心从浏览移到检查。

## 不只换一套主题色

- **先比较真正不同的方向**：新界面或开放式改版先探索构图、材料与内容表达，等你选定后再实现。
- **把方向变成具体约束**：用设计卡明确构图主角、字体与材料、关键状态和窄屏转换，让后续代码有据可依。
- **按原稿还原，按范围精修**：已有参考图就保留它的构图与排印关系；局部调整不自动扩大为全站改版，也不强制再做两个方向。
- **在运行的界面上验收**：实际操作并读图，分别检查功能与视觉，而不是用“编译通过”代替界面质量。

适用于网页、桌面软件、移动 App 与 Web 工作台的设计、改版和评审。

## 安装

这是供编程助手读取的指令与参考资料包，不是独立设计软件。README 提供中英两版，**技能指令与参考资料目前为中文**。

安装前查看 [SKILL.md](SKILL.md)、`references/` 及附带脚本，了解可能执行的代码与外部请求；安装完整包，不要只导入入口文件。已有同名技能时先核对来源、备份需要保留的修改，避免覆盖。

三个客户端共用一条 `skills` CLI 命令，安装的是同一个完整技能包。需要 **Node.js 22.20+** 和已安装的客户端，在终端任意目录运行：

```sh
npx skills add DreamOfXM/ui-taste-skill -g
```

按提示选择客户端，或用 `-a` 指定目标。`-g` 是用户级安装，所有项目可用；在目标项目目录去掉 `-g` 则只装到该项目。

- **Claude Code**（`-a claude-code`）：`~/.claude/skills/`；新会话输入 `/` 选择 `ui-taste-skill`
- **Codex**（`-a codex`）：`~/.agents/skills/`；新会话输入 `$ui-taste-skill`
- **Qoder Desktop**（`-a qoder`）：`~/.qoder/skills/`；新会话输入 `/` 选择 `ui-taste-skill`

装好后开启新会话；技能未出现时，确认包内包含 `SKILL.md` 和 `references/`、上面列出的安装目录正确，再重启客户端。没有 Node.js 22.20+ 时无法运行该命令，可下载[发布附件 ZIP](https://github.com/DreamOfXM/ui-taste-skill/releases/latest/download/ui-taste-skill.zip) 在 Qoder Desktop 的扩展面板导入，或把仓库复制到上面列出的安装目录。

维护：更新用 `npx skills update ui-taste-skill -g`，卸载用 `npx skills remove ui-taste-skill -g`；装到多个客户端时会提示选择目标，也可加 `-a`。其他支持 skills CLI 的客户端（Cursor、Gemini CLI、OpenCode 等）走同一条命令，目标名见[支持列表](https://github.com/vercel-labs/skills/blob/main/docs/agents.md)；安装器支持某个客户端，不等于本 Skill 已在该客户端验证。

## 试一个任务

在已有项目中按对应客户端的步骤选中技能，提供要修改的页面或截图，然后输入：

```text
请使用 ui-taste-skill 改版当前页面，
保留已有功能。
先用真实内容比较两个视觉方向，
等我确认后再写设计卡并落实到代码。
完成后运行页面并读图，
分别检查功能、视觉和窄屏状态。
```

第一次应得到两个可比较的方向，而不是立即收到整页实现。确认后，设计卡应明确布局、字体、关键状态和响应式处理；最终交付应包含实际运行与读图的检查结果。

按参考图还原时，附图并说明保留哪些关系；局部精修时，指明修改范围。如果只想评审，明确加上“先不要修改代码”。

## 查看示范

示范是随仓库提供的离线 HTML 页面。取得完整仓库或解压 ZIP 后，需要 Python 3；在仓库根目录或解压后的技能根目录运行：

```sh
python3 -m http.server 8788 --bind 127.0.0.1
```

服务开启后，在浏览器打开下列本地链接；结束后在终端按 `Ctrl+C` 停止。它们不是托管站点，本地服务未运行时无法访问。

- [字间方向工作室](http://127.0.0.1:8788/assets/variant-board.html)：同一组标本的展陈与工作面构图，可切换、筛选与试写。
- [索引工作台](http://127.0.0.1:8788/assets/reference-workbench.html)：列表与详情、搜索、收藏及窄屏返回。
- [间阅读刊物](http://127.0.0.1:8788/assets/reference-editorial.html)：中文排印、阅读节奏、文章与主题筛选。
- [软件关系精修实验室](http://127.0.0.1:8788/assets/app-craft-lab.html)：比较同内容的排布，检查列表、详情与偏好。
- [项目雷达](http://127.0.0.1:8788/examples/project-radar/index.html)：真实项目的改版原型，让项目用途先于统计信息被看见。

前四个是内容虚构的教学页面。项目雷达使用 2026-10-19 的公开数据快照，只覆盖浏览、筛选与详情，不是线上产品。页面使用本地字体，外观可能随系统变化。设计关系见[视觉拆解](references/visual-examples.md)。

## 使用边界与参考

Skill 提供设计与验证方法，不保证每个模型都能稳定产出优秀界面。仓库示范都是网页，原生 App 仍需在目标平台验收；执行环境无法读图时，视觉与交互结论需要补验。

以下指令与参考资料为中文：

- [完整技能指令](SKILL.md)
- [生成方法](references/generation.md)
- [参考适配](references/visual-calibration.md)
- [评审方法](references/review.md)

<details>
<summary>维护者：运行验证</summary>

在仓库根目录运行包检查，需要 Python 3.9+，仅使用标准库：

```sh
python3 -B -m unittest discover -s tests -v
```

检查覆盖安装切换、恢复、元数据、文档资源与已有截图的源码哈希；不操作真实安装目录，也不评价审美。

重新生成示范的浏览器证据需要 Node.js 18+ 与 Chrome / Chromium：

```sh
node scripts/verify-app-craft.cjs
node scripts/verify-references.cjs
```

找不到浏览器时通过 `CHROME_BIN` 指定。脚本使用隔离的临时浏览器配置，会更新仓库内的报告和截图；更新后仍需实际读图。范围与方法见[效果验证](references/evaluation.md)。

</details>

## 许可

作者：DreamOfXM。采用 [MIT 许可证](LICENSE)，允许商业或非商业使用、修改和再分发，需保留版权与许可声明。
