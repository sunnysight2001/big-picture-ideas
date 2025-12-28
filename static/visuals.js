document.addEventListener('DOMContentLoaded', () => {
    const visualContainer = document.getElementById('visual-container');
    if (visualContainer) {
        const type = visualContainer.dataset.type;
        renderVisual(type, visualContainer);
    }
});
// ================================
// HERO BANNER AUTO-CAROUSEL
// ================================
document.addEventListener("DOMContentLoaded", () => {
  const slides = document.querySelectorAll(".hero-slide");
  let current = 0;

  if (slides.length <= 1) return;

  setInterval(() => {
    slides[current].classList.remove("active");
    current = (current + 1) % slides.length;
    slides[current].classList.add("active");
  }, 4000); // 4 seconds
});



function renderVisual(type, container) {
    // Simple placeholder visuals using SVG or just text for now
    // In a real app, this would draw SVG shapes based on the type
    
    let content = '';
    
    if (type === 'friction_graph') {
        content = '<div style="text-align:center; font-size: 2rem;">📉<br><span style="font-size:1rem">Friction ↓ Motivation ↑</span></div>';
    } else if (type === 'clock_visual') {
        content = '<div style="text-align:center; font-size: 2rem;">⏱️<br><span style="font-size:1rem">< 2 Minutes</span></div>';
    } else if (type === 'layers_visual') {
        content = '<div style="text-align:center; font-size: 2rem;">🧅<br><span style="font-size:1rem">Peel the layers</span></div>';
    } else {
        content = '<div style="text-align:center; font-size: 2rem;">💡</div>';
    }
    
    container.innerHTML = content;
}
