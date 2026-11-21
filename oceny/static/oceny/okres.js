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

// Animujemy rzeczywistą wysokość, aby zwijanie działało także dla treści ładowanej przez HTMX.
const ograniczRuch = window.matchMedia("(prefers-reduced-motion: reduce)");
const przejscia = new WeakMap();

function animujSzczegoly(szczegoly, summary, zamknij) {
  if (ograniczRuch.matches || !szczegoly.animate) {
    przejscia.get(szczegoly)?.cancel();
    przejscia.delete(szczegoly);
    szczegoly.removeAttribute("data-zamykanie");
    szczegoly.open = !zamknij;
    return;
  }

  const poczatek = szczegoly.getBoundingClientRect().height;
  przejscia.get(szczegoly)?.cancel();
  szczegoly.toggleAttribute("data-zamykanie", zamknij);
  szczegoly.open = true;

  const styl = getComputedStyle(szczegoly);
  const krawedzie = parseFloat(styl.paddingTop) + parseFloat(styl.paddingBottom)
    + parseFloat(styl.borderTopWidth) + parseFloat(styl.borderBottomWidth);
  const koniec = zamknij ? summary.getBoundingClientRect().height + krawedzie : szczegoly.getBoundingClientRect().height;
  const animacja = szczegoly.animate(
    [{ height: poczatek + "px", overflow: "clip" }, { height: koniec + "px", overflow: "clip" }],
    { duration: 180, easing: "cubic-bezier(.2,.7,.2,1)" },
  );
  przejscia.set(szczegoly, animacja);
  animacja.onfinish = function () {
    szczegoly.open = !zamknij;
    szczegoly.removeAttribute("data-zamykanie");
    przejscia.delete(szczegoly);
  };
}

document.addEventListener("click", function (event) {
  const summary = event.target.closest("details > summary");
  if (!summary || event.defaultPrevented) {
    const odnosnik = event.target.closest('a[href^="#"]');
    if (odnosnik && odnosnik.hash === location.hash) pokazCelOdnosnika();
    return;
  }
  if (event.target.closest("a, button, input, select, textarea, label")) return;
  const szczegoly = summary.parentElement;
  const zamknij = szczegoly.open && !szczegoly.hasAttribute("data-zamykanie");
  event.preventDefault();
  animujSzczegoly(szczegoly, summary, zamknij);
});

function pokazCelOdnosnika() {
  const cel = document.getElementById(location.hash.slice(1));
  const sekcja = cel?.closest(".sekcja-sprawy");
  if (!sekcja || sekcja.open && !sekcja.hasAttribute("data-zamykanie")) return;
  animujSzczegoly(sekcja, sekcja.firstElementChild, false);
  sekcja.scrollIntoView();
}

window.addEventListener("hashchange", pokazCelOdnosnika);
pokazCelOdnosnika();

// Każdy wybór zostaje w formularzu aż do zatwierdzenia rozmowy.
function odswiezDostepneKryteria(grupa) {
  const pola = [...grupa.querySelectorAll("select")];
  const wybrane = new Set(pola.map((pole) => pole.value).filter(Boolean));
  for (const pole of pola) {
    for (const opcja of pole.options) {
      opcja.disabled = !opcja.selected && wybrane.has(opcja.value);
    }
  }
}

document.addEventListener("change", function (event) {
  const grupa = event.target.closest("[data-wybor-kryteriow]");
  if (grupa) odswiezDostepneKryteria(grupa);
});
document.addEventListener("htmx:load", function (event) {
  event.target.querySelectorAll("[data-wybor-kryteriow]").forEach(odswiezDostepneKryteria);
});
