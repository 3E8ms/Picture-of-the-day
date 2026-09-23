import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api, imageSrc, type Post } from "../api/client";
import { Avatar } from "../components/Avatar";
import { CommentSection } from "../components/CommentSection";

export function PostDetail() {
  const { id } = useParams<{ id: string }>();
  const [post, setPost] = useState<Post | null>(null);
  const [loading, setLoading] = useState(true);
  const [notFound, setNotFound] = useState(false);
  const [likeBusy, setLikeBusy] = useState(false);

  useEffect(() => {
    async function load() {
      setLoading(true);
      setNotFound(false);
      try {
        const res = await api.get<Post>(`/posts/${id}`);
        setPost(res.data);
      } catch {
        setNotFound(true);
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [id]);

  async function toggleLike() {
    if (!post || likeBusy) return;
    setLikeBusy(true);
    const prev = post;
    setPost({
      ...post,
      liked_by_me: !post.liked_by_me,
      like_count: post.like_count + (post.liked_by_me ? -1 : 1),
    });
    try {
      const res = await api.post<{
        liked: boolean;
        like_count: number;
      }>(`/posts/${post.id}/like`);
      setPost({
        ...prev,
        liked_by_me: res.data.liked,
        like_count: res.data.like_count,
      });
    } catch {
      setPost(prev);
    } finally {
      setLikeBusy(false);
    }
  }

  if (loading) return <p className="muted">Loading…</p>;
  if (notFound || !post) return <p className="muted">Post not found.</p>;

  return (
    <div className="post-detail">
      <div className="post-detail-main">
        <img
          src={imageSrc(post.image_url)}
          alt={post.caption || `Post by ${post.author.username}`}
        />
      </div>
      <div className="post-detail-side">
        <header className="post-header">
          <Link to={`/u/${post.author.username}`} className="post-author">
            <Avatar user={post.author} size={36} />
            <span>
              <strong>{post.author.display_name}</strong>
              <small>@{post.author.username}</small>
            </span>
          </Link>
        </header>
        {post.caption && <p className="post-caption">{post.caption}</p>}
        <button
          className={`like-btn${post.liked_by_me ? " liked" : ""}`}
          onClick={toggleLike}
          disabled={likeBusy}
        >
          {post.liked_by_me ? "♥" : "♡"} {post.like_count}{" "}
          {post.like_count === 1 ? "like" : "likes"}
        </button>
        <CommentSection postId={post.id} />
      </div>
    </div>
  );
}
