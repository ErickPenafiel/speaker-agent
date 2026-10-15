import React, { useSyncExternalStore } from "react"
import { Moon, Sun } from "lucide-react"
import { useTheme } from "next-themes"

import { Button } from "@/components/ui/button"

const emptySubscribe = () => () => {}

export const ThemeToggle: React.FC = () => {
  const isClient = useSyncExternalStore(
    emptySubscribe,
    () => true,
    () => false
  )
  const { theme, setTheme } = useTheme()

  if (!isClient) {
    return (
      <Button variant="ghost" size="icon" className="size-8 opacity-0">
        <Sun className="size-4" />
      </Button>
    )
  }

  const isDark = theme === "dark"

  return (
    <Button
      variant="ghost"
      size="icon"
      onClick={() => setTheme(isDark ? "light" : "dark")}
      className="size-8 rounded-full text-muted-foreground hover:text-foreground"
      aria-label="Alternar tema"
      title={isDark ? "Cambiar a modo claro" : "Cambiar a modo oscuro"}
    >
      {isDark ? <Sun className="size-4" /> : <Moon className="size-4" />}
    </Button>
  )
}
