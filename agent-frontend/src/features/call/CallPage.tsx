import React from "react"
import { AlertCircle } from "lucide-react"

import { useOrders } from "@/features/orders/hooks/useOrders"
import { CallControls } from "./components/CallControls"
import { LiveOrderPanel } from "./components/LiveOrderPanel"
import { LiveTranscript } from "./components/LiveTranscript"
import { TryIdeas } from "./components/TryIdeas"
import { VoiceOrb } from "./components/VoiceOrb"
import { useVoiceCall } from "./useVoiceCall"

export const CallPage: React.FC = () => {
  const {
    callState,
    volume,
    isMuted,
    language,
    errorMessage,
    transcripts,
    setLanguage,
    startCall,
    endCall,
    toggleMute,
  } = useVoiceCall()

  const { orders, updateStatus, isUpdating } = useOrders()

  return (
    <div className="flex flex-col gap-6 p-4 md:p-6">
      {/* Alerta de error si ocurrió algún fallo de micrófono o conexión */}
      {errorMessage && (
        <div className="flex items-center gap-2 rounded-lg border border-destructive/40 bg-destructive/10 p-3 text-xs text-destructive">
          <AlertCircle className="size-4 shrink-0" />
          <span>{errorMessage}</span>
        </div>
      )}

      {/* Layout principal dividido */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-12">
        {/* Columna Izquierda: Voz, Controles y Transcripción */}
        <div className="flex flex-col gap-5 lg:col-span-7">
          {/* Tarjeta del Orbe de Voz y Controles */}
          <div className="flex flex-col items-center justify-center rounded-md border border-border bg-card p-6">
            <VoiceOrb state={callState} volume={volume} />

            <div className="mt-4 w-full">
              <CallControls
                state={callState}
                isMuted={isMuted}
                language={language}
                onStartCall={startCall}
                onEndCall={endCall}
                onToggleMute={toggleMute}
                onSetLanguage={setLanguage}
              />
            </div>
          </div>

          {/* Transcripción en vivo */}
          <div className="flex flex-col gap-2">
            <h3 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
              Conversación en vivo
            </h3>
            <LiveTranscript items={transcripts} />
          </div>

          {/* Sugerencias de qué probar */}
          <TryIdeas />
        </div>

        {/* Columna Derecha: Pedido armándose en vivo */}
        <div className="flex flex-col gap-5 lg:col-span-5">
          <LiveOrderPanel
            orders={orders}
            onUpdateStatus={(orderId, status) => updateStatus({ orderId, status })}
            isUpdating={isUpdating}
          />
        </div>
      </div>
    </div>
  )
}
export default CallPage
