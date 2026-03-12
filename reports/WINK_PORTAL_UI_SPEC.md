# WINK Portal UI — Rebuild Spec for Lovable

**Role:** Senior Product Designer + UI/UX Architect  
**Scope:** Portal UI only (no backend/admin screens).  
**Constraints:** Use existing Lovable color palette and fonts; match screenshots with high fidelity; improvements only as “Proposed UX Enhancements.”

---

## 1. Screenshot Analysis & Inventory

### 1.1 Screenshot 1 — Service Catalogue

| Attribute | Details |
|-----------|---------|
| **Page name** | Service Catalogue |
| **Main sections** | Header (blue banner: title, subtitle, search bar); Left sidebar (Filters); Main content (service count + card grid) |
| **Header** | Title: “Service Catalogue”; Subtitle: “Browse and request professional services…”; Search: white rounded input, magnifying glass, placeholder “Search services by name or keyword…” |
| **Sidebar** | “Filters” + filter icon; DEPARTMENT (radio list with icons + counts); SERVICE NATURE (Governmental / Non-Governmental); DELIVERY MODEL (Project / Retainer) |
| **Content** | “Showing 6 services”; 3-column grid of service cards |
| **Components** | Search input, radio buttons (selected = blue fill), service cards (title, description, tags, pricing, “Details” / “Request →”), “POPULAR” badge (orange, star) |
| **States** | Default search; one department selected (Information Tec…); cards in default state |

---

### 1.2 Screenshot 2 — My Requests (List)

| Attribute | Details |
|-----------|---------|
| **Page name** | My Requests |
| **Main sections** | Header (title, subtitle, “+ New Request”); Toolbar (search, filters, sort); Table (requests list) |
| **Header** | Title: “My Requests”; Subtitle: “Track all your service requests and their status.”; CTA: “+ New Request” (primary, right) |
| **Toolbar** | Search: “Search by ID or service name…” (magnifying glass); Dropdowns: “All Status”, “All Types”, “All Payment”; Sort: “Latest” + up/down arrow |
| **Table** | Columns: REQUEST #, (date), SERVICE, TYPE, TOTAL AMOUNT, STATUS, PAYMENT; alternating row background |
| **Components** | Primary button, dropdown buttons, sort button, search input, table, type badges (One-time, Retainer), status badges (Quotation, Sales Order) with dot, payment badges (Locked, Due, Paid) |
| **States** | Quotation + Locked; Sales Order + Due/Paid; default buttons |

---

### 1.3 Screenshot 3 — Request Detail (Order 500056)

| Attribute | Details |
|-----------|---------|
| **Page name** | Request Detail |
| **Main sections** | Breadcrumbs; Top alert banner; Order Summary card; Next Steps card; Delivery Progress card; Activity & Updates card |
| **Breadcrumbs** | Home > My Requests > 500056 |
| **Alert** | Yellow/blue banner: padlock icon, “Payment locked — awaiting coordinator price confirmation…” |
| **Order Summary** | Blue header “Order Summary: S00056”; status badge “Quotation”; key-value: SERVICE, STATUS, REQUESTED START, AMOUNT DUE |
| **Next Steps** | Yellow info block, clock icon, “Payment locked…” text; buttons: “View My Requests”, “Browse More Services >” |
| **Delivery Progress** | Stepper: Submitted (✓) → Quote Revi… (active) → Payment → In Progress → Completed; “Last updated: 2/28/2026” |
| **Activity** | List: “Request submitted…”, “Awaiting coordinator price confirmation” with icons and timestamps |
| **Components** | Breadcrumbs, alert/banner, cards (blue header + white body), badges, key-value pairs, primary/secondary buttons, stepper, timeline |
| **States** | Payment locked; Quotation; Pending coordinator confirmation |

---

### 1.4 Screenshot 4 — Create New Request — Choose Service

| Attribute | Details |
|-----------|---------|
| **Page name** | Create New Request — Step 1: Choose Service |
| **Main sections** | Header (title, subtitle); Stepper (4 steps); Search bar; Service cards grid; Footer “Next” |
| **Stepper** | 1 Choose Service (active, blue); 2 Configure, 3 Employees, 4 Review & Submit (inactive, grey) |
| **Content** | Search “Search services…”; 2×3 grid of service cards (title, description, tags, price or “Request a custom proposal”) |
| **Footer** | “Next” (primary, right arrow) |
| **Components** | Stepper, search input, service cards, primary button with icon |
| **States** | Step 1 active; cards default |

---

### 1.5 Screenshot 5 — Create New Request — Configure

| Attribute | Details |
|-----------|---------|
| **Page name** | Create New Request — Step 2: Configure |
| **Main sections** | Header; Stepper (1 done, 2 active, 3–4 inactive); Selected service card; Form (Requested Start Date, Special Requirements); Back / Next |
| **Selected card** | Light blue background: “IT Support - Monthly Retainer”, “Retainer”, “1,800 AED” |
| **Form** | Requested Start Date (date input, calendar icon); Special Requirements / Notes (textarea, resizable) |
| **Components** | Stepper (completed/active/inactive), card, text input, textarea, ghost “Back”, primary “Next” |
| **States** | Step 2 active; form empty/default |

---

### 1.6 Screenshot 6 — Create New Request — Employees

| Attribute | Details |
|-----------|---------|
| **Page name** | Create New Request — Step 3: Employees |
| **Main sections** | Header; Stepper (1–2 done, 3 active, 4 inactive); “Select Employees for This Service”; Employee list (radio cards); Back / Next |
| **List** | Cards: radio + name (bold) + job title (grey); e.g. Ahmed Al Mansoori, Sara Hassan, Mohammed Ali, Fatima Khalid |
| **Components** | Stepper, section heading, list of radio cards, Back / Next |
| **States** | All radios unselected; step 3 active |

---

### 1.7 Screenshot 7 — Create New Request — Review & Submit

| Attribute | Details |
|-----------|---------|
| **Page name** | Create New Request — Step 4: Review & Submit |
| **Main sections** | Header; Stepper (1–3 done, 4 active); “Review Your Request” card; Back / Submit Request |
| **Card** | SERVICE, TYPE, EMPLOYEES (1); values + “Ahmed Al Mansoori” as blue underlined link |
| **Components** | Stepper, summary card (key-value + link), ghost Back, primary “Submit Request →” |
| **States** | Step 4 active; one employee selected |

---

### 1.8 Screenshot 8 — Request Submitted (Success)

| Attribute | Details |
|-----------|---------|
| **Page name** | Request Submitted (Confirmation) |
| **Main sections** | Success icon; “Request Submitted!”; Message (service name bold); “What happens next?” card (bulleted list); View My Requests / Browse More Services |
| **Components** | Success icon (green circle + checkmark), H1, paragraph, card with list, secondary + primary buttons |
| **States** | Success; informational |

---

### 1.9 Documents Upload / Documents Management (No screenshot — built from patterns)

| Attribute | Details |
|-----------|---------|
| **Page name** | Request Detail — Documents (or Documents section within Request Detail) |
| **Main sections** | Same shell as Request Detail: breadcrumbs (Home > My Requests > [ID]); Order Summary card (blue header) if on same page, else section title “Compliance Documents” or “Documents”; Document list (table or list); Upload area; “Change requested” note when applicable |
| **Layout** | Same page container width and padding as Request Detail; same card spacing rhythm. Section appears as a card or block below Order Summary / Next Steps. |
| **Document list** | Rows: document/requirement name, status badge, submitted date, optional action (View / Re-upload). Use same table component as My Requests: header row, alternating row background, cells with text + Badge/Document status (Not submitted, Under review, Change requested, Approved, Rejected). |
| **Upload** | Drag/drop zone: same border and radius as inputs, card-like container. Optional “Choose file” button. Progress bar during upload (same visual style as stepper connector or a simple progress bar). File validation errors: show as Alert/Banner (Error) or inline error text below zone; reuse existing alert pattern. |
| **Change requested** | When status = Change requested: show coordinator note prominently in a banner or card (same alert/banner style as “Payment locked” — e.g. yellow/light background, icon, message). |
| **States** | Default (list + upload); Loading (skeleton for table); Empty (no documents — empty state from inventory); Error (validation/upload failure — alert); Change requested (banner with note). |
| **Assumption (No screenshot)** | Documents live as a section on Request Detail or a sub-page with same layout. Table columns: Document name, Status, Submitted date. Upload is single or multi-file; validation errors listed per file or as a single message. |
| **Needs Screenshot Validation** | Exact copy for section title; table columns and order; whether upload is inline or modal; exact wording for “Change requested” and coordinator note; allowed file types and error messages. |

---

### 1.10 Employee Directory (No screenshot — built from patterns)

| Attribute | Details |
|-----------|---------|
| **Page name** | Employee Directory (List); Employee Create/Edit; Bulk Upload Results |
| **Main sections (List)** | Same header pattern as My Requests: page title “Employee Directory”, subtitle (e.g. “Manage your company employees.”), primary CTA “+ Add Employee” or “Bulk Upload”. Toolbar: search (same as My Requests), optional filters. Table: same style as My Requests — columns e.g. Name, Job title, Email, Status (if any); alternating rows; no new badge styles unless needed (reuse Type/Status badges if applicable). |
| **Main sections (Create/Edit)** | Same container as Configure step: form in card or white block. Fields: Name, Job title, Email, etc. Label style and input style as in Configure (Requested Start Date, Special Requirements). Buttons: Cancel (ghost), Save (primary). Breadcrumb or back link: “Home > Employee Directory > New” or “Edit”. |
| **Main sections (Bulk Upload)** | Page or modal with same card/container style. Step 1: “Download template” (secondary/ghost button). Step 2: Upload file — same drag/drop as Documents Upload; progress bar. Step 3: Results table — same table component; columns e.g. Row, Name, Email, Status, Error message. Rows with errors: show error in cell or alert; reuse table + inline error or badge “Error”. Buttons: “Back to list” (ghost), “Confirm” (primary) if applicable. |
| **Components** | Page title/subtitle, Primary button, Search input, Table (same as My Requests), Ghost/Primary buttons, Form inputs (text, optional date), Upload (drag/drop + progress), Alert/Banner for bulk errors if needed, Empty state, Skeleton loading. |
| **States** | List: default, empty, loading. Create/Edit: default, validation error. Bulk: upload in progress, success (results table), partial failure (rows with errors). |
| **Assumption (No screenshot)** | List columns: Name, Job title, Email (and optional Status). Bulk upload results show one row per record; “Error” column or message per row. No new component types — reuse Table, Badge, Alert, Upload. |
| **Needs Screenshot Validation** | Exact page title and subtitle; list columns and order; Create/Edit form fields; bulk upload copy (Download template, Upload, Results); result table columns; error presentation (per row vs summary). |

---

### 1.11 Retainer Change Plan Page (No screenshot — built from patterns)

| Attribute | Details |
|-----------|---------|
| **Page name** | Retainer Change Plan (or “Change Plan” within Request Detail) |
| **Main sections** | Same shell as Request Detail: breadcrumbs (Home > My Requests > [ID] or … > Manage retainer). Section title “Change Plan” or “Upgrade / Downgrade”. Left: current plan card (Summary card style with blue header or Info card — plan name, price, current period). Right (or below on mobile): target plan cards in a grid (same card styling as Service cards): title, price, optional badge “Upgrade” or “Downgrade” (Category tag style). Proration preview: one or two lines below selected target — “You will pay AED X” (upgrade) or “Credit AED Y (policy: Wallet / Next invoice / No refund)” (downgrade). Buttons: Back (ghost), Confirm change (primary). Disabled cards: when policy or min_days block change, show reason via existing Alert/tooltip pattern (e.g. greyed card + tooltip or small alert below). |
| **Layout** | Same container width and padding; same card spacing. Two-column on desktop (current | targets), single column on mobile (current then targets). Plan cards same size and shadow as Service cards. |
| **Components** | Breadcrumbs, Summary card (blue header) or Info card (current plan), Plan cards (Service card shape + Upgrade/Downgrade badge), Proration text (body or small bold), Alert/Banner or tooltip for disabled state, Ghost Back, Primary Confirm. |
| **States** | Default (current + list of targets); one target selected (proration shown); disabled (policy/min_days — alert or tooltip); loading (skeleton for cards). |
| **Assumption (No screenshot)** | Current plan is one card; target plans are selectable cards (radio or click). Proration is text only (no separate card). Policy label is short (Wallet / Next invoice / No refund). |
| **Needs Screenshot Validation** | Exact copy for “Change Plan”, “Upgrade”, “Downgrade”; proration line wording; disabled state message; button labels. |

---

### 1.12 Cancellation Preview Page (No screenshot — built from patterns)

| Attribute | Details |
|-----------|---------|
| **Page name** | Cancellation Preview (or “Request Cancellation” within Request Detail) |
| **Main sections** | Same shell as Request Detail: breadcrumbs. Summary card (blue header): “Cancellation” or “Cancel retainer” — key-value: Effective date, Remaining days, Refund/Credit outcome (e.g. “Refund AED X” or “Credit to wallet: AED Y” or “No refund”). Content section: short explanation if needed. Reason: textarea (same as Special Requirements — label “Cancellation reason” or “Reason”). Buttons: Back (secondary/ghost), Confirm cancellation (destructive). After submit: same confirmation pattern as Request Submitted — success icon + “Cancellation requested” (or similar) + “What happens next?” card + View My Requests / Back to request. |
| **Layout** | Same container and card spacing. Single column: summary card, then textarea, then buttons. Confirmation replaces the form or appears as banner/card above. |
| **Components** | Breadcrumbs, Summary card (blue header, key-value), Textarea, Ghost Back, Destructive Confirm, Confirmation banner (success icon + message + list + buttons). |
| **States** | Default (summary + reason + buttons); validation (reason required); after submit (confirmation banner). |
| **Assumption (No screenshot)** | Refund/credit outcome is one line in summary. Destructive button for confirm. Confirmation reuses “Request Submitted!” layout (icon, title, message, “What happens next?”, two buttons). |
| **Needs Screenshot Validation** | Exact copy for summary labels and “What happens next?”; destructive button label; confirmation title and message. |

---

### 1.13 Payment States (No screenshot — built from patterns)

| Attribute | Details |
|-----------|---------|
| **Page name** | Request Detail — Payment Locked / Payable / Paid |
| **Main sections** | Same layout as Request Detail (Screenshot 3): breadcrumbs, Order Summary card (blue header), Next Steps card, Delivery Progress, Activity. Only the alert content and Next Steps content change by state. |
| **Locked** | Alert: padlock icon, “Payment locked — awaiting coordinator price confirmation…” (as in Screenshot 3). Next Steps: yellow info block, “Payment locked…” text; buttons: View My Requests, Browse More Services. Amount Due badge: “Pending coordinator confirmation”. |
| **Payable** | Alert: optional info banner (e.g. “Quote ready — approve and pay when ready”) or none. Next Steps: “Proceed to Payment” or “Pay now” — primary CTA; optional “View quote” secondary. Amount Due: shows amount. |
| **Paid** | Alert: success-style banner (e.g. green checkmark, “Payment received”). Next Steps: “Your request has been confirmed!” or similar; optional “Download receipt” link (blue link). Amount Due or new field: “Paid” badge. |
| **Components** | Same as Request Detail: Breadcrumbs, Alert/Banner (variants: locked, info, success), Order Summary card, Next Steps card (content + buttons), Delivery Progress stepper, Activity timeline. Reuse Badge/Payment (Locked, Due, Paid). |
| **States** | Locked; Payable (Pay now CTA); Paid (confirmation + optional receipt). |
| **Assumption (No screenshot)** | Payable and Paid reuse the same Request Detail layout; no new sections. Receipt is optional link. |
| **Needs Screenshot Validation** | Exact copy for Payable and Paid banners and Next Steps; receipt link label and placement. |

---

## 2. UI Inventory (Reusable Components + Variants)

Use this list in Lovable to define a component library. Match names and variants to the screenshots.

| Component | Variants | Usage |
|-----------|----------|--------|
| **Button** | Primary (solid blue, white text, optional right arrow); Secondary (white, blue border/text); Ghost (grey border, dark text); Destructive; Disabled; Loading | CTAs, navigation, actions |
| **Badge / Status chip** | Type: One-time (grey), Retainer (light blue); Status: Quotation (orange + dot), Sales Order (blue + dot); Payment: Locked (orange), Due (pink/red), Paid (green); Category tags (pill, light bg + colored text); POPULAR (orange, star) | Table cells, cards, filters |
| **Card** | Service card (title, description, tags, price, 2 buttons); Summary card (blue header, white body, key-value); Info card (e.g. selected service, light blue bg); KPI/tile | Catalogue, request detail, steps |
| **Input** | Search (icon left, placeholder); Text; Date (calendar icon); Textarea (resizable) | Forms, toolbar |
| **Radio** | Default; Selected (blue fill); With icon + label + count (sidebar) | Filters, employees |
| **Table** | Header row; Data rows (alternating bg); Cells: text, link, badge | My Requests list |
| **Stepper / Progress** | Step: Completed (blue circle + checkmark), Active (blue outline + number), Pending (grey); Connectors: solid blue (done), dashed grey (pending) | Create flow, Delivery Progress |
| **Alert / Banner** | Payment locked (yellow/blue, padlock); Warning; Error; Info | Request detail top |
| **Breadcrumbs** | Home > My Requests > [ID]; links + current page text | Request detail |
| **Timeline / Activity** | Item: icon + text + timestamp | Activity & Updates |
| **Dropdown** | Filter style (grey border, chevron): “All Status”, “All Types”, “All Payment” | Toolbar |
| **Sort control** | “Latest” + up/down arrow icon | Toolbar |
| **Empty state** | (Define when no requests / no results) | List, search |
| **Skeleton loading** | (Define for tables/cards) | Loading states |
| **Badge / Document status** | Not submitted; Under review; Change requested; Approved; Rejected | Documents list |
| **Upload** | Drag/drop zone (same border/radius as inputs); progress bar; file validation errors (inline or alert) | Documents, Bulk upload |
| **Plan card** | Same shape as Service card; optional badge: Upgrade / Downgrade; proration line (e.g. “You will pay AED X” / “Credit AED Y”) | Retainer Change Plan |
| **Confirmation banner** | Same tone as “Request Submitted!” success block (icon + message + optional actions) | Cancellation confirmed, Payment confirmed |

---

## 3. Mapping Table: Screenshot → Page → Components → Notes

| Screenshot | Page name | Components used | Notes |
|------------|-----------|-----------------|--------|
| 1 | Service Catalogue | Header, Search, Sidebar (Filters, radio + icons + counts), Service cards, POPULAR badge, Details/Request buttons | 3-column grid; one department selected |
| 2 | My Requests (List) | Page title/subtitle, Primary “+ New Request”, Search, Dropdowns (Status/Types/Payment), Sort, Table, Type/Status/Payment badges | Alternating rows; mix of Quotation/Sales Order and Locked/Due/Paid |
| 3 | Request Detail | Breadcrumbs, Alert banner, Order Summary card, Next Steps card (info block + buttons), Delivery Progress stepper, Activity timeline | Payment locked; Quotation; coordinator confirmation pending |
| 4 | Create New Request — Choose Service | Title/subtitle, Stepper (step 1 active), Search, Service cards grid, Next button | First step of 4-step flow |
| 5 | Create New Request — Configure | Stepper (1 done, 2 active), Selected service card, Date input, Textarea, Back / Next | Retainer + 1,800 AED example |
| 6 | Create New Request — Employees | Stepper (1–2 done, 3 active), Section title, Employee radio cards, Back / Next | 4 employees; none selected in screenshot |
| 7 | Create New Request — Review & Submit | Stepper (4 active), “Review Your Request” card (key-value + link), Back / Submit Request | One employee (Ahmed) linked |
| 8 | Request Submitted | Success icon, H1, Message, “What happens next?” card (list), View My Requests / Browse More Services | Generic success template |
| MISSING (built from patterns) | Documents Upload / Management | Breadcrumbs, Summary card or section title, Table (document name, status badge, date), Upload (drag/drop, progress, errors), Alert for “Change requested” + coordinator note | Assumptions: §1.9. Validate: copy, columns, upload placement, error wording |
| MISSING (built from patterns) | Employee Directory (List, Create/Edit, Bulk Upload) | Page title/subtitle, Primary “+ Add”/“Bulk Upload”, Search, Table (same as My Requests), Form (Create/Edit), Upload + Results table with row errors | Assumptions: §1.10. Validate: columns, form fields, bulk copy |
| MISSING (built from patterns) | Retainer Change Plan | Breadcrumbs, Summary/Info card (current plan), Plan cards (Upgrade/Downgrade badge), Proration line, Alert/tooltip for disabled, Back / Confirm | Assumptions: §1.11. Validate: copy, proration wording, disabled message |
| MISSING (built from patterns) | Cancellation Preview | Breadcrumbs, Summary card (effective date, remaining days, refund/credit), Textarea (reason), Back / Confirm cancellation (destructive), Confirmation banner after submit | Assumptions: §1.12. Validate: summary copy, confirmation copy |
| MISSING (built from patterns) | Payment States (Locked / Payable / Paid) | Same as Request Detail; Alert + Next Steps content vary by state; Badge Payment (Locked/Due/Paid); optional receipt link for Paid | Assumptions: §1.13. Validate: Payable/Paid copy, receipt placement |

---

## 4. Design System Application (for Lovable)

- **Colors:** Use the existing Lovable project palette. From screenshots: primary blue (buttons, active step, links); white/grey backgrounds; orange for locked/quotation; green for paid/success; red/pink for due; light blue for retainer/selected.
- **Typography:** Existing fonts; hierarchy: H1 (page title), subtitle (lighter), body, labels (uppercase small for key-value), table headers (bold).
- **Spacing:** Consistent padding in cards and between sections; same gap in grids and between toolbar elements.
- **Borders & radius:** Rounded corners on inputs, buttons, cards, badges; subtle borders on cards and inputs.
- **Icons:** Magnifying glass (search), filter, padlock, clock, checkmark, arrow (left/right), star (POPULAR), calendar, paper plane, gear — keep style consistent.

Define in Lovable:

- **Buttons:** Primary, Secondary, Ghost with optional left/right icon.
- **Badges:** Variants for Type, Status, Payment, Category, POPULAR.
- **Cards:** Service card, Summary card (blue header), Info card (light blue), “What happens next?” (grey card + list).
- **Tables:** Header + striped rows; cell types: text, bold link, badge.
- **Stepper:** 3 step states + 2 connector styles.
- **Alert/Banner:** One variant for “payment locked” (icon + message).
- **Timeline:** Icon + text + timestamp per item.
- **Empty state & skeleton:** Placeholder components for no data / loading.
- **Badge/Document status:** Not submitted, Under review, Change requested, Approved, Rejected (for Documents list).
- **Upload:** Drag/drop zone (same border/radius as inputs); progress bar; validation errors (Alert or inline).
- **Plan card:** Service card shape + Upgrade/Downgrade badge; proration line text.
- **Confirmation banner:** Success icon + message + optional "What happens next?" + actions (for cancellation/payment confirmed).

---

## 5. Rebuild Checklist (Portal Pages)

Use this to rebuild in Lovable; order matches the flow. For pages with no screenshot, follow §1.9–§1.13 and reuse only components from Section 2 + 4.

- [ ] **Service Catalogue** — Header (title, subtitle, search); sidebar filters (DEPARTMENT with icons/counts, SERVICE NATURE, DELIVERY MODEL); “Showing N services”; 3-column service cards (title, description, tags, price, Details / Request →); POPULAR badge where needed.
- [ ] **My Requests** — Title, subtitle, “+ New Request”; search + “All Status” / “All Types” / “All Payment” + “Latest” sort; table with columns and Type/Status/Payment badges; alternating row style. Include Empty state and Skeleton loading.
- [ ] **Request Detail** — Breadcrumbs; alert “Payment locked…”; Order Summary card (blue header, key-value, badges); Next Steps (yellow info + 2 buttons); Delivery Progress (5-step stepper); Activity & Updates (timeline). Include Loading (skeleton) and Error state if applicable.
- [ ] **Create New Request (4 steps)** — Shared header + stepper; Step 1: search + service grid + Next; Step 2: selected service card + date + notes + Back/Next; Step 3: employee radio list + Back/Next; Step 4: review card + Back/Submit Request.
- [ ] **Request Submitted** — Success icon, “Request Submitted!”, message with bold service name, “What happens next?” card, two buttons.
- [ ] **Documents Upload / Management** (§1.9) — Same shell as Request Detail. Section “Compliance Documents” or “Documents”. Table: document name, Status (Badge/Document status), submitted date. Upload: drag/drop zone (same border/radius as inputs), progress, validation errors (Alert or inline). “Change requested” state: banner/card with coordinator note. States: Loading (skeleton), Empty, Error (upload/validation).
- [ ] **Employee Directory** (§1.10) — List: same header as My Requests (“Employee Directory”, subtitle, “+ Add Employee” / “Bulk Upload”), search, table (Name, Job title, Email). Create/Edit: same form layout as Configure step; Cancel (ghost) + Save (primary). Bulk Upload: Download template, Upload (drag/drop + progress), Results table (row-level errors). Empty state, Skeleton.
- [ ] **Retainer Change Plan** (§1.11) — Same shell as Request Detail. Left: current plan (Summary or Info card). Right: target plan cards (Service card style + Upgrade/Downgrade badge). Proration line below selection. Disabled state: Alert or tooltip with reason. Back (ghost) + Confirm change (primary). Skeleton when loading.
- [ ] **Cancellation Preview** (§1.12) — Same shell. Summary card (blue header): effective date, remaining days, refund/credit outcome. Textarea “Cancellation reason”. Back (ghost) + Confirm cancellation (destructive). After submit: Confirmation banner (same pattern as Request Submitted — success icon, message, “What happens next?”, View My Requests / Back).
- [ ] **Payment States** (§1.13) — Same Request Detail layout. Locked: alert + “Payment locked…”, Next Steps with View My Requests / Browse More Services. Payable: optional info alert, Next Steps with “Pay now” (primary). Paid: success banner, “Payment received”, optional “Download receipt” link. Reuse Badge/Payment (Locked, Due, Paid).

---

## 6. Responsiveness

- **Desktop:** Current screenshots (sidebar + grid, full table, stepper horizontal).
- **Mobile:** Same design language: stack sidebar filters (e.g. collapsible or top); single-column card grid; table → cards or horizontal scroll; stepper compact or vertical; buttons full-width or stacked; breadcrumbs truncate if needed.

Do not redesign; only adapt layout (stack, collapse, scroll).

---

## 7. Proposed UX Enhancements

List only; do not implement unless approved.

1. **Service Catalogue — Zero-count filters:** Consider disabling or hiding filter options with count “0” (e.g. “Finance & Acco... 0”) to reduce clutter and confusion.
2. **Service cards — Truncated description:** Add tooltip on hover or “Read more” for long descriptions instead of ellipsis only.
3. **Create flow — “Request a custom proposal”:** If this implies a different workflow than fixed-price services, make the distinction more visible (e.g. different card style or label).
4. **Review & Submit — “Ahmed Al Mansoori” link:** Clarify behavior (e.g. employee profile vs tag). If it’s only a label, consider a badge style instead of link to avoid implying navigation.
5. **Request Detail — Delivery Progress:** Ensure “Quote Revi...” truncation has a tooltip or full label on hover so the step name is clear.
6. **Consistency:** Use the same primary/secondary/ghost button styles and badge variants across Service Catalogue, My Requests, Request Detail, and Create flow so the component library is applied uniformly.

---

## 8. Needs Screenshot Validation (Missing Pages)

When screenshots become available for the following pages, confirm or adjust only these details. Do not redesign; only align copy, columns, and placement.

| Page | What to validate |
|------|------------------|
| **Documents Upload / Management** | Section title ("Compliance Documents" vs "Documents"); table columns and order (Document name, Status, Submitted date, Actions); upload inline vs modal; exact "Change requested" and coordinator-note wording; allowed file types and error message copy. |
| **Employee Directory** | List page title and subtitle; table columns (Name, Job title, Email, Status); Create/Edit form fields; Bulk upload: "Download template", "Upload", Results table columns; per-row vs summary error presentation. |
| **Retainer Change Plan** | "Change Plan" / "Upgrade" / "Downgrade" labels; proration line copy ("You will pay AED X", "Credit AED Y"); policy label (Wallet / Next invoice / No refund); disabled-state message; button labels. |
| **Cancellation Preview** | Summary card labels (Effective date, Remaining days, Refund/credit); "What happens next?" content after submit; destructive button label ("Confirm cancellation"); confirmation title and message. |
| **Payment States** | Payable: banner and "Pay now" / "Proceed to Payment" copy; Paid: success banner and "Download receipt" link label and placement. |

---

## 9. Next Steps

- Apply this spec in Lovable: create the component library (Section 2 + 4), then rebuild each page (Section 5).
- Pages with no screenshot (§1.9–§1.13) are built from the same layout and component patterns; assumptions are noted in each section.
- When new screenshots arrive, update only the mismatched details using Section 8 (Needs Screenshot Validation).
- Keep “Proposed UX Enhancements” (Section 7) separate from the rebuild until you approve changes.
