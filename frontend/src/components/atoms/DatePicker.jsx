import { Calendar } from "@/components/ui/calendar"
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover"
import { Calendar as CalendarIcon } from "lucide-react"
import { format, parseISO } from "date-fns"

export default function DatePicker({ value, onChange, placeholder = "Pick a date" }) {
  return (
    <Popover>
      <PopoverTrigger asChild>
        <button
          type="button"
          className="bg-transparent border-0 font-medium focus:ring-0 text-sm text-left text-gray-700 p-0 outline-none cursor-pointer flex items-center gap-2 w-full"
        >
          <CalendarIcon size={14} className="text-gray-400 flex-shrink-0" />
          {value ? (
            format(parseISO(value), "MMM dd, yyyy")
          ) : (
            <span className="text-gray-400 font-normal">{placeholder}</span>
          )}
        </button>
      </PopoverTrigger>
      <PopoverContent className="w-auto p-0 bg-white shadow-xl rounded-xl border border-slate-200 animate-in fade-in zoom-in duration-100" align="start">
        <Calendar
          mode="single"
          selected={value ? parseISO(value) : undefined}
          onSelect={(date) => {
            onChange(date ? format(date, "yyyy-MM-dd") : "")
          }}
          initialFocus
        />
      </PopoverContent>
    </Popover>
  )
}
