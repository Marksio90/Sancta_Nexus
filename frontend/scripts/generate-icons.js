#!/usr/bin/env node
/**
 * Sancta Nexus — Generator ikon PNG
 *
 * Generuje wszystkie wymagane rozmiary ikon PNG z SVG źródłowego.
 * Wymaga: sharp  →  npm install --save-dev sharp
 *
 * Użycie:
 *   node scripts/generate-icons.js
 *
 * Wyjście: public/icons/*.png  (PWA + App Store)
 *
 * Rozmiary:
 *   PWA:        192, 512
 *   iOS:        20, 29, 40, 58, 60, 76, 80, 87, 120, 152, 167, 180, 1024
 *   Android:    36, 48, 72, 96, 144, 192, 512
 *   Favicon:    16, 32
 */

const path = require("path");
const fs   = require("fs");

const ICONS_DIR = path.join(__dirname, "../public/icons");
const SVG_512   = path.join(ICONS_DIR, "icon-512.svg");

const SIZES = [
  // Favicon
  { size: 16,   name: "favicon-16.png" },
  { size: 32,   name: "favicon-32.png" },
  // PWA
  { size: 192,  name: "icon-192.png" },
  { size: 512,  name: "icon-512.png" },
  // iOS (AppIcon.appiconset)
  { size: 20,   name: "ios-20.png" },
  { size: 29,   name: "ios-29.png" },
  { size: 40,   name: "ios-40.png" },
  { size: 58,   name: "ios-58.png" },
  { size: 60,   name: "ios-60.png" },
  { size: 76,   name: "ios-76.png" },
  { size: 80,   name: "ios-80.png" },
  { size: 87,   name: "ios-87.png" },
  { size: 120,  name: "ios-120.png" },
  { size: 152,  name: "ios-152.png" },
  { size: 167,  name: "ios-167.png" },
  { size: 180,  name: "ios-180.png" },
  { size: 1024, name: "ios-1024.png" }, // App Store
  // Android (mipmap)
  { size: 36,   name: "android-36.png" },
  { size: 48,   name: "android-48.png" },
  { size: 72,   name: "android-72.png" },
  { size: 96,   name: "android-96.png" },
  { size: 144,  name: "android-144.png" },
  { size: 192,  name: "android-192.png" },
  { size: 512,  name: "android-512.png" }, // Play Store
];

async function generate() {
  let sharp;
  try {
    sharp = require("sharp");
  } catch {
    console.error("❌  Brak pakietu sharp. Zainstaluj: npm install --save-dev sharp");
    process.exit(1);
  }

  if (!fs.existsSync(SVG_512)) {
    console.error("❌  Brak pliku źródłowego:", SVG_512);
    process.exit(1);
  }

  const svgBuffer = fs.readFileSync(SVG_512);
  fs.mkdirSync(ICONS_DIR, { recursive: true });

  console.log("🎨  Generuję ikony PNG z SVG...\n");

  const results = await Promise.allSettled(
    SIZES.map(async ({ size, name }) => {
      const outPath = path.join(ICONS_DIR, name);
      await sharp(svgBuffer)
        .resize(size, size)
        .png({ quality: 100, compressionLevel: 9 })
        .toFile(outPath);
      console.log(`  ✓  ${name.padEnd(22)} ${size}×${size}`);
    })
  );

  const failed = results.filter((r) => r.status === "rejected");
  if (failed.length) {
    console.error("\n❌  Błędy:", failed.map((r) => r.reason));
    process.exit(1);
  }

  console.log(`\n✅  Wygenerowano ${SIZES.length} plików ikon w: ${ICONS_DIR}`);
  console.log("\nNastępne kroki:");
  console.log("  iOS:     skopiuj ios-1024.png do AppIcon.appiconset w Xcode");
  console.log("  Android: ikony android-*.png → res/mipmap-* w Android Studio");
  console.log("  PWA:     icon-192.png i icon-512.png są już odczytywane przez manifest.json\n");
}

generate().catch((err) => { console.error(err); process.exit(1); });
