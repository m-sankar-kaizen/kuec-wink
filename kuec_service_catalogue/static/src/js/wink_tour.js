/** @odoo-module **/

import { registry } from "@web/core/registry";

// DOMPurify safety shim for public pages
if (typeof window.DOMPurify === "undefined") {
    window.DOMPurify = { sanitize: (str) => str };
}

const guestTour = {
    url: "/services",
    showSkipButton: true,
    steps: () => [
        {
            trigger: ".wink-catalogue-header h1",
            content: "Welcome to WINK \u2014 KUEC's Shared Services Portal. Let us show you around.",
            run: () => { },
        },
        {
            trigger: "input[name='search']",
            content: "Search for any service by name or keyword.",
            run: () => { },
        },
        {
            trigger: ".wink-filter-sidebar",
            content: "Use filters to narrow down services by department, nature, or delivery model.",
            run: () => { },
        },
        {
            trigger: ".wink-service-card",
            content: "Each card shows service details, pricing, and delivery type at a glance.",
            run: () => { },
        },
        {
            trigger: ".wink-request-btn",
            content: "Ready to request? Click here \u2014 you'll be guided to sign in or create a free account.",
            run: () => {
                localStorage.setItem("wink_guest_tour_seen", "true");
            },
        },
    ],
};

const clientTour = {
    url: "/my/home",
    showSkipButton: true,
    steps: () => [
        {
            trigger: "#wrapwrap",
            content: "Welcome to your WINK portal. Here's a quick overview.",
            run: () => { },
        },
        {
            trigger: "a[href*='/my/employees']",
            content: "Start by uploading your team's details to the Employee Directory.",
            run: () => { },
        },
        {
            trigger: ".o_portal_docs",
            content: "Track all your service requests, invoices, and projects from here.",
            run: () => {
                localStorage.setItem("wink_client_tour_seen", "true");
            },
        },
    ],
};

if (localStorage.getItem("wink_guest_tour_seen") !== "true") {
    registry.category("web_tour.tours").add("wink_guest_tour", guestTour);
}

if (localStorage.getItem("wink_client_tour_seen") !== "true") {
    registry.category("web_tour.tours").add("wink_client_tour", clientTour);
}
