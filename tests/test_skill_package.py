"""Package integrity only: these tests do not establish visual quality."""
import hashlib
import json
import re
import unittest
from datetime import datetime
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]


class ResourceParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.resources = []
        self.ids = []
        self.styles = []
        self.in_style = False

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if 'id' in attrs:
            self.ids.append(attrs['id'])
        if 'style' in attrs:
            self.styles.append(attrs['style'])
        if tag == 'style':
            self.in_style = True
        keys = ['src', 'poster']
        if tag == 'link':
            keys.append('href')
        for key in keys:
            if key in attrs:
                self.resources.append(attrs[key])

    def handle_endtag(self, tag):
        if tag == 'style':
            self.in_style = False

    def handle_data(self, data):
        if self.in_style:
            self.styles.append(data)


class SkillPackageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.skill = (ROOT / 'SKILL.md').read_text()
        cls.meta = json.loads((ROOT / '_meta.json').read_text())
        match = re.match(r'\A---\n(.*?)\n---\n(.*)\Z', cls.skill, re.S)
        if not match:
            raise AssertionError('SKILL.md must have closed YAML frontmatter')
        cls.frontmatter, cls.body = match.groups()

    def test_frontmatter_identity_and_description(self):
        name = re.search(r'^name: (.+)$', self.frontmatter, re.M).group(1)
        description_line = re.search(r'^description: (.+)$', self.frontmatter, re.M).group(1)
        description = json.loads(description_line)
        self.assertRegex(name, r'^[a-z0-9]+(?:-[a-z0-9]+)*$')
        self.assertEqual(name, ROOT.name)
        self.assertEqual(name, self.meta['name'])
        self.assertEqual(description, self.meta['description'])
        self.assertLessEqual(len(description), 1024)
        self.assertNotIn('\n', description)

    def test_version_and_entry_size(self):
        version = re.search(r'^  version: "([^"]+)"$', self.frontmatter, re.M).group(1)
        self.assertEqual(version, self.meta['version'])
        self.assertRegex(version, r'^\d+\.\d+\.\d+$')
        self.assertLess(len(self.body.splitlines()), 500)

    def test_execution_document_links_resolve(self):
        documents = [ROOT / 'SKILL.md', ROOT / 'README.md', *sorted((ROOT / 'references').glob('*.md'))]
        for document in documents:
            content = re.sub(r'```.*?```', '', document.read_text(), flags=re.S)
            for target in re.findall(r'!?\[[^\]]*\]\(([^\s)]+)\)', content):
                parsed = urlsplit(target)
                if parsed.scheme or not parsed.path:
                    continue
                path = (document.parent / unquote(parsed.path)).resolve()
                with self.subTest(document=document.name, target=target):
                    self.assertTrue(path.is_relative_to(ROOT), 'Package links must stay in the repository')
                    self.assertTrue(path.is_file(), f'Missing linked file: {path}')

    def test_execution_documents_have_no_unresolved_markers(self):
        for path in [ROOT / 'SKILL.md', *sorted((ROOT / 'references').glob('*.md'))]:
            with self.subTest(path=path.name):
                self.assertNotIn('TODO:', path.read_text())

    def test_offline_lab_has_no_external_resources_or_duplicate_ids(self):
        for filename in ('app-craft-lab.html', 'reference-workbench.html', 'reference-editorial.html', 'variant-board.html'):
            with self.subTest(file=filename):
                html = (ROOT / 'assets' / filename).read_text(encoding='utf-8')
                parser = ResourceParser()
                parser.feed(html)
                parser.close()
                self.assertEqual(len(parser.ids), len(set(parser.ids)), 'Duplicate static HTML IDs')
                for resource in parser.resources:
                    with self.subTest(resource=resource):
                        self.assertTrue(resource.startswith(('data:', '#')), 'Offline assets must be embedded')
                css = '\n'.join(parser.styles)
                for resource in re.findall(r'url\(\s*[\'"]?([^\s)\'"]+)', css, flags=re.I):
                    with self.subTest(css_resource=resource):
                        self.assertTrue(resource.startswith(('data:', '#')), 'CSS resources must be embedded')
                self.assertIsNone(re.search(r'@import\b', css, flags=re.I), 'No remote CSS imports')

    def test_resource_parser_distinguishes_styles_from_scripts(self):
        parser = ResourceParser()
        parser.feed('<style>.icon { filter: url(#filter); }</style>'
                    '<span style="background: url(data:image/png;base64,AA==)"></span>'
                    '<script>const url = new URL(location.href);</script>')
        parser.close()
        self.assertEqual(parser.styles, ['.icon { filter: url(#filter); }',
                                         'background: url(data:image/png;base64,AA==)'])

    def test_browser_evidence_matches_current_source(self):
        evidence = ROOT / 'assets' / 'app-craft-evidence'
        report = json.loads((evidence / 'report.json').read_text())
        source_hash = hashlib.sha256((ROOT / 'assets' / 'app-craft-lab.html').read_bytes()).hexdigest()
        self.assertEqual(report['sourceSha256'], source_hash, 'Demo changed: rerun browser verification')
        self.assertEqual(report['status'], 'passed', 'Browser evidence must record a successful run')
        self.assertTrue(report['checks'])
        self.assertTrue(report['captures'])
        filenames = [capture['file'] for capture in report['captures']]
        self.assertEqual(len(filenames), len(set(filenames)))
        for capture in report['captures']:
            with self.subTest(file=capture['file']):
                screenshot = (evidence / capture['file']).resolve()
                self.assertTrue(screenshot.is_relative_to(evidence.resolve()))
                content = screenshot.read_bytes()
                self.assertTrue(content.startswith(b'\x89PNG\r\n\x1a\n'))
                self.assertEqual(hashlib.sha256(content).hexdigest(), capture['sha256'])

    def test_reference_evidence_matches_current_sources(self):
        evidence = (ROOT / 'assets' / 'reference-evidence').resolve()
        self.assertTrue(evidence.is_relative_to((ROOT / 'assets').resolve()))
        report_path = (evidence / 'report.json').resolve()
        self.assertTrue(report_path.is_relative_to(evidence), 'Report must stay inside its evidence directory')
        report = json.loads(report_path.read_text(encoding='utf-8'))
        self.assertEqual(report['status'], 'passed', 'Rerun scripts/verify-references.cjs successfully')
        expected_sources = {
            filename: hashlib.sha256((ROOT / 'assets' / filename).read_bytes()).hexdigest()
            for filename in ('reference-workbench.html', 'reference-editorial.html', 'variant-board.html')
        }
        self.assertEqual(report['sources'], expected_sources, 'Reference changed: rerun browser verification')
        self.assertIsInstance(report['scope'], str)
        self.assertTrue(report['scope'].strip())
        captured_at = datetime.fromisoformat(report['capturedAt'].replace('Z', '+00:00'))
        self.assertIsNotNone(captured_at.tzinfo, 'Capture time must include a timezone')
        self.assertIsInstance(report['browser'], dict)
        self.assertTrue(report['browser']['product'])
        self.assertIsInstance(report['checks'], list)
        self.assertTrue(report['checks'])
        self.assertTrue(all(isinstance(check, str) and check.strip() for check in report['checks']))
        self.assertFalse(report.get('error'))
        self.assertFalse(report.get('errors'))
        self.assertFalse(report.get('externalRequests'))
        self.assertIsInstance(report['captures'], list)
        expected_captures = {
            'workbench-desktop.png': ('workbench', [1440, 960]),
            'workbench-empty.png': ('workbench', [1440, 960]),
            'workbench-mobile.png': ('workbench', [390, 844]),
            'workbench-detail-mobile.png': ('workbench', [390, 844]),
            'editorial-desktop.png': ('editorial', [1440, 1000]),
            'editorial-article.png': ('editorial', [1440, 1000]),
            'editorial-mobile.png': ('editorial', [390, 844]),
            'editorial-article-mobile.png': ('editorial', [390, 844]),
            'studio-gallery-desktop.png': ('studio-gallery', [1440, 960]),
            'studio-instrument-desktop.png': ('studio-instrument', [1440, 960]),
            'studio-gallery-mobile.png': ('studio-gallery', [390, 844]),
            'studio-instrument-mobile.png': ('studio-instrument', [390, 844]),
            'studio-gallery-detail-mobile.png': ('studio-gallery', [390, 844]),
            'studio-instrument-detail-mobile.png': ('studio-instrument', [390, 844]),
        }
        filenames = [capture['file'] for capture in report['captures']]
        self.assertEqual(len(filenames), len(set(filenames)), 'Duplicate screenshot paths')
        self.assertTrue(set(expected_captures).issubset(filenames), 'Missing required desktop/mobile states')
        for capture in report['captures']:
            with self.subTest(file=capture['file']):
                filename = capture['file']
                self.assertIsInstance(filename, str)
                parsed = urlsplit(filename)
                self.assertFalse(parsed.scheme or parsed.netloc or parsed.query or parsed.fragment)
                self.assertEqual(unquote(filename), filename, 'Screenshot paths must not be URL encoded')
                self.assertNotIn('\\', filename, 'Use portable relative paths')
                relative = Path(filename)
                self.assertFalse(relative.is_absolute(), 'Screenshot paths must be relative')
                self.assertNotIn('..', relative.parts, 'Screenshot paths must not traverse directories')
                self.assertEqual(relative.suffix, '.png')
                screenshot = (evidence / relative).resolve()
                self.assertTrue(screenshot.is_relative_to(evidence), 'Screenshot/symlink escapes evidence directory')
                self.assertTrue(screenshot.is_file())
                content = screenshot.read_bytes()
                self.assertTrue(content.startswith(b'\x89PNG\r\n\x1a\n'))
                self.assertGreaterEqual(len(content), 33, 'PNG must contain an IHDR chunk')
                self.assertEqual(content[8:16], b'\x00\x00\x00\x0dIHDR')
                self.assertRegex(capture['sha256'], r'^[0-9a-f]{64}$')
                self.assertEqual(hashlib.sha256(content).hexdigest(), capture['sha256'])
                self.assertIn(capture['surface'], ('workbench', 'editorial', 'studio-gallery', 'studio-instrument'))
                self.assertIsInstance(capture['state'], str)
                self.assertTrue(capture['state'].strip())
                viewport = capture['viewport']
                self.assertIsInstance(viewport, list)
                self.assertEqual(len(viewport), 2)
                self.assertTrue(all(type(value) is int and value > 0 for value in viewport))
                self.assertEqual(int.from_bytes(content[16:20], 'big'), viewport[0])
                self.assertGreaterEqual(int.from_bytes(content[20:24], 'big'), viewport[1])
                if filename in expected_captures:
                    surface, expected_viewport = expected_captures[filename]
                    self.assertEqual(capture['surface'], surface)
                    self.assertEqual(viewport, expected_viewport)

    def test_core_execution_reading_budget(self):
        documents = [ROOT / 'SKILL.md'] + [
            ROOT / 'references' / filename
            for filename in ('generation.md', 'visual-calibration.md', 'review.md')
        ]
        total = sum(len(document.read_text(encoding='utf-8')) for document in documents)
        self.assertLessEqual(total, 14000, 'Keep the core execution chain within 14,000 characters')


if __name__ == '__main__':
    unittest.main()
