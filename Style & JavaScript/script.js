document.addEventListener("DOMContentLoaded", () => {
    // Update the selected favourite sports counter.
    const sportCheckboxes = document.querySelectorAll(
        'input[name="sports"]'
    );

    const selectedCount = document.querySelector("#selected-count");

    function updateSelectedCount() {
        if (!selectedCount) {
            return;
        }

        const count = document.querySelectorAll(
            'input[name="sports"]:checked'
        ).length;

        selectedCount.textContent = `${count} selected`;
    }

    sportCheckboxes.forEach((checkbox) => {
        checkbox.addEventListener("change", updateSelectedCount);
    });

    updateSelectedCount();

    // Confirm before deleting an activity.
    const deleteForms = document.querySelectorAll(
        "[data-confirm-delete]"
    );

    deleteForms.forEach((form) => {
        form.addEventListener("submit", (event) => {
            const activityName = form.dataset.confirmDelete;

            const confirmed = window.confirm(
                `Are you sure you want to delete "${activityName}"? ` +
                "This action cannot be undone."
            );

            if (!confirmed) {
                event.preventDefault();
            }
        });
    });

    // Confirm before leaving an activity.
    const leaveForms = document.querySelectorAll(
        "[data-confirm-leave]"
    );

    leaveForms.forEach((form) => {
        form.addEventListener("submit", (event) => {
            const activityName = form.dataset.confirmLeave;

            const confirmed = window.confirm(
                `Are you sure you want to leave "${activityName}"?`
            );

            if (!confirmed) {
                event.preventDefault();
            }
        });
    });

    console.log("PlayMaker is ready!");
});
