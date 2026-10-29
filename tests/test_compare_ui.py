import base64
import hashlib
import importlib.util
import json
from pathlib import Path
import struct
import tempfile
import unittest
from unittest import mock
import zlib

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('compare_ui', ROOT / 'scripts/compare-ui.py')
COMPARE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(COMPARE)
SIGNATURE = b'\x89PNG\r\n\x1a\n'


def chunk(kind, body=b''):
    return (struct.pack('>I', len(body)) + kind + body
            + struct.pack('>I', zlib.crc32(body, zlib.crc32(kind)) & 0xffffffff))


def header(width=1, height=1, depth=8, color=6, interlace=0):
    return chunk(b'IHDR', struct.pack('>IIBBBBB', width, height, depth, color, 0, 0, interlace))


def png(width=1, height=1, depth=8, color=6, raw=None, before=(), after=(), compressed=None):
    if compressed is None:
        if raw is None:
            channels = {0: 1, 2: 3, 3: 1, 4: 2, 6: 4}[color]
            raw = bytes(((width * channels * depth + 7) // 8 + 1) * height)
        compressed = zlib.compress(raw)
    return (SIGNATURE + header(width, height, depth, color) + b''.join(before)
            + chunk(b'IDAT', compressed) + b''.join(after) + chunk(b'IEND'))


def chunks(data):
    offset, result = 8, []
    while offset < len(data):
        size, kind = struct.unpack_from('>I4s', data, offset)
        result.append((kind, data[offset + 8:offset + 8 + size]))
        offset += size + 12
    return result


PNG = png()


class CompareUITests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        (self.root / 'one.png').write_bytes(PNG)
        (self.root / 'two.png').write_bytes(PNG)
        self.manifest = self.root / 'comparison.json'
        self.output = self.root / 'review'
        self.payload = {'cases': [{'id': 'task', 'title': '真实任务', 'candidates': [
            {'id': 'secret-old-version', 'states': [{'label': '桌面', 'image': 'one.png'}]},
            {'id': 'secret-new-version', 'states': [{'label': '桌面', 'image': 'two.png'}]},
        ]}]}

    def tearDown(self):
        self.temp.cleanup()

    def write(self):
        self.manifest.write_text(json.dumps(self.payload), encoding='utf-8')

    def build(self):
        self.write()
        COMPARE.build(self.manifest, self.output)

    def artifacts(self):
        page = (self.output / 'index.html').read_text()
        public, _ = json.JSONDecoder().raw_decode(page.split('const cases=', 1)[1])
        private = json.loads((self.output / 'reveal.json').read_text())
        return page, public, private

    def full_page(self, viewport=None):
        for candidate in self.payload['cases'][0]['candidates']:
            candidate['states'][0].update(fullPage=True, viewport=viewport or [2, 2])
        (self.root / 'one.png').write_bytes(png(2, 3))
        (self.root / 'two.png').write_bytes(png(2, 5))

    def test_sources_are_separate_and_hashes_retained(self):
        self.build()
        page, public, private = self.artifacts()
        for secret in ('secret-old-version', 'secret-new-version', 'one.png', 'two.png'):
            self.assertNotIn(secret, page)
        self.assertIn('data:image/png;base64,', page)
        mapping = private['cases'][0]['mapping']
        self.assertEqual(set(mapping), {'A', 'B'})
        self.assertEqual({v['candidate'] for v in mapping.values()}, {'secret-old-version', 'secret-new-version'})
        for value in mapping.values():
            self.assertEqual(value['sha256'], [hashlib.sha256(PNG).hexdigest()])
            self.assertEqual(value['displayedSha256'], value['sha256'])
            self.assertNotIn(value['sha256'][0], page)
        self.assertEqual(public[0]['candidates'][0]['states'][0]['viewport'], [1, 1])

    def test_comparison_id_binds_page_export_and_reveal_and_changes_on_rebuild(self):
        self.build()
        page, _, private = self.artifacts()
        comparison_id, _ = json.JSONDecoder().raw_decode(page.split('const comparisonId=', 1)[1])
        self.assertRegex(comparison_id, r'^[a-f0-9]{32}$')
        self.assertEqual(comparison_id, private['comparisonId'])
        self.assertEqual(set(private), {'comparisonId', 'cases'})
        # The browser export serializes this same constant; browser tests exercise the click.
        self.assertIn('JSON.stringify({comparisonId,reviewer:', page)
        self.assertIn('visual-preferences-${comparisonId}.json', page)
        self.output = self.root / 'another-review'
        self.build()
        self.assertNotEqual(self.artifacts()[2]['comparisonId'], comparison_id)

    def test_metadata_is_stripped_from_decoded_public_images(self):
        visual = [chunk(b'sRGB', b'\x00'), chunk(b'gAMA', struct.pack('>I', 45455)),
                  chunk(b'cHRM', struct.pack('>8I', 31270, 32900, 64000, 33000, 30000, 60000, 15000, 6000)),
                  chunk(b'PLTE', b'\x00\x00\x00\xff\xff\xff'),
                  chunk(b'tRNS', b'\xff\x80'), chunk(b'bKGD', b'\x00')]
        clean = png(color=3, before=visual)
        originals = {}
        for candidate in self.payload['cases'][0]['candidates']:
            secret = candidate['id'].encode()
            metadata = [chunk(b'tEXt', b'Software\x00' + secret),
                        chunk(b'eXIf', b'II*\x00\x08\x00\x00\x00' + secret),
                        chunk(b'iTXt', b'Source\x00\x00\x00\x00\x00' + secret),
                        chunk(b'zTXt', b'Author\x00\x00' + zlib.compress(secret)),
                        chunk(b'vpAg', secret)]
            original = png(color=3, before=visual + metadata[:2], after=metadata[2:])
            originals[candidate['id']] = original
            (self.root / candidate['states'][0]['image']).write_bytes(original)
        self.build()
        page, public, private = self.artifacts()
        for candidate in public[0]['candidates']:
            displayed = base64.b64decode(candidate['states'][0]['image'].split(',', 1)[1])
            mapping = private['cases'][0]['mapping'][candidate['label']]
            original = originals[mapping['candidate']]
            self.assertEqual(displayed, clean)
            self.assertNotIn(b'secret-', displayed)
            self.assertEqual({kind for kind, _ in chunks(displayed)}, COMPARE.DISPLAY_CHUNKS)
            self.assertEqual(mapping['sha256'], [hashlib.sha256(original).hexdigest()])
            self.assertEqual(mapping['displayedSha256'], [hashlib.sha256(displayed).hexdigest()])
            self.assertNotEqual(mapping['sha256'], mapping['displayedSha256'])
            self.assertEqual([body for kind, body in chunks(original) if kind == b'IDAT'],
                             [body for kind, body in chunks(displayed) if kind == b'IDAT'])
            self.assertNotIn(mapping['candidate'], page)

    def test_profiles_are_not_silently_stripped_and_colors_changed(self):
        for kind in (b'iCCP', b'cICP', b'mDCV', b'cLLI'):
            with self.subTest(kind=kind):
                with self.assertRaisesRegex(ValueError, 'color conversion to sRGB'):
                    COMPARE.sanitize_png(png(before=[chunk(kind, b'profile')]))

    def test_non_object_manifest_has_a_clear_error(self):
        self.payload = []
        with self.assertRaisesRegex(ValueError, 'Manifest must be an object'):
            self.build()

    def test_script_end_in_title_cannot_inject_markup(self):
        self.payload['cases'][0]['title'] = '</script><img src=x onerror=alert(1)>'
        self.build()
        page = (self.output / 'index.html').read_text()
        self.assertNotIn('</script><img', page)
        self.assertIn('\\u003c/script>', page)
        self.assertEqual(page.count('</script>'), 1)

    def test_mismatched_state_labels_rejected(self):
        self.payload['cases'][0]['candidates'][1]['states'][0]['label'] = '不同状态'
        with self.assertRaisesRegex(ValueError, 'identical state'):
            self.build()
        self.assertFalse(self.output.exists())

    def test_mismatched_dimensions_rejected(self):
        for width, height in ((2, 1), (1, 2)):
            with self.subTest(width=width, height=height):
                (self.root / 'two.png').write_bytes(png(width, height))
                with self.assertRaisesRegex(ValueError, 'dimensions'):
                    self.build()
                self.assertFalse(self.output.exists())

    def test_full_page_different_heights_are_not_resized_or_cropped(self):
        self.full_page()
        self.build()
        _, public, _ = self.artifacts()
        states = [c['states'][0] for c in public[0]['candidates']]
        self.assertEqual({s['height'] for s in states}, {3, 5})
        for state in states:
            self.assertEqual(state['viewport'], [2, 2])
            self.assertIs(state['fullPage'], True)
            self.assertEqual(state['width'], 2)
            self.assertEqual(base64.b64decode(state['image'].split(',', 1)[1]), png(2, state['height']))

    def test_full_page_mismatched_viewports_rejected(self):
        self.full_page()
        state = self.payload['cases'][0]['candidates'][1]['states'][0]
        for viewport in ([2, 3], [3, 2]):
            with self.subTest(viewport=viewport):
                state['viewport'] = viewport
                (self.root / 'two.png').write_bytes(png(viewport[0], 5))
                with self.assertRaisesRegex(ValueError, 'identical state.*viewport'):
                    self.build()

    def test_full_page_flag_must_match(self):
        self.full_page()
        (self.root / 'one.png').write_bytes(png(2, 2))
        self.payload['cases'][0]['candidates'][0]['states'][0]['fullPage'] = False
        with self.assertRaisesRegex(ValueError, 'fullPage settings'):
            self.build()

    def test_full_page_image_must_cover_viewport_at_exact_width(self):
        self.full_page()
        for width, height in ((1, 4), (3, 4), (2, 1)):
            with self.subTest(width=width, height=height):
                (self.root / 'two.png').write_bytes(png(width, height))
                with self.assertRaisesRegex(ValueError, 'PNG dimensions'):
                    self.build()

    def test_full_page_requires_explicit_viewport(self):
        self.full_page()
        del self.payload['cases'][0]['candidates'][0]['states'][0]['viewport']
        with self.assertRaisesRegex(ValueError, 'explicit viewport'):
            self.build()

    def test_default_capture_requires_exact_declared_viewport(self):
        state = self.payload['cases'][0]['candidates'][0]['states'][0]
        for viewport in ([1, 2], [2, 1]):
            with self.subTest(viewport=viewport):
                state['viewport'] = viewport
                with self.assertRaisesRegex(ValueError, 'PNG dimensions'):
                    self.build()

    def test_invalid_capture_settings_rejected(self):
        state = self.payload['cases'][0]['candidates'][0]['states'][0]
        for viewport in (None, '1x1', [], [1], [1, 1, 1], [True, 1], [1, 1.0], [0, 1], [1, -1]):
            with self.subTest(viewport=viewport):
                state['viewport'] = viewport
                with self.assertRaisesRegex(ValueError, 'viewport'):
                    self.build()
        state.pop('viewport')
        for flag in (None, 0, 1, 'true'):
            with self.subTest(fullPage=flag):
                state['fullPage'] = flag
                with self.assertRaisesRegex(ValueError, 'boolean'):
                    self.build()

    def test_source_traversal_rejected(self):
        self.payload['cases'][0]['candidates'][0]['states'][0]['image'] = '../outside.png'
        with self.assertRaisesRegex(ValueError, 'inside'):
            self.build()

    def test_image_symlink_escape_rejected(self):
        (self.root / 'escape.png').symlink_to(self.root.parent / 'outside.png')
        self.payload['cases'][0]['candidates'][0]['states'][0]['image'] = 'escape.png'
        with self.assertRaisesRegex(ValueError, 'inside'):
            self.build()

    def test_duplicate_candidates_rejected(self):
        candidates = self.payload['cases'][0]['candidates']
        candidates[1]['id'] = candidates[0]['id']
        with self.assertRaisesRegex(ValueError, 'unique'):
            self.build()

    def test_existing_evidence_not_overwritten(self):
        self.build()
        before = (self.output / 'reveal.json').read_bytes()
        with self.assertRaisesRegex(ValueError, 'new or empty'):
            self.build()
        self.assertEqual(before, (self.output / 'reveal.json').read_bytes())

    def test_output_symlink_rejected(self):
        target = self.root / 'elsewhere'
        target.mkdir()
        self.output.symlink_to(target, target_is_directory=True)
        with self.assertRaisesRegex(ValueError, 'non-symlink'):
            self.build()

    def test_invalid_png_rejected(self):
        (self.root / 'one.png').write_text('<svg></svg>')
        with self.assertRaisesRegex(ValueError, 'Invalid PNG'):
            self.build()

    def test_truncated_and_header_only_png_rejected(self):
        for data in (SIGNATURE, PNG[:33], PNG[:40], PNG[:-1], PNG[:-12],
                     PNG[:33] + struct.pack('>I4sI', 0x7fffffff, b'IDAT', 0)):
            with self.subTest(length=len(data)):
                (self.root / 'one.png').write_bytes(data)
                with self.assertRaisesRegex(ValueError, 'Invalid PNG'):
                    self.build()
                self.assertFalse(self.output.exists())

    def test_crc_validation_includes_stripped_metadata(self):
        source = png(before=[chunk(b'tEXt', b'secret')])
        offset = 8
        for kind, body in chunks(source):
            end = offset + len(body) + 12
            damaged = source[:end - 1] + bytes([source[end - 1] ^ 1]) + source[end:]
            with self.subTest(kind=kind):
                with self.assertRaisesRegex(ValueError, 'CRC'):
                    COMPARE.sanitize_png(damaged)
            offset = end

    def test_ihdr_type_depth_dimensions_and_methods_validated(self):
        bodies = [b'bad length']
        for width, height, depth, color, compression, filtering, interlace in (
                (0, 1, 8, 6, 0, 0, 0), (1, 0, 8, 6, 0, 0, 0),
                (32000001, 1, 8, 6, 0, 0, 0), (1, 1, 8, 1, 0, 0, 0),
                (1, 1, 4, 6, 0, 0, 0), (1, 1, 16, 3, 0, 0, 0),
                (1, 1, 8, 6, 1, 0, 0), (1, 1, 8, 6, 0, 1, 0),
                (1, 1, 8, 6, 0, 0, 2)):
            bodies.append(struct.pack('>IIBBBBB', width, height, depth, color, compression, filtering, interlace))
        for body in bodies:
            with self.subTest(body=body):
                with self.assertRaisesRegex(ValueError, 'PNG'):
                    COMPARE.sanitize_png(SIGNATURE + chunk(b'IHDR', body) + PNG[33:])

    def test_unsupported_interlace_animation_and_critical_chunks_rejected(self):
        with self.assertRaisesRegex(ValueError, 'Interlaced.*re-export.*non-interlaced'):
            COMPARE.sanitize_png(SIGNATURE + header(interlace=1) + PNG[33:])
        for kind in (b'acTL', b'fcTL', b'fdAT', b'ABCD'):
            with self.subTest(kind=kind):
                with self.assertRaisesRegex(ValueError, '(Animated|critical).*re-export'):
                    COMPARE.sanitize_png(png(before=[chunk(kind)]))

    def test_chunk_order_lengths_and_palette_validated(self):
        compressed = zlib.compress(bytes(5))
        bad = [SIGNATURE + chunk(b'tEXt', b'x') + PNG[8:],
               SIGNATURE + header() + chunk(b'IEND'),
               png(before=[header()]),
               PNG + b'trailing', PNG[:-12] + chunk(b'IEND', b'x'),
               png(before=[chunk(b'abcd')]), png(before=[chunk(b't3Xt')]),
               png(before=[chunk(b'PLTE', b'x')]), png(color=3),
               png(before=[chunk(b'tRNS', bytes(6))]),
               png(before=[chunk(b'gAMA', bytes(4))]),
               png(before=[chunk(b'sRGB', b'\x04')]),
               png(before=[chunk(b'cHRM', bytes(31))]),
               png(after=[chunk(b'sRGB', b'\x00')]),
               png(color=3, before=[chunk(b'PLTE', bytes(3)), chunk(b'bKGD', b'\x01')]),
               SIGNATURE + header() + chunk(b'IDAT', compressed[:3])
               + chunk(b'tEXt', b'x') + chunk(b'IDAT', compressed[3:]) + chunk(b'IEND')]
        for index, data in enumerate(bad):
            with self.subTest(case=index):
                with self.assertRaisesRegex(ValueError, 'Invalid PNG'):
                    COMPARE.sanitize_png(data)

    def test_zlib_stream_scanline_lengths_and_filters_validated(self):
        invalid = [b'', b'not zlib', zlib.compress(bytes(5))[:-1],
                   zlib.compress(bytes(4)), zlib.compress(bytes(6)),
                   zlib.compress(b'\x05' + bytes(4)), zlib.compress(b'\xff' + bytes(4)),
                   zlib.compress(bytes(5)) + b'trailing',
                   zlib.compress(bytes(5)) + zlib.compress(b'extra')]
        for compressed in invalid:
            with self.subTest(compressed=compressed):
                with self.assertRaisesRegex(ValueError, 'Invalid PNG'):
                    COMPARE.sanitize_png(png(compressed=compressed))

    def test_decompression_bomb_and_declared_memory_limit_rejected(self):
        # A tiny IHDR must not permit a highly compressed multi-megabyte payload.
        with self.assertRaisesRegex(ValueError, 'decompressed scanline length'):
            COMPARE.sanitize_png(png(raw=bytes(2 * 1024 * 1024)))
        # Under the pixel-count limit, but 16-bit RGBA exceeds 128 MB decoded.
        with mock.patch.object(COMPARE.zlib, 'decompressobj') as decoder:
            with self.assertRaisesRegex(ValueError, '128 MB'):
                COMPARE.sanitize_png(png(6000, 4000, depth=16, raw=b'\x00'))
            decoder.assert_not_called()

    def test_file_limit_rejected_before_reading(self):
        with (self.root / 'one.png').open('wb') as stream:
            stream.truncate(COMPARE.MAX_FILE_BYTES + 1)
        with self.assertRaisesRegex(ValueError, '16 MB'):
            self.build()

    def test_all_supported_depths_and_color_types_have_valid_pixels(self):
        for color, depths in {0: (1, 2, 4, 8, 16), 2: (8, 16), 3: (1, 2, 4, 8),
                              4: (8, 16), 6: (8, 16)}.items():
            for depth in depths:
                with self.subTest(color=color, depth=depth):
                    before = [chunk(b'PLTE', bytes(3))] if color == 3 else []
                    image = png(3, 2, depth=depth, color=color, before=before)
                    self.assertEqual(COMPARE.sanitize_png(image), (image, 3, 2))

    def test_split_idat_and_scanlines_crossing_decode_blocks(self):
        width, height = 20000, 5
        # Rows exceed a decode block; each allowed filter is present once.
        raw = b''.join(bytes([f]) + bytes(width * 4) for f in range(height))
        compressed = zlib.compress(raw)
        image = (SIGNATURE + header(width, height)
                 + b''.join(chunk(b'IDAT', compressed[i:i + 7]) for i in range(0, len(compressed), 7))
                 + chunk(b'IEND'))
        self.assertEqual(COMPARE.sanitize_png(image), (image, width, height))
        # Also exercise 64-KB compressed-input boundaries with poorly compressible data.
        raw = b'\x00' + bytes(range(256)) * 313
        image = png(width=20032, raw=raw, compressed=zlib.compress(raw, 0))
        self.assertEqual(COMPARE.sanitize_png(image), (image, 20032, 1))
        invalid = raw + b'\x05' + raw[1:]
        with self.assertRaisesRegex(ValueError, 'scanline filter'):
            COMPARE.sanitize_png(png(width=20032, height=2, raw=invalid))

    def test_browser_failure_guards_are_in_generated_page(self):
        self.build()
        page, _, _ = self.artifacts()
        self.assertIn('截图加载失败，无法投票或导出', page)
        self.assertIn("el('vote').disabled=disabled;el('export').disabled=disabled", page)
        self.assertIn("if(el('export').disabled)return", page)
        self.assertIn('image.onerror=', page)
        self.assertIn('setup();checkImages();', page)

    def test_empty_manifest_rejected(self):
        self.payload = {'cases': []}
        with self.assertRaisesRegex(ValueError, '1–20'):
            self.build()


if __name__ == '__main__':
    unittest.main()
