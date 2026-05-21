const DIAGRAM_WIDTH = 1460;
const DIAGRAM_HEIGHT = 700;
const NODE_CARD_WIDTH = 208;
const MISSING_VALUE = "—";
const NODE_ORDER = ["host-simulator", "local-agent", "r1", "r2", "monitor"];
const NODE_POSITIONS = {
  "host-simulator": { x: 80, y: 100 },
  "local-agent": { x: 365, y: 255 },
  r1: { x: 655, y: 255 },
  r2: { x: 945, y: 155 },
  monitor: { x: 1215, y: 100 },
};
const NODE_META = {
  "host-simulator": { role: "Host Simulator", displayName: "호스트 시뮬레이터" },
  "local-agent": { role: "Local Agent", displayName: "로컬 에이전트" },
  r1: { role: "Relay", displayName: "릴레이 R1" },
  r2: { role: "Relay", displayName: "릴레이 R2" },
  monitor: { role: "Monitor", displayName: "모니터" },
};
const FAULT_CONTROLS = [
  { key: "cpu", type: "CPU_SPIKE", label: "CPU 장애" },
  { key: "service", type: "SERVICE_DOWN", label: "서비스 중단" },
  { key: "latency", type: "LATENCY_HIGH", label: "지연 증가" },
];
const MAIN_LINKS = [
  { id: "host-agent", from: "host-simulator", to: "local-agent", label: "상태 수집", labelOffsetY: -22 },
  { id: "agent-r1", from: "local-agent", to: "r1", label: "EVENT 전달", labelOffsetY: -24 },
  { id: "r1-r2", from: "r1", to: "r2", label: "EVENT 중계", labelOffsetY: -28 },
  { id: "r2-monitor", from: "r2", to: "monitor", label: "Monitor 전달", labelOffsetY: -30 },
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

const summaryMetrics = document.querySelector("#summary-metrics");
const dataPath = document.querySelector("#data-path");
const nodeLayer = document.querySelector("#node-layer");
const detailInspector = document.querySelector("#detail-inspector");
const detailInspectorInner = document.querySelector("#detail-inspector-inner");
const runtimeStatus = document.querySelector("#runtime-status");
const faultSwitches = document.querySelector("#fault-switches");
const nodeSwitches = document.querySelector("#node-switches");

let latestState = null;
let selectedNodeId = null;
let detailNodeId = null;
let detailState = "closed";
let closeTimer = null;

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

function markerForTone(tone) {
  if (tone === "down") return "url(#arrow-red)";
  if (tone === "warn") return "url(#arrow-orange)";
  if (tone === "ok") return "url(#arrow-green)";
  if (tone === "active") return "url(#arrow-blue)";
  return "url(#arrow-gray)";
}

function linkStatusLabel(link, hopState) {
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
  if (hopState === "paused") return "일시정지";
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

function livenessTone(value) {
  return value === "live" ? "is-live" : "is-muted";
}

function stateBadgeTone(value) {
  return value === "RUNNING" || value === "실행 중" ? "" : "is-muted";
}

function isNodeRunning(node) {
  return node.reported_state === "RUNNING" || node.reported_state === "실행 중";
}

function commandTargetForNode(nodeId) {
  if (nodeId === "host-simulator") return "host";
  if (nodeId === "local-agent") return "agent";
  return nodeId;
}

function currentFaultType(adapted) {
  const host = adapted.nodesById["host-simulator"];
  return getNested(host, ["runtime", "details", "detail", "host_state", "fault_mode"], "NORMAL");
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
      ["fault", "fault", hostState.fault_mode || detail.fault_type],
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
  const cards = [["관찰 노드", adapted.nodes.length], ["live lamp", liveCount], ["retry", retryTotal], ["duplicate", duplicateTotal]];
  summaryMetrics.innerHTML = cards.map(function card(pair) {
    return `<div class="summary-metric"><span>${escapeHtml(pair[0])}</span><strong>${escapeHtml(pair[1])}</strong></div>`;
  }).join("");
}

function renderPaths(adapted) {
  dataPath.innerHTML = "";
  MAIN_LINKS.forEach(function renderLink(link) {
    const path = buildMainPath(link, adapted.nodesById);
    const labelPosition = linkLabelPosition(link, adapted.nodesById);
    const hopState = linkHopState(link, adapted.nodesById);
    const tone = hopTone(hopState);
    const label = linkStatusLabel(link, hopState);
    const labelWidth = Math.max(78, label.length * 12 + 22);
    const group = document.createElementNS("http://www.w3.org/2000/svg", "g");
    group.dataset.linkId = link.id;
    group.dataset.hopState = hopState;
    group.dataset.hopTone = tone;
    const title = document.createElementNS("http://www.w3.org/2000/svg", "title");
    title.textContent = `${label}: ${hopState}`;
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
    if (tone === "active" || tone === "warn") {
      line.classList.add("path-flow");
    }
    const labelGroup = document.createElementNS("http://www.w3.org/2000/svg", "g");
    labelGroup.setAttribute("class", "path-status-label");
    labelGroup.setAttribute("transform", `translate(${labelPosition.x}, ${labelPosition.y})`);
    const labelBackground = document.createElementNS("http://www.w3.org/2000/svg", "rect");
    labelBackground.setAttribute("x", String(-labelWidth / 2));
    labelBackground.setAttribute("y", "-14");
    labelBackground.setAttribute("width", String(labelWidth));
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
    const chips = activityChips(node).slice(0, 2).map(function chip(row) {
      return nodeInfoRow(row[1], row[2]);
    }).join("");
    card.innerHTML = `
      <div class="node-card-top">
        ${livenessLamp(node.observed_liveness)}
      </div>
      <div class="node-title-block">
        <div class="node-name">${escapeHtml(node.displayName)}</div>
        <div class="node-role-line">${escapeHtml(node.role)}</div>
      </div>
      <div class="node-info-box">
        ${nodeInfoRow("상태", stateBadge(node.reported_state), true)}
        ${chips || nodeInfoRow("핵심 신호", cardSignal(node))}
      </div>
    `;
    nodeLayer.appendChild(card);
  });
}

function livenessLamp(value) {
  return `<span class="lamp-wrap" data-liveness-tone="${value === "live" ? "green" : "gray"}"><i class="lamp ${livenessTone(value)}"></i>${escapeHtml(value)}</span>`;
}

function stateBadge(value) {
  return `<span class="state-badge ${stateBadgeTone(value)}" data-reported-state-tone="${stateBadgeTone(value) ? "unknown" : "running"}">${escapeHtml(value)}</span>`;
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

function renderDetail(adapted) {
  const node = detailNodeId ? adapted.nodesById[detailNodeId] : null;
  updateDetailState();
  if (!node) {
    detailInspectorInner.innerHTML = "";
    return;
  }
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
        <span>role · ${escapeHtml(node.role)}</span>
        <span>${livenessLamp(node.observed_liveness)}</span>
        <span>${stateBadge(node.reported_state)}</span>
        <span>last_seen · ${escapeHtml(node.last_seen)}</span>
      </div>
    </div>
    <div class="detail-body">${roleDetail(node)}</div>
  `;
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
    return `<div class="key-value-row"><span>${escapeHtml(pair[0])}</span><span>${escapeHtml(pair[1])}</span></div>`;
  }).join("")}</div>`;
}

function objectRows(object) {
  if (!object || typeof object !== "object") return [];
  return Object.keys(object).map(function row(key) { return [key, object[key]]; });
}

function dataTable(columns, rows) {
  if (!Array.isArray(rows) || !rows.length) return keyValueRows([["자료", MISSING_VALUE]]);
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
    section("Host Metrics", keyValueRows(objectRows(hostState))),
    section("Runtime Tick / Fault", keyValueRows([["tick", detail.tick], ["fault_active", detail.fault_active], ["fault_type", detail.fault_type]])),
    trafficSection(node),
  ].join("");
}

function agentDetail(node) {
  const detail = getNested(node, ["runtime", "details", "detail"], {});
  const event = detail.emitted_event || {};
  return [
    section("Host Input", keyValueRows(objectRows(detail.latest_input_state))),
    section("Input Result / Fault", keyValueRows([["latest_input_result", detail.latest_input_result], ["detected_fault", detail.detected_fault]])),
    section("Emitted Event", keyValueRows([
      ["msg_type", event.msg_type], ["event_id", event.event_id], ["seq_no", event.seq_no], ["host_id", event.host_id],
      ["agent_id", event.agent_id], ["event_type", event.event_type], ["severity", event.severity], ["timestamp", event.timestamp],
      ["payload.cpu", getNested(event, ["payload", "cpu"], MISSING_VALUE)], ["payload.memory", getNested(event, ["payload", "memory"], MISSING_VALUE)],
      ["payload.service_state", getNested(event, ["payload", "service_state"], MISSING_VALUE)], ["payload.latency_ms", getNested(event, ["payload", "latency_ms"], MISSING_VALUE)],
      ["payload.fault_mode", getNested(event, ["payload", "fault_mode"], MISSING_VALUE)],
    ])),
    section("Downstream / Last Event", keyValueRows([["downstream_result", detail.downstream_result], ["last_event", detail.last_event || getNested(node, ["runtime", "details", "last_event"], MISSING_VALUE)]])),
    trafficSection(node),
  ].join("");
}

function relayDetail(node) {
  const detail = getNested(node, ["runtime", "details", "detail"], {});
  return [
    section("Received Event", keyValueRows(objectRows(detail.last_received_event))),
    section("Pending ACK Table", dataTable([
      { key: "event_id", label: "event_id" }, { key: "event_type", label: "event_type" }, { key: "seq_no", label: "seq_no" },
      { key: "downstream_target", label: "downstream_target" }, { key: "attempt", label: "attempt" }, { key: "state", label: "state" },
      { key: "last_outcome", label: "last_outcome" }, { key: "ack_from", label: "ack_from" },
    ], detail.pending_ack_state)),
    section("Retry / Dedup Counters", keyValueRows([["pending_ack_count", node.pending_ack_count], ["retry_total", node.retry_total], ["duplicate_dropped", node.duplicate_dropped], ["recent_received_event_ids", detail.recent_received_event_ids]])),
    section("Downstream / Forwarding Result", keyValueRows([["last_downstream_result", detail.last_downstream_result], ["last_forwarded_result", detail.last_forwarded_result]])),
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
    section("Event Sink Summary", dataTable([
      { key: "event_id", label: "event_id" }, { key: "event_type", label: "event_type" }, { key: "severity", label: "severity" },
      { key: "host_id", label: "host_id" }, { key: "seq_no", label: "seq_no" }, { key: "timestamp", label: "timestamp" },
    ], detail.recent_event_summaries || getNested(node, ["runtime", "details", "recent_events"], []))),
    section("Last Processed Event", keyValueRows(objectRows(detail.last_processed_event))),
    section("Sink / ACK Result", keyValueRows([["last_sink_result", detail.last_sink_result], ["last_ack_result", detail.last_ack_result]])),
    section("Host State Table", dataTable([
      { key: "host_id", label: "host_id" }, { key: "event_type", label: "event_type" }, { key: "severity", label: "severity" },
      { key: "payload", label: "payload" }, { key: "timestamp", label: "timestamp" },
    ], hostRows)),
    section("Counters", keyValueRows([["out_of_order_count", getNested(node, ["runtime", "details", "out_of_order_count"], 0)], ["total_logged", getNested(node, ["runtime", "details", "total_logged"], 0)], ["duplicate_count", getNested(node, ["runtime", "details", "duplicate_count"], 0)]])),
    trafficSection(node),
  ].join("");
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
  return section("Traffic Snapshot", [
    keyValueRows([["capture_seq", traffic.capture_seq], ["captured_at", traffic.captured_at]]),
    `<div class="traffic-peers">${trafficPeer(traffic.previous_peer, "previous_peer")}${trafficPeer(traffic.next_peer, "next_peer")}</div>`,
    dataTable([
      { key: "direction", label: "direction" }, { key: "flow", label: "flow" }, { key: "peer_node_id", label: "peer_node_id" },
      { key: "peer_role", label: "peer_role" }, { key: "hop_state", label: "hop_state" }, { key: "failure_reason", label: "failure_reason" },
      { key: "logical_id", label: "logical_id" }, { key: "attempt_no", label: "attempt_no" }, { key: "phase", label: "phase" },
      { key: "captured_at", label: "captured_at" }, { key: "truncated", label: "truncated" }, { key: "original_size", label: "original_size" },
      { key: "preview", label: "preview" },
    ], recentRows),
  ].join(""));
}

function trafficPeer(peer, title) {
  const actual = peer || emptyPeer();
  return `<div>${keyValueRows([[title, ""], ["node", actual.peer_node_id], ["role", actual.peer_role], ["hop_state", actual.hop_state], ["failure_reason", actual.failure_reason], ["last_received", actual.last_received], ["last_sent", actual.last_sent]])}</div>`;
}

function renderLatest() {
  const adapted = adaptState(latestState || {});
  renderSummary(adapted);
  renderControls(adapted);
  renderPaths(adapted);
  renderNodes(adapted);
  renderDetail(adapted);
}

function renderControls(adapted) {
  const faultType = currentFaultType(adapted);
  faultSwitches.innerHTML = FAULT_CONTROLS.map(function renderFault(control) {
    const active = faultType === control.type;
    const command = `fault ${control.key} ${active ? "off" : "on"}`;
    return switchButton(control.label, active ? "켜짐" : "꺼짐", command, active);
  }).join("");

  nodeSwitches.innerHTML = adapted.nodes.map(function renderNodeSwitch(node) {
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

document.addEventListener("click", function onCommandClick(event) {
  const button = event.target.closest("[data-command]");
  if (!button) return;
  sendCommand(button.dataset.command);
});

refreshState();
window.setInterval(refreshState, 2000);
