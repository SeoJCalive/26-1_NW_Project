from contextlib import contextmanager
from collections.abc import Generator
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread
from urllib.error import URLError
from urllib.request import urlopen

from playwright.sync_api import FloatRect, expect, sync_playwright


ROOT = Path("/home/tjwocjf0915/workspace/NW_project")
PREVIEW_DIR = ROOT / "docs/reference/ui-preview"
SOURCE = PREVIEW_DIR / "preview.revised.jsx"
EVIDENCE = ROOT / ".sisyphus/evidence"
REMOTE_URL = "http://10.192.20.70:8088/preview.revised.html"
NODE_IDS = ["host-simulator", "local-agent", "r1", "r2", "monitor"]


def check_source_contract():
    source = SOURCE.read_text(encoding="utf-8")
    required = [
        "function reportedStateTone",
        "function ReportedStateBadge",
        "data-reported-state-tone",
        "function NodeInfoRow",
        "data-node-info-row",
        "data-node-info-label",
        "data-node-info-value",
        "data-testid=\"diagram-overlay-host\"",
        "const diagramWidth = 1240;",
        "const diagramHeight = 660;",
        "data-testid=\"detail-inspector-overlay\"",
        "data-overlay=\"diagram\"",
        "data-detail-state={detailState}",
        "@keyframes detailInspectorIn",
        "animation: detailInspectorIn 220ms ease both",
        "detail-inspector-closing",
    ]
    missing = [fragment for fragment in required if fragment not in source]
    assert missing == [], missing
    assert 'xl:grid-cols-[minmax(0,1fr)_minmax(360px,33vw)]' not in source
    assert "reportedStateTone(node.reported_state)" in source
    assert "livenessLampTone(node.reported_state)" not in source
    (EVIDENCE / "task-4-reported-card-overlay-static-check.txt").write_text(
        "PASS static reported-state/card/overlay source contract\n",
        encoding="utf-8",
    )


def remote_available():
    try:
        with urlopen(REMOTE_URL, timeout=2) as response:
            return response.status == 200
    except (OSError, URLError):
        return False


@contextmanager
def preview_url() -> Generator[str, None, None]:
    if remote_available():
        yield REMOTE_URL
        return

    server = ThreadingHTTPServer(("127.0.0.1", 0), lambda *args, **kwargs: SimpleHTTPRequestHandler(*args, directory=str(PREVIEW_DIR), **kwargs))
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}/preview.revised.html"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def assert_stable_box(before: FloatRect | None, after: FloatRect | None) -> None:
    assert before is not None and after is not None
    for key in ["width", "height"]:
        delta = abs(float(before[key]) - float(after[key]))
        assert delta <= 2, {"key": key, "before": before[key], "after": after[key], "delta": delta}


def check_browser_contract(url: str) -> None:
    console_messages = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, executable_path="/snap/bin/chromium")
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        page.on("console", lambda msg: console_messages.append(f"{msg.type}: {msg.text}"))
        _ = page.goto(url, wait_until="networkidle")

        expect(page.locator('[data-testid="node-detail-inspector"]')).to_have_count(0)
        diagram_before = page.locator('[data-testid="diagram-overlay-host"]').bounding_box()
        assert diagram_before is not None
        assert 1230 <= diagram_before["width"] <= 1250, diagram_before
        assert 650 <= diagram_before["height"] <= 670, diagram_before
        for node_id in NODE_IDS:
            expect(page.locator(f'[data-testid="node-card-{node_id}"]')).to_have_count(1)
            expect(page.locator(f'[data-testid="node-card-rows-{node_id}"]')).to_have_count(1)
            for row in ["node-id", "role", "observed-liveness", "reported-state"]:
                expect(page.locator(f'[data-testid="node-info-row-{node_id}-{row}"]')).to_have_count(1)
            expect(page.locator(f'[data-testid="liveness-lamp-{node_id}"]')).to_have_count(1)
            expect(page.locator(f'[data-testid="reported-state-{node_id}"]')).to_have_count(1)
            expect(page.locator(f'[data-testid="reported-state-{node_id}"]')).to_have_attribute("data-reported-state-tone", "running")
            expect(page.locator(f'[data-testid="node-role-{node_id}"]')).to_have_count(1)
            expect(page.locator(f'[data-testid^="activity-chip-{node_id}-"]').first).to_be_visible()

        r2_tone = page.locator('[data-testid="liveness-lamp-r2"]').get_attribute("data-liveness-tone")
        r2_reported_tone = page.locator('[data-testid="reported-state-r2"]').get_attribute("data-reported-state-tone")
        assert r2_tone == "gray", r2_tone
        assert r2_reported_tone == "running", r2_reported_tone

        page.locator('[data-testid="node-card-r1"]').click()
        expect(page.locator('[data-testid="node-detail-inspector"]')).to_be_visible()
        expect(page.locator('[data-testid="node-detail-inspector"]')).to_have_attribute("data-overlay", "diagram")
        expect(page.locator('[data-testid="node-detail-inspector"]')).to_have_attribute("data-detail-state", "open")
        open_animation = page.locator('[data-testid="node-detail-inspector"]').evaluate("el => getComputedStyle(el).animationName")
        assert open_animation == "detailInspectorIn", open_animation
        expect(page.locator('[data-testid="detail-inspector-overlay"]')).to_be_visible()
        overlay_overflow_y = page.locator('[data-testid="detail-inspector-overlay"]').evaluate("el => getComputedStyle(el).overflowY")
        assert overlay_overflow_y == "auto", overlay_overflow_y
        overlay_box = page.locator('[data-testid="node-detail-inspector"]').bounding_box()
        assert overlay_box is not None
        assert 610 <= overlay_box["height"] <= 640, overlay_box
        expect(page.locator('[data-testid="relay-detail-r1"]')).to_be_visible()
        diagram_after_open = page.locator('[data-testid="diagram-overlay-host"]').bounding_box()
        assert_stable_box(diagram_before, diagram_after_open)

        expected_details = [
            ("host-simulator", "host-detail"),
            ("local-agent", "agent-detail"),
            ("r1", "relay-detail-r1"),
            ("r2", "relay-detail-r2"),
            ("monitor", "monitor-detail"),
        ]
        for node_id, detail_id in expected_details:
            if page.locator('[data-testid="node-detail-inspector"]').count():
                page.locator('[data-testid="detail-close-button"]').click()
                page.wait_for_timeout(260)
            page.locator(f'[data-testid="node-card-{node_id}"]').click()
            expect(page.locator('[data-testid="node-detail-inspector"]')).to_be_visible()
            expect(page.locator(f'[data-testid="detail-node-role-{node_id}"]')).to_have_count(1)
            expect(page.locator(f'[data-testid="{detail_id}"]')).to_be_visible()
            assert_stable_box(diagram_before, page.locator('[data-testid="diagram-overlay-host"]').bounding_box())

        expect(page.locator("text=peer_role").first).to_be_visible()
        inspector_box = page.locator('[data-testid="node-detail-inspector"]').bounding_box()
        assert inspector_box is not None
        width_ratio = inspector_box["width"] / 1440
        assert 0.28 <= width_ratio <= 0.38, width_ratio
        body = page.locator("body").inner_text()
        forbidden = ["비고", "설명", "activityLogs", "description", "state=", "state =", "attempt=", "attempt =", "queue=", "pending=", "retries=", "dup=", "Controller/UI", "Reporting Hub", "Control Hub", "Management Node"]
        findings = [token for token in forbidden if token in body]
        assert findings == [], findings

        page.locator('[data-testid="detail-close-button"]').click()
        expect(page.locator('[data-testid="node-detail-inspector"]')).to_have_attribute("data-detail-state", "closing")
        page.wait_for_timeout(260)
        expect(page.locator('[data-testid="node-detail-inspector"]')).to_have_count(0)
        assert_stable_box(diagram_before, page.locator('[data-testid="diagram-overlay-host"]').bounding_box())

        (EVIDENCE / "task-4-reported-card-overlay-dom.html").write_text(page.content(), encoding="utf-8")
        (EVIDENCE / "task-4-reported-card-overlay-browser-check.txt").write_text(
            "\n".join([
                "PASS reported-state card overlay browser contract",
                f"url={url}",
                f"inspector_width_ratio={width_ratio:.3f}",
                f"open_animation={open_animation}",
                f"overlay_overflow_y={overlay_overflow_y}",
                f"overlay_height={overlay_box['height']:.1f}",
                f"diagram_width={diagram_before['width']:.1f}",
                f"diagram_height={diagram_before['height']:.1f}",
                *console_messages,
            ]),
            encoding="utf-8",
        )
        page.screenshot(path=str(EVIDENCE / "task-4-reported-card-overlay-preview.png"), full_page=True)
        browser.close()


check_source_contract()
with preview_url() as actual_url:
    check_browser_contract(actual_url)
print("PASS reported-state card overlay preview contract")
