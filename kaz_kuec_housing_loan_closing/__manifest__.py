{
    'name': "KUEC Housing Loan Closing",
    "depends": [
        'ent_ohrms_loan',
        'kaz_ent_loan',
        'kaz_company_restriction_base'
    ],
    "data":
        [
            'data/hr_loan_data.xml',
            'views/hr_loan_views.xml'
        ]
}
