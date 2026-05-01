/**
 * SidebarManager — Controla os 3 estados da sidebar do Mini ERP
 *
 * Estados:
 *   1. Colapsado  — somente ícones (64px), estado padrão
 *   2. Fixado     — sidebar permanece expandida quando o usuário fixa manualmente
 *
 * Persistência : localStorage  (chave STORAGE_KEY)
 * Mobile       : overlay tipo hambúrguer, sem hover
 * Acessibilidade: aria-expanded, aria-pressed, aria-label, focus-visible
 */

(function () {
  'use strict';

  /* ---------------------------------------------------------------
     CONSTANTES
  --------------------------------------------------------------- */
  var STORAGE_KEY      = 'mini_erp_sidebar_pinned';
  var BREAKPOINT_MOBILE = 768;  // px

  /* ---------------------------------------------------------------
     REFERÊNCIAS DOM (preenchidas em init)
  --------------------------------------------------------------- */
  var sidebar        = null;  // <aside class="sidebar">
  var appLayout      = null;  // <div class="app-layout">
  var pinBtn         = null;  // botão de fixar/desafixar
  var hamburgerBtn   = null;  // botão hambúrguer (mobile)
  var mobileOverlay  = null;  // overlay escuro mobile

  /* ---------------------------------------------------------------
     ESTADO
  --------------------------------------------------------------- */
  var state = {
    pinned     : false,  // sidebar fixada permanentemente
    hovered    : false,  // reservado para compatibilidade de eventos
    mobileOpen : false   // menu mobile aberto
  };

  var expandTimer = null;    // reservado para compatibilidade
  var collapseTimer = null;  // reservado para compatibilidade
  var motionTimer = null;    // limpa classes transitórias de animação

  /* ---------------------------------------------------------------
     UTILIDADES
  --------------------------------------------------------------- */

  function isMobile() {
    return window.innerWidth <= BREAKPOINT_MOBILE;
  }

  function loadPinState() {
    try {
      return localStorage.getItem(STORAGE_KEY) === 'true';
    } catch (e) {
      return false;
    }
  }

  function savePinState(pinned) {
    try {
      localStorage.setItem(STORAGE_KEY, pinned ? 'true' : 'false');
    } catch (e) { /* silent */ }
  }

  function clearHoverTimers() {
    clearTimeout(expandTimer);
    clearTimeout(collapseTimer);
  }

  function syncBodySidebarState() {
    if (!sidebar) return;
    var expanded = sidebar.classList.contains('is-expanded') ||
      sidebar.classList.contains('is-pinned') ||
      sidebar.classList.contains('mobile-open');
    document.body.classList.toggle('sidebar-expanded-state', expanded);
  }

  function syncLayoutPinState() {
    if (!appLayout) return;
    appLayout.classList.toggle('sidebar-is-pinned', !!state.pinned && !isMobile());
  }

  function setMotionState(mode) {
    if (!sidebar) return;
    clearTimeout(motionTimer);
    sidebar.classList.remove('is-opening', 'is-closing');
    if (mode === 'open') {
      sidebar.classList.add('is-opening');
    } else if (mode === 'close') {
      sidebar.classList.add('is-closing');
    }
    motionTimer = setTimeout(function () {
      sidebar.classList.remove('is-opening', 'is-closing');
    }, 340);
  }

  /* ---------------------------------------------------------------
     CONTROLE DE ESTADO — DESKTOP
  --------------------------------------------------------------- */

  /** Expande a sidebar (hover ou pin). */
  function expand() {
    if (!sidebar) return;
    setMotionState('open');
    sidebar.classList.add('is-expanded');
    sidebar.setAttribute('aria-expanded', 'true');
    syncBodySidebarState();
    syncFlyoutAwareness();
    dispatch('expanded');
  }

  /** Colapsa a sidebar (volta a somente ícones). */
  function collapse() {
    if (!sidebar || state.pinned) return;
    setMotionState('close');
    sidebar.classList.remove('is-expanded');
    sidebar.setAttribute('aria-expanded', 'false');
    syncBodySidebarState();
    syncFlyoutAwareness();
    dispatch('collapsed');
  }

  /** Fixa a sidebar expandida permanentemente. */
  function pin() {
    if (!sidebar || !pinBtn) return;
    state.pinned = true;
    clearHoverTimers();

    sidebar.classList.add('is-pinned', 'is-expanded');
    sidebar.setAttribute('aria-expanded', 'true');
    syncBodySidebarState();
    syncLayoutPinState();

    /* Visual do botão pin */
    pinBtn.classList.add('is-active');
    pinBtn.setAttribute('aria-label', 'Desafixar menu lateral');
    pinBtn.setAttribute('title', 'Desafixar menu');
    pinBtn.setAttribute('aria-pressed', 'true');

    /* Abre automaticamente a seção ativa ao fixar */
    var sectionsWrap = document.getElementById('sidebar-sections');
    if (sectionsWrap) {
      var activeSection = sectionsWrap.querySelector('.menu-section.has-active');
      if (activeSection) activeSection.classList.add('is-inline-open');
    }

    savePinState(true);
    dispatch('pinned');
  }

  /** Desfixa a sidebar — volta ao comportamento de hover. */
  function unpin() {
    if (!sidebar || !pinBtn) return;
    state.pinned = false;
    clearHoverTimers();

    sidebar.classList.remove('is-pinned', 'is-expanded');
    sidebar.setAttribute('aria-expanded', 'false');
    syncBodySidebarState();
    syncLayoutPinState();

    pinBtn.classList.remove('is-active');
    pinBtn.setAttribute('aria-label', 'Fixar menu lateral');
    pinBtn.setAttribute('title', 'Fixar menu');
    pinBtn.setAttribute('aria-pressed', 'false');

    savePinState(false);
    dispatch('unpinned');
  }

  /* ---------------------------------------------------------------
     CONTROLE DE ESTADO — MOBILE
  --------------------------------------------------------------- */

  function openMobile() {
    if (!sidebar || !mobileOverlay) return;
    state.mobileOpen = true;
    closeAllInlineSections();

    sidebar.classList.add('mobile-open');
    mobileOverlay.classList.add('is-visible');
    document.body.classList.add('sidebar-mobile-open');
    syncBodySidebarState();

    if (hamburgerBtn) {
      hamburgerBtn.setAttribute('aria-expanded', 'true');
      hamburgerBtn.setAttribute('aria-label', 'Fechar menu lateral');
    }
    openActiveSection();
    dispatch('mobile-opened');
  }

  function closeMobile() {
    if (!sidebar || !mobileOverlay) return;
    state.mobileOpen = false;
    closeAllInlineSections();

    sidebar.classList.remove('mobile-open');
    mobileOverlay.classList.remove('is-visible');
    document.body.classList.remove('sidebar-mobile-open');
    syncBodySidebarState();

    if (hamburgerBtn) {
      hamburgerBtn.setAttribute('aria-expanded', 'false');
      hamburgerBtn.setAttribute('aria-label', 'Abrir menu lateral');
    }
    dispatch('mobile-closed');
  }

  function toggleMobile() {
    if (state.mobileOpen) { closeMobile(); } else { openMobile(); }
  }

    /* ---------------------------------------------------------------
      HOVER HANDLERS (somente desktop)
      Sidebar não expande mais por hover: expansão ocorre apenas com pin.
    --------------------------------------------------------------- */

  function onMouseEnter() {
    if (isMobile() || state.pinned) return;
    state.hovered = false;
  }

  function onMouseLeave() {
    if (isMobile() || state.pinned) return;
    state.hovered = false;
  }

  /* ---------------------------------------------------------------
     DISPATCH EVENTOS (integração com outros módulos)
  --------------------------------------------------------------- */

  function dispatch(eventName) {
    try {
      document.dispatchEvent(new CustomEvent('sidebar-' + eventName, {
        detail: { pinned: state.pinned, mobileOpen: state.mobileOpen }
      }));
    } catch (e) { /* IE fallback — eventos sem detail */ }
  }

  /* ---------------------------------------------------------------
     SEÇÕES INLINE (quando sidebar está expandida)
     Quando expandido, seções podem ser abertas inline (accordion).
     O flyout continua funcionando quando colapsado.
  --------------------------------------------------------------- */

  function openActiveSection() {
    if (!isMobile()) return;
    if (!sidebar) return;
    var sectionsWrap = document.getElementById('sidebar-sections');
    if (!sectionsWrap) return;

    /* Abre a seção que contém o link ativo */
    var activeSection = sectionsWrap.querySelector('.menu-section.has-active');
    if (activeSection) {
      var body = activeSection.querySelector('.menu-section-body');
      if (body) {
        body.hidden = false;
        activeSection.classList.add('is-inline-open');
      }
    }
  }

  function closeAllInlineSections() {
    var sectionsWrap = document.getElementById('sidebar-sections');
    if (!sectionsWrap) return;
    sectionsWrap.querySelectorAll('.menu-section').forEach(function (s) {
      s.classList.remove('is-inline-open');
      var body = s.querySelector('.menu-section-body');
      if (body) body.hidden = true;
    });
  }

  /* ---------------------------------------------------------------
     SYNC COM FLYOUT (comunica estado ao bindFlyoutMenu em base.html)
     A variável global `window.sidebarIsExpanded` é lida pelo flyout.
  --------------------------------------------------------------- */

  function syncFlyoutAwareness() {
    window.sidebarIsExpanded = sidebar
      ? sidebar.classList.contains('is-expanded')
      : false;
  }

  /* ---------------------------------------------------------------
     INICIALIZAÇÃO
  --------------------------------------------------------------- */

  function init() {
    appLayout     = document.querySelector('.app-layout');
    sidebar       = document.querySelector('.sidebar');
    pinBtn        = document.getElementById('sidebar-pin-btn');
    hamburgerBtn  = document.getElementById('sidebar-hamburger-btn');
    mobileOverlay = document.getElementById('sidebar-mobile-overlay');

    if (!sidebar) return;

    /* Aria inicial */
    sidebar.setAttribute('aria-expanded', 'false');
    sidebar.setAttribute('role', 'navigation');
    sidebar.setAttribute('aria-label', 'Menu lateral');
    syncBodySidebarState();
    syncLayoutPinState();

    /* Restaura preferência do usuário */
    state.pinned = loadPinState();
    if (state.pinned && !isMobile()) {
      pin();
    }

    /* ----- Botão PIN ----- */
    if (pinBtn) {
      pinBtn.setAttribute('aria-pressed', state.pinned ? 'true' : 'false');
      pinBtn.setAttribute('aria-label', state.pinned ? 'Desafixar menu lateral' : 'Fixar menu lateral');
      pinBtn.setAttribute('title',      state.pinned ? 'Desafixar menu'         : 'Fixar menu');

      pinBtn.addEventListener('click', function (e) {
        e.stopPropagation();
        if (state.pinned) {
          unpin();
        } else {
          pin();
        }
      });

      pinBtn.addEventListener('keydown', function (e) {
        if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); pinBtn.click(); }
      });
    }

    /* ----- Botão HAMBÚRGUER ----- */
    if (hamburgerBtn) {
      hamburgerBtn.setAttribute('aria-expanded', 'false');
      hamburgerBtn.setAttribute('aria-label', 'Abrir menu lateral');
      hamburgerBtn.addEventListener('click', toggleMobile);
    }

    /* ----- Overlay mobile ----- */
    if (mobileOverlay) {
      mobileOverlay.addEventListener('click', closeMobile);
    }

    /* ----- Hover desktop ----- */
    sidebar.addEventListener('mouseenter', function () {
      onMouseEnter();
    });
    sidebar.addEventListener('mouseleave', function () {
      onMouseLeave();
    });

    /* ----- Seções inline (accordion quando expandido) ----- */
    var sectionsWrap = document.getElementById('sidebar-sections');
    if (sectionsWrap) {
      sectionsWrap.addEventListener('click', function (e) {
        var header = e.target.closest('.menu-section-header');
        if (!header) return;

        var isAccordionMode = isMobile() && sidebar.classList.contains('mobile-open');
        if (!isAccordionMode) return; /* No desktop o submenu é sempre flyout lateral */

        e.stopPropagation();
        var section = header.closest('.menu-section');
        if (!section) return;

        var body = section.querySelector('.menu-section-body');
        var links = body ? body.querySelectorAll('.nav-link') : [];

        /* Seção com apenas 1 link: navega diretamente */
        if (links.length === 1) {
          window.location.href = links[0].href;
          return;
        }

        var isOpen = section.classList.contains('is-inline-open');

        /* Fecha as outras seções (accordion) */
        sectionsWrap.querySelectorAll('.menu-section.is-inline-open').forEach(function (s) {
          if (s !== section) {
            s.classList.remove('is-inline-open');
            var b = s.querySelector('.menu-section-body');
            if (b) b.hidden = true;
          }
        });

        /* Alterna a seção clicada */
        section.classList.toggle('is-inline-open', !isOpen);
        if (body) body.hidden = isOpen;
      });
    }

    /* ----- Colapsa menu mobile ao clicar em link ----- */
    sidebar.addEventListener('click', function (e) {
      if (isMobile() && e.target.closest('.nav-link')) {
        closeMobile();
      }
    });

    /* ----- Fecha menu mobile ao redimensionar para desktop ----- */
    window.addEventListener('resize', function () {
      if (!isMobile() && state.mobileOpen) {
        closeMobile();
      }
      if (!isMobile()) {
        closeAllInlineSections();
      }
      /* Aplica pin state correto ao voltar para desktop */
      if (!isMobile() && state.pinned && !sidebar.classList.contains('is-pinned')) {
        pin();
      }
      syncLayoutPinState();
    });

    /* ----- Escape fecha mobile ----- */
    document.addEventListener('keydown', function (e) {
      if (e.key === 'Escape') {
        if (state.mobileOpen) { closeMobile(); }
      }
    });

    /* ----- Sync inicial com flyout ----- */
    syncFlyoutAwareness();
  }

  /* DOM pronto */
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }

})();
