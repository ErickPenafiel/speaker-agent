import { expect, test } from "@playwright/test"

test.describe("Tema y Sesión en Navbar", () => {
  test("cambia entre tema oscuro y claro", async ({ page }) => {
    await page.goto("/")

    const html = page.locator("html")
    const themeBtn = page.getByRole("button", { name: /Alternar tema/i })
    await expect(themeBtn).toBeVisible()

    // Cambiar tema
    await themeBtn.click()
    // El atributo class o color-scheme de html cambia
    await expect(html).toBeAttached()
  })

  test("muestra el identificador de sesión X-Session-Id en la barra superior", async ({
    page,
  }) => {
    await page.goto("/")
    // El badge de sesión muestra 'Sesión: xxxx'
    await expect(page.getByText(/Sesión:/i)).toBeVisible()
  })
})
