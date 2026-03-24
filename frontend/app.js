// ── Config ────────────────────────────────────────────────
const API_BASE = "https://franckate-api.onrender.com/api";
// For local dev, change to: const API_BASE = "http://127.0.0.1:5000/api";

let currentMode = "encrypt";
let savedApiKey = localStorage.getItem("franckate_api_key") || "";
let savedKey = null;

// ── Init ──────────────────────────────────────────────────
document.addEventListener("DOMContentLoaded", () => {
  if (savedApiKey) {
    document.getElementById("pg-api-key").value = savedApiKey;
    updateKeyStatus(savedApiKey);
  }
  document.getElementById("pg-input").addEventListener("input", updateCharCount);
  document.getElementById("pg-api-key").addEventListener("input", (e) => {
    const key = e.target.value.trim();
    localStorage.setItem("franckate_api_key", key);
    savedApiKey = key;
    updateKeyStatus(key);
  });
  animateHeroCipher();
});

function updateKeyStatus(key) {
  const el = document.getElementById("key-status");
  if (key.length > 20) {
    el.textContent = "✓ Key loaded";
    el.style.color = "var(--accent)";
    document.getElementById("pg-hint").style.display = "none";
    document.getElementById("pg-run-btn").disabled = false;
  } else if (key.length > 0) {
    el.textContent = "Key looks short";
    el.style.color = "var(--amber)";
  } else {
    el.textContent = "";
    document.getElementById("pg-hint").style.display = "block";
  }
}

function updateCharCount() {
  const len = document.getElementById("pg-input").value.length;
  document.getElementById("pg-char-count").textContent = `${len} char${len !== 1 ? "s" : ""}`;
}

// ── Playground mode ───────────────────────────────────────
function setPgMode(mode) {
  currentMode = mode;
  ["encrypt", "decrypt", "steps", "batch"].forEach((m) => {
    document.getElementById(`pg-mode-${m.slice(0, 3) === "ste" ? "steps" : m === "batch" ? "batch" : m}`).classList.toggle(
      "active",
      m === mode
    );
  });
  document.getElementById(`pg-mode-enc`).classList.toggle("active", mode === "encrypt");
  document.getElementById(`pg-mode-dec`).classList.toggle("active", mode === "decrypt");
  document.getElementById(`pg-mode-steps`).classList.toggle("active", mode === "steps");
  document.getElementById(`pg-mode-batch`).classList.toggle("active", mode === "batch");

  const ta = document.getElementById("pg-input");
  const hints = {
    encrypt: "Type something to encrypt...",
    decrypt: "Paste Franckate ciphertext here (e.g. U7.L4.L11...)",
    steps: "Type up to 200 chars to see step-by-step encoding...",
    batch: 'Enter one item per line — each line will be encrypted separately.',
  };
  ta.placeholder = hints[mode];
  clearPlayground();
}

// ── Run playground ────────────────────────────────────────
async function runPlayground() {
  const key = document.getElementById("pg-api-key").value.trim();
  const input = document.getElementById("pg-input").value;
  if (!key) return showPgError("Please enter your API key above.");
  if (!input.trim()) return showPgError("Please enter some text first.");

  const btn = document.getElementById("pg-run-btn");
  btn.textContent = "Running...";
  btn.disabled = true;

  try {
    let endpoint, body;
    if (currentMode === "encrypt") {
      endpoint = "/encrypt"; body = { text: input };
    } else if (currentMode === "decrypt") {
      endpoint = "/decrypt"; body = { text: input };
    } else if (currentMode === "steps") {
      endpoint = "/encrypt/steps"; body = { text: input };
    } else if (currentMode === "batch") {
      endpoint = "/batch/encrypt";
      body = { texts: input.split("\n").map(s => s.trim()).filter(Boolean) };
    }

    const res = await fetch(API_BASE + endpoint, {
      method: "POST",
      headers: { "Content-Type": "application/json", "X-API-Key": key },
      body: JSON.stringify(body),
    });
    const data = await res.json();

    if (!res.ok) {
      showPgError(data.error || `Error ${res.status}`);
      return;
    }
    renderOutput(data);
    document.getElementById("copy-output-btn").style.display = "inline-block";
  } catch (e) {
    showPgError("Network error — is the API running? " + e.message);
  } finally {
    btn.textContent = "Run →";
    btn.disabled = false;
  }
}

function renderOutput(data) {
  const el = document.getElementById("pg-output");

  if (currentMode === "encrypt") {
    el.innerHTML = `
      <div class="field"><span class="label">Original</span><span>${escHtml(data.original)}</span></div>
      <div class="field"><span class="label">Encrypted</span><span class="encrypted">${escHtml(data.encrypted)}</span></div>
      <div class="field"><span class="label">Length</span><span style="color:var(--muted)">${data.length.input} chars → ${data.length.output} chars (${Math.round(data.length.output/data.length.input)}× expansion)</span></div>
    `;
  } else if (currentMode === "decrypt") {
    el.innerHTML = `
      <div class="field"><span class="label">Ciphertext</span><span class="encrypted">${escHtml(data.original)}</span></div>
      <div class="field"><span class="label">Decrypted</span><span class="decrypted">${escHtml(data.decrypted)}</span></div>
    `;
  } else if (currentMode === "steps") {
    let stepsHtml = data.steps.map(s => `
      <div class="pg-step">
        <span class="char">'${escHtml(s.character)}'</span>
        → <span class="token">${escHtml(s.token)}</span>
        <div class="expl">${escHtml(s.explanation)}</div>
      </div>
    `).join("");
    el.innerHTML = `
      <div class="field"><span class="label">Final output</span><span class="encrypted">${escHtml(data.encrypted)}</span></div>
      <div class="field"><span class="label">Steps (${data.total_steps})</span>${stepsHtml}</div>
    `;
  } else if (currentMode === "batch") {
    let rows = data.results.map(r => r.error
      ? `<div class="pg-step"><span class="error-msg">Item ${r.index}: ${escHtml(r.error)}</span></div>`
      : `<div class="pg-step"><span class="char">${escHtml(r.original)}</span><div class="token">${escHtml(r.encrypted)}</div></div>`
    ).join("");
    el.innerHTML = `<div class="field"><span class="label">${data.count} results</span>${rows}</div>`;
  }
}

function showPgError(msg) {
  document.getElementById("pg-output").innerHTML = `<div class="error-msg">${escHtml(msg)}</div>`;
}

function clearPlayground() {
  document.getElementById("pg-input").value = "";
  document.getElementById("pg-output").innerHTML = '<div class="pg-output-placeholder">Results will appear here</div>';
  document.getElementById("pg-char-count").textContent = "0 chars";
  document.getElementById("copy-output-btn").style.display = "none";
}

function copyOutput() {
  const text = document.getElementById("pg-output").innerText;
  navigator.clipboard.writeText(text).then(() => {
    const btn = document.getElementById("copy-output-btn");
    btn.textContent = "Copied!";
    setTimeout(() => (btn.textContent = "Copy"), 1800);
  });
}

// ── Tab switching ─────────────────────────────────────────
function switchTab(btn, panelId) {
  const card = btn.closest(".endpoint-card");
  card.querySelectorAll(".tab").forEach(t => t.classList.remove("active"));
  card.querySelectorAll(".tab-panel").forEach(p => p.classList.remove("active"));
  btn.classList.add("active");
  document.getElementById(panelId).classList.add("active");
}

// ── Auth tabs ─────────────────────────────────────────────
function switchAuthTab(tab) {
  document.querySelectorAll(".auth-tab").forEach(t => t.classList.remove("active"));
  event.target.classList.add("active");
  document.getElementById("register-form").style.display = tab === "register" ? "flex" : "none";
  document.getElementById("login-form").style.display = tab === "login" ? "flex" : "none";
  document.getElementById("key-display").style.display = "none";
}

// ── Register ──────────────────────────────────────────────
async function doRegister() {
  const name = document.getElementById("reg-name").value.trim();
  const email = document.getElementById("reg-email").value.trim();
  const password = document.getElementById("reg-password").value;
  const fb = document.getElementById("reg-feedback");

  fb.textContent = "";
  if (!name || !email || !password) {
    fb.textContent = "All fields are required.";
    fb.className = "form-feedback error";
    return;
  }
  if (password.length < 8) {
    fb.textContent = "Password must be at least 8 characters.";
    fb.className = "form-feedback error";
    return;
  }

  fb.textContent = "Creating account...";
  fb.className = "form-feedback";

  try {
    const res = await fetch(`${API_BASE}/register`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name, email, password }),
    });
    const data = await res.json();
    if (!res.ok) {
      fb.textContent = data.error || "Registration failed.";
      fb.className = "form-feedback error";
      return;
    }
    savedKey = data.developer.api_key;
    showKeyDisplay(savedKey);
  } catch (e) {
    fb.textContent = "Network error: " + e.message;
    fb.className = "form-feedback error";
  }
}

// ── Login ─────────────────────────────────────────────────
async function doLogin() {
  const email = document.getElementById("login-email").value.trim();
  const password = document.getElementById("login-password").value;
  const fb = document.getElementById("login-feedback");

  fb.textContent = "Logging in...";
  fb.className = "form-feedback";

  try {
    const res = await fetch(`${API_BASE}/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password }),
    });
    const data = await res.json();
    if (!res.ok) {
      fb.textContent = data.error || "Login failed.";
      fb.className = "form-feedback error";
      return;
    }
    savedKey = data.developer.api_key;
    showKeyDisplay(savedKey);
  } catch (e) {
    fb.textContent = "Network error: " + e.message;
    fb.className = "form-feedback error";
  }
}

function showKeyDisplay(key) {
  document.getElementById("key-display").style.display = "flex";
  document.getElementById("display-key").textContent = key;
  localStorage.setItem("franckate_api_key", key);
  savedApiKey = key;
  if (document.getElementById("pg-api-key")) {
    document.getElementById("pg-api-key").value = key;
    updateKeyStatus(key);
  }
}

function copyKey() {
  navigator.clipboard.writeText(savedKey || document.getElementById("display-key").textContent).then(() => {
    alert("API key copied to clipboard! 🔑");
  });
}

function goToPlayground() {
  document.getElementById("playground").scrollIntoView({ behavior: "smooth" });
}

// ── Utilities ─────────────────────────────────────────────
function copyText(text, btn) {
  navigator.clipboard.writeText(text).then(() => {
    const orig = btn.textContent;
    btn.textContent = "Copied!";
    setTimeout(() => (btn.textContent = orig), 1800);
  });
}

function escHtml(str) {
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

// ── Hero cipher animation ─────────────────────────────────
const demos = [
  ["Hello", "U7.L4.L11.L11.L14."],
  ["Crypto", "U2.L17.L24.L15.L19.L14."],
  ["Secret!", "U18.L4.L2.L17.L4.L19.F0."],
  ["API 2024", "U0.U15.U8.F27.D1.D9.D1.D3."],
];
let demoIdx = 0;
function animateHeroCipher() {
  setInterval(() => {
    demoIdx = (demoIdx + 1) % demos.length;
    const [plain, cipher] = demos[demoIdx];
    const pe = document.getElementById("hero-plain");
    const ce = document.getElementById("hero-cipher");
    pe.style.opacity = 0;
    ce.style.opacity = 0;
    setTimeout(() => {
      pe.textContent = plain;
      ce.textContent = cipher;
      pe.style.transition = "opacity 0.4s";
      ce.style.transition = "opacity 0.4s";
      pe.style.opacity = 1;
      ce.style.opacity = 1;
    }, 300);
  }, 3000);
}
