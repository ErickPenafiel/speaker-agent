/** Marca de Las Flamas: una llama de tres lenguas hecha a mano, sin caja ni degradado. */
export function FlameMark({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 32 32" aria-hidden="true" className={className} fill="currentColor">
      <path d="M16 2c1 5 6 8 6 14a6 6 0 0 1-2 4.5c.4-2.6-.8-4.4-2.4-6C17 11 16 8 16 2Z" />
      <path d="M11 9c.4 4-3 6-3 11 0 3.5 2.2 6.4 5.4 7.4C11.700 25.200 12 22.800 13 21c-2.500-3.500-2-7-2-12Z" />
      <path d="M21.500 19.500c2 2 2.500 4 1.500 6.500a8 8 0 0 1-6 3.600c3-1.500 4-4.500 4.500-10.100Z" />
    </svg>
  )
}
