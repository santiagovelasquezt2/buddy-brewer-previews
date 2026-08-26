const menuToggle = document.querySelector(".menu-toggle");
const navigation = document.querySelector("#primary-navigation");
const siteNav = document.querySelector(".site-nav");
const siteHeader = document.querySelector(".site-header");
const pageIntro = document.querySelector(".page-intro");

function finishIntro() {
  document.body.classList.remove("is-intro-playing");
  pageIntro?.remove();
}

if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
  finishIntro();
} else if (pageIntro) {
  pageIntro.addEventListener("animationend", (event) => {
    if (event.animationName === "intro-panel-exit") finishIntro();
  });

  window.setTimeout(finishIntro, 2500);
}
