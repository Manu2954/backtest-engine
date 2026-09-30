import { useEffect, useCallback } from 'react'

/**
 * Warns the user about unsaved changes when they try to navigate away.
 * - Blocks browser tab close / refresh via the beforeunload event.
 *
 * Note: In-app navigation blocking requires a data router (createBrowserRouter).
 * Since this app uses BrowserRouter, we only handle beforeunload.
 * Components should use the returned confirmNavigation for programmatic navigation.
 *
 * @param when - whether there are unsaved changes to guard against
 * @returns confirmNavigation - function to wrap navigation calls
 */
export function useUnsavedChanges(when: boolean) {
  // Block browser tab close / refresh
  useEffect(() => {
    if (!when) return

    const handleBeforeUnload = (e: BeforeUnloadEvent) => {
      e.preventDefault()
      // Modern browsers show their own generic message; setting returnValue triggers the prompt.
      e.returnValue = ''
    }

    window.addEventListener('beforeunload', handleBeforeUnload)
    return () => window.removeEventListener('beforeunload', handleBeforeUnload)
  }, [when])

  // Helper for programmatic navigation with confirmation
  const confirmNavigation = useCallback(
    (callback: () => void) => {
      if (!when) {
        callback()
        return
      }
      const confirmed = window.confirm(
        'You have unsaved changes. Are you sure you want to leave? Your changes will be lost.'
      )
      if (confirmed) {
        callback()
      }
    },
    [when]
  )

  return { confirmNavigation }
}
