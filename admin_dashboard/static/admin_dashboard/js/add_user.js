const input = document.getElementById("photos");
const grid = document.getElementById("preview-grid");
const countEl = document.getElementById("photo-count");
const submitBtn = document.getElementById("submit-btn");
const zone = document.getElementById("photo-zone");

submitBtn.disabled = true;

zone.addEventListener("dragover", (e) => {
	e.preventDefault();
	zone.classList.add("border-primary");
});

zone.addEventListener("dragleave", () => {
	zone.classList.remove("border-primary");
});

zone.addEventListener("drop", (e) => {
	e.preventDefault();
	zone.classList.remove("border-primary");
	input.files = e.dataTransfer.files;
	updatePreview();
});

input.addEventListener("change", updatePreview);

function updatePreview() {
	const files = Array.from(input.files);
	grid.innerHTML = "";

	files.slice(0, 5).forEach((file) => {
		const img = document.createElement("img");
		img.src = URL.createObjectURL(file);
		img.onload = () => URL.revokeObjectURL(img.src);
		img.style =
			"width:100px; height:100px; object-fit:cover; border-radius:8px;";
		grid.appendChild(img);
	});

	if (files.length === 0) {
		countEl.textContent = "";
		countEl.className = "form-text mt-1";
		submitBtn.disabled = false;
	} else if (files.length > 5) {
		const msg = interpolate(gettext("Selected %s photos – maximum is 5!"), [
			files.length,
		]);
		countEl.textContent = `⚠️ ` + msg;
		countEl.className = "text-danger small mt-1";
		submitBtn.disabled = true;
	} else {
		const text = interpolate(
			ngettext("%s photo selected", "%s photos selected", files.length),
			[files.length],
		);
		countEl.textContent = `✓ ${text}`;
		countEl.className = "text-success small mt-1";
		submitBtn.disabled = false;
	}
}
