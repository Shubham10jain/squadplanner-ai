import { Navigate } from "react-router-dom"
import { useAuth } from "@/store/authStore.jsx"

export default function ProtectedRoute({ children }) {
  const { user, loading } = useAuth()

  if (loading) return null  // avoids flash before cookie check resolves

  if (!user) return <Navigate to="/auth" replace />

  return children
}
