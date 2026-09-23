# 📷 Picture of the Day

An Instagram-like photo sharing web app: users register, post one photo a day
(or as many as they like), like and comment on each other's pictures, reply to
comments, and follow each other.

**Stack:** FastAPI + SQLAlchemy 2.0 + PostgreSQL · React 18 + TypeScript (Vite)
· Docker Compose.

## Features

- **Auth** — register / login / logout with JWT (OAuth2 password flow).
- **Posts** — publish a photo + caption; images validated (JPEG/PNG/GIF/WebP,
  ≤ 5 MB) and stored on disk under `uploads/`, served by the API.
- **Feed** — chronological home feed of people you follow + yourself;
  **Explore** page with every post.
- **Likes** — idempotent like/unlike toggle with live counts.
- **Comments** — threaded comments with one level of nested replies.
- **Profiles** — bio, post grid, post/follower/following counts, follow button,
  followers/following lists with mutual-follow badges.
- **Follow system** — follow/unfollow (no self-follows), idempotent endpoints.

## Architecture

```
picture-of-the-day/
├── backend/            # FastAPI app
│   └── app/
│       ├── main.py         # app factory, CORS, /uploads static mount
│       ├── models.py       # User, Post, Like, Comment (self-FK), Follow
│       ├── schemas.py      # Pydantic v2 request/response models
│       ├── routers/        # auth.py, posts.py, users.py
│       ├── services.py     # batched post serialization, comment threading
│       ├── storage.py      # upload validation + disk persistence
│       └── seed.py         # idempotent demo data
├── frontend/           # React + TypeScript (Vite)
│   └── src/
│       ├── api/client.ts       # axios + JWT interceptor, shared types
│       ├── auth/AuthContext.tsx # login/register/logout, session restore
│       ├── components/         # PostCard, CommentSection, FollowButton…
│       └── pages/              # Feed, Explore, PostDetail, Upload, Profile…
└── docker-compose.yml  # postgres + api (uploads volume) + frontend (nginx)
```

## Quickstart

```bash
cd picture-of-the-day
docker compose up --build
```

- App: http://localhost:3000
- API docs (Swagger): http://localhost:8000/docs

The API seeds demo data on first startup (`seed_on_startup=true`).

### Demo accounts (password `Password123!`)

| Username | Email               | Notes                          |
|----------|---------------------|--------------------------------|
| alice    | alice@example.com   | follows bob; mutual with bob   |
| bob      | bob@example.com     | 3 posts, street photography    |
| carol    | carol@example.com   | follows alice                  |
| admin    | admin@example.com   | follows everyone, can delete any post |

### Local development (without Docker)

Backend:

```bash
cd backend
cp .env.example .env          # point database_url at your Postgres
python -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/python -m app.seed  # optional demo data
.venv/bin/uvicorn app.main:app --reload
```

Frontend:

```bash
cd frontend
npm install
npm run dev                   # http://localhost:5173 (proxies to :8000 via VITE_API_URL default)
```

## API summary

| Method & path                        | Auth | Description                              |
|--------------------------------------|------|------------------------------------------|
| `POST /auth/register`                | –    | Create account → JWT                     |
| `POST /auth/login`                   | –    | OAuth2 password form → JWT               |
| `GET /auth/me`                       | ✓    | Current user                             |
| `GET /feed?limit&offset`             | ✓    | Posts from followed users + self         |
| `GET /posts?limit&offset`            | opt  | Explore: all posts, newest first         |
| `POST /posts` (multipart)            | ✓    | Publish photo + caption                  |
| `GET /posts/{id}` · `DELETE /posts/{id}` | opt/✓ | Post detail / delete (owner or admin) |
| `POST /posts/{id}/like`              | ✓    | Toggle like → `{liked, like_count}`      |
| `GET /posts/{id}/comments`           | opt  | Threaded comment tree                    |
| `POST /posts/{id}/comments`          | ✓    | Comment or reply (`parent_id`)           |
| `GET /users/{username}`              | opt  | Profile + counts + follow flags          |
| `PATCH /users/me`                    | ✓    | Update display name / bio                |
| `GET /users/{username}/posts`        | opt  | User's posts (for the grid)              |
| `POST /users/{username}/follow`      | ✓    | Follow (idempotent, no self-follow)      |
| `DELETE /users/{username}/follow`    | ✓    | Unfollow (idempotent)                    |
| `GET /users/{username}/followers` / `/following` | opt | Follow lists with mutual flags |

## Tests

```bash
cd backend
.venv/bin/python -m pytest tests/ -q
```

12 tests cover register/login, upload validation, like-toggle idempotency,
comment threading (incl. depth-limit rejection), follow/unfollow/self-follow
rejection, mutual-follow flags, feed scoping, and auth enforcement. They run
against a throwaway SQLite file — the SQL is portable (no Postgres-specific
features).

## Resume bullets (copy-paste)

- Built "Picture of the Day", an Instagram-like full-stack app (FastAPI +
  React/TypeScript + PostgreSQL) with JWT auth, image uploads, likes, threaded
  comments, and a follow graph.
- Designed a normalized schema (self-referencing comments/follows with DB-level
  uniqueness + check constraints) and batched feed serialization to avoid N+1
  queries.
- Implemented idempotent like/follow toggles, optimistic UI updates, and a
  seeded demo dataset; 12 passing API tests, clean `tsc` + production build.

## Notes / trade-offs

- Uploads are stored on local disk (Docker volume `uploads`); for production,
  swap `storage.py` for S3/object storage.
- Auth is stateless JWT in `localStorage` — fine for a demo; a production app
  would use httpOnly cookies + refresh tokens.
- Comment replies are limited to one level deep (enforced by the API); the
  frontend renders the tree recursively so the limit can be raised later.
- Tests run against SQLite while production uses PostgreSQL; SQL is kept
  portable (no PG-specific features) but a real Postgres integration run is
  still worthwhile before demoing.
