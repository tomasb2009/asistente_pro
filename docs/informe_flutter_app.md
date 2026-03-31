# Informe: aplicación Flutter (escritorio) para el asistente personal

Este documento describe **cómo diseñar e implementar** una app Flutter orientada a **escritorio** (Windows, Linux) que se conecta al backend FastAPI existente, incorpora **wake word**, **voz (entrada y salida)**, una **vista de conversación** con visualización de audio, y un **dashboard** minimalista como pantalla principal. La estética objetivo es **minimalista y futurista**, con **paleta en azules**.

---

## 1. Objetivo y alcance

| Objetivo | Detalle |
|----------|---------|
| **Backend único para lenguaje natural** | Todas las peticiones de “hablar con el asistente” deben ir al **mismo endpoint HTTP** que ya existe: no inventar rutas nuevas para el mismo propósito. |
| **Wake word** | Activar el modo escucha cuando el usuario diga una palabra clave (p. ej. “Asistente”), sin mantener pulsado un botón de forma obligatoria. |
| **Voz → texto → backend → texto → voz** | Micrófono → reconocimiento de voz (STT) → `message` en la query → respuesta `reply` → síntesis de voz (TTS). |
| **UI conversacional** | Barras que reaccionen al nivel de voz mientras hablas; zona clara para el **texto de respuesta**; **TTS** automático al recibir respuesta. |
| **Dashboard principal** | Página inicial con **hora**, **temperatura actual**, **estado del cielo**, **estado de luces por zona** (vivible y ampliable), más **acciones rápidas** (encender/apagar). |
| **Escritorio + minimalismo** | Ventanas anchas, `NavigationRail` o layout en columnas, pocos adornos, tipografía legible, **tema azul futurista**. |

**Nota sobre “endpoint raíz”:** En el backend actual, la entrada del asistente **no** es `GET /`, sino:

```http
GET /api/v1/query?message=<texto codificado en URL>
```

Respuesta JSON:

```json
{
  "intent": "weather",
  "reply": "Texto largo de respuesta en español..."
}
```

“Usar siempre el mismo endpoint” en la práctica significa: **una sola URL base configurable** (p. ej. `http://IP:8000`) y **un solo path de consulta** (`/api/v1/query`) para todo lo que sea “pregunta al asistente”. Los botones del dashboard pueden enviar **mensajes fijos** (“enciende la luz del patio”, “apaga todas las luces”) por el **mismo** `GET`, para no duplicar lógica en el cliente.

---

## 2. Contrato HTTP que debes respetar

- **Método:** `GET`
- **Path:** `/api/v1/query`
- **Query obligatorio:** `message` (string, mínimo 1 carácter)
- **Ejemplo:** `http://192.168.5.10:8000/api/v1/query?message=Qu%C3%A9%20hora%20es`

**Codificación:** Usar `Uri.encodeQueryComponent` (o equivalente en Dio) para tildes y espacios.

**CORS:** Si algún día sirves la app como web, el backend debe permitir el origen de la app. Para **app de escritorio** Flutter, las peticiones suelen ir “directas” al host; en muchos casos no hay CORS, pero si usas un proxy o web, configura CORS en FastAPI.

**Errores:** Manejar `4xx/5xx`, timeouts y cuerpo vacío; mostrar mensaje amable en la UI.

**Sesión:** El backend usa **una sesión interna fija**; el cliente **no** envía `session_id`. No hace falta cabecera extra para conversación.

---

## 3. Limitaciones importantes (para no frustrarte)

### 3.1 Estado real de las luces (MQTT)

Hoy el backend **publica órdenes MQTT** pero **no expone** un API de lectura del estado de cada luz (encendida/apagada). Opciones:

1. **UI optimista:** al pulsar “Apagar patio”, marcas el estado como apagado y envías el `GET` con el mensaje correspondiente; si falla la red, reviertes o muestras error.
2. **Futuro:** añadir en FastAPI algo como `GET /api/v1/home/state` alimentado por MQTT retained messages, Redis, o el propio ESP32 reportando estado (fuera del alcance de este informe, pero conviene reservar la interfaz en Flutter como `Stream`/`Future` sustituible).

El informe asume **estado local en la app** + sincronización por comandos, hasta que exista API de lectura.

### 3.2 Wake word en escritorio

El **wake word** continuo en segundo plano en **Windows/Linux/macOS** con Flutter no es trivial:

- **Picovoice Porcupine** tiene SDKs y puede integrarse vía plugins de la comunidad o FFI; requiere modelo `.ppn` y claves de licencia según uso.
- **Alternativa pragmática:** atajo de teclado global o botón grande “Escuchar” + detección de silencio para cortar frase.
- **Plan recomendado:** Fase 1 = **push-to-talk** o **doble clic**; Fase 2 = integrar Porcupine (o similar) cuando la app base funcione.

Documenta en la app que el wake word es “mejora opcional” si la integración nativa se complica en tu plataforma objetivo.

### 3.3 Clima y hora en el dashboard

El backend **ya responde** por el mismo `GET` con frases naturales. Para **widgets numéricos** (temperatura, icono de cielo):

- Opción A: Enviar mensajes fijos (`message=¿Qué temperatura hace en Córdoba?`) y **parsear** el texto de `reply` (frágil).
- Opción B (mejor a medio plazo): añadir endpoints JSON dedicados en FastAPI (`/api/v1/dashboard/weather`) que devuelvan `{temp, code, description}` — **no** sustituyen al endpoint de conversación; solo alimentan el dashboard.

Este informe detalla la UI asumiendo que **inicialmente** puedes mostrar un **resumen de texto** o parseo mínimo, y luego sustituir por API estructurada.

---

## 4. Arquitectura Flutter recomendada

```
lib/
  main.dart
  app.dart                 # MaterialApp + tema
  core/
    config.dart            # Base URL, timeouts (env / dart-define)
    theme/
      app_theme.dart       # ColorScheme futurista azul
  data/
    api/
      assistant_api.dart   # Solo GET /api/v1/query
    models/
      query_response.dart  # intent + reply (json_serializable)
  features/
    dashboard/
      dashboard_page.dart
      widgets/
        clock_card.dart
        weather_card.dart
        light_grid.dart    # Lista de zonas desde config
    voice/
      voice_page.dart
      widgets/
        waveform_bars.dart
        transcript_area.dart
  services/
    speech_service.dart    # STT (speech_to_text)
    tts_service.dart       # flutter_tts
    wake_word_service.dart # Interfaz + implementación stub / Porcupine
    audio_level_service.dart # Nivel para barras (opcional: record package)
```

**Estado:** `Riverpod` o `Bloc` — para separar “servicio de voz”, “última respuesta”, “estado de luces local”, “carga de red”.

---

## 5. Dependencias (`pubspec.yaml`) orientativas

| Paquete | Uso |
|---------|-----|
| `dio` o `http` | Cliente HTTP con timeouts y query params |
| `speech_to_text` | STT en desktop (soporte variable; probar en tu SO) |
| `flutter_tts` | TTS para leer `reply` |
| `json_annotation` + `json_serializable` | Modelo `QueryResponse` |
| `flutter_riverpod` (opcional) | Estado |
| `window_manager` (opcional) | Tamaño mínimo, título ventana, siempre encima |
| `record` / `mic_stream` (opcional) | Nivel de audio real para barras; si no, animación “fake” sincronizada con `speech_to_text` |

**Wake word comercial/libre:** investigar `porcupine_flutter` o bindings FFI según licencia.

---

## 6. Servicio de API (único endpoint de conversación)

Pseudo-contrato Dart:

```dart
class AssistantApi {
  AssistantApi({required String baseUrl}) : _base = baseUrl.replaceAll(RegExp(r'/$'), '');

  final String _base;

  Future<QueryResponse> query(String message) async {
    final uri = Uri.parse('$_base/api/v1/query').replace(
      queryParameters: {'message': message},
    );
    // GET con timeout 60–120 s (LLM puede tardar)
    // throw si status != 200
  }
}
```

**Configuración:** `baseUrl` por defecto `http://127.0.0.1:8000`, editable en pantalla de ajustes o `--dart-define=API_BASE=http://192.168.60.216:8000`.

---

## 7. Flujo de voz (página “Hablar”)

1. Usuario activa escucha (wake word o botón).
2. **STT** escucha hasta pausa o botón “Enviar”.
3. Texto reconocido se muestra en un área de “lo que entendí”.
4. Llamada `query(texto)`.
5. Mostrar `reply` en el panel de respuesta.
6. **TTS** `speak(reply)`; botón “Repetir” / “Silenciar”.

**Barras animadas:**

- Si tienes nivel de micrófono: mapear amplitud a altura de 5–12 barras (clamp + suavizado).
- Si no: animación tipo `AnimationController` con loop mientras `listening == true`.

---

## 8. Dashboard (página principal)

**Layout sugerido (escritorio):**

- **Columna izquierda o cabecera:** reloj grande (hora local del sistema o la zona que elijas mostrando texto fijo).
- **Tarjeta clima:** temperatura + descripción del cielo — datos obtenidos enviando una query predefinida al **mismo** endpoint y mostrando `reply` o un parseo futuro.
- **Cuadrícula de luces:** una tarjeta por zona (`living`, `comedor`, `patio`, …) leídas de una **lista configurable** en Dart o JSON local que coincida con `MQTT_HOME_ZONES`.
  - Cada tarjeta: nombre, **indicador** ON/OFF (color o icono), botones **Encender** / **Apagar** que llaman a `query("enciende la luz del patio")` etc.
- **Fila inferior:** botón “Todas ON” / “Todas OFF” → `query` con los mensajes que ya definiste en el backend para “todas las luces”.

**Minimalismo:** mucho espacio en blanco, bordes redondeados suaves, sombras muy leves, sin gradientes recargados; acentos en **cian / azul eléctrico / azul noche**.

---

## 9. Tema visual (futurista, azules)

Directrices:

- **Fondo:** `#0B1020` – `#121A2F` (oscuro).
- **Superficies:** `#162036`, bordes `#2A3F6B` con opacidad baja.
- **Primario:** `#3D7CFF` o `#5B8DEF`; **acento:** `#00D4FF`.
- **Texto:** `#E8EEF8` principal, `#8FA4C7` secundario.
- **Tipografía:** una sola familia (p. ej. **Inter**, **IBM Plex Sans** o **JetBrains Mono** solo para números/reloj).
- **Material 3:** `ColorScheme.dark` con `seedColor` azul; `useMaterial3: true`.

Evitar: violetas genéricos “IA”, demasiados neones simultáneos.

---

## 10. Seguridad y red

- En casa, HTTP en LAN es común; si expones fuera de casa, **HTTPS** + túnel o reverse proxy.
- No incrustar claves OpenAI en la app Flutter; solo habla con **tu** backend.
- Validar certificados si pasas a HTTPS.

---

## 11. Orden de implementación sugerido

1. Proyecto Flutter **desktop** + tema + pantalla vacía con `NavigationRail` (Dashboard | Voz | Ajustes).
2. Servicio `AssistantApi` + pantalla de prueba que envía un `TextField` y muestra JSON/`reply`.
3. Dashboard con **hora** (`DateTime.now`) y tarjetas **placeholder** para clima y luces.
4. Botones de luces que llaman al API con strings fijos; estado local ON/OFF.
5. Integrar **TTS** para leer respuestas en la vista de voz.
6. Integrar **STT** y flujo completo conversación.
7. Barras de audio (real o animadas).
8. Wake word o atajo global como mejora final.

---

## 12. Checklist de calidad

- [ ] Un solo método de red para “preguntar al asistente” (`/api/v1/query`).
- [ ] `message` siempre codificado correctamente en la URL.
- [ ] Timeout largo en peticiones al LLM.
- [ ] Manejo de error de red y de servidor.
- [ ] TTS cancelable al salir de la pantalla.
- [ ] Dashboard usable sin voz (solo botones).
- [ ] Tema coherente y legible en monitor grande.

---

## 13. Referencia rápida del backend

| Elemento | Valor |
|----------|--------|
| Health | `GET /health` → `{"status":"ok"}` |
| Consulta | `GET /api/v1/query?message=...` |
| Respuesta | `{ "intent": "<string>", "reply": "<string>" }` |

Intents típicos que verás en `intent`: `weather`, `time`, `general_knowledge`, `home_command` — la UI puede mostrar un chip opcional con la intención para depuración.

---

*Documento generado para alineación con el repositorio `asistente_personal` (FastAPI + pipeline único de sesión). Ajustá nombres de zonas y URL base a tu entorno.*
