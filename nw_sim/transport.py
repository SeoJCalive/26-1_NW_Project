from __future__ import annotations

import asyncio
from typing import Any

from .messages import decode_message, encode_message


async def write_json_line(writer: asyncio.StreamWriter, message: dict[str, Any]) -> None:
    writer.write((encode_message(message) + "\n").encode())
    await writer.drain()


async def read_json_line(reader: asyncio.StreamReader) -> dict[str, Any] | None:
    raw = await reader.readline()
    if not raw:
        return None
    return decode_message(raw.decode().strip())


async def send_request(
    host: str,
    port: int,
    message: dict[str, Any],
    *,
    expect_response: bool,
    timeout: float | None = None,
) -> dict[str, Any] | None:
    async def _send() -> dict[str, Any] | None:
        reader, writer = await asyncio.open_connection(host, port)
        try:
            await write_json_line(writer, message)
            if not expect_response:
                return None
            return await read_json_line(reader)
        finally:
            writer.close()
            await writer.wait_closed()

    if timeout is None:
        return await _send()
    return await asyncio.wait_for(_send(), timeout=timeout)
