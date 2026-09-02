document.querySelectorAll('.delete-photo').forEach(btn => {
    btn.addEventListener('click', async () => {
        const photoId = btn.dataset.photoId;
        const wrapper = document.getElementById(`photo-wrapper-${photoId}`);
        const currentCount = parseInt(document.querySelectorAll('.delete-photo').length);

        if (currentCount <= 1) {
            alert(gettext('At least 1 photo must remain.'));
            return;
        }

        if (!confirm(gettext('Are you sure you want to delete this photo?'))) return;

        const csrfToken = document.cookie
            .split('; ')
            .find(row => row.startsWith('csrftoken='))
            ?.split('=')[1];

        try {
            const lang = document.documentElement.lang;
            const response = await fetch(`/${lang}/delete-photo/${photoId}/`, {
                method: 'POST',
                headers: { 'X-CSRFToken': csrfToken },
            });

            const data = await response.json();

            if (data.success) {
                wrapper.remove();
                const countLabel = document.querySelector('label .text-secondary.small');
                const newCount = document.querySelectorAll('.delete-photo').length;
                if (countLabel) countLabel.textContent = `(${newCount}/5)`;
            } else {
                alert(data.error);
            }
        } catch (err) {
            console.error(gettext('Error while deleting: '), err);
        }
    });
});

const input = document.getElementById('photos');
const grid = document.getElementById('preview-grid');
const countEl = document.getElementById('photo-count');
const zone = document.getElementById('photo-zone');

if (input) {
    zone.addEventListener('dragover', e => { e.preventDefault(); zone.classList.add('border-primary'); });
    zone.addEventListener('dragleave', () => zone.classList.remove('border-primary'));
    zone.addEventListener('drop', e => {
        e.preventDefault();
        zone.classList.remove('border-primary');
        input.files = e.dataTransfer.files;
        updatePreview();
    });

    input.addEventListener('change', updatePreview);

    function updatePreview() {
        const files = Array.from(input.files);
        grid.innerHTML = '';
        files.forEach(file => {
            const img = document.createElement('img');
            img.src = URL.createObjectURL(file);
            img.onload = () => URL.revokeObjectURL(img.src);
            img.style = 'width:100px; height:100px; object-fit:cover; border-radius:6px;';
            grid.appendChild(img);
        });

        const existing = document.querySelectorAll('.delete-photo').length;
        const total = existing + files.length;

        if (total > 5) {
            countEl.textContent = interpolate(gettext("⚠️ Too many photos (%s/5)"), [total]);
            countEl.className = 'text-danger small mt-1';
        } else {
            countEl.textContent = files.length ? interpolate(
                ngettext("✓ %s new photo", "✓ %s new photos", files.length),
                [files.length]
            ) : '';
            countEl.className = 'text-success small mt-1';
        }
    }
}