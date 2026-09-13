import { createContext, useContext, useState } from "react";
import api from "../api/axios";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(() => {
    const raw = localStorage.getItem("dalil_user");
    return raw ? JSON.parse(raw) : null;
  });
  const [loading, setLoading] = useState(false);

  const saveSession = (data) => {
    localStorage.setItem("dalil_access", data.access);
    localStorage.setItem("dalil_refresh", data.refresh);
    localStorage.setItem("dalil_user", JSON.stringify(data.user));
    setUser(data.user);
    return data.user;
  };

  const login = async (username, password) => {
    setLoading(true);
    try {
      const { data } = await api.post("/accounts/login/", { username, password });
      return saveSession(data);
    } finally {
      setLoading(false);
    }
  };

  const register = async (username, email, password) => {
    setLoading(true);
    try {
      const { data } = await api.post("/accounts/register/", {
        username,
        email,
        password,
      });
      return saveSession(data);
    } finally {
      setLoading(false);
    }
  };

  const logout = () => {
    localStorage.removeItem("dalil_access");
    localStorage.removeItem("dalil_refresh");
    localStorage.removeItem("dalil_user");
    setUser(null);
  };

  return (
    <AuthContext.Provider value={{ user, loading, login, register, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  return useContext(AuthContext);
}