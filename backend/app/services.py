"""Shared query helpers: post serialization and comment threading."""

from collections import defaultdict

from sqlalchemy import func
from sqlalchemy.orm import Session

from . import schemas
from .models import Comment, Follow, Like, Post


def _author_snippet(user) -> schemas.AuthorSnippet:
    return schemas.AuthorSnippet(
        id=user.id,
        username=user.username,
        display_name=user.display_name,
        avatar_url=user.avatar_url,
    )


def posts_to_out(
    posts: list[Post], db: Session, viewer_id: int | None
) -> list[schemas.PostOut]:
    """Serialize posts with like/comment counts and liked_by_me, batched."""
    if not posts:
        return []
    ids = [p.id for p in posts]

    like_counts = dict(
        db.query(Like.post_id, func.count(Like.id))
        .filter(Like.post_id.in_(ids))
        .group_by(Like.post_id)
        .all()
    )
    comment_counts = dict(
        db.query(Comment.post_id, func.count(Comment.id))
        .filter(Comment.post_id.in_(ids))
        .group_by(Comment.post_id)
        .all()
    )
    liked_ids: set[int] = set()
    if viewer_id is not None:
        liked_ids = {
            pid
            for (pid,) in db.query(Like.post_id)
            .filter(Like.post_id.in_(ids), Like.user_id == viewer_id)
            .all()
        }

    out = []
    for post in posts:
        out.append(
            schemas.PostOut(
                id=post.id,
                image_url=post.image_url,
                caption=post.caption,
                created_at=post.created_at,
                author=_author_snippet(post.author),
                like_count=like_counts.get(post.id, 0),
                comment_count=comment_counts.get(post.id, 0),
                liked_by_me=post.id in liked_ids,
            )
        )
    return out


def comment_tree(
    comments: list[Comment],
) -> list[schemas.CommentOut]:
    """Build a threaded tree from a flat, chronologically ordered list."""
    nodes: dict[int, schemas.CommentOut] = {}
    roots: list[schemas.CommentOut] = []
    for c in comments:
        nodes[c.id] = schemas.CommentOut(
            id=c.id,
            body=c.body,
            created_at=c.created_at,
            author=_author_snippet(c.user),
            replies=[],
        )
    for c in comments:
        node = nodes[c.id]
        if c.parent_id and c.parent_id in nodes:
            nodes[c.parent_id].replies.append(node)
        else:
            roots.append(node)
    return roots


def profile_counts(db: Session, user_id: int) -> tuple[int, int, int]:
    """Return (post_count, follower_count, following_count) for a user."""
    post_count = (
        db.query(func.count(Post.id)).filter(Post.user_id == user_id).scalar()
        or 0
    )
    follower_count = (
        db.query(func.count(Follow.id))
        .filter(Follow.following_id == user_id)
        .scalar()
        or 0
    )
    following_count = (
        db.query(func.count(Follow.id))
        .filter(Follow.follower_id == user_id)
        .scalar()
        or 0
    )
    return post_count, follower_count, following_count


def follow_flags(
    db: Session, viewer_id: int | None, target_id: int
) -> tuple[bool, bool]:
    """(viewer follows target, target follows viewer)."""
    if viewer_id is None or viewer_id == target_id:
        return False, False
    viewer_follows = (
        db.query(Follow.id)
        .filter(
            Follow.follower_id == viewer_id,
            Follow.following_id == target_id,
        )
        .first()
        is not None
    )
    followed_by = (
        db.query(Follow.id)
        .filter(
            Follow.follower_id == target_id,
            Follow.following_id == viewer_id,
        )
        .first()
        is not None
    )
    return viewer_follows, followed_by
