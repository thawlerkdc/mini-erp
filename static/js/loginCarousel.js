// Carrossel de imagens para tela de login
// Requer um elemento com id="login-rotary-stage" e um array de imagens

(function() {
  const images = [
    '/static/img/previews/login1.jpg',
    '/static/img/previews/login2.jpg',
    '/static/img/previews/login3.jpg'
    // Adicione mais imagens conforme necessário
  ];
  const stage = document.getElementById('login-rotary-stage');
  const dots = document.getElementById('login-rotary-dots');
  if (!stage || !dots) return;

  let current = 0;
  let timer = null;

  // Cria slides
  stage.innerHTML = images.map((src, idx) =>
    `<div class="login-slide" style="background-image:url('${src}'); left:${idx*100}%"></div>`
  ).join('');
  dots.innerHTML = images.map((_, idx) =>
    `<span class="login-dot${idx===0?' active':''}" data-idx="${idx}"></span>`
  ).join('');

  function goTo(idx) {
    const slides = stage.querySelectorAll('.login-slide');
    slides.forEach((slide, i) => {
      slide.style.transition = 'left 0.7s cubic-bezier(.77,0,.18,1)';
      slide.style.left = ((i-idx)*100)+"%";
    });
    dots.querySelectorAll('.login-dot').forEach((dot, i) => {
      dot.classList.toggle('active', i === idx);
    });
    current = idx;
  }

  function next() {
    goTo((current+1)%images.length);
  }

  // Timer
  function start() {
    timer = setInterval(next, 4500);
  }
  function stop() {
    clearInterval(timer);
  }

  // Dot click
  dots.addEventListener('click', function(e) {
    if (e.target.classList.contains('login-dot')) {
      stop();
      goTo(Number(e.target.dataset.idx));
      start();
    }
  });

  // Responsivo: ajusta altura
  function adjustHeight() {
    const slide = stage.querySelector('.login-slide');
    if (slide) {
      stage.style.height = (slide.offsetWidth * 0.6) + 'px';
    }
  }
  window.addEventListener('resize', adjustHeight);

  goTo(0);
  start();
  setTimeout(adjustHeight, 100);
})();
