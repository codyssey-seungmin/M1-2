import { build } from "esbuild";
import { copyFile, mkdir, writeFile } from "node:fs/promises";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const root = dirname(fileURLToPath(import.meta.url));
const dist = join(root, "dist");
await mkdir(dist, { recursive: true });
await Promise.all(
  ["index.html", "styles.css"].map((file) =>
    copyFile(join(root, file), join(dist, file)),
  ),
);

const config = {
  apiBaseUrl: process.env.API_BASE_URL || "",
  firebase: {
    apiKey: process.env.FIREBASE_API_KEY || "",
    authDomain: process.env.FIREBASE_AUTH_DOMAIN || "",
    projectId: process.env.FIREBASE_PROJECT_ID || "",
    storageBucket: process.env.FIREBASE_STORAGE_BUCKET || "",
    messagingSenderId: process.env.FIREBASE_MESSAGING_SENDER_ID || "",
    appId: process.env.FIREBASE_APP_ID || "",
  },
};
await writeFile(
  join(dist, "config.js"),
  `window.APP_CONFIG = ${JSON.stringify(config)};\n`,
  "utf8",
);
await build({
  entryPoints: [join(root, "app.js")],
  outfile: join(dist, "app.js"),
  bundle: true,
  format: "iife",
  target: "es2020",
  minify: true,
});
console.log(`Pageful frontend built: ${dist}`);
