import { useState, useRef, useEffect } from "react"
import { PlaneTakeoff, Search, ChevronDown, X } from "lucide-react"
import { US_AIRPORTS } from "@/constants/usAirports"

const AirportSelect = ({ value, onChange, placeholder = "Select your departure airport" }) => {
  const [open, setOpen]   = useState(false)
  const [query, setQuery] = useState("")
  const containerRef      = useRef(null)
  const inputRef          = useRef(null)

  const selected = US_AIRPORTS.find((a) => a.code === value) ?? null

  const filtered = (() => {
    const q = query.trim().toLowerCase()
    return (
      q
        ? US_AIRPORTS.filter(
            (a) =>
              a.code.toLowerCase().includes(q) ||
              a.name.toLowerCase().includes(q) ||
              a.city.toLowerCase().includes(q) ||
              a.state.toLowerCase().includes(q)
          )
        : US_AIRPORTS
    ).slice(0, 40)
  })()

  useEffect(() => {
    const handleOutside = (e) => {
      if (containerRef.current && !containerRef.current.contains(e.target)) {
        setOpen(false)
        setQuery("")
      }
    }
    document.addEventListener("mousedown", handleOutside)
    return () => document.removeEventListener("mousedown", handleOutside)
  }, [])

  const handleOpen = () => {
    setOpen(true)
    setQuery("")
    setTimeout(() => inputRef.current?.focus(), 50)
  }

  const handleSelect = (airport) => {
    onChange(airport.code)
    setOpen(false)
    setQuery("")
  }

  const handleClear = (e) => {
    e.stopPropagation()
    onChange("")
  }

  return (
    <div ref={containerRef} className="relative">
      {/* Trigger */}
      <button
        type="button"
        onClick={handleOpen}
        className="w-full flex items-center gap-2 border border-gray-200 rounded-xl px-3 py-2.5 bg-white/60 focus:border-primary focus:ring-2 focus:ring-primary/20 transition-all text-left"
      >
        <PlaneTakeoff size={14} className="text-gray-400 flex-shrink-0" />
        {selected ? (
          <span className="flex-1 text-sm text-gray-700 flex items-center gap-1.5 min-w-0">
            <span className="font-bold text-gray-900">{selected.code}</span>
            <span className="text-gray-500 truncate">— {selected.city}, {selected.state}</span>
          </span>
        ) : (
          <span className="flex-1 text-sm text-gray-400">{placeholder}</span>
        )}
        <span className="flex items-center gap-1 ml-auto flex-shrink-0">
          {selected && (
            <span
              role="button"
              tabIndex={0}
              onClick={handleClear}
              onKeyDown={(e) => e.key === "Enter" && handleClear(e)}
              className="p-0.5 rounded text-gray-400 hover:text-gray-600 transition-colors"
            >
              <X size={12} />
            </span>
          )}
          <ChevronDown
            size={13}
            className={`text-gray-400 transition-transform ${open ? "rotate-180" : ""}`}
          />
        </span>
      </button>

      {/* Dropdown */}
      {open && (
        <div className="absolute z-50 top-full left-0 right-0 mt-1.5 bg-white border border-gray-200 rounded-xl shadow-lg overflow-hidden">
          {/* Search bar */}
          <div className="flex items-center gap-2 px-3 py-2 border-b border-gray-100">
            <Search size={13} className="text-gray-400 flex-shrink-0" />
            <input
              ref={inputRef}
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Search by code, city, or name…"
              className="flex-1 text-sm text-gray-700 placeholder:text-gray-400 outline-none bg-transparent"
            />
            {query && (
              <button type="button" onClick={() => setQuery("")} className="text-gray-400 hover:text-gray-600">
                <X size={12} />
              </button>
            )}
          </div>

          {/* Options list */}
          <ul className="max-h-40 overflow-y-auto py-1">
            {filtered.length === 0 ? (
              <li className="px-3 py-2 text-sm text-gray-400 text-center">No airports found</li>
            ) : (
              filtered.map((airport) => (
                <li key={airport.code}>
                  <button
                    type="button"
                    onClick={() => handleSelect(airport)}
                    className={`w-full text-left px-3 py-1.5 flex items-center gap-3 hover:bg-gray-50 transition-colors ${
                      value === airport.code ? "bg-primary/10" : ""
                    }`}
                  >
                    <span className="text-xs font-black text-gray-900 w-9 flex-shrink-0">{airport.code}</span>
                    <span className="flex flex-col min-w-0">
                      <span className="text-sm text-gray-700 truncate">{airport.city}, {airport.state}</span>
                      <span className="text-[11px] text-gray-400 truncate">{airport.name}</span>
                    </span>
                  </button>
                </li>
              ))
            )}
          </ul>
        </div>
      )}
    </div>
  )
}

export default AirportSelect
