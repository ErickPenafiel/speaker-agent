import React, { useEffect, useRef } from "react"
import { Bot, CheckCircle2, MessageSquare, User, Wrench } from "lucide-react"

import { Badge } from "@/components/ui/badge"
import type { TranscriptItem } from "../transcriptReducer"

interface LiveTranscriptProps {
  items: TranscriptItem[]
}

export const LiveTranscript: React.FC<LiveTranscriptProps> = ({ items }) => {
  const scrollRef = useRef<HTMLDivElement>(null)

  // Auto-scroll hacia el mensaje más reciente
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight
    }
  }, [items])

  if (items.length === 0) {
    return (
      <div className="flex min-h-[280px] flex-col items-center justify-center rounded-xl border border-dashed border-border/60 p-6 text-center text-muted-foreground">
        <MessageSquare className="mb-2 size-8 opacity-40" />
        <p className="text-xs font-medium">Lo que se va hablando</p>
        <p className="text-[11px] text-muted-foreground/80">
          Tu voz y la respuesta de la casa aparecen aquí mientras hablan.
        </p>
      </div>
    )
  }

  return (
    <div
      ref={scrollRef}
      aria-live="polite"
      className="flex max-h-[380px] min-h-[280px] flex-col gap-3 overflow-y-auto rounded-xl border border-border/60 bg-muted/15 p-4 scroll-smooth"
    >
      {items.map((item) => {
        if (item.type === "tool") {
          return (
            <div
              key={item.id}
              className="my-1 flex items-center justify-center animate-in fade-in zoom-in-95 duration-200"
            >
              <Badge
                variant="outline"
                className="gap-1.5 border-primary/30 bg-primary/10 py-1 text-xs text-primary"
              >
                {item.status === "completed" ? (
                  <CheckCircle2 className="size-3 text-emerald-500" />
                ) : (
                  <Wrench className="size-3 text-primary animate-spin" />
                )}
                <span>{item.message}</span>
              </Badge>
            </div>
          )
        }

        const isUser = item.role === "user"

        return (
          <div
            key={item.id}
            className={`flex items-start gap-2.5 ${
              isUser ? "flex-row-reverse" : "flex-row"
            } animate-in fade-in duration-200`}
          >
            {/* Avatar icono */}
            <div
              className={`flex size-7 shrink-0 items-center justify-center rounded-full text-xs font-semibold ${
                isUser
                  ? "bg-primary text-primary-foreground"
                  : "bg-ember text-foreground"
              }`}
            >
              {isUser ? <User className="size-3.5" /> : <Bot className="size-3.5" />}
            </div>

            {/* Burbuja de mensaje */}
            <div
              className={`flex max-w-[82%] flex-col rounded-md px-3.5 py-2 text-xs leading-relaxed ${
                isUser
                  ? "bg-primary text-primary-foreground"
                  : "border border-border/70 bg-card text-card-foreground"
              } ${!item.isFinal ? "opacity-75 italic" : ""}`}
            >
              <span className="font-semibold text-[10px] opacity-75">
                {isUser ? "Tú" : "Las Flamas"}
              </span>
              <p className="mt-0.5 break-words whitespace-pre-wrap">{item.text}</p>
              {!item.isFinal && (
                <span className="mt-1 self-end text-[9px] opacity-60">escribiendo...</span>
              )}
            </div>
          </div>
        )
      })}
    </div>
  )
}
