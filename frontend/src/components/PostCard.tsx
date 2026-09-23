import { useState } from "react";
import { Link } from "react-router-dom";
import { api, imageSrc, type Post } from "../api/client";
import { Avatar } from "./Avatar";

export function PostCard({
  initial,
  onDeleted,
}: {
  initial: Post;
  onDeleted?: (id: number) => void;
}) {
  const [post, setPost] = useState(initial);
  const [likeBusy, setLikeBusy] = useState(false);

  async function toggleLike() {
    if (likeBusy) return;
    setLikeBusy(true);
    const prevLiked = post.liked_by_me;
    const prevCount = post.like_count;
    // optimistic
    setPost({
      ...post,
      liked_by_me: !prevLiked,
      like_count: prevCount + (prevLiked ? -1 : 1),
    });
    try {
      const res = await api.post<{
        liked: boolean;
        like_count: number;
      }>(`/posts/${post.id}/like`);
      setPost({
        ...post,
        liked_by_me: res.data.liked,
        like_count: res.data.like_count,
      });
    } catch {
      setPost({ ...post, liked_by_me: prevLiked, like_count: prevCount });
    } finally {
      setLikeBusy(false);
    }
  }

  async function remove() {
    if (!window.confirm("Delete this post?")) return;
    await api.delete(`/posts/${post.id}`);
    onDeleted?.(post.id);
  }

  return (
    <article className="post-card">
      <header className="post-header">
        <Link to={`/u/${post.author.username}`} className="post-author">
          <Avatar user={post.author} size={36} />
          <span>
            <strong>{post.author.display_name}</strong>
            <small>@{post.author.username}</small>
          </span>
        </Link>
      </header>
      <Link to={`/p/${post.id}`}>
        <img
          className="post-image"
          src={imageSrc(post.image_url)}
          alt={post.caption || `Post by ${post.author.username}`}
          loading="lazy"
        />
      </Link>
      <div className="post-actions">
        <button
          className={`like-btn${post.liked_by_me ? " liked" : ""}`}
          onClick={toggleLike}
          disabled={likeBusy}
          aria-label={post.liked_by_me ? "Unlike" : "Like"}
        >
          {post.liked_by_me ? "♥" : "♡"} {post.like_count}
        </button>
        <Link className="comment-link" to={`/p/${post.id}`}>
          💬 {post.comment_count}
        </Link>
        {onDeleted && (
          <button className="delete-btn" onClick={remove}>
            Delete
          </button>
        )}
      </div>
      {post.caption && (
        <p className="post-caption">
          <Link to={`/u/${post.author.username}`}>
            <strong>{post.author.username}</strong>
          </Link>{" "}
          {post.caption}
        </p>
      )}
    </article>
  );
}
