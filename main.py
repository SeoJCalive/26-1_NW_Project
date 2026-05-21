from __future__ import annotations

import argparse
import asyncio
import ctypes
import os
import secrets
import sys

from nw_demo import config
from nw_demo.controller_client import run_controller_client
from nw_demo.system import run_controller_ui, run_demo, run_role


CONTROL_TOKEN_ENV_VAR = "NW_CONTROL_TOKEN"


def set_process_label(node_name: str) -> None:
    label = f"{config.PROCESS_LABEL_PREFIX} {node_name}"
    sys.argv[0] = label
    try:
        libc = ctypes.CDLL(None)
        pr_set_name = 15
        libc.prctl(pr_set_name, ctypes.c_char_p(label.encode()[:15]), 0, 0, 0)
    except Exception:
        pass


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Minimal network project demo")
    parser.add_argument(
        "--role",
        choices=["controller", "host", "agent", "relay-r1", "relay-r2", "monitor"],
        default=None,
        help="Run a specific long-running role process.",
    )
    parser.add_argument(
        "--duration",
        type=float,
        default=None,
        help="Stop automatically after N seconds. Defaults to 28 seconds in non-interactive mode.",
    )
    parser.add_argument(
        "--interactive",
        action="store_true",
        help="Keep viewer mode even if stdin is not a TTY.",
    )
    parser.add_argument(
        "--scripted",
        action="store_true",
        help="Force the scripted demo sequence in the viewer.",
    )
    parser.add_argument(
        "--controller",
        action="store_true",
        help="Run the separate controller terminal instead of the viewer.",
    )
    parser.add_argument(
        "--host",
        default=config.DEFAULT_HOST,
        help="Host for the viewer/controller control channel.",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=config.CONTROLLER_PORT,
        help="Port for the viewer/controller control channel.",
    )
    parser.add_argument(
        "--listen-host",
        default=config.DEFAULT_HOST,
        help="Listen host for a role process.",
    )
    parser.add_argument(
        "--listen-port",
        type=int,
        default=None,
        help="Listen port for a role process.",
    )
    parser.add_argument(
        "--controller-host",
        default=config.DEFAULT_HOST,
        help="Controller/UI host that role processes report STATUS to.",
    )
    parser.add_argument(
        "--controller-port",
        type=int,
        default=config.CONTROLLER_PORT,
        help="Controller/UI port that role processes report STATUS to.",
    )
    parser.add_argument(
        "--control-token",
        default=None,
        help="Shared control/status token for local demo processes and external controller connections.",
    )
    parser.add_argument(
        "--allow-unauthenticated-control",
        action="store_true",
        help="Allow standalone controller/node processes to accept unauthenticated control connections.",
    )
    parser.add_argument(
        "--focus-node",
        choices=["host-simulator", "local-agent", "r1", "r2", "monitor"],
        default=None,
        help="Render a focused single-node monitoring surface (controller role only).",
    )
    return parser.parse_args()


def resolve_control_token(cli_value: str | None) -> str | None:
    return cli_value or os.environ.get(CONTROL_TOKEN_ENV_VAR)


def main() -> None:
    args = parse_args()
    control_token = resolve_control_token(args.control_token)
    control_token_was_supplied = control_token is not None
    if args.controller:
        if args.focus_node is not None:
            raise SystemExit("--focus-node는 standalone controller UI(--role controller)에서만 사용할 수 있습니다.")
        if control_token is None:
            raise SystemExit(
                "외부 controller는 control token이 필요합니다. --control-token 또는 NW_CONTROL_TOKEN을 제공하세요."
            )
        asyncio.run(run_controller_client(host=args.host, port=args.port, control_token=control_token))
        return

    if args.role is not None:
        if args.role == "controller":
            set_process_label("controller")
            viewer_mode = args.interactive or sys.stdin.isatty()
            scripted_demo = args.scripted or not viewer_mode
            duration = args.duration
            if control_token is None and not args.allow_unauthenticated_control:
                raise SystemExit(
                    "Standalone controller UI는 control token이 필요합니다. --control-token, NW_CONTROL_TOKEN 또는 --allow-unauthenticated-control을 사용하세요."
                )
            if duration is None and scripted_demo:
                duration = config.SCRIPTED_DEFAULT_DURATION_SECONDS
            asyncio.run(
                run_controller_ui(
                    duration=duration,
                    scripted_demo=scripted_demo,
                    control_host=args.host,
                    control_port=args.port,
                    control_token=control_token,
                    focus_node=args.focus_node,
                )
            )
            return

        if args.focus_node is not None:
            raise SystemExit("--focus-node는 standalone controller UI(--role controller)에서만 사용할 수 있습니다.")

        node_id = config.ROLE_TO_NODE_ID[args.role]
        if control_token is None and not args.allow_unauthenticated_control:
            raise SystemExit(
                f"Standalone role '{node_id}'는 control token이 필요합니다. --control-token, NW_CONTROL_TOKEN 또는 --allow-unauthenticated-control을 사용하세요."
            )
        set_process_label(node_id)
        default_host, default_port = config.NODE_ENDPOINTS[node_id]
        asyncio.run(
            run_role(
                role=args.role,
                listen_host=args.listen_host or default_host,
                listen_port=args.listen_port or default_port,
                controller_host=args.controller_host,
                controller_port=args.controller_port,
                control_token=control_token,
            )
        )
        return

    set_process_label("viewer")
    if args.focus_node is not None:
        raise SystemExit("--focus-node는 standalone controller UI(--role controller)에서만 사용할 수 있습니다.")
    viewer_mode = args.interactive or sys.stdin.isatty()
    scripted_demo = args.scripted or not viewer_mode
    duration = args.duration
    if control_token is None:
        control_token = secrets.token_urlsafe(12)
    if duration is None and scripted_demo:
        duration = config.SCRIPTED_DEFAULT_DURATION_SECONDS
    asyncio.run(
        run_demo(
            duration=duration,
            scripted_demo=scripted_demo,
            control_host=args.host,
            control_port=args.port,
            control_token=control_token,
            public_external_control=control_token_was_supplied,
        )
    )


if __name__ == "__main__":
    main()
