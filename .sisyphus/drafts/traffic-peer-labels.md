# Draft: Traffic Peer Labels

## Requirements (confirmed)
- "정리를 바탕으로 수정 계획 작성하자."
- "코딩 행동 md파일을 읽고 안전하게 계획을 수립해."
- Plan must address Web UI `Traffic Snapshot` peer block labels/visibility based on the provided problem definition.
- Do not implement source changes in this planning step.

## Technical Decisions
- Keep backend/API data shape unchanged: `previous_peer`, `next_peer`, `/api/state` remain intact.
- Plan a Web UI-only rendering change in `web_ui/static/app.js`.
- Host and Monitor should hide meaningless `next_peer` block because it is a `not_applicable` placeholder.
- Local Agent and Relay nodes should retain two peer blocks.
- Fallback for unknown/future node types must render both peer blocks to avoid hiding data.
- Raw recent traffic table remains out of scope unless separately requested.

## Research Findings
- `README.md` is the only markdown file currently present; no separate coding behavior markdown exists in the repo after cleanup.
- `README.md` says Web UI reads JSON API state and `detail.traffic` directly, not TUI output.
- `web_ui/static/app.js:824` contains shared `trafficSection(node)`; line 846 currently renders both peer blocks unconditionally.
- `web_ui/static/app.js:857` contains `trafficPeer(peer, title)`, which can be reused with node-specific titles.
- `nw_demo/host_simulator.py:29-30` sets Host `previous_peer=local-agent`, `next_peer=not_applicable`.
- `nw_demo/monitor.py:39-40` sets Monitor `previous_peer=r2`, `next_peer=not_applicable`; monitor can switch previous peer to `r2b` on backup path.
- `nw_demo/local_agent.py:63-64` uses both peers: Host fetch and Relay event delivery.
- `nw_demo/relay.py:43-55` uses both peers: upstream event receipt and downstream event delivery.
- Existing Python tests assert backend traffic schema/producer semantics; no dedicated static JS unit test was found for Web UI labels.
- Explore confirmed `web_ui/static/app.css` has `.traffic-peers` fixed at two columns and needs a single-peer layout for Host/Monitor if the second block is hidden.
- Explore confirmed `web_ui/static/index.html` exposes browser QA hooks including `data-testid="node-detail-inspector"` and node-card test ids are generated in `app.js` as `node-card-${node.id}`.
- Existing QA command surface: `python -m unittest discover -s tests`, `node --check web_ui/static/app.js`, and browser smoke against `python -m web_ui.server --web-port 8080` or the running server.
- No `package.json`, Playwright/Cypress config, `pyproject.toml`, or dedicated Web UI DOM test suite was found.

## Open Questions
- None currently blocking. User already approved the semantic direction and asked for a plan.

## Scope Boundaries
- INCLUDE: UI-only rendering helper/config for peer block titles/visibility; syntax/browser verification; backend regression tests that protect schema.
- EXCLUDE: Backend data structure changes; API response changes; producer logic changes; raw recent traffic table relabeling; broad detail panel redesign; introducing a new frontend test framework.
