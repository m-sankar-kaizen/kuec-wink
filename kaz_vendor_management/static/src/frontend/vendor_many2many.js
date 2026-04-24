/** @odoo-module **/
/**
 * vendor_many2many.js
 *
 * Modern M2M widget for the Vendor Portal "Offered Products & Services" section.
 *
 * Features
 * ────────
 * • Renders the first 3 matching options as clickable chips (show-more for the rest)
 * • Live search filtering across all options
 * • Selected items appear as animated removable pills on the right panel
 * • Keeps the hidden native <select> in sync so existing form-submit / Odoo
 *   logic (products_ids hidden inputs) continues to work unchanged
 * • "Other" checkbox / text-input behaviour is preserved exactly as before
 */

import publicWidget from "@web/legacy/js/public/public_widget";

const INITIAL_VISIBLE = 3;          // chips shown before "Show more"

publicWidget.registry.TagPills = publicWidget.Widget.extend({

    selector: '.m2m_container',

    events: {
        'click    .m2m-pill-remove':  '_onRemovePill',
        'input    #m2m_search_input': '_onSearch',
        'click    #m2m_show_more_btn':'_onShowMore',
    },

    // ── Lifecycle ────────────────────────────────────────────────────────────

    init(parent, options) {
        this._super(...arguments);
        this.selectedTags = [];     // [{id, name}, …]
        this._allOptions   = [];    // [{id, name}, …] full list from <select>
        this._showAll      = false; // whether "show more" has been tapped
        this._query        = '';
    },

    start() {
        this._nativeSelect = this.el?.parentElement?.querySelector('#products_tag');
        if (!this._nativeSelect) return this._super(...arguments);

        // Build the master list from <select> options
        this._allOptions = [...this._nativeSelect.options].map(opt => ({
            id:   opt.value,
            name: opt.text.trim(),
        }));

        // Pre-select any options that were already selected (e.g. re-render)
        this.selectedTags = this._allOptions.filter(o => {
            const opt = this._nativeSelect.querySelector(`option[value="${o.id}"]`);
            return opt && opt.selected;
        });

        this._renderChips();
        this._renderPills();
        return this._super(...arguments);
    },

    // ── Event handlers ───────────────────────────────────────────────────────

    _onSearch(ev) {
        this._query   = ev.target.value.trim().toLowerCase();
        this._showAll = false;          // reset expansion on new search
        this._renderChips();
    },

    _onShowMore(ev) {
        this._showAll = true;
        this._renderChips();
    },

    /** Click on an option chip – toggle select/deselect */
    _onChipClick(ev) {
        const chip = ev.currentTarget;
        const id   = chip.dataset.optId;
        const name = chip.dataset.optName;

        const exists = this.selectedTags.find(t => t.id === id);
        if (exists) {
            this.selectedTags = this.selectedTags.filter(t => t.id !== id);
        } else {
            this.selectedTags = [...this.selectedTags, { id, name }];
        }

        this._syncNativeSelect();
        this._renderChips();
        this._renderPills();
    },

    /** Click the × button on a selected pill */
    _onRemovePill(ev) {
        const id = ev.currentTarget.dataset.tagId;
        this.selectedTags = this.selectedTags.filter(t => t.id !== id);
        this._syncNativeSelect();
        this._renderChips();
        this._renderPills();
    },

    // ── Rendering ────────────────────────────────────────────────────────────

    _renderChips() {
        const list        = this.el.querySelector('#m2m_options_list');
        const showMoreWrap= this.el.querySelector('#m2m_show_more_wrap');
        console.log(list, "list")

        if (!list) return;

        const q = this._query;

        // Filter
        const filtered = q
            ? this._allOptions.filter(o => o.name.toLowerCase().includes(q))
            : this._allOptions;

        console.log(this, filtered, "filtered")
        console.log(showMoreWrap, "showMoreWrap")

        // Slice
        const visible = this._showAll || q
            ? filtered
            : filtered.slice(0, INITIAL_VISIBLE);

        const hasMore = !this._showAll && !q && filtered.length > INITIAL_VISIBLE;

        // Build list items
        list.innerHTML = '';

        if (filtered.length === 0) {
            list.innerHTML = `<li class="m2m-empty">No products match "<em>${this._escHtml(q)}</em>"</li>`;
        } else {
            visible.forEach(opt => {
                const isSelected = !!this.selectedTags.find(t => t.id === opt.id);
                const li = document.createElement('li');
                li.className = `m2m-option-chip${isSelected ? ' selected' : ''}`;
                li.dataset.optId   = opt.id;
                li.dataset.optName = opt.name;
                li.innerHTML = `
                    <span class="m2m-chip-name">${this._escHtml(opt.name)}</span>
                    <span class="m2m-chip-check" aria-hidden="true">✓</span>
                `;
                li.addEventListener('click', e => this._onChipClick(e));
                list.appendChild(li);
            });
        }

        // Show-more button
        if (showMoreWrap) {
            if (hasMore) {
                showMoreWrap.classList.remove('d-none');
                const btn = showMoreWrap.querySelector('#m2m_show_more_btn');
                if (btn) btn.textContent = `Show ${filtered.length - INITIAL_VISIBLE} more…`;
            } else {
                showMoreWrap.classList.add('d-none');
            }
        }
    },

    _renderPills() {
        const pillContainer = this.el.querySelector('#tag-pills-container');
        const emptyHint     = this.el.querySelector('#m2m_empty_hint');
        if (!pillContainer) return;

        // Remove existing pills (keep the empty hint node)
        pillContainer.querySelectorAll('.m2m-pill').forEach(p => p.remove());

        if (this.selectedTags.length === 0) {
            pillContainer.classList.remove('has-items');
            if (emptyHint) emptyHint.style.display = '';
        } else {
            pillContainer.classList.add('has-items');
            if (emptyHint) emptyHint.style.display = 'none';

            this.selectedTags.forEach(({ id, name }) => {
                const pill = document.createElement('div');
                pill.className = 'm2m-pill';
                pill.innerHTML = `
                    <span>${this._escHtml(name)}</span>
                    <button type="button"
                            class="m2m-pill-remove remove-tag-btn"
                            data-tag-id="${this._escHtml(id)}"
                            title="Remove ${this._escHtml(name)}">×</button>
                `;
                pillContainer.appendChild(pill);
            });
        }

        // Sync hidden inputs used by the controller (products_ids)
        this._syncHiddenInputs();
    },

    // ── Sync helpers ─────────────────────────────────────────────────────────

    /** Keep the native <select> options in sync (for any code reading it) */
    _syncNativeSelect() {
        if (!this._nativeSelect) return;
        [...this._nativeSelect.options].forEach(opt => {
            opt.selected = !!this.selectedTags.find(t => t.id === opt.value);
        });

        // Toggle `required` based on selection (mirrors original logic)
        const otherOpChecked = this.el.querySelector('#other_op')?.checked;
        if (!otherOpChecked) {
            if (this.selectedTags.length > 0) {
                this._nativeSelect.removeAttribute('required');
            } else {
                this._nativeSelect.setAttribute('required', 'required');
            }
        }
    },

    /** Hidden inputs that the Python controller reads as `products_ids` */
    _syncHiddenInputs() {
        // Remove old hidden inputs
        this.el.querySelectorAll('input[name="products_ids"]').forEach(i => i.remove());

        this.selectedTags.forEach(({ id }) => {
            const hidden = document.createElement('input');
            hidden.type  = 'hidden';
            hidden.name  = 'products_ids';
            hidden.value = id;
            this.el.appendChild(hidden);
        });
    },

    // ── Utility ──────────────────────────────────────────────────────────────

    _escHtml(str) {
        return String(str)
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;');
    },
});