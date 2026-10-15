import { useCallback, useEffect, useReducer, useRef, useState } from "react"
import { useQueryClient } from "@tanstack/react-query"
import { toast } from "sonner"

import { api, ApiClientError } from "@/lib/api"
import { getSessionId } from "@/lib/session"
import { RetellAdapter } from "./adapters/retellAdapter"
import { VapiAdapter } from "./adapters/vapiAdapter"
import type {
  VoiceAdapter,
  VoiceCallState,
} from "./adapters/voiceAdapter"
import {
  initialTranscriptState,
  transcriptReducer,
} from "./transcriptReducer"

export function useVoiceCall() {
  const queryClient = useQueryClient()
  const [callState, setCallState] = useState<VoiceCallState>("idle")
  const [volume, setVolume] = useState<number>(0)
  const [isMuted, setIsMuted] = useState<boolean>(false)
  const [language, setLanguage] = useState<"es" | "en">("es")
  const [errorMessage, setErrorMessage] = useState<string | null>(null)

  const [transcriptState, dispatch] = useReducer(
    transcriptReducer,
    initialTranscriptState
  )

  const adapterRef = useRef<VoiceAdapter | null>(null)
  const wakeLockRef = useRef<WakeLockSentinel | null>(null)

  // Manejo de Screen Wake Lock para dispositivos móviles
  const requestWakeLock = useCallback(async () => {
    if ("wakeLock" in navigator && !wakeLockRef.current) {
      try {
        wakeLockRef.current = await navigator.wakeLock.request("screen")
      } catch {
        // En algunos navegadores o niveles de batería bajos puede fallar silenciosamente
      }
    }
  }, [])

  const releaseWakeLock = useCallback(async () => {
    if (wakeLockRef.current) {
      try {
        await wakeLockRef.current.release()
      } catch {
        // Ignorar error al liberar
      }
      wakeLockRef.current = null
    }
  }, [])

  // Limpiar instancia previa
  const cleanupAdapter = useCallback(() => {
    if (adapterRef.current) {
      adapterRef.current.destroy()
      adapterRef.current = null
    }
    releaseWakeLock()
  }, [releaseWakeLock])

  const startCall = useCallback(async () => {
    setErrorMessage(null)
    dispatch({ type: "CLEAR" })
    cleanupAdapter()

    // 1. Validar acceso a micrófono
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      // Liberar el stream de prueba inmediato
      for (const track of stream.getTracks()) {
        track.stop()
      }
    } catch (err: unknown) {
      const isPermissionDenied =
        err instanceof DOMException &&
        (err.name === "NotAllowedError" || err.name === "PermissionDeniedError")

      const msg = isPermissionDenied
        ? "El acceso al micrófono fue denegado. Habilita los permisos en tu navegador para continuar."
        : "No se detectó un micrófono disponible en tu dispositivo."

      setErrorMessage(msg)
      toast.error(msg)
      return
    }

    setCallState("connecting")

    // 2. Obtener credenciales de llamada web desde el backend
    try {
      const webCallInfo = await api.createWebCall({
        session_id: getSessionId(),
        language,
      })

      let adapter: VoiceAdapter

      if (webCallInfo.provider === "vapi") {
        const publicKey =
          webCallInfo.public_key || import.meta.env.VITE_VAPI_PUBLIC_KEY
        const assistantId =
          webCallInfo.assistant_id || import.meta.env.VITE_VAPI_ASSISTANT_ID

        if (!publicKey || !assistantId) {
          throw new Error(
            "Faltan credenciales de Vapi (public_key o assistant_id)"
          )
        }

        adapter = new VapiAdapter({ publicKey, assistantId })
      } else {
        adapter = new RetellAdapter({
          accessToken: webCallInfo.access_token,
          callId: webCallInfo.call_id,
        })
      }

      adapterRef.current = adapter

      // 3. Suscribir listeners normalizados
      adapter.on("stateChange", (state) => {
        setCallState(state)
        if (state === "idle") {
          releaseWakeLock()
          // Al terminar la llamada, invalidar queries del panel para mostrar resultados finales
          queryClient.invalidateQueries({ queryKey: ["calls"] })
          queryClient.invalidateQueries({ queryKey: ["orders"] })
          queryClient.invalidateQueries({ queryKey: ["reservations"] })
        }
      })

      adapter.on("volume", (vol) => {
        setVolume(vol)
      })

      adapter.on("transcript", (msg) => {
        dispatch({ type: "ADD_TRANSCRIPT", payload: msg })
      })

      adapter.on("toolCall", (tool) => {
        dispatch({ type: "ADD_TOOL", payload: tool })
        // Si el agente ejecuta una herramienta, invalidar inmediatamente
        if (tool.toolName === "create_order") {
          queryClient.invalidateQueries({ queryKey: ["orders"] })
        } else if (tool.toolName === "create_reservation") {
          queryClient.invalidateQueries({ queryKey: ["reservations"] })
        }
      })

      adapter.on("error", (err) => {
        setErrorMessage(err.message)
        toast.error(`Error en la llamada: ${err.message}`)
        setCallState("idle")
        releaseWakeLock()
      })

      // 4. Activar Wake Lock e iniciar llamada
      await requestWakeLock()
      await adapter.start({
        sessionId: getSessionId(),
        language,
      })
    } catch (err: unknown) {
      cleanupAdapter()
      setCallState("idle")

      let msg = "Error al iniciar la llamada."
      if (err instanceof ApiClientError) {
        if (err.isRateLimit) {
          msg = `Has alcanzado el límite de llamadas permitidas.${
            err.retryAfter ? ` Espera ${err.retryAfter}s.` : ""
          }`
        } else {
          msg = err.message
        }
      } else if (err instanceof Error) {
        msg = err.message
      }

      setErrorMessage(msg)
      toast.error(msg)
    }
  }, [
    language,
    cleanupAdapter,
    queryClient,
    requestWakeLock,
    releaseWakeLock,
  ])

  const endCall = useCallback(async () => {
    if (adapterRef.current) {
      await adapterRef.current.stop()
    }
    setCallState("idle")
    setVolume(0)
    cleanupAdapter()

    // Invalidación con reintento leve para absorber la latencia del webhook del proveedor
    queryClient.invalidateQueries({ queryKey: ["calls"] })
    queryClient.invalidateQueries({ queryKey: ["orders"] })
    queryClient.invalidateQueries({ queryKey: ["reservations"] })
  }, [cleanupAdapter, queryClient])

  const toggleMute = useCallback(() => {
    if (adapterRef.current) {
      const nextMuted = !isMuted
      adapterRef.current.setMuted(nextMuted)
      setIsMuted(nextMuted)
    }
  }, [isMuted])

  // Limpieza al desmontar componente
  useEffect(() => {
    return () => {
      cleanupAdapter()
    }
  }, [cleanupAdapter])

  return {
    callState,
    volume,
    isMuted,
    language,
    errorMessage,
    transcripts: transcriptState.items,
    setLanguage,
    startCall,
    endCall,
    toggleMute,
    isInCall: callState === "listening" || callState === "speaking" || callState === "connecting",
  }
}
