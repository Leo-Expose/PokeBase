// search.js — Autocomplete search dropdown
(function() {
  let debounceTimer = null;
  let activeIndex = -1;

  function initSearch(inputEl, dropdownEl, baseUrl) {
    if (!inputEl || !dropdownEl) return;

    inputEl.addEventListener('input', () => {
      clearTimeout(debounceTimer);
      const q = inputEl.value.trim();
      if (q.length < 1) {
        dropdownEl.classList.add('hidden');
        return;
      }
      debounceTimer = setTimeout(() => fetchSuggestions(q, dropdownEl, baseUrl), 200);
    });

    inputEl.addEventListener('keydown', (e) => {
      const items = dropdownEl.querySelectorAll('li');
      if (e.key === 'ArrowDown') {
        e.preventDefault();
        activeIndex = Math.min(activeIndex + 1, items.length - 1);
        updateActive(items);
      } else if (e.key === 'ArrowUp') {
        e.preventDefault();
        activeIndex = Math.max(activeIndex - 1, 0);
        updateActive(items);
      } else if (e.key === 'Enter') {
        e.preventDefault();
        if (activeIndex >= 0 && items[activeIndex]) {
          items[activeIndex].click();
        } else if (inputEl.value.trim()) {
          window.location.href = `/pokemon/${inputEl.value.trim().toLowerCase()}`;
        }
      } else if (e.key === 'Escape') {
        dropdownEl.classList.add('hidden');
        activeIndex = -1;
      }
    });

    // Close dropdown on click outside
    document.addEventListener('click', (e) => {
      if (!inputEl.contains(e.target) && !dropdownEl.contains(e.target)) {
        dropdownEl.classList.add('hidden');
        activeIndex = -1;
      }
    });
  }

  function updateActive(items) {
    items.forEach((item, i) => {
      item.classList.toggle('active', i === activeIndex);
    });
  }

  async function fetchSuggestions(q, dropdownEl, baseUrl) {
    try {
      const resp = await fetch(`/api/suggest?q=${encodeURIComponent(q)}`);
      const data = await resp.json();
      renderDropdown(data, dropdownEl);
    } catch (err) {
      console.error('Search error:', err);
    }
  }

  function renderDropdown(results, dropdownEl) {
    activeIndex = -1;
    if (!results || results.length === 0) {
      dropdownEl.classList.add('hidden');
      return;
    }

    dropdownEl.innerHTML = results.map(r => {
      const types = (r.types || []).map(t =>
        `<span class="type-badge ${t}">${t}</span>`
      ).join('');
      const dex = String(r.dex).padStart(3, '0');
      const displayName = r.name.replace(/-/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
      return `
        <li data-name="${r.name}">
          <img src="/static/sprites/${r.dex}.png"
               onerror="this.src='/static/sprites/official-artwork/${r.dex}.png'; this.onerror=null;"
               alt="${r.name}">
          <div>
            <span class="search-item-name">${displayName}</span>
            <span class="search-item-dex">#${dex}</span>
          </div>
          <div class="search-item-types">${types}</div>
        </li>
      `;
    }).join('');

    dropdownEl.querySelectorAll('li').forEach(li => {
      li.addEventListener('click', () => {
        window.location.href = `/pokemon/${li.dataset.name}`;
      });
    });

    dropdownEl.classList.remove('hidden');
  }

  // Initialize on DOM ready
  document.addEventListener('DOMContentLoaded', () => {
    // Navbar search
    initSearch(
      document.getElementById('nav-search-input'),
      document.getElementById('search-dropdown')
    );
    // Hero search (home page)
    initSearch(
      document.getElementById('hero-search-input'),
      document.getElementById('hero-search-dropdown')
    );
    // Compare search inputs
    initSearch(
      document.getElementById('compare-search-a'),
      document.getElementById('compare-dropdown-a')
    );
    initSearch(
      document.getElementById('compare-search-b'),
      document.getElementById('compare-dropdown-b')
    );
  });
})();
