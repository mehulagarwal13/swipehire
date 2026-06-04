/**
 * Expo Push Notification service.
 * - Requests permission on first launch
 * - Registers token with SwipeHire backend
 * - Handles foreground + background notification routing
 */
import * as Notifications from "expo-notifications";
import * as Device from "expo-device";
import { Platform } from "react-native";
import { router } from "expo-router";
import { api } from "./api";

// Configure how notifications appear when app is in foreground
Notifications.setNotificationHandler({
  handleNotification: async () => ({
    shouldShowAlert: true,
    shouldPlaySound: true,
    shouldSetBadge: true,
  }),
});

// ─── Android notification channels ───────────────────────────────────────────

export async function setupAndroidChannels(): Promise<void> {
  if (Platform.OS !== "android") return;

  await Notifications.setNotificationChannelAsync("default", {
    name: "General",
    importance: Notifications.AndroidImportance.DEFAULT,
  });
  await Notifications.setNotificationChannelAsync("matches", {
    name: "Job Matches",
    importance: Notifications.AndroidImportance.HIGH,
    vibrationPattern: [0, 250, 250, 250],
    lightColor: "#16a34a",
  });
  await Notifications.setNotificationChannelAsync("applications", {
    name: "Application Updates",
    importance: Notifications.AndroidImportance.HIGH,
    vibrationPattern: [0, 250, 250, 250],
    lightColor: "#3b82f6",
  });
}

// ─── Permission + token registration ─────────────────────────────────────────

export async function registerForPushNotifications(): Promise<string | null> {
  if (!Device.isDevice) {
    console.log("Push notifications only work on physical devices");
    return null;
  }

  // Request permissions
  const { status: existingStatus } = await Notifications.getPermissionsAsync();
  let finalStatus = existingStatus;

  if (existingStatus !== "granted") {
    const { status } = await Notifications.requestPermissionsAsync();
    finalStatus = status;
  }

  if (finalStatus !== "granted") {
    console.log("Push notification permission denied");
    return null;
  }

  // Setup Android channels
  await setupAndroidChannels();

  // Get Expo push token
  const tokenData = await Notifications.getExpoPushTokenAsync({
    projectId: "your-eas-project-id", // from app.json extra.eas.projectId
  });
  const token = tokenData.data;

  // Register with our backend
  try {
    await api.post("/push/register", {
      token,
      platform: Platform.OS,
    });
    console.log("Push token registered:", token.slice(0, 30) + "...");
  } catch (err) {
    console.warn("Failed to register push token:", err);
  }

  return token;
}

// ─── Notification tap handler ─────────────────────────────────────────────────

export function handleNotificationResponse(
  response: Notifications.NotificationResponse
): void {
  const data = response.notification.request.content.data as Record<string, string>;
  const screen = data?.screen;

  if (!screen) return;

  // Route to correct screen based on notification data
  switch (screen) {
    case "swipe":
      router.push("/(tabs)/swipe");
      break;
    case "applications":
      router.push("/(tabs)/applications");
      break;
    case "profile":
      router.push("/(tabs)/profile");
      break;
    default:
      router.push("/(tabs)/swipe");
  }
}

// ─── Unregister on logout ─────────────────────────────────────────────────────

export async function unregisterPushToken(): Promise<void> {
  try {
    await api.delete("/push/token");
  } catch {
    // Ignore — best effort
  }
}
