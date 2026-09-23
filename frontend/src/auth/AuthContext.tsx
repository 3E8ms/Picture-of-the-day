import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import { api, type Author } from "../api/client";

interface AuthState {
  user: Author | null;
  loading: boolean;
  login: (username: string, password: string) => Promise<void>;
  register: (data: {
    username: string;
    email: string;
    password: string;
    display_name: string;
  }) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthState | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<Author | null>(null);
  const [loading, setLoading] = useState(true);

  const fetchMe = useCallback(async () => {
    const token = localStorage.getItem("potd_token");
    if (!token) {
      setLoading(false);
      return;
    }
    try {
      const res = await api.get<Author>("/auth/me");
      setUser(res.data);
    } catch {
      localStorage.removeItem("potd_token");
      setUser(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchMe();
  }, [fetchMe]);

  const saveTokenAndLoad = useCallback(async (token: string) => {
    localStorage.setItem("potd_token", token);
    const res = await api.get<Author>("/auth/me");
    setUser(res.data);
  }, []);

  const login = useCallback(
    async (username: string, password: string) => {
      const form = new URLSearchParams({ username, password });
      const res = await api.post<{ access_token: string }>(
        "/auth/login",
        form,
        { headers: { "Content-Type": "application/x-www-form-urlencoded" } }
      );
      await saveTokenAndLoad(res.data.access_token);
    },
    [saveTokenAndLoad]
  );

  const register = useCallback(
    async (data: {
      username: string;
      email: string;
      password: string;
      display_name: string;
    }) => {
      const res = await api.post<{ access_token: string }>(
        "/auth/register",
        data
      );
      await saveTokenAndLoad(res.data.access_token);
    },
    [saveTokenAndLoad]
  );

  const logout = useCallback(() => {
    localStorage.removeItem("potd_token");
    setUser(null);
  }, []);

  const value = useMemo(
    () => ({ user, loading, login, register, logout }),
    [user, loading, login, register, logout]
  );
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthState {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used inside AuthProvider");
  return ctx;
}
