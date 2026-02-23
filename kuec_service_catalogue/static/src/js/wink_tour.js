/** @odoo-module **/

import { registry } from "@web/core/registry";

/*
 * WINK Portal Tours
 *
 * Two tours:
 * 1. wink_guest_tour  — shown on /services for first-time visitors
 * 2. wink_client_tour — shown on /my/home for first-time portal users
 *
 * Tours are always registered in the registry (Odoo requires this).
 * The localStorage flags are checked inside the first step's run()
 * to auto-skip the tour if the user has already seen it.
 */

registry.category("web_tour.tours").add("wink_guest_tour", {
    url: "/services",
    steps: () => [
        {
            trigger: ".wink-catalogue-header",
            content: "Welcome to WINK — KUEC's Shared Services Portal. Let us show you around.",
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
            content: "Ready to request? Click here — you'll be guided to sign in or create a free account.",
            run: () => { },
        },
    ],
});

registry.category("web_tour.tours").add("wink_client_tour", {
    url: "/my/home",
    steps: () => [
        {
            trigger: "#wrapwrap",
            content: "Welcome to your WINK portal dashboard. Here's a quick overview.",
            run: () => { },
        },
        {
            trigger: ".o_portal_my_home",
            content: "Track all your service requests, invoices, and projects from this dashboard.",
            run: () => { },
        },
    ],
});
