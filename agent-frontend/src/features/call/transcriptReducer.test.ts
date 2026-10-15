import { describe, expect, it } from "vitest"
import {
  initialTranscriptState,
  transcriptReducer,
} from "./transcriptReducer"

describe("transcriptReducer", () => {
  it("agrega un nuevo mensaje parcial cuando la transcripción está vacía", () => {
    const state = transcriptReducer(initialTranscriptState, {
      type: "ADD_TRANSCRIPT",
      payload: {
        id: "msg-1",
        role: "user",
        text: "Hola",
        isFinal: false,
        timestamp: 1000,
      },
    })

    expect(state.items).toHaveLength(1)
    expect(state.items[0]).toEqual({
      type: "message",
      id: "msg-1",
      role: "user",
      text: "Hola",
      isFinal: false,
      timestamp: 1000,
    })
  })

  it("reemplaza el mensaje parcial previo del mismo rol sin duplicar", () => {
    let state = transcriptReducer(initialTranscriptState, {
      type: "ADD_TRANSCRIPT",
      payload: {
        id: "msg-1",
        role: "user",
        text: "Quiero un",
        isFinal: false,
        timestamp: 1000,
      },
    })

    state = transcriptReducer(state, {
      type: "ADD_TRANSCRIPT",
      payload: {
        id: "msg-2",
        role: "user",
        text: "Quiero hacer un pedido",
        isFinal: false,
        timestamp: 1050,
      },
    })

    expect(state.items).toHaveLength(1)
    const item = state.items[0]
    expect(item.type).toBe("message")
    if (item.type === "message") {
      expect(item.text).toBe("Quiero hacer un pedido")
      expect(item.isFinal).toBe(false)
    }
  })

  it("consolida el mensaje cuando llega isFinal: true", () => {
    let state = transcriptReducer(initialTranscriptState, {
      type: "ADD_TRANSCRIPT",
      payload: {
        id: "msg-1",
        role: "user",
        text: "Quiero hacer un pedido",
        isFinal: false,
        timestamp: 1000,
      },
    })

    state = transcriptReducer(state, {
      type: "ADD_TRANSCRIPT",
      payload: {
        id: "msg-1",
        role: "user",
        text: "Quiero hacer un pedido",
        isFinal: true,
        timestamp: 1100,
      },
    })

    expect(state.items).toHaveLength(1)
    const item1 = state.items[0]
    expect(item1.type).toBe("message")
    if (item1.type === "message") {
      expect(item1.isFinal).toBe(true)
    }

    // El siguiente mensaje del asistente debe ser un nuevo item
    state = transcriptReducer(state, {
      type: "ADD_TRANSCRIPT",
      payload: {
        id: "msg-asst-1",
        role: "assistant",
        text: "Perfecto, ¿para recoger o delivery?",
        isFinal: true,
        timestamp: 1200,
      },
    })

    expect(state.items).toHaveLength(2)
    const item2 = state.items[1]
    expect(item2.type).toBe("message")
    if (item2.type === "message") {
      expect(item2.role).toBe("assistant")
    }
  })

  it("agrega chips de tools intercalados en la conversación", () => {
    let state = transcriptReducer(initialTranscriptState, {
      type: "ADD_TRANSCRIPT",
      payload: {
        id: "msg-1",
        role: "user",
        text: "Confirmo el pedido",
        isFinal: true,
        timestamp: 1000,
      },
    })

    state = transcriptReducer(state, {
      type: "ADD_TOOL",
      payload: {
        toolName: "create_order",
        status: "completed",
        message: "Registrando pedido en cocina...",
      },
    })

    expect(state.items).toHaveLength(2)
    expect(state.items[1].type).toBe("tool")
    if (state.items[1].type === "tool") {
      expect(state.items[1].toolName).toBe("create_order")
      expect(state.items[1].status).toBe("completed")
    }
  })

  it("limpia todos los items al disparar CLEAR", () => {
    let state = transcriptReducer(initialTranscriptState, {
      type: "ADD_TRANSCRIPT",
      payload: {
        id: "msg-1",
        role: "user",
        text: "Hola",
        isFinal: true,
        timestamp: 1000,
      },
    })

    state = transcriptReducer(state, { type: "CLEAR" })
    expect(state.items).toEqual([])
  })
})
