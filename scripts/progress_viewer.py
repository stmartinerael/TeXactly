#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse


ROOT = Path(__file__).resolve().parent.parent
STATE_PATH = ROOT / "project-tracker.json"


HTML = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>TeXactly Progress Viewer</title>
  <style>
    :root {
      --bg: #f4efe5;
      --panel: #fffaf2;
      --panel-strong: #f7f0e4;
      --ink: #1d1b18;
      --muted: #6a6258;
      --line: #d7ccb9;
      --accent: #0f766e;
      --accent-strong: #115e59;
      --warn: #b45309;
      --danger: #b42318;
      --shadow: 0 18px 45px rgba(70, 52, 27, 0.08);
      --radius: 18px;
      --mono: "SFMono-Regular", Consolas, "Liberation Mono", monospace;
      --sans: "Segoe UI", "Avenir Next", "Helvetica Neue", sans-serif;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      font-family: var(--sans);
      color: var(--ink);
      background:
        radial-gradient(circle at top left, rgba(15,118,110,0.12), transparent 28%),
        radial-gradient(circle at top right, rgba(180,83,9,0.12), transparent 24%),
        linear-gradient(180deg, #fbf7f0 0%, var(--bg) 100%);
    }
    button, input, select, textarea {
      font: inherit;
    }
    .shell {
      max-width: 1440px;
      margin: 0 auto;
      padding: 24px;
    }
    .topbar {
      position: sticky;
      top: 0;
      z-index: 10;
      display: flex;
      gap: 12px;
      align-items: center;
      justify-content: space-between;
      padding: 16px 20px;
      margin-bottom: 24px;
      background: rgba(255, 250, 242, 0.9);
      backdrop-filter: blur(14px);
      border: 1px solid rgba(215, 204, 185, 0.8);
      border-radius: var(--radius);
      box-shadow: var(--shadow);
    }
    .brand h1 {
      margin: 0;
      font-size: 1.3rem;
    }
    .brand p {
      margin: 4px 0 0;
      color: var(--muted);
    }
    .toolbar {
      display: flex;
      gap: 10px;
      align-items: center;
      flex-wrap: wrap;
    }
    .toolbar button {
      border: 0;
      border-radius: 999px;
      padding: 10px 16px;
      cursor: pointer;
      transition: transform 0.16s ease, background 0.16s ease;
    }
    .toolbar button:hover {
      transform: translateY(-1px);
    }
    .primary {
      background: var(--accent);
      color: white;
    }
    .ghost {
      background: var(--panel-strong);
      color: var(--ink);
      border: 1px solid var(--line);
    }
    .status {
      color: var(--muted);
      font-size: 0.95rem;
      min-width: 170px;
      text-align: right;
    }
    .hero {
      display: grid;
      grid-template-columns: 2fr 1fr;
      gap: 18px;
      margin-bottom: 24px;
    }
    .panel {
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: var(--radius);
      box-shadow: var(--shadow);
      overflow: hidden;
    }
    .panel-inner {
      padding: 20px;
    }
    .panel h2, .panel h3 {
      margin: 0 0 12px;
    }
    .lede {
      font-size: 1.05rem;
      line-height: 1.55;
      margin: 0 0 16px;
    }
    .source-note {
      background: var(--panel-strong);
      border-radius: 14px;
      padding: 14px;
      color: var(--muted);
      line-height: 1.45;
    }
    .stats {
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 12px;
    }
    .stat {
      padding: 16px;
      border-radius: 14px;
      background: var(--panel-strong);
      border: 1px solid rgba(215, 204, 185, 0.8);
    }
    .stat strong {
      display: block;
      font-size: 1.5rem;
      margin-bottom: 4px;
    }
    .grid {
      display: grid;
      grid-template-columns: 1.1fr 1fr;
      gap: 18px;
      align-items: start;
    }
    .stack {
      display: grid;
      gap: 18px;
    }
    .subtle {
      color: var(--muted);
    }
    .artifact-list, .error-list, .action-list, .prompt-list, .direction-list {
      display: grid;
      gap: 14px;
    }
    .artifact-item, .error-card, .action-card, .prompt-card, .direction-card {
      border: 1px solid rgba(215, 204, 185, 0.9);
      border-radius: 14px;
      background: #fffdf8;
      padding: 16px;
    }
    .direction-status-proposed { color: var(--accent-strong); }
    .direction-status-active { color: var(--warn); }
    .direction-status-rejected { color: var(--danger); }
    .direction-status-done { color: var(--muted); }
    .artifact-item {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 12px;
    }
    .artifact-meta {
      display: grid;
      gap: 3px;
    }
    .pill {
      display: inline-flex;
      align-items: center;
      gap: 6px;
      padding: 4px 10px;
      border-radius: 999px;
      font-size: 0.8rem;
      text-transform: uppercase;
      letter-spacing: 0.06em;
      background: var(--panel-strong);
      color: var(--muted);
    }
    .severity-blocker { color: var(--danger); }
    .severity-high { color: var(--warn); }
    .severity-medium { color: var(--accent-strong); }
    .card-head {
      display: flex;
      justify-content: space-between;
      gap: 12px;
      align-items: start;
      margin-bottom: 12px;
    }
    .card-head h3 {
      margin: 0;
      font-size: 1.02rem;
    }
    .meta-row {
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      margin-bottom: 10px;
    }
    .evidence, .tags, .refs {
      margin: 12px 0 0;
      padding-left: 18px;
      color: var(--muted);
    }
    .refs li, .evidence li, .tags li {
      margin-bottom: 6px;
    }
    .field {
      display: grid;
      gap: 6px;
      margin-top: 12px;
    }
    .field label {
      font-size: 0.9rem;
      color: var(--muted);
    }
    textarea, input[type="text"], select {
      width: 100%;
      border: 1px solid var(--line);
      border-radius: 12px;
      background: white;
      padding: 10px 12px;
      min-height: 44px;
    }
    textarea {
      resize: vertical;
      min-height: 94px;
      line-height: 1.45;
    }
    .split {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 12px;
    }
    .code-view {
      min-height: 440px;
      background: #181714;
      color: #f8f3eb;
      border-radius: 16px;
      padding: 16px;
      overflow: auto;
      font-family: var(--mono);
      font-size: 0.9rem;
      line-height: 1.45;
      white-space: pre-wrap;
      border: 1px solid rgba(255, 255, 255, 0.08);
    }
    .muted-box {
      border: 1px dashed var(--line);
      border-radius: 14px;
      padding: 16px;
      color: var(--muted);
      background: rgba(247, 240, 228, 0.55);
    }
    .section-title {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 12px;
      margin-bottom: 14px;
    }
    .section-title p {
      margin: 0;
      color: var(--muted);
      max-width: 60ch;
    }
    .tiny {
      font-size: 0.84rem;
      color: var(--muted);
    }
    @media (max-width: 1080px) {
      .hero, .grid {
        grid-template-columns: 1fr;
      }
    }
    @media (max-width: 700px) {
      .shell { padding: 14px; }
      .topbar { padding: 14px; }
      .stats, .split { grid-template-columns: 1fr; }
      .status { text-align: left; min-width: 0; }
      .toolbar { width: 100%; justify-content: flex-start; }
    }
  </style>
</head>
<body>
  <div class="shell">
    <div class="topbar">
      <div class="brand">
        <h1>TeXactly Progress Viewer</h1>
        <p id="brand-subtitle">Loading tracker state…</p>
      </div>
      <div class="toolbar">
        <button class="ghost" id="reload-btn">Reload</button>
        <button class="ghost" id="add-prompt-btn">Add Prompt</button>
        <button class="primary" id="save-btn">Save Tracker</button>
        <div class="status" id="save-status">Not loaded yet</div>
      </div>
    </div>

    <div class="hero">
      <section class="panel">
        <div class="panel-inner">
          <h2 id="project-name"></h2>
          <p class="lede" id="project-goal"></p>
          <div class="source-note" id="source-note"></div>
        </div>
      </section>
      <section class="panel">
        <div class="panel-inner">
          <h2>Project Snapshot</h2>
          <div class="stats" id="stats"></div>
        </div>
      </section>
    </div>

    <div class="grid">
      <div class="stack">
        <section class="panel">
          <div class="panel-inner">
            <div class="section-title">
              <div>
                <h2>Action Items</h2>
                <p>Track the current work, write comments on what to do next, and keep prompt-ready notes in one place.</p>
              </div>
            </div>
            <div class="action-list" id="action-list"></div>
          </div>
        </section>

        <section class="panel">
          <div class="panel-inner">
            <div class="section-title">
              <div>
                <h2>Directions</h2>
                <p>Strategic options and decisions. Track which paths are under consideration and which have been chosen.</p>
              </div>
              <button class="ghost" id="add-direction-btn">Add Direction</button>
            </div>
            <div class="direction-list" id="direction-list"></div>
          </div>
        </section>

        <section class="panel">
          <div class="panel-inner">
            <div class="section-title">
              <div>
                <h2>Prompt Sketches</h2>
                <p>Use these as reusable launch points for deeper investigation or implementation prompts.</p>
              </div>
            </div>
            <div class="prompt-list" id="prompt-list"></div>
          </div>
        </section>

        <section class="panel">
          <div class="panel-inner">
            <div class="section-title">
              <div>
                <h2>Project Notes</h2>
                <p>These notes live in the tracker JSON and are meant for decisions, context, and active thinking.</p>
              </div>
            </div>
            <div class="field">
              <label for="project-notes">Shared project notes</label>
              <textarea id="project-notes"></textarea>
            </div>
            <div class="field">
              <label for="session-notes">Session notes</label>
              <textarea id="session-notes"></textarea>
            </div>
          </div>
        </section>
      </div>

      <div class="stack">
        <section class="panel">
          <div class="panel-inner">
            <div class="section-title">
              <div>
                <h2>Known Errors</h2>
                <p>The tracker state is authoritative for project-level error triage. Update comments and hypotheses as we learn more.</p>
              </div>
            </div>
            <div class="error-list" id="error-list"></div>
          </div>
        </section>

        <section class="panel">
          <div class="panel-inner">
            <div class="section-title">
              <div>
                <h2>Artifact Browser</h2>
                <p>Artifact contents are read live from disk so the app does not duplicate them.</p>
              </div>
            </div>
            <div class="artifact-list" id="artifact-list"></div>
            <div style="margin-top:16px;">
              <div class="tiny" id="artifact-path-label">Select an artifact to preview it here.</div>
              <pre class="code-view" id="artifact-viewer">Artifact preview will appear here.</pre>
            </div>
          </div>
        </section>
      </div>
    </div>
  </div>

  <script>
    const state = { data: null, dirty: false, currentArtifactPath: null };

    const saveStatus = document.getElementById("save-status");
    const setStatus = (message, kind = "info") => {
      saveStatus.textContent = message;
      saveStatus.style.color = kind === "error" ? "var(--danger)" : kind === "ok" ? "var(--accent-strong)" : "var(--muted)";
    };

    const markDirty = () => {
      state.dirty = true;
      setStatus("Unsaved changes", "error");
    };

    const readText = (value) => value == null ? "" : String(value);

    async function fetchJson(url, options) {
      const response = await fetch(url, options);
      if (!response.ok) {
        const text = await response.text();
        throw new Error(text || `Request failed: ${response.status}`);
      }
      return response.json();
    }

    function renderStats(data) {
      const stats = [
        { label: "Known errors", value: data.known_errors.length },
        { label: "Active items", value: data.action_items.filter(item => item.status === "active").length },
        { label: "Prompt sketches", value: data.prompt_sketches.length },
        { label: "Directions", value: (data.directions || []).length }
      ];
      document.getElementById("stats").innerHTML = stats.map(stat => `
        <div class="stat">
          <strong>${stat.value}</strong>
          <span>${stat.label}</span>
        </div>
      `).join("");
    }

    function renderHeader(data) {
      document.getElementById("project-name").textContent = `${data.project.name}`;
      document.getElementById("brand-subtitle").textContent = data.project.tagline;
      document.getElementById("project-goal").textContent = data.project.current_goal;
      document.getElementById("source-note").textContent = data.project.source_of_truth_note;
    }

    function renderArtifacts(data) {
      const list = document.getElementById("artifact-list");
      list.innerHTML = data.artifacts.map(artifact => `
        <div class="artifact-item">
          <div class="artifact-meta">
            <strong>${artifact.label}</strong>
            <span class="tiny">${artifact.path}</span>
          </div>
          <div style="display:flex; gap:8px; align-items:center;">
            <span class="pill">${artifact.kind}</span>
            <button class="ghost" data-artifact-path="${artifact.path}">Open</button>
          </div>
        </div>
      `).join("");
      list.querySelectorAll("button[data-artifact-path]").forEach(button => {
        button.addEventListener("click", () => loadArtifact(button.dataset.artifactPath));
      });
    }

    function renderKnownErrors(data) {
      const list = document.getElementById("error-list");
      list.innerHTML = "";
      data.known_errors.forEach((error, index) => {
        const card = document.createElement("div");
        card.className = "error-card";
        card.innerHTML = `
          <div class="card-head">
            <div>
              <h3>${error.id} · ${error.title}</h3>
              <div class="meta-row">
                <span class="pill severity-${error.severity}">${error.severity}</span>
                <span class="pill">${error.category}</span>
                <span class="pill">count ${error.count}</span>
                <span class="pill">${error.status}</span>
              </div>
            </div>
          </div>
          <p class="subtle">${readText(error.hypothesis)}</p>
          <div class="field">
            <label>Evidence</label>
            <ul class="evidence">${error.evidence.map(item => `<li><code>${item}</code></li>`).join("")}</ul>
          </div>
          <div class="field">
            <label>Next questions</label>
            <ul class="refs">${error.next_questions.map(item => `<li>${item}</li>`).join("")}</ul>
          </div>
          <div class="field">
            <label for="error-comments-${index}">Comments</label>
            <textarea id="error-comments-${index}" data-error-index="${index}">${readText(error.comments)}</textarea>
          </div>
        `;
        list.appendChild(card);
      });
      list.querySelectorAll("textarea[data-error-index]").forEach(textarea => {
        textarea.addEventListener("input", (event) => {
          const index = Number(event.target.dataset.errorIndex);
          state.data.known_errors[index].comments = event.target.value;
          markDirty();
        });
      });
    }

    function renderActionItems(data) {
      const list = document.getElementById("action-list");
      list.innerHTML = "";
      data.action_items.forEach((item, index) => {
        const card = document.createElement("div");
        card.className = "action-card";
        card.innerHTML = `
          <div class="card-head">
            <div>
              <h3>${item.id} · ${item.title}</h3>
              <div class="meta-row">
                <span class="pill">${item.priority}</span>
                <span class="pill">${item.status}</span>
              </div>
            </div>
          </div>
          <div class="split">
            <div class="field">
              <label for="action-status-${index}">Status</label>
              <select id="action-status-${index}" data-action-index="${index}" data-action-field="status">
                ${["todo", "active", "blocked", "done"].map(status => `<option value="${status}" ${status === item.status ? "selected" : ""}>${status}</option>`).join("")}
              </select>
            </div>
            <div class="field">
              <label>Linked errors</label>
              <div class="muted-box">${item.linked_error_ids.length ? item.linked_error_ids.join(", ") : "No linked errors."}</div>
            </div>
          </div>
          <div class="field">
            <label>Definition of done</label>
            <div class="muted-box">${item.definition_of_done}</div>
          </div>
          <div class="field">
            <label for="action-next-${index}">Next step</label>
            <textarea id="action-next-${index}" data-action-index="${index}" data-action-field="next_step">${readText(item.next_step)}</textarea>
          </div>
          <div class="field">
            <label for="action-comments-${index}">Comments</label>
            <textarea id="action-comments-${index}" data-action-index="${index}" data-action-field="comments">${readText(item.comments)}</textarea>
          </div>
          <div class="field">
            <label>Artifact refs</label>
            <ul class="refs">${item.artifact_refs.map(ref => `<li><code>${ref}</code></li>`).join("")}</ul>
          </div>
        `;
        list.appendChild(card);
      });
      list.querySelectorAll("[data-action-index]").forEach(control => {
        control.addEventListener("input", (event) => {
          const index = Number(event.target.dataset.actionIndex);
          const field = event.target.dataset.actionField;
          state.data.action_items[index][field] = event.target.value;
          markDirty();
        });
      });
    }

    function renderDirections(data) {
      const list = document.getElementById("direction-list");
      list.innerHTML = "";
      (data.directions || []).forEach((dir, index) => {
        const card = document.createElement("div");
        card.className = "direction-card";
        card.innerHTML = `
          <div class="card-head">
            <div>
              <h3>${dir.id} · ${dir.title}</h3>
              <div class="meta-row">
                <span class="pill direction-status-${dir.status}">${dir.status}</span>
              </div>
            </div>
          </div>
          <p class="subtle">${readText(dir.description)}</p>
          <div class="split">
            <div class="field">
              <label for="dir-status-${index}">Status</label>
              <select id="dir-status-${index}" data-dir-index="${index}" data-dir-field="status">
                ${["proposed", "active", "rejected", "done"].map(s => `<option value="${s}" ${s === dir.status ? "selected" : ""}>${s}</option>`).join("")}
              </select>
            </div>
            <div class="field">
              <label>Linked errors</label>
              <div class="muted-box">${dir.linked_error_ids.length ? dir.linked_error_ids.join(", ") : "None."}</div>
            </div>
          </div>
          <div class="split">
            <div class="field">
              <label>Pros</label>
              <ul class="refs">${dir.pros.map(p => `<li>${p}</li>`).join("") || "<li class='subtle'>None listed.</li>"}</ul>
            </div>
            <div class="field">
              <label>Cons</label>
              <ul class="refs">${dir.cons.map(c => `<li>${c}</li>`).join("") || "<li class='subtle'>None listed.</li>"}</ul>
            </div>
          </div>
          <div class="field">
            <label for="dir-comments-${index}">Comments</label>
            <textarea id="dir-comments-${index}" data-dir-index="${index}" data-dir-field="comments">${readText(dir.comments)}</textarea>
          </div>
        `;
        list.appendChild(card);
      });
      list.querySelectorAll("[data-dir-index]").forEach(control => {
        control.addEventListener("input", (event) => {
          const index = Number(event.target.dataset.dirIndex);
          const field = event.target.dataset.dirField;
          state.data.directions[index][field] = event.target.value;
          markDirty();
        });
      });
    }

    function addDirection() {
      if (!state.data.directions) state.data.directions = [];
      const nextNumber = state.data.directions.length + 1;
      state.data.directions.push({
        id: `DIR-${String(nextNumber).padStart(3, "0")}`,
        title: "New direction",
        description: "",
        status: "proposed",
        pros: [],
        cons: [],
        linked_error_ids: [],
        linked_action_item_ids: [],
        comments: ""
      });
      renderDirections(state.data);
      renderStats(state.data);
      markDirty();
    }

    function renderPromptSketches(data) {
      const list = document.getElementById("prompt-list");
      list.innerHTML = "";
      data.prompt_sketches.forEach((prompt, index) => {
        const card = document.createElement("div");
        card.className = "prompt-card";
        card.innerHTML = `
          <div class="card-head">
            <div>
              <h3>${prompt.id}</h3>
            </div>
            <button class="ghost" data-copy-index="${index}">Copy Prompt</button>
          </div>
          <div class="field">
            <label for="prompt-title-${index}">Title</label>
            <input type="text" id="prompt-title-${index}" data-prompt-index="${index}" data-prompt-field="title" value="${prompt.title.replace(/"/g, "&quot;")}">
          </div>
          <div class="field">
            <label for="prompt-body-${index}">Body</label>
            <textarea id="prompt-body-${index}" data-prompt-index="${index}" data-prompt-field="body">${readText(prompt.body)}</textarea>
          </div>
          <div class="field">
            <label for="prompt-tags-${index}">Tags (comma separated)</label>
            <input type="text" id="prompt-tags-${index}" data-prompt-index="${index}" data-prompt-field="tags" value="${prompt.tags.join(", ").replace(/"/g, "&quot;")}">
          </div>
        `;
        list.appendChild(card);
      });
      list.querySelectorAll("[data-prompt-index]").forEach(control => {
        control.addEventListener("input", (event) => {
          const index = Number(event.target.dataset.promptIndex);
          const field = event.target.dataset.promptField;
          if (field === "tags") {
            state.data.prompt_sketches[index].tags = event.target.value
              .split(",")
              .map(tag => tag.trim())
              .filter(Boolean);
          } else {
            state.data.prompt_sketches[index][field] = event.target.value;
          }
          markDirty();
        });
      });
      list.querySelectorAll("[data-copy-index]").forEach(button => {
        button.addEventListener("click", async () => {
          const prompt = state.data.prompt_sketches[Number(button.dataset.copyIndex)];
          await navigator.clipboard.writeText(prompt.body);
          setStatus(`Copied ${prompt.id}`, "ok");
        });
      });
    }

    function bindNotes(data) {
      const projectNotes = document.getElementById("project-notes");
      const sessionNotes = document.getElementById("session-notes");
      projectNotes.value = readText(data.notes.project_notes);
      sessionNotes.value = readText(data.notes.session_notes);
      projectNotes.oninput = (event) => {
        state.data.notes.project_notes = event.target.value;
        markDirty();
      };
      sessionNotes.oninput = (event) => {
        state.data.notes.session_notes = event.target.value;
        markDirty();
      };
    }

    async function loadArtifact(path) {
      const response = await fetch(`/api/artifact?path=${encodeURIComponent(path)}`);
      if (!response.ok) {
        document.getElementById("artifact-viewer").textContent = `Failed to load ${path}`;
        return;
      }
      const payload = await response.json();
      state.currentArtifactPath = path;
      document.getElementById("artifact-path-label").textContent = payload.path;
      document.getElementById("artifact-viewer").textContent = payload.content;
    }

    function addPrompt() {
      const nextNumber = state.data.prompt_sketches.length + 1;
      state.data.prompt_sketches.push({
        id: `PROMPT-${String(nextNumber).padStart(3, "0")}`,
        title: "New prompt sketch",
        body: "",
        tags: []
      });
      renderPromptSketches(state.data);
      markDirty();
    }

    async function saveState() {
      const payload = JSON.stringify(state.data, null, 2);
      await fetchJson("/api/state", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: payload
      });
      state.dirty = false;
      setStatus("Tracker saved", "ok");
    }

    function renderAll(data) {
      renderHeader(data);
      renderStats(data);
      renderArtifacts(data);
      renderKnownErrors(data);
      renderActionItems(data);
      renderDirections(data);
      renderPromptSketches(data);
      bindNotes(data);
    }

    async function loadState() {
      setStatus("Loading tracker…");
      const data = await fetchJson("/api/state");
      state.data = data;
      state.dirty = false;
      renderAll(data);
      setStatus("Tracker loaded", "ok");
      if (data.artifacts.length) {
        loadArtifact(data.artifacts[0].path);
      }
    }

    document.getElementById("reload-btn").addEventListener("click", () => loadState().catch(error => setStatus(error.message, "error")));
    document.getElementById("save-btn").addEventListener("click", () => saveState().catch(error => setStatus(error.message, "error")));
    document.getElementById("add-prompt-btn").addEventListener("click", addPrompt);
    document.getElementById("add-direction-btn").addEventListener("click", addDirection);
    window.addEventListener("keydown", (event) => {
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "s") {
        event.preventDefault();
        saveState().catch(error => setStatus(error.message, "error"));
      }
    });

    loadState().catch(error => setStatus(error.message, "error"));
  </script>
</body>
</html>
"""


def load_state() -> dict:
    return json.loads(STATE_PATH.read_text(encoding="utf-8"))


def save_state(payload: dict) -> None:
    if not isinstance(payload, dict):
        raise ValueError("Tracker payload must be a JSON object.")
    if payload.get("version") != 1:
        raise ValueError("Tracker payload must keep version 1.")
    STATE_PATH.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def resolve_artifact_path(raw_path: str) -> Path:
    candidate = (ROOT / raw_path).resolve()
    if ROOT not in candidate.parents and candidate != ROOT:
        raise ValueError("Artifact path escapes the repository root.")
    if not candidate.is_file():
        raise FileNotFoundError(raw_path)
    return candidate


class ProgressViewerHandler(BaseHTTPRequestHandler):
    server_version = "TeXactlyProgressViewer/1.0"

    def _send_json(self, payload: dict, status: HTTPStatus = HTTPStatus.OK) -> None:
        body = json.dumps(payload, indent=2).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_text(self, text: str, status: HTTPStatus = HTTPStatus.OK) -> None:
        body = text.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        if parsed.path == "/":
            self._send_text(HTML)
            return
        if parsed.path == "/api/state":
            self._send_json(load_state())
            return
        if parsed.path == "/api/artifact":
            params = parse_qs(parsed.query)
            raw_path = params.get("path", [""])[0]
            try:
                artifact_path = resolve_artifact_path(raw_path)
                payload = {
                    "path": raw_path,
                    "content": artifact_path.read_text(encoding="utf-8"),
                }
                self._send_json(payload)
            except FileNotFoundError:
                self._send_json({"error": f"Artifact not found: {raw_path}"}, HTTPStatus.NOT_FOUND)
            except Exception as exc:  # pragma: no cover - defensive
                self._send_json({"error": str(exc)}, HTTPStatus.BAD_REQUEST)
            return
        self._send_json({"error": "Not found"}, HTTPStatus.NOT_FOUND)

    def do_POST(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        if parsed.path != "/api/state":
            self._send_json({"error": "Not found"}, HTTPStatus.NOT_FOUND)
            return
        length = int(self.headers.get("Content-Length", "0"))
        raw_body = self.rfile.read(length)
        try:
            payload = json.loads(raw_body.decode("utf-8"))
            save_state(payload)
        except Exception as exc:
            self._send_json({"error": str(exc)}, HTTPStatus.BAD_REQUEST)
            return
        self._send_json({"ok": True})

    def log_message(self, format: str, *args) -> None:  # noqa: A003
        print(format % args)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Serve the TeXactly progress viewer.")
    parser.add_argument("--host", default="127.0.0.1", help="Host to bind to.")
    parser.add_argument("--port", default=8421, type=int, help="Port to listen on.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    server = ThreadingHTTPServer((args.host, args.port), ProgressViewerHandler)
    print(f"TeXactly progress viewer running at http://{args.host}:{args.port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
