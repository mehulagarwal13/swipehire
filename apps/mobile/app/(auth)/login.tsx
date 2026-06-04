import { useState } from "react";
import {
  View, Text, TextInput, TouchableOpacity, ActivityIndicator,
  StyleSheet, KeyboardAvoidingView, Platform, ScrollView
} from "react-native";
import { router } from "expo-router";
import * as SecureStore from "expo-secure-store";
import { authApi } from "@/services/api";
import Toast from "react-native-toast-message";

export default function LoginScreen() {
  const [phone, setPhone]   = useState("");
  const [otp, setOtp]       = useState("");
  const [step, setStep]     = useState<"phone" | "otp">("phone");
  const [loading, setLoading] = useState(false);

  const handleSendOtp = async () => {
    if (phone.length !== 10) {
      Toast.show({ type: "error", text1: "Enter a valid 10-digit number" });
      return;
    }
    setLoading(true);
    try {
      const data = await authApi.sendOtp(phone);
      if (data.dev_otp) Toast.show({ type: "info", text1: `Dev OTP: ${data.dev_otp}`, visibilityTime: 10000 });
      setStep("otp");
    } catch (e: unknown) {
      Toast.show({ type: "error", text1: e instanceof Error ? e.message : "Failed to send OTP" });
    } finally {
      setLoading(false);
    }
  };

  const handleVerifyOtp = async () => {
    if (otp.length !== 6) {
      Toast.show({ type: "error", text1: "Enter the 6-digit OTP" });
      return;
    }
    setLoading(true);
    try {
      const tokens = await authApi.verifyOtp(phone, otp);
      await SecureStore.setItemAsync("access_token",  tokens.access_token);
      await SecureStore.setItemAsync("refresh_token", tokens.refresh_token);
      await SecureStore.setItemAsync("user_id",       tokens.user_id);

      // Register push token after successful login
      const { registerForPushNotifications } = await import("@/services/push");
      registerForPushNotifications().catch(() => {});

      router.replace(tokens.is_onboarded ? "/(tabs)/swipe" : "/(auth)/onboarding");
    } catch (e: unknown) {
      Toast.show({ type: "error", text1: e instanceof Error ? e.message : "Invalid OTP" });
    } finally {
      setLoading(false);
    }
  };

  return (
    <KeyboardAvoidingView style={styles.container} behavior={Platform.OS === "ios" ? "padding" : undefined}>
      <ScrollView contentContainerStyle={styles.scroll} keyboardShouldPersistTaps="handled">
        {/* Logo */}
        <View style={styles.logoContainer}>
          <View style={styles.logoBox}>
            <Text style={styles.logoEmoji}>⚡</Text>
          </View>
          <Text style={styles.appName}>SwipeHire</Text>
          <Text style={styles.tagline}>India's AI job platform</Text>
        </View>

        <View style={styles.card}>
          {step === "phone" ? (
            <>
              <Text style={styles.heading}>Enter your mobile number</Text>
              <View style={styles.phoneRow}>
                <View style={styles.countryCode}>
                  <Text style={styles.countryCodeText}>🇮🇳 +91</Text>
                </View>
                <TextInput
                  style={styles.phoneInput}
                  value={phone}
                  onChangeText={t => setPhone(t.replace(/\D/g, "").slice(0, 10))}
                  placeholder="10-digit number"
                  keyboardType="phone-pad"
                  maxLength={10}
                />
              </View>
              <TouchableOpacity
                style={[styles.btn, phone.length !== 10 && styles.btnDisabled]}
                onPress={handleSendOtp}
                disabled={loading || phone.length !== 10}
              >
                {loading ? <ActivityIndicator color="#fff" /> : <Text style={styles.btnText}>Send OTP</Text>}
              </TouchableOpacity>
            </>
          ) : (
            <>
              <Text style={styles.heading}>Enter OTP</Text>
              <Text style={styles.subText}>Sent to +91 {phone}</Text>
              <TextInput
                style={styles.otpInput}
                value={otp}
                onChangeText={t => setOtp(t.replace(/\D/g, "").slice(0, 6))}
                placeholder="••••••"
                keyboardType="number-pad"
                maxLength={6}
                textAlign="center"
              />
              <TouchableOpacity
                style={[styles.btn, otp.length !== 6 && styles.btnDisabled]}
                onPress={handleVerifyOtp}
                disabled={loading || otp.length !== 6}
              >
                {loading ? <ActivityIndicator color="#fff" /> : <Text style={styles.btnText}>Verify & Sign In</Text>}
              </TouchableOpacity>
              <TouchableOpacity onPress={() => setStep("phone")} style={styles.backBtn}>
                <Text style={styles.backText}>← Change number</Text>
              </TouchableOpacity>
            </>
          )}
        </View>
      </ScrollView>
    </KeyboardAvoidingView>
  );
}

const GREEN = "#16a34a";

const styles = StyleSheet.create({
  container:       { flex: 1, backgroundColor: "#f0fdf4" },
  scroll:          { flexGrow: 1, justifyContent: "center", padding: 24 },
  logoContainer:   { alignItems: "center", marginBottom: 40 },
  logoBox:         { width: 72, height: 72, backgroundColor: GREEN, borderRadius: 20, alignItems: "center", justifyContent: "center", marginBottom: 12 },
  logoEmoji:       { fontSize: 36 },
  appName:         { fontSize: 30, fontWeight: "800", color: "#111827" },
  tagline:         { color: "#6b7280", marginTop: 4 },
  card:            { backgroundColor: "white", borderRadius: 24, padding: 28, shadowColor: "#000", shadowOffset: { width: 0, height: 4 }, shadowOpacity: 0.08, shadowRadius: 16, elevation: 4 },
  heading:         { fontSize: 18, fontWeight: "700", color: "#111827", marginBottom: 20 },
  subText:         { color: "#6b7280", fontSize: 14, marginBottom: 16 },
  phoneRow:        { flexDirection: "row", marginBottom: 20 },
  countryCode:     { backgroundColor: "#f9fafb", borderWidth: 1, borderColor: "#e5e7eb", borderRadius: 12, paddingHorizontal: 14, justifyContent: "center", marginRight: 8 },
  countryCodeText: { fontSize: 15, color: "#374151", fontWeight: "600" },
  phoneInput:      { flex: 1, borderWidth: 1, borderColor: "#e5e7eb", borderRadius: 12, paddingHorizontal: 16, paddingVertical: 14, fontSize: 16, color: "#111827" },
  otpInput:        { borderWidth: 1, borderColor: "#e5e7eb", borderRadius: 16, paddingVertical: 18, fontSize: 28, letterSpacing: 12, color: "#111827", marginBottom: 20, fontWeight: "700" },
  btn:             { backgroundColor: GREEN, borderRadius: 16, paddingVertical: 16, alignItems: "center" },
  btnDisabled:     { opacity: 0.5 },
  btnText:         { color: "white", fontWeight: "700", fontSize: 16 },
  backBtn:         { alignItems: "center", marginTop: 16 },
  backText:        { color: "#6b7280", fontSize: 14 },
});
