/** @odoo-module **/
import { Component, useEffect, useState, onWillStart, onMounted } from "@odoo/owl";
import { registry } from "@web/core/registry"
import { rpc } from "@web/core/network/rpc";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { TenderItem } from "@kaz_vendor_management/frontend/tender/tender_item";


const SORT_BY_FIELDS = {
    'create_date': "Newest",
    'name': 'Name',
    'title': 'Title',
    'bid_end_date': 'Closing Date',
}

const TENDER_STATES = {
    'active': 'Open Tender',
    'closed': 'Completed Tender',
    'under_review': 'Under Review',
    'awarded': 'Awarded'
}

export class Tender extends Component {
    static template = "Tender";
    static components = { Dropdown, DropdownItem, TenderItem };
    setup() {
        this.state = useState({
            tenderState: 'active',
            searchQuery: '',
            sortField: 'create_date',
            sortOrder: 'desc',    // or 'asc'
            tenders: [],
            categories: [],
            user: [],
            selectedCategories: [],
            total: 0,
            limit: 20,
            offset: 0,
            currentPage: 1,
            closingDays: 'all',
        })
        useEffect(() => {
            const loadData = async () => {
                await this.fetchTenders();
            };
            loadData();
        }, () => [
            this.state.tenderState,
            this.state.searchQuery,
            this.state.sortField,
            this.state.sortOrder,
            this.state.offset,
            this.state.closingDays,
        ]);
        onWillStart(async ()=> await this.loadBasic())
    }

    toggleState(state) {
        this.state.tenderState = state;
        this.goToPage(1);
    }

    async setSort(field) {
        if (this.state.sortField === field) {
            this.state.sortOrder = this.state.sortOrder === "asc" ? "desc" : "asc";
        } else {
            this.state.sortField = field;
            this.state.sortOrder = "asc";
        }
        this.goToPage(1);
    }

    async clearSearch() {
        this.state.searchQuery = ""
        this.goToPage(1);
    }

    async loadBasic() {
        const response = await rpc('/get/tender/basic-info', {
            company_id: this.props.company_id,
            user_id: this.props.user_id,
        })
        this.state.categories = response.partner_categories;
        this.state.user = response.user;
    }

    async fetchTenders() {
        const response = await rpc('/get/tender/items', {
            company_id: this.props.company_id,
            user_id: this.props.user_id,
            state: this.state.tenderState,
            name: this.state.searchQuery,
            sort_field: this.state.sortField,
            sort_order: this.state.sortOrder,
            limit: this.state.limit,
            offset: this.state.offset,
            closing_day: this.state.closingDays,
            category_ids: this.state.selectedCategories,
        })
        this.state.tenders = response.tenders;
        this.state.total = response.total;
    }

    goToPage(page) {
        this.state.currentPage = page;
        this.state.offset = (page - 1) * this.state.limit;
    }

    nextPage() {
        const maxPage = Math.ceil(this.state.total / this.state.limit);
        if (this.state.currentPage < maxPage) {
            this.goToPage(this.state.currentPage + 1);
        }
    }

    prevPage() {
        if (this.state.currentPage > 1) {
            this.goToPage(this.state.currentPage - 1);
        }
    }

    get displaySortName() {
        const { sortField } = this.state;
        return Object.keys(SORT_BY_FIELDS).includes(sortField) ? SORT_BY_FIELDS[sortField] : 'N/A';
    }

    get sortByFields() {
        return SORT_BY_FIELDS;
    }

    get closingDays() {
        return ['all', 5, 10, 15, 30, 45, 60];
    }

    get tenderStates() {
        return TENDER_STATES;
    }

    async clearCategory() {
        this.state.selectedCategories = []
        await this.fetchTenders();
    }

    async toggleCategory(categoryId) {
        const idx = this.state.selectedCategories.indexOf(categoryId);
        if (idx > -1) {
            // remove
            this.state.selectedCategories.splice(idx, 1);
        } else {
            // add
            this.state.selectedCategories.push(categoryId);
        }
        await this.fetchTenders();
    }

    getTenderProps(props) {
        return {
            ...props,
            categories: this.state.categories,
            user: this.state.user?.[0] || {},
        }
    }

    static props = {
        company_id: { type: Number },
        user_id: { type: Number },
    };
}

registry.category("public_components").add("Tender", Tender);