/** @odoo-module */

export class makeChartValue {
    constructor(values, chartType, additionalOptions={}) {
        this.values = values;
        this.chartType = chartType;
        this.additionalOptions = additionalOptions;
    }

    getData() {
        if (typeof this[this.chartType]==="function") {
            return this[this.chartType]();
        }
        console.warn(`Chart type method "${this.chartType}" not found.`);

        return {};
    }

    midYearChart() {
        return {
            title: {
                text: 'Mid-Year Status',
                left: 'center'
            },
            tooltip: {
                trigger: 'item'
            },
            legend: {
                orient: 'vertical',
                left: 'left'
            },
            series: [ {
                name: 'Status',
                type: 'pie',
                radius: '50%',
                data: this.values,
                label: {
                    show: true,
                    formatter: "{b} ({d}%)"
                },
                emphasis: {
                    itemStyle: {
                        shadowBlur: 10,
                        shadowOffsetX: 0,
                        shadowColor: 'rgba(0, 0, 0, 0.5)',
                    }
                }
            }]
        };
    }

    yearComparisonChart() {
        return {
            title: {
                text: 'YoY - Average Annual Rating'
            },
            tooltip: {
                trigger: 'item',
                formatter: '{b}: {c}'
            },
            xAxis: this.additionalOptions.xAxis,
            yAxis: {
                type: 'value'
            },
            series: [ {
                type: 'bar',
                data: this.values,
                // last year, this year
                itemStyle: {
                    color: function(params) {
                        return params.dataIndex===0 ? '#5470C6': '#91CC75';
                    }
                }
            } ]
        };
    }

    annualChart() {
        const colors = [
            '#E74C3C', // Rating 1 – Low (Red)
            '#F39C12', // Rating 2 – Below Avg (Orange)
            '#F1C40F', // Rating 3 – Good (Yellow)
            '#2ECC71'  // Rating 4 – High (Green)
        ];

        return {
            title: {
                text: 'Annual Distribution'
            },
            tooltip: {
                trigger: 'item',
                formatter: '{b}: {c}'
            },
            xAxis: this.additionalOptions.xAxis,
            yAxis: {
                type: 'value'
            },
            series: [
                {
                    type: 'bar',
                    data: this.values,
                    itemStyle: {
                        color: (params) => colors[params.dataIndex]
                    },
                    label: {
                        show: true,
                        position: 'top'
                    }
                }
            ]
        };
    }

}