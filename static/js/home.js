document.addEventListener("DOMContentLoaded", function () {
  const token = localStorage.getItem("token");
  const usuarioRaw = localStorage.getItem("usuario");

  if (!token) {
    window.location.href = "/index.html?error=unauthorized";
    return;
  }

  let login = "";
  if (usuarioRaw) {
    try {
      const usuarioObj = JSON.parse(usuarioRaw);
      login = usuarioObj.login || "";
    } catch {
      login = usuarioRaw;
    }
  }

  const usuarioLogado = document.getElementById("usuario-logado");
  if (usuarioLogado) {
    usuarioLogado.textContent = login || "Usuário";
  }

  // Mostra apenas as áreas compatíveis com o perfil autenticado.
  let role = "";
  try { role = JSON.parse(usuarioRaw || "{}").role || ""; } catch {}
  const allowed = {
    PROFESSOR: ["ocorrencias.html"],
    ANALISTA: ["ocorrencias.html", "dashboard-ocorrencias.html", "relatorios.html"],
    COORDENADOR: ["ocorrencias.html", "dashboard-ocorrencias.html", "relatorios.html"],
    ADMINISTRATIVO: ["alunos.html", "turmas.html", "usuarios.html", "vincular-alunos.html", "gerenciar-categorias.html"]
  }[role] || [];
  document.querySelectorAll(".cards-container .card").forEach(card => {
    const target = card.getAttribute("onclick") || "";
    const page = target.match(/navigateTo\('([^']+)'\)/)?.[1];
    if (page && !allowed.includes(page)) card.style.display = "none";
  });

  const btnLogout = document.getElementById("btn-logout");
  if (btnLogout) {
    btnLogout.addEventListener("click", function () {
      localStorage.removeItem("token");
      localStorage.removeItem("usuario");
      localStorage.removeItem("id");
      window.location.href = "/index.html?logout=true";
    });
  }
});

function navigateTo(page) {
  window.location.href = page;
}