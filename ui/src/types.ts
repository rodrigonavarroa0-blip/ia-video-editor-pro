export type EditActionType = 'keep' | 'cut' | 'zoom_in' | 'speed_up' | 'b_roll' | 'emphasize';

export interface EditDecision {
  action: EditActionType;
  source_in: number;
  source_out: number;
  target_duration?: number;
  reason: string;
  b_roll_keyword?: string;
  zoom_scale?: number;
}

export interface EditorialPlan {
  project_id: string;
  summary: string;
  hook_score: number;
  retention_score: number;
  redundancy_score: number;
  decisions: EditDecision[];
  suggested_broll_keywords: string[];
  target_duration_seconds: number;
}

export interface WordTimestamp {
  word: string;
  start: number;
  end: number;
  confidence: number;
  is_filler?: boolean;
}

export interface CropCoordinate {
  center_x: number;
  center_y: number;
  scale: number;
}

export interface VideoClipItem {
  id: string;
  source_path: string;
  source_in: number;
  source_out: number;
  timeline_in: number;
  timeline_out: number;
  scale: number;
  crop: CropCoordinate;
}

export interface VirtualTimeline {
  version: number;
  project_id: string;
  fps: number;
  width: number;
  height: number;
  duration_seconds: number;
  video_clips: VideoClipItem[];
}

export interface ProjectManifest {
  name: string;
  profile: string;
  format: string;
  created_at: string;
  media_files?: Array<{ raw_path: string; proxy_path: string; audio_path: string }>;
  analysis_ready?: boolean;
  transcript_ready?: boolean;
  editorial_plan_ready?: boolean;
  vision_tracking_ready?: boolean;
  audio_processed?: boolean;
  subtitles_ready?: boolean;
  timeline_ready?: boolean;
  rendered?: boolean;
  final_video_path?: string;
  final_lufs?: number;
}

export interface SubtitlePresetConfig {
  name: string;
  preset: 'hormozi' | 'minimal' | 'bold_pop' | 'cinema';
  fontName: string;
  fontSize: number;
  primaryColor: string;
  highlightColor: string;
  outlineWidth: number;
  shadowWidth: number;
}
