import React, { useState, useCallback } from 'react';
import { X, FolderOpen, Film, CheckCircle2, Loader2, AlertCircle, Clock } from 'lucide-react';

interface ImportVideoModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSelectSampleProject: (path: string) => void;
  onIngestCustomVideo: (filePath: string, name: string) => Promise<void>;
  isProcessing: boolean;
}

const SAMPLE_PROJECTS = [
  {
    path: './qa_golden_reports/golden_1_monologue',
    name: 'Monólogo Demo (Golden)',
    desc: 'Análisis completo con Hook 0.88, Retención 0.92',
    icon: '🎤',
    duration: '~12s',
  },
];

const SUPPORTED_EXTENSIONS = ['.mp4', '.mov', '.avi', '.mkv', '.webm', '.m4v', '.mts', '.hevc'];

export const ImportVideoModal: React.FC<ImportVideoModalProps> = ({
  isOpen,
  onClose,
  onSelectSampleProject,
  onIngestCustomVideo,
  isProcessing,
}) => {
  const [projectName, setProjectName] = useState('');
  const [selectedFile, setSelectedFile] = useState('');
  const [fileError, setFileError] = useState('');
  const [tab, setTab] = useState<'sample' | 'custom'>('sample');

  const validateExtension = (filePath: string): boolean => {
    const lower = filePath.toLowerCase();
    return SUPPORTED_EXTENSIONS.some((ext) => lower.endsWith(ext));
  };

  const handleChooseFile = useCallback(async () => {
    try {
      const res = await fetch('/api/system/choose_file');
      if (res.ok) {
        const data = await res.json();
        if (data.file_path) {
          const fp = data.file_path as string;
          setFileError('');
          if (!validateExtension(fp)) {
            setFileError(`Formato no soportado. Usa: ${SUPPORTED_EXTENSIONS.join(', ')}`);
            setSelectedFile('');
            return;
          }
          setSelectedFile(fp);
          // Auto-rellenar nombre con el nombre del archivo sin extensión
          const base = fp.split('/').pop() || fp;
          const nameWithoutExt = base.replace(/\.[^.]+$/, '').replace(/[-_]/g, ' ');
          if (!projectName) {
            setProjectName(nameWithoutExt.slice(0, 40));
          }
        }
      }
    } catch {
      setFileError('No se pudo abrir el selector de archivos.');
    }
  }, [projectName]);

  const handleIngest = async () => {
    setFileError('');
    if (!selectedFile) {
      setFileError('Selecciona un archivo de video primero.');
      return;
    }
    if (!validateExtension(selectedFile)) {
      setFileError(`Formato no soportado. Usa: ${SUPPORTED_EXTENSIONS.join(', ')}`);
      return;
    }
    const name = projectName.trim() || 'Mi Video';
    await onIngestCustomVideo(selectedFile, name);
    onClose();
  };

  const getFilename = (fp: string) => fp.split('/').pop() || fp;

  if (!isOpen) return null;

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-panel" style={{ maxWidth: 560 }} onClick={(e) => e.stopPropagation()}>
        {/* Header */}
        <div className="modal-header">
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <Film size={20} className="modal-icon" />
            <div>
              <h3 className="modal-title">Importar Video</h3>
              <p className="modal-subtitle">Selecciona un proyecto o ingresa tu propio material</p>
            </div>
          </div>
          <button onClick={onClose} className="btn-close-modal" disabled={isProcessing}>
            <X size={18} />
          </button>
        </div>

        {/* Tabs */}
        <div className="modal-tabs">
          <button
            className={`modal-tab ${tab === 'sample' ? 'active' : ''}`}
            onClick={() => setTab('sample')}
          >
            Proyectos de Ejemplo
          </button>
          <button
            className={`modal-tab ${tab === 'custom' ? 'active' : ''}`}
            onClick={() => setTab('custom')}
          >
            Mi Propio Video
          </button>
        </div>

        {/* Tab: Sample Projects */}
        {tab === 'sample' && (
          <div className="modal-body">
            <p className="modal-desc">
              Proyectos pre-analizados listos para explorar el editor sin necesidad de procesamiento.
            </p>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
              {SAMPLE_PROJECTS.map((proj) => (
                <button
                  key={proj.path}
                  className="sample-project-card"
                  onClick={() => {
                    onSelectSampleProject(proj.path);
                    onClose();
                  }}
                  disabled={isProcessing}
                >
                  <span style={{ fontSize: 28 }}>{proj.icon}</span>
                  <div style={{ flex: 1, textAlign: 'left' }}>
                    <div style={{ fontWeight: 600, color: 'var(--text-primary)', fontSize: '0.92rem' }}>
                      {proj.name}
                    </div>
                    <div style={{ fontSize: '0.78rem', color: 'var(--text-muted)', marginTop: 2 }}>
                      {proj.desc}
                    </div>
                  </div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 4, color: 'var(--text-muted)', fontSize: '0.76rem' }}>
                    <Clock size={12} />
                    {proj.duration}
                  </div>
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Tab: Custom Video */}
        {tab === 'custom' && (
          <div className="modal-body">
            <p className="modal-desc">
              Selecciona un video desde el Finder de macOS. El pipeline analizará el contenido automáticamente.
            </p>

            {/* File Picker */}
            <div className="file-picker-area">
              <button
                onClick={handleChooseFile}
                className="btn-choose-file"
                disabled={isProcessing}
              >
                <FolderOpen size={16} />
                Abrir Finder...
              </button>

              <div className={`file-selected-display ${selectedFile ? 'has-file' : ''}`}>
                {selectedFile ? (
                  <>
                    <CheckCircle2 size={14} color="var(--accent-emerald)" />
                    <span className="file-name-display">{getFilename(selectedFile)}</span>
                  </>
                ) : (
                  <span style={{ color: 'var(--text-muted)' }}>
                    Ningún archivo seleccionado
                  </span>
                )}
              </div>
            </div>

            {/* Formato admitido */}
            <p style={{ fontSize: '0.72rem', color: 'var(--text-muted)', marginTop: 4 }}>
              Formatos: {SUPPORTED_EXTENSIONS.join(' · ')}
            </p>

            {/* Project Name */}
            <div className="form-field" style={{ marginTop: 16 }}>
              <label className="form-label">Nombre del Proyecto</label>
              <input
                type="text"
                value={projectName}
                onChange={(e) => setProjectName(e.target.value)}
                placeholder="Ej: Mi Video TikTok"
                className="form-input"
                maxLength={60}
                disabled={isProcessing}
              />
            </div>

            {/* Error message */}
            {fileError && (
              <div className="modal-error-msg">
                <AlertCircle size={14} />
                {fileError}
              </div>
            )}

            {/* Processing indicator */}
            {isProcessing && (
              <div className="modal-processing-indicator">
                <Loader2 size={16} className="spin" />
                <span>Pipeline ejecutándose… puede tomar 30–120 segundos.</span>
              </div>
            )}
          </div>
        )}

        {/* Footer */}
        {tab === 'custom' && (
          <div className="modal-footer">
            <button onClick={onClose} className="btn-secondary" disabled={isProcessing}>
              Cancelar
            </button>
            <button
              onClick={handleIngest}
              className="btn-primary"
              disabled={isProcessing || !selectedFile}
            >
              {isProcessing ? (
                <>
                  <Loader2 size={15} className="spin" /> Procesando…
                </>
              ) : (
                <>
                  <Film size={15} /> Ingestar y Analizar
                </>
              )}
            </button>
          </div>
        )}
      </div>
    </div>
  );
};
