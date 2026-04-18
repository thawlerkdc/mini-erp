/**
 * GERENCIADOR DE TEMAS - ALUMnO/ESCURO RESPONSIVO
 * 
 * Funcionalidades:
 * - Detecção automática de preferência do sistema
 * - Alternância automática baseada em horário
 * - Toggle manual com persistência em localStorage
 * - Transições suaves entre temas
 */

class ThemeManager {
  constructor() {
    this.STORAGE_KEY = 'theme-preference';
    this.THEME_AUTO = 'auto';
    this.THEME_LIGHT = 'light';
    this.THEME_DARK = 'dark';
    
    // Horários para alternância automática
    this.HOUR_LIGHT_START = 6;    // 06:00
    this.HOUR_DARK_START = 18;    // 18:00
    
    this.currentTheme = null;
    this.isAutoMode = true;
    this.autoCheckInterval = null;
    
    this.initialize();
  }

  /**
   * Inicializa o gerenciador de temas
   */
  initialize() {
    // Obter preferência salva do localStorage
    const savedPreference = this.getSavedPreference();
    
    if (savedPreference === this.THEME_AUTO || savedPreference === null) {
      this.isAutoMode = true;
      this.applyAutoTheme();
      this.startAutoCheck();
    } else {
      this.isAutoMode = false;
      this.setTheme(savedPreference);
    }
    
    // Detectar mudanças na preferência do sistema
    this.watchSystemPreference();
    
    // Atualizar a cada minuto para ajustes de hora
    this.startAutoCheck();
  }

  /**
   * Salva a preferência no localStorage
   */
  savePreference(preference) {
    try {
      localStorage.setItem(this.STORAGE_KEY, preference);
    } catch (e) {
      console.warn('LocalStorage não disponível:', e);
    }
  }

  /**
   * Obtém a preferência salva do localStorage
   */
  getSavedPreference() {
    try {
      return localStorage.getItem(this.STORAGE_KEY);
    } catch (e) {
      console.warn('LocalStorage não disponível:', e);
      return null;
    }
  }

  /**
   * Retorna o tema baseado no horário
   */
  getThemeByHour() {
    const now = new Date();
    const hour = now.getHours();
    
    if (hour >= this.HOUR_LIGHT_START && hour < this.HOUR_DARK_START) {
      return this.THEME_LIGHT;
    } else {
      return this.THEME_DARK;
    }
  }

  /**
   * Detecta preferência do sistema
   */
  getSystemPreference() {
    if (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches) {
      return this.THEME_DARK;
    }
    return this.THEME_LIGHT;
  }

  /**
   * Aplica o tema automático (baseado em horário se sistema for light, ou sistema se preferir dark)
   */
  applyAutoTheme() {
    const systemPreference = this.getSystemPreference();
    
    // Priorizar preferência do sistema
    if (systemPreference === this.THEME_DARK) {
      this.setTheme(this.THEME_DARK);
    } else {
      // Se preferência é light, usar lógica de horário
      const themeByHour = this.getThemeByHour();
      this.setTheme(themeByHour);
    }
  }

  /**
   * Define o tema atual e aplica ao documento
   */
  setTheme(theme) {
    if (theme !== this.THEME_LIGHT && theme !== this.THEME_DARK) {
      console.warn('Tema inválido:', theme);
      return;
    }

    // Evitar aplicação redundante
    if (this.currentTheme === theme) {
      return;
    }

    this.currentTheme = theme;
    
    // Aplicar ao atributo data-theme
    document.documentElement.setAttribute('data-theme', theme);
    document.body.setAttribute('data-theme', theme);
    
    // Atualizar cor meta do tema (para navegadores que suportam)
    this.updateMetaThemeColor(theme);
    
    // Disparar evento customizado
    this.dispatchThemeChangeEvent(theme);
    
    // Log para debug
    console.log(`🎨 Tema aplicado: ${theme} (modo: ${this.isAutoMode ? 'automático' : 'manual'})`);
  }

  /**
   * Alterna entre temas automático e manual
   */
  toggleAutoMode() {
    this.isAutoMode = !this.isAutoMode;
    
    if (this.isAutoMode) {
      this.savePreference(this.THEME_AUTO);
      this.applyAutoTheme();
      console.log('✅ Modo automático ativado');
    } else {
      console.log('❌ Modo autorático desativado');
    }
    
    this.updateToggleButton();
    return this.isAutoMode;
  }

  /**
   * Define manualmente um tema específico
   */
  setManualTheme(theme) {
    this.isAutoMode = false;
    this.savePreference(theme);
    this.setTheme(theme);
    this.updateToggleButton();
  }

  /**
   * Atualiza a cor meta do tema (Android, alguns navegadores)
   */
  updateMetaThemeColor(theme) {
    let metaThemeColor = document.querySelector('meta[name="theme-color"]');
    
    if (!metaThemeColor) {
      metaThemeColor = document.createElement('meta');
      metaThemeColor.name = 'theme-color';
      document.head.appendChild(metaThemeColor);
    }
    
    if (theme === this.THEME_DARK) {
      metaThemeColor.content = '#0f172a';
    } else {
      metaThemeColor.content = '#0b4a82';
    }
  }

  /**
   * Dispara evento customizado quando tema muda
   */
  dispatchThemeChangeEvent(theme) {
    const event = new CustomEvent('themechange', {
      detail: {
        theme: theme,
        isAuto: this.isAutoMode,
        timestamp: new Date()
      }
    });
    window.dispatchEvent(event);
  }

  /**
   * Monitora mudanças na preferência do sistema
   */
  watchSystemPreference() {
    if (!window.matchMedia) return;
    
    const darkModeQuery = window.matchMedia('(prefers-color-scheme: dark)');
    
    // Listener para mudanças de preferência
    darkModeQuery.addEventListener('change', (e) => {
      console.log('🔄 Preferência do sistema alterada');
      if (this.isAutoMode) {
        this.applyAutoTheme();
      }
    });
  }

  /**
   * Inicia verificação automática a cada minuto
   */
  startAutoCheck() {
    if (this.autoCheckInterval) {
      clearInterval(this.autoCheckInterval);
    }
    
    // Verificar a cada minuto se houve mudança de hora
    this.autoCheckInterval = setInterval(() => {
      if (this.isAutoMode) {
        const systemPreference = this.getSystemPreference();
        
        // Se preferência do sistema é dark, manter dark
        if (systemPreference === this.THEME_DARK) {
          if (this.currentTheme !== this.THEME_DARK) {
            this.setTheme(this.THEME_DARK);
          }
        } else {
          // Caso contrário, usar lógica de horário
          const themeByHour = this.getThemeByHour();
          if (this.currentTheme !== themeByHour) {
            this.setTheme(themeByHour);
          }
        }
      }
    }, 60000); // A cada 60 segundos
  }

  /**
   * Atualiza o estado visual do botão toggle
   */
  updateToggleButton() {
    const button = document.getElementById('theme-toggle-btn');
    const icon = document.getElementById('theme-toggle-icon');
    const label = document.getElementById('theme-toggle-label');
    const indicator = document.getElementById('theme-auto-indicator');
    
    if (!button) return;
    
    // Atualizar ícone
    if (icon) {
      icon.textContent = this.currentTheme === this.THEME_DARK ? '🌙' : '☀️';
    }
    
    // Atualizar label
    if (label) {
      label.textContent = this.currentTheme === this.THEME_DARK ? 'Escuro' : 'Claro';
    }
    
    // Atualizar indicador de modo
    if (indicator) {
      indicator.textContent = this.isAutoMode 
        ? `🔄 Auto (${this.currentTheme === this.THEME_DARK ? 'Noite' : 'Dia'})`
        : '👤 Manual';
      indicator.title = this.isAutoMode 
        ? 'Modo automático ativado' 
        : 'Modo manual ativado';
    }
    
    // Atributo data para CSS
    button.setAttribute('data-theme', this.currentTheme);
    button.setAttribute('data-mode', this.isAutoMode ? 'auto' : 'manual');
  }

  /**
   * Obtém o tema atual
   */
  getCurrentTheme() {
    return this.currentTheme;
  }

  /**
   * Obtém status do modo automático
   */
  getAutoModeStatus() {
    return this.isAutoMode;
  }

  /**
   * Destrói a instância e limpa listeners
   */
  destroy() {
    if (this.autoCheckInterval) {
      clearInterval(this.autoCheckInterval);
      this.autoCheckInterval = null;
    }
  }
}

/**
 * Inicialização global
 */
let themeManager = null;

document.addEventListener('DOMContentLoaded', () => {
  // Criar instância global
  themeManager = new ThemeManager();
  
  // Configurar botão toggle se existir
  const toggleButton = document.getElementById('theme-toggle-btn');
  if (toggleButton) {
    toggleButton.addEventListener('click', () => {
      themeManager.toggleAutoMode();
    });
    
    // Menu de shortcuts (se existir)
    const toggleMenuBtn = document.getElementById('theme-toggle-menu-btn');
    if (toggleMenuBtn) {
      toggleMenuBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        const menu = document.getElementById('theme-menu');
        if (menu) {
          menu.classList.toggle('hidden');
        }
      });
    }
    
    // Botões de seleção manual
    const lightBtn = document.getElementById('theme-light-btn');
    const darkBtn = document.getElementById('theme-dark-btn');
    
    if (lightBtn) {
      lightBtn.addEventListener('click', () => {
        themeManager.setManualTheme('light');
      });
    }
    
    if (darkBtn) {
      darkBtn.addEventListener('click', () => {
        themeManager.setManualTheme('dark');
      });
    }
  }
  
  // Listener para eventos de mudança de tema
  window.addEventListener('themechange', (e) => {
    console.log('Tema mudou:', e.detail);
    // Você pode adicionar lógica customizada aqui
  });
  
  // Atualizar botão na inicialização
  setTimeout(() => {
    themeManager.updateToggleButton();
  }, 100);
});

// Exportar para uso em outros scripts
if (typeof module !== 'undefined' && module.exports) {
  module.exports = ThemeManager;
}
