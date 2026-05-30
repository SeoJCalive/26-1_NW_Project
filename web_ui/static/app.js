const DIAGRAM_WIDTH = 1460;
const DIAGRAM_HEIGHT = 700;
const NODE_CARD_WIDTH = 166;
const PATH_LABEL_HORIZONTAL_PADDING = 10;
const MISSING_VALUE = "—";
const JSON_BLOCK_ROW = "json-block";
const NODE_ORDER = ["host-simulator", "local-agent", "r1", "r2", "monitor", "r1b", "r2b"];
const NODE_POSITIONS = {
  "host-simulator": { x: 80, y: 100 },
  "local-agent": { x: 365, y: 255 },
  r1: { x: 655, y: 255 },
  r2: { x: 945, y: 155 },
  monitor: { x: 1215, y: 100 },
  r1b: { x: 655, y: 460 },
  r2b: { x: 945, y: 460 },
};
const NODE_META = {
  "host-simulator": { role: "Host Simulator", displayName: "호스트 시뮬레이터" },
  "local-agent": { role: "Local Agent", displayName: "로컬 에이전트" },
  r1: { role: "Relay", displayName: "릴레이 R1" },
  r2: { role: "Relay", displayName: "릴레이 R2" },
  monitor: { role: "Monitor", displayName: "모니터" },
  r1b: { role: "Relay", displayName: "릴레이 R1B" },
  r2b: { role: "Relay", displayName: "릴레이 R2B" },
};
const FAULT_CONTROLS = [
  { key: "cpu", type: "CPU_SPIKE", label: "CPU 장애" },
  { key: "service", type: "SERVICE_DOWN", label: "서비스 중단" },
  { key: "latency", type: "LATENCY_HIGH", label: "지연 증가" },
];
const POWER_START_COOLDOWN_MS = 6000;
const POWER_STOP_COOLDOWN_MS = 4000;
const RECENT_TRANSFER_HOLD_MS = 3000;
const MAIN_LINKS = [
  { id: "host-agent", from: "host-simulator", to: "local-agent", label: "상태 수집", labelOffsetY: -22 },
  { id: "agent-r1", from: "local-agent", to: "r1", label: "EVENT 전달", labelOffsetY: -24 },
  { id: "r1-r2", from: "r1", to: "r2", label: "EVENT 중계", labelOffsetY: -28 },
  { id: "r2-monitor", from: "r2", to: "monitor", label: "Monitor 전달", labelOffsetY: -30 },
  { id: "agent-r1b", from: "local-agent", to: "r1b", label: "backup 진입", labelOffsetY: 34 },
  { id: "r1b-r2b", from: "r1b", to: "r2b", label: "backup 중계", labelOffsetY: 34 },
  { id: "r2b-monitor", from: "r2b", to: "monitor", label: "backup Monitor", labelOffsetY: 34 },
];
const HOP_STATE_TONE = {
  acknowledged: "ok",
  request_received: "active",
  request_sent: "active",
  pending: "active",
  retrying: "warn",
  timeout: "down",
  connection_error: "down",
  ack_dropped: "down",
  delivery_failed: "down",
  rejected: "down",
  invalid_response: "warn",
  paused: "muted",
  idle: "idle",
  not_started: "muted",
  unknown: "muted",
  not_applicable: "muted",
};
const HOP_TONE_PRIORITY = { down: 5, warn: 4, active: 3, ok: 2, idle: 1, muted: 0 };
const FRESH_ENDPOINT_STATES = new Set(["live", "kill_requested"]);
const RECENT_TRANSFER_STATES = { request_sent: true, request_received: true };
const ROUTE_ACTIVE_STATES = { PRIMARY: true, BYPASS_ACTIVE: true };
const ROUTE_LINK_GROUPS = {
  "host-agent": "shared",
  "agent-r1": "primary",
  "r1-r2": "primary",
  "r2-monitor": "primary",
  "agent-r1b": "backup",
  "r1b-r2b": "backup",
  "r2b-monitor": "backup",
};

const summaryMetrics = document.querySelector("#summary-metrics");
const dataPath = document.querySelector("#data-path");
const nodeLayer = document.querySelector("#node-layer");
const detailInspector = document.querySelector("#detail-inspector");
const detailInspectorInner = document.querySelector("#detail-inspector-inner");
const runtimeStatus = document.querySelector("#runtime-status");
const faultSwitches = document.querySelector("#fault-switches");
const nodeSwitches = document.querySelector("#node-switches");
const nodePowerButton = document.querySelector("#node-power-button");
const nodePowerLabel = document.querySelector("#node-power-label");
const nodePowerHint = document.querySelector("#node-power-hint");

let latestState = null;
let selectedNodeId = null;
let detailNodeId = null;
let detailState = "closed";
let renderedDetailNodeId = null;
let closeTimer = null;
let powerLockUntil = 0;
let powerActionInFlight = false;

function escapeHtml(value) {
  return formatScalar(value)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

function formatScalar(value) {
  if (value === null || value === undefined || value === "") return MISSING_VALUE;
  if (typeof value === "boolean") return value ? "true" : "false";
  if (Array.isArray(value)) return value.length ? value.join(", ") : MISSING_VALUE;
  if (typeof value === "object") return compactObject(value);
  return String(value);
}

function compactObject(value) {
  try {
    return JSON.stringify(value);
  } catch (error) {
    return String(value);
  }
}

function formatJsonBlock(value) {
  if (value === null || value === undefined || value === "") return MISSING_VALUE;
  let parsed = value;
  if (typeof value === "string") {
    const trimmed = value.trim();
    if (trimmed[0] === "{" || trimmed[0] === "[") {
      try {
        parsed = JSON.parse(trimmed);
      } catch (error) {
        return value;
      }
    }
  }
  if (typeof parsed !== "object") return formatScalar(parsed);
  try {
    return JSON.stringify(parsed, null, 2);
  } catch (error) {
    return String(parsed);
  }
}

function getNested(source, path, fallback) {
  let current = source;
  for (let index = 0; index < path.length; index += 1) {
    if (current === null || current === undefined || typeof current !== "object") return fallback;
    current = current[path[index]];
  }
  return current === undefined ? fallback : current;
}

function lastSeenText(value) {
  if (value === null || value === undefined) return "never";
  if (typeof value === "number") return `${Math.max(0, value).toFixed(1)}s ago`;
  return String(value);
}

function elapsedSince(lastSeen, generatedAt) {
  if (typeof lastSeen !== "number") return lastSeenText(lastSeen);
  if (typeof generatedAt !== "number") return lastSeenText(lastSeen);
  return `${Math.max(0, generatedAt - lastSeen).toFixed(1)}s ago`;
}

function nodeCenter(node) {
  return { x: node.position.x + NODE_CARD_WIDTH / 2, y: node.position.y + 64 };
}

function buildMainPath(link, nodesById) {
  const from = nodeCenter(nodesById[link.from]);
  const to = nodeCenter(nodesById[link.to]);
  const midX = Math.round((from.x + to.x) / 2);
  return `M ${from.x} ${from.y} C ${midX} ${from.y}, ${midX} ${to.y}, ${to.x} ${to.y}`;
}

function linkLabelPosition(link, nodesById) {
  const from = nodeCenter(nodesById[link.from]);
  const to = nodeCenter(nodesById[link.to]);
  return {
    x: Math.round((from.x + to.x) / 2),
    y: Math.round((from.y + to.y) / 2 + (link.labelOffsetY || -24)),
  };
}

function peerStateForLink(source, peerKey, peerId) {
  const peer = trafficOf(source)[peerKey] || {};
  if (peer.peer_node_id !== peerId) return null;
  return peer.hop_state || "unknown";
}

function linkHopState(link, nodesById) {
  const fromNode = nodesById[link.from];
  const toNode = nodesById[link.to];
  const candidates = [
    peerStateForLink(fromNode, "next_peer", link.to),
    peerStateForLink(toNode, "previous_peer", link.from),
  ].filter(function keep(value) { return value; });
  if (!candidates.length) return "unknown";
  return candidates.reduce(function chooseWorst(current, next) {
    return HOP_TONE_PRIORITY[hopTone(next)] > HOP_TONE_PRIORITY[hopTone(current)] ? next : current;
  });
}

function hopTone(state) {
  return HOP_STATE_TONE[state] || "muted";
}

function monitorRouteSummary(adapted) {
  return getNested(adapted, ["nodesById", "monitor", "runtime", "details", "detail", "last_route_summary"], null);
}

function routeGroupForLink(link) {
  return ROUTE_LINK_GROUPS[link.id] || "unknown";
}

function isKnownRouteSummary(summary) {
  if (!summary || typeof summary !== "object") return false;
  if (summary.active_route !== "primary" && summary.active_route !== "backup") return false;
  return ROUTE_ACTIVE_STATES[summary.route_state] === true;
}

function routeActiveForLink(link, summary) {
  const group = routeGroupForLink(link);
  if (!isKnownRouteSummary(summary)) return "unknown";
  if (group === "shared") return "shared";
  return group === summary.active_route ? "true" : "false";
}

function overviewToneForLink(rawHopState, rawTone, routeActive) {
  if (routeActive === "false" && rawHopState === "acknowledged" && rawTone === "ok") return "inactive";
  return rawTone;
}

function linkEndpointFreshness(link, nodesById) {
  const fromNode = nodesById[link.from];
  const toNode = nodesById[link.to];
  if (!fromNode || !toNode) return "unknown";
  const states = [fromNode.observed_liveness, toNode.observed_liveness];
  if (states[0] === "offline" || states[1] === "offline") return "offline";
  if (states[0] === "stale" || states[1] === "stale") return "stale";
  if (FRESH_ENDPOINT_STATES.has(states[0]) && FRESH_ENDPOINT_STATES.has(states[1])) return "fresh";
  return "unknown";
}

function isFreshnessOverlayAllowed(tone, linkFreshness, lifecycleOverride) {
  if (lifecycleOverride) return false;
  if (linkFreshness !== "stale" && linkFreshness !== "offline") return false;
  return tone === "ok" || tone === "idle";
}

function freshnessOverlayLabel(linkFreshness) {
  if (linkFreshness === "stale") return "최근 상태 없음";
  if (linkFreshness === "offline") return "엔드포인트 오프라인";
  return null;
}

function captureAgeMs(capture) {
  if (!capture || typeof capture !== "object") return null;
  const capturedAt = Date.parse(capture.captured_at);
  if (!Number.isFinite(capturedAt)) return null;
  return Math.max(0, Date.now() - capturedAt);
}

function collectRecentTransfers(node, peerId, result) {
  const recent = trafficOf(node).recent;
  if (!Array.isArray(recent)) return;
  recent.forEach(function collect(item) {
    if (!item || item.peer_node_id !== peerId || !RECENT_TRANSFER_STATES[item.hop_state]) return;
    const ageMs = captureAgeMs(item.capture);
    if (ageMs === null || ageMs > RECENT_TRANSFER_HOLD_MS) return;
    result.push({ state: item.hop_state, flow: item.flow, phase: getNested(item, ["capture", "phase"], null), ageMs: ageMs });
  });
}

function recentTransferForLink(link, nodesById) {
  const candidates = [];
  collectRecentTransfers(nodesById[link.from], link.to, candidates);
  collectRecentTransfers(nodesById[link.to], link.from, candidates);
  if (!candidates.length) return null;
  return candidates.reduce(function chooseNewest(current, next) {
    return next.ageMs < current.ageMs ? next : current;
  });
}

function pathLifecycleOverride() {
  const state = getNested(latestState, ["node_power", "state"], null);
  if (state === "stopped") {
    return {
      hopState: "stopped",
      rawTone: "muted",
      routeActive: "lifecycle",
      tone: "inactive",
      label: "전원 꺼짐",
      flow: false,
    };
  }
  if (state === "transitioning") {
    return {
      hopState: "transitioning",
      rawTone: "muted",
      routeActive: "lifecycle",
      tone: "inactive",
      label: "전원 전환 중",
      flow: false,
    };
  }
  return null;
}

function markerForTone(tone) {
  if (tone === "down") return "url(#arrow-red)";
  if (tone === "warn") return "url(#arrow-orange)";
  if (tone === "ok") return "url(#arrow-green)";
  if (tone === "active") return "url(#arrow-blue)";
  return "url(#arrow-gray)";
}

function linkStatusLabel(link, hopState, routeActive) {
  if (hopState === "acknowledged" && routeActive === "false") return "비활성 경로";
  if (hopState === "acknowledged") return `${link.label} 완료`;
  if (hopState === "request_sent" || hopState === "request_received") return `${link.label} 중`;
  if (hopState === "pending") return ackWaitLabel(link);
  if (hopState === "retrying") return retryLabel(link);
  if (hopState === "ack_dropped") return "ACK 드롭";
  if (hopState === "timeout") return "응답 시간초과";
  if (hopState === "connection_error") return "연결 실패";
  if (hopState === "delivery_failed" || hopState === "rejected") return "전달 실패";
  if (hopState === "invalid_response") return "응답 이상";
  if (hopState === "idle") return `${link.label} 대기`;
  if (hopState === "paused") return "정지";
  if (hopState === "not_started") return "시작 전";
  if (hopState === "not_applicable") return "해당 없음";
  return "상태 확인 중";
}

function ackWaitLabel(link) {
  if (link.id === "agent-r1") return "R1 ACK 대기";
  if (link.id === "r1-r2") return "R2 ACK 대기";
  if (link.id === "r2-monitor") return "Monitor ACK 대기";
  return "상태 응답 대기";
}

function retryLabel(link) {
  if (link.id === "agent-r1") return "R1 재전송 중";
  if (link.id === "r1-r2") return "R2 재전송 중";
  if (link.id === "r2-monitor") return "Monitor 재전송 중";
  return "재시도 중";
}

function connectionTone(value) {
  return value === "live" ? "is-connected" : "is-disconnected";
}

function connectionLabel(value) {
  return value === "live" ? "연결됨" : "단절됨";
}

function stateBadgeTone(value) {
  return value === "RUNNING" || value === "실행 중" ? "" : "is-muted";
}

function reportedStateTone(value) {
  return value === "RUNNING" || value === "실행 중" ? "is-running" : "is-muted";
}

function reportedStateLabel(value) {
  return value === "일시정지" ? "정지" : value;
}

function isNodeRunning(node) {
  return node.reported_state === "RUNNING" || node.reported_state === "실행 중";
}

function commandTargetForNode(nodeId) {
  if (nodeId === "host-simulator") return "host";
  if (nodeId === "local-agent") return "agent";
  return nodeId;
}

function currentInjectionType(adapted) {
  const host = adapted.nodesById["host-simulator"];
  return getNested(host, ["runtime", "details", "detail", "fault_type"], null);
}

function liveNodeCount(adapted) {
  return adapted.nodes.filter(function countLive(node) { return node.observed_liveness === "live"; }).length;
}

function nodePowerState(adapted) {
  const apiPower = latestState && latestState.node_power ? latestState.node_power : {};
  const liveCount = liveNodeCount(adapted);
  if (apiPower.state === "transitioning") return "transitioning";
  if (apiPower.state === "stopped") return "stopped";
  if (apiPower.state === "external") return liveCount > 0 ? "running" : "external";
  if (liveCount === adapted.nodes.length && adapted.nodes.length > 0) return "running";
  if (liveCount === 0) return "stopped";
  return "partial";
}

function nextPowerAction(adapted) {
  const state = nodePowerState(adapted);
  return state === "running" || state === "partial" ? "stop" : "start";
}

function powerButtonLocked() {
  return powerActionInFlight || Date.now() < powerLockUntil;
}

function trafficOf(node) {
  return getNested(node, ["runtime", "details", "detail", "traffic"], emptyTraffic());
}

function emptyPeer(role) {
  return {
    peer_node_id: MISSING_VALUE,
    peer_role: role || "not_applicable",
    hop_state: "not_applicable",
    failure_reason: MISSING_VALUE,
    last_received: MISSING_VALUE,
    last_sent: MISSING_VALUE,
  };
}

function emptyTraffic() {
  return {
    capture_seq: MISSING_VALUE,
    captured_at: MISSING_VALUE,
    previous_peer: emptyPeer(),
    next_peer: emptyPeer(),
    recent: [],
  };
}

function adaptState(apiState) {
  const sourceNodes = Array.isArray(apiState && apiState.nodes) ? apiState.nodes : [];
  const generatedAt = apiState ? apiState.generated_at_monotonic : null;
  const byId = {};
  for (let index = 0; index < sourceNodes.length; index += 1) {
    byId[sourceNodes[index].node_id] = sourceNodes[index];
  }
  const nodes = NODE_ORDER.map(function mapNode(nodeId) {
    const runtime = byId[nodeId] || { node_id: nodeId, details: {} };
    const meta = NODE_META[nodeId];
    return {
      id: nodeId,
      role: meta.role,
      displayName: meta.displayName,
      position: NODE_POSITIONS[nodeId],
      observed_liveness: runtime.observed_liveness || "unknown",
      reported_state: runtime.reported_state || "UNKNOWN",
      last_seen: elapsedSince(runtime.last_seen, generatedAt),
      queue_length: runtime.queue_length || 0,
      pending_ack_count: runtime.pending_ack_count || 0,
      retry_total: runtime.retry_total || 0,
      duplicate_dropped: runtime.duplicate_dropped || 0,
      note: runtime.note || MISSING_VALUE,
      runtime: runtime,
    };
  });
  const adaptedById = {};
  nodes.forEach(function setById(node) { adaptedById[node.id] = node; });
  return { nodes: nodes, nodesById: adaptedById };
}

function activityChips(node) {
  const detail = getNested(node, ["runtime", "details", "detail"], {});
  if (node.id === "host-simulator") {
    const hostState = detail.host_state || getNested(node, ["runtime", "details", "host_state"], {});
    return [
      ["cpu", "CPU", hostState.cpu_usage === undefined ? MISSING_VALUE : `${hostState.cpu_usage}%`],
      ["memory", "메모리", hostState.memory_usage === undefined ? MISSING_VALUE : `${hostState.memory_usage}%`],
      ["latency", "latency", hostState.latency_ms === undefined ? MISSING_VALUE : `${hostState.latency_ms}ms`],
      ["service", "service", hostState.service_state || MISSING_VALUE],
    ];
  }
  if (node.id === "local-agent") {
    return [
      ["input", "입력", getNested(detail, ["latest_input_result", "status"], MISSING_VALUE)],
      ["fault", "fault", detail.detected_fault],
      ["downstream", "downstream", getNested(detail, ["downstream_result", "status"], MISSING_VALUE)],
      ["event", "event", joinPresent([getNested(detail, ["emitted_event", "event_type"], null), getNested(detail, ["emitted_event", "severity"], null)])],
    ];
  }
  if (node.role === "Relay") {
    const pending = Array.isArray(detail.pending_ack_state) ? detail.pending_ack_state[0] || {} : {};
    return [
      ["ack-count", "ACK 대기 수", node.pending_ack_count],
      ["retry-total", "retry", node.retry_total],
      ["dedup", "dedup", node.duplicate_dropped],
      ["ack-current", "ACK 항목", joinPresent([pending.state, pending.attempt])],
    ];
  }
  return [
    ["logged", "logged", getNested(node, ["runtime", "details", "total_logged"], getNested(detail, ["total_logged"], 0))],
    ["duplicate", "duplicate", getNested(node, ["runtime", "details", "duplicate_count"], getNested(detail, ["duplicate_count"], 0))],
    ["order", "order", getNested(node, ["runtime", "details", "out_of_order_count"], getNested(detail, ["out_of_order_count"], 0))],
    ["sink", "sink", getNested(detail, ["last_sink_result", "status"], MISSING_VALUE)],
  ];
}

function cardSignal(node) {
  const chips = activityChips(node);
  if (node.id === "host-simulator") {
    return joinPresent([chips[0] && chips[0][2], chips[1] && chips[1][2]]);
  }
  if (node.id === "local-agent") {
    return joinPresent([chips[1] && chips[1][2], chips[2] && chips[2][2]]);
  }
  if (node.role === "Relay") {
    return joinPresent([`ACK ${node.pending_ack_count}`, `retry ${node.retry_total}`]);
  }
  return joinPresent([chips[0] && `logged ${chips[0][2]}`, chips[3] && chips[3][2]]);
}

function joinPresent(values) {
  const filtered = values.filter(function keep(value) {
    return value !== null && value !== undefined && value !== "" && value !== MISSING_VALUE;
  });
  return filtered.length ? filtered.join(" · ") : MISSING_VALUE;
}

function renderSummary(adapted) {
  const liveCount = adapted.nodes.filter(function isLive(node) { return node.observed_liveness === "live"; }).length;
  const retryTotal = adapted.nodes.filter(function relay(node) { return node.role === "Relay"; }).reduce(function sum(total, node) { return total + Number(node.retry_total || 0); }, 0);
  const monitor = adapted.nodesById.monitor;
  const duplicateTotal = getNested(monitor, ["runtime", "details", "duplicate_count"], getNested(monitor, ["runtime", "details", "detail", "duplicate_count"], 0));
  const cards = [["관찰 노드", adapted.nodes.length], ["연결됨", liveCount], ["retry", retryTotal], ["duplicate", duplicateTotal]];
  summaryMetrics.innerHTML = cards.map(function card(pair) {
    return `<div class="summary-metric"><span>${escapeHtml(pair[0])}</span><strong>${escapeHtml(pair[1])}</strong></div>`;
  }).join("");
}

function renderPaths(adapted) {
  dataPath.innerHTML = "";
  const routeSummary = monitorRouteSummary(adapted);
  const lifecycleOverride = pathLifecycleOverride();
  MAIN_LINKS.forEach(function renderLink(link) {
    const path = buildMainPath(link, adapted.nodesById);
    const labelPosition = linkLabelPosition(link, adapted.nodesById);
    const hopState = linkHopState(link, adapted.nodesById);
    const rawTone = hopTone(hopState);
    const routeActive = lifecycleOverride ? lifecycleOverride.routeActive : routeActiveForLink(link, routeSummary);
    const tone = lifecycleOverride ? lifecycleOverride.tone : overviewToneForLink(hopState, rawTone, routeActive);
    const linkFreshness = linkEndpointFreshness(link, adapted.nodesById);
    const freshnessOverlay = isFreshnessOverlayAllowed(tone, linkFreshness, lifecycleOverride);
    const label = freshnessOverlay ? freshnessOverlayLabel(linkFreshness) : lifecycleOverride ? lifecycleOverride.label : linkStatusLabel(link, hopState, routeActive);
    const recentTransfer = !lifecycleOverride && tone === "ok" && linkFreshness === "fresh" ? recentTransferForLink(link, adapted.nodesById) : null;
    const shouldFlow = lifecycleOverride ? lifecycleOverride.flow : tone === "active" || tone === "warn";
    const group = document.createElementNS("http://www.w3.org/2000/svg", "g");
    group.dataset.linkId = link.id;
    group.dataset.hopState = hopState;
    group.dataset.rawHopTone = rawTone;
    group.dataset.routeActive = routeActive;
    group.dataset.hopTone = tone;
    group.dataset.displayHopState = lifecycleOverride ? lifecycleOverride.hopState : hopState;
    group.dataset.linkFreshness = linkFreshness;
    group.dataset.linkFreshnessOverlay = freshnessOverlay ? "true" : "false";
    group.dataset.recentTransfer = recentTransfer ? "true" : "false";
    if (recentTransfer) {
      group.dataset.recentTransferState = recentTransfer.state;
      group.dataset.recentTransferFlow = recentTransfer.flow || "unknown";
    }
    const title = document.createElementNS("http://www.w3.org/2000/svg", "title");
    title.textContent = `${label}: raw=${hopState}/${rawTone}, route=${routeActive}, overview=${tone}, freshness=${linkFreshness}/${freshnessOverlay ? "overlay" : "no-overlay"}${recentTransfer ? `, recent=${recentTransfer.state}/${recentTransfer.phase || recentTransfer.flow || "unknown"}` : ""}`;
    const halo = document.createElementNS("http://www.w3.org/2000/svg", "path");
    halo.setAttribute("d", path);
    halo.setAttribute("class", "path-halo");
    halo.setAttribute("stroke-width", "18");
    halo.setAttribute("stroke-linecap", "round");
    const line = document.createElementNS("http://www.w3.org/2000/svg", "path");
    line.setAttribute("d", path);
    line.setAttribute("class", "path-line");
    line.setAttribute("stroke-width", "5");
    line.setAttribute("stroke-linecap", "round");
    line.setAttribute("marker-end", markerForTone(tone));
    if (shouldFlow) {
      line.classList.add("path-flow");
    }
    const labelGroup = document.createElementNS("http://www.w3.org/2000/svg", "g");
    labelGroup.setAttribute("class", "path-status-label");
    labelGroup.setAttribute("transform", `translate(${labelPosition.x}, ${labelPosition.y})`);
    const labelBackground = document.createElementNS("http://www.w3.org/2000/svg", "rect");
    labelBackground.setAttribute("y", "-14");
    labelBackground.setAttribute("height", "24");
    labelBackground.setAttribute("rx", "12");
    const labelText = document.createElementNS("http://www.w3.org/2000/svg", "text");
    labelText.setAttribute("text-anchor", "middle");
    labelText.setAttribute("dominant-baseline", "middle");
    labelText.textContent = label;
    group.appendChild(title);
    group.appendChild(halo);
    group.appendChild(line);
    labelGroup.appendChild(labelBackground);
    labelGroup.appendChild(labelText);
    group.appendChild(labelGroup);
    dataPath.appendChild(group);
    const measuredTextWidth = labelText.getComputedTextLength();
    const labelWidth = Math.ceil(measuredTextWidth + PATH_LABEL_HORIZONTAL_PADDING * 2);
    labelBackground.setAttribute("x", String(-labelWidth / 2));
    labelBackground.setAttribute("width", String(labelWidth));
  });
}

function renderNodes(adapted) {
  nodeLayer.innerHTML = "";
  adapted.nodes.forEach(function renderNode(node) {
    const card = document.createElement("button");
    card.type = "button";
    card.className = `node-card${selectedNodeId === node.id ? " is-selected" : ""}`;
    card.dataset.testid = `node-card-${node.id}`;
    card.dataset.nodeId = node.id;
    card.style.left = `${node.position.x}px`;
    card.style.top = `${node.position.y}px`;
    card.addEventListener("click", function onClick() { selectNode(node.id); });
    const chipRows = node.id === "host-simulator" ? activityChips(node) : activityChips(node).slice(0, 2);
    const chips = chipRows.map(function chip(row) {
      return nodeInfoRow(row[1], row[2]);
    }).join("");
    card.innerHTML = `
      <div class="node-card-top">
        ${reportedStateLamp(node.reported_state)}
        ${connectionLamp(node.observed_liveness)}
      </div>
      <div class="node-title-block">
        <div class="node-name">${escapeHtml(node.displayName)}</div>
        <div class="node-role-line">${escapeHtml(node.role)}</div>
      </div>
      <div class="node-info-box">
        ${chips || nodeInfoRow("핵심 신호", cardSignal(node))}
      </div>
    `;
    nodeLayer.appendChild(card);
  });
}

function connectionLamp(value) {
  return `<span class="lamp-wrap connection-lamp" data-liveness-state="${escapeHtml(value)}" data-connection-tone="${value === "live" ? "connected" : "disconnected"}"><i class="lamp ${connectionTone(value)}"></i>${connectionLabel(value)}</span>`;
}

function reportedStateLamp(value) {
  const tone = stateBadgeTone(value) ? "not-running" : "running";
  return `<span class="lamp-wrap state-lamp" data-reported-state-tone="${tone}"><i class="lamp ${reportedStateTone(value)}"></i>${escapeHtml(reportedStateLabel(value))}</span>`;
}

function stateBadge(value) {
  return `<span class="state-badge ${stateBadgeTone(value)}" data-reported-state-tone="${stateBadgeTone(value) ? "unknown" : "running"}">${escapeHtml(reportedStateLabel(value))}</span>`;
}

function nodeInfoRow(label, value, valueIsHtml) {
  return `<div class="node-info-row"><span>${escapeHtml(label)}</span><span>${valueIsHtml ? value : escapeHtml(value)}</span></div>`;
}

function selectNode(nodeId) {
  if (closeTimer) window.clearTimeout(closeTimer);
  selectedNodeId = nodeId;
  detailNodeId = nodeId;
  detailState = "open";
  renderLatest();
}

function closeDetail() {
  detailState = "closing";
  updateDetailState();
  closeTimer = window.setTimeout(function clearDetail() {
    selectedNodeId = null;
    detailNodeId = null;
    detailState = "closed";
    closeTimer = null;
    renderLatest();
  }, 220);
}

function updateDetailState() {
  detailInspector.dataset.detailState = detailState;
  detailInspector.hidden = detailState === "closed";
}

function captureDetailScrollState(nodeId) {
  if (renderedDetailNodeId !== nodeId) return null;
  return {
    scrollTop: detailInspectorInner.scrollTop,
    tables: Array.from(detailInspectorInner.querySelectorAll(".data-table-wrap")).map(function tableScroll(table) {
      return { scrollLeft: table.scrollLeft, scrollTop: table.scrollTop };
    }),
    jsonBlocks: Array.from(detailInspectorInner.querySelectorAll(".json-block-value")).map(function jsonBlockState(block) {
      return { height: block.getBoundingClientRect().height, scrollLeft: block.scrollLeft, scrollTop: block.scrollTop };
    }),
  };
}

function restoreDetailScrollState(state) {
  if (!state) return;
  detailInspectorInner.scrollTop = state.scrollTop;
  Array.from(detailInspectorInner.querySelectorAll(".data-table-wrap")).forEach(function restoreTableScroll(table, index) {
    const tableState = state.tables[index];
    if (!tableState) return;
    table.scrollLeft = tableState.scrollLeft;
    table.scrollTop = tableState.scrollTop;
  });
  Array.from(detailInspectorInner.querySelectorAll(".json-block-value")).forEach(function restoreJsonBlock(block, index) {
    const blockState = state.jsonBlocks[index];
    if (!blockState) return;
    block.style.minHeight = `${blockState.height}px`;
    block.scrollLeft = blockState.scrollLeft;
    block.scrollTop = blockState.scrollTop;
  });
}

function renderDetail(adapted) {
  const node = detailNodeId ? adapted.nodesById[detailNodeId] : null;
  updateDetailState();
  if (!node) {
    detailInspectorInner.innerHTML = "";
    renderedDetailNodeId = null;
    return;
  }
  const scrollState = captureDetailScrollState(node.id);
  detailInspectorInner.innerHTML = `
    <div class="detail-header">
      <div class="detail-header-top">
        <div>
          <div class="detail-eyebrow">SELECTED NODE · ${escapeHtml(node.id)}</div>
          <h2>${escapeHtml(node.displayName)}</h2>
        </div>
        <button id="detail-close-button" class="detail-close" type="button" aria-label="close detail inspector">X</button>
      </div>
      <div class="detail-meta">
        <span>${reportedStateLamp(node.reported_state)}</span>
        <span>${connectionLamp(node.observed_liveness)}</span>
        <span>last_seen · ${escapeHtml(node.last_seen)}</span>
      </div>
    </div>
    <div class="detail-body">${roleDetail(node)}</div>
  `;
  renderedDetailNodeId = node.id;
  restoreDetailScrollState(scrollState);
  document.querySelector("#detail-close-button").addEventListener("click", closeDetail);
}

function roleDetail(node) {
  if (node.id === "host-simulator") return hostDetail(node);
  if (node.id === "local-agent") return agentDetail(node);
  if (node.role === "Relay") return relayDetail(node);
  return monitorDetail(node);
}

function section(title, body) {
  return `<section class="detail-section"><h3>${escapeHtml(title)}</h3><div class="detail-section-content">${body}</div></section>`;
}

function keyValueRows(rows) {
  if (!rows.length) rows = [["자료", MISSING_VALUE]];
  return `<div class="key-value-box">${rows.map(function row(pair) {
    if (pair[2] === JSON_BLOCK_ROW) {
      return `<div class="key-value-row is-json-block"><span>${escapeHtml(pair[0])}</span><pre class="json-block-value">${escapeHtml(formatJsonBlock(pair[1]))}</pre></div>`;
    }
    return `<div class="key-value-row"><span>${escapeHtml(pair[0])}</span><span>${escapeHtml(pair[1])}</span></div>`;
  }).join("")}</div>`;
}

function objectRows(object) {
  if (!object || typeof object !== "object") return [];
  return Object.keys(object).map(function row(key) { return [key, object[key]]; });
}

function dataTable(columns, rows, emptyMessage) {
  if (!Array.isArray(rows) || !rows.length) {
    if (!emptyMessage) return keyValueRows([["자료", MISSING_VALUE]]);
    return `<div class="data-table-wrap"><table><thead><tr>${columns.map(function head(column) {
      return `<th>${escapeHtml(column.label)}</th>`;
    }).join("")}</tr></thead><tbody><tr><td colspan="${columns.length}">${escapeHtml(emptyMessage)}</td></tr></tbody></table></div>`;
  }
  return `<div class="data-table-wrap"><table><thead><tr>${columns.map(function head(column) {
    return `<th>${escapeHtml(column.label)}</th>`;
  }).join("")}</tr></thead><tbody>${rows.map(function row(item) {
    return `<tr>${columns.map(function cell(column) { return `<td>${escapeHtml(item[column.key])}</td>`; }).join("")}</tr>`;
  }).join("")}</tbody></table></div>`;
}

function hostDetail(node) {
  const detail = getNested(node, ["runtime", "details", "detail"], {});
  const hostState = detail.host_state || getNested(node, ["runtime", "details", "host_state"], {});
  return [
    section("Host 지표", keyValueRows(objectRows(hostState))),
    section("Host 실행 상태", keyValueRows([["tick", detail.tick]])),
    trafficSection(node),
  ].join("");
}

function agentDetail(node) {
  const detail = getNested(node, ["runtime", "details", "detail"], {});
  const event = detail.emitted_event || {};
  return [
    section("Host 입력", keyValueRows(objectRows(detail.latest_input_state))),
    section("입력 결과 / 장애", keyValueRows([["latest_input_result", detail.latest_input_result], ["detected_fault", detail.detected_fault]])),
    section("발생 이벤트", keyValueRows([
      ["msg_type", event.msg_type], ["event_id", event.event_id], ["seq_no", event.seq_no], ["host_id", event.host_id],
      ["agent_id", event.agent_id], ["event_type", event.event_type], ["severity", event.severity], ["timestamp", event.timestamp],
      ["payload.cpu", getNested(event, ["payload", "cpu"], MISSING_VALUE)], ["payload.memory", getNested(event, ["payload", "memory"], MISSING_VALUE)],
      ["payload.service_state", getNested(event, ["payload", "service_state"], MISSING_VALUE)], ["payload.latency_ms", getNested(event, ["payload", "latency_ms"], MISSING_VALUE)],
      ["payload.fault_mode", getNested(event, ["payload", "fault_mode"], MISSING_VALUE)],
    ])),
    section("Downstream / 최근 이벤트", keyValueRows([["downstream_result", detail.downstream_result], ["last_event", detail.last_event || getNested(node, ["runtime", "details", "last_event"], MISSING_VALUE), JSON_BLOCK_ROW]])),
    trafficSection(node),
  ].join("");
}

function relayDetail(node) {
  const detail = getNested(node, ["runtime", "details", "detail"], {});
  return [
    section("수신 이벤트", keyValueRows([["last_received_event", detail.last_received_event, JSON_BLOCK_ROW]])),
    section("ACK 대기 목록", dataTable([
      { key: "event_id", label: "event_id" }, { key: "event_type", label: "event_type" }, { key: "seq_no", label: "seq_no" },
      { key: "downstream_target", label: "downstream_target" }, { key: "attempt", label: "attempt" }, { key: "state", label: "state" },
      { key: "last_outcome", label: "last_outcome" }, { key: "ack_from", label: "ack_from" },
    ], detail.pending_ack_state, "대기 중인 ACK 없음")),
    section("Retry / Dedup 카운터", keyValueRows([["pending_ack_count", node.pending_ack_count], ["retry_total", node.retry_total], ["duplicate_dropped", node.duplicate_dropped], ["recent_received_event_ids", detail.recent_received_event_ids]])),
    section("Downstream / Forwarding 결과", keyValueRows([["last_downstream_result", detail.last_downstream_result], ["last_forwarded_result", detail.last_forwarded_result]])),
    trafficSection(node),
  ].join("");
}

function monitorDetail(node) {
  const detail = getNested(node, ["runtime", "details", "detail"], {});
  const hostTable = getNested(node, ["runtime", "details", "host_state_table"], {});
  const hostRows = Object.keys(hostTable || {}).map(function mapHost(hostId) {
    const value = hostTable[hostId] || {};
    return { host_id: hostId, event_type: value.event_type, severity: value.severity, payload: compactObject(value.payload), timestamp: value.timestamp };
  });
  return [
    section("현재 상황 요약", keyValueRows([
      ["last_event", getNested(detail, ["last_processed_event", "event_id"], MISSING_VALUE)],
      ["event_type", getNested(detail, ["last_processed_event", "event_type"], MISSING_VALUE)],
      ["host_state", firstHostStateSummary(hostTable)],
      ["ACK", getNested(detail, ["last_ack_result", "status"], MISSING_VALUE)],
      ["retry", node.retry_total],
    ])),
    section("Route 요약", keyValueRows(routeSummaryRows(detail.last_route_summary))),
    section("장애 위치 추정", keyValueRows(faultLocalizationRows(detail.last_fault_localization))),
    section("Route Trace", dataTable([
      { key: "from_node", label: "from" }, { key: "to_node", label: "to" }, { key: "route_id", label: "route" },
      { key: "attempt_no", label: "attempt" }, { key: "phase", label: "phase" }, { key: "result", label: "result" },
      { key: "failure_reason", label: "reason" },
    ], detail.last_route_trace || [])),
    section("Event Sink 요약", dataTable([
      { key: "event_id", label: "event_id" }, { key: "event_type", label: "event_type" }, { key: "severity", label: "severity" },
      { key: "host_id", label: "host_id" }, { key: "seq_no", label: "seq_no" }, { key: "timestamp", label: "timestamp" },
    ], detail.recent_event_summaries || getNested(node, ["runtime", "details", "recent_events"], []))),
    section("최근 처리 이벤트", keyValueRows([["last_processed_event", detail.last_processed_event, JSON_BLOCK_ROW]])),
    section("Sink / ACK 결과", keyValueRows([["last_sink_result", detail.last_sink_result], ["last_ack_result", detail.last_ack_result]])),
    section("Host 상태 목록", dataTable([
      { key: "host_id", label: "host_id" }, { key: "event_type", label: "event_type" }, { key: "severity", label: "severity" },
      { key: "payload", label: "payload" }, { key: "timestamp", label: "timestamp" },
    ], hostRows)),
    section("카운터", keyValueRows([["out_of_order_count", getNested(node, ["runtime", "details", "out_of_order_count"], 0)], ["total_logged", getNested(node, ["runtime", "details", "total_logged"], 0)], ["duplicate_count", getNested(node, ["runtime", "details", "duplicate_count"], 0)]])),
    trafficSection(node),
  ].join("");
}

function routeSummaryRows(summary) {
  const route = summary || {};
  return [
    ["route_state", route.route_state],
    ["active_route", route.active_route],
    ["failed_hop", route.failed_hop],
    ["suspected_node", route.suspected_node],
    ["reroute_reason", route.reroute_reason],
  ];
}

function faultLocalizationRows(localization) {
  const fault = localization || {};
  return [
    ["failure_scope", fault.failure_scope],
    ["failed_hop", fault.failed_hop],
    ["suspected_node", fault.suspected_node],
    ["failure_reason", fault.failure_reason],
    ["confidence", fault.confidence],
    ["basis", fault.basis],
  ];
}

function firstHostStateSummary(hostTable) {
  const keys = Object.keys(hostTable || {});
  if (!keys.length) return MISSING_VALUE;
  const value = hostTable[keys[0]] || {};
  const payload = value.payload || {};
  return joinPresent([keys[0], value.event_type, value.severity, payload.fault_mode]);
}

function trafficSection(node) {
  const traffic = trafficOf(node);
  const peers = trafficPeerSpecs(node, traffic);
  const recentRows = (traffic.recent || []).map(function mapRecent(item) {
    const capture = item.capture || {};
    return {
      direction: item.direction,
      flow: item.flow,
      peer_node_id: item.peer_node_id,
      peer_role: item.peer_role,
      hop_state: item.hop_state,
      failure_reason: item.failure_reason,
      logical_id: capture.logical_id,
      attempt_no: capture.attempt_no,
      phase: capture.phase,
      captured_at: capture.captured_at,
      truncated: capture.truncated,
      original_size: capture.original_size,
      preview: capture.preview || compactObject(capture.payload),
    };
  });
  return section("최근 통신 상태", [
    keyValueRows([["기록 번호", traffic.capture_seq], ["최근 기록 시각", traffic.captured_at]]),
    `<div class="traffic-peers" data-peer-count="${peers.length}">${peers.map(function renderPeer(spec) { return trafficPeer(spec.peer, spec.title); }).join("")}</div>`,
    dataTable([
      { key: "direction", label: "direction" }, { key: "flow", label: "flow" }, { key: "peer_node_id", label: "peer_node_id" },
      { key: "peer_role", label: "peer_role" }, { key: "hop_state", label: "hop_state" }, { key: "failure_reason", label: "failure_reason" },
      { key: "logical_id", label: "logical_id" }, { key: "attempt_no", label: "attempt_no" }, { key: "phase", label: "phase" },
      { key: "captured_at", label: "최근 기록 시각" }, { key: "truncated", label: "truncated" }, { key: "original_size", label: "original_size" },
      { key: "preview", label: "preview" },
    ], recentRows),
  ].join(""));
}

function isMissingPeerValue(value) {
  return value === null || value === undefined || value === "" || value === MISSING_VALUE;
}

function isEndpointPlaceholderPeer(peer) {
  if (!peer || peer.hop_state !== "not_applicable") return false;
  return isMissingPeerValue(peer.peer_node_id)
    && isMissingPeerValue(peer.peer_role)
    && isMissingPeerValue(peer.last_received)
    && isMissingPeerValue(peer.last_sent);
}

function endpointPeerSpecs(traffic, title) {
  const specs = [{ peer: traffic.previous_peer, title: title }];
  if (!isEndpointPlaceholderPeer(traffic.next_peer)) {
    specs.push({ peer: traffic.next_peer, title: "다음 구간" });
  }
  return specs;
}

function trafficPeerSpecs(node, traffic) {
  if (node.id === "host-simulator") return endpointPeerSpecs(traffic, "상태 조회 요청/응답");
  if (node.id === "monitor") return endpointPeerSpecs(traffic, "이벤트 수신/ACK");
  if (node.id === "local-agent") {
    return [
      { peer: traffic.previous_peer, title: "Host 상태 조회" },
      { peer: traffic.next_peer, title: "이벤트 전달" },
    ];
  }
  if (node.role === "Relay") {
    return [
      { peer: traffic.previous_peer, title: "이벤트 수신" },
      { peer: traffic.next_peer, title: "이벤트 전달" },
    ];
  }
  return [
    { peer: traffic.previous_peer, title: "이전 구간" },
    { peer: traffic.next_peer, title: "다음 구간" },
  ];
}

function trafficPeer(peer, title) {
  const actual = peer || emptyPeer();
  return `<div>${keyValueRows([[title, ""], ["node", actual.peer_node_id], ["role", actual.peer_role], ["hop_state", actual.hop_state], ["failure_reason", actual.failure_reason], ["last_received", actual.last_received, JSON_BLOCK_ROW], ["last_sent", actual.last_sent, JSON_BLOCK_ROW]])}</div>`;
}

function renderLatest() {
  const adapted = adaptState(latestState || {});
  renderSummary(adapted);
  renderNodePower(adapted);
  renderControls(adapted);
  renderPaths(adapted);
  renderNodes(adapted);
  renderDetail(adapted);
}

function renderNodePower(adapted) {
  if (!nodePowerButton) return;
  const state = nodePowerState(adapted);
  const dynamicPorts = getNested(latestState, ["node_power", "dynamic_ports"], false);
  const liveCount = liveNodeCount(adapted);
  const totalCount = adapted.nodes.length;
  const lockRemaining = Math.max(0, Math.ceil((powerLockUntil - Date.now()) / 1000));
  nodePowerButton.dataset.powerState = state;
  nodePowerButton.disabled = powerButtonLocked();
  if (powerActionInFlight || lockRemaining > 0 || state === "transitioning") {
    nodePowerLabel.textContent = "전원 전환 중";
    nodePowerHint.textContent = `${lockRemaining || Math.ceil(getNested(latestState, ["node_power", "lock_remaining_sec"], 1))}초 후 다시 가능`;
    return;
  }
  if (state === "running") {
    nodePowerLabel.textContent = "노드 끄기";
    nodePowerHint.textContent = dynamicPorts ? `전체 ${totalCount}개 실행 중 · 유동 포트` : `전체 ${totalCount}개 실행 중`;
    return;
  }
  if (state === "partial") {
    nodePowerLabel.textContent = "안전 종료";
    nodePowerHint.textContent = `${liveCount}/${totalCount}개 연결됨`;
    return;
  }
  nodePowerLabel.textContent = "노드 켜기";
  nodePowerHint.textContent = dynamicPorts ? "빈 포트로 전체 시작" : "전체 노드 시작";
}

function renderControls(adapted) {
  const injectionType = currentInjectionType(adapted);
  faultSwitches.innerHTML = FAULT_CONTROLS.map(function renderFault(control) {
    const active = injectionType === control.type;
    const command = `fault ${control.key} ${active ? "off" : "on"}`;
    return switchButton(control.label, active ? "켜짐" : "꺼짐", command, active);
  }).join("");

  const nodeSwitchNodes = adapted.nodes
    .filter(function notMonitor(node) { return node.id !== "monitor"; })
    .concat(adapted.nodes.filter(function onlyMonitor(node) { return node.id === "monitor"; }));
  nodeSwitches.innerHTML = nodeSwitchNodes.map(function renderNodeSwitch(node) {
    const running = isNodeRunning(node);
    const target = commandTargetForNode(node.id);
    const command = `${running ? "pause" : "start"} ${target}`;
    return switchButton(node.displayName, running ? "켜짐" : "꺼짐", command, running);
  }).join("");
}

function switchButton(label, state, command, active) {
  return `<button class="switch-button${active ? " is-on" : ""}" type="button" data-command="${escapeHtml(command)}"><span>${escapeHtml(label)}</span><strong>${escapeHtml(state)}</strong></button>`;
}

async function refreshState() {
  try {
    const response = await fetch("/api/state", { cache: "no-store" });
    latestState = await response.json();
    const source = latestState.source || "controller_gateway_runtime_state";
    runtimeStatus.textContent = `${source} · 갱신 ${new Date().toLocaleTimeString("ko-KR")}`;
    renderLatest();
  } catch (error) {
    runtimeStatus.textContent = `runtime 연결 실패: ${error}`;
    renderLatest();
  }
}

async function sendCommand(line) {
  runtimeStatus.textContent = `명령 전송: ${line}`;
  try {
    const response = await fetch("/api/control", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ line: line }),
    });
    const result = await response.json();
    runtimeStatus.textContent = result.ok ? `명령 완료: ${line}` : `명령 실패: ${result.reason || result.message || line}`;
  } catch (error) {
    runtimeStatus.textContent = `명령 실패: ${error}`;
  }
  await refreshState();
}

async function setNodePower(action) {
  powerActionInFlight = true;
  const cooldown = action === "start" ? POWER_START_COOLDOWN_MS : POWER_STOP_COOLDOWN_MS;
  powerLockUntil = Date.now() + cooldown;
  renderLatest();
  runtimeStatus.textContent = action === "start" ? "노드 전원 켜는 중" : "노드 안전 종료 중";
  try {
    const response = await fetch("/api/power", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ action: action }),
    });
    const result = await response.json();
    if (!result.ok) {
      if (Array.isArray(result.conflicts) && result.conflicts.length) {
        const occupied = result.conflicts.map(function labelConflict(conflict) {
          return `${conflict.node_id}:${conflict.port}`;
        }).join(", ");
        runtimeStatus.textContent = `전원 제어 실패: 포트 점유 ${occupied}`;
      } else {
        runtimeStatus.textContent = `전원 제어 실패: ${result.reason || action}`;
      }
    } else {
      runtimeStatus.textContent = action === "start" ? "노드 시작 완료" : "노드 안전 종료 완료";
      const lockSec = typeof result.lock_sec === "number" ? result.lock_sec : cooldown / 1000;
      powerLockUntil = Date.now() + lockSec * 1000;
    }
  } catch (error) {
    runtimeStatus.textContent = `전원 제어 실패: ${error}`;
  }
  powerActionInFlight = false;
  await refreshState();
}

document.addEventListener("click", function onCommandClick(event) {
  const button = event.target.closest("[data-command]");
  if (!button) return;
  sendCommand(button.dataset.command);
});

if (nodePowerButton) {
  nodePowerButton.addEventListener("click", function onPowerClick() {
    if (powerButtonLocked()) return;
    setNodePower(nextPowerAction(adaptState(latestState || {})));
  });
}

refreshState();
window.setInterval(refreshState, 2000);
