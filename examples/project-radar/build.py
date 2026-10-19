#!/usr/bin/env python3
"""Build a standalone design experiment from a dated, local public-data snapshot."""
import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent

# Editorial translations are scoped to these records, never inferred financial results.
EDITED = {
    'shader-effects-inc/shaders': ('Shaders', '开发工具', '把实时图形，带进你的下一个网页。',
        '为 React、Vue、Svelte、Solid、JavaScript 和 Framer 提供 WebGPU 视觉组件。',
        '观察图形能力如何被封装成开发者可使用的组件，以及开源关注与收费入口之间的关系。', 'shader'),
    'Atelier': ('Atelier', 'AI 工作流', '给 AI 编程，留一张完整的工作台。',
        'Mac 上的 AI 编程工作室，将应用任务、发布、反馈和记忆放在同一个工作空间。',
        '研究多项目与多会话之间的上下文，如何成为一个独立的产品体验。', 'atelier'),
    'CrewTower Mod for Claude Code': ('CrewTower', 'AI 工作流', '让编程 Agent 的进度，留在视线里。',
        '在 Mac 刘海区域查看 Claude Code、Codex 等 Agent 的进度，并响应它们的请求。',
        '研究一个足够小的界面，如何解决频繁切换应用查看状态的问题。', 'crew'),
    'Atoll92/agent-standup': ('Agent Standup', 'AI 工作流', '让编程会话，变成看得懂的协作。',
        '把 Claude Code、Codex 和 Mistral Vibe 会话呈现为实时团队通话，看见谁在工作、谁在等待。',
        '研究怎样把看不见的 Agent 协作状态变成可理解的界面。采集记录只有打赏入口，不能据此判断产品收入。', 'standup'),
    'Show HN: ThemesFor.app': ('ThemesFor', '建站工具', '搭建页面，也保留对 HTML 的掌控。',
        '面向创业项目、通讯和个人项目的响应式网站主题与在线建站工具。',
        '研究可视化搭建与代码控制权如何共存。原简介写有免费使用，采集到支付入口，具体收费范围仍需核实。', 'themes'),
    'Show HN: Katalog': ('Katalog', '生活工具', '把本地音乐，重新整理成自己的收藏。',
        '面向本地音乐收藏的快速音乐库应用。',
        '研究本地内容管理与日常播放体验的结合。当前公开关注数据有限。', 'music'),
    'Show HN: MacVisor': ('MacVisor', '开发工具', '在 Mac 上管理虚拟机与网络环境。',
        '提供虚拟机、VLAN 与防火墙相关功能的 Mac 工具。',
        '研究专业系统功能如何被组织成可以日常使用的桌面工具。', 'visor'),
}


def normalize(raw):
    result = []
    for p in raw['sections']['discovered_projects']:
        name = p['display_name']
        edit = next((v for k, v in EDITED.items() if k.lower() in name.lower()), None)
        urls = [u for u in p.get('evidence_urls', []) if u.startswith(('https://', 'http://'))]
        result.append({
            'id': p['project_id'], 'name': edit[0] if edit else name.removeprefix('Show HN: '),
            'originalName': name, 'category': edit[1] if edit else p.get('theme') or '其他项目',
            'headline': edit[2] if edit else '', 'description': edit[3] if edit else p.get('blurb', ''),
            'originalDescription': p.get('blurb', ''), 'note': edit[4] if edit else '',
            'art': edit[5] if edit else '', 'urls': urls, 'sources': p.get('sources', []),
            'metrics': p.get('latest_metrics', {}), 'mechanisms': p.get('mechanisms', []),
            'moneyStatus': p.get('money_status'), 'lastSeen': p.get('last_seen'),
            'firstSeen': p.get('first_seen'), 'trend': p.get('trend'), 'seeded': p.get('seeded', False),
        })
    return result


def build(source=None):
    if source:
        raw_bytes = Path(source).read_bytes()
        raw = json.loads(raw_bytes)
        snapshot = {'generatedAt': raw['generated_at'], 'sourceSha256': hashlib.sha256(raw_bytes).hexdigest(),
                    'coverage': raw['probe_coverage'], 'projects': normalize(raw)}
        (ROOT / 'snapshot.json').write_text(json.dumps(snapshot, ensure_ascii=False, separators=(',', ':')) + '\n')
    else:
        snapshot = json.loads((ROOT / 'snapshot.json').read_text())
    html = (ROOT / 'page.html').read_text()
    html = html.replace('/* INLINE_STYLE */', (ROOT / 'style.css').read_text())
    data = json.dumps(snapshot, ensure_ascii=False, separators=(',', ':')).replace('<', '\\u003c')
    html = html.replace('/* INLINE_DATA */', data)
    html = html.replace('/* INLINE_APP */', (ROOT / 'app.js').read_text())
    (ROOT / 'index.html').write_text(html)
    print(f'Built {len(snapshot["projects"])} dated project records into index.html')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--source', type=Path, help='Read a fresh local daily.json snapshot')
    build(parser.parse_args().source)
