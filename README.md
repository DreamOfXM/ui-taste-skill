# UI Taste Skill

**给支持 Agent Skills 的编程助手用的 UI 设计 Skill。它在写代码前先比较视觉方向，把选定方向写成可执行的约束，最后在真实运行的界面上验收——而不是直接往页面里堆通用卡片和渐变。**

覆盖网页、桌面软件、移动 App 与 Web 工作台；新界面、整体改版、按参考图还原、局部精修和纯评审都能用。

[快速开始](#快速开始) · [试一个任务](#试一个任务) · [查看示范](#查看示范)

![字间展陈方向：六组字体标本以大字号并排构图，右侧详情提供试写与收藏](assets/reference-evidence/studio-gallery-desktop.png)

*「字间」教学示范的展陈方向：同一组六份字体标本，由字号、行形和疏密共同构图。同样的内容还有[工作面方向](assets/reference-evidence/studio-instrument-desktop.png)：目录压紧、当前标本放大，重心从浏览移到检查。两个方向都是预先完成的页面，不是模型即时生成的效果。*

## 一次任务里发生什么

- **先定方向，再动代码。** 开放式改版先给出两张构图、材料或对象表达真正不同的关键屏，而不是换一组主题色就交稿。
- **方向写成能执行的约束。** 选定后填一张设计卡（对象与边界、构图主角、字体与材料、关键状态、窄屏转换），把实现细节固定下来，不必猜“高级感”指什么。
- **原稿就是规格。** 给了参考图就按构图与排印关系还原，不添加原图没有的元素；局部精修不会变成全站重做。
- **交付前查看实际界面。** 运行页面并读图，把“能操作、不报错”和“好看、有主张”分开验收。

具体流程见 [SKILL.md](SKILL.md)；需要深入时再读[生成方法](references/generation.md)、[参考适配](references/visual-calibration.md)、[评审方法](references/review.md)。

## 快速开始

这是给编程助手读取的指令与参考资料目录，不是可单独运行的设计软件。仓库根目录就是技能根目录：克隆完整仓库，不要只复制 `SKILL.md`，执行中还会读取 `references/` 和 `assets/`。

需要 Git，以下命令在 macOS / Linux 终端执行；按你使用的客户端选择一条路径。

### 在 Qoder 中使用

在终端运行：

```sh
mkdir -p "$HOME/.qoder/skills"
git clone https://github.com/DreamOfXM/ui-taste-skill.git "$HOME/.qoder/skills/ui-taste-skill"
```

开启新会话，可用 Skill 列表中出现 `ui-taste-skill` 即装好，也可以直接输入 `/ui-taste-skill 评审当前页面，先不要修改代码`。

### 在 Claude Code 中使用

用户级安装让本机所有项目可用；只给一个项目用时，把同样的目录放到该项目的 `.claude/skills/ui-taste-skill/`。用户级安装：

```sh
mkdir -p "$HOME/.claude/skills"
git clone https://github.com/DreamOfXM/ui-taste-skill.git "$HOME/.claude/skills/ui-taste-skill"
```

在任意项目中开启新会话，先问 `What skills are available?`，列表里出现 `ui-taste-skill` 后，可以直接输入 `/ui-taste-skill 评审当前页面，先不要修改代码`。目录位置与显式调用方式见 [Claude Code 官方说明](https://code.claude.com/docs/en/skills#where-skills-live)。

### 在 Codex 中使用

Codex 的 skill 安装脚本默认把技能放进 `$CODEX_HOME/skills`，未设置 `CODEX_HOME` 时就是 `~/.codex/skills`（见 [openai/codex 仓库里的 skill-installer 说明](https://github.com/openai/codex/blob/main/codex-rs/skills/src/assets/samples/skill-installer/SKILL.md)）。在终端运行：

```sh
mkdir -p "$HOME/.codex/skills"
git clone https://github.com/DreamOfXM/ui-taste-skill.git "$HOME/.codex/skills/ui-taste-skill"
```

设置过 `CODEX_HOME` 时，把上面两个路径换成 `$CODEX_HOME/skills`。开启新会话后输入 `$ui-taste-skill`，应能指名这个技能；没有反应时先确认目录是否正确、克隆是否完整。

### 安装时注意

- 目标目录已存在时不要覆盖：它已经指向本仓库或其他克隆就保留现状；是无关目录就先移开或备份再克隆。
- 技能列表里没有出现，先确认克隆的是完整仓库、放的是所用客户端真正扫描的目录；旧会话可能需要重开。
- 加载技能不需要 Python 或 Node.js，只有本地打开示范页面、运行维护检查时才需要。
- 更新时在安装目录执行 `git pull`；不再使用时删除该目录即可。

## 试一个任务

在已有项目中，附上要修改的页面、截图或参考图，再用自然语言提出任务。例如：

**整体改版，先比较方向**

```text
请使用 ui-taste-skill 改版当前页面，保留已有功能。
先用真实内容比较两个视觉方向，再将选定方向落到代码中。
```

**按参考图还原，不擅自加戏**

```text
请使用 ui-taste-skill，按这张参考图重做当前页面。
保留参考图的构图与排印关系，不增加原图没有的装饰。
```

**只做评审，不修改代码**

```text
请使用 ui-taste-skill 评审这张截图，先不要修改代码。
指出最影响整体观感的三个问题，给出具体的修改方向。
```

开放式设计会先探索方向；明确原稿或局部精修不强制重做全局。

## 查看示范

这些是随仓库提供的离线 HTML 页面，不是在线产品。GitHub 中的 HTML 文件链接展示源码；要在浏览器里体验，需要 Python 3，在已安装的仓库目录运行：

```sh
cd ~/.qoder/skills/ui-taste-skill   # 换成实际安装目录，如 ~/.claude/skills/ui-taste-skill
python3 -m http.server 8788 --bind 127.0.0.1
```

打开服务后，访问 `http://127.0.0.1:8788/` 加上表中路径；这些地址只在本地服务运行时有效。结束后在终端按 `Ctrl+C` 停止。

| 示范 | 看什么 | 路径 |
| --- | --- | --- |
| 字间方向工作室 | 同一组标本的展陈 / 工作面两种构图，可切换、筛选与试写 | `assets/variant-board.html` |
| 索引工作台 | 列表与详情、搜索、收藏及窄屏返回 | `assets/reference-workbench.html` |
| 间阅读刊物 | 中文排印、阅读节奏、文章与主题筛选 | `assets/reference-editorial.html` |
| 软件关系精修实验室 | 比较同内容的排布，检查列表、详情与偏好 | `assets/app-craft-lab.html` |
| 项目雷达 | 一个真实项目的改版原型：旧版被反馈“更像统计表”，现在让项目用途先被看见 | `examples/project-radar/index.html` |

前四个是为演示设计关系制作的原创教学页面，内容虚构。项目雷达是真实项目的原型实验，用的是 2026-10-19 的公开数据快照；它只验证浏览、筛选与详情这条路径，不是上线产品。页面使用本地字体，字体外观可能随系统变化。每个示范的设计关系见[视觉拆解](references/visual-examples.md)。

## 使用边界

Skill 提供设计与验证方法，不保证每个模型都能稳定产出优秀界面。仓库内的示范都是网页，原生 App 界面仍需在目标平台验收；执行环境无法读图时，视觉与交互结论也需要补验。

<details>
<summary>维护者：运行验证</summary>

在仓库根目录运行安装与包检查，需要 Python 3.9+，仅使用标准库：

```sh
python3 -B -m unittest discover -s tests -v
```

检查覆盖安装切换、恢复、元数据、文档资源与已有截图的源码哈希；不操作真实安装目录，也不评价审美。

重新生成示范的浏览器证据需要 Node.js 18+ 与 Chrome / Chromium：

```sh
node scripts/verify-app-craft.cjs
node scripts/verify-references.cjs
```

找不到浏览器时通过 `CHROME_BIN` 指定。脚本使用隔离的临时浏览器配置，会更新仓库内的报告和截图；更新后还需实际读图。评估范围与方法见[效果验证](references/evaluation.md)。

</details>

## 许可

采用 [MIT 许可证](LICENSE)：可以用于商业或非商业项目，也可以修改和再分发，需保留版权与许可声明。
