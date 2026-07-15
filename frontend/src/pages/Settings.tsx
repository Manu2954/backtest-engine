import { useEffect, useState } from 'react'
import { Sun, Moon, Monitor, CheckCircle2, XCircle, ExternalLink } from 'lucide-react'
import { Header } from '@/components/layout'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Separator } from '@/components/ui/separator'
import { useUIStore, type Theme } from '@/store/uiStore'
import { cn } from '@/lib/utils'

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8081/api/v1'
const APP_VERSION = '1.0.0'

type ConnectionStatus = 'checking' | 'connected' | 'disconnected'

export function SettingsPage() {
  const { theme, setTheme } = useUIStore()
  const [connectionStatus, setConnectionStatus] = useState<ConnectionStatus>('checking')

  useEffect(() => {
    async function checkHealth() {
      setConnectionStatus('checking')
      try {
        // API_BASE_URL is like http://localhost:8081/api/v1, health is at root
        const baseUrl = API_BASE_URL.replace(/\/api\/v1$/, '')
        const response = await fetch(`${baseUrl}/health`, {
          method: 'GET',
          signal: AbortSignal.timeout(5000),
        })
        if (response.ok) {
          setConnectionStatus('connected')
        } else {
          setConnectionStatus('disconnected')
        }
      } catch {
        setConnectionStatus('disconnected')
      }
    }
    checkHealth()
  }, [])

  const themeOptions: { value: Theme; label: string; icon: typeof Sun }[] = [
    { value: 'light', label: 'Light', icon: Sun },
    { value: 'dark', label: 'Dark', icon: Moon },
    { value: 'system', label: 'System', icon: Monitor },
  ]

  return (
    <>
      <Header title="Settings" />
      <div className="p-6 max-w-2xl">
        <div className="space-y-6">
          {/* Theme Section */}
          <Card>
            <CardHeader>
              <CardTitle>Appearance</CardTitle>
              <CardDescription>
                Customize how the application looks on your device.
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                <div>
                  <label className="text-sm font-medium text-foreground mb-3 block">
                    Theme
                  </label>
                  <div className="flex gap-2">
                    {themeOptions.map((option) => {
                      const Icon = option.icon
                      const isSelected = theme === option.value
                      return (
                        <Button
                          key={option.value}
                          variant={isSelected ? 'default' : 'outline'}
                          className={cn(
                            'flex-1 justify-center gap-2',
                            isSelected && 'ring-2 ring-ring ring-offset-2 ring-offset-background'
                          )}
                          onClick={() => setTheme(option.value)}
                        >
                          <Icon className="h-4 w-4" />
                          {option.label}
                        </Button>
                      )
                    })}
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* API Configuration Section */}
          <Card>
            <CardHeader>
              <CardTitle>API Configuration</CardTitle>
              <CardDescription>
                Backend API connection details (read-only).
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm font-medium text-foreground">API URL</p>
                    <p className="text-sm text-muted-foreground font-mono">
                      {API_BASE_URL}
                    </p>
                  </div>
                </div>
                <Separator />
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm font-medium text-foreground">
                      Connection Status
                    </p>
                    <p className="text-sm text-muted-foreground">
                      Health check endpoint
                    </p>
                  </div>
                  <div className="flex items-center gap-2">
                    {connectionStatus === 'checking' && (
                      <>
                        <div className="h-4 w-4 rounded-full border-2 border-primary border-t-transparent animate-spin" />
                        <span className="text-sm text-muted-foreground">
                          Checking...
                        </span>
                      </>
                    )}
                    {connectionStatus === 'connected' && (
                      <>
                        <CheckCircle2 className="h-4 w-4 text-profit" />
                        <span className="text-sm text-profit">Connected</span>
                      </>
                    )}
                    {connectionStatus === 'disconnected' && (
                      <>
                        <XCircle className="h-4 w-4 text-loss" />
                        <span className="text-sm text-loss">Disconnected</span>
                      </>
                    )}
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* About Section */}
          <Card>
            <CardHeader>
              <CardTitle>About</CardTitle>
              <CardDescription>
                Application information and resources.
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <p className="text-sm font-medium text-foreground">Version</p>
                  <p className="text-sm text-muted-foreground font-mono">
                    {APP_VERSION}
                  </p>
                </div>
                <Separator />
                <div className="flex items-center justify-between">
                  <p className="text-sm font-medium text-foreground">
                    Documentation
                  </p>
                  <Button variant="ghost" size="sm" asChild>
                    <a href="#" className="flex items-center gap-1.5">
                      View Docs
                      <ExternalLink className="h-3.5 w-3.5" />
                    </a>
                  </Button>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </>
  )
}
