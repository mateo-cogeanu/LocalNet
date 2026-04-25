from __future__ import annotations

import base64
import hashlib
import hmac
import html
import json
import os
import secrets
import shutil
import time
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
    redirect,
    render_template,
    request,
    send_from_directory,
    session,
    url_for,
)
from flask_socketio import SocketIO, emit
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename


APP_ROOT = Path(__file__).resolve().parent
DATA_DIR = APP_ROOT / "data"
UPLOADS_DIR = APP_ROOT / "uploads"
STATIC_DIR = APP_ROOT / "static"
TEMPLATES_DIR = APP_ROOT / "templates"

USERS_FILE = DATA_DIR / "users.json"
VIDEOS_FILE = DATA_DIR / "videos.json"
GAMES_FILE = DATA_DIR / "games.json"
PASTES_FILE = DATA_DIR / "pastes.json"
WIKI_FILE = DATA_DIR / "wiki.json"
FORUMS_FILE = DATA_DIR / "forums.json"
CHAT_FILE = DATA_DIR / "chat.json"

VIDEO_DIR = UPLOADS_DIR / "videos"
THUMBS_DIR = UPLOADS_DIR / "thumbs"
IMAGES_DIR = UPLOADS_DIR / "images"
COVERS_DIR = UPLOADS_DIR / "covers"
GAMES_DIR = UPLOADS_DIR / "games"

ALLOWED_VIDEO_EXTS = {".mp4", ".webm", ".ogv", ".mov", ".m4v"}
ALLOWED_IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".gif", ".webp"}
ALLOWED_GAME_EXTS = {".zip", ".html", ".htm"}


def ensure_dirs() -> None:
    for path in [
        DATA_DIR,
        VIDEO_DIR,
        THUMBS_DIR,
        IMAGES_DIR,
        COVERS_DIR,
        GAMES_DIR,
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


def current_user() -> str | None:
    return session.get("user")


def login_required(fn):
    @wraps(fn)
    def wrapped(*args, **kwargs):
        if not current_user():
            return redirect(url_for("login", next=request.path))
        return fn(*args, **kwargs)

    return wrapped


def get_users() -> dict[str, dict[str, Any]]:
    return load_json(USERS_FILE, {})


def save_users(data: dict[str, dict[str, Any]]) -> None:
    save_json(USERS_FILE, data)


def get_items(path: Path) -> list[dict[str, Any]]:
    return load_json(path, [])


def save_items(path: Path, items: list[dict[str, Any]]) -> None:
    save_json(path, items)


def make_id(prefix: str) -> str:
    return f"{prefix}_{secrets.token_hex(6)}"


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
        return cls(load_json(FORUMS_FILE, []))

    def save(self) -> None:
        save_json(FORUMS_FILE, self.threads)


app = Flask(__name__, template_folder=str(TEMPLATES_DIR), static_folder=str(STATIC_DIR))
app.config["SECRET_KEY"] = os.environ.get("LOCALNET_SECRET", secrets.token_hex(32))
app.config["MAX_CONTENT_LENGTH"] = 512 * 1024 * 1024
socketio = SocketIO(app, async_mode="threading")

online_users: dict[str, str] = {}


@app.context_processor
def inject_globals():
    return {"user": current_user(), "request": request}


@app.route("/uploads/<path:subpath>")
def uploads(subpath: str):
    return send_from_directory(UPLOADS_DIR, subpath)


@app.route("/login", methods=["GET", "POST"])
def login():
    if current_user():
        return redirect(url_for("home"))

    error = None
    username = ""
    otp_required = False
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        otp = request.form.get("otp", "").strip()
        users = get_users()

        if not username or not password:
            error = "Username and password are required."
        elif username not in users:
            users[username] = {
                "password_hash": generate_password_hash(password),
                "created_at": now_utc().isoformat(),
                "two_factor_enabled": False,
                "two_factor_secret": "",
            }
            save_users(users)
            session["user"] = username
            return redirect(request.args.get("next") or url_for("home"))
        else:
            account = users[username]
            if not check_password_hash(account["password_hash"], password):
                error = "Incorrect password."
            elif account.get("two_factor_enabled"):
                otp_required = True
                if not verify_totp(account.get("two_factor_secret", ""), otp):
                    error = "Two-factor code required." if not otp else "Invalid two-factor code."
                else:
                    session["user"] = username
                    return redirect(request.args.get("next") or url_for("home"))
            else:
                session["user"] = username
                return redirect(request.args.get("next") or url_for("home"))

    return render_template("login.html", error=error, username=username, otp_required=otp_required)


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/")
@login_required
def home():
    forum_threads = ForumStore.load().threads
    videos = sorted(get_items(VIDEOS_FILE), key=lambda v: v.get("created_at", ""), reverse=True)[:4]
    games = sorted(get_items(GAMES_FILE), key=lambda g: g.get("created_at", ""), reverse=True)[:4]
    threads = sorted(forum_threads, key=lambda t: t.get("updated_at", ""), reverse=True)[:5]
    pastes = prune_expired_pastes()[:5]
    wiki = sorted(get_items(WIKI_FILE), key=lambda a: a.get("updated_at", ""), reverse=True)[:5]
    counts = {
        "videos": len(get_items(VIDEOS_FILE)),
        "games": len(get_items(GAMES_FILE)),
        "threads": len(forum_threads),
        "articles": len(get_items(WIKI_FILE)),
        "pastes": len(prune_expired_pastes()),
    }
    return render_template(
        "home.html",
        videos=videos,
        games=games,
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
        if action == "setup_2fa":
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

    pending = account.get("two_factor_pending")
    if pending and not secret:
        secret = pending
        provisioning_uri = otpauth_uri(current_user(), pending)

    return render_template(
        "settings.html",
        message=message,
        error=error,
        secret=secret,
        provisioning_uri=provisioning_uri,
        two_factor_enabled=bool(account.get("two_factor_enabled")),
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
        return redirect(url_for("tube_watch", video_id=video_id))

    related = [v for v in videos if v.get("id") != video_id][:8]
    return render_template("tube_watch.html", v=video, related=related)


@app.route("/tube/vote/<video_id>")
@login_required
def tube_vote(video_id: str):
    videos, video = find_by_id(VIDEOS_FILE, video_id)
    if video:
        voters = video.setdefault("voters", {})
        if voters.get(current_user()):
            voters.pop(current_user(), None)
            video["votes"] = max(0, int(video.get("votes", 0)) - 1)
        else:
            voters[current_user()] = True
            video["votes"] = int(video.get("votes", 0)) + 1
        save_items(VIDEOS_FILE, videos)
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
        if voters.get(current_user()):
            voters.pop(current_user(), None)
            game["votes"] = max(0, int(game.get("votes", 0)) - 1)
        else:
            voters[current_user()] = True
            game["votes"] = int(game.get("votes", 0)) + 1
        save_items(GAMES_FILE, items)
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
                idx = articles.index(next(a for a in articles if a.get("slug") == slug))
                articles[idx] = payload
            save_items(WIKI_FILE, articles)
            return redirect(url_for("wiki_article", slug=target_slug))

    return render_template("wiki_edit.html", art=article)


@app.route("/forums", methods=["GET", "POST"])
@login_required
def forums():
    store = ForumStore.load()
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        body = request.form.get("body", "").strip()
        if title and body:
            store.threads.append(
                {
                    "id": make_id("thread"),
                    "title": title,
                    "body": body,
                    "author": current_user(),
                    "votes": 0,
                    "voters": {},
                    "comments": [],
                    "created_at": now_utc().isoformat(),
                    "updated_at": now_utc().isoformat(),
                    "ts": ts_human(),
                }
            )
            store.save()
            return redirect(url_for("forums"))
    store.threads.sort(key=lambda t: (t.get("updated_at", ""), t.get("votes", 0)), reverse=True)
    return render_template("forums.html", threads=store.threads)


@app.route("/forums/vote/<thread_id>")
@login_required
def forums_vote(thread_id: str):
    store = ForumStore.load()
    for thread in store.threads:
        if thread.get("id") == thread_id:
            voters = thread.setdefault("voters", {})
            if voters.get(current_user()):
                voters.pop(current_user(), None)
                thread["votes"] = max(0, int(thread.get("votes", 0)) - 1)
            else:
                voters[current_user()] = True
                thread["votes"] = int(thread.get("votes", 0)) + 1
            thread["updated_at"] = now_utc().isoformat()
            store.save()
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
    for thread in store.threads:
        if thread.get("id") == thread_id:
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
            break
    return redirect(url_for("forums"))


@app.route("/chat")
@login_required
def chat():
    return render_template("chat.html")


@socketio.on("join")
def socket_join(data):
    username = (data or {}).get("username") or current_user() or "Guest"
    online_users[request.sid] = username
    emit("message", {"sender": "System", "text": f"{username} joined chat.", "ts": ts_human()}, broadcast=True)
    emit("userlist", sorted(set(online_users.values())), broadcast=True)
    for msg in load_json(CHAT_FILE, [])[-50:]:
        emit("message", msg)


@socketio.on("send_message")
def socket_message(data):
    sender = current_user() or (data or {}).get("sender") or "Guest"
    text = (data or {}).get("text", "").strip()
    if not text:
        return
    payload = {"sender": sender, "text": text[:2000], "ts": ts_human()}
    history = load_json(CHAT_FILE, [])
    history.append(payload)
    history = history[-200:]
    save_json(CHAT_FILE, history)
    emit("message", payload, broadcast=True)


@socketio.on("disconnect")
def socket_disconnect():
    username = online_users.pop(request.sid, None)
    if username:
        emit("message", {"sender": "System", "text": f"{username} left chat.", "ts": ts_human()}, broadcast=True)
    emit("userlist", sorted(set(online_users.values())), broadcast=True)


def bootstrap_files() -> None:
    ensure_dirs()
    for path, default in [
        (USERS_FILE, {}),
        (VIDEOS_FILE, []),
        (GAMES_FILE, []),
        (PASTES_FILE, []),
        (WIKI_FILE, []),
        (FORUMS_FILE, []),
        (CHAT_FILE, []),
    ]:
        if not path.exists():
            save_json(path, default)


bootstrap_files()


if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=2453, debug=True)
