# ssl-agents

AI-driven coding workflows for the [Silver Shamrock Labs](https://github.com/silver-shamrock-labs) GitHub org. @mention a Slack bot from your phone, get GitHub issues, pull requests, and preview environment URLs posted back to the thread — automatically.

## How it works

```
You: @ssl-agents add a dark mode toggle to my-app

Bot: On it! Starting work on my-app...

Routine: Issues created:
         • api: github.com/silver-shamrock-labs/my-app-api/issues/42
         • web: github.com/silver-shamrock-labs/my-app-web/issues/31

Routine: PRs ready for review:
         • api: github.com/silver-shamrock-labs/my-app-api/pull/17
         • web: github.com/silver-shamrock-labs/my-app-web/pull/8

Routine: Preview environments ready:
         • api: https://feature-dark-mode.api.preview.example.com
         • web: https://feature-dark-mode.app.preview.example.com
```

Leave a review comment on any PR — the routine picks it up and pushes a fix automatically. When you're happy, merge directly in GitHub.

## Architecture

A Slack Bolt app runs on AWS Lambda. When you @mention the bot in a per-application Slack channel, Lambda fires a [Claude Routine](https://code.claude.com/docs/en/routines) via API. The routine runs on Anthropic-managed cloud infrastructure, handles all the GitHub work, and posts updates back to your Slack thread via a connector.

```
Slack @mention
  └─► Lambda (AWS)
        ├─► Look up app in apps.yaml
        └─► Fire CODING routine (Claude)

CODING routine
  ├─► Create GH issues → post to Slack
  ├─► Write code, open PRs → post to Slack
  ├─► Poll GitHub Deployments API → post preview URLs to Slack
  └─► Auto-fix review comments and CI failures
```

## Setup

### Prerequisites

- AWS account with CLI access
- Terraform >= 1.6
- Python 3.12
- A [claude.ai](https://claude.ai) Pro, Max, Team, or Enterprise plan with Claude Code enabled
- A Slack workspace where you can create apps

### 1. Create the Slack app

1. Go to [api.slack.com/apps](https://api.slack.com/apps) and create a new app
2. Under **OAuth & Permissions**, add these bot token scopes:
   - `app_mentions:read`
   - `chat:write`
   - `channels:history`
3. Install the app to your workspace and copy the **Bot Token** (`xoxb-...`)
4. Under **Basic Information**, copy the **Signing Secret**
5. Enable **Event Subscriptions** — you'll add the Request URL after deploying

### 2. Create the CODING routine

1. Go to [claude.ai/code/routines](https://claude.ai/code/routines) and click **New routine**
2. Name it something like `ssl-agents coding`
3. Paste the prompt from [`docs/routine-prompts.md`](docs/routine-prompts.md)
4. Add all Silver Shamrock Labs repos; enable **Allow unrestricted branch pushes** for each
5. Add your **Slack connector** under Connectors
6. Under **Behaviors**, enable **Auto-fix pull requests**
7. Under **Select a trigger**, add an **API** trigger; copy the URL and click **Generate token**
8. Note the trigger ID (from the URL, prefixed `trig_`) and the token

### 3. Configure `apps.yaml`

Edit [`apps.yaml`](apps.yaml) to map each Slack channel to its repos:

```yaml
apps:
  my-app:
    slack_channel: C1234567890   # Right-click the channel in Slack → Copy link → last segment
    repos:
      - name: silver-shamrock-labs/my-app-api
        role: backend
        deploy_order: 1
      - name: silver-shamrock-labs/my-app-web
        role: frontend
        deploy_order: 2
```

`deploy_order` controls the order preview environment URLs are reported. Use `1` for backend, `2` for frontend.

### 4. Deploy

```bash
# Build the Lambda zip
make build

# Create terraform.tfvars
cat > terraform/terraform.tfvars <<EOF
slack_bot_token            = "xoxb-..."
slack_signing_secret       = "..."
coding_routine_trigger_id  = "trig_01..."
coding_routine_token       = "sk-ant-oat01-..."
EOF

# Deploy
cd terraform
terraform init
terraform apply
```

Terraform outputs the `slack_events_url`. Paste it into your Slack app under **Event Subscriptions > Request URL**, then subscribe to the `app_mention` bot event.

### 5. Invite the bot

Invite `@ssl-agents` (or whatever you named your Slack app) to each per-application channel listed in `apps.yaml`.

## Adding a new application

1. Add an entry to `apps.yaml` with the Slack channel ID and repo list
2. Run `make build && cd terraform && terraform apply` to redeploy the Lambda with the updated registry
3. Add the new repos to the CODING routine in claude.ai
4. Invite the bot to the new channel

## Ephemeral environments

Repos that support preview environments need to report their deployment URL via the GitHub Deployments API. See [`docs/ephemeral-environments.md`](docs/ephemeral-environments.md) for the GitHub Actions steps to add to a repo's workflow.

## Repo structure

```
ssl-agents/
├── slack/                      # Slack Bolt Lambda handler
│   ├── app.py                  # app_mention handler
│   └── routine.py              # Routine API client
├── terraform/                  # AWS infrastructure
│   ├── main.tf
│   ├── variables.tf
│   └── lambda.tf               # Lambda + IAM + API Gateway
├── docs/
│   ├── routine-prompts.md      # Prompt for the CODING routine
│   └── ephemeral-environments.md
├── apps.yaml                   # App → channel → repo registry
├── Makefile                    # make build → dist/lambda.zip
└── requirements.txt
```
