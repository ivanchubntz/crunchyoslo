import AsyncStorage from "@react-native-async-storage/async-storage";
import { CameraView, useCameraPermissions } from "expo-camera";
import { useEffect, useRef, useState } from "react";
import {
  ActivityIndicator,
  KeyboardAvoidingView,
  Platform,
  Pressable,
  SafeAreaView,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  View,
} from "react-native";

const STORAGE_KEY = "oslo-reader-connection-v1";
const BARCODE_TYPES = ["ean13", "ean8", "upc_a", "upc_e", "code128", "code39", "itf14"];

export default function App() {
  const [permission, requestPermission] = useCameraPermissions();
  const [connection, setConnection] = useState(null);
  const [baseUrl, setBaseUrl] = useState("");
  const [token, setToken] = useState("");
  const [mode, setMode] = useState("loading");
  const [busy, setBusy] = useState(false);
  const [scanArmed, setScanArmed] = useState(false);
  const [message, setMessage] = useState({ tone: "neutral", title: "Preparando lector", detail: "" });
  const locked = useRef(false);

  useEffect(() => {
    AsyncStorage.getItem(STORAGE_KEY)
      .then((value) => {
        if (!value) {
          setMode("connect");
          return;
        }
        const saved = JSON.parse(value);
        return fetch(`${saved.baseUrl}/api/session?token=${encodeURIComponent(saved.token)}`)
          .then((response) => response.json())
          .then(async (session) => {
            if (!session.valid) {
              await AsyncStorage.removeItem(STORAGE_KEY);
              setMode("connect");
              setMessage({ tone: "warn", title: "Vuelve a vincular la caja", detail: "La sesión anterior terminó." });
              return;
            }
            setConnection(saved);
            setBaseUrl(saved.baseUrl);
            setToken(saved.token);
            setMode("ready");
            setMessage({ tone: "good", title: "Caja vinculada", detail: "Escanea un código para enviarlo al punto de venta." });
          });
      })
      .catch(() => {
        setMode("connect");
        setMessage({ tone: "warn", title: "Vuelve a conectar la caja", detail: "La caja puede estar cerrada o la sesión anterior venció." });
      });
  }, []);

  const normalizeConnection = (value) => {
    if (!value || value.type !== "oslo-reader" || value.version !== 1) {
      throw new Error("Este QR no pertenece al lector Oslo.");
    }
    const parsedUrl = new URL(value.baseUrl);
    if (!["http:", "https:"].includes(parsedUrl.protocol) || !value.token) {
      throw new Error("El QR no contiene una dirección y clave válidas.");
    }
    return { baseUrl: parsedUrl.origin, token: String(value.token) };
  };

  const verifyAndSave = async (candidate) => {
    setBusy(true);
    setMessage({ tone: "neutral", title: "Conectando con la caja…", detail: "Compruebo la red local." });
    try {
      const response = await Promise.race([
        fetch(`${candidate.baseUrl}/health`),
        new Promise((_, reject) => setTimeout(() => reject(new Error("La caja no respondió a tiempo.")), 4500)),
      ]);
      if (!response.ok) throw new Error("La caja respondió con un error.");
      const health = await response.json();
      if (health.service !== "oslo-reader") throw new Error("La dirección no corresponde a la caja Oslo.");
      const sessionResponse = await fetch(`${candidate.baseUrl}/api/session?token=${encodeURIComponent(candidate.token)}`);
      const session = await sessionResponse.json();
      if (!session.valid) throw new Error("La clave temporal no coincide con la sesión actual de la caja.");
      await AsyncStorage.setItem(STORAGE_KEY, JSON.stringify(candidate));
      setConnection(candidate);
      setBaseUrl(candidate.baseUrl);
      setToken(candidate.token);
      setMode("ready");
      setMessage({ tone: "good", title: "Caja vinculada", detail: "Ya puedes escanear productos para el punto de venta." });
    } catch (error) {
      setMessage({ tone: "bad", title: "No se pudo conectar", detail: `${error.message} Verifica que ambos dispositivos estén en la misma red Wi-Fi y que la caja esté abierta.` });
      setMode("connect");
    } finally {
      setBusy(false);
    }
  };

  const handleQr = async ({ data }) => {
    if (mode !== "pairing" || locked.current) return;
    locked.current = true;
    try {
      const candidate = normalizeConnection(JSON.parse(data));
      setMode("connect");
      await verifyAndSave(candidate);
    } catch (error) {
      setMessage({ tone: "bad", title: "No se pudo vincular", detail: error.message || "Escanea el QR que muestra la caja." });
      setTimeout(() => { locked.current = false; }, 1200);
    }
  };

  const handleProductBarcode = async ({ data }) => {
    if (mode !== "scanning" || locked.current || !connection) return;
    const barcode = String(data || "").trim();
    if (!barcode) return;
    locked.current = true;
    setScanArmed(false);
    setMessage({ tone: "neutral", title: "Enviando lectura…", detail: barcode });
    try {
      const response = await fetch(`${connection.baseUrl}/api/scan`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ token: connection.token, barcode }),
      });
      const result = await response.json();
      if (!response.ok) {
        if (result.error === "invalid_session") {
          await AsyncStorage.removeItem(STORAGE_KEY);
          setConnection(null);
          setMode("connect");
          throw new Error("La sesión de la caja venció. Vuelve a vincular el teléfono.");
        }
        throw new Error("La caja rechazó el código leído.");
      }
      if (result.found) {
        const price = Number(result.price).toLocaleString("es-AR", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
        setMessage({ tone: "good", title: result.product, detail: `$${price} · Código enviado al punto de venta` });
      } else {
        setMessage({ tone: "warn", title: "Producto nuevo", detail: `${barcode} · Confirma el alta desde la caja.` });
      }
    } catch (error) {
      setMessage({ tone: "bad", title: "No se envió el código", detail: `${error.message} La caja sigue funcionando; comprueba la conexión y vuelve a escanear.` });
    } finally {
      setTimeout(() => { locked.current = false; }, 1600);
    }
  };

  const connectManually = () => {
    try {
      const candidate = normalizeConnection({
        type: "oslo-reader",
        version: 1,
        baseUrl: baseUrl.trim(),
        token: token.trim(),
      });
      verifyAndSave(candidate);
    } catch (error) {
      setMessage({ tone: "bad", title: "Revisa los datos", detail: error.message });
    }
  };

  const disconnect = async () => {
    await AsyncStorage.removeItem(STORAGE_KEY);
    setConnection(null);
    setMode("connect");
    setMessage({ tone: "neutral", title: "Lector sin vincular", detail: "Escanea el QR de la caja para conectarte." });
  };

  const askForCamera = async (nextMode) => {
    if (!permission?.granted) {
      const result = await requestPermission();
      if (!result.granted) {
        setMessage({ tone: "bad", title: "Falta permiso de cámara", detail: "Activa el permiso de cámara para usar el lector." });
        return;
      }
    }
    locked.current = false;
    setScanArmed(nextMode === "scanning");
    setMode(nextMode);
  };

  if (mode === "loading") {
    return <SafeAreaView style={styles.loading}><ActivityIndicator size="large" color="#38bdf8" /><Text style={styles.loadingText}>Preparando lector…</Text></SafeAreaView>;
  }

  const isCameraMode = mode === "pairing" || mode === "scanning";
  const cameraTypes = mode === "pairing" ? ["qr"] : BARCODE_TYPES;

  return (
    <SafeAreaView style={styles.safe}>
      <KeyboardAvoidingView style={styles.flex} behavior={Platform.OS === "ios" ? "padding" : undefined}>
        <ScrollView contentContainerStyle={styles.page} keyboardShouldPersistTaps="handled">
          <View style={styles.header}>
            <View style={styles.brandIcon}><Text style={styles.brandGlyph}>O</Text></View>
            <View style={styles.headerCopy}>
              <Text style={styles.eyebrow}>OSLO</Text>
              <Text style={styles.title}>Lector móvil</Text>
            </View>
            <View style={[styles.onlineDot, connection ? styles.dotGood : styles.dotOff]} />
          </View>

          <View style={styles.connectionCard}>
            <View style={styles.connectionTop}>
              <View>
                <Text style={styles.cardLabel}>PUNTO DE VENTA</Text>
                <Text style={styles.connectionTitle}>{connection ? "Caja conectada" : "Sin conectar"}</Text>
              </View>
              {connection ? <Pressable onPress={disconnect} style={styles.linkButton}><Text style={styles.linkText}>Cambiar</Text></Pressable> : null}
            </View>
            <Text style={styles.connectionDetail}>{connection ? connection.baseUrl : "Vincula este teléfono con la caja de tu comercio."}</Text>
          </View>

          <View style={[styles.statusCard, statusStyle(message.tone)]}>
            <View style={styles.statusMark}><Text style={styles.statusMarkText}>{statusGlyph(message.tone)}</Text></View>
            <View style={styles.statusCopy}>
              <Text style={styles.statusTitle}>{message.title}</Text>
              {message.detail ? <Text style={styles.statusDetail}>{message.detail}</Text> : null}
            </View>
          </View>

          {isCameraMode ? (
            <View style={styles.cameraCard}>
              <CameraView
                style={styles.camera}
                facing="back"
                barcodeScannerSettings={{ barcodeTypes: cameraTypes }}
                onBarcodeScanned={mode === "pairing" ? handleQr : scanArmed ? handleProductBarcode : undefined}
              >
                <View style={styles.cameraOverlay}>
                  <View style={mode === "pairing" ? styles.qrFrame : styles.scanFrame} />
                  <Text style={styles.cameraHint}>{mode === "pairing" ? "Alinea el QR de la caja" : "Alinea el código dentro del marco"}</Text>
                </View>
              </CameraView>
              {mode === "scanning" && !scanArmed ? <Pressable onPress={() => { locked.current = false; setScanArmed(true); }} style={styles.nextScan}><Text style={styles.primaryButtonText}>Escanear siguiente producto</Text></Pressable> : null}
              <Pressable onPress={() => { locked.current = false; setScanArmed(false); setMode(connection ? "ready" : "connect"); }} style={styles.cancelScan}><Text style={styles.cancelScanText}>{mode === "pairing" ? "Cancelar" : "Cerrar lector"}</Text></Pressable>
            </View>
          ) : connection && mode === "scanning" ? null : connection && mode === "ready" ? (
            <View style={styles.scanPanel}>
              <View style={styles.scanIcon}><Text style={styles.scanIconText}>▥</Text></View>
              <Text style={styles.panelTitle}>Listo para cobrar</Text>
              <Text style={styles.panelDescription}>Escanea un producto. La caja lo buscará en el catálogo y lo dejará seleccionado para confirmar la venta.</Text>
              <Pressable style={styles.primaryButton} onPress={() => askForCamera("scanning")}>
                <Text style={styles.primaryButtonText}>Abrir cámara</Text>
                <Text style={styles.buttonArrow}>→</Text>
              </Pressable>
              <Text style={styles.smallNote}>Cada lectura se envía a la caja conectada.</Text>
            </View>
          ) : (
            <View style={styles.connectPanel}>
              <Text style={styles.panelTitle}>Conecta tu caja</Text>
              <Text style={styles.panelDescription}>En Oslo, abre Punto de Venta y toca “Conectar móvil”. Escanea el QR que aparece en la computadora.</Text>
              <Pressable style={styles.primaryButton} onPress={() => askForCamera("pairing")} disabled={busy}>
                <Text style={styles.primaryButtonText}>Escanear QR de la caja</Text>
                <Text style={styles.buttonArrow}>→</Text>
              </Pressable>
              <View style={styles.divider}><View style={styles.dividerLine} /><Text style={styles.dividerText}>o conecta manualmente</Text><View style={styles.dividerLine} /></View>
              <Text style={styles.fieldLabel}>Dirección de la caja</Text>
              <TextInput style={styles.input} value={baseUrl} onChangeText={setBaseUrl} placeholder="http://IP-DE-LA-CAJA:8765" placeholderTextColor="#64748b" autoCapitalize="none" autoCorrect={false} keyboardType="url" />
              <Text style={styles.fieldLabel}>Clave temporal</Text>
              <TextInput style={styles.input} value={token} onChangeText={setToken} placeholder="Clave que muestra Oslo" placeholderTextColor="#64748b" autoCapitalize="none" autoCorrect={false} />
              <Pressable style={[styles.secondaryButton, busy && styles.buttonDisabled]} onPress={connectManually} disabled={busy}>
                {busy ? <ActivityIndicator color="#e2e8f0" /> : <Text style={styles.secondaryButtonText}>Probar conexión</Text>}
              </Pressable>
              <Text style={styles.smallNote}>El teléfono y la computadora deben estar en la misma red Wi-Fi.</Text>
            </View>
          )}

          {connection && mode !== "scanning" && mode !== "pairing" ? (
            <Pressable style={styles.secondaryButton} onPress={() => askForCamera("pairing")}><Text style={styles.secondaryButtonText}>Vincular otra caja</Text></Pressable>
          ) : null}
          <Text style={styles.footer}>El lector solo transmite códigos a la caja vinculada.</Text>
        </ScrollView>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}

function statusGlyph(tone) {
  return tone === "good" ? "✓" : tone === "bad" ? "!" : tone === "warn" ? "?" : "•";
}

function statusStyle(tone) {
  if (tone === "good") return { borderColor: "#14532d", backgroundColor: "#0d1c18" };
  if (tone === "bad") return { borderColor: "#7f1d1d", backgroundColor: "#211316" };
  if (tone === "warn") return { borderColor: "#854d0e", backgroundColor: "#211b10" };
  return { borderColor: "#263448", backgroundColor: "#121e2d" };
}

const styles = StyleSheet.create({
  flex: { flex: 1 },
  safe: { flex: 1, backgroundColor: "#090f1b" },
  loading: { flex: 1, backgroundColor: "#090f1b", alignItems: "center", justifyContent: "center" },
  loadingText: { color: "#94a3b8", marginTop: 14, fontSize: 14 },
  page: { paddingHorizontal: 20, paddingTop: 18, paddingBottom: 34, maxWidth: 560, width: "100%", alignSelf: "center" },
  header: { flexDirection: "row", alignItems: "center", marginBottom: 22 },
  brandIcon: { width: 44, height: 44, backgroundColor: "#123047", borderRadius: 14, alignItems: "center", justifyContent: "center", marginRight: 12, borderWidth: 1, borderColor: "#1e526b" },
  brandGlyph: { color: "#7dd3fc", fontWeight: "900", fontSize: 24 },
  headerCopy: { flex: 1 },
  eyebrow: { color: "#38bdf8", fontSize: 10, letterSpacing: 2, fontWeight: "800" },
  title: { color: "#f8fafc", fontSize: 21, fontWeight: "800", marginTop: 1 },
  onlineDot: { width: 10, height: 10, borderRadius: 5 },
  dotGood: { backgroundColor: "#34d399" },
  dotOff: { backgroundColor: "#64748b" },
  connectionCard: { padding: 16, backgroundColor: "#111c2c", borderColor: "#233248", borderWidth: 1, borderRadius: 18, marginBottom: 12 },
  connectionTop: { flexDirection: "row", alignItems: "center", justifyContent: "space-between" },
  cardLabel: { color: "#64748b", fontSize: 9, letterSpacing: 1.5, fontWeight: "800" },
  connectionTitle: { color: "#e2e8f0", fontSize: 15, fontWeight: "700", marginTop: 5 },
  connectionDetail: { color: "#94a3b8", fontSize: 12, marginTop: 10 },
  linkButton: { paddingHorizontal: 12, paddingVertical: 8 },
  linkText: { color: "#7dd3fc", fontSize: 12, fontWeight: "700" },
  statusCard: { minHeight: 68, borderWidth: 1, borderRadius: 16, padding: 13, flexDirection: "row", alignItems: "center", marginBottom: 16 },
  statusMark: { width: 30, height: 30, borderRadius: 15, backgroundColor: "#172638", alignItems: "center", justifyContent: "center", marginRight: 11 },
  statusMarkText: { color: "#7dd3fc", fontWeight: "900", fontSize: 15 },
  statusCopy: { flex: 1 },
  statusTitle: { color: "#f1f5f9", fontSize: 13, fontWeight: "700" },
  statusDetail: { color: "#a5b4c5", fontSize: 11, lineHeight: 16, marginTop: 3 },
  scanPanel: { backgroundColor: "#111c2c", borderColor: "#233248", borderWidth: 1, borderRadius: 22, padding: 22, alignItems: "center", marginBottom: 14 },
  connectPanel: { backgroundColor: "#111c2c", borderColor: "#233248", borderWidth: 1, borderRadius: 22, padding: 20, marginBottom: 14 },
  scanIcon: { width: 64, height: 64, borderRadius: 20, backgroundColor: "#102c40", borderWidth: 1, borderColor: "#1e526b", alignItems: "center", justifyContent: "center", marginBottom: 15 },
  scanIconText: { color: "#7dd3fc", fontSize: 32, fontWeight: "700" },
  panelTitle: { color: "#f8fafc", fontSize: 19, fontWeight: "800", textAlign: "center", marginBottom: 8 },
  panelDescription: { color: "#9bacbf", fontSize: 13, lineHeight: 20, textAlign: "center", marginBottom: 18 },
  primaryButton: { backgroundColor: "#38bdf8", borderRadius: 14, minHeight: 52, paddingHorizontal: 17, flexDirection: "row", alignItems: "center", justifyContent: "center", width: "100%" },
  primaryButtonText: { color: "#071521", fontWeight: "800", fontSize: 14 },
  buttonArrow: { position: "absolute", right: 18, color: "#071521", fontSize: 21, fontWeight: "700" },
  smallNote: { color: "#64748b", fontSize: 10, textAlign: "center", lineHeight: 15, marginTop: 14 },
  divider: { flexDirection: "row", alignItems: "center", marginVertical: 18 },
  dividerLine: { flex: 1, height: 1, backgroundColor: "#29384c" },
  dividerText: { color: "#64748b", fontSize: 10, paddingHorizontal: 10 },
  fieldLabel: { color: "#a9b8c9", fontSize: 11, fontWeight: "700", marginBottom: 6, marginTop: 10 },
  input: { backgroundColor: "#0b1421", color: "#e2e8f0", borderColor: "#29384c", borderWidth: 1, borderRadius: 11, paddingHorizontal: 12, paddingVertical: 12, fontSize: 13 },
  secondaryButton: { minHeight: 46, alignItems: "center", justifyContent: "center", backgroundColor: "#1c2a3b", borderWidth: 1, borderColor: "#314359", borderRadius: 13, marginTop: 12, paddingHorizontal: 16 },
  secondaryButtonText: { color: "#dbe7f2", fontWeight: "700", fontSize: 12 },
  buttonDisabled: { opacity: 0.6 },
  cameraCard: { overflow: "hidden", borderRadius: 22, borderColor: "#263448", borderWidth: 1, backgroundColor: "#101a29", marginBottom: 14 },
  camera: { width: "100%", height: 430 },
  cameraOverlay: { flex: 1, alignItems: "center", justifyContent: "center", backgroundColor: "rgba(4, 10, 18, 0.18)" },
  scanFrame: { width: "78%", height: 148, borderWidth: 2, borderColor: "#7dd3fc", borderRadius: 16, backgroundColor: "rgba(56, 189, 248, 0.04)" },
  qrFrame: { width: 230, height: 230, borderWidth: 2, borderColor: "#7dd3fc", borderRadius: 22, backgroundColor: "rgba(56, 189, 248, 0.04)" },
  cameraHint: { color: "#f8fafc", fontSize: 12, fontWeight: "700", backgroundColor: "rgba(5, 12, 20, 0.72)", paddingHorizontal: 13, paddingVertical: 8, borderRadius: 20, marginTop: 19, overflow: "hidden" },
  cancelScan: { alignItems: "center", paddingVertical: 14 },
  nextScan: { alignSelf: "center", backgroundColor: "#38bdf8", borderRadius: 12, alignItems: "center", paddingHorizontal: 18, paddingVertical: 12, marginTop: 12 },
  cancelScanText: { color: "#7dd3fc", fontWeight: "700", fontSize: 13 },
  footer: { color: "#56657a", textAlign: "center", fontSize: 10, marginTop: 10 },
});
