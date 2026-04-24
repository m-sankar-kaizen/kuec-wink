{
    'name': "KUEC Employee Notice Period",
    'depends': [
                'kaz_kuec_offboarding',
                'hr'],
    'data': [
        'data/cron.xml',
        'data/mail_template.xml',
        'views/res_settings_views.xml',
        'views/hr_contract_views.xml',
    ]
}
