# 1. Visión y alcance

## Objetivo
Una sola app con dos funciones:
1. **Probar al agente**: botón de llamada desde el navegador con transcripción en vivo.
2. **Ver el resultado**: panel de pedidos, reservas y llamadas de **La Brasa** (ficticio), actualizado durante y después de cada llamada.

Meta para el cliente (Upwork): en 30 segundos escucha al agente y ve cómo el pedido aparece **en la misma pantalla**.

## Caso de uso
Restaurante de parrilla y comida criolla. **Sofía** contesta en español: informa de menú y horarios, toma pedidos (confirmando en voz alta antes de enviarlos), hace reservas y transfiere a una persona.

## Dentro del alcance
- Llamada web (Vapi Web SDK), 4 tools: `get_menu`, `create_order`, `create_reservation`, `transfer_to_human`.
- Webhook de fin de llamada (transcripción, resumen, outcome).
- Panel: pedidos (kanban), reservas, llamadas con detalle, menú.
- Selector de idioma del agente EN/ES (el cliente de Upwork probablemente no habla español).
- Aislamiento de datos por sesión de visitante.

## Fuera del alcance
Telefonía real, pagos, autenticación de usuarios, multi-restaurante, gestión de mesas/capacidad.

## Principios
- Respuestas de tools **cortas y fáciles de decir en voz alta**.
- El **total del pedido se calcula siempre en el backend**, nunca por el LLM.
- Nunca se crea un pedido sin confirmación explícita del cliente.
- Verificar siempre el formato actual de tool calls y server messages en la documentación oficial de Vapi.
