import { expect, test } from "@playwright/test"

test.describe("Ciclo de Vida CRUD y Mutaciones de Pedidos", () => {
  test("crea un pedido real para la sesión activa y avanza su estado de forma interactiva (Confirmado -> Preparar -> Listo)", async ({
    page,
    request,
  }) => {
    // 1. Abrir la aplicación y obtener el session_id activo del navegador
    await page.goto("/")
    const sessionId = await page.evaluate(() =>
      localStorage.getItem("speaker_agent_session_id")
    )
    expect(sessionId).toBeTruthy()

    // 2. Simular la creación de un pedido real por voz para esta sesión mediante la tool 'create_order'
    const uniqueCustomer = `Carlos Cliente ${Date.now().toString().slice(-4)}`
    const toolCallId = `tc-e2e-${Date.now()}`

    const toolResponse = await request.post("http://localhost:8000/vapi/tools", {
      headers: {
        Authorization: "Bearer change-me",
        "Content-Type": "application/json",
      },
      data: {
        message: {
          type: "tool-calls",
          call: {
            id: `call-e2e-${Date.now()}`,
            metadata: { sessionId },
          },
          toolCallList: [
            {
              id: toolCallId,
              name: "create_order",
              function: {
                name: "create_order",
                arguments: {
                  customer_name: uniqueCustomer,
                  type: "pickup",
                  customer_confirmed: true,
                  items: [{ name: "Gaseosa", quantity: 2 }],
                  notes: "Sin hielo",
                },
              },
            },
          ],
        },
      },
    })
    expect(toolResponse.ok()).toBeTruthy()
    const toolData = await toolResponse.json()
    expect(toolData.results[0].result).toContain("confirmado")

    // 3. Navegar a Cocina / Pedidos
    await page.getByRole("button", { name: /Cocina \/ Pedidos/i }).click()
    await expect(page.getByText("Tablero de Cocina")).toBeVisible()

    // 4. Localizar la tarjeta del cliente recién creado dentro de la columna "Confirmados"
    const orderCard = page.getByTestId("order-card").filter({ hasText: uniqueCustomer })
    await expect(orderCard).toBeVisible({ timeout: 6000 })
    await expect(orderCard.getByText("Sin hielo")).toBeVisible()

    // 5. El botón de acción está habilitado (NO es solo lectura)
    const prepareButton = orderCard.getByRole("button", { name: /Preparar/i })
    await expect(prepareButton).toBeVisible()
    await expect(prepareButton).toBeEnabled()

    // 6. Mutación 1: Transicionar de 'confirmed' a 'preparing'
    await prepareButton.click()

    // Ahora el botón debe cambiar a "Listo" dentro de la columna "En preparación"
    const readyButton = orderCard.getByRole("button", { name: /Listo/i })
    await expect(readyButton).toBeVisible({ timeout: 5000 })

    // 7. Mutación 2: Transicionar de 'preparing' a 'ready'
    await readyButton.click()

    // La tarjeta ahora debe mostrar el badge de "Completado" en la columna "Listos"
    await expect(orderCard.getByText("Completado")).toBeVisible({ timeout: 5000 })

    // 8. Persistencia: Recargar la página, volver a Cocina y verificar que el pedido se mantiene en 'ready'
    await page.reload()
    await page.getByRole("button", { name: /Cocina \/ Pedidos/i }).click()
    await expect(page.getByText("Tablero de Cocina")).toBeVisible()
    const persistedCard = page.getByTestId("order-card").filter({ hasText: uniqueCustomer })
    await expect(persistedCard).toBeVisible()
    await expect(persistedCard.getByText("Completado")).toBeVisible()
  })
})
