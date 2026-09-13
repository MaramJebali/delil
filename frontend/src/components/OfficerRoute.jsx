import { Navigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext.jsx";

export default function OfficerRoute({ children }) {
  const { user } = useAuth();
  if (!user) return <Navigate to="/" replace />;
  if (user.role !== "officer") return <Navigate to="/dashboard" replace />;
  return children;
}