# Integrantes

Eduardo da Silva Lima (RM: 554804)
 
Enzo Bonacasata Motta  (RM: 555372)
 
Guilherme Ulacco (RM: 558418)
 
Matheus Hostim (RM: 556517)

# IncidentManagement — Sistema de gestão de ocorrências escolares

Esta versão mantém a estrutura original (`templates/`, `static/css/` e `static/js/`) e adiciona uma API Flask com banco SQLite para atender aos requisitos do PDF.

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

Altere as senhas e a chave de sessão antes de qualquer uso real. O banco de dados é criado automaticamente em `instance/incident_management.db`.

## Funcionalidades cobertas

- Login e autorização por perfil no backend.
- Cadastro, consulta, edição e inativação de alunos e turmas.
- Cadastro de categorias e tipos de ocorrência.
- Vínculo muitos-para-muitos entre alunos e turmas.
- Registro de ocorrências com validação do vínculo aluno/turma e categoria/tipo.
- Professor pode consultar ocorrências de todos os professores, mas só alterar/excluir as próprias.
- Consultas com filtros por aluno, turma, categoria, tipo e período.
- Dashboard com totalizadores e gráficos por categoria, tipo, turma e aluno.
- Upload de foto de aluno (máximo 5 MB).

## Observações

- O banco SQLite e as fotos ficam localmente no computador que executa o servidor.
- As contas iniciais são apenas para demonstração; não use senhas de demonstração em produção.
- A interface original foi preservada e os arquivos novos foram adicionados para completar os requisitos. Algumas telas antigas do projeto original podem conter operações extras que não fazem parte dos requisitos principais e não foram substituídas por uma nova interface.
