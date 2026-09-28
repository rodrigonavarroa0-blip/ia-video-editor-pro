# 🔐 Guía Oficial de Firma y Notarización para macOS (Apple Gatekeeper)

Este documento detalla el procedimiento oficial de firma digital (*Code Signing*) y notarización ante los servidores de Apple para distribuir **IA Video Editor Pro** como aplicación de confianza en macOS (Apple Silicon e Intel).

---

## 1. Requisitos Previos

1. **Cuenta de Desarrollador de Apple (Apple Developer Program)** activa.
2. **Certificado Developer ID Application** instalado en el llavero local de macOS (*Keychain*).
3. **Contraseña específica de aplicación** generada en [appleid.apple.com](https://appleid.apple.com).
4. Guardar las credenciales en `notarytool` con un perfil reutilizable:
   ```bash
   xcrun notarytool store-credentials "AC_NOTARY" \
       --apple-id "tu_email@developer.com" \
       --team-id "TU_TEAM_ID" \
       --password "abcd-efgh-ijkl-mnop"
   ```

---

## 2. Archivo de Permisos (Entitlements)

Crear el archivo `entitlements.plist` para conceder acceso al micrófono, cámara y hardware de codificación VideoToolbox:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>com.apple.security.cs.allow-jit</key>
    <true/>
    <key>com.apple.security.cs.allow-unsigned-executable-memory</key>
    <true/>
    <key>com.apple.security.cs.disable-library-validation</key>
    <true/>
    <key>com.apple.security.device.audio-input</key>
    <true/>
    <key>com.apple.security.device.camera</key>
    <true/>
</dict>
</plist>
```

---

## 3. Procedimiento de Firma del Bundle `.app`

Firmar todos los binarios internos (FFmpeg, bibliotecas dinámicas) y el ejecutable principal:

```bash
# 1. Firmar binarios embebidos
codesign --force --options runtime --deep --sign "Developer ID Application: Tu Nombre/Empresa (TU_TEAM_ID)" \
    "IA Video Editor Pro.app/Contents/Resources/bin/ffmpeg"

# 2. Firmar el bundle completo
codesign --force --options runtime --deep \
    --entitlements entitlements.plist \
    --sign "Developer ID Application: Tu Nombre/Empresa (TU_TEAM_ID)" \
    "IA Video Editor Pro.app"

# 3. Verificar la firma del .app
codesign --verify --deep --strict --verbose=2 "IA Video Editor Pro.app"
```

---

## 4. Creación y Firma del Instalador `.dmg`

```bash
# 1. Crear el instalador DMG usando la CLI
iva package --output-dir ./release

# 2. Firmar la imagen de disco
codesign --force --sign "Developer ID Application: Tu Nombre/Empresa (TU_TEAM_ID)" \
    "./release/IA Video Editor Pro.dmg"
```

---

## 5. Notarización y Grapado (Stapling)

```bash
# 1. Enviar el DMG al servicio de notarización de Apple
xcrun notarytool submit "./release/IA Video Editor Pro.dmg" \
    --keychain-profile "AC_NOTARY" \
    --wait

# 2. Grapar el ticket de notarización en el DMG
xcrun stapler staple "./release/IA Video Editor Pro.dmg"

# 3. Validar con Gatekeeper
spctl -a -t open --context context:primary-signature -v "./release/IA Video Editor Pro.dmg"
```

Resultado esperado:
```text
./release/IA Video Editor Pro.dmg: accepted
source=Notarized Developer ID
```
