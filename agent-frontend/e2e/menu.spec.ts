import { expect, test } from "@playwright/test"

test.describe("Diálogo de Menú y Catálogo", () => {
  test("abre el modal de menú y muestra las categorías cargadas del backend", async ({
    page,
  }) => {
    await page.goto("/")

    // Clic en el botón "Ver Menú" del Navbar
    const menuButton = page.getByRole("button", { name: /Ver Menú/i })
    await expect(menuButton).toBeVisible()
    await menuButton.click()

    // Verificar que el diálogo se abre con título genérico
    await expect(page.getByText("Menú y Catálogo")).toBeVisible()
    await expect(
      page.getByText("Platos y precios consultados en tiempo real")
    ).toBeVisible()

    // Debe mostrar platos reales desde el backend dentro del modal
    await expect(page.getByRole("dialog").getByText("Gaseosa")).toBeVisible({ timeout: 5000 })

    // Cerrar el diálogo usando la tecla Escape o haciendo clic fuera
    await page.keyboard.press("Escape")
    await expect(page.getByText("Menú y Catálogo")).not.toBeVisible()
  })
})
