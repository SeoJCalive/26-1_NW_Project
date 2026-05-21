const { useState } = React;

const diagramWidth = 1180;
const diagramHeight = 620;

const revisedNodes = [
    {
        id: "host",
        name: "호스트 시뮬레이터",
        short: "HOST",
        status: "정상",
        tone: "green",
        position: { x: 56, y: 70 },
        cardStats: [
            ["CPU", "62%"],
            ["메모리", "41%"],
            ["서비스", "정상"],
        ],
        metrics: ["Tick 12", "Agent 보고", "Fault 없음", "지연 정상"],
        detailRows: [
            ["역할", "상태 소스"],
            ["최근 Tick", "12"],
            ["Export 대상", "Local Agent"],
            ["Fault", "없음"],
        ],
        logs: [
            "[정보] Host tick 샘플링 완료",
            "[정보] CPU 범위 정상 유지",
            "[정보] 상태를 Agent로 전달",
            "[제어] fault mode cleared",
            "[정보] 다음 tick 대기 중",
        ],
    },
    {
        id: "agent",
        name: "로컬 에이전트",
        short: "AGENT",
        status: "감시 중",
        tone: "cyan",
        position: { x: 278, y: 214 },
        cardStats: [
            ["이벤트", "MSG_A"],
            ["Seq", "003"],
            ["폴링", "2.0s"],
        ],
        metrics: ["Host 변화 감지", "ACK 대기", "Queue 0", "다음 R1"],
        detailRows: [
            ["역할", "이벤트 생성"],
            ["최근 이벤트", "MSG_A"],
            ["Payload", "CPU_SPIKE"],
            ["다음 홉", "Relay R1"],
        ],
        logs: [
            "[정보] Host 상태 변화 감지",
            "[EVENT] MSG_A seq=003 생성",
            "[SEND] Relay R1로 전송",
            "[WAIT] Downstream ACK 대기",
            "[정보] 다음 host delta 감시 중",
        ],
    },
    {
        id: "r1",
        name: "릴레이 R1",
        short: "R1",
        status: "전달 중",
        tone: "amber",
        position: { x: 538, y: 214 },
        cardStats: [
            ["Queue", "1"],
            ["ACK", "ACK_A"],
            ["Delay", "1.5s"],
        ],
        metrics: ["재전송 1", "중복 0", "R2 연결 정상", "1차 홉"],
        detailRows: [
            ["역할", "1차 전달 홉"],
            ["상위", "Agent"],
            ["하위", "Relay R2"],
            ["재전송 남음", "2"],
        ],
        logs: [
            "[RECV] Agent에서 MSG_A 수신",
            "[FWD] Relay R2로 전달",
            "[ACK] R2 ACK 대기 시작",
            "[정보] Queue 1 유지",
            "[정보] 링크 상태 양호",
        ],
    },
    {
        id: "r2",
        name: "릴레이 R2",
        short: "R2",
        status: "재시도 대기",
        tone: "orange",
        position: { x: 798, y: 126 },
        cardStats: [
            ["Queue", "1"],
            ["재전송", "2"],
            ["ACK", "지연"],
        ],
        metrics: ["Monitor ACK 미도착", "Timeout 감지", "중복 0", "2차 홉"],
        detailRows: [
            ["역할", "2차 전달 홉"],
            ["상위", "Relay R1"],
            ["하위", "Monitor"],
            ["현재 상태", "재시도 대기"],
        ],
        logs: [
            "[RECV] R1에서 MSG_A 수신",
            "[TIMEOUT] ACK_A 미도착",
            "[RETRY] Monitor로 재전송 준비",
            "[WAIT] Monitor ACK 대기",
            "[경고] 링크 품질 저하",
        ],
    },
    {
        id: "monitor",
        name: "모니터",
        short: "MON",
        status: "수신 준비",
        tone: "green",
        position: { x: 1000, y: 72 },
        cardStats: [
            ["수신", "3"],
            ["ACK", "반환"],
            ["중복", "0"],
        ],
        metrics: ["수신 준비", "ACK 반환", "역순 0", "Counter 안정"],
        detailRows: [
            ["역할", "최종 수신지"],
            ["최근 수신", "MSG_A"],
            ["최근 ACK", "ACK_A"],
            ["중복 처리", "0"],
        ],
        logs: [
            "[RECV] MSG_A 수용 완료",
            "[ACK] ACK_A 반환",
            "[정보] Counter 갱신",
            "[정보] 다음 이벤트 대기",
            "[정보] Sink 경로 응답 양호",
        ],
    },
];

const reportingHub = {
    id: "ops-hub",
    title: "모니터링 / 제어",
    subtitle: "상태 수집 · 제어 명령 · 추후 신호 처리 확장",
    x: 884,
    y: 332,
    width: 250,
    height: 170,
};

const mainLinks = [
    { id: "host-agent", from: "host", to: "agent", label: "상태 보고", state: "active" },
    { id: "agent-r1", from: "agent", to: "r1", label: "이벤트 전달", state: "active" },
    { id: "r1-r2", from: "r1", to: "r2", label: "이벤트 전달", state: "active" },
    { id: "r2-monitor", from: "r2", to: "monitor", label: "ACK 대기", state: "broken" },
];

const reportLinks = revisedNodes.map((node) => ({
    id: `report-${node.id}`,
    from: node.id,
    to: reportingHub.id,
    label: "상태 보고",
}));

const timeline = [
    { step: "01", text: "AGENT가 MSG_A / seq=003 생성", tone: "ok" },
    { step: "02", text: "R1이 이벤트를 R2로 전달", tone: "ok" },
    { step: "03", text: "R2가 Monitor ACK 대기", tone: "warn" },
    { step: "04", text: "ACK 지연으로 재전송 경로 활성화", tone: "warn" },
    { step: "05", text: "모니터링 / 제어 영역에 상태 집계", tone: "idle" },
];

function IconBase({ className = "h-4 w-4", children, viewBox = "0 0 24 24" }) {
    return (
        <svg
            viewBox={viewBox}
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
            className={className}
            aria-hidden="true"
        >
            {children}
        </svg>
    );
}

function CpuIcon({ className }) {
    return (
        <IconBase className={className}>
            <rect x="7" y="7" width="10" height="10" rx="2" />
            <path d="M9 1v3" />
            <path d="M15 1v3" />
            <path d="M9 20v3" />
            <path d="M15 20v3" />
            <path d="M20 9h3" />
            <path d="M20 14h3" />
            <path d="M1 9h3" />
            <path d="M1 14h3" />
        </IconBase>
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

function AlertTriangleIcon({ className }) {
    return (
        <IconBase className={className}>
            <path d="M10.29 3.86 1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z" />
            <line x1="12" y1="9" x2="12" y2="13" />
            <line x1="12" y1="17" x2="12.01" y2="17" />
        </IconBase>
    );
}

function toneClasses(tone) {
    const map = {
        green: {
            dot: "bg-emerald-500",
            text: "text-emerald-700",
            soft: "border-emerald-200 bg-emerald-50",
            ring: "ring-emerald-100",
        },
        cyan: {
            dot: "bg-cyan-500",
            text: "text-cyan-700",
            soft: "border-cyan-200 bg-cyan-50",
            ring: "ring-cyan-100",
        },
        amber: {
            dot: "bg-amber-500",
            text: "text-amber-700",
            soft: "border-amber-200 bg-amber-50",
            ring: "ring-amber-100",
        },
        orange: {
            dot: "bg-orange-500",
            text: "text-orange-700",
            soft: "border-orange-200 bg-orange-50",
            ring: "ring-orange-100",
        },
    };
    return map[tone] || map.green;
}

function getNodeById(nodeId) {
    return revisedNodes.find((node) => node.id === nodeId);
}

function getNodeCenter(node) {
    return { x: node.position.x + 82, y: node.position.y + 58 };
}

function getHubAnchor() {
    return { x: reportingHub.x + 24, y: reportingHub.y + reportingHub.height / 2 };
}

function buildMainPath(link) {
    const from = getNodeCenter(getNodeById(link.from));
    const to = getNodeCenter(getNodeById(link.to));
    const midX = Math.round((from.x + to.x) / 2);
    return `M ${from.x} ${from.y} C ${midX} ${from.y}, ${midX} ${to.y}, ${to.x} ${to.y}`;
}

function buildReportPath(link) {
    const from = getNodeCenter(getNodeById(link.from));
    const hub = getHubAnchor();
    const bendX = Math.max(from.x + 32, hub.x - 90);
    return `M ${from.x} ${from.y + 12} C ${bendX} ${from.y + 18}, ${hub.x - 70} ${hub.y}, ${hub.x} ${hub.y}`;
}

function HeaderSummary() {
    const summaryCards = [
                        ["운영 상태", "실행 중", "text-emerald-700"],
        ["현재 이벤트", "MSG_A", "text-cyan-700"],
                        ["재전송", "2", "text-amber-700"],
        ["중복", "0", "text-slate-700"],
    ];

    return (
        <header className="rounded-lg border border-slate-200 bg-white px-4 py-3 shadow-sm">
            <div className="flex flex-wrap items-center justify-between gap-3">
                <div>
                    <h1 className="text-lg font-bold tracking-wide text-slate-900">
                        NET-DEMO 관제 화면 · 신뢰 전달
                    </h1>
                    <div className="mt-1 text-xs text-slate-500">
                        홉 간 ACK · timeout/retry · duplicate suppression
                    </div>
                </div>
                <div className="grid grid-cols-4 gap-2 text-center text-[11px]">
                    {summaryCards.map(([label, value, valueClass]) => (
                        <div
                            key={label}
                            className="rounded border border-slate-200 bg-slate-50 px-3 py-2"
                        >
                            <div className="text-slate-500">{label}</div>
                            <div className={valueClass}>{value}</div>
                        </div>
                    ))}
                </div>
            </div>
        </header>
    );
}

function NodeCard({ node, selected, onSelect }) {
    const tone = toneClasses(node.tone);

    return (
        <button
            type="button"
            onClick={() => onSelect(node.id)}
            className={`absolute w-[164px] rounded-xl border bg-white p-3 text-left shadow-sm transition-all ${
                selected
                    ? `${tone.soft} ring-2 ${tone.ring} shadow-md`
                    : "border-slate-200 hover:border-cyan-300 hover:shadow-md"
            }`}
            style={{ left: `${node.position.x}px`, top: `${node.position.y}px` }}
        >
            <div className="mb-2 flex items-center justify-between gap-2">
                <div className="flex items-center gap-2 text-[10px] font-semibold tracking-[0.18em] text-slate-500">
                    <span className={`h-2.5 w-2.5 rounded-full ${tone.dot}`} />
                    {node.short}
                </div>
                <div className={`rounded border px-1.5 py-0.5 text-[10px] font-medium ${tone.soft} ${tone.text}`}>
                    {node.status}
                </div>
            </div>
            <div className="text-sm font-semibold text-slate-900">{node.name}</div>
            <div className="mt-2 grid grid-cols-3 gap-1">
                {node.cardStats.map(([label, value]) => (
                    <div key={label} className="rounded border border-slate-200 bg-slate-50 px-1.5 py-1 text-center">
                        <div className="text-[9px] text-slate-500">{label}</div>
                        <div className="mt-0.5 text-[11px] font-semibold text-slate-800">{value}</div>
                    </div>
                ))}
            </div>
            <div className="mt-2 space-y-1 text-[10px] text-slate-600">
                {node.metrics.slice(0, 2).map((item) => (
                    <div key={item} className="truncate">
                        • {item}
                    </div>
                ))}
            </div>
        </button>
    );
}

function MonitoringHub() {
    return (
        <div
            className="absolute rounded-2xl border border-slate-300 bg-white/95 p-4 shadow-lg"
            style={{
                left: `${reportingHub.x}px`,
                top: `${reportingHub.y}px`,
                width: `${reportingHub.width}px`,
                height: `${reportingHub.height}px`,
            }}
        >
                    <div className="text-[10px] font-semibold tracking-[0.2em] text-slate-500">관제 허브</div>
            <div className="mt-1 text-base font-semibold text-slate-900">{reportingHub.title}</div>
            <div className="mt-1 text-xs leading-5 text-slate-500">{reportingHub.subtitle}</div>
            <div className="mt-4 grid grid-cols-2 gap-2 text-[11px]">
                <div className="rounded border border-slate-200 bg-slate-50 px-2 py-2 text-slate-700">노드 상태 수집</div>
                <div className="rounded border border-slate-200 bg-slate-50 px-2 py-2 text-slate-700">제어 명령 분배</div>
                <div className="rounded border border-slate-200 bg-slate-50 px-2 py-2 text-slate-700">이벤트 흐름 관찰</div>
                <div className="rounded border border-slate-200 bg-slate-50 px-2 py-2 text-slate-700">확장 신호 처리</div>
            </div>
        </div>
    );
}

function DiagramCanvas({ selectedNodeId, onSelect }) {
    return (
        <section className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
            <div className="mb-3 flex items-center justify-between gap-3">
                <h2 className="text-sm font-semibold text-slate-900">구조 다이어그램</h2>
                <div className="rounded border border-slate-200 bg-slate-50 px-2 py-1 text-[11px] text-slate-500">
                    주 경로 + 상태 보고 경로
                </div>
            </div>

            <div className="overflow-x-auto pb-2">
                <div
                    className="relative rounded-2xl border border-slate-200 bg-[radial-gradient(circle_at_top_left,#eef8ff,transparent_32%),linear-gradient(180deg,#ffffff_0%,#f8fbff_100%)]"
                    style={{ width: `${diagramWidth}px`, height: `${diagramHeight}px` }}
                >
                    <svg
                        className="absolute inset-0 h-full w-full"
                        viewBox={`0 0 ${diagramWidth} ${diagramHeight}`}
                        fill="none"
                    >
                        <defs>
                            <marker id="arrow-blue" markerWidth="10" markerHeight="10" refX="8" refY="5" orient="auto">
                                <path d="M0,0 L10,5 L0,10 z" fill="#0ea5e9" />
                            </marker>
                            <marker id="arrow-gray" markerWidth="10" markerHeight="10" refX="8" refY="5" orient="auto">
                                <path d="M0,0 L10,5 L0,10 z" fill="#94a3b8" />
                            </marker>
                            <marker id="arrow-report" markerWidth="10" markerHeight="10" refX="8" refY="5" orient="auto">
                                <path d="M0,0 L10,5 L0,10 z" fill="#38bdf8" />
                            </marker>
                        </defs>

                        {mainLinks.map((link) => {
                            const path = buildMainPath(link);
                            const broken = link.state === "broken";
                            return (
                                <g key={link.id}>
                                    <path
                                        d={path}
                                        stroke={broken ? "#cbd5e1" : "#bae6fd"}
                                        strokeWidth="16"
                                        strokeLinecap="round"
                                        opacity="0.7"
                                    />
                                    <path
                                        d={path}
                                        className={broken ? "" : "path-flow"}
                                        stroke={broken ? "#94a3b8" : "#0ea5e9"}
                                        strokeWidth="5"
                                        strokeLinecap="round"
                                        markerEnd={broken ? "url(#arrow-gray)" : "url(#arrow-blue)"}
                                        strokeDasharray={broken ? undefined : "10 8"}
                                    />
                                </g>
                            );
                        })}

                        {reportLinks.map((link) => {
                            const path = buildReportPath(link);
                            return (
                                <path
                                    key={link.id}
                                    d={path}
                                    className="path-report"
                                    stroke="#38bdf8"
                                    strokeWidth="2.5"
                                    strokeLinecap="round"
                                    strokeDasharray="4 8"
                                    markerEnd="url(#arrow-report)"
                                    opacity="0.8"
                                />
                            );
                        })}

                        <text x="194" y="188" fontSize="11" fill="#0284c7" fontWeight="600">상태 보고</text>
                        <text x="444" y="202" fontSize="11" fill="#0284c7" fontWeight="600">이벤트 전달</text>
                        <text x="697" y="170" fontSize="11" fill="#0284c7" fontWeight="600">이벤트 전달</text>
                        <text x="938" y="126" fontSize="11" fill="#64748b" fontWeight="600">ACK 대기</text>
                        <text x="918" y="286" fontSize="11" fill="#0ea5e9" fontWeight="600">상태 집계</text>

                        <circle cx="923" cy="214" r="16" fill="#ffffff" stroke="#cbd5e1" strokeWidth="2" />
                        <text x="917" y="219" fontSize="14" fill="#64748b" fontWeight="700">×</text>
                    </svg>

                    <div className="absolute left-[88px] top-[28px] rounded-full border border-cyan-200 bg-cyan-50 px-3 py-1 text-[11px] font-medium text-cyan-700">
                        데이터 경로
                    </div>
                    <div className="absolute left-[760px] top-[292px] rounded-full border border-sky-200 bg-sky-50 px-3 py-1 text-[11px] font-medium text-sky-700">
                        모니터링 경로
                    </div>

                    {revisedNodes.map((node) => (
                        <NodeCard
                            key={node.id}
                            node={node}
                            selected={selectedNodeId === node.id}
                            onSelect={onSelect}
                        />
                    ))}

                    <MonitoringHub />
                </div>
            </div>
        </section>
    );
}

function ControlPanel() {
    return (
        <section className="rounded-lg border border-slate-200 bg-white p-3 shadow-sm">
            <div className="mb-3 text-sm font-semibold text-slate-900">제어 패널</div>
            <div className="grid grid-cols-3 gap-2">
                <button className="flex items-center justify-center gap-1 rounded bg-emerald-500 px-2 py-2 text-xs font-semibold text-white">
                    <PlayIcon className="h-3 w-3" />
                    시작
                </button>
                <button className="flex items-center justify-center gap-1 rounded border border-slate-300 bg-white px-2 py-2 text-xs font-semibold text-slate-700">
                    <PauseIcon className="h-3 w-3" />
                    일시정지
                </button>
                <button className="flex items-center justify-center gap-1 rounded border border-slate-300 bg-white px-2 py-2 text-xs font-semibold text-slate-700">
                    <RotateCcwIcon className="h-3 w-3" />
                    초기화
                </button>
            </div>
            <div className="mt-3 grid gap-2 text-xs">
                <button className="rounded border border-orange-200 bg-orange-50 px-3 py-2 text-left text-orange-700">fault cpu 6</button>
                <button className="rounded border border-rose-200 bg-rose-50 px-3 py-2 text-left text-rose-700">fault service 6</button>
                <button className="rounded border border-amber-200 bg-amber-50 px-3 py-2 text-left text-amber-700">fault latency 6</button>
                <button className="rounded border border-slate-300 bg-slate-50 px-3 py-2 text-left text-slate-700">ackdrop</button>
            </div>
        </section>
    );
}

function EventTimeline() {
    return (
        <section className="rounded-lg border border-slate-200 bg-white p-3 shadow-sm">
            <div className="mb-3 flex items-center justify-between gap-2">
                <div className="text-sm font-semibold text-slate-900">현재 이벤트 흐름</div>
                <span className="rounded border border-cyan-200 bg-cyan-50 px-2 py-1 font-mono text-[11px] text-cyan-700">
                    MSG_A / seq=003
                </span>
            </div>
            <div className="space-y-2">
                {timeline.map((item) => (
                    <div
                        key={item.step}
                        className="flex items-center gap-3 rounded border border-slate-200 bg-slate-50 px-3 py-2"
                    >
                        <div
                            className={`flex h-6 w-6 items-center justify-center rounded-full text-[11px] font-bold ${
                                item.tone === "warn"
                                    ? "bg-amber-400 text-white"
                                    : item.tone === "ok"
                                      ? "bg-emerald-500 text-white"
                                      : "bg-slate-300 text-slate-700"
                            }`}
                        >
                            {item.step}
                        </div>
                        <div className="flex-1 text-xs text-slate-700">{item.text}</div>
                        {item.tone === "warn" && (
                            <AlertTriangleIcon className="h-4 w-4 text-amber-500" />
                        )}
                    </div>
                ))}
            </div>
        </section>
    );
}

function DetailPanel({ node }) {
    const tone = toneClasses(node.tone);

    return (
        <section className="sticky top-4 space-y-4">
            <div className="rounded-lg border border-slate-200 bg-white shadow-sm">
                <div className="border-b border-slate-200 px-4 py-3">
                    <div className="flex items-center justify-between gap-3">
                        <div>
                            <div className="text-[10px] font-semibold tracking-[0.2em] text-slate-500">
                                선택된 노드
                            </div>
                            <h2 className="mt-1 text-base font-semibold text-slate-900">{node.name}</h2>
                        </div>
                        <div className={`rounded border px-2 py-1 text-[11px] font-medium ${tone.soft} ${tone.text}`}>
                            {node.status}
                        </div>
                    </div>
                </div>

                <div className="space-y-4 px-4 py-4">
                    <div className="grid grid-cols-2 gap-2">
                        {node.metrics.map((item) => (
                            <div
                                key={item}
                                className="rounded border border-slate-200 bg-slate-50 px-2 py-2 text-[11px] text-slate-700"
                            >
                                {item}
                            </div>
                        ))}
                    </div>

                    <div className="rounded-lg border border-slate-200 bg-slate-50">
                        {node.detailRows.map(([label, value], index) => (
                            <div
                                key={label}
                                className={`flex items-center justify-between gap-3 px-3 py-2 text-xs ${
                                    index < node.detailRows.length - 1 ? "border-b border-slate-200" : ""
                                }`}
                            >
                                <span className="text-slate-500">{label}</span>
                                <span className="font-medium text-slate-800">{value}</span>
                            </div>
                        ))}
                    </div>

                    <div>
                        <div className="mb-2 text-[11px] font-semibold tracking-[0.18em] text-slate-500">
                            최근 활동
                        </div>
                        <div className="space-y-1 rounded-lg border border-slate-200 bg-[#f6fbff] px-3 py-3 font-mono text-[11px] leading-5 text-slate-700">
                            {node.logs.map((log) => (
                                <div key={log} className="truncate">
                                    {log}
                                </div>
                            ))}
                        </div>
                    </div>
                </div>
            </div>

            <div className="rounded-lg border border-slate-200 bg-white p-3 shadow-sm">
                <div className="mb-2 text-sm font-semibold text-slate-900">포트</div>
                <div className="flex items-center gap-2 text-xs text-slate-600">
                    <CpuIcon className="h-3.5 w-3.5" />
                    9101-9110
                </div>
            </div>
        </section>
    );
}

function runSanityChecks() {
    console.assert(Array.isArray(revisedNodes), "revisedNodes should be an array");
    console.assert(revisedNodes.length === 5, "there should be 5 nodes");
    console.assert(
        revisedNodes.every((node) => typeof node.name === "string" && /[가-힣]/.test(node.name)),
        "node names should include Korean labels",
    );
    console.assert(
        revisedNodes.every((node) => Array.isArray(node.cardStats) && node.cardStats.length === 3),
        "each node should expose compact monitoring card stats",
    );
    console.assert(mainLinks.length === 4, "there should be 4 main links");
    console.assert(reportLinks.length === 5, "every node should have a reporting link");
    console.assert(
        reportLinks.every((link) => link.to === reportingHub.id),
        "all reporting links should converge on the ops hub",
    );
}

runSanityChecks();

function NetworkDemoWebUIRevised() {
    const [selectedNodeId, setSelectedNodeId] = useState("r2");
    const selectedNode = getNodeById(selectedNodeId) || revisedNodes[0];

    return (
        <div className="min-h-screen bg-[#f3f6fb] p-4 text-slate-900">
            <style>{`
                @keyframes pathFlow {
                    from { stroke-dashoffset: 36; }
                    to { stroke-dashoffset: 0; }
                }
                @keyframes reportFlow {
                    from { stroke-dashoffset: 48; }
                    to { stroke-dashoffset: 0; }
                }
                .path-flow {
                    animation: pathFlow 1.8s linear infinite;
                }
                .path-report {
                    animation: reportFlow 2.4s linear infinite;
                }
            `}</style>

            <div className="mx-auto max-w-[1600px] space-y-4">
                <HeaderSummary />

                <div className="grid gap-4 xl:grid-cols-[1fr_360px]">
                    <main className="space-y-4">
                        <DiagramCanvas
                            selectedNodeId={selectedNode.id}
                            onSelect={setSelectedNodeId}
                        />
                        <div className="grid gap-4 lg:grid-cols-[1fr_320px]">
                            <ControlPanel />
                            <EventTimeline />
                        </div>
                    </main>

                    <aside>
                        <DetailPanel node={selectedNode} />
                    </aside>
                </div>
            </div>
        </div>
    );
}

window.NetworkDemoWebUIRevised = NetworkDemoWebUIRevised;
