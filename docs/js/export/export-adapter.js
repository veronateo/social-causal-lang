// docs/js/export/export-adapter.js

(function () {
  function getLexical(name) {
    try { return (0, eval)(name); } catch { return undefined; }
  }
  function resolveCtor(name) {
    const out = [];
    const w = window[name];
    if (w) out.push(w);
    const lex = getLexical(name);
    if (lex) out.push(lex);

    if (w && typeof w === "object") {
      if (typeof w.default === "function") out.push(w.default);
      if (typeof w[name] === "function") out.push(w[name]);
    }
    if (lex && typeof lex === "object") {
      if (typeof lex.default === "function") out.push(lex.default);
      if (typeof lex[name] === "function") out.push(lex[name]);
    }
    for (const c of out) if (typeof c === "function") return c;
    return undefined;
  }

  function errLog(prefix, e) {
    const msg = (e && (e.stack || e.message)) ? (e.stack || e.message) : String(e);
    console.error(prefix, msg);
  }

  function pickTrial(trialId) {
    if (Array.isArray(window.TRIALS)) {
      const t = window.TRIALS.find(t =>
        t.trial_id === trialId || t.id === trialId || t.name === trialId
      );
      if (t) return t;
    }
    if (window.TRIAL_DATA && window.TRIAL_DATA[trialId]) return window.TRIAL_DATA[trialId];
    return null;
  }

  // Map JSON --> TrialGenerator.generateTrial() params 
  function mapJsonToGenerateParams(json) {
    return {
      id: json.trial_id || json.id || json.name,
      label: String(json.trial_id || json.id || json.name || ""),
      description: json.description || "",
      initialDirectionGoal: json.farmer_initial_direction_goal,  // "apple" | "banana"
      wizardAction: json.wizard_action,                   // "place_rock" | "remove_rock" | "nothing"
      rockStartsPresent: !!json.rock_initial,                   // boolean
      finalOutcome: json.final_outcome,                   // "apple" | "banana"
      instructionOnly: false
    };
  }

  // Build scene with TrialGenerator
  function buildSceneWithGenerator(jsonDef) {
    const GenCtor = resolveCtor("TrialGenerator");
    if (!GenCtor) {
      console.error("[adapter] TrialGenerator not available (did trial-generator.js load?).");
      return null;
    }
    try {
      const gen = new GenCtor();                  // uses defaults from file
      const params = mapJsonToGenerateParams(jsonDef);
      const scene = gen.generateTrial(params);      // { id, label, description, outcome, frames }
      if (!scene || !Array.isArray(scene.frames) || scene.frames.length === 0) {
        console.error("[adapter] TrialGenerator returned no frames.");
        return null;
      }
      console.log("[adapter] TrialGenerator path: gen.generateTrial(params) ✓");
      return scene;
    } catch (e) {
      errLog("[adapter] TrialGenerator.generateTrial threw:", e);
      return null;
    }
  }

  function imgReady(img) { return !!(img && img.complete && img.naturalWidth > 0); }
  function waitRendererAssets(renderer, timeout = 5000) {
    const need = ["farmer", "wizard", "wizard-wand", "lightning", "apple", "banana", "rock", "thought"];
    const start = performance.now();
    return new Promise(resolve => {
      (function tick() {
        const ok = need.every(k => imgReady(renderer?.images?.get?.(k)));
        if (ok || (performance.now() - start > timeout)) return resolve(ok);
        requestAnimationFrame(tick);
      })();
    });
  }


  // Renderer selection
  function makeFallbackRenderer(canvas) {
    const ctx = canvas.getContext("2d");
    const W = canvas.width, H = canvas.height;
    const pad = 40, laneW = W - pad * 2;
    const toX = (cell, max = 18) => Math.round(pad + (cell / max) * laneW); // default applePos=18
    return {
      renderFrame(scene, idx) {
        const f = scene.frames[Math.min(idx, scene.frames.length - 1)] || {};
        const ents = f.entities || [];
        ctx.fillStyle = "#fff"; ctx.fillRect(0, 0, W, H);
        // lane
        ctx.strokeStyle = "#e0e0e0"; ctx.lineWidth = 6;
        ctx.beginPath(); ctx.moveTo(toX(0), H / 2); ctx.lineTo(toX(18), H / 2); ctx.stroke();
        // entities
        for (const e of ents) {
          const x = toX(e.position || 0);
          if (e.type === "banana") { ctx.fillStyle = "#ffcc00"; ctx.beginPath(); ctx.arc(x, H / 2, 12, 0, Math.PI * 2); ctx.fill(); }
          else if (e.type === "apple") { ctx.fillStyle = "#cc0000"; ctx.beginPath(); ctx.arc(x, H / 2, 12, 0, Math.PI * 2); ctx.fill(); }
          else if (e.type === "rock") { ctx.fillStyle = "#7f8c8d"; ctx.fillRect(x - 10, H / 2 - 10, 20, 20); }
          else if (e.type === "wizard") { ctx.fillStyle = "#3498db"; ctx.beginPath(); ctx.arc(x, H / 2, 14, 0, Math.PI * 2); ctx.fill(); }
          else if (e.type === "farmer") { ctx.fillStyle = "#2ecc71"; ctx.beginPath(); ctx.arc(x, H / 2, 16, 0, Math.PI * 2); ctx.fill(); }
        }
      }
    };
  }

  function pickRenderer(canvas) {
    const RendererCtor = (function () {
      try { return (window.GridWorldRenderer) || (0, eval)("GridWorldRenderer"); } catch { return undefined; }
    })();

    if (typeof RendererCtor === "function") {
      try {
        const cfg = window.EXPORT_CONFIG || {};
        const r = new RendererCtor(canvas, {
          // do NOT change maxWidth / borders / laneLength => preserves ~61px cell width
          laneHeight: typeof cfg.laneHeight === "number" ? cfg.laneHeight : undefined,
          animationSpeed: 500
        });
        if (
          r &&
          (typeof r.renderFrame === "function" ||
            typeof r.drawFrame === "function" ||
            typeof r.draw === "function" ||
            typeof r.render === "function")
        ) return r;
      } catch (e) {
        console.error("[adapter] GridWorldRenderer ctor failed:", e.stack || e);
      }
    }

    console.warn("[adapter] GridWorldRenderer not found; using fallback renderer.");
    return makeFallbackRenderer(canvas);
  }


  // Adapter API
  window.__adapter = {
    create: async ({ trialId, canvas }) => {
      const renderer = pickRenderer(canvas);
      const hasTrials = Array.isArray(window.TRIALS);
      const hasMap = !!(window.TRIAL_DATA && typeof window.TRIAL_DATA === "object");
      const hasGen = !!resolveCtor("TrialGenerator");
      const hasRend = !!resolveCtor("GridWorldRenderer");
      console.log(`[adapter] presence: TRIALS=${hasTrials}, TRIAL_DATA=${hasMap}, TrialGenerator=${hasGen}, Renderer=${hasRend}`);

      const jsonDef = pickTrial(trialId);
      if (!jsonDef) {
        console.error(`[adapter] No trial JSON for ${trialId} in TRIALS/TRIAL_DATA`);
        return null;
      }

      // Use generator exactly
      let scene = buildSceneWithGenerator(jsonDef);
      if (!scene) return null;

      // Deterministic 1-frame-per-step player
      const sim = {
        idx: 0,
        reset() { this.idx = 0; },
        update() { if (this.idx < scene.frames.length - 1) this.idx += 1; },
        isDone() { return this.idx >= scene.frames.length - 1; }
      };
      sim.reset();

      // First paint initialization
      await waitRendererAssets(renderer);
      try {
        const ctx = canvas.getContext("2d");
        if (typeof renderer.renderFrame === "function") renderer.renderFrame(scene, 0, ctx);
        else if (typeof renderer.drawFrame === "function") renderer.drawFrame(scene, 0, ctx);
        else if (typeof renderer.draw === "function") renderer.draw(scene, 0, ctx);
        else if (typeof renderer.render === "function") renderer.render(scene, 0, ctx);
        window.__initialPaintDone = true;
      } catch { }

      return {
        update() { sim.update(); },
        render(ctx) {
          if (typeof renderer.renderFrame === "function") return renderer.renderFrame(scene, sim.idx, ctx);
          if (typeof renderer.drawFrame === "function") return renderer.drawFrame(scene, sim.idx, ctx);
          if (typeof renderer.draw === "function") return renderer.draw(scene, sim.idx, ctx);
          if (typeof renderer.render === "function") return renderer.render(scene, sim.idx, ctx);
        },
        isDone() { return sim.isDone(); }
      };
    }
  };
})();
