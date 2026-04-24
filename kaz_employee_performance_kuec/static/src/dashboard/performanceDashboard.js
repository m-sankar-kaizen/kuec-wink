import { Component, useState, onWillStart } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { Chart } from "./charts/chart";
import { KPI } from "./kpi/kpi";

export class PerformanceDashboard extends Component {
    static template = "PerformanceDashboard";
    static components = {Dropdown, DropdownItem, Chart, KPI}
    setup() {
        this.orm = useService("orm");
        this.state = useState({
            data: {},
            filters: {
                yearIds: [],
            },
            activeFilters: {
                yearId: {},
            },
        });
        this.company = useService("company");
        this.companyId = this.company.currentCompany.id;

        onWillStart(async () => await this.fetchAllData())
    }

    async fetchBasicData() {
        const filters = await this.orm.call('performance.evaluation', 'load_dashboard_filter', [this.companyId])
        this.state.filters.yearIds = filters.year_ids
        this.state.activeFilters.yearId = filters.year_ids ? filters.year_ids[filters.year_ids.length - 1] : {}
    }

    async fetchAllData() {
        await this.fetchBasicData();
        await this.fetchData();
    }

    async updateYear(yearId) {
        this.state.activeFilters.yearId = yearId;
        await this.fetchData();
        this.env.bus.trigger("RE_RENDER")
    }

    async fetchData() {
        const yearId = this.state.activeFilters.yearId
        this.state.data = await this.orm.call('performance.evaluation', 'fetch_dashboard_data', [this.companyId, yearId?.id]);
    }

    get midYearStatus() {
        const performanceData = this.state.data.performance_overview;
        return {
            data: [
                { value: performanceData.on_track_pct, name: 'On Track' },
                { value: performanceData.off_track_pct, name: 'Off Track' },
                { value: performanceData.no_track_pct, name: 'N/A' },
            ],
            chartMethod: "midYearChart",
            type: 'pie'
        }
    }

    get yearEndStatus() {
        const performanceData = this.state.data.performance_overview;
        return {
            data: [performanceData.avg_prev_annual_rating, performanceData.avg_annual_rating],
            chartMethod: "yearComparisonChart",
            type: 'bar',
            additionalOptions: {
                xAxis: {
                    type: 'category',
                    data: [performanceData.prev_year_name, performanceData.current_year_name]
                }
            }
        }
    }

    get annualDistribution() {
        const annualData = this.state.data.annual_distribution;
        return {
            data: [annualData.rating_1, annualData.rating_2, annualData.rating_3, annualData.rating_4],
            chartMethod: "annualChart",
            type: 'bar',
            additionalOptions: {
                xAxis: {
                    type: 'category',
                    data: ["Rating 1", "Rating 2", "Rating 3", "Rating 4"]
                }
            }
        }
    }

    get midEvalKpi() {
        const performanceData = this.state.data.performance_overview;
        return {
           midEvaluated: performanceData.mid_year_evaluated,
           total: performanceData.total_records,
           heading: 'Mid-Year Employees Evaluated',
           className: 'blue-background'
        }
    }

    get yearEvalKpi() {
        const performanceData = this.state.data.performance_overview;
        return {
           yearEndEvaluated: performanceData.year_end_evaluated,
           total: performanceData.total_records,
           heading: 'Year-End Employees Evaluated',
           className: 'green-background'
        }
    }

    get avgAnnualRating() {
        const performanceData = this.state.data.performance_overview;
        return {
           rating: performanceData.avg_annual_rating,
           heading: "Average Annual Rating",
           year: performanceData.current_year_name,
           className: 'purple-background'
        }
    }

    get yoyAnnualRating() {
        const performanceData = this.state.data.performance_overview;
        const prevYear = performanceData.avg_prev_annual_rating
        const currentYear = performanceData.avg_annual_rating
        const yoy = ((currentYear - prevYear) / prevYear) * 100
        return {
           rating: yoy,
           heading: "Year-Over-Year Improvement Rate",
           className: 'bright-purple-background'
        }
    }

    get improvedKPI() {
        const yoy = this.state.data.yoy_analysis;
        return {
           rating: yoy.improved,
           heading: "Improved Performance",
           className: 'tinted-blue-background'
        }
    }

    get stableKPI() {
        const yoy = this.state.data.yoy_analysis;
        return {
           rating: yoy.stable,
           heading: "Consistent Performance",
           className: 'tinted-yellow-background'
        }
    }

    get declinedKPI() {
        const yoy = this.state.data.yoy_analysis;
        return {
           rating: yoy.declined,
           heading: "Declined Performance",
           className: 'tinted-red-background'
        }
    }
}

registry.category("actions").add("performance_dashboard", PerformanceDashboard);
