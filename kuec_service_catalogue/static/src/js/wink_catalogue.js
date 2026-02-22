/** @odoo-module **/

import publicWidget from "@web/legacy/js/public/public_widget";

publicWidget.registry.WinkCatalogue = publicWidget.Widget.extend({
    selector: '#wrapwrap', // Target the main wrapper so both catalogue and detail pages are caught
    events: {
        'change .wink-filter-checkbox': '_onFilterChange',
        'change input[name="delivery_model"]': '_onFilterChange',
        'change input[name="commercial_structure"]': '_onFilterChange',
        'input .wink-catalogue-header input[name="search"]': '_onSearchInput',
        'click .wink-request-btn': '_onRequestBtnClick',
    },

    init: function () {
        this._super.apply(this, arguments);
        this.debounceTimer = null;
    },

    _onFilterChange: function (ev) {
        const form = document.getElementById('wink-filter-form');
        if (form) {
            form.submit();
        }
    },

    _onSearchInput: function (ev) {
        clearTimeout(this.debounceTimer);
        this.debounceTimer = setTimeout(() => {
            const form = ev.currentTarget.closest('form');
            if (form) {
                form.submit();
            }
        }, 300);
    },

    _onRequestBtnClick: function (ev) {
        ev.preventDefault();
        const btn = ev.currentTarget;
        const productId = btn.dataset.productId;
        const redirectUrl = btn.dataset.redirect;

        const isAuthenticated = (typeof odoo !== 'undefined' && odoo.session_info && odoo.session_info.uid);

        if (!isAuthenticated) {
            const modalEl = document.getElementById('winkLoginModal');
            if (modalEl) {
                const encodedRedirect = encodeURIComponent(redirectUrl + '?request=1');
                const signinLink = modalEl.querySelector('.wink-signin-link');
                const signupLink = modalEl.querySelector('.wink-signup-link');

                if (signinLink) signinLink.href = '/web/login?redirect=' + encodedRedirect;
                if (signupLink) signupLink.href = '/web/signup?redirect=' + encodedRedirect;

                const modal = new window.bootstrap.Modal(modalEl);
                modal.show();
            }
        } else {
            window.location.href = '/my/requests/new?product_id=' + productId;
        }
    }
});
