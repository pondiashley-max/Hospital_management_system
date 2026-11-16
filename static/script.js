document.addEventListener("DOMContentLoaded", function () {
    const billTotalInput = document.getElementById("bill_total");
    const billPaidInput = document.getElementById("bill_paid");
    const calculatedBalanceSpan = document.getElementById("calculated-balance");

    function updateCalculatedBalance() {
        if (billTotalInput && billPaidInput && calculatedBalanceSpan) {
            const total = parseFloat(billTotalInput.value) || 0;
            const paid = parseFloat(billPaidInput.value) || 0;
            const balance = Math.max(0, total - paid);
            calculatedBalanceSpan.textContent = balance.toFixed(0) + " fcfa";
        }
    }

    if (billTotalInput && billPaidInput) {
        billTotalInput.addEventListener("input", updateCalculatedBalance);
        billPaidInput.addEventListener("input", updateCalculatedBalance);
    }

    const patientForm = document.getElementById("patient-form");
    if (patientForm) {
        patientForm.addEventListener("submit", function (event) {
            const nameInput = document.getElementById("name");
            if (nameInput && nameInput.value.trim() === "") {
                event.preventDefault();
                alert("please enter a valid patient full name.");
            }
        });
    }
});
