import logging
import os

import yaml
from slack_bolt import App
from slack_bolt.adapter.aws_lambda import SlackRequestHandler

from slack.routine import fire_coding_routine

logger = logging.getLogger(__name__)

_HERE = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(_HERE, "..", "apps.yaml")) as f:
    _REGISTRY = yaml.safe_load(f)["apps"]

_CHANNEL_TO_APP = {
    cfg["slack_channel"]: (name, cfg)
    for name, cfg in _REGISTRY.items()
}

app = App(
    token=os.environ["SLACK_BOT_TOKEN"],
    signing_secret=os.environ["SLACK_SIGNING_SECRET"],
    process_before_response=True,
)


@app.event("app_mention")
def handle_mention(event, say):
    channel = event["channel"]
    thread_ts = event.get("thread_ts", event["ts"])
    text = event["text"]

    if channel not in _CHANNEL_TO_APP:
        say(text="I'm not configured for this channel.", thread_ts=thread_ts)
        return

    app_name, app_config = _CHANNEL_TO_APP[channel]
    repos = app_config["repos"]

    say(text=f"On it! Starting work on *{app_name}*...", thread_ts=thread_ts)

    fire_coding_routine(
        feature_request=text,
        app_name=app_name,
        repos=repos,
        slack_channel=channel,
        slack_thread_ts=thread_ts,
    )


slack_handler = SlackRequestHandler(app=app)


def handler(event, context):
    return slack_handler.handle(event, context)
