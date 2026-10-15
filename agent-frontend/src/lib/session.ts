const STORAGE_KEY = "speaker_agent_session_id"

/**
 * Retorna el session_id del visitante actual.
 * Si no existe o es inválido, genera uno nuevo usando crypto.randomUUID().
 * El ID debe tener entre 16 y 64 caracteres [A-Za-z0-9_-] según el backend.
 */
export function getSessionId(): string {
  if (typeof window === "undefined") {
    return "00000000-0000-0000-0000-000000000000"
  }

  try {
    const existing = window.localStorage.getItem(STORAGE_KEY)
    if (existing && /^[A-Za-z0-9_-]{16,64}$/.test(existing)) {
      return existing
    }

    const newId = crypto.randomUUID()
    window.localStorage.setItem(STORAGE_KEY, newId)
    return newId
  } catch {
    // Si localStorage está bloqueado o en modo incógnito estricto
    return crypto.randomUUID()
  }
}

/**
 * Regenera la sesión del visitante (útil para reiniciar datos en pruebas).
 */
export function resetSessionId(): string {
  if (typeof window === "undefined") {
    return "00000000-0000-0000-0000-000000000000"
  }
  const newId = crypto.randomUUID()
  try {
    window.localStorage.setItem(STORAGE_KEY, newId)
  } catch {
    // ignorar error de almacenamiento
  }
  return newId
}
