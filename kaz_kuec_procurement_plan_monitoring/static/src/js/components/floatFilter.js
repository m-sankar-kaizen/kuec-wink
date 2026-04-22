/* @odoo-module */
import { Component, useState } from "@odoo/owl";
import { MultiRecordSelector } from "@web/core/record_selectors/multi_record_selector";

export class FloatFilter extends Component {
    static template = "FloatFilter";
    static components = { MultiRecordSelector };

    setup() {
        this.state = useState({
            open: false,
            startDate: this.props.startDate,
            endDate: this.props.endDate,
            requisition_type: this.props.requisition_type || [],
            vendor: this.props.vendor || [],
            product: this.props.product || [],
            departments: this.props.departments || [],
            dateTypes: this.props.dateTypes,
            dateType: this.props.dateType,
        });
    }

    handleDateTypeChange() {
        const now = new Date();
        let start, end;

        switch (this.state.dateType) {
            case "all":
                this.state.startDate = null;
                this.state.endDate = null;
                return;
            case "this_month":
                start = new Date(now.getFullYear(), now.getMonth(), 1);
                end = new Date(now.getFullYear(), now.getMonth() + 1, 0);
                break;
            case "last_month":
                start = new Date(now.getFullYear(), now.getMonth() - 1, 1);
                end = new Date(now.getFullYear(), now.getMonth(), 0);
                break;
            case "this_year":
                start = new Date(now.getFullYear(), 0, 1);
                end = new Date(now.getFullYear(), 11, 31);
                break;
            case "last_year":
                start = new Date(now.getFullYear() - 1, 0, 1);
                end = new Date(now.getFullYear() - 1, 11, 31);
                break;
            case "custom":
                return;
        }

        this.state.startDate = this.formatDate(start);
        this.state.endDate = this.formatDate(end);
    }

    formatDate(date) {
        const offset = date.getTimezoneOffset();
        return new Date(date.getTime() - offset * 60000)
            .toISOString()
            .split("T")[0];
    }

    handleOnChangeDate() {
        this.state.dateType = "custom";
    }

    onUpdateRequisitionType(value) {
        this.state.requisition_type = value;
    }

    onUpdateVendor(value) {
        this.state.vendor = value;
    }

    onUpdateDepartment(value) {
        this.state.departments = value;
    }

    onUpdateProduct(value) {
        this.state.product = value;
    }

    toggleFilterPanel() {
        this.state.open = !this.state.open;
    }

    handleApply() {
        this.state.open = false;
        this.props.handleFilterChange({ ...this.state });
    }
}
