# 项目雷达：产品表达实验

这是 ui-taste-skill 2.1 的实测案例，针对用户指出的“只是统计表、不像对外产品”。包含真实数据快照、浏览页面、详情、搜索筛选、分页、浏览器收藏和明暗主题；不是原项目整站迁移。

直接打开 [index.html](index.html) 可查看自包含原型。用于真实运行和浏览器测试时，从仓库根目录启动：

```sh
python3 -m http.server 8788 --bind 127.0.0.1
```

预览：<http://127.0.0.1:8788/examples/project-radar/index.html?theme=dark>

页面不依赖 CDN，不发送收藏数据；收藏保存在当前浏览器。显示的是 2026-10-19 的公开项目采集快照，不是实时数据。原始来源与未知项在详情中；产品展示图于 2026-10-20 取得，出处见 [素材记录](assets/SOURCES.md)，不作为历史商业数据的证据。

## 构建

```sh
python3 examples/project-radar/build.py
```

从提交的 `snapshot.json`、`page.html`、`style.css` 和 `app.js` 生成单文件。`--source /path/to/daily.json` 可重新提取数据；本案例的编辑文案与日期绑定当前快照，新数据需要同时复核它们，不能直接作为生产报告生成器。

## 验证层次

- DOM 逻辑：`RADAR_JSDOM_PATH=/path/to/jsdom node examples/project-radar/check-dom.cjs`。依赖现有 jsdom；没有执行真实布局，dialog/scroll 用了替身。
- 真实浏览器：启动服务后，用含 Playwright 的 Python 执行 `examples/project-radar/verify-browser.py`。脚本输出截图与 `evidence/browser-results.json`。本机解释器为 `~/browser-use-env/bin/python`。
- 视觉判断：查看真实截图，按方向与参考比较；浏览器断言不等于审美认可。

本次执行状态见仓库 [2.1 验证记录](../../docs/validation-2.1.md)。未生成截图或未运行的检查不得算通过。
