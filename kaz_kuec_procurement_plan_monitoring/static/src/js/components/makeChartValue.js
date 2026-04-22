/** @odoo-module */

export class makeChartValue {
    constructor(values, chartType) {
        this.values = values;
        this.chartType = chartType;
    }

    getData() {
        if (typeof this[this.chartType] === "function") {
            return this[this.chartType]();
        }
        console.warn(`Chart type method "${this.chartType}" not found.`);
        return {};
    }

    barUnitStatusChart() {
        const body = this.values || [];

        const categories = body.map(row => row.project_name);
        const units = body.map(row => row.number_of_units);
        const available = body.map(row => row.number_of_units_available);
        const hold = body.map(row => row.number_of_units_on_hold);
        const booked = body.map(row => row.number_of_units_booked);
        const sold = body.map(row => row.number_of_units_sold);

        return {
            tooltip: {
                trigger: 'axis',
                axisPointer: { type: 'shadow' }
            },
            legend: {},
            grid: {
                left: '3%',
                right: '4%',
                bottom: '3%',
                containLabel: true
            },
            xAxis: { type: 'value' },
            yAxis: {
                type: 'category',
                data: categories || []
            },
            series: [
                { name: 'Total Units', type: 'bar', stack: 'total', label: { show: false }, data: units },
                { name: 'Available', type: 'bar', stack: 'total', label: { show: false }, data: available },
                { name: 'On Hold', type: 'bar', stack: 'total', label: { show: false }, data: hold },
                { name: 'Booked', type: 'bar', stack: 'total', label: { show: false }, data: booked },
                { name: 'Sold', type: 'bar', stack: 'total', label: { show: false }, data: sold },
            ]
        };
    }

    pieUnitStatusChart() {
        const kpiData = this.values || [];

        // Filter relevant KPI values
        const mapping = {
            'All Properties': 'All Properties',
            'Vacant': 'Vacant',
            'Sold': 'Sold',
            'On Hold': 'On Hold'
        };

        const pieData = kpiData
            .filter(item => mapping[item.text])
            .map(item => ({
                value: item.value,
                name: item.text
            }));

        return {
            tooltip: {
                trigger: 'item'
            },
            legend: {
                top: '5%',
                left: 'center'
            },
            series: [
                {
                    name: 'Unit Distribution',
                    type: 'pie',
                    radius: ['40%', '70%'],
                    avoidLabelOverlap: false,
                    label: {
                        show: false,
                        position: 'center'
                    },
                    emphasis: {
                        label: {
                            show: false,
                            fontSize: 20,
                            fontWeight: 'bold'
                        }
                    },
                    labelLine: {
                        show: false
                    },
                    data: pieData
                }
            ]
        };
    }

    pieSqftStatusChart() {
        const kpiData = this.values || [];

        const mapping = {
            'Total SQFT': 'Total SQFT',
            'Vacant SQFT': 'Vacant SQFT',
            'Sold SQFT': 'Sold SQFT',
            'On Hold SQFT': 'On Hold SQFT'
        };

        const pieData = kpiData
            .filter(item => mapping[item.text])
            .map(item => ({
                value: item.value,
                name: item.text
            }));

        return {
            tooltip: {
                trigger: 'item'
            },
            legend: {
                top: '5%',
                left: 'center'
            },
            series: [
                {
                    name: 'SQFT Distribution',
                    type: 'pie',
                    radius: ['40%', '70%'],
                    avoidLabelOverlap: false,
                    label: {
                        show: false,
                        position: 'center'
                    },
                    emphasis: {
                        label: {
                            show: false,
                            fontSize: 20,
                            fontWeight: 'bold'
                        }
                    },
                    labelLine: {
                        show: false
                    },
                    data: pieData
                }
            ]
        };
    }

    barSqftStatusChart() {
        const body = this.values || [];

        const categories = body.map(row => row.project_name);
        const total = body.map(row => row.total_sqft || 0);
        const available = body.map(row => row.available_total_sqft || 0);
        const hold = body.map(row => row.hold_total_sqft || 0);
        const booked = body.map(row => row.booked_total_sqft || 0);
        const sold = body.map(row => row.sold_total_sqft || 0);

        return {
            tooltip: {
                trigger: 'axis',
                axisPointer: { type: 'shadow' }
            },
            legend: {},
            grid: {
                left: '3%',
                right: '4%',
                bottom: '3%',
                containLabel: true
            },
            xAxis: { type: 'value' },
            yAxis: {
                type: 'category',
                data: categories
            },
            series: [
                {
                    name: 'Total SQFT',
                    type: 'bar',
                    stack: 'total',
                    label: { show: false },
                    data: total
                },
                {
                    name: 'Available SQFT',
                    type: 'bar',
                    stack: 'total',
                    label: { show: false },
                    data: available
                },
                {
                    name: 'Hold SQFT',
                    type: 'bar',
                    stack: 'total',
                    label: { show: false },
                    data: hold
                },
                {
                    name: 'Booked SQFT',
                    type: 'bar',
                    stack: 'total',
                    label: { show: false },
                    data: booked
                },
                {
                    name: 'Sold SQFT',
                    type: 'bar',
                    stack: 'total',
                    label: { show: false },
                    data: sold
                }
            ]
        };
    }

    barProjectFinancialChart() {
        const body = this.values || [];

        const categories = body.map(row => row.project_name);

        const totalSales = body.map(row => row.total_sales_price || 0);
        const deferredRevenue = body.map(row => row.deferred_revenue || 0);
        const recognizedRevenue = body.map(row => row.recognized_revenue || 0);
        const deferredExpense = body.map(row => row.deferred_expense || 0);
        const recognizedExpense = body.map(row => row.recognized_expense || 0);
        const grossMargin = body.map(row => row.overall_gross_margin || 0);

        // Calculate category width for 4 projects visible
        // You might want to set a fixed width per category or leave to ECharts auto sizing
        // We will use dataZoom slider to allow horizontal scrolling

        return {
            tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
            legend: {
                data: ['Total Sales Price', 'Deferred Revenue', 'Recognized Revenue', 'Deferred Expense', 'Recognized Expense', 'Gross Margin']
            },
            grid: { left: '3%', right: '4%', bottom: '15%', containLabel: true },
            xAxis: {
                type: 'category',
                data: categories,
                axisLabel: {
                    interval: 0, // show all labels
                    rotate: 30 // rotate labels for readability
                }
            },
            yAxis: { type: 'value' },
            dataZoom: [
                {
                    type: 'slider',
                    show: true,
                    xAxisIndex: 0,
                    start: 0,
                    end: Math.min(100, (4 / categories.length) * 100), // Show 4 projects initially or less if fewer projects
                    bottom: 0,
                    height: 20
                },
                {
                    type: 'inside',
                    xAxisIndex: 0
                }
            ],
            series: [
                { name: 'Total Sales Price', type: 'bar', data: totalSales },
                { name: 'Deferred Revenue', type: 'bar', data: deferredRevenue },
                { name: 'Recognized Revenue', type: 'bar', data: recognizedRevenue },
                { name: 'Deferred Expense', type: 'bar', data: deferredExpense },
                { name: 'Recognized Expense', type: 'bar', data: recognizedExpense },
                { name: 'Gross Margin', type: 'bar', data: grossMargin },
            ]
        };
    }

    deferredRevEx() {
        const body = this.values || [];

        const categories = body.map(row => row.project_name);
        const deferredRevenue = body.map(row => row.deferred_revenue || 0);
        const deferredExpense = body.map(row => row.deferred_expense || 0);

        return {
            tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
            legend: {
                data: ['Deferred Revenue', 'Deferred Expense']
            },
            grid: {
                left: '3%',
                right: '4%',
                bottom: '15%',
                containLabel: true
            },
            xAxis: {
                type: 'category',
                data: categories,
                axisLabel: {
                    interval: 0,
                    rotate: 30
                }
            },
            yAxis: { type: 'value' },
            dataZoom: [
                {
                    type: 'slider',
                    show: true,
                    xAxisIndex: 0,
                    start: 0,
                    end: Math.min(100, (4 / categories.length) * 100),
                    bottom: 0,
                    height: 20
                },
                {
                    type: 'inside',
                    xAxisIndex: 0
                }
            ],
            series: [
                {
                    name: 'Deferred Revenue',
                    type: 'bar',
                    data: deferredRevenue,
                    itemStyle: { color: '#3c8dbc' }
                },
                {
                    name: 'Deferred Expense',
                    type: 'bar',
                    data: deferredExpense,
                    itemStyle: { color: '#f39c12' }
                }
            ]
        };
    }

    recognizedRevEx() {
        const body = this.values || [];

        const categories = body.map(row => row.project_name);
        const recognizedRevenue = body.map(row => row.recognized_revenue || 0);
        const recognizedExpense = body.map(row => row.recognized_expense || 0);

        return {
            tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
            legend: {
                data: ['Recognized Revenue', 'Recognized Expense']
            },
            grid: {
                left: '3%',
                right: '4%',
                bottom: '15%',
                containLabel: true
            },
            xAxis: {
                type: 'category',
                data: categories,
                axisLabel: {
                    interval: 0,
                    rotate: 30
                }
            },
            yAxis: { type: 'value' },
            dataZoom: [
                {
                    type: 'slider',
                    show: true,
                    xAxisIndex: 0,
                    start: 0,
                    end: Math.min(100, (4 / categories.length) * 100),
                    bottom: 0,
                    height: 20
                },
                {
                    type: 'inside',
                    xAxisIndex: 0
                }
            ],
            series: [
                {
                    name: 'Recognized Revenue',
                    type: 'bar',
                    data: recognizedRevenue,
                    itemStyle: { color: '#28a745' } // green
                },
                {
                    name: 'Recognized Expense',
                    type: 'bar',
                    data: recognizedExpense,
                    itemStyle: { color: '#dc3545' } // red
                }
            ]
        };
    }

    committedRevEx() {
        const body = this.values || [];
        const categories = body.map(row => row.project_name);
        const committedRevenue = body.map(row => row.total_committed_revenue || 0);
        const committedExpense = body.map(row => row.total_committed_expense || 0);

        return {
            tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
            legend: {
                data: ['Committed Revenue', 'Committed Expense']
            },
            grid: {
                left: '3%',
                right: '4%',
                bottom: '15%',
                containLabel: true
            },
            xAxis: {
                type: 'category',
                data: categories,
                axisLabel: {
                    interval: 0,
                    rotate: 30
                }
            },
            yAxis: { type: 'value' },
            dataZoom: [
                {
                    type: 'slider',
                    show: true,
                    xAxisIndex: 0,
                    start: 0,
                    end: Math.min(100, (4 / categories.length) * 100),
                    bottom: 0,
                    height: 20
                },
                {
                    type: 'inside',
                    xAxisIndex: 0
                }
            ],
            series: [
                {
                    name: 'Committed Revenue',
                    type: 'bar',
                    data: committedRevenue,
                    itemStyle: { color: '#17a2b8' } // teal
                },
                {
                    name: 'Committed Expense',
                    type: 'bar',
                    data: committedExpense,
                    itemStyle: { color: '#dc3545' } // red
                }
            ]
        };
    }

    overallGrsMarginMarkup() {
        const body = this.values || [];

        const categories = body.map(row => row.project_name);
        const grossMarginPercent = body.map(row => row.overall_gross_margin_percent || 0);
        const markupPercent = body.map(row => row.overall_markup_percent || 0);

        return {
            tooltip: {
                trigger: 'axis',
                axisPointer: { type: 'shadow' },
                valueFormatter: (value) => `${value}%`
            },
            legend: {
                data: ['Gross Margin %', 'Markup %']
            },
            grid: {
                left: '3%',
                right: '4%',
                bottom: '15%',
                containLabel: true
            },
            xAxis: {
                type: 'category',
                data: categories,
                axisLabel: {
                    interval: 0,
                    rotate: 30
                }
            },
            yAxis: {
                type: 'value',
                axisLabel: {
                    formatter: '{value}%'
                }
            },
            dataZoom: [
                {
                    type: 'slider',
                    show: true,
                    xAxisIndex: 0,
                    start: 0,
                    end: Math.min(100, (4 / categories.length) * 100),
                    bottom: 0,
                    height: 20
                },
                {
                    type: 'inside',
                    xAxisIndex: 0
                }
            ],
            series: [
                {
                    name: 'Gross Margin %',
                    type: 'bar',
                    data: grossMarginPercent,
                    itemStyle: { color: '#20c997' } // greenish
                },
                {
                    name: 'Markup %',
                    type: 'bar',
                    data: markupPercent,
                    itemStyle: { color: '#ffc107' } // yellow
                }
            ]
        };
    }

}
