"""Idempotent demo seed: users, posts, follows, likes, comments."""

from .database import SessionLocal, init_db
from .models import Comment, Follow, Like, Post, User
from .security import hash_password

PASSWORD = "Password123!"

USERS = [
    {
        "username": "alice",
        "email": "alice@example.com",
        "display_name": "Alice Chen",
        "bio": "Chasing golden hour, one photo a day.",
        "avatar_url": "https://i.pravatar.cc/150?img=47",
    },
    {
        "username": "bob",
        "email": "bob@example.com",
        "display_name": "Bob Rivera",
        "bio": "Street photography & espresso.",
        "avatar_url": "https://i.pravatar.cc/150?img=12",
    },
    {
        "username": "carol",
        "email": "carol@example.com",
        "display_name": "Carol Kim",
        "bio": "Film, mountains, and my dog.",
        "avatar_url": "https://i.pravatar.cc/150?img=32",
    },
    {
        "username": "admin",
        "email": "admin@example.com",
        "display_name": "Site Admin",
        "bio": "Keeping the lights on.",
        "avatar_url": None,
    },
]

# picsum seeds give stable placeholder photos without binary assets.
POSTS = [
    ("alice", "potd-alice-1", "Morning fog over the lake. My picture of the day."),
    ("alice", "potd-alice-2", "City lights never sleep."),
    ("bob", "potd-bob-1", "Found this alley on my walk home."),
    ("bob", "potd-bob-2", "Espresso first, photos second."),
    ("bob", "potd-bob-3", "Rainy day reflections."),
    ("carol", "potd-carol-1", "Summit views with Biscuit."),
    ("carol", "potd-carol-2", "Shot on film, no edits."),
]


def _pic(seed: str) -> str:
    return f"https://picsum.photos/seed/{seed}/800/800"


def run() -> None:
    init_db()
    db = SessionLocal()
    try:
        if db.query(User).first():
            print("Seed: users already exist, skipping.")
            return

        users: dict[str, User] = {}
        for i, u in enumerate(USERS):
            user = User(
                username=u["username"],
                email=u["email"],
                hashed_password=hash_password(PASSWORD),
                display_name=u["display_name"],
                bio=u["bio"],
                avatar_url=u["avatar_url"],
                is_admin=(u["username"] == "admin"),
            )
            db.add(user)
            users[u["username"]] = user
        db.flush()

        posts: list[Post] = []
        for username, seed, caption in POSTS:
            post = Post(
                user_id=users[username].id, image_url=_pic(seed), caption=caption
            )
            db.add(post)
            posts.append(post)
        db.flush()

        # Follows: alice <-> bob mutual, carol follows alice, admin follows all.
        pairs = [
            ("alice", "bob"),
            ("bob", "alice"),
            ("carol", "alice"),
            ("admin", "alice"),
            ("admin", "bob"),
            ("admin", "carol"),
        ]
        for follower, following in pairs:
            db.add(
                Follow(
                    follower_id=users[follower].id,
                    following_id=users[following].id,
                )
            )

        # Likes: bob & carol like alice's first post, alice likes bob's.
        db.add(Like(user_id=users["bob"].id, post_id=posts[0].id))
        db.add(Like(user_id=users["carol"].id, post_id=posts[0].id))
        db.add(Like(user_id=users["alice"].id, post_id=posts[2].id))

        # Comments incl. a nested reply thread on alice's first post.
        c1 = Comment(
            post_id=posts[0].id,
            user_id=users["bob"].id,
            body="That fog looks unreal. What time was this?",
        )
        db.add(c1)
        db.flush()
        db.add(
            Comment(
                post_id=posts[0].id,
                user_id=users["alice"].id,
                parent_id=c1.id,
                body="Around 6:40am — worth the early alarm!",
            )
        )
        db.add(
            Comment(
                post_id=posts[2].id,
                user_id=users["carol"].id,
                body="Love the leading lines here.",
            )
        )

        db.commit()
        print("Seed: created demo users, posts, follows, likes, comments.")
    finally:
        db.close()


if __name__ == "__main__":
    run()
