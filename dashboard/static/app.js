(function () {
  "use strict";

  const PHASE_LABELS = {
    intake: "Intake",
    model: "Model",
    sizing_gate: "Sizing gate",
    approval: "Approval",
    generate: "Generate",
    tools: "Tools",
  };

  const PHASE_ORDER = [
    "intake",
    "model",
    "sizing_gate",
    "approval",
    "generate",
    "tools",
  ];

  const params = new URLSearchParams(window.location.search);
  let currentCase = params.get("case") || localStorage.getItem("dashboardCase") || "_example";
  let serverDefaultCase = null;

  const els = {
    caseInput: document.getElementById("case-input"),
    caseApply: document.getElementById("case-apply"),
    phaseRail: document.getElementById("phase-rail"),
    activityFeed: document.getElementById("activity-feed"),
    artifactList: document.getElementById("artifact-list"),
    modeBadge: document.getElementById("mode-badge"),
    approvalBadge: document.getElementById("approval-badge"),
    agentId: document.getElementById("agent-id"),
    connectionStatus: document.getElementById("connection-status"),
    sizingPanel: document.getElementById("sizing-panel"),
    diskValue: document.getElementById("disk-value"),
    ramValue: document.getElementById("ram-value"),
    previewDrawer: document.getElementById("preview-drawer"),
    previewTitle: document.getElementById("preview-title"),
    previewContent: document.getElementById("preview-content"),
    previewClose: document.getElementById("preview-close"),
  };

  els.caseInput.value = currentCase;

  // #region agent log
  function dbgLog(hypothesisId, location, message, data) {
    fetch("http://127.0.0.1:7302/ingest/9a292b43-83f4-426a-a07b-f0a3b161bd17", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-Debug-Session-Id": "36c7fc",
      },
      body: JSON.stringify({
        sessionId: "36c7fc",
        runId: "post-fix",
        hypothesisId: hypothesisId,
        location: location,
        message: message,
        data: data || {},
        timestamp: Date.now(),
      }),
    }).catch(function () {});
  }
  // #endregion

  function clearActivityFeed() {
    els.activityFeed.innerHTML = "";
    assistantBodyEl = null;
  }

  function eventMatchesCase(event) {
    if (!event.case) return true;
    return event.case === currentCase;
  }

  function resolveCaseName() {
    if (params.get("case")) {
      return params.get("case");
    }
    if (serverDefaultCase) {
      return serverDefaultCase;
    }
    return localStorage.getItem("dashboardCase") || "_example";
  }

  function formatBytes(n) {
    if (n == null) return "—";
    const gb = n / (1024 ** 3);
    if (gb >= 1) return gb.toFixed(2) + " GB";
    const mb = n / (1024 ** 2);
    return mb.toFixed(1) + " MB";
  }

  function formatTime(ts) {
    if (!ts) return "";
    const d = new Date(typeof ts === "number" ? ts * 1000 : ts);
    return d.toLocaleTimeString();
  }

  function renderPhases(phases) {
    els.phaseRail.innerHTML = "";
    PHASE_ORDER.forEach((key, i) => {
      const status = (phases && phases[key]) || "pending";
      const step = document.createElement("div");
      step.className = "phase-step " + status;
      step.innerHTML =
        (i > 0 ? '<div class="phase-connector"></div>' : "") +
        '<div class="phase-node">' +
        '<div class="phase-dot"></div>' +
        '<span class="phase-label">' + (PHASE_LABELS[key] || key) + "</span>" +
        "</div>";
      els.phaseRail.appendChild(step);
    });
  }

  function renderArtifacts(artifacts) {
    els.artifactList.innerHTML = "";
    (artifacts || []).forEach(function (a) {
      const li = document.createElement("li");
      li.className = "artifact-item " + (a.exists ? "exists" : "missing");
      const name = document.createElement("span");
      name.textContent = a.name;
      li.appendChild(name);
      const right = document.createElement("span");
      if (a.exists) {
        right.innerHTML =
          '<span class="artifact-status">ready</span>' +
          (a.previewable
            ? '<button type="button" class="artifact-preview-btn" data-name="' +
              a.name +
              '">preview</button>'
            : "");
      } else {
        right.innerHTML = '<span class="artifact-status">—</span>';
      }
      li.appendChild(right);
      els.artifactList.appendChild(li);
    });
    var previewBtns = els.artifactList.querySelectorAll(".artifact-preview-btn");
    // #region agent log
    dbgLog("B", "app.js:renderArtifacts", "artifacts rendered", {
      artifactCount: (artifacts || []).length,
      previewBtnCount: previewBtns.length,
      previewableReady: (artifacts || [])
        .filter(function (a) {
          return a.exists && a.previewable;
        })
        .map(function (a) {
          return a.name;
        }),
    });
    // #endregion
    previewBtns.forEach(function (btn) {
      btn.addEventListener("click", function () {
        openPreview(btn.dataset.name);
      });
    });
  }

  function renderState(state) {
    if (!state) return;
    els.modeBadge.textContent = state.mode || "plan";
    els.modeBadge.className = "badge badge-mode";
    const approval = state.approvalStatus || "missing";
    els.approvalBadge.textContent = approval;
    els.approvalBadge.className = "badge badge-approval " + approval;
    els.agentId.textContent = state.agentId ? "agent " + state.agentId : "—";
    renderPhases(state.phases);
    renderArtifacts(state.artifacts);
    if (state.atlas) {
      els.sizingPanel.hidden = false;
      els.diskValue.textContent = formatBytes(state.atlas.diskRequired);
      els.ramValue.textContent = formatBytes(state.atlas.ramRequired);
    } else {
      els.sizingPanel.hidden = true;
    }
  }

  async function fetchState() {
    try {
      const res = await fetch("/api/state?case=" + encodeURIComponent(currentCase));
      if (!res.ok) return;
      const state = await res.json();
      renderState(state);
    } catch (_) {
      /* ignore */
    }
  }

  // Append consecutive assistant_text events into one card (defensive if
  // the agent still emits token deltas; session.py normally buffers first).
  let assistantBodyEl = null;

  function appendAssistantText(event) {
    const text = event.text || "";
    if (!text) return;

    if (assistantBodyEl) {
      assistantBodyEl.textContent += text;
      els.activityFeed.scrollTop = els.activityFeed.scrollHeight;
      return;
    }

    const card = document.createElement("div");
    card.className = "event-card assistant";
    card.innerHTML =
      '<div class="event-meta">' +
      formatTime(event.ts) +
      " · assistant</div>" +
      '<div class="event-body assistant-body"></div>';
    assistantBodyEl = card.querySelector(".event-body");
    assistantBodyEl.textContent = text;
    els.activityFeed.appendChild(card);
    els.activityFeed.scrollTop = els.activityFeed.scrollHeight;
  }

  function handleStreamEvent(event) {
    const type = event.type || "event";
    if (type === "assistant_text") {
      appendAssistantText(event);
      return;
    }
    // Any non-text event closes the current assistant card.
    assistantBodyEl = null;
    appendEventCard(event);
  }

  function appendEventCard(event) {
    const card = document.createElement("div");
    const type = event.type || "event";
    let cardClass = "event-card";
    let meta = type;
    let body = "";

    if (type === "tool_activity") {
      cardClass += " tool";
      meta = "tool · " + (event.tool || event.name || "unknown");
      body = event.target || event.path || event.line || "";
    } else if (type === "pipeline_step") {
      const st = event.status || "running";
      cardClass += " pipeline " + st;
      meta = "pipeline · " + (event.step || "");
      body = event.detail || st;
    } else if (type === "run_started") {
      cardClass += " tool";
      meta = "run started";
      body =
        "run " +
        (event.run_id || event.runId || "?") +
        " · mode " +
        (event.mode || "?");
    } else if (type === "run_finished") {
      cardClass += " pipeline " + (event.status === "error" ? "fail" : "ok");
      meta = "run finished";
      body = event.status || "finished";
    } else if (type === "session_started") {
      cardClass += " tool";
      meta = "session";
      body =
        "case " +
        (event.case || currentCase) +
        (event.resumed ? " (resumed)" : " (new)");
      if (event.case === currentCase) {
        clearActivityFeed();
        fetchState();
      }
    } else if (type === "approval_changed") {
      cardClass += " pipeline ok";
      meta = "approval";
      body = "status → " + (event.status || "approved");
    } else if (type === "pipeline_finished") {
      cardClass += " pipeline ok";
      meta = "pipeline complete";
      body = event.report_path || event.reportPath || "";
    } else {
      body = JSON.stringify(event, null, 0).slice(0, 200);
    }

    card.className = cardClass;
    card.innerHTML =
      '<div class="event-meta">' +
      formatTime(event.ts) +
      " · " +
      meta +
      "</div>" +
      '<div class="event-body">' +
      escapeHtml(body) +
      "</div>";
    els.activityFeed.appendChild(card);
    els.activityFeed.scrollTop = els.activityFeed.scrollHeight;
  }

  function escapeHtml(s) {
    const d = document.createElement("div");
    d.textContent = s;
    return d.innerHTML;
  }

  let eventSource = null;

  function connectSSE() {
    if (eventSource) {
      eventSource.close();
      eventSource = null;
    }
    const source = new EventSource(
      "/events/stream?case=" + encodeURIComponent(currentCase)
    );
    eventSource = source;
    source.onopen = function () {
      els.connectionStatus.textContent = "Live";
      els.connectionStatus.className = "connection connected";
    };
    source.onmessage = function (msg) {
      try {
        const event = JSON.parse(msg.data);
        if (!eventMatchesCase(event)) return;
        handleStreamEvent(event);
        if (
          event.type === "pipeline_finished" ||
          event.type === "approval_changed" ||
          event.type === "run_finished"
        ) {
          fetchState();
        }
      } catch (_) {
        /* ignore */
      }
    };
    source.onerror = function () {
      els.connectionStatus.textContent = "Reconnecting";
      els.connectionStatus.className = "connection disconnected";
    };
  }

  async function openPreview(name) {
    // #region agent log
    dbgLog("C", "app.js:openPreview:entry", "openPreview called", {
      name: name,
      currentCase: currentCase,
      markedDefined: typeof marked !== "undefined",
    });
    // #endregion
    try {
      const res = await fetch(
        "/api/artifact?case=" +
          encodeURIComponent(currentCase) +
          "&name=" +
          encodeURIComponent(name)
      );
      // #region agent log
      dbgLog("C", "app.js:openPreview:response", "artifact fetch result", {
        name: name,
        ok: res.ok,
        status: res.status,
      });
      // #endregion
      if (!res.ok) return;
      const data = await res.json();
      els.previewTitle.textContent = data.name;
      if (typeof marked !== "undefined") {
        els.previewContent.innerHTML = marked.parse(data.content || "");
      } else {
        els.previewContent.textContent = data.content || "";
      }
      els.previewDrawer.hidden = false;
      // #region agent log
      dbgLog("D", "app.js:openPreview:rendered", "preview content applied", {
        name: data.name,
        contentLen: (data.content || "").length,
        htmlLen: els.previewContent.innerHTML.length,
        drawerHidden: els.previewDrawer.hidden,
      });
      // #endregion
    } catch (err) {
      // #region agent log
      dbgLog("C", "app.js:openPreview:error", "openPreview failed", {
        name: name,
        error: String(err && err.message ? err.message : err),
      });
      // #endregion
    }
  }

  function setCase(name) {
    currentCase = name.trim() || "_example";
    localStorage.setItem("dashboardCase", currentCase);
    els.caseInput.value = currentCase;
    const url = new URL(window.location.href);
    url.searchParams.set("case", currentCase);
    window.history.replaceState({}, "", url);
    clearActivityFeed();
    connectSSE();
    fetchState();
  }

  async function bootstrap() {
    try {
      const res = await fetch("/api/config");
      if (res.ok) {
        const config = await res.json();
        serverDefaultCase = config.defaultCase || null;
      }
    } catch (_) {
      /* ignore */
    }
    currentCase = resolveCaseName();
    els.caseInput.value = currentCase;
    localStorage.setItem("dashboardCase", currentCase);
    renderPhases({});
    fetchState();
    setInterval(fetchState, 2000);
    connectSSE();
  }

  els.caseApply.addEventListener("click", function () {
    setCase(els.caseInput.value);
  });
  els.caseInput.addEventListener("keydown", function (e) {
    if (e.key === "Enter") setCase(els.caseInput.value);
  });
  els.previewClose.addEventListener("click", function () {
    els.previewDrawer.hidden = true;
  });

  bootstrap();
})();
