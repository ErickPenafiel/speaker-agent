import { cleanup, render, screen } from "@testing-library/react"
import { afterEach, describe, expect, it } from "vitest"

import { VoiceOrb } from "./components/VoiceOrb"

describe("VoiceOrb", () => {
  afterEach(cleanup)

  it("muestra el mensaje de estado inactivo (idle)", () => {
    render(<VoiceOrb state="idle" volume={0} />)
    expect(screen.getByText("Las Flamas, a la orden")).toBeDefined()
  })

  it("muestra el mensaje de estado conectando (connecting)", () => {
    render(<VoiceOrb state="connecting" volume={0} />)
    expect(screen.getByText("Marcando...")).toBeDefined()
  })

  it("muestra el mensaje de estado escuchando (listening)", () => {
    render(<VoiceOrb state="listening" volume={0} />)
    expect(screen.getByText("Te escuchamos")).toBeDefined()
  })

  it("muestra el mensaje de estado hablando (speaking)", () => {
    render(<VoiceOrb state="speaking" volume={0.8} />)
    expect(screen.getByText("Está hablando")).toBeDefined()
  })
})
