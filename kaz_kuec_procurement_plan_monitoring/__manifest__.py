{
    'name': 'Kaz Kuec Procurement Plan Monitoring',
    'depends': [
        'base',
        'material_purchase_requisitions',
        'department_procurement',
        'kaz_procurement_doa_kuec',
        'kaz_vendor_management'
    ],
    'data': [
        'views/menu.xml'
    ],
    'assets': {
        'web.assets_backend': [
            'https://cdn.jsdelivr.net/npm/echarts@5.6.0/dist/echarts.min.js',
            'kaz_kuec_procurement_plan_monitoring/static/src/css/procurement_plan_monitoring_dashboard.css',
            'kaz_kuec_procurement_plan_monitoring/static/src/css/main.css',
            'kaz_kuec_procurement_plan_monitoring/static/src/xml/procurement_plan_monitoring_dashboard.xml',
            'kaz_kuec_procurement_plan_monitoring/static/src/js/components/**/*',
            'kaz_kuec_procurement_plan_monitoring/static/src/js/procurement_plan_monitoring_dashboard.js',
        ],
    },
}
