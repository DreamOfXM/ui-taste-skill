"""Argument safety and real Chromium evidence capture; stdlib only, no package installs."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import struct
import subprocess
import tempfile
import threading
import time
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "capture-ui.cjs"
NODE = shutil.which("node")


def chrome_binary():
    override = os.environ.get("CHROME_BIN")
    candidates = [override] if override else [
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        "/Applications/Chromium.app/Contents/MacOS/Chromium",
        str(Path.home() / "Applications/Google Chrome.app/Contents/MacOS/Google Chrome"),
        "/usr/bin/google-chrome", "/usr/bin/google-chrome-stable", "/usr/bin/chromium",
        "/usr/bin/chromium-browser", "/opt/google/chrome/chrome", "/snap/bin/chromium",
    ]
    if not override:
        for variable in ("PROGRAMFILES", "PROGRAMFILES(X86)", "LOCALAPPDATA"):
            if os.environ.get(variable):
                for suffix in ("Google/Chrome/Application/chrome.exe", "Chromium/Application/chrome.exe"):
                    candidates.append(str(Path(os.environ[variable]) / suffix))
    return next((str(Path(p).resolve()) for p in candidates if p and Path(p).is_file() and os.access(p, os.X_OK)), None)


CHROME = chrome_binary()
FIXTURE = """<!doctype html><html><head><meta charset="utf-8">
<link rel="icon" href="data:,">
<style>
body { margin: 0; padding: 24px; box-sizing: border-box; background: #f4efe3; }
button, input { font: 18px sans-serif; padding: 10px; max-width: 80%; }
body.open { background: #c4e4da; } body.submitted { background: #e2d4f0; }
body.escaped { background: #f4d5bd; } form[hidden] { display: none; }
#tall { height: 1800px; } #motion { width: 80px; height: 40px; background: #b11; }
@media (prefers-reduced-motion: reduce) { #motion { background: #16a; width: 150px; } }
dialog { border: 2px solid #333; padding: 32px; }
</style></head><body>
<button id="open">Open editor</button>
<form hidden><input id="entry" data-field="message" value="old text"><button>Submit</button></form>
<output id="result"></output><div id="motion"></div>
<img alt="pixel" src="data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+aS1kAAAAASUVORK5CYII=">
<dialog><p>Submitted</p><button id="close">Close</button></dialog><div id="tall"></div>
<script>
const field = document.querySelector('#entry'), dialog = document.querySelector('dialog');
function observe(kind, event, extra = {}) {
  navigator.sendBeacon('/events', JSON.stringify({kind, trusted: event?.isTrusted, value: field.value,
    width: innerWidth, height: innerHeight, reducedMotion: matchMedia('(prefers-reduced-motion: reduce)').matches,
    active: document.activeElement.id, ...extra}));
}
document.querySelector('#open').addEventListener('click', event => {
  document.querySelector('form').hidden = false; document.body.className = 'open'; observe('click', event);
});
field.addEventListener('input', event => observe('input', event));
document.addEventListener('keydown', event => observe('key', event, {key: event.key}));
document.querySelector('form').addEventListener('submit', event => {
  event.preventDefault(); document.body.className = 'submitted';
  document.querySelector('#result').textContent = field.value; dialog.showModal(); observe('submit', event);
});
dialog.addEventListener('cancel', event => { document.body.className = 'escaped'; observe('escape', event); });
document.querySelector('#close').addEventListener('click', () => dialog.close());
window.addEventListener('resize', event => observe('resize', event));
matchMedia('(prefers-reduced-motion: reduce)').addEventListener('change', event => observe('media', event));
const mode = new URL(location.href).searchParams.get('mode');
if (mode === 'errors' || mode === 'overflow') {
  const wide = document.createElement('div'); wide.style.cssText = 'width:2200px;height:20px'; document.body.append(wide);
}
if (mode === 'errors' || mode === 'console') console.error('控制台错误 — café');
if (mode === 'errors') setTimeout(() => { throw new Error('fixture exception — 中文'); }, 0);
if (mode === 'broken-image') document.images[0].src = '/missing.png';
if (mode === 'font-timeout') window.addEventListener('load', () => {
  const font = new FontFace('NeverReady', 'url(/slow-font)'); document.fonts.add(font);
  document.body.style.fontFamily = 'NeverReady'; font.load().catch(() => {});
});
</script></body></html>"""


class CaptureBase(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="test-ui-capture-")
        self.addCleanup(self.temp.cleanup)
        # macOS /var is a symlink: use the canonical path because the CLI rejects output symlinks.
        self.root = Path(self.temp.name).resolve()
        self.source = self.root / "generated.html"
        self.source.write_text(FIXTURE, encoding="utf-8")
        self.out = self.root / "evidence"
        self.env = dict(os.environ, CHROME_BIN=str(self.root / "missing-chrome"))

    def args(self, **changes):
        options = {"url": "http://127.0.0.1:9/", "source": str(self.source), "out": str(self.out)}
        options.update(changes)
        result = []
        for name, value in options.items():
            if value is not None:
                result.extend(["--" + name, str(value)])
        return result

    def run_cli(self, args, env=None, timeout=45):
        return subprocess.run([NODE, str(SCRIPT), *args], env=env or self.env,
                              capture_output=True, text=True, timeout=timeout)

    def steps(self, value):
        target = self.root / "steps.json"
        target.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")
        return str(target)

    def invalid(self, args, message):
        result = self.run_cli(args)
        self.assertNotEqual(result.returncode, 0, result.stdout)
        self.assertIn(message, result.stderr)
        self.assertNotIn("Chrome/Chromium not found", result.stderr)
        self.assertFalse(self.out.exists(), "Validation must run before reserving output or launching Chrome")


@unittest.skipUnless(NODE, "Node.js is required")
class CaptureArguments(CaptureBase):
    def test_help_and_required_flags(self):
        result = self.run_cli(["--help"])
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Selectors:", result.stdout)
        self.invalid([], "Required: --url")
        self.invalid(self.args(source=None), "Required: --source")
        self.invalid(self.args(out=None), "Required: --out")
        self.invalid(self.args() + ["--width"], "Missing value")
        self.invalid(self.args() + ["--url", "http://localhost/"], "duplicate")
        self.invalid(self.args() + ["--unknown", "x"], "Unknown")
        self.invalid(self.args() + ["positional", "x"], "Unknown")

    def test_url_validation(self):
        for url in ("https://example.com/", "file:///tmp/ui.html", "data:text/html,hello",
                    "http://127.0.0.1.evil.test/", "http://localhost.evil/", "http://0.0.0.0/",
                    "http://[::]/", "http://user:secret@localhost/", "http://192.168.1.2/",
                    "http://localhost/\n", "http://localhost\\@example.com", "not-a-url"):
            with self.subTest(url=url):
                self.invalid(self.args(url=url), "--url")

    def test_dimensions_and_source(self):
        for value in ("0", "-1", "8193", "1.5", "NaN", "Infinity", "1e3", "12px"):
            with self.subTest(value=value):
                self.invalid(self.args(width=value), "imension")
        self.invalid(self.args(height="0"), "imension")
        self.invalid(self.args(source=str(self.root)), "HTML file")
        other = self.root / "not-html.txt"
        other.write_text("hello", encoding="utf-8")
        self.invalid(self.args(source=str(other)), "HTML file")
        self.invalid(self.args(source=str(self.root / "absent.html")), "ENOENT")

    def test_steps_validation(self):
        cases = [({}, "array"), ([None], "action"), ([{}], "action"),
                 ([{"action": "evaluate", "code": "alert(1)"}], "action"),
                 ([{"action": "click"}], "fields"),
                 ([{"action": "click", "selector": "button", "text": "x"}], "fields"),
                 ([{"action": "fill", "selector": "input", "text": 3}], "fill text"),
                 ([{"action": "fill", "selector": "input", "text": "x\0"}], "fill text"),
                 ([{"action": "key", "key": "Ctrl+R"}], "key"),
                 ([{"action": "key", "key": "\n"}], "key"),
                 ([{"action": "viewport", "width": "390", "height": 844}], "Dimensions"),
                 ([{"action": "media", "reducedMotion": "true"}], "boolean"),
                 ([{"action": "capture", "name": "ok"}] * 201, "200")]
        for value, message in cases:
            with self.subTest(value=str(value)[:100]):
                self.invalid(self.args(steps=self.steps(value)), message)
        target = self.root / "bad.json"
        target.write_text("[", encoding="utf-8")
        self.invalid(self.args(steps=target), "valid JSON")
        self.invalid(self.args(steps=self.root), "JSON file")

    def test_selectors_and_capture_names(self):
        for css in ("", "[", "#", "button >", "input,,button", "input;alert(1)", "#x\n", "[x='bad]", ":has(*)", "a" * 1025):
            with self.subTest(selector=css):
                self.invalid(self.args(steps=self.steps([{"action": "click", "selector": css}])), "selector")
        for name in ("initial", "INITIAL", "../outside", "/absolute", "a.png", "", "a/b", "a\\b", "CON", "name\n", 4):
            with self.subTest(name=name):
                self.invalid(self.args(steps=self.steps([{"action": "capture", "name": name}])), "capture name")
        self.invalid(self.args(steps=self.steps([{"action": "capture", "name": "One"},
                                               {"action": "capture", "name": "one"}])), "capture name")

    def test_output_refuses_files_nonempty_and_symlinks(self):
        existing = self.root / "existing"
        existing.mkdir()
        sentinel = existing / "keep.txt"
        sentinel.write_bytes(b"unchanged")
        self.invalid(self.args(out=existing), "refusing overwrite")
        self.invalid(self.args(out=sentinel), "only directories")
        self.invalid(self.args(out=self.root / "missing-parent" / "out"), "parent must exist")
        self.assertEqual(sentinel.read_bytes(), b"unchanged")
        link = self.root / "link"
        try:
            link.symlink_to(existing, target_is_directory=True)
        except OSError:
            self.skipTest("Symlink creation unavailable")
        self.invalid(self.args(out=link), "symlinks")
        self.invalid(self.args(out=link / "new"), "symlinks")
        empty = self.root / "empty"
        empty.mkdir()
        link.unlink()
        link.symlink_to(empty, target_is_directory=True)
        self.invalid(self.args(out=link), "symlinks")
        link.unlink()
        link.symlink_to(self.root / "dangling", target_is_directory=True)
        self.invalid(self.args(out=link), "symlinks")
        self.assertEqual(list(empty.iterdir()), [])

    def test_validated_missing_browser_produces_honest_report(self):
        self.out.mkdir()  # Existing empty directories are explicitly supported.
        result = self.run_cli(self.args(url="https://[::1]:4443/", steps=self.steps([
            {"action": "click", "selector": "main > form input[data-field=\"message\"], #other"},
            {"action": "fill", "selector": "input", "text": "中文 ' \\\""},
            {"action": "key", "key": "Escape"}, {"action": "media", "reducedMotion": False}])))
        self.assertNotEqual(result.returncode, 0)
        report = json.loads((self.out / "report.json").read_text())
        self.assertEqual(report["status"], "failed")
        self.assertIsNone(report["browserVersion"])
        self.assertEqual(report["captures"], [])
        self.assertIn("Chrome/Chromium not found", report["errors"][0]["message"])

    @unittest.skipIf(os.name == "nt", "POSIX fake executable")
    def test_browser_crash_rejects_pending_and_removes_owned_profile(self):
        fake = self.root / "crash-browser"
        fake.write_text("#!/bin/sh\nfor arg in \"$@\"; do\n case \"$arg\" in --user-data-dir=*) printf '%s\\n' \"$arg\" >&2;; esac\ndone\nexit 7\n")
        fake.chmod(0o700)
        started = time.monotonic()
        result = self.run_cli(self.args(), env=dict(self.env, CHROME_BIN=str(fake)), timeout=12)
        self.assertNotEqual(result.returncode, 0)
        self.assertLess(time.monotonic() - started, 10)
        report = json.loads((self.out / "report.json").read_text())
        self.assertEqual(report["status"], "failed")
        self.assertTrue(any("Browser" in item["message"] for item in report["errors"]))
        profile = report["browserStderr"].strip().split("--user-data-dir=", 1)[1]
        self.assertFalse(Path(profile).exists())


@unittest.skipUnless(NODE and CHROME, "Installed Chrome/Chromium and Node.js required for real-browser smoke tests")
class CaptureBrowser(CaptureBase):
    def setUp(self):
        super().setUp()
        self.env["CHROME_BIN"] = CHROME
        self.events = []
        self.condition = threading.Condition()
        owner = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def do_GET(self):
                if self.path.startswith("/redirect"):
                    self.send_response(302)
                    self.send_header("Location", "https://example.com/")
                    self.end_headers()
                    return
                if self.path == "/slow-font":
                    self.send_response(200)
                    self.send_header("Content-Type", "font/woff2")
                    self.end_headers()
                    owner.font_release.wait(20)
                    return
                if self.path == "/missing.png":
                    self.send_error(404)
                    return
                data = owner.source.read_bytes()
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)

            def do_POST(self):
                event = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
                with owner.condition:
                    owner.events.append(event)
                    owner.condition.notify_all()
                self.send_response(204)
                self.end_headers()

        self.font_release = threading.Event()
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.addCleanup(self.close_server)
        self.url = "http://127.0.0.1:{}/".format(self.server.server_port)

    def close_server(self):
        self.font_release.set()
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=3)

    def capture(self, steps=None, query="", **changes):
        if steps is not None:
            changes["steps"] = self.steps(steps)
        result = self.run_cli(self.args(url=self.url + query, **changes))
        report_path = Path(changes.get("out", self.out)) / "report.json"
        self.assertTrue(report_path.is_file(), result.stdout + result.stderr)
        return result, json.loads(report_path.read_text(encoding="utf-8"))

    def verify_hashes(self, report, out=None):
        self.assertEqual(report["source"]["sha256"], hashlib.sha256(self.source.read_bytes()).hexdigest())
        self.assertEqual(report["source"]["path"], str(self.source))
        self.assertIn("Chrome", report["browserVersion"]["product"])
        self.assertIn("T", report["timestamp"])
        for frame in report["captures"]:
            data = ((out or self.out) / frame["file"]).read_bytes()
            self.assertEqual(data[:8], b"\x89PNG\r\n\x1a\n")
            self.assertEqual(frame["sha256"], hashlib.sha256(data).hexdigest())
            self.assertEqual(struct.unpack(">II", data[16:24]), (frame["viewport"]["width"], frame["viewport"]["height"]))
            self.assertIn("step", frame)
            self.assertIn("T", frame["timestamp"])

    def test_real_input_viewports_media_and_capture_hashes(self):
        text = "真实 UI — café ' \\ \" ; window.bad = 1;"
        steps = [
            {"action": "click", "selector": "#open"},
            {"action": "key", "key": "Tab"},
            {"action": "fill", "selector": 'form > input[data-field="message"]', "text": text},
            {"action": "capture", "name": "filled"},
            {"action": "key", "key": "Enter"},
            {"action": "capture", "name": "submitted"},
            {"action": "key", "key": "Escape"},
            {"action": "capture", "name": "escaped"},
            {"action": "viewport", "width": 390, "height": 844},
            {"action": "media", "reducedMotion": True},
            {"action": "capture", "name": "mobile"},
            {"action": "fill", "selector": "#entry", "text": ""},
            {"action": "capture", "name": "cleared"},
        ]
        result, report = self.capture(steps)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr + str(report["errors"]))
        self.assertEqual(report["status"], "passed")
        self.assertEqual(report["errors"], [])
        self.verify_hashes(report)
        frames = report["captures"]
        self.assertEqual([f["name"] for f in frames], ["initial", "filled", "submitted", "escaped", "mobile", "cleared"])
        self.assertEqual([f["step"] for f in frames], [0, 4, 6, 8, 11, 13])
        self.assertEqual(len({f["sha256"] for f in frames}), len(frames))
        self.assertEqual(frames[0]["viewport"], {"width": 1440, "height": 960, "deviceScaleFactor": 1})
        self.assertEqual(frames[-1]["viewport"], {"width": 390, "height": 844, "deviceScaleFactor": 1})
        self.assertTrue(frames[-1]["reducedMotion"])
        self.assertTrue(all(f["overflow"]["pixels"] == 0 for f in frames))
        with self.condition:
            self.assertTrue(self.condition.wait_for(lambda: any(e["kind"] == "input" and e["value"] == "" for e in self.events), timeout=3))
        self.assertTrue(any(e["kind"] == "click" and e["trusted"] for e in self.events))
        self.assertTrue(any(e["kind"] == "input" and e["trusted"] and e["value"] == text for e in self.events))
        self.assertTrue(any(e["kind"] == "submit" and e["value"] == text for e in self.events))
        self.assertTrue(any(e["kind"] == "escape" and e["trusted"] for e in self.events))
        keys = {e["key"] for e in self.events if e["kind"] == "key" and e["trusted"]}
        self.assertTrue({"Tab", "Enter", "Escape"}.issubset(keys))
        self.assertTrue(any(e["width"] == 390 and e["height"] == 844 and e["reducedMotion"] for e in self.events))
        before = {p.name: p.read_bytes() for p in self.out.iterdir()}
        second = self.run_cli(self.args(url=self.url))
        self.assertNotEqual(second.returncode, 0)
        self.assertIn("refusing overwrite", second.stderr)
        self.assertEqual(before, {p.name: p.read_bytes() for p in self.out.iterdir()})

    def test_real_overflow_and_console_exception_failures_keep_png(self):
        result, report = self.capture(query="?mode=errors")
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(report["status"], "failed")
        self.verify_hashes(report)
        self.assertEqual(len(report["captures"]), 1)
        overflow = report["captures"][0]["overflow"]
        self.assertGreater(overflow["pixels"], 0)
        self.assertEqual(overflow["pixels"], overflow["scrollWidth"] - overflow["clientWidth"])
        self.assertTrue({"overflow", "console", "exception"}.issubset({e["kind"] for e in report["errors"]}))
        self.assertTrue(any("控制台错误 — café" in e["message"] for e in report["errors"]))
        self.assertTrue(any("fixture exception — 中文" in e["message"] for e in report["errors"]))

    def test_real_overflow_alone_exits_nonzero(self):
        result, report = self.capture(query="?mode=overflow")
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(report["status"], "failed")
        self.assertEqual({e["kind"] for e in report["errors"]}, {"overflow"})
        self.verify_hashes(report)

    def test_real_console_error_alone_exits_nonzero(self):
        result, report = self.capture(query="?mode=console")
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(report["status"], "failed")
        self.assertEqual({e["kind"] for e in report["errors"]}, {"console"})
        self.assertEqual(report["captures"][0]["overflow"]["pixels"], 0)
        self.verify_hashes(report)

    def test_real_missing_control_reports_failed_step(self):
        result, report = self.capture([{"action": "click", "selector": "#missing"}])
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(len(report["captures"]), 1)
        self.assertEqual(report["errors"][-1]["step"], 1)
        self.assertIn("exactly one", report["errors"][-1]["message"])
        self.verify_hashes(report)

    def test_real_broken_image_is_not_reported_ready(self):
        result, report = self.capture(query="?mode=broken-image")
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(report["status"], "failed")
        self.assertEqual(report["captures"], [])
        self.assertTrue(any(e["kind"] == "capture" for e in report["errors"]))

    def test_real_readiness_timeout(self):
        started = time.monotonic()
        result, report = self.capture(query="?mode=font-timeout")
        self.assertNotEqual(result.returncode, 0)
        self.assertLess(time.monotonic() - started, 30)
        self.assertEqual(report["captures"], [])
        self.assertTrue(any("Document/font/image readiness timed out" in e["message"] for e in report["errors"]), report["errors"])

    def test_real_non_loopback_redirect_is_blocked(self):
        result, report = self.capture(query="redirect")
        self.assertNotEqual(result.returncode, 0)
        self.assertTrue(any(e["kind"] == "navigation" for e in report["errors"]))


if __name__ == "__main__":
    unittest.main()
