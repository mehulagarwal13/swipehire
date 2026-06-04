import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  View, Text, ScrollView, StyleSheet, TouchableOpacity,
  ActivityIndicator, TextInput
} from "react-native";
import { profileApi, type UserProfile } from "@/services/api";
import { SafeAreaView } from "react-native-safe-area-context";
import { Ionicons } from "@expo/vector-icons";
import * as SecureStore from "expo-secure-store";
import { router } from "expo-router";
import Toast from "react-native-toast-message";
import { useState } from "react";

const GREEN = "#16a34a";

const SKILLS = ["JavaScript","TypeScript","React","Node.js","Python","Java","SQL",
  "AWS","Docker","Git","MongoDB","PostgreSQL","Machine Learning","FastAPI","React Native"];

const LOCATIONS = ["Bangalore","Mumbai","Delhi NCR","Hyderabad","Pune","Chennai","Remote"];

export default function ProfileScreen() {
  const qc = useQueryClient();
  const [editing, setEditing] = useState(false);

  const { data: profile, isLoading } = useQuery({
    queryKey: ["profile"],
    queryFn: profileApi.get,
  });

  const [headline, setHeadline] = useState(profile?.headline ?? "");
  const [selectedSkills, setSelectedSkills] = useState<string[]>(profile?.skills ?? []);
  const [selectedLocs, setSelectedLocs] = useState<string[]>(profile?.preferred_locations ?? []);

  const updateMutation = useMutation({
    mutationFn: () => profileApi.update({ headline, skills: selectedSkills, preferred_locations: selectedLocs }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["profile"] });
      setEditing(false);
      Toast.show({ type: "success", text1: "Profile updated!" });
    },
    onError: (e: Error) => Toast.show({ type: "error", text1: e.message }),
  });

  const handleLogout = async () => {
    // Unregister push token before clearing session
    const { unregisterPushToken } = await import("@/services/push");
    await unregisterPushToken().catch(() => {});
    await SecureStore.deleteItemAsync("access_token");
    await SecureStore.deleteItemAsync("refresh_token");
    router.replace("/(auth)/login");
  };

  if (isLoading) {
    return (
      <View style={styles.center}>
        <ActivityIndicator size="large" color={GREEN} />
      </View>
    );
  }

  return (
    <SafeAreaView style={styles.container}>
      <ScrollView contentContainerStyle={styles.scroll}>
        {/* Header */}
        <View style={styles.header}>
          <View style={styles.avatar}>
            <Text style={styles.avatarText}>
              {(profile?.full_name ?? "U")[0].toUpperCase()}
            </Text>
          </View>
          <View style={styles.userInfo}>
            <Text style={styles.name}>{profile?.full_name ?? "User"}</Text>
            <Text style={styles.sub}>{profile?.email ?? profile?.phone ?? ""}</Text>
          </View>
          <TouchableOpacity onPress={() => setEditing(!editing)}>
            <Ionicons name={editing ? "close" : "pencil"} size={22} color={GREEN} />
          </TouchableOpacity>
        </View>

        {/* Profile score bar */}
        <View style={styles.scoreBox}>
          <View style={styles.scoreRow}>
            <Text style={styles.scoreLabel}>Profile Score</Text>
            <Text style={styles.scoreVal}>{profile?.profile_score ?? 0}%</Text>
          </View>
          <View style={styles.barBg}>
            <View style={[styles.barFill, { width: `${profile?.profile_score ?? 0}%` }]} />
          </View>
        </View>

        {/* Headline */}
        <Section title="Headline">
          {editing ? (
            <TextInput
              value={headline}
              onChangeText={setHeadline}
              placeholder="e.g. Full-stack Developer, 2 yrs"
              style={styles.input}
            />
          ) : (
            <Text style={styles.sectionValue}>{profile?.headline ?? "—"}</Text>
          )}
        </Section>

        {/* Skills */}
        <Section title="Skills">
          {editing ? (
            <View style={styles.chipGrid}>
              {SKILLS.map(s => (
                <TouchableOpacity
                  key={s}
                  onPress={() => setSelectedSkills(prev =>
                    prev.includes(s) ? prev.filter(x => x !== s) : [...prev, s]
                  )}
                  style={[styles.chip, selectedSkills.includes(s) && styles.chipActive]}
                >
                  <Text style={[styles.chipText, selectedSkills.includes(s) && styles.chipTextActive]}>{s}</Text>
                </TouchableOpacity>
              ))}
            </View>
          ) : (
            <View style={styles.chipGrid}>
              {(profile?.skills ?? []).slice(0, 8).map(s => (
                <View key={s} style={[styles.chip, styles.chipActive]}>
                  <Text style={styles.chipTextActive}>{s}</Text>
                </View>
              ))}
            </View>
          )}
        </Section>

        {/* Preferred locations */}
        <Section title="Preferred Locations">
          {editing ? (
            <View style={styles.chipGrid}>
              {LOCATIONS.map(l => (
                <TouchableOpacity
                  key={l}
                  onPress={() => setSelectedLocs(prev =>
                    prev.includes(l) ? prev.filter(x => x !== l) : [...prev, l]
                  )}
                  style={[styles.chip, selectedLocs.includes(l) && styles.chipActive]}
                >
                  <Text style={[styles.chipText, selectedLocs.includes(l) && styles.chipTextActive]}>{l}</Text>
                </TouchableOpacity>
              ))}
            </View>
          ) : (
            <Text style={styles.sectionValue}>
              {(profile?.preferred_locations ?? []).join(", ") || "—"}
            </Text>
          )}
        </Section>

        {/* Stats */}
        <Section title="Experience">
          <Text style={styles.sectionValue}>{profile?.experience_years ?? 0} years</Text>
        </Section>

        <Section title="Salary Expectation">
          <Text style={styles.sectionValue}>
            {profile?.min_salary_lpa ? `₹${profile.min_salary_lpa}–${profile.max_salary_lpa} LPA` : "Not set"}
          </Text>
        </Section>

        {/* Save button */}
        {editing && (
          <TouchableOpacity
            style={styles.saveBtn}
            onPress={() => updateMutation.mutate()}
            disabled={updateMutation.isPending}
          >
            {updateMutation.isPending
              ? <ActivityIndicator color="white" />
              : <Text style={styles.saveBtnText}>Save Profile</Text>
            }
          </TouchableOpacity>
        )}

        {/* Logout */}
        <TouchableOpacity style={styles.logoutBtn} onPress={handleLogout}>
          <Ionicons name="log-out-outline" size={18} color="#ef4444" />
          <Text style={styles.logoutText}>Sign Out</Text>
        </TouchableOpacity>
      </ScrollView>
    </SafeAreaView>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <View style={styles.section}>
      <Text style={styles.sectionTitle}>{title}</Text>
      {children}
    </View>
  );
}

const styles = StyleSheet.create({
  container:       { flex: 1, backgroundColor: "#f9fafb" },
  center:          { flex: 1, alignItems: "center", justifyContent: "center" },
  scroll:          { padding: 20, paddingBottom: 40 },
  header:          { flexDirection: "row", alignItems: "center", marginBottom: 20, backgroundColor: "white", padding: 16, borderRadius: 20 },
  avatar:          { width: 56, height: 56, borderRadius: 28, backgroundColor: GREEN, alignItems: "center", justifyContent: "center", marginRight: 14 },
  avatarText:      { color: "white", fontSize: 24, fontWeight: "800" },
  userInfo:        { flex: 1 },
  name:            { fontSize: 18, fontWeight: "700", color: "#111827" },
  sub:             { fontSize: 13, color: "#9ca3af", marginTop: 2 },
  scoreBox:        { backgroundColor: "white", borderRadius: 16, padding: 16, marginBottom: 16 },
  scoreRow:        { flexDirection: "row", justifyContent: "space-between", marginBottom: 8 },
  scoreLabel:      { fontSize: 14, color: "#6b7280", fontWeight: "600" },
  scoreVal:        { fontSize: 14, color: GREEN, fontWeight: "800" },
  barBg:           { height: 8, backgroundColor: "#f3f4f6", borderRadius: 8 },
  barFill:         { height: 8, backgroundColor: GREEN, borderRadius: 8 },
  section:         { backgroundColor: "white", borderRadius: 16, padding: 16, marginBottom: 12 },
  sectionTitle:    { fontSize: 12, fontWeight: "700", color: "#9ca3af", textTransform: "uppercase", letterSpacing: 0.5, marginBottom: 10 },
  sectionValue:    { fontSize: 15, color: "#374151" },
  chipGrid:        { flexDirection: "row", flexWrap: "wrap", gap: 8 },
  chip:            { paddingHorizontal: 12, paddingVertical: 6, borderRadius: 20, borderWidth: 1, borderColor: "#e5e7eb", backgroundColor: "white" },
  chipActive:      { backgroundColor: GREEN, borderColor: GREEN },
  chipText:        { fontSize: 13, color: "#374151" },
  chipTextActive:  { color: "white", fontWeight: "600" },
  input:           { borderWidth: 1, borderColor: "#e5e7eb", borderRadius: 12, paddingHorizontal: 14, paddingVertical: 12, fontSize: 15, color: "#111827" },
  saveBtn:         { backgroundColor: GREEN, borderRadius: 16, paddingVertical: 16, alignItems: "center", marginTop: 8, marginBottom: 12 },
  saveBtnText:     { color: "white", fontWeight: "700", fontSize: 16 },
  logoutBtn:       { flexDirection: "row", alignItems: "center", justifyContent: "center", gap: 8, paddingVertical: 16, marginTop: 8 },
  logoutText:      { color: "#ef4444", fontWeight: "600", fontSize: 15 },
});
