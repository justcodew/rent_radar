import { Navigate } from "react-router-dom";
import { useAuthStore } from "../stores/auth";

export default function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const isAuth = useAuthStore((s) => !!s.accessToken);
  if (!isAuth) {
    return <Navigate to="/login" replace />;
  }
  return <>{children}</>;
}
