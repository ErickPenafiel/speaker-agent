import React from "react"
import {
  Calendar,
  ChefHat,
  Phone,
  PhoneCall,
  RotateCcw,
  UtensilsCrossed,
} from "lucide-react"

import { FlameMark } from "@/app/FlameMark"
import { ThemeToggle } from "@/components/ThemeToggle"
import { Button } from "@/components/ui/button"
import { getSessionId, resetSessionId } from "@/lib/session"

export type NavTab = "call" | "orders" | "reservations" | "calls"

interface NavbarProps {
  currentTab: NavTab
  onSelectTab: (tab: NavTab) => void
  onOpenMenu: () => void
}

export const Navbar: React.FC<NavbarProps> = ({
  currentTab,
  onSelectTab,
  onOpenMenu,
}) => {
  const sessionId = getSessionId()
  const shortSession = sessionId.slice(0, 8)

  const handleResetSession = () => {
    if (confirm("¿Empezar de cero? Se borra tu panel de prueba y se crea una sesión nueva.")) {
      resetSessionId()
      window.location.reload()
    }
  }

  const NAV_ITEMS: { id: NavTab; label: string; icon: React.ElementType }[] = [
    { id: "call", label: "Llamar", icon: Phone },
    { id: "orders", label: "Cocina", icon: ChefHat },
    { id: "reservations", label: "Reservas", icon: Calendar },
    { id: "calls", label: "Llamadas", icon: PhoneCall },
  ]

  return (
    <header className="sticky top-0 z-40 w-full border-b border-border bg-background">
      <div className="mx-auto flex h-16 max-w-7xl items-center justify-between px-4 sm:px-6">
        {/* Marca */}
        <div className="flex items-center gap-2.5">
          <FlameMark className="size-7 text-primary" />
          <div className="flex flex-col leading-none">
            <span className="font-heading text-xl font-semibold tracking-tight text-foreground">
              Las Flamas
            </span>
            <span className="mt-1 text-[10px] font-medium uppercase tracking-[0.18em] text-muted-foreground">
              Parrilla boliviana
            </span>
          </div>
        </div>

        {/* Pestañas de Navegación de Escritorio */}
        <nav className="hidden items-center gap-1 md:flex">
          {NAV_ITEMS.map((item) => {
            const Icon = item.icon
            const isActive = currentTab === item.id
            return (
              <button
                key={item.id}
                type="button"
                onClick={() => onSelectTab(item.id)}
                className={`flex items-center gap-1.5 rounded-md px-3 py-1.5 text-sm font-medium transition-colors ${
                  isActive
                    ? "bg-primary text-primary-foreground shadow-sm"
                    : "text-muted-foreground hover:bg-muted/60 hover:text-foreground"
                }`}
              >
                <Icon className="size-3.5" />
                <span>{item.label}</span>
              </button>
            )
          })}
        </nav>

        {/* Acciones del Extremo Derecho */}
        <div className="flex items-center gap-2">
          {/* Botón de Ver Menú */}
          <Button
            variant="outline"
            size="sm"
            onClick={onOpenMenu}
            className="h-8 gap-1.5 px-2.5 text-xs border-border/80"
          >
            <UtensilsCrossed className="size-3.5 text-primary" />
            <span className="hidden sm:inline">Ver Menú</span>
          </Button>

          {/* Sesión de visitante */}
          <div
            onClick={handleResetSession}
            title={`Sesión activa: ${sessionId}. Clic para reiniciar.`}
            className="hidden cursor-pointer items-center gap-1 rounded-md border border-border/60 bg-muted/30 px-2 py-1 font-mono text-[10px] text-muted-foreground hover:border-primary/40 hover:text-foreground sm:flex"
          >
            <span className="size-1.5 rounded-full bg-emerald-500" />
            <span>Mesa {shortSession}</span>
            <RotateCcw className="size-2.5 ml-0.5 opacity-60" />
          </div>

          {/* Toggle de Modo Oscuro / Claro */}
          <ThemeToggle />
        </div>
      </div>
    </header>
  )
}
