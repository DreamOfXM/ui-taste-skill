# UI Taste Skill

English · [简体中文](README.md)

Turn a redesign into a checkable process: compare two visual directions, constrain the implementation with a design card, then validate on the densest screen and at narrow widths.

[Install](#install) · [Try a task](#try-a-task) · [Explore the examples](#explore-the-examples)

[![Zijian exhibition direction: six large type specimens form the composition, with typing and favorites in the detail panel](assets/reference-evidence/studio-gallery-desktop.png)](assets/reference-evidence/studio-gallery-desktop.png)

Zijian teaching example: the exhibition direction arranges six type specimens through scale and spacing. The [workbench direction](assets/reference-evidence/studio-instrument-desktop.png) uses the same content, tightening the catalog and enlarging the active specimen to shift from browsing to inspection.

## How a redesign runs

- **Start from real content, compare two directions**: set the final language, the longest title, and the most complex object first. The difference should be in composition, material, or object presentation, not a new color scheme. Pick a direction yourself, or let the assistant choose and finish.
- **Turn the direction into a design card**: specify region proportions, target viewport, title line breaks, image crops, and key states. Check the build against it so defaults do not sand those relationships down.
- **Honor the reference and the scope**: preserve a reference image’s composition and typographic relationships. A targeted refinement does not become a full redesign or force a second direction.
- **Test the hardest screen first**: validate dense interior pages, expanded states, and narrow windows before extending. Independent visual review and source-blinded comparison keep aesthetic judgment separate from functional checks.

Use it for new design, redesign, and review of websites, desktop software, mobile apps, and web workbenches.

## Install

This is an instruction and reference package for a coding assistant, not a standalone design application. The README is bilingual; **the skill instructions and reference materials are currently in Chinese**.

Before installing, review [SKILL.md](SKILL.md), `references/`, and the bundled scripts for the code they run and the external services they reach. Install the complete package, not just the entry file. If a skill with the same name already exists, check its source and back up local changes before replacing it.

All three clients take the same `skills` CLI command and receive the same complete package. Requires **Node.js 22.20+** and the client already installed. Run in a terminal from any directory:

```sh
npx skills add DreamOfXM/ui-taste-skill -g
```

Choose a client when prompted, or name one with `-a`. `-g` installs at user scope, available in every project; run from the target project directory and omit `-g` for project scope.

- **Claude Code** (`-a claude-code`): `~/.claude/skills/`; type `/` in a new session and select `ui-taste-skill`
- **Codex** (`-a codex`): `~/.agents/skills/`; enter `$ui-taste-skill` in a new session
- **Qoder Desktop** (`-a qoder`): `~/.qoder/skills/`; type `/` in a new task and select `ui-taste-skill`

Open a new session and confirm the skill appears in the list. If it does not, check that the package includes `SKILL.md` and `references/`, that the directory matches the list above, then restart the client. Without Node.js 22.20+ the command cannot run: on Qoder Desktop, import the [release ZIP](https://github.com/DreamOfXM/ui-taste-skill/releases/latest/download/ui-taste-skill.zip) (release assets may lag behind the latest commits); other clients need Node.js 22.20+ first.

Maintenance: update with `npx skills update ui-taste-skill -g`, remove with `npx skills remove ui-taste-skill -g`; with several clients installed the CLI prompts for a target, or pass `-a`. Cursor, Gemini CLI, OpenCode, and other supported clients use the same command; target names are in the [supported clients list](https://github.com/vercel-labs/skills/blob/main/docs/agents.md). Installer support for a client does not mean this skill has been validated there.

## Try a task

In an existing project, select the skill, provide the page or screenshot you want to change, then enter:

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

The first result should be two directions you can compare, not an immediate full-page implementation. After you confirm one, the design card should specify layout, typography, key states, and responsive behavior; the delivery should include findings from actually running and inspecting the page.

For reference-matching, attach the image and name the relationships to preserve; for a targeted refinement, state the scope; for review only, add “Do not modify code yet.”

## Explore the examples

The examples are offline HTML pages in the repository, not hosted sites. Obtain the full repository or extract the ZIP; with Python 3 available, run this from the repository root or the extracted skill root:

```sh
python3 -m http.server 8788 --bind 127.0.0.1
```

While the server runs, open the local links below in your browser; press `Ctrl+C` in the terminal to stop it. The links do not work without the local server.

- [Zijian direction studio](http://127.0.0.1:8788/assets/variant-board.html): exhibition and workbench compositions using the same specimens, with switching, filtering, and typing.
- [Index workbench](http://127.0.0.1:8788/assets/reference-workbench.html): list and detail views, search, favorites, and narrow-screen back navigation.
- [Jian reading journal](http://127.0.0.1:8788/assets/reference-editorial.html): Chinese typography, reading rhythm, and article and topic filters.
- [App relationship refinement lab](http://127.0.0.1:8788/assets/app-craft-lab.html): compare arrangements of the same content and inspect lists, details, and preferences.
- [Project Radar](http://127.0.0.1:8788/examples/project-radar/index.html): a redesign prototype for a real project, bringing project purpose ahead of statistics.

The first four are teaching pages with fictional content. Project Radar uses a public data snapshot from 2026-10-19 and covers only browsing, filtering, and details; it is not a live product. The pages use local fonts, whose appearance may vary by system. See the [visual breakdowns](references/visual-examples.md) for the design relationships.

## Boundaries and references

The Skill provides design and validation methods. It does not guarantee consistently excellent output from every model, and does not replace product decisions, implementation, or security review. Repository examples are web pages; native apps still need validation on their target platforms. When the environment cannot inspect images, visual and interaction conclusions need further verification.

Reference materials (in Chinese):

- [Complete skill instructions](SKILL.md)
- [Generation methods](references/generation.md)
- [Reference adaptation](references/visual-calibration.md)
- [Typography and Chinese–Latin typesetting](references/typography.md)
- [Independent visual review](references/review.md)
- [Browser evidence tool](references/tooling.md#通用网页取证) and [source-blinded comparisons](references/evaluation.md#执行可复查的匿名对照)

<details>
<summary>Maintainers: run validation</summary>

Run package checks from the repository root. Requires Python 3.9+ and uses only the standard library:

```sh
python3 -B -m unittest discover -s tests -v
```

The checks cover installation switching, recovery, metadata, resource links, screenshot hashes, and the source-blinded comparison tool. Browser capture cases also need local Node.js and Chrome / Chromium; unavailable dependencies are reported as skips. Tests use isolated temporary directories, not real installation directories, and do not evaluate aesthetics.

Regenerating browser evidence for the examples requires Node.js 18+ and Chrome / Chromium:

```sh
node scripts/verify-app-craft.cjs
node scripts/verify-references.cjs
```

Set `CHROME_BIN` if the browser is not found. The scripts use an isolated temporary browser profile and update reports and screenshots in the repository; the resulting images still need visual inspection. See [evaluation methods](references/evaluation.md) for scope and methodology.

</details>

## License

By DreamOfXM. Released under the [MIT License](LICENSE): commercial and noncommercial use, modification, and redistribution are permitted, with the copyright and permission notices retained.
