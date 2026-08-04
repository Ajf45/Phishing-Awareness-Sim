// Minor UX helper: nothing analytics-related lives here — chart logic is
// inline in campaign_detail.html since it needs the campaign id from Jinja.
document.addEventListener("DOMContentLoaded", () => {
  const picker = document.querySelector(".target-picker");
  if (!picker) return;

  const selectAllBtn = document.createElement("button");
  selectAllBtn.type = "button";
  selectAllBtn.textContent = "Select all";
  selectAllBtn.className = "btn-secondary";
  selectAllBtn.style.marginTop = "8px";
  selectAllBtn.addEventListener("click", () => {
    picker.querySelectorAll('input[type=checkbox]').forEach(cb => cb.checked = true);
  });
  picker.after(selectAllBtn);
});