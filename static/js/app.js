document.querySelectorAll('.flash').forEach((item) => { setTimeout(() => { if (item && item.parentElement) item.style.opacity = '0.92'; }, 4000); });
