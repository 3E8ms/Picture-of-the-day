"""API tests for Picture of the Day (SQLite-backed, no external services)."""

import io
import os
import tempfile
from pathlib import Path

_tmpdir = tempfile.mkdtemp(prefix="potd-test-")
# Must be set before importing app modules (engine is built at import time).
os.environ["DATABASE_URL"] = f"sqlite:///{_tmpdir}/test.db"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402

from app import storage  # noqa: E402
from app.database import Base, get_db  # noqa: E402
from app.main import create_app  # noqa: E402

# 1x1 transparent PNG.
TINY_PNG = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
    b"\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00\x01"
    b"\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
)

_engine = create_engine(
    f"sqlite:///{_tmpdir}/test.db", connect_args={"check_same_thread": False}
)
TestingSession = sessionmaker(autocommit=False, autoflush=False, bind=_engine)

app = create_app()


def _override_db():
    db = TestingSession()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = _override_db
client = TestClient(app)


@pytest.fixture(autouse=True)
def _fresh_db_and_uploads(tmp_path, monkeypatch):
    Base.metadata.drop_all(bind=_engine)
    Base.metadata.create_all(bind=_engine)
    upload_dir = tmp_path / "uploads"
    monkeypatch.setattr(storage, "UPLOAD_DIR", upload_dir)
    yield


def _register(username: str, email: str | None = None) -> dict:
    email = email or f"{username}@example.com"
    r = client.post(
        "/auth/register",
        json={
            "username": username,
            "email": email,
            "password": "Password123!",
            "display_name": username.title(),
        },
    )
    assert r.status_code == 201, r.text
    return r.json()


def _auth(username: str) -> dict:
    token = _register(username)["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _login(username: str) -> dict:
    r = client.post(
        "/auth/login", data={"username": username, "password": "Password123!"}
    )
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def _post_image(headers: dict, caption: str = "hello") -> dict:
    r = client.post(
        "/posts",
        headers=headers,
        files={"image": ("pic.png", io.BytesIO(TINY_PNG), "image/png")},
        data={"caption": caption},
    )
    assert r.status_code == 201, r.text
    return r.json()


# ---------- Auth ----------


def test_register_and_login_flow():
    _register("alice")
    headers = _login("alice")
    r = client.get("/auth/me", headers=headers)
    assert r.status_code == 200
    assert r.json()["username"] == "alice"


def test_register_duplicate_username_conflict():
    _register("bob")
    r = client.post(
        "/auth/register",
        json={
            "username": "bob",
            "email": "other@example.com",
            "password": "Password123!",
            "display_name": "Bob",
        },
    )
    assert r.status_code == 409


def test_login_wrong_password_unauthorized():
    _register("carol")
    r = client.post(
        "/auth/login", data={"username": "carol", "password": "WrongPass1!"}
    )
    assert r.status_code == 401


def test_protected_route_requires_auth():
    r = client.post(
        "/posts",
        files={"image": ("pic.png", io.BytesIO(TINY_PNG), "image/png")},
        data={"caption": "x"},
    )
    assert r.status_code == 401


# ---------- Posts / uploads ----------


def test_create_post_uploads_image():
    headers = _auth("dave")
    post = _post_image(headers, caption="my first pic")
    assert post["image_url"].startswith("/uploads/")
    assert post["image_url"].endswith(".png")
    assert post["caption"] == "my first pic"
    assert post["like_count"] == 0
    # File actually landed on disk.
    name = Path(post["image_url"]).name
    assert (storage.UPLOAD_DIR / name).exists()


def test_create_post_rejects_non_image():
    headers = _auth("erin")
    r = client.post(
        "/posts",
        headers=headers,
        files={"image": ("evil.txt", io.BytesIO(b"not an image"), "text/plain")},
        data={"caption": "x"},
    )
    assert r.status_code == 400


def test_delete_own_post_and_forbidden_for_others():
    alice = _auth("alice")
    bob = _auth("bob")
    post = _post_image(alice)
    r = client.delete(f"/posts/{post['id']}", headers=bob)
    assert r.status_code == 403
    r = client.delete(f"/posts/{post['id']}", headers=alice)
    assert r.status_code == 204
    assert client.get(f"/posts/{post['id']}").status_code == 404


# ---------- Likes ----------


def test_like_toggle_is_idempotent():
    alice = _auth("alice")
    bob = _auth("bob")
    post = _post_image(alice)

    r = client.post(f"/posts/{post['id']}/like", headers=bob)
    assert r.json() == {"liked": True, "like_count": 1}

    r = client.post(f"/posts/{post['id']}/like", headers=bob)
    assert r.json() == {"liked": False, "like_count": 0}

    r = client.post(f"/posts/{post['id']}/like", headers=bob)
    assert r.json() == {"liked": True, "like_count": 1}

    # Detail reflects liked_by_me for the liker only.
    detail = client.get(f"/posts/{post['id']}", headers=bob).json()
    assert detail["liked_by_me"] is True
    assert detail["like_count"] == 1
    detail = client.get(f"/posts/{post['id']}", headers=alice).json()
    assert detail["liked_by_me"] is False


# ---------- Comments / threading ----------


def test_comment_reply_threading():
    alice = _auth("alice")
    bob = _auth("bob")
    post = _post_image(alice)

    c1 = client.post(
        f"/posts/{post['id']}/comments",
        headers=bob,
        json={"body": "Nice shot!"},
    ).json()
    reply = client.post(
        f"/posts/{post['id']}/comments",
        headers=alice,
        json={"body": "Thanks!", "parent_id": c1["id"]},
    )
    assert reply.status_code == 201
    # Third level is rejected.
    r = client.post(
        f"/posts/{post['id']}/comments",
        headers=bob,
        json={"body": "too deep", "parent_id": reply.json()["id"]},
    )
    assert r.status_code == 400

    tree = client.get(f"/posts/{post['id']}/comments").json()
    assert len(tree) == 1
    assert tree[0]["body"] == "Nice shot!"
    assert len(tree[0]["replies"]) == 1
    assert tree[0]["replies"][0]["body"] == "Thanks!"
    assert tree[0]["replies"][0]["author"]["username"] == "alice"

    # comment_count on the post includes replies.
    detail = client.get(f"/posts/{post['id']}", headers=alice).json()
    assert detail["comment_count"] == 2


# ---------- Follow system ----------


def test_follow_unfollow_and_self_follow_rejected():
    alice = _auth("alice")
    bob = _auth("bob")

    r = client.post("/users/bob/follow", headers=alice)
    assert r.status_code == 201
    # Idempotent second follow.
    r = client.post("/users/bob/follow", headers=alice)
    assert r.status_code == 201

    r = client.post("/users/alice/follow", headers=alice)
    assert r.status_code == 400

    profile = client.get("/users/bob", headers=alice).json()
    assert profile["follower_count"] == 1
    assert profile["is_following"] is True
    assert profile["is_followed_by"] is False

    followers = client.get("/users/bob/followers", headers=alice).json()
    assert [u["username"] for u in followers] == ["alice"]

    r = client.delete("/users/bob/follow", headers=alice)
    assert r.status_code == 200
    assert r.json() == {"following": False}
    profile = client.get("/users/bob", headers=alice).json()
    assert profile["follower_count"] == 0
    assert profile["is_following"] is False


def test_mutual_follow_indication():
    alice = _auth("alice")
    bob = _auth("bob")
    client.post("/users/bob/follow", headers=alice)
    client.post("/users/alice/follow", headers=bob)

    profile = client.get("/users/bob", headers=alice).json()
    assert profile["is_following"] is True
    assert profile["is_followed_by"] is True  # mutual

    item = client.get("/users/bob/followers", headers=alice).json()[0]
    assert item["username"] == "alice"
    # follow flags are relative to the viewer; a self entry is neutral.
    assert item["is_following"] is False
    assert item["is_followed_by"] is False


def test_feed_only_shows_followed_and_self():
    alice = _auth("alice")
    bob = _auth("bob")
    carol = _auth("carol")

    bob_post = _post_image(bob, caption="bob pic")
    _post_image(carol, caption="carol pic")
    alice_post = _post_image(alice, caption="alice pic")

    client.post("/users/bob/follow", headers=alice)

    feed = client.get("/feed", headers=alice).json()
    captions = [p["caption"] for p in feed["items"]]
    assert feed["total"] == 2
    assert "bob pic" in captions
    assert "alice pic" in captions
    assert "carol pic" not in captions
    # Newest first.
    assert feed["items"][0]["id"] == alice_post["id"]

    # Explore shows everything.
    explore = client.get("/posts").json()
    assert explore["total"] == 3

    # bob's profile lists his post.
    mine = client.get("/users/bob/posts", headers=alice).json()
    assert mine["total"] == 1
    assert mine["items"][0]["id"] == bob_post["id"]
    assert mine["items"][0]["author"]["username"] == "bob"
