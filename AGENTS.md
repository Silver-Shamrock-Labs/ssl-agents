# ssl-agents

Agentic workflows for the [Silver Shamrock Labs](https://github.com/silver-shamrock-labs) GitHub org.

## Overview

Applications at Silver Shamrock Labs often span multiple repositories. This system provides AI-driven workflows that can plan and execute changes across all repos in an application in response to a natural-language feature request.

## Architecture

### Components

**Slack App** (`slack/`)
- Built with [Slack Bolt for Python](https://slack.dev/bolt-python/)
- Entry point for all workflow requests
- Accepts feature requests as natural-language messages
- Posts back issue links, PR links, and status updates as work progresses

**Orchestrator Agent** (`agent/`)
- Powered by the Anthropic SDK (tool use / agentic loop)
- Receives a feature request and a target application name
- Plans which repos need changes and what those changes should be
- Executes the plan: creates issues, branches, commits, and PRs
- Monitors open PRs for review comments and addresses feedback in a loop

**GitHub Tools** (`tools/github.py`)
- Thin wrappers around the GitHub API used as agent tools
- `list_app_repos` — look up repos for a given application
- `create_issue` — open a GH issue in a repo
- `create_branch` — branch off main for the work
- `read_file` / `write_file` — read and modify repo contents
- `create_pr` — open a pull request
- `get_pr_comments` — fetch review comments on an open PR
- `reply_to_pr_comment` — respond to a reviewer comment
- `commit_files` — commit a batch of file changes to a branch

**App Registry** (`apps.yaml`)
- Maps application names to their constituent GitHub repos
- Maintained manually (or eventually via tooling)
- Example:
  ```yaml
  apps:
    my-app:
      repos:
        - silver-shamrock-labs/my-app-api
        - silver-shamrock-labs/my-app-web
        - silver-shamrock-labs/my-app-infra
  ```

**State Store** (`store/`)
- SQLite database tracking the lifecycle of each workflow run
- Survives the async gap between PR creation and review completion

### Workflow Stages

```
1. PENDING        — Feature request received from Slack
2. PLANNING       — Agent analyzes request, identifies affected repos
3. ISSUES_CREATED — GH issues opened in each affected repo; links posted to Slack
4. CODING         — Agent reads code, makes changes across repos
5. PRS_OPEN       — PRs cut for each repo; links posted to Slack
6. IN_REVIEW      — Waiting for PR review comments
7. ADDRESSING     — Agent reads comments and pushes follow-up commits
8. COMPLETE       — All PRs approved and merged
```

### Trigger Flow

```
Slack message (feature request)
  └─► Slack App receives event
        └─► Orchestrator Agent starts
              ├─► Plan: which repos, what changes
              ├─► Create GH issues → post to Slack
              ├─► Make code changes → create PRs → post to Slack
              └─► Poll for PR comments → address feedback → loop
```

## Tech Stack

| Layer | Choice |
|---|---|
| Language | Python |
| Agent SDK | [Anthropic Python SDK](https://github.com/anthropics/anthropic-sdk-python) |
| Slack integration | Slack Bolt for Python |
| GitHub integration | PyGitHub / GitHub REST API |
| State persistence | SQLite (to start) |
| Infrastructure | Terraform (see `.gitignore`) |

## Open Questions

- **App registry format**: `apps.yaml` in this repo vs. GitHub repo topics vs. naming convention
- **PR comment notifications**: Polling on a schedule vs. GitHub webhook calling back to a service endpoint
- **Deployment target**: Where the Slack app and agent service will be hosted (cloud TBD)
- **Repo permissions**: GitHub token / App auth scope needed to write to all org repos

## Repo Structure (planned)

```
ssl-agents/
├── agent/          # Orchestrator agent and tool definitions
├── slack/          # Slack Bolt app
├── store/          # State store (SQLite schema, access layer)
├── tools/          # GitHub and other external tool wrappers
├── apps.yaml       # Application → repo registry
└── terraform/      # Infrastructure
```
