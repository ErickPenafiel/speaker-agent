import { expect, test } from "@playwright/test"

test.describe("Historial y Auditoría de Llamadas", () => {
  test("navega al historial, lista las llamadas y abre el detalle de transcripción", async ({
    page,
  }) => {
    await page.goto("/")

    // Clic en pestaña Historial
    const callsTabBtn = page.getByRole("button", { name: "Historial" })
    await expect(callsTabBtn).toBeVisible()
    await callsTabBtn.click()

    // Encabezado
    await expect(page.getByText("Historial de Llamadas")).toBeVisible()
    await expect(
      page.getByText("Auditoría de conversaciones, duración y transcripciones")
    ).toBeVisible()

    // Clic en la primera tarjeta de llamada que tenga "Ver detalle"
    const firstCallCard = page.getByRole("button", { name: /Ver detalle/i }).first()
    await expect(firstCallCard).toBeVisible({ timeout: 5000 })
    await firstCallCard.click()

    // Se abre el modal de detalle
    await expect(page.getByText("Detalle de Llamada")).toBeVisible()
    await expect(page.getByText("Resumen ejecutivo:")).toBeVisible()
    await expect(page.getByText("Transcripción completa")).toBeVisible()

    // Verificar que los roles de transcripción son genéricos (Cliente / Asistente)
    await expect(
      page.getByText("Asistente").first()
    ).toBeVisible({ timeout: 5000 })

    // Cerrar el modal
    await page.keyboard.press("Escape")
    await expect(page.getByText("Detalle de Llamada")).not.toBeVisible()
  })
})
