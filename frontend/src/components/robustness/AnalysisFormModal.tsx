import { useState, useMemo } from "react";
import type {
  AnalysisType,
  StrategyOut,
  RegimeStrategy,
} from "../../types";

interface AnalysisFormModalProps {
  analysisType: AnalysisType;
  strategies: StrategyOut[];
  onClose: () => void;
  onSubmit: (params: Record<string, unknown>) => void;
  submitting: boolean;
}

const ANALYSIS_TITLES: Record<AnalysisType, string> = {
  parameter_sensitivity: "Parameter Sensitivity Analysis",
  walk_forward: "Walk-Forward Validation",
  regime_detection: "Regime Detection",
  feature_conditioning: "Feature Conditioning",
};

const ANALYSIS_DESCRIPTIONS: Record<AnalysisType, string> = {
  parameter_sensitivity:
    "Tests strategy robustness by varying indicator parameters +/-20% and measuring metric stability.",
  walk_forward:
    "Divides data into time windows and tests consistency across periods.",
  regime_detection:
    "Identifies market regimes and analyzes performance in different market conditions.",
  feature_conditioning:
    "Extracts market features at trade entries to identify winning/losing conditions.",
};

export default function AnalysisFormModal({
  analysisType,
  strategies,
  onClose,
  onSubmit,
  submitting,
}: AnalysisFormModalProps) {
  const [selectedStrategyId, setSelectedStrategyId] = useState<string>(
    strategies.length > 0 ? strategies[0].id : ""
  );
  const [ticker, setTicker] = useState("AAPL");
  const [assetClass, setAssetClass] = useState<"STOCK" | "CRYPTO">("STOCK");
  const [startDate, setStartDate] = useState("2020-01-01");
  const [endDate, setEndDate] = useState("2023-12-31");
  const [resolution, setResolution] = useState("1d");
  const [initialCapital, setInitialCapital] = useState("10000");

  // Analysis-specific options
  const [variationPct, setVariationPct] = useState("0.2");
  const [windowCount, setWindowCount] = useState("5");
  const [segmentationStrategy, setSegmentationStrategy] =
    useState<RegimeStrategy>("pelt_volatility");
  const [lookbackWindow, setLookbackWindow] = useState("50");

  const resolutionOptions = useMemo(
    () =>
      assetClass === "CRYPTO"
        ? ["1m", "5m", "15m", "30m", "1h", "4h", "1d"]
        : ["1m", "5m", "15m", "30m", "1h", "1d"],
    [assetClass]
  );

  const handleSubmit = () => {
    const baseParams = {
      strategy_id: selectedStrategyId,
      ticker,
      asset_class: assetClass,
      start_date: startDate,
      end_date: endDate,
      bar_resolution: resolution,
      initial_capital: Number(initialCapital),
    };

    let additionalParams = {};

    switch (analysisType) {
      case "parameter_sensitivity":
        additionalParams = { variation_pct: Number(variationPct) };
        break;
      case "walk_forward":
        additionalParams = { window_count: Number(windowCount) };
        break;
      case "regime_detection":
        additionalParams = { segmentation_strategy: segmentationStrategy };
        break;
      case "feature_conditioning":
        additionalParams = { lookback_window: Number(lookbackWindow) };
        break;
    }

    onSubmit({ ...baseParams, ...additionalParams });
  };

  return (
    <div className="modal-backdrop">
      <div className="modal">
        <h3>{ANALYSIS_TITLES[analysisType]}</h3>
        <p style={{ color: "var(--muted)", fontSize: "0.9rem", marginBottom: "16px" }}>
          {ANALYSIS_DESCRIPTIONS[analysisType]}
        </p>

        <div className="row" style={{ marginTop: "12px" }}>
          <div>
            <label>Strategy</label>
            <select
              value={selectedStrategyId}
              onChange={(e) => setSelectedStrategyId(e.target.value)}
            >
              {strategies.map((strategy) => (
                <option key={strategy.id} value={strategy.id}>
                  {strategy.name}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label>Ticker</label>
            <input value={ticker} onChange={(e) => setTicker(e.target.value)} />
          </div>
        </div>

        <div className="row" style={{ marginTop: "12px" }}>
          <div>
            <label>Asset Class</label>
            <select
              value={assetClass}
              onChange={(e) => setAssetClass(e.target.value as "STOCK" | "CRYPTO")}
            >
              <option value="STOCK">STOCK</option>
              <option value="CRYPTO">CRYPTO</option>
            </select>
          </div>
          <div>
            <label>Resolution</label>
            <select value={resolution} onChange={(e) => setResolution(e.target.value)}>
              {resolutionOptions.map((opt) => (
                <option key={opt} value={opt}>
                  {opt}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label>Initial Capital</label>
            <input
              type="number"
              value={initialCapital}
              onChange={(e) => setInitialCapital(e.target.value)}
            />
          </div>
        </div>

        <div className="row" style={{ marginTop: "12px" }}>
          <div>
            <label>Start Date</label>
            <input
              type="date"
              value={startDate}
              onChange={(e) => setStartDate(e.target.value)}
            />
          </div>
          <div>
            <label>End Date</label>
            <input
              type="date"
              value={endDate}
              onChange={(e) => setEndDate(e.target.value)}
            />
          </div>
        </div>

        {/* Analysis-specific options */}
        {analysisType === "parameter_sensitivity" && (
          <div className="card" style={{ marginTop: "16px" }}>
            <h4>Parameter Sensitivity Options</h4>
            <div className="row">
              <div>
                <label>Variation Percentage</label>
                <select
                  value={variationPct}
                  onChange={(e) => setVariationPct(e.target.value)}
                >
                  <option value="0.1">+/- 10%</option>
                  <option value="0.2">+/- 20%</option>
                  <option value="0.3">+/- 30%</option>
                </select>
              </div>
            </div>
          </div>
        )}

        {analysisType === "walk_forward" && (
          <div className="card" style={{ marginTop: "16px" }}>
            <h4>Walk-Forward Options</h4>
            <div className="row">
              <div>
                <label>Number of Windows</label>
                <select
                  value={windowCount}
                  onChange={(e) => setWindowCount(e.target.value)}
                >
                  <option value="3">3 Windows</option>
                  <option value="5">5 Windows</option>
                  <option value="10">10 Windows</option>
                </select>
              </div>
            </div>
          </div>
        )}

        {analysisType === "regime_detection" && (
          <div className="card" style={{ marginTop: "16px" }}>
            <h4>Regime Detection Options</h4>
            <div className="row">
              <div>
                <label>Segmentation Strategy</label>
                <select
                  value={segmentationStrategy}
                  onChange={(e) =>
                    setSegmentationStrategy(e.target.value as RegimeStrategy)
                  }
                >
                  <option value="l1_trend">L1 Trend (BULL/BEAR)</option>
                  <option value="pelt_directional">
                    PELT Directional (BULL/BEAR/CHOPPY/RANGING)
                  </option>
                  <option value="pelt_volatility">
                    PELT Volatility (HIGH_VOL/LOW_VOL/TRANSITION)
                  </option>
                </select>
              </div>
            </div>
            <p style={{ fontSize: "0.85rem", color: "var(--muted)", marginTop: "8px" }}>
              L1 Trend is stable with 2 regimes. PELT strategies are more responsive with
              4 regimes.
            </p>
          </div>
        )}

        {analysisType === "feature_conditioning" && (
          <div className="card" style={{ marginTop: "16px" }}>
            <h4>Feature Conditioning Options</h4>
            <div className="row">
              <div>
                <label>Lookback Window (bars)</label>
                <select
                  value={lookbackWindow}
                  onChange={(e) => setLookbackWindow(e.target.value)}
                >
                  <option value="20">20 bars</option>
                  <option value="50">50 bars</option>
                  <option value="100">100 bars</option>
                </select>
              </div>
            </div>
          </div>
        )}

        <div className="row" style={{ justifyContent: "flex-end", marginTop: "16px" }}>
          <button className="btn secondary" onClick={onClose}>
            Cancel
          </button>
          <button
            className="btn"
            onClick={handleSubmit}
            disabled={submitting || !selectedStrategyId}
          >
            {submitting ? "Starting..." : "Start Analysis"}
          </button>
        </div>
      </div>
    </div>
  );
}
