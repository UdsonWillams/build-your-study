# 🚀 BuildYourStudy

Um app **local** para estudar do seu jeito, com lições interativas no navegador. Você lê
uma lição curta, resolve um exercício (código, SQL, quiz, digitação, áudio ou fala) **no
próprio navegador**, e o app corrige na hora. O progresso fica salvo num banco SQLite
local — sem servidor externo, sem assinatura, sem conta.

O que começou como um treino de Python virou uma plataforma multi-curso: hoje o
BuildYourStudy tem **5 trilhas completas**, cobrindo programação, banco de dados,
fundamentos de ciência da computação e dois idiomas.

## Cursos disponíveis

| Curso                                              | Categoria      | Nível                      |
| -------------------------------------------------- | -------------- | -------------------------- |
| 🐍 **Python do Zero**                              | Programação    | Iniciante                  |
| 🛢️ **SQL & Banco de Dados**                        | Banco de Dados | Iniciante ao Intermediário |
| 🧠 **Lógica de Programação & Estruturas de Dados** | Lógica         | Iniciante ao Avançado      |
| 🇬🇧 **Inglês do Zero**                              | Idiomas        | A1 a C1                    |
| 🇷🇺 **Russo do Zero**                               | Idiomas        | A1 a C1                    |

Cada curso é uma trilha de **Módulos → Tópicos → Exercícios**, com progresso salvo por
tópico e navegação sequencial (anterior/próximo).

## Como os exercícios rodam (sem servidor)

Tudo roda **dentro do navegador**, via WebAssembly — o servidor só serve HTML/JSON, não
executa nada dos alunos:

| Tipo    | Como funciona                                                                                                                                                                                                                                                                                                       |
| ------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `code`  | Código Python real, executado via [Pyodide](https://pyodide.org/) (Python compilado para WASM). O `test_code` roda `assert`s contra o código do aluno.                                                                                                                                                              |
| `sql`   | Consulta SQL real, executada via [sql.js](https://sql.js.org/) (SQLite compilado para WASM). O resultado da consulta do aluno é comparado com o de uma consulta de referência — não é comparação de texto. Suporta `SELECT` e também `INSERT`/`UPDATE`/`DELETE` (verificando o estado da tabela depois do comando). |
| `text`  | Resposta digitada, comparada de forma tolerante (sem diferenciar maiúsculas/pontuação; para russo, também aceita `е`/`ё` como equivalentes). Exercícios em russo mostram um **teclado cirílico virtual** clicável, e um botão 🔊 toca a pronúncia da resposta certa via TTS.                                        |
| `audio` | Toca uma frase por TTS (`speechSynthesis`, com opção de velocidade lenta) e o aluno transcreve o que ouviu.                                                                                                                                                                                                         |
| `speak` | O aluno fala em voz alta e o navegador transcreve via reconhecimento de voz (`SpeechRecognition`), comparando com a frase alvo. **Só funciona no Chrome/Edge** — ver [Navegadores](#navegadores).                                                                                                                    |
| `quiz`  | Múltipla escolha, com feedback visual de certo/errado e destaque da opção correta. Cada alternativa tem um botão 🔊 próprio para ouvir a pronúncia daquela opção via TTS.                                                                                                                                            |

Cada página de tópico só carrega os motores (Pyodide/sql.js) que aquele tópico
realmente usa — um tópico só de quiz, por exemplo, não baixa nem o Python nem o SQL.

## Nota do tópico (0 a 10)

Todo tópico com exercícios recebe uma nota: **cada exercício vale 1 ponto quando fica
correto**, e a nota é `acertos / total × 10`. Errar não tira ponto — dá para rever a
lição e tentar de novo quantas vezes quiser.

- A nota aparece num painel acima dos exercícios e num **espelho fixo na lateral**, que
  acompanha a rolagem para você não perder a pontuação de vista.
- O servidor guarda só a **melhor nota** já obtida: refazer um tópico nunca piora o que
  você já tinha.
- Num tópico já concluído, cada acerto que supera a melhor nota é salvo na hora — não
  precisa refazer o tópico inteiro nem clicar em nada.
- Um exercício só entra na conta depois de **respondido**: clicar em "Verificar" com o
  campo vazio, ou tentar gravar a fala e o microfone falhar, não vale zero.
- Na página do curso, cada lição avaliada mostra sua nota, e o cabeçalho traz a média
  das lições avaliadas.

Tópicos só de leitura (sem exercícios) não têm nota — só o "Marcar como lido".

## Progresso e Lixeira

O progresso é salvo por tópico (via SQLite) e sobrevive a reinícios do app e a
atualizações de conteúdo. Cursos podem ser **desativados** (somem do catálogo, mas nada é
apagado) e reativados a qualquer momento pela **Lixeira** (`/lixeira`); só é possível
excluir um curso **definitivamente** depois de desativado — e mesmo assim, se o arquivo
`.json` do curso ainda existir em `app/content/`, a exclusão é lembrada (não volta sozinha
num próximo restart).

## Como rodar

Requer **Python 3.10+**.

```bash
# 1. (opcional) crie um ambiente virtual
python -m venv .venv
# Windows:
.venv\Scripts\activate
# Linux/macOS:
source .venv/bin/activate

# 2. instale as dependências
pip install -r requirements.txt

# 3. rode o app
uvicorn app.main:app --reload
```

Abra <http://localhost:8000> no navegador.

### Navegadores

**Python, SQL e Lógica funcionam igual em qualquer navegador atual** — Pyodide, sql.js,
CodeMirror e o CSS são tudo WebAssembly/JS padrão, sem nada específico do Chrome.

A limitação está nos **cursos de idiomas**, e vem da Web Speech API, que os navegadores
implementam de forma bem diferente:

| Recurso                        | Chrome / Edge | Firefox                                       | Safari         |
| ------------------------------ | ------------- | --------------------------------------------- | -------------- |
| `code`, `sql`, `text`, `quiz`  | ✅            | ✅                                            | ✅             |
| Áudio/TTS (`audio`, botões 🔊) | ✅            | ⚠️ só com a voz do idioma instalada no sistema | ✅             |
| Exercícios `speak` (falar)     | ✅            | ❌ não implementa `SpeechRecognition`          | ⚠️ parcial      |

Quanto isso pesa: os exercícios `speak` são **7% do curso de inglês** e **16% do de
russo**. Todo o resto continua utilizável.

**O que o app faz quando o recurso não existe:**

- Sem reconhecimento de voz, os exercícios `speak` já abrem desabilitados, com o motivo
  explicado, e **saem do cálculo da nota** — um tópico de 10 exercícios vira um tópico de
  8, e dá para tirar 10,0 normalmente. Ninguém é penalizado pelo navegador que usa.
- Sem voz do idioma instalada, o app **avisa e não toca o áudio**, em vez de ler a frase
  em inglês/russo com a voz padrão em português. O Chrome não passa por isso porque traz
  vozes próprias; o Firefox só usa as vozes do sistema operacional.

**Instalar a voz do idioma (Windows):** Configurações → Hora e idioma → Idioma e região →
adicione o idioma → Opções → Fala. Depois reinicie o navegador.

Para conferir quais vozes o seu navegador enxerga, abra o console (F12) e rode:

```js
speechSynthesis.getVoices().map((v) => v.lang + " — " + v.name);
```

> Na primeira vez que abrir um tópico com exercício de código/SQL, o Pyodide/sql.js são
> baixados (alguns segundos). Depois fica rápido, graças ao cache do navegador.

## Estrutura do projeto

```
.
├─ app/
│  ├─ main.py            # FastAPI: páginas (catálogo, curso, tópico, lixeira) + API de progresso
│  ├─ database.py        # engine/sessão SQLAlchemy (SQLite)
│  ├─ models.py          # models ORM: Roadmap, Module, Topic, Exercise, Progress, DeletedRoadmap
│  ├─ schemas.py         # modelos Pydantic da API de progresso
│  ├─ seed.py            # carrega o conteúdo dos JSONs no banco (idempotente) + valida exercícios
│  └─ content/
│     ├─ python-do-zero.json
│     ├─ sql-do-zero.json
│     ├─ logica-de-programacao.json
│     ├─ ingles-do-zero.json
│     └─ russo-do-zero.json
├─ web/
│  ├─ templates/         # base.html, index.html, roadmap.html, topic.html, lixeira.html
│  └─ static/
│     ├─ css/           # broadsheet.css (design system) + style.css (telas do app)
│     └─ js/            # runner.js (exercícios, nota, TTS/STT) + progress.js (API)
├─ tools/                # geradores dos cursos grandes + roadmaps de expansão (ver tools/README.md)
├─ web-antigo/           # front-end da primeira versão, mantido só como referência
├─ requirements.txt
└─ study.db              # banco SQLite (gerado automaticamente, não versionado)
```

## Como adicionar novas aulas / cursos

Todo o conteúdo vive em `app/content/*.json`. Cursos pequenos (SQL, Lógica) são editados
direto no `.json`; os grandes (Python, Inglês, Russo) são **gerados** por scripts em
`tools/`, porque editar milhares de linhas de JSON escapado à mão quebra fácil:

```bash
python tools/build_python.py    # reescreve app/content/python-do-zero.json
python tools/build_ingles.py    # reescreve app/content/ingles-do-zero.json
python tools/build_russo.py     # reescreve app/content/russo-do-zero.json
```

`build_python.py` e `build_ingles.py` são incrementais: carregam o JSON atual como base e
só mexem nos módulos da fase em andamento, preservando os slugs (e o progresso) do que já
existe. Os planos de expansão de cada curso estão em `tools/PYTHON_ROADMAP.md`,
`tools/ENGLISH_ROADMAP.md` e `tools/RUSSIAN_ROADMAP.md`. Detalhes em
[`tools/README.md`](tools/README.md).

Para criar um curso novo do zero, adicione um arquivo `.json` em `app/content/` seguindo
o formato:

```jsonc
{
  "slug": "meu-curso", // identificador único (sem espaços)
  "title": "Meu Curso",
  "description": "...",
  "category": "Geral", // agrupa cursos no filtro do catálogo
  "icon": "📚", // emoji do card
  "level": "Iniciante",
  "position": 5, // ordem entre os cursos no catálogo
  "modules": [
    {
      "slug": "modulo-1",
      "title": "Módulo 1 — ...",
      "summary": "...",
      "position": 0,
      "topics": [
        {
          "slug": "topico-1",
          "title": "Tópico 1",
          "position": 0,
          "lesson_md": "# Markdown da lição...",
          "setup_sql": "", // só para exercícios do tipo sql (ver abaixo)
          "exercises": [
            {
              "position": 0,
              "type": "code", // code (padrão) | sql | text | audio | speak | quiz
              "prompt": "Enunciado em markdown.",
              "starter_code": "# código inicial\n",
              "test_code": "assert resultado == 42, 'mensagem de erro'",
              "solution": "resultado = 42",
            },
          ],
        },
      ],
    },
  ],
}
```

Depois é só reiniciar o app. O conteúdo é recarregado a cada inicialização, e o
**progresso e o estado ativo/desativado de cada curso são preservados** (religados pelos
`slug`).

### Slugs precisam ser únicos entre TODOS os cursos

`slug` de módulo e de tópico são identificadores globais (usados nas URLs `/topic/{slug}`
e como chave para religar progresso) — não podem se repetir entre arquivos `.json`
diferentes. Antes de adicionar conteúdo novo, vale rodar uma checagem rápida:

```python
import json, glob
slugs = {}
for path in glob.glob("app/content/*.json"):
    d = json.load(open(path, encoding="utf-8"))
    for m in d.get("modules", []):
        slugs.setdefault(m["slug"], []).append(path)
        for t in m.get("topics", []):
            slugs.setdefault(t["slug"], []).append(path)
print({k: v for k, v in slugs.items() if len(v) > 1} or "sem colisões")
```

### Campos por tipo de exercício

| Campo                       | `code`                    | `sql`                                                                                                                              | `text` / `audio`                                   | `speak`             | `quiz`                                           |
| --------------------------- | ------------------------- | ---------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------- | ------------------- | ------------------------------------------------ |
| `prompt`                    | ✅                        | ✅                                                                                                                                 | ✅                                                 | ✅                  | ✅                                               |
| `starter_code`              | ✅                        | opcional                                                                                                                           | —                                                  | —                   | —                                                |
| `test_code`                 | ✅ (asserts)              | —                                                                                                                                  | —                                                  | —                   | —                                                |
| `solution`                  | ✅ (código de referência) | ✅ (query/comando de referência)                                                                                                   | ✅ (resposta esperada)                             | ✅ (frase esperada) | ✅ (texto da opção correta)                      |
| `audio_text`                | —                         | —                                                                                                                                  | só `audio` (frase que o TTS lê)                    | ✅ (frase a falar)  | —                                                |
| `audio_lang`                | —                         | —                                                                                                                                  | ✅ (voz do 🔊)                                     | ✅                  | ✅ (voz do 🔊 de cada alternativa)               |
| `options`                   | —                         | metadados opcionais: `{"order_matters": true}`, `{"verify_query": "SELECT ..."}`, `{"setup_sql": "..."}` (sobrescreve o do tópico) | —                                                  | —                   | ✅ lista de alternativas, ex.: `["A", "B", "C"]` |

Exercícios `sql` usam `Topic.setup_sql` (DDL/DML compartilhado pelos exercícios daquele
tópico) — a consulta do aluno roda contra esse schema e o resultado é comparado ao da
`solution`, ignorando a ordem das linhas por padrão (ative `order_matters` quando a ordem
importar). Para `INSERT`/`UPDATE`/`DELETE`, defina `verify_query` em `options`: o app roda
o comando do aluno, depois a `verify_query`, e compara o estado resultante da tabela.

### Validação automática de conteúdo

Ao carregar os JSONs, o `seed()` **executa de verdade** cada exercício `code` (Python,
via `exec`) e `sql` (SQLite em memória) contra sua própria `solution`/`test_code` —
bugs de autoria (assert errado, SQL quebrado) derrubam o carregamento com uma mensagem
apontando o tópico e a posição do exercício, em vez de chegar até o aluno.

## Tecnologias

FastAPI · Uvicorn · SQLAlchemy · Jinja2 · SQLite · Pyodide · sql.js · CodeMirror · Web Speech API (TTS/STT)

## Inspiração de conteúdo

- [gto76/python-cheatsheet](https://github.com/gto76/python-cheatsheet) (referência — licença CC BY-NC-SA)
- [TheAlgorithms/Python](https://github.com/TheAlgorithms/Python) (referência de algoritmos — licença MIT)
