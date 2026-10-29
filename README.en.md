# UI Taste Skill

English · [简体中文](README.md)

Help your AI coding assistant choose a visual direction, then carry it through layout, typography, and interaction.

[Install](#install) · [Try a task](#try-a-task) · [Explore the examples](#explore-the-examples)

[![Zijian exhibition direction: six large type specimens form the composition, with typing and favorites in the detail panel](assets/reference-evidence/studio-gallery-desktop.png)](assets/reference-evidence/studio-gallery-desktop.png)

Zijian teaching example: the exhibition direction arranges six type specimens through scale and spacing. The [workbench direction](assets/reference-evidence/studio-instrument-desktop.png) uses the same content, tightening the catalog and enlarging the active specimen to shift from browsing to inspection.

## More than a different theme

- **Compare genuinely different directions**: for a new interface or open-ended redesign, explore composition, materials, and content presentation. Choose a direction before implementation begins.
- **Turn that choice into concrete constraints**: a design card specifies the compositional focus, typography and materials, key states, and narrow-screen transitions to guide the code.
- **Honor the reference and scope**: preserve a reference image’s composition and typographic relationships. A targeted refinement does not become a full redesign or require another two-direction comparison.
- **Inspect the running interface**: use it and examine screenshots, checking functionality and visual design separately. A successful build does not establish interface quality.

Use it to design, redesign, or review websites, desktop software, mobile apps, and web workbenches.

## Install

This is an instruction and reference package for a coding assistant, not a standalone design application. The README is bilingual; **the skill instructions and reference materials are currently in Chinese**.

Before installing, review [SKILL.md](SKILL.md), `references/`, and the bundled scripts for code and external requests they may run. Install the complete package, not just the entry file. If a skill with the same name already exists, check its source and back up local changes before replacing it.

All three clients take the same `skills` CLI command and receive the same complete package. Requires **Node.js 22.20+** and the client already installed. Run in a terminal from any directory:

```sh
npx skills add DreamOfXM/ui-taste-skill -g
```

Choose a client when prompted; to install into one client, add `-a` and its target name, for example `-a codex`. Expand your client for its install location, how to activate the skill, and the alternative when Node.js is unavailable:

<details open>
<summary><b>Claude Code</b> · <code>claude-code</code></summary>

Installed to `~/.claude/skills/`. In a new session, type `/`, select `ui-taste-skill`, then enter the [first task](#try-a-task).

Without Node.js, use the plugin marketplace inside a **Claude Code session**, not an ordinary terminal:

```text
/plugin marketplace add DreamOfXM/ui-taste-skill
/plugin install ui-taste-skill@ui-taste-skill
```

In a new session, ask `What skills are available?` and select the plugin-prefixed entry from the `/` list. Update and remove it from the `/plugin` panel; see the [Claude Code plugin documentation](https://code.claude.com/docs/en/plugins) for host details.

</details>

<details>
<summary><b>Codex</b> · <code>codex</code></summary>

Installed to `~/.agents/skills/`. Start a new session, enter `$ui-taste-skill`, then the [first task](#try-a-task).

</details>

<details>
<summary><b>Qoder Desktop</b> · <code>qoder</code></summary>

Installed to `~/.qoder/skills/`. In a new task, type `/`, select the skill, then enter the [first task](#try-a-task).

Without Node.js, download the release asset [ui-taste-skill.zip](https://github.com/DreamOfXM/ui-taste-skill/releases/latest/download/ui-taste-skill.zip) and import it via Extensions → Skills → Add Skills → Upload Skill; confirm `ui-taste-skill` appears under Installed.

</details>

`-g` installs at user scope, available in every project; run from the target project directory and omit `-g` for project scope. If the skill does not appear, confirm the package includes `SKILL.md` and `references/`, that it sits in a directory the client scans, and that you opened a new session.

Update:

```sh
npx skills update ui-taste-skill -g
```

Remove:

```sh
npx skills remove ui-taste-skill -g
```

With installs in several clients, update and remove prompt for a target, or accept `-a`. Other clients supported by the skills CLI (Cursor, Gemini CLI, OpenCode, and others) use the same command; target names are in the [supported clients list](https://github.com/vercel-labs/skills/blob/main/docs/agents.md). Installer support for a client does not establish that this Skill has been validated there.

## Try a task

In an existing project, select the skill using your client’s steps above. Provide the page or screenshot you want to change, then enter:

```text
Redesign this page with ui-taste-skill.
Preserve its existing functionality.
Compare two visual directions first,
using real content.
Wait for my choice before writing
a design card and implementing it.
Run and inspect the result.
Check functionality, visual design,
and narrow-screen states separately.
```

The first result should be two directions you can compare, rather than an immediate full-page implementation. After you confirm one, the design card should specify layout, typography, key states, and responsive behavior. The final delivery should include findings from running and visually inspecting the interface.

For reference-matching, attach the image and name the relationships to preserve. For a targeted refinement, specify the scope. For review only, explicitly add “Do not modify code yet.”

## Explore the examples

These are offline HTML pages included in the repository. Obtain the complete repository or extract the ZIP. With Python 3 available, run this from the repository root or the extracted skill root:

```sh
python3 -m http.server 8788 --bind 127.0.0.1
```

While the server is running, open the local links below in your browser. Press `Ctrl+C` in the terminal to stop it. These are not hosted sites; the links will not work without the local server.

- [Zijian direction studio](http://127.0.0.1:8788/assets/variant-board.html): exhibition and workbench compositions using the same specimens, with switching, filtering, and typing.
- [Index workbench](http://127.0.0.1:8788/assets/reference-workbench.html): list and detail views, search, favorites, and narrow-screen back navigation.
- [Jian reading journal](http://127.0.0.1:8788/assets/reference-editorial.html): Chinese typography, reading rhythm, and article and topic filters.
- [App relationship refinement lab](http://127.0.0.1:8788/assets/app-craft-lab.html): compare arrangements of the same content and inspect lists, details, and preferences.
- [Project Radar](http://127.0.0.1:8788/examples/project-radar/index.html): a redesign prototype for a real project, bringing project purpose ahead of statistics.

The first four are teaching pages with fictional content. Project Radar uses a public data snapshot from 2026-10-19 and covers only browsing, filtering, and details; it is not a live product. The pages use local fonts, whose appearance may vary by system. See the [visual breakdowns](references/visual-examples.md) for the design relationships.

## Boundaries and references

The Skill provides design and validation methods, not a guarantee of consistently excellent output from every model. Repository examples are web pages; native apps still require validation on their target platforms. When the execution environment cannot inspect images, visual and interaction conclusions need further verification.

The following instructions and reference materials are in Chinese:

- [Complete skill instructions](SKILL.md)
- [Generation methods](references/generation.md)
- [Reference adaptation](references/visual-calibration.md)
- [Review methods](references/review.md)

<details>
<summary>Maintainers: run validation</summary>

Run package checks from the repository root. Requires Python 3.9+ and uses only the standard library:

```sh
python3 -B -m unittest discover -s tests -v
```

The checks cover installation switching, recovery, metadata, documentation resources, and source hashes for existing screenshots. They do not touch real installation directories or evaluate aesthetics.

Regenerating browser evidence for the examples requires Node.js 18+ and Chrome / Chromium:

```sh
node scripts/verify-app-craft.cjs
node scripts/verify-references.cjs
```

Set `CHROME_BIN` if the browser is not found. The scripts use an isolated temporary browser profile and update reports and screenshots in the repository; the resulting images still need visual inspection. See [evaluation methods](references/evaluation.md) for scope and methodology.

</details>

## License

By DreamOfXM. Released under the [MIT License](LICENSE): commercial and noncommercial use, modification, and redistribution are permitted, with the copyright and permission notices retained.
