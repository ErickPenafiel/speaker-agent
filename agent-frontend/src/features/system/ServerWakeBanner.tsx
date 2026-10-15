import React, { useEffect, useState } from "react"
import { AlertTriangle, Loader2, RefreshCw } from "lucide-react"

import { Button } from "@/components/ui/button"
import { api } from "@/lib/api"

export const ServerWakeBanner: React.FC = () => {
  const [status, setStatus] = useState<"checking" | "sleeping" | "ready">("checking")
  const [attempts, setAttempts] = useState(0)

  const checkServer = () => {
    setStatus("checking")
    api
      .getHealth()
      .then(() => setStatus("ready"))
      .catch(() => setStatus("sleeping"))
  }

  useEffect(() => {
    let active = true
    api
      .getHealth()
      .then(() => {
        if (active) setStatus("ready")
      })
      .catch(() => {
        if (active) setStatus("sleeping")
      })
    return () => {
      active = false
    }
  }, [])

  // Si está durmiendo, reintentar automáticamente cada 6 segundos
  useEffect(() => {
    if (status === "sleeping") {
      const timer = setInterval(() => {
        setAttempts((prev) => prev + 1)
        api
          .getHealth()
          .then(() => setStatus("ready"))
          .catch(() => {})
      }, 6000)
      return () => clearInterval(timer)
    }
  }, [status])

  if (status === "ready") {
    return null
  }

  return (
    <div className="border-b border-primary/30 bg-primary/10 px-4 py-2.5 text-xs text-primary">
      <div className="mx-auto flex max-w-7xl items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          {status === "checking" ? (
            <Loader2 className="size-4 shrink-0 animate-spin text-primary" />
          ) : (
            <AlertTriangle className="size-4 shrink-0 text-primary" />
          )}
          <span>
            {status === "checking"
              ? "Verificando estado del servidor..."
              : `Conectando con el servidor${
                  attempts > 0 ? ` · Reintentando (${attempts})...` : "..."
                }`}
          </span>
        </div>

        {status === "sleeping" && (
          <Button
            variant="ghost"
            size="sm"
            onClick={checkServer}
            className="h-7 gap-1 px-2 text-xs text-primary hover:bg-primary/20"
          >
            <RefreshCw className="size-3" />
            Reintentar ahora
          </Button>
        )}
      </div>
    </div>
  )
}
