import { expect, test } from "@playwright/test"

test.describe("Tablero Kanban de Cocina y Pedidos", () => {
  test("navega a Cocina / Pedidos y visualiza las 3 columnas del tablero", async ({
    page,
  }) => {
    await page.goto("/")

    // Clic en pestaña Cocina / Pedidos
    const ordersTabBtn = page.getByRole("button", { name: /Cocina \/ Pedidos/i })
    await expect(ordersTabBtn).toBeVisible()
    await ordersTabBtn.click()

    // Encabezado del tablero
    await expect(page.getByText("Tablero de Cocina")).toBeVisible()

    // Las 3 columnas del Kanban
    await expect(page.getByRole("heading", { name: "Confirmados" })).toBeVisible()
    await expect(page.getByRole("heading", { name: "En preparación" })).toBeVisible()
    await expect(page.getByRole("heading", { name: "Listos" })).toBeVisible()

    // Verificar que los pedidos cargados desde el backend aparecen
    // (Lucía Rojas o pedidos sembrados)
    await expect(page.getByText(/Lucía Rojas|Ana García|Carlos Méndez/i).first()).toBeVisible({
      timeout: 5000,
    })
  })
})
