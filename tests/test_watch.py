"""`driftguard watch`: fingerprints of provider pages, served here by a local HTTP server."""

import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

from driftguard import watch
from driftguard.cli import main

PAGES = {}


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        page = PAGES.get(self.path)
        if page is None:
            self.send_response(404)
            self.end_headers()
            return
        status, content_type, body = page
        self.send_response(status)
        if status in (301, 302):
            self.send_header("Location", body)
            self.end_headers()
            return
        self.send_header("Content-Type", content_type)
        self.end_headers()
        self.wfile.write(body.encode("utf-8"))

    def log_message(self, *args):
        pass


@pytest.fixture(scope="module")
def server():
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{httpd.server_address[1]}"
    httpd.shutdown()


@pytest.fixture(autouse=True)
def clean_pages():
    PAGES.clear()
    yield
    PAGES.clear()


def write_config(repo, base, extra=""):
    (repo / ".driftguard.yml").write_text(
        "watch:\n"
        "  - id: pricing\n"
        f"    url: {base}/pricing\n"
        "    why: prices in src/pricing.ts\n"
        "  - id: schema\n"
        f"    url: {base}/log.ts\n"
        "    start: 'export interface Tokens'\n"
        "    end: 'export interface Other'\n" + extra,
        encoding="utf-8",
    )


PRICING_HTML = """<!doctype html><html><head><title>Pricing</title>
<script>window.__BUILD = "abc123";</script><style>.x{color:red}</style></head>
<body><nav>Docs</nav><h1>Pricing</h1><p>Model A: <b>$3</b> / MTok</p><!-- note --></body></html>"""
SCHEMA = "header\nexport interface Tokens {\n  prompt: number;\n}\nexport interface Other {}\n"


def test_readable_text_drops_scripts_styles_tags_and_comments():
    text = watch.readable_text(PRICING_HTML.encode(), "text/html; charset=utf-8")
    assert "abc123" not in text and "color:red" not in text and "note" not in text
    assert "Model A: $3 / MTok" in text
    # Markdown and code keep their lines, without trailing blanks or Windows line ends.
    assert watch.readable_text(b"# T  \r\n\r\nline ", "text/markdown") == "# T\nline"


def test_section_needs_both_markers():
    assert watch.section("a START b END c", "START", "END") == "START b "
    assert watch.section("a START b", "START", "END") is None
    assert watch.section("a b", "START", None) is None
    assert watch.section("a b", None, None) == "a b"


def test_first_run_is_new_then_update_then_unchanged(server, tmp_path, capsys):
    write_config(tmp_path, server)
    PAGES["/pricing"] = (200, "text/html", PRICING_HTML)
    PAGES["/log.ts"] = (200, "text/plain", SCHEMA)

    assert main(["watch", str(tmp_path)]) == 1
    out = capsys.readouterr().out
    assert out.count("new") >= 2 and "driftguard watch . --update" in out

    assert main(["watch", str(tmp_path), "--update"]) == 0
    lock = json.loads((tmp_path / watch.LOCK_FILE).read_text())
    assert set(lock["sources"]) == {"pricing", "schema"}
    assert lock["sources"]["pricing"]["final_url"] == f"{server}/pricing"

    assert main(["watch", str(tmp_path)]) == 0
    assert "0 to review" in capsys.readouterr().out


def test_a_new_build_id_is_not_a_change_but_a_new_price_is(server, tmp_path, capsys):
    write_config(tmp_path, server)
    PAGES["/pricing"] = (200, "text/html", PRICING_HTML)
    PAGES["/log.ts"] = (200, "text/plain", SCHEMA)
    main(["watch", str(tmp_path), "--update"])
    capsys.readouterr()

    PAGES["/pricing"] = (200, "text/html", PRICING_HTML.replace("abc123", "def456"))
    assert main(["watch", str(tmp_path)]) == 0

    PAGES["/pricing"] = (200, "text/html", PRICING_HTML.replace("$3", "$4"))
    assert main(["watch", str(tmp_path)]) == 1
    out = capsys.readouterr().out
    assert "changed" in out and "prices in src/pricing.ts" in out


def test_only_the_section_between_markers_counts(server, tmp_path):
    write_config(tmp_path, server)
    PAGES["/pricing"] = (200, "text/html", PRICING_HTML)
    PAGES["/log.ts"] = (200, "text/plain", SCHEMA)
    main(["watch", str(tmp_path), "--update"])

    PAGES["/log.ts"] = (200, "text/plain", "other header\n" + SCHEMA.split("\n", 1)[1] + "// tail\n")
    assert [r.status for r in watch.run(tmp_path)] == [watch.UNCHANGED, watch.UNCHANGED]

    PAGES["/log.ts"] = (200, "text/plain", SCHEMA.replace("prompt: number", "prompt?: number"))
    assert watch.run(tmp_path)[1].status == watch.CHANGED

    PAGES["/log.ts"] = (200, "text/plain", SCHEMA.replace("export interface Tokens", "type T"))
    assert watch.run(tmp_path)[1].status == watch.NO_SECTION


def test_redirects_missing_pages_and_empty_pages(server, tmp_path, capsys):
    write_config(tmp_path, server)
    PAGES["/pricing"] = (200, "text/html", PRICING_HTML)
    PAGES["/log.ts"] = (200, "text/plain", SCHEMA)
    main(["watch", str(tmp_path), "--update"])

    PAGES["/pricing"] = (301, "", f"{server}/new-pricing")
    PAGES["/new-pricing"] = (200, "text/html", PRICING_HTML)
    del PAGES["/log.ts"]
    results = watch.run(tmp_path)
    assert results[0].status == watch.MOVED and "new-pricing" in results[0].detail
    assert results[1].status == watch.UNREACHABLE and results[1].detail == "HTTP 404"

    PAGES["/pricing"] = (200, "text/html", "<html><body><script>app()</script></body></html>")
    assert watch.run(tmp_path)[0].status == watch.EMPTY

    # --update records what could be read and keeps the last fingerprint of the rest, but still fails.
    before = json.loads((tmp_path / watch.LOCK_FILE).read_text())["sources"]["schema"]
    capsys.readouterr()
    assert main(["watch", str(tmp_path), "--update"]) == 1
    after = json.loads((tmp_path / watch.LOCK_FILE).read_text())["sources"]["schema"]
    assert after == before


def test_github_format_annotates_and_writes_the_summary(server, tmp_path, capsys, monkeypatch):
    write_config(tmp_path, server)
    PAGES["/pricing"] = (200, "text/html", PRICING_HTML)
    summary = tmp_path / "summary.md"
    monkeypatch.setenv("GITHUB_STEP_SUMMARY", str(summary))
    assert main(["watch", str(tmp_path), "--format", "github"]) == 1
    out = capsys.readouterr().out
    assert "::warning title=DriftGuard watch%3A pricing new::" in out
    assert "::error title=DriftGuard watch%3A schema unreachable::" in out
    assert "| 🔴 | [schema]" in summary.read_text()
    assert main(["watch", str(tmp_path), "--no-fail"]) == 0


def test_changing_an_address_in_the_watch_list_asks_for_a_new_fingerprint(server, tmp_path):
    write_config(tmp_path, server)
    PAGES["/pricing"] = (200, "text/html", PRICING_HTML)
    PAGES["/log.ts"] = (200, "text/plain", SCHEMA)
    main(["watch", str(tmp_path), "--update"])
    PAGES["/pricing.md"] = (200, "text/markdown", "# Pricing\nModel A: $3 / MTok\n")
    config = (tmp_path / ".driftguard.yml").read_text().replace("/pricing\n", "/pricing.md\n")
    (tmp_path / ".driftguard.yml").write_text(config)
    result = watch.run(tmp_path)[0]
    assert result.status == watch.NEW and "address changed" in result.detail


def test_a_source_removed_from_the_list_leaves_the_lock_file(server, tmp_path):
    write_config(tmp_path, server)
    PAGES["/pricing"] = (200, "text/html", PRICING_HTML)
    PAGES["/log.ts"] = (200, "text/plain", SCHEMA)
    main(["watch", str(tmp_path), "--update"])
    (tmp_path / ".driftguard.yml").write_text(f"watch:\n  - id: pricing\n    url: {server}/pricing\n")
    main(["watch", str(tmp_path), "--update"])
    assert set(json.loads((tmp_path / watch.LOCK_FILE).read_text())["sources"]) == {"pricing"}


@pytest.mark.parametrize("config, message", [
    ("watch: nope\n", "must be a list"),
    ("watch:\n  - url: https://x\n", "`id`"),
    ("watch:\n  - id: a\n    url: ftp://x\n", "https://"),
    ("watch:\n  - id: a\n    url: https://x\n  - id: a\n    url: https://y\n", "used twice"),
    ("watch: [\n", "not valid YAML"),
])
def test_bad_watch_lists_are_refused(tmp_path, capsys, config, message):
    (tmp_path / ".driftguard.yml").write_text(config)
    assert main(["watch", str(tmp_path)]) == 2
    assert message in capsys.readouterr().err


def test_no_watch_list_is_not_an_error(tmp_path, capsys):
    (tmp_path / ".driftguard.yml").write_text("min_severity: critical\n")
    assert main(["watch", str(tmp_path)]) == 0
    assert "nothing to check" in capsys.readouterr().out


def test_scan_config_still_ignores_the_watch_key(tmp_path):
    from driftguard.config import load_repo_config

    (tmp_path / ".driftguard.yml").write_text("min_severity: critical\nwatch: []\n")
    assert load_repo_config(tmp_path).min_severity == "critical"
