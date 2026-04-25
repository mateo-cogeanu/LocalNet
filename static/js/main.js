function showToast(text) {
  const toast = document.getElementById("toast");
  if (!toast) return;
  toast.textContent = text;
  toast.classList.add("open");
  clearTimeout(window.__lnToastTimer);
  window.__lnToastTimer = setTimeout(() => toast.classList.remove("open"), 2200);
}

function openImg(src) {
  const box = document.getElementById("lightbox");
  const img = document.getElementById("lb-img");
  if (!box || !img) return;
  img.src = src;
  box.classList.add("open");
}

function initDrop(inputId, previewId, nameId) {
  const input = document.getElementById(inputId);
  if (!input) return;
  const preview = document.getElementById(previewId);
  const previewImg = preview ? preview.querySelector("img") : null;
  const name = document.getElementById(nameId);
  const drop = input.closest(".file-drop");

  const refresh = () => {
    const file = input.files && input.files[0];
    if (name) name.textContent = file ? file.name : "";
    if (preview && previewImg && file && file.type.startsWith("image/")) {
      preview.classList.add("show");
      previewImg.src = URL.createObjectURL(file);
    } else if (preview) {
      preview.classList.remove("show");
    }
  };

  input.addEventListener("change", refresh);
  if (!drop) return;
  ["dragenter", "dragover"].forEach((evt) =>
    drop.addEventListener(evt, (e) => {
      e.preventDefault();
      drop.classList.add("drag");
    })
  );
  ["dragleave", "drop"].forEach((evt) =>
    drop.addEventListener(evt, (e) => {
      e.preventDefault();
      drop.classList.remove("drag");
    })
  );
  drop.addEventListener("drop", (e) => {
    if (!e.dataTransfer.files.length) return;
    input.files = e.dataTransfer.files;
    refresh();
  });
}

function applyTheme(theme) {
  document.documentElement.dataset.theme = theme;
  localStorage.setItem("ln-theme", theme);
  document.querySelectorAll(".theme-swatch").forEach((swatch) => {
    swatch.classList.toggle("selected", swatch.dataset.theme === theme);
  });
}

function applyCompact(enabled) {
  document.documentElement.classList.toggle("compact", !!enabled);
  localStorage.setItem("ln-compact", enabled ? "1" : "0");
}

function loadCompact() {
  const enabled = localStorage.getItem("ln-compact") === "1";
  document.documentElement.classList.toggle("compact", enabled);
  const checkbox = document.getElementById("tog-compact");
  if (checkbox) checkbox.checked = enabled;
}

function applyFont(size) {
  document.documentElement.style.setProperty("--base-size", `${size}px`);
  localStorage.setItem("ln-font", size);
}

function loadFont() {
  const size = localStorage.getItem("ln-font") || "16";
  applyFont(size);
  const select = document.getElementById("font-sel");
  if (select) select.value = size;
}

function showTab(name) {
  document.querySelectorAll(".s-panel").forEach((panel) => {
    panel.classList.toggle("active", panel.id === `panel-${name}`);
  });
  document.querySelectorAll(".s-nav-btn").forEach((btn) => {
    btn.classList.toggle("active", btn.dataset.tab === name);
  });
}

const LOCALNET_SITE_MAP = {
  tube: { label: "Tube", href: "/tube", icon: `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polygon points="23 7 16 12 23 17 23 7"/><rect x="1" y="5" width="15" height="14" rx="2"/></svg>` },
  games: { label: "Games", href: "/games", icon: `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="2" y="6" width="20" height="12" rx="2"/><path d="M6 12h4m-2-2v4M15 11h.01M17 13h.01"/></svg>` },
  forums: { label: "Forums", href: "/forums", icon: `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15a2 2 0 01-2 2H7l-4 4V5a2 2 0 012-2h14a2 2 0 012 2z"/></svg>` },
  wiki: { label: "Wiki", href: "/wiki", icon: `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M2 3h6a4 4 0 014 4v14a3 3 0 00-3-3H2z"/><path d="M22 3h-6a4 4 0 00-4 4v14a3 3 0 013-3h7z"/></svg>` },
  paste: { label: "Paste", href: "/paste", icon: `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M16 4h2a2 2 0 012 2v14a2 2 0 01-2 2H6a2 2 0 01-2-2V6a2 2 0 012-2h2"/><rect x="8" y="2" width="8" height="4" rx="1" ry="1"/></svg>` },
  chat: { label: "Chat", href: "/chat", icon: `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15a2 2 0 01-2 2H7l-4 4V5a2 2 0 012-2h14a2 2 0 012 2z"/><line x1="9" y1="9" x2="15" y2="9"/><line x1="9" y1="13" x2="13" y2="13"/></svg>` },
};

function getFavoriteSites() {
  try {
    const parsed = JSON.parse(localStorage.getItem("ln-favorites") || "[]");
    return Array.isArray(parsed) ? parsed.filter((key) => LOCALNET_SITE_MAP[key]) : [];
  } catch {
    return [];
  }
}

function setFavoriteSites(sites) {
  localStorage.setItem("ln-favorites", JSON.stringify(sites));
}

function toggleFavoriteSite(site) {
  const current = getFavoriteSites();
  const next = current.includes(site)
    ? current.filter((item) => item !== site)
    : [...current, site];
  setFavoriteSites(next);
  renderFavoriteSites();
}

function renderFavoriteSites() {
  const holder = document.getElementById("favorite-sites");
  if (!holder) return;
  const favorites = getFavoriteSites();
  document.querySelectorAll(".pin-chip").forEach((chip) => {
    chip.classList.toggle("active", favorites.includes(chip.dataset.site));
  });
  if (!favorites.length) {
    holder.innerHTML = `<div class="favorite-empty">Use the pen to pin a few favorite sites right here under ⟨LocalNet⟩.</div>`;
    return;
  }
  holder.innerHTML = favorites
    .map((key) => {
      const site = LOCALNET_SITE_MAP[key];
      return `
        <a class="favorite-site-card" href="${site.href}">
          <span class="favorite-site-icon">${site.icon}</span>
          <strong>${site.label}</strong>
        </a>
      `;
    })
    .join("");
}

function togglePinPicker() {
  const picker = document.getElementById("pin-picker");
  if (!picker) return;
  picker.classList.toggle("pin-picker-hidden");
}

function toggleMobileNav() {
  const nav = document.getElementById("site-nav");
  if (!nav) return;
  nav.classList.toggle("nav-open");
}

document.addEventListener("DOMContentLoaded", () => {
  applyTheme(localStorage.getItem("ln-theme") || "default");
  loadFont();
  loadCompact();
  renderFavoriteSites();
  window.addEventListener("resize", () => {
    if (window.innerWidth > 860) {
      document.getElementById("site-nav")?.classList.remove("nav-open");
    }
  });
});
