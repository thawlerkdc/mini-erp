# Carrossel Moderno - Documentação

## Descrição

O carrossel da página de login foi completamente reformulado para oferecer um layout moderno estilo Netflix/Apple com transições suaves, efeito de profundidade e responsividade total.

## Características Principais

### 1. **Layout Visual Moderno**
- **3 imagens visíveis simultaneamente**: Criando sensação de profundidade
- **Imagem central em destaque**: Scale 1.05x, opacity 100%, maior sombra
- **Imagens laterais reduzidas**: Scale 0.82x, opacity 55%, leve blur
- **Imagem oculta (trailing)**: Para animação contínua suave
- **Efeito de profundidade**: Blur e brightness gradualmente reduzidos nas laterais

### 2. **Dimensões e Formato**
- **Aspecto 16:9**: Formato horizontal cinematográfico
- **100% de largura do container**: Responsivo em qualquer tamanho
- **object-fit: cover**: Mantém proporção sem distorção
- **Imagens: 1200x900 atualmente** (recomendamos mínimo 1920x1080 para melhor qualidade)

### 3. **Transições e Animações**
- **Duração por slide**: 4-5 segundos (configurável via `holdMs`)
- **Duração da transição**: 0.75 segundos (configurável via `transitionMs`)
- **Easing**: cubic-bezier(0.25, 0.46, 0.45, 0.94) - suave e natural
- **Transição por translateX**: Deslizamento lateral fluido

### 4. **Responsividade**
- **Desktop (> 768px)**: 3 imagens visíveis, botões de navegação
- **Tablet (480px - 768px)**: Layout otimizado, botões menores
- **Mobile (< 480px)**: Layout redimensionado, gaps menores

### 5. **Interatividade**
- **Botões anterior/próximo**: Navegação manual com hover effects
- **Indicadores (dots)**: Mostram slide ativo, clicáveis para navegação direta
- **Pausa automática**: Quando a aba fica oculta (visibility change)
- **Retomada automática**: Quando usuário volta para a aba

## Estrutura de Arquivos

### CSS
- **Global**: `static/css/style.css` - Estilos principais do carrossel
- **Local**: `templates/login.html` - Estilos inline da página de login

### JavaScript
- **Script de controle**: `static/js/loginCarousel.js` - Lógica do carrossel

### HTML
- **Template**: `templates/login.html` - Markup e inicialização

## Conversão de Imagens (Opcional)

Incluímos um script Python para converter imagens para 16:9 com corte centralizado:

```bash
python convert_images_to_16_9.py
```

**O que ele faz:**
1. Detecta imagens em `static/img/previews/`
2. Aplica crop centralizado mantendo foco principal
3. Redimensiona para 1920x1080 (16:9)
4. Salva com qualidade alta (95%)

**Requisitos:**
```bash
pip install Pillow
```

## Configuração Avançada

### Alterar Duração dos Slides

No arquivo `templates/login.html`, procure pela inicialização:

```javascript
initLoginRotaryCarousel({
  // ... outras opções
  holdMs: 4500,        // Duração em ms (4-5 segundos)
  transitionMs: 750    // Duração transição (500-1000ms)
});
```

### Alterar Velocidade da Transição

Editar o easing e duração no CSS (`style.css`):

```css
.login-rotary-card {
  transition: transform 0.6s cubic-bezier(0.25, 0.46, 0.45, 0.94),
              opacity 0.6s cubic-bezier(0.25, 0.46, 0.45, 0.94),
              filter 0.6s cubic-bezier(0.25, 0.46, 0.45, 0.94);
}
```

### Alterar Escala e Opacidade

Editar as classes de posição no CSS:

```css
.login-rotary-card.pos-center {
  transform: scale(1.05);   /* Zoom central */
  opacity: 1;               /* Opacidade central */
}

.login-rotary-card.pos-left,
.login-rotary-card.pos-right {
  transform: scale(0.82);   /* Zoom lateral */
  opacity: 0.55;            /* Opacidade lateral */
}
```

## Performance

- **GPU Acceleration**: Uso de `transform` e `will-change` para render otimizado
- **Lazy Loading**: Imagens carregam sob demanda
- **Prevenção de flicker**: Sem layouts thrashing
- **Memory efficient**: Reusa DOM nodes ao invés de criar novos

## Compatibilidade

- ✅ Chrome/Edge (Todos versões recentes)
- ✅ Firefox (Todos versões recentes)
- ✅ Safari (iOS 12+, macOS 10.14+)
- ✅ Mobile browsers (Android Chrome, Safari iOS)

## Troubleshooting

### Carrossel não está animando
1. Verificar se o `loginCarousel.js` está carregado
2. Verificar console para erros
3. Garantir que há pelo menos 3 imagens no array

### Imagens aparecem com corte errado
- Usar o script `convert_images_to_16_9.py`
- Ou colocar imagens com dimensões 16:9 de preferência

### Botões de navegação não funcionam
1. Verificar se elementos `login-rotary-prev` e `login-rotary-next` existem no HTML
2. Verificar se não há CSS conflitante escondendo os botões

## Futuras Melhorias

- [ ] Adicionar suporte a toque/swipe em mobile
- [ ] Adicionar autoplay toggle
- [ ] Adicionar effects de parallax
- [ ] Adicionar modo dark/light automático
- [ ] Adicionar indicadores de progresso (progress bar)

## Notas de Desenvolvimento

O carrossel usa:
- **CSS Variables**: Para configuração dinâmica de tamanhos
- **CSS Grid/Flexbox**: Layout responsivo
- **requestAnimationFrame**: Para otimização de resize
- **Visibility API**: Pausa quando muda de aba

---

Última atualização: 17 de Abril de 2026
