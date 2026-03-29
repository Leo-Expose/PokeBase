// type_calc.js — Interactive type effectiveness calculator
(function() {
  const ALL_TYPES = [
    'normal', 'fire', 'water', 'electric', 'grass', 'ice',
    'fighting', 'poison', 'ground', 'flying', 'psychic', 'bug',
    'rock', 'ghost', 'dragon', 'dark', 'steel', 'fairy'
  ];

  function capitalize(s) {
    return s.charAt(0).toUpperCase() + s.slice(1);
  }

  function populateSelect(selectEl, includeNone) {
    if (!selectEl) return;
    selectEl.innerHTML = '';
    if (includeNone) {
      const opt = document.createElement('option');
      opt.value = '';
      opt.textContent = '— None —';
      selectEl.appendChild(opt);
    }
    ALL_TYPES.forEach(t => {
      const opt = document.createElement('option');
      opt.value = t;
      opt.textContent = capitalize(t);
      selectEl.appendChild(opt);
    });
  }

  async function calcOffensive() {
    const atkType = document.getElementById('atk-type')?.value;
    const defType1 = document.getElementById('def-type1')?.value;
    const defType2 = document.getElementById('def-type2')?.value;

    if (!atkType || !defType1) return;

    const defending = [defType1, defType2].filter(Boolean).join(',');
    try {
      const resp = await fetch(`/api/type-effectiveness?attacking=${atkType}&defending=${defending}`);
      const data = await resp.json();
      renderResult(data);
    } catch (err) {
      console.error('Calc error:', err);
    }
  }

  function renderResult(data) {
    const container = document.getElementById('calc-result');
    if (!container) return;

    let cls = 'normal';
    if (data.category === 'super_effective') cls = 'super';
    else if (data.category === 'not_very') cls = 'not-very';
    else if (data.category === 'immune') cls = 'immune';

    const categoryLabels = {
      'super_effective': '🔥 Super Effective',
      'not_very': '🛡️ Not Very Effective',
      'immune': '🚫 No Effect',
      'normal': '⚔️ Normal'
    };

    const breakdownHtml = data.breakdown.map(b =>
      `<div>${capitalize(b.attacker)} → ${capitalize(b.defender)}: ×${b.mult}</div>`
    ).join('');

    container.innerHTML = `
      <div class="multiplier ${cls}">${data.label}</div>
      <div class="category-label">${categoryLabels[data.category] || data.category}</div>
      <div class="calc-breakdown">${breakdownHtml}</div>
    `;
  }

  async function calcDefensive() {
    const defType1 = document.getElementById('chart-type1')?.value;
    const defType2 = document.getElementById('chart-type2')?.value;

    if (!defType1) return;

    const defending = [defType1, defType2].filter(Boolean).join(',');

    const container = document.getElementById('defensive-chart');
    if (!container) return;

    container.innerHTML = '<div class="loading"><div class="spinner"></div></div>';

    // Build the full chart by querying each attacking type
    const sections = { weak: [], resist: [], immune: [] };

    for (const atkType of ALL_TYPES) {
      try {
        const resp = await fetch(`/api/type-effectiveness?attacking=${atkType}&defending=${defending}`);
        const data = await resp.json();
        const entry = { type: atkType, multiplier: data.multiplier, label: data.label };
        if (data.multiplier === 0) sections.immune.push(entry);
        else if (data.multiplier >= 2) sections.weak.push(entry);
        else if (data.multiplier < 1) sections.resist.push(entry);
      } catch (err) { /* skip */ }
    }

    sections.weak.sort((a, b) => b.multiplier - a.multiplier);
    sections.resist.sort((a, b) => a.multiplier - b.multiplier);

    function renderChips(entries) {
      if (entries.length === 0) return '<span class="text-muted">None</span>';
      return entries.map(e =>
        `<div class="matchup-chip">
          <span class="type-badge ${e.type}">${capitalize(e.type)}</span>
          <span class="mult">${e.label}</span>
        </div>`
      ).join('');
    }

    container.innerHTML = `
      <div class="matchup-section">
        <div class="matchup-title">⚠️ Weak To</div>
        <div class="matchup-list">${renderChips(sections.weak)}</div>
      </div>
      <div class="matchup-section">
        <div class="matchup-title">🛡️ Resists</div>
        <div class="matchup-list">${renderChips(sections.resist)}</div>
      </div>
      <div class="matchup-section">
        <div class="matchup-title">🚫 Immune To</div>
        <div class="matchup-list">${renderChips(sections.immune)}</div>
      </div>
    `;
  }

  document.addEventListener('DOMContentLoaded', () => {
    // Offensive calc
    populateSelect(document.getElementById('atk-type'), false);
    populateSelect(document.getElementById('def-type1'), false);
    populateSelect(document.getElementById('def-type2'), true);

    document.getElementById('atk-type')?.addEventListener('change', calcOffensive);
    document.getElementById('def-type1')?.addEventListener('change', calcOffensive);
    document.getElementById('def-type2')?.addEventListener('change', calcOffensive);

    // Defensive chart
    populateSelect(document.getElementById('chart-type1'), false);
    populateSelect(document.getElementById('chart-type2'), true);

    document.getElementById('chart-type1')?.addEventListener('change', calcDefensive);
    document.getElementById('chart-type2')?.addEventListener('change', calcDefensive);

    // Trigger initial calc
    calcOffensive();
  });
})();
