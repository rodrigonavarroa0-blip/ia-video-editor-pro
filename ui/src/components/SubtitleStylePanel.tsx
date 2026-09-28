import React from 'react';
import { Type, Volume2 } from 'lucide-react';
import { SubtitlePresetConfig } from '../types';

interface SubtitleStylePanelProps {
  config: SubtitlePresetConfig;
  onChangeConfig: (newConfig: SubtitlePresetConfig) => void;
  targetLufs: number;
  onChangeLufs: (lufs: number) => void;
}

export const SubtitleStylePanel: React.FC<SubtitleStylePanelProps> = ({
  config,
  onChangeConfig,
  targetLufs,
  onChangeLufs,
}) => {
  const presets: Array<{ id: SubtitlePresetConfig['preset']; name: string; desc: string }> = [
    { id: 'hormozi', name: 'Hormozi Kinetic', desc: 'Impactante con pop y oro' },
    { id: 'bold_pop', name: 'Bold Pop', desc: 'Escalado 108% con cyan' },
    { id: 'minimal', name: 'Minimal Modern', desc: 'Limpio y sutil' },
    { id: 'cinema', name: 'Cinema Elegance', desc: 'Estilo cinematográfico' },
  ];

  return (
    <aside className="right-panel">
      {/* Subtitles Section */}
      <div>
        <div className="panel-title" style={{ marginBottom: 12 }}>
          <Type size={16} color="var(--accent-gold)" />
          <span>Estilos de Subtítulos (ASS)</span>
        </div>

        {/* Preset Cards */}
        <div className="preset-cards-grid">
          {presets.map((p) => {
            const isSelected = config.preset === p.id;
            return (
              <div
                key={p.id}
                onClick={() => onChangeConfig({ ...config, preset: p.id })}
                className={`preset-card ${isSelected ? 'active' : ''}`}
              >
                <div className="preset-card-name">{p.name}</div>
                <div className="preset-card-desc">{p.desc}</div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Subtitle Fine Tuning */}
      <div className="studio-group-card">
        <div className="slider-group">
          <div className="slider-label-row">
            <span>Tamaño de Fuente</span>
            <span className="slider-value-pill">{config.fontSize} pt</span>
          </div>
          <input
            type="range"
            min="36"
            max="72"
            value={config.fontSize}
            onChange={(e) => onChangeConfig({ ...config, fontSize: Number(e.target.value) })}
          />
        </div>

        <div className="slider-group">
          <div className="slider-label-row">
            <span>Grosor de Trazo / Borde</span>
            <span className="slider-value-pill">{config.outlineWidth} px</span>
          </div>
          <input
            type="range"
            min="2"
            max="8"
            value={config.outlineWidth}
            onChange={(e) => onChangeConfig({ ...config, outlineWidth: Number(e.target.value) })}
          />
        </div>
      </div>

      {/* Audio Mastering Section */}
      <div>
        <div className="panel-title" style={{ marginBottom: 12 }}>
          <Volume2 size={16} color="var(--accent-emerald)" />
          <span>Masterización EBU R128</span>
        </div>

        <div className="studio-group-card">
          <div className="slider-group">
            <div className="slider-label-row">
              <span>Target Sonoridad Integrada</span>
              <span className="slider-value-pill emerald">{targetLufs.toFixed(1)} LUFS</span>
            </div>
            <input
              type="range"
              min="-24"
              max="-10"
              step="0.5"
              value={targetLufs}
              onChange={(e) => onChangeLufs(Number(e.target.value))}
              className="emerald"
            />
          </div>
          <div className="helper-text">
            Estándar acústico broadcast para TikTok / Reels / Shorts: -14.0 LUFS integrado con True Peak ≤ -1.0 dBTP.
          </div>
        </div>
      </div>
    </aside>
  );
};
