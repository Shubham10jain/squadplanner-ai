import { createBrowserRouter } from "react-router-dom"
import HomeLayout from "@/layout/HomeLayout"
import TripFlowLayout from "@/templates/TripFlowLayout"
import Home from "@/pages/Home"
import Auth from "@/pages/Auth"
import NewTrip from "@/pages/NewTrip"
import TripPreferences from "@/pages/TripPreferences"
import ProtectedRoute from "@/atoms/ProtectedRoute"

const router = createBrowserRouter([
  {
    element: <HomeLayout />,
    children: [
      { path: "/", element: <Home /> },
    ],
  },
  {
    path: "/auth",
    element: <Auth />,
  },
  {
    element: <TripFlowLayout />,
    children: [
      { path: "/trips/new",         element: <ProtectedRoute><NewTrip /></ProtectedRoute> },
      { path: "/trips/preferences", element: <ProtectedRoute><TripPreferences /></ProtectedRoute> },
    ],
  },
])

export default router
