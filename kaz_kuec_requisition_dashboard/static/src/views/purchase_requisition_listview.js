/** @odoo-module **/

import { registry } from "@web/core/registry";
import { listView } from "@web/views/list/list_view";
import { ListRenderer } from "@web/views/list/list_renderer";
import { PurchaseRequisitionDashBoard } from "@kaz_kuec_requisition_dashboard/views/purchase_requisition_dashboard";

export class PurchaseRequisitionDashBoardRenderer extends ListRenderer {
    static template = "kaz_kuec_requisition_dashboard.PurchaseRequisitionListView";
    static components = {
        ...ListRenderer.components,
        PurchaseRequisitionDashBoard,
    };

    async setup() {
        await super.setup();

        this.isKUEC = false;

        const companyId = this.env.services.company.currentCompany.id;
        const orm = this.env.services.orm;

        const [company] = await orm.read(
            "res.company",
            [companyId],
            ["company_code"]
        );

        this.isKUEC = company?.company_code === "KUEC";
    }
}

export const PurchaseRequisitionDashBoardListView = {
    ...listView,
    Renderer: PurchaseRequisitionDashBoardRenderer,
};

registry.category("views").add(
    "material_purchase_requisition_dashboard_list",
    PurchaseRequisitionDashBoardListView
);
