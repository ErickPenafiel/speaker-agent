import { expect, test } from "@playwright/test"

test.describe("Pantalla Principal y Asistente de Voz", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/")
  })

  test("carga la página principal con branding genérico y título", async ({ page }) => {
    await expect(page).toHaveTitle(/Speaker Agent/)
    await expect(page.getByText("Speaker Agent")).toBeVisible()
    await expect(page.getByText("Asistente de Voz · Pedidos y Reservas")).toBeVisible()
  })

  test("muestra el orbe de voz en estado inicial con controles", async ({ page }) => {
    // El orbe muestra estado inactivo genérico
    await expect(page.getByText("Asistente de Voz", { exact: true })).toBeVisible()
    await expect(
      page.getByText("Presiona 'Iniciar Llamada' para hablar por voz")
    ).toBeVisible()

    // Botón de llamada
    const startCallBtn = page.getByRole("button", { name: /Iniciar Llamada/i })
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
    await expect(page.getByText("Qué puedes probar con el asistente")).toBeVisible()
    await expect(page.getByText("Realizar un pedido (Entrega / Retiro)")).toBeVisible()
    await expect(page.getByText("Reservar una mesa", { exact: true })).toBeVisible()

    // Panel lateral de pedido
    await expect(page.getByText("Pedido en Vivo")).toBeVisible()
  })
})
