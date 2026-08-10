# Roteiro: Python do Zero → Hero

Documento vivo. Se você é uma sessão nova (Claude ou humano) pegando este
trabalho do zero: leia isto inteiro antes de mexer em qualquer coisa. Ele
existe porque o curso proposto é grande demais para uma sessão só — a ideia é
avançar por fases, cada uma commitável e validável sozinha.

**Como continuar de onde parou**: veja a seção "Status" abaixo para saber qual
é a próxima fase. Todo módulo já construído tem checkbox marcado. Comece pela
primeira fase sem checkbox.

## Contexto

O curso hoje (antes deste roteiro) tinha 5 módulos rasos (20 tópicos, 22
exercícios) — só o essencial de sintaxe. O pedido é transformar isso num "0 to
hero" de verdade: lógica de programação, ambiente, fundamentos, OOP, tratamento
de erros, módulos, Python avançado (generators/decorators/context managers),
type hints, arquivos, dependências, Git, qualidade de código, testes, web,
FastAPI, async/concorrência e, no fim, Python aplicado a IA/LLMs.

## Restrição técnica importante

Os exercícios de código deste site rodam **Python de verdade, mas dentro do
navegador via Pyodide** — sem terminal real, sem sistema de arquivos de
verdade, sem `git`, sem servidor HTTP rodando, sem threads/processos do SO de
verdade, sem chamada de rede para APIs externas (LLMs inclusive).

Decisão já validada com o usuário: nesses módulos, os exercícios são
**conceituais** (`quiz`/`text` testando entendimento, com trechos de código
mostrados na lição mas não "rodados") em vez de `code`. Módulos afetados:
Preparando o Ambiente, Git e GitHub, Programação Web/FastAPI,
Programação assíncrona (a sintaxe `async`/`await` roda no Pyodide; concorrência
*de verdade* com I/O real, não), Concorrência e Paralelismo, Python para IA.

Nesses módulos a lição deve ser **mais didática e sugerir ativamente que o
aluno abra o próprio terminal e rode um comando** para validar o que acabou de
aprender (ex.: "agora abra seu terminal e rode `python --version`"). Regra
importante: **só sugerir um comando que já foi explicado nessa lição ou em
lição anterior** — nunca pedir pro aluno rodar algo que ele ainda não viu.

Tudo que é linguagem pura — OOP, decorators, generators, context managers,
exceções, type hints, `asyncio` sintático — roda de verdade no Pyodide e deve
usar exercícios `code` com `test_code` real (o `seed.py` já executa e valida
isso na carga, e o gerador replica a mesma validação antes mesmo de escrever o
JSON — ver `_validate_code_exercise` abaixo).

## Padrão de autoria (igual ao russo/inglês)

Curso inteiro num único `app/content/python-do-zero.json`, gerado por
`tools/build_python.py` (mesmo padrão de `build_russo.py`/`build_ingles.py`,
documentado em `tools/README.md`). **Nunca edite o JSON à mão** — edite o
gerador e rode `python tools/build_python.py`.

O gerador **carrega o JSON atual como base** e só acrescenta/edita os módulos
da fase em andamento — módulos de fases futuras (ainda não escritos) ficam
intactos. Isso preserva os slugs existentes (e portanto o progresso já salvo
de quem já usa o curso).

Regras que o `check()` do gerador trava antes de escrever qualquer coisa:
- tópico com menos de 5 exercícios;
- exercício `quiz` cujas alternativas colidem depois de normalizar, ou cuja
  solução não bate com exatamente uma alternativa;
- exercício `code` cujo `solution` + `test_code` não passam quando executados
  de verdade (mesmo mecanismo do `seed.py`);
- slugs de tópico/módulo duplicados (inclusive contra os outros 4 cursos).

## Numeração

A lista original do usuário tinha lacunas (pulava de 18 para 23, e de 24 para
35) — provavelmente reservadas para módulos que ele ainda vai detalhar. Para
não ter buracos no curso publicado, renumerei os módulos **sequencialmente**
conforme vão sendo construídos; a tabela abaixo mostra de onde cada um veio.

## Status

| # | Módulo | Origem na lista do usuário | Tipo | Status |
|---|---|---|---|---|
| 0 | Hello World: bem-vindo | (já existia, fora da lista nova) | conceitual | ✅ já existia, mantido |
| 1 | Lógica de Programação | 1. Introdução à programação | conceitual | ✅ feito (9 tópicos, 46 exercícios) |
| 2 | Preparando o Ambiente | 2. Preparando o ambiente | conceitual | ✅ feito (5 tópicos, 25 exercícios) |
| 3 | Fundamentos do Python | 3. Fundamentos do Python | código | ✅ feito (6 tópicos, 45 exercícios) |
| 4 | Estruturas de Controle | 4. Estruturas de controle | código | ⬜ (expandir "Controle de fluxo" existente, sem comprehensions) |
| 5 | Estruturas de Dados | 5. Estruturas de dados | código | ⬜ (expandir "Estruturas de dados" existente + mover comprehensions pra cá) |
| 6 | Funções | 6. Funções | código | ⬜ (expandir função já existente em "Organizando o código") |
| 7 | Tratamento de Erros | 7. Tratamento de erros | código | ⬜ (expandir "tratamento-de-erros" existente) |
| 8 | Módulos e Pacotes | 8. Módulos e pacotes | misto (import é código; `__name__`/pacotes/pyproject é conceitual) | ⬜ (expandir "modulos-e-imports" existente) |
| 9 | Programação Orientada a Objetos | 9. POO | código | ⬜ novo |
| 10 | Python Avançado | 10. Python avançado | código | ⬜ novo |
| 11 | Type Hints | 11. Type Hints | código | ⬜ novo |
| 12 | Arquivos e Dados | 12. Arquivos e dados | código (I/O de arquivo funciona no Pyodide, sistema de arquivos virtual em memória) | ⬜ novo |
| 13 | Bibliotecas e Dependências | 13. Bibliotecas e gerenciamento de dependências | conceitual | ⬜ novo |
| 14 | Git e GitHub | 14. Git e GitHub | conceitual | ⬜ novo |
| 15 | Qualidade de Código | 15. Qualidade de código | misto (PEP 8/nomes dá pra testar com quiz sobre trechos de código; linters/ruff é conceitual) | ⬜ novo |
| 16 | Testes Automatizados | 16. Testes automatizados | misto (asserts/pytest básico rodam no Pyodide; fixtures/mocks avançados ficam conceituais) | ⬜ novo |
| 17 | Programação Web | 17. Programação Web | conceitual | ⬜ novo |
| 18 | FastAPI | 18. FastAPI | conceitual (com trechos de código de exemplo) | ⬜ novo |
| 19 | Programação Assíncrona | 23. Programação assíncrona | misto (sintaxe async/await roda no Pyodide; conceitos de I/O real ficam conceituais) | ⬜ novo |
| 20 | Concorrência e Paralelismo | 24. Concorrência e paralelismo | conceitual | ⬜ novo |
| 21 | Python para IA | 35. Python para IA | conceitual (com trechos de código de exemplo) | ⬜ novo |

## Fases de execução sugeridas

Cada fase é um tamanho razoável para uma sessão. Ordem sugerida (pode mudar a
pedido do usuário):

- ✅ **Fase 1**: Módulo 1 (Lógica de Programação) — feito.
- ✅ **Fase 2**: Módulo 2 (Preparando o Ambiente) + Módulo 3 (Fundamentos, expandir existente) — feito.
- **Fase 3**: Módulo 4 (Estruturas de Controle) + Módulo 5 (Estruturas de Dados, com comprehensions).
- **Fase 4**: Módulo 6 (Funções) + Módulo 7 (Tratamento de Erros) + Módulo 8 (Módulos e Pacotes).
- **Fase 5**: Módulo 9 (POO) — provavelmente o maior módulo sozinho (classes, herança, polimorfismo, dunder methods, dataclasses, properties).
- **Fase 6**: Módulo 10 (Python Avançado: iterators/generators/decorators/context managers) + Módulo 11 (Type Hints).
- **Fase 7**: Módulo 12 (Arquivos) + Módulo 13 (Dependências) + Módulo 14 (Git).
- **Fase 8**: Módulo 15 (Qualidade) + Módulo 16 (Testes).
- **Fase 9**: Módulo 17 (Web) + Módulo 18 (FastAPI).
- **Fase 10**: Módulo 19 (Async) + Módulo 20 (Concorrência).
- **Fase 11**: Módulo 21 (Python para IA) — fecha o curso.

Depois de cada fase: rodar `python tools/build_python.py`, depois
`python -m app.seed`, subir o app e conferir 1-2 tópicos no navegador antes de
marcar o checkbox e seguir. Não é preciso perguntar permissão para continuar
entre fases — só checar com o usuário se algo no plano parecer errado.
