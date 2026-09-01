"""Central config: everything comes from env, nothing hardcoded."""
import os
from dotenv import load_dotenv

load_dotenv()


def req(name: str) -> str:
    v = os.environ.get(name, "").strip()
    if not v:
        raise RuntimeError(f"Missing required env var: {name}")
    return v


def opt(name: str, default: str = "") -> str:
    return os.environ.get(name, default).strip()


# Anthropic
ANTHROPIC_MODEL = opt("ANTHROPIC_MODEL", "claude-sonnet-5")
WEB_SEARCH_TOOL = opt("WEB_SEARCH_TOOL", "web_search_20250305")

# Meta
GRAPH_VERSION = opt("GRAPH_API_VERSION", "v21.0")
GRAPH_BASE = f"https://graph.facebook.com/{GRAPH_VERSION}"

# Storage
S3_REGION = opt("S3_REGION", "auto")

# Which networks to publish to
TARGETS = [t.strip().lower() for t in opt("TARGETS", "facebook,instagram,x").split(",") if t.strip()]

# Paths
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
USED_TOPICS = os.path.join(ROOT, "data", "used_topics.json")
TEMPLATE = os.path.join(ROOT, "templates", "template.html")
ICONS = os.path.join(ROOT, "templates", "icons.json")
OUT_DIR = os.path.join(ROOT, "out")
