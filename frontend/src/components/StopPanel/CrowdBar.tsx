const BUS_CAPACITY = 60

interface Props {
  passengers: number
}

export default function CrowdBar({ passengers }: Props) {
  const pct = Math.min(100, Math.round((passengers / BUS_CAPACITY) * 100))
  const color =
    pct < 40 ? 'bg-green-500' : pct < 80 ? 'bg-yellow-400' : 'bg-red-500'

  return (
    <div>
      <div className="flex justify-between text-xs text-gray-500 mb-1">
        <span>Crowd level</span>
        <span>{passengers} / {BUS_CAPACITY} passengers</span>
      </div>
      <div className="w-full bg-gray-200 rounded-full h-3">
        <div
          className={`${color} h-3 rounded-full transition-all duration-300`}
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  )
}
