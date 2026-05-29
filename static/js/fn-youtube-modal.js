document.addEventListener('alpine:init', function () {
  Alpine.data('youtubeModal', function (embedBase) {
    return {
      open: false,
      embedBase: embedBase || '',
      get embedSrc() {
        if (!this.open || !this.embedBase) return '';
        var join = this.embedBase.indexOf('?') >= 0 ? '&' : '?';
        return this.embedBase + join + 'autoplay=1';
      },
      openModal() {
        if (!this.embedBase) return;
        this.open = true;
        document.body.classList.add('overflow-hidden');
      },
      closeModal() {
        this.open = false;
        document.body.classList.remove('overflow-hidden');
      },
    };
  });
});
