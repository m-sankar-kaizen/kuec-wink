/** @odoo-module **/

import { registry } from "@web/core/registry";
import { Component, onWillStart, useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { DashboardCard, DashboardCardMulti, DashboardCardMultiPeriod, TopVendorCard, DashboardTopRequestTypesCard, DashboardTopDepartmentsCard} from "./components/dashboardCard";
import { FloatFilter } from "./components/floatFilter";

export class ProcurementDashboard extends Component {
    static components = {DashboardCard, DashboardCardMulti, DashboardCardMultiPeriod, TopVendorCard, FloatFilter, DashboardTopRequestTypesCard, DashboardTopDepartmentsCard};
    setup() {
        this.action = useService("action");
        this.orm = useService("orm");
        const now = new Date();
        const start = new Date(now.getFullYear(), now.getMonth(), 1);
        const end = new Date(now.getFullYear(), now.getMonth() + 1, 0);

        this.current_company_id = this.env.services.company.currentCompany.id
        this.state = useState({
            startDate: null,
            endDate: null,
            company_id: this.current_company_id,
            requisition_type: [],
            vendor: [],
            product: [],
            departments_filter: [],
            dateType: "all",
            data: {},
        });

        onWillStart(async () => {
            const departments = await this.orm.searchRead("hr.department", [
                    ["company_id", "in", [false, this.current_company_id]],
                ], ["id", "name", "color"])

            for (const dept of departments) {
                dept.planned_vs_actual = await this.plannedVsActual(dept.id);
            }

            this.state.departments = departments;
            await this.loadData();

        });
    }

    /**
     * Open HR Department form view
     * @param {Number} departmentId
     */
    openDepartment(departmentId) {
        this.action.doAction({
            name: "Annual Department Procurement Plan",
            type: "ir.actions.act_window",
            res_model: "annual.department.procurement.plan",
            domain: [["department_id", "=", departmentId],
                     ["company_id", "=", this.current_company_id]],
            views: [
                [false, "list"],
                [false, "form"],
            ],
        });
    }

    async plannedVsActual(departmentId) {
        return await this.orm.call(
            "annual.department.procurement.plan",
            "get_planned_vs_actual",
            [departmentId, this.current_company_id],
            {}
        );
    }

    get filterProps() {
        return {
            startDate: this.state.startDate,
            endDate: this.state.endDate,
            requisition_type: this.state.requisition_type,
            vendor: this.state.vendor,
            product: this.state.product,
            departments: this.state.departments_filter,
            company_id: this.current_company_id,
            dateTypes: this.dateTypes,
            dateType: this.state.dateType,
            handleFilterChange: this.handleFilterChange.bind(this),
        };
    }

    async handleFilterChange(values) {
        this.state.startDate = values.startDate;
        this.state.endDate = values.endDate;
        this.state.requisition_type = values.requisition_type;
        this.state.vendor = values.vendor;
        this.state.product = values.product;
        this.state.departments_filter = values.departments;
        this.state.dateType = values.dateType;

        await this.loadData();
    }


    formatDate(date) {
        const offset = date.getTimezoneOffset();
        const localDate = new Date(date.getTime() - offset * 60 * 1000);
        return localDate.toISOString().split('T')[0];
    }

    async loadData() {
        const {
            requisition_type,
            vendor,
            product,
            departments_filter,
            startDate,
            endDate,
            company_id,
        } = this.state;

        const data = await this.orm.call(
            "annual.department.procurement.plan",
            "load_data",
            [
                {
                    requisition_type,
                    vendor,
                    product,
                    departments: departments_filter,
                    startDate,
                    endDate,
                    company_id,
                },
            ]
        );

        this.state.data = data;
    }


    get dateTypes() {
        return [
            { id: "all", value: "All Dates" },
            {id: 'this_month', value:"This Month"},
            {id: 'last_month', value: "Last Month"},
            {id: 'this_year', value: "This Year"},
            {id: 'last_year', value: "Last Year"},
            {id: 'custom', value: "Custom"},
        ]
    }


}

ProcurementDashboard.template = "kaz_kuec_procurement_plan_monitoring.Dashboard";

registry.category("actions").add("kaz_kuec_procurement_plan_monitoring.action_purchase_requisition_dashboard", ProcurementDashboard);
