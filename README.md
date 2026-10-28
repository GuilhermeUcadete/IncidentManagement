# Integrantes

Eduardo da Silva Lima (RM: 554804)
 
Enzo Bonacasata Motta  (RM: 555372)
 
Guilherme Ulacco (RM: 558418)
 
Matheus Hostim (RM: 556517)

## Como executar no Windows

1. Instale Python 3.10 ou superior.
2. Abra o Prompt de Comando dentro da pasta `IncidentManagement`.
3. Execute:

```bat
py -m venv .venv
.venv\Scripts\activate
py -m pip install -r requirements.txt
py app.py
```

4. Abra `http://127.0.0.1:5000` no navegador.

## Contas demonstrativas

| Perfil | Login | Senha |
|---|---|---|
| Professor | `professor` | `1234` |
| Analista de Qualidade | `analista` | `1234` |
| Coordenador | `coordenador` | `1234` |
| Professor Administrativo | `administrativo` | `1234` |

## Funcionalidades 

- Login e autorização por perfil no backend.
- Cadastro, consulta, edição e inativação de alunos e turmas.
- Cadastro de categorias e tipos de ocorrência.
- Vínculo muitos-para-muitos entre alunos e turmas.
- Registro de ocorrências com validação do vínculo aluno/turma e categoria/tipo.
- Professor pode consultar ocorrências de todos os professores, mas só alterar/excluir as próprias.
- Consultas com filtros por aluno, turma, categoria, tipo e período.
- Dashboard com totalizadores e gráficos por categoria, tipo, turma e aluno.
- Upload de foto de aluno (máximo 5 MB).

