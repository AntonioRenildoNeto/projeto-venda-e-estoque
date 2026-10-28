// Scripts do sistema (arquivo externo por causa da política de segurança do navegador).
(function () {
  "use strict";

  // Pede confirmação antes de enviar formulários marcados com data-confirmar="mensagem".
  document.addEventListener("submit", function (evento) {
    var mensagem = evento.target.getAttribute("data-confirmar");
    if (mensagem && !window.confirm(mensagem)) {
      evento.preventDefault();
    }
  });

  // Várias linhas de produto na mesma compra/venda.
  var botaoAdicionar = document.getElementById("btn-adicionar-item");
  if (botaoAdicionar) {
    var caixa = document.getElementById(botaoAdicionar.getAttribute("data-alvo"));
    var modelo = caixa.querySelector(".item-linha");
    botaoAdicionar.hidden = false;

    botaoAdicionar.addEventListener("click", function () {
      var nova = modelo.cloneNode(true);
      nova.querySelectorAll("[id]").forEach(function (el) { el.removeAttribute("id"); });
      nova.querySelectorAll("label").forEach(function (el) { el.remove(); });
      nova.querySelectorAll("input").forEach(function (el) { el.value = ""; });
      nova.querySelectorAll("select").forEach(function (el) { el.selectedIndex = 0; });
      nova.querySelectorAll("select, input").forEach(function (el) {
        el.setAttribute("aria-label", el.name.replace("_", " "));
      });
      nova.querySelector(".btn-remover-item").hidden = false;
      caixa.appendChild(nova);
      var primeiro = nova.querySelector("select, input");
      if (primeiro) { primeiro.focus(); }
    });

    caixa.addEventListener("click", function (evento) {
      if (evento.target.classList.contains("btn-remover-item")) {
        evento.target.closest(".item-linha").remove();
      }
    });
  }
})();
