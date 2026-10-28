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

这是给编程助手读取的指令与参考资料目录，不是可单独运行的设计软件；仓库根目录就是技能根目录。

### 在 Qoder 中安装

1. 下载 [ui-taste-skill.zip](https://github.com/DreamOfXM/ui-taste-skill/releases/latest/download/ui-taste-skill.zip)。
2. 打开 Extensions → Skills，选择 Add Skills → Upload Skill，导入这个 ZIP。
3. Installed 里出现 `ui-taste-skill` 后，在新任务中输入 `/` 选中它，再接上你的需求。

导入前建议浏览一遍 `SKILL.md` 与 `references/`：其中的脚本和外部请求都要按作者提供的可执行代码对待。

### 在 Claude Code 中安装

本仓库同时是一个 Claude Code 插件市场。在 Claude Code 会话里输入：

```text
/plugin marketplace add DreamOfXM/ui-taste-skill
/plugin install ui-taste-skill@ui-taste-skill
```

也可以不进会话，在终端执行 `claude plugin marketplace add DreamOfXM/ui-taste-skill` 和 `claude plugin install ui-taste-skill@ui-taste-skill`。装好后新会话里问 `What skills are available?`，应出现 `ui-taste-skill`；它的调用名带插件前缀，在 `/` 列表里能看到。依据见 [Claude Code 插件文档](https://code.claude.com/docs/en/plugins)。

### 在 Codex 中安装

Codex 从用户级目录 `~/.agents/skills` 读取技能。用 skills CLI 装到该目录（需要 Node.js 22.20+）：

```sh
npx skills add DreamOfXM/ui-taste-skill -g -a codex
```

也可以把本仓库完整复制到 `~/.agents/skills/ui-taste-skill`。新会话中输入 `$ui-taste-skill` 应能指名它；没有反应时先确认目录是否正确、文件是否完整。

### 其他客户端

[skills CLI](https://github.com/vercel-labs/skills) 支持 Qoder、Claude Code、Codex 等 75 个以上客户端。把仓库装到它识别到的客户端（`-g` 表示用户级，去掉则只装到当前项目）：

```sh
npx skills add DreamOfXM/ui-taste-skill -g
```

升级用 `npx skills update`，卸载用 `npx skills remove ui-taste-skill`。

### 安装时注意

- 目标目录已存在时不要覆盖：它已经指向本仓库或其他克隆就保留现状；是无关目录就先移开或备份再克隆。
- 技能列表里没有出现，先确认克隆或导入的是完整目录、放的是所用客户端真正扫描的位置；旧会话可能需要重开。
- Qoder 与 Claude Code 的安装不需要 Node.js 或 Python；只有 `npx skills`、本地打开示范页面、运行维护检查时才需要。

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

这些是随仓库提供的离线 HTML 页面，不是在线产品。GitHub 中的 HTML 文件链接展示源码；要在浏览器里体验，需要 Python 3，在本仓库目录或解压后的 ZIP 目录运行：

```sh
cd /path/to/ui-taste-skill   # 换成仓库或解压目录
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
