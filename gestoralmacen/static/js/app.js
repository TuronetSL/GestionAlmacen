/* ============================================================
   GestorAlmacén Pro – App JS
   Química del Sur S.L.
   ============================================================ */

(function () {
  'use strict';

  /* ── Sidebar collapse / expand ─────────────────────────── */
  function initSidebar() {
    // Department group toggles
    document.querySelectorAll('.nav-section-header').forEach(function (header) {
      header.addEventListener('click', function () {
        var section = header.closest('.nav-section');
        if (!section) return;
        var isOpen = section.classList.contains('open');
        // Close all open sections
        document.querySelectorAll('.nav-section.open').forEach(function (s) {
          s.classList.remove('open');
        });
        // Toggle this one
        if (!isOpen) {
          section.classList.add('open');
        }
      });
    });

    // Sidebar collapse button (desktop)
    var sidebar = document.getElementById('sidebar');
    var toggleBtn = document.getElementById('sidebarToggle');
    if (toggleBtn && sidebar) {
      toggleBtn.addEventListener('click', function () {
        sidebar.classList.toggle('collapsed');
        var isCollapsed = sidebar.classList.contains('collapsed');
        localStorage.setItem('sidebarCollapsed', isCollapsed ? '1' : '0');
      });
    }

    // Restore collapsed state
    if (sidebar && localStorage.getItem('sidebarCollapsed') === '1') {
      sidebar.classList.add('collapsed');
    }

    // Mobile sidebar toggle
    var mobileToggle = document.getElementById('mobileToggle');
    var backdrop = document.getElementById('sidebarBackdrop');

    if (mobileToggle && sidebar) {
      mobileToggle.addEventListener('click', function () {
        sidebar.classList.toggle('mobile-open');
        if (backdrop) backdrop.classList.toggle('visible');
      });
    }

    if (backdrop && sidebar) {
      backdrop.addEventListener('click', function () {
        sidebar.classList.remove('mobile-open');
        backdrop.classList.remove('visible');
      });
    }
  }

  /* ── Active nav item ───────────────────────────────────── */
  function initActiveNav() {
    var path = window.location.pathname;

    document.querySelectorAll('.nav-item[data-url]').forEach(function (item) {
      var url = item.getAttribute('data-url');
      if (!url) return;

      // Exact match or starts-with match
      if (path === url || (url !== '/' && path.startsWith(url))) {
        item.classList.add('active');

        // Open parent section
        var section = item.closest('.nav-section');
        if (section) {
          section.classList.add('open');
          var header = section.querySelector('.nav-section-header');
          if (header) header.classList.add('active');
        }
      }
    });
  }

  /* ── Modals ────────────────────────────────────────────── */
  function initModals() {
    // Open buttons
    document.addEventListener('click', function (e) {
      var trigger = e.target.closest('[data-modal]');
      if (trigger) {
        var modalId = trigger.getAttribute('data-modal');
        var modal = document.getElementById(modalId);
        if (modal) {
          modal.classList.add('active');
          document.body.style.overflow = 'hidden';
        }
        return;
      }

      // Close buttons
      var closeBtn = e.target.closest('.modal-close');
      if (closeBtn) {
        var overlay = closeBtn.closest('.modal-overlay');
        if (overlay) {
          overlay.classList.remove('active');
          document.body.style.overflow = '';
        }
        return;
      }

      // Click outside modal
      if (e.target.classList.contains('modal-overlay')) {
        e.target.classList.remove('active');
        document.body.style.overflow = '';
      }
    });

    // ESC key
    document.addEventListener('keydown', function (e) {
      if (e.key === 'Escape') {
        document.querySelectorAll('.modal-overlay.active').forEach(function (m) {
          m.classList.remove('active');
          document.body.style.overflow = '';
        });
      }
    });
  }

  /* ── Flash messages auto-dismiss ──────────────────────── */
  function initFlash() {
    document.querySelectorAll('.flash').forEach(function (flash) {
      // Manual close
      var closeBtn = flash.querySelector('.flash-close');
      if (closeBtn) {
        closeBtn.addEventListener('click', function () {
          dismissFlash(flash);
        });
      }

      // Auto-dismiss after 4 seconds
      setTimeout(function () {
        dismissFlash(flash);
      }, 4000);
    });
  }

  function dismissFlash(flash) {
    flash.style.transition = 'opacity 0.3s, transform 0.3s';
    flash.style.opacity = '0';
    flash.style.transform = 'translateY(-8px)';
    setTimeout(function () {
      if (flash.parentNode) flash.parentNode.removeChild(flash);
    }, 300);
  }

  /* ── Confirm delete dialogs ────────────────────────────── */
  function initConfirmDelete() {
    document.addEventListener('click', function (e) {
      var btn = e.target.closest('[data-confirm]');
      if (!btn) return;

      var message = btn.getAttribute('data-confirm') || '¿Está seguro de que desea eliminar este registro?';
      if (!window.confirm(message)) {
        e.preventDefault();
        e.stopPropagation();
      }
    });
  }

  /* ── Form loading state ────────────────────────────────── */
  function initFormLoading() {
    document.addEventListener('submit', function (e) {
      var form = e.target;
      if (form.classList.contains('no-loading')) return;

      var submitBtn = form.querySelector('[type="submit"]');
      if (submitBtn && !submitBtn.disabled) {
        submitBtn.classList.add('loading');
        submitBtn.disabled = true;

        // Safety fallback: re-enable after 8s
        setTimeout(function () {
          submitBtn.classList.remove('loading');
          submitBtn.disabled = false;
        }, 8000);
      }
    });
  }

  /* ── Search debounce ───────────────────────────────────── */
  function debounce(fn, delay) {
    var timer;
    return function () {
      var args = arguments;
      var ctx = this;
      clearTimeout(timer);
      timer = setTimeout(function () {
        fn.apply(ctx, args);
      }, delay);
    };
  }

  function initSearchFilter() {
    // Client-side table filter for .filter-input paired with data-table
    document.querySelectorAll('.filter-input[data-table]').forEach(function (input) {
      var tableId = input.getAttribute('data-table');
      var table = document.getElementById(tableId);
      if (!table) return;

      var rows = table.querySelectorAll('tbody tr');

      var doFilter = debounce(function () {
        var q = input.value.toLowerCase().trim();
        rows.forEach(function (row) {
          var text = row.textContent.toLowerCase();
          row.style.display = q === '' || text.includes(q) ? '' : 'none';
        });
      }, 250);

      input.addEventListener('input', doFilter);
    });

    // Select filter
    document.querySelectorAll('.filter-select[data-table][data-col]').forEach(function (select) {
      var tableId = select.getAttribute('data-table');
      var colIdx = parseInt(select.getAttribute('data-col'), 10);
      var table = document.getElementById(tableId);
      if (!table || isNaN(colIdx)) return;

      var rows = table.querySelectorAll('tbody tr');

      select.addEventListener('change', function () {
        var val = select.value.toLowerCase().trim();
        rows.forEach(function (row) {
          var cell = row.cells[colIdx];
          if (!cell) return;
          row.style.display = val === '' || cell.textContent.toLowerCase().includes(val) ? '' : 'none';
        });
      });
    });
  }

  /* ── Tabs ──────────────────────────────────────────────── */
  function initTabs() {
    document.querySelectorAll('.tabs').forEach(function (tabs) {
      var buttons = tabs.querySelectorAll('.tab-btn');
      buttons.forEach(function (btn) {
        btn.addEventListener('click', function () {
          // Deactivate all in this tab group
          buttons.forEach(function (b) { b.classList.remove('active'); });
          btn.classList.add('active');

          var target = btn.getAttribute('data-tab');
          var container = tabs.closest('.tabs-container') || document;
          container.querySelectorAll('.tab-content').forEach(function (content) {
            content.classList.toggle('active', content.id === target);
          });
        });
      });
    });
  }

  /* ── Topbar search (global redirect) ──────────────────── */
  function initTopbarSearch() {
    var form = document.getElementById('globalSearchForm');
    if (!form) return;

    form.addEventListener('submit', function (e) {
      e.preventDefault();
      var q = form.querySelector('input').value.trim();
      if (q) {
        window.location.href = '/buscar?q=' + encodeURIComponent(q);
      }
    });
  }

  /* ── Auto-open section if active item inside ───────────── */
  function initAutoOpenSection() {
    document.querySelectorAll('.nav-section').forEach(function (section) {
      if (section.querySelector('.nav-item.active')) {
        section.classList.add('open');
      }
    });
  }

  /* ── Notification bell ─────────────────────────────────── */
  function initNotifications() {
    var bell = document.getElementById('notifBell');
    var panel = document.getElementById('notifPanel');
    if (!bell || !panel) return;

    bell.addEventListener('click', function (e) {
      e.stopPropagation();
      panel.classList.toggle('active');
    });

    document.addEventListener('click', function () {
      if (panel) panel.classList.remove('active');
    });
  }

  /* ── Smooth number animation for KPI values ────────────── */
  function animateNumbers() {
    document.querySelectorAll('.kpi-value[data-value]').forEach(function (el) {
      var target = parseFloat(el.getAttribute('data-value'));
      if (isNaN(target)) return;
      var start = 0;
      var duration = 800;
      var startTime = null;
      var isInt = Number.isInteger(target);

      function step(ts) {
        if (!startTime) startTime = ts;
        var progress = Math.min((ts - startTime) / duration, 1);
        var eased = 1 - Math.pow(1 - progress, 3);
        var current = eased * target;
        el.textContent = isInt ? Math.round(current).toLocaleString('es-ES') : current.toFixed(2);
        if (progress < 1) requestAnimationFrame(step);
      }

      requestAnimationFrame(step);
    });
  }

  /* ── Init ──────────────────────────────────────────────── */
  document.addEventListener('DOMContentLoaded', function () {
    initSidebar();
    initActiveNav();
    initAutoOpenSection();
    initModals();
    initFlash();
    initConfirmDelete();
    initFormLoading();
    initSearchFilter();
    initTabs();
    initTopbarSearch();
    initNotifications();
    animateNumbers();
  });

})();
