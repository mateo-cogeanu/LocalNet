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
  tube: { label: "Tube", href: "/tube", desc: "Videos and uploads" },
  games: { label: "Games", href: "/games", desc: "Playable local games" },
  forums: { label: "Forums", href: "/forums", desc: "Threads and comments" },
  wiki: { label: "Wiki", href: "/wiki", desc: "Collaborative pages" },
  paste: { label: "Paste", href: "/paste", desc: "Snippets and code" },
  chat: { label: "Chat", href: "/chat", desc: "Live room" },
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
    holder.innerHTML = `<div class="favorite-empty">Pick a few favorite sites above and they’ll live here under ⟨LocalNet⟩.</div>`;
    return;
  }
  holder.innerHTML = favorites
    .map((key) => {
      const site = LOCALNET_SITE_MAP[key];
      return `
        <a class="favorite-site-card" href="${site.href}">
          <strong>${site.label}</strong>
          <span>${site.desc}</span>
        </a>
      `;
    })
    .join("");
}

document.addEventListener("DOMContentLoaded", () => {
  applyTheme(localStorage.getItem("ln-theme") || "default");
  loadFont();
  loadCompact();
});
