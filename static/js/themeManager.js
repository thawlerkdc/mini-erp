/**
 * Global Theme Manager - Gerencia tema claro/escuro em todo o sistema
 * Persistência: localStorage
 * Aplicação: Automática ao carregar página + toggleável via menu de usuário
 */

(function() {
  const THEME_KEY = 'mini_erp_app_theme';
  const THEME_LIGHT = 'light';
  const THEME_DARK = 'dark';

  /**
   * Obtém preferência de tema do localStorage
   */
  function getStoredTheme() {
    try {
      return localStorage.getItem(THEME_KEY) || THEME_LIGHT;
    } catch (e) {
      return THEME_LIGHT;
    }
  }

  /**
   * Salva preferência de tema no localStorage
   */
  function setStoredTheme(theme) {
    try {
      localStorage.setItem(THEME_KEY, theme);
    } catch (e) {
      console.warn('Não foi possível salvar preferência de tema');
    }
  }

  /**
   * Aplica tema ao documento
   */
  function applyTheme(theme) {
    const isDark = theme === THEME_DARK;
    
    // Aplicar classe ao body
    document.body.classList.toggle('theme-dark', isDark);
    document.body.classList.toggle('theme-light', !isDark);
    
    // Atualizar atributo data para acesso via CSS/JS
    document.documentElement.setAttribute('data-theme', isDark ? 'dark' : 'light');
    
    // Atualizar botões no menu do usuário (se existirem)
    updateThemeButtons(theme);
  }

  /**
   * Atualiza estado visual dos botões de tema no menu
   */
  function updateThemeButtons(theme) {
    const lightBtn = document.getElementById('theme-light-btn');
    const darkBtn = document.getElementById('theme-dark-btn');
    
    if (lightBtn) {
      lightBtn.classList.toggle('active', theme === THEME_LIGHT);
    }
    if (darkBtn) {
      darkBtn.classList.toggle('active', theme === THEME_DARK);
    }
  }

  /**
   * Alterna para um tema específico
   */
  window.switchTheme = function(theme) {
    if ([THEME_LIGHT, THEME_DARK].includes(theme)) {
      applyTheme(theme);
      setStoredTheme(theme);
    }
  };

  /**
   * Inicializa tema ao carregar página
   */
  function initializeTheme() {
    const savedTheme = getStoredTheme();
    applyTheme(savedTheme);
  }

  // Aplicar tema AINDA mais cedo se possível (antes de pintura)  
  // Isso previne flash de tema errado ao carregar página
  const savedTheme = getStoredTheme();
  if (savedTheme === THEME_DARK) {
    document.documentElement.classList.add('theme-dark-pending');
  }

  // Inicializar assim que o DOM estiver pronto
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initializeTheme);
  } else {
    initializeTheme();
  }
})();
