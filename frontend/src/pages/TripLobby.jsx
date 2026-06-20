import { useState, useEffect } from "react"
import { useParams, useNavigate } from "react-router-dom"
import { Users, Mail, Copy, Settings, PlusCircle, Check, RefreshCw, CheckCircle2, Shield } from "lucide-react"
import { getTripById } from "@/services/ApiList"
import { toast } from "sonner"

const TripLobby = () => {
  const { tripId } = useParams()
  const navigate = useNavigate()
  const [trip, setTrip] = useState(null)
  const [loading, setLoading] = useState(true)
  const [copied, setCopied] = useState(false)

  useEffect(() => {
    let id = tripId
    if (!id || id === "lobby") {
      id = sessionStorage.getItem("currentTripId")
    }

    if (!id) {
      navigate("/trips/new")
      return
    }

    const fetchTrip = async () => {
      try {
        const data = await getTripById(id)
        setTrip(data)
      } catch (error) {
        console.error("Error fetching trip:", error)
      } finally {
        setLoading(false)
      }
    }

    fetchTrip()
    // Poll for status updates every 5 seconds
    const interval = setInterval(fetchTrip, 5000)
    return () => clearInterval(interval)
  }, [tripId, navigate])

  const handleCopyLink = () => {
    const inviteLink = `${window.location.origin}/join/${trip?.invite_code || ""}`
    navigator.clipboard.writeText(inviteLink)
    setCopied(true)
    toast.success("Invite link copied to clipboard!")
    setTimeout(() => setCopied(false), 2000)
  }

  if (loading) {
    return (
      <div className="flex-1 flex items-center justify-center min-h-[60vh]">
        <div className="animate-pulse text-slate-500 font-medium">Entering the lobby...</div>
      </div>
    )
  }

  if (!trip) {
    return (
      <div className="flex-1 flex items-center justify-center min-h-[60vh] text-slate-500">
        Trip details not found.
      </div>
    )
  }

  const members = trip.invited_members || []
  const totalMembers = members.length
  const readyMembers = members.filter((m) => m.status === "accepted").length
  const readiness = 60

  return (
    <main className="flex-1 max-w-6xl mx-auto w-full px-6 py-6 lg:px-12 overflow-y-auto">
      {/* Hero Header Section */}
      <div className="flex items-center justify-between gap-4 mb-8">
        <div className="space-y-1">
          <div className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full bg-primary/20 text-slate-800 text-[10px] font-bold uppercase tracking-wider">
            <span className="relative flex h-1.5 w-1.5">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-primary opacity-75"></span>
              <span className="relative inline-flex rounded-full h-1.5 w-1.5 bg-primary"></span>
            </span>
            Live Lobby
          </div>
          <h1 className="text-2xl md:text-3xl font-black text-slate-900 tracking-tight leading-none">
            Trip Lobby: <span className="text-primary bg-slate-900 px-3 py-1 rounded-xl inline-block ml-1 not-italic font-black text-xl md:text-2xl">{trip.trip_name}</span>
          </h1>
          <p className="text-slate-500 text-xs font-medium">Waiting for the squad to sync their vibes...</p>
        </div>
        
        <div className="flex items-center">
          <button
            onClick={handleCopyLink}
            className="flex items-center justify-center gap-2 px-5 h-10 bg-primary text-black rounded-xl text-xs font-bold hover:brightness-105 transition-all shadow-md shadow-primary/20 hover:scale-102 active:scale-98 cursor-pointer"
          >
            <Copy size={14} />
            Copy Invite Link
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Main Content: The Squad */}
        <div className="lg:col-span-2 space-y-4">
          <section className="bg-white/40 backdrop-blur-md rounded-2xl border border-white/60 p-6 shadow-sm">
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-lg font-black text-slate-900 flex items-center gap-2">
                <Users className="text-primary" size={20} />
                The Squad
              </h2>
              <span className="text-[10px] font-bold text-slate-400 uppercase tracking-widest">{totalMembers} Members Joined</span>
            </div>

            <div className="space-y-3">
              {members.map((member, idx) => {
                const isReady = member.status === "accepted"
                const isPending = member.status === "pending"
                
                // Initials fallback
                const email = member.email || ""
                const initial = email ? email[0].toUpperCase() : "?"
                
                // Color mapping for avatars
                const bgColors = [
                  "bg-orange-500",
                  "bg-pink-500",
                  "bg-purple-600",
                  "bg-teal-500",
                  "bg-blue-600"
                ]
                const avatarBg = bgColors[idx % bgColors.length]

                return (
                  <div key={idx} className="flex items-center justify-between p-3.5 rounded-xl bg-white/50 border border-slate-100/50 shadow-sm transition-all hover:bg-white/60">
                    <div className="flex items-center gap-3">
                      <div className="relative">
                        {member.avatar_url ? (
                          <img
                            className={`size-10 rounded-full object-cover ring-2 ${isReady ? "ring-primary" : "ring-transparent"}`}
                            src={member.avatar_url}
                            alt={member.name}
                          />
                        ) : (
                          <div className={`size-10 rounded-full flex items-center justify-center text-white font-black text-sm shadow-sm ${avatarBg} ring-2 ${isReady ? "ring-primary" : "ring-transparent"}`}>
                            {initial}
                          </div>
                        )}
                        <span className={`absolute bottom-0 right-0 size-3 rounded-full border border-white ${isReady ? "bg-green-500" : isPending ? "bg-slate-300" : "bg-orange-400"}`}></span>
                      </div>
                      <div>
                        <h3 className="font-bold text-slate-900 text-sm leading-tight">{member.name || email}</h3>
                        <p className="text-[10px] text-slate-500 font-medium mt-0.5">
                          {idx === 0 ? "Vibe Master (Host)" : isReady ? "Ready to Roll" : isPending ? "Invitation Sent" : "Syncing Preferences..."}
                        </p>
                      </div>
                    </div>

                    {isReady ? (
                      <div className="flex items-center gap-1 px-3 py-1 rounded-full bg-primary/20 text-slate-800 text-[10px] font-bold uppercase tracking-wider">
                        <CheckCircle2 size={12} className="text-green-600" />
                        READY
                      </div>
                    ) : isPending ? (
                      <div className="flex items-center gap-1 px-3 py-1 rounded-full bg-slate-100 text-slate-500 text-[10px] font-bold uppercase tracking-wider">
                        <Mail size={12} />
                        PENDING
                      </div>
                    ) : (
                      <div className="flex items-center gap-1 px-3 py-1 rounded-full bg-amber-100 text-amber-700 text-[10px] font-bold uppercase tracking-wider">
                        <RefreshCw size={12} className="animate-spin" />
                        SYNCING
                      </div>
                    )}
                  </div>
                )
              })}

              {/* Invite more friends slot */}
              <button
                onClick={() => {
                  const inviteLink = `${window.location.origin}/join/${trip?.invite_code || ""}`
                  navigator.clipboard.writeText(inviteLink)
                  toast.success("Invite link copied! Send it to your friends.")
                }}
                className="w-full flex items-center justify-center p-3 border border-dashed border-slate-200 hover:border-primary hover:bg-primary/5 rounded-xl transition-all group cursor-pointer"
              >
                <div className="flex items-center gap-2 text-slate-400 group-hover:text-primary transition-colors">
                  <PlusCircle size={16} />
                  <span className="font-bold text-xs uppercase tracking-wider">Invite more friends</span>
                </div>
              </button>
            </div>
          </section>
        </div>

        {/* Sidebar Content */}
        <div className="space-y-4">
          {/* Progress Card */}
          <section className="bg-slate-900 rounded-2xl p-6 text-white volt-glow">
            <h2 className="text-sm font-bold mb-4 flex items-center gap-2 text-primary uppercase tracking-wider">
              <CheckCircle2 size={16} />
              Sync Progress
            </h2>
            <div className="space-y-4">
              <div className="flex justify-between text-xs font-bold uppercase tracking-wider">
                <span>Squad Readiness</span>
                <span className="text-primary">{readiness}%</span>
              </div>
              <div className="w-full bg-slate-800 rounded-full h-2 overflow-hidden">
                <div className="bg-primary h-full rounded-full transition-all duration-500" style={{ width: `${readiness}%` }}></div>
              </div>
              <p className="text-slate-400 text-xs leading-relaxed font-medium">
                We're analyzing everyone's budget, date preferences, and activity styles to find the perfect match.
              </p>
            </div>
          </section>

          {/* What's Next Card */}
          <section className="bg-white/40 backdrop-blur-md rounded-2xl border border-white/60 p-6 shadow-sm">
            <h2 className="text-base font-black text-slate-900 mb-5 uppercase tracking-wider">What's Next</h2>
            <div className="space-y-6 relative before:absolute before:left-[13px] before:top-2 before:bottom-2 before:w-0.5 before:bg-slate-200">
              {/* Step 1 */}
              <div className="relative pl-10">
                <div className="absolute left-0 top-0.5 size-7 rounded-full bg-primary flex items-center justify-center text-slate-900 shadow-sm">
                  <Check size={16} className="font-bold" />
                </div>
                <h4 className="font-extrabold text-slate-900 text-base leading-none mb-1.5">Squad formation</h4>
                <p className="text-sm text-slate-500 font-medium">Invite your travel buddies to the hub.</p>
              </div>
              {/* Step 2 */}
              <div className="relative pl-10">
                <div className="absolute left-0 top-0.5 size-7 rounded-full bg-primary/20 text-primary border border-primary flex items-center justify-center animate-pulse shadow-sm">
                  <RefreshCw size={14} className="animate-spin" />
                </div>
                <h4 className="font-extrabold text-slate-900 text-base leading-none mb-1.5">Syncing vibes</h4>
                <p className="text-sm text-slate-500 font-medium">Gathering preferences from the squad.</p>
              </div>
              {/* Step 3 */}
              <div className="relative pl-10 opacity-40">
                <div className="absolute left-0 top-0.5 size-7 rounded-full bg-slate-100 flex items-center justify-center text-slate-400 shadow-sm">
                  <Shield size={14} />
                </div>
                <h4 className="font-extrabold text-slate-900 text-base leading-none mb-1.5">Scouting destinations</h4>
                <p className="text-sm text-slate-500 font-medium">AI picks the best spots for your group.</p>
              </div>
            </div>
          </section>
        </div>
      </div>
    </main>
  )
}

export default TripLobby
