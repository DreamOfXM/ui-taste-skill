---
name: ui-design-router
description: "UI 设计路由层：按意图分发命令，跑闸门产数字结论"
tags: ["ui", "design", "workflow", "routing"]
---

# ui-design-router — 路由层

本 skill **不生成设计稿，只路由到能生成的命令**。它做三件事：
1. 判断意图 → 2. 挑对应命令 → 3. 把闸门数字变成结论。

**生成能力由以下承担**（见§二.零与§三仲裁表）：
- `references/generation.md`（生成协议与工艺标准，2026-09-26 蒸馏自 Claude Design 方法论——
  管结构发散 ≥3 骨架、vault 参考输入、活体验证、永不填充，防"每次换皮"）
- finesse-ui / impeccable 的 SKILL.md 正文（方法论与命令）
- product-design 套件（market-discovery.md 调研过，**未安装**，见§二.零——装上前不算能力）

审美真源在 `~/.agents/skills/design-inspiration/`（`BEAUTY_RUBRIC.md` + `scripts/beauty_gate.py`）。
判据数值只在那一处演进，本文件只引用不复制。

---

## 一、先判意图，再动手

收到设计类请求，**先按这张表定位**，不要直接开始读源码写报告：

| 用户说的话 | 意图 | 走哪条 |
|---|---|---|
| 「设计 XXX 界面」「画个原型」「做个 App UI」 | 新页面 | 取参考 → 生成 → 过闸 → 实拍 |
| 「改版 XXX」「优化这个页面」「左边放导航」 | 改已有页面 | 先 detect 拿基线 → 改 → 复检 |
| 「彻底重构 XXX」「重新设计，结构也换」 | 结构重开 | 组织轴全开 → ≥3 骨架画板 → 锚定 → 闸门 → 盲评 |
| 「给我个新方案对比」「看看别的思路」 | 出对比稿 | 生成 N 版，冻结构只换皮（或冻皮只换结构） |
| 「检查下设计是否合理」「哪里不对」 | 评审 | **不许**凭空判，跑闸门拿数字，见第三节 |

意图不明时问一句，别猜。

### 生成类意图的公共协议（防换皮，2026-09-26 起）

新页面 / 对比稿 / 结构重开三条路线共用。执行者见§二.零（generation.md 协议 + finesse / impeccable 方法论），
发散协议细则在 `references/generation.md`：

1. **生成走生成引擎方法论**：`references/generation.md`（Claude Design 方法论蒸馏，来源与许可已注）——
   问透 → 读 choices.log → vault 真图输入 → 变体画板 → 活体验证。
2. **结构先行，≥3 个骨架**：结构轮必须产出 ≥3 个**结构互异**骨架（不同组织轴、不同阅读顺序，
   只重排不算），同一画板并排，锚定 + 盲评选出后才准进皮肤轮。
   画板模板：`assets/variant-board.html`（`?a=骨架1.html&b=骨架2.html&c=骨架3.html`，专注键全屏对比）。
   **未过结构轮直接改颜色/字体/圆角 ＝ 本路线未开始。**
3. **vault 必作输入**：生成前取 `vault/refs{,_beauty}/` ≥2 张真图作上下文——
   参考对质量影响最大，冷描述生成必然回落均值。
4. **变体意图四分法**：用户要"新方案"时先问清要的是新结构、新视觉、新动效还是新文案——
   四件不同的事，别混着做。

---

## 二、已验证可执行的命令

### 零、生成能力的承担者

本 skill **不负责生成设计稿**。§一的"生成"步骤由以下承担：

| 承担者 | 状态 | 角色 |
|--------|------|------|
| `references/generation.md`（Claude Design 方法论蒸馏） | ✅ 已在库 | 生成协议与工艺标准：怎么发散、什么算完成 |
| finesse-ui 0.20.0 正文（四寄存器/动效十族/反雷同 divergence） | ✅ 已在库 | 生成方法论与类型系统 |
| impeccable `/craft` 等 24 命令 | ✅ 已在库（harness 指令；CLI 仅 `detect` 可 exec） | 生成与改造命令 |
| product-design 套件（/flow-web /board /chart /edge…） | ⚠️ **未安装**（2026-09-26 全盘实测不存在） | market-discovery.md 调研对象；v1.0.0 曾当已存在写入。装前不得当能力引用；要装先过 skill-vetter |

产物交给 beauty_gate/impeccable 等闸门检验。
生成过程必须遵守§一「生成类意图的公共协议」与 `references/generation.md` 的工艺标准
（44px 触达、oklch 调色、永不填充、活体验证）。


以下每一条都在本机实跑通过，可直接调用。

### 1. 反模式扫描（最高价值，支持文件 / 目录 / URL）

```bash
IMPECCABLE=~/.agents/skills/impeccable/scripts/impeccable

$IMPECCABLE detect <文件或目录>            # 人读输出（走 stderr）
$IMPECCABLE detect --json <target>         # 结构化输出（走 stdout），供编排
$IMPECCABLE detect --quiet <target>        # 只要末行计数
$IMPECCABLE detect --viewport 390x844 <URL>  # 移动视口（iPhone 12 Pro 宽度）
```

- 实测（2026-09-21 复评）：`ai-color-palette` 的触发口径是紫色 **accent 用色**（紫渐变 hero、紫按钮、紫卡片），暗底紫字本身不触发它；`dark-glow` 对每处零偏移彩色光晕各计一条。命中即 exit 2。
- **exit code（impeccable 专用约定）**：
  - `0` = 反模式扫描未发现问题
  - `2` = 发现反模式（如 AI 紫、假截图）→ CI 应阻断
  - `1` = 目标不可访问
  **注意**: 这与 gate scripts 的 `0/1/2` 含义不同（见§二末尾对照表）。
- 可读项目 `.impeccable/config.json` 与 `DESIGN.md`；`--no-design-system` 可关掉。

### 2. 美感闸门（审美真源，判据 B0–B6 + B12，打印 B11 读数）

```bash
PY=~/browser-use-env/bin/python    # 需要 playwright；见第四节
$PY ~/.agents/skills/design-inspiration/scripts/beauty_gate.py \
    --register product <候选.html | URL>
```

- 实测输出：`FAIL ×2 / display 32px / B1 无展示级字号（真值需 ≥40）/ B12 报头字距 +0.000em＝浏览器默认（参考站 4/4 均为负）`。
- **任何 elevate 交付前必须跑这条**，且要把数字抄进结论，不许只说"不够高级"。
- `--register publication|product|brand` 换地板值（默认 publication）；值非法直接退 2。**这个值取自本轮
  `DIRECTION.md` 的 `寄存器:` 行**，两处不一致时以 DIRECTION 为准重跑，不要手改一档凑通过。
- 本地 HTML 自渲染判 FAIL；给 `http(s)` URL 视为参考站，**只打印读数不判 FAIL**。
- B0（默认面孔命中 ≥3）是唯一有出口的判据：写一份辩护落盘再 `--defense <文件>` 复跑；口头声称不采信，
  文件不存在直接退 2。B11 间距刻度**永远只打印**——四代探针已被同一批数据证伪（`BEAUTY_RUBRIC.md` §七·五），
  谁写第五代几何探针谁错。

### 3. 结构轮内容保真闸门（防"换皮时偷删内容"）

```bash
/usr/bin/python3 ~/.agents/skills/design-inspiration/scripts/check_style.py <候选.html> <基线.html>
```

- PASS 行打印 `texts=… distinct=… | nodes=…（切分数，不同不判分）| hrefs=… | nums=… | blocks=…`，逐项抄进结论。
- 结构轮（动布局骨架的那一轮）的候选稿必须过这条，否则"布局更克制"可能是靠**删掉了内容**换来的。
- 纯 stdlib，`/usr/bin/python3` 即可跑，不需要 playwright。

### 4. 轮次协议闸门（方向锚点先于稿、盲评真的落盘）

```bash
/usr/bin/python3 ~/.agents/skills/design-inspiration/scripts/check_round.py \
    ~/Desktop/prototypes/<项目>/r<NN>/ --candidates a.html b.html
```

- 查两件事：`DIRECTION.md`（五字段 + 参考图真实存在 + 寄存器合法）是否**早于**所有候选稿；
  `blind-*.md` 盲评票是否 ≥2 票、九字段齐全、评的是当前这张图、且票里没出现代码文件名。
- 这一步的存在理由：`BEAUTY_RUBRIC.md` 里"方向起点"和"盲评落盘"两条判据曾指向已删除的 ui-lead 协议，
  等于没有任何地方定义落盘格式与核对人——于是两步被静默跳过，四版收敛成同一张脸。
- 闸门只保证**步骤发生**，不保证**意见正确**；票面的定性结论仍要抽查回图。

**第 2、3、4 条共用一套退出码：`0` 通过 / `1` 测了且不合格 / `2` 根本没跑成**（参数错、文件缺、渲染不出字）。
2 与 0 的区别是唯一诚实口径——**没测的算不过**，口头结论不采信；把 2 当 0 汇报是本 skill 最严重的一类错误。

### 退出码契约对照表

| 命令 | 0 | 1 | 2 |
|------|---|---|---|
| `impeccable detect` | 无反模式问题 | 目标不可访问 | 发现问题（CI 应阻断） |
| `beauty_gate.py` | 通过所有判据 | 未通过判据 | 没跑成（参数错/文件缺） |
| `check_style.py` | 内容保真 | 内容被删改 | 没跑成 |
| `check_round.py` | 轮次协议完整 | 盲评不足/字段缺失 | 没跑成 |

**通用原则**: 遇到非 0 退出码一律视为"不过",口头结论不采信。

这条与第 1 条 impeccable 的 `0/1/2` **含义不同**（那边 2 = 有主发现），别看数字一样就当同一套。

### 5. 抓真实参考（皮肤轮的输入，不能省）

```bash
$PY ~/.agents/skills/design-inspiration/scripts/capture_refs.py
```

- 落盘 `design-inspiration/vault/refs/`（44 个文件 = 39 张首屏 + 5 张整页）+ `refs_beauty/`（23 张，**全部只有首屏**）。
  即"每条参考都同抓整页"这条硬要求目前欠 57 张，下次抓新增站时回头补，别再累积。
- 实测：5 成功 / 13 因反爬失败——Cloudflare 类站点换 `lite.cnn.com`、`text.npr.org` 替身。
- 优先用浏览器工具而非 curl。

### 6. 设计系统 token 生成

```bash
python3 ~/.agents/skills/ui-ux-pro-max/scripts/design_system.py "SaaS dashboard" --format markdown
```

- 实测可用，输出 pattern / style / 色板 / CSS 变量。
- ⚠️ 它会给出不符合你偏好的默认值（实测推荐过 Glassmorphism、`#EA580C` 橙）。
  **只当候选来源，不当判据**，冲突按第三节仲裁表处理。

### 7. 正则层粗筛

```bash
node ~/.agents/skills/finesse-ui/scripts/detect.mjs <文件>
```

- 脚本自己声明「Regex layer only」，紫色氛围、重复卡片、320px 溢出等**它明说扫不到**，
  需交给上面第 1、2 条和浏览器实拍。别把它当完整审计。

### 8. 浏览器实拍（交付前必过）

走 `mcp_call` 调 `mcp__browser-use__*` 或 `mcp__plugin_chrome-devtools-mcp_chrome-devtools__*`：
`navigate_page` → `take_screenshot` / `take_snapshot`。
移动端用 `resize_page` 或 `--viewport 390x844`。

---

## 三、仲裁表（多个 skill 打架时按这张表，不临时判断）

| 争什么 | 谁说了算 | 理由 |
|---|---|---|
| 美感判据数值（字号/字距/墨色/饱和色个数） | **design-inspiration `BEAUTY_RUBRIC.md`** | 唯一由真实站实测反推、且带可执行闸门的一份；其它处的副本一律视为过期 |
| 反模式黑名单（AI 紫、发光、假截图、重复卡片） | **impeccable detect** | 规则最多且支持 URL/视口/JSON |
| 配色与风格偏好（暖白底+蓝、禁珊瑚、专业文案） | **用户记忆 + 项目 DESIGN.md** | 个人指纹，优先级高于任何通用推荐 |
| 交付前是否放行 | **beauty_gate + impeccable detect + 亲眼读图** 三关全过 | 单靠 grep 或单靠模型自评都不算证据 |
| 「寄存器」一词（两套同名坐标系） | **`DIRECTION.md` 的 `寄存器:` 只写 beauty_gate 三值（publication/product/brand＝地板档位）；finesse 的 register（brand/product/commerce/h5＝页面类型）另起 `页面类型:` 行，禁止混写** | 同词不同义＝组成性失效（2026-09-26 调研漏检回流，skill-evaluation failure-log #9） |
| 生成能力（用什么库、怎么搭页面） | **finesse / impeccable 出稿，方法论与发散协议归 `references/generation.md`** | 执行者出稿，协议管怎么发散、什么算完成 |

`ui-ux-pro-max` 的推荐与上表冲突时，**让位**，它是候选生成器不是判据。

---

## 四、环境事实（本机实测，别再猜）

| 用途 | 路径 | 备注 |
|---|---|---|
| 需要 playwright 的闸门脚本 | `~/browser-use-env/bin/python` | playwright ✓ PIL 12.1.1 |
| 同上（备选） | `~/Desktop/_项目代码/ai-content-monetizer/backend/venv/bin/python` | playwright ✓ PIL 11.3.0 |
| 只要 playwright 不需 PIL | `/usr/bin/python3`、`~/.copaw/venv/bin/python`、`~/.qiji_venv/bin/python` | 能截图，不能拼图 |
| 默认 PATH 上的 `python3` | ❌ 无 playwright | 直接跑 beauty_gate 会 ModuleNotFoundError |
| impeccable CLI | `~/.agents/skills/impeccable/scripts/impeccable` | POSIX shell，无需 Node |

Chromium 缓存已在 `~/Library/Caches/ms-playwright`，不必额外下载。
MCP 工具报 `Tool not found` 通常是没走 `mcp_call`，不代表环境缺能力，别据此要求重启。

---

## 五、交付要求（每个设计任务收口时逐项对齐）

1. **结论带数字**：引用 beauty_gate / detect 的实际输出，不写"更高级""更专业"。
2. **实拍为证**：改版后必须起浏览器截图，先读图再描述改动；只读代码不算视觉验收。
3. **新鲜度自证**：截图与产物写清生成时间与来源路径，同名旧稿要能排除。
4. **结构 / 皮肤分轮**：改结构就冻结视觉层，改视觉就冻结 DOM；同一轮只动一件事。
5. **反雷同**：连续两轮不许收敛到同一张面孔，上一轮方向不得作为本轮默认。
6. **导航可见**：每屏自带明写的返回；返回挂在悬停才出现的上级名上＝糊弄。
7. **文案专业**：按钮用专业动词+对象，禁口语俏皮；术语晦涩时在控件右侧加 HelpHint。
8. **活体验证**：交付前 localhost 起服务预览（禁 file://，多文件原型会静默失败）、控制台零错、
   截图过目——预览 URL 是交付物的一部分，不是裸文件路径。
9. **永不填充**：不拿占位文字凑版面；"空"是布局问题，不是编内容的问题；想加内容先问。
   每个元素都要配得上存在——一千个否定换一个肯定。

---

## 六、已知断链（别当已存在的能力用）

2026-09-21 复核后，本节只剩"确实没有执行器"的条目；曾列在前两条（`check_style.py` 不存在、
`beauty_gate` 未实现 B2/B4/B6）**已修好并移到第二节**，别再照旧文说它们缺。

- **B7–B10 + 间距刻度天生没有机器闸门**：`beauty_gate.py` 判 B0–B6 + B12、只**打印** B11 读数
  （§七·五 已把四代 B11 探针全部证伪，谁写第五代谁错）。这四条轴必须由盲评 subagent 读图裁定，
  且落盘成票后由 `check_round.py` 核对——**口头转述不算盲评**。
- **信息架构类判断没有闸门（2026-09-29 实战盲区，makemovie 连环翻车暴露）**：常驻解释文案
  该不该问号化、低频动作该不该入口化/弹框化、空态框高度——闸门词表（反模式+B0-B12）完全
  不覆盖。这类条款归项目规范（makemovie-ui-rules）+ 项目测试机器检查（如 apps/web 的
  ui-rules.test.ts）双层兜底；评审结论必须声明「本结论不含 IA 判断」，别让用户以为全查过了。
- **「文字碰撞」「内容被遮 ≥0.9」目前没有闸门**：真源曾指向 `check_layout.py`，全仓 `find` 实测
  该文件不存在。现在能扫这类问题的是 `$IMPECCABLE detect`，但它不覆盖这两条判据的完整口径，
  所以**不要把它们当"已验证的通过项"汇报**。
- **参考库的整页截图欠账**：`vault/refs/` 39 张首屏里只有 5 张带 `_full.png`，`refs_beauty/` 23 张
  一张都没有。"每条参考都同抓整页"这条硬要求目前不成立，读旧图当参考时要知道自己只看得到首屏。
- **`capture_refs.py` 对反爬站点成功率低**：实测 5 成功 / 13 失败；Cloudflare 类站点换
  `lite.cnn.com`、`text.npr.org` 替身，批量抓前先单页测。
- impeccable 的 25 个 `/命令`（`/critique` `/audit` `/live` …）是**给 AI harness 的 skill 指令，不是 CLI 子命令**；CLI 里唯一可 exec 的是 `detect`。旧版本文档把这两件事混为一谈，导致 AI「想调也调不到」。
- **`design-taste-frontend`（即旧文档里的 "Taste Skill"）和 `redesign-existing-projects` 没有 `scripts/`，一个都 exec 不了**——实测其目录下脚本数为 0。它们是纯方法论文档，只能被 AI 读完照着做，不存在"调用"这回事。旧版本文档把它们写成可 invoked 的模块，是「集成了但跑不起来」的直接来源。
  - 它们承诺的能力已有可跑替身：口味判分 → `beauty_gate.py`；反塑料感 → `impeccable detect`；改版基线 → `impeccable detect` 先扫再改；参考输入 → `capture_refs.py`；换皮不删内容 → `check_style.py`；轮次协议 → `check_round.py`。凡提到 "taste skill" 一律路由到这几个命令，不要再去"调用"那两个文档型 skill。
  - 第三方 skill 不改文件（用户规则），所以**不给它们补脚本**，只在此处说明它们没有可执行层。

---

## 七、产物落盘

轮次目录是唯一落点：**`~/Desktop/prototypes/<项目>/r<NN>/`**。候选 HTML、`DIRECTION.md`、`blind-*.md`、
截图全部落在这一个目录里，因为 `check_round.py` 就是拿这个目录做 mtime 先后核对的——候选稿散到别处，
第 4 条闸门等于没跑。

- 候选原型：`~/Desktop/prototypes/<项目>/r<NN>/<候选名>.html`
- 实拍截图：`~/Desktop/prototypes/<项目>/r<NN>/<屏>-<版本>-<日期>.png`
- 反馈/状态：`~/Desktop/prototypes/<项目>/design-state.json`（状态记 `approved` / `changes-requested`）
- 取舍账：`~/Desktop/prototypes/<项目>/choices.log`（append-only：每轮记 选了哪版 / 毙了哪些 / 一句为什么；
  **写 DIRECTION.md 前必读**——跨轮品味沉淀的最小闭环，别让八轮选择白躺在目录里）

**不要把原型放 `/tmp`**（旧版本这里写过 `/tmp/prototype-<项目>-<日期>.html`）。本机 `/tmp` 随重启蒸发，
2026-09-21 实测该路径下已无任何文件，第三轮皮肤轮的输入与产物就是这么全量丢失的。

反馈框与 JSON 是**手写在原型 HTML 里的模式**，没有生成器——需要时按第五节要求现写，
不要假设有脚本会自动导出。

---

## 八、使用示例

**场景 A：新建页面设计**
```
用户："帮我设计一个 SaaS 管理后台的主页"
↓ 路由判断 → 取参考 → 生成 → beauty_gate过闸 → 实拍截图
输出：3 版不同布局的 HTML + 美感读数 (B0-B6)
```

**场景 B：改版已有页面**
```
用户："这个 dashboard 太乱了，左边放导航"
↓ 路由判断 → impeccable detect 基线扫当前稿 → 改布局 → check_style 防删内容 →复检
输出：改版后 HTML + 对比报告（文字/数字节点保真度）
```

**场景 C：设计评审**
```
用户："检查下设计是否合理，哪里不对"
↓ 路由判断 → 不许凭空判 → run beauty_gate + impeccable detect → 拿数字
输出：逐项打分报告（字号≥40px? 字距负值？墨色 95%+？饱和色≤4？）
```

---

## 九、变更记录

| 日期 | 版本 | 变更内容 |
|------|------|---------|
| 2026-09-26 | v1.1.1 | P1 双修：①寄存器语义分轨——仲裁表新增"两套同名坐标系"行，`DIRECTION.md` 的 `寄存器:` 限定 beauty_gate 三值，finesse 页面类型另起 `页面类型:` 行；②B1 阈值对齐实测——publication 正文地板 16→14（实测两站 14px，按「5 参考全过」标定），rubric/代码/投影表三处同步。新增 `assets/variant-board.html` 变体画板模板 |
| 2026-09-26 | v1.1.0 | 新增生成引擎 `references/generation.md`（蒸馏自 Claude Design 方法论）与生成类意图公共协议（结构发散 ≥3 骨架 / vault 必作输入 / 变体画板 / 活体验证 / 永不填充）；意图表加"结构重开"路线；落盘加 `choices.log` 取舍账；交付要求补 8/9 两条；修正 v1.0.0 幽灵承诺——product-design 套件实测未安装，§二.零 改为状态标注 |
| 2026-09-23 | v1.0.0 | 新增 `_meta.json` + `SKILL.md` frontmatter tags；新增使用示例章节；精简 description |
| 2026-09-21 | v0.9.0 | 首次实测 8 条命令并验证环境配置；补全仲裁表与交付要求 |

---

## 十、相关文件

- 真源：`~/.agents/skills/design-inspiration/SKILL.md`、`BEAUTY_RUBRIC.md`
- 生成引擎：`~/.agents/skills/ui-design-router/references/generation.md`（方法论蒸馏自 JimLiu/baoyu-design @ MIT，其上游为 Anthropic Claude Design）
- 可行性调研：`~/.agents/skills/ui-design-router/references/market-discovery.md`
- 本文件唯一真源：`~/.agents/skills/ui-design-router/SKILL.md`（曾用名 live-design-skill）
  （`~/.qoder/skills/` 下为镜像；旧文档里写的 `Desktop/_工具脚本/skills/live-design.md` 已废弃）
