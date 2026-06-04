import { useEffect, useState, useCallback, useRef } from "react";
import {
  View, Text, StyleSheet, ActivityIndicator,
  TouchableOpacity, Dimensions, Animated
} from "react-native";
import Swiper from "react-native-deck-swiper";
import { Ionicons } from "@expo/vector-icons";
import { jobsApi, swipesApi, type JobCard } from "@/services/api";
import Toast from "react-native-toast-message";
import { SafeAreaView } from "react-native-safe-area-context";

const { width: SCREEN_W } = Dimensions.get("window");
const GREEN = "#16a34a";
const RED   = "#ef4444";
const BLUE  = "#3b82f6";

// ─── Job card component ───────────────────────────────────────────────────────

function MobileJobCard({ card }: { card: JobCard }) {
  const scoreColor =
    card.match_score >= 80 ? GREEN :
    card.match_score >= 60 ? "#f59e0b" : "#9ca3af";

  return (
    <View style={styles.card}>
      {/* Header */}
      <View style={styles.cardHeader}>
        <View style={styles.companyLogoBox}>
          <Text style={styles.companyLogoText}>{card.company[0]}</Text>
        </View>
        <View style={styles.cardHeaderText}>
          <Text style={styles.companyName} numberOfLines={1}>{card.company}</Text>
          <Text style={styles.jobTitle} numberOfLines={2}>{card.title}</Text>
        </View>
        {card.match_score > 0 && (
          <View style={[styles.matchBadge, { backgroundColor: scoreColor }]}>
            <Text style={styles.matchBadgeText}>{card.match_score}%</Text>
          </View>
        )}
      </View>

      {/* Tags */}
      <View style={styles.tagsRow}>
        {card.is_remote && <Tag label="🌍 Remote" color={BLUE} />}
        {!card.is_remote && card.location && <Tag label={`📍 ${card.location}`} />}
        {card.job_type && <Tag label={card.job_type} />}
        {(card.salary_min_lpa || card.salary_max_lpa) && (
          <Tag
            label={`₹${card.salary_min_lpa ?? "?"}–${card.salary_max_lpa ?? "?"} LPA`}
            color={GREEN}
          />
        )}
      </View>

      {/* Skills */}
      <View style={styles.skillsRow}>
        {card.skills_required.slice(0, 5).map(s => (
          <View key={s} style={styles.skillPill}>
            <Text style={styles.skillText}>{s}</Text>
          </View>
        ))}
        {card.skills_required.length > 5 && (
          <View style={[styles.skillPill, { backgroundColor: "#f3f4f6" }]}>
            <Text style={[styles.skillText, { color: "#6b7280" }]}>+{card.skills_required.length - 5}</Text>
          </View>
        )}
      </View>

      {/* Highlights */}
      {card.highlights.map((h, i) => (
        <Text key={i} style={styles.highlight}>• {h}</Text>
      ))}

      {/* Description */}
      {card.description && (
        <Text style={styles.description} numberOfLines={4}>{card.description}</Text>
      )}

      {/* Footer */}
      <View style={styles.cardFooter}>
        <Text style={styles.footerText}>via {card.source}</Text>
        <Text style={styles.footerText}>
          {new Date(card.posted_at).toLocaleDateString("en-IN", { day: "numeric", month: "short" })}
        </Text>
      </View>
    </View>
  );
}

function Tag({ label, color = "#374151" }: { label: string; color?: string }) {
  return (
    <View style={[styles.tag, { borderColor: color + "33" }]}>
      <Text style={[styles.tagText, { color }]}>{label}</Text>
    </View>
  );
}

// ─── Swipe screen ─────────────────────────────────────────────────────────────

export default function SwipeScreen() {
  const swiperRef = useRef<Swiper<JobCard>>(null);
  const [jobs, setJobs]     = useState<JobCard[]>([]);
  const [loading, setLoading] = useState(true);
  const [cardIndex, setCardIndex] = useState(0);

  const loadJobs = useCallback(async (offset = 0) => {
    try {
      const feed = await jobsApi.getFeed(20, offset);
      setJobs(prev => offset === 0 ? feed : [...prev, ...feed]);
    } catch (e: unknown) {
      Toast.show({ type: "error", text1: "Failed to load jobs" });
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { loadJobs(0); }, [loadJobs]);

  const handleSwipe = useCallback(async (index: number, direction: "left" | "right" | "up") => {
    const job = jobs[index];
    if (!job) return;
    try {
      await swipesApi.record(job.id, direction, job.match_score);
      if (direction === "right") Toast.show({ type: "success", text1: `Applied to ${job.title}` });
      if (direction === "up")    Toast.show({ type: "info", text1: `Saved ${job.title}` });
    } catch {}

    // Load more when near end
    if (jobs.length - index <= 5) {
      loadJobs(jobs.length);
    }
  }, [jobs, loadJobs]);

  if (loading) {
    return (
      <View style={styles.center}>
        <ActivityIndicator size="large" color={GREEN} />
        <Text style={styles.loadingText}>Finding your matches…</Text>
      </View>
    );
  }

  if (jobs.length === 0 || cardIndex >= jobs.length) {
    return (
      <View style={styles.center}>
        <Text style={styles.emptyEmoji}>🎉</Text>
        <Text style={styles.emptyTitle}>All caught up!</Text>
        <Text style={styles.emptySubtitle}>Check back later for new jobs.</Text>
        <TouchableOpacity onPress={() => { setCardIndex(0); loadJobs(0); }} style={styles.reloadBtn}>
          <Text style={styles.reloadBtnText}>Refresh Feed</Text>
        </TouchableOpacity>
      </View>
    );
  }

  return (
    <SafeAreaView style={styles.container}>
      <View style={styles.header}>
        <Text style={styles.headerTitle}>⚡ SwipeHire</Text>
        <Text style={styles.headerSub}>{jobs.length - cardIndex} jobs remaining</Text>
      </View>

      <View style={styles.deckContainer}>
        <Swiper
          ref={swiperRef}
          cards={jobs}
          cardIndex={cardIndex}
          renderCard={(card) => <MobileJobCard card={card} />}
          onSwipedLeft={(i)  => { setCardIndex(i + 1); handleSwipe(i, "left"); }}
          onSwipedRight={(i) => { setCardIndex(i + 1); handleSwipe(i, "right"); }}
          onSwipedTop={(i)   => { setCardIndex(i + 1); handleSwipe(i, "up"); }}
          onSwipedAll={() => setCardIndex(jobs.length)}
          stackSize={3}
          stackSeparation={12}
          stackScale={4}
          backgroundColor="transparent"
          cardVerticalMargin={0}
          animateOverlayLabelsOpacity
          overlayLabels={{
            left:  { title: "SKIP",  style: { label: { color: RED,   fontSize: 28, fontWeight: "900", borderWidth: 3, borderColor: RED,   padding: 8, borderRadius: 8 }, wrapper: { flexDirection: "column", alignItems: "flex-end",  justifyContent: "flex-start", marginTop: 20, marginLeft: -20 } } },
            right: { title: "APPLY", style: { label: { color: GREEN, fontSize: 28, fontWeight: "900", borderWidth: 3, borderColor: GREEN, padding: 8, borderRadius: 8 }, wrapper: { flexDirection: "column", alignItems: "flex-start", justifyContent: "flex-start", marginTop: 20, marginLeft: 20 } } },
            top:   { title: "SAVE",  style: { label: { color: BLUE,  fontSize: 28, fontWeight: "900", borderWidth: 3, borderColor: BLUE,  padding: 8, borderRadius: 8 }, wrapper: { flexDirection: "column", alignItems: "center",     justifyContent: "center" } } },
          }}
        />
      </View>

      {/* Action buttons */}
      <View style={styles.actions}>
        <ActionBtn icon="close"        color={RED}   onPress={() => swiperRef.current?.swipeLeft()} />
        <ActionBtn icon="bookmark"     color={BLUE}  onPress={() => swiperRef.current?.swipeTop()} size={20} />
        <ActionBtn icon="checkmark"    color={GREEN} onPress={() => swiperRef.current?.swipeRight()} />
      </View>
    </SafeAreaView>
  );
}

function ActionBtn({ icon, color, onPress, size = 26 }: { icon: string; color: string; onPress: () => void; size?: number }) {
  return (
    <TouchableOpacity
      onPress={onPress}
      style={[styles.actionBtn, { borderColor: color + "44" }]}
      activeOpacity={0.7}
    >
      <Ionicons name={icon as never} size={size} color={color} />
    </TouchableOpacity>
  );
}

const styles = StyleSheet.create({
  container:      { flex: 1, backgroundColor: "#f9fafb" },
  center:         { flex: 1, alignItems: "center", justifyContent: "center", padding: 32 },
  loadingText:    { color: "#6b7280", marginTop: 12 },
  emptyEmoji:     { fontSize: 48, marginBottom: 12 },
  emptyTitle:     { fontSize: 22, fontWeight: "700", color: "#111827", marginBottom: 8 },
  emptySubtitle:  { color: "#6b7280", marginBottom: 24 },
  reloadBtn:      { backgroundColor: GREEN, paddingHorizontal: 24, paddingVertical: 14, borderRadius: 16 },
  reloadBtnText:  { color: "white", fontWeight: "700" },
  header:         { flexDirection: "row", justifyContent: "space-between", alignItems: "center", paddingHorizontal: 20, paddingVertical: 12 },
  headerTitle:    { fontSize: 20, fontWeight: "800", color: "#111827" },
  headerSub:      { fontSize: 12, color: "#9ca3af" },
  deckContainer:  { flex: 1 },
  actions:        { flexDirection: "row", justifyContent: "center", alignItems: "center", gap: 20, paddingBottom: 16, paddingTop: 8 },
  actionBtn:      { width: 60, height: 60, borderRadius: 30, backgroundColor: "white", borderWidth: 2, alignItems: "center", justifyContent: "center", shadowColor: "#000", shadowOffset: { width: 0, height: 2 }, shadowOpacity: 0.08, shadowRadius: 8, elevation: 3 },

  // Card
  card:           { flex: 1, backgroundColor: "white", borderRadius: 24, padding: 20, margin: 16, shadowColor: "#000", shadowOffset: { width: 0, height: 4 }, shadowOpacity: 0.1, shadowRadius: 16, elevation: 6 },
  cardHeader:     { flexDirection: "row", alignItems: "flex-start", marginBottom: 16 },
  companyLogoBox: { width: 52, height: 52, borderRadius: 14, backgroundColor: "#f3f4f6", alignItems: "center", justifyContent: "center", marginRight: 12, flexShrink: 0 },
  companyLogoText:{ fontSize: 24, fontWeight: "700", color: "#6b7280" },
  cardHeaderText: { flex: 1 },
  companyName:    { fontSize: 13, color: "#6b7280", fontWeight: "500", marginBottom: 2 },
  jobTitle:       { fontSize: 18, fontWeight: "800", color: "#111827" },
  matchBadge:     { paddingHorizontal: 10, paddingVertical: 4, borderRadius: 20, marginLeft: 8 },
  matchBadgeText: { color: "white", fontWeight: "700", fontSize: 12 },
  tagsRow:        { flexDirection: "row", flexWrap: "wrap", gap: 6, marginBottom: 12 },
  tag:            { paddingHorizontal: 10, paddingVertical: 4, borderRadius: 20, borderWidth: 1, borderColor: "#e5e7eb" },
  tagText:        { fontSize: 12, fontWeight: "500", color: "#374151" },
  skillsRow:      { flexDirection: "row", flexWrap: "wrap", gap: 6, marginBottom: 12 },
  skillPill:      { paddingHorizontal: 10, paddingVertical: 4, backgroundColor: "#f0fdf4", borderRadius: 20 },
  skillText:      { fontSize: 12, color: GREEN, fontWeight: "500" },
  highlight:      { fontSize: 13, color: "#4b5563", marginBottom: 4 },
  description:    { fontSize: 13, color: "#6b7280", lineHeight: 20, marginTop: 8 },
  cardFooter:     { flexDirection: "row", justifyContent: "space-between", marginTop: "auto", paddingTop: 12, borderTopWidth: 1, borderTopColor: "#f3f4f6" },
  footerText:     { fontSize: 11, color: "#9ca3af" },
});
