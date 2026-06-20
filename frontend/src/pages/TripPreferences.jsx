import { useState } from "react"
import { useNavigate } from "react-router-dom"
import { Wallet, Luggage, Lock, Users, CalendarRange, PlusCircle, Trash2 } from "lucide-react"
import PreferenceSlider from "@/molecules/PreferenceSlider"
import AirportSelect from "@/atoms/AirportSelect"
import DatePicker from "@/atoms/DatePicker"

const DEFAULT_VIBES = [
  { key: "nightlife", label: "Nightlife", value: 50 },
  { key: "adventure", label: "Adventure", value: 75 },
  { key: "shopping", label: "Shopping", value: 25 },
  { key: "food", label: "Food & Dining", value: 100 },
  { key: "urban", label: "Urban Exploration", value: 50 },
  { key: "nature", label: "Nature & Outdoors", value: 50 },
]

const TripPreferences = () => {
  const navigate = useNavigate()
  const [vibes, setVibes] = useState(DEFAULT_VIBES)
  const [airport, setAirport] = useState("")
  const [budget, setBudget] = useState("")
  const [carryOn, setCarryOn] = useState(false)
  const [notes, setNotes] = useState("")

  // Date windows list state
  const [dateWindows, setDateWindows] = useState([
    { start_date: "2026-07-15", end_date: "2026-07-30" },
    { start_date: "2026-08-05", end_date: "2026-08-20" }
  ])

  const updateVibe = (key, value) =>
    setVibes((prev) => prev.map((v) => (v.key === key ? { ...v, value } : v)))

  const addDateWindow = () => {
    setDateWindows((prev) => [...prev, { start_date: "", end_date: "" }])
  }

  const removeDateWindow = (index) => {
    setDateWindows((prev) => prev.filter((_, i) => i !== index))
  }

  const updateDateWindow = (index, field, value) => {
    setDateWindows((prev) =>
      prev.map((d, i) => (i === index ? { ...d, [field]: value } : d))
    )
  }

  const handleSubmit = (e) => {
    e.preventDefault()
    const tripId = sessionStorage.getItem("currentTripId")
    if (tripId) {
      navigate(`/trips/${tripId}/lobby`)
    } else {
      navigate("/dashboard")
    }
  }

  // Validate form required fields (Personal Notes is optional)
  const isFormValid =
    airport &&
    budget &&
    dateWindows.length > 0 &&
    dateWindows.every((w) => w.start_date && w.end_date)

  return (
    <main className="flex-1 min-h-0 overflow-y-auto px-8 pb-8 pt-2">
      <div className="max-w-3xl mx-auto">

        {/* Title Header */}
        <div className="mb-6">
          <p className="text-[11px] font-bold uppercase tracking-widest text-gray-400 mb-1">
            Personalize your journey
          </p>
          <h1 className="text-4xl font-black text-gray-900 italic leading-tight">
            Trip Preferences
          </h1>
        </div>

        {/* Form Container */}
        <form onSubmit={handleSubmit} className="flex flex-col gap-4">

          {/* Scrollable Options Container (Constrained to max height) */}
          <div className="max-h-[520px] overflow-y-auto pr-2 space-y-4 mb-2 border-b border-slate-100 pb-4 min-h-0">

            {/* Travel Vibes */}
            <section className="bg-white/40 backdrop-blur-md rounded-2xl border border-white/60 p-6 shadow-sm">
              <h2 className="text-lg font-black text-gray-800 italic mb-5">Travel Vibes</h2>
              <div className="grid grid-cols-2 gap-x-10 gap-y-6">
                {vibes.map(({ key, label, value }) => (
                  <PreferenceSlider
                    key={key}
                    label={label}
                    value={value}
                    onChange={(v) => updateVibe(key, v)}
                  />
                ))}
              </div>
            </section>

            {/* Date Windows */}
            <section className="bg-white/40 backdrop-blur-md rounded-2xl border border-white/60 p-6 shadow-sm">
              <h2 className="text-lg font-black text-gray-800 italic flex items-center gap-2 mb-5">
                <CalendarRange size={20} className="text-primary" />
                Date Windows
              </h2>

              {/* Scrollable date window list */}
              <div className="space-y-3 mb-4 max-h-[165px] overflow-y-auto pr-1">
                {dateWindows.map((window, idx) => (
                  <div key={idx} className="flex items-center gap-4 p-4 rounded-xl bg-white/40 border border-slate-200/50 shadow-sm">
                    <div className="flex-grow grid grid-cols-2 gap-4">
                      <div className="flex flex-col">
                        <label className="block text-[10px] font-bold uppercase tracking-widest text-gray-400 mb-1">Start Date</label>
                        <DatePicker
                          value={window.start_date}
                          onChange={(date) => updateDateWindow(idx, "start_date", date)}
                          placeholder="Pick start date"
                        />
                      </div>
                      <div className="flex flex-col">
                        <label className="block text-[10px] font-bold uppercase tracking-widest text-gray-400 mb-1">End Date</label>
                        <DatePicker
                          value={window.end_date}
                          onChange={(date) => updateDateWindow(idx, "end_date", date)}
                          placeholder="Pick end date"
                        />
                      </div>
                    </div>
                    <button
                      type="button"
                      onClick={() => removeDateWindow(idx)}
                      className="text-slate-400 hover:text-red-500 transition-colors self-end pb-1"
                    >
                      <Trash2 size={18} />
                    </button>
                  </div>
                ))}
              </div>

              <button
                type="button"
                onClick={addDateWindow}
                className="w-full py-4 border-2 border-dashed border-primary/45 hover:border-primary rounded-xl text-primary font-bold hover:bg-primary/5 transition-all flex items-center justify-center gap-2 text-sm"
              >
                <PlusCircle size={16} />
                Add Another Date Range
              </button>
            </section>

            {/* Logistics + Personal Notes */}
            <div className="grid grid-cols-2 gap-4">
              <section className="bg-white/40 backdrop-blur-md rounded-2xl border border-white/60 p-6 flex flex-col gap-4 shadow-sm">
                <h2 className="text-lg font-black text-gray-800 italic">Logistics</h2>

                <div>
                  <label className="block text-[11px] font-bold uppercase tracking-widest text-gray-400 mb-2">
                    Starting Airport
                  </label>
                  <AirportSelect
                    value={airport}
                    onChange={setAirport}
                    placeholder="Select your departure airport"
                  />
                </div>

                <div>
                  <label className="block text-[11px] font-bold uppercase tracking-widest text-gray-400 mb-2">
                    Total Budget (USD)
                  </label>
                  <div className="flex items-center gap-2 border border-gray-200 rounded-xl px-3 py-2.5 bg-white/60 focus-within:border-primary focus-within:ring-2 focus-within:ring-primary/20 transition-all">
                    <Wallet size={14} className="text-gray-400 flex-shrink-0" />
                    <input
                      type="number"
                      value={budget}
                      onChange={(e) => setBudget(e.target.value)}
                      placeholder="$500"
                      className="flex-1 bg-transparent text-sm text-slate-700 placeholder:text-slate-400 outline-none"
                      required
                    />
                  </div>
                </div>

                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2 text-sm font-semibold text-gray-700">
                    <Luggage size={15} className="text-gray-400" />
                    Carry-on Only
                  </div>
                  <button
                    type="button"
                    onClick={() => setCarryOn((v) => !v)}
                    className={`relative w-10 h-5 rounded-full transition-colors ${carryOn ? "bg-primary" : "bg-gray-200"}`}
                  >
                    <span
                      className={`absolute top-0.5 left-0.5 w-4 h-4 rounded-full bg-white shadow transition-transform ${carryOn ? "translate-x-5" : "translate-x-0"}`}
                    />
                  </button>
                </div>
              </section>

              <section className="bg-white/40 backdrop-blur-md rounded-2xl border border-white/60 p-6 flex flex-col gap-4 shadow-sm">
                <h2 className="text-lg font-black text-gray-800 italic">Personal Notes</h2>
                <div className="flex flex-col flex-1">
                  <label className="block text-[11px] font-bold uppercase tracking-widest text-gray-400 mb-2">
                    Special Requirements
                  </label>
                  <textarea
                    value={notes}
                    onChange={(e) => setNotes(e.target.value)}
                    placeholder="Any allergies, mobility needs, or must-see spots?"
                    rows={6}
                    className="flex-1 w-full border border-gray-200 rounded-xl px-3 py-2.5 bg-white/60 focus:border-primary focus:ring-2 focus:ring-primary/20 text-sm text-gray-700 placeholder:text-gray-400 outline-none resize-none transition-all"
                  />
                </div>
              </section>
            </div>
          </div>

          {/* Action Footer button directly below the container */}
          <div className="flex justify-end mt-2 shrink-0">
            <button
              type="submit"
              disabled={!isFormValid}
              className="px-8 py-3 rounded-xl bg-primary text-black font-bold text-sm hover:bg-primary-dim transition-colors volt-glow disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:bg-primary"
            >
              Save Preferences
            </button>
          </div>

        </form>

        <div className="flex items-center justify-center gap-6 mt-4 text-xs text-gray-400 shrink-0">
          <span className="flex items-center gap-1.5"><Lock size={11} /> End-to-end encrypted</span>
          <span className="flex items-center gap-1.5"><Users size={11} /> Shared with your squad</span>
        </div>

      </div>
    </main>
  )
}

export default TripPreferences
