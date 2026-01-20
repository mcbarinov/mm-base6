/* Alert close button handler - removes .alert element and following <hr> if present */
document.addEventListener('click', (e) => {
    if (e.target.closest('.alert-close')) {
        const alert = e.target.closest('.alert');
        if (alert) {
            alert.remove();
            const hr = alert.nextElementSibling;
            if (hr && hr.tagName === 'HR') {
                hr.remove();
            }
        }
    }
});

/* Open modal dialog by id. Closes on backdrop click. */
function openDialog(id) {
    const dialog = document.getElementById(id);
    if (dialog) {
        dialog.showModal();
        dialog.onclick = (e) => { if (e.target === dialog) dialog.close(); };
    }
}

/* Close the nearest parent dialog */
function closeDialog(el) {
    const dialog = el.closest('dialog');
    if (dialog) {
        dialog.close();
    }
}

/* Auto-generate dialog headers from label attribute */
document.addEventListener('DOMContentLoaded', () => {
    document.querySelectorAll('dialog[label]').forEach(dialog => {
        const article = dialog.querySelector('article');
        if (!article) return;

        const header = document.createElement('header');
        header.innerHTML = `<h4>${dialog.getAttribute('label')}</h4>`;
        article.prepend(header);
    });
});
