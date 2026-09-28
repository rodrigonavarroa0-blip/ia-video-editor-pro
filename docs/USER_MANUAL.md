# 🎬 IA Video Editor Pro — Manual de Usuario y Guía Técnica Oficial

Bienvenido a la documentación oficial de **IA Video Editor Pro** (`iva`), el motor de edición automatizada asistido por Inteligencia Artificial diseñado para creadores de contenido, agencias y editores profesionales de videos verticales de alta retención (**TikTok, Reels, Shorts y Podcasts**).

---

## 1. Arquitectura y Principio No-Destructivo

IA Video Editor Pro trabaja con una arquitectura estrictamente **no-destructiva**:
1. **Material RAW Inmutable**: Los videos originales se copian a `raw/` y nunca se modifican. Su integridad se valida mediante hashes criptográficos **SHA-256**.
2. **Proxies Livianos 720p**: Se generan copias optimizadas en `proxies/` para análisis rápido de visión artificial, transcripción y detección de silencios.
3. **Conformación Directa a RAW**: El render final master aplica todos los cortes, encuadres 9:16 y zooms directamente sobre el archivo **RAW en resolución nativa (4K / 1080p)** con aceleración por hardware (**Apple VideoToolbox / NVENC**).

---

## 2. Inicio Rápido con la Interfaz Gráfica (Desktop Studio)

Para iniciar la suite visual interactiva:

```bash
iva ui --port 8000
```

### Componentes de la Interfaz:
- **Reproductor Vertical 9:16**: Previsualización cinemática con sincronización de subtítulos palabra por palabra, selector de zonas seguras (TikTok/Reels) y visualización de encuadre de rostros.
- **Timeline Multipista Interactiva**: Pistas visuales V1 (Video con badges de corte y zoom 1.15x), S1 (Subtítulos cinéticos) y A1 (Audio masterizado -14 LUFS) con scrubber interactivo.
- **Panel de Decisiones Editoriales**: Métricas de Hook Score, Retención y Redundancia con capacidad de override manual (*Restaurar corte*, *Forzar corte*, *Aplicar zoom*).
- **Estudio de Subtítulos**: Selección de presets (*Hormozi*, *Bold Pop*, *Minimal*, *Cinema*) y ajustes de sonoridad EBU R128.
- **Diálogo de Exportación**: Renderizado acelerado por hardware con presets *Social 9:16*, *Master RAW* o *Preview*.

---

## 3. Referencia Completa de Comandos CLI (`iva`)

| Comando | Descripción | Ejemplo de Uso |
| :--- | :--- | :--- |
| `iva info` | Muestra estado del sistema y soporte VideoToolbox. | `iva info` |
| `iva init-project` | Inicializa un nuevo proyecto estructurado. | `iva init-project ./mi_reel --name "Mi Reel" --profile social` |
| `iva probe` | Inspecciona metadatos técnicos de video/audio. | `iva probe /ruta/video.mp4` |
| `iva ingest` | Ingesta RAW, crea proxy 720p y extrae audio WAV. | `iva ingest ./mi_reel /ruta/video.mp4` |
| `iva transcribe` | Transcribe fonéticamente con `faster-whisper`. | `iva transcribe ./mi_reel --model small --language es` |
| `iva analyze` | Ejecuta análisis integral (Whisper + OpenCV + DSP). | `iva analyze ./mi_reel` |
| `iva plan-edit` | Genera plan editorial con Gemini 3.7 Flash o heurística. | `iva plan-edit ./mi_reel --offline` |
| `iva reframe` | Smart Reframing 9:16 con Face Tracking. | `iva reframe ./mi_reel --format 9:16` |
| `iva enhance-audio`| Masteriza audio a -14 LUFS (EBU R128) y aplica EQ. | `iva enhance-audio ./mi_reel --target -14.0` |
| `iva generate-subtitles` | Genera subtítulos cinéticos ASS, SRT y WebVTT. | `iva generate-subtitles ./mi_reel --style hormozi` |
| `iva build-timeline` | Construye VirtualTimeline y exporta EDL, FCPXML, OTIO. | `iva build-timeline ./mi_reel --fps 30` |
| `iva render` | Conformación a RAW y exportación final master. | `iva render ./mi_reel --preset social` |
| `iva golden-test` | Ejecuta la suite de 3 Golden Tests de no-regresión. | `iva golden-test --output-dir ./qa_reports` |
| `iva ui` | Inicia el servidor local y abre la Desktop UI. | `iva ui --port 8000` |
| `iva package` | Empaqueta `.app` e instalador `.dmg` para macOS. | `iva package --output-dir ./release` |

---

## 4. Integración con Editores Profesionales (NLE)

IA Video Editor Pro genera automáticamente los formatos de intercambio estándar en `timeline/`:
- **CMX 3600 EDL (`timeline/export.edl`)**: Para importar cortes precisos en **Adobe Premiere Pro** y **Avid Media Composer**.
- **Final Cut Pro XML v1.9 (`timeline/export.fcpxml`)**: Para abrir secuencias directas en **DaVinci Resolve** y **Final Cut Pro**.
- **OpenTimelineIO (`timeline/export.otio`)**: Formato de la Academy Software Foundation para pipelines de post-producción avanzados.
