# UI Taste Skill

**给 AI 编程助手用的 UI 设计 Skill，让界面不止“能用、整齐”，还拥有自己的视觉气质。**

适用于网页、桌面软件、移动 App 和 Web 工作台的设计、改版与评审。从具体内容出发，比较构图、排印和交互方向，再把选定方案落实为可运行的界面，而不是反复套同一组配色与卡片。

[快速开始](#快速开始) · [试一个任务](#试一个任务) · [查看示范](#查看示范)

![字间字体工作室的展陈方向：以大字样、疏密布局和蓝色展板组织同一组字体标本](assets/reference-evidence/studio-gallery-desktop.png)

*仓库内的原创教学示范「字间」：同一组字体内容的展陈方向；[工作面方向](assets/reference-evidence/studio-instrument-desktop.png)比较的是构图与操作关系。两个方向都是预先完成的静态页面，不是模型即时生成的效果。*

## 快速开始

这是供支持 Agent Skills 的编程助手读取的指令与参考资料，不是独立运行的设计软件。

### 在 Qoder 中使用

以下步骤在 macOS + Qoder 上验证过，需要先安装 Git；其他系统与客户端请按所用工具的 Skill 目录替换路径。在终端运行：

```sh
mkdir -p "$HOME/.qoder/skills"
git clone https://github.com/DreamOfXM/ui-taste-skill.git "$HOME/.qoder/skills/ui-taste-skill"
```

如果目标目录已经存在，不要直接覆盖：它是指向本仓库或其他克隆的链接时保留现状；是无关目录时先移开或备份，再重新克隆。

开启新会话，确认可用 Skill 列表中出现 `ui-taste-skill`，然后给出下面的任务。列表没有出现时，检查克隆的是否为完整目录，以及所用工具是否扫描 `~/.qoder/skills`；旧会话可能需要重开。加载 Skill 本身不需要 Python、Node.js 或运行仓库里的验证脚本。

### 其他编程助手

按照所用工具的 Agent Skills 安装方式接入**整个仓库目录**，不要只复制 `SKILL.md`，执行过程中还会读取参考资料；扫描目录与加载方式以该工具的说明为准。

## 试一个任务

在已有项目中，附上需要修改的页面、截图或参考图，再用自然语言提出任务。例如：

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

开放式设计会先探索方向；明确原稿或局部精修不强制重做全局。交付需检查实际界面与交互，不能只交设计说明。

## 它怎样帮助设计

- **从内容决定形式。** 先理解用户任务和信息关系，再决定构图、密度与视觉重心，不默认所有产品都适合相同的卡片布局。
- **比较真正不同的方向。** 用关键屏检验对象尺度、排印和操作关系的差异，而不是只换主题色。
- **把方向写成可执行的约束。** 明确布局、字级、素材、材质与交互；对于容易偏离方案的实现者，提供更具体的视觉执行说明。
- **实现后再看实际结果。** 将可用性、运行情况与审美判断分开检查；页面不报错只是底线。

方法入口见 [SKILL.md](SKILL.md)。需要深入了解时，阅读[生成方法](references/generation.md)、[参考适配](references/visual-calibration.md)与[评审方法](references/review.md)。

## 查看示范

这些是随仓库提供的离线 HTML 教学页面，不是在线产品。GitHub 中的 HTML 文件链接展示源码；在本地浏览器体验时，需要 Python 3，在已安装的仓库目录运行：

```sh
cd ~/.qoder/skills/ui-taste-skill   # 换成实际安装目录
python3 -m http.server 8788 --bind 127.0.0.1
```

打开以下地址；结束后在终端按 `Ctrl+C` 停止服务。

| 示范 | 看什么 | 本地地址 |
| --- | --- | --- |
| 字间方向工作室 | 同内容的展陈 / 工作面两种构图，可切换、筛选与试写 | [打开字间](http://127.0.0.1:8788/assets/variant-board.html) |
| 索引工作台 | 列表与详情、搜索、收藏及窄屏返回 | [打开工作台](http://127.0.0.1:8788/assets/reference-workbench.html) |
| 间阅读刊物 | 中文排印、阅读节奏、文章与主题筛选 | [打开刊物](http://127.0.0.1:8788/assets/reference-editorial.html) |
| 软件关系精修实验室 | 比较同内容的排布，检查列表、详情与偏好 | [打开实验室](http://127.0.0.1:8788/assets/app-craft-lab.html) |

页面使用本地字体，字体外观可能随系统变化。每个示范的设计关系见[视觉拆解](references/visual-examples.md)。

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
