import { Editor } from "@tiptap/core";
import StarterKit from "@tiptap/starter-kit";

const requestInput = document.getElementById("request-input");
const searchBtn = document.getElementById("search-btn");
const resultsStep = document.getElementById("step-results");
const resultsList = document.getElementById("results-list");
const draftBtn = document.getElementById("draft-btn");
const editorStep = document.getElementById("step-editor");
const editorEl = document.getElementById("editor");
const exportBtn = document.getElementById("export-btn");
const demoBanner = document.getElementById("demo-banner");
const statusEl = document.getElementById("status");
const toolbar = document.getElementById("toolbar");

let lastQuery = "";
let selectedIds = new Set();
let editor = null;

function setStatus(text) {
  statusEl.textContent = text;
}

function highlightPlaceholders(html) {
  // Wraps [SOMETHING LIKE THIS] in a span so the editor can style it.
  return html.replace(/\[([A-Z0-9 \/\-]+)\]/g, '<span class="placeholder">[$1]</span>');
}

async function runSearch() {
  const query = requestInput.value.trim();
  if (!query) return;
  lastQuery = query;
  setStatus("Searching templates...");
  searchBtn.disabled = true;

  const res = await fetch("/api/search", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ query, top_k: 3 }),
  });
  const data = await res.json();
  searchBtn.disabled = false;
  demoBanner.classList.toggle("hidden", !data.demo_mode);

  resultsList.innerHTML = "";
  selectedIds = new Set();
  data.results.forEach((hit, i) => {
    const li = document.createElement("li");
    const checkbox = document.createElement("input");
    checkbox.type = "checkbox";
    checkbox.checked = i === 0;
    checkbox.addEventListener("change", () => {
      if (checkbox.checked) selectedIds.add(hit.id);
      else selectedIds.delete(hit.id);
      draftBtn.disabled = selectedIds.size === 0;
    });
    if (i === 0) selectedIds.add(hit.id);

    const label = document.createElement("span");
    label.textContent = hit.title;

    const score = document.createElement("span");
    score.className = "score";
    // Order comes from the final pick; the number is the raw search score,
    // so the best fit can show a lower number than a topic-heavy match.
    score.textContent = i === 0 ? `best fit · search ${hit.score.toFixed(2)}` : `search ${hit.score.toFixed(2)}`;

    li.appendChild(checkbox);
    li.appendChild(label);
    li.appendChild(score);
    resultsList.appendChild(li);
  });

  resultsStep.classList.remove("hidden");
  draftBtn.disabled = selectedIds.size === 0;
  setStatus(`Found ${data.results.length} match(es).`);
}

async function runDraft() {
  setStatus("Drafting contract...");
  draftBtn.disabled = true;

  const res = await fetch("/api/draft", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ query: lastQuery, template_ids: Array.from(selectedIds) }),
  });
  const data = await res.json();
  draftBtn.disabled = false;
  demoBanner.classList.toggle("hidden", !data.demo_mode);

  const content = highlightPlaceholders(data.html);

  if (editor) {
    editor.commands.setContent(content);
  } else {
    editor = new Editor({
      element: editorEl,
      extensions: [StarterKit],
      content,
    });
  }

  editorStep.classList.remove("hidden");
  setStatus(`Draft ready. ${data.placeholders.length} placeholder field(s) left to fill in.`);
}

async function runExport() {
  if (!editor) return;
  setStatus("Building PDF...");
  exportBtn.disabled = true;

  const html = editor.getHTML();
  const res = await fetch("/api/export", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ html }),
  });

  exportBtn.disabled = false;
  if (!res.ok) {
    setStatus("PDF export failed.");
    return;
  }

  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = "contract-draft.pdf";
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
  setStatus("PDF downloaded.");
}

toolbar.addEventListener("click", (e) => {
  const btn = e.target.closest("button[data-cmd]");
  if (!btn || !editor) return;
  const cmd = btn.dataset.cmd;
  const chain = editor.chain().focus();
  switch (cmd) {
    case "bold": chain.toggleBold().run(); break;
    case "italic": chain.toggleItalic().run(); break;
    case "h1": chain.toggleHeading({ level: 1 }).run(); break;
    case "h2": chain.toggleHeading({ level: 2 }).run(); break;
    case "bulletList": chain.toggleBulletList().run(); break;
    case "orderedList": chain.toggleOrderedList().run(); break;
    case "undo": chain.undo().run(); break;
    case "redo": chain.redo().run(); break;
  }
});

searchBtn.addEventListener("click", runSearch);
draftBtn.addEventListener("click", runDraft);
exportBtn.addEventListener("click", runExport);
