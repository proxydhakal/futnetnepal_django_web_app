/**
 * Futnet toast queue — dispatches after Alpine is ready so @toast.window receives events.
 */
(function (global) {
  'use strict';

  var queue = [];
  var DEFAULT_MS = 5000;
  var STAGGER_MS = 350;

  function normalizeType(type) {
    var t = (type == null ? '' : String(type)).toLowerCase();
    if (t.indexOf('error') >= 0 || t.indexOf('danger') >= 0) return 'error';
    if (t.indexOf('warn') >= 0) return 'warning';
    if (t.indexOf('info') >= 0) return 'info';
    return 'success';
  }

  function dispatch(detail) {
    global.dispatchEvent(new CustomEvent('toast', { detail: detail }));
  }

  function flush() {
    if (!queue.length) return;
    var pending = queue.slice();
    queue = [];
    pending.forEach(function (detail, index) {
      setTimeout(function () {
        dispatch(detail);
      }, index * STAGGER_MS);
    });
  }

  function fnToast(text, type, durationMs) {
    var msg = (text == null ? '' : String(text)).trim();
    if (!msg) return;
    queue.push({
      text: msg,
      type: normalizeType(type),
      duration: durationMs > 0 ? durationMs : DEFAULT_MS,
    });
    if (global.Alpine) {
      flush();
    }
  }

  global.fnToast = fnToast;
  global.addEventListener('alpine:initialized', flush);
  global.addEventListener('DOMContentLoaded', function () {
    if (global.Alpine) flush();
  });
})(window);
