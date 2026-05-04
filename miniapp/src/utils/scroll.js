export function resetViewportScroll() {
  const scrollTop = () => {
    const scrollingElement = document.scrollingElement || document.documentElement;
    scrollingElement.scrollTop = 0;
    document.body.scrollTop = 0;
    window.scrollTo(0, 0);
  };

  scrollTop();
  requestAnimationFrame(scrollTop);
  setTimeout(scrollTop, 0);
}
