// AeroOps frontend -- vanilla JS, no framework/build step. Fetches JSON
// from /query and renders results client-side. Chosen over HTMX here
// specifically because the endpoint returns JSON, not an HTML fragment --
// doing this in vanilla JS avoids content-negotiation gymnastics while
// still needing zero full page reloads for a query submit.
//
// Simplified to GraphRAG-only, single mode: the mode toggle and /compare
// view were removed when naive RAG and the agentic router were archived
// (see archive_naive_agentic/README.md at the repo root) -- there's no
// second backend left to compare against or route between.

(() => {
  "use strict";

  const ICON_WARNING = `
    <svg viewBox="0 0 24 24" fill="none" aria-hidden="true">
      <path d="M12 3 L22 20 L2 20 Z" fill="currentColor" opacity="0.15"
            stroke="currentColor" stroke-width="1.5" stroke-linejoin="round"/>
      <line x1="12" y1="9" x2="12" y2="14" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
      <circle cx="12" cy="17" r="1.1" fill="currentColor"/>
    </svg>`;

  // A signal pulsing node-to-node across a mini graph -- stands in for the
  // generic spinner during a wait, on-theme for a GraphRAG product instead
  // of a decoration with no relationship to what's happening underneath.
  const GRAPH_LOADER_SVG = `
    <svg class="graph-loader" viewBox="0 0 92 24" fill="none" aria-hidden="true">
      <line class="gl-line" x1="10" y1="12" x2="34" y2="12"/>
      <line class="gl-line" x1="34" y1="12" x2="58" y2="12"/>
      <line class="gl-line" x1="58" y1="12" x2="82" y2="12"/>
      <circle class="gl-node" cx="10" cy="12" r="4" style="animation-delay:0s"/>
      <circle class="gl-node" cx="34" cy="12" r="4" style="animation-delay:0.2s"/>
      <circle class="gl-node" cx="58" cy="12" r="4" style="animation-delay:0.4s"/>
      <circle class="gl-node" cx="82" cy="12" r="4" style="animation-delay:0.6s"/>
    </svg>`;

  // A representative subset of the sample questions from the Streamlit
  // demo's "Sample Queries" tab -- gives a first-time visitor something
  // concrete to try instead of a bare form with only a placeholder. Kept
  // short since these render as chips, not full sentences to read.
  // "What are the repair limits for nicks on a compressor blade?" was
  // deliberately dropped from this list -- the router sends procedural/
  // limits-style questions like that to GraphRAG, which doesn't answer it
  // well, while naive RAG does. Not something to spotlight as a suggested
  // example on the front page.
  const SAMPLE_QUESTIONS = [
    "What causes a compressor surge?",
    "What causes a tailpipe fire?",
    "How can a failing bearing trigger an oil filter bypass indication?",
    "What's the immediate crew action after a bird strike causes a bang and yaw?",
    "How does rotor/case interference reduce EGT margin?",
  ];

  const els = {
    form: document.getElementById("query-form"),
    input: document.getElementById("question"),
    submit: document.getElementById("query-submit"),
    statusArea: document.getElementById("status-area"),
    sampleChips: document.getElementById("sample-chips"),
    agenticView: document.getElementById("agentic-view"),
  };

  SAMPLE_QUESTIONS.forEach((q) => {
    const chip = document.createElement("button");
    chip.type = "button";
    chip.className = "sample-chip";
    chip.textContent = q;
    // Populates the input rather than auto-submitting -- a click here
    // shouldn't silently trigger a real LLM call the user didn't
    // explicitly ask for. They still press Ask/Compare themselves.
    chip.addEventListener("click", () => {
      els.input.value = q;
      els.input.focus();
    });
    els.sampleChips.appendChild(chip);
  });

  function el(tag, opts = {}, children = []) {
    const node = document.createElement(tag);
    if (opts.className) node.className = opts.className;
    if (opts.text !== undefined) node.textContent = opts.text;
    if (opts.html !== undefined) node.innerHTML = opts.html;
    if (opts.attrs) {
      for (const [k, v] of Object.entries(opts.attrs)) node.setAttribute(k, v);
    }
    for (const child of children) node.appendChild(child);
    return node;
  }

  function fmtTime(seconds) {
    if (seconds === null || seconds === undefined) return "—";
    return `${Number(seconds).toFixed(2)}s`;
  }

  // Real per-query cost, computed server-side from the actual token
  // counts and the actual OpenRouter provider that served the request
  // (main.py's estimated_cost_usd) -- not a flat estimate. Costs here run
  // well under a cent (~$0.0001/query), so toFixed(2) would round
  // everything to "$0.00" and read as broken; 4 significant figures after
  // the decimal keeps real variation between queries visible.
  function fmtCost(usd, provider) {
    if (usd === null || usd === undefined) return "—";
    const amount = `$${Number(usd).toFixed(6)}`;
    // Cost varies call-to-call because OpenRouter routes gpt-oss-20b to
    // a different backing provider each time (Parasail, Darkbloom, Groq,
    // etc, each at its own rate) -- naming which one actually served
    // this request is what explains that variation, not a fixed model
    // name that's the same on every query.
    return provider ? `${amount} · ${provider}` : amount;
  }

  function degradedBanner(fields) {
    const list = (fields && fields.length ? fields : []).join(", ") || "unknown";
    return el(
      "div",
      { className: "degraded-banner", attrs: { role: "status" } },
      [
        el("span", { html: ICON_WARNING }),
        el("div", {}, [
          el("strong", { text: "Degraded response" }),
          el("span", { text: `This answer came from a fallback path: ${list}` }),
        ]),
      ]
    );
  }

  function errorBanner(message) {
    return el("div", { className: "error-banner", attrs: { role: "alert" } }, [
      el("span", { html: ICON_WARNING }),
      el("span", { text: message }),
    ]);
  }

  function loadingRow(label) {
    return el("div", { className: "loading-row" }, [
      el("span", { html: GRAPH_LOADER_SVG }),
      el("span", { className: "loading-label", text: label }),
    ]);
  }

  // A static "Running..." spinner reads as broken once a request runs past
  // a few seconds -- this escalates the message instead of leaving it
  // frozen, so a genuinely slow (but still working) request doesn't look
  // hung. Returns a stop() to call once the request settles.
  function startLoadingSequence(target) {
    const row = loadingRow("Running query...");
    target.appendChild(row);
    const label = row.querySelector(".loading-label");

    const timers = [
      setTimeout(() => {
        label.textContent = "Still working — thanks for your patience.";
      }, 6000),
      setTimeout(() => {
        label.textContent =
          "This is taking longer than usual. Still trying — no need to resubmit.";
      }, 20000),
    ];

    return () => timers.forEach(clearTimeout);
  }

  // Answers come back with raw grounding tags inline -- "[D3_c02]" style
  // chunk-id citations from GraphRAG. Those tags exist for grounding
  // verification (RAGAS, the eval harness), not for an end user reading
  // the answer -- shown as-is they read as broken/leftover debug text.
  // This converts them into numbered,
  // clickable footnote markers tied to the Sources list already below the
  // answer, instead of either leaving the raw tags in or silently
  // deleting information about where a claim came from.
  const CITATION_RE = /\[(?:CITE:\s*([^\]]+)|((?:[A-Za-z0-9]+_c\d+)(?:\s*,\s*[A-Za-z0-9]+_c\d+)*))\]/g;

  function sourceKeyFor(src) {
    return src.chunk_id || `${src.source_file || "src"}|${src.page ?? "?"}`;
  }

  function sourceDomId(key) {
    return `source-${String(key).replace(/[^A-Za-z0-9_-]/g, "-")}`;
  }

  function parseCitations(text, sources) {
    const byChunkId = new Map();
    const byFileCite = new Map();
    (sources || []).forEach((src) => {
      if (src.chunk_id) byChunkId.set(src.chunk_id, src);
      if (src.source_file) byFileCite.set(`${src.source_file} p.${src.page}`, src);
    });

    const footnoteNumberByKey = new Map();
    function assignFootnote(src) {
      const key = sourceKeyFor(src);
      if (!footnoteNumberByKey.has(key)) {
        footnoteNumberByKey.set(key, footnoteNumberByKey.size + 1);
      }
      return footnoteNumberByKey.get(key);
    }

    const segments = [];
    let lastIndex = 0;
    let match;
    while ((match = CITATION_RE.exec(text)) !== null) {
      if (match.index > lastIndex) {
        segments.push({ type: "text", value: text.slice(lastIndex, match.index) });
      }
      const citeTarget = match[1];
      const chunkIds = match[2];
      const nums = [];
      if (citeTarget) {
        const src = byFileCite.get(citeTarget.trim());
        if (src) nums.push(assignFootnote(src));
      } else if (chunkIds) {
        chunkIds.split(",").forEach((id) => {
          const src = byChunkId.get(id.trim());
          if (src) nums.push(assignFootnote(src));
        });
      }
      if (nums.length) segments.push({ type: "citation", nums });
      lastIndex = CITATION_RE.lastIndex;
    }
    if (lastIndex < text.length) {
      segments.push({ type: "text", value: text.slice(lastIndex) });
    }

    const keyToNumber = new Map();
    footnoteNumberByKey.forEach((num, key) => keyToNumber.set(key, num));
    return { segments, keyToNumber };
  }

  function renderAnswerText(text, sources) {
    const { segments, keyToNumber } = parseCitations(text, sources || []);
    const p = document.createElement("p");
    p.className = "answer-text";
    segments.forEach((seg) => {
      if (seg.type === "text") {
        p.appendChild(document.createTextNode(seg.value));
        return;
      }
      seg.nums.forEach((num) => {
        const key = [...keyToNumber.entries()].find(([, n]) => n === num)?.[0];
        const sup = document.createElement("sup");
        const btn = document.createElement("button");
        btn.type = "button";
        btn.className = "citation-ref";
        btn.textContent = String(num);
        btn.setAttribute("aria-label", `Jump to source ${num}`);
        if (key) btn.dataset.sourceKey = key;
        sup.appendChild(btn);
        p.appendChild(sup);
      });
    });
    return { node: p, keyToNumber };
  }

  document.addEventListener("click", (e) => {
    const btn = e.target.closest(".citation-ref");
    if (!btn || !btn.dataset.sourceKey) return;
    const targetEl = document.getElementById(sourceDomId(btn.dataset.sourceKey));
    if (!targetEl) return;
    const details = targetEl.closest("details.sources");
    if (details) details.open = true;
    targetEl.scrollIntoView({ behavior: "smooth", block: "center" });
    targetEl.classList.add("source-highlight");
    setTimeout(() => targetEl.classList.remove("source-highlight"), 1500);
  });

  function renderAgenticResult(payload) {
    els.agenticView.innerHTML = "";

    // No backend badge -- there's only one backend now, GraphRAG, so the
    // answer reads as one system responding, full stop.
    const card = el("div", { className: "card" });

    if (payload.degraded) {
      card.appendChild(degradedBanner(payload.degraded_fields));
    }

    // Scope detection only (zero matched entities / failed retrieval); says
    // nothing about whether the answer is correct.
    if (payload.scope_flag === "LOW") {
      card.appendChild(
        el("div", { className: "scope-notice", attrs: { role: "status" } }, [
          el("strong", { text: "Possibly outside AeroOps' scope" }),
          el("span", { text: "No known engine entities were matched in this question, so the answer may not be grounded in the maintenance corpus." }),
        ])
      );
    }

    const { node: answerNode, keyToNumber } = renderAnswerText(payload.answer, payload.sources);
    card.appendChild(answerNode);

    const timingRow = el("div", { className: "timing-row" }, [
      el("div", { className: "timing-primary" }, [
        el("span", { className: "timing-value mono", text: fmtTime(payload.generation_time) }),
        el("span", { className: "timing-label", text: "generation time" }),
      ]),
      // Same prominence as generation time, not tucked in with retrieval
      // -- cost-per-query is the other half of "is this efficient", not
      // a minor footnote. Real value from main.py's estimated_cost_usd
      // (actual tokens x the actual OpenRouter provider's real rate),
      // not a flat guess.
      el("div", { className: "timing-primary" }, [
        el("span", { className: "timing-value mono", text: fmtCost(payload.estimated_cost_usd, payload.provider) }),
        el("span", { className: "timing-label", text: "cost" }),
      ]),
      el("div", { className: "timing-secondary" }, [
        el("span", { className: "timing-value mono", text: fmtTime(payload.retrieval_time) }),
        el("span", { className: "timing-label", text: "retrieval time" }),
      ]),
    ]);
    card.appendChild(timingRow);
    card.appendChild(renderSources(payload.sources, keyToNumber));

    els.agenticView.appendChild(card);
  }

  function renderSources(sources, keyToNumber) {
    if (!sources || !sources.length) {
      return el("p", { className: "meta-caption", text: "No sources returned." });
    }
    const details = document.createElement("details");
    details.className = "sources";
    const summary = document.createElement("summary");
    summary.textContent = `Sources (${sources.length})`;
    details.appendChild(summary);

    sources.forEach((src) => {
      const key = sourceKeyFor(src);
      const num = keyToNumber && keyToNumber.get(key);
      const chip = src.chunk_id || `${src.source_file || "source"} p.${src.page ?? "?"}`;
      const item = el("div", { className: "source-item" });
      item.id = sourceDomId(key);
      const titlePrefix = num ? `[${num}] ` : "";
      item.appendChild(
        el("div", { className: "source-title mono", text: `${titlePrefix}${chip} — ${src.title || "Untitled"}` })
      );
      if (src.quote) {
        const bq = document.createElement("blockquote");
        bq.textContent = src.quote;
        item.appendChild(bq);
      }
      details.appendChild(item);
    });
    return details;
  }

  async function submitQuery(question) {
    const target = els.agenticView;

    // Sample questions stay visible permanently (not hidden after first
    // use) -- they're a way to try more examples, not a one-shot onboarding
    // hint that should disappear once "used up".
    els.statusArea.innerHTML = "";
    target.innerHTML = "";
    const stopLoading = startLoadingSequence(target);
    els.submit.disabled = true;

    try {
      const resp = await fetch("/query", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question }),
      });

      const body = await resp.json().catch(() => null);

      if (!resp.ok) {
        const message = (body && body.detail) || `Request failed with status ${resp.status}`;
        target.innerHTML = "";
        els.statusArea.appendChild(errorBanner(message));
        return;
      }

      renderAgenticResult(body);
    } catch (err) {
      target.innerHTML = "";
      els.statusArea.appendChild(errorBanner(`Network error: ${err.message}`));
    } finally {
      stopLoading();
      els.submit.disabled = false;
    }
  }

  els.form.addEventListener("submit", (e) => {
    e.preventDefault();
    const question = els.input.value.trim();
    if (!question) return;
    submitQuery(question);
  });
})();
