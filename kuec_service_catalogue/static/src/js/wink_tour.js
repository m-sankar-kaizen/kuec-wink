/** @odoo-module **/

import { registry } from "@web/core/registry";

const guestTour = {
    id: "wink_guest_tour",
    url: "/services",
    showSkipButton: true,
    steps: () => [
        {
            id: "guest_step_1",
            trigger: ".wink-catalogue-header h1",
            content: "Welcome to WINK \u2014 KUEC's Shared Services Portal. Let us show you around.",
            position: "bottom",
            run: () => { },
        },
        {
            id: "guest_step_2",
            trigger: "input[name='search']",
            content: "Search for any service by name or keyword.",
            position: "bottom",
            run: () => { },
        },
        {
            id: "guest_step_3",
            trigger: ".wink-filter-sidebar",
            content: "Use filters to narrow down services by department, nature, or delivery model.",
            position: "right",
            run: () => { },
        },
        {
            id: "guest_step_4",
            trigger: ".wink-service-card:first-child",
            content: "Each card shows service details, pricing, and delivery type at a glance.",
            position: "top",
            run: () => { },
        },
        {
            id: "guest_step_5",
            trigger: ".wink-request-btn",
            content: "Ready to request? Click here \u2014 you'll be guided to sign in or create a free account.",
            position: "top",
            run: () => {
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
            id: "client_step_1",
            trigger: "#wrapwrap",
            content: "Welcome to your WINK portal. Here's a quick overview.",
            position: "bottom",
            run: () => { },
        },
        {
            id: "client_step_2",
            trigger: "a[href*='/my/employees']",
            content: "Start by uploading your team's details to the Employee Directory.",
            position: "right",
            run: () => { },
        },
        {
            id: "client_step_3",
            trigger: ".o_portal_docs",
            content: "Track all your service requests, invoices, and projects from here.",
            position: "top",
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
// We removed the @web/session check to prevent Odoo 18 module crash.
// Odoo will only trigger this tour on /my/home, which is already login-gated.
if (localStorage.getItem('wink_client_tour_seen') !== 'true') {
    clientTour.sequence = 20;
    registry.category("web_tour.tours").add("wink_client_tour", clientTour);
}
