export interface VoiceCallConfig {
  sessionId: string
  language: "es" | "en"
}

export type VoiceCallState = "idle" | "connecting" | "listening" | "speaking"

export interface TranscriptMessage {
  id: string
  role: "user" | "assistant"
  text: string
  isFinal: boolean
  timestamp: number
}

export interface ToolCallEvent {
  toolName: string
  status: "running" | "completed" | "failed"
  message?: string
  orderId?: number
}

export type VoiceEventHandler<T = unknown> = (data: T) => void

export interface VoiceAdapter {
  start(config: VoiceCallConfig): Promise<void>
  stop(): Promise<void>
  setMuted(muted: boolean): void
  isMuted(): boolean

  on(event: "stateChange", cb: (state: VoiceCallState) => void): () => void
  on(event: "volume", cb: (volume: number) => void): () => void
  on(event: "transcript", cb: (msg: TranscriptMessage) => void): () => void
  on(event: "toolCall", cb: (tool: ToolCallEvent) => void): () => void
  on(event: "error", cb: (error: Error) => void): () => void

  destroy(): void
}
