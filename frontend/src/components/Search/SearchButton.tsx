interface Props {
  onClick: () => void
}

export default function SearchButton({ onClick }: Props) {
  return (
    <button
      onClick={onClick}
      aria-label="Yer ara"
      className="
        absolute top-3 right-3 z-[1000]
        w-10 h-10 rounded-full bg-white shadow-md
        flex items-center justify-center
        hover:bg-gray-50 active:scale-95 transition-transform
        border border-gray-200
      "
    >
      <svg xmlns="http://www.w3.org/2000/svg" className="w-5 h-5 text-gray-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
        <circle cx="11" cy="11" r="8" />
        <path strokeLinecap="round" d="M21 21l-4.35-4.35" />
      </svg>
    </button>
  )
}
