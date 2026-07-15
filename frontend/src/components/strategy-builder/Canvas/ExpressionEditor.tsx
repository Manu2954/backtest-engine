import { useState, useEffect } from 'react'
import { Button } from '@/components/ui/button'
import { AlertCircle, Check, Edit2, X, Info } from 'lucide-react'
import { cn } from '@/lib/utils'
import { useStrategyBuilderStore, type ConditionTarget } from '@/store/strategyBuilderStore'

interface ExpressionEditorProps {
  target: ConditionTarget
  groupNames: string[]
}

interface ValidationResult {
  valid: boolean
  errors: string[]
  warnings: string[]
}

function validateExpression(expression: string, groupNames: string[]): ValidationResult {
  const errors: string[] = []
  const warnings: string[] = []

  if (!expression || expression.trim() === '') {
    return { valid: false, errors: ['Expression cannot be empty'], warnings: [] }
  }

  // Check for balanced parentheses
  let openCount = 0
  for (const char of expression) {
    if (char === '(') openCount++
    if (char === ')') openCount--
    if (openCount < 0) {
      errors.push('Unbalanced parentheses: closing ")" without opening')
      break
    }
  }
  if (openCount > 0) {
    errors.push(`Unbalanced parentheses: ${openCount} unclosed "("`)
  }

  // Extract tokens (group names and operators)
  const tokens = expression.split(/\s+/).filter(t => t && !['(', ')'].includes(t))
  const operators = ['AND', 'OR', 'NOT']

  // Check if all non-operator tokens are valid group names
  const referencedGroups = new Set<string>()
  for (const token of tokens) {
    if (!operators.includes(token.toUpperCase())) {
      if (!groupNames.includes(token)) {
        errors.push(`Unknown group: "${token}"`)
      } else {
        referencedGroups.add(token)
      }
    }
  }

  // Warn if some groups are not referenced
  const unreferencedGroups = groupNames.filter(name => !referencedGroups.has(name))
  if (unreferencedGroups.length > 0) {
    warnings.push(`Unused: ${unreferencedGroups.join(', ')}`)
  }

  return {
    valid: errors.length === 0,
    errors,
    warnings,
  }
}

export function ExpressionEditor({ target, groupNames }: ExpressionEditorProps) {
  const expression = useStrategyBuilderStore((s) => s.getExpression(target))
  const setExpression = useStrategyBuilderStore((s) => s.setExpression)

  const [isEditing, setIsEditing] = useState(false)
  const [draftExpression, setDraftExpression] = useState(expression)
  const [validation, setValidation] = useState<ValidationResult | null>(null)

  // Real-time validation as user types
  useEffect(() => {
    if (isEditing && draftExpression) {
      const result = validateExpression(draftExpression, groupNames)
      setValidation(result)
    }
  }, [draftExpression, groupNames, isEditing])

  const handleEdit = () => {
    setDraftExpression(expression)
    setValidation(null)
    setIsEditing(true)
  }

  const handleSave = () => {
    const result = validateExpression(draftExpression, groupNames)
    if (result.valid) {
      setExpression(target, draftExpression)
      setIsEditing(false)
      setValidation(null)
    } else {
      setValidation(result)
    }
  }

  const handleCancel = () => {
    setDraftExpression(expression)
    setIsEditing(false)
    setValidation(null)
  }

  // If there are no groups, don't show anything
  if (groupNames.length === 0) {
    return null
  }

  // Default expression if empty
  const displayExpression = expression || groupNames.join(' OR ')

  return (
    <div className="mb-4 p-4 border rounded-lg bg-muted/30">
      <div className="flex items-center gap-2 mb-2">
        <h4 className="text-sm font-semibold">Boolean Expression</h4>
        {!isEditing && (
          <Button onClick={handleEdit} variant="ghost" size="sm">
            <Edit2 className="h-3 w-3 mr-1" />
            Edit
          </Button>
        )}
      </div>

      {isEditing ? (
        <div className="space-y-3">
          <div className="relative">
            <input
              type="text"
              value={draftExpression}
              onChange={(e) => setDraftExpression(e.target.value)}
              placeholder="e.g., oversold OR breakout"
              className={cn(
                "w-full px-3 py-2 text-sm rounded-md border bg-background font-mono",
                validation && !validation.valid && "border-red-500 focus:ring-red-500",
                validation && validation.valid && validation.warnings.length === 0 && "border-green-500 focus:ring-green-500",
                validation && validation.valid && validation.warnings.length > 0 && "border-yellow-500 focus:ring-yellow-500"
              )}
              autoFocus
            />
            {validation && (
              <div className="absolute right-2 top-1/2 -translate-y-1/2 flex items-center gap-1">
                {!validation.valid ? (
                  <AlertCircle className="h-4 w-4 text-red-500" />
                ) : validation.warnings.length > 0 ? (
                  <Info className="h-4 w-4 text-yellow-500" />
                ) : (
                  <Check className="h-4 w-4 text-green-500" />
                )}
              </div>
            )}
          </div>

          {/* Inline validation feedback */}
          {validation && (
            <div className="space-y-2">
              {validation.errors.length > 0 && (
                <div className="flex items-start gap-2 p-2 rounded-md bg-red-50 border border-red-200">
                  <AlertCircle className="h-4 w-4 text-red-600 flex-shrink-0 mt-0.5" />
                  <div className="flex-1 text-xs space-y-1">
                    {validation.errors.map((error, i) => (
                      <div key={i} className="text-red-700">{error}</div>
                    ))}
                  </div>
                </div>
              )}
              {validation.warnings.length > 0 && (
                <div className="flex items-start gap-2 p-2 rounded-md bg-yellow-50 border border-yellow-200">
                  <Info className="h-4 w-4 text-yellow-600 flex-shrink-0 mt-0.5" />
                  <div className="flex-1 text-xs space-y-1">
                    {validation.warnings.map((warning, i) => (
                      <div key={i} className="text-yellow-700">{warning}</div>
                    ))}
                  </div>
                </div>
              )}
              {validation.valid && validation.errors.length === 0 && validation.warnings.length === 0 && (
                <div className="flex items-center gap-2 p-2 rounded-md bg-green-50 border border-green-200">
                  <Check className="h-4 w-4 text-green-600" />
                  <span className="text-xs text-green-700 font-medium">Valid expression</span>
                </div>
              )}
            </div>
          )}

          <div className="flex gap-2">
            <Button
              onClick={handleSave}
              variant="default"
              size="sm"
              disabled={validation ? !validation.valid : false}
            >
              <Check className="h-4 w-4 mr-1" />
              Save
            </Button>
            <Button onClick={handleCancel} variant="ghost" size="sm">
              <X className="h-4 w-4 mr-1" />
              Cancel
            </Button>
          </div>

          <div className="text-xs text-muted-foreground space-y-1">
            <p className="font-medium">Available groups:</p>
            <p className="font-mono">{groupNames.join(', ')}</p>
            <p className="font-medium mt-2">Operators:</p>
            <p className="font-mono">AND, OR, NOT, ( )</p>
            <p className="font-medium mt-2">Examples:</p>
            <ul className="list-disc list-inside space-y-1 font-mono">
              <li>oversold</li>
              <li>oversold OR breakout</li>
              <li>oversold AND NOT ranging</li>
              <li>(oversold OR breakout) AND uptrend</li>
            </ul>
          </div>
        </div>
      ) : (
        <div className="p-3 bg-background rounded-md border">
          <code className="text-sm font-mono">{displayExpression}</code>
        </div>
      )}
    </div>
  )
}
