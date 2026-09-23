import { useCallback, useEffect, useState } from "react";
import { api, type PaginatedPosts, type Post } from "../api/client";
import { PostCard } from "../components/PostCard";

const PAGE = 12;

function usePaginatedPosts(fetcher: (limit: number, offset: number) => Promise<PaginatedPosts>) {
  const [posts, setPosts] = useState<Post[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const res = await fetcher(PAGE, 0);
      setPosts(res.items);
      setTotal(res.total);
    } finally {
      setLoading(false);
    }
  }, [fetcher]);

  useEffect(() => {
    load();
  }, [load]);

  async function loadMore() {
    if (loadingMore || posts.length >= total) return;
    setLoadingMore(true);
    try {
      const res = await fetcher(PAGE, posts.length);
      setPosts((p) => [...p, ...res.items]);
      setTotal(res.total);
    } finally {
      setLoadingMore(false);
    }
  }

  function remove(id: number) {
    setPosts((p) => p.filter((x) => x.id !== id));
    setTotal((t) => t - 1);
  }

  return { posts, total, loading, loadingMore, loadMore, remove };
}

export function Feed() {
  const fetcher = useCallback(
    (limit: number, offset: number) =>
      api
        .get<PaginatedPosts>("/feed", { params: { limit, offset } })
        .then((r) => r.data),
    []
  );
  const { posts, total, loading, loadingMore, loadMore } =
    usePaginatedPosts(fetcher);

  return (
    <div className="feed">
      <h2>Your Feed</h2>
      {loading ? (
        <p className="muted">Loading…</p>
      ) : posts.length === 0 ? (
        <p className="muted">
          Nothing here yet. Follow people or share your first picture!
        </p>
      ) : (
        <>
          {posts.map((p) => (
            <PostCard key={p.id} initial={p} />
          ))}
          {posts.length < total && (
            <button
              className="btn btn-secondary"
              onClick={loadMore}
              disabled={loadingMore}
            >
              {loadingMore ? "Loading…" : "Load more"}
            </button>
          )}
        </>
      )}
    </div>
  );
}

export function Explore() {
  const fetcher = useCallback(
    (limit: number, offset: number) =>
      api
        .get<PaginatedPosts>("/posts", { params: { limit, offset } })
        .then((r) => r.data),
    []
  );
  const { posts, total, loading, loadingMore, loadMore, remove } =
    usePaginatedPosts(fetcher);

  return (
    <div className="feed">
      <h2>Explore</h2>
      {loading ? (
        <p className="muted">Loading…</p>
      ) : (
        <>
          <div className="grid">
            {posts.map((p) => (
              <PostCard key={p.id} initial={p} onDeleted={remove} />
            ))}
          </div>
          {posts.length < total && (
            <button
              className="btn btn-secondary"
              onClick={loadMore}
              disabled={loadingMore}
            >
              {loadingMore ? "Loading…" : "Load more"}
            </button>
          )}
        </>
      )}
    </div>
  );
}
