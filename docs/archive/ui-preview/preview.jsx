import React from "react";

/**
 * Local inline SVG icons
 * - Replaces lucide-react dependency to avoid CDN/package fetch failures
 * - Accepts className for sizing/styling
 */
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

function ActivityIcon({ className }) {
    return (
        <IconBase className={className}>
            <polyline points="22 12 18 12 15 21 9 3 6 12 2 12" />
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

function PauseIcon({ className }) {
    return (
        <IconBase className={className}>
            <rect x="6" y="4" width="4" height="16" />
            <rect x="14" y="4" width="4" height="16" />
        </IconBase>
    );
}

function PlayIcon({ className }) {
    return (
        <IconBase className={className}>
            <polygon
                points="8 5 19 12 8 19 8 5"
                fill="currentColor"
                stroke="none"
            />
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

function SendIcon({ className }) {
    return (
        <IconBase className={className}>
            <line x1="22" y1="2" x2="11" y2="13" />
            <polygon points="22 2 15 22 11 13 2 9 22 2" />
        </IconBase>
    );
}

function SettingsIcon({ className }) {
    return (
        <IconBase className={className}>
            <circle cx="12" cy="12" r="3" />
            <path d="M19.4 15a1.7 1.7 0 0 0 .33 1.82l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06A1.7 1.7 0 0 0 15 19.4a1.7 1.7 0 0 0-1 .6 1.7 1.7 0 0 0-.4 1.06V21a2 2 0 1 1-4 0v-.09A1.7 1.7 0 0 0 9 19.4a1.7 1.7 0 0 0-1-.6 1.7 1.7 0 0 0-1.82.33l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06A1.7 1.7 0 0 0 4.6 15a1.7 1.7 0 0 0-.6-1 1.7 1.7 0 0 0-1.06-.4H2.9a2 2 0 1 1 0-4H3a1.7 1.7 0 0 0 1.6-1 1.7 1.7 0 0 0-.33-1.82l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06A1.7 1.7 0 0 0 9 4.6a1.7 1.7 0 0 0 1-.6 1.7 1.7 0 0 0 .4-1.06V2.9a2 2 0 1 1 4 0V3a1.7 1.7 0 0 0 1 1.6 1.7 1.7 0 0 0 1.82-.33l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06A1.7 1.7 0 0 0 19.4 9a1.7 1.7 0 0 0 .6 1 1.7 1.7 0 0 0 1.06.4h.09a2 2 0 1 1 0 4H21a1.7 1.7 0 0 0-1.6 1z" />
        </IconBase>
    );
}

const nodes = [
    {
        name: "Host Simulator",
        short: "HOST",
        status: "Online",
        tone: "green",
        sent: 0,
        recv: 0,
        details: ["CPU 62%", "Memory 41%", "Service OK", "Latency Normal"],
        logs: [
            "[INFO] Host tick sampled",
            "[INFO] Status exported to Agent",
            "[CTRL] Fault mode cleared",
        ],
    },
    {
        name: "Local Agent",
        short: "AGENT",
        status: "Watching Host",
        tone: "cyan",
        sent: 3,
        recv: 12,
        details: [
            "Last event: MSG_A",
            "Seq: 003",
            "Payload: CPU_SPIKE",
            "Next hop: Relay R1",
        ],
        logs: [
            "[INFO] Host state changed",
            "[EVENT] Created MSG_A seq=003",
            "[SEND] MSG_A forwarded to R1",
        ],
    },
    {
        name: "Relay R1",
        short: "R1",
        status: "Forwarding / Wait ACK",
        tone: "amber",
        sent: 3,
        recv: 12,
        details: [
            "Queue: 1",
            "Pending ACK: ACK_A",
            "Retries: 1",
            "Delay: 1.5s",
        ],
        logs: [
            "[RECV] MSG_A from Agent",
            "[FWD] MSG_A to Relay R2",
            "[ACK] Waiting ACK from R2",
        ],
    },
    {
        name: "Relay R2",
        short: "R2",
        status: "Retry Scheduled",
        tone: "orange",
        sent: 2,
        recv: 11,
        details: [
            "Queue: 1",
            "Pending ACK: ACK_A",
            "Retries: 2",
            "Duplicate drop: 0",
        ],
        logs: [
            "[RECV] MSG_A from R1",
            "[TIMEOUT] ACK_A missing",
            "[RETRY] MSG_A to Monitor",
        ],
    },
    {
        name: "Monitor",
        short: "MON",
        status: "Sink Ready",
        tone: "green",
        sent: 1,
        recv: 2,
        details: [
            "Logged: 3",
            "Duplicate: 0",
            "Out-of-order: 0",
            "Last ACK: MSG_A",
        ],
        logs: [
            "[RECV] MSG_A accepted",
            "[ACK] ACK_A returned to R2",
            "[INFO] Counters updated",
        ],
    },
];

const timeline = [
    { step: "1", text: "Agent creates EVENT MSG_A", ok: true },
    { step: "2", text: "R1 receives and forwards", ok: true },
    { step: "3", text: "R2 waits for ACK", ok: true },
    { step: "4", text: "Timeout triggers retry", warn: true },
    { step: "5", text: "Monitor accepts and ACKs", ok: false },
];

function toneClasses(tone) {
    const map = {
        green: "bg-emerald-400 shadow-emerald-400/70 text-emerald-300 border-emerald-500/40",
        cyan: "bg-cyan-400 shadow-cyan-400/70 text-cyan-300 border-cyan-500/40",
        amber: "bg-amber-400 shadow-amber-400/70 text-amber-300 border-amber-500/40",
        orange: "bg-orange-400 shadow-orange-400/70 text-orange-300 border-orange-500/40",
    };
    return map[tone] || map.green;
}

function StatusDot({ tone = "green" }) {
    const toneClass = toneClasses(tone);
    const parts = toneClass.split(" ");
    const bgClass = parts[0];
    const shadowClass = parts[1];

    return (
        <span
            className={`h-2.5 w-2.5 rounded-full ${bgClass} shadow-lg ${shadowClass}`}
        />
    );
}

function MiniQueue({ active = 2 }) {
    return (
        <div className="flex items-end gap-1.5 rounded-md border border-slate-600/60 bg-slate-950/40 px-3 py-2">
            {[0, 1, 2].map((i) => (
                <div
                    key={i}
                    className={`w-3 rounded-sm ${i < active ? "bg-cyan-400/70" : "bg-slate-700/80"}`}
                    style={{ height: `${18 + i * 6}px` }}
                />
            ))}
        </div>
    );
}

function NodePanel({ node, index }) {
    const toneClass = toneClasses(node.tone);
    const toneParts = toneClass.split(" ");
    const textColorClass = toneParts[2];

    return (
        <section className="overflow-hidden rounded-lg border border-slate-600/70 bg-slate-900/80 shadow-xl shadow-black/30">
            <div className="flex items-center justify-between border-b border-slate-700/80 bg-slate-800/70 px-3 py-2">
                <div>
                    <h3 className="text-sm font-semibold tracking-wide text-slate-100">
                        {node.name}
                    </h3>
                    <div className="mt-1 text-[10px] text-slate-400">
                        Independent process · TCP/JSON
                    </div>
                </div>
                <div className="flex items-center gap-2">
                    <StatusDot tone={node.tone} />
                    <span className={`text-[11px] ${textColorClass}`}>
                        {node.status}
                    </span>
                </div>
            </div>

            <div className="grid grid-cols-[88px_1fr] gap-3 px-3 py-3">
                <div className="rounded-md border border-slate-600/70 bg-slate-950/50 p-2 text-center">
                    <div className="mx-auto mb-2 flex h-12 w-12 items-center justify-center rounded-md border border-cyan-500/40 bg-cyan-950/30 text-xs font-bold text-cyan-200">
                        {node.short}
                    </div>
                    <div className="space-y-1 text-[10px] text-slate-400">
                        <div>
                            Sent:{" "}
                            <span className="text-slate-200">{node.sent}</span>
                        </div>
                        <div>
                            Recv:{" "}
                            <span className="text-slate-200">{node.recv}</span>
                        </div>
                    </div>
                </div>

                <div className="space-y-3">
                    <div className="flex items-center justify-between gap-3">
                        <div className="min-w-0 flex-1">
                            <div className="text-[10px] uppercase tracking-widest text-slate-500">
                                State summary
                            </div>
                            <div className="mt-1 truncate text-xs text-slate-100">
                                {node.status}
                            </div>
                        </div>
                        <MiniQueue
                            active={index === 4 ? 1 : index === 0 ? 0 : 2}
                        />
                    </div>

                    <div className="grid grid-cols-2 gap-1.5 text-[11px]">
                        {node.details.map((item) => (
                            <div
                                key={item}
                                className="rounded border border-slate-700/70 bg-slate-950/30 px-2 py-1 text-slate-300"
                            >
                                {item}
                            </div>
                        ))}
                    </div>
                </div>
            </div>

            <div className="border-t border-slate-700/80 bg-slate-950/35 px-3 py-2">
                <div className="mb-1.5 flex items-center gap-2 text-[10px] uppercase tracking-widest text-slate-500">
                    <ActivityIcon className="h-3 w-3" />
                    Node recent activity
                </div>
                <div className="space-y-1 font-mono text-[11px] leading-4">
                    {node.logs.map((log) => (
                        <div key={log} className="truncate text-cyan-200/90">
                            {log}
                        </div>
                    ))}
                </div>
            </div>
        </section>
    );
}

function TopologyStrip() {
    const chain = ["HOST", "AGENT", "R1", "R2", "MONITOR"];

    return (
        <div className="rounded-lg border border-slate-600/70 bg-slate-900/75 p-3 shadow-xl shadow-black/30">
            <div className="mb-3 flex items-center justify-between">
                <h2 className="text-sm font-semibold text-slate-100">
                    Event Flow Topology
                </h2>
                <div className="text-[11px] text-slate-400">
                    Data path only · Controller is out-of-band
                </div>
            </div>
            <div className="flex items-center gap-2 overflow-hidden">
                {chain.map((item, i) => (
                    <React.Fragment key={item}>
                        <div className="flex min-w-[86px] items-center justify-center rounded-md border border-cyan-500/40 bg-cyan-950/30 px-3 py-2 text-xs font-semibold text-cyan-100">
                            {item}
                        </div>
                        {i < chain.length - 1 && (
                            <div className="flex flex-1 items-center gap-1">
                                <div className="h-px flex-1 bg-cyan-500/50" />
                                <SendIcon className="h-3.5 w-3.5 text-orange-300" />
                            </div>
                        )}
                    </React.Fragment>
                ))}
            </div>
        </div>
    );
}

function ControlPanel() {
    return (
        <aside className="space-y-3 rounded-lg border border-slate-600/70 bg-slate-900/80 p-3 shadow-xl shadow-black/30">
            <div className="flex items-center justify-between border-b border-slate-700/80 pb-2">
                <h2 className="text-sm font-semibold text-slate-100">
                    Control & Settings
                </h2>
                <SettingsIcon className="h-4 w-4 text-slate-400" />
            </div>

            <div>
                <div className="mb-2 text-[11px] uppercase tracking-widest text-slate-500">
                    Simulation
                </div>
                <div className="grid grid-cols-3 gap-2">
                    <button className="flex items-center justify-center gap-1 rounded bg-emerald-500/80 px-2 py-2 text-xs font-semibold text-slate-950">
                        <PlayIcon className="h-3 w-3" />
                        Start
                    </button>
                    <button className="flex items-center justify-center gap-1 rounded bg-slate-700 px-2 py-2 text-xs font-semibold text-slate-100">
                        <PauseIcon className="h-3 w-3" />
                        Pause
                    </button>
                    <button className="flex items-center justify-center gap-1 rounded bg-slate-700 px-2 py-2 text-xs font-semibold text-slate-100">
                        <RotateCcwIcon className="h-3 w-3" />
                        Reset
                    </button>
                </div>
            </div>

            <div>
                <div className="mb-2 text-[11px] uppercase tracking-widest text-slate-500">
                    Fault Injection
                </div>
                <div className="grid grid-cols-1 gap-2 text-xs">
                    <button className="rounded border border-orange-500/40 bg-orange-950/30 px-3 py-2 text-left text-orange-200">
                        fault cpu 6
                    </button>
                    <button className="rounded border border-rose-500/40 bg-rose-950/30 px-3 py-2 text-left text-rose-200">
                        fault service 6
                    </button>
                    <button className="rounded border border-amber-500/40 bg-amber-950/30 px-3 py-2 text-left text-amber-200">
                        fault latency 6
                    </button>
                    <button className="rounded border border-slate-500/40 bg-slate-950/50 px-3 py-2 text-left text-slate-200">
                        ackdrop
                    </button>
                </div>
            </div>

            <div>
                <div className="mb-2 text-[11px] uppercase tracking-widest text-slate-500">
                    Relay Delay
                </div>
                <div className="space-y-2 text-xs text-slate-300">
                    <label className="block">
                        R1 delay{" "}
                        <span className="float-right text-cyan-300">1.5s</span>
                    </label>
                    <div className="h-1.5 rounded-full bg-slate-700">
                        <div className="h-1.5 w-1/2 rounded-full bg-cyan-400" />
                    </div>
                    <label className="block">
                        R2 delay{" "}
                        <span className="float-right text-cyan-300">1.5s</span>
                    </label>
                    <div className="h-1.5 rounded-full bg-slate-700">
                        <div className="h-1.5 w-1/2 rounded-full bg-cyan-400" />
                    </div>
                </div>
            </div>
        </aside>
    );
}

function EventTimeline() {
    return (
        <section className="rounded-lg border border-slate-600/70 bg-slate-900/80 p-3 shadow-xl shadow-black/30">
            <div className="mb-3 flex items-center justify-between">
                <h2 className="text-sm font-semibold text-slate-100">
                    Current Event Trace
                </h2>
                <span className="rounded border border-cyan-500/40 bg-cyan-950/30 px-2 py-1 font-mono text-[11px] text-cyan-200">
                    MSG_A / seq=003
                </span>
            </div>
            <div className="space-y-2">
                {timeline.map((item) => (
                    <div
                        key={item.step}
                        className="flex items-center gap-3 rounded border border-slate-700/70 bg-slate-950/35 px-3 py-2"
                    >
                        <div
                            className={`flex h-6 w-6 items-center justify-center rounded-full text-[11px] font-bold ${
                                item.warn
                                    ? "bg-amber-400 text-slate-950"
                                    : item.ok
                                      ? "bg-emerald-400 text-slate-950"
                                      : "bg-slate-700 text-slate-300"
                            }`}
                        >
                            {item.step}
                        </div>
                        <div className="flex-1 text-xs text-slate-200">
                            {item.text}
                        </div>
                        {item.warn && (
                            <AlertTriangleIcon className="h-4 w-4 text-amber-300" />
                        )}
                    </div>
                ))}
            </div>
        </section>
    );
}

function GlobalLog() {
    const logs = [
        "[SYSTEM] Demo started by Controller",
        "[CONTROL] fault latency 6 applied",
        "[NODE:R2] ACK timeout detected",
        "[NODE:R2] Retrying MSG_A to Monitor",
        "[NODE:MON] Waiting for MSG_A retry",
    ];

    return (
        <section className="rounded-lg border border-slate-600/70 bg-slate-900/80 p-3 shadow-xl shadow-black/30">
            <h2 className="mb-2 text-sm font-semibold text-slate-100">
                Global Event Log
            </h2>
            <div className="space-y-1 font-mono text-[11px] leading-5">
                {logs.map((log) => (
                    <div key={log} className="truncate text-cyan-200/90">
                        {log}
                    </div>
                ))}
            </div>
        </section>
    );
}

/**
 * Basic sanity checks
 * Added because there were no tests.
 * These checks are intentionally lightweight and safe for sandbox execution.
 */
function runSanityChecks() {
    console.assert(Array.isArray(nodes), "nodes should be an array");
    console.assert(nodes.length === 5, "there should be 5 node panels");
    console.assert(
        nodes.every((n) => typeof n.name === "string" && n.name.length > 0),
        "each node needs a name",
    );
    console.assert(
        nodes.every((n) => Array.isArray(n.details)),
        "each node needs details array",
    );
    console.assert(
        nodes.every((n) => Array.isArray(n.logs)),
        "each node needs logs array",
    );
    console.assert(Array.isArray(timeline), "timeline should be an array");
    console.assert(timeline.length >= 1, "timeline should not be empty");
    console.assert(
        toneClasses("green").includes("bg-emerald-400"),
        "green tone mapping should exist",
    );
    console.assert(
        typeof toneClasses("unknown") === "string",
        "fallback tone should return a string",
    );
}

runSanityChecks();

export default function NetworkDemoWebUIConcept() {
    return (
        <div className="min-h-screen bg-[#07131d] p-4 text-slate-100">
            <div className="mx-auto max-w-[1500px] space-y-4">
                <header className="rounded-lg border border-slate-600/70 bg-slate-900/90 px-4 py-3 shadow-xl shadow-black/30">
                    <div className="flex flex-wrap items-center justify-between gap-3">
                        <div>
                            <h1 className="text-lg font-bold tracking-wide text-slate-50">
                                NET-DEMO Controller · Message Passing & Reliable
                                Delivery
                            </h1>
                            <p className="mt-1 text-xs text-slate-400">
                                교육용 네트워크 데모 · hop-by-hop ACK ·
                                timeout/retry · duplicate suppression
                            </p>
                        </div>
                        <div className="grid grid-cols-4 gap-2 text-center text-[11px]">
                            <div className="rounded border border-slate-600 bg-slate-950/40 px-3 py-2">
                                <div className="text-slate-500">Mode</div>
                                <div className="text-emerald-300">Running</div>
                            </div>
                            <div className="rounded border border-slate-600 bg-slate-950/40 px-3 py-2">
                                <div className="text-slate-500">Events</div>
                                <div className="text-cyan-300">3</div>
                            </div>
                            <div className="rounded border border-slate-600 bg-slate-950/40 px-3 py-2">
                                <div className="text-slate-500">Retries</div>
                                <div className="text-amber-300">2</div>
                            </div>
                            <div className="rounded border border-slate-600 bg-slate-950/40 px-3 py-2">
                                <div className="text-slate-500">Duplicate</div>
                                <div className="text-slate-200">0</div>
                            </div>
                        </div>
                    </div>
                </header>

                <div className="grid grid-cols-[1fr_320px] gap-4">
                    <main className="space-y-4">
                        <TopologyStrip />
                        <div className="grid grid-cols-2 gap-4 xl:grid-cols-3">
                            {nodes.map((node, index) => (
                                <NodePanel
                                    key={node.name}
                                    node={node}
                                    index={index}
                                />
                            ))}
                        </div>
                    </main>

                    <aside className="space-y-4">
                        <ControlPanel />
                        <EventTimeline />
                        <GlobalLog />
                    </aside>
                </div>

                <footer className="flex items-center justify-between rounded-lg border border-slate-700/70 bg-slate-950/50 px-4 py-2 text-[11px] text-slate-500">
                    <span>
                        UI concept based on terminal monitoring sections,
                        adapted to node-card web panels.
                    </span>
                    <span className="flex items-center gap-1">
                        <CpuIcon className="h-3 w-3" />
                        Ports: 9101-9110
                    </span>
                </footer>
            </div>
        </div>
    );
}
