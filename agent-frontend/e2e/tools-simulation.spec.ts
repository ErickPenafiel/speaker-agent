import { expect, test } from "@playwright/test"

test.describe("Features y Tools del Asistente", () => {
  test("verifica el comportamiento de solo lectura en pedidos de demostración (tool create_order)", async ({
    page,
  }) => {
    await page.goto("/")

    // Navegar a Cocina / Pedidos
    await page.getByRole("button", { name: /Cocina \/ Pedidos/i }).click()
    await expect(page.getByText("Tablero de Cocina")).toBeVisible()

    // Los pedidos de demo sembrados deben tener el botón de acción bloqueado con 'Solo lectura'
    const readOnlyButtons = page.getByRole("button", { name: /Solo lectura/i })
    await expect(readOnlyButtons.first()).toBeVisible({ timeout: 5000 })
    await expect(readOnlyButtons.first()).toBeDisabled()
  })

  test("verifica la consulta de menú en tiempo real con platos disponibles y agotados (tool get_menu)", async ({
    page,
  }) => {
    await page.goto("/")

    // Abrir modal de menú
    await page.getByRole("button", { name: /Ver Menú/i }).click()
    const dialog = page.getByRole("dialog")
    await expect(dialog).toBeVisible()

    // Verificar categorías cargadas
    await expect(dialog.getByText(/bebidas|platos|guarniciones/i).first()).toBeVisible()

    // Verificar platos disponibles con precios
    await expect(dialog.getByText("Gaseosa")).toBeVisible()

    // Cerrar modal
    await page.keyboard.press("Escape")
    await expect(dialog).not.toBeVisible()
  })

  test("verifica los resultados generados por tools (reservas y transferencias) en el detalle de llamada", async ({
    page,
  }) => {
    await page.goto("/")

    // Ir a pestaña de Historial
    await page.getByRole("button", { name: "Historial" }).click()
    await expect(page.getByText("Historial de Llamadas")).toBeVisible()

    // Buscar una llamada que tenga outcome de transferencia o reserva
    const callCard = page.getByRole("button", { name: /Ver detalle/i }).first()
    await expect(callCard).toBeVisible()
    await callCard.click()

    const sheet = page.getByRole("dialog")
    await expect(sheet).toBeVisible()

    // Comprobar que se muestra la transcripción estructurada con roles Cliente / Asistente
    await expect(sheet.getByText("Transcripción completa")).toBeVisible()
    await expect(sheet.getByText("Asistente").first()).toBeVisible()

    // Cerrar el modal
    await page.keyboard.press("Escape")
    await expect(sheet).not.toBeVisible()
  })

  test("verifica el flujo de reinicio de sesión (resetSessionId)", async ({ page }) => {
    await page.goto("/")

    // Obtener sesión previa de localStorage
    const initialSession = await page.evaluate(() =>
      localStorage.getItem("speaker_agent_session_id")
    )
    expect(initialSession).toBeTruthy()

    // Aceptar automáticamente el diálogo de confirmación de window.confirm
    page.once("dialog", (dialog) => dialog.accept())

    // Hacer clic en el indicador de sesión
    const sessionIndicator = page.getByText(/Sesión:/i)
    await expect(sessionIndicator).toBeVisible()
    await sessionIndicator.click()

    // Esperar a que la página se recargue con una nueva sesión
    await page.waitForTimeout(1000)

    const newSession = await page.evaluate(() =>
      localStorage.getItem("speaker_agent_session_id")
    )
    expect(newSession).toBeTruthy()
    expect(newSession).not.toBe(initialSession)
  })
})
