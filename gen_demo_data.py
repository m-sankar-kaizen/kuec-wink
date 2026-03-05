
# script to generate demo data XML
import xml.etree.ElementTree as ET
import xml.dom.minidom

services = [
    # Bronze (1-42)
    ("General Manager (GM) Visa & Medical Insurance", "govt", "visa", "bronze"),
    ("Employment Visa Issuance", "govt", "visa", "bronze"),
    ("Health Insurance Subscription", "govt", "visa", "bronze"),
    ("Employment Visa Cancellation", "govt", "visa", "bronze"),
    ("Family Member Visa Issuance", "govt", "visa", "bronze"),
    ("Family Member Visa Cancellation", "govt", "visa", "bronze"),
    ("Health Insurance Cancellation", "govt", "visa", "bronze"),
    ("Health Insurance Upgrade", "govt", "visa", "bronze"),
    ("Health Insurance Downgrade", "govt", "visa", "bronze"),
    ("Golden Visa Issuance", "govt", "visa", "bronze"),
    ("Family Member Golden Visa Issuance", "govt", "visa", "bronze"),
    ("Document Attestation", "govt", "pro", "bronze"),
    ("Governmental Permits and Approvals", "govt", "pro", "bronze"),
    ("Legal Translation", "govt", "pro", "bronze"),
    ("Custom Clearance", "govt", "pro", "bronze"),
    ("Tax Registration", "govt", "finance", "bronze"),
    ("Monthly Bookkeeping", "non-govt", "finance", "bronze"),
    ("Accounts Payable and Receivable", "non-govt", "finance", "bronze"),
    ("Corporate Tax Registration", "non-govt", "finance", "bronze"),
    ("Corporate Tax Filing", "non-govt", "finance", "bronze"),
    ("VAT Returns Filing", "non-govt", "finance", "bronze"),
    ("VAT Registration", "non-govt", "finance", "bronze"),
    ("VAT Registration Amendments", "non-govt", "finance", "bronze"),
    ("VAT Refunds", "non-govt", "finance", "bronze"),
    ("Payroll Processing (Finance)", "non-govt", "finance", "bronze"),
    ("UBO Registration", "non-govt", "finance", "bronze"),
    ("ESR Filings", "non-govt", "finance", "bronze"),
    ("Monthly Financial Statements", "non-govt", "finance", "bronze"),
    ("MOHRE Registration", "non-govt", "hr", "bronze"),
    ("Recruitment and Talent Acquisition", "non-govt", "hr", "bronze"),
    ("Employee Onboarding", "non-govt", "hr", "bronze"),
    ("Employee offboarding", "non-govt", "hr", "bronze"),
    ("Performance Management", "non-govt", "hr", "bronze"),
    ("Assessment Centre Management", "non-govt", "hr", "bronze"),
    ("Employee Relations", "non-govt", "hr", "bronze"),
    ("Payroll Processing (HR)", "non-govt", "hr", "bronze"),
    ("Ongoing HR Announcements", "non-govt", "hr", "bronze"),
    ("RFX Management", "non-govt", "procurement", "bronze"),
    ("Sourcing Suppliers", "non-govt", "procurement", "bronze"),
    ("Contract Negotiation", "non-govt", "procurement", "bronze"),
    ("Supplier Relationship Management", "non-govt", "procurement", "bronze"),
    ("General Operational Support", "non-govt", "pro", "bronze"), # Extra to make 42

    # Silver (43-54)
    ("Flexible Office Helper Staff", "non-govt", "fm", "silver"),
    ("Security & Reception Staff", "non-govt", "fm", "silver"),
    ("Catering Services", "non-govt", "fm", "silver"),
    ("Shared Transportation Services", "non-govt", "fm", "silver"),
    ("Dedicated Transportation Service", "non-govt", "fm", "silver"),
    ("Facility Maintenance & Repairs", "non-govt", "fm", "silver"),
    ("Document Management & Printing", "non-govt", "fm", "silver"),
    ("Workspace Planning & Fit-Out", "non-govt", "fm", "silver"),
    ("Short term car access permit", "non-govt", "fm", "silver"),
    ("Long term car access permit", "non-govt", "fm", "silver"),
    ("Short term access permit", "non-govt", "fm", "silver"),
    ("Long term access permit", "non-govt", "fm", "silver"),

    # Gold (55-70)
    ("IT Policies management", "non-govt", "it", "gold"),
    ("Website Management", "non-govt", "it", "gold"),
    ("CRM Management", "non-govt", "it", "gold"),
    ("Help desk support", "non-govt", "it", "gold"),
    ("New Hire Onboarding (IT)", "non-govt", "it", "gold"),
    ("Employee offboarding (IT)", "non-govt", "it", "gold"),
    ("Cyber Security Management", "non-govt", "it", "gold"),
    ("Office Internet & Network Management", "non-govt", "it", "gold"),
    ("Hardware Rental", "non-govt", "it", "gold"),
    ("Social Media Content Creation", "non-govt", "marketing", "gold"),
    ("Media Buying and Digital Ad Spend Management", "non-govt", "marketing", "gold"),
    ("Social Media Pages Moderation", "non-govt", "marketing", "gold"),
    ("Email Marketing", "non-govt", "marketing", "gold"),
    ("Event Planning and Execution", "non-govt", "marketing", "gold"),
    ("PR and Partnership Activities", "non-govt", "marketing", "gold"),
    ("Monthly legal support bundle", "non-govt", "legal", "gold"),
]

dept_map = {
    "visa": "kuec_demo_dept_visa",
    "pro": "kuec_demo_dept_pro",
    "finance": "kuec_demo_dept_finance",
    "hr": "kuec_demo_dept_hr",
    "procurement": "kuec_demo_dept_procurement",
    "fm": "kuec_demo_dept_fm",
    "it": "kuec_demo_dept_it",
    "marketing": "kuec_demo_dept_marketing",
    "legal": "kuec_demo_dept_legal",
}

nature_map = {
    "govt": "kuec_service_catalogue.kuec_service_nature_governmental",
    "non-govt": "kuec_service_catalogue.kuec_service_nature_non_governmental",
}

root = ET.Element("odoo")
data = ET.SubElement(root, "data", noupdate="1")

# 1. Product Templates
for i, (name, nature, dept, tier) in enumerate(services, 1):
    record_id = f"kuec_coe_svc_{i}"
    record = ET.SubElement(data, "record", id=record_id, model="product.template")
    ET.SubElement(record, "field", name="name").text = name
    ET.SubElement(record, "field", name="type").text = "service"
    ET.SubElement(record, "field", name="sale_ok").text = "True"
    ET.SubElement(record, "field", name="available_on_wink").text = "False"
    ET.SubElement(record, "field", name="list_price").text = "0.00"
    ET.SubElement(record, "field", name="department_ids", eval=f"[(6, 0, [ref('{dept_map[dept]}')])]").text = ""
    ET.SubElement(record, "field", name="nature_id", ref=nature_map[nature]).text = ""
    ET.SubElement(record, "field", name="delivery_model").text = "retainer"
    ET.SubElement(record, "field", name="commercial_structure").text = "bundled"
    ET.SubElement(record, "field", name="price_visibility").text = "visible"
    ET.SubElement(record, "field", name="request_frequency").text = "repeated" # Default most to repeated as per user text "can reused"

# 2. Bundle Wrapper
bundle_wrapper_id = "kuec_coe_svc_retainer_package"
record = ET.SubElement(data, "record", id=bundle_wrapper_id, model="product.template")
ET.SubElement(record, "field", name="name").text = "KUEC Centre of Excellence Monthly Retainer"
ET.SubElement(record, "field", name="type").text = "service"
ET.SubElement(record, "field", name="sale_ok").text = "True"
ET.SubElement(record, "field", name="available_on_wink").text = "True"
ET.SubElement(record, "field", name="is_bundle").text = "True"
ET.SubElement(record, "field", name="delivery_model").text = "retainer"
ET.SubElement(record, "field", name="commercial_structure").text = "standalone" # Bundle wrapper is standalone in catalogue
ET.SubElement(record, "field", name="nature_id", ref="kuec_service_catalogue.kuec_service_nature_non_governmental").text = ""
ET.SubElement(record, "field", name="wink_description").text = "A Comprehensive Guide for KUEC Customers..."

# 3. Wink Bundle Record
bundle_id = "kuec_coe_bundle"
record = ET.SubElement(data, "record", id=bundle_id, model="wink.bundle")
ET.SubElement(record, "field", name="name").text = "KUEC Centre of Excellence Retainer"

# Link wrapper to bundle
wrapper_ref = ET.SubElement(data, "record", id=bundle_wrapper_id, model="product.template", context="{'no_create': True}")
ET.SubElement(wrapper_ref, "field", name="wink_bundle_id", ref=bundle_id).text = ""

# 4. Bundle Tiers
tiers = [("Bronze", "bronze"), ("Silver", "silver"), ("Gold", "gold")]
for name, tier_key in tiers:
    tier_id = f"kuec_coe_tier_{tier_key}"
    record = ET.SubElement(data, "record", id=tier_id, model="wink.bundle.tier")
    ET.SubElement(record, "field", name="name").text = name
    ET.SubElement(record, "field", name="bundle_id", ref=bundle_id).text = ""
    
    # Tier Items
    # Flat duplication approach
    allowed_tiers = []
    if tier_key == "bronze": allowed_tiers = ["bronze"]
    elif tier_key == "silver": allowed_tiers = ["bronze", "silver"]
    elif tier_key == "gold": allowed_tiers = ["bronze", "silver", "gold"]
    
    tier_index = 1
    for i, (svc_name, nature, dept, svc_tier) in enumerate(services, 1):
        if svc_tier in allowed_tiers:
            item_id = f"kuec_coe_item_{tier_key}_{i}"
            item = ET.SubElement(data, "record", id=item_id, model="wink.bundle.tier.item")
            ET.SubElement(item, "field", name="tier_id", ref=tier_id).text = ""
            ET.SubElement(item, "field", name="service_product_id", ref=f"kuec_coe_svc_{i}").text = ""
            ET.SubElement(item, "field", name="qty").text = "1"
            ET.SubElement(item, "field", name="sequence").text = str(tier_index * 10)
            tier_index += 1

# Export
xml_str = xml.dom.minidom.parseString(ET.tostring(root)).toprettyxml(indent="    ")
with open("e:/Odoo 18/custom/kuec_service_catalogue/data/gen_demo_data.xml", "w", encoding="utf-8") as f:
    f.write(xml_str)
print("Generated gen_demo_data.xml successfully")
