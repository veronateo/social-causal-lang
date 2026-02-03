// docs/js/scripts/record-trials.mjs

import fs from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { execa } from "execa";
import puppeteer from "puppeteer";
import ffmpegPath from "ffmpeg-static";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const ROOT_JS = path.resolve(__dirname, "..");        // docs/js
const DOCS_DIR = path.resolve(ROOT_JS, "..");          // docs
const REPO_ROOT = path.resolve(DOCS_DIR, "..");         // repo root

const OUT_DIR = path.join(ROOT_JS, "gifs");
const FRAMES_DIR = path.join(ROOT_JS, "frames");
const EXPORT_HTML = path.join(ROOT_JS, "export", "export.html");

const PATH_RENDERER = path.join(ROOT_JS, "grid-world-renderer.js");
const PATH_GENERATOR = path.join(ROOT_JS, "trial-generator.js");
const PATH_ADAPTER = path.join(ROOT_JS, "export", "export-adapter.js");

const FPS = Number(process.env.FPS || 10);
const MAX_S = Number(process.env.MAX_S || 8);
const MAX_W = Number(process.env.MAX_W || 1000);
const LANE_H = Number(process.env.LANE_H || 110);
const DPR = Number(process.env.DPR || 2);
const TARGET_W = process.env.WIDTH ? Number(process.env.WIDTH) : null;
const COLORS = Number(process.env.COLORS || 256);

// Load trials
async function loadTrials() {
  const jsonPath = path.join(REPO_ROOT, "data", "exp1", "trial_data.json");
  const raw = await fs.readFile(jsonPath, "utf8");
  const data = JSON.parse(raw);
  const ids = Array.isArray(data)
    ? data.map(d => d.trial_id || d.id || d.name).filter(Boolean)
    : Object.keys(data);
  if (!ids.length) throw new Error("No trial ids found in data/exp1/trial_data.json");
  return { kind: Array.isArray(data) ? "array" : "object", data, ids, source: jsonPath };
}


async function dumpCanvasPNG(page, selector, outPath) {
  const dataUrl = await page.evaluate((sel) => {
    const c = document.querySelector(sel);
    return c.toDataURL("image/png"); // capture full backing buffer
  }, selector);
  const base64 = dataUrl.split(",")[1];
  await fs.writeFile(outPath, Buffer.from(base64, "base64"));
}

async function waitForFirstPaint(page, selector = "#c", timeout = 5000) {
  await page.waitForFunction((sel) => {
    if (!window.__initialPaintDone) return false;                 // adapter says "first render attempted"
    const c = document.querySelector(sel);
    if (!c) return false;
    const ctx = c.getContext("2d");
    if (!ctx || c.width === 0 || c.height === 0) return false;

    // sample around the lane center area (entities live here)
    const w = c.width, h = c.height;
    const pts = [
      [w * 0.50, h * 0.22], [w * 0.45, h * 0.22], [w * 0.55, h * 0.22],       // lane band
      [w * 0.50, h * 0.50],                                           // mid
    ];
    for (const [sx, sy] of pts) {
      const x = Math.max(0, Math.min(w - 2, sx | 0));
      const y = Math.max(0, Math.min(h - 2, sy | 0));
      const d = ctx.getImageData(x, y, 2, 2).data;
      for (let i = 0; i < d.length; i += 4) {
        const r = d[i], g = d[i + 1], b = d[i + 2], a = d[i + 3];
        if (a !== 0 && (r !== 255 || g !== 255 || b !== 255)) return true; // non-white, non-transparent
      }
    }
    return false;
  }, { polling: "raf", timeout }, selector);
}


// Create GIF
async function paletteAndGif(framesDir, outGif) {
  const inputGlob = path.join(framesDir, "%05d.png");
  const scale = TARGET_W ? `scale=${TARGET_W}:-1:flags=lanczos,` : "";

  await execa(ffmpegPath, [
    "-y",
    "-framerate", String(FPS),
    "-i", inputGlob,
    "-filter_complex",
    `${scale}format=rgb24,split[a][b];[a]palettegen=stats_mode=full[p];[b][p]paletteuse=dither=none:diff_mode=none:new=1`,
    "-loop", "0",
    outGif
  ], { stdio: "inherit" });
}



async function ensureGlobalFromFile(page, filePath, name, exportNames) {
  const src = await fs.readFile(filePath, "utf8");

  const success = await page.evaluate(async ({ src, name, exportNames }) => {
    function setIfFunc(val) {
      if (typeof val === "function") {
        window[name] = val;
        return true;
      }
      return false;
    }

    if (window[name] && typeof window[name] === "function") return true;

    // Try module import via Blob
    try {
      const blob = new Blob([src], { type: "text/javascript" });
      const url = URL.createObjectURL(blob);
      const mod = await import(url);
      URL.revokeObjectURL(url);

      // Check preferred named exports
      for (const en of exportNames) {
        if (mod && typeof mod[en] === "function") {
          return setIfFunc(mod[en]);
        }
      }
      if (mod && typeof mod.default === "function") {
        return setIfFunc(mod.default);
      }

    } catch (_e) {
    }

    // Classic injection: exec as <script> and hoist a lexical binding to window
    try {
      const s = document.createElement("script");
      s.type = "text/javascript";
      s.textContent = src + `
        ;(function(){
          try {
            if (typeof ${name} !== "undefined" && !window.${name}) {
              window.${name} = ${name};
            }
          } catch (_) {}
        })();
      `;
      document.documentElement.appendChild(s);
      s.remove();
      return !!(window[name] && typeof window[name] === "function");
    } catch (_e2) {
      return false;
    }
  }, { src, name, exportNames });

  if (!success) {
    throw new Error(`Failed to expose window.${name} from ${filePath}`);
  }
}

(async () => {
  await fs.mkdir(OUT_DIR, { recursive: true });
  await fs.mkdir(FRAMES_DIR, { recursive: true });

  const { kind, data, ids, source } = await loadTrials();
  console.log(`[recorder] using ${source}`);
  console.log(`[recorder] Trials (${ids.length}): ${ids.join(", ")}`);

  // const CHROME_PROFILE = path.join(REPO_ROOT, ".tmp-chrome-profile"); // any temp folder

  const browser = await puppeteer.launch({
    headless: "new",
    // args: [
    //   "--allow-file-access-from-files",   // let file:// pages read file:// images
    //   "--disable-web-security",           // relaxes CORS/same-origin (only in this temp profile)
    //   `--user-data-dir=${CHROME_PROFILE}` // required when disabling web security
    // ],
    defaultViewport: { width: 1200, height: 400, deviceScaleFactor: DPR }
  });


  try {
    for (const trial of ids) {
      console.log(`\n== ${trial} ==`);
      const page = await browser.newPage();

      // Page logs for debugging
      // page.on("console", msg => {
      //   const text = msg.text();
      //   if (msg.type() === "info" && text.includes("Noise was added to a canvas readback")) {
      //     return;
      //   }
      //   console.log(`[page ${trial}] ${msg.type()}: ${text}`);
      // });
      // page.on("pageerror", err => console.error(`[page ${trial}] pageerror:`, err));

      // Ensure DPR is set before any page scripts run
      await page.evaluateOnNewDocument((dpr) => {
        try {
          Object.defineProperty(window, "devicePixelRatio", {
            get: () => dpr,
            configurable: true
          });
          const w = dpr;
          const override = (obj, prop, val) =>
            Object.defineProperty(obj, prop, { get: () => val, configurable: true });
          override(window, "devicePixelRatio", dpr);
          override(screen, "pixelDepth", Math.round(24 * dpr));
          override(screen, "colorDepth", 24);
        } catch { }
      }, DPR);

      await page.setRequestInterception(true);
      page.on("request", async (req) => {
        const url = req.url();
        if (url.startsWith("file:") && /\/images\/[^/]+\.png$/i.test(url)) {
          try {
            // Map the file URL back to disk and read it
            const filePath = url.replace("file://", "");
            const buf = await fs.readFile(filePath);
            // Respond with the raw bytes and permissive headers
            await req.respond({
              status: 200,
              headers: {
                "Content-Type": "image/png",
                "Access-Control-Allow-Origin": "*",
                "Cache-Control": "no-cache"
              },
              body: buf
            });
            return;
          } catch (e) {
            console.error("[intercept] failed to serve", url, e);
          }
        }
        req.continue();
      });

      // Also set the viewport DPR (Puppeteer uses this for rasterization)
      await page.setViewport({ width: 1200, height: 400, deviceScaleFactor: DPR });

      // Load minimal export shell
      await page.goto(`file://${EXPORT_HTML}`, { waitUntil: "domcontentloaded" });

      // Tell the page/adapter how big to render
      await page.evaluate((cfg) => { window.EXPORT_CONFIG = cfg; }, { maxWidth: MAX_W, laneHeight: LANE_H });

      // Provide trials to the page
      await page.evaluate((payload) => {
        if (payload.kind === "array") window.TRIALS = payload.data;
        else window.TRIAL_DATA = payload.data;
      }, { kind, data });

      // Ensure globals from your files
      await ensureGlobalFromFile(page, PATH_RENDERER, "GridWorldRenderer", ["GridWorldRenderer"]);
      await ensureGlobalFromFile(page, PATH_GENERATOR, "TrialGenerator", ["TrialGenerator"]);

      // Inject the adapter (expects globals to exist)
      await page.addScriptTag({ path: PATH_ADAPTER });

      // Bootstrap after everything is in place
      const ok = await page.evaluate((trialId, fps) => {
        return typeof window.__bootstrap === "function" && window.__bootstrap(trialId, fps);
      }, trial, FPS);
      if (!ok) throw new Error("Bootstrap failed (no env). Check page logs.");

      // Record frames
      const canvas = await page.$("#c");
      if (!canvas) throw new Error("Canvas #c not found in export.html");

      const trialFramesDir = path.join(FRAMES_DIR, trial);
      await fs.rm(trialFramesDir, { recursive: true, force: true });
      await fs.mkdir(trialFramesDir, { recursive: true });

      const maxFrames = Math.ceil(MAX_S * FPS);

      // Wait until the first paint actually happened
      await waitForFirstPaint(page, "#c");

      // Capture initial frame before any updates
      let frameCounter = 0;
      const out0 = path.join(trialFramesDir, `${String(frameCounter++).padStart(5, "0")}.png`);
      await dumpCanvasPNG(page, "#c", out0);

      // Now advance the sim one step at a time, capturing after each step
      let done = false;
      let simFrame = 0;
      while (!done && simFrame < maxFrames) {
        const res = await page.evaluate(idx => window.__exportStep(idx), simFrame);
        done = !!(res && res.done);

        const outPath = path.join(trialFramesDir, `${String(frameCounter++).padStart(5, "0")}.png`);
        await dumpCanvasPNG(page, "#c", outPath);

        simFrame += 1;
      }

      await page.close();

      // Build GIF
      const outGif = path.join(OUT_DIR, `${trial}.gif`);
      await paletteAndGif(trialFramesDir, outGif);
      console.log(`[recorder] Wrote ${outGif}`);
    }
  } finally {
    await browser.close();
  }

  console.log("\nAll GIFs created successfully! Saved to docs/js/gifs/");
})().catch(err => { console.error(err); process.exit(1); });
