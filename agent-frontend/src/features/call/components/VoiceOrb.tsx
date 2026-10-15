import React from "react"
import { motion } from "motion/react"
import type { VoiceCallState } from "../adapters/voiceAdapter"

interface VoiceOrbProps {
  state: VoiceCallState
  volume: number // 0.0 a 1.0
}

// Alturas base de las barras: una onda irregular, no una simetría perfecta
const BARS = [0.35, 0.6, 0.45, 0.9, 0.7, 1, 0.55, 0.8, 0.4, 0.65, 0.3]

const LABELS: Record<VoiceCallState, { title: string; hint: string }> = {
  idle: {
    title: "Las Flamas, a la orden",
    hint: "Toca «Llamar» y pide como en el local: tu pedido o tu mesa.",
  },
  connecting: { title: "Marcando...", hint: "Un segundo, ya te atienden." },
  listening: { title: "Te escuchamos", hint: "Habla con calma, como en el mostrador." },
  speaking: { title: "Está hablando", hint: "Escucha lo que te confirma." },
}

export const VoiceOrb: React.FC<VoiceOrbProps> = ({ state, volume }) => {
  const active = state === "speaking" || state === "listening"

  return (
    <div className="flex flex-col items-center p-4">
      <div
        className="flex h-24 items-center justify-center gap-1.5"
        role="img"
        aria-label={LABELS[state].title}
      >
        {BARS.map((base, i) => {
          const speaking = state === "speaking" ? Math.max(0.15, base * (0.25 + volume * 1.1)) : 0
          const height =
            state === "speaking"
              ? speaking
              : state === "listening"
                ? [0.12, 0.12 + base * 0.22, 0.12]
                : state === "connecting"
                  ? [0.1, base * 0.5, 0.1]
                  : 0.08
          return (
            <motion.span
              key={i}
              className={`w-1.5 origin-center rounded-sm ${
                state === "speaking" ? "bg-primary" : active ? "bg-ember" : "bg-border"
              }`}
              style={{ height: "100%" }}
              animate={{ scaleY: height }}
              transition={
                state === "speaking"
                  ? { duration: 0.09, ease: "easeOut" }
                  : { duration: 1.1, repeat: Infinity, delay: i * 0.07, ease: "easeInOut" }
              }
            />
          )
        })}
      </div>

      <div className="mt-4 flex flex-col items-center text-center">
        <span className="font-heading text-xl font-medium text-foreground">
          {LABELS[state].title}
        </span>
        <span className="mt-1 max-w-xs text-sm text-muted-foreground">{LABELS[state].hint}</span>
      </div>
    </div>
  )
}
