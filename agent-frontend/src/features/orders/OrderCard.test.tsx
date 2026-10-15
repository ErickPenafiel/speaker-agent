import { cleanup, fireEvent, render, screen } from "@testing-library/react"
import { afterEach, describe, expect, it, vi } from "vitest"

import type { Order } from "@/lib/types"
import { OrderCard } from "./components/OrderCard"

describe("OrderCard", () => {
  afterEach(cleanup)

  const mockOrder: Order = {
    id: "ord-123",
    number: 14,
    call_id: "call-1",
    customer_name: "Ana García",
    type: "pickup",
    address: null,
    status: "confirmed",
    notes: "Bien cocido",
    total: 108.5,
    created_at: new Date().toISOString(),
    items: [
      { name: "Plato Principal", quantity: 1, unit_price: 78.5 },
      { name: "Bebida Especial", quantity: 2, unit_price: 15.0 },
    ],
    is_demo: false,
  }

  it("renderiza correctamente el número de pedido, cliente y platos", () => {
    render(<OrderCard order={mockOrder} onUpdateStatus={vi.fn()} />)

    expect(screen.getByText("#14")).toBeDefined()
    expect(screen.getByText("Ana García")).toBeDefined()
    expect(screen.getByText("Para recoger")).toBeDefined()
    expect(screen.getByText("Plato Principal")).toBeDefined()
    expect(screen.getByText("Bebida Especial")).toBeDefined()
    expect(screen.getByText("Bs 108.50")).toBeDefined()
  })

  it("dispara onUpdateStatus con el siguiente estado al pulsar el botón", () => {
    const handleUpdate = vi.fn()
    render(<OrderCard order={mockOrder} onUpdateStatus={handleUpdate} />)

    const button = screen.getByRole("button", { name: /preparar/i })
    fireEvent.click(button)

    expect(handleUpdate).toHaveBeenCalledWith("ord-123", "preparing")
  })

  it("deshabilita el botón de acción si el pedido es de demostración (is_demo: true)", () => {
    const demoOrder = { ...mockOrder, is_demo: true }
    render(<OrderCard order={demoOrder} onUpdateStatus={vi.fn()} />)

    const button = screen.getByRole("button", { name: /solo lectura/i })
    expect(button.hasAttribute("disabled")).toBe(true)
  })
})
