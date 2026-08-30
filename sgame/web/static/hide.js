// Экран команды гаснет по кнопке и через минуту бездействия:
// компьютер переходит из рук в руки, случайный взгляд не должен ничего показать.
(function () {
  const cover = document.getElementById("cover");
  if (!cover) return;
  // На личном телефоне гасить экран по таймеру незачем: он придуман для
  // компьютера, который передают из рук в руки.
  const script = document.currentScript || document.querySelector('script[src*="hide.js"]');
  const autohide = !script || script.dataset.autohide !== "0";
  let timer = null;

  function hide() { cover.hidden = false; }
  function show() { cover.hidden = true; restart(); }
  function restart() {
    clearTimeout(timer);
    if (autohide) timer = setTimeout(hide, 60000);
  }

  document.getElementById("hide-button").addEventListener("click", hide);
  cover.addEventListener("click", show);
  ["keydown", "pointerdown"].forEach((event) =>
    document.addEventListener(event, () => { if (cover.hidden) restart(); })
  );
  restart();
})();
