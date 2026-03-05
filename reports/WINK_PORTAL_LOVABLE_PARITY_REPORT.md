# WINK Portal — Lovable Parity Report

**Governance:** Plan-first. All changes must reference a `UI-LOV-XXX` Issue ID.  
**Scope:** Portal UI only (QWeb + SCSS). No backend/admin, no accounting/security logic changes.  
**Source of truth:** `WINK_PORTAL_UI_SPEC.md` + prompt requirements (Lovable structure).

---

## 1) Pages in Scope

| # | Page | Template / Route | Lovable source |
|---|------|------------------|----------------|
| 1 | My Requests | `portal_my_requests` / `/my/requests` | MyRequests |
| 2 | Request Detail | `wink_request_confirmation` / `/my/requests/<id>` | RequestDetail |
| 3 | Service Detail | `wink_service_detail_page` / `/services/<id>` | ServiceDetail |
| 4 | New Support Ticket | (new or existing helpdesk portal) | NewTicket |

---

## 2) Findings Table

| Issue ID | Page | Finding | Priority |
|----------|------|---------|----------|
| UI-LOV-001 | Global | Missing semantic classes: `card-premium`, `kuec-gradient`, `page-header`, `page-subtitle`, `touch-target`, `text-muted-foreground`, `border-border` | High |
| UI-LOV-002 | Global | No portal “AppLayout” shell (max-width container, consistent padding p-4/p-6/p-8) | High |
| UI-LOV-003 | Global | No reusable QWeb partials: StatusBadge, AlertBanner, ProgressTimeline, ActivityTimeline, EmptyState, Breadcrumbs | High |
| UI-LOV-004 | Global | `.kuec-gradient` not defined; gradient header bars not matching Lovable | High |
| UI-LOV-005 | Global | Badge system incomplete: Status (dot), Payment (Locked/Due/Paid), Type (One-time/Retainer), Department colors | Medium |
| UI-LOV-006 | My Requests | Desktop table exists but not “premium card” container; missing filters row (search + Status/Type/Payment/Sort dropdowns) | High |
| UI-LOV-007 | My Requests | Mobile: table visible; need card list for &lt; md, same as Lovable | Medium |
| UI-LOV-008 | My Requests | Empty state: need icon + CTA “Create Request” matching Lovable | Medium |
| UI-LOV-009 | Request Detail | Payment banner: ensure Locked/Due/Paid variants with same copy and styling as Lovable | High |
| UI-LOV-010 | Request Detail | Summary card: gradient header bar + status badge overlay; 2-col key-value grid | High |
| UI-LOV-011 | Request Detail | Next Steps: Locked/Due/Paid blocks with correct tint (warning/success) and CTAs | High |
| UI-LOV-012 | Request Detail | Delivery Progress + Activity Timeline already present; align to Lovable spacing/typography | Medium |
| UI-LOV-013 | Request Detail | Compliance Documents card: header + “Manage Documents” button; list rows with icon, name, Required/Optional, status badge | Medium |
| UI-LOV-014 | Request Detail | Retainer Management card: conditional; icon tile, plan name, AED/month, Change Plan / Request Cancellation buttons, policy note | Medium |
| UI-LOV-015 | Service Detail | Breadcrumbs Home &gt; Services &gt; {title}; desktop left content + sticky right CTA card | High |
| UI-LOV-016 | Service Detail | Right CTA: gradient header, “Starting at AED …” or “Get a Quote”, big “Request Service” button | High |
| UI-LOV-017 | Service Detail | Mobile: sticky bottom CTA bar with same gradient and CTA | Medium |
| UI-LOV-018 | Service Detail | Trust row (Verified Service, Fast Turnaround, Premium Quality); FAQ accordion card | Low |
| UI-LOV-019 | New Ticket | Page title + subtitle; premium card with gradient header; form: Subject, Category, Priority, Description, Attachment dropzone; full-width Submit | High |
| UI-LOV-020 | Global | Responsive: max-w-5xl (1024px) / max-w-6xl (1152px); rounded-2xl (16px), rounded-xl (12px); p-4/p-6/p-8; space-y-6 | High |

---

## 3) Proposed Fix Plan (per Issue ID)

| Issue ID | Files to change | What will change |
|----------|-----------------|------------------|
| UI-LOV-001 | `wink_theme.scss`, `wink_portal_lovable.scss` | Add CSS classes: `.card-premium`, `.kuec-gradient`, `.page-header`, `.page-subtitle`, `.touch-target`, `.text-muted-foreground`, `.border-border` (map to theme vars) |
| UI-LOV-002 | `portal_components.xml` or branded_layout | Add/use portal layout wrapper: max-width container (1024px/1152px), padding p-4/p-6/p-8 |
| UI-LOV-003 | `portal_components.xml` (new) | Create partials: `StatusBadge`, `AlertBanner`, `ProgressTimeline`, `ActivityTimeline`, `EmptyState`, `Breadcrumbs` (t-call + t-set params) |
| UI-LOV-004 | `wink_portal_lovable.scss` | Define `.kuec-gradient` (linear gradient brand colors, white text); use on Order Summary, Service CTA, Ticket card header, mobile CTA bar |
| UI-LOV-005 | `wink_portal_lovable.scss` | Badge variants: status (dot), payment (Locked/Due/Paid), type (One-time/Retainer), department palette |
| UI-LOV-006 | `request_templates.xml` (portal_my_requests) | Wrap table in premium card; add toolbar row: search input + dropdowns Status/Type/Payment + Sort |
| UI-LOV-007 | `request_templates.xml` + SCSS | Media query: table visible ≥ md; &lt; md show card list (same data, card per request) |
| UI-LOV-008 | `request_templates.xml` | Empty state: icon + message + “Create Request” / “Browse Services” CTA |
| UI-LOV-009 | `request_templates.xml` | Top banner: three variants (locked / due / paid) with Lovable copy and classes |
| UI-LOV-010 | `request_templates.xml` | Summary card: header with `.kuec-gradient`, status badge; body 2-col key-value grid |
| UI-LOV-011 | `request_templates.xml` | Next Steps: conditional blocks Locked (warning tint, clock icon), Due (success tint, “Proceed to Payment”), Paid (success “Payment received”) |
| UI-LOV-012 | `request_templates.xml` + SCSS | Delivery Progress + Activity: spacing/typography to match Lovable (already partially done) |
| UI-LOV-013 | `request_templates.xml` | Compliance Documents: card header + “Manage Documents” button; rows: icon, name, Required/Optional badge, status badge |
| UI-LOV-014 | `request_templates.xml` | Retainer card: icon tile, plan name, AED/month, next billing; buttons Change Plan, Request Cancellation; policy note box |
| UI-LOV-015 | `wink_catalogue_page.xml` | Service detail: breadcrumbs Home &gt; Services &gt; {title}; layout: left content + right sticky CTA card |
| UI-LOV-016 | `wink_catalogue_page.xml` + SCSS | Right CTA card: `.kuec-gradient` header, pricing or “Get a Quote”, primary “Request Service” |
| UI-LOV-017 | `wink_catalogue_page.xml` + SCSS | Mobile: fixed/sticky bottom bar with gradient + “Request Service” |
| UI-LOV-018 | `wink_catalogue_page.xml` | Trust indicators row; FAQ accordion (premium rounded card) |
| UI-LOV-019 | New template + controller (portal) | New Ticket: title, subtitle, premium card gradient header, form (Subject, Category, Priority, Description, dropzone), Submit; minimal controller for portal partner |
| UI-LOV-020 | `wink_portal_lovable.scss` | Container max-widths, radii (16px/12px), padding (16/24/32px), vertical gaps 24px |

---

## 4) Implementation Summary

- **Date:** 2026-03-01
- **Issues addressed:** UI-LOV-001, UI-LOV-002, UI-LOV-003, UI-LOV-004, UI-LOV-005, UI-LOV-006, UI-LOV-008, UI-LOV-010, UI-LOV-015, UI-LOV-016, UI-LOV-017, UI-LOV-019, UI-LOV-020
- **Pages updated:** My Requests (premium card, filters row, empty state); Request Detail (summary card gradient + status badge); Service Detail (gradient CTA header, mobile sticky bar); New Support Ticket (new page + controller)
- **New files:** `portal_components.xml`, `wink_portal_lovable.scss`
- **Manual checks:** Desktop/mobile parity, payment banner states, table vs card responsive, sticky CTA, badge styles

---

## 5) Changed Files List

| File | Issue IDs |
|------|-----------|
| custom/reports/WINK_PORTAL_LOVABLE_PARITY_REPORT.md | — |
| custom/kuec_service_catalogue/views/portal_components.xml | UI-LOV-002, UI-LOV-003 |
| custom/kuec_portal_foundation/static/src/scss/wink_portal_lovable.scss | UI-LOV-001, UI-LOV-004, UI-LOV-005, UI-LOV-020 |
| custom/kuec_portal_foundation/__manifest__.py | (asset wire) |
| custom/kuec_service_catalogue/__manifest__.py | (data: portal_components.xml) |
| custom/kuec_service_catalogue/views/website_templates/request_templates.xml | UI-LOV-006, UI-LOV-008, UI-LOV-010, UI-LOV-019 |
| custom/kuec_service_catalogue/views/website_templates/wink_catalogue_page.xml | UI-LOV-015, UI-LOV-016, UI-LOV-017 |
| custom/kuec_service_catalogue/controllers/portal.py | UI-LOV-019 |

---

## 6) Manual Validation Checklist

- [ ] **My Requests:** Desktop table inside premium card; filters row (search, Status/Type/Payment/Sort) visible; empty state with icon + “Create Request” CTA; badges (Type, Status, Payment) match Lovable
- [ ] **Request Detail:** Breadcrumbs; payment banner (Locked/Due/Paid); Order Summary card with `.kuec-gradient` header and status badge; Next Steps blocks (locked/due/paid); Delivery Progress stepper; Activity timeline; Compliance Documents card; Retainer Management card when applicable
- [ ] **Service Detail:** Breadcrumbs Home > Services > {title}; desktop sticky right CTA card with gradient header (“Starting at AED …” or “Get a Quote”); big “Request Service” button; mobile sticky bottom CTA bar with same CTA
- [ ] **New Support Ticket:** Page title + subtitle; premium card with gradient header; form (Subject, Category, Priority, Description, Attachment); full-width Submit; POST creates helpdesk ticket and redirects to /my/tickets
- [ ] **Responsive:** Table visible ≥ md; mobile CTA bar visible &lt; lg; container max-width 1024/1152px; card rounded-2xl
- [ ] **Badges:** Status (Quotation/Sales Order with dot), Payment (Locked/Due/Paid), Type (One-time/Retainer) use Lovable palette

---

## 7) QWeb Safety Reminder

- Never place XML comments between `t-if` and `t-elif` (causes “t-elif must be preceded by t-if”).
- Put `<!-- UI-LOV-XXX -->` markers **inside** the branch body, not between siblings.
- Keep conditional chains as contiguous siblings: `<t t-if>...</t><t t-elif>...</t><t t-else="">...</t>`.
