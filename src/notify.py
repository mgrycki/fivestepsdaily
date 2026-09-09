"""Post-publish ping to phone or Slack. Fail-soft: a dead notifier never fails a run."""
import sys

import requests

from . import config


def send(title: str, text: str) -> None:
    slack = config.opt("SLACK_WEBHOOK_URL")
    ntfy = config.opt("NTFY_TOPIC")
    try:
        if slack:
            requests.post(slack, json={"text": f"*{title}*\n{text}"}, timeout=15)
        elif ntfy:
            requests.post(f"https://ntfy.sh/{ntfy}", data=text.encode("utf-8"),
                          headers={"Title": title[:80], "Priority": "default"}, timeout=15)
        else:
            return
        print(f"[notify] sent: {title}")
    except Exception as e:
        print(f"[notify] failed (ignored): {e}", file=sys.stderr)


def summary(kind: str, title: str, results: dict, failures: list) -> None:
    lines = [f"{kind}: {title}"]
    lines += [f"ok {net}: {pid}" for net, pid in results.items()]
    lines += [f"FAIL {f}" for f in failures]
    send(f"Publisher {kind} " + ("OK" if not failures else "with errors"), "\n".join(lines))
