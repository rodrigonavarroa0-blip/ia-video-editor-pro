import React, { useRef, useState, useEffect, useCallback } from 'react';
import { Play, Pause, SkipBack, SkipForward, Volume2, VolumeX, Eye, Sparkles } from 'lucide-react';
import { SubtitlePresetConfig, WordTimestamp } from '../types';

interface VideoPlayerProps {
  videoSrc?: string;
  currentTime: number;
  duration: number;
  isPlaying: boolean;
  onTimeUpdate: (time: number) => void;
  onTogglePlay: () => void;
  words: WordTimestamp[];
  subtitleConfig: SubtitlePresetConfig;
  showSafeAreas: boolean;
  onToggleSafeAreas: () => void;
}

export const VideoPlayer: React.FC<VideoPlayerProps> = ({
  videoSrc,
  currentTime,
  duration,
  isPlaying,
  onTimeUpdate,
  onTogglePlay,
  words,
  subtitleConfig,
  showSafeAreas,
  onToggleSafeAreas,
}) => {
  const videoRef = useRef<HTMLVideoElement>(null);
  const rafRef = useRef<number | null>(null);
  const [isMuted, setIsMuted] = useState(false);
  const [showFaceBox] = useState(true);
  const [isScrubbing, setIsScrubbing] = useState(false);
  const [localTime, setLocalTime] = useState(currentTime);

  // Sincronizar estado de reproducción con el elemento video
  useEffect(() => {
    if (videoRef.current) {
      if (isPlaying && videoRef.current.paused) {
        videoRef.current.play().catch(() => {});
      } else if (!isPlaying && !videoRef.current.paused) {
        videoRef.current.pause();
      }
    }
  }, [isPlaying]);

  // Sincronizar tiempo externo sólo si la diferencia es significativa y no estamos scrubbing
  useEffect(() => {
    if (!isScrubbing && videoRef.current && Math.abs(videoRef.current.currentTime - currentTime) > 0.5) {
      videoRef.current.currentTime = currentTime;
    }
    setLocalTime(currentTime);
  }, [currentTime, isScrubbing]);

  // RAF loop para actualizar UI suavemente mientras reproduce
  const startRaf = useCallback(() => {
    const tick = () => {
      if (videoRef.current && !isScrubbing) {
        const t = videoRef.current.currentTime;
        setLocalTime(t);
        onTimeUpdate(t);
      }
      rafRef.current = requestAnimationFrame(tick);
    };
    rafRef.current = requestAnimationFrame(tick);
  }, [isScrubbing, onTimeUpdate]);

  const stopRaf = useCallback(() => {
    if (rafRef.current !== null) {
      cancelAnimationFrame(rafRef.current);
      rafRef.current = null;
    }
  }, []);

  useEffect(() => {
    if (isPlaying) {
      startRaf();
    } else {
      stopRaf();
    }
    return stopRaf;
  }, [isPlaying, startRaf, stopRaf]);

  const stepFrame = (frames: number) => {
    if (videoRef.current) {
      const newTime = Math.max(0, Math.min(duration, videoRef.current.currentTime + (frames / 30.0)));
      videoRef.current.currentTime = newTime;
      onTimeUpdate(newTime);
      setLocalTime(newTime);
    }
  };

  const formatSMPTE = (seconds: number) => {
    const sec = Math.max(0, seconds);
    const h = Math.floor(sec / 3600);
    const m = Math.floor((sec % 3600) / 60);
    const s = Math.floor(sec % 60);
    const f = Math.floor((sec % 1) * 30);
    return `${String(h).padStart(2, '0')}:${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}:${String(f).padStart(2, '0')}`;
  };

  const handleScrubberChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const newTime = parseFloat(e.target.value);
    setLocalTime(newTime);
    if (videoRef.current) {
      videoRef.current.currentTime = newTime;
    }
    onTimeUpdate(newTime);
  };

  const handleScrubberMouseDown = () => setIsScrubbing(true);
  const handleScrubberMouseUp = () => setIsScrubbing(false);

  const progressPercent = duration > 0 ? (localTime / duration) * 100 : 0;

  // Subtítulos activos en el instante actual
  const currentWords = words.filter(
    (w) => localTime >= w.start - 0.05 && localTime <= w.end + 0.25
  );

  return (
    <div className="center-stage">
      {/* 9:16 Frame Container */}
      <div id="video-viewport-9-16" className="viewport-frame-9-16">
        {videoSrc ? (
          <video
            ref={videoRef}
            src={videoSrc}
            onEnded={() => onTogglePlay()}
            className="video-element"
            playsInline
            muted={isMuted}
          />
        ) : (
          <div className="viewport-empty-state">
            <div className="sparkle-icon-circle">
              <Sparkles size={28} />
            </div>
            <h3 className="viewport-empty-title">Previsualización Cinemática 9:16</h3>
            <p className="viewport-empty-desc">Material RAW conformando dinámicamente con Smart Reframing</p>
          </div>
        )}

        {/* Dynamic Safe Areas Overlay */}
        {showSafeAreas && (
          <div className="safe-areas-overlay">
            <div className="safe-areas-tag">SAFE ZONE 9:16 (TIKTOK / REELS)</div>
            <div className="safe-areas-tag" style={{ alignSelf: 'flex-end', opacity: 0.8 }}>CONTROLES UI APP</div>
          </div>
        )}

        {/* Face Tracking Box */}
        {showFaceBox && (
          <div className="face-tracker-box">
            <span className="face-tracker-tag">SUJETO 01 (98%)</span>
          </div>
        )}

        {/* Kinetic Subtitles Live Overlay */}
        <div className="subtitle-overlay">
          {currentWords.map((w, idx) => {
            const isActive = localTime >= w.start && localTime <= w.end;
            return (
              <span
                key={idx}
                className={`subtitle-word ${isActive ? 'active' : ''}`}
                style={{
                  fontFamily: subtitleConfig.fontName,
                  fontSize: `${subtitleConfig.fontSize * 0.42}px`,
                }}
              >
                {w.word}
              </span>
            );
          })}
        </div>
      </div>

      {/* Scrubber / Progress Bar */}
      <div className="scrubber-container">
        <input
          type="range"
          min={0}
          max={duration || 100}
          step={0.033}
          value={localTime}
          onChange={handleScrubberChange}
          onMouseDown={handleScrubberMouseDown}
          onMouseUp={handleScrubberMouseUp}
          onTouchStart={handleScrubberMouseDown}
          onTouchEnd={handleScrubberMouseUp}
          className="scrubber-track"
          style={{
            background: `linear-gradient(to right, var(--accent-gold) ${progressPercent}%, rgba(255,255,255,0.12) ${progressPercent}%)`,
          }}
        />
        <div className="scrubber-times">
          <span className="scrubber-time-current">{formatSMPTE(localTime)}</span>
          <span className="scrubber-time-total">{formatSMPTE(duration)}</span>
        </div>
      </div>

      {/* Floating Controls Bar */}
      <div className="player-controls-bar">
        <button onClick={() => stepFrame(-1)} title="Retroceder 1 fotograma" className="btn-icon-control">
          <SkipBack size={16} />
        </button>

        <button
          onClick={onTogglePlay}
          className="btn-play-pause"
          title={isPlaying ? 'Pausar (Espacio)' : 'Reproducir (Espacio)'}
        >
          {isPlaying
            ? <Pause size={18} fill="currentColor" />
            : <Play size={18} fill="currentColor" style={{ marginLeft: 2 }} />}
        </button>

        <button onClick={() => stepFrame(1)} title="Avanzar 1 fotograma" className="btn-icon-control">
          <SkipForward size={16} />
        </button>

        <div className="smpte-display">
          {formatSMPTE(localTime)} <span style={{ color: 'var(--text-muted)' }}>/</span> {formatSMPTE(duration)}
        </div>

        <button
          onClick={onToggleSafeAreas}
          title="Alternar Guías de Zona Segura 9:16"
          className={`btn-icon-control ${showSafeAreas ? 'active' : ''}`}
        >
          <Eye size={16} />
        </button>

        <button
          onClick={() => setIsMuted(!isMuted)}
          title={isMuted ? 'Activar sonido' : 'Silenciar'}
          className="btn-icon-control"
        >
          {isMuted ? <VolumeX size={16} color="var(--accent-rose)" /> : <Volume2 size={16} />}
        </button>
      </div>
    </div>
  );
};
