import { HelpCircle } from 'lucide-react'
import { cn } from '@/lib/utils'

interface HelpTooltipProps {
  text: string | React.ReactNode
  className?: string
  iconClassName?: string
  position?: 'top' | 'bottom' | 'left' | 'right'
}

export function HelpTooltip({
  text,
  className,
  iconClassName,
  position = 'bottom'
}: HelpTooltipProps) {
  const positionClasses = {
    top: 'bottom-full mb-2 left-1/2 -translate-x-1/2',
    bottom: 'top-full mt-2 left-1/2 -translate-x-1/2',
    left: 'right-full mr-2 top-1/2 -translate-y-1/2',
    right: 'left-full ml-2 top-1/2 -translate-y-1/2',
  }

  return (
    <div className={cn("relative group inline-flex", className)}>
      <HelpCircle className={cn("h-4 w-4 text-muted-foreground cursor-help", iconClassName)} />
      <div
        className={cn(
          "absolute px-3 py-2 bg-popover border border-border rounded-md shadow-lg text-xs text-popover-foreground",
          "opacity-0 group-hover:opacity-100 transition-opacity z-50 pointer-events-none",
          "min-w-max max-w-xs",
          positionClasses[position]
        )}
      >
        {text}
      </div>
    </div>
  )
}
