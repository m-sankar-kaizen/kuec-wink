/** @odoo-module **/

// 1. Auto-submit filter form on checkbox/radio change
document.addEventListener('change', function (ev) {
    if (ev.target.matches('.wink-filter-checkbox, input[name="delivery_model"], input[name="commercial_structure"]')) {
        const form = document.getElementById('wink-filter-form');
        if (form) form.submit();
    }
});

// 2. Search debounce (300ms)
let debounceTimer;
document.addEventListener('input', function (ev) {
    if (ev.target.matches('.wink-catalogue-header input[name="search"]')) {
        clearTimeout(debounceTimer);
        debounceTimer = setTimeout(() => {
            const form = ev.target.closest('form');
            if (form) form.submit();
        }, 300);
    }
});

// 3. Request Service Login Gate
document.addEventListener('click', function (ev) {
    const btn = ev.target.closest('.wink-request-btn');
    if (btn) {
        ev.preventDefault();
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

                // Provide fallback if bootstrap isn't globally exposed
                if (window.bootstrap && window.bootstrap.Modal) {
                    const modal = new window.bootstrap.Modal(modalEl);
                    modal.show();
                } else {
                    // Fallback directly to login if Bootstrap fails
                    window.location.href = '/web/login?redirect=' + encodedRedirect;
                }
            }
        } else {
            window.location.href = '/my/requests/new?product_id=' + productId;
        }
    }
});
