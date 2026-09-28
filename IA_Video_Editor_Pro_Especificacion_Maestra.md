# IA Video Editor Pro — Especificación Maestra del Producto

> **Documento de arquitectura, producto y desarrollo**
>
> Versión: 2.0 — Especificación ampliada  
> Objetivo: construir un editor de video automatizado de nivel profesional, local-first, orientado a creación de contenido personal y empresarial, con énfasis en automatización, calidad de montaje y costos de software cercanos a cero.

---

# 1. Visión del producto

## 1.1 Concepto

**IA Video Editor Pro** será una aplicación de edición audiovisual asistida por inteligencia artificial capaz de recibir uno o varios archivos de video en bruto y producir automáticamente una edición profesional basada en reglas de montaje, análisis de audio, visión computacional, semántica, composición, color y métricas de calidad.

El objetivo no es simplemente “cortar silencios”.

El objetivo es construir un **motor de decisión editorial** que pueda responder:

- qué partes del material sirven;
- qué partes deberían eliminarse;
- dónde conviene hacer un corte;
- cuándo introducir un zoom;
- cuándo cambiar el encuadre;
- cuándo mostrar subtítulos;
- qué palabras deben destacarse;
- cuándo introducir B-Roll;
- cómo equilibrar voz, música y efectos;
- cómo adaptar el video a distintas plataformas;
- cómo exportar una versión final de alta calidad;
- y cómo explicar por qué el sistema tomó determinadas decisiones.

## 1.2 Posicionamiento

La aplicación debe acercarse conceptualmente a una combinación de:

- editor no lineal;
- asistente de edición;
- sistema de auto-reencuadre;
- motor de subtítulos;
- procesador de audio;
- analizador de contenido;
- generador de versiones para redes;
- pipeline de render profesional.

No se debe intentar copiar literalmente el código, interfaz o propiedades internas de Premiere Pro o DaVinci Resolve.

En cambio, se deben implementar **criterios propios de calidad editorial** inspirados en prácticas profesionales.

---

# 2. Problema que resuelve

Actualmente, editar un video de calidad puede exigir muchas operaciones manuales:

1. importar material;
2. revisar horas de grabación;
3. seleccionar tomas;
4. eliminar errores;
5. eliminar silencios;
6. ajustar ritmo;
7. limpiar audio;
8. corregir niveles;
9. recortar a vertical;
10. realizar seguimiento del sujeto;
11. agregar subtítulos;
12. agregar elementos gráficos;
13. hacer zooms;
14. incorporar B-Roll;
15. agregar música;
16. ajustar música debajo de la voz;
17. corregir color;
18. revisar cortes;
19. exportar;
20. revisar el resultado;
21. realizar correcciones;
22. volver a exportar.

El producto pretende convertir buena parte de este proceso en un pipeline automático y configurable.

---

# 3. Objetivos

## 3.1 Objetivo principal

Transformar material audiovisual en bruto en una edición lista para publicar con una intervención manual mínima.

## 3.2 Objetivos secundarios

- reducir drásticamente el tiempo de edición;
- mantener calidad visual y sonora;
- generar una edición consistente;
- evitar errores de sincronización;
- conservar los archivos originales;
- trabajar localmente siempre que sea posible;
- permitir intervención humana antes del render final;
- generar diferentes formatos desde un mismo proyecto;
- funcionar sin depender obligatoriamente de una base de datos;
- tener arquitectura preparada para escalar a una versión empresarial.

---

# 4. Filosofía técnica

## 4.1 Local-first

La primera versión debe priorizar procesamiento local.

Esto reduce:

- costos de API;
- exposición de material audiovisual;
- dependencia de Internet;
- tiempos de subida;
- costos variables por minuto de video.

## 4.2 Determinista donde sea posible

No todo debe resolverse con IA generativa.

Usar:

- FFmpeg para transformación y render;
- OpenCV para visión clásica;
- modelos especializados para transcripción;
- algoritmos matemáticos para silencio, volumen, escenas y movimiento;
- IA generativa solo donde aporte razonamiento semántico.

## 4.3 Reproducibilidad

Cada procesamiento debe poder producir un:

```text
analysis/
    media.json
    transcript.json
    scenes.json
    faces.json
    audio_metrics.json
    edit_plan.json
    quality_report.json
```

Esto permite repetir renders sin volver a ejecutar todo el análisis.

---

# 5. Principio arquitectónico fundamental

## Separar ANALIZAR de EDITAR y de RENDERIZAR

La aplicación no debe modificar directamente el video original.

Debe seguir este esquema:

```text
RAW
 ↓
INGESTA
 ↓
ANÁLISIS
 ↓
PLAN EDITORIAL
 ↓
TIMELINE VIRTUAL
 ↓
PREVISUALIZACIÓN
 ↓
APROBACIÓN / AJUSTES
 ↓
CONFORMADO CON ORIGINAL
 ↓
RENDER FINAL
```

Esta decisión es fundamental.

Permite:

- cambiar decisiones sin reprocesar todo;
- conservar el video fuente;
- generar distintas versiones;
- depurar errores;
- crear undo/redo;
- comparar ediciones;
- regenerar solo partes.

---

# 6. Arquitectura general

```text
┌────────────────────────────────────────────┐
│              DESKTOP APPLICATION            │
│                                              │
│  React + Tauri                               │
│  ├── Project Manager                         │
│  ├── Media Browser                           │
│  ├── Timeline                                │
│  ├── Preview                                 │
│  ├── AI Decisions                            │
│  ├── Export Center                           │
│  └── Settings                                │
└──────────────────┬───────────────────────────┘
                   │
                   ▼
┌────────────────────────────────────────────┐
│                CORE ENGINE                  │
│                                              │
│ Python                                      │
│ ├── ingestion                               │
│ ├── analysis                                │
│ ├── timeline                                │
│ ├── audio                                   │
│ ├── vision                                  │
│ ├── subtitles                               │
│ ├── editorial engine                        │
│ ├── render planning                          │
│ └── quality control                         │
└──────────────────┬───────────────────────────┘
                   │
       ┌───────────┼─────────────┐
       ▼           ▼             ▼
    FFmpeg      AI Models     Media Assets
    Renderer    Local AI      LUT/SFX/B-roll
```

---

# 7. Stack tecnológico recomendado

## 7.1 Frontend

### Recomendación

- React
- TypeScript
- Vite
- Tauri
- Tailwind CSS

### Razones

Tauri permite construir una aplicación de escritorio utilizando tecnologías web, con un runtime liviano.

React permite:

- construir una interfaz compleja;
- timeline;
- paneles;
- reproductor;
- inspector;
- estados de procesamiento;
- configuración por proyecto.

---

# 8. Backend / Core Engine

## Python

Python será responsable de:

- procesamiento audiovisual;
- análisis;
- IA;
- generación del timeline;
- ejecución de FFmpeg;
- gestión de archivos;
- exportación de JSON;
- coordinación de workers.

Dependencias principales:

```text
ffmpeg-python
opencv-python
numpy
scipy
pydub
soundfile
librosa
pyloudnorm
pedalboard
faster-whisper
mediapipe
```

Dependiendo de la implementación final también se pueden evaluar:

```text
torch
onnxruntime
sentence-transformers
transformers
```

---

# 9. Motor de video

## FFmpeg

FFmpeg debe ser el núcleo real de:

- decodificación;
- extracción;
- transcodificación;
- cortes;
- concatenación;
- escalado;
- crop;
- overlays;
- subtítulos;
- audio;
- filtros;
- encoding final.

No conviene usar MoviePy como motor principal de todo el sistema.

Puede usarse como herramienta auxiliar, pero el pipeline crítico debe construirse preferentemente alrededor de FFmpeg y archivos temporales controlados.

---

# 10. Aceleración en Apple Silicon

El software deberá detectar automáticamente las capacidades disponibles.

En macOS se debe evaluar:

```text
VideoToolbox
Metal
MPS
CPU
```

FFmpeg soporta VideoToolbox como mecanismo de aceleración de hardware en plataformas Apple.

La arquitectura debe permitir:

```text
hardware acceleration enabled
```

pero también:

```text
software fallback
```

Nunca asumir que todos los codecs o filtros tendrán aceleración completa.

---

# 11. Inteligencia artificial

## 11.1 Transcripción

Usar una implementación de Whisper o una alternativa optimizada para inferencia local.

Preferencia inicial:

```text
faster-whisper
```

Alternativa:

```text
whisper.cpp
```

El sistema debe generar:

```json
{
  "language": "es",
  "segments": [],
  "words": []
}
```

Cada palabra debería almacenar:

```text
word
start
end
confidence
speaker (optional)
```

---

# 12. Motor semántico

El LLM no debe editar directamente el video.

El LLM debe generar **decisiones estructuradas**.

Ejemplo:

```json
{
  "segment_id": 13,
  "keep": true,
  "importance": 0.91,
  "hook_score": 0.87,
  "energy": 0.78,
  "reason": "Explica el beneficio principal del producto"
}
```

El renderizador solo debe ejecutar instrucciones válidas.

Nunca permitir:

```text
LLM → comando arbitrario de shell
```

Debe existir una capa intermedia:

```text
LLM
 ↓
JSON schema
 ↓
Validator
 ↓
Edit Planner
 ↓
Render Engine
```

---

# 13. Arquitectura del análisis audiovisual

El sistema debe procesar el video mediante múltiples analizadores.

## 13.1 Media Analyzer

Extrae:

- duración;
- resolución;
- fps;
- codec;
- bitrate;
- canales de audio;
- sample rate;
- orientación;
- metadata;
- color space.

Salida:

```json
{
  "duration": 134.4,
  "width": 3840,
  "height": 2160,
  "fps": 30,
  "codec": "hevc"
}
```

---

# 14. Scene Detection

Detectar cambios de plano utilizando:

- diferencia de histogramas;
- diferencia de frames;
- detección de cortes;
- análisis de movimiento.

Cada escena:

```json
{
  "start": 25.40,
  "end": 31.10,
  "duration": 5.70,
  "score": 0.81
}
```

---

# 15. Silence Detection

No usar una regla absoluta como:

```text
silencio > 0.4 = eliminar
```

Eso puede destruir pausas naturales.

Implementar niveles:

```text
0.0–0.25 s → mantener
0.25–0.50 s → evaluar
0.50–1.00 s → probable reducción
>1.00 s → fuerte candidato a recorte
```

El algoritmo debe analizar:

- duración;
- contexto lingüístico;
- respiración;
- final de frase;
- comienzo de frase;
- energía vocal.

---

# 16. Speech Rate

Calcular:

```text
palabras por minuto
```

Usar esta métrica para detectar:

- segmentos demasiado lentos;
- segmentos demasiado rápidos;
- partes naturalmente pausadas.

No imponer una velocidad universal.

---

# 17. Hook Score

Crear una métrica propia de gancho.

Ejemplo:

```text
Hook Score =
  0.25 × claridad
+ 0.20 × novedad
+ 0.20 × especificidad
+ 0.15 × tensión
+ 0.10 × beneficio
+ 0.10 × velocidad
```

Este score es heurístico y debe poder cambiarse desde configuración.

---

# 18. Retention Score

Construir una métrica estimada de retención.

Variables:

```text
Hook Score
Pacing Score
Silence Ratio
Visual Change Rate
Speech Energy
Semantic Density
Question/Curiosity Score
Redundancy Score
```

Resultado:

```text
0–39   = bajo
40–59  = aceptable
60–74  = bueno
75–89  = muy bueno
90–100 = excelente
```

No afirmar que representa la retención real de TikTok, Instagram o YouTube.

Es una métrica interna de calidad predictiva.

---

# 19. Redundancy Detection

Detectar:

- frases repetidas;
- ideas duplicadas;
- reformulaciones;
- muletillas;
- repeticiones involuntarias.

Ejemplos:

```text
"o sea"
"básicamente"
"este..."
"tipo..."
"bueno..."
```

La detección debe ser configurable por idioma.

---

# 20. Filler Word Detection

Crear un diccionario configurable:

```json
{
  "es": [
    "eh",
    "este",
    "bueno",
    "o sea",
    "tipo"
  ]
}
```

Estas palabras no deben eliminarse siempre.

Deben clasificarse:

```text
natural
innecesaria
repetitiva
error
```

---

# 21. Face Tracking

Usar:

- MediaPipe;
- OpenCV;
- trackers adicionales cuando sean necesarios.

El objetivo:

```text
frame
 ↓
face detection
 ↓
face landmark
 ↓
subject position
 ↓
crop path
```

El movimiento del crop debe suavizarse para evitar:

```text
camera jitter
```

---

# 22. Smart Reframing

Para video 16:9 → 9:16:

```text
source: 3840 × 2160
output: 1080 × 1920
```

La posición horizontal debe variar dinámicamente.

Agregar:

```text
dead zone
smoothing
acceleration limit
look-ahead
subject priority
```

Esto evita que el encuadre “persiga” bruscamente al sujeto.

---

# 23. Multi-person Tracking

Si aparecen varias personas:

1. detectar personas;
2. asignar scores;
3. identificar sujeto dominante;
4. determinar posición grupal;
5. decidir si conviene plano individual o grupal.

Ejemplo:

```text
single subject → face priority
two subjects   → center weighted
group scene    → wider crop
```

---

# 24. Visual Energy

Medir cambios visuales por segundo.

Variables:

```text
scene_changes
motion
camera_movement
face_position_change
zoom_events
graphic_events
```

El sistema debe evitar períodos excesivamente estáticos cuando el contenido requiere mayor dinamismo.

---

# 25. Dynamic Zoom

El zoom no debe activarse por cada frase.

Definir:

```text
zoom_in_probability
zoom_out_probability
max_zoom
min_duration
cooldown
```

Ejemplo:

```text
normal: 1.00x
emphasis: 1.08x
strong emphasis: 1.14x
```

Nunca exceder límites configurables.

---

# 26. Audio Engine

El audio debe ser tratado como un subsistema independiente.

Pipeline:

```text
RAW AUDIO
 ↓
High-pass
 ↓
Noise reduction
 ↓
EQ
 ↓
Compression
 ↓
De-essing
 ↓
Limiter
 ↓
Loudness analysis
 ↓
Final mix
```

---

# 27. Loudness

No asumir que existe un único estándar universal de “-14 LUFS”.

Crear presets:

```text
Social Standard
YouTube
Podcast
Corporate
Voice Priority
Custom
```

Ejemplo:

```json
{
  "target_lufs": -14,
  "true_peak": -1.0
}
```

Los valores deben ser editables.

---

# 28. Voice Enhancement

Crear un preset de voz:

```text
HPF
80–100 Hz
↓
mud control
↓
presence
↓
compression
↓
de-esser
↓
limiter
```

Los parámetros deben configurarse de acuerdo con análisis del material y no aplicarse ciegamente.

---

# 29. Música y Ducking

Cuando exista música:

```text
voice detected
      ↓
music gain decreases
      ↓
voice finishes
      ↓
music returns gradually
```

Debe usarse un envelope suave.

Ejemplo:

```text
duck: -8 dB
attack: 150 ms
release: 600 ms
```

---

# 30. Subtítulos

Sistema de subtítulos basado en timestamps por palabra.

Debe soportar:

- palabra individual;
- grupos de palabras;
- frases;
- resaltado;
- emojis;
- símbolos;
- estilos;
- posiciones;
- safe areas.

---

# 31. Subtitle Engine

Crear un esquema interno:

```json
{
  "text": "Esto es increíble",
  "start": 2.10,
  "end": 3.40,
  "style": "bold_pop",
  "keywords": ["increíble"]
}
```

---

# 32. Estilos

Implementar inicialmente:

```text
Classic
Bold
Minimal
Gaming
Corporate
Podcast
High Contrast
Kinetic
```

Cada estilo debe ser un archivo de configuración y no código duro.

---

# 33. Kinetic Typography

Animaciones:

```text
fade
pop
slide
scale
bounce
word highlight
```

Debe existir una duración máxima y mínima para no producir animaciones excesivas.

---

# 34. Safe Areas

El sistema debe conocer las áreas potencialmente tapadas por interfaces de:

- TikTok;
- Reels;
- Shorts;
- otras plataformas.

No depender de posiciones absolutas.

Usar porcentajes de la composición:

```text
top safe
bottom safe
left safe
right safe
```

---

# 35. B-Roll

## Versión inicial

No hacer búsqueda automática online como dependencia obligatoria.

Implementar:

```text
local B-roll library
```

El usuario puede importar una carpeta:

```text
assets/broll/
```

El sistema genera embeddings o tags.

Ejemplo:

```text
car
money
computer
business
gym
travel
city
food
```

Luego selecciona material relacionado con el contenido.

---

# 36. B-Roll inteligente

Pipeline:

```text
Transcript
 ↓
Semantic chunks
 ↓
Keywords
 ↓
B-roll candidates
 ↓
Similarity score
 ↓
Temporal placement
 ↓
Opacity / cut strategy
```

No cubrir información crítica del hablante por demasiado tiempo.

---

# 37. SFX Engine

Biblioteca local:

```text
whoosh
pop
click
impact
transition
notification
```

Los SFX deben ser:

- cortos;
- configurables;
- normalizados;
- sincronizados;
- opcionales.

---

# 38. Music Engine

Sistema de música:

```text
music library
 ↓
genre
 ↓
tempo
 ↓
energy
 ↓
license
```

Cada pista debe tener metadata.

Ejemplo:

```json
{
  "title": "Track 01",
  "bpm": 118,
  "energy": 0.76,
  "license": "royalty_free"
}
```

---

# 39. Color Engine

No aplicar LUT indiscriminadamente.

Primero detectar:

- exposure;
- white balance aproximado;
- contrast;
- saturation;
- clipping.

Después aplicar:

```text
technical correction
 ↓
creative look
```

---

# 40. LUT System

Soportar:

```text
.cube
```

Organización:

```text
assets/
    luts/
        cinematic/
        clean/
        warm/
        corporate/
```

---

# 41. Color presets

Inicialmente:

```text
Natural
Clean
Cinematic
Warm
Cold
Contrast
Corporate
```

---

# 42. Timeline Virtual

El proyecto debe contar con un timeline interno.

Ejemplo:

```json
{
  "version": 1,
  "tracks": [
    {
      "type": "video",
      "clips": []
    },
    {
      "type": "audio",
      "clips": []
    },
    {
      "type": "graphics",
      "clips": []
    }
  ]
}
```

---

# 43. EDL interno

Cada decisión de edición debe transformarse en una instrucción estructurada.

Ejemplo:

```json
{
  "source": "camera_01.mp4",
  "in": 25.10,
  "out": 31.40,
  "scale": 1.08,
  "crop_x": 0.43,
  "crop_y": 0.50,
  "subtitle": true,
  "broll": null
}
```

---

# 44. Nunca editar destructivamente

No modificar:

```text
RAW/
```

Crear:

```text
PROJECT/
    raw/
    cache/
    analysis/
    proxies/
    timeline/
    assets/
    renders/
```

---

# 45. Sistema de caché

Guardar:

```text
proxy
audio analysis
transcription
face tracking
scene detection
embeddings
render intermediates
```

Si el usuario vuelve a abrir el proyecto, reutilizar resultados existentes.

---

# 46. Jobs y procesamiento

No ejecutar todo en un solo proceso.

Crear un sistema de jobs:

```text
queued
running
paused
completed
failed
cancelled
```

Ejemplo:

```text
JOB 01 → ingest
JOB 02 → proxy
JOB 03 → transcription
JOB 04 → scene analysis
JOB 05 → face tracking
JOB 06 → editorial analysis
JOB 07 → timeline
JOB 08 → render
```

---

# 47. Parallel Processing

Las tareas independientes deben ejecutarse en paralelo cuando el hardware lo permita.

Ejemplo:

```text
                 ┌→ transcription
video → analysis ┼→ scene detection
                 ├→ face tracking
                 └→ audio analysis
```

Luego:

```text
all analyses
      ↓
editorial engine
```

---

# 48. Fault Tolerance

Si falla un módulo:

```text
no perder el proyecto
```

Registrar:

```text
error type
timestamp
module
command
stderr
retry count
```

---

# 49. Logging

Estructura:

```text
logs/
    app.log
    analysis.log
    ffmpeg.log
    ai.log
    render.log
```

Usar niveles:

```text
DEBUG
INFO
WARNING
ERROR
CRITICAL
```

---

# 50. Quality Control automático

Antes de exportar:

```text
resolution check
fps check
audio sync
black frames
frozen frames
clipping
subtitle overflow
safe area
audio peak
missing assets
broken links
```

Generar:

```json
{
  "status": "pass",
  "warnings": [],
  "errors": []
}
```

---

# 51. Auto Review

El sistema debe hacer una segunda revisión de la edición.

Pipeline:

```text
EDIT PLAN
 ↓
RENDER PREVIEW
 ↓
RE-ANALYZE RESULT
 ↓
QUALITY CHECK
 ↓
FIX / ACCEPT
```

Esto crea un ciclo:

```text
plan → render → review → improve
```

---

# 52. Métrica editorial global

Crear:

```text
Professional Edit Score
```

Ejemplo conceptual:

```text
PES =
25% Audio
20% Pacing
15% Visual Stability
15% Story Structure
10% Subtitle Quality
10% Framing
5% Technical Quality
```

Rango:

```text
0–100
```

Esta puntuación pertenece al producto y no debe presentarse como una métrica oficial de Adobe, Blackmagic o una plataforma social.

---

# 53. Modos de edición

## Mode A — Minimal

- pocos cortes;
- subtítulos discretos;
- poco zoom;
- color natural.

## Mode B — Social

- cortes más dinámicos;
- subtítulos grandes;
- zoom;
- SFX moderados.

## Mode C — Professional

- pacing equilibrado;
- color limpio;
- audio refinado;
- motion graphics moderados.

## Mode D — Corporate

- branding;
- ritmo moderado;
- subtítulos limpios;
- lower thirds;
- colores consistentes.

## Mode E — Podcast

- multicámara futura;
- cortes por hablante;
- subtítulos;
- B-roll contextual.

---

# 54. Perfil de proyecto

Cada proyecto debe guardar:

```text
project.json
```

Ejemplo:

```json
{
  "name": "Video producto",
  "language": "es",
  "format": "9:16",
  "fps": 30,
  "resolution": "1080x1920",
  "edit_mode": "social",
  "subtitle_style": "bold",
  "target_lufs": -14
}
```

---

# 55. Perfiles de exportación

Inicialmente:

```text
TikTok 1080x1920
Instagram Reels 1080x1920
YouTube Shorts 1080x1920
YouTube 1920x1080
Instagram Feed 1080x1350
Square 1080x1080
Custom
```

Los parámetros deben vivir en configuración.

---

# 56. Export Pipeline

```text
Timeline JSON
      ↓
Validate
      ↓
Resolve media
      ↓
Build FFmpeg graph
      ↓
Conform with RAW
      ↓
Encode
      ↓
Quality Check
      ↓
Final Export
```

---

# 57. Render reproducible

Un proyecto debe permitir:

```text
same project
+
same assets
+
same settings
=
same edit
```

Siempre que los componentes externos y versiones sean equivalentes.

---

# 58. Interfaz de usuario

## Pantalla principal

```text
┌──────────────────────────────────────────┐
│ IA VIDEO EDITOR PRO                      │
├───────────┬─────────────────┬────────────┤
│ PROJECT   │ PREVIEW         │ INSPECTOR  │
│           │                 │            │
│ Media     │                 │ AI Score   │
│ Scenes    │                 │ Audio      │
│ Assets    │                 │ Crop       │
│           │                 │ Subtitle   │
├───────────┴─────────────────┴────────────┤
│ TIMELINE                                  │
│ V1 ───────────────────────────────────── │
│ A1 ───────────────────────────────────── │
│ G1 ───────────────────────────────────── │
├──────────────────────────────────────────┤
│ ANALYZE | AUTO EDIT | PREVIEW | EXPORT   │
└──────────────────────────────────────────┘
```

---

# 59. UX de Auto Edit

Flujo:

```text
1. Create Project
2. Import Video
3. Analyze
4. Choose Edit Style
5. Generate Edit
6. Preview
7. Review Decisions
8. Adjust
9. Export
```

---

# 60. Explicabilidad

Cada decisión importante debe poder mostrar:

```text
¿Por qué eliminaste este segmento?
```

Respuesta:

```text
Silencio: 1.24 s
Redundancia: 82%
Energía: baja
Confianza editorial: 91%
```

Esto es extremadamente importante para confianza del usuario.

---

# 61. Human-in-the-loop

El sistema debe ser automático, pero nunca obligatoriamente autónomo.

Controles:

```text
Approve
Reject
Keep
Restore
Regenerate
Lock clip
Lock crop
Lock subtitle
```

---

# 62. Sistema de configuración

Toda regla importante debe vivir fuera del código.

Ejemplo:

```text
config/
    editing.yaml
    audio.yaml
    subtitles.yaml
    export.yaml
    ai.yaml
    profiles/
        social.yaml
        youtube.yaml
        corporate.yaml
```

---

# 63. Configuración del Pacing

Ejemplo:

```yaml
silence:
  analyze_above_ms: 250
  suggest_cut_above_ms: 500
  aggressive_cut_above_ms: 1000

zoom:
  max_scale: 1.14
  min_duration_ms: 700
  cooldown_ms: 1800
```

---

# 64. Configuración de IA

Debe permitir cambiar:

```text
model
temperature
max_tokens
timeout
fallback
```

Pero la lógica crítica no debe depender de un LLM.

---

# 65. Estrategia de IA gratuita

La prioridad debe ser:

## Nivel 1 — Local

- Whisper / faster-whisper / whisper.cpp;
- modelos pequeños locales;
- OpenCV;
- MediaPipe;
- ONNX Runtime;
- FFmpeg.

## Nivel 2 — API gratuita o con cuota

Solo para funcionalidades opcionales.

## Nivel 3 — API de pago

Nunca obligatoria para el funcionamiento básico.

---

# 66. LLM local

Para análisis semántico se puede diseñar una interfaz abstracta:

```python
class LanguageModel:
    def analyze_transcript(self, transcript):
        ...
```

Implementaciones:

```text
LocalLLM
GeminiProvider
FutureProvider
```

Esto evita acoplar todo el sistema a un proveedor.

---

# 67. Seguridad

Nunca entregar al LLM acceso directo a:

- shell;
- filesystem completo;
- FFmpeg;
- comandos arbitrarios.

Usar:

```text
structured actions
```

Ejemplo:

```json
{
  "action": "CUT",
  "start": 15.3,
  "end": 16.8
}
```

Validar cada acción.

---

# 68. Sandboxing conceptual

Los workers deben operar únicamente dentro de:

```text
project_root/
```

Nunca permitir rutas arbitrarias generadas por modelos.

Validar:

```text
path traversal
absolute paths
file extensions
command arguments
```

---

# 69. Privacidad

Modo recomendado:

```text
LOCAL ONLY
```

El proyecto debe poder funcionar sin subir:

- videos;
- audios;
- transcripciones;
- imágenes.

Si una función usa API externa, mostrar claramente:

```text
This feature sends data to an external provider.
```

---

# 70. Arquitectura de carpetas

```text
ia-video-editor/
│
├── app/
│   ├── core/
│   ├── analyzers/
│   ├── ai/
│   ├── audio/
│   ├── vision/
│   ├── timeline/
│   ├── subtitles/
│   ├── render/
│   ├── quality/
│   └── utils/
│
├── desktop/
│   ├── src/
│   └── src-tauri/
│
├── config/
│
├── assets/
│
├── tests/
│
├── scripts/
│
├── docs/
│
└── projects/
```

---

# 71. Contratos entre módulos

Cada módulo debe tener entrada y salida explícitas.

Ejemplo:

```python
AnalysisResult
EditorialPlan
Timeline
RenderJob
QualityReport
```

No intercambiar datos complejos mediante variables globales.

---

# 72. Modelos internos

Crear dataclasses o Pydantic models:

```text
MediaInfo
Transcript
Word
Scene
FaceTrack
AudioMetrics
EditDecision
TimelineClip
Subtitle
RenderPreset
QualityReport
```

---

# 73. Tests

## Unit tests

Testear:

- timestamp conversions;
- silence detection;
- EDL;
- clip trimming;
- crop calculation;
- score calculation.

## Integration tests

Testear:

```text
video
→ analysis
→ edit plan
→ timeline
→ render
```

## Golden tests

Guardar algunos outputs conocidos y comparar:

```text
duration
resolution
frame count
audio duration
```

---

# 74. Test media

Crear un conjunto de videos pequeños:

```text
talking_head.mp4
two_people.mp4
silences.mp4
fast_speech.mp4
dark_video.mp4
noisy_audio.mp4
horizontal_to_vertical.mp4
```

El sistema debe poder testearse sin usar videos gigantes.

---

# 75. Performance

## Principios

- evitar recodificación innecesaria;
- usar proxies;
- analizar a resolución reducida;
- cachear resultados;
- paralelizar tareas;
- liberar memoria entre jobs.

---

# 76. Sistema de proxies

Ejemplo:

```text
RAW 4K
 ↓
Proxy 720p
 ↓
AI analysis
 ↓
Timeline
 ↓
Final conform
 ↓
RAW 4K
```

Nunca exportar la versión final desde el proxy.

---

# 77. Preview Engine

La previsualización debe ser más rápida que el render final.

Utilizar:

```text
proxy
lower resolution
simplified effects
```

Luego:

```text
final render
```

con:

```text
original source
full quality
full effects
```

---

# 78. Streaming de procesamiento

Evitar cargar todo el video en RAM.

Procesar por:

```text
frames
chunks
segments
```

Esto permite soportar archivos largos.

---

# 79. Gestión de memoria

Cada módulo debe tener un límite razonable.

Ejemplo conceptual:

```text
decode
→ process
→ release
```

Nunca:

```text
load entire 4K video into RAM
```

---

# 80. Métricas internas de observabilidad

Registrar:

```text
analysis time
render time
CPU usage
GPU usage
RAM peak
cache hit rate
LLM calls
model inference time
FFmpeg execution time
```

---

# 81. Dashboard técnico

Dentro de una sección avanzada:

```text
Project duration: 04:32
Analysis: 48 s
Transcription: 23 s
Vision: 17 s
Timeline: 3 s
Preview render: 19 s
Final render: 1m42s
```

---

# 82. Sistema de presets

Permitir:

```text
Save preset
Load preset
Duplicate preset
Edit preset
Export preset
Import preset
```

---

# 83. Preset profesional

Ejemplo:

```yaml
name: "Social Fast"
aspect_ratio: "9:16"

editing:
  silence_cut: medium
  jump_cuts: high
  zooms: medium

subtitles:
  enabled: true
  style: bold

audio:
  voice_enhancement: true
  music_ducking: true

color:
  preset: clean
```

---

# 84. Pipeline final completo

```text
┌───────────────┐
│ INPUT VIDEO   │
└───────┬───────┘
        ↓
┌───────────────┐
│ MEDIA INGEST  │
└───────┬───────┘
        ↓
┌───────────────┐
│ PROXY         │
└───────┬───────┘
        ↓
 ┌──────┼────────┬──────────┐
 ↓      ↓        ↓          ↓
Audio  Speech  Vision     Scenes
 ↓      ↓        ↓          ↓
 └──────┴────────┴──────────┘
                 ↓
       ┌──────────────────┐
       │ SEMANTIC ENGINE  │
       └────────┬─────────┘
                ↓
       ┌──────────────────┐
       │ EDITORIAL ENGINE │
       └────────┬─────────┘
                ↓
       ┌──────────────────┐
       │ TIMELINE BUILDER │
       └────────┬─────────┘
                ↓
       ┌──────────────────┐
       │ PREVIEW RENDER   │
       └────────┬─────────┘
                ↓
       ┌──────────────────┐
       │ QUALITY CONTROL  │
       └────────┬─────────┘
                ↓
       ┌──────────────────┐
       │ FINAL CONFORM    │
       └────────┬─────────┘
                ↓
       ┌──────────────────┐
       │ FINAL RENDER     │
       └──────────────────┘
```

---

# 85. Desarrollo utilizando Google Antigravity

Google Antigravity está orientado a un flujo agent-first, donde agentes pueden trabajar sobre editor, terminal y navegador y producir artefactos verificables. La documentación actual también contempla integraciones con editores como VS Code. Para un proyecto de este tamaño, esto favorece trabajar con agentes especializados en lugar de pedirle a un único agente que genere toda la aplicación de una vez.

**Principio:** Antigravity debe ser el sistema de orquestación del desarrollo, no la arquitectura del producto.

---

# 86. Regla para Antigravity

Nunca pedir:

> “Construye toda la app.”

En cambio:

```text
specification
→ architecture
→ module
→ tests
→ integration
→ verification
```

---

# 87. Roles recomendados para agentes

## Agent 01 — Architect

Responsable de:

- arquitectura;
- contratos;
- carpetas;
- dependencias;
- decisiones técnicas.

## Agent 02 — Video Engine

Responsable de:

- FFmpeg;
- proxies;
- render;
- conform;
- export.

## Agent 03 — Audio

Responsable de:

- loudness;
- cleanup;
- compression;
- ducking.

## Agent 04 — Vision

Responsable de:

- face tracking;
- scene analysis;
- auto-framing.

## Agent 05 — Speech/AI

Responsable de:

- Whisper;
- timestamps;
- análisis semántico;
- scoring.

## Agent 06 — Timeline

Responsable de:

- EDL;
- timeline JSON;
- clip operations.

## Agent 07 — Frontend

Responsable de:

- React;
- Tauri;
- timeline UI;
- preview;
- settings.

## Agent 08 — QA

Responsable de:

- tests;
- regression;
- invalid input;
- edge cases.

## Agent 09 — DevOps/Packaging

Responsable de:

- macOS build;
- dependencies;
- installer;
- reproducible environment.

---

# 88. Regla de comunicación entre agentes

Cada agente debe entregar:

```text
WHAT CHANGED
FILES CHANGED
TESTS
KNOWN ISSUES
NEXT RECOMMENDATION
```

No aceptar:

```text
“done”
```

sin evidencia.

---

# 89. Artefactos de verificación

Los agentes deben producir evidencia como:

```text
implementation plan
test results
screenshots
render sample
logs
benchmark
```

Esto encaja con el enfoque de Antigravity de utilizar artefactos verificables en lugar de depender únicamente del historial de llamadas.

---

# 90. Sprint 0 — Foundation

Objetivos:

- repositorio;
- estructura;
- configuración;
- logging;
- tests;
- schemas.

Entregables:

```text
project/
app/
desktop/
tests/
config/
docs/
```

---

# 91. Sprint 1 — Media Ingest

Implementar:

- import;
- media probing;
- metadata;
- validation;
- proxy generation;
- audio extraction.

Definition of Done:

```text
MP4 4K
→ metadata
→ proxy
→ wav
```

---

# 92. Sprint 2 — Speech

Implementar:

- Whisper;
- timestamps;
- language detection;
- transcript JSON;
- subtitle timing.

Definition of Done:

```text
audio
→ transcript.json
```

---

# 93. Sprint 3 — Scene + Silence

Implementar:

- scene detection;
- silence analysis;
- filler detection;
- speech rate.

Definition of Done:

```text
analysis
→ scenes.json
→ silence.json
→ speech.json
```

---

# 94. Sprint 4 — Editorial Engine

Implementar:

- hook score;
- redundancy;
- importance;
- pacing;
- retention proxy score;
- cut proposals.

Output:

```text
edit_plan.json
```

---

# 95. Sprint 5 — Vision

Implementar:

- face detection;
- tracking;
- smart crop;
- vertical composition;
- smoothing.

Output:

```text
faces.json
reframe.json
```

---

# 96. Sprint 6 — Audio Engine

Implementar:

- cleanup;
- EQ;
- compression;
- de-esser;
- loudness;
- limiter;
- ducking.

---

# 97. Sprint 7 — Subtitle Engine

Implementar:

- styles;
- word-level timing;
- highlight;
- kinetic effects;
- safe areas.

---

# 98. Sprint 8 — Timeline

Integrar:

```text
cuts
audio
crop
subtitles
B-roll
SFX
music
color
```

---

# 99. Sprint 9 — Render Engine

Implementar:

- preview render;
- final render;
- hardware acceleration detection;
- export presets;
- progress.

---

# 100. Sprint 10 — Desktop UI

Implementar:

- project manager;
- media bin;
- timeline;
- preview;
- inspector;
- progress;
- settings.

---

# 101. Sprint 11 — QA

Pruebas:

```text
empty file
corrupted video
unsupported codec
variable FPS
no audio
multiple audio tracks
very long video
multiple faces
no face
dark footage
high noise
portrait source
square source
```

---

# 102. Sprint 12 — Packaging

Crear:

```text
macOS application
installer
versioning
config migration
crash reporting local
logs export
```

---

# 103. Prompt maestro para el Agente Arquitecto

```text
You are the lead software architect for IA Video Editor Pro.

Do not build the entire project at once.

First inspect the repository and produce:
1. architecture;
2. module boundaries;
3. dependency graph;
4. data contracts;
5. test strategy;
6. development sequence.

The application is a local-first professional AI video editor.

Core requirements:
- FFmpeg-based video engine;
- Python core;
- React + TypeScript + Tauri desktop UI;
- local speech-to-text;
- computer vision;
- structured editorial decisions;
- non-destructive editing;
- proxy workflow;
- preview render;
- final conform with original media;
- quality-control stage;
- configurable presets;
- no database required for the MVP.

Never allow the LLM to execute arbitrary shell commands.
Use typed JSON schemas between AI and the renderer.

Before implementing code, document assumptions and interfaces.
```

---

# 104. Prompt para Video Engine Agent

```text
Build only the media ingestion and rendering subsystem.

Requirements:
- FFmpeg;
- media metadata inspection;
- proxy generation;
- audio extraction;
- preview rendering;
- final rendering;
- export presets;
- progress tracking;
- cancellation;
- error handling.

Do not implement AI.
Do not implement UI.
Do not modify source media.

Create:
- typed Python APIs;
- unit tests;
- integration tests using small fixture videos.

Every FFmpeg command must be safely constructed and logged.
```

---

# 105. Prompt para AI Agent

```text
Build the speech and semantic analysis layer.

Requirements:
- local speech-to-text;
- word-level timestamps;
- transcript JSON;
- silence segmentation;
- filler detection;
- speech rate;
- hook scoring;
- redundancy scoring.

The LLM must never control FFmpeg directly.

Instead output validated structured decisions.

Create schemas, validation, tests, fixtures and example outputs.
```

---

# 106. Prompt para Vision Agent

```text
Build the video vision subsystem.

Requirements:
- face detection;
- tracking;
- subject priority;
- frame-safe crop;
- 16:9 to 9:16 reframing;
- smoothing;
- multi-person fallback.

Return coordinate/time-series data.
Do not render the final video in this module.

Create visualization/debug output to verify tracking quality.
```

---

# 107. Prompt para QA Agent

```text
Act as a hostile QA engineer.

Test:
- missing files;
- corrupted media;
- unsupported formats;
- unusual frame rates;
- no audio;
- multiple people;
- no detectable face;
- long pauses;
- speech overlaps;
- subtitle overflow;
- extreme crop movement;
- FFmpeg errors;
- interrupted renders.

Do not change architecture simply to make tests pass.

Report:
- severity;
- reproduction;
- expected;
- actual;
- proposed fix.
```

---

# 108. Reglas de desarrollo

## Regla 1

Nunca mezclar:

```text
analysis
render
UI
```

en un único archivo gigantesco.

## Regla 2

Nunca hardcodear configuraciones editoriales.

## Regla 3

Toda funcionalidad crítica debe tener test.

## Regla 4

Toda decisión de IA debe ser validada.

## Regla 5

Nunca eliminar automáticamente el RAW.

## Regla 6

Todo render debe poder cancelarse.

## Regla 7

Todos los paths deben validarse.

---

# 109. MVP realista

El MVP no debe intentar tener:

- multicámara;
- B-roll online;
- marketplace;
- colaboración;
- cloud rendering;
- edición avanzada manual;
- entrenamiento de modelos propios.

El MVP debe resolver perfectamente:

```text
input
→ transcription
→ silence/cut analysis
→ vertical crop
→ subtitles
→ audio cleanup
→ preview
→ final export
```

---

# 110. V1 profesional

Después del MVP:

```text
B-roll local
SFX
music
ducking
color presets
multiple export profiles
timeline editor
undo/redo
quality score
batch export
```

---

# 111. V2 avanzada

Añadir:

```text
multi-camera
speaker detection
automatic story structure
advanced B-roll
semantic asset library
brand kits
auto title generation
thumbnail generation
chapter generation
batch processing
```

---

# 112. V3 empresarial

Añadir:

```text
team workspaces
role-based permissions
cloud storage
central asset management
brand compliance
render farms
organization presets
audit logs
API
```

---

# 113. Monetización futura

Aunque la primera versión sea gratuita, la arquitectura debe permitir:

```text
Free
Creator
Pro
Business
Enterprise
```

Pero el núcleo local no debe romperse por una suscripción.

---

# 114. Costos y estrategia “gratis”

## Núcleo

Priorizar componentes open source/locales:

```text
Python
FFmpeg
OpenCV
MediaPipe
Whisper / faster-whisper
Tauri
React
TypeScript
SQLite opcional para futuro
Git
```

## IA

Preferir:

```text
local inference
```

antes que pagar por cada minuto de video.

## APIs externas

Tratar:

```text
B-roll online
cloud LLM
cloud storage
```

como módulos opcionales.

---

# 115. Limitación importante sobre el “gratis”

“Gratis” no significa que el sistema pueda ejecutar modelos grandes o renders pesados sin costo computacional.

Los costos que permanecen son:

- energía;
- almacenamiento;
- tiempo de render;
- memoria;
- espacio en disco;
- eventuales cuotas de proveedores.

Por eso la arquitectura debe minimizar dependencias externas.

---

# 116. Recomendación específica para tu Mac

La aplicación debería tener dos perfiles:

```text
QUALITY
PERFORMANCE
```

## QUALITY

- mayor modelo;
- más análisis;
- tracking más preciso;
- render de mayor calidad.

## PERFORMANCE

- menor proxy;
- análisis reducido;
- modelo más pequeño;
- menor latencia.

---

# 117. Detección automática del entorno

Al iniciar:

```text
OS
CPU
GPU
RAM
available disk
FFmpeg version
hardware acceleration
Python version
model availability
```

Luego construir:

```json
{
  "profile": "apple_silicon",
  "hardware_acceleration": true
}
```

---

# 118. Compatibilidad futura

Aunque inicialmente se optimice para macOS Apple Silicon, evitar APIs exclusivamente dependientes de Apple en el núcleo.

Separar:

```text
platform-neutral core
+
platform adapters
```

Así se podrá incorporar:

```text
Windows
Linux
```

más adelante.

---

# 119. Recomendación de arquitectura de plugins

Diseñar interfaces para:

```text
Analyzer
AudioProcessor
VideoProcessor
AIProvider
RenderBackend
SubtitleRenderer
AssetProvider
```

Esto permite agregar capacidades sin modificar todo el sistema.

---

# 120. Ejemplo de plugin

```python
class Analyzer:
    name = "scene_detector"

    def analyze(self, media_path):
        ...
```

---

# 121. Roadmap resumido

```text
PHASE 0
Architecture

PHASE 1
Media engine

PHASE 2
Speech

PHASE 3
Analysis

PHASE 4
Editorial AI

PHASE 5
Vision

PHASE 6
Audio

PHASE 7
Subtitles

PHASE 8
Timeline

PHASE 9
Rendering

PHASE 10
Desktop UI

PHASE 11
QA

PHASE 12
Packaging
```

---

# 122. Criterios de éxito del MVP

El MVP será considerado funcional cuando pueda:

```text
[✓] importar video
[✓] generar proxy
[✓] transcribir
[✓] detectar silencios
[✓] sugerir cortes
[✓] detectar rostro
[✓] generar crop 9:16
[✓] generar subtítulos
[✓] procesar audio
[✓] construir timeline
[✓] renderizar preview
[✓] renderizar final
[✓] preservar RAW
[✓] recuperarse de errores básicos
```

---

# 123. Criterios de calidad

El software debe priorizar:

```text
1. Correctness
2. Stability
3. Predictability
4. Quality
5. Performance
6. Automation
7. Aesthetics
```

Nunca invertir el orden y sacrificar estabilidad por “efectos llamativos”.

---

# 124. Principio editorial final

El software no debe intentar hacer el video:

> “más editado”.

Debe intentar hacerlo:

> **más claro, más dinámico, más profesional y más adecuado para su objetivo.**

Un video con 300 efectos no necesariamente es mejor.

La inteligencia del producto estará en saber **cuándo no hacer nada**.

---

# 125. Resultado final esperado

Entrada:

```text
camera_raw.mp4
```

Salida:

```text
project/
├── analysis/
├── timeline/
├── preview/
└── export/
    ├── final_9x16.mp4
    ├── final_16x9.mp4
    └── final_1x1.mp4
```

El resultado debe ser:

- visualmente coherente;
- correctamente encuadrado;
- con audio limpio;
- subtítulos sincronizados;
- ritmo razonable;
- sin pérdida del archivo original;
- reproducible;
- configurable;
- explicable;
- exportable en distintos formatos.

---

# 126. Decisión técnica recomendada

Para la primera implementación:

```text
FRONTEND
React + TypeScript + Tauri

CORE
Python

VIDEO
FFmpeg

AUDIO
FFmpeg + pyloudnorm + pedalboard

SPEECH
faster-whisper

VISION
OpenCV + MediaPipe

SEMANTIC AI
Local LLM abstraction
+ optional Gemini provider

DATA
JSON + project folders

TESTING
pytest

VERSION CONTROL
Git

BUILD
Tauri + Python packaged runtime
```

---

# 127. Advertencia sobre alcance

Este proyecto es significativamente más grande que un script de automatización.

Un editor con:

- timeline;
- preview;
- IA;
- tracking;
- subtítulos;
- audio;
- render;
- gestión de proyectos;
- UX;
- recuperación de errores

se acerca más a un producto de software audiovisual completo.

Por eso el mejor camino es construir primero un **motor headless profesional** y posteriormente envolverlo en una interfaz gráfica.

---

# 128. Estrategia final de implementación

## Etapa A

Construir:

```text
CLI
```

Ejemplo:

```bash
video-editor analyze input.mp4
video-editor auto-edit input.mp4
video-editor preview project/
video-editor render project/
```

## Etapa B

Construir GUI.

## Etapa C

Agregar IA avanzada.

## Etapa D

Agregar automatización empresarial.

---

# 129. CLI propuesta

```bash
iva analyze video.mp4
iva edit video.mp4 --profile social
iva preview project.json
iva render project.json
iva inspect project.json
```

Esto permite desarrollar y depurar mucho más rápido que comenzar inmediatamente con una GUI.

---

# 130. Arquitectura definitiva

```text
                 USER
                   │
                   ▼
             DESKTOP UI
          React + Tauri
                   │
                   ▼
             PROJECT API
                   │
                   ▼
             PYTHON CORE
                   │
      ┌────────────┼────────────┐
      ▼            ▼            ▼
 ANALYSIS       EDITORIAL     TIMELINE
 ENGINE         ENGINE        ENGINE
      │            │            │
      ├──────┬─────┘            │
      ▼      ▼                  ▼
   AUDIO   VISION          RENDER PLAN
      │      │                  │
      └──────┴──────────────────┘
                   │
                   ▼
                 FFMPEG
                   │
                   ▼
               QA ENGINE
                   │
             ┌─────┴─────┐
             ▼           ▼
           PASS        WARN/FAIL
             │
             ▼
         FINAL EXPORT
```

---

# 131. Fuentes técnicas y notas de actualidad

- Google describe Antigravity como una plataforma de desarrollo agent-first capaz de coordinar agentes sobre editor, terminal y navegador y producir artefactos verificables. La plataforma fue presentada en preview público y sus herramientas/planes han evolucionado durante 2026.
- La documentación actual de FFmpeg mantiene soporte para `videotoolbox` como mecanismo de aceleración de hardware en plataformas Apple.
- Whisper continúa disponible como proyecto de código abierto con licencia MIT; su enfoque general cubre reconocimiento multilingüe, identificación de idioma y otras tareas de audio.

---

# 132. Conclusión

La idea correcta no es:

```text
“Una IA que edita videos”
```

La idea correcta es:

```text
“Un sistema editorial audiovisual automatizado que
analiza material, propone una edición, construye un
timeline no destructivo, ejecuta el montaje, verifica
el resultado y entrega múltiples versiones finales.”
```

Ese cambio conceptual convierte el proyecto de un simple script de IA en una arquitectura de producto mucho más sólida.

---

# 133. Orden exacto recomendado para comenzar

```text
1. Crear repositorio
2. Crear arquitectura
3. Construir CLI
4. Integrar FFmpeg
5. Crear media analyzer
6. Crear proxy engine
7. Integrar transcripción
8. Crear analysis JSON
9. Crear editorial engine
10. Crear EDL
11. Crear vision engine
12. Crear subtitle engine
13. Crear audio engine
14. Crear render engine
15. Crear quality control
16. Crear preview
17. Crear GUI
18. Crear packaging
19. Benchmark
20. Beta
```

**No empezar por la interfaz.**

El producto debe tener primero un motor de edición confiable.

