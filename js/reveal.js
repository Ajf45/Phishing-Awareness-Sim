document.addEventListener('DOMContentLoaded', () => {
  const btn = document.getElementById('reveal');
  if (btn) {
    btn.addEventListener('click', () => {
      document.querySelectorAll('.red-flag').forEach(flag => flag.style.display = 'block');
    });
  }
});