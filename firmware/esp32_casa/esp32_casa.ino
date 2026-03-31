/**
 * ESP32: un solo módulo controla 3 luces (3 relés/GPIO) vía 3 topics MQTT.
 * Topics: {TOPIC_PREFIX}/living, {TOPIC_PREFIX}/comedor, {TOPIC_PREFIX}/patio
 * Payload en cada uno: on | off | toggle
 *
 * Biblioteca: PubSubClient — gestor de bibliotecas de Arduino.
 * En el servidor: MQTT_HOME_ZONES=living,comedor,patio (mismos nombres).
 */

#include <WiFi.h>
#include <PubSubClient.h>

// ---------- WiFi ----------
static const char *WIFI_SSID = "TU_WIFI";
static const char *WIFI_PASSWORD = "TU_CLAVE";

// ---------- Broker (IP de la Raspberry con Mosquitto) ----------
static const char *MQTT_HOST = "192.168.60.216";
static const uint16_t MQTT_PORT = 1883;
static const char *MQTT_USER = nullptr;
static const char *MQTT_PASS = nullptr;

static const char *TOPIC_PREFIX = "casa";

/** Zonas = último segmento del topic. Deben coincidir con MQTT_HOME_ZONES. */
static const char *ZONAS_SLUG[] = {"living", "comedor", "patio"};
static const int NUM_ZONAS = 3;

/** Un GPIO por luz (rele activo HIGH o LOW según tu módulo; ajustá lógica si hace falta). */
static const int PIN_LUZ[] = {2, 4, 5};
static bool estadoLuz[NUM_ZONAS] = {false, false, false};

WiFiClient wifiClient;
PubSubClient mqtt(wifiClient);

static String topicParaZona(int i) {
  return String(TOPIC_PREFIX) + "/" + String(ZONAS_SLUG[i]);
}

static int indiceZonaPorTopic(const char *topic) {
  String t(topic);
  int slash = t.lastIndexOf('/');
  if (slash < 0) {
    return -1;
  }
  String zona = t.substring(slash + 1);
  zona.toLowerCase();
  for (int i = 0; i < NUM_ZONAS; i++) {
    if (zona == String(ZONAS_SLUG[i])) {
      return i;
    }
  }
  return -1;
}

static void aplicarOnOff(int idx, bool on) {
  if (idx < 0 || idx >= NUM_ZONAS) {
    return;
  }
  estadoLuz[idx] = on;
  digitalWrite(PIN_LUZ[idx], on ? HIGH : LOW);
}

static void aplicarToggle(int idx) {
  if (idx < 0 || idx >= NUM_ZONAS) {
    return;
  }
  aplicarOnOff(idx, !estadoLuz[idx]);
}

void callback(char *topic, byte *payload, unsigned int length) {
  char buf[32];
  if (length >= sizeof(buf)) {
    length = sizeof(buf) - 1;
  }
  memcpy(buf, payload, length);
  buf[length] = '\0';

  int idx = indiceZonaPorTopic(topic);
  if (idx < 0) {
    return;
  }

  String p = String(buf);
  p.trim();
  p.toLowerCase();

  if (p == "on" || p == "1" || p == "encender" || p == "enciende") {
    aplicarOnOff(idx, true);
  } else if (p == "off" || p == "0" || p == "apagar" || p == "apaga") {
    aplicarOnOff(idx, false);
  } else if (p == "toggle" || p == "pulse" || p.length() == 0) {
    aplicarToggle(idx);
  }
}

void reconnectMqtt() {
  String clientId =
      String("esp32-tres-luces-") + String(random(0xffff), HEX);
  while (!mqtt.connected()) {
    if (MQTT_USER != nullptr && strlen(MQTT_USER) > 0) {
      const char *pw = (MQTT_PASS != nullptr) ? MQTT_PASS : "";
      mqtt.connect(clientId.c_str(), MQTT_USER, pw);
    } else {
      mqtt.connect(clientId.c_str());
    }
    if (mqtt.connected()) {
      for (int i = 0; i < NUM_ZONAS; i++) {
        String sub = topicParaZona(i);
        mqtt.subscribe(sub.c_str());
      }
      break;
    }
    delay(2000);
  }
}

void setupWifi() {
  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
  }
}

void setup() {
  for (int i = 0; i < NUM_ZONAS; i++) {
    pinMode(PIN_LUZ[i], OUTPUT);
    aplicarOnOff(i, false);
  }

  randomSeed(esp_random());
  setupWifi();

  mqtt.setServer(MQTT_HOST, MQTT_PORT);
  mqtt.setCallback(callback);
  reconnectMqtt();
}

void loop() {
  if (WiFi.status() != WL_CONNECTED) {
    setupWifi();
  }
  if (!mqtt.connected()) {
    reconnectMqtt();
  }
  mqtt.loop();
}
