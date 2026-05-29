/**
 * Homepage approved reviews carousel (Alpine.js).
 * Usage: x-data="homeReviewsCarousel(totalSlides, intervalMs)"
 */
document.addEventListener('alpine:init', () => {
  Alpine.data('homeReviewsCarousel', (total = 0, intervalMs = 6000) => ({
    active: 0,
    total: Number(total) || 0,
    intervalMs: Number(intervalMs) || 6000,
    timer: null,
    paused: false,

    init() {
      if (this.total > 1) {
        this.play();
      }
    },

    destroy() {
      this.pause();
    },

    play() {
      this.pause();
      if (this.total <= 1 || this.paused) {
        return;
      }
      this.timer = setInterval(() => this.next(), this.intervalMs);
    },

    pause() {
      if (this.timer) {
        clearInterval(this.timer);
        this.timer = null;
      }
    },

    pauseHover() {
      this.paused = true;
      this.pause();
    },

    resumeHover() {
      this.paused = false;
      this.play();
    },

    next() {
      if (this.total <= 1) {
        return;
      }
      this.active = (this.active + 1) % this.total;
      this.play();
    },

    prev() {
      if (this.total <= 1) {
        return;
      }
      this.active = this.active === 0 ? this.total - 1 : this.active - 1;
      this.play();
    },

    goTo(index) {
      if (index >= 0 && index < this.total) {
        this.active = index;
        this.play();
      }
    },
  }));
});
