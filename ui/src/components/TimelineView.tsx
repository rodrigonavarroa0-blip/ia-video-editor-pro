import React, { useRef } from 'react';
import { Scissors, Volume2, Type, Video } from 'lucide-react';
import { EditDecision, VirtualTimeline } from '../types';

interface TimelineViewProps {
  timeline: VirtualTimeline | null;
  decisions: EditDecision[];
  currentTime: number;
  duration: number;
  onSeek: (time: number) => void;
}

export const TimelineView: React.FC<TimelineViewProps> = ({
  timeline,
  decisions,
  currentTime,
  duration,
  onSeek,
}) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const totalDuration = Math.max(1.0, duration || timeline?.duration_seconds || 10.0);

  const handleTimelineClick = (e: React.MouseEvent<HTMLDivElement>) => {
    if (!containerRef.current) return;
    const rect = containerRef.current.getBoundingClientRect();
    const clickX = e.clientX - rect.left;
    const ratio = Math.max(0, Math.min(1, clickX / rect.width));
    onSeek(ratio * totalDuration);
  };

  const playheadPercent = Math.min(100, Math.max(0, (currentTime / totalDuration) * 100));

  return (
    <footer className="bottom-timeline">
      {/* Timeline Controls Header */}
      <div className="timeline-header">
        <div className="timeline-title-group">
          <Scissors size={14} color="var(--accent-gold)" />
          <span style={{ color: '#ffffff' }}>TIMELINE MULTIPISTA</span>
          <span style={{ opacity: 0.3 }}>|</span>
          <span style={{ fontWeight: 500 }}>{decisions.length} Decisiones Editoriales</span>
        </div>

        {/* Tracks Legend */}
        <div className="timeline-legend">
          <div className="legend-item">
            <div className="legend-dot emerald" />
            <span>V1 Video</span>
          </div>
          <div className="legend-item">
            <div className="legend-dot purple" />
            <span>Zoom 1.15x</span>
          </div>
          <div className="legend-item">
            <div className="legend-dot gold" />
            <span>S1 Subtítulos</span>
          </div>
          <div className="legend-item">
            <div className="legend-dot cyan" />
            <span>A1 Audio Master</span>
          </div>
        </div>
      </div>

      {/* Main Tracks Area */}
      <div
        ref={containerRef}
        onClick={handleTimelineClick}
        className="timeline-tracks-area"
      >
        {/* Playhead Line */}
        <div
          className="playhead-needle"
          style={{ left: `${playheadPercent}%` }}
        >
          <div className="playhead-diamond" />
        </div>

        {/* TRACK V1: VIDEO A-ROLL */}
        <div className="timeline-track">
          <div className="track-label-badge">
            <Video size={11} color="var(--accent-cyan)" />
            <span>V1</span>
          </div>

          {decisions.map((dec, idx) => {
            if (dec.action === 'cut') return null;
            const startPct = (dec.source_in / totalDuration) * 100;
            const widthPct = ((dec.source_out - dec.source_in) / totalDuration) * 100;
            const isZoom = dec.action === 'zoom_in';

            return (
              <div
                key={idx}
                className={`timeline-clip-block ${isZoom ? 'zoom' : ''}`}
                style={{ left: `${startPct}%`, width: `${widthPct}%` }}
              >
                <span>{dec.reason || `Clip #${idx + 1}`}</span>
                {isZoom && <span className="clip-zoom-pill">1.15x</span>}
              </div>
            );
          })}
        </div>

        {/* TRACK S1: SUBTÍTULOS CINÉTICOS */}
        <div className="timeline-track secondary">
          <div className="track-label-badge">
            <Type size={11} color="var(--accent-gold)" />
            <span>S1</span>
          </div>

          <div
            className="timeline-clip-block subtitles"
            style={{ left: '0%', width: '96%' }}
          >
            Subtítulos ASS Cinéticos Hormozi
          </div>
        </div>

        {/* TRACK A1: MASTER AUDIO (-14 LUFS) */}
        <div className="timeline-track secondary">
          <div className="track-label-badge">
            <Volume2 size={11} color="var(--accent-emerald)" />
            <span>A1</span>
          </div>

          <div
            className="timeline-clip-block audio"
            style={{ left: '0%', width: '100%' }}
          >
            Voz Masterizada EBU R128 (-14.0 LUFS)
          </div>
        </div>
      </div>
    </footer>
  );
};
