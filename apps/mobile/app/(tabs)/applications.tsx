import { useQuery } from "@tanstack/react-query";
import {
  View, Text, FlatList, StyleSheet, ActivityIndicator, TouchableOpacity
} from "react-native";
import { applicationsApi, type Application } from "@/services/api";
import { SafeAreaView } from "react-native-safe-area-context";
import { Ionicons } from "@expo/vector-icons";

const STATUS_CONFIG: Record<string, { label: string; color: string; icon: string }> = {
  applied:              { label: "Applied",      color: "#3b82f6", icon: "send-outline" },
  screening:            { label: "Screening",    color: "#f59e0b", icon: "search-outline" },
  interview_scheduled:  { label: "Interview",    color: "#8b5cf6", icon: "calendar-outline" },
  interview_completed:  { label: "Interviewed",  color: "#6366f1", icon: "checkmark-done-outline" },
  offer_extended:       { label: "Offer",        color: "#16a34a", icon: "gift-outline" },
  offer_accepted:       { label: "Accepted",     color: "#15803d", icon: "trophy-outline" },
  offer_rejected:       { label: "Declined",     color: "#6b7280", icon: "close-circle-outline" },
  rejected:             { label: "Rejected",     color: "#ef4444", icon: "close-outline" },
  withdrawn:            { label: "Withdrawn",    color: "#9ca3af", icon: "remove-circle-outline" },
};

function ApplicationCard({ app }: { app: Application }) {
  const cfg = STATUS_CONFIG[app.status] ?? STATUS_CONFIG.applied;
  return (
    <View style={styles.card}>
      <View style={styles.cardRow}>
        <View style={styles.logoBox}>
          <Text style={styles.logoText}>{app.company[0]}</Text>
        </View>
        <View style={styles.cardInfo}>
          <Text style={styles.jobTitle} numberOfLines={1}>{app.title}</Text>
          <Text style={styles.companyName}>{app.company}</Text>
          {app.location && (
            <Text style={styles.location}>📍 {app.location}</Text>
          )}
        </View>
        <View style={[styles.statusBadge, { backgroundColor: cfg.color + "18", borderColor: cfg.color + "44" }]}>
          <Ionicons name={cfg.icon as never} size={12} color={cfg.color} />
          <Text style={[styles.statusText, { color: cfg.color }]}>{cfg.label}</Text>
        </View>
      </View>
      {app.interview_date && (
        <View style={styles.interviewRow}>
          <Ionicons name="calendar" size={12} color="#8b5cf6" />
          <Text style={styles.interviewText}>
            {new Date(app.interview_date).toLocaleDateString("en-IN", { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" })}
          </Text>
        </View>
      )}
      {app.offer_amount && (
        <Text style={styles.offerText}>🎉 Offer: ₹{app.offer_amount} LPA</Text>
      )}
      <Text style={styles.dateText}>
        Applied {new Date(app.applied_at).toLocaleDateString("en-IN", { day: "numeric", month: "short" })}
      </Text>
    </View>
  );
}

export default function ApplicationsScreen() {
  const { data: apps = [], isLoading, refetch } = useQuery({
    queryKey: ["applications"],
    queryFn: applicationsApi.list,
  });

  const grouped = Object.entries(
    apps.reduce<Record<string, Application[]>>((acc, a) => {
      acc[a.status] = [...(acc[a.status] ?? []), a];
      return acc;
    }, {})
  );

  if (isLoading) {
    return (
      <View style={styles.center}>
        <ActivityIndicator size="large" color="#16a34a" />
      </View>
    );
  }

  return (
    <SafeAreaView style={styles.container}>
      <View style={styles.header}>
        <Text style={styles.headerTitle}>Applications</Text>
        <Text style={styles.headerCount}>{apps.length} total</Text>
      </View>

      {apps.length === 0 ? (
        <View style={styles.center}>
          <Text style={{ fontSize: 40 }}>📭</Text>
          <Text style={styles.emptyText}>No applications yet</Text>
          <Text style={styles.emptySub}>Swipe right on jobs to apply!</Text>
        </View>
      ) : (
        <FlatList
          data={apps}
          keyExtractor={a => a.id}
          renderItem={({ item }) => <ApplicationCard app={item} />}
          contentContainerStyle={{ padding: 16, gap: 12 }}
          onRefresh={refetch}
          refreshing={isLoading}
        />
      )}
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container:      { flex: 1, backgroundColor: "#f9fafb" },
  center:         { flex: 1, alignItems: "center", justifyContent: "center" },
  header:         { flexDirection: "row", justifyContent: "space-between", alignItems: "center", padding: 20, paddingBottom: 12 },
  headerTitle:    { fontSize: 22, fontWeight: "800", color: "#111827" },
  headerCount:    { fontSize: 13, color: "#9ca3af" },
  emptyText:      { fontSize: 18, fontWeight: "700", color: "#111827", marginTop: 12 },
  emptySub:       { fontSize: 13, color: "#9ca3af", marginTop: 4 },
  card:           { backgroundColor: "white", borderRadius: 18, padding: 16, shadowColor: "#000", shadowOffset: { width: 0, height: 2 }, shadowOpacity: 0.06, shadowRadius: 8, elevation: 2 },
  cardRow:        { flexDirection: "row", alignItems: "flex-start" },
  logoBox:        { width: 44, height: 44, borderRadius: 12, backgroundColor: "#f3f4f6", alignItems: "center", justifyContent: "center", marginRight: 12 },
  logoText:       { fontSize: 20, fontWeight: "700", color: "#6b7280" },
  cardInfo:       { flex: 1, marginRight: 8 },
  jobTitle:       { fontSize: 15, fontWeight: "700", color: "#111827" },
  companyName:    { fontSize: 13, color: "#6b7280", marginTop: 2 },
  location:       { fontSize: 12, color: "#9ca3af", marginTop: 2 },
  statusBadge:    { flexDirection: "row", alignItems: "center", gap: 4, paddingHorizontal: 8, paddingVertical: 4, borderRadius: 20, borderWidth: 1 },
  statusText:     { fontSize: 11, fontWeight: "600" },
  interviewRow:   { flexDirection: "row", alignItems: "center", gap: 4, marginTop: 8, backgroundColor: "#f5f3ff", padding: 8, borderRadius: 10 },
  interviewText:  { fontSize: 12, color: "#8b5cf6", fontWeight: "600" },
  offerText:      { fontSize: 13, color: "#16a34a", fontWeight: "700", marginTop: 8 },
  dateText:       { fontSize: 11, color: "#d1d5db", marginTop: 8 },
});
