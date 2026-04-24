/** @odoo-module **/
import publicWidget from "@web/legacy/js/public/public_widget";
import { rpc } from '@web/core/network/rpc';

publicWidget.registry.VendorSignupForm = publicWidget.Widget.extend({
    selector: '#vendor_signup_form',
    events: {
        'click .upload_image': '_onUploadImageClick',
        'change #country_id': '_onCountryChange',
        'input #mobile': '_onMobileInput',
        'change #company_type': '_onCompanyTypeChange',
        //        'click #other_category': '_onOtherCategoryClick',
        'change .category-checkbox': '_onCategoryChange',
        'change #other_category': '_onOtherCategoryClick',
        'click #other_certificate': '_onOtherCertificateClick',
        'click #other_op': '_onOtherOfferedProductClick',
        'click #has_worked_for_govt': '_onHasWorkedGovtClick',
        'click #add_company_row': '_addCompanyTableRow',
        'click .remove-row': '_removeTableRow',
        'change #email': '_toggleOTPChange',
        'click #sendOtpBtn': '_onClickSendOTP',
        'click #verifyOtpBtn': '_onClickVerifyOTP',
        'click #na_website': '_onClickNAWebsite',
        'click #na_icv': '_onClickNAICV',
        'change #icv_score': '_onChangeICV',
        'change #delivery_capacity': '_onChangeDelivery',
        'click #add_bank_row': '_addBankTableRow',
        'submit #vendor-portal-registration': '_onFormSubmit',
    },

    _onUploadImageClick(ev) {
        ev.preventDefault();
        const fileInput = this.el.querySelector('.image_1920');
        const previewImg = this.el.querySelector('#preview');

        if (!fileInput || !previewImg) {
            console.warn("File input or preview image not found.");
            return;
        }

        fileInput.click();

        fileInput.addEventListener('change', function (event) {
            const file = event.target.files[0];
            if (file) {
                const reader = new FileReader();
                reader.onload = function (e) {
                    previewImg.src = e.target.result;
                };
                reader.readAsDataURL(file);
            }
        }, { once: true });
    },

    async _onCountryChange(ev) {
        const countryId = ev.target.value;
        const stateSelect = this.el.querySelector('#state_id');

        stateSelect.innerHTML = '<option value="">Select State</option>';

        if (!countryId) {
            return;
        }

        try {
            const states = await rpc(`/web/get-state/${parseInt(countryId)}`);
            states.forEach(state => {
                const option = document.createElement('option');
                option.value = state.id;
                option.textContent = state.name;
                stateSelect.appendChild(option);
            });

            stateSelect.disabled = states.length === 0;

        } catch (error) {
            console.error("Error fetching states:", error);
            stateSelect.disabled = true;
        }
    },

    _onMobileInput(ev) {
        const mobileInput = ev.target;
        const phoneInput = this.el.querySelector('#phone');

        if (!mobileInput || !phoneInput) return;

        if (mobileInput.value.trim() !== '') {
            // Mobile has a value → make phone optional
            phoneInput.removeAttribute('required');
            phoneInput.closest('.input-group').querySelector('.phone-required')?.classList.add('d-none');
        } else {
            // Mobile is empty → make phone required
            phoneInput.setAttribute('required', 'required');
            phoneInput.closest('.input-group').querySelector('.phone-required')?.classList.remove('d-none');
        }
    },

    async _onCompanyTypeChange(ev) {
        const companyType = ev.target.value;
        const vatRequired = this.el.querySelector('.vat-required');
        const sizeRequired = this.el.querySelector('.size-required');
        const sizeSelect = this.el.querySelector('#company_size_id');
        const vatInput = this.el.querySelector('#vat');

        const contactPersonDetail = this.el.querySelector('#contact_person_detail');
        const naWebsite = this.el.querySelector('#na_website');
        const contactInputs = contactPersonDetail.querySelectorAll('input, select, textarea');
        if (companyType === 'person') {
            naWebsite.checked = true
            if (contactPersonDetail) {
                contactPersonDetail.classList.add('d-none');
                // Remove 'required' from all inputs inside
                contactInputs.forEach(input => {
                    input.removeAttribute('required');
                });
            }
            if (vatInput) {
                vatInput.removeAttribute('required');
                vatRequired.classList.add('d-none');
            }
            if (sizeSelect) {
                sizeSelect.removeAttribute('required');
                sizeRequired.classList.add('d-none');
            }
        }
        else {
            naWebsite.checked = false
            if (contactPersonDetail) {
                contactPersonDetail.classList.remove('d-none');
                // Remove 'required' from all inputs inside
                contactInputs.forEach(input => {
                    input.setAttribute('required', 'required');
                });
            }
            if (vatInput) {
                vatInput.setAttribute('required', 'required');
                vatRequired.classList.remove('d-none');
            }
            if (sizeSelect) {
                sizeSelect.setAttribute('required', 'required');
                sizeRequired.classList.remove('d-none');
            }
        }
        this._onClickNAWebsite({ target: naWebsite })

        await this._loadAttachmentLines(companyType)
    },

    async _loadAttachmentLines(companyType) {
        const attachmentBody = this.el.querySelector('#vendor_attachments_table tbody');
        const attachmentContainer = this.el.querySelector('.attachment_container');
        attachmentBody.innerHTML = '';
        try {
            const attachmentLines = await rpc(`/web/get-attachment/${companyType}`);
            attachmentLines.length ? attachmentContainer.classList.remove('d-none') : attachmentContainer.classList.add('d-none')
            attachmentLines.sort((a, b) => a.sequence - b.sequence);
            // optional: sort by sequence
            attachmentLines.forEach((line, index) => {
                const tr = document.createElement('tr');
                tr.setAttribute('data-id', line.id);

                // Sequence
                const tdSeq = document.createElement('td');
                tdSeq.textContent = index + 1;
                tr.appendChild(tdSeq);

                // Name
                const tdName = document.createElement('td');
                tdName.textContent = line.name || '';
                tr.appendChild(tdName);

                // File / Link input
                const tdInput = document.createElement('td');
                const attachmentRequired = line.attachment_is_required;

                if (line.attachment_type === 'attachment') {
                    // Hidden file input
                    const input = document.createElement('input');
                    input.type = 'file';
                    input.className = 'd-none';
                    input.name = `attach_file_${line.id}`;
                    if (attachmentRequired) input.required = true;

                    // Button to trigger file picker
                    const i = document.createElement('i');
                    i.className = 'fa fa-upload cursor-pointer';

                    i.addEventListener('click', () => input.click());
                    const fileNameSpan = document.createElement('span');
                    fileNameSpan.className = 'ms-2 file-name-span text-truncate';

                    input.addEventListener('change', () => {
                        fileNameSpan.textContent = input.files[0]?.name || '';
                    });
                    tdInput.appendChild(i);
                    tdInput.appendChild(input);
                    tdInput.appendChild(fileNameSpan);
                } else if (line.attachment_type === 'link') {
                    const input = document.createElement('input');
                    input.type = 'text';
                    input.className = 'form-control';
                    input.name = `attach_link_${line.id}`;
                    input.placeholder = 'Enter link';
                    if (attachmentRequired) input.required = true;
                    tdInput.appendChild(input);
                }
                tr.appendChild(tdInput);

                if (attachmentRequired) {
                    const requiredSpan = document.createElement('span');
                    requiredSpan.className = 'field-required ms-1';
                    requiredSpan.textContent = '*';
                    tdInput.appendChild(requiredSpan);
                }

                // Expiry date
                const tdExpiry = document.createElement('td');
                if (line.expiry_date_required) {
                    const input = document.createElement('input');
                    input.type = 'date';
                    input.className = 'form-control';
                    input.name = `expiry_${line.id}`;
                    input.required = true;

                    const tomorrow = new Date();
                    tomorrow.setDate(tomorrow.getDate() + 1);
                    input.min = tomorrow.toISOString().split("T")[0];

                    tdExpiry.appendChild(input);

                    const requiredSpan = document.createElement('span');
                    requiredSpan.className = 'field-required ms-1';
                    requiredSpan.textContent = '*';
                    tdExpiry.appendChild(requiredSpan);
                }
                tr.appendChild(tdExpiry);

                attachmentBody.appendChild(tr);
            });
        } catch (error) {
            console.error("Error fetching states:", error);
        }
    },

    _updateValidation() {
        const allCheckboxes = this.el.querySelectorAll('.category-checkbox, #other_category');
        const isAnyChecked = Array.from(allCheckboxes).some(cb => cb.checked);

        // If at least one is checked, nobody needs the 'required' attribute.
        // If none are checked, we set 'required' on all to block form submission.
        allCheckboxes.forEach(cb => {
            if (isAnyChecked) {
                cb.removeAttribute('required');
            } else {
                cb.setAttribute('required', 'required');
            }
        });
    },

    _onCategoryChange(ev) {
        this._updateValidation();
    },

    _onOtherCategoryClick(ev) {
        const checkbox = ev.target;
        const otherContainer = this.el.querySelector('.other_partner_category_container');
        const otherInput = this.el.querySelector('#other_partner_category');

        // 1. Handle the "Other" text field visibility and requirement
        if (checkbox.checked) {
            otherContainer.classList.remove('d-none');
            otherInput.setAttribute('required', 'required');
        } else {
            otherContainer.classList.add('d-none');
            otherInput.removeAttribute('required');
            otherInput.value = '';
        }

        // 2. Update the "at least one" checkbox validation
        this._updateValidation();
    },

    _onOtherCertificateClick(ev) {
        const checkbox = ev.target;
        const otherContainer = this.el.querySelector('.other_partner_certificates_container');
        const otherInput = this.el.querySelector('#other_partner_certificates');
        if (!checkbox || !otherContainer || !otherInput) return;

        if (checkbox.checked) {
            otherContainer.classList.remove('d-none');
            otherInput.setAttribute('required', 'required');
        } else {
            otherContainer.classList.add('d-none');
            otherInput.removeAttribute('required');
            otherInput.value = '';
        }
    },

    _onOtherOfferedProductClick(ev) {
        const checkbox = ev.target;
        const otherContainer = this.el.querySelector('.other_offered_product_container');
        const offeredProducts = this.el.querySelector('#products_tag');
        const otherInput = this.el.querySelector('#other_offered_product');
        if (!checkbox || !otherContainer || !otherInput) return;

        if (checkbox.checked) {
            otherContainer.classList.remove('d-none');
            otherInput.setAttribute('required', 'required');
            offeredProducts.removeAttribute('required');
        } else {
            otherContainer.classList.add('d-none');
            otherInput.removeAttribute('required');
            offeredProducts.setAttribute('required', 'required');
            otherInput.value = '';
        }
    },

    _onHasWorkedGovtClick(ev) {
        const checkbox = ev.target;
        const container = this.el.querySelector('#companies_worked_for_container');
        const tableBody = this.el.querySelector('#companies_worked_for_table tbody');
        if (checkbox.checked) {
            container.classList.remove('d-none');
            if (tableBody.children.length === 0) {
                this._addCompanyTableRow();
            }
        } else {
            container.classList.add('d-none');
            tableBody.innerHTML = ''; // optional: clear rows when disabled
        }
    },

    _addCompanyTableRow() {
        const tableBody = this.el.querySelector('#companies_worked_for_table tbody');
        const sl = tableBody.children.length + 1
        const tr = document.createElement('tr');
        tr.innerHTML = `
            <td class="sl_no">${sl}</td>
            <td>
                <input type="text" class="form-control" name="companies_worked_for" required="required">
            </td>
            <td>
                <button type="button" class="btn btn-sm btn-danger remove-row secondary-text">Remove</button>
            </td>
        `;
        tableBody.appendChild(tr);
    },

    _addBankTableRow() {
        const tableBody = this.el.querySelector('#bank_ids_table tbody');
        const sl = tableBody.children.length + 1;

        // Clone the first row
        const firstRow = tableBody.querySelector('tr');
        const newRow = firstRow.cloneNode(true);

        // Update SL number
        newRow.querySelector('.sl_no').textContent = sl;

        // Clear input/select values
        newRow.querySelectorAll('input, select').forEach(el => {
            el.value = '';
        });

        const removeCell = newRow.querySelector('.remove-action');
        if (removeCell) {
            removeCell.innerHTML = `
                <button type="button" class="btn btn-sm btn-danger remove-row">Remove</button>
            `;
        }

        tableBody.appendChild(newRow);
    },

    _removeTableRow(ev) {
        const button = ev.target;
        const row = button.closest('tr'); // get the parent row
        if (!row) return;

        const tableBody = row.parentElement;
        row.remove();

        // Recalculate serial numbers
        Array.from(tableBody.children).forEach((tr, index) => {
            const sl = tr.querySelector('td:first-child.sl_no')
            if (sl) sl.textContent = index + 1;
        });
    },

    _toggleOTPChange(ev) {
        const email = ev.target.value;
        const otpSection = this.el.querySelector('.otp-section');
        const otpPlaceholder = otpSection.querySelector('#otp_email_placeholder');
        const sendBtn = otpSection.querySelector('#sendOtpBtn');

        if (email && email.includes('@')) {
            otpSection.classList.remove('d-none');
            otpPlaceholder.textContent = email;
            sendBtn.removeAttribute('disabled');
        } else {
            otpSection.classList.add('d-none');
            otpPlaceholder.textContent = '';
            sendBtn.setAttribute('disabled', true);
        }
    },

    async _onClickSendOTP(ev) {
        ev.preventDefault();
        const emailInput = this.el.querySelector('#email');
        const nameInput = this.el.querySelector('#name');
        const email = emailInput.value.trim();
        const name = nameInput.value.trim();
        const sendBtn = ev.target;

        if (!email || !email.includes('@')) {
            alert("Please enter a valid email before sending OTP");
            return;
        }

        sendBtn.setAttribute('disabled', true);   // prevent multiple clicks
        sendBtn.textContent = "Sending...";

        try {
            const result = await rpc('/vendor/send_otp', {
                email, name
            });

            if (result.status == 'success') {
                this.el.querySelector('#otpSection').classList.remove('d-none');
                this.el.querySelector('#verifyOtpBtn').removeAttribute('disabled');
            } else {
                alert(result.error || "Failed to send OTP");
                sendBtn.removeAttribute('disabled');
            }
        } catch (err) {
            console.log(err);
            sendBtn.removeAttribute('disabled');
        } finally {
            sendBtn.textContent = "Send OTP";
        }
    },

    async _onClickVerifyOTP(ev) {
        ev.preventDefault();
        const email = this.el.querySelector('#email').value.trim();
        const otp = this.el.querySelector('#otpInput').value.trim();
        const verifyBtn = ev.target;

        if (!otp) return;

        verifyBtn.setAttribute('disabled', true);

        try {
            const result = await rpc('/vendor/verify_otp', {
                email, otp
            });

            if (result.status === 'success') {
                alert("OTP verified successfully!");
                this.el.querySelector('#registerBtn').removeAttribute('disabled');
                this.el.querySelector('#otpSection').classList.add('d-none');
                this.el.querySelector('.otp-section').classList.add('d-none');
                this.el.querySelector('#email').setAttribute('readonly', true);
            } else {
                alert(result.message || "Invalid OTP");
                verifyBtn.removeAttribute('disabled');
            }
        } catch (err) {
            console.error(err);
            alert("Error verifying OTP");
            verifyBtn.removeAttribute('disabled');
        }
    },

    _onClickNAWebsite(ev) {
        const isChecked = ev.target.checked;
        const websiteInput = this.el.querySelector('#website');
        const websiteRequired = this.el.querySelector('.website-required');
        if (isChecked) {
            websiteInput.required = false;
            websiteRequired.classList.add('d-none')
        }
        else {
            websiteInput.required = true;
            websiteRequired.classList.remove('d-none')
        }
    },

    _onClickNAICV(ev) {
        const isChecked = ev.target.checked;
        const icvInput = this.el.querySelector('#icv_score');
        const icvRequired = this.el.querySelector('.icv-required');
        if (isChecked) {
            icvInput.required = false;
            icvRequired.classList.add('d-none')
        }
        else {
            icvInput.required = true;
            icvRequired.classList.remove('d-none')
        }
    },

    _onChangeICV(ev) {
        let value = parseFloat(ev.target.value);

        if (isNaN(value)) {
            ev.target.value = "";
            return;
        }

        if (value > 100) {
            ev.target.value = 100;
        } else if (value <= 0) {
            ev.target.value = 1;
        } else {
            ev.target.value = value; // keep the valid number
        }
    },

    _onFormSubmit(ev) {
        // 1. Select all inputs with the name="bank_name"
        // (We use the attribute selector because your HTML does not have a 'bank_name' class)
        const bankInputs = this.el.querySelectorAll('input[name="bank_name"]');

        // 2. Iterate through them
        bankInputs.forEach((input) => {
            // 3. Check if the value is empty or just whitespace
            if (!input.value || input.value.trim() === '') {
                // 4. Set default value to "0" so the server accepts it
                input.value = '0';
            }
        });

        // The form submission process continues from here...
    },

    _onChangeDelivery(ev) {
        const value = ev.target.value;
        const vatRequired = this.el.querySelector('.vat-required');
        const vatInput = this.el.querySelector('#vat');

        if (value === 'international') {
            vatInput.removeAttribute('required');
            vatRequired.classList.add('d-none');
        }
        else {
            vatInput.setAttribute('required', 'required');
            vatRequired.classList.remove('d-none');
        }
    },
});
