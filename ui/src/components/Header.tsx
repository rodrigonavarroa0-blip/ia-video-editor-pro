import React from 'react';
import { Sparkles, Film, Cpu, Download, RefreshCw, FolderOpen } from 'lucide-react';
import { ProjectManifest } from '../types';

interface HeaderProps {
  manifest: ProjectManifest | null;
  onOpenExport: () => void;
  onOpenImport: () => void;
  onRunPipeline: () => void;
  isProcessing: boolean;
}

export const Header: React.FC<HeaderProps> = ({
  manifest,
  onOpenExport,
  onOpenImport,
  onRunPipeline,
  isProcessing,
}) => {
  return (
    <header className="header-container">
      {/* Brand & Project Info */}
      <div className="header-left">
        <div className="brand-badge">
          <div className="brand-icon-box">
            <Sparkles size={16} strokeWidth={2.5} />
          </div>
          <span className="brand-title">
            IA Video Editor <span className="brand-pro-tag">PRO</span>
          </span>
        </div>

        <div className="header-divider" />

        <div className="project-meta-pill">
          <Film size={14} />
          <span className="project-name">{manifest?.name || 'Demo Video Reel 9:16'}</span>
          <span className="project-format-tag">
            {manifest?.profile || 'social'} (9:16)
          </span>
        </div>
      </div>

      {/* Hardware & Actions */}
      <div className="header-right">
        {/* Hardware Status */}
        <div className="hw-status-badge">
          <Cpu size={14} />
          <span>Apple VideoToolbox HW</span>
        </div>

        {/* Ingest / Open Project Button */}
        <button
          id="btn-open-import"
          onClick={onOpenImport}
          className="btn-secondary"
          title="Cargar o Ingestar Video"
        >
          <FolderOpen size={14} color="var(--accent-gold)" />
          <span>Cargar Video</span>
        </button>

        {/* Re-Analyze Pipeline Button */}
        <button
          id="btn-reanalyze"
          onClick={onRunPipeline}
          disabled={isProcessing}
          className="btn-secondary"
        >
          <RefreshCw size={14} className={isProcessing ? 'spinner' : ''} />
          <span>{isProcessing ? 'Procesando IA...' : 'Re-analizar IA'}</span>
        </button>

        {/* Export / Render Button */}
        <button
          id="btn-open-export"
          onClick={onOpenExport}
          className="btn-primary-gradient"
        >
          <Download size={14} strokeWidth={2.5} />
          <span>EXPORTAR VIDEO</span>
        </button>
      </div>
    </header>
  );
};
