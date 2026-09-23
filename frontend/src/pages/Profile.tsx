import { useCallback, useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import {
  api,
  imageSrc,
  type FollowItem,
  type PaginatedPosts,
  type Post,
  type Profile as ProfileType,
} from "../api/client";
import { useAuth } from "../auth/AuthContext";
import { Avatar } from "../components/Avatar";
import { FollowButton } from "../components/FollowButton";

function FollowList({
  title,
  items,
  onClose,
}: {
  title: string;
  items: FollowItem[];
  onClose: () => void;
}) {
  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <h3>{title}</h3>
        <button className="modal-close" onClick={onClose}>
          ✕
        </button>
        {items.length === 0 ? (
          <p className="muted">Nobody here yet.</p>
        ) : (
          <ul className="follow-list">
            {items.map((u) => (
              <li key={u.id}>
                <Link to={`/u/${u.username}`} onClick={onClose}>
                  <Avatar user={u} size={36} />
                  <span>
                    <strong>{u.display_name}</strong>
                    <small>@{u.username}</small>
                  </span>
                </Link>
                {u.is_following && u.is_followed_by && (
                  <span className="mutual-badge">mutual</span>
                )}
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}

export function Profile() {
  const { username } = useParams<{ username: string }>();
  const { user: me } = useAuth();
  const [profile, setProfile] = useState<ProfileType | null>(null);
  const [posts, setPosts] = useState<Post[]>([]);
  const [loading, setLoading] = useState(true);
  const [notFound, setNotFound] = useState(false);
  const [listKind, setListKind] = useState<"followers" | "following" | null>(
    null
  );
  const [listItems, setListItems] = useState<FollowItem[]>([]);
  const [editing, setEditing] = useState(false);
  const [bio, setBio] = useState("");
  const [displayName, setDisplayName] = useState("");

  const load = useCallback(async () => {
    if (!username) return;
    setLoading(true);
    setNotFound(false);
    try {
      const [pRes, postsRes] = await Promise.all([
        api.get<ProfileType>(`/users/${username}`),
        api.get<PaginatedPosts>(`/users/${username}/posts`, {
          params: { limit: 60 },
        }),
      ]);
      setProfile(pRes.data);
      setPosts(postsRes.data.items);
      setBio(pRes.data.bio);
      setDisplayName(pRes.data.display_name);
    } catch {
      setNotFound(true);
    } finally {
      setLoading(false);
    }
  }, [username]);

  useEffect(() => {
    load();
  }, [load]);

  async function openList(kind: "followers" | "following") {
    const res = await api.get<FollowItem[]>(`/users/${username}/${kind}`);
    setListItems(res.data);
    setListKind(kind);
  }

  async function saveProfile() {
    await api.patch("/users/me", {
      display_name: displayName.trim(),
      bio: bio,
    });
    setEditing(false);
    load();
  }

  if (loading) return <p className="muted">Loading…</p>;
  if (notFound || !profile) return <p className="muted">User not found.</p>;

  return (
    <div className="profile">
      <header className="profile-header">
        <Avatar user={profile} size={96} />
        <div className="profile-info">
          <div className="profile-toprow">
            <h2>@{profile.username}</h2>
            {profile.is_me ? (
              <button
                className="btn btn-secondary btn-sm"
                onClick={() => setEditing((v) => !v)}
              >
                {editing ? "Cancel" : "Edit profile"}
              </button>
            ) : me ? (
              <FollowButton
                username={profile.username}
                initialFollowing={profile.is_following}
                onChange={(f) =>
                  setProfile({
                    ...profile,
                    is_following: f,
                    follower_count:
                      profile.follower_count + (f ? 1 : -1),
                  })
                }
              />
            ) : null}
          </div>
          {editing ? (
            <div className="profile-edit">
              <input
                value={displayName}
                onChange={(e) => setDisplayName(e.target.value)}
                placeholder="Display name"
                maxLength={80}
              />
              <textarea
                value={bio}
                onChange={(e) => setBio(e.target.value)}
                placeholder="Bio"
                maxLength={500}
                rows={2}
              />
              <button className="btn btn-primary btn-sm" onClick={saveProfile}>
                Save
              </button>
            </div>
          ) : (
            <>
              <p className="profile-display">{profile.display_name}</p>
              {profile.bio && <p className="profile-bio">{profile.bio}</p>}
              {profile.is_followed_by && !profile.is_me && (
                <p className="muted follows-you">Follows you</p>
              )}
            </>
          )}
          <div className="profile-stats">
            <span>
              <strong>{profile.post_count}</strong> posts
            </span>
            <button
              className="stat-btn"
              onClick={() => openList("followers")}
            >
              <strong>{profile.follower_count}</strong> followers
            </button>
            <button
              className="stat-btn"
              onClick={() => openList("following")}
            >
              <strong>{profile.following_count}</strong> following
            </button>
          </div>
        </div>
      </header>

      <div className="image-grid">
        {posts.map((p) => (
          <Link key={p.id} to={`/p/${p.id}`} className="grid-item">
            <img
              src={imageSrc(p.image_url)}
              alt={p.caption || `Post by ${profile.username}`}
              loading="lazy"
            />
            <span className="grid-overlay">
              ♥ {p.like_count} &nbsp; 💬 {p.comment_count}
            </span>
          </Link>
        ))}
      </div>
      {posts.length === 0 && (
        <p className="muted">No pictures yet.</p>
      )}

      {listKind && (
        <FollowList
          title={listKind === "followers" ? "Followers" : "Following"}
          items={listItems}
          onClose={() => setListKind(null)}
        />
      )}
    </div>
  );
}
