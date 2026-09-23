import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";
import { Avatar } from "./Avatar";

export function Navbar() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  return (
    <nav className="navbar">
      <Link to="/" className="brand">
        📷 Picture of the Day
      </Link>
      <div className="nav-links">
        {user ? (
          <>
            <Link to="/">Feed</Link>
            <Link to="/explore">Explore</Link>
            <Link to="/upload" className="btn btn-primary btn-sm">
              + New Post
            </Link>
            <Link to={`/u/${user.username}`}>
              <Avatar user={user} size={32} />
            </Link>
            <button
              className="btn btn-ghost btn-sm"
              onClick={() => {
                logout();
                navigate("/login");
              }}
            >
              Log out
            </button>
          </>
        ) : (
          <>
            <Link to="/login">Log in</Link>
            <Link to="/register" className="btn btn-primary btn-sm">
              Sign up
            </Link>
          </>
        )}
      </div>
    </nav>
  );
}
