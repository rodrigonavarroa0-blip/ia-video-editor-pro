# Documentación de Arquitectura — IA Video Editor Pro

## Resumen del Sistema
- **Core**: Python 3.10+ con contratos estrictos Pydantic.
- **Frontend**: Tauri v2 + React 19 + TypeScript + Tailwind CSS.
- **Video Engine**: FFmpeg con aceleración VideoToolbox en macOS.
- **Speech Engine**: faster-whisper con timestamps por palabra.
- **Vision Engine**: MediaPipe + OpenCV para Face Tracking y Smart Reframing 9:16.
- **Semantic Engine**: Gemini 3.7 Flash con Structured Output (JSON Schema) + Fallback heurístico local.
- **Filosofía**: Non-destructive editing, local-first, determinismo y separación estricta de etapas.
