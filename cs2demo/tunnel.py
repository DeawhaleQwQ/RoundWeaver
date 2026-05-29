from __future__ import annotations

import asyncio
import re
import shutil
from asyncio.subprocess import PIPE, Process


class TunnelManager:
    def __init__(self, provider: str, command: str, local_url: str, startup_timeout: float = 25.0) -> None:
        self.provider = provider
        self.command = command
        self.local_url = local_url
        self.startup_timeout = startup_timeout
        self.process: Process | None = None
        self.public_url: str = ""
        self.output: list[str] = []
        self._reader_tasks: list[asyncio.Task] = []

    async def start(self) -> str:
        if self.provider != "cloudflared":
            raise RuntimeError(f"Unsupported tunnel provider: {self.provider}")
        if shutil.which(self.command) is None:
            raise RuntimeError("未检测到 cloudflared；请安装 cloudflared，或使用 --public-url / CS2PLUGIN_PUBLIC_BASE_URL。")

        self.process = await asyncio.create_subprocess_exec(
            self.command,
            "tunnel",
            "--url",
            self.local_url,
            stdout=PIPE,
            stderr=PIPE,
        )
        queue: asyncio.Queue[str] = asyncio.Queue()
        self._reader_tasks = [
            asyncio.create_task(self._read_stream(self.process.stdout, queue)),
            asyncio.create_task(self._read_stream(self.process.stderr, queue)),
        ]

        loop = asyncio.get_running_loop()
        deadline = loop.time() + self.startup_timeout
        while loop.time() < deadline:
            if self.process.returncode is not None:
                break
            timeout = max(0.1, min(0.5, deadline - loop.time()))
            try:
                self.public_url = await asyncio.wait_for(queue.get(), timeout=timeout)
                return self.public_url
            except asyncio.TimeoutError:
                continue

        await self.stop()
        detail = "\n".join(self.output[-8:])
        if detail:
            raise RuntimeError(f"cloudflared 未返回公网 URL：{detail}")
        raise RuntimeError("cloudflared 未返回公网 URL。")

    async def stop(self) -> None:
        for task in self._reader_tasks:
            task.cancel()
        self._reader_tasks = []
        if self.process is None:
            return
        if self.process.returncode is None:
            self.process.terminate()
            try:
                await asyncio.wait_for(self.process.wait(), timeout=5)
            except asyncio.TimeoutError:
                self.process.kill()
                await self.process.wait()
        self.process = None

    async def _read_stream(self, stream: asyncio.StreamReader | None, queue: asyncio.Queue[str]) -> None:
        if stream is None:
            return
        while True:
            line = await stream.readline()
            if not line:
                return
            text = line.decode("utf-8", errors="replace").strip()
            if text:
                self.output.append(text)
            public_url = self.parse_public_url(text)
            if public_url and not self.public_url:
                await queue.put(public_url)

    @staticmethod
    def parse_public_url(line: str) -> str | None:
        match = re.search(r"https://[^\s]+?\.trycloudflare\.com", line or "")
        if not match:
            return None
        return match.group(0).rstrip("/.,)")
