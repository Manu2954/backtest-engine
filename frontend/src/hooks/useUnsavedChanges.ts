import { useEffect } from 'react'
import { useBlocker } from 'react-router-dom'

/**
 * Warns the user about unsaved changes when they try to navigate away.
 * - Blocks in-app (React Router) navigation with a confirm dialog.
 * - Blocks browser tab close / refresh via the beforeunload event.
 *
 * @param when - whether there are unsaved changes to guard against
 */
export function useUnsavedChanges(when: boolean) {
  // Block in-app navigation
  const blocker = useBlocker(
    ({ currentLocation, nextLocation }) =>
      when && currentLocation.pathname !== nextLocation.pathname
  )

  useEffect(() => {
    if (blocker.state === 'blocked') {
      const confirmed = window.confirm(
        'You have unsaved changes. Are you sure you want to leave? Your changes will be lost.'
      )
      if (confirmed) {
        blocker.proceed()
      } else {
        blocker.reset()
      }
    }
  }, [blocker])

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
}
