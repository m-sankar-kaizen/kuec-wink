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

// 3. Request Service Login Gate Modal Setup
document.addEventListener('show.bs.modal', function(ev) {
    if (ev.target.id === 'winkLoginModal') {
        const btn = ev.relatedTarget;
        if (btn && btn.dataset.productId) {
            const productId = btn.dataset.productId;
            const signinLink = ev.target.querySelector('.wink-signin-link');
            const signupLink = ev.target.querySelector('.wink-signup-link');
            
            // Log in redirects back to the request form
            if (signinLink) {
                signinLink.href = '/web/login?redirect=' + encodeURIComponent('/my/requests/new?product_id=' + productId);
            }
            
            // Create account goes straight to the custom WINK registration form for this product
            if (signupLink) {
                signupLink.href = '/my/requests/new?product_id=' + productId;
            }
        }
    }
});
