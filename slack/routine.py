import os

import requests

_API_BASE = "https://api.anthropic.com/v1/claude_code/routines"
_BETA_HEADER = "experimental-cc-routine-2026-04-01"


def fire_coding_routine(
    feature_request: str,
    app_name: str,
    repos: list[dict],
    slack_channel: str,
    slack_thread_ts: str,
) -> tuple[str, str]:
    repo_lines = "\n".join(
        f"  - {r['name']} (role: {r['role']}, deploy_order: {r['deploy_order']})"
        for r in repos
    )
    text = (
        f"Feature request: {feature_request}\n\n"
        f"App: {app_name}\n"
        f"Slack channel: {slack_channel}\n"
        f"Slack thread: {slack_thread_ts}\n"
        f"Repos:\n{repo_lines}"
    )
    resp = requests.post(
        f"{_API_BASE}/{os.environ['CODING_ROUTINE_TRIGGER_ID']}/fire",
        headers={
            "Authorization": f"Bearer {os.environ['CODING_ROUTINE_TOKEN']}",
            "anthropic-beta": _BETA_HEADER,
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json",
        },
        json={"text": text},
        timeout=10,
    )
    resp.raise_for_status()
    data = resp.json()
    return data["claude_code_session_id"], data["claude_code_session_url"]
