"""Posts: upload, feed, explore, likes, comments."""

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    UploadFile,
    status,
)
from sqlalchemy.orm import Session, joinedload

from .. import schemas, storage
from ..database import get_db
from ..deps import get_current_user, get_optional_user
from ..models import Comment, Follow, Like, Post, User
from ..services import comment_tree, posts_to_out

router = APIRouter(tags=["posts"])

MAX_LIMIT = 50


def _get_post_or_404(post_id: int, db: Session) -> Post:
    post = (
        db.query(Post)
        .options(joinedload(Post.author))
        .filter(Post.id == post_id)
        .first()
    )
    if post is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Post not found."
        )
    return post


def _paginate(query, limit: int, offset: int):
    total = query.count()
    items = query.offset(offset).limit(limit).all()
    return items, total


@router.post(
    "/posts",
    response_model=schemas.PostOut,
    status_code=status.HTTP_201_CREATED,
)
def create_post(
    image: UploadFile = File(...),
    caption: str = Form(default="", max_length=2000),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    image_url = storage.save_upload(image)
    post = Post(user_id=user.id, image_url=image_url, caption=caption)
    db.add(post)
    db.commit()
    db.refresh(post)
    # author is already loaded via relationship on the fresh instance
    db.refresh(post, attribute_names=["author"])
    return posts_to_out([post], db, user.id)[0]


@router.get("/posts", response_model=schemas.PaginatedPosts)
def explore_posts(
    limit: int = Query(20, ge=1, le=MAX_LIMIT),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    viewer: User | None = Depends(get_optional_user),
):
    """Explore: every post on the platform, newest first."""
    query = (
        db.query(Post)
        .options(joinedload(Post.author))
        .order_by(Post.created_at.desc(), Post.id.desc())
    )
    items, total = _paginate(query, limit, offset)
    viewer_id = viewer.id if viewer else None
    return schemas.PaginatedPosts(
        items=posts_to_out(items, db, viewer_id),
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/feed", response_model=schemas.PaginatedPosts)
def home_feed(
    limit: int = Query(20, ge=1, le=MAX_LIMIT),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Posts from people you follow plus your own, newest first."""
    followed_ids = [
        fid
        for (fid,) in db.query(Follow.following_id)
        .filter(Follow.follower_id == user.id)
        .all()
    ]
    author_ids = followed_ids + [user.id]
    query = (
        db.query(Post)
        .options(joinedload(Post.author))
        .filter(Post.user_id.in_(author_ids))
        .order_by(Post.created_at.desc(), Post.id.desc())
    )
    items, total = _paginate(query, limit, offset)
    return schemas.PaginatedPosts(
        items=posts_to_out(items, db, user.id),
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/posts/{post_id}", response_model=schemas.PostOut)
def get_post(
    post_id: int,
    db: Session = Depends(get_db),
    viewer: User | None = Depends(get_optional_user),
):
    post = _get_post_or_404(post_id, db)
    viewer_id = viewer.id if viewer else None
    return posts_to_out([post], db, viewer_id)[0]


@router.delete("/posts/{post_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_post(
    post_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    post = _get_post_or_404(post_id, db)
    if post.user_id != user.id and not user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only delete your own posts.",
        )
    image_url = post.image_url
    db.delete(post)
    db.commit()
    storage.delete_upload(image_url)


@router.post("/posts/{post_id}/like", response_model=schemas.LikeToggleOut)
def toggle_like(
    post_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    _get_post_or_404(post_id, db)
    existing = (
        db.query(Like)
        .filter(Like.post_id == post_id, Like.user_id == user.id)
        .first()
    )
    if existing:
        db.delete(existing)
        liked = False
    else:
        db.add(Like(post_id=post_id, user_id=user.id))
        liked = True
    db.commit()
    like_count = (
        db.query(Like).filter(Like.post_id == post_id).count()
    )
    return schemas.LikeToggleOut(liked=liked, like_count=like_count)


@router.get("/posts/{post_id}/comments", response_model=list[schemas.CommentOut])
def list_comments(
    post_id: int,
    db: Session = Depends(get_db),
    viewer: User | None = Depends(get_optional_user),  # noqa: ARG001
):
    _get_post_or_404(post_id, db)
    comments = (
        db.query(Comment)
        .options(joinedload(Comment.user))
        .filter(Comment.post_id == post_id)
        .order_by(Comment.created_at.asc(), Comment.id.asc())
        .all()
    )
    return comment_tree(comments)


@router.post(
    "/posts/{post_id}/comments",
    response_model=schemas.CommentOut,
    status_code=status.HTTP_201_CREATED,
)
def create_comment(
    post_id: int,
    payload: schemas.CommentCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    _get_post_or_404(post_id, db)
    parent = None
    if payload.parent_id is not None:
        parent = (
            db.query(Comment)
            .filter(
                Comment.id == payload.parent_id,
                Comment.post_id == post_id,
            )
            .first()
        )
        if parent is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Parent comment not found on this post.",
            )
        if parent.parent_id is not None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Replies are limited to one level deep.",
            )
    comment = Comment(
        post_id=post_id,
        user_id=user.id,
        parent_id=payload.parent_id,
        body=payload.body.strip(),
    )
    db.add(comment)
    db.commit()
    db.refresh(comment)
    db.refresh(comment, attribute_names=["user"])
    return comment_tree([comment])[0]
