(function () {
  "use strict";

  const PHASE_LABELS = {
    intake: "Intake",
    plan: "Plan",
    design: "Design",
    approval: "Approval",
    code: "Code",
    test: "Test",
    sizing: "Sizing",
    output: "Output",
  };

  const PHASE_ORDER = [
    "intake",
    "plan",
    "design",
    "approval",
    "code",
    "test",
    "sizing",
    "output",
  ];

  const ARTIFACT_PHASE = {
    "session.json": "plan",
    "data-model.md": "design",
    "sizing_inputs.json": "design",
    "seed.py": "code",
    "mongodb_indexes.json": "code",
    "mongo_repository.py": "code",
    "test_mongo_repository.py": "test",
    "sizing-report.json": "sizing",
    "sizing-report.md": "sizing",
  };

  const PIPELINE_STEP_PHASE = {
    sizing: "sizing",
    repository_tests: "test",
    seed: "code",
    indexes: "code",
  };

  const PHASE_RANK = { fail: 3, active: 2, done: 1, pending: 0 };

  let livePhaseOverlay = {};
  let lastToolPhase = null;
  let lastDiskPhases = {};

  const params = new URLSearchParams(window.location.search);
  let currentCase = params.get("case") || localStorage.getItem("dashboardCase") || "_example";

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

  function getDiskActivePhase(diskPhases) {
    for (let i = 0; i < PHASE_ORDER.length; i++) {
      const key = PHASE_ORDER[i];
      if ((diskPhases && diskPhases[key]) === "active") {
        return key;
      }
    }
    return null;
  }

  function phaseFromToolTarget(target, diskPhases) {
    if (!target) return null;
    const diskActive = getDiskActivePhase(diskPhases);
    if (!diskActive) return null;

    if (target.indexOf("data-model.md") !== -1) {
      return diskActive === "plan" || diskActive === "design" ? diskActive : null;
    }
    if (target.indexOf("sizing_inputs.json") !== -1) {
      return diskActive === "design" ? "design" : null;
    }
    if (target.indexOf("session.json") !== -1) {
      return diskActive === "plan" ? "plan" : null;
    }
    for (const artifact in ARTIFACT_PHASE) {
      if (artifact === "data-model.md" || artifact === "sizing_inputs.json") {
        continue;
      }
      if (target.indexOf(artifact) !== -1) {
        const phase = ARTIFACT_PHASE[artifact];
        return phase === diskActive ? phase : null;
      }
    }
    return null;
  }

  function phaseFromToolName(toolName, diskPhases) {
    if (!toolName) return null;
    const diskActive = getDiskActivePhase(diskPhases);
    if (toolName.indexOf("createPlan") !== -1 && diskActive === "plan") {
      return "plan";
    }
    return null;
  }

  function mergePhases(diskPhases) {
    const diskActive = getDiskActivePhase(diskPhases);
    const merged = {};
    PHASE_ORDER.forEach(function (key) {
      const disk = (diskPhases && diskPhases[key]) || "pending";
      const live = livePhaseOverlay[key];
      if (!live) {
        merged[key] = disk;
        return;
      }
      if (live === "fail") {
        merged[key] = "fail";
        return;
      }
      if (live === "active" && diskActive && key !== diskActive) {
        merged[key] = disk;
        return;
      }
      const diskRank = PHASE_RANK[disk] || 0;
      const liveRank = PHASE_RANK[live] || 0;
      merged[key] = liveRank >= diskRank ? live : disk;
    });
    return merged;
  }

  function clearLivePhaseOverlay() {
    livePhaseOverlay = {};
    lastToolPhase = null;
  }

  function applyPhaseOverlay() {
    renderPhases(mergePhases(lastDiskPhases));
  }

  function setLivePhase(phase, status) {
    if (!phase || !PHASE_RANK[status]) return;
    if (status === "active") {
      const diskActive = getDiskActivePhase(lastDiskPhases);
      if (!diskActive || phase !== diskActive) return;
    }
    livePhaseOverlay[phase] = status;
    applyPhaseOverlay();
  }

  function renderPhases(phases) {
    els.phaseRail.innerHTML = "";
    PHASE_ORDER.forEach(function (key, i) {
      const status = (phases && phases[key]) || "pending";
      if (i > 0) {
        const prevKey = PHASE_ORDER[i - 1];
        const prevStatus = (phases && phases[prevKey]) || "pending";
        let connectorClass = "phase-connector";
        if (prevStatus === "done") {
          connectorClass += " done";
        } else if (prevStatus === "fail") {
          connectorClass += " fail";
        }
        const connector = document.createElement("div");
        connector.className = connectorClass;
        els.phaseRail.appendChild(connector);
      }
      const step = document.createElement("div");
      step.className = "phase-step " + status;
      step.innerHTML =
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
    lastDiskPhases = state.phases || {};
    renderPhases(mergePhases(lastDiskPhases));
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
      clearLivePhaseOverlay();
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

    if (type === "tool_activity") {
      const toolName = event.tool || event.name || "";
      const target = event.target || event.path || event.line || "";
      const phase =
        phaseFromToolName(toolName, lastDiskPhases) ||
        phaseFromToolTarget(target, lastDiskPhases);
      if (phase) {
        lastToolPhase = phase;
        setLivePhase(phase, "active");
      }
    } else if (type === "pipeline_step") {
      const st = event.status || "running";
      const phase = PIPELINE_STEP_PHASE[event.step || ""];
      if (phase) {
        lastToolPhase = phase;
        if (st === "running") {
          setLivePhase(phase, "active");
        } else if (st === "fail") {
          setLivePhase(phase, "fail");
        }
      }
    } else if (type === "run_finished") {
      if (event.status === "error" && lastToolPhase) {
        setLivePhase(lastToolPhase, "fail");
      } else {
        clearLivePhaseOverlay();
      }
    }

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

  function connectSSE() {
    const source = new EventSource("/events/stream");
    source.onopen = function () {
      els.connectionStatus.textContent = "Live";
      els.connectionStatus.className = "connection connected";
    };
    source.onmessage = function (msg) {
      try {
        const event = JSON.parse(msg.data);
        handleStreamEvent(event);
        if (
          event.type === "pipeline_finished" ||
          event.type === "approval_changed" ||
          event.type === "run_finished" ||
          event.type === "session_started"
        ) {
          fetchState();
        } else if (
          event.type === "tool_activity" ||
          event.type === "pipeline_step"
        ) {
          applyPhaseOverlay();
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
    try {
      const res = await fetch(
        "/api/artifact?case=" +
          encodeURIComponent(currentCase) +
          "&name=" +
          encodeURIComponent(name)
      );
      if (!res.ok) return;
      const data = await res.json();
      els.previewTitle.textContent = data.name;
      if (typeof marked !== "undefined") {
        els.previewContent.innerHTML = marked.parse(data.content || "");
      } else {
        els.previewContent.textContent = data.content || "";
      }
      els.previewDrawer.hidden = false;
    } catch (err) {
      /* ignore */
    }
  }

  function setCase(name) {
    currentCase = name.trim() || "_example";
    localStorage.setItem("dashboardCase", currentCase);
    els.caseInput.value = currentCase;
    const url = new URL(window.location.href);
    url.searchParams.set("case", currentCase);
    window.history.replaceState({}, "", url);
    clearLivePhaseOverlay();
    fetchState();
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

  fetchState();
  setInterval(fetchState, 2000);
  connectSSE();
})();
