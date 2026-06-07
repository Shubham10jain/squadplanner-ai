import { StrictMode } from "react"
import { createRoot } from "react-dom/client"
import { RouterProvider } from "react-router-dom"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { ThemeProvider } from "./providers/ThemeProvider"
import { UserProvider } from "./providers/UserProvider"
import { AuthProvider } from "./store/authStore.jsx"
import router from "./routes"
import "./index.css"

const queryClient = new QueryClient()

createRoot(document.getElementById("root")).render(
  <StrictMode>
    <AuthProvider>
      <UserProvider>
        <ThemeProvider>
          <QueryClientProvider client={queryClient}>
            <RouterProvider router={router} />
          </QueryClientProvider>
        </ThemeProvider>
      </UserProvider>
    </AuthProvider>
  </StrictMode>
)
