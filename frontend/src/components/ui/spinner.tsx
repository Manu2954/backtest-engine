import { Loader2 } from "lucide-react"
import { cn } from "@/lib/utils"

interface SpinnerProps {
  className?: string
  size?: "sm" | "md" | "lg"
}

const sizeClasses = {
  sm: "h-4 w-4",
  md: "h-6 w-6",
  lg: "h-8 w-8",
}

export function Spinner({ className, size = "md" }: SpinnerProps) {
  return (
    <Loader2
      className={cn("animate-spin", sizeClasses[size], className)}
      aria-hidden="true"
    />
  )
}

export function SpinnerWithText({
  children,
  className
}: {
  children?: React.ReactNode
  className?: string
}) {
  return (
    <div className={cn("flex items-center gap-2 text-muted-foreground", className)}>
      <Spinner size="sm" />
      {children && <span>{children}</span>}
    </div>
  )
}
