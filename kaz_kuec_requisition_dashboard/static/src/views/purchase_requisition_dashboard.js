/** @odoo-module */
import { useService } from "@web/core/utils/hooks";
import { Component, onWillStart } from "@odoo/owl";
import { formatDate, today } from "@web/core/l10n/dates";


export class PurchaseRequisitionDashBoard extends Component {
    static template = "kaz_kuec_requisition_dashboard.PurchaseRequisitionDashboard";
    static props = {};
    setup() {
        this.orm = useService("orm");
        this.action = useService("action");

        onWillStart(async () => {
            this.purchaseRequisitionData = await this.orm.call("material.purchase.requisition", "retrieve_dashboard");
        });
    }

    /**
     * This method clears the current search query and activates
     * the filters found in `filter_name` attibute from button pressed
     */
setSearchContext(ev) {
    ev.preventDefault();

    const filter_name = ev.currentTarget.getAttribute("filter_name");
    let domain = [];

    const today = new Date().toISOString().slice(0, 10);

    switch (filter_name) {
        case "draft_rfqs":
            domain = [
                ['kuec_approval_state', 'not in', ['approved','rejected','cancel']]
            ];
            break;

        case "waiting_rfqs":
            domain = [
                ['kuec_approval_state', 'not in', ['draft','approved','rejected','cancel']]
            ];
            break;

        case "late_rfqs":
            domain = [
                ['kuec_approval_state', '=', 'approved'],
                ['purchase_order_ids', '=', false],
            ];
            break;

        case "prs_converted_po":
            domain = [
                ['kuec_approval_state', '=', 'approved'],
                ['purchase_order_ids', '!=', false],
            ];
            break;

        case "activity_today":
            domain = [['activity_ids.date_deadline', '=', today]];
            break;

        case "activity_due":
            domain = [['activity_ids.date_deadline', '<', today]];
            break;

        case "activity_upcoming":
            domain = [['activity_ids.date_deadline', '>', today]];
            break;
    }

    this.action.doAction({
        type: "ir.actions.act_window",
        name: "Purchase Requisitions",
        res_model: "material.purchase.requisition",
        views: [[false, "list"], [false, "form"]],
        domain,
    });
}
}
