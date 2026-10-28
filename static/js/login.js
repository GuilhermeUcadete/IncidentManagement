document.addEventListener("DOMContentLoaded", function () {
  const urlParams = new URLSearchParams(window.location.search);

  const erroLogin = document.getElementById("erro-login");
  const logoutOk = document.getElementById("logout-ok");
  const cadastroForm = document.getElementById("cadastro-form");
  const abrirCadastro = document.getElementById("abrir-cadastro");
  const voltarLogin = document.getElementById("voltar-login");
  const loginForm = document.getElementById("login-form");
  const mensagemCadastro = document.getElementById("mensagem-cadastro");

  if (abrirCadastro) abrirCadastro.addEventListener("click", function (event) {
    event.preventDefault();
    loginForm.style.display = "none";
    cadastroForm.style.display = "block";
    if (mensagemCadastro) mensagemCadastro.style.display = "none";
    if (erroLogin) erroLogin.style.display = "none";
  });

  if (voltarLogin) voltarLogin.addEventListener("click", function (event) {
    event.preventDefault();
    cadastroForm.style.display = "none";
    loginForm.style.display = "block";
    if (mensagemCadastro) mensagemCadastro.style.display = "none";
  });

  if (cadastroForm) cadastroForm.addEventListener("submit", async function (event) {
    event.preventDefault();
    if (mensagemCadastro) {
      mensagemCadastro.style.display = "block";
      mensagemCadastro.style.color = "#45f3ff";
      mensagemCadastro.textContent = "Realizando cadastro...";
    }
    const name = document.getElementById("cadastro-nome").value.trim();
    const login = document.getElementById("cadastro-login").value.trim();
    const password = document.getElementById("cadastro-senha").value;
    try {
      const response = await fetch("/register", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name, login, password })
      });
      const result = await response.json();
      if (!response.ok) throw new Error(result.error || "Não foi possível realizar o cadastro.");
      if (mensagemCadastro) {
        mensagemCadastro.style.color = "#45f3ff";
        mensagemCadastro.textContent = result.message;
      }
      document.getElementById("login").value = login;
      document.getElementById("password").value = "";
      cadastroForm.reset();
      cadastroForm.style.display = "none";
      loginForm.style.display = "block";
    } catch (error) {
      if (mensagemCadastro) {
        mensagemCadastro.style.display = "block";
        mensagemCadastro.style.color = "#ff2770";
        mensagemCadastro.textContent = error.message;
      }
    }
  });

  if (urlParams.has("error") && erroLogin) erroLogin.style.display = "block";
  if (urlParams.has("logout") && logoutOk) logoutOk.style.display = "block";

  const form = document.getElementById("login-form");
  if (!form) return;

  form.addEventListener("submit", async function (event) {
    event.preventDefault();

    const login = document.getElementById("login").value.trim();
    const password = document.getElementById("password").value.trim();

    if (erroLogin) erroLogin.style.display = "none";

    try {
      const response = await fetch("/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ login, password }),
      });

      if (!response.ok) {
        if (erroLogin) erroLogin.style.display = "block";
        return;
      }

      const data = await response.json();

      if (!data.tokenJWT) {
        if (erroLogin) erroLogin.style.display = "block";
        return;
      }

      localStorage.setItem("token", data.tokenJWT);
      localStorage.setItem(
        "usuario",
        JSON.stringify({
          id: data.id,
          login: data.login,
          name: data.name,
          role: data.role,
        })
      );

      window.location.href = "/templates/home.html";
    } catch (error) {
      console.error("Erro ao tentar logar:", error);
      if (erroLogin) erroLogin.style.display = "block";
    }
  });
});