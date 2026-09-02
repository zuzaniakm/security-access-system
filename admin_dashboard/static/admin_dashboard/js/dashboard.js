document.addEventListener("DOMContentLoaded", () => {

    document.querySelectorAll('.toggle-blocked').forEach(badge => {
        badge.addEventListener('click', async (e) => {
            const userId = badge.dataset.userId;
            const csrfToken = document.cookie
                .split('; ')
                .find(row => row.startsWith('csrftoken='))
                ?.split('=')[1];

            const isBlocked = badge.dataset.blocked === 'true';
            const action = isBlocked ? gettext('unblock') : gettext('block');

            if (!confirm(interpolate(gettext("Do you really want to %s this user?"),[action]))) return;

            try {
                const lang = document.documentElement.lang;
                const response = await fetch(`/${lang}/toggle-blocked/${userId}/`, {
                    method: 'POST',
                    headers: { 'X-CSRFToken': csrfToken },
                });

                const data = await response.json();

                if (data.blocked) {
                    badge.textContent = gettext('Blocked');
                    badge.classList.replace('bg-success', 'bg-danger');
                } else {
                    badge.textContent = gettext('Active');
                    badge.classList.replace('bg-danger', 'bg-success');
                }

                badge.dataset.blocked = data.blocked;

            } catch (err) {
                console.error(gettext('Error while changing state: '), err);
            }
        });
    });

    document.querySelectorAll('.card-hoverable').forEach(card => {
        const editUrl = card.dataset.editUrl;
        const clickables = card.querySelectorAll('.card-clickable');

        clickables.forEach(el => {
            el.addEventListener('mouseover', () => card.style.filter = 'brightness(1.1)');
            el.addEventListener('mouseout', () => card.style.filter = 'brightness(1)');
            el.addEventListener('click', () => window.location.href = editUrl);
        });
    });

    document.querySelectorAll('.delete-user-form').forEach(form => {
        form.addEventListener('submit', e => {
            e.stopPropagation();
            if (!confirm(gettext('Are you sure you want to delete this user?'))) {
                e.preventDefault();
            }
        });
    });
});