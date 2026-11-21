// Wstawienie propozycji z katalogu rozwoju do pola wniosków IPRZ, tylko na kliknięcie oceniającego.
document.addEventListener("click", function (e) {
  var przycisk = e.target.closest("[data-wstaw-iprz]");
  if (!przycisk) return;
  var formularz = przycisk.closest("form");
  var pole = formularz && formularz.querySelector("textarea[name=wnioski_iprz]");
  if (!pole) return;
  var tekst = "- " + przycisk.getAttribute("data-wstaw-iprz");
  if (pole.value.indexOf(tekst) === -1) {
    pole.value = pole.value.trim() ? pole.value.replace(/\s+$/, "") + "\n" + tekst : tekst;
  }
  przycisk.textContent = "Wstawiono: przeredaguj w polu wniosków";
  pole.focus();
});
