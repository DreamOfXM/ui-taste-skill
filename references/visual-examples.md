# 看得见、可运行、可拆解的示范

只选与当前任务最接近的一例：先用读图工具打开截图，再按需读对应 HTML 的 CSS 与状态实现。文字不是看图的替代。这些是原创教学样例，内容虚构，尚非用户认可标准或市场标杆；不能用它们宣称跨模型效果已验证。它们示范如何作决定，不限定下一件作品只能达到这里。

## 方向工作室：同一份内容，创造两种完整美感

打开[字间工作室](../assets/variant-board.html)，比较[展陈桌面](../assets/reference-evidence/studio-gallery-desktop.png)与[工作面桌面](../assets/reference-evidence/studio-instrument-desktop.png)。两者共享六组标本、当前对象、搜索、分类、收藏及每组试写；不是故意做差的旧版与精修新版，也不是两个独立产品。

**先观察值得欣赏的关系：**

| 关系 | 展陈 Gallery | 工作面 Instrument |
|---|---|---|
| 画面主角 | 六组字样以大小、行形和轻重共同构图，浏览本身有节奏 | 左侧目录压紧，右侧当前字样放大，选择后的重心非常明确 |
| 空间组织 | 1440 宽时集合约为详情的三倍；集合内部用 7:5、5:7 的分配交替 | 326px 目录旁是可伸展的试样面，索引与检查拥有不同密度 |
| 材料与色彩 | 宋体笔画、斜体曲线、等宽代码本身就是材料；蓝底白字让斜体成为一个停顿 | 近黑底、稍亮工作面与选中行构成表面层次；亮字在大试样区获得呼吸 |
| 工艺 | 字样换尺度，名称与说明保持稳定轴线；细线连接区域，不把每组都重重包裹 | 目录各行的编号、名称和样本有共同列位，预览、试写与字体栈顺次展开 |

这些优点不来自“暖白更高级”或“深色更专业”。把两版都转成灰度，仍能辨认展陈与检查的不同重心；只换颜色不会得到这种变化。蓝色展陈块是材料处理，不是选中状态；当前对象另外由“当前”、细线与详情表达，不能复制成含糊的数据状态编码。

**实际操作后再判断：**选中另一组 → 试写一句 → 切换方向 → 返回原标本；观察内容、草稿和收藏有没有丢失。展开不是增加一个通用弹窗，而是让同一对象进入适合细看的尺度。移动端分别看[展陈列表](../assets/reference-evidence/studio-gallery-mobile.png)、[工作面列表](../assets/reference-evidence/studio-instrument-mobile.png)与[展陈详情](../assets/reference-evidence/studio-gallery-detail-mobile.png)、[工作面详情](../assets/reference-evidence/studio-instrument-detail-mobile.png)：列表仍有不同节奏，详情则都聚焦于一个试样，不为制造差异牺牲窄屏操作。截图中的焦点框来自实际键盘操作。

**取舍：**以感受字样、发现灵感为主时，展陈更有吸引力；高频选择、试写与检查时，工作面更直接。展陈在窄屏需要更长滚动，工作面在总览时牺牲单个字样的表现空间。这里不裁定一种永远更美，也没有用户偏好结论。

**迁移方法：**先换成你的真实对象，再保留“集合与单体如何争取注意”的关系；照片任务用照片，审计任务以差异和证据为材料。不要把字样替换成六个统计数字就套到仪表盘。字体均由本机字体栈实际渲染，不提供字体文件，也不保证跨系统字形相同；空间和字形仍需在目标平台重校。

**源码入口：**查看 `.workspace`、`.specimen-list`、`#specimen-detail` 及 `data-direction` 的布局切换，跟随 `renderDirection`、`openSpecimen`、`renderProof` 看共用状态。此例使用容器单位适配字样宽度，使用 `textContent` 展示试写；具体尺寸是此内容的决定，不是通用 token。

## A. 索引：精确、安静但不寡淡的工作界面

适合对象查找、选择、检查和收藏。先看[桌面画面](../assets/reference-evidence/workbench-desktop.png)，再看[窄屏列表](../assets/reference-evidence/workbench-mobile.png)与[窄屏详情](../assets/reference-evidence/workbench-detail-mobile.png)。[完整实现](../assets/reference-workbench.html)离线可运行，源码包含排布与交互。

**读图时看四个关系，而不是记配色：**

- 深色窄导航稳定边界，浅色大工作面让对象易读；深色不自动等于主角，因为它的宽度、内容与强调都受控。
- 列表直接构成页面，不套一层又一层卡片；对象名、来源、日期、收藏有稳定的角色与列位。
- 蓝色主要表示操作与选择，不给每条记录分配颜色；选中行与右侧详情始终指向同一对象。
- 密集列表旁的详情较舒展，形成密度对比；窄屏把“列表与详情同时看”改成“进入与返回”，不将三栏挤小。

**适配顺序：**用你的对象名、来源和摘要替换演示内容 → 保留大区比例与文字角色 → 调整列宽和行高以容纳最长内容 → 最后换品牌颜色。高密度金融表格应重新评估列与行高，不原封不动套这份资料列表。

**源码入口：**查看根部 CSS 变量、工作区网格、`.resource-row` 与媒体查询；跟随 `data-select-id`、`data-favorite-id` 找到选择与收藏状态。一开始只借当前需要的关系，不复制无关功能。

## B. 间：由排印与材料承担表达的阅读界面

适合刊物、设计文章、内容专题。先看[整页画面](../assets/reference-evidence/editorial-desktop.png)与[实际阅读页](../assets/reference-evidence/editorial-article.png)，再看[窄屏入口](../assets/reference-evidence/editorial-mobile.png)。[完整实现](../assets/reference-editorial.html)包含主题筛选、阅读、收藏与返回。

**这例与工作台不是换色关系：**

- 中文展示字与右侧排版习作共同构图，文字本身是内容而非后台标题放大；朱红承担大片材料，不只是按钮点缀。
- 首屏较舒展，文章目录更紧凑，正文回到有限行长；不同阶段用不同密度，让阅读有节奏。
- 线条用于分隔章节与目录，不把每篇文章装进同样的圆角框；图形是明确的原创排版示意，不伪装照片。
- 阅读页收回展示性处理，让正文与返回、收藏成为重点；入口的个性不能以阅读疲劳为代价。

**适配顺序：**先确认真实标题与主材料 → 固定二者比例，校准中文断行 → 组织目录和正文的疏密 → 最后决定色彩与展示字体。不要把这套大字、宽留白或衬线复制到高频操作表格。

**源码入口：**看首屏网格、展示字与正文的分离、文章视图和媒体查询；通过 `data-open-article`、`#toggle-article-save` 跟随阅读状态，而不是只截一张入口图。

## 一处常见错误，如何具体改

下面是可试的关系变化，不是所有界面的默认样式：

```css
/* 当外框比内容更抢眼时，先减掉冗余容器。 */
.collection { display: grid; gap: 12px; }
.record { padding: 24px; border: 1px solid #ccd1da; border-radius: 16px; }
```

对“扫读同类对象”的列表，可试：

```css
.collection { display: block; }
.record { display: grid; grid-template-columns: minmax(0, 1fr) 7rem 2rem;
  gap: 16px; align-items: center; padding: 16px 0;
  border: 0; border-bottom: 1px solid #e4e7ec; border-radius: 0; }
.record-title { font-size: 14px; font-weight: 600; line-height: 1.5; }
.record-meta { font-size: 12px; line-height: 1.5; color: #596372; }
@media (max-width: 640px) {
  .record { grid-template-columns: minmax(0, 1fr) 2rem; }
  .record-date { grid-column: 1; }
}
```

先看对象是否更易扫读，再决定是否保留。若这些是独立可操作的项目、图片或需要强边界的对象，卡片可能更合适；不能把“去卡片”当审美结论。值只服务本次实验，仍需检查实际语言、对比度与交互。

## 已有材料与证据边界

- [Fold 常规](../assets/app-craft-evidence/standard-light.png) / [Fold 精修](../assets/app-craft-evidence/refined-light.png)适合观察局部关系；[实验室](../assets/app-craft-lab.html)可操作，不是宏观视觉方向的唯一范本。
- [项目雷达旧稿](../examples/project-radar/evidence/before-desktop.png)有既往用户认可记录，仅限当时画面与场景，不能延伸为后续版本或所有项目偏好。
- 新示范的源码和截图哈希、视口、实际功能检查由[运行记录](../assets/reference-evidence/report.json)绑定。报告通过只代表对应功能与布局检查；视觉观察、独立生成效果和用户偏好仍是不同证据。
