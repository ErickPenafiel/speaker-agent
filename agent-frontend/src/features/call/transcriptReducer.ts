import type { ToolCallEvent, TranscriptMessage } from "./adapters/voiceAdapter"

export type TranscriptItem =
  | {
      type: "message"
      id: string
      role: "user" | "assistant"
      text: string
      isFinal: boolean
      timestamp: number
    }
  | {
      type: "tool"
      id: string
      toolName: string
      status: "running" | "completed" | "failed"
      message: string
      timestamp: number
    }

export interface TranscriptState {
  items: TranscriptItem[]
}

export type TranscriptAction =
  | { type: "ADD_TRANSCRIPT"; payload: TranscriptMessage }
  | { type: "ADD_TOOL"; payload: ToolCallEvent }
  | { type: "CLEAR" }

export const initialTranscriptState: TranscriptState = {
  items: [],
}

export function transcriptReducer(
  state: TranscriptState,
  action: TranscriptAction
): TranscriptState {
  switch (action.type) {
    case "CLEAR":
      return initialTranscriptState

    case "ADD_TRANSCRIPT": {
      const msg = action.payload
      const items = [...state.items]
      const lastIndex = items.length - 1
      const lastItem = items[lastIndex]

      // Si el último item es un mensaje parcial del mismo rol, lo reemplazamos con el nuevo texto
      if (
        lastItem &&
        lastItem.type === "message" &&
        lastItem.role === msg.role &&
        !lastItem.isFinal
      ) {
        items[lastIndex] = {
          ...lastItem,
          text: msg.text,
          isFinal: msg.isFinal,
          timestamp: msg.timestamp,
        }
        return { items }
      }

      // Si no hay parcial previo o es un nuevo turno/rol, agregamos nuevo mensaje
      return {
        items: [
          ...items,
          {
            type: "message",
            id: msg.id,
            role: msg.role,
            text: msg.text,
            isFinal: msg.isFinal,
            timestamp: msg.timestamp,
          },
        ],
      }
    }

    case "ADD_TOOL": {
      const tool = action.payload
      return {
        items: [
          ...state.items,
          {
            type: "tool",
            id: `tool-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`,
            toolName: tool.toolName,
            status: tool.status,
            message: tool.message || `Ejecutando ${tool.toolName}...`,
            timestamp: Date.now(),
          },
        ],
      }
    }

    default:
      return state
  }
}
