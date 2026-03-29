// tabs.js — Tab switching for detail page
(function() {
  document.addEventListener('DOMContentLoaded', () => {
    document.querySelectorAll('.tabs').forEach(tabsContainer => {
      const btns = tabsContainer.querySelectorAll('.tab-btn');
      const panels = tabsContainer.parentElement.querySelectorAll('.tab-panel');

      btns.forEach(btn => {
        btn.addEventListener('click', () => {
          const target = btn.dataset.tab;

          btns.forEach(b => b.classList.remove('active'));
          btn.classList.add('active');

          panels.forEach(panel => {
            panel.classList.toggle('active', panel.id === target);
          });
        });
      });
    });
  });
})();
