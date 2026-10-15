import { beforeEach, describe, expect, it } from "vitest"
import { getSessionId, resetSessionId } from "./session"

describe("session manager", () => {
  beforeEach(() => {
    window.localStorage.clear()
  })

  it("genera un UUID válido compatible con el backend", () => {
    const id = getSessionId()
    expect(id).toMatch(/^[A-Za-z0-9_-]{16,64}$/)
    expect(id).toHaveLength(36)
  })

  it("reutiliza el mismo session_id en subsecuentes llamadas", () => {
    const id1 = getSessionId()
    const id2 = getSessionId()
    expect(id1).toBe(id2)
  })

  it("regenera una nueva sesión al llamar resetSessionId", () => {
    const id1 = getSessionId()
    const id2 = resetSessionId()
    expect(id1).not.toBe(id2)
    expect(getSessionId()).toBe(id2)
  })
})
