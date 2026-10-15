import React from "react"
import { Calendar, ChefHat, Phone, PhoneCall } from "lucide-react"

import type { NavTab } from "./Navbar"

interface BottomNavProps {
  currentTab: NavTab
  onSelectTab: (tab: NavTab) => void
}

export const BottomNav: React.FC<BottomNavProps> = ({ currentTab, onSelectTab }) => {
  const ITEMS: { id: NavTab; label: string; icon: React.ElementType }[] = [
    { id: "call", label: "Llamar", icon: Phone },
    { id: "orders", label: "Cocina", icon: ChefHat },
    { id: "reservations", label: "Reservas", icon: Calendar },
    { id: "calls", label: "Llamadas", icon: PhoneCall },
  ]

  return (
    <nav className="fixed bottom-0 left-0 right-0 z-40 border-t border-border/70 bg-background px-2 py-1 md:hidden">
      <div className="flex items-center justify-around">
        {ITEMS.map((item) => {
          const Icon = item.icon
          const isActive = currentTab === item.id
          return (
            <button
              key={item.id}
              type="button"
              onClick={() => onSelectTab(item.id)}
              className={`flex flex-col items-center gap-1 rounded-lg px-3 py-1.5 transition-colors ${
                isActive
                  ? "text-primary font-semibold"
                  : "text-muted-foreground hover:text-foreground"
              }`}
            >
              <div
                className={`flex size-8 items-center justify-center rounded-full ${
                  isActive ? "bg-primary/10 text-primary" : ""
                }`}
              >
                <Icon className="size-4" />
              </div>
              <span className="text-[10px]">{item.label}</span>
            </button>
          )
        })}
      </div>
    </nav>
  )
}
