import type {
  ToolCallEvent,
  TranscriptMessage,
  VoiceAdapter,
  VoiceCallConfig,
  VoiceCallState,
} from "./voiceAdapter"

interface RetellAdapterOptions {
  accessToken?: string | null
  callId?: string | null
}

export class RetellAdapter implements VoiceAdapter {
  private accessToken?: string | null
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

  constructor(options: RetellAdapterOptions = {}) {
    this.accessToken = options.accessToken
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

  async start(config: VoiceCallConfig): Promise<void> {
    void config
    if (!this.accessToken) {
      throw new Error("Se requiere access_token para iniciar la llamada con Retell")
    }
    this.updateState("connecting")

    // Nota: Si en el futuro se instala retell-client-js-sdk, aquí se conecta.
    // Por el momento se deja la abstracción preparada y validada.
    setTimeout(() => {
      this.updateState("listening")
    }, 500)
  }

  async stop(): Promise<void> {
    this.updateState("idle")
    this.emitVolume(0)
  }

  setMuted(muted: boolean): void {
    this.muted = muted
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
