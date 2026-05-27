/**
 * jQuery + Select2 bundle (built via npm / esbuild).
 * Exposes window.jQuery, window.$, and window.fnInitSelect2 helpers.
 */
import jQuery from 'jquery';
import 'select2/dist/js/select2.full.js';

window.jQuery = window.$ = jQuery;

function resolveParent(dropdownParent) {
  if (dropdownParent) {
    const $parent = jQuery(dropdownParent);
    if ($parent.length) return $parent;
  }
  return jQuery(document.body);
}

window.fnDestroySelect2 = function (scope) {
  const $scope = scope ? jQuery(scope) : jQuery(document);
  $scope.find('select.fn-select2').each(function () {
    const $el = jQuery(this);
    if ($el.hasClass('select2-hidden-accessible')) {
      $el.select2('destroy');
    }
  });
};

window.fnInitSelect2 = function (scope, dropdownParent) {
  const run = function () {
    if (!jQuery.fn.select2) {
      console.error('Futnet: Select2 did not attach to jQuery.');
      return;
    }
    const $scope = scope ? jQuery(scope) : jQuery(document);
    const $parent = resolveParent(dropdownParent);
    $scope.find('select.fn-select2').each(function () {
      const $el = jQuery(this);
      if ($el.hasClass('select2-hidden-accessible')) {
        $el.select2('destroy');
      }
      $el.select2({
        width: '100%',
        placeholder: 'Search...',
        allowClear: false,
        minimumResultsForSearch: 0,
        dropdownParent: $parent,
      });
    });
  };
  requestAnimationFrame(function () {
    requestAnimationFrame(run);
  });
};

window.fnSetSelect2Values = function (values) {
  Object.keys(values).forEach(function (id) {
    jQuery('#' + id).val(String(values[id])).trigger('change');
  });
};

// Re-init when Alpine opens a modal (home feed create/edit).
document.addEventListener('fn-select2-init', function (e) {
  const detail = e.detail || {};
  window.fnInitSelect2(detail.scope, detail.parent);
});
