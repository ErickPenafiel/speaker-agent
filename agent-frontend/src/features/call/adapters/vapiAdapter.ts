import VapiModule from "@vapi-ai/web"
import type {
  ToolCallEvent,
  TranscriptMessage,
  VoiceAdapter,
  VoiceCallConfig,
  VoiceCallState,
} from "./voiceAdapter"

// El SDK es CommonJS (`exports.default = Vapi`): según el bundler el import por defecto llega como la
// clase o como el objeto del módulo, así que se normaliza.
type VapiInstance = InstanceType<typeof VapiModule>
const Vapi = (
  (VapiModule as unknown as { default?: typeof VapiModule }).default ?? VapiModule
) as typeof VapiModule

// Vapi emite objetos (`{ type, stage, error: { message, ... } }`), no `Error`: se busca el primer mensaje.
function toError(err: unknown): Error {
  if (err instanceof Error) return err
  const find = (v: unknown, depth = 0): string | undefined => {
    if (typeof v === "string") return v || undefined
    if (!v || typeof v !== "object" || depth > 3) return undefined
    const o = v as Record<string, unknown>
    for (const k of ["message", "errorMsg", "msg", "error"]) {
      const m = find(o[k], depth + 1)
      if (m) return m
    }
    return undefined
  }
  return new Error(find(err) ?? "Error desconocido en Vapi")
}

interface VapiAdapterOptions {
  publicKey: string
  assistantId: string
}

export class VapiAdapter implements VoiceAdapter {
  private vapi: VapiInstance
  private assistantId: string
  private listeners: {
    stateChange: Set<(state: VoiceCallState) => void>
    volume: Set<(vol: number) => void>
    transcript: Set<(msg: TranscriptMessage) => void>
    toolCall: Set<(tool: ToolCallEvent) => void>
    error: Set<(err: Error) => void>
  } = {
    stateChange: new Set(),
    volume: new Set(),
    transcript: new Set(),
    toolCall: new Set(),
    error: new Set(),
  }

  private currentState: VoiceCallState = "idle"
  private muted = false

  constructor({ publicKey, assistantId }: VapiAdapterOptions) {
    this.assistantId = assistantId
    this.vapi = new Vapi(publicKey)
    this.bindEvents()
  }

  private bindEvents() {
    this.vapi.on("call-start", () => {
      this.updateState("listening")
    })

    this.vapi.on("call-end", () => {
      this.updateState("idle")
      this.emitVolume(0)
    })

    this.vapi.on("speech-start", () => {
      this.updateState("speaking")
    })

    this.vapi.on("speech-end", () => {
      this.updateState("listening")
      this.emitVolume(0)
    })

    this.vapi.on("volume-level", (vol: number) => {
      // Normalizar a un rango de 0 a 1
      const normalized = Math.min(Math.max(vol, 0), 1)
      this.emitVolume(normalized)
    })

    this.vapi.on("message", (msg: unknown) => {
      if (!msg || typeof msg !== "object") return
      const raw = msg as Record<string, unknown>

      // 1. Mensajes de transcripción
      if (raw.type === "transcript") {
        const role = raw.role === "user" ? "user" : "assistant"
        const text = String(raw.transcript || raw.text || "")
        const isFinal = raw.transcriptType === "final"

        if (text.trim()) {
          this.emitTranscript({
            id: `${role}-${Date.now()}`,
            role,
            text,
            isFinal,
            timestamp: Date.now(),
          })
        }
      }

      // 2. Eventos de tool call / function call
      if (raw.type === "function-call" || raw.type === "tool-calls") {
        const functionCall = (raw.functionCall || {}) as Record<string, unknown>
        const name = String(functionCall.name || raw.name || "tool")

        this.emitToolCall({
          toolName: name,
          status: "completed",
          message: this.formatToolMessage(name),
        })
      }
    })

    this.vapi.on("error", (err: unknown) => {
      console.error("[vapi] error", err)
      this.emitError(toError(err))
      this.updateState("idle")
    })
  }

  private formatToolMessage(name: string): string {
    switch (name) {
      case "get_menu":
        return "Consultando opciones del menú..."
      case "create_order":
        return "Registrando pedido en cocina..."
      case "create_reservation":
        return "Confirmando reserva de mesa..."
      case "transfer_to_human":
        return "Transfiriendo a una persona del equipo..."
      default:
        return `Ejecutando ${name}...`
    }
  }

  private updateState(state: VoiceCallState) {
    if (this.currentState === state) return
    this.currentState = state
    for (const cb of this.listeners.stateChange) {
      cb(state)
    }
  }

  private emitVolume(vol: number) {
    for (const cb of this.listeners.volume) {
      cb(vol)
    }
  }

  private emitTranscript(msg: TranscriptMessage) {
    for (const cb of this.listeners.transcript) {
      cb(msg)
    }
  }

  private emitToolCall(tool: ToolCallEvent) {
    for (const cb of this.listeners.toolCall) {
      cb(tool)
    }
  }

  private emitError(err: Error) {
    for (const cb of this.listeners.error) {
      cb(err)
    }
  }

  async start(config: VoiceCallConfig): Promise<void> {
    this.updateState("connecting")
    try {
      await this.vapi.start(this.assistantId, {
        metadata: {
          sessionId: config.sessionId,
        },
        variableValues: {
          sessionId: config.sessionId,
          language: config.language,
        },
      })
    } catch (err) {
      this.updateState("idle")
      throw err instanceof Error ? err : new Error("No se pudo iniciar la llamada")
    }
  }

  async stop(): Promise<void> {
    try {
      this.vapi.stop()
    } finally {
      this.updateState("idle")
      this.emitVolume(0)
    }
  }

  setMuted(muted: boolean): void {
    this.muted = muted
    this.vapi.setMuted(muted)
  }

  isMuted(): boolean {
    return this.muted
  }

  on(event: "stateChange", cb: (state: VoiceCallState) => void): () => void
  on(event: "volume", cb: (volume: number) => void): () => void
  on(event: "transcript", cb: (msg: TranscriptMessage) => void): () => void
  on(event: "toolCall", cb: (tool: ToolCallEvent) => void): () => void
  on(event: "error", cb: (error: Error) => void): () => void
  on<K extends keyof typeof this.listeners>(
    event: K,
    cb: (typeof this.listeners)[K] extends Set<infer T> ? T : never
  ): () => void {
    const set = this.listeners[event]
    if (set) {
      set.add(cb as never)
      return () => set.delete(cb as never)
    }
    return () => {}
  }

  destroy(): void {
    this.stop().catch(() => {})
    for (const key of Object.keys(this.listeners) as (keyof typeof this.listeners)[]) {
      this.listeners[key].clear()
    }
  }
}
