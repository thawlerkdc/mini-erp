function initLoginRotaryCarousel(config) {
  const stage = config && config.stage;
  const dotsWrap = config && config.dots;
  const items = (config && config.items) || [];
  const holdMs = Math.max(4000, Math.min(5000, Number((config && config.holdMs) || 4500)));
  const transitionMs = Math.max(500, Number((config && config.transitionMs) || 760));

  if (!stage || !dotsWrap || items.length < 3) {
    return null;
  }

  let current = 0;
  let timer = null;
  let isAnimating = false;
  let cardWidthPx = 0;
  let gapPx = 14;
  let resizeRaf = null;
  const track = document.createElement('div');
  track.className = 'login-rotary-track';
  stage.innerHTML = '';
  stage.appendChild(track);

  const dots = items.map(function(_, index) {
    const button = document.createElement('button');
    button.type = 'button';
    button.setAttribute('aria-label', 'Ir para imagem ' + (index + 1));
    button.addEventListener('click', function() {
      if (isAnimating) return;
      current = index;
      renderWindow();
      updateDots();
      restart();
    });
    dotsWrap.appendChild(button);
    return button;
  });

  function modulo(index) {
    return (index + items.length) % items.length;
  }

  function buildCard(item, positionClass) {
    const card = document.createElement('figure');
    card.className = 'login-rotary-card ' + positionClass;

    const image = document.createElement('img');
    image.src = item.src;
    image.alt = item.cap;
    image.loading = 'lazy';

    const caption = document.createElement('figcaption');
    caption.textContent = item.cap;

    card.appendChild(image);
    card.appendChild(caption);
    return card;
  }

  function setupLayout() {
    const stageWidth = stage.clientWidth || 0;
    gapPx = stageWidth < 720 ? 10 : 14;
    cardWidthPx = Math.max(120, (stageWidth - (gapPx * 2)) / 3);
    track.style.setProperty('--carousel-gap', gapPx + 'px');
    track.style.setProperty('--carousel-card-width', cardWidthPx + 'px');
  }

  function renderWindow() {
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

    track.style.transition = 'none';
    track.style.transform = 'translate3d(0, 0, 0)';
  }

  function updateDots() {
    dots.forEach(function(dot, index) {
      dot.classList.toggle('is-active', index === current);
    });
  }

  function goNext() {
    if (isAnimating) return;
    isAnimating = true;
    track.style.transition = 'transform ' + transitionMs + 'ms ease-in-out';
    const shiftPx = cardWidthPx + gapPx;
    track.style.transform = 'translate3d(-' + shiftPx + 'px, 0, 0)';
  }

  track.addEventListener('transitionend', function() {
    if (!isAnimating) return;
    current = modulo(current + 1);
    renderWindow();
    updateDots();
    isAnimating = false;
  });

  function start() {
    timer = window.setInterval(goNext, holdMs);
  }

  function stop() {
    if (timer) {
      window.clearInterval(timer);
      timer = null;
    }
  }

  function restart() {
    stop();
    start();
  }

  document.addEventListener('visibilitychange', function() {
    if (document.hidden) {
      stop();
    } else {
      restart();
    }
  });

  window.addEventListener('resize', function() {
    if (resizeRaf) return;
    resizeRaf = window.requestAnimationFrame(function() {
      resizeRaf = null;
      setupLayout();
      renderWindow();
      updateDots();
    });
  });

  setupLayout();
  renderWindow();
  updateDots();
  start();

  return {
    next: goNext,
    stop: stop,
    start: start,
    goTo: function(index) {
      if (isAnimating) return;
      current = modulo(index);
      renderWindow();
      updateDots();
      restart();
    }
  };
}
