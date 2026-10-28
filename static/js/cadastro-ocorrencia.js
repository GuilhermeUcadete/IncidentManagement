document.addEventListener("DOMContentLoaded", () => {
  const form = document.getElementById("form-cadastro");
  const mensagem = document.getElementById("mensagem-retorno");
  const turmaSelect = document.getElementById("id-schoolclass");
  const alunoSelect = document.getElementById("id-student");
  const categoriaSelect = document.getElementById("category");
  const tipoSelect = document.getElementById("type");
  const dataInput = document.getElementById("register-date");

  const agoraLocal = () => new Date(Date.now() - new Date().getTimezoneOffset() * 60000).toISOString().slice(0, 16);
  if (!dataInput.value) dataInput.value = agoraLocal();

  function mostrarMensagem(texto, tipo = "erro") {
    mensagem.textContent = texto;
    mensagem.className = `mensagem ${tipo}`;
  }

  async function requisitar(url, opcoes = {}) {
    const resposta = await apiFetch(url, opcoes);
    const dados = await resposta.json().catch(() => ({}));
    if (!resposta.ok) throw new Error(dados.error || `Erro ao consultar ${url} (${resposta.status}).`);
    return dados;
  }

  function listaDaResposta(dados) {
    if (Array.isArray(dados)) return dados;
    if (dados && Array.isArray(dados.content)) return dados.content;
    if (dados && Array.isArray(dados.items)) return dados.items;
    return [];
  }

  async function carregarTurmas() {
    turmaSelect.disabled = true;
    turmaSelect.innerHTML = '<option value="">Carregando turmas...</option>';
    alunoSelect.disabled = true;
    alunoSelect.innerHTML = '<option value="">Selecione uma turma primeiro</option>';
    try {
      const dados = await requisitar("/schoolclasses?page=0&size=100");
      const turmas = listaDaResposta(dados).filter(t => !t.canceled);
      turmaSelect.innerHTML = '<option value="">Selecione a turma</option>';
      turmas.forEach(t => {
        const opcao = document.createElement("option");
        opcao.value = t.id;
        opcao.textContent = `${t.name} — ${t.shift}, ${t.year}/${t.semester}`;
        turmaSelect.appendChild(opcao);
      });
      if (turmas.length === 0) {
        turmaSelect.innerHTML = '<option value="">Nenhuma turma cadastrada</option>';
        mostrarMensagem("Nenhuma turma cadastrada. Entre com o perfil Administrativo e cadastre uma turma.");
      } else {
        turmaSelect.disabled = false;
        mensagem.textContent = "";
      }
    } catch (erro) {
      turmaSelect.innerHTML = '<option value="">Erro ao carregar turmas</option>';
      mostrarMensagem(`${erro.message} Atualize a página e confirme que você entrou no sistema.`);
    }
  }

  async function carregarAlunos() {
    alunoSelect.disabled = true;
    alunoSelect.innerHTML = '<option value="">Carregando alunos...</option>';
    if (!turmaSelect.value) {
      alunoSelect.innerHTML = '<option value="">Selecione uma turma primeiro</option>';
      return;
    }
    try {
      const dados = await requisitar(`/students?classId=${encodeURIComponent(turmaSelect.value)}&page=0&size=100`);
      const alunos = listaDaResposta(dados);
      alunoSelect.innerHTML = '<option value="">Selecione o aluno</option>';
      alunos.forEach(a => {
        const opcao = document.createElement("option");
        opcao.value = a.id;
        opcao.textContent = a.name;
        alunoSelect.appendChild(opcao);
      });
      if (alunos.length === 0) {
        alunoSelect.innerHTML = '<option value="">Nenhum aluno vinculado a esta turma</option>';
        mostrarMensagem("Esta turma ainda não tem alunos vinculados. Use a opção 'Vincular alunos' no perfil Administrativo.");
      } else {
        alunoSelect.disabled = false;
        mensagem.textContent = "";
      }
    } catch (erro) {
      alunoSelect.innerHTML = '<option value="">Erro ao carregar alunos</option>';
      mostrarMensagem(erro.message);
    }
  }

  async function carregarCategorias() {
    categoriaSelect.disabled = true;
    categoriaSelect.innerHTML = '<option value="">Carregando categorias...</option>';
    try {
      const dados = await requisitar("/incidents/categories");
      const categorias = listaDaResposta(dados);
      categoriaSelect.innerHTML = '<option value="">Selecione a categoria</option>';
      categorias.forEach(valor => {
        const nome = typeof valor === "string" ? valor : valor.name;
        if (!nome) return;
        const opcao = document.createElement("option");
        opcao.value = nome;
        opcao.textContent = nome.replaceAll("_", " ");
        categoriaSelect.appendChild(opcao);
      });
      if (categorias.length === 0) {
        categoriaSelect.innerHTML = '<option value="">Nenhuma categoria cadastrada</option>';
        mostrarMensagem("Não há categorias cadastradas. Cadastre uma categoria no perfil Administrativo.");
      } else {
        categoriaSelect.disabled = false;
      }
    } catch (erro) {
      categoriaSelect.innerHTML = '<option value="">Erro ao carregar categorias</option>';
      mostrarMensagem(erro.message);
    }
  }

  async function carregarTipos() {
    tipoSelect.disabled = true;
    tipoSelect.innerHTML = '<option value="">Selecione uma categoria primeiro</option>';
    if (!categoriaSelect.value) return;
    try {
      const dados = await requisitar(`/incidents/types/${encodeURIComponent(categoriaSelect.value)}`);
      const tipos = listaDaResposta(dados);
      tipoSelect.innerHTML = '<option value="">Selecione o tipo de ocorrência</option>';
      tipos.forEach(valor => {
        const nome = typeof valor === "string" ? valor : valor.name;
        if (!nome) return;
        const opcao = document.createElement("option");
        opcao.value = nome;
        opcao.textContent = nome.replaceAll("_", " ");
        tipoSelect.appendChild(opcao);
      });
      if (tipos.length === 0) {
        tipoSelect.innerHTML = '<option value="">Nenhum tipo nesta categoria</option>';
        mostrarMensagem("Não há tipos cadastrados para esta categoria. Cadastre um tipo no perfil Administrativo.");
      } else {
        tipoSelect.disabled = false;
        mensagem.textContent = "";
      }
    } catch (erro) {
      tipoSelect.innerHTML = '<option value="">Erro ao carregar tipos</option>';
      mostrarMensagem(erro.message);
    }
  }

  turmaSelect.addEventListener("change", carregarAlunos);
  categoriaSelect.addEventListener("change", carregarTipos);

  form.addEventListener("submit", async evento => {
    evento.preventDefault();
    if (!turmaSelect.value || !alunoSelect.value || !categoriaSelect.value || !tipoSelect.value) {
      mostrarMensagem("Selecione a turma, o aluno, a categoria e o tipo de ocorrência.");
      return;
    }
    const payload = {
      idSchoolClass: Number(turmaSelect.value),
      idStudent: Number(alunoSelect.value),
      registerDate: dataInput.value.replace("T", " "),
      category: categoriaSelect.value,
      type: tipoSelect.value,
      description: document.getElementById("description").value.trim()
    };
    try {
      await requisitar("/incidents", { method: "POST", body: JSON.stringify(payload) });
      mostrarMensagem("Ocorrência registrada com sucesso!", "sucesso");
      form.reset();
      dataInput.value = agoraLocal();
      tipoSelect.disabled = true;
      tipoSelect.innerHTML = '<option value="">Selecione uma categoria primeiro</option>';
      alunoSelect.disabled = true;
      alunoSelect.innerHTML = '<option value="">Selecione uma turma primeiro</option>';
    } catch (erro) {
      mostrarMensagem(erro.message);
    }
  });

  carregarTurmas();
  carregarCategorias();
});
