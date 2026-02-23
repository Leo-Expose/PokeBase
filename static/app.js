document.addEventListener("DOMContentLoaded", () => {
  const root = document.documentElement;
  const input = document.querySelector('input[name="pokemon_name"]');
  const box = document.getElementById("suggestions");
  const form = document.getElementById("searchForm");
  const submitBtn = form ? form.querySelector('button[type="submit"]') : null;
  const themeToggle = document.getElementById("themeToggle");
  const moveFilter = document.getElementById("moveFilter");
  const movesTable = document.getElementById("movesTable");
  const moveDetail = document.getElementById("moveDetail");
  const copyLinkBtn = document.getElementById("copyLink");
  const layout = document.querySelector(".pokemon-layout");

  // ---- theme toggle (Catppuccin Mocha / Latte) ----
  const stored = localStorage.getItem("pdx-theme");
  if (stored === "light" || stored === "dark") {
    root.setAttribute("data-theme", stored);
  }

  function toggleTheme() {
    const current = root.getAttribute("data-theme") || "dark";
    const next = current === "dark" ? "light" : "dark";
    root.setAttribute("data-theme", next);
    localStorage.setItem("pdx-theme", next);
  }
  if (themeToggle) {
    themeToggle.addEventListener("click", toggleTheme);
  }

  // ---- autocomplete + keyboard nav ----
  let controller = null;
  let activeIndex = -1;

  function clearSuggestions() {
    if (!box) return;
    box.innerHTML = "";
    box.classList.remove("open");
    activeIndex = -1;
  }
  function updateActiveItem() {
    if (!box) return;
    const items = box.querySelectorAll(".suggestion-item");
    items.forEach((el, i) => el.classList.toggle("active", i === activeIndex));
  }

  if (input && box) {
    input.addEventListener("input", () => {
      const q = input.value.trim();
      if (!q) {
        clearSuggestions();
        return;
      }
      if (controller) controller.abort();
      controller = new AbortController();

      fetch(`/api/pokemon-suggest?q=${encodeURIComponent(q)}`, {
        signal: controller.signal,
      })
        .then((r) => (r.ok ? r.json() : { results: [] }))
        .then((data) => {
          box.innerHTML = "";
          const results = data.results || [];
          if (!results.length) {
            clearSuggestions();
            return;
          }
          results.forEach((row) => {
            const btn = document.createElement("button");
            btn.type = "button";
            btn.className = "suggestion-item";
            btn.dataset.id = row.id;
            btn.setAttribute("role", "option");
            btn.textContent = row.name;
            box.appendChild(btn);
          });
          box.classList.add("open");
          activeIndex = -1;
          updateActiveItem();
        })
        .catch(() => {});
    });

    input.addEventListener("keydown", (e) => {
      const items = box.querySelectorAll(".suggestion-item");
      const count = items.length;
      if (!count) return;

      if (e.key === "ArrowDown") {
        e.preventDefault();
        activeIndex = (activeIndex + 1) % count;
        updateActiveItem();
      } else if (e.key === "ArrowUp") {
        e.preventDefault();
        activeIndex = (activeIndex - 1 + count) % count;
        updateActiveItem();
      } else if (e.key === "Enter") {
        if (activeIndex >= 0 && activeIndex < count && box.classList.contains("open")) {
          e.preventDefault();
          const chosen = items[activeIndex];
          const identifier = chosen.dataset.id;
          clearSuggestions();
          window.location.href = `/pokemon/${encodeURIComponent(identifier)}`;
        }
      } else if (e.key === "Escape") {
        clearSuggestions();
      }
    });

    box.addEventListener("click", (e) => {
      const item = e.target.closest(".suggestion-item");
      if (!item) return;
      const identifier = item.dataset.id;
      clearSuggestions();
      window.location.href = `/pokemon/${encodeURIComponent(identifier)}`;
    });

    document.addEventListener("click", (e) => {
      if (e.target !== input && !box.contains(e.target)) {
        clearSuggestions();
      }
    });
  }

  // ---- submit spinner on search button ----
  if (form && submitBtn) {
    form.addEventListener("submit", () => {
      submitBtn.classList.add("loading");
      submitBtn.disabled = true;
    });
  }

  // ---- keyboard shortcuts ----
  document.addEventListener("keydown", (e) => {
    // Ignore key commands if user is typing in the move filter
    const isEditingFilter = moveFilter && document.activeElement === moveFilter;
    if (isEditingFilter) return;

    if (e.key === "/" && document.activeElement !== input) {
      e.preventDefault();
      input && input.focus();
    }
    if (e.ctrlKey && e.key.toLowerCase() === "k") {
      e.preventDefault();
      input && input.focus();
    }

    // Ignore prev/next if input is focused
    if (document.activeElement === input) return;

    // prev / next with arrow keys
    const navPrev = document.querySelector(".nav-card.prev:not(.disabled)");
    const navNext = document.querySelector(".nav-card.next:not(.disabled)");
    if (e.key === "ArrowLeft" && navPrev && !box.classList.contains("open")) {
      e.preventDefault();
      const href = navPrev.getAttribute("href");
      if (href) window.location.href = href;
    } else if (e.key === "ArrowRight" && navNext && !box.classList.contains("open")) {
      e.preventDefault();
      const href = navNext.getAttribute("href");
      if (href) window.location.href = href;
    }
  });

  // ---- move filter ----
  if (moveFilter && movesTable) {
    const rows = Array.from(movesTable.querySelectorAll("tbody tr"));
    moveFilter.addEventListener("input", () => {
      const q = moveFilter.value.trim().toLowerCase();
      rows.forEach((row) => {
        const moveName = row.cells[0].textContent.toLowerCase();
        row.style.display = moveName.includes(q) ? "" : "none";
      });
    });
  }

  // ---- move detail panel ----
  function renderMoveDetail(row) {
    if (!moveDetail || !row) {
      if (moveDetail) moveDetail.innerHTML = '<div class="move-detail-empty">Click a move to see details.</div>';
      return;
    }
    const name = row.dataset.moveName || "";
    const typeName = row.dataset.moveType || "";
    const typeId = row.dataset.moveTypeId || "";
    const cat = row.dataset.moveCat || "";
    const power = row.dataset.movePower || "";
    const acc = row.dataset.moveAcc || "";
    const pp = row.dataset.movePp || "";
    const effect = row.dataset.moveEffect || "";

    moveDetail.innerHTML = `
      <div class="move-detail">
        <div class="move-detail-header">
          <span class="move-detail-name">${name}</span>
          ${
            typeName
              ? `<span class="chip tiny type-${typeId}">${typeName}</span>`
              : ""
          }
        </div>
        <div class="move-detail-meta">
          <span>Category: ${cat || "—"}</span>
          <span>Power: ${power || "—"}</span>
          <span>Accuracy: ${acc ? acc + "%" : "—"}</span>
          <span>PP: ${pp || "—"}</span>
        </div>
        <p class="move-detail-text">${effect || "No effect text available."}</p>
      </div>
    `;
  }

  if (movesTable && moveDetail) {
    const rows = movesTable.querySelectorAll(".move-row");
    rows.forEach((row) => {
      row.addEventListener("click", () => {
        rows.forEach((r) => r.classList.remove("active"));
        row.classList.add("active");
        renderMoveDetail(row);
      });
    });
  }

  // ---- copy share link ----
  if (copyLinkBtn) {
    copyLinkBtn.addEventListener("click", async () => {
      try {
        await navigator.clipboard.writeText(window.location.href);
        copyLinkBtn.classList.add("copied");
        setTimeout(() => copyLinkBtn.classList.remove("copied"), 1200);
      } catch (e) {
        // ignore
      }
    });
  }
});
