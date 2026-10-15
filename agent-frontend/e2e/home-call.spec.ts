import { expect, test } from "@playwright/test"

test.describe("Pantalla Principal y Asistente de Voz", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/")
  })

  test("carga la página principal con la marca y el título", async ({ page }) => {
    await expect(page).toHaveTitle(/Las Flamas/)
    await expect(page.getByText("Las Flamas", { exact: true }).first()).toBeVisible()
    await expect(page.getByText("Parrilla boliviana", { exact: true })).toBeVisible()
  })

  test("muestra el orbe de voz en estado inicial con controles", async ({ page }) => {
    // El orbe muestra estado inactivo genérico
    await expect(page.getByText("Las Flamas, a la orden")).toBeVisible()
    await expect(page.getByText(/Toca «Llamar» y pide como en el local/)).toBeVisible()

    // Botón de llamada
    const startCallBtn = page.getByRole("button", { name: /Llamar a Las Flamas/i })
    await expect(startCallBtn).toBeVisible()
    await expect(startCallBtn).toBeEnabled()

    // Selector de idioma (Español / English)
    const langBtn = page.getByRole("button", { name: /Español/i })
    await expect(langBtn).toBeVisible()
    await langBtn.click()
    await expect(page.getByRole("button", { name: /English/i })).toBeVisible()
    // Volver a Español
    await page.getByRole("button", { name: /English/i }).click()
    await expect(page.getByRole("button", { name: /Español/i })).toBeVisible()
  })

  test("muestra la sección de sugerencias qué probar y el panel de pedido en vivo", async ({
    page,
  }) => {
    // Sugerencias
    await expect(page.getByText("Prueba diciendo")).toBeVisible()
    await expect(page.getByText("Pedir para llevar")).toBeVisible()
    await expect(page.getByText("Reservar mesa", { exact: true })).toBeVisible()

    // Panel lateral de la comanda
    await expect(page.getByText("La comanda")).toBeVisible()
  })
})
