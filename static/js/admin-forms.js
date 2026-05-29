/**
 * Premium admin CRUD form renderer (Flatpickr + Select2 + file dropzones).
 */
(function () {
  function labelize(name) {
    return name.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());
  }

  function fieldId(name) {
    return 'admin_f_' + name.replace(/[^a-zA-Z0-9]/g, '_');
  }

  function debounce(fn, ms) {
    let timer;
    return (...args) => {
      clearTimeout(timer);
      timer = setTimeout(() => fn(...args), ms);
    };
  }

  async function fetchSlug(text, options) {
    const url = options.slugifyUrl || '/iamadmin/api/slugify/';
    const res = await fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': options.csrf || '',
      },
      body: JSON.stringify({
        text: text || '',
        model_key: options.modelKey || '',
        instance_pk: options.editingId || null,
      }),
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) return '';
    return data.slug || '';
  }

  function sourceTextForSlug(container, sourceName) {
    const sourceId = fieldId(sourceName);
    const el = container.querySelector('#' + sourceId);
    if (!el) return '';
    if (window.CKEDITOR?.instances[sourceId]) {
      return CKEDITOR.instances[sourceId].getData().replace(/<[^>]+>/g, ' ').trim();
    }
    return (el.value || '').trim();
  }

  function bindAutoSlug(container, fieldDefs, options) {
    const onChange = options.onChange || (() => {});
    const slugifyOpts = {
      slugifyUrl: options.slugifyUrl,
      csrf: options.csrf,
      modelKey: options.modelKey,
      editingId: options.editingId,
    };

    Object.keys(fieldDefs).forEach((slugName) => {
      const info = fieldDefs[slugName];
      const sourceName = info.auto_slug_from;
      if (!sourceName) return;

      const slugEl = container.querySelector('#' + fieldId(slugName));
      if (!slugEl) return;

      const run = debounce(async () => {
        const text = sourceTextForSlug(container, sourceName);
        if (!text) {
          slugEl.value = '';
          onChange(slugName, '');
          return;
        }
        slugEl.classList.add('admin-slug-loading');
        const slug = await fetchSlug(text, slugifyOpts);
        slugEl.classList.remove('admin-slug-loading');
        if (slug) {
          slugEl.value = slug;
          onChange(slugName, slug);
        }
      }, 350);

      const sourceEl = container.querySelector('#' + fieldId(sourceName));
      if (sourceEl) {
        sourceEl.addEventListener('input', run);
        sourceEl.addEventListener('change', run);
      }
      const ck = window.CKEDITOR?.instances[fieldId(sourceName)];
      if (ck) {
        ck.on('change', run);
        ck.on('blur', run);
      }

      if (!slugEl.value && sourceTextForSlug(container, sourceName)) {
        run();
      }
    });
  }

  function isSelectField(info) {
    return (
      info.type === 'ForeignKey' ||
      info.type === 'ManyToManyField' ||
      (info.choices && info.choices.length && info.type !== 'BooleanField')
    );
  }

  function formatValueForInput(info, value) {
    if (value === null || value === undefined) return '';
    if (info.type === 'ManyToManyField') {
      return Array.isArray(value) ? value.map(String) : [];
    }
    if (info.type === 'DateTimeField' && value) {
      const d = new Date(value);
      if (!isNaN(d)) {
        const p = (n) => String(n).padStart(2, '0');
        return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())} ${p(d.getHours())}:${p(d.getMinutes())}`;
      }
    }
    return String(value);
  }

  function ckEditorConfig() {
    return {
      height: 280,
      removePlugins: 'elementspath',
      resize_enabled: true,
      filebrowserUploadUrl: window.FN_CKEDITOR_UPLOAD_URL || '/ckeditor/upload/',
      filebrowserImageUploadUrl: window.FN_CKEDITOR_UPLOAD_URL || '/ckeditor/upload/',
      extraPlugins: 'uploadimage,image2',
      toolbar: [
        { name: 'clipboard', items: ['Undo', 'Redo'] },
        { name: 'styles', items: ['Format'] },
        { name: 'basicstyles', items: ['Bold', 'Italic', 'Underline', 'Strike', '-', 'RemoveFormat'] },
        { name: 'paragraph', items: ['NumberedList', 'BulletedList', '-', 'Outdent', 'Indent', 'Blockquote'] },
        { name: 'links', items: ['Link', 'Unlink'] },
        { name: 'insert', items: ['Image', 'Table', 'HorizontalRule'] },
        { name: 'tools', items: ['Maximize', 'Source'] },
      ],
    };
  }

  function destroyCkEditors(container) {
    if (!window.CKEDITOR || !container) return;
    container.querySelectorAll('textarea.admin-ckeditor-field').forEach((ta) => {
      const instance = CKEDITOR.instances[ta.id];
      if (instance) instance.destroy(true);
    });
  }

  function initCkEditors(container) {
    if (!window.CKEDITOR || !container) return;
    if (window.FN_CKEDITOR_BASE) {
      CKEDITOR.basePath = window.FN_CKEDITOR_BASE;
    }
    container.querySelectorAll('textarea.admin-ckeditor-field').forEach((ta) => {
      if (CKEDITOR.instances[ta.id]) return;
      const editor = CKEDITOR.replace(ta.id, ckEditorConfig());
      editor.on('change', () => {
        ta.value = editor.getData();
        ta.dispatchEvent(new Event('input', { bubbles: true }));
      });
      editor.on('instanceReady', () => {
        ta.value = editor.getData();
      });
    });
  }

  window.adminFormKit = {
    clearFieldErrors(container) {
      if (!container) return;
      container.querySelectorAll('.admin-field-error').forEach((el) => el.remove());
      container.querySelectorAll('.admin-field').forEach((wrap) => {
        wrap.classList.remove('admin-field-has-error');
      });
    },

    showFieldErrors(container, fieldErrors) {
      if (!container || !fieldErrors) return;
      this.clearFieldErrors(container);
      Object.keys(fieldErrors).forEach((name) => {
        const messages = fieldErrors[name];
        const wrap = container.querySelector(`[data-field="${name}"]`);
        if (!wrap || !messages || !messages.length) return;
        wrap.classList.add('admin-field-has-error');
        const err = document.createElement('p');
        err.className = 'admin-field-error';
        err.setAttribute('role', 'alert');
        err.textContent = messages.join(' ');
        wrap.appendChild(err);
        const input = wrap.querySelector(`#${fieldId(name)}, .cke`);
        if (input) {
          input.setAttribute('aria-invalid', 'true');
          input.setAttribute('aria-describedby', `err-${fieldId(name)}`);
          err.id = `err-${fieldId(name)}`;
        }
      });
      const first = container.querySelector('.admin-field-has-error');
      if (first) {
        first.scrollIntoView({ behavior: 'smooth', block: 'center' });
      }
    },

    destroy(container) {
      if (!container) return;
      destroyCkEditors(container);
      container.querySelectorAll('input.admin-fp').forEach((el) => {
        if (el._flatpickr) el._flatpickr.destroy();
      });
      if (window.fnDestroySelect2) window.fnDestroySelect2(container);
      container.innerHTML = '';
    },

    render(container, fieldDefs, form, options) {
      if (!container) return;
      const opts = options || {};
      const editing = !!opts.editing;
      const onChange = opts.onChange || (() => {});
      const onFile = opts.onFile || (() => {});

      this.destroy(container);
      const frag = document.createDocumentFragment();

      Object.keys(fieldDefs).forEach((name) => {
        const info = fieldDefs[name];
        if (info.readonly && !editing && !info.auto_slug_from) return;

        const wrap = document.createElement('div');
        wrap.className = 'admin-field';
        wrap.dataset.field = name;

        const label = document.createElement('label');
        label.className = 'admin-field-label';
        label.setAttribute('for', fieldId(name));
        label.textContent = labelize(name);
        if (info.required) {
          const req = document.createElement('span');
          req.className = 'admin-field-required';
          req.textContent = '*';
          label.appendChild(req);
        }
        wrap.appendChild(label);

        const val = form[name];
        const id = fieldId(name);

        if (info.type === 'BooleanField') {
          const row = document.createElement('label');
          row.className = 'admin-toggle';
          const input = document.createElement('input');
          input.type = 'checkbox';
          input.id = id;
          input.checked = !!val;
          input.addEventListener('change', () => onChange(name, input.checked));
          const track = document.createElement('span');
          track.className = 'admin-toggle-track';
          const knob = document.createElement('span');
          knob.className = 'admin-toggle-knob';
          track.appendChild(knob);
          row.appendChild(input);
          row.appendChild(track);
          wrap.appendChild(row);
        } else if (info.type === 'RichTextField') {
          const ta = document.createElement('textarea');
          ta.id = id;
          ta.className = 'admin-ckeditor-field';
          ta.value = val || '';
          ta.disabled = !!info.readonly;
          ta.addEventListener('input', () => onChange(name, ta.value));
          wrap.classList.add('admin-field-richtext');
          wrap.appendChild(ta);
        } else if (info.type === 'TextField') {
          const ta = document.createElement('textarea');
          ta.id = id;
          ta.className = 'admin-input admin-input-area';
          ta.rows = 4;
          ta.value = val || '';
          ta.disabled = !!info.readonly;
          ta.addEventListener('input', () => onChange(name, ta.value));
          wrap.appendChild(ta);
        } else if (isSelectField(info)) {
          const sel = document.createElement('select');
          sel.id = id;
          sel.className = 'admin-input fn-select2';
          sel.dataset.placeholder = 'Search or select…';
          if (info.type === 'ManyToManyField') sel.multiple = true;
          if (!info.required && info.type !== 'ManyToManyField') {
            sel.dataset.allowClear = 'true';
            const empty = document.createElement('option');
            empty.value = '';
            empty.textContent = '— Select —';
            sel.appendChild(empty);
          }
          (info.choices || []).forEach((opt) => {
            const o = document.createElement('option');
            o.value = String(opt.value);
            o.textContent = opt.label;
            sel.appendChild(o);
          });
          const selected = formatValueForInput(info, val);
          if (Array.isArray(selected)) {
            selected.forEach((v) => {
              [...sel.options].forEach((o) => {
                if (o.value === v) o.selected = true;
              });
            });
          } else if (selected) sel.value = selected;
          sel.disabled = !!info.readonly;
          sel.addEventListener('change', () => {
            const v = sel.multiple
              ? [...sel.selectedOptions].map((o) => o.value)
              : sel.value;
            onChange(name, v);
          });
          wrap.appendChild(sel);
        } else if (info.type === 'ImageField' || info.type === 'FileField') {
          const zone = document.createElement('div');
          zone.className = 'admin-file-zone';
          const input = document.createElement('input');
          input.type = 'file';
          input.id = id;
          input.className = 'admin-file-input';
          if (info.type === 'ImageField') input.accept = 'image/*';
          const hint = document.createElement('p');
          hint.className = 'admin-file-hint';
          hint.innerHTML =
            '<i class="fa-solid fa-cloud-arrow-up"></i> Drop file or <span>browse</span>';
          const current = document.createElement('p');
          current.className = 'admin-file-current';
          if (val) current.textContent = 'Current: ' + val;
          input.addEventListener('change', () => {
            const file = input.files?.[0];
            if (file) {
              current.textContent = 'Selected: ' + file.name;
              onFile(name, file);
            }
          });
          zone.appendChild(input);
          zone.appendChild(hint);
          if (val) zone.appendChild(current);
          wrap.appendChild(zone);
        } else if (info.type === 'DateTimeField') {
          const input = document.createElement('input');
          input.type = 'text';
          input.id = id;
          input.className = 'admin-input admin-fp';
          input.dataset.fpType = 'datetime';
          input.placeholder = 'Select date & time';
          input.value = formatValueForInput(info, val);
          input.disabled = !!info.readonly;
          input.autocomplete = 'off';
          input.addEventListener('change', () => onChange(name, input.value));
          wrap.appendChild(input);
        } else if (info.type === 'DateField') {
          const input = document.createElement('input');
          input.type = 'text';
          input.id = id;
          input.className = 'admin-input admin-fp';
          input.dataset.fpType = 'date';
          input.placeholder = 'Select date';
          input.value = formatValueForInput(info, val);
          input.disabled = !!info.readonly;
          input.autocomplete = 'off';
          input.addEventListener('change', () => onChange(name, input.value));
          wrap.appendChild(input);
        } else if (info.type === 'TimeField') {
          const input = document.createElement('input');
          input.type = 'text';
          input.id = id;
          input.className = 'admin-input admin-fp';
          input.dataset.fpType = 'time';
          input.placeholder = 'Select time';
          input.value = val || '';
          input.disabled = !!info.readonly;
          input.autocomplete = 'off';
          input.addEventListener('change', () => onChange(name, input.value));
          wrap.appendChild(input);
        } else {
          const input = document.createElement('input');
          const types = {
            IntegerField: 'number',
            BigIntegerField: 'number',
            DecimalField: 'number',
            FloatField: 'number',
            EmailField: 'email',
            URLField: 'url',
          };
          input.type = types[info.type] || 'text';
          input.id = id;
          input.className = 'admin-input';
          input.value = val ?? '';
          if (info.auto_slug_from) {
            input.readOnly = true;
            input.classList.add('admin-slug-field');
            input.setAttribute('aria-readonly', 'true');
            const hint = document.createElement('p');
            hint.className = 'admin-field-hint text-xs text-slate-500 mt-1';
            hint.textContent = 'Auto-generated from ' + labelize(info.auto_slug_from).toLowerCase();
            wrap.appendChild(input);
            wrap.appendChild(hint);
          } else {
            input.disabled = !!info.readonly;
            input.addEventListener('input', () => onChange(name, input.value));
            wrap.appendChild(input);
          }
        }

        if (info.readonly) wrap.classList.add('admin-field-readonly');
        frag.appendChild(wrap);
      });

      container.appendChild(frag);
      this.initWidgets(container, opts.dropdownParent);
      bindAutoSlug(container, fieldDefs, opts);
    },

    initWidgets(container, dropdownParent) {
      if (!container) return;

      initCkEditors(container);

      if (window.flatpickr) {
        container.querySelectorAll('input.admin-fp').forEach((el) => {
          if (el._flatpickr) return;
          const fpType = el.dataset.fpType || 'date';
          let config = {
            disableMobile: false,
            altInput: true,
            onChange: () => el.dispatchEvent(new Event('change', { bubbles: true })),
          };
          if (fpType === 'datetime') {
            config = {
              ...config,
              enableTime: true,
              dateFormat: 'Y-m-d H:i',
              altFormat: 'M j, Y · h:i K',
            };
          } else if (fpType === 'time') {
            config = {
              ...config,
              enableTime: true,
              noCalendar: true,
              dateFormat: 'H:i',
              altFormat: 'h:i K',
            };
          } else {
            config = { ...config, dateFormat: 'Y-m-d', altFormat: 'M j, Y' };
          }
          flatpickr(el, config);
          if (el._flatpickr?.calendarContainer) {
            el._flatpickr.calendarContainer.classList.add('admin-fp-light');
          }
        });
      }

      if (window.fnInitSelect2) {
        document.dispatchEvent(
          new CustomEvent('fn-select2-init', {
            detail: { scope: container, parent: dropdownParent || '#adminCrudModal' },
          })
        );
        if (window.jQuery) {
          jQuery(container).find('select.fn-select2').on('change.select2sync', function () {
            this.dispatchEvent(new Event('change', { bubbles: true }));
          });
        }
      }
    },

    collect(container, fieldDefs) {
      const data = {};
      if (!container) return data;

      if (window.CKEDITOR) {
        Object.keys(CKEDITOR.instances).forEach((key) => {
          CKEDITOR.instances[key].updateElement();
        });
      }

      Object.keys(fieldDefs).forEach((name) => {
        const info = fieldDefs[name];
        const id = fieldId(name);
        const el = container.querySelector('#' + id);
        if (!el) return;

        if (info.type === 'BooleanField') {
          data[name] = el.checked;
        } else if (info.type === 'ManyToManyField') {
          const vals = window.jQuery
            ? jQuery(el).val()
            : [...el.selectedOptions].map((o) => o.value);
          data[name] = vals ? (Array.isArray(vals) ? vals : [vals]) : [];
        } else if (isSelectField(info)) {
          const v = window.jQuery ? jQuery(el).val() : el.value;
          data[name] = v ?? '';
        } else if (info.type === 'ImageField' || info.type === 'FileField') {
          return;
        } else if (info.type === 'RichTextField') {
          const inst = window.CKEDITOR?.instances[id];
          data[name] = inst ? inst.getData() : el.value;
        } else {
          data[name] = el.value;
        }
      });
      return data;
    },
  };
})();
