/** @odoo-module **/

import { registry } from "@web/core/registry";

const guestTour = {
    id: "wink_guest_tour",
    url: "/services",
    showSkipButton: true,
    steps: () => [
        {
            trigger: ".wink-catalogue-header h1",
            content: "Welcome to WINK \u2014 KUEC's Shared Services Portal. Let us show you around.",
            position: "bottom",
            isCheck: false,
        },
        {
            trigger: "input[name='search']",
            content: "Search for any service by name or keyword.",
            position: "bottom",
            isCheck: false,
        },
        {
            trigger: ".wink-filter-sidebar",
            content: "Use filters to narrow down services by department, nature, or delivery model.",
            position: "right",
            isCheck: false,
        },
        {
            trigger: ".wink-service-card:first-child",
            content: "Each card shows service details, pricing, and delivery type at a glance.",
            position: "top",
            isCheck: false,
        },
        {
            trigger: ".wink-service-card:first-child .wink-request-btn",
            content: "Ready to request? Click here \u2014 you'll be guided to sign in or create a free account.",
            position: "top",
            isCheck: false,
            run: () => {
                // Mark tour seen before letting user click it
                localStorage.setItem('wink_guest_tour_seen', 'true');
            }
        }
    ]
};

const clientTour = {
    id: "wink_client_tour",
    url: "/my/home",
    showSkipButton: true,
    steps: () => [
        {
            trigger: ".o_portal_my_home",
            content: "Welcome to your WINK portal. Here's a quick overview.",
            position: "bottom",
            isCheck: false,
        },
        {
            trigger: "a[href*='/my/employees']",
            content: "Start by uploading your team's details to the Employee Directory.",
            position: "right",
            isCheck: false,
            run: () => { }, // do not navigate - tooltip only
        },
        {
            trigger: ".o_portal_docs",
            content: "Track all your service requests, invoices, and projects from here.",
            position: "top",
            isCheck: false,
            run: () => {
                localStorage.setItem('wink_client_tour_seen', 'true');
            }
        }
    ]
};

// Check Guest Tour
if (localStorage.getItem('wink_guest_tour_seen') !== 'true') {
    guestTour.sequence = 10;
    registry.category("web_tour.tours").add("wink_guest_tour", guestTour);
}

// Check Client Tour
if (localStorage.getItem('wink_client_tour_seen') !== 'true') {
    const isAuthenticated = (typeof odoo !== 'undefined' && odoo.session_info && odoo.session_info.uid);
    if (isAuthenticated) {
        clientTour.sequence = 20;
        registry.category("web_tour.tours").add("wink_client_tour", clientTour);
    }
}
