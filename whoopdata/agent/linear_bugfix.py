from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any

import httpx
from langchain_core.tools import tool

LINEAR_GRAPHQL_URL = "https://api.linear.app/graphql"

# Hard scope: ONLY create issues in this team + project.
LINEAR_TEAM_ID = "ca1391c6-183a-4b0d-82f9-3a18774088d3"  # Agent-aware
LINEAR_PROJECT_ID = "be07eb42-745f-4418-9582-2398609dca73"  # Bug Fixes


@dataclass
class BugReportPayload:
    reported_at_iso: str
    reporter: str
    summary: str
    expected: str | None = None
    actual: str | None = None
    steps_to_reproduce: str | None = None
    frequency: str | None = None
    severity: str | None = None
    notes: str | None = None
    screenshot_caption: str | None = None
    screenshot_b64: str | None = None


def build_linear_bugfix_markdown(report: BugReportPayload) -> tuple[str, str]:
    """Return (title, description_markdown) for a Linear bug fix issue."""
    title = report.summary.strip()
    if len(title) > 120:
        title = title[:117].rstrip() + "…"

    def _bullet(label: str, value: str | None) -> str:
        if not value:
            return f"- {label}: (unknown)"
        return f"- {label}: {value.strip()}"

    parts: list[str] = []
    parts.append("## Summary")
    parts.append(report.summary.strip() or "(missing)")

    parts.append("\n## Expected vs actual")
    parts.append(_bullet("Expected", report.expected))
    parts.append(_bullet("Actual", report.actual))

    parts.append("\n## Steps to reproduce")
    parts.append(report.steps_to_reproduce.strip() if report.steps_to_reproduce else "(not provided)")

    parts.append("\n## Frequency / severity")
    parts.append(_bullet("Frequency", report.frequency))
    parts.append(_bullet("Severity", report.severity))

    parts.append("\n## Reporter / timestamp")
    parts.append(_bullet("Reporter", report.reporter))
    parts.append(_bullet("Reported at", report.reported_at_iso))

    if report.notes:
        parts.append("\n## Notes")
        parts.append(report.notes.strip())

    if report.screenshot_b64:
        # Linear does not accept arbitrary binary uploads here; keep a placeholder.
        parts.append("\n## Attachment")
        parts.append(
            "A screenshot was provided via Telegram (base64 not embedded here). "
            "If needed, ask the reporter to re-share it in Linear or provide a public link."
        )
        if report.screenshot_caption:
            parts.append(f"Caption: {report.screenshot_caption}")

    parts.append("\n## Definition of done")
    parts.append("- Correct the output so it matches expected behavior.\n- Add/adjust a test to prevent regression.")

    description = "\n".join(parts).strip() + "\n"
    return title, description


async def _linear_graphql(query: str, variables: dict[str, Any]) -> dict[str, Any]:
    api_key = os.getenv("LINEAR_API_KEY")
    if not api_key:
        raise RuntimeError("LINEAR_API_KEY is required")

    headers = {
        "Authorization": api_key if api_key.lower().startswith("bearer ") else f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {"query": query, "variables": variables}

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(LINEAR_GRAPHQL_URL, headers=headers, json=payload)
        resp.raise_for_status()
        data = resp.json()

    if "errors" in data and data["errors"]:
        raise RuntimeError(f"Linear GraphQL error: {json.dumps(data['errors'])}")

    return data.get("data") or {}


@tool(
    "create_bugfix_linear_issue",
    description=(
        "Create a Linear issue in the hard-coded 'Bug Fixes' project. "
        "Do not use this tool for any other project."
    ),
)
async def create_bugfix_linear_issue_tool(
    title: str,
    description: str,
    priority: int = 3,
) -> str:
    """Create the Linear issue (returns the issue URL)."""

    mutation = """
    mutation IssueCreate($input: IssueCreateInput!) {
      issueCreate(input: $input) {
        success
        issue {
          id
          identifier
          url
        }
      }
    }
    """

    # Hard-scope enforcement: ignore any caller-provided team/project.
    variables = {
        "input": {
            "teamId": LINEAR_TEAM_ID,
            "projectId": LINEAR_PROJECT_ID,
            "title": title,
            "description": description,
            "priority": priority,
        }
    }

    data = await _linear_graphql(mutation, variables)
    result = (data.get("issueCreate") or {}).get("issue") or {}
    url = result.get("url")
    if not url:
        raise RuntimeError("Linear issueCreate succeeded but returned no URL")
    return url


async def create_bugfix_issue_from_report(report: BugReportPayload) -> str:
    """High-level helper: build title/description from BugReportPayload and create the issue."""
    title, description = build_linear_bugfix_markdown(report)
    return await create_bugfix_linear_issue_tool.ainvoke(
        {"title": title, "description": description, "priority": 3}
    )
