# Ephemeral Environments Setup

Each repo that participates in an ssl-agents workflow can expose a preview environment per PR branch. The orchestrator agent uses the **GitHub Deployments API** to discover those URLs and post them back to Slack.

## How it works

1. Your CI/CD pipeline deploys a preview environment when a PR branch is pushed.
2. It records that deployment in the GitHub Deployments API with the live URL.
3. The agent polls `GET /repos/{owner}/{repo}/deployments?ref={branch}` after PRs are opened, waits for a `success` status, and extracts `environment_url`.
4. The agent posts all environment URLs to the Slack thread, grouped by role (backend first, then frontend).

## Branch name coordination

The orchestrator uses **one branch name across all repos in a feature**. This is intentional: if your preview infrastructure routes traffic based on branch name (e.g. the FE env is configured to call `api-{branch}.preview.example.com`), the shared branch name is what makes cross-service preview environments work.

Your `apps.yaml` entry must declare `deploy_order` and `role` for each repo so the agent knows which service is which and what order to deploy in. See [apps.yaml reference](../AGENTS.md).

## Adding deployment reporting to a repo's workflow

Add the following steps to your existing CI/CD workflow file (e.g. `.github/workflows/preview.yml`). Insert them around your deploy step:

```yaml
jobs:
  preview:
    runs-on: ubuntu-latest
    # Only run on PRs
    if: github.event_name == 'pull_request'

    steps:
      - uses: actions/checkout@v4

      # --- Create the GitHub Deployment record before deploying ---
      - name: Create GitHub Deployment
        id: create_deployment
        uses: actions/github-script@v7
        with:
          script: |
            const { data } = await github.rest.repos.createDeployment({
              owner: context.repo.owner,
              repo: context.repo.repo,
              ref: context.payload.pull_request.head.ref,
              environment: 'preview',
              auto_merge: false,
              required_contexts: [],
              description: 'Preview deployment'
            });
            core.setOutput('deployment_id', data.id);

      # --- Your existing deploy step goes here ---
      # - name: Deploy to preview
      #   run: ./deploy.sh
      #   env:
      #     BRANCH: ${{ github.head_ref }}

      # --- Mark deployment successful and record the URL ---
      - name: Update Deployment Status (success)
        if: success()
        uses: actions/github-script@v7
        with:
          script: |
            await github.rest.repos.createDeploymentStatus({
              owner: context.repo.owner,
              repo: context.repo.repo,
              deployment_id: '${{ steps.create_deployment.outputs.deployment_id }}',
              state: 'success',
              // Replace with your actual preview URL pattern
              environment_url: `https://${{ github.head_ref }}.preview.example.com`,
              description: 'Preview ready'
            });

      # --- Mark deployment failed if something went wrong ---
      - name: Update Deployment Status (failure)
        if: failure()
        uses: actions/github-script@v7
        with:
          script: |
            await github.rest.repos.createDeploymentStatus({
              owner: context.repo.owner,
              repo: context.repo.repo,
              deployment_id: '${{ steps.create_deployment.outputs.deployment_id }}',
              state: 'failure',
              description: 'Preview deployment failed'
            });
```

### Notes

- **`environment_url` pattern**: Use the branch name as part of the URL so that related services (BE and FE on the same branch) can find each other. Common patterns:
  - `https://{branch}.api.preview.example.com`
  - `https://{branch}.app.preview.example.com`
- **`required_contexts: []`**: Disables GitHub's default requirement that all status checks pass before a deployment is created. Remove this if your pipeline already enforces that.
- **`auto_merge: false`**: Prevents GitHub from trying to auto-merge the branch before deploying.

## How the agent polls for URLs

After creating all PRs, the orchestrator:

1. Waits a configurable delay (default: 60s) for CI to start.
2. Polls each repo's deployments API for the branch ref, up to a configurable timeout (default: 15 min).
3. Checks the latest deployment status for `state: success` and extracts `environment_url`.
4. Posts all ready URLs to the Slack thread in deploy order once all repos have reported in.

If a deployment times out or fails, the agent posts a warning to Slack and continues — the human can still review code even without a live preview.
