import { imageSrc, type Author } from "../api/client";

export function Avatar({
  user,
  size = 40,
}: {
  user: Pick<Author, "username" | "display_name" | "avatar_url">;
  size?: number;
}) {
  if (user.avatar_url) {
    return (
      <img
        className="avatar"
        src={imageSrc(user.avatar_url)}
        alt={user.username}
        style={{ width: size, height: size }}
      />
    );
  }
  const initial = (user.display_name || user.username || "?")[0].toUpperCase();
  return (
    <div
      className="avatar avatar-fallback"
      style={{ width: size, height: size, fontSize: size * 0.45 }}
      aria-label={user.username}
    >
      {initial}
    </div>
  );
}
