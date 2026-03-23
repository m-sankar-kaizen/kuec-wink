# -*- coding: utf-8 -*-
import odoo, sys, logging
logging.disable(logging.CRITICAL)
odoo.tools.config.parse_config(['-c', '/etc/odoo/odoo.conf', '-d', 'salih'])
from odoo import api, SUPERUSER_ID
from odoo.modules.registry import Registry

reg = Registry('salih')
with reg.cursor() as cr:
    env = api.Environment(cr, SUPERUSER_ID, {})
    order = env['sale.order'].browse(64)
    partner = env['res.partner'].browse(10)

    print('=== BEFORE ===')
    print('Wallet balance: %s' % partner.wink_wallet_balance)
    print('Order: %s | Total: %s' % (order.name, order.amount_total))

    # Find WEWL journal
    journal = env['account.journal'].search(
        [('code', '=', 'WEWL'), ('company_id', '=', order.company_id.id)], limit=1
    )
    if not journal:
        print('ERROR: WEWL journal not found')
        sys.exit(1)
    print('WEWL journal: %s | default_account: %s' % (
        journal.name,
        journal.default_account_id.name if journal.default_account_id else 'NONE'
    ))

    # Create invoice if none
    invoices = order.invoice_ids.filtered(lambda inv: inv.state != 'cancel')
    if not invoices:
        order._create_invoices(final=True)
        invoices = order.invoice_ids.filtered(lambda inv: inv.state != 'cancel')

    invoice = invoices[0]
    if invoice.state == 'draft':
        invoice.action_post()
    print('Invoice: %s | state=%s | residual=%s' % (invoice.name, invoice.state, invoice.amount_residual))

    if invoice.amount_residual <= 0:
        print('Invoice already paid!')
        sys.exit(0)

    # Ensure payment method line has payment_account_id
    pm_line = journal.inbound_payment_method_line_ids.filtered(lambda l: l.code == 'manual')[:1]
    if pm_line and not pm_line.payment_account_id and journal.default_account_id:
        pm_line.write({'payment_account_id': journal.default_account_id.id})
        print('Set payment_account_id = %s' % journal.default_account_id.name)

    # Create and post payment
    payment = env['account.payment'].create({
        'payment_type': 'inbound',
        'partner_type': 'customer',
        'partner_id': order.partner_id.id,
        'amount': invoice.amount_residual,
        'journal_id': journal.id,
        'currency_id': order.currency_id.id,
        'memo': 'eWallet -- %s' % order.name,
        'payment_method_line_id': pm_line.id if pm_line else False,
    })
    payment.action_post()
    print('Payment posted: %s' % payment.name)

    print('\n=== PAYMENT JV LINES ===')
    for line in payment.move_id.line_ids:
        print('  %s %-35s DR=%10.2f  CR=%10.2f' % (
            line.account_id.code, line.account_id.name, line.debit, line.credit
        ))

    # Reconcile AR lines
    receivable_lines = invoice.line_ids.filtered(
        lambda l: l.account_id.account_type == 'asset_receivable' and not l.reconciled
    )
    payment_receivable = payment.move_id.line_ids.filtered(
        lambda l: l.account_id.account_type == 'asset_receivable' and not l.reconciled
    ) if payment.move_id else env['account.move.line']
    if receivable_lines and payment_receivable:
        (receivable_lines + payment_receivable).reconcile()
        print('\nAR lines reconciled OK')

    # Create wallet transaction
    env['kuec.wallet.transaction'].create({
        'partner_id': partner.id,
        'transaction_type': 'payment',
        'amount': -invoice.amount_residual,
        'description': 'Payment for %s' % order.name,
        'order_id': order.id,
        'currency_id': order.currency_id.id,
    })

    cr.commit()
    print('\n=== AFTER ===')
    print('Wallet balance: %s' % partner.wink_wallet_balance)
    print('Invoice payment state: %s' % invoice.payment_state)
    sys.stdout.flush()
