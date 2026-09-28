import React from 'react';
import { Brain } from 'lucide-react';
import { EditDecision, EditorialPlan } from '../types';

interface DecisionPanelProps {
  plan: EditorialPlan | null;
  decisions: EditDecision[];
  onToggleAction: (index: number) => void;
  onSelectDecision: (decision: EditDecision) => void;
}

export const DecisionPanel: React.FC<DecisionPanelProps> = ({
  plan,
  decisions,
  onToggleAction,
  onSelectDecision,
}) => {
  return (
    <aside className="left-panel">
      {/* Metrics Header */}
      <div className="panel-header">
        <div className="panel-title-row">
          <div className="panel-title">
            <Brain size={16} color="var(--accent-gold)" />
            <span>IA Editorial Brain</span>
          </div>
          <span className="badge-ai">Gemini 3.7 Flash</span>
        </div>

        {/* Retention Scores */}
        <div className="metrics-grid">
          <div className="metric-card">
            <div className="metric-label">Hook Score</div>
            <div className="metric-value gold">
              {((plan?.hook_score || 0.88) * 100).toFixed(0)}%
            </div>
          </div>

          <div className="metric-card">
            <div className="metric-label">Retención</div>
            <div className="metric-value emerald">
              {((plan?.retention_score || 0.92) * 100).toFixed(0)}%
            </div>
          </div>

          <div className="metric-card">
            <div className="metric-label">Redundancia</div>
            <div className="metric-value rose">
              {((plan?.redundancy_score || 0.05) * 100).toFixed(0)}%
            </div>
          </div>
        </div>
      </div>

      {/* Decisions List */}
      <div className="decisions-container">
        <div className="section-label">
          Decisiones de Edición ({decisions.length})
        </div>

        {decisions.map((dec, idx) => {
          const isCut = dec.action === 'cut';
          const isZoom = dec.action === 'zoom_in';
          const cardClass = isCut ? 'decision-card cut' : isZoom ? 'decision-card zoom' : 'decision-card';
          const pillClass = isCut ? 'action-pill cut' : isZoom ? 'action-pill zoom_in' : 'action-pill keep';

          return (
            <div
              key={idx}
              onClick={() => onSelectDecision(dec)}
              className={cardClass}
            >
              <div className="decision-card-top">
                <div className="decision-timecode-badge">
                  <span className="decision-timecode">
                    {dec.source_in.toFixed(1)}s - {dec.source_out.toFixed(1)}s
                  </span>
                  <span className={pillClass}>
                    {dec.action}
                  </span>
                </div>

                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    onToggleAction(idx);
                  }}
                  className="btn-toggle-action"
                >
                  {isCut ? 'Restaurar' : 'Cortar'}
                </button>
              </div>

              <p className="decision-reason">{dec.reason}</p>
            </div>
          );
        })}
      </div>
    </aside>
  );
};
