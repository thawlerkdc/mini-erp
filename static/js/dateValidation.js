// Shared date range validator with inline feedback (no browser alerts)

function parseIsoDate(value) {
    if (!value || !/^\d{4}-\d{2}-\d{2}$/.test(value)) {
        return null;
    }
    const parts = value.split('-');
    const year = Number(parts[0]);
    const month = Number(parts[1]) - 1;
    const day = Number(parts[2]);
    return new Date(year, month, day);
}

function setFieldsInvalid(fields, isInvalid) {
    if (!fields || !fields.length) {
        return;
    }
    fields.forEach((field) => {
        if (!field) {
            return;
        }
        field.classList.toggle('invalid-date-field', Boolean(isInvalid));
    });
}

function setErrorMessage(errorElement, message) {
    if (!errorElement) {
        return;
    }
    errorElement.textContent = message || '';
    errorElement.classList.toggle('visible', Boolean(message));
}

function animateDateValidationFeedback(fields, errorElement) {
    if (errorElement) {
        errorElement.classList.remove('date-error-pop');
        // Force reflow to replay animation on repeated invalid attempts.
        void errorElement.offsetWidth;
        errorElement.classList.add('date-error-pop');
    }

    (fields || []).forEach((field) => {
        if (!field) {
            return;
        }
        field.classList.remove('invalid-date-pulse');
        void field.offsetWidth;
        field.classList.add('invalid-date-pulse');
    });
}

function validateDateRange(startDate, endDate, options = {}) {
    const start = startDate instanceof Date ? startDate : parseIsoDate(String(startDate || ''));
    const end = endDate instanceof Date ? endDate : parseIsoDate(String(endDate || ''));
    const message = 'A data final não pode ser menor que a data inicial.';

    // If one side is empty, keep form submittable and remove previous error state.
    if (!start || !end) {
        setFieldsInvalid(options.highlightFields || [], false);
        if (typeof options.onError === 'function') {
            options.onError('');
        }
        return true;
    }

    const isValid = end >= start;
    setFieldsInvalid(options.highlightFields || [], !isValid);
    if (typeof options.onError === 'function') {
        options.onError(isValid ? '' : message);
    }
    return isValid;
}

function bindDateRangeForm(form) {
    if (!form) {
        return;
    }

    const startInput = document.getElementById(form.dataset.dateStart || '');
    const endInput = document.getElementById(form.dataset.dateEnd || '');
    const errorElement = document.getElementById(form.dataset.dateError || '');

    if (!startInput || !endInput) {
        return;
    }

    let lastValidationState = true;
    const runValidation = () => {
        const isValid = validateDateRange(startInput.value, endInput.value, {
        highlightFields: [startInput, endInput],
        onError: (msg) => setErrorMessage(errorElement, msg),
    });

        if (!isValid && lastValidationState) {
            animateDateValidationFeedback([startInput, endInput], errorElement);
        }
        lastValidationState = isValid;
        return isValid;
    };

    startInput.addEventListener('input', runValidation);
    endInput.addEventListener('input', runValidation);
    startInput.addEventListener('change', runValidation);
    endInput.addEventListener('change', runValidation);

    form.addEventListener('submit', (event) => {
        if (!runValidation()) {
            event.preventDefault();
            endInput.focus();
        }
    });

    runValidation();
}

function initDateRangeForms() {
    const forms = document.querySelectorAll('form[data-date-range-form="true"]');
    forms.forEach((form) => bindDateRangeForm(form));
}

document.addEventListener('DOMContentLoaded', initDateRangeForms);

window.validateDateRange = validateDateRange;
window.bindDateRangeForm = bindDateRangeForm;
