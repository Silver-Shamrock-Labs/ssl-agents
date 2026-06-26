# ssl-agents

Agentic workflows for the [Silver Shamrock Labs](https://github.com/silver-shamrock-labs) GitHub org.

## Overview

Applications at Silver Shamrock Labs often span multiple repositories. This system provides AI-driven workflows that can plan and execute changes across all repos in an application in response to a natural-language feature request from Slack.

## Architecture

### Components

**Slack App** (`slack/`)
- Built with [Slack Bolt for Python](https://slack.dev/bolt-python/), deployed as an AWS Lambda function
- Receives @mention in a per-application Slack channel → fires the CODING routine
- Detects merge signals in thread (natural language or emoji reaction) → fires the MERGE routine
- Stores run context in DynamoDB so merge signals can be routed to the right routine

**Claude Routines** (configured at [claude.ai/code/routines](https://claude.ai/code/routines))
- One routine with a Slack connector and GitHub access to all org repos
- Runs on Anthropic-managed cloud infrastructure — no agent loop to maintain
- **CODING routine**: receives the feature request via API trigger; plans changes, creates GH issues, creates branches, writes code, opens PRs, posts updates to Slack; Auto-fix behavior watches for review comments and CI failures and pushes follow-up commits automatically

**App Registry** (`apps.yaml`)
- Maps Slack channel IDs to applications and their constituent repos
- Bundled with the Lambda — loaded at cold start
- Maintained manually as new apps and repos are added

**Infrastructure** (`terraform/`)
- Lambda function + execution role
- API Gateway (HTTP API) fronting the Lambda

### Trigger Flow

```
Slack @mention (feature request)
  └─► Lambda receives event
        ├─► Look up channel ID in apps.yaml → resolve app + repos
        ├─► Fire CODING routine via API
        └─► Reply "On it!" to Slack thread

CODING Routine (Anthropic-managed cloud session)
  ├─► Creates GH issues in each repo → posts links to Slack
  ├─► Creates shared branch, writes code changes across repos
  ├─► Opens PRs → posts links to Slack
  ├─► Detects preview deployment URLs (GitHub Deployments API) → posts to Slack
  └─► Auto-fix: watches CI results and review comments, pushes follow-up commits

Human reviews PRs in GitHub and merges directly when satisfied.
```

## Tech Stack

| Layer | Choice |
|---|---|
| Language | Python |
| Slack integration | Slack Bolt for Python (Lambda adapter) |
| Agent surface | Claude Routines (claude.ai) |
| Infrastructure | Terraform + AWS (Lambda, API Gateway) |

## Routines Setup

Create and manage the routine at [claude.ai/code/routines](https://claude.ai/code/routines).

### CODING routine

- **Trigger**: API (copy the trigger ID and token into Lambda env vars as `CODING_ROUTINE_TRIGGER_ID` / `CODING_ROUTINE_TOKEN`)
- **Repositories**: all Silver Shamrock Labs repos the routine should be able to touch; enable **Allow unrestricted branch pushes**
- **Connectors**: Slack (for posting updates), GitHub (native)
- **Behaviors**: enable **Auto-fix pull requests**
- **Prompt**: see `docs/routine-prompts.md`

## `apps.yaml` Schema

Each application entry declares its Slack channel and its repos in deployment order:

```yaml
apps:
  my-app:
    slack_channel: C1234567890   # Slack channel ID
    repos:
      - name: silver-shamrock-labs/my-app-api
        role: backend
        deploy_order: 1
      - name: silver-shamrock-labs/my-app-web
        role: frontend
        deploy_order: 2
```

## Workflow Stages

```
1. PENDING        — @mention received in Slack channel
2. PLANNING       — Routine determines affected repos, picks shared branch name
3. ISSUES_CREATED — GH issues created per repo; links posted to Slack
4. CODING         — Routine reads code, writes changes across repos
5. PRS_OPEN       — PRs created (same branch name in every repo); links posted to Slack
6. DEPLOYING      — Routine polls GitHub Deployments API; preview URLs posted to Slack
7. IN_REVIEW      — Waiting for PR comments; Auto-fix addresses feedback automatically
8. COMPLETE       — Human reviews and merges PRs directly in GitHub
```

## Branch Naming

The CODING routine picks **one branch name for the entire feature** and uses it across every repo. This is required so ephemeral environments can communicate across services (e.g. the FE preview is configured to call `api-{branch}.preview.example.com`).

## Ephemeral Environments

Repos that support preview environments must report their deployment URL via the **GitHub Deployments API**. The CODING routine polls for `state: success` on the branch's latest deployment and posts the URL to Slack.

See [docs/ephemeral-environments.md](docs/ephemeral-environments.md) for the GitHub Actions steps to add to a repo's workflow.

## Repo Structure

```
ssl-agents/
├── slack/          # Slack Bolt Lambda handler
│   ├── app.py      # Entry point + app_mention handler
│   └── routine.py  # Routine API client
├── terraform/      # AWS infrastructure
│   ├── main.tf
│   ├── variables.tf
│   └── lambda.tf
├── docs/           # Setup guides
├── apps.yaml       # Application → repo registry
├── Makefile        # Build Lambda zip (make build)
└── requirements.txt
```

## Lambda Environment Variables

| Variable | Description |
|---|---|
| `SLACK_BOT_TOKEN` | Slack bot OAuth token (`xoxb-...`) |
| `SLACK_SIGNING_SECRET` | Slack app signing secret |
| `CODING_ROUTINE_TRIGGER_ID` | Trigger ID from the CODING routine's API trigger |
| `CODING_ROUTINE_TOKEN` | Bearer token for the CODING routine |
