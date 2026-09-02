function showEncodingOverlay(userId, onDone) {
    const overlay = document.createElement('div');
    overlay.id = 'encoding-overlay';
    overlay.style = `
        position: fixed; inset: 0; z-index: 9999;
        background: rgba(0,0,0,0.8);
        display: flex; flex-direction: column;
        align-items: center; justify-content: center;
        gap: 1rem;
    `;
    overlay.innerHTML = `
        <div class="spinner-border text-light" style="width: 3rem; height: 3rem;"></div>
        <p class="text-white fs-5 mb-0">${gettext("Face encoding in progress...")}</p>
        <p class="text-secondary small">${gettext("Please wait, do not leave the page.")}</p>
    `;
    document.body.appendChild(overlay);
    document.body.style.pointerEvents = 'none'; 

    const interval = setInterval(async () => {
        try {
            const response = await fetch(`/encoding-status/${userId}/`);
            const data = await response.json();

            if (data.status === 'done') {
                clearInterval(interval);
                document.body.removeChild(overlay);
                document.body.style.pointerEvents = '';
                if (onDone) onDone();
            } else if (data.status === 'error') {
                clearInterval(interval);
                overlay.innerHTML = `
                    <p class="text-danger fs-5">❌ ${gettext("Encoding failed")}.</p>
                    <button class="btn btn-secondary" onclick="location.reload()">${gettext("Close")}</button>
                `;
                document.body.style.pointerEvents = '';
            }
        } catch (err) {
            console.error('Polling error:', err);
        }
    }, 1000); 
}