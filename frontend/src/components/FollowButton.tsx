import { useState } from "react";
import { api } from "../api/client";

export function FollowButton({
  username,
  initialFollowing,
  onChange,
}: {
  username: string;
  initialFollowing: boolean;
  onChange?: (following: boolean) => void;
}) {
  const [following, setFollowing] = useState(initialFollowing);
  const [busy, setBusy] = useState(false);

  async function toggle() {
    if (busy) return;
    const next = !following;
    setFollowing(next); // optimistic
    setBusy(true);
    try {
      if (next) {
        await api.post(`/users/${username}/follow`);
      } else {
        await api.delete(`/users/${username}/follow`);
      }
      onChange?.(next);
    } catch {
      setFollowing(!next); // roll back
    } finally {
      setBusy(false);
    }
  }

  return (
    <button
      className={following ? "btn btn-secondary" : "btn btn-primary"}
      onClick={toggle}
      disabled={busy}
    >
      {following ? "Following" : "Follow"}
    </button>
  );
}
