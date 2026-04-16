// Centralized date filter validation helper
// Usage: validateDateRange(startDate, endDate, { highlightFields: [input1, input2], onError })

function validateDateRange(startDate, endDate, options = {}) {
    // Accepts dates as strings (YYYY-MM-DD) or Date objects
    let start = typeof startDate === 'string' ? new Date(startDate) : startDate;
    let end = typeof endDate === 'string' ? new Date(endDate) : endDate;

    // Remove time for pure date comparison
    start.setHours(0,0,0,0);
    end.setHours(0,0,0,0);

    if (end < start) {
        if (options.highlightFields) {
            options.highlightFields.forEach(field => {
                field.classList.add('invalid-date-field');
            });
        }
        if (typeof options.onError === 'function') {
            options.onError('A data final não pode ser menor que a data inicial.');
        } else {
            alert('A data final não pode ser menor que a data inicial.');
        }
        return false;
    } else {
        if (options.highlightFields) {
            options.highlightFields.forEach(field => {
                field.classList.remove('invalid-date-field');
            });
        }
        return true;
    }
}

// Export for use in HTML via <script src="/static/js/dateValidation.js"></script>
window.validateDateRange = validateDateRange;
