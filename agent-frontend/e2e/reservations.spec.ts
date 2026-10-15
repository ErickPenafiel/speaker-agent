import { expect, test } from "@playwright/test"

test.describe("Página de Reservas", () => {
  test("navega a Reservas y visualiza el libro de reservas con datos del backend", async ({
    page,
  }) => {
    await page.goto("/")

    // Clic en pestaña Reservas
    const reservationsTabBtn = page.getByRole("button", { name: "Reservas" })
    await expect(reservationsTabBtn).toBeVisible()
    await reservationsTabBtn.click()

    // Encabezado
    await expect(page.getByText("Libro de Reservas")).toBeVisible()
    await expect(
      page.getByText("Mesas agendadas por el asistente en tiempo real")
    ).toBeVisible()

    // Comprobar que carga reservas existentes del backend (ej: Familia Vargas)
    await expect(page.getByText(/Familia Vargas|Carlos Méndez|Lucía Rojas/i).first()).toBeVisible({
      timeout: 5000,
    })
  })
})
