import React, { useEffect, useState } from 'react';
import { CheckCircle2, Loader2, AlertCircle, Circle, X } from 'lucide-react';

type StepStatus = 'pending' | 'running' | 'done' | 'error';

interface PipelineStep {
  id: string;
  label: string;
  description: string;
  status: StepStatus;
  detail?: string;
}

const PIPELINE_STEPS: Omit<PipelineStep, 'status' | 'detail'>[] = [
  { id: 'init',            label: 'Inicializando Proyecto',   description: 'Creando estructura de carpetas y manifiesto' },
  { id: 'ingest',          label: 'Ingesta de Material RAW',  description: 'Verificando archivo y creando proxy de baja resolución' },
  { id: 'analyze',         label: 'Análisis Completo',        description: 'Transcripción Whisper · Detección de escenas · Análisis de silencios' },
  { id: 'plan_edit',       label: 'Plan Editorial IA',        description: 'Generando decisiones de corte, ritmo y zooms' },
  { id: 'reframe',         label: 'Smart Reframing 9:16',     description: 'Tracking facial y cálculo de keyframes de encuadre' },
  { id: 'enhance_audio',   label: 'Masterización de Audio',   description: 'Normalización EBU R128 · Brickwall limiting a -14 LUFS' },
  { id: 'build_timeline',  label: 'Construcción del Timeline', description: 'Ensamblando VirtualTimeline y exportando FCPXML/OTIO' },
];

interface PipelineProgressModalProps {
  isOpen: boolean;
  onClose: () => void;
  videoName: string;
  pipelineSteps: Array<{ step: string; status: StepStatus; detail?: string }>;
  isComplete: boolean;
  hasError: boolean;
  hookScore?: number;
  retentionScore?: number;
}

const StepIcon: React.FC<{ status: StepStatus }> = ({ status }) => {
  if (status === 'done') return <CheckCircle2 size={18} color="var(--accent-emerald)" />;
  if (status === 'running') return <Loader2 size={18} color="var(--accent-gold)" className="spin" />;
  if (status === 'error') return <AlertCircle size={18} color="var(--accent-rose)" />;
  return <Circle size={18} color="var(--text-muted)" strokeWidth={1.5} />;
};

export const PipelineProgressModal: React.FC<PipelineProgressModalProps> = ({
  isOpen,
  onClose,
  videoName,
  pipelineSteps,
  isComplete,
  hasError,
  hookScore,
  retentionScore,
}) => {
  const [displaySteps, setDisplaySteps] = useState<PipelineStep[]>(
    PIPELINE_STEPS.map((s) => ({ ...s, status: 'pending' }))
  );
  const completedCount = displaySteps.filter(s => s.status === 'done').length;
  const totalProgress = Math.round((completedCount / PIPELINE_STEPS.length) * 100);

  useEffect(() => {
    setDisplaySteps(
      PIPELINE_STEPS.map((template) => {
        const serverStep = pipelineSteps.find((ps) => ps.step === template.id);
        if (!serverStep) return { ...template, status: 'pending' as StepStatus };
        return { ...template, status: serverStep.status, detail: serverStep.detail };
      })
    );
  }, [pipelineSteps]);

  if (!isOpen) return null;

  const filename = videoName.split('/').pop() || videoName;

  return (
    <div className="modal-overlay">
      <div className="modal-panel pipeline-modal" onClick={(e) => e.stopPropagation()}>
        {/* Header */}
        <div className="modal-header">
          <div>
            <h3 className="modal-title">
              {isComplete ? (hasError ? '⚠ Pipeline Interrumpido' : '✓ Pipeline Completado') : 'Procesando Pipeline…'}
            </h3>
            <p className="modal-subtitle" style={{ maxWidth: 380, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
              {filename}
            </p>
          </div>
          {(isComplete) && (
            <button onClick={onClose} className="btn-close-modal">
              <X size={18} />
            </button>
          )}
        </div>

        {/* Progress Bar */}
        <div className="pipeline-progress-bar-track">
          <div
            className={`pipeline-progress-bar-fill ${hasError ? 'error' : ''}`}
            style={{ width: `${totalProgress}%` }}
          />
        </div>
        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 20, fontSize: '0.75rem', color: 'var(--text-muted)' }}>
          <span>{completedCount}/{PIPELINE_STEPS.length} pasos</span>
          <span>{totalProgress}%</span>
        </div>

        {/* Steps List */}
        <div className="pipeline-steps-list">
          {displaySteps.map((step, idx) => (
            <div key={step.id} className={`pipeline-step-row ${step.status}`}>
              <div className="step-icon-col">
                <StepIcon status={step.status} />
                {idx < displaySteps.length - 1 && (
                  <div className={`step-connector ${step.status === 'done' ? 'done' : ''}`} />
                )}
              </div>
              <div className="step-content-col">
                <div className="step-label">{step.label}</div>
                <div className="step-description">{step.description}</div>
                {step.detail && (
                  <div className="step-detail">{step.detail}</div>
                )}
              </div>
              <div className="step-status-badge">
                {step.status === 'pending' && <span className="badge pending">Pendiente</span>}
                {step.status === 'running' && <span className="badge running">En Proceso</span>}
                {step.status === 'done' && <span className="badge done">✓</span>}
                {step.status === 'error' && <span className="badge error">Error</span>}
              </div>
            </div>
          ))}
        </div>

        {/* Completion Summary */}
        {isComplete && !hasError && hookScore !== undefined && (
          <div className="pipeline-summary-card">
            <div className="summary-metric">
              <span className="metric-label">Hook Score</span>
              <span className="metric-value" style={{ color: hookScore >= 0.7 ? 'var(--accent-emerald)' : 'var(--accent-gold)' }}>
                {Math.round(hookScore * 100)}%
              </span>
            </div>
            <div className="summary-divider" />
            <div className="summary-metric">
              <span className="metric-label">Retención Est.</span>
              <span className="metric-value" style={{ color: retentionScore !== undefined && retentionScore >= 0.7 ? 'var(--accent-emerald)' : 'var(--accent-gold)' }}>
                {retentionScore !== undefined ? `${Math.round(retentionScore * 100)}%` : '—'}
              </span>
            </div>
          </div>
        )}

        {/* Footer */}
        {isComplete && (
          <div className="modal-footer">
            {hasError ? (
              <button onClick={onClose} className="btn-secondary">Cerrar</button>
            ) : (
              <button onClick={onClose} className="btn-primary">
                <CheckCircle2 size={15} /> Ver en Editor
              </button>
            )}
          </div>
        )}

        {!isComplete && (
          <div className="pipeline-running-hint">
            <Loader2 size={13} className="spin" />
            <span>Esto puede tardar 30–120 segundos dependiendo de la duración del video</span>
          </div>
        )}
      </div>
    </div>
  );
};
