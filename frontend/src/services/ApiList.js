import { apiFetch } from "@/services"

export const getMe        = ()     => apiFetch("/auth/me")
export const register     = (data) => apiFetch("/auth/register", { method: "POST", body: JSON.stringify(data), credentials: "include" })
export const login        = (data) => apiFetch("/auth/login",    { method: "POST", body: JSON.stringify(data), credentials: "include" })
export const googleAuth   = (data) => apiFetch("/auth/google",   { method: "POST", body: JSON.stringify(data), credentials: "include" })
export const logout       = ()     => apiFetch("/auth/logout",   { method: "POST", credentials: "include" })

export const getTrips = (email, createdBy) => {
  const query = new URLSearchParams()
  if (email) query.append("email", email)
  if (createdBy) query.append("created_by", createdBy)
  const queryString = query.toString()
  return apiFetch(`/trips${queryString ? `?${queryString}` : ""}`)
}
export const getTripById = (id) => apiFetch(`/trips/${id}`)
export const createTrip = (data) => apiFetch("/trips", { method: "POST", body: JSON.stringify(data) })
