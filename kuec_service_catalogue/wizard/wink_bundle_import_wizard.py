# -*- coding: utf-8 -*-
import base64
import io
import json
import logging

from odoo import models, fields, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

try:
    import openpyxl
except ImportError:
    openpyxl = None

# Expected column headers (case-insensitive match)
_COL_BUNDLE = 'bundle name'
_COL_TIER = 'tier name'
_COL_TIER_SEQ = 'tier seq'
_COL_SERVICE = 'service name'
_COL_QTY = 'qty'
_COL_DESC = 'item description'
_COL_ITEM_SEQ = 'item seq'

REQUIRED_COLS = {_COL_BUNDLE, _COL_TIER, _COL_SERVICE}


class WinkBundleImportWizard(models.TransientModel):
    _name = 'wink.bundle.import.wizard'
    _description = 'Bundle Package Import Wizard'

    file_data = fields.Binary(
        string='Excel File (.xlsx)',
        help='Upload an .xlsx file with columns: Bundle Name, Tier Name, Tier Seq, Service Name, Qty, Item Description, Item Seq.',
    )
    file_name = fields.Char(
        string='File Name',
        help='Name of the uploaded file.',
    )
    state = fields.Selection(
        [('upload', 'Upload'), ('preview', 'Preview'), ('done', 'Done')],
        default='upload',
        help='Current step of the import wizard.',
    )
    preview_html = fields.Html(
        string='Preview',
        readonly=True,
        help='Validation preview — green = create, yellow = update, red = error.',
    )
    row_data = fields.Text(
        help='JSON-serialised validated rows for the confirm step.',
    )
    result_html = fields.Html(
        string='Import Result',
        readonly=True,
        help='Summary of records created, updated, and errors after import.',
    )

    # ── Step 1: Parse & Preview ───────────────────────────────────────────────

    def action_preview(self):
        """Parse the uploaded file, validate each row, render preview table.

        Workflow:
            1. Decode and open the .xlsx workbook.
            2. Map header row to column indices.
            3. For each data row, resolve bundle/tier/service and determine
               whether the record will be created, updated, or has an error.
            4. Render an HTML preview table and store JSON row data.
            5. Advance wizard to 'preview' state.
        """
        self.ensure_one()
        if not openpyxl:
            raise UserError(_('openpyxl is not installed. Cannot read Excel files.'))
        if not self.file_data:
            raise UserError(_('Please upload an Excel file first.'))

        try:
            raw = base64.b64decode(self.file_data)
            wb = openpyxl.load_workbook(io.BytesIO(raw), read_only=True, data_only=True)
            ws = wb.active
        except Exception as e:
            raise UserError(_('Could not open the Excel file: %s') % str(e))

        rows = list(ws.iter_rows(values_only=True))
        if not rows:
            raise UserError(_('The file is empty.'))

        # Map header columns
        header = [str(c).strip().lower() if c else '' for c in rows[0]]
        col = {name: header.index(name) for name in (_COL_BUNDLE, _COL_TIER, _COL_SERVICE)
               if name in header}

        missing = REQUIRED_COLS - set(col.keys())
        if missing:
            raise UserError(_(
                'Missing required columns: %s\n\nExpected headers: Bundle Name, Tier Name, Service Name'
            ) % ', '.join(missing))

        def _ci(name):
            return header.index(name) if name in header else None

        idx = {
            'bundle':    _ci(_COL_BUNDLE),
            'tier':      _ci(_COL_TIER),
            'tier_seq':  _ci(_COL_TIER_SEQ),
            'service':   _ci(_COL_SERVICE),
            'qty':       _ci(_COL_QTY),
            'desc':      _ci(_COL_DESC),
            'item_seq':  _ci(_COL_ITEM_SEQ),
        }

        # Pre-fetch all product templates (name → id, case-insensitive)
        products = self.env['product.template'].sudo().search([
            ('type', '=', 'service'),
        ])
        product_map = {p.name.strip().lower(): p for p in products}

        # Pre-fetch existing bundles and tiers
        bundles = self.env['wink.bundle'].sudo().search([])
        bundle_map = {b.name.strip().lower(): b for b in bundles}

        tiers = self.env['wink.bundle.tier'].sudo().search([])
        tier_map = {}
        for t in tiers:
            tier_map[(t.bundle_id.id, t.name.strip().lower())] = t

        tier_items = self.env['wink.bundle.tier.item'].sudo().search([])
        item_map = {}
        for i in tier_items:
            item_map[(i.tier_id.id, i.service_product_id.id)] = i

        # Track auto-sequence for tiers/items not yet in DB (within this file)
        file_tier_seq = {}   # (bundle_name_lower, tier_name_lower) → seq
        file_item_seq = {}   # (bundle_name_lower, tier_name_lower, service_name_lower) → seq
        seen_items = set()   # deduplicate within file

        parsed_rows = []
        auto_tier_seq = {}   # bundle_lower → last used seq (for new tiers)
        auto_item_seq = {}   # (b_lower, t_lower) → last used seq (for new items)

        for row_num, row in enumerate(rows[1:], start=2):
            def cell(i):
                return str(row[i]).strip() if i is not None and i < len(row) and row[i] is not None else ''

            bundle_name = cell(idx['bundle'])
            tier_name = cell(idx['tier'])
            service_name = cell(idx['service'])
            tier_seq_raw = cell(idx['tier_seq'])
            qty_raw = cell(idx['qty'])
            desc = cell(idx['desc'])
            item_seq_raw = cell(idx['item_seq'])

            if not bundle_name and not tier_name and not service_name:
                continue  # blank row

            errors = []
            if not bundle_name:
                errors.append('Bundle Name is required')
            if not tier_name:
                errors.append('Tier Name is required')
            if not service_name:
                errors.append('Service Name is required')

            product = product_map.get(service_name.lower()) if service_name else None
            if service_name and not product:
                errors.append('Service "%s" not found in product catalogue' % service_name)

            # Qty
            try:
                qty = int(float(qty_raw)) if qty_raw else 1
                if qty < 1:
                    qty = 1
            except ValueError:
                qty = 1

            # Tier sequence
            b_lower = bundle_name.lower()
            t_lower = tier_name.lower()
            if tier_seq_raw:
                try:
                    tier_seq = int(float(tier_seq_raw))
                except ValueError:
                    tier_seq = None
            else:
                tier_seq = None
            if tier_seq is None:
                # Auto-assign: 10, 20, 30... per bundle
                last = auto_tier_seq.get(b_lower, 0)
                # Check if tier already exists or was seen in file
                key = (b_lower, t_lower)
                if key not in file_tier_seq:
                    last += 10
                    auto_tier_seq[b_lower] = last
                    file_tier_seq[key] = last
                tier_seq = file_tier_seq.get(key, last)
            else:
                file_tier_seq.setdefault((b_lower, t_lower), tier_seq)

            # Item sequence
            svc_lower = service_name.lower() if service_name else ''
            if item_seq_raw:
                try:
                    item_seq = int(float(item_seq_raw))
                except ValueError:
                    item_seq = None
            else:
                item_seq = None
            if item_seq is None:
                bt_key = (b_lower, t_lower)
                last_i = auto_item_seq.get(bt_key, 0)
                item_key = (b_lower, t_lower, svc_lower)
                if item_key not in file_item_seq:
                    last_i += 10
                    auto_item_seq[bt_key] = last_i
                    file_item_seq[item_key] = last_i
                item_seq = file_item_seq.get(item_key, last_i)
            else:
                file_item_seq.setdefault((b_lower, t_lower, svc_lower), item_seq)

            # Deduplication within file
            dedup_key = (b_lower, t_lower, svc_lower)
            if dedup_key in seen_items:
                parsed_rows.append({
                    'row': row_num, 'bundle': bundle_name, 'tier': tier_name,
                    'service': service_name, 'qty': qty, 'desc': desc,
                    'tier_seq': tier_seq, 'item_seq': item_seq,
                    'status': 'skip', 'reason': 'Duplicate in file — skipped',
                    'errors': [],
                })
                continue
            seen_items.add(dedup_key)

            if errors:
                parsed_rows.append({
                    'row': row_num, 'bundle': bundle_name, 'tier': tier_name,
                    'service': service_name, 'qty': qty, 'desc': desc,
                    'tier_seq': tier_seq, 'item_seq': item_seq,
                    'status': 'error', 'reason': '; '.join(errors),
                    'errors': errors,
                    'product_id': None,
                })
                continue

            # Determine create/update status
            existing_bundle = bundle_map.get(b_lower)
            existing_tier = tier_map.get((existing_bundle.id, t_lower)) if existing_bundle else None
            existing_item = None
            if existing_tier and product:
                existing_item = item_map.get((existing_tier.id, product.id))

            if existing_item:
                needs_update = (existing_item.qty != qty or (desc and existing_item.description != desc))
                status = 'update' if needs_update else 'ok'
                reason = 'Will update qty/description' if needs_update else 'Already exists — no change'
            elif existing_tier:
                status = 'create'
                reason = 'New service in existing tier'
            elif existing_bundle:
                status = 'create'
                reason = 'New tier + service in existing bundle'
            else:
                status = 'create'
                reason = 'New bundle + tier + service'

            parsed_rows.append({
                'row': row_num,
                'bundle': bundle_name,
                'tier': tier_name,
                'service': service_name,
                'qty': qty,
                'desc': desc,
                'tier_seq': tier_seq,
                'item_seq': item_seq,
                'status': status,
                'reason': reason,
                'errors': [],
                'product_id': product.id if product else None,
            })

        if not parsed_rows:
            raise UserError(_('No data rows found in the file.'))

        # Build preview HTML
        total_create = sum(1 for r in parsed_rows if r['status'] == 'create')
        total_update = sum(1 for r in parsed_rows if r['status'] == 'update')
        total_error = sum(1 for r in parsed_rows if r['status'] == 'error')
        total_skip = sum(1 for r in parsed_rows if r['status'] in ('skip', 'ok'))

        status_colors = {
            'create': '#d4edda',
            'update': '#fff3cd',
            'error': '#f8d7da',
            'skip': '#f8f9fa',
            'ok': '#f8f9fa',
        }
        status_labels = {
            'create': '✅ Create',
            'update': '🔄 Update',
            'error': '❌ Error',
            'skip': '⏭ Skip',
            'ok': '— No change',
        }

        html = '<div style="font-family:sans-serif;font-size:13px;">'
        html += '<div style="margin-bottom:12px;padding:10px 14px;background:#e9ecef;border-radius:6px;">'
        html += '<strong>Preview Summary:</strong> '
        html += '<span style="color:#198754;">%d to create</span> &nbsp;|&nbsp; ' % total_create
        html += '<span style="color:#856404;">%d to update</span> &nbsp;|&nbsp; ' % total_update
        html += '<span style="color:#842029;">%d errors (will be skipped)</span> &nbsp;|&nbsp; ' % total_error
        html += '<span style="color:#6c757d;">%d no change / duplicate</span>' % total_skip
        html += '</div>'

        html += '<table style="width:100%;border-collapse:collapse;font-size:12px;">'
        html += '<thead><tr style="background:#f1f3f5;">'
        for h in ['Row', 'Bundle', 'Tier', 'Service', 'Qty', 'Description', 'Status', 'Notes']:
            html += '<th style="padding:6px 8px;border:1px solid #dee2e6;text-align:left;">%s</th>' % h
        html += '</tr></thead><tbody>'

        for r in parsed_rows:
            bg = status_colors.get(r['status'], '#fff')
            html += '<tr style="background:%s;">' % bg
            html += '<td style="padding:5px 8px;border:1px solid #dee2e6;">%s</td>' % r['row']
            html += '<td style="padding:5px 8px;border:1px solid #dee2e6;">%s</td>' % (r['bundle'] or '')
            html += '<td style="padding:5px 8px;border:1px solid #dee2e6;">%s</td>' % (r['tier'] or '')
            html += '<td style="padding:5px 8px;border:1px solid #dee2e6;">%s</td>' % (r['service'] or '')
            html += '<td style="padding:5px 8px;border:1px solid #dee2e6;text-align:center;">%s</td>' % r['qty']
            html += '<td style="padding:5px 8px;border:1px solid #dee2e6;">%s</td>' % (r['desc'] or '')
            html += '<td style="padding:5px 8px;border:1px solid #dee2e6;white-space:nowrap;">%s</td>' % status_labels.get(r['status'], '')
            html += '<td style="padding:5px 8px;border:1px solid #dee2e6;color:#6c757d;">%s</td>' % (r['reason'] or '')
            html += '</tr>'

        html += '</tbody></table></div>'

        self.write({
            'state': 'preview',
            'preview_html': html,
            'row_data': json.dumps(parsed_rows),
        })
        return self._reopen()

    # ── Step 2: Confirm Import ────────────────────────────────────────────────

    def action_import(self):
        """Write validated rows to the database.

        Workflow:
            1. Deserialise row_data JSON.
            2. Process only rows with status 'create' or 'update'.
            3. Find-or-create wink.bundle, wink.bundle.tier, wink.bundle.tier.item.
            4. Render result summary and advance to 'done' state.
        """
        self.ensure_one()
        if not self.row_data:
            raise UserError(_('No preview data found. Please re-upload the file.'))

        parsed_rows = json.loads(self.row_data)
        actionable = [r for r in parsed_rows if r['status'] in ('create', 'update')]

        if not actionable:
            raise UserError(_('Nothing to import — all rows are errors or duplicates.'))

        Bundle = self.env['wink.bundle'].sudo()
        Tier = self.env['wink.bundle.tier'].sudo()
        Item = self.env['wink.bundle.tier.item'].sudo()

        bundle_cache = {}   # name_lower → wink.bundle record
        tier_cache = {}     # (bundle_id, name_lower) → wink.bundle.tier record

        created_bundles = created_tiers = created_items = updated_items = errors = 0

        for r in actionable:
            try:
                b_lower = r['bundle'].strip().lower()
                t_lower = r['tier'].strip().lower()
                product_id = r.get('product_id')
                if not product_id:
                    errors += 1
                    continue

                # Find or create bundle
                if b_lower not in bundle_cache:
                    existing = Bundle.search([('name', '=ilike', r['bundle'].strip())], limit=1)
                    if existing:
                        bundle_cache[b_lower] = existing
                    else:
                        bundle_cache[b_lower] = Bundle.create({'name': r['bundle'].strip()})
                        created_bundles += 1
                bundle = bundle_cache[b_lower]

                # Find or create tier
                tier_key = (bundle.id, t_lower)
                if tier_key not in tier_cache:
                    existing_tier = Tier.search([
                        ('bundle_id', '=', bundle.id),
                        ('name', '=ilike', r['tier'].strip()),
                    ], limit=1)
                    if existing_tier:
                        if r.get('tier_seq') and existing_tier.sequence != r['tier_seq']:
                            existing_tier.write({'sequence': r['tier_seq']})
                        tier_cache[tier_key] = existing_tier
                    else:
                        tier_cache[tier_key] = Tier.create({
                            'bundle_id': bundle.id,
                            'name': r['tier'].strip(),
                            'sequence': r.get('tier_seq') or 10,
                        })
                        created_tiers += 1
                tier = tier_cache[tier_key]

                # Find or create / update item
                existing_item = Item.search([
                    ('tier_id', '=', tier.id),
                    ('service_product_id', '=', product_id),
                ], limit=1)

                if existing_item:
                    vals = {}
                    if existing_item.qty != r['qty']:
                        vals['qty'] = r['qty']
                    if r.get('desc') and existing_item.description != r['desc']:
                        vals['description'] = r['desc']
                    if vals:
                        existing_item.write(vals)
                        updated_items += 1
                else:
                    item_vals = {
                        'tier_id': tier.id,
                        'service_product_id': product_id,
                        'qty': r['qty'],
                        'sequence': r.get('item_seq') or 10,
                    }
                    if r.get('desc'):
                        item_vals['description'] = r['desc']
                    Item.create(item_vals)
                    created_items += 1

            except Exception as e:
                _logger.warning('Bundle import error on row %s: %s', r.get('row'), e, exc_info=True)
                errors += 1

        # Build result HTML
        html = '<div style="font-family:sans-serif;font-size:13px;">'
        html += '<div style="padding:14px 16px;background:#d4edda;border-radius:6px;margin-bottom:12px;">'
        html += '<strong>✅ Import Complete</strong><br/>'
        html += '%d bundle(s) created &nbsp;·&nbsp; ' % created_bundles
        html += '%d tier(s) created &nbsp;·&nbsp; ' % created_tiers
        html += '%d service item(s) created &nbsp;·&nbsp; ' % created_items
        html += '%d service item(s) updated' % updated_items
        if errors:
            html += '<br/><span style="color:#842029;">%d row(s) failed (see server log for details)</span>' % errors
        html += '</div></div>'

        self.write({'state': 'done', 'result_html': html})
        return self._reopen()

    # ── Template Download ─────────────────────────────────────────────────────

    def action_download_template(self):
        """Open the dedicated template download route in a new tab."""
        return {
            'type': 'ir.actions.act_url',
            'url': '/wink/bundle-import/template',
            'target': 'new',
        }

    def action_back(self):
        """Return to upload step."""
        self.write({'state': 'upload', 'preview_html': False, 'row_data': False})
        return self._reopen()

    def _reopen(self):
        return {
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }
