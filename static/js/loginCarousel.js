/**
 * Carrossel Moderno Estilo Netflix/Apple
 * Com 3 imagens visíveis, transição suave e efeito de profundidade
 */
function initLoginRotaryCarousel(config) {
  const stage = config && config.stage;
  const dotsWrap = config && config.dots;
  const prevButton = config && config.prevButton;
  const nextButton = config && config.nextButton;
  const items = (config && config.items) || [];
  const holdMs = Math.max(4000, Math.min(5000, Number((config && config.holdMs) || 4500)));
  const transitionMs = Math.max(500, Math.min(1000, Number((config && config.transitionMs) || 750)));

  if (!stage || !dotsWrap || items.length < 3) {
    return null;
  }

  let current = 0;
  let timer = null;
  let isAnimating = false;
  let containerWidth = 0;
  let cardWidth = 0;
  let gap = 0;
  let resizeRaf = null;

  // Criar o track (container das imagens)
  const track = document.createElement('div');
  track.className = 'login-rotary-track';
  stage.innerHTML = '';
  stage.appendChild(track);

  // Criar botões indicadores
  const dots = items.map(function(_, index) {
    const button = document.createElement('button');
    button.type = 'button';
    button.setAttribute('aria-label', 'Ir para slide ' + (index + 1));
    button.addEventListener('click', function() {
      if (isAnimating) return;
      current = index;
      renderCards();
      updateDots();
      restart();
    });
    dotsWrap.appendChild(button);
    return button;
  });

  /**
   * Função auxiliar para calcular índice com wrapping circular
   */
  function modulo(index) {
    return (index % items.length + items.length) % items.length;
  }

  /**
   * Criar um card de imagem
   */
  function buildCard(item, positionClass) {
    const card = document.createElement('figure');
    card.className = 'login-rotary-card ' + positionClass;
    card.style.margin = '0';

    const image = document.createElement('img');
    image.src = item.src;
    image.alt = item.cap;
    image.loading = 'lazy';
    image.draggable = false;

    const caption = document.createElement('figcaption');
    caption.textContent = item.cap;

    card.appendChild(image);
    card.appendChild(caption);
    return card;
  }

  /**
   * Configurar layout (calcular tamanhos)
   */
  function setupLayout() {
    containerWidth = stage.clientWidth || 0;
    gap = containerWidth < 480 ? 8 : (containerWidth < 768 ? 12 : 16);
    
    // Calcular 3 cards visíveis + padding
    const visibleCards = 3;
    const trackPadding = gap * 2;
    const totalGap = gap * (visibleCards - 1);
    cardWidth = (containerWidth - trackPadding - totalGap) / visibleCards;
    
    track.style.setProperty('--carousel-gap', gap + 'px');
    track.style.setProperty('--carousel-card-width', cardWidth + 'px');
  }

  /**
   * Renderizar os 4 cards visíveis (left, center, right, trailing)
   */
  function renderCards() {
    const left = modulo(current - 1);
    const center = modulo(current);
    const right = modulo(current + 1);
    const trailing = modulo(current + 2);

    track.replaceChildren(
      buildCard(items[left], 'pos-left'),
      buildCard(items[center], 'pos-center'),
      buildCard(items[right], 'pos-right'),
      buildCard(items[trailing], 'pos-trailing')
    );

    // Resetar transição (sem animação)
    track.style.transition = 'none';
    track.style.transform = 'translate3d(0, 0, 0)';
  }

  /**
   * Atualizar estado dos dots
   */
  function updateDots() {
    dots.forEach(function(dot, index) {
      dot.classList.toggle('is-active', index === current);
    });
  }

  /**
   * Ir para o próximo card
   */
  function goNext() {
    if (isAnimating) return;
    isAnimating = true;

    // Iniciar transição suave
    track.style.transition = 'transform ' + transitionMs + 'ms cubic-bezier(0.25, 0.46, 0.45, 0.94)';
    
    // Deslocar uma card width + gap
    const shiftPx = cardWidth + gap;
    track.style.transform = 'translate3d(-' + shiftPx + 'px, 0, 0)';
  }

  /**
   * Ir para o card anterior
   */
  function goPrev() {
    if (isAnimating) return;
    
    current = modulo(current - 1);
    renderCards();
    updateDots();
    restart();
  }

  /**
   * Evento de fim de transição
   */
  track.addEventListener('transitionend', function(e) {
    if (!isAnimating || e.propertyName !== 'transform') return;
    
    current = modulo(current + 1);
    renderCards();
    updateDots();
    isAnimating = false;
  });

  /**
   * Iniciar o loop automático
   */
  function start() {
    timer = window.setInterval(goNext, holdMs);
  }

  /**
   * Parar o loop
   */
  function stop() {
    if (timer) {
      window.clearInterval(timer);
      timer = null;
    }
  }

  /**
   * Reiniciar o loop
   */
  function restart() {
    stop();
    start();
  }

  /**
   * Pausar quando a aba está oculta
   */
  document.addEventListener('visibilitychange', function() {
    if (document.hidden) {
      stop();
    } else {
      restart();
    }
  });

  /**
   * Listeners dos botões de navegação
   */
  if (prevButton) {
    prevButton.addEventListener('click', function() {
      goPrev();
    });
  }

  if (nextButton) {
    nextButton.addEventListener('click', function() {
      goNext();
      restart();
    });
  }

  /**
   * Responder a redimensionamento da tela
   */
  window.addEventListener('resize', function() {
    if (resizeRaf) return;
    resizeRaf = window.requestAnimationFrame(function() {
      resizeRaf = null;
      setupLayout();
      renderCards();
    });
  });

  /**
   * Prevenir seleção de imagens ao arrastar
   */
  track.addEventListener('selectstart', function(e) {
    e.preventDefault();
  });

  // Inicializar
  setupLayout();
  renderCards();
  updateDots();
  start();

  // Retornar API pública
  return {
    next: goNext,
    prev: goPrev,
    stop: stop,
    start: start,
    goTo: function(index) {
      if (isAnimating) return;
      current = modulo(index);
      renderCards();
      updateDots();
      restart();
    }
  };
}
