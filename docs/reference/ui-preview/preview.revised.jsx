const { useRef, useState } = React;

const diagramWidth = 1240;
const diagramHeight = 660;
const missingValue = "—";

const nodeOrder = ["host-simulator", "local-agent", "r1", "r2", "monitor"];

const revisedNodes = [
    {
        id: "host-simulator",
        role: "Host Simulator",
        displayName: "호스트 시뮬레이터",
        short: "HOST",
        position: { x: 56, y: 78 },
        observed_liveness: "live",
        reported_state: "실행 중",
        last_seen: "0.8초 전",
        activity: {
            host_state: {
                host_id: "host-1",
                cpu_usage: "62%",
                memory_usage: "41%",
                service_state: "UP",
                latency_ms: 22,
                last_update_time: "2026-05-09T10:21:12",
            },
            detail: {
                tick: 12,
                fault_active: false,
                fault_type: missingValue,
            },
        },
        traffic: {
            capture_seq: 121,
            captured_at: "2026-05-09T10:21:12",
            previous_peer: {
                peer_node_id: missingValue,
                peer_role: "not_applicable",
                hop_state: "not_applicable",
                failure_reason: missingValue,
                last_received: missingValue,
                last_sent: missingValue,
            },
            next_peer: {
                peer_node_id: "local-agent",
                peer_role: "Local Agent",
                hop_state: "acknowledged",
                failure_reason: missingValue,
                last_received: "poll request",
                last_sent: "host_state",
            },
            recent: [
                {
                    direction: "outbound",
                    flow: "host polling",
                    peer_node_id: "local-agent",
                    peer_role: "Local Agent",
                    hop_state: "acknowledged",
                    failure_reason: missingValue,
                    capture: {
                        logical_id: "host-state-12",
                        attempt_no: 1,
                        phase: "sampled",
                        captured_at: "2026-05-09T10:21:12",
                        truncated: false,
                        original_size: 148,
                        preview: '{"cpu_usage":62,"memory_usage":41,"service_state":"UP","latency_ms":22}',
                    },
                },
            ],
        },
    },
    {
        id: "local-agent",
        role: "Local Agent",
        displayName: "로컬 에이전트",
        short: "AGENT",
        position: { x: 278, y: 214 },
        observed_liveness: "live",
        reported_state: "실행 중",
        last_seen: "1.1초 전",
        activity: {
            latest_input_state: {
                host_id: "host-1",
                cpu_usage: "96%",
                memory_usage: "51%",
                service_state: "UP",
                latency_ms: 28,
            },
            latest_input_result: {
                status: "changed",
                host_id: "host-1",
                seq_no: 7,
            },
            detected_fault: "CPU_SPIKE",
            emitted_event: {
                msg_type: "EVENT",
                event_id: "evt-host-1-7",
                seq_no: 7,
                host_id: "host-1",
                agent_id: "agent-1",
                event_type: "CPU_SPIKE",
                severity: "WARN",
                timestamp: "2026-05-09T10:21:14",
                payload: {
                    cpu: 96,
                    memory: 51,
                    service_state: "UP",
                    latency_ms: 28,
                    fault_mode: "CPU_SPIKE",
                },
            },
            downstream_result: {
                status: "request_sent",
                target: "r1",
                event_id: "evt-host-1-7",
            },
            last_event: "evt-host-1-7",
        },
        traffic: {
            capture_seq: 88,
            captured_at: "2026-05-09T10:21:14",
            previous_peer: {
                peer_node_id: "host-simulator",
                peer_role: "Host Simulator",
                hop_state: "acknowledged",
                failure_reason: missingValue,
                last_received: "host_state",
                last_sent: "poll request",
            },
            next_peer: {
                peer_node_id: "r1",
                peer_role: "Relay R1",
                hop_state: "request_sent",
                failure_reason: missingValue,
                last_received: missingValue,
                last_sent: "EVENT evt-host-1-7",
            },
            recent: [
                {
                    direction: "inbound",
                    flow: "host polling",
                    peer_node_id: "host-simulator",
                    peer_role: "Host Simulator",
                    hop_state: "acknowledged",
                    failure_reason: missingValue,
                    capture: {
                        logical_id: "host-state-12",
                        attempt_no: 1,
                        phase: "received",
                        captured_at: "2026-05-09T10:21:14",
                        truncated: false,
                        original_size: 148,
                        preview: '{"cpu_usage":96,"memory_usage":51,"service_state":"UP","latency_ms":28}',
                    },
                },
                {
                    direction: "outbound",
                    flow: "event forwarding",
                    peer_node_id: "r1",
                    peer_role: "Relay R1",
                    hop_state: "request_sent",
                    failure_reason: missingValue,
                    capture: {
                        logical_id: "evt-host-1-7",
                        attempt_no: 1,
                        phase: "sent",
                        captured_at: "2026-05-09T10:21:14",
                        truncated: false,
                        original_size: 286,
                        preview: '{"event_id":"evt-host-1-7","event_type":"CPU_SPIKE","severity":"WARN"}',
                    },
                },
            ],
        },
    },
    {
        id: "r1",
        role: "Relay",
        displayName: "릴레이 R1",
        short: "R1",
        position: { x: 538, y: 214 },
        observed_liveness: "live",
        reported_state: "실행 중",
        last_seen: "1.4초 전",
        activity: {
            pending_ack_count: 1,
            retry_total: 1,
            duplicate_dropped: 0,
            last_received_event: {
                event_id: "evt-host-1-7",
                event_type: "CPU_SPIKE",
                seq_no: 7,
                host_id: "host-1",
                timestamp: "2026-05-09T10:21:14",
            },
            pending_ack_state: [
                {
                    event_id: "evt-host-1-7",
                    event_type: "CPU_SPIKE",
                    seq_no: 7,
                    downstream_target: "r2",
                    attempt: 1,
                    state: "acknowledged",
                    last_outcome: "ACK from r2",
                    ack_from: "r2",
                },
            ],
            recent_received_event_ids: ["evt-host-1-7", "evt-host-1-6"],
            last_downstream_result: {
                status: "acknowledged",
                target: "r2",
                event_id: "evt-host-1-7",
            },
            last_forwarded_result: {
                status: "forwarded",
                target: "r2",
                event_id: "evt-host-1-7",
            },
        },
        traffic: {
            capture_seq: 54,
            captured_at: "2026-05-09T10:21:16",
            previous_peer: {
                peer_node_id: "local-agent",
                peer_role: "Local Agent",
                hop_state: "acknowledged",
                failure_reason: missingValue,
                last_received: "EVENT evt-host-1-7",
                last_sent: "ACK evt-host-1-7",
            },
            next_peer: {
                peer_node_id: "r2",
                peer_role: "Relay R2",
                hop_state: "acknowledged",
                failure_reason: missingValue,
                last_received: "ACK evt-host-1-7",
                last_sent: "EVENT evt-host-1-7",
            },
            recent: [
                {
                    direction: "inbound",
                    flow: "event forwarding",
                    peer_node_id: "local-agent",
                    peer_role: "Local Agent",
                    hop_state: "acknowledged",
                    failure_reason: missingValue,
                    capture: {
                        logical_id: "evt-host-1-7",
                        attempt_no: 1,
                        phase: "received",
                        captured_at: "2026-05-09T10:21:15",
                        truncated: false,
                        original_size: 286,
                        preview: '{"event_id":"evt-host-1-7","seq_no":7,"host_id":"host-1"}',
                    },
                },
                {
                    direction: "outbound",
                    flow: "relay forwarding",
                    peer_node_id: "r2",
                    peer_role: "Relay R2",
                    hop_state: "acknowledged",
                    failure_reason: missingValue,
                    capture: {
                        logical_id: "evt-host-1-7",
                        attempt_no: 1,
                        phase: "forwarded",
                        captured_at: "2026-05-09T10:21:16",
                        truncated: false,
                        original_size: 286,
                        preview: '{"event_id":"evt-host-1-7","target":"r2","attempt":1}',
                    },
                },
            ],
        },
    },
    {
        id: "r2",
        role: "Relay",
        displayName: "릴레이 R2",
        short: "R2",
        position: { x: 798, y: 126 },
        observed_liveness: "stale",
        reported_state: "실행 중",
        last_seen: "6.2초 전",
        activity: {
            pending_ack_count: 1,
            retry_total: 2,
            duplicate_dropped: 0,
            last_received_event: {
                event_id: "evt-host-1-7",
                event_type: "CPU_SPIKE",
                seq_no: 7,
                host_id: "host-1",
                timestamp: "2026-05-09T10:21:16",
            },
            pending_ack_state: [
                {
                    event_id: "evt-host-1-7",
                    event_type: "CPU_SPIKE",
                    seq_no: 7,
                    downstream_target: "monitor",
                    attempt: 2,
                    state: "request_sent",
                    last_outcome: "timeout",
                    ack_from: missingValue,
                },
            ],
            recent_received_event_ids: ["evt-host-1-7", "evt-host-1-6"],
            last_downstream_result: {
                status: "timeout",
                target: "monitor",
                event_id: "evt-host-1-7",
            },
            last_forwarded_result: {
                status: "retry_sent",
                target: "monitor",
                event_id: "evt-host-1-7",
            },
        },
        traffic: {
            capture_seq: 47,
            captured_at: "2026-05-09T10:21:20",
            previous_peer: {
                peer_node_id: "r1",
                peer_role: "Relay R1",
                hop_state: "acknowledged",
                failure_reason: missingValue,
                last_received: "EVENT evt-host-1-7",
                last_sent: "ACK pending",
            },
            next_peer: {
                peer_node_id: "monitor",
                peer_role: "Monitor",
                hop_state: "timeout",
                failure_reason: "ack_dropped",
                last_received: missingValue,
                last_sent: "EVENT evt-host-1-7 retry",
            },
            recent: [
                {
                    direction: "outbound",
                    flow: "relay forwarding",
                    peer_node_id: "monitor",
                    peer_role: "Monitor",
                    hop_state: "timeout",
                    failure_reason: "ack_dropped",
                    capture: {
                        logical_id: "evt-host-1-7",
                        attempt_no: 1,
                        phase: "sent",
                        captured_at: "2026-05-09T10:21:18",
                        truncated: false,
                        original_size: 286,
                        preview: '{"event_id":"evt-host-1-7","target":"monitor","attempt":1}',
                    },
                },
                {
                    direction: "outbound",
                    flow: "relay forwarding",
                    peer_node_id: "monitor",
                    peer_role: "Monitor",
                    hop_state: "request_sent",
                    failure_reason: missingValue,
                    capture: {
                        logical_id: "evt-host-1-7",
                        attempt_no: 2,
                        phase: "retry_sent",
                        captured_at: "2026-05-09T10:21:20",
                        truncated: false,
                        original_size: 286,
                        preview: '{"event_id":"evt-host-1-7","target":"monitor","attempt":2}',
                    },
                },
            ],
        },
    },
    {
        id: "monitor",
        role: "Monitor",
        displayName: "모니터",
        short: "MON",
        position: { x: 1000, y: 72 },
        observed_liveness: "live",
        reported_state: "실행 중",
        last_seen: "0.6초 전",
        activity: {
            total_logged: 2,
            duplicate_count: 1,
            out_of_order_count: 0,
            recent_event_summaries: [
                {
                    event_id: "evt-host-1-7",
                    event_type: "CPU_SPIKE",
                    severity: "WARN",
                    host_id: "host-1",
                    seq_no: 7,
                    timestamp: "2026-05-09T10:21:22",
                },
                {
                    event_id: "evt-host-1-6",
                    event_type: "HOST_STATE_UPDATE",
                    severity: "INFO",
                    host_id: "host-1",
                    seq_no: 6,
                    timestamp: "2026-05-09T10:21:02",
                },
            ],
            last_processed_event: {
                event_id: "evt-host-1-7",
                event_type: "CPU_SPIKE",
                severity: "WARN",
                host_id: "host-1",
                seq_no: 7,
                timestamp: "2026-05-09T10:21:22",
            },
            last_sink_result: {
                status: "stored",
                event_id: "evt-host-1-7",
                host_id: "host-1",
                seq_no: 7,
            },
            last_ack_result: {
                status: "sent",
                event_id: "evt-host-1-7",
                duplicate: true,
            },
            host_state_table: {
                "host-1": {
                    event_type: "CPU_SPIKE",
                    severity: "WARN",
                    payload: {
                        cpu: 96,
                        memory: 51,
                        service_state: "UP",
                        latency_ms: 28,
                        fault_mode: "CPU_SPIKE",
                    },
                    timestamp: "2026-05-09T10:21:22",
                },
            },
        },
        traffic: {
            capture_seq: 35,
            captured_at: "2026-05-09T10:21:22",
            previous_peer: {
                peer_node_id: "r2",
                peer_role: "Relay R2",
                hop_state: "acknowledged",
                failure_reason: missingValue,
                last_received: "EVENT evt-host-1-7 retry",
                last_sent: "ACK evt-host-1-7",
            },
            next_peer: {
                peer_node_id: missingValue,
                peer_role: "not_applicable",
                hop_state: "not_applicable",
                failure_reason: missingValue,
                last_received: missingValue,
                last_sent: missingValue,
            },
            recent: [
                {
                    direction: "inbound",
                    flow: "sink input",
                    peer_node_id: "r2",
                    peer_role: "Relay R2",
                    hop_state: "acknowledged",
                    failure_reason: missingValue,
                    capture: {
                        logical_id: "evt-host-1-7",
                        attempt_no: 2,
                        phase: "received",
                        captured_at: "2026-05-09T10:21:22",
                        truncated: false,
                        original_size: 286,
                        preview: '{"event_id":"evt-host-1-7","seq_no":7,"duplicate":true}',
                    },
                },
            ],
        },
    },
];

const mainLinks = [
    { id: "host-agent", from: "host-simulator", to: "local-agent", label: "상태 수집", condition: "active" },
    { id: "agent-r1", from: "local-agent", to: "r1", label: "EVENT 전달", condition: "active" },
    { id: "r1-r2", from: "r1", to: "r2", label: "EVENT 전달", condition: "active" },
    { id: "r2-monitor", from: "r2", to: "monitor", label: "ACK 지연", condition: "watch" },
];

function IconBase({ className = "h-4 w-4", children, viewBox = "0 0 24 24" }) {
    return (
        <svg viewBox={viewBox} fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className={className} aria-hidden="true">
            {children}
        </svg>
    );
}

function PlayIcon({ className }) {
    return (
        <IconBase className={className}>
            <polygon points="8 5 19 12 8 19 8 5" fill="currentColor" stroke="none" />
        </IconBase>
    );
}

function PauseIcon({ className }) {
    return (
        <IconBase className={className}>
            <rect x="6" y="4" width="4" height="16" />
            <rect x="14" y="4" width="4" height="16" />
        </IconBase>
    );
}

function RotateCcwIcon({ className }) {
    return (
        <IconBase className={className}>
            <polyline points="1 4 1 10 7 10" />
            <path d="M3.51 15a9 9 0 1 0 .49-9" />
        </IconBase>
    );
}

function livenessLampTone(observedLiveness) {
    return observedLiveness === "live" ? "green" : "gray";
}

function LivenessLamp({ value, nodeId, compact = false }) {
    const green = livenessLampTone(value) === "green";
    return (
        <span data-testid={nodeId ? `liveness-lamp-${nodeId}` : undefined} data-liveness-tone={green ? "green" : "gray"} className="inline-flex items-center gap-1.5">
            <span className={`${compact ? "h-2.5 w-2.5" : "h-3 w-3"} rounded-full border ${green ? "border-emerald-300 bg-emerald-500 shadow-[0_0_0_3px_rgba(16,185,129,0.16)]" : "border-slate-300 bg-slate-400"}`} />
            <span className="text-[11px] font-medium text-slate-600">{value}</span>
        </span>
    );
}

function reportedStateTone(reportedState) {
    return reportedState === "실행 중" ? "running" : "unknown";
}

function ReportedStateBadge({ value, nodeId, compact = false }) {
    const tone = reportedStateTone(value);
    const toneClass = tone === "running"
        ? "border-cyan-200 bg-cyan-50 text-cyan-700"
        : "border-slate-200 bg-slate-50 text-slate-600";
    return (
        <span
            data-testid={nodeId ? `reported-state-${nodeId}` : undefined}
            data-reported-state-tone={tone}
            className={`inline-flex items-center justify-end gap-1.5 rounded-full border px-2 py-1 font-semibold ${compact ? "text-[10px]" : "text-[11px]"} ${toneClass}`}
        >
            <span className={`rounded-full ${compact ? "h-1.5 w-1.5" : "h-2 w-2"} ${tone === "running" ? "bg-cyan-500" : "bg-slate-400"}`} />
            {formatScalar(value)}
        </span>
    );
}

function getNodeById(nodeId) {
    return revisedNodes.find((node) => node.id === nodeId);
}

function getNodeCenter(node) {
    return { x: node.position.x + 87, y: node.position.y + 64 };
}

function buildMainPath(link) {
    const from = getNodeCenter(getNodeById(link.from));
    const to = getNodeCenter(getNodeById(link.to));
    const midX = Math.round((from.x + to.x) / 2);
    return `M ${from.x} ${from.y} C ${midX} ${from.y}, ${midX} ${to.y}, ${to.x} ${to.y}`;
}

function formatScalar(value) {
    if (value === null || value === undefined || value === "") return missingValue;
    if (typeof value === "boolean") return value ? "true" : "false";
    if (Array.isArray(value)) return value.length ? value.join(", ") : missingValue;
    if (typeof value === "object") return JSON.stringify(value);
    return String(value);
}

function activityChips(node) {
    const activity = node.activity;
    if (node.id === "host-simulator") {
        return [
            ["service", "서비스", activity.host_state.service_state],
            ["latency", "지연", `${activity.host_state.latency_ms}ms`],
            ["injection", "주입", activity.detail.fault_type],
        ];
    }
    if (node.id === "local-agent") {
        return [
            ["input", "입력", activity.latest_input_result.status],
            ["fault", "fault", activity.detected_fault],
            ["downstream", "downstream", activity.downstream_result.status],
            ["event", "event", `${activity.emitted_event.event_type} · ${activity.emitted_event.severity}`],
        ];
    }
    if (node.role === "Relay") {
        const current = activity.pending_ack_state[0] || {};
        return [
            ["ack-count", "ACK 대기 수", activity.pending_ack_count],
            ["retry-total", "retry", activity.retry_total],
            ["dedup", "dedup", activity.duplicate_dropped],
            ["ack-current", "ACK 항목", `${formatScalar(current.state)} · ${formatScalar(current.attempt)}`],
            ["downstream", "downstream", (activity.last_downstream_result || activity.last_forwarded_result).status],
        ];
    }
    return [
        ["logged", "logged", activity.total_logged],
        ["duplicate", "duplicate", activity.duplicate_count],
        ["order", "order", activity.out_of_order_count],
        ["sink", "sink", activity.last_sink_result.status],
        ["ack", "ACK", activity.last_ack_result.status],
    ];
}

function Section({ title, children, testId }) {
    return (
        <section data-testid={testId} className="rounded-lg border border-slate-200 bg-white shadow-sm">
            <div className="border-b border-slate-200 px-3 py-2 text-[11px] font-semibold tracking-[0.14em] text-slate-500">{title}</div>
            <div className="p-3">{children}</div>
        </section>
    );
}

function KeyValueRows({ rows }) {
    return (
        <div className="overflow-hidden rounded-lg border border-slate-200 bg-slate-50">
            {rows.map(([label, value], index) => (
                <div key={`${label}-${index}`} className={`flex items-start justify-between gap-3 px-3 py-2 text-xs ${index < rows.length - 1 ? "border-b border-slate-200" : ""}`}>
                    <span className="shrink-0 text-slate-500">{label}</span>
                    <span className="text-right font-medium leading-5 text-slate-800">{formatScalar(value)}</span>
                </div>
            ))}
        </div>
    );
}

function NodeInfoRow({ label, value, testId, valueTestId, children }) {
    return (
        <div data-testid={testId} data-node-info-row={label} className="flex items-center justify-between gap-2 border-b border-slate-200 px-2.5 py-2 last:border-b-0">
            <span data-node-info-label className="shrink-0 text-[10px] font-semibold tracking-[0.08em] text-slate-500">{label}</span>
            <span data-node-info-value data-testid={valueTestId} className="min-w-0 text-right text-[11px] font-semibold leading-5 text-slate-800">
                {children || formatScalar(value)}
            </span>
        </div>
    );
}

function DataTable({ columns, rows, testId }) {
    return (
        <div data-testid={testId} className="overflow-x-auto rounded-lg border border-slate-200">
            <table className="min-w-full text-left text-[11px]">
                <thead className="bg-slate-100 text-slate-500">
                    <tr>{columns.map((column) => <th key={column.key} className="px-2 py-2 font-semibold">{column.label}</th>)}</tr>
                </thead>
                <tbody className="divide-y divide-slate-200 bg-white text-slate-700">
                    {rows.map((row, rowIndex) => (
                        <tr key={`${row.event_id || row.logical_id || "row"}-${rowIndex}`}>
                            {columns.map((column) => <td key={column.key} className="px-2 py-2 align-top">{formatScalar(row[column.key])}</td>)}
                        </tr>
                    ))}
                </tbody>
            </table>
        </div>
    );
}

function TrafficPeer({ peer, title }) {
    return (
        <div className="rounded-lg border border-slate-200 bg-slate-50 p-3">
            <div className="mb-2 text-xs font-semibold text-slate-900">{title}</div>
            <KeyValueRows rows={[
                ["node", peer.peer_node_id],
                ["role", peer.peer_role],
                ["hop_state", peer.hop_state],
                ["failure_reason", peer.failure_reason],
                ["last_received", peer.last_received],
                ["last_sent", peer.last_sent],
            ]} />
        </div>
    );
}

function TrafficSection({ traffic }) {
    const recentRows = traffic.recent.map((item) => ({
        direction: item.direction,
        flow: item.flow,
        peer_node_id: item.peer_node_id,
        peer_role: item.peer_role,
        hop_state: item.hop_state,
        failure_reason: item.failure_reason,
        logical_id: item.capture.logical_id,
        attempt_no: item.capture.attempt_no,
        phase: item.capture.phase,
        captured_at: item.capture.captured_at,
        truncated: item.capture.truncated,
        original_size: item.capture.original_size,
        preview: item.capture.preview,
    }));
    return (
        <Section title="Traffic Snapshot" testId="detail-traffic">
            <div className="space-y-3">
                <KeyValueRows rows={[["capture_seq", traffic.capture_seq], ["captured_at", traffic.captured_at]]} />
                <div className="grid gap-2 md:grid-cols-2">
                    <TrafficPeer peer={traffic.previous_peer} title="previous_peer" />
                    {traffic.next_peer && traffic.next_peer.hop_state !== "not_applicable" ? <TrafficPeer peer={traffic.next_peer} title="next_peer" /> : null}
                </div>
                <DataTable
                    testId="traffic-recent"
                    columns={[
                        { key: "direction", label: "direction" },
                        { key: "flow", label: "flow" },
                        { key: "peer_node_id", label: "peer_node_id" },
                        { key: "peer_role", label: "peer_role" },
                        { key: "hop_state", label: "hop_state" },
                        { key: "failure_reason", label: "failure_reason" },
                        { key: "logical_id", label: "logical_id" },
                        { key: "attempt_no", label: "attempt_no" },
                        { key: "phase", label: "phase" },
                        { key: "captured_at", label: "captured_at" },
                        { key: "truncated", label: "truncated" },
                        { key: "original_size", label: "original_size" },
                        { key: "preview", label: "preview" },
                    ]}
                    rows={recentRows}
                />
            </div>
        </Section>
    );
}

function HeaderSummary() {
    const retryTotal = revisedNodes.filter((node) => node.role === "Relay").reduce((total, node) => total + node.activity.retry_total, 0);
    const duplicateTotal = getNodeById("monitor").activity.duplicate_count;
    const liveCount = revisedNodes.filter((node) => node.observed_liveness === "live").length;
    const cards = [["관찰 노드", revisedNodes.length], ["live lamp", liveCount], ["retry", retryTotal], ["duplicate", duplicateTotal]];
    return (
        <header className="rounded-lg border border-slate-200 bg-white px-4 py-3 shadow-sm">
            <div className="flex flex-wrap items-center justify-between gap-3">
                <div>
                    <h1 className="text-lg font-bold tracking-wide text-slate-900">NET-DEMO Web Preview · Node-first Dashboard</h1>
                    <div className="mt-1 text-xs text-slate-500">liveness lamp / reported state / traffic activity 분리</div>
                </div>
                <div className="grid grid-cols-4 gap-2 text-center text-[11px]">
                    {cards.map(([label, value]) => (
                        <div key={label} className="rounded border border-slate-200 bg-slate-50 px-3 py-2">
                            <div className="text-slate-500">{label}</div>
                            <div className="font-semibold text-slate-800">{value}</div>
                        </div>
                    ))}
                </div>
            </div>
        </header>
    );
}

function PageChrome() {
    return (
        <section data-testid="page-control-chrome" className="rounded-lg border border-sky-200 bg-sky-50 px-4 py-3 shadow-sm">
            <div className="flex flex-wrap items-center justify-between gap-3">
                <div>
                    <div className="text-[10px] font-semibold tracking-[0.18em] text-sky-600">BROWSER SURFACE</div>
                    <div className="mt-1 text-sm font-semibold text-slate-900">그래프는 data-plane node만 표시합니다</div>
                    <div className="mt-1 text-xs text-sky-800">관찰 전환과 명령 표면은 page chrome에 머물고, node graph에는 들어가지 않습니다.</div>
                </div>
                <LivenessLegend />
            </div>
        </section>
    );
}

function LivenessLegend() {
    return (
        <div data-testid="liveness-legend" className="grid gap-2 text-xs sm:grid-cols-2">
            <div className="rounded border border-emerald-200 bg-white px-3 py-2"><LivenessLamp value="live" compact /> live 관측</div>
            <div className="rounded border border-slate-200 bg-white px-3 py-2"><LivenessLamp value="stale/offline/unknown" compact /> non-live 관측</div>
        </div>
    );
}

function NodeCard({ node, selected, onSelect }) {
    const chips = activityChips(node);
    return (
        <button
            type="button"
            onClick={() => onSelect(node.id)}
            data-testid={`node-card-${node.id}`}
            className={`absolute w-[166px] rounded-xl border bg-white p-3 text-left shadow-sm transition-all ${selected ? "border-sky-300 ring-2 ring-sky-100 shadow-md" : "border-slate-200 hover:border-cyan-300 hover:shadow-md"}`}
            style={{ left: `${node.position.x}px`, top: `${node.position.y}px` }}
        >
            <div className="mb-2 flex items-center justify-between gap-2">
                <div className="text-[10px] font-semibold tracking-[0.18em] text-slate-500">{node.short}</div>
                <LivenessLamp value={node.observed_liveness} nodeId={node.id} compact />
            </div>
            <div className="text-sm font-semibold text-slate-900">{node.displayName}</div>
            <div className="mt-2 overflow-hidden rounded-lg border border-slate-200 bg-slate-50/80" data-testid={`node-card-rows-${node.id}`}>
                <NodeInfoRow label="node_id" value={node.id} testId={`node-info-row-${node.id}-node-id`} />
                <NodeInfoRow label="role" testId={`node-info-row-${node.id}-role`} valueTestId={`node-role-${node.id}`}>{node.role}</NodeInfoRow>
                <NodeInfoRow label="observed_liveness" testId={`node-info-row-${node.id}-observed-liveness`}>
                    <LivenessLamp value={node.observed_liveness} nodeId={`${node.id}-row`} compact />
                </NodeInfoRow>
                <NodeInfoRow label="reported_state" testId={`node-info-row-${node.id}-reported-state`}>
                    <ReportedStateBadge value={node.reported_state} nodeId={node.id} compact />
                </NodeInfoRow>
                {chips.slice(0, 4).map(([key, label, value]) => (
                    <NodeInfoRow key={key} label={label} value={value} testId={`node-info-row-${node.id}-activity-${key}`} valueTestId={`activity-chip-${node.id}-${key}`} />
                ))}
            </div>
        </button>
    );
}

function DiagramCanvas({ selectedNodeId, detailNode, detailState, onSelect, onClose }) {
    return (
        <section className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
            <div className="mb-3 flex items-center justify-between gap-3">
                <h2 className="text-sm font-semibold text-slate-900">구조 다이어그램</h2>
                <div className="rounded border border-slate-200 bg-slate-50 px-2 py-1 text-[11px] text-slate-500">data-plane 5-node chain</div>
            </div>
            <div className="overflow-x-auto overflow-y-visible pb-2">
                <div data-testid="diagram-overlay-host" className="relative mx-auto rounded-2xl border border-slate-200 bg-[radial-gradient(circle_at_top_left,#eef8ff,transparent_32%),linear-gradient(180deg,#ffffff_0%,#f8fbff_100%)]" style={{ width: `${diagramWidth}px`, height: `${diagramHeight}px` }}>
                    <svg className="absolute inset-0 h-full w-full" viewBox={`0 0 ${diagramWidth} ${diagramHeight}`} fill="none">
                        <defs>
                            <marker id="arrow-blue" markerWidth="10" markerHeight="10" refX="8" refY="5" orient="auto"><path d="M0,0 L10,5 L0,10 z" fill="#0ea5e9" /></marker>
                            <marker id="arrow-gray" markerWidth="10" markerHeight="10" refX="8" refY="5" orient="auto"><path d="M0,0 L10,5 L0,10 z" fill="#94a3b8" /></marker>
                        </defs>
                        <g data-testid="data-path">
                            {mainLinks.map((link) => {
                                const watch = link.condition === "watch";
                                const path = buildMainPath(link);
                                return (
                                    <g key={link.id}>
                                        <path d={path} stroke={watch ? "#cbd5e1" : "#bae6fd"} strokeWidth="16" strokeLinecap="round" opacity="0.7" />
                                        <path d={path} className={watch ? "" : "path-flow"} stroke={watch ? "#94a3b8" : "#0ea5e9"} strokeWidth="5" strokeLinecap="round" markerEnd={watch ? "url(#arrow-gray)" : "url(#arrow-blue)"} strokeDasharray={watch ? undefined : "10 8"} />
                                    </g>
                                );
                            })}
                        </g>
                        <text x="190" y="188" fontSize="11" fill="#0284c7" fontWeight="600">상태 수집</text>
                        <text x="444" y="202" fontSize="11" fill="#0284c7" fontWeight="600">EVENT 전달</text>
                        <text x="697" y="170" fontSize="11" fill="#0284c7" fontWeight="600">EVENT 전달</text>
                        <text x="938" y="126" fontSize="11" fill="#64748b" fontWeight="600">ACK 지연</text>
                    </svg>
                    <div className="absolute left-[88px] top-[28px] rounded-full border border-cyan-200 bg-cyan-50 px-3 py-1 text-[11px] font-medium text-cyan-700">Host -> Agent -> R1 -> R2 -> Monitor</div>
                    {revisedNodes.map((node) => <NodeCard key={node.id} node={node} selected={selectedNodeId === node.id} onSelect={onSelect} />)}
                    <DetailInspector node={detailNode} detailState={detailState} onClose={onClose} />
                </div>
            </div>
        </section>
    );
}

function ControlPanel() {
    return (
        <section className="rounded-lg border border-slate-200 bg-white p-3 shadow-sm">
            <div className="mb-3 text-sm font-semibold text-slate-900">명령 팔레트</div>
            <div className="mb-3 rounded border border-sky-200 bg-sky-50 px-3 py-2 text-xs leading-5 text-sky-800">focus / overview는 화면 전환이며, 아래 버튼은 static preview 의미만 보여줍니다.</div>
            <div className="grid grid-cols-3 gap-2">
                <button className="flex items-center justify-center gap-1 rounded bg-emerald-500 px-2 py-2 text-xs font-semibold text-white"><PlayIcon className="h-3 w-3" />시작</button>
                <button className="flex items-center justify-center gap-1 rounded border border-slate-300 bg-white px-2 py-2 text-xs font-semibold text-slate-700"><PauseIcon className="h-3 w-3" />정지</button>
                <button className="flex items-center justify-center gap-1 rounded border border-slate-300 bg-white px-2 py-2 text-xs font-semibold text-slate-700"><RotateCcwIcon className="h-3 w-3" />초기화</button>
            </div>
            <div className="mt-3 grid gap-2 text-xs">
                <button className="rounded border border-orange-200 bg-orange-50 px-3 py-2 text-left text-orange-700">fault cpu 6</button>
                <button className="rounded border border-rose-200 bg-rose-50 px-3 py-2 text-left text-rose-700">fault service 6</button>
                <button className="rounded border border-amber-200 bg-amber-50 px-3 py-2 text-left text-amber-700">fault latency 6</button>
            </div>
        </section>
    );
}

function DetailHeader({ node, onClose }) {
    return (
        <div className="sticky top-0 z-10 border-b border-slate-200 bg-white px-4 py-3">
            <div className="flex items-start justify-between gap-3">
                <div>
                    <div className="text-[10px] font-semibold tracking-[0.2em] text-slate-500">SELECTED NODE · {node.id}</div>
                    <h2 className="mt-1 text-base font-semibold text-slate-900">{node.displayName}</h2>
                    <div className="mt-2 flex flex-wrap items-center gap-3 text-xs">
                        <span data-testid={`detail-node-role-${node.id}`} className="rounded border border-slate-200 bg-white px-2 py-1">role · {node.role}</span>
                        <LivenessLamp value={node.observed_liveness} nodeId={`${node.id}-detail`} />
                        <span data-testid={`detail-reported-state-${node.id}`} data-reported-state-tone={reportedStateTone(node.reported_state)} className="rounded border border-cyan-200 bg-cyan-50 px-2 py-1 font-semibold text-cyan-700">reported_state · {node.reported_state}</span>
                        <span className="text-slate-500">last_seen · {formatScalar(node.last_seen)}</span>
                    </div>
                </div>
                <button type="button" data-testid="detail-close-button" onClick={onClose} className="rounded-full border border-slate-300 bg-white px-3 py-1 text-sm font-semibold text-slate-600 hover:bg-slate-50" aria-label="close detail inspector">X</button>
            </div>
        </div>
    );
}

function HostDetail({ node }) {
    const { host_state, detail } = node.activity;
    return (
        <div data-testid="host-detail" className="space-y-3">
            <Section title="Host Metrics" testId="host-metrics"><KeyValueRows rows={[["host_id", host_state.host_id], ["cpu_usage", host_state.cpu_usage], ["memory_usage", host_state.memory_usage], ["service_state", host_state.service_state], ["latency_ms", host_state.latency_ms], ["last_update_time", host_state.last_update_time]]} /></Section>
            <Section title="Runtime Tick / Injection" testId="host-runtime"><KeyValueRows rows={[["tick", detail.tick], ["injection_active", detail.fault_active], ["injection_type", detail.fault_type]]} /></Section>
            <TrafficSection traffic={node.traffic} />
        </div>
    );
}

function AgentDetail({ node }) {
    const activity = node.activity;
    const event = activity.emitted_event;
    return (
        <div data-testid="agent-detail" className="space-y-3">
            <Section title="Host Input" testId="agent-host-input"><KeyValueRows rows={Object.entries(activity.latest_input_state)} /></Section>
            <Section title="Input Result / Fault" testId="agent-fault"><KeyValueRows rows={[["latest_input_result", JSON.stringify(activity.latest_input_result)], ["detected_fault", activity.detected_fault]]} /></Section>
            <Section title="Emitted Event" testId="agent-emitted-event"><KeyValueRows rows={[["msg_type", event.msg_type], ["event_id", event.event_id], ["seq_no", event.seq_no], ["host_id", event.host_id], ["agent_id", event.agent_id], ["event_type", event.event_type], ["severity", event.severity], ["timestamp", event.timestamp], ["payload.cpu", event.payload.cpu], ["payload.memory", event.payload.memory], ["payload.service_state", event.payload.service_state], ["payload.latency_ms", event.payload.latency_ms], ["payload.fault_mode", event.payload.fault_mode]]} /></Section>
            <Section title="Downstream / Last Event" testId="agent-downstream"><KeyValueRows rows={[["downstream_result", JSON.stringify(activity.downstream_result)], ["last_event", activity.last_event]]} /></Section>
            <TrafficSection traffic={node.traffic} />
        </div>
    );
}

function RelayDetail({ node }) {
    const activity = node.activity;
    return (
        <div data-testid={`relay-detail-${node.id}`} className="space-y-3">
            <Section title="Received Event" testId={`relay-received-${node.id}`}><KeyValueRows rows={Object.entries(activity.last_received_event)} /></Section>
            <Section title="Pending ACK Table" testId={`relay-ack-${node.id}`}>
                <DataTable columns={[{ key: "event_id", label: "event_id" }, { key: "event_type", label: "event_type" }, { key: "seq_no", label: "seq_no" }, { key: "downstream_target", label: "downstream_target" }, { key: "attempt", label: "attempt" }, { key: "state", label: "state" }, { key: "last_outcome", label: "last_outcome" }, { key: "ack_from", label: "ack_from" }]} rows={activity.pending_ack_state} />
            </Section>
            <Section title="Retry / Dedup Counters" testId={`relay-counters-${node.id}`}><KeyValueRows rows={[["pending_ack_count", activity.pending_ack_count], ["retry_total", activity.retry_total], ["duplicate_dropped", activity.duplicate_dropped], ["recent_received_event_ids", activity.recent_received_event_ids]]} /></Section>
            <Section title="Downstream / Forwarding Result" testId={`relay-results-${node.id}`}><KeyValueRows rows={[["last_downstream_result", JSON.stringify(activity.last_downstream_result)], ["last_forwarded_result", JSON.stringify(activity.last_forwarded_result)]]} /></Section>
            <TrafficSection traffic={node.traffic} />
        </div>
    );
}

function MonitorDetail({ node }) {
    const activity = node.activity;
    const hostRows = Object.entries(activity.host_state_table).map(([host_id, value]) => ({ host_id, event_type: value.event_type, severity: value.severity, payload: JSON.stringify(value.payload), timestamp: value.timestamp }));
    return (
        <div data-testid="monitor-detail" className="space-y-3">
            <Section title="Event Sink Summary" testId="monitor-events"><DataTable columns={[{ key: "event_id", label: "event_id" }, { key: "event_type", label: "event_type" }, { key: "severity", label: "severity" }, { key: "host_id", label: "host_id" }, { key: "seq_no", label: "seq_no" }, { key: "timestamp", label: "timestamp" }]} rows={activity.recent_event_summaries} /></Section>
            <Section title="Last Processed Event" testId="monitor-last-event"><KeyValueRows rows={Object.entries(activity.last_processed_event)} /></Section>
            <Section title="Sink / ACK Result" testId="monitor-results"><KeyValueRows rows={[["last_sink_result", JSON.stringify(activity.last_sink_result)], ["last_ack_result", JSON.stringify(activity.last_ack_result)]]} /></Section>
            <Section title="Host State Table" testId="monitor-host-table"><DataTable columns={[{ key: "host_id", label: "host_id" }, { key: "event_type", label: "event_type" }, { key: "severity", label: "severity" }, { key: "payload", label: "payload" }, { key: "timestamp", label: "timestamp" }]} rows={hostRows} /></Section>
            <Section title="Counters" testId="monitor-counters"><KeyValueRows rows={[["out_of_order_count", activity.out_of_order_count], ["total_logged", activity.total_logged], ["duplicate_count", activity.duplicate_count]]} /></Section>
            <TrafficSection traffic={node.traffic} />
        </div>
    );
}

function RoleDetail({ node }) {
    if (node.id === "host-simulator") return <HostDetail node={node} />;
    if (node.id === "local-agent") return <AgentDetail node={node} />;
    if (node.role === "Relay") return <RelayDetail node={node} />;
    return <MonitorDetail node={node} />;
}

function DetailInspector({ node, detailState, onClose }) {
    if (!node) return null;
    return (
        <aside
            data-testid="node-detail-inspector"
            data-overlay="diagram"
            data-detail-state={detailState}
            className={`detail-inspector-overlay absolute bottom-4 right-4 top-4 z-30 w-[calc(100%-2rem)] min-w-0 max-w-[520px] sm:min-w-[360px] xl:w-[33vw] ${detailState === "closing" ? "detail-inspector-closing" : "detail-inspector-open"}`}
        >
            <div data-testid="detail-inspector-overlay" className="h-full overflow-y-auto rounded-xl border border-slate-200 bg-white shadow-2xl ring-1 ring-slate-900/5">
                <DetailHeader node={node} onClose={onClose} />
                <div className="space-y-3 bg-slate-50 p-3"><RoleDetail node={node} /></div>
            </div>
        </aside>
    );
}

function hasOwn(object, key) {
    return Object.prototype.hasOwnProperty.call(object, key);
}

function runSanityChecks() {
    const serialized = JSON.stringify({ revisedNodes, mainLinks });
    const forbiddenExact = ["activityLogs", "note", "비고", "설명", "description", ["state", "="].join(""), ["state ", "="].join(""), ["attempt", "="].join(""), ["attempt ", "="].join(""), ["queue", "="].join(""), ["pending", "="].join(""), ["retries", "="].join(""), ["dup", "="].join("")];
    console.assert(Array.isArray(revisedNodes), "revisedNodes should be an array");
    console.assert(revisedNodes.length === 5, "there should be five data-plane nodes");
    console.assert(revisedNodes.map((node) => node.id).join(",") === nodeOrder.join(","), "node ids should preserve canonical data-plane order");
    console.assert(mainLinks.length === 4, "there should be four data path links");
    console.assert(mainLinks.every((link) => nodeOrder.includes(link.from) && nodeOrder.includes(link.to)), "links should connect data-plane nodes only");
    console.assert(revisedNodes.every((node) => ["observed_liveness", "reported_state", "activity", "traffic"].every((key) => hasOwn(node, key))), "every node should keep separated liveness, reported state, activity, and traffic fields");
    console.assert(revisedNodes.every((node) => node.role && node.displayName && node.id), "every node should expose id, display name, and role");
    console.assert(revisedNodes.some((node) => node.observed_liveness !== "live" && String(node.reported_state).localeCompare("실행 중") === 0), "one sample should prove liveness and reported runtime value stay separate");
    console.assert(revisedNodes.every((node) => livenessLampTone(node.observed_liveness) === (node.observed_liveness === "live" ? "green" : "gray")), "lamp color should depend only on observed_liveness");
    console.assert(revisedNodes.every((node) => reportedStateTone(node.reported_state) === "running"), "reported_state should map to its own running tone in the sample data");
    console.assert(getNodeById("r2").observed_liveness !== "live" && reportedStateTone(getNodeById("r2").reported_state) === "running", "reported_state tone should stay separate from non-live liveness");
    console.assert(revisedNodes.every((node) => activityChips(node).length > 0), "every card should have activity chips");
    console.assert(revisedNodes.every((node) => node.traffic && ["capture_seq", "captured_at", "previous_peer", "next_peer", "recent"].every((key) => hasOwn(node.traffic, key))), "every node should have structured traffic snapshot fields");
    console.assert(revisedNodes.every((node) => node.traffic.recent.every((item) => hasOwn(item, "peer_role"))), "traffic recent rows should keep peer_role");
    console.assert(getNodeById("host-simulator").activity.host_state.host_id === "host-1", "Host detail contract should expose host_state");
    console.assert(getNodeById("local-agent").activity.emitted_event.msg_type === "EVENT", "Agent detail contract should expose emitted event");
    console.assert(getNodeById("r1").activity.pending_ack_state[0].downstream_target === "r2", "R1 should use relay contract with R2 target");
    console.assert(getNodeById("r2").activity.pending_ack_state[0].downstream_target === "monitor", "R2 should use relay contract with Monitor target");
    console.assert(getNodeById("monitor").activity.host_state_table["host-1"].payload.fault_mode === "CPU_SPIKE", "Monitor detail contract should expose Agent-authored event payload compatibility");
    console.assert(forbiddenExact.every((fragment) => !serialized.includes(fragment)), "preview data should not include forbidden narrative or copied TUI fragments");
}

runSanityChecks();

function NetworkDemoWebUIRevised() {
    const [selectedNodeId, setSelectedNodeId] = useState(null);
    const [detailNodeId, setDetailNodeId] = useState(null);
    const [detailState, setDetailState] = useState("closed");
    const closeTimerRef = useRef(null);
    const detailNode = detailNodeId ? getNodeById(detailNodeId) : null;

    function handleSelectNode(nodeId) {
        if (closeTimerRef.current) {
            window.clearTimeout(closeTimerRef.current);
            closeTimerRef.current = null;
        }
        setSelectedNodeId(nodeId);
        setDetailNodeId(nodeId);
        setDetailState("open");
    }

    function handleCloseDetail() {
        setDetailState("closing");
        closeTimerRef.current = window.setTimeout(() => {
            setSelectedNodeId(null);
            setDetailNodeId(null);
            setDetailState("closed");
            closeTimerRef.current = null;
        }, 220);
    }

    return (
        <div className="min-h-screen bg-[#f3f6fb] p-4 text-slate-900">
            <style>{`
                @keyframes pathFlow {
                    from { stroke-dashoffset: 36; }
                    to { stroke-dashoffset: 0; }
                }
                @keyframes detailInspectorIn {
                    from { opacity: 0; transform: translate3d(12px, -8px, 0) scale(0.985); }
                    to { opacity: 1; transform: translate3d(0, 0, 0) scale(1); }
                }
                .path-flow { animation: pathFlow 1.8s linear infinite; }
                .detail-inspector-overlay {
                    transform-origin: top right;
                    transition: opacity 220ms ease, transform 220ms ease;
                }
                .detail-inspector-open {
                    opacity: 1;
                    transform: translate3d(0, 0, 0) scale(1);
                    animation: detailInspectorIn 220ms ease both;
                }
                .detail-inspector-closing {
                    opacity: 0;
                    transform: translate3d(12px, -8px, 0) scale(0.985);
                    pointer-events: none;
                }
            `}</style>
            <div className="mx-auto max-w-[1600px] space-y-4">
                <HeaderSummary />
                <PageChrome />
                <main className="space-y-4">
                    <DiagramCanvas selectedNodeId={selectedNodeId} detailNode={detailNode} detailState={detailState} onSelect={handleSelectNode} onClose={handleCloseDetail} />
                    <div className="grid gap-4 lg:grid-cols-[1fr_360px]"><ControlPanel /></div>
                </main>
            </div>
        </div>
    );
}

window.NetworkDemoWebUIRevised = NetworkDemoWebUIRevised;
window.__NW_PREVIEW_PARITY__ = {
    revisedNodes,
    mainLinks,
    nodeOrder,
};
