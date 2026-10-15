import { getSessionId } from "./session"
import type {
  Call,
  CallDetail,
  CallOutcome,
  MenuItem,
  Order,
  OrderStatus,
  Reservation,
  VoiceConfig,
  WebCallInfo,
  WebCallParams,
} from "./types"

const API_BASE_URL = (import.meta.env.VITE_API_URL || "").replace(/\/$/, "")

export class ApiClientError extends Error {
  status: number
  retryAfter?: number

  constructor(message: string, status: number, retryAfter?: number) {
    super(message)
    this.name = "ApiClientError"
    this.status = status
    this.retryAfter = retryAfter
  }

  get isRateLimit(): boolean {
    return this.status === 429
  }

  get isForbiddenDemo(): boolean {
    return this.status === 403
  }

  get isServiceUnavailable(): boolean {
    return this.status === 503
  }
}

interface RequestOptions extends RequestInit {
  includeSession?: boolean
  params?: Record<string, string | number | undefined | null>
}

async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const { includeSession = true, params, headers: customHeaders, ...fetchOptions } = options

  let url = `${API_BASE_URL}${path}`
  if (params) {
    const searchParams = new URLSearchParams()
    for (const [key, val] of Object.entries(params)) {
      if (val !== undefined && val !== null) {
        searchParams.append(key, String(val))
      }
    }
    const qs = searchParams.toString()
    if (qs) {
      url += (url.includes("?") ? "&" : "?") + qs
    }
  }

  const headers = new Headers(customHeaders)
  if (!headers.has("Content-Type") && fetchOptions.body && typeof fetchOptions.body === "string") {
    headers.set("Content-Type", "application/json")
  }

  if (includeSession) {
    headers.set("X-Session-Id", getSessionId())
  }

  let res: Response
  try {
    res = await fetch(url, {
      ...fetchOptions,
      headers,
    })
  } catch (err) {
    throw new ApiClientError(
      err instanceof Error ? err.message : "Error de conexión con el servidor",
      0
    )
  }

  if (!res.ok) {
    let errorMessage = `Error HTTP ${res.status}`
    try {
      const data = await res.json()
      if (data && typeof data === "object" && "detail" in data) {
        errorMessage = String(data.detail)
      }
    } catch {
      // Si la respuesta no es JSON válido
    }

    const retryAfterHeader = res.headers.get("Retry-After")
    const retryAfter = retryAfterHeader ? Number.parseInt(retryAfterHeader, 10) : undefined

    throw new ApiClientError(errorMessage, res.status, retryAfter)
  }

  return res.json() as Promise<T>
}

// ==========================================
// API Endpoints
// ==========================================
export const api = {
  // Salud y preparación
  async getHealth(): Promise<{ status: string }> {
    return request<{ status: string }>("/health", { includeSession: false })
  },

  async getHealthReady(): Promise<{ status: string; db: string }> {
    return request<{ status: string; db: string }>("/health/ready", { includeSession: false })
  },

  // Menú
  async getMenu(): Promise<MenuItem[]> {
    return request<MenuItem[]>("/menu", { includeSession: false })
  },

  // Voz
  async getVoiceConfig(): Promise<VoiceConfig> {
    return request<VoiceConfig>("/voice/config", { includeSession: false })
  },

  async createWebCall(params?: Partial<WebCallParams>): Promise<WebCallInfo> {
    const sessionId = params?.session_id || getSessionId()
    return request<WebCallInfo>("/voice/web-call", {
      method: "POST",
      includeSession: false,
      body: JSON.stringify({
        session_id: sessionId,
        language: params?.language || "es",
      }),
    })
  },

  // Pedidos (Requiere X-Session-Id)
  async getOrders(params?: { limit?: number; offset?: number; since?: string }): Promise<Order[]> {
    return request<Order[]>("/orders", {
      includeSession: true,
      params,
    })
  },

  async updateOrderStatus(orderId: string, status: OrderStatus): Promise<Order> {
    return request<Order>(`/orders/${orderId}/status`, {
      method: "PATCH",
      includeSession: true,
      body: JSON.stringify({ status }),
    })
  },

  // Reservas (Requiere X-Session-Id)
  async getReservations(params?: {
    limit?: number
    offset?: number
    since?: string
    date_from?: string
    date_to?: string
  }): Promise<Reservation[]> {
    return request<Reservation[]>("/reservations", {
      includeSession: true,
      params,
    })
  },

  // Llamadas (Requiere X-Session-Id)
  async getCalls(params?: {
    limit?: number
    offset?: number
    since?: string
    outcome?: CallOutcome
  }): Promise<Call[]> {
    return request<Call[]>("/calls", {
      includeSession: true,
      params,
    })
  },

  async getCallDetail(callId: string): Promise<CallDetail> {
    return request<CallDetail>(`/calls/${callId}`, {
      includeSession: true,
    })
  },
}
