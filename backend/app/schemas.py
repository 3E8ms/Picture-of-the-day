"""Pydantic v2 request/response schemas."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


# ---------- Auth ----------


class UserRegister(BaseModel):
    username: str = Field(min_length=3, max_length=30, pattern=r"^[a-zA-Z0-9_.]+$")
    email: EmailStr
    password: str = Field(min_length=8, max_length=72)
    display_name: str = Field(min_length=1, max_length=80)


class UserLogin(BaseModel):
    username: str
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    user_id: int


# ---------- Users ----------


class AuthorSnippet(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    display_name: str
    avatar_url: str | None


class UserProfile(AuthorSnippet):
    bio: str
    created_at: datetime
    post_count: int
    follower_count: int
    following_count: int
    is_following: bool = False  # does the viewer follow this user?
    is_followed_by: bool = False  # does this user follow the viewer?
    is_me: bool = False


class UserUpdate(BaseModel):
    display_name: str | None = Field(default=None, min_length=1, max_length=80)
    bio: str | None = Field(default=None, max_length=500)
    avatar_url: str | None = Field(default=None, max_length=512)


class FollowListItem(AuthorSnippet):
    is_following: bool = False  # does the viewer follow this user?
    is_followed_by: bool = False  # does this user follow the viewer?


# ---------- Posts ----------


class PostOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    image_url: str
    caption: str
    created_at: datetime
    author: AuthorSnippet
    like_count: int = 0
    comment_count: int = 0
    liked_by_me: bool = False


class PostCreateResponse(PostOut):
    pass


# ---------- Likes ----------


class LikeToggleOut(BaseModel):
    liked: bool
    like_count: int


# ---------- Comments ----------


class CommentCreate(BaseModel):
    body: str = Field(min_length=1, max_length=2000)
    parent_id: int | None = None


class CommentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    body: str
    created_at: datetime
    author: AuthorSnippet
    replies: list["CommentOut"] = []


CommentOut.model_rebuild()


# ---------- Pagination ----------


class PaginatedPosts(BaseModel):
    items: list[PostOut]
    total: int
    limit: int
    offset: int
