import { Outlet } from "react-router-dom"
import { Toaster } from "sonner"
import HomeHeader from "@/organisms/HomeHeader"

const HomeLayout = () => (
  <>
    {/* Background: light base + volt green blob top-left + soft pink blob top-right */}
    <div
      className="h-screen font-sans flex flex-col overflow-hidden"
      style={{
        background: `
          radial-gradient(ellipse at 4% 8%,  rgba(209,249,77,0.18) 0%, transparent 40%),
          radial-gradient(ellipse at 96% 6%,  rgba(255,182,200,0.22) 0%, transparent 38%),
          radial-gradient(ellipse at 55% 96%, rgba(200,220,255,0.14) 0%, transparent 45%),
          #f9f9f6
        `,
      }}
    >
      <HomeHeader />
      <Outlet />
    </div>
    <Toaster
      position="top-right"
      richColors
      closeButton
      toastOptions={{
        style: {
          background: "var(--surface-bright)",
          color: "var(--on-surface)",
          border: "1px solid var(--outline-variant)",
        },
      }}
    />
  </>
)

export default HomeLayout
