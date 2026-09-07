import { useEffect, useState } from "react";
import { StatusBar } from "expo-status-bar";
import {
  ActivityIndicator, Modal, Pressable, ScrollView, StyleSheet, Text, View,
} from "react-native";
import MapView, { Marker } from "react-native-maps";
import { api } from "./src/api.js";
import { classInfo } from "./src/classes.js";

// View-only alert companion (Plan.md "one honest risk call"): map of
// classified thermal sources + an alert feed + tap-for-detail. No more.
// From a device, localhost is not the dev machine — set
// EXPO_PUBLIC_API_BASE_URL to the LAN IP (Android emulator: 10.0.2.2).

export default function App() {
  const [sources, setSources] = useState([]);
  const [alerts, setAlerts] = useState([]);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(true);
  const [feedOpen, setFeedOpen] = useState(false);
  const [detailId, setDetailId] = useState(null);

  useEffect(() => {
    Promise.all([api.sources(), api.alerts()])
      .then(([fc, al]) => { setSources(fc.features); setAlerts(al.alerts); })
      .catch((e) => setError(String(e.message || e)))
      .finally(() => setLoading(false));
  }, []);

  return (
    <View style={styles.container}>
      <View style={styles.header}>
        <Text style={styles.headerText}>Thermal Source Monitor</Text>
        <Text style={styles.sub}>
          {error ? `! ${error}` : loading ? "Loading…" : `${sources.length} classified sources`}
        </Text>
      </View>

      <MapView
        style={styles.map}
        initialRegion={{ latitude: 22.5, longitude: 80, latitudeDelta: 22, longitudeDelta: 22 }}
      >
        {sources.map((f) => {
          const [lng, lat] = f.geometry.coordinates;
          const p = f.properties;
          const info = classInfo(p.predicted_class);
          return (
            <Marker
              key={p.id}
              coordinate={{ latitude: lat, longitude: lng }}
              onPress={() => setDetailId(p.id)}
              tracksViewChanges={false}
            >
              <View
                style={[
                  styles.dot,
                  { backgroundColor: info.color, borderColor: p.is_unregistered ? "#fafafa" : "#09090b",
                    borderWidth: p.is_unregistered ? 2 : 1 },
                ]}
              />
            </Marker>
          );
        })}
      </MapView>

      <Pressable style={styles.feedTab} onPress={() => setFeedOpen(true)}>
        <Text style={styles.feedTabText}>Alerts</Text>
        <View style={styles.badge}><Text style={styles.badgeText}>{alerts.length}</Text></View>
      </Pressable>

      <AlertFeed
        visible={feedOpen}
        alerts={alerts}
        onClose={() => setFeedOpen(false)}
        onPick={(id) => { setFeedOpen(false); setDetailId(id); }}
      />
      <SourceDetail id={detailId} onClose={() => setDetailId(null)} />

      <StatusBar style="light" />
    </View>
  );
}

function AlertFeed({ visible, alerts, onClose, onPick }) {
  return (
    <Modal visible={visible} animationType="slide" transparent onRequestClose={onClose}>
      <Pressable style={styles.sheetScrim} onPress={onClose} />
      <View style={styles.sheet}>
        <View style={styles.sheetHandle} />
        <Text style={styles.sheetTitle}>Alerts</Text>
        <ScrollView>
          {alerts.map((a) => (
            <Pressable key={a.source_id} style={styles.alertRow} onPress={() => onPick(a.source_id)}>
              <View style={[styles.sev, { backgroundColor: a.severity === "unregistered" ? "#f59e0b" : "#52525b" }]} />
              <View style={{ flex: 1 }}>
                <Text style={styles.alertClass}>
                  {classInfo(a.predicted_class).label}
                  <Text style={styles.alertSev}>  {a.severity.toUpperCase()}</Text>
                </Text>
                <Text style={styles.alertReason}>{a.reason}</Text>
              </View>
            </Pressable>
          ))}
          {alerts.length === 0 && <Text style={styles.empty}>No active alerts.</Text>}
        </ScrollView>
      </View>
    </Modal>
  );
}

function SourceDetail({ id, onClose }) {
  const [data, setData] = useState(null);
  const [err, setErr] = useState(null);

  useEffect(() => {
    if (id == null) return;
    setData(null); setErr(null);
    api.source(id).then(setData).catch((e) => setErr(String(e.message || e)));
  }, [id]);

  const p = data?.properties;
  const c = data?.classification;

  return (
    <Modal visible={id != null} animationType="slide" transparent onRequestClose={onClose}>
      <Pressable style={styles.sheetScrim} onPress={onClose} />
      <View style={[styles.sheet, { maxHeight: "80%" }]}>
        <View style={styles.sheetHandle} />
        <Text style={styles.sheetTitle}>Source #{id}</Text>
        {!data && !err && <ActivityIndicator color="#a1a1aa" style={{ marginVertical: 24 }} />}
        {err && <Text style={styles.errText}>{err}</Text>}
        {data && (
          <ScrollView>
            {c && (
              <>
                <View style={styles.classRow}>
                  <View style={[styles.dot, { backgroundColor: classInfo(c.predicted_class).color }]} />
                  <Text style={styles.className}>{classInfo(c.predicted_class).label}</Text>
                  <Text style={styles.classConf}>{Math.round(c.confidence * 100)}% · {c.method}</Text>
                </View>
                {c.is_unregistered && (
                  <View style={styles.unregBox}>
                    <Text style={styles.unregTitle}>UNREGISTERED SOURCE</Text>
                    <Text style={styles.unregBody}>{c.unregistered_reason}</Text>
                  </View>
                )}
                <Text style={styles.blockLabel}>Why</Text>
                <Text style={styles.body}>{c.rationale}</Text>
                {data.narrative ? (
                  <>
                    <Text style={styles.blockLabel}>Incident brief (AI)</Text>
                    <Text style={styles.body}>{data.narrative}</Text>
                  </>
                ) : null}
              </>
            )}
            <Text style={styles.blockLabel}>Lifecycle</Text>
            {p && (
              <View>
                <Row k="Land cover" v={(p.land_cover || "not sampled").replace(/_/g, " ")} />
                {p.burn_scar ? (
                  <Row k="Burn scar (S2)" v={`${p.burn_scar} · dNBR ${p.dnbr}`} />
                ) : null}
                <Row k="First seen" v={String(p.first_seen).slice(0, 10)} />
                <Row k="Last seen" v={String(p.last_seen).slice(0, 10)} />
                <Row k="Span (days)" v={p.span_days} />
                <Row k="Seen on (days)" v={p.recurrence_days} />
                <Row k="Detections" v={p.detection_count} />
                <Row k="Day/night" v={p.day_night_ratio} />
                <Row k="FRP mean (MW)" v={Number(p.frp_mean).toFixed(1)} />
                <Row k="Footprint (km2)" v={p.bbox_area_km2} />
              </View>
            )}
          </ScrollView>
        )}
      </View>
    </Modal>
  );
}

const Row = ({ k, v }) => (
  <View style={styles.kv}>
    <Text style={styles.kvK}>{k}</Text>
    <Text style={styles.kvV}>{String(v)}</Text>
  </View>
);

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: "#09090b" },
  header: { padding: 16, paddingTop: 48 },
  headerText: { color: "#fafafa", fontSize: 14, fontWeight: "700", textTransform: "uppercase" },
  sub: { color: "#a1a1aa", fontSize: 12, marginTop: 2 },
  map: { flex: 1 },
  dot: { width: 12, height: 12, borderRadius: 3 },

  feedTab: {
    position: "absolute", right: 16, bottom: 32, flexDirection: "row", alignItems: "center",
    backgroundColor: "#18181b", borderColor: "#3f3f46", borderWidth: 1, borderRadius: 4,
    paddingHorizontal: 14, paddingVertical: 10, gap: 8,
  },
  feedTabText: { color: "#e4e4e7", fontSize: 13, fontWeight: "600" },
  badge: { backgroundColor: "#f59e0b", borderRadius: 8, paddingHorizontal: 6, paddingVertical: 1 },
  badgeText: { color: "#09090b", fontSize: 11, fontWeight: "700" },

  sheetScrim: { flex: 1, backgroundColor: "rgba(0,0,0,0.5)" },
  sheet: {
    backgroundColor: "#09090b", borderTopColor: "#27272a", borderTopWidth: 1,
    padding: 16, paddingBottom: 32, maxHeight: "70%",
  },
  sheetHandle: { alignSelf: "center", width: 36, height: 4, borderRadius: 2, backgroundColor: "#3f3f46", marginBottom: 12 },
  sheetTitle: { color: "#fafafa", fontSize: 14, fontWeight: "700", textTransform: "uppercase", marginBottom: 10 },

  alertRow: { flexDirection: "row", gap: 10, paddingVertical: 10, borderBottomColor: "#18181b", borderBottomWidth: 1 },
  sev: { width: 6, height: 6, borderRadius: 3, marginTop: 5 },
  alertClass: { color: "#e4e4e7", fontSize: 13, fontWeight: "600" },
  alertSev: { color: "#71717a", fontSize: 10, fontWeight: "600" },
  alertReason: { color: "#a1a1aa", fontSize: 11, marginTop: 2 },
  empty: { color: "#71717a", fontSize: 12, paddingVertical: 16 },

  classRow: { flexDirection: "row", alignItems: "center", gap: 8, marginBottom: 8 },
  className: { color: "#fafafa", fontSize: 15, fontWeight: "700" },
  classConf: { color: "#a1a1aa", fontSize: 12, marginLeft: "auto" },
  unregBox: { borderColor: "rgba(245,158,11,0.4)", borderWidth: 1, backgroundColor: "rgba(69,26,3,0.3)", borderRadius: 4, padding: 10, marginBottom: 8 },
  unregTitle: { color: "#fcd34d", fontSize: 11, fontWeight: "700" },
  unregBody: { color: "rgba(253,230,138,0.8)", fontSize: 12, marginTop: 4 },

  blockLabel: { color: "#71717a", fontSize: 11, fontWeight: "700", textTransform: "uppercase", marginTop: 14, marginBottom: 4 },
  body: { color: "#d4d4d8", fontSize: 12, lineHeight: 18 },
  errText: { color: "#f87171", fontSize: 12, marginVertical: 16 },

  kv: { flexDirection: "row", justifyContent: "space-between", paddingVertical: 3 },
  kvK: { color: "#71717a", fontSize: 12 },
  kvV: { color: "#e4e4e7", fontSize: 12, fontVariant: ["tabular-nums"] },
});
