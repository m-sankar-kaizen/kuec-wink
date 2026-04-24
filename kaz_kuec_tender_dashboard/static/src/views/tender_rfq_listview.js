/** @odoo-module **/

import { registry } from "@web/core/registry";
import { listView } from "@web/views/list/list_view";
import { ListRenderer } from "@web/views/list/list_renderer";
import { TenderRfqDashBoard } from "@kaz_kuec_tender_dashboard/views/tender_rfq_dashboard";

export class TenderRfqDashBoardRenderer extends ListRenderer {
    static template = "kaz_kuec_tender_dashboard.TenderRfqListView";
    static components = {
        ...ListRenderer.components,
        TenderRfqDashBoard,
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

export const TenderRfqDashBoardListView = {
    ...listView,
    Renderer: TenderRfqDashBoardRenderer,
};

registry.category("views").add(
    "tender_rfq_dashboard_list",
    TenderRfqDashBoardListView
);
