import axios from "axios";

export const API_BASE =
  import.meta.env.VITE_API_URL ?? "http://localhost:8000";

export const api = axios.create({ baseURL: API_BASE });

api.interceptors.request.use((config) => {
  const token = localStorage.getItem("potd_token");
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

api.interceptors.response.use(
  (res) => res,
  (err) => {
    if (err.response?.status === 401) {
      localStorage.removeItem("potd_token");
      if (!window.location.pathname.startsWith("/login")) {
        window.location.href = "/login";
      }
    }
    return Promise.reject(err);
  }
);

/** Resolve an image URL: absolute URLs pass through, "/uploads/..." is
 *  prefixed with the API base. */
export function imageSrc(url: string): string {
  if (url.startsWith("http://") || url.startsWith("https://")) return url;
  return `${API_BASE}${url}`;
}

// ---------- Shared types ----------

export interface Author {
  id: number;
  username: string;
  display_name: string;
  avatar_url: string | null;
}

export interface Post {
  id: number;
  image_url: string;
  caption: string;
  created_at: string;
  author: Author;
  like_count: number;
  comment_count: number;
  liked_by_me: boolean;
}

export interface PaginatedPosts {
  items: Post[];
  total: number;
  limit: number;
  offset: number;
}

export interface CommentNode {
  id: number;
  body: string;
  created_at: string;
  author: Author;
  replies: CommentNode[];
}

export interface Profile extends Author {
  bio: string;
  created_at: string;
  post_count: number;
  follower_count: number;
  following_count: number;
  is_following: boolean;
  is_followed_by: boolean;
  is_me: boolean;
}

export interface FollowItem extends Author {
  is_following: boolean;
  is_followed_by: boolean;
}
