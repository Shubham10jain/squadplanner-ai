import { NavLink, Link } from "react-router-dom"
import { PlusCircle } from "lucide-react"
import Logo from "@/atoms/Logo"
import { useAuth } from "@/store/authStore"

const tabs = [
  { label: "Home",         to: "/",        end: true },
  { label: "My Trips",     to: "/mytrips" },
  { label: "Explore",      to: "/explore" },
  { label: "Shared Trips", to: "/shared" },
  { label: "Stats",        to: "/stats" },
]

const HomeHeader = () => {
  const { user } = useAuth()
  
  return (
    <header className="flex items-center justify-between px-8 pt-5 pb-3">
      {/* Logo — no background */}
      <Logo />

      {/* Nav tabs — glass pill only around these */}
      <nav className="flex items-center gap-0.5 bg-white/40 backdrop-blur-md rounded-2xl px-2 py-1.5 border border-white/60 shadow-sm">
        {tabs.map(({ label, to, end }) => (
          <NavLink
            key={to}
            to={to}
            end={end}
            className={({ isActive }) =>
              `px-4 py-1.5 text-sm transition-colors ${
                isActive
                  ? "text-black font-bold"
                  : "text-gray-500 hover:text-black font-medium"
              }`
            }
          >
            {label}
          </NavLink>
        ))}
      </nav>

      {/* Actions — no background */}
      <div className="flex items-center gap-1.5">
        <Link
          to="/trips/new"
          className="flex items-center gap-1.5 px-4 py-2 rounded-full bg-primary text-black text-sm font-bold hover:bg-primary-dim transition-colors volt-glow ml-1"
        >
          <PlusCircle size={14} />
          Plan a new trip
        </Link>

        {/* Profile Avatar Icon */}
        <div className="w-9 h-9 rounded-full border-2 border-primary bg-slate-900 flex items-center justify-center text-primary font-bold text-xs cursor-pointer overflow-hidden shadow-sm hover:scale-105 active:scale-95 transition-transform ml-1.5 flex-shrink-0">
          {user?.avatar_url ? (
            <img src={user.avatar_url} alt="Profile" className="w-full h-full object-cover" />
          ) : (
            user?.name ? user.name.slice(0, 2).toUpperCase() : user?.email ? user.email.slice(0, 2).toUpperCase() : "JD"
          )}
        </div>
      </div>
    </header>
  )
}

export default HomeHeader
