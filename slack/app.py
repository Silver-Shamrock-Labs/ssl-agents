import logging
import os

import yaml
from slack_bolt import App, BoltResponse
from slack_bolt.adapter.aws_lambda import SlackRequestHandler

from slack.routine import fire_coding_routine

logger = logging.getLogger(__name__)


def _cw_encode(s: str) -> str:
    return s.replace("$", "$2524").replace("/", "$252F").replace("[", "$255B").replace("]", "$255D")


def _cloudwatch_url() -> str:
    region = os.environ.get("AWS_REGION", "us-east-1")
    log_group = _cw_encode(os.environ.get("AWS_LAMBDA_LOG_GROUP_NAME", ""))
    log_stream = _cw_encode(os.environ.get("AWS_LAMBDA_LOG_STREAM_NAME", ""))
    base = f"https://{region}.console.aws.amazon.com/cloudwatch/home?region={region}"
    return f"{base}#logsV2:log-groups/log-group/{log_group}/log-events/{log_stream}"

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


@app.middleware
def ignore_retries(req, next):
    if req.headers.get("x-slack-retry-num"):
        return BoltResponse(status=200, body="")
    return next()


@app.event("app_mention")
def handle_mention(event, say, client):
    channel = event["channel"]
    thread_ts = event.get("thread_ts", event["ts"])
    text = event["text"]

    if channel not in _CHANNEL_TO_APP:
        say(text="I'm not configured for this channel.", thread_ts=thread_ts)
        return

    app_name, app_config = _CHANNEL_TO_APP[channel]
    repos = app_config["repos"]

    thread_history = None
    if event.get("thread_ts") and event["thread_ts"] != event["ts"]:
        result = client.conversations_replies(channel=channel, ts=event["thread_ts"])
        thread_history = result.get("messages", [])

    friendly_name = app_config.get("friendly_name", app_name)
    say(text=f"On it! Starting work on *{friendly_name}*", thread_ts=thread_ts)

    try:
        fire_coding_routine(
            feature_request=text,
            app_name=app_name,
            repos=repos,
            slack_channel=channel,
            slack_thread_ts=thread_ts,
            thread_history=thread_history,
        )
    except Exception:
        logger.exception("Failed to fire coding routine")
        say(
            text=f"Something went wrong starting the routine. <{_cloudwatch_url()}|View logs>",
            thread_ts=thread_ts,
        )


slack_handler = SlackRequestHandler(app=app)


def handler(event, context):
    return slack_handler.handle(event, context)
