/** @odoo-module **/

import { registry } from "@web/core/registry";

// Odoo 18 TourInteractive explicitly calls DOMPurify.sanitize onTourEnd, but public website 
// pages (like /services) might not load the DOMPurify bundle, resulting in a TypeError.
if (typeof window.DOMPurify === 'undefined') {
    window.DOMPurify = { sanitize: (str) => str };
}

const guestTour = {
    url: "/services",
    steps: () => [
        {
            trigger: ".wink-catalogue-header h1",
            content: "Welcome to WINK \u2014 KUEC's Shared Services Portal. Let us show you around.",
        },
        {
            trigger: "input[name='search']",
            content: "Search for any service by name or keyword.",
        },
        {
            trigger: ".wink-filter-sidebar",
            content: "Use filters to narrow down services by department, nature, or delivery model.",
        },
        {
            trigger: ".wink-service-card:first-child",
            content: "Each card shows service details, pricing, and delivery type at a glance.",
        },
        {
            trigger: ".wink-request-btn",
            content: "Ready to request? Click here \u2014 you'll be guided to sign in or create a free account.",
        }
    ]
};

const clientTour = {
    url: "/my/home",
    steps: () => [
        {
            trigger: "#wrapwrap",
            content: "Welcome to your WINK portal. Here's a quick overview.",
        },
        {
            trigger: "a[href*='/my/employees']",
            content: "Start by uploading your team's details to the Employee Directory.",
        },
        {
            trigger: ".o_portal_docs",
            content: "Track all your service requests, invoices, and projects from here.",
        }
    ]
};

// Check Guest Tour
if (localStorage.getItem('wink_guest_tour_seen') !== 'true') {
    registry.category("web_tour.tours").add("wink_guest_tour", guestTour);
}

// Check Client Tour
// We removed the @web/session check to prevent Odoo 18 module crash.
// Odoo will only trigger this tour on /my/home, which is already login-gated.
if (localStorage.getItem('wink_client_tour_seen') !== 'true') {
    registry.category("web_tour.tours").add("wink_client_tour", clientTour);
}
