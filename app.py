from __future__ import annotations

import base64
import hashlib
import hmac
import html
import json
import os
import secrets
import shutil
import subprocess
import threading
import time
import urllib.error
import urllib.request
import zipfile
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from functools import wraps
from pathlib import Path
from typing import Any
from urllib.parse import quote

from flask import (
    Flask,
    Response,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    send_from_directory,
    session,
    url_for,
)
from flask_socketio import SocketIO, emit
from werkzeug.middleware.proxy_fix import ProxyFix
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename


APP_ROOT = Path(__file__).resolve().parent
DATA_DIR = APP_ROOT / "data"
UPLOADS_DIR = APP_ROOT / "uploads"
STATIC_DIR = APP_ROOT / "static"
TEMPLATES_DIR = APP_ROOT / "templates"
TOOLS_DIR = APP_ROOT / "tools"

USERS_FILE = DATA_DIR / "users.json"
VIDEOS_FILE = DATA_DIR / "videos.json"
GAMES_FILE = DATA_DIR / "games.json"
PASTES_FILE = DATA_DIR / "pastes.json"
WIKI_FILE = DATA_DIR / "wiki.json"
FORUMS_FILE = DATA_DIR / "forums.json"
CHAT_FILE = DATA_DIR / "chat.json"
NOTIFICATIONS_FILE = DATA_DIR / "notifications.json"
MUSIC_FILE = DATA_DIR / "music.json"
DOWNLOADS_FILE = DATA_DIR / "downloads.json"
LIBRARY_FILE = DATA_DIR / "library.json"
SECRET_FILE = DATA_DIR / "secret_key.txt"
ADMINS_FILE = DATA_DIR / "admins.txt"

VIDEO_DIR = UPLOADS_DIR / "videos"
THUMBS_DIR = UPLOADS_DIR / "thumbs"
IMAGES_DIR = UPLOADS_DIR / "images"
COVERS_DIR = UPLOADS_DIR / "covers"
GAMES_DIR = UPLOADS_DIR / "games"
MUSIC_DIR = UPLOADS_DIR / "music"
PFP_DIR = UPLOADS_DIR / "pfps"
BANNER_DIR = UPLOADS_DIR / "banners"
ZIM_DIR = UPLOADS_DIR / "zim"

ALLOWED_VIDEO_EXTS = {".mp4", ".webm", ".ogv", ".mov", ".m4v"}
ALLOWED_IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".gif", ".webp"}
ALLOWED_GAME_EXTS = {".zip", ".html", ".htm"}
ALLOWED_AUDIO_EXTS = {".mp3", ".m4a", ".aac", ".wav", ".ogg", ".oga", ".flac", ".opus", ".webm"}
KIWIX_PORT = int(os.environ.get("LOCALNET_KIWIX_PORT", "2462"))
KIWIX_ROOT = "/offlinewiki"


def detect_kiwix_bin() -> str | None:
    env_path = os.environ.get("LOCALNET_KIWIX_BIN")
    if env_path and Path(env_path).exists():
        return env_path
    shell_path = shutil.which("kiwix-serve")
    if shell_path:
        return shell_path
    candidates = [
        TOOLS_DIR / "kiwix-tools" / "kiwix-serve",
        Path("/Applications/Kiwix.app/Contents/MacOS/kiwix-serve"),
        Path.home() / "Applications/Kiwix.app/Contents/MacOS/kiwix-serve",
    ]
    for candidate in candidates:
        if candidate.exists():
            return str(candidate)
    for candidate in sorted(TOOLS_DIR.glob("kiwix-tools*/kiwix-serve")):
        if candidate.exists():
            return str(candidate)
    return None


FORUM_SECTIONS = [
    {"slug": "general", "name": "General", "desc": "Everything local and everything else."},
    {"slug": "showcase", "name": "Showcase", "desc": "Share projects, builds, and experiments."},
    {"slug": "help", "name": "Help Desk", "desc": "Ask questions and help each other troubleshoot."},
    {"slug": "games", "name": "Games Club", "desc": "Talk about uploads, scores, and what to play next."},
]
FORUM_LOOKUP = {forum["slug"]: forum for forum in FORUM_SECTIONS}
WIKI_PACKS = {
    "spark": {
        "name": "Starter Seed",
        "desc": "A small starter wiki with compact offline pages.",
        "mode": "compact",
        "topics": [
            ("LocalNet", "LocalNet is a self-hosted local internet hub for media, forums, chat, and offline knowledge."),
            ("Intranet", "An intranet is a private network that brings communication, files, and shared tools into one place."),
            ("Wikipedia", "Wikipedia is a collaborative encyclopedia that organizes articles by topic, history, and references."),
            ("Web Browser", "A web browser opens pages, plays media, and connects people to web apps like LocalNet."),
            ("Computer", "A computer processes information, stores files, and runs software for local and online tasks."),
            ("Network", "A network links devices together so they can share data, messages, and services."),
        ],
    },
    "base": {
        "name": "Core Seed",
        "desc": "A balanced offline wiki with more context on each page.",
        "mode": "balanced",
        "topics": [
            ("LocalNet", "LocalNet is a self-hosted local internet hub for media, forums, chat, and offline knowledge.\n\nIt combines video, games, forums, personal profiles, and a wiki into one local-first social web."),
            ("Wikipedia", "Wikipedia is a collaborative encyclopedia built from community editing.\n\nArticles usually summarize a topic, give historical context, explain key ideas, and point toward related pages."),
            ("Internet", "The internet is a global system of connected networks.\n\nIt moves messages, web pages, video, files, and live communication between devices across many independent systems."),
            ("Intranet", "An intranet is a private network used inside a home, school, lab, or company.\n\nIt can host chat, documentation, announcements, local streaming, and tools without depending on the public web."),
            ("Operating System", "An operating system manages hardware, files, apps, and user sessions.\n\nIt provides the foundation that lets browsers, games, editors, and services run smoothly."),
            ("Router", "A router connects networks and decides where traffic should go.\n\nIn a local environment it often provides Wi-Fi, DHCP, and the path between devices and internet access."),
            ("History of the Web", "The web grew from linked hypertext documents into an ecosystem of apps, media, and social spaces.\n\nModern web software can now power live chat, voice calls, and rich local experiences."),
            ("Digital Library", "A digital library stores articles, media, and references in a searchable format.\n\nOffline libraries are especially useful for private intranets, classrooms, and portable deployments."),
        ],
    },
    "atlas": {
        "name": "Expanded Seed",
        "desc": "A richer offline wiki set with broader seeded topics and fuller summaries.",
        "mode": "expanded",
        "topics": [
            ("LocalNet", "LocalNet is a self-hosted local internet hub for media, forums, chat, and offline knowledge.\n\nIt is designed to feel like a complete private web, where users can upload videos and games, talk in real time, organize knowledge, and shape the local culture of the network."),
            ("Wikipedia", "Wikipedia is a community-built encyclopedia that organizes knowledge into linked articles.\n\nIts structure makes it useful as inspiration for offline knowledge packs because each page can stand alone while also connecting outward into a larger map of ideas."),
            ("Internet", "The internet is a system of interconnected networks that allows devices to exchange data using shared protocols.\n\nIt supports the web, messaging, streaming, file transfer, collaboration, and many other layers of modern communication."),
            ("Intranet", "An intranet is a private internal network used for communication, tools, and shared information.\n\nA strong intranet often includes profiles, search, media, reference material, and administrative tools that make the network feel alive and useful every day."),
            ("Operating System", "An operating system coordinates memory, storage, devices, networking, and processes.\n\nIt creates the environment that lets browsers, local servers, media tools, and communication apps all work together."),
            ("Router", "A router directs packets between networks and often acts as the center of a local deployment.\n\nIn many self-hosted setups it determines how phones, laptops, smart devices, and local servers discover and reach one another."),
            ("Offline Knowledge", "Offline knowledge systems preserve useful information even when internet access is limited or intentionally absent.\n\nThey are valuable for travel, education, archiving, emergency planning, and private environments."),
            ("Digital Library", "A digital library is a curated collection of documents, reference pages, and media.\n\nUnlike a random file dump, a good digital library is organized for browsing, search, and long-term reuse."),
            ("Search Engine", "A search engine helps users find relevant information quickly across many pages.\n\nOn a local network, search becomes a force multiplier because it turns scattered content into a usable shared memory."),
            ("Voice over IP", "Voice over IP carries calls as internet packets instead of traditional phone lines.\n\nModern browsers can support private voice calls directly through web standards such as WebRTC."),
            ("WebRTC", "WebRTC is a browser technology for live audio, video, and peer-to-peer data.\n\nIt is commonly used for real-time calls because it can connect browsers directly after an app handles signaling."),
            ("Community Moderation", "Community moderation shapes the tone and safety of a shared online space.\n\nClear rules, useful tools, and visible trust signals help a local network stay welcoming and reliable."),
        ],
    },
}
ZIM_PRESETS = {
    "wikipedia_100_mini": {
        "name": "Wikipedia 100 Mini",
        "desc": "A tiny English Wikipedia sample with a compact set of pages.",
        "size": "4.4 MB",
        "url": "https://download.kiwix.org/zim/wikipedia/wikipedia_en_100_mini_2026-04.zim",
    },
    "wikipedia_100_nopic": {
        "name": "Wikipedia 100 No Pictures",
        "desc": "A small English Wikipedia sample without images.",
        "size": "13 MB",
        "url": "https://download.kiwix.org/zim/wikipedia/wikipedia_en_100_nopic_2026-04.zim",
    },
    "wikipedia_100_maxi": {
        "name": "Wikipedia 100 With Pictures",
        "desc": "A small English Wikipedia sample with images kept in.",
        "size": "48 MB",
        "url": "https://download.kiwix.org/zim/wikipedia/wikipedia_en_100_maxi_2026-04.zim",
    },
    "wikipedia_all_mini": {
        "name": "Wikipedia Full Mini",
        "desc": "A large but trimmed-down English Wikipedia archive.",
        "size": "12 GB",
        "url": "https://download.kiwix.org/zim/wikipedia/wikipedia_en_all_mini_2026-03.zim",
    },
    "wikipedia_all_nopic": {
        "name": "Wikipedia Full No Pictures",
        "desc": "The full English Wikipedia without images.",
        "size": "48 GB",
        "url": "https://download.kiwix.org/zim/wikipedia/wikipedia_en_all_nopic_2026-03.zim",
    },
    "wikipedia_all_maxi": {
        "name": "Wikipedia Full With Pictures",
        "desc": "The biggest English Wikipedia archive with images included.",
        "size": "115 GB",
        "url": "https://download.kiwix.org/zim/wikipedia/wikipedia_en_all_maxi_2026-02.zim",
    },
}


def ensure_dirs() -> None:
    for path in [
        DATA_DIR,
        VIDEO_DIR,
        THUMBS_DIR,
        IMAGES_DIR,
        COVERS_DIR,
        GAMES_DIR,
        MUSIC_DIR,
        PFP_DIR,
        BANNER_DIR,
        ZIM_DIR,
        TOOLS_DIR,
        STATIC_DIR / "css",
        STATIC_DIR / "js",
    ]:
        path.mkdir(parents=True, exist_ok=True)


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def ts_human(dt: datetime | None = None) -> str:
    dt = dt or now_utc()
    return dt.astimezone().strftime("%Y-%m-%d %H:%M")


def load_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return default


def save_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=True), encoding="utf-8")


def load_or_create_secret() -> str:
    ensure_dirs()
    if SECRET_FILE.exists():
        return SECRET_FILE.read_text(encoding="utf-8").strip()
    secret = os.environ.get("LOCALNET_SECRET", secrets.token_hex(32))
    SECRET_FILE.write_text(secret, encoding="utf-8")
    return secret


def current_user() -> str | None:
    return session.get("user")


def get_admins() -> set[str]:
    if not ADMINS_FILE.exists():
        return set()
    return {
        line.strip()
        for line in ADMINS_FILE.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.strip().startswith("#")
    }


def is_admin_user(username: str | None) -> bool:
    return bool(username and username in get_admins())


def login_required(fn):
    @wraps(fn)
    def wrapped(*args, **kwargs):
        if not current_user():
            return redirect(url_for("login", next=request.path))
        return fn(*args, **kwargs)

    return wrapped


def get_users() -> dict[str, dict[str, Any]]:
    users = load_json(USERS_FILE, {})
    changed = False
    for username, account in users.items():
        changed = ensure_account_defaults(username, account) or changed
    if changed:
        save_users(users)
    return users


def save_users(data: dict[str, dict[str, Any]]) -> None:
    save_json(USERS_FILE, data)


def get_notifications_store() -> dict[str, list[dict[str, Any]]]:
    raw = load_json(NOTIFICATIONS_FILE, {})
    return raw if isinstance(raw, dict) else {}


def save_notifications_store(store: dict[str, list[dict[str, Any]]]) -> None:
    save_json(NOTIFICATIONS_FILE, store)


def user_notifications(username: str | None) -> list[dict[str, Any]]:
    if not username:
        return []
    return list(get_notifications_store().get(username, []))


def unread_notification_count(username: str | None) -> int:
    return sum(1 for item in user_notifications(username) if not item.get("read"))


def add_notification(username: str | None, text: str, href: str, kind: str = "general", actor: str | None = None) -> None:
    if not username:
        return
    store = get_notifications_store()
    items = store.setdefault(username, [])
    items.insert(
        0,
        {
            "id": make_id("note"),
            "text": text,
            "href": href,
            "kind": kind,
            "actor": actor or "",
            "ts": ts_human(),
            "created_at": now_utc().isoformat(),
            "read": False,
        },
    )
    store[username] = items[:150]
    save_notifications_store(store)


def mark_notifications_read(username: str, note_id: str | None = None) -> None:
    store = get_notifications_store()
    changed = False
    for item in store.get(username, []):
        if note_id and item.get("id") != note_id:
            continue
        if not item.get("read"):
            item["read"] = True
            changed = True
    if changed:
        save_notifications_store(store)


def get_download_jobs() -> list[dict[str, Any]]:
    jobs = load_json(DOWNLOADS_FILE, [])
    return jobs if isinstance(jobs, list) else []


def save_download_jobs(jobs: list[dict[str, Any]]) -> None:
    save_json(DOWNLOADS_FILE, jobs)


def get_library_state() -> dict[str, Any]:
    raw = load_json(LIBRARY_FILE, {})
    return raw if isinstance(raw, dict) else {}


def save_library_state(state: dict[str, Any]) -> None:
    save_json(LIBRARY_FILE, state)


def format_bytes(num: int | float | None) -> str:
    value = float(num or 0)
    units = ["B", "KB", "MB", "GB", "TB"]
    for unit in units:
        if value < 1024 or unit == units[-1]:
            if unit == "B":
                return f"{int(value)} {unit}"
            return f"{value:.1f} {unit}"
        value /= 1024
    return "0 B"


def resolve_downloaded_zim(filename: str) -> Path | None:
    def normalize_zim_path(path: Path) -> Path | None:
        if not path.exists() or not path.is_file():
            return None
        if path.suffix != ".zip":
            return path
        try:
            with path.open("rb") as handle:
                if handle.read(4)[:3] != b"ZIM":
                    return path
        except OSError:
            return path
        normalized = path.with_suffix("")
        if normalized.exists():
            return normalized
        try:
            path.rename(normalized)
            return normalized
        except OSError:
            return path

    direct = normalize_zim_path(ZIM_DIR / filename)
    if direct:
        return direct
    alt = normalize_zim_path(ZIM_DIR / f"{filename}.zip")
    if alt:
        return alt
    matches = sorted(ZIM_DIR.glob(f"{filename}*"))
    for match in matches:
        normalized = normalize_zim_path(match)
        if normalized:
            return normalized
    return None


def process_alive(pid: int | None) -> bool:
    if not pid:
        return False
    try:
        os.kill(int(pid), 0)
        return True
    except OSError:
        return False


def current_library_reader() -> dict[str, Any]:
    state = get_library_state()
    pid = int(state.get("pid") or 0)
    if not process_alive(pid):
        if state:
            state["pid"] = 0
            state["status"] = "stopped"
            save_library_state(state)
        return state
    return state


def offlinewiki_upstream_url() -> str:
    raw_path = request.environ.get("RAW_URI") or request.full_path or request.path
    path_part = raw_path.split("?", 1)[0]
    if not path_part.startswith(KIWIX_ROOT):
        path_part = request.path
    suffix = path_part[len(KIWIX_ROOT):]
    if suffix and not suffix.startswith("/"):
        suffix = f"/{suffix}"
    target = f"http://127.0.0.1:{current_library_reader().get('port', KIWIX_PORT)}{KIWIX_ROOT}{suffix}"
    if request.query_string:
        target = f"{target}?{request.query_string.decode('latin-1')}"
    return target


def stop_library_reader() -> None:
    state = get_library_state()
    pid = int(state.get("pid") or 0)
    if pid and process_alive(pid):
        try:
            os.kill(pid, 15)
        except OSError:
            pass
    save_library_state({"pid": 0, "status": "stopped", "port": KIWIX_PORT})


def start_library_reader(filename: str) -> tuple[bool, str]:
    kiwix_bin = detect_kiwix_bin()
    if not kiwix_bin:
        return False, "kiwix-serve is not installed on this host yet."
    path = resolve_downloaded_zim(filename)
    if not path:
        return False, "That downloaded Wikipedia file could not be found."
    state = current_library_reader()
    if state.get("active_filename") == path.name and process_alive(state.get("pid")):
        return True, ""
    stop_library_reader()
    proc = subprocess.Popen(
        [
            kiwix_bin,
            f"--port={KIWIX_PORT}",
            f"--urlRootLocation={KIWIX_ROOT}",
            str(path),
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )
    probe_url = f"http://127.0.0.1:{KIWIX_PORT}{KIWIX_ROOT}/"
    for _ in range(20):
        if proc.poll() is not None:
            return False, "kiwix-serve could not start for that archive."
        try:
            with urllib.request.urlopen(probe_url, timeout=0.4) as resp:
                if resp.status < 500:
                    break
        except Exception:
            time.sleep(0.25)
    else:
        try:
            proc.terminate()
        except OSError:
            pass
        return False, "kiwix-serve started but never became reachable."
    save_library_state(
        {
            "pid": proc.pid,
            "status": "running",
            "port": KIWIX_PORT,
            "active_filename": path.name,
            "started_at": now_utc().isoformat(),
            "started_ts": ts_human(),
        }
    )
    return True, ""


def ensure_account_defaults(username: str, account: dict[str, Any]) -> bool:
    changed = False
    defaults = {
        "created_at": now_utc().isoformat(),
        "two_factor_enabled": False,
        "two_factor_secret": "",
        "bio": "",
        "pfp": "",
        "banner": "",
    }
    for key, value in defaults.items():
        if key not in account:
            account[key] = value
            changed = True
    if "password_hash" not in account:
        account["password_hash"] = generate_password_hash(username)
        changed = True
    return changed


def file_url(folder: str, filename: str | None) -> str | None:
    if not filename:
        return None
    return f"/uploads/{folder}/{filename}"


def public_profile(username: str | None) -> dict[str, Any]:
    if not username:
        return {"username": "", "bio": "", "pfp": "", "banner": "", "pfp_url": None, "banner_url": None, "is_admin": False}
    account = get_users().get(username, {})
    return {
        "username": username,
        "bio": account.get("bio", ""),
        "pfp": account.get("pfp", ""),
        "banner": account.get("banner", ""),
        "pfp_url": file_url("pfps", account.get("pfp", "")),
        "banner_url": file_url("banners", account.get("banner", "")),
        "is_admin": is_admin_user(username),
    }


def decorate_author(username: str | None) -> dict[str, Any]:
    profile = public_profile(username)
    return {
        "name": username or "",
        "bio": profile["bio"],
        "pfp_url": profile["pfp_url"],
        "banner_url": profile["banner_url"],
        "is_admin": profile["is_admin"],
    }


def ensure_thread_defaults(thread: dict[str, Any]) -> bool:
    changed = False
    if thread.get("subforum") not in FORUM_LOOKUP:
        thread["subforum"] = "general"
        changed = True
    if "comments" not in thread:
        thread["comments"] = []
        changed = True
    if "voters" not in thread:
        thread["voters"] = {}
        changed = True
    return changed


def get_chat_store() -> dict[str, Any]:
    raw = load_json(CHAT_FILE, {"global": [], "dms": {}})
    changed = False
    if isinstance(raw, list):
        raw = {"global": raw, "dms": {}}
        changed = True
    if "global" not in raw:
        raw["global"] = []
        changed = True
    if "dms" not in raw:
        raw["dms"] = {}
        changed = True
    if changed:
        save_json(CHAT_FILE, raw)
    return raw


def save_chat_store(store: dict[str, Any]) -> None:
    save_json(CHAT_FILE, store)


def chat_thread_key(user_a: str, user_b: str) -> str:
    return "|".join(sorted([user_a, user_b]))


def serialize_message(message: dict[str, Any], current: str | None = None) -> dict[str, Any]:
    sender = message.get("sender", "")
    recipient = message.get("recipient")
    return {
        "sender": sender,
        "recipient": recipient,
        "text": message.get("text", ""),
        "ts": message.get("ts", ""),
        "kind": message.get("kind", "global" if not recipient else "dm"),
        "own": sender == current,
        "profile": decorate_author(sender),
    }


def latest_message_time(message: dict[str, Any]) -> str:
    return message.get("created_at", "") or message.get("ts", "")


def get_items(path: Path) -> list[dict[str, Any]]:
    return load_json(path, [])


def save_items(path: Path, items: list[dict[str, Any]]) -> None:
    save_json(path, items)


def make_id(prefix: str) -> str:
    return f"{prefix}_{secrets.token_hex(6)}"


downloads_lock = threading.Lock()


def slugify(value: str) -> str:
    cleaned = "".join(ch.lower() if ch.isalnum() else "-" for ch in value).strip("-")
    while "--" in cleaned:
        cleaned = cleaned.replace("--", "-")
    return cleaned or f"item-{secrets.token_hex(3)}"


def unique_slug(title: str, articles: list[dict[str, Any]], current_slug: str | None = None) -> str:
    base = slugify(title)
    slug = base
    taken = {a["slug"] for a in articles if a.get("slug") != current_slug}
    idx = 2
    while slug in taken:
        slug = f"{base}-{idx}"
        idx += 1
    return slug


def allowed_file(filename: str, allowed_exts: set[str]) -> bool:
    return Path(filename).suffix.lower() in allowed_exts


def save_upload(file_storage, dest_dir: Path, allowed_exts: set[str], prefix: str) -> str | None:
    if not file_storage or not file_storage.filename:
        return None
    original = secure_filename(file_storage.filename)
    if not original or not allowed_file(original, allowed_exts):
        return None
    ext = Path(original).suffix.lower()
    name = f"{prefix}_{secrets.token_hex(8)}{ext}"
    dest = dest_dir / name
    file_storage.save(dest)
    return name


def parse_expiry(value: str) -> str | None:
    mapping = {
        "1h": timedelta(hours=1),
        "24h": timedelta(hours=24),
        "7d": timedelta(days=7),
    }
    delta = mapping.get(value)
    if not delta:
        return None
    return (now_utc() + delta).isoformat()


def is_expired(item: dict[str, Any]) -> bool:
    expires_at = item.get("expires_at")
    if not expires_at:
        return False
    try:
        return datetime.fromisoformat(expires_at) <= now_utc()
    except ValueError:
        return False


def prune_expired_pastes() -> list[dict[str, Any]]:
    pastes = get_items(PASTES_FILE)
    kept = [p for p in pastes if not is_expired(p)]
    if len(kept) != len(pastes):
        save_items(PASTES_FILE, kept)
    return kept


def get_client_set(key: str) -> set[str]:
    return set(session.setdefault(key, []))


def store_client_set(key: str, values: set[str]) -> None:
    session[key] = list(values)


def html_paragraphs(text: str) -> str:
    escaped = html.escape(text or "")
    blocks = [segment.strip() for segment in escaped.split("\n\n")]
    rendered = []
    for block in blocks:
        if not block:
            continue
        rendered.append(f"<p>{block.replace(chr(10), '<br>')}</p>")
    return "".join(rendered) or "<p></p>"


def human_bytes(value: int | float | None) -> str:
    amount = float(value or 0)
    units = ["B", "KB", "MB", "GB", "TB"]
    idx = 0
    while amount >= 1024 and idx < len(units) - 1:
        amount /= 1024
        idx += 1
    if idx == 0:
        return f"{int(amount)} {units[idx]}"
    return f"{amount:.1f} {units[idx]}"


def seed_wiki_pack(pack_slug: str, username: str) -> int:
    pack = WIKI_PACKS.get(pack_slug)
    if not pack:
        return 0
    articles = get_items(WIKI_FILE)
    existing = {article.get("slug") for article in articles}
    added = 0
    for title, body in pack["topics"]:
        slug = unique_slug(title, articles)
        if slug in existing:
            continue
        articles.append(
            {
                "slug": slug,
                "title": title,
                "body": body,
                "author": username,
                "updated_at": now_utc().isoformat(),
                "ts": ts_human(),
            }
        )
        existing.add(slug)
        added += 1
    if added:
        save_items(WIKI_FILE, articles)
    return added


def update_download_job(job_id: str, **updates: Any) -> dict[str, Any] | None:
    with downloads_lock:
        jobs = get_download_jobs()
        for job in jobs:
            if job.get("id") == job_id:
                job.update(updates)
                save_download_jobs(jobs)
                return job
    return None


def run_zim_download(job_id: str, url: str, filename: str) -> None:
    target = ZIM_DIR / filename
    try:
        update_download_job(job_id, status="downloading", started_at=now_utc().isoformat(), started_ts=ts_human())
        req = urllib.request.Request(url, headers={"User-Agent": "LocalNet/1.0"})
        downloaded = 0
        total = 0
        last_save = 0.0
        with urllib.request.urlopen(req, timeout=60) as src, target.open("wb") as dst:
            total = int(src.headers.get("Content-Length") or 0)
            update_download_job(job_id, bytes_total=total)
            while True:
                chunk = src.read(1024 * 1024)
                if not chunk:
                    break
                dst.write(chunk)
                downloaded += len(chunk)
                if time.monotonic() - last_save > 0.8:
                    update_download_job(job_id, bytes_downloaded=downloaded, bytes_total=total)
                    last_save = time.monotonic()
        update_download_job(
            job_id,
            status="completed",
            bytes_downloaded=downloaded,
            bytes_total=total,
            finished_at=now_utc().isoformat(),
            finished_ts=ts_human(),
            local_path=str(target.relative_to(APP_ROOT)),
        )
    except Exception as exc:
        target.unlink(missing_ok=True)
        update_download_job(
            job_id,
            status="error",
            error=str(exc),
            finished_at=now_utc().isoformat(),
            finished_ts=ts_human(),
        )


def queue_zim_download(preset_slug: str, username: str) -> tuple[bool, str]:
    preset = ZIM_PRESETS.get(preset_slug)
    if not preset:
        return False, "That ZIM preset could not be found."
    jobs = get_download_jobs()
    filename = Path(preset["url"]).name
    for job in jobs:
        if job.get("filename") == filename and job.get("status") in {"queued", "downloading"}:
            return False, "That ZIM download is already running."
        if job.get("filename") == filename and job.get("status") == "completed":
            return False, "That ZIM file is already downloaded."
    job = {
        "id": make_id("zim"),
        "slug": preset_slug,
        "name": preset["name"],
        "desc": preset["desc"],
        "filename": filename,
        "url": preset["url"],
        "size": preset["size"],
        "status": "queued",
        "requested_by": username,
        "ts": ts_human(),
        "created_at": now_utc().isoformat(),
        "bytes_downloaded": 0,
        "bytes_total": 0,
    }
    jobs.insert(0, job)
    save_download_jobs(jobs[:60])
    threading.Thread(target=run_zim_download, args=(job["id"], preset["url"], filename), daemon=True).start()
    return True, f"{preset['name']} download started."


def urlsafe_b32_secret(length: int = 20) -> str:
    return base64.b32encode(secrets.token_bytes(length)).decode("ascii").rstrip("=")


def _totp_counter(for_time: int | None = None, step: int = 30) -> int:
    current = int(for_time or time.time())
    return current // step


def _hotp(secret: str, counter: int, digits: int = 6) -> str:
    padded = secret + "=" * ((8 - len(secret) % 8) % 8)
    key = base64.b32decode(padded, casefold=True)
    msg = counter.to_bytes(8, "big")
    digest = hmac.new(key, msg, hashlib.sha1).digest()
    offset = digest[-1] & 0x0F
    code_int = int.from_bytes(digest[offset : offset + 4], "big") & 0x7FFFFFFF
    return str(code_int % (10**digits)).zfill(digits)


def verify_totp(secret: str, code: str, window: int = 1) -> bool:
    if not code or not code.isdigit():
        return False
    counter = _totp_counter()
    for offset in range(-window, window + 1):
        if hmac.compare_digest(_hotp(secret, counter + offset), code.strip()):
            return True
    return False


def otpauth_uri(username: str, secret: str) -> str:
    label = quote(f"LocalNet:{username}")
    issuer = quote("LocalNet")
    return f"otpauth://totp/{label}?secret={secret}&issuer={issuer}&algorithm=SHA1&digits=6&period=30"


def safe_extract_zip(zip_path: Path, dest_dir: Path) -> None:
    with zipfile.ZipFile(zip_path) as zf:
        for member in zf.infolist():
            member_path = Path(member.filename)
            if member_path.is_absolute() or ".." in member_path.parts:
                continue
            target = dest_dir / member.filename
            target.parent.mkdir(parents=True, exist_ok=True)
            if member.is_dir():
                target.mkdir(parents=True, exist_ok=True)
                continue
            with zf.open(member) as src, target.open("wb") as dst:
                shutil.copyfileobj(src, dst)


def normalize_game_index(game_dir: Path) -> bool:
    index_html = game_dir / "index.html"
    if index_html.exists():
        return True
    html_files = [p for p in game_dir.rglob("*") if p.suffix.lower() in {".html", ".htm"}]
    if not html_files:
        return False
    chosen = min(html_files, key=lambda p: (len(p.parts), p.name != "index.html", p.name))
    if chosen.name.lower() == "index.html":
        rel_parts = chosen.relative_to(game_dir).parts
        if len(rel_parts) == 1:
            return True
    rel_target = chosen.relative_to(game_dir).as_posix()
    launcher = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta http-equiv="refresh" content="0; url=./{rel_target}">
  <script>location.replace("./{rel_target}");</script>
  <title>Launching game...</title>
</head>
<body style="background:#000;color:#fff;font-family:sans-serif;display:grid;place-items:center;height:100vh;margin:0">
  Launching game...
</body>
</html>
"""
    index_html.write_text(launcher, encoding="utf-8")
    return True


@dataclass
class ForumStore:
    threads: list[dict[str, Any]]

    @classmethod
    def load(cls) -> "ForumStore":
        threads = load_json(FORUMS_FILE, [])
        changed = False
        for thread in threads:
            changed = ensure_thread_defaults(thread) or changed
        if changed:
            save_json(FORUMS_FILE, threads)
        return cls(threads)

    def save(self) -> None:
        save_json(FORUMS_FILE, self.threads)


app = Flask(__name__, template_folder=str(TEMPLATES_DIR), static_folder=str(STATIC_DIR))
app.config["SECRET_KEY"] = load_or_create_secret()
app.config["MAX_CONTENT_LENGTH"] = 512 * 1024 * 1024
app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(days=30)
app.config["PREFERRED_URL_SCHEME"] = "https" if os.environ.get("LOCALNET_HTTPS") == "1" else "http"
app.config["SESSION_COOKIE_SECURE"] = os.environ.get("LOCALNET_HTTPS") == "1"
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)
socketio = SocketIO(app, async_mode="threading")

online_users: dict[str, str] = {}
user_sids: dict[str, set[str]] = {}
pending_calls: dict[str, str] = {}
active_calls: dict[str, str] = {}


def emit_to_user(event: str, payload: dict[str, Any], username: str) -> None:
    for sid in list(user_sids.get(username, set())):
        socketio.emit(event, payload, to=sid)


def clear_call_links(username: str) -> tuple[str | None, str | None]:
    pending_peer = pending_calls.pop(username, None)
    if pending_peer and pending_calls.get(pending_peer) == username:
        pending_calls.pop(pending_peer, None)
    active_peer = active_calls.pop(username, None)
    if active_peer and active_calls.get(active_peer) == username:
        active_calls.pop(active_peer, None)
    return pending_peer, active_peer


@app.context_processor
def inject_globals():
    username = current_user()
    return {
        "user": username,
        "request": request,
        "current_profile": public_profile(username),
        "current_is_admin": is_admin_user(username),
        "is_admin_user": is_admin_user,
        "notification_unread_count": unread_notification_count(username),
    }


@app.route("/uploads/<path:subpath>")
def uploads(subpath: str):
    return send_from_directory(UPLOADS_DIR, subpath)


@app.route("/login", methods=["GET", "POST"])
def login():
    if current_user():
        return redirect(url_for("home"))

    error = None
    username = session.get("pending_login_user", "")
    next_target = session.get("pending_login_next", request.args.get("next", ""))
    stage = "2fa" if session.get("pending_login_user") else "password"
    if request.method == "POST":
        users = get_users()
        form_stage = request.form.get("stage", "password")

        if form_stage == "2fa" and session.get("pending_login_user"):
            username = session.get("pending_login_user", "")
            otp = request.form.get("otp", "").strip()
            account = users.get(username)
            if not account:
                session.pop("pending_login_user", None)
                session.pop("pending_login_next", None)
                username = ""
                stage = "password"
                error = "That account could not be found anymore."
            elif verify_totp(account.get("two_factor_secret", ""), otp):
                session.pop("pending_login_user", None)
                next_target = session.pop("pending_login_next", "") or url_for("home")
                session["user"] = username
                session.permanent = True
                return redirect(next_target)
            else:
                stage = "2fa"
                error = "Enter the 6-digit code from your authenticator app."
        else:
            username = request.form.get("username", "").strip()
            password = request.form.get("password", "")
            next_target = request.form.get("next", "").strip() or request.args.get("next", "")

            if not username or not password:
                error = "Username and password are required."
            elif username not in users:
                users[username] = {
                    "password_hash": generate_password_hash(password),
                    "created_at": now_utc().isoformat(),
                    "two_factor_enabled": False,
                    "two_factor_secret": "",
                    "bio": "",
                    "pfp": "",
                    "banner": "",
                }
                save_users(users)
                session["user"] = username
                session.permanent = True
                return redirect(next_target or url_for("home"))
            else:
                account = users[username]
                if not check_password_hash(account["password_hash"], password):
                    error = "Incorrect password."
                elif account.get("two_factor_enabled"):
                    session["pending_login_user"] = username
                    session["pending_login_next"] = next_target
                    return redirect(url_for("login"))
                else:
                    session["user"] = username
                    session.permanent = True
                    return redirect(next_target or url_for("home"))

    return render_template("login.html", error=error, username=username, stage=stage, next_target=next_target)


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/notifications", methods=["GET", "POST"])
@login_required
def notifications():
    username = current_user()
    if request.method == "POST":
        action = request.form.get("action", "")
        if action == "mark_all_read":
            mark_notifications_read(username)
        elif action == "mark_read":
            mark_notifications_read(username, request.form.get("note_id", "").strip())
        return redirect(url_for("notifications"))
    items = sorted(user_notifications(username), key=lambda item: item.get("created_at", ""), reverse=True)
    return render_template("notifications.html", notifications=items)


@app.route("/library")
@login_required
def library():
    reader = current_library_reader()
    zim_files = []
    seen = set()
    for job in sorted(get_download_jobs(), key=lambda item: item.get("created_at", ""), reverse=True):
        if job.get("status") != "completed":
            continue
        path = resolve_downloaded_zim(job.get("filename", ""))
        if not path or path.name in seen:
            continue
        seen.add(path.name)
        zim_files.append(
            {
                "title": job.get("name") or path.name,
                "filename": path.name,
                "size": format_bytes(path.stat().st_size),
                "url": url_for("library_zim_file", filename=path.name),
                "reader_url": url_for("library_read", filename=path.name),
            }
        )
    for path in sorted(ZIM_DIR.iterdir()):
        if not path.is_file() or path.name in seen:
            continue
        zim_files.append(
            {
                "title": path.name,
                "filename": path.name,
                "size": format_bytes(path.stat().st_size),
                "url": url_for("library_zim_file", filename=path.name),
                "reader_url": url_for("library_read", filename=path.name),
            }
        )
    return render_template("library.html", zim_files=zim_files, wiki_packs=WIKI_PACKS, kiwix_available=bool(detect_kiwix_bin()), library_reader=reader)


@app.route("/library/zim/<path:filename>")
@login_required
def library_zim_file(filename: str):
    safe_name = Path(filename).name
    return send_from_directory(ZIM_DIR, safe_name, as_attachment=True)


@app.route("/library/read/<path:filename>")
@login_required
def library_read(filename: str):
    safe_name = Path(filename).name
    ok, error = start_library_reader(safe_name)
    return render_template(
        "library_reader.html",
        filename=safe_name,
        reader_ready=ok,
        reader_error=error,
        kiwix_available=bool(detect_kiwix_bin()),
        iframe_src=f"{KIWIX_ROOT}/",
    )


@app.route("/offlinewiki/", defaults={"proxy_path": ""})
@app.route("/offlinewiki/<path:proxy_path>")
@login_required
def offlinewiki_proxy(proxy_path: str):
    state = current_library_reader()
    if not process_alive(state.get("pid")):
        return Response("Offline wiki reader is not running.", status=503, mimetype="text/plain; charset=utf-8")
    target = offlinewiki_upstream_url()
    try:
        upstream = urllib.request.Request(target, headers={"User-Agent": "LocalNet/1.0"})
        with urllib.request.urlopen(upstream, timeout=30) as response:
            body = response.read()
            headers = []
            for key, value in response.headers.items():
                if key.lower() in {"content-type", "content-length", "cache-control", "etag", "last-modified", "content-security-policy", "referrer-policy"}:
                    headers.append((key, value))
            return Response(body, status=response.status, headers=headers)
    except urllib.error.HTTPError as exc:
        return Response(exc.read(), status=exc.code, mimetype=exc.headers.get_content_type())
    except Exception:
        return Response("Could not reach the offline wiki reader.", status=502, mimetype="text/plain; charset=utf-8")


@app.route("/setup/downloads")
@login_required
def setup_downloads():
    if not is_admin_user(current_user()):
        return jsonify({"error": "forbidden"}), 403
    jobs = sorted(get_download_jobs(), key=lambda item: item.get("created_at", ""), reverse=True)
    payload = []
    for job in jobs:
        total = int(job.get("bytes_total") or 0)
        done = int(job.get("bytes_downloaded") or 0)
        payload.append(
            {
                "id": job.get("id"),
                "name": job.get("name"),
                "filename": job.get("filename"),
                "status": job.get("status"),
                "size": job.get("size"),
                "error": job.get("error", ""),
                "bytes_downloaded": done,
                "bytes_total": total,
                "downloaded_label": format_bytes(done),
                "total_label": format_bytes(total) if total else "",
                "percent": round((done / total) * 100, 1) if total else 0,
            }
        )
    return jsonify({"jobs": payload})


@app.route("/")
@login_required
def home():
    forum_threads = ForumStore.load().threads
    videos = sorted(get_items(VIDEOS_FILE), key=lambda v: v.get("created_at", ""), reverse=True)[:4]
    games = sorted(get_items(GAMES_FILE), key=lambda g: g.get("created_at", ""), reverse=True)[:4]
    tracks = sorted(get_items(MUSIC_FILE), key=lambda t: t.get("created_at", ""), reverse=True)[:4]
    threads = sorted(forum_threads, key=lambda t: t.get("updated_at", ""), reverse=True)[:5]
    pastes = prune_expired_pastes()[:5]
    wiki = sorted(get_items(WIKI_FILE), key=lambda a: a.get("updated_at", ""), reverse=True)[:5]
    counts = {
        "videos": len(get_items(VIDEOS_FILE)),
        "games": len(get_items(GAMES_FILE)),
        "tracks": len(get_items(MUSIC_FILE)),
        "threads": len(forum_threads),
        "articles": len(get_items(WIKI_FILE)),
        "pastes": len(prune_expired_pastes()),
    }
    return render_template(
        "home.html",
        videos=videos,
        games=games,
        tracks=tracks,
        threads=threads,
        pastes=pastes,
        wiki=wiki,
        counts=counts,
    )


@app.route("/settings", methods=["GET", "POST"])
@login_required
def settings():
    message = None
    error = None
    secret = None
    provisioning_uri = None
    users = get_users()
    account = users[current_user()]

    if request.method == "POST":
        action = request.form.get("action", "")
        if action == "update_profile":
            bio = request.form.get("bio", "").strip()
            pfp = save_replacement_upload(
                request.files.get("pfp"),
                PFP_DIR,
                ALLOWED_IMAGE_EXTS,
                f"{current_user()}_pfp",
                account.get("pfp"),
            )
            banner = save_replacement_upload(
                request.files.get("banner"),
                BANNER_DIR,
                ALLOWED_IMAGE_EXTS,
                f"{current_user()}_banner",
                account.get("banner"),
            )
            account["bio"] = bio[:300]
            account["pfp"] = pfp or ""
            account["banner"] = banner or ""
            save_users(users)
            message = "Profile updated."
        elif action == "change_password":
            current_password = request.form.get("current_password", "")
            new_password = request.form.get("new_password", "")
            confirm_password = request.form.get("confirm_password", "")
            if not check_password_hash(account["password_hash"], current_password):
                error = "Your current password was incorrect."
            elif len(new_password) < 4:
                error = "New password must be at least 4 characters."
            elif new_password != confirm_password:
                error = "New password confirmation did not match."
            else:
                account["password_hash"] = generate_password_hash(new_password)
                save_users(users)
                message = "Password changed."
        elif action == "delete_account":
            password = request.form.get("password", "")
            confirm = request.form.get("confirm", "").strip()
            if not check_password_hash(account["password_hash"], password):
                error = "Password did not match your account."
            elif confirm != current_user():
                error = "Type your username exactly to delete the account."
            else:
                username = current_user()
                remove_user_account(username)
                session.clear()
                return redirect(url_for("login"))
        elif action == "setup_2fa":
            secret = urlsafe_b32_secret()
            account["two_factor_pending"] = secret
            save_users(users)
            provisioning_uri = otpauth_uri(current_user(), secret)
            message = "Scan the secret below in your authenticator app, then confirm with a code."
        elif action == "confirm_2fa":
            pending = account.get("two_factor_pending", "")
            code = request.form.get("otp", "").strip()
            if not pending:
                error = "Start setup first so we can generate a secret."
            elif not verify_totp(pending, code):
                error = "That verification code did not match."
                secret = pending
                provisioning_uri = otpauth_uri(current_user(), pending)
            else:
                account["two_factor_enabled"] = True
                account["two_factor_secret"] = pending
                account.pop("two_factor_pending", None)
                save_users(users)
                message = "Two-factor authentication is now enabled."
        elif action == "disable_2fa":
            account["two_factor_enabled"] = False
            account["two_factor_secret"] = ""
            account.pop("two_factor_pending", None)
            save_users(users)
            message = "Two-factor authentication has been disabled."
        elif action == "seed_wiki_pack" and is_admin_user(current_user()):
            added = seed_wiki_pack(request.form.get("pack", "").strip(), current_user())
            if added:
                message = f"Seeded {added} wiki pages into LocalNet."
            else:
                error = "That pack was empty or already seeded."
        elif action == "download_zim" and is_admin_user(current_user()):
            ok, msg = queue_zim_download(request.form.get("preset", "").strip(), current_user())
            if ok:
                message = msg
            else:
                error = msg

    pending = account.get("two_factor_pending")
    if pending and not secret:
        secret = pending
        provisioning_uri = otpauth_uri(current_user(), pending)

    jobs = get_download_jobs()
    jobs.sort(key=lambda item: item.get("created_at", ""), reverse=True)
    active_downloads = False
    for job in jobs:
        total = int(job.get("bytes_total") or 0)
        done = int(job.get("bytes_downloaded") or 0)
        job["downloaded_human"] = human_bytes(done)
        job["total_human"] = human_bytes(total) if total else ""
        job["progress_pct"] = round((done / total) * 100, 1) if total else 0
        if job.get("status") in {"queued", "downloading"}:
            active_downloads = True

    return render_template(
        "settings.html",
        message=message,
        error=error,
        secret=secret,
        provisioning_uri=provisioning_uri,
        two_factor_enabled=bool(account.get("two_factor_enabled")),
        account=account,
        wiki_packs=WIKI_PACKS,
        zim_presets=ZIM_PRESETS,
        download_jobs=jobs,
        active_downloads=active_downloads,
    )


@app.route("/tube")
@login_required
def tube():
    sort = request.args.get("sort", "new")
    videos = get_items(VIDEOS_FILE)
    if sort == "top":
        videos.sort(key=lambda v: (v.get("votes", 0), v.get("views", 0)), reverse=True)
    elif sort == "views":
        videos.sort(key=lambda v: v.get("views", 0), reverse=True)
    else:
        videos.sort(key=lambda v: v.get("created_at", ""), reverse=True)
    return render_template("tube.html", videos=videos, sort=sort)


@app.route("/tube/upload", methods=["GET", "POST"])
@login_required
def tube_upload():
    error = None
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        desc = request.form.get("desc", "").strip()
        video = request.files.get("video")
        thumb = request.files.get("thumbnail")
        if not title or not video or not video.filename:
            error = "Title and video file are required."
        elif not allowed_file(video.filename, ALLOWED_VIDEO_EXTS):
            error = "Unsupported video format."
        else:
            videos = get_items(VIDEOS_FILE)
            item_id = make_id("vid")
            filename = save_upload(video, VIDEO_DIR, ALLOWED_VIDEO_EXTS, item_id)
            thumbnail = save_upload(thumb, THUMBS_DIR, ALLOWED_IMAGE_EXTS, f"{item_id}_thumb")
            videos.append(
                {
                    "id": item_id,
                    "title": title,
                    "desc": desc,
                    "author": current_user(),
                    "filename": filename,
                    "thumbnail": thumbnail,
                    "views": 0,
                    "votes": 0,
                    "voters": {},
                    "comments": [],
                    "created_at": now_utc().isoformat(),
                    "ts": ts_human(),
                }
            )
            save_items(VIDEOS_FILE, videos)
            return redirect(url_for("tube_watch", video_id=item_id))
    return render_template("tube_upload.html", error=error)


def find_by_id(path: Path, item_id: str) -> tuple[list[dict[str, Any]], dict[str, Any] | None]:
    items = get_items(path)
    for item in items:
        if item.get("id") == item_id:
            return items, item
    return items, None


def save_replacement_upload(file_storage, dest_dir: Path, allowed_exts: set[str], prefix: str, previous: str | None = None) -> str | None:
    filename = save_upload(file_storage, dest_dir, allowed_exts, prefix)
    if filename and previous:
        (dest_dir / previous).unlink(missing_ok=True)
    return filename or previous


def remove_user_account(username: str) -> None:
    users = get_users()
    account = users.pop(username, None)
    if account:
        if account.get("pfp"):
            (PFP_DIR / account["pfp"]).unlink(missing_ok=True)
        if account.get("banner"):
            (BANNER_DIR / account["banner"]).unlink(missing_ok=True)
        save_users(users)

    videos = get_items(VIDEOS_FILE)
    kept_videos = []
    for video in videos:
        if video.get("author") == username:
            if video.get("filename"):
                (VIDEO_DIR / video["filename"]).unlink(missing_ok=True)
            if video.get("thumbnail"):
                (THUMBS_DIR / video["thumbnail"]).unlink(missing_ok=True)
            for comment in video.get("comments", []):
                if comment.get("image"):
                    (IMAGES_DIR / comment["image"]).unlink(missing_ok=True)
            continue
        if video.get("voters", {}).pop(username, None):
            video["votes"] = max(0, int(video.get("votes", 0)) - 1)
        filtered_comments = []
        for comment in video.get("comments", []):
            if comment.get("author") == username:
                if comment.get("image"):
                    (IMAGES_DIR / comment["image"]).unlink(missing_ok=True)
                continue
            filtered_comments.append(comment)
        video["comments"] = filtered_comments
        kept_videos.append(video)
    save_items(VIDEOS_FILE, kept_videos)

    games = get_items(GAMES_FILE)
    kept_games = []
    for game in games:
        if game.get("author") == username:
            shutil.rmtree(GAMES_DIR / game.get("id", ""), ignore_errors=True)
            if game.get("cover"):
                (COVERS_DIR / game["cover"]).unlink(missing_ok=True)
            continue
        if game.get("voters", {}).pop(username, None):
            game["votes"] = max(0, int(game.get("votes", 0)) - 1)
        kept_games.append(game)
    save_items(GAMES_FILE, kept_games)

    tracks = get_items(MUSIC_FILE)
    kept_tracks = []
    for track in tracks:
        if track.get("author") == username:
            if track.get("filename"):
                (MUSIC_DIR / track["filename"]).unlink(missing_ok=True)
            if track.get("cover"):
                (COVERS_DIR / track["cover"]).unlink(missing_ok=True)
            continue
        if track.get("voters", {}).pop(username, None):
            track["votes"] = max(0, int(track.get("votes", 0)) - 1)
        track["comments"] = [comment for comment in track.get("comments", []) if comment.get("author") != username]
        kept_tracks.append(track)
    save_items(MUSIC_FILE, kept_tracks)

    save_items(PASTES_FILE, [paste for paste in get_items(PASTES_FILE) if paste.get("author") != username])
    save_items(WIKI_FILE, [article for article in get_items(WIKI_FILE) if article.get("author") != username])

    store = ForumStore.load()
    kept_threads = []
    for thread in store.threads:
        if thread.get("author") == username:
            for comment in thread.get("comments", []):
                if comment.get("image"):
                    (IMAGES_DIR / comment["image"]).unlink(missing_ok=True)
            continue
        if thread.get("voters", {}).pop(username, None):
            thread["votes"] = max(0, int(thread.get("votes", 0)) - 1)
        comments = []
        for comment in thread.get("comments", []):
            if comment.get("author") == username:
                if comment.get("image"):
                    (IMAGES_DIR / comment["image"]).unlink(missing_ok=True)
                continue
            comments.append(comment)
        thread["comments"] = comments
        kept_threads.append(thread)
    store.threads = kept_threads
    store.save()

    chat_store = get_chat_store()
    chat_store["global"] = [msg for msg in chat_store.get("global", []) if msg.get("sender") != username]
    filtered_dms = {}
    for key, messages in chat_store.get("dms", {}).items():
        if username in key.split("|"):
            continue
        filtered_dms[key] = [msg for msg in messages if msg.get("sender") != username]
    chat_store["dms"] = filtered_dms
    save_chat_store(chat_store)

    notifications = get_notifications_store()
    notifications.pop(username, None)
    changed = False
    for target, items in notifications.items():
        filtered = [item for item in items if item.get("actor") != username]
        if len(filtered) != len(items):
            notifications[target] = filtered
            changed = True
    if changed or username not in notifications:
        save_notifications_store(notifications)


@app.route("/tube/watch/<video_id>", methods=["GET", "POST"])
@login_required
def tube_watch(video_id: str):
    videos, video = find_by_id(VIDEOS_FILE, video_id)
    if not video:
        return redirect(url_for("tube"))

    viewed = get_client_set("viewed_videos")
    if request.method == "GET" and video_id not in viewed:
        video["views"] = int(video.get("views", 0)) + 1
        viewed.add(video_id)
        store_client_set("viewed_videos", viewed)
        save_items(VIDEOS_FILE, videos)

    if request.method == "POST":
        body = request.form.get("body", "").strip()
        image = request.files.get("image")
        image_name = save_upload(image, IMAGES_DIR, ALLOWED_IMAGE_EXTS, f"cmt_{video_id}")
        if body or image_name:
            video.setdefault("comments", []).append(
                {
                    "author": current_user(),
                    "body": body,
                    "image": image_name,
                    "ts": ts_human(),
                }
            )
            save_items(VIDEOS_FILE, videos)
            if video.get("author") and video.get("author") != current_user():
                add_notification(video.get("author"), f"{current_user()} commented on your video {video.get('title', 'Untitled')}.", url_for("tube_watch", video_id=video_id), kind="tube", actor=current_user())
        return redirect(url_for("tube_watch", video_id=video_id))

    related = [v for v in videos if v.get("id") != video_id][:8]
    return render_template("tube_watch.html", v=video, related=related)


@app.route("/tube/vote/<video_id>")
@login_required
def tube_vote(video_id: str):
    videos, video = find_by_id(VIDEOS_FILE, video_id)
    if video:
        voters = video.setdefault("voters", {})
        voted = False
        if voters.get(current_user()):
            voters.pop(current_user(), None)
            video["votes"] = max(0, int(video.get("votes", 0)) - 1)
        else:
            voters[current_user()] = True
            video["votes"] = int(video.get("votes", 0)) + 1
            voted = True
        save_items(VIDEOS_FILE, videos)
        if voted and video.get("author") and video.get("author") != current_user():
            add_notification(video.get("author"), f"{current_user()} liked your video {video.get('title', 'Untitled')}.", url_for("tube_watch", video_id=video_id), kind="tube", actor=current_user())
    return redirect(request.referrer or url_for("tube_watch", video_id=video_id))


@app.route("/tube/edit/<video_id>", methods=["GET", "POST"])
@login_required
def tube_edit(video_id: str):
    videos, video = find_by_id(VIDEOS_FILE, video_id)
    if not video or video.get("author") != current_user():
        return redirect(url_for("tube"))
    error = None
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        if not title:
            error = "Title is required."
        else:
            video["title"] = title
            video["desc"] = request.form.get("desc", "").strip()
            save_items(VIDEOS_FILE, videos)
            return redirect(url_for("tube_watch", video_id=video_id))
    return render_template("tube_edit.html", v=video, error=error)


@app.route("/tube/delete/<video_id>")
@login_required
def tube_delete(video_id: str):
    videos = get_items(VIDEOS_FILE)
    kept = []
    for video in videos:
        if video.get("id") == video_id and video.get("author") == current_user():
            if video.get("filename"):
                (VIDEO_DIR / video["filename"]).unlink(missing_ok=True)
            if video.get("thumbnail"):
                (THUMBS_DIR / video["thumbnail"]).unlink(missing_ok=True)
            for comment in video.get("comments", []):
                if comment.get("image"):
                    (IMAGES_DIR / comment["image"]).unlink(missing_ok=True)
            continue
        kept.append(video)
    save_items(VIDEOS_FILE, kept)
    return redirect(url_for("tube"))


@app.route("/games")
@login_required
def games():
    sort = request.args.get("sort", "new")
    items = get_items(GAMES_FILE)
    if sort == "top":
        items.sort(key=lambda g: (g.get("votes", 0), g.get("plays", 0)), reverse=True)
    else:
        items.sort(key=lambda g: g.get("created_at", ""), reverse=True)
    return render_template("games.html", games=items, sort=sort)


@app.route("/games/upload", methods=["GET", "POST"])
@login_required
def games_upload():
    error = None
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        desc = request.form.get("desc", "").strip()
        game_file = request.files.get("game")
        cover = request.files.get("cover")
        if not title or not game_file or not game_file.filename:
            error = "Title and game file are required."
        elif not allowed_file(game_file.filename, ALLOWED_GAME_EXTS):
            error = "Game uploads must be a zip or html file."
        else:
            game_id = make_id("game")
            game_dir = GAMES_DIR / game_id
            game_dir.mkdir(parents=True, exist_ok=True)
            uploaded_name = secure_filename(game_file.filename)
            uploaded_path = game_dir / uploaded_name
            game_file.save(uploaded_path)
            if uploaded_path.suffix.lower() == ".zip":
                safe_extract_zip(uploaded_path, game_dir)
                uploaded_path.unlink(missing_ok=True)
            else:
                target = game_dir / "index.html"
                if uploaded_path != target:
                    shutil.move(str(uploaded_path), target)
            if not normalize_game_index(game_dir):
                shutil.rmtree(game_dir, ignore_errors=True)
                error = "Could not find an index.html in that game package."
            else:
                cover_name = save_upload(cover, COVERS_DIR, ALLOWED_IMAGE_EXTS, f"{game_id}_cover")
                items = get_items(GAMES_FILE)
                items.append(
                    {
                        "id": game_id,
                        "title": title,
                        "desc": desc,
                        "author": current_user(),
                        "cover": cover_name,
                        "plays": 0,
                        "votes": 0,
                        "voters": {},
                        "created_at": now_utc().isoformat(),
                        "ts": ts_human(),
                    }
                )
                save_items(GAMES_FILE, items)
                return redirect(url_for("games_play", game_id=game_id))
    return render_template("games_upload.html", error=error)


@app.route("/games/play/<game_id>")
@login_required
def games_play(game_id: str):
    items, game = find_by_id(GAMES_FILE, game_id)
    if not game:
        return redirect(url_for("games"))
    played = get_client_set("played_games")
    if game_id not in played:
        game["plays"] = int(game.get("plays", 0)) + 1
        played.add(game_id)
        store_client_set("played_games", played)
        save_items(GAMES_FILE, items)
    return render_template("games_play.html", g=game)


@app.route("/games/vote/<game_id>")
@login_required
def games_vote(game_id: str):
    items, game = find_by_id(GAMES_FILE, game_id)
    if game:
        voters = game.setdefault("voters", {})
        voted = False
        if voters.get(current_user()):
            voters.pop(current_user(), None)
            game["votes"] = max(0, int(game.get("votes", 0)) - 1)
        else:
            voters[current_user()] = True
            game["votes"] = int(game.get("votes", 0)) + 1
            voted = True
        save_items(GAMES_FILE, items)
        if voted and game.get("author") and game.get("author") != current_user():
            add_notification(game.get("author"), f"{current_user()} liked your game {game.get('title', 'Untitled')}.", url_for("games_play", game_id=game_id), kind="games", actor=current_user())
    return redirect(request.referrer or url_for("games_play", game_id=game_id))


@app.route("/games/delete/<game_id>")
@login_required
def games_delete(game_id: str):
    items = get_items(GAMES_FILE)
    kept = []
    for game in items:
        if game.get("id") == game_id and game.get("author") == current_user():
            shutil.rmtree(GAMES_DIR / game_id, ignore_errors=True)
            if game.get("cover"):
                (COVERS_DIR / game["cover"]).unlink(missing_ok=True)
            continue
        kept.append(game)
    save_items(GAMES_FILE, kept)
    return redirect(url_for("games"))


@app.route("/music")
@login_required
def music():
    sort = request.args.get("sort", "new")
    tracks = get_items(MUSIC_FILE)
    if sort == "top":
        tracks.sort(key=lambda track: (track.get("votes", 0), track.get("plays", 0)), reverse=True)
    elif sort == "plays":
        tracks.sort(key=lambda track: track.get("plays", 0), reverse=True)
    else:
        tracks.sort(key=lambda track: track.get("created_at", ""), reverse=True)
    return render_template("music.html", tracks=tracks, sort=sort)


@app.route("/music/upload", methods=["GET", "POST"])
@login_required
def music_upload():
    error = None
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        artist = request.form.get("artist", "").strip()
        album = request.form.get("album", "").strip()
        desc = request.form.get("desc", "").strip()
        audio = request.files.get("audio")
        cover = request.files.get("cover")
        if not title or not audio or not audio.filename:
            error = "Title and audio file are required."
        elif not allowed_file(audio.filename, ALLOWED_AUDIO_EXTS):
            error = "Unsupported audio format."
        else:
            tracks = get_items(MUSIC_FILE)
            item_id = make_id("track")
            filename = save_upload(audio, MUSIC_DIR, ALLOWED_AUDIO_EXTS, item_id)
            cover_name = save_upload(cover, COVERS_DIR, ALLOWED_IMAGE_EXTS, f"{item_id}_cover")
            tracks.append(
                {
                    "id": item_id,
                    "title": title,
                    "artist": artist or current_user(),
                    "album": album,
                    "desc": desc,
                    "author": current_user(),
                    "filename": filename,
                    "cover": cover_name,
                    "plays": 0,
                    "votes": 0,
                    "voters": {},
                    "comments": [],
                    "created_at": now_utc().isoformat(),
                    "ts": ts_human(),
                }
            )
            save_items(MUSIC_FILE, tracks)
            return redirect(url_for("music_track", track_id=item_id))
    return render_template("music_upload.html", error=error)


@app.route("/music/track/<track_id>", methods=["GET", "POST"])
@login_required
def music_track(track_id: str):
    tracks, track = find_by_id(MUSIC_FILE, track_id)
    if not track:
        return redirect(url_for("music"))

    played = get_client_set("played_tracks")
    if request.method == "GET" and track_id not in played:
        track["plays"] = int(track.get("plays", 0)) + 1
        played.add(track_id)
        store_client_set("played_tracks", played)
        save_items(MUSIC_FILE, tracks)

    if request.method == "POST":
        body = request.form.get("body", "").strip()
        if body:
            track.setdefault("comments", []).append(
                {
                    "author": current_user(),
                    "body": body,
                    "ts": ts_human(),
                }
            )
            save_items(MUSIC_FILE, tracks)
            if track.get("author") and track.get("author") != current_user():
                add_notification(track.get("author"), f"{current_user()} commented on your track {track.get('title', 'Untitled')}.", url_for("music_track", track_id=track_id), kind="music", actor=current_user())
        return redirect(url_for("music_track", track_id=track_id))

    related = [item for item in tracks if item.get("id") != track_id][:8]
    return render_template("music_track.html", track=track, related=related)


@app.route("/music/vote/<track_id>")
@login_required
def music_vote(track_id: str):
    tracks, track = find_by_id(MUSIC_FILE, track_id)
    if track:
        voters = track.setdefault("voters", {})
        voted = False
        if voters.get(current_user()):
            voters.pop(current_user(), None)
            track["votes"] = max(0, int(track.get("votes", 0)) - 1)
        else:
            voters[current_user()] = True
            track["votes"] = int(track.get("votes", 0)) + 1
            voted = True
        save_items(MUSIC_FILE, tracks)
        if voted and track.get("author") and track.get("author") != current_user():
            add_notification(track.get("author"), f"{current_user()} liked your track {track.get('title', 'Untitled')}.", url_for("music_track", track_id=track_id), kind="music", actor=current_user())
    return redirect(request.referrer or url_for("music_track", track_id=track_id))


@app.route("/music/edit/<track_id>", methods=["GET", "POST"])
@login_required
def music_edit(track_id: str):
    tracks, track = find_by_id(MUSIC_FILE, track_id)
    if not track or track.get("author") != current_user():
        return redirect(url_for("music"))
    error = None
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        if not title:
            error = "Title is required."
        else:
            track["title"] = title
            track["artist"] = request.form.get("artist", "").strip() or current_user()
            track["album"] = request.form.get("album", "").strip()
            track["desc"] = request.form.get("desc", "").strip()
            save_items(MUSIC_FILE, tracks)
            return redirect(url_for("music_track", track_id=track_id))
    return render_template("music_edit.html", track=track, error=error)


@app.route("/music/delete/<track_id>")
@login_required
def music_delete(track_id: str):
    tracks = get_items(MUSIC_FILE)
    kept = []
    for track in tracks:
        if track.get("id") == track_id and track.get("author") == current_user():
            if track.get("filename"):
                (MUSIC_DIR / track["filename"]).unlink(missing_ok=True)
            if track.get("cover"):
                (COVERS_DIR / track["cover"]).unlink(missing_ok=True)
            continue
        kept.append(track)
    save_items(MUSIC_FILE, kept)
    return redirect(url_for("music"))


@app.route("/paste")
@login_required
def paste():
    pastes = prune_expired_pastes()
    pastes.sort(key=lambda p: p.get("created_at", ""), reverse=True)
    return render_template("paste.html", pastes=pastes)


@app.route("/paste/new", methods=["GET", "POST"])
@login_required
def paste_new():
    error = None
    if request.method == "POST":
        body = request.form.get("body", "")
        if not body.strip():
            error = "Paste content is required."
        else:
            pastes = prune_expired_pastes()
            paste_id = make_id("paste")
            pastes.append(
                {
                    "id": paste_id,
                    "title": request.form.get("title", "").strip(),
                    "lang": request.form.get("lang", "text").strip() or "text",
                    "body": body,
                    "author": current_user(),
                    "views": 0,
                    "expires_at": parse_expiry(request.form.get("expires", "never")),
                    "created_at": now_utc().isoformat(),
                    "ts": ts_human(),
                }
            )
            save_items(PASTES_FILE, pastes)
            return redirect(url_for("paste_view", paste_id=paste_id))
    return render_template("paste_new.html", error=error)


@app.route("/paste/<paste_id>")
@login_required
def paste_view(paste_id: str):
    pastes = prune_expired_pastes()
    for item in pastes:
        if item.get("id") == paste_id:
            seen = get_client_set("viewed_pastes")
            if paste_id not in seen:
                item["views"] = int(item.get("views", 0)) + 1
                seen.add(paste_id)
                store_client_set("viewed_pastes", seen)
                save_items(PASTES_FILE, pastes)
            return render_template("paste_view.html", p=item)
    return redirect(url_for("paste"))


@app.route("/paste/<paste_id>/raw")
@login_required
def paste_raw(paste_id: str):
    pastes = prune_expired_pastes()
    for item in pastes:
        if item.get("id") == paste_id:
            return Response(item.get("body", ""), mimetype="text/plain; charset=utf-8")
    return Response("Not found", status=404, mimetype="text/plain; charset=utf-8")


@app.route("/paste/delete/<paste_id>")
@login_required
def paste_delete(paste_id: str):
    pastes = prune_expired_pastes()
    kept = [p for p in pastes if not (p.get("id") == paste_id and p.get("author") == current_user())]
    save_items(PASTES_FILE, kept)
    return redirect(url_for("paste"))


@app.route("/wiki")
@login_required
def wiki():
    articles = get_items(WIKI_FILE)
    articles.sort(key=lambda a: a.get("updated_at", ""), reverse=True)
    return render_template("wiki.html", articles=articles)


@app.route("/wiki/<slug>")
@login_required
def wiki_article(slug: str):
    articles = get_items(WIKI_FILE)
    for article in articles:
        if article.get("slug") == slug:
            return render_template("wiki_article.html", art=article, slug=slug, art_html=html_paragraphs(article.get("body", "")))
    return redirect(url_for("wiki"))


@app.route("/wiki/<slug>/edit", methods=["GET", "POST"])
@login_required
def wiki_edit(slug: str):
    articles = get_items(WIKI_FILE)
    article = next((a for a in articles if a.get("slug") == slug), None)
    is_new = article is None
    if is_new:
        article = {"title": "" if slug == "new" else slug.replace("-", " ").title(), "body": "", "slug": slug}

    if request.method == "POST":
        title = request.form.get("title", "").strip()
        body = request.form.get("body", "").strip()
        if title:
            target_slug = unique_slug(title, articles, None if is_new else slug)
            payload = {
                "slug": target_slug,
                "title": title,
                "body": body,
                "author": current_user(),
                "updated_at": now_utc().isoformat(),
                "ts": ts_human(),
            }
            if is_new:
                articles.append(payload)
            else:
                previous_author = article.get("author")
                idx = articles.index(next(a for a in articles if a.get("slug") == slug))
                articles[idx] = payload
            save_items(WIKI_FILE, articles)
            if not is_new and previous_author and previous_author != current_user():
                add_notification(previous_author, f"{current_user()} edited your wiki page {title}.", url_for("wiki_article", slug=target_slug), kind="wiki", actor=current_user())
            return redirect(url_for("wiki_article", slug=target_slug))

    return render_template("wiki_edit.html", art=article)


@app.route("/forums", methods=["GET", "POST"])
@login_required
def forums():
    store = ForumStore.load()
    active_forum = request.args.get("forum", "all")
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        body = request.form.get("body", "").strip()
        subforum = request.form.get("subforum", "general")
        if subforum not in FORUM_LOOKUP:
            subforum = "general"
        if title and body:
            store.threads.append(
                {
                    "id": make_id("thread"),
                    "title": title,
                    "body": body,
                    "author": current_user(),
                    "subforum": subforum,
                    "votes": 0,
                    "voters": {},
                    "comments": [],
                    "created_at": now_utc().isoformat(),
                    "updated_at": now_utc().isoformat(),
                    "ts": ts_human(),
                }
            )
            store.save()
            return redirect(url_for("forums", forum=subforum))
    store.threads.sort(key=lambda t: (t.get("updated_at", ""), t.get("votes", 0)), reverse=True)
    filtered = [
        thread
        for thread in store.threads
        if active_forum == "all" or thread.get("subforum", "general") == active_forum
    ]
    counts = {forum["slug"]: 0 for forum in FORUM_SECTIONS}
    for thread in store.threads:
        counts[thread.get("subforum", "general")] = counts.get(thread.get("subforum", "general"), 0) + 1
    decorated_threads = []
    for thread in filtered:
        item = dict(thread)
        item["forum_meta"] = FORUM_LOOKUP.get(item.get("subforum", "general"), FORUM_LOOKUP["general"])
        item["author_profile"] = decorate_author(item.get("author"))
        item["comments"] = [
            {**comment, "author_profile": decorate_author(comment.get("author"))}
            for comment in item.get("comments", [])
        ]
        decorated_threads.append(item)
    return render_template(
        "forums.html",
        threads=decorated_threads,
        subforums=FORUM_SECTIONS,
        active_forum=active_forum,
        counts=counts,
    )


@app.route("/forums/vote/<thread_id>")
@login_required
def forums_vote(thread_id: str):
    store = ForumStore.load()
    for thread in store.threads:
        if thread.get("id") == thread_id:
            voters = thread.setdefault("voters", {})
            voted = False
            if voters.get(current_user()):
                voters.pop(current_user(), None)
                thread["votes"] = max(0, int(thread.get("votes", 0)) - 1)
            else:
                voters[current_user()] = True
                thread["votes"] = int(thread.get("votes", 0)) + 1
                voted = True
            thread["updated_at"] = now_utc().isoformat()
            store.save()
            if voted and thread.get("author") and thread.get("author") != current_user():
                add_notification(thread.get("author"), f"{current_user()} liked your forum thread {thread.get('title', 'Untitled')}.", url_for("forums", forum=thread.get("subforum", "general")), kind="forums", actor=current_user())
            break
    return redirect(url_for("forums"))


@app.route("/forums/comment/<thread_id>", methods=["POST"])
@login_required
def forums_comment(thread_id: str):
    store = ForumStore.load()
    body = request.form.get("body", "").strip()
    image = request.files.get("image")
    image_name = save_upload(image, IMAGES_DIR, ALLOWED_IMAGE_EXTS, f"forum_{thread_id}")
    if not body and not image_name:
        return redirect(url_for("forums"))
    target_forum = "general"
    for thread in store.threads:
        if thread.get("id") == thread_id:
            target_forum = thread.get("subforum", "general")
            thread.setdefault("comments", []).append(
                {
                    "author": current_user(),
                    "body": body,
                    "image": image_name,
                    "ts": ts_human(),
                }
            )
            thread["updated_at"] = now_utc().isoformat()
            store.save()
            if thread.get("author") and thread.get("author") != current_user():
                add_notification(thread.get("author"), f"{current_user()} replied to your thread {thread.get('title', 'Untitled')}.", url_for("forums", forum=target_forum), kind="forums", actor=current_user())
            break
    return redirect(url_for("forums", forum=target_forum))


@app.route("/chat")
@login_required
def chat():
    username = current_user()
    users = []
    for other_name in sorted(get_users()):
        if other_name == username:
            continue
        users.append(
            {
                "username": other_name,
                "profile": public_profile(other_name),
            }
        )
    store = get_chat_store()
    conversations = []
    for key, messages in store.get("dms", {}).items():
        participants = key.split("|")
        if username not in participants or not messages:
            continue
        peer = participants[0] if participants[1] == username else participants[1]
        last = messages[-1]
        conversations.append(
            {
                "peer": peer,
                "profile": public_profile(peer),
                "last_text": last.get("text", ""),
                "last_ts": last.get("ts", ""),
                "last_time": latest_message_time(last),
            }
        )
    conversations.sort(key=lambda conv: conv["last_time"], reverse=True)
    active_peer = request.args.get("dm", "").strip()
    if active_peer == username or active_peer not in {user["username"] for user in users}:
        active_peer = ""
    return render_template("chat.html", chat_users=users, conversations=conversations, active_peer=active_peer)


@app.route("/chat/history")
@login_required
def chat_history():
    username = current_user()
    peer = request.args.get("peer", "").strip()
    store = get_chat_store()
    if peer:
        messages = store.get("dms", {}).get(chat_thread_key(username, peer), [])
        title = f"DM with {peer}"
        scope = "dm"
    else:
        messages = store.get("global", [])
        title = "Lobby"
        scope = "global"
    return jsonify(
        {
            "scope": scope,
            "title": title,
            "peer": peer,
            "messages": [serialize_message(message, username) for message in messages[-200:]],
        }
    )


@socketio.on("join")
def socket_join(data):
    username = (data or {}).get("username") or current_user() or "Guest"
    online_users[request.sid] = username
    user_sids.setdefault(username, set()).add(request.sid)
    emit("global_message", {"sender": "System", "text": f"{username} joined chat.", "ts": ts_human(), "kind": "system"}, broadcast=True)
    emit("userlist", sorted(set(online_users.values())), broadcast=True)


@socketio.on("send_message")
def socket_message(data):
    sender = current_user() or (data or {}).get("sender") or "Guest"
    text = (data or {}).get("text", "").strip()
    if not text:
        return
    recipient = ((data or {}).get("recipient") or "").strip()
    payload = {
        "sender": sender,
        "recipient": recipient or None,
        "text": text[:2000],
        "ts": ts_human(),
        "created_at": now_utc().isoformat(),
        "kind": "dm" if recipient else "global",
    }
    store = get_chat_store()
    if recipient and recipient != sender:
        key = chat_thread_key(sender, recipient)
        thread = store.setdefault("dms", {}).setdefault(key, [])
        thread.append(payload)
        thread[:] = thread[-200:]
        save_chat_store(store)
        add_notification(recipient, f"New DM from {sender}.", url_for("chat", dm=sender), kind="chat", actor=sender)
        for target in {sender, recipient}:
            for sid in user_sids.get(target, set()):
                socketio.emit("direct_message", serialize_message(payload, target), to=sid)
    else:
        store.setdefault("global", []).append(payload)
        store["global"] = store["global"][-200:]
        save_chat_store(store)
        emit("global_message", serialize_message(payload, sender), broadcast=True)


@socketio.on("call_offer")
def socket_call_offer(data):
    sender = current_user() or (data or {}).get("from") or ""
    recipient = ((data or {}).get("to") or "").strip()
    offer = (data or {}).get("offer")
    if not sender or not recipient or recipient == sender or not offer:
        emit("call_error", {"message": "Call could not be started."})
        return
    if recipient not in get_users():
        emit("call_error", {"message": "That user does not exist."})
        return
    if recipient not in user_sids:
        emit("call_unavailable", {"peer": recipient})
        return
    if active_calls.get(sender) not in {None, recipient} or active_calls.get(recipient) not in {None, sender}:
        emit("call_busy", {"peer": recipient})
        return
    if pending_calls.get(recipient) not in {None, sender}:
        emit("call_busy", {"peer": recipient})
        return
    pending_calls[sender] = recipient
    pending_calls[recipient] = sender
    emit_to_user(
        "call_offer",
        {"from": sender, "offer": offer, "profile": public_profile(sender)},
        recipient,
    )


@socketio.on("call_answer")
def socket_call_answer(data):
    sender = current_user() or (data or {}).get("from") or ""
    recipient = ((data or {}).get("to") or "").strip()
    accepted = bool((data or {}).get("accepted"))
    answer = (data or {}).get("answer")
    if not sender or not recipient:
        return
    if pending_calls.get(sender) != recipient and active_calls.get(sender) != recipient:
        return
    pending_calls.pop(sender, None)
    if pending_calls.get(recipient) == sender:
        pending_calls.pop(recipient, None)
    if not accepted or not answer:
        emit_to_user("call_declined", {"from": sender}, recipient)
        return
    active_calls[sender] = recipient
    active_calls[recipient] = sender
    emit_to_user(
        "call_answer",
        {"from": sender, "answer": answer, "profile": public_profile(sender)},
        recipient,
    )


@socketio.on("call_ice")
def socket_call_ice(data):
    sender = current_user() or (data or {}).get("from") or ""
    recipient = ((data or {}).get("to") or "").strip()
    candidate = (data or {}).get("candidate")
    if not sender or not recipient or not candidate:
        return
    if active_calls.get(sender) == recipient or pending_calls.get(sender) == recipient or pending_calls.get(recipient) == sender:
        emit_to_user("call_ice", {"from": sender, "candidate": candidate}, recipient)


@socketio.on("call_end")
def socket_call_end(data):
    sender = current_user() or (data or {}).get("from") or ""
    peer = ((data or {}).get("to") or "").strip() or active_calls.get(sender) or pending_calls.get(sender) or ""
    if not sender or not peer:
        return
    pending_calls.pop(sender, None)
    if pending_calls.get(peer) == sender:
        pending_calls.pop(peer, None)
    active_calls.pop(sender, None)
    if active_calls.get(peer) == sender:
        active_calls.pop(peer, None)
    emit_to_user("call_end", {"from": sender}, peer)


@socketio.on("disconnect")
def socket_disconnect():
    username = online_users.pop(request.sid, None)
    if username:
        if username in user_sids:
            user_sids[username].discard(request.sid)
            if not user_sids[username]:
                user_sids.pop(username, None)
        if username not in user_sids:
            pending_peer, active_peer = clear_call_links(username)
            if active_peer:
                emit_to_user("call_end", {"from": username}, active_peer)
            elif pending_peer:
                emit_to_user("call_unavailable", {"peer": username}, pending_peer)
        emit("global_message", {"sender": "System", "text": f"{username} left chat.", "ts": ts_human(), "kind": "system"}, broadcast=True)
    emit("userlist", sorted(set(online_users.values())), broadcast=True)


def bootstrap_files() -> None:
    ensure_dirs()
    for path, default in [
        (USERS_FILE, {}),
        (VIDEOS_FILE, []),
        (GAMES_FILE, []),
        (MUSIC_FILE, []),
        (PASTES_FILE, []),
        (WIKI_FILE, []),
        (FORUMS_FILE, []),
        (CHAT_FILE, []),
        (NOTIFICATIONS_FILE, {}),
        (DOWNLOADS_FILE, []),
        (LIBRARY_FILE, {}),
    ]:
        if not path.exists():
            save_json(path, default)
    if not ADMINS_FILE.exists():
        ADMINS_FILE.write_text("", encoding="utf-8")


bootstrap_files()


if __name__ == "__main__":
    socketio.run(
        app,
        host=os.environ.get("LOCALNET_HOST_BIND", "0.0.0.0"),
        port=int(os.environ.get("LOCALNET_PORT", "2453")),
        debug=os.environ.get("LOCALNET_DEBUG", "1") == "1",
    )
