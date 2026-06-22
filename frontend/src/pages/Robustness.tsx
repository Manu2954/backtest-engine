import { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { Header } from '@/components/layout'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Skeleton } from '@/components/ui/skeleton'
import { ErrorBoundary } from '@/components/shared'
import { useStrategies } from '@/api/hooks'
import {
  startParameterSensitivity,
  startWalkForward,
  startRegimeDetection,
  startFeatureConditioning,
  getRobustnessAnalysis,
} from '@/api/endpoints/robustness'
import type {
  AnalysisType,
  RobustnessAnalysis,
  ParameterSensitivityReport,
  WalkForwardReport,
  RegimeDetectionReport,
  FeatureConditioningReport,
} from '@/types'
import AnalysisFormModal from '@/components/robustness/AnalysisFormModal'
import ParameterSensitivityResults from '@/components/robustness/ParameterSensitivityResults'
import WalkForwardResults from '@/components/robustness/WalkForwardResults'
import RegimeDetectionResults from '@/components/robustness/RegimeDetectionResults'
import FeatureConditioningResults from '@/components/robustness/FeatureConditioningResults'
import { Activity, BarChart3, TrendingUp, Layers } from 'lucide-react'

const ANALYSIS_TYPES: Array<{
  type: AnalysisType
  title: string
  description: string
  icon: React.ReactNode
}> = [
  {
    type: 'parameter_sensitivity',
    title: 'Parameter Sensitivity',
    description: 'Test how strategy performance changes when indicator parameters vary ±20%',
    icon: <BarChart3 className="h-6 w-6" />,
  },
  {
    type: 'walk_forward',
    title: 'Walk-Forward Validation',
    description: 'Validate consistency across multiple time periods',
    icon: <TrendingUp className="h-6 w-6" />,
  },
  {
    type: 'regime_detection',
    title: 'Regime Detection',
    description: 'Analyze performance under different market regimes',
    icon: <Activity className="h-6 w-6" />,
  },
  {
    type: 'feature_conditioning',
    title: 'Feature Conditioning',
    description: 'Identify market conditions that favor or hurt the strategy',
    icon: <Layers className="h-6 w-6" />,
  },
]

export function RobustnessPage() {
  const { id } = useParams()
  const navigate = useNavigate()
  const { data: strategies, isLoading: loadingStrategies } = useStrategies()

  const [selectedType, setSelectedType] = useState<AnalysisType | null>(null)
  const [submitting, setSubmitting] = useState(false)

  // Analysis result state
  const [analysis, setAnalysis] = useState<RobustnessAnalysis | null>(null)
  const [loadingAnalysis, setLoadingAnalysis] = useState(false)
  const [pollingId, setPollingId] = useState<string | null>(null)

  // Load analysis by ID
  useEffect(() => {
    if (!id) {
      setAnalysis(null)
      return
    }

    setLoadingAnalysis(true)
    getRobustnessAnalysis(id)
      .then((data) => {
        setAnalysis(data)
        if (data.status === 'PENDING' || data.status === 'RUNNING') {
          setPollingId(data.id)
        }
      })
      .catch((err) => {
        console.error('Failed to load analysis:', err)
        navigate('/robustness')
      })
      .finally(() => setLoadingAnalysis(false))
  }, [id, navigate])

  // Poll for status updates
  useEffect(() => {
    if (!pollingId) return

    const interval = setInterval(() => {
      getRobustnessAnalysis(pollingId)
        .then((data) => {
          setAnalysis(data)
          if (data.status !== 'PENDING' && data.status !== 'RUNNING') {
            setPollingId(null)
          }
        })
        .catch((err) => {
          console.error('Polling error:', err)
          setPollingId(null)
        })
    }, 2000)

    return () => clearInterval(interval)
  }, [pollingId])

  const handleStartAnalysis = async (params: Record<string, unknown>) => {
    if (!selectedType) return

    setSubmitting(true)
    try {
      let result: RobustnessAnalysis

      switch (selectedType) {
        case 'parameter_sensitivity':
          result = await startParameterSensitivity(params as never)
          break
        case 'walk_forward':
          result = await startWalkForward(params as never)
          break
        case 'regime_detection':
          result = await startRegimeDetection(params as never)
          break
        case 'feature_conditioning':
          result = await startFeatureConditioning(params as never)
          break
        default:
          throw new Error('Unknown analysis type')
      }

      setSelectedType(null)
      navigate(`/robustness/${result.id}`)
    } catch (err) {
      console.error('Failed to start analysis:', err)
    } finally {
      setSubmitting(false)
    }
  }

  const renderResults = () => {
    if (!analysis?.report) return null

    // Normalize to lowercase for comparison
    const analysisType = analysis.analysis_type?.toLowerCase()

    switch (analysisType) {
      case 'parameter_sensitivity':
        return (
          <ParameterSensitivityResults
            report={analysis.report as unknown as ParameterSensitivityReport}
          />
        )
      case 'walk_forward':
        return (
          <WalkForwardResults
            report={analysis.report as unknown as WalkForwardReport}
          />
        )
      case 'regime_detection':
        return (
          <RegimeDetectionResults
            report={analysis.report as unknown as RegimeDetectionReport}
          />
        )
      case 'feature_conditioning':
        return (
          <FeatureConditioningResults
            report={analysis.report as unknown as FeatureConditioningReport}
          />
        )
      default:
        return <pre>{JSON.stringify(analysis.report, null, 2)}</pre>
    }
  }

  // Show analysis results
  if (id) {
    if (loadingAnalysis) {
      return (
        <>
          <Header title="Robustness Analysis" />
          <div className="p-6">
            <Skeleton className="h-48" />
          </div>
        </>
      )
    }

    if (!analysis) {
      return (
        <>
          <Header title="Robustness Analysis" />
          <div className="p-6">
            <Card>
              <CardContent className="py-8">
                <p className="text-center text-muted-foreground">Analysis not found</p>
              </CardContent>
            </Card>
          </div>
        </>
      )
    }

    const isPending = analysis.status === 'PENDING' || analysis.status === 'RUNNING'

    return (
      <>
        <Header title="Robustness Analysis" />
        <div className="p-6 space-y-6">
          {/* Analysis header */}
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <div>
                  <CardTitle className="capitalize">
                    {analysis.analysis_type.replace(/_/g, ' ')}
                  </CardTitle>
                  <CardDescription>
                    Created {new Date(analysis.created_at).toLocaleString()}
                  </CardDescription>
                </div>
                <div className="flex items-center gap-4">
                  <Badge
                    variant={
                      analysis.status === 'COMPLETE' || analysis.status === 'COMPLETED'
                        ? 'default'
                        : analysis.status === 'FAILED'
                        ? 'destructive'
                        : 'secondary'
                    }
                  >
                    {analysis.status}
                  </Badge>
                  <Button variant="outline" onClick={() => navigate('/robustness')}>
                    ← Back
                  </Button>
                </div>
              </div>
            </CardHeader>
          </Card>

          {/* Status or results */}
          {isPending ? (
            <Card>
              <CardContent className="py-12">
                <div className="flex flex-col items-center gap-4">
                  <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-primary" />
                  <p className="text-muted-foreground">
                    Analysis in progress... This may take a few minutes.
                  </p>
                </div>
              </CardContent>
            </Card>
          ) : analysis.status === 'FAILED' ? (
            <Card>
              <CardContent className="py-8">
                <p className="text-destructive text-center">
                  {analysis.error_message || 'Analysis failed'}
                </p>
              </CardContent>
            </Card>
          ) : (
            <ErrorBoundary>
              {renderResults()}
            </ErrorBoundary>
          )}
        </div>
      </>
    )
  }

  // Show analysis type selector
  return (
    <>
      <Header title="Robustness Analysis" />
      <div className="p-6 space-y-6">
        <Card>
          <CardHeader>
            <CardTitle>Start New Analysis</CardTitle>
            <CardDescription>
              Select an analysis type to evaluate your strategy's robustness
            </CardDescription>
          </CardHeader>
          <CardContent>
            {loadingStrategies ? (
              <div className="space-y-2">
                <Skeleton className="h-24" />
                <Skeleton className="h-24" />
              </div>
            ) : !strategies?.length ? (
              <p className="text-muted-foreground text-center py-8">
                No strategies available. Create a strategy first.
              </p>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {ANALYSIS_TYPES.map((item) => (
                  <div
                    key={item.type}
                    className="p-4 border rounded-lg hover:border-primary cursor-pointer transition-colors"
                    onClick={() => setSelectedType(item.type)}
                  >
                    <div className="flex items-start gap-4">
                      <div className="p-2 rounded-lg bg-primary/10 text-primary">
                        {item.icon}
                      </div>
                      <div className="flex-1">
                        <h3 className="font-semibold">{item.title}</h3>
                        <p className="text-sm text-muted-foreground mt-1">
                          {item.description}
                        </p>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Analysis form modal */}
      {selectedType && strategies && (
        <AnalysisFormModal
          analysisType={selectedType}
          strategies={strategies}
          onClose={() => setSelectedType(null)}
          onSubmit={handleStartAnalysis}
          submitting={submitting}
        />
      )}
    </>
  )
}
