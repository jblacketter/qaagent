from __future__ import annotations

import asyncio
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict

import pytest


pytest.importorskip("mcp.server.fastmcp")


async def _start_mcp(project_root: Path) -> asyncio.subprocess.Process:
    env = os.environ.copy()
    env.setdefault("PYTHONPATH", str(project_root))
    return await asyncio.create_subprocess_exec(
        "qaagent-mcp",
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        cwd=project_root,
        env=env,
    )


async def _read_message(proc: asyncio.subprocess.Process, timeout: float = 5.0) -> Dict[str, Any]:
    assert proc.stdout is not None
    line = await asyncio.wait_for(proc.stdout.readline(), timeout=timeout)
    text = line.decode().strip()
    if not text:
        return {}
    return json.loads(text)


async def _write_message(proc: asyncio.subprocess.Process, payload: Dict[str, Any]) -> None:
    assert proc.stdin is not None
    message = json.dumps(payload) + "\n"
    proc.stdin.write(message.encode())
    await proc.stdin.drain()


async def _initialize(proc: asyncio.subprocess.Process) -> Dict[str, Any]:
    await _write_message(
        proc,
        {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {"protocolVersion": "1.0"},
        },
    )
    return await _read_message(proc)


async def _shutdown(proc: asyncio.subprocess.Process) -> None:
    if proc.stdin:
        try:
            proc.stdin.close()
        except Exception:
            pass
    try:
        await asyncio.wait_for(proc.wait(), timeout=1.0)
    except asyncio.TimeoutError:
        proc.terminate()
        try:
            await asyncio.wait_for(proc.wait(), timeout=1.0)
        except asyncio.TimeoutError:
            proc.kill()


@pytest.mark.asyncio
async def test_mcp_server_initializes(project_root: Path) -> None:
    proc = await _start_mcp(project_root)
    try:
        response = await _initialize(proc)
        assert response.get("jsonrpc") == "2.0"
        assert "result" in response
    finally:
        await _shutdown(proc)


@pytest.mark.asyncio
async def test_mcp_detect_openapi_tool(project_root: Path, petstore_server: str) -> None:
    proc = await _start_mcp(project_root)
    try:
        init_response = await _initialize(proc)
        assert init_response.get("jsonrpc") == "2.0"

        await _write_message(
            proc,
            {
                "jsonrpc": "2.0",
                "id": 2,
                "method": "tools/list",
                "params": {},
            },
        )
        tools_response = await _read_message(proc)
        tools = tools_response.get("result", {}).get("tools", [])
        names = {tool.get("name") for tool in tools}
        assert {"detect_openapi", "discover_routes", "assess_risks"}.issubset(names)

        await _write_message(
            proc,
            {
                "jsonrpc": "2.0",
                "id": 3,
                "method": "tools/call",
                "params": {
                    "name": "detect_openapi",
                    "arguments": {"path": "examples/petstore-api", "base_url": petstore_server, "probe": True},
                },
            },
        )
        call_response = await _read_message(proc)
        assert "result" in call_response
        result = call_response["result"]
        assert isinstance(result.get("files"), list)

        # Discover routes via MCP
        await _write_message(
            proc,
            {
                "jsonrpc": "2.0",
                "id": 4,
                "method": "tools/call",
                "params": {
                    "name": "discover_routes",
                    "arguments": {"openapi": "examples/petstore-api/openapi.yaml"},
                },
            },
        )
        routes_response = await _read_message(proc)
        routes_payload = routes_response.get("result", {})
        assert isinstance(routes_payload.get("routes"), list)

        # Assess risks directly from OpenAPI
        await _write_message(
            proc,
            {
                "jsonrpc": "2.0",
                "id": 5,
                "method": "tools/call",
                "params": {
                    "name": "assess_risks",
                    "arguments": {"openapi": "examples/petstore-api/openapi.yaml"},
                },
            },
        )
        risks_response = await _read_message(proc)
        risks_payload = risks_response.get("result", {})
        assert isinstance(risks_payload.get("risks"), list)
    finally:
        await _shutdown(proc)
