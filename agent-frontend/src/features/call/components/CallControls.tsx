import React from "react"
import { Loader2, Mic, MicOff, Phone, PhoneOff } from "lucide-react"

import { Button } from "@/components/ui/button"
import type { VoiceCallState } from "../adapters/voiceAdapter"

interface CallControlsProps {
  state: VoiceCallState
  isMuted: boolean
  language: "es" | "en"
  onStartCall: () => void
  onEndCall: () => void
  onToggleMute: () => void
  onSetLanguage: (lang: "es" | "en") => void
}

export const CallControls: React.FC<CallControlsProps> = ({
  state,
  isMuted,
  language,
  onStartCall,
  onEndCall,
  onToggleMute,
  onSetLanguage,
}) => {
  const isInCall = state === "listening" || state === "speaking"
  const isConnecting = state === "connecting"

  return (
    <div className="flex flex-col items-center gap-4">
      {/* Botones de acción principal */}
      <div className="flex items-center gap-3">
        {/* Botón de Silenciar Micrófono (solo visible durante llamada) */}
        {isInCall && (
          <Button
            type="button"
            variant={isMuted ? "destructive" : "secondary"}
            size="icon"
            onClick={onToggleMute}
            className="size-12 rounded-full shadow-md"
            title={isMuted ? "Reanudar micrófono" : "Silenciar micrófono"}
          >
            {isMuted ? <MicOff className="size-5" /> : <Mic className="size-5" />}
          </Button>
        )}

        {/* Botón Principal (Llamar / Colgar) */}
        {!isInCall && !isConnecting ? (
          <Button
            type="button"
            onClick={onStartCall}
            size="lg"
            className="h-14 gap-2.5 rounded-md px-8 text-base font-semibold"
          >
            <Phone className="size-5" />
            Llamar a Las Flamas
          </Button>
        ) : isConnecting ? (
          <Button
            disabled
            size="lg"
            className="h-14 gap-2.5 rounded-full px-8 text-base font-medium shadow-md"
          >
            <Loader2 className="size-5 animate-spin" />
            Conectando...
          </Button>
        ) : (
          <Button
            type="button"
            onClick={onEndCall}
            variant="destructive"
            size="lg"
            className="h-14 gap-2.5 rounded-full px-8 text-base font-semibold shadow-lg shadow-red-500/20 hover:scale-105"
          >
            <PhoneOff className="size-5" />
            Colgar llamada
          </Button>
        )}
      </div>

      {/* Selector de idioma del agente */}
      <div className="flex items-center gap-1.5 rounded-full border border-border/60 bg-muted/30 p-1 text-xs">
        <button
          type="button"
          onClick={() => onSetLanguage("es")}
          disabled={isInCall}
          className={`flex items-center gap-1 rounded-full px-3 py-1 font-medium transition-colors ${
            language === "es"
              ? "bg-background text-foreground shadow-sm"
              : "text-muted-foreground hover:text-foreground"
          }`}
        >
          <span>🇪🇸</span> Español
        </button>
        <button
          type="button"
          onClick={() => onSetLanguage("en")}
          disabled={isInCall}
          className={`flex items-center gap-1 rounded-full px-3 py-1 font-medium transition-colors ${
            language === "en"
              ? "bg-background text-foreground shadow-sm"
              : "text-muted-foreground hover:text-foreground"
          }`}
        >
          <span>🇺🇸</span> English
        </button>
      </div>
    </div>
  )
}
