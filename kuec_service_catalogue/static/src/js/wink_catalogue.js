/** @odoo-module **/

document.addEventListener("DOMContentLoaded", function () {
    // 1. Auto-submit filter form on checkbox/radio change
    const filterElements = document.querySelectorAll('.wink-filter-checkbox, input[name="delivery_model"], input[name="commercial_structure"]');
    filterElements.forEach(el => {
        el.addEventListener('change', () => {
            const form = document.getElementById('wink-filter-form');
            if (form) {
                form.submit();
            }
        });
    });

    // 2. Search debounce (300ms)
    const searchInput = document.querySelector('.wink-catalogue-header input[name="search"]');
    if (searchInput) {
        let debounceTimer;
        searchInput.addEventListener('input', () => {
            clearTimeout(debounceTimer);
            debounceTimer = setTimeout(() => {
                const form = searchInput.closest('form');
                if (form) {
                    form.submit();
                }
            }, 300);
        });
    }

    // 3. Request Service Login Gate
    const requestButtons = document.querySelectorAll('.wink-request-btn');
    requestButtons.forEach(btn => {
        btn.addEventListener('click', function(e) {
            e.preventDefault();
            const productId = this.dataset.productId;
            const redirectUrl = this.dataset.redirect;

            // Check if user is authenticated using Odoo's session info
            const isAuthenticated = (typeof odoo !== 'undefined' && odoo.session_info && odoo.session_info.uid);

            if (!isAuthenticated) {
                // Show login modal
                const modalEl = document.getElementById('winkLoginModal');
                if (modalEl) {
                    // Set redirect links to point back to the details page
                    const encodedRedirect = encodeURIComponent(redirectUrl + '?request=1');
                    const signinLink = modalEl.querySelector('.wink-signin-link');
                    const signupLink = modalEl.querySelector('.wink-signup-link');
                    
                    if (signinLink) signinLink.href = '/web/login?redirect=' + encodedRedirect;
                    if (signupLink) signupLink.href = '/web/signup?redirect=' + encodedRedirect;
                    
                    // Use Bootstrap 5 Global Modal
                    const modal = new bootstrap.Modal(modalEl);
                    modal.show();
                }
            } else {
                // Authenticated - navigate to request form
                // In Epic 2, we just return to request flow. For now, it will link to a placeholder /my/requests/new
                window.location.href = '/my/requests/new?product_id=' + productId;
            }
        });
    });
});
