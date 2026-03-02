#!/usr/bin/env python3
"""Test scheduled agent messages via the LangGraph SDK.

Starts the LangGraph dev server, waits 5 seconds, then creates a new
thread and sends a test message to it. Open Studio to see the result.

Usage: uv run python scripts/test_cron.py
"""

import asyncio
import signal
import subprocess
import httpx
from langgraph_sdk import get_client

DEPLOYMENT_URL = "http://127.0.0.1:2024"
ASSISTANT_ID = "health_agent"
SERVER_READY_TIMEOUT = 60
DELAY_SECONDS = 5  # How long to wait before firing the test message

_shutdown = asyncio.Event()


async def wait_for_server(url: str, timeout: int = SERVER_READY_TIMEOUT):
    """Poll until the LangGraph server is healthy."""
    async with httpx.AsyncClient() as http:
        for _ in range(timeout):
            try:
                r = await http.get(f"{url}/ok")
                if r.status_code == 200:
                    return True
            except httpx.ConnectError:
                pass
            await asyncio.sleep(1)
    return False


def kill_proc(proc: subprocess.Popen):
    """Terminate a subprocess and its children."""
    try:
        proc.terminate()
        proc.wait(timeout=5)
    except Exception:
        proc.kill()
        proc.wait()


async def main():
    server_proc: subprocess.Popen | None = None

    async def cleanup():
        if server_proc:
            kill_proc(server_proc)
            print("\U0001f6d1 Server stopped.")

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, _shutdown.set)

    try:
        # 1. Start LangGraph dev server
        print("\U0001f680 Starting LangGraph dev server...")
        server_proc = subprocess.Popen(
            ["uv", "run", "langgraph", "dev", "--allow-blocking", "--no-browser"],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )

        # 2. Wait for server to be ready
        print("\u23f3 Waiting for server to be ready...")
        if not await wait_for_server(DEPLOYMENT_URL):
            print("\u274c Server didn't start in time.")
            return

        print(f"\u2705 Server ready at {DEPLOYMENT_URL}")
        client = get_client(url=DEPLOYMENT_URL)

        # 3. Wait before firing
        print(f"\u23f3 Waiting {DELAY_SECONDS}s before sending test message...")
        await asyncio.sleep(DELAY_SECONDS)

        # 4. Create a new thread and send the test message
        thread = await client.threads.create()
        thread_id = thread["thread_id"]
        print(f"\U0001f4ac Created thread: {thread_id}")

        print("\U0001f4e8 Sending test message...")
        await client.runs.create(
            thread_id,
            ASSISTANT_ID,
            input={
                "messages": [
                    {
                        "role": "assistant",
                        "content": "THIS IS A TEST THIS IS WORKING",
                    }
                ]
            },
        )
        print("\u2705 Test message sent!")
        print()
        print(f"\U0001f440 Open Studio to see the thread:")
        print(f"   https://smith.langchain.com/studio/?baseUrl={DEPLOYMENT_URL}")
        print()
        print("Press Ctrl+C to stop the server.")

        # 5. Keep server alive until Ctrl+C
        await _shutdown.wait()

    except Exception as e:
        print(f"\u274c Error: {e}")
    finally:
        await cleanup()


if __name__ == "__main__":
    asyncio.run(main())
