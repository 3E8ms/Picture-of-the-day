"""Users: profiles, follow system."""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from .. import schemas
from ..database import get_db
from ..deps import get_current_user, get_optional_user
from ..models import Follow, Post, User
from ..services import _author_snippet, follow_flags, posts_to_out, profile_counts

router = APIRouter(tags=["users"])

MAX_LIMIT = 50


def _get_user_or_404(username: str, db: Session) -> User:
    user = db.query(User).filter(User.username == username).first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found."
        )
    return user


def _profile_out(
    target: User, db: Session, viewer: User | None
) -> schemas.UserProfile:
    post_count, follower_count, following_count = profile_counts(db, target.id)
    viewer_id = viewer.id if viewer else None
    is_following, is_followed_by = follow_flags(db, viewer_id, target.id)
    return schemas.UserProfile(
        id=target.id,
        username=target.username,
        display_name=target.display_name,
        avatar_url=target.avatar_url,
        bio=target.bio,
        created_at=target.created_at,
        post_count=post_count,
        follower_count=follower_count,
        following_count=following_count,
        is_following=is_following,
        is_followed_by=is_followed_by,
        is_me=viewer_id == target.id,
    )


@router.get("/users/me", response_model=schemas.UserProfile)
def my_profile(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return _profile_out(user, db, user)


@router.patch("/users/me", response_model=schemas.UserProfile)
def update_me(
    payload: schemas.UserUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    data = payload.model_dump(exclude_unset=True)
    for key, value in data.items():
        setattr(user, key, value)
    db.commit()
    db.refresh(user)
    return _profile_out(user, db, user)


@router.get("/users/{username}", response_model=schemas.UserProfile)
def user_profile(
    username: str,
    db: Session = Depends(get_db),
    viewer: User | None = Depends(get_optional_user),
):
    target = _get_user_or_404(username, db)
    return _profile_out(target, db, viewer)


@router.get("/users/{username}/posts", response_model=schemas.PaginatedPosts)
def user_posts(
    username: str,
    limit: int = Query(24, ge=1, le=MAX_LIMIT),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    viewer: User | None = Depends(get_optional_user),
):
    target = _get_user_or_404(username, db)
    query = (
        db.query(Post)
        .options(joinedload(Post.author))
        .filter(Post.user_id == target.id)
        .order_by(Post.created_at.desc(), Post.id.desc())
    )
    total = query.count()
    items = query.offset(offset).limit(limit).all()
    viewer_id = viewer.id if viewer else None
    return schemas.PaginatedPosts(
        items=posts_to_out(items, db, viewer_id),
        total=total,
        limit=limit,
        offset=offset,
    )


@router.post(
    "/users/{username}/follow", status_code=status.HTTP_201_CREATED
)
def follow_user(
    username: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    target = _get_user_or_404(username, db)
    if target.id == user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot follow yourself.",
        )
    if (
        db.query(Follow)
        .filter(
            Follow.follower_id == user.id, Follow.following_id == target.id
        )
        .first()
    ):
        return {"following": True}  # idempotent
    db.add(Follow(follower_id=user.id, following_id=target.id))
    try:
        db.commit()
    except IntegrityError:
        db.rollback()  # lost a race; treat as already following
    return {"following": True}


@router.delete("/users/{username}/follow")
def unfollow_user(
    username: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    target = _get_user_or_404(username, db)
    rel = (
        db.query(Follow)
        .filter(
            Follow.follower_id == user.id, Follow.following_id == target.id
        )
        .first()
    )
    if rel:
        db.delete(rel)
        db.commit()
    return {"following": False}  # idempotent


def _follow_list(
    user_ids: list[int], db: Session, viewer_id: int | None
) -> list[schemas.FollowListItem]:
    if not user_ids:
        return []
    users = db.query(User).filter(User.id.in_(user_ids)).all()
    by_id = {u.id: u for u in users}
    items = []
    for uid in user_ids:  # preserve the requested order
        u = by_id.get(uid)
        if u is None:
            continue
        is_following, is_followed_by = follow_flags(db, viewer_id, uid)
        items.append(
            schemas.FollowListItem(
                **_author_snippet(u).model_dump(),
                is_following=is_following,
                is_followed_by=is_followed_by,
            )
        )
    return items


@router.get(
    "/users/{username}/followers", response_model=list[schemas.FollowListItem]
)
def followers(
    username: str,
    db: Session = Depends(get_db),
    viewer: User | None = Depends(get_optional_user),
):
    target = _get_user_or_404(username, db)
    ids = [
        fid
        for (fid,) in db.query(Follow.follower_id)
        .filter(Follow.following_id == target.id)
        .order_by(Follow.created_at.desc())
        .all()
    ]
    viewer_id = viewer.id if viewer else None
    return _follow_list(ids, db, viewer_id)


@router.get(
    "/users/{username}/following", response_model=list[schemas.FollowListItem]
)
def following(
    username: str,
    db: Session = Depends(get_db),
    viewer: User | None = Depends(get_optional_user),
):
    target = _get_user_or_404(username, db)
    ids = [
        fid
        for (fid,) in db.query(Follow.following_id)
        .filter(Follow.follower_id == target.id)
        .order_by(Follow.created_at.desc())
        .all()
    ]
    viewer_id = viewer.id if viewer else None
    return _follow_list(ids, db, viewer_id)
