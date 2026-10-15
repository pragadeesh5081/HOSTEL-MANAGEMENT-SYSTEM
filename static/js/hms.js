/* hms.js — reusable animations, sidebar, toast, counter, search */

/* ── Sidebar ─────────────────────────────────────────────── */
(function initSidebar() {
  const sidebar   = document.getElementById('hmsSidebar');
  const main      = document.getElementById('hmsMain');
  const toggleBtn = document.getElementById('sidebarToggle');
  const mobileBtn = document.getElementById('mobileSidebarBtn');
  const backdrop  = document.getElementById('sidebarBackdrop');
  if (!sidebar) return;

  const COLLAPSED_KEY = 'hms_sidebar_collapsed';
  if (localStorage.getItem(COLLAPSED_KEY) === 'true') {
    sidebar.classList.add('collapsed');
    if (main) main.classList.add('expanded');
    if (toggleBtn) toggleBtn.querySelector('.toggle-icon') && (toggleBtn.querySelector('.toggle-icon').style.transform = 'rotate(180deg)');
  }

  if (toggleBtn) {
    toggleBtn.addEventListener('click', () => {
      const isCollapsed = sidebar.classList.toggle('collapsed');
      if (main) main.classList.toggle('expanded', isCollapsed);
      localStorage.setItem(COLLAPSED_KEY, isCollapsed);
    });
  }

  if (mobileBtn) {
    mobileBtn.addEventListener('click', () => {
      sidebar.classList.add('mobile-open');
      if (backdrop) backdrop.classList.add('active');
      document.body.style.overflow = 'hidden';
    });
  }

  if (backdrop) {
    backdrop.addEventListener('click', closeMobile);
  }

  function closeMobile() {
    sidebar.classList.remove('mobile-open');
    if (backdrop) backdrop.classList.remove('active');
    document.body.style.overflow = '';
  }
})();

/* ── Animated Counter ────────────────────────────────────── */
function animateCounter(el, target, duration = 1200) {
  const start = 0;
  const step  = target / (duration / 16);
  let   current = start;
  el.textContent = '0';

  function tick() {
    current += step;
    if (current >= target) {
      el.textContent = formatNumber(target);
      return;
    }
    el.textContent = formatNumber(Math.floor(current));
    requestAnimationFrame(tick);
  }
  requestAnimationFrame(tick);
}

function formatNumber(n) {
  return n.toLocaleString();
}

/* Run counters when elements enter viewport */
(function initCounters() {
  const counters = document.querySelectorAll('[data-count]');
  if (!counters.length) return;

  const io = new IntersectionObserver((entries) => {
    entries.forEach(e => {
      if (e.isIntersecting) {
        const target = parseInt(e.target.getAttribute('data-count'), 10);
        animateCounter(e.target, target);
        io.unobserve(e.target);
      }
    });
  }, { threshold: 0.3 });

  counters.forEach(c => io.observe(c));
})();

/* ── Toast Notifications ─────────────────────────────────── */
window.hmsToast = (function () {
  let container = document.getElementById('hmsToastContainer');
  if (!container) {
    container = document.createElement('div');
    container.id = 'hmsToastContainer';
    container.className = 'hms-toast-container';
    document.body.appendChild(container);
  }

  const ICONS = {
    success: '<i class="bi bi-check-circle-fill toast-icon toast-icon-success"></i>',
    danger : '<i class="bi bi-x-circle-fill  toast-icon toast-icon-danger"></i>',
    warning: '<i class="bi bi-exclamation-triangle-fill toast-icon toast-icon-warning"></i>',
    info   : '<i class="bi bi-info-circle-fill toast-icon toast-icon-info"></i>',
  };

  function show(message, type = 'info', duration = 4000) {
    const toast = document.createElement('div');
    toast.className = `hms-toast toast-${type}`;
    toast.innerHTML = `
      ${ICONS[type] || ICONS.info}
      <span class="toast-msg">${message}</span>
      <button class="toast-close" aria-label="Close">&times;</button>`;
    container.appendChild(toast);

    const closeBtn = toast.querySelector('.toast-close');
    closeBtn.addEventListener('click', () => dismiss(toast));

    const timer = setTimeout(() => dismiss(toast), duration);
    toast._timer = timer;
    return toast;
  }

  function dismiss(toast) {
    clearTimeout(toast._timer);
    toast.classList.add('hiding');
    toast.addEventListener('animationend', () => toast.remove(), { once: true });
    setTimeout(() => toast.remove(), 500);
  }

  return { show, dismiss };
})();

/* Convert server-rendered flash messages to toasts */
(function convertFlashMessages() {
  const flashes = document.querySelectorAll('[data-flash]');
  flashes.forEach(el => {
    const msg  = el.getAttribute('data-flash');
    const type = el.getAttribute('data-flash-type') || 'info';
    hmsToast.show(msg, type);
    el.remove();
  });
})();

/* ── Scroll Reveal ───────────────────────────────────────── */
(function initScrollReveal() {
  const items = document.querySelectorAll('.reveal-on-scroll');
  if (!items.length) return;

  const io = new IntersectionObserver((entries) => {
    entries.forEach(e => {
      if (e.isIntersecting) {
        e.target.classList.add('animate-fade-in-up');
        io.unobserve(e.target);
      }
    });
  }, { threshold: 0.1 });

  items.forEach(i => io.observe(i));
})();

/* ── Search Table Filter ─────────────────────────────────── */
(function initTableSearch() {
  document.querySelectorAll('[data-search-table]').forEach(input => {
    const tableId = input.getAttribute('data-search-table');
    const table   = document.getElementById(tableId);
    if (!table) return;

    input.addEventListener('input', () => {
      const q = input.value.toLowerCase().trim();
      table.querySelectorAll('tbody tr').forEach(row => {
        const text = row.textContent.toLowerCase();
        row.style.display = (!q || text.includes(q)) ? '' : 'none';
      });
    });
  });
})();

/* ── Dropdown Filter for Tables ──────────────────────────── */
(function initFilterSelect() {
  document.querySelectorAll('[data-filter-col]').forEach(select => {
    const tableId = select.getAttribute('data-filter-table');
    const col     = parseInt(select.getAttribute('data-filter-col'), 10);
    const table   = document.getElementById(tableId);
    if (!table) return;

    select.addEventListener('change', () => {
      const val = select.value.toLowerCase();
      table.querySelectorAll('tbody tr').forEach(row => {
        const cell = row.cells[col];
        const text = cell ? cell.textContent.toLowerCase() : '';
        row.style.display = (!val || text.includes(val)) ? '' : 'none';
      });
    });
  });
})();

/* ── Room Grid Filter Animation ──────────────────────────── */
(function initRoomFilter() {
  const filterBtns = document.querySelectorAll('[data-room-filter]');
  if (!filterBtns.length) return;

  filterBtns.forEach(btn => {
    btn.addEventListener('click', () => {
      filterBtns.forEach(b => b.classList.remove('active', 'btn-hms-primary'));
      btn.classList.add('active', 'btn-hms-primary');

      const filter = btn.getAttribute('data-room-filter');
      document.querySelectorAll('.room-card').forEach(card => {
        const match = !filter || card.getAttribute('data-status') === filter
                      || filter === 'all';
        card.style.transition = 'opacity 0.3s, transform 0.3s';
        if (match) {
          card.style.opacity = '1';
          card.style.transform = '';
          card.style.display = '';
        } else {
          card.style.opacity = '0';
          card.style.transform = 'scale(0.95)';
          setTimeout(() => { if (card.style.opacity === '0') card.style.display = 'none'; }, 300);
        }
      });
    });
  });
})();

/* ── Progress Bars ───────────────────────────────────────── */
(function initProgressBars() {
  const io = new IntersectionObserver((entries) => {
    entries.forEach(e => {
      if (e.isIntersecting) {
        const bar = e.target;
        const pct = bar.getAttribute('data-progress') || '0';
        bar.style.setProperty('--progress', pct + '%');
        bar.style.width = pct + '%';
        io.unobserve(bar);
      }
    });
  }, { threshold: 0.2 });

  document.querySelectorAll('.hms-progress-bar[data-progress]').forEach(b => io.observe(b));
})();

/* ── Announcement Expand/Collapse ────────────────────────── */
(function initAnnExpand() {
  document.querySelectorAll('.ann-toggle').forEach(btn => {
    btn.addEventListener('click', () => {
      const content = btn.closest('.announcement-card').querySelector('.ann-collapsible');
      if (!content) return;
      const expanded = content.classList.toggle('expanded');
      btn.textContent = expanded ? 'Show less' : 'Read more';
    });
  });
})();

/* ── Confirmation Dialog ─────────────────────────────────── */
document.querySelectorAll('[data-confirm]').forEach(el => {
  el.addEventListener('click', function (e) {
    const msg = this.getAttribute('data-confirm') || 'Are you sure?';
    if (!confirm(msg)) e.preventDefault();
  });
});

/* ── Button Loading State ────────────────────────────────── */
document.querySelectorAll('form').forEach(form => {
  form.addEventListener('submit', function () {
    const btn = this.querySelector('[data-loading]');
    if (btn) {
      btn.classList.add('btn-loading');
      btn.disabled = true;
    }
  });
});

/* ── Tooltip initialization (Bootstrap) ─────────────────── */
(function () {
  if (typeof bootstrap !== 'undefined' && bootstrap.Tooltip) {
    document.querySelectorAll('[data-bs-toggle="tooltip"]')
      .forEach(el => new bootstrap.Tooltip(el));
  }
})();
