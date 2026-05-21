from __future__ import annotations

import asyncio
import os
import shlex
import sys
from pathlib import Path

from . import config
from .controller_ui import ControllerUI
from .host_simulator import HostSimulator
from .local_agent import LocalAgent
from .monitor import Monitor
from .relay import RelayNode


ROLE_START_ORDER = ["host", "monitor", "relay-r2", "relay-r2b", "relay-r1", "relay-r1b", "agent"]


class LocalProcessSupervisor:
    def __init__(self, controller_host: str, controller_port: int, control_token: str | None) -> None:
        self.controller_host = controller_host
        self.controller_port = controller_port
        self.control_token = control_token
        self.processes: list[asyncio.subprocess.Process] = []

    async def start(self) -> None:
        main_path = Path(__file__).resolve().parent.parent / "main.py"
        for role in ROLE_START_ORDER:
            node_id = config.ROLE_TO_NODE_ID[role]
            process_label = f"{config.PROCESS_LABEL_PREFIX} {node_id}"
            command = " ".join(
                [
                    "exec",
                    "-a",
                    shlex.quote(process_label),
                    shlex.quote(sys.executable),
                    shlex.quote(str(main_path)),
                    "--role",
                    shlex.quote(role),
                    "--controller-host",
                    shlex.quote(self.controller_host),
                    "--controller-port",
                    shlex.quote(str(self.controller_port)),
                ]
            )
            if self.control_token:
                child_env = dict(os.environ)
                child_env["NW_CONTROL_TOKEN"] = self.control_token
            else:
                child_env = None
            process = await asyncio.create_subprocess_exec(
                "bash",
                "-lc",
                command,
                env=child_env,
            )
            self.processes.append(process)
            await asyncio.sleep(config.SUPERVISOR_START_SPACING_SECONDS)

    async def stop(self) -> None:
        for process in reversed(self.processes):
            if process.returncode is None:
                process.terminate()
        for process in reversed(self.processes):
            if process.returncode is None:
                await process.wait()


def build_role(
    role: str,
    listen_host: str,
    listen_port: int,
    controller_host: str,
    controller_port: int,
    control_token: str | None,
):
    if role == "host":
        return HostSimulator(listen_host, listen_port, controller_host, controller_port, control_token)
    if role == "agent":
        host_host, host_port = config.NODE_ENDPOINTS["host-simulator"]
        downstream_host, downstream_port = config.NODE_ENDPOINTS["r1"]
        backup_downstream_host, backup_downstream_port = config.NODE_ENDPOINTS["r1b"]
        return LocalAgent(
            listen_host,
            listen_port,
            controller_host,
            controller_port,
            host_host,
            host_port,
            downstream_host,
            downstream_port,
            control_token,
            backup_downstream_host=backup_downstream_host,
            backup_downstream_port=backup_downstream_port,
        )
    if role == "relay-r1":
        downstream_host, downstream_port = config.NODE_ENDPOINTS["r2"]
        return RelayNode("r1", listen_host, listen_port, controller_host, controller_port, downstream_host, downstream_port, control_token)
    if role == "relay-r2":
        downstream_host, downstream_port = config.NODE_ENDPOINTS["monitor"]
        return RelayNode("r2", listen_host, listen_port, controller_host, controller_port, downstream_host, downstream_port, control_token)
    if role == "relay-r1b":
        downstream_host, downstream_port = config.NODE_ENDPOINTS["r2b"]
        return RelayNode("r1b", listen_host, listen_port, controller_host, controller_port, downstream_host, downstream_port, control_token)
    if role == "relay-r2b":
        downstream_host, downstream_port = config.NODE_ENDPOINTS["monitor"]
        return RelayNode("r2b", listen_host, listen_port, controller_host, controller_port, downstream_host, downstream_port, control_token)
    if role == "monitor":
        return Monitor(listen_host, listen_port, controller_host, controller_port, control_token)
    raise ValueError(f"unsupported role: {role}")


async def run_role(
    role: str,
    listen_host: str,
    listen_port: int,
    controller_host: str,
    controller_port: int,
    control_token: str | None,
) -> None:
    node = build_role(role, listen_host, listen_port, controller_host, controller_port, control_token)
    await node.start()
    try:
        await node.wait_until_stopped()
    finally:
        await node.stop()


async def run_demo(
    duration: float | None,
    scripted_demo: bool,
    control_host: str,
    control_port: int,
    control_token: str | None,
    public_external_control: bool,
) -> None:
    supervisor = LocalProcessSupervisor(control_host, control_port, control_token)
    controller = ControllerUI(
        control_host=control_host,
        control_port=control_port,
        node_endpoints=config.NODE_ENDPOINTS,
        control_token=control_token,
        public_external_control=public_external_control,
    )
    await controller.run(duration=duration, scripted_demo=scripted_demo, startup=supervisor.start, shutdown=supervisor.stop)


async def run_controller_ui(
    duration: float | None,
    scripted_demo: bool,
    control_host: str,
    control_port: int,
    control_token: str | None,
    focus_node: str | None = None,
) -> None:
    controller = ControllerUI(
        control_host=control_host,
        control_port=control_port,
        node_endpoints=config.NODE_ENDPOINTS,
        control_token=control_token,
        public_external_control=True,
        focus_node=focus_node,
    )
    await controller.run(duration=duration, scripted_demo=scripted_demo)
