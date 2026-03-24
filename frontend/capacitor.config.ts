import type { CapacitorConfig } from "@capacitor/cli";

/**
 * Capacitor configuration for Sancta Nexus native iOS & Android apps.
 *
 * Build steps:
 *   1. npm run build:mobile   (Next.js static export → out/)
 *   2. npx cap sync           (copy web assets to native projects)
 *   3. npx cap open ios       (open Xcode)
 *   4. npx cap open android   (open Android Studio)
 *
 * First-time setup:
 *   npx cap add ios
 *   npx cap add android
 */

const config: CapacitorConfig = {
  appId: "org.sanctanexus.app",
  appName: "Sancta Nexus",
  webDir: "out",

  // ── iOS ──────────────────────────────────────────────────────────────
  ios: {
    contentInset: "always",            // respect safe-area / notch
    backgroundColor: "#0d0b1a",
    allowsLinkPreview: false,
    scrollEnabled: true,
    limitsNavigationsToAppBoundDomains: true,
  },

  // ── Android ──────────────────────────────────────────────────────────
  android: {
    backgroundColor: "#0d0b1a",
    allowMixedContent: false,          // HTTPS only in production
    captureInput: true,                // proper keyboard handling
    webContentsDebuggingEnabled: false, // disable in production
  },

  // ── Capacitor Plugins ────────────────────────────────────────────────
  plugins: {
    // Push Notifications (FCM on Android, APNs on iOS)
    PushNotifications: {
      presentationOptions: ["badge", "sound", "alert"],
    },

    // Local Notifications — for scheduled prayer times (offline)
    LocalNotifications: {
      smallIcon: "ic_stat_cross",
      iconColor: "#d4af37",  // --color-gold
      sound: "prayer_bell.wav",
    },

    // Status Bar — dark content on sacred dark background
    StatusBar: {
      style: "DARK",
      backgroundColor: "#0d0b1a",
      overlaysWebView: true,
    },

    // Splash Screen
    SplashScreen: {
      launchShowDuration: 2000,
      launchAutoHide: true,
      backgroundColor: "#0d0b1a",
      androidSplashResourceName: "splash",
      showSpinner: false,
    },

    // Haptics — subtle vibration on prayer actions
    Haptics: {},

    // Keyboard — prevent viewport resize when keyboard opens
    Keyboard: {
      resize: "body",
      style: "DARK",
      resizeOnFullScreen: true,
    },

    // Background Runner — for offline scripture pre-fetch
    BackgroundRunner: {
      label: "org.sanctanexus.app.background",
      src: "background.js",
      event: "background",
      repeat: true,
      interval: 1440, // every 24 hours (minutes)
      autoStart: false,
    },
  },

  // ── Server (dev only — comment out for production builds) ────────────
  // server: {
  //   url: "http://192.168.1.X:3000",
  //   cleartext: true,
  // },
};

export default config;
