// ==========================================
// 1. Menú
// ==========================================
export interface MenuItem {
  id: string
  name: string
  category: string
  description: string | null
  price: string | number
  allergens: string[]
  available: boolean
}

// ==========================================
// 2. Pedidos (Cocina Kanban)
// ==========================================
export type OrderStatus = "confirmed" | "preparing" | "ready"

export interface OrderLine {
  name: string
  quantity: number
  unit_price: string | number
  options?: Record<string, unknown> | null
  notes?: string | null
}

export interface Order {
  id: string
  number: number
  call_id: string | null
  customer_name: string
  type: "pickup" | "delivery"
  address: string | null
  status: OrderStatus
  notes: string | null
  total: string | number
  created_at: string
  items: OrderLine[]
  is_demo: boolean
}

// ==========================================
// 3. Reservas
// ==========================================
export interface Reservation {
  id: string
  call_id: string | null
  customer_name: string
  party_size: number
  date: string // YYYY-MM-DD
  time: string // HH:MM
  notes: string | null
  created_at: string
  is_demo: boolean
}

// ==========================================
// 4. Llamadas y Transcripción
// ==========================================
export type CallOutcome = "order" | "reservation" | "transferred" | "info" | "abandoned"

export interface TranscriptTurn {
  role: "user" | "assistant"
  text: string
}

export interface Call {
  id: string
  provider: "vapi" | "retell"
  provider_call_id: string
  started_at: string | null
  duration_seconds: number | null
  outcome: CallOutcome | null
  summary: string | null
  created_at: string
  is_demo: boolean
}

export interface TransferInfo {
  id: string
  reason: string
  created_at: string
}

export interface CallDetail extends Call {
  transcript: TranscriptTurn[]
  orders: Order[]
  reservations: Reservation[]
  transfers: TransferInfo[]
}

// ==========================================
// 5. Configuración de Voz y Web Call
// ==========================================
export interface VoiceConfig {
  provider: "vapi" | "retell"
}

export interface WebCallInfo {
  provider: "vapi" | "retell"
  public_key?: string | null
  assistant_id?: string | null
  access_token?: string | null
  call_id?: string | null
  metadata?: Record<string, string>
}

export interface WebCallParams {
  session_id: string
  language?: "es" | "en"
}

// ==========================================
// 6. Transcripción en vivo y Eventos de UI
// ==========================================
export type VoiceCallState = "idle" | "connecting" | "listening" | "speaking"

export interface LiveTranscriptItem {
  id: string
  role: "user" | "assistant"
  text: string
  isFinal: boolean
  timestamp: number
}

export interface LiveToolNotification {
  id: string
  toolName: string
  status: "running" | "completed" | "failed"
  message: string
  timestamp: number
}
