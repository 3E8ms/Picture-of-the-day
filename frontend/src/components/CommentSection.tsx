import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api, type CommentNode } from "../api/client";
import { Avatar } from "./Avatar";

function CommentBox({
  postId,
  parentId,
  onDone,
  autoFocus,
  placeholder,
}: {
  postId: number;
  parentId: number | null;
  onDone: () => void;
  autoFocus?: boolean;
  placeholder: string;
}) {
  const [body, setBody] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (!body.trim() || busy) return;
    setBusy(true);
    setError("");
    try {
      await api.post(`/posts/${postId}/comments`, {
        body: body.trim(),
        parent_id: parentId,
      });
      setBody("");
      onDone();
    } catch (err: unknown) {
      setError("Couldn't post your comment. Try again.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <form className="comment-box" onSubmit={submit}>
      <input
        value={body}
        onChange={(e) => setBody(e.target.value)}
        placeholder={placeholder}
        autoFocus={autoFocus}
        maxLength={2000}
      />
      <button className="btn btn-primary btn-sm" type="submit" disabled={busy}>
        Post
      </button>
      {error && <span className="error">{error}</span>}
    </form>
  );
}

function CommentItem({
  postId,
  comment,
  depth,
  onDone,
}: {
  postId: number;
  comment: CommentNode;
  depth: number;
  onDone: () => void;
}) {
  const [replying, setReplying] = useState(false);
  return (
    <div className={`comment depth-${depth}`}>
      <Link to={`/u/${comment.author.username}`}>
        <Avatar user={comment.author} size={28} />
      </Link>
      <div className="comment-body">
        <p>
          <Link to={`/u/${comment.author.username}`}>
            <strong>{comment.author.username}</strong>
          </Link>{" "}
          {comment.body}
        </p>
        {depth === 0 && (
          <button
            className="reply-btn"
            onClick={() => setReplying((v) => !v)}
          >
            Reply
          </button>
        )}
        {replying && (
          <CommentBox
            postId={postId}
            parentId={comment.id}
            autoFocus
            placeholder={`Reply to ${comment.author.username}…`}
            onDone={() => {
              setReplying(false);
              onDone();
            }}
          />
        )}
        {comment.replies.map((r) => (
          <CommentItem
            key={r.id}
            postId={postId}
            comment={r}
            depth={depth + 1}
            onDone={onDone}
          />
        ))}
      </div>
    </div>
  );
}

export function CommentSection({ postId }: { postId: number }) {
  const [comments, setComments] = useState<CommentNode[]>([]);
  const [loading, setLoading] = useState(true);

  async function load() {
    setLoading(true);
    try {
      const res = await api.get<CommentNode[]>(`/posts/${postId}/comments`);
      setComments(res.data);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [postId ]);

  return (
    <section className="comments">
      <h3>Comments</h3>
      <CommentBox
        postId={postId}
        parentId={null}
        placeholder="Add a comment…"
        onDone={load}
      />
      {loading ? (
        <p className="muted">Loading comments…</p>
      ) : comments.length === 0 ? (
        <p className="muted">No comments yet. Be the first!</p>
      ) : (
        comments.map((c) => (
          <CommentItem
            key={c.id}
            postId={postId}
            comment={c}
            depth={0}
            onDone={load}
          />
        ))
      )}
    </section>
  );
}
