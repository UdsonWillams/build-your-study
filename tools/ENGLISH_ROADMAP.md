# Roteiro: Inglês do Zero → Fluência (A1 → C1 + trilha aplicada)

Documento vivo, no mesmo espírito de `tools/PYTHON_ROADMAP.md`. Se você é uma
sessão nova (Claude ou humano) pegando este trabalho do zero: leia isto
inteiro antes de mexer em qualquer coisa. O curso proposto é grande demais
para uma sessão só — a ideia é avançar por fases, cada uma commitável e
validável sozinha.

**Como continuar de onde parou**: veja a seção "Status" abaixo. Todo módulo
já construído tem checkbox marcado. Comece pelo primeiro módulo sem checkbox.

**Todo o conteúdo deste documento (e do curso) é em português (pt-BR)**,
inclusive os nomes dos pontos gramaticais — por preferência explícita do
usuário. Isso é uma mudança de convenção em relação ao curso atual, que usa
termos em inglês nos títulos (ex.: "Perfect Tenses (B1–B2)"); no novo curso,
o mesmo módulo vira "Tempos Perfeitos".

## Contexto

O curso atual (`app/content/ingles-do-zero.json`) tem 9 módulos, 45 tópicos e
190 exercícios cobrindo A1→C1 de forma enxuta (1-2 módulos por nível). O
usuário desenhou uma grade curricular bem mais granular e completa: **27
módulos**, cada um com ~10-15 itens, separados por habilidade (gramática,
vocabulário, comunicação, speaking, listening, writing) por nível, mais uma
trilha aplicada pós-C1 (trabalho, tecnologia, fluência, imersão).

**Decisão confirmada com o usuário**: o curso vai ser **reescrito do zero**
seguindo esse novo esqueleto — os 9 módulos e slugs atuais são descartados
(o progresso salvo do curso de inglês atual, se houver, será perdido; foi
uma escolha consciente do usuário em troca de uma estrutura muito mais
completa).

**Gramática explícita, não "disfarçada"**: o usuário deixou claro (colando um
exemplo real de grade curricular de escola de inglês) que quer os pontos de
gramática ensinados de forma direta e completa — cada estrutura com suas
formas afirmativa, negativa e interrogativa cobertas no mesmo tópico — e não
costurados dentro de uma narrativa/situação como pretexto. Módulos de
gramática e de vocabulário continuam **separados**, como no outline original
do usuário (não viram módulos temáticos híbridos).

## Restrição técnica

Diferente do curso de Python, o curso de inglês não tem exercícios `code` —
só `quiz`, `text`, `audio` e `speak`. Não há restrição de sandbox aqui: tudo
gira em torno de compreensão e produção de texto/fala, o que roda inteiramente
via TTS/STT do navegador (Web Speech API). Não é necessário o cuidado que o
roteiro de Python tem com "isso não roda no Pyodide" — mas vale manter os
exemplos de frases realistas e o vocabulário de cada nível compatível com o
que já foi ensinado até ali (não usar estrutura gramatical ainda não
apresentada dentro do enunciado de um exercício).

## Padrão de autoria

Curso inteiro num único `app/content/ingles-do-zero.json`, gerado por
`tools/build_ingles.py` (documentado em `tools/README.md`). **Nunca edite o
JSON à mão** — edite o gerador e rode `python tools/build_ingles.py`. Reuse
os helpers já existentes no script (`ex()`, `topic()`, `module()`,
`normalize()`, `is_target_language()` — ver `tools/build_ingles.py:1-52`).

**Decisão técnica da Fase 1 (✅ executada)**: `build_ingles.py` foi migrado
para o padrão incremental de `build_python.py`: um dicionário `BUILDERS`
(slug do módulo -> função que constrói aquele módulo) e uma lista
`TARGET_ORDER` com a ordem final dos 27 slugs do roteiro. Diferente de
Python, aqui não há JSON legado a preservar como base (é reescrita total) —
cada execução reconstrói do zero, a partir do próprio código Python, todos
os módulos que já têm builder; módulos do `TARGET_ORDER` sem builder ainda
simplesmente não aparecem no JSON publicado. `check()` foi ajustado para
exigir mínimo de 5 exercícios/tópico (era 4), consistente com
`tools/README.md`.

Conteúdo do curso atual pode (e deve) ser reaproveitado como ponto de partida
ao escrever os tópicos equivalentes no novo esqueleto — mesmo que os slugs
mudem, o texto das lições e exercícios já existentes é um bom rascunho.

## Regras de validação herdadas (o `check()` do gerador trava antes de escrever)

- tópico com menos de 5 exercícios (regra do `tools/README.md`; o `check()`
  atual de `build_ingles.py` valida ≥4 — ajustar para 5 ao migrar, para ficar
  consistente com a regra documentada);
- alternativas de quiz que colidem depois de normalizadas (`normalize()`
  ignora maiúsculas/pontuação/espaços);
- `solution` que não bate com exatamente uma alternativa de quiz;
- exercício `audio`/`speak` cujo `audio_text` não bate (após normalize) com a
  `solution`;
- `audio_lang="pt-BR"` obrigatório em alternativas de quiz que são teoria em
  português (o `finalize()` já detecta isso automaticamente por maioria de
  palavras em português nas opções — conferir se continua funcionando após a
  migração para o padrão incremental);
- slugs de módulo/tópico duplicados — **dentro do curso e contra os outros 4
  arquivos** de `app/content/*.json` (checagem global, ver `tools/README.md`).

## Granularidade dos tópicos

Cada item alfabetado do outline (a, b, c...) vira **um tópico só**. Um
tópico de gramática cobre a estrutura inteira, incluindo as formas
afirmativa, negativa e interrogativa quando fizer sentido (ex.: o tópico
"Presente Simples" tem exercícios nas três formas, não três tópicos
separados) — mínimo de 5 exercícios por tópico é tranquilo de bater assim.

## Status

| # | Módulo | Nível | Itens | Status |
|---|---|---|---|---|
| 1 | Primeiros Passos (Sobrevivência) | A1 | 15 | ✅ (15 tópicos, 78 exercícios) |
| 2 | Gramática Essencial | A1 | 15 | ✅ (15 tópicos, 90 exercícios) |
| 3 | Vocabulário Básico | A1 | 15 | ✅ (15 tópicos, 90 exercícios) |
| 4 | Comunicação | A1 | 10 | ✅ (10 tópicos, 60 exercícios) |
| 5 | Gramática Essencial | A2 | 15 | ✅ (15 tópicos, 90 exercícios) |
| 6 | Ampliação de Vocabulário | A2 | 15 | ✅ (15 tópicos, 90 exercícios) |
| 7 | Comunicação | A2 | 13 | ✅ (13 tópicos, 78 exercícios) |
| 8 | Gramática Essencial | B1 | 15 | ✅ (15 tópicos, 90 exercícios) |
| 9 | Vocabulário | B1 | 15 | ✅ (15 tópicos, 90 exercícios) |
| 10 | Speaking | B1 | 13 | ✅ (13 tópicos, 78 exercícios) |
| 11 | Listening | B1 | 10 | ✅ (10 tópicos, 60 exercícios) |
| 12 | Gramática Essencial | B2 | 11 | ✅ (11 tópicos, 66 exercícios) |
| 13 | Vocabulário Avançado | B2 | 12 | ✅ (12 tópicos, 72 exercícios) |
| 14 | Inglês Natural | B2 | 12 | ✅ (12 tópicos, 72 exercícios) |
| 15 | Speaking | B2 | 12 | ✅ (12 tópicos, 72 exercícios) |
| 16 | Writing | B2 | 10 | ✅ (10 tópicos, 60 exercícios) |
| 17 | Gramática Avançada | C1 | 13 | ✅ (13 tópicos, 78 exercícios) |
| 18 | Vocabulário Avançado | C1 | 12 | ✅ (12 tópicos, 72 exercícios) |
| 19 | Speaking | C1 | 15 | ✅ (15 tópicos, 90 exercícios) |
| 20 | Listening | C1 | 13 | ✅ (13 tópicos, 78 exercícios) |
| 21 | Reading | C1 | 12 | ✅ (12 tópicos, 72 exercícios) |
| 22 | Writing | C1 | 15 | ✅ (15 tópicos, 90 exercícios) |
| 23 | Inglês para o Trabalho | Aplicado (pós-C1) | 15 | ✅ (15 tópicos, 90 exercícios) |
| 24 | Inglês para Tecnologia | Aplicado (pós-C1) | 14 | ✅ (14 tópicos, 84 exercícios) |
| 25 | Treino de Fluência | Aplicado (pós-C1) | 12 | ✅ (12 tópicos, 72 exercícios) |
| 26 | Domínio C1 (C1 Mastery) | Aplicado (pós-C1) | 14 | ✅ (14 tópicos, 84 exercícios) |
| 27 | Imersão Final | Aplicado (pós-C1) | 10 | ✅ (10 tópicos, 60 exercícios) |

Os **27 módulos já foram construídos** (ver as notas "✅ Construído" abaixo) —
todos com builder em `tools/build_ingles.py` e presentes no JSON publicado.
O detalhamento item a item de cada módulo continua abaixo como referência.

## Detalhamento por módulo

### Nível A1 — sobrevivência

**Módulo 1 — Primeiros Passos (Sobrevivência)**
Alfabeto e pronúncia · Cumprimentos básicos · Apresentando-se · Informações
pessoais · Números · Datas e horas · Países e nacionalidades · Família ·
Cores · Objetos e lugares · Atividades diárias · Perguntas básicas ·
Respostas básicas · Inglês de sala de aula · Inglês de sobrevivência.

> ✅ **Construído** (slug `modulo-01-primeiros-passos`, builder
> `build_modulo_01_primeiros_passos` em `tools/build_ingles.py`): 15 tópicos,
> 78 exercícios (`quiz`/`text`/`audio`/`speak`, sem `code`), todos validados
> por `check()` e por `python -m app.seed`. Nenhuma estrutura além de
> presente simples/verbo to be foi usada nos enunciados. Essa foi também a
> primeira execução do `build_ingles.py` já migrado para o padrão
> incremental (`BUILDERS`/`TARGET_ORDER`) — os outros 26 módulos do
> `TARGET_ORDER` ainda não têm builder e por isso não aparecem no JSON
> publicado.

**Módulo 2 — Gramática Essencial (A1)**
Pronomes pessoais · Verbo To Be (afirmativo/negativo/interrogativo) ·
Adjetivos possessivos · Artigos (a/an/the) · Singular e plural ·
Demonstrativos (this/that/these/those) · There is / There are · Have / Have
got · Presente Simples (afirmativo/negativo/interrogativo) · Advérbios de
frequência · Imperativo · Can / Can't · Preposições básicas · Palavras
interrogativas (question words) · Estrutura básica da frase.

> ✅ **Construído** (slug `modulo-02-gramatica-essencial-a1`, builder
> `build_modulo_02_gramatica_essencial_a1` em `tools/build_ingles.py`): 15
> tópicos, 90 exercícios (`quiz`/`text`/`audio`/`speak`, sem `code`), todos
> validados por `check()` e por `python -m app.seed`. Cada tópico cobre a
> estrutura completa (afirmativo/negativo/interrogativo quando aplicável, sem
> separar por forma). O tópico de question words usa o slug `question-words`
> (o nome em português já existia no curso de russo — `check()` exige slugs
> únicos globalmente). Nenhuma estrutura além de presente simples/verbo to
> be/can foi usada nos enunciados.

**Módulo 3 — Vocabulário Básico**
Família · Casa · Comida · Roupas · Escola · Trabalho · Transporte · Clima ·
Hobbies · Compras · Lugares na cidade · Partes do corpo · Verbos comuns ·
Adjetivos comuns · Expressões do dia a dia.

> ✅ **Construído** (slug `modulo-03-vocabulario-basico`, builder
> `build_modulo_03_vocabulario_basico` em `tools/build_ingles.py`): 15
> tópicos, 90 exercícios (`quiz`/`text`/`audio`/`speak`, sem `code`), todos
> validados por `check()` e por `python -m app.seed`. A família estendida
> (uncle/aunt/cousin/nephew/niece) complementa o tópico de família do Módulo
> 1 sem repetir o conteúdo. Nenhuma estrutura além das já vistas (presente
> simples, to be, can, preposições) foi usada nos enunciados.

**Módulo 4 — Comunicação (A1)**
Apresentando-se · Pedindo informações · Pedindo direções · Pedindo comida ·
Fazendo compras · Falando da família · Falando da rotina · Falando de gostos
e preferências · Fazendo pedidos simples · Entendendo conversas simples.

> ✅ **Construído** (slug `modulo-04-comunicacao-a1`, builder
> `build_modulo_04_comunicacao_a1` em `tools/build_ingles.py`): 10 tópicos,
> 60 exercícios (`quiz`/`text`/`audio`/`speak`, sem `code`), todos validados
> por `check()` e por `python -m app.seed`. Focado em frases prontas e
> microdiálogos (pergunta + resposta). Nenhuma estrutura além das já vistas
> até aqui (presente simples, to be, can, going a partir de "I'd like"/"going
> to" não é usado) foi empregada nos enunciados.

### Nível A2 — elementar

**Módulo 5 — Gramática Essencial (A2)**
Revisão do Presente Simples · Presente Contínuo · Passado Simples · Futuro
com "going to" · Futuro com "will" · Substantivos contáveis e incontáveis ·
Some / Any · Much / Many · A lot of · Must / Have to (obrigação) ·
Comparativo e superlativo · Advérbios de modo · Pronomes objeto · Pronomes
possessivos · Conjunções básicas.

> ✅ **Construído** (slug `modulo-05-gramatica-essencial-a2`, builder
> `build_modulo_05_gramatica_essencial_a2` em `tools/build_ingles.py`): 15
> tópicos, 90 exercícios (`quiz`/`text`/`audio`/`speak`, sem `code`), todos
> validados por `check()` e por `python -m app.seed`. Cada estrutura cobre as
> três formas (afirmativo/negativo/interrogativo) no mesmo tópico. Cuidado
> tomado para não usar nos enunciados estruturas ainda não apresentadas
> (ex.: "going to" só aparece depois do próprio tópico).

> Correção de validação: "Advérbios de modo" (não "advérbios" genérico, para
> não colidir com "advérbios de frequência" do módulo 2). "Must / Have to"
> entra aqui (A2) em vez de ficar amontoado com should/may/might no módulo 8.

**Módulo 6 — Ampliação de Vocabulário (A2)**
Viagem · Profissões · Educação · Saúde · Tecnologia · Entretenimento ·
Relacionamentos · Dinheiro · Compras · Restaurantes · Hotéis · Transporte ·
Natureza · Cidade e interior · Problemas do dia a dia.

> ✅ **Construído** (slug `modulo-06-vocabulario-a2`, builder
> `build_modulo_06_vocabulario_a2` em `tools/build_ingles.py`): 15 tópicos,
> 90 exercícios (`quiz`/`text`/`audio`/`speak`, sem `code`), todos validados
> por `check()` e por `python -m app.seed`. Vocabulário expande os módulos 3
> e 5 (profissões, transporte, compras) sem repetir, e só usa estruturas já
> apresentadas (presente/passado simples, presente contínuo, going to,
> modais can/must, comparativos) nos exemplos e enunciados.

**Módulo 7 — Comunicação (A2)**
Falando sobre o passado · Falando de planos futuros · Descrevendo pessoas ·
Descrevendo lugares · Fazendo convites · Aceitando convites · Recusando
educadamente · Fazendo sugestões · Dando conselhos · Pedindo ajuda · Fazendo
reclamações · Falando de experiências · Expressando opiniões.

> ✅ **Construído** (slug `modulo-07-comunicacao-a2`, builder
> `build_modulo_07_comunicacao_a2` em `tools/build_ingles.py`): 13 tópicos,
> 78 exercícios (`quiz`/`text`/`audio`/`speak`, sem `code`), todos validados
> por `check()` e por `python -m app.seed`. Microdiálogos de situações reais
> usando só a gramática do A1/A2 (presente/passado simples, presente
> contínuo, going to/will, modais can/could/should, there is/are).

### Nível B1 — intermediário

**Módulo 8 — Gramática Essencial (B1)**
Presente Perfeito · Presente Perfeito vs. Passado Simples · Passado Contínuo
· Passado Perfeito · Formas de futuro · Condicional Zero e Primeiro ·
Condicional Segundo · Should / May / Might (conselho e possibilidade) ·
Orações relativas · Gerúndio · Infinitivo · Voz passiva (presente e passado
simples) · Discurso indireto — afirmações · Question tags · Phrasal verbs
comuns.

> ✅ **Construído** (slug `modulo-08-gramatica-essencial-b1`, builder
> `build_modulo_08_gramatica_essencial_b1` em `tools/build_ingles.py`): 15
> tópicos, 90 exercícios (`quiz`/`text`/`audio`/`speak`, sem `code`), todos
> validados por `check()` e por `python -m app.seed`. Cada estrutura cobre
> as três formas no mesmo tópico. Escopo respeitado conforme a nota do
> roteiro: voz passiva e discurso indireto só em presente/passado simples e
> em afirmações (a versão avançada é do Módulo 12).

> Correção de validação: Condicional Zero foi adicionado aqui (faltava no
> outline original). Discurso indireto e voz passiva ficam com escopo restrito
> a afirmações/tempos simples — a versão mais avançada de cada um vive no
> módulo 12 (ver nota lá).

**Módulo 9 — Vocabulário (B1)**
Trabalho · Carreira · Tecnologia · Ciência · Política · Sociedade · Meio
ambiente · Educação · Cultura · Mídia · Negócios · Emoções · Personalidade ·
Relacionamentos · Conceitos abstratos.

> ✅ **Construído** (slug `modulo-09-vocabulario-b1`, builder
> `build_modulo_09_vocabulario_b1` em `tools/build_ingles.py`): 15 tópicos,
> 90 exercícios (`quiz`/`text`/`audio`/`speak`, sem `code`), todos validados
> por `check()` e por `python -m app.seed`. Vocabulário de nível B1; slugs
> que colidiam com o A2 foram diferenciados (trabalho-b1, mundo-digital,
> educacao-e-aprendizado, relacoes-interpessoais). Só usa estruturas já
> apresentadas (presente/passado, presente perfeito, condicional zero/
> primeiro, modais should/must/can) nos enunciados.

**Módulo 10 — Speaking (B1)**
Expressando opiniões · Concordando · Discordando · Explicando ideias ·
Contando histórias · Descrevendo experiências · Dando razões · Comparando
coisas · Construindo argumentos · Dando conselhos · Discutindo problemas ·
Falando de planos · Falando de objetivos.

> ✅ **Construído** (slug `modulo-10-speaking-b1`, builder
> `build_modulo_10_speaking_b1` em `tools/build_ingles.py`): 13 tópicos,
> 78 exercícios (`quiz`/`text`/`audio`/`speak`, sem `code`), todos validados
> por `check()` e por `python -m app.seed`. Cada tópico traz as expressões
> úteis + exercícios de produção (speak). Slugs que colidiam com o A2 foram
> diferenciados (dando-sua-opiniao, aconselhando).

**Módulo 11 — Listening (B1)**
Entendendo fala natural · Sotaques diferentes · Fala reduzida · Fala
conectada · Contrações comuns · Identificando palavras-chave · Entendendo
contexto · Entendendo conversas · Entendendo podcasts · Entendendo vídeos.

> ✅ **Construído** (slug `modulo-11-listening-b1`, builder
> `build_modulo_11_listening_b1` em `tools/build_ingles.py`): 10 tópicos,
> 60 exercícios (`quiz`/`audio` com bastante transcrição, sem `code`), todos
> validados por `check()` e por `python -m app.seed`. Foco em estratégias de
> escuta + prática de transcrição (TTS do navegador).

### Nível B2 — intermediário avançado

**Módulo 12 — Gramática Essencial (B2)**
Presente Perfeito avançado · Terceiro Condicional · Condicionais mistas ·
Modais compostos (must have / should have / can't have) · Estruturas
passivas avançadas (com modais) · Causativo (have/get something done) ·
Discurso indireto — perguntas, imperativos e verbos de citação (suggest,
deny, insist) · Inversão com advérbios negativos (Never have I…) · Orações
relativas e reduzidas (participle clauses) · Gerúndio e infinitivo avançados
· Estruturas de frase complexas.

> ✅ **Construído** (slug `modulo-12-gramatica-essencial-b2`, builder
> `build_modulo_12_gramatica_essencial_b2` em `tools/build_ingles.py`): 11
> tópicos, 66 exercícios (`quiz`/`text`/`audio`/`speak`, sem `code`), todos
> validados por `check()` e por `python -m app.seed`. Continua em espiral o
> discurso indireto (perguntas/imperativos/verbos de citação) e a voz
> passiva (modais/perfeito), sem repetir o escopo do B1.

> Correção de validação: este módulo é a continuação em espiral de discurso
> indireto e voz passiva do módulo 8 — não repetir o mesmo conteúdo, subir o
> nível (perguntas/imperativos/backshift em vez de só afirmações; passiva com
> modais/causativo em vez de só presente/passado simples). A inversão aqui é
> a versão "advérbio negativo"; a versão formal/literária fica pro módulo 17.

**Módulo 13 — Vocabulário Avançado (B2)**
Collocations · Phrasal verbs · Expressões idiomáticas (idioms) · Sinônimos ·
Antônimos · Formação de palavras · Prefixos · Sufixos · Vocabulário
acadêmico · Vocabulário profissional · Registro formal · Registro informal.

> ✅ **Construído** (slug `modulo-13-vocabulario-b2`, builder
> `build_modulo_13_vocabulario_b2` em `tools/build_ingles.py`): 12 tópicos,
> 72 exercícios (`quiz`/`text`/`audio`/`speak`, sem `code`), todos validados
> por `check()` e por `python -m app.seed`. Phrasal verbs/idioms avançados
> sem repetir o escopo do B1 (novos phrasal verbs e idioms).

**Módulo 14 — Inglês Natural (B2)**
Contrações · Fala conectada · Reduções · Entonação · Acentuação (stress) ·
Ritmo · Preenchedores naturais (fillers) · Marcadores de conversa ·
Expressões informais · Gírias (slang) · Idioms comuns · Fraseado natural
(native-like).

> ✅ **Construído** (slug `modulo-14-ingles-natural-b2`, builder
> `build_modulo_14_ingles_natural_b2` em `tools/build_ingles.py`): 12
> tópicos, 72 exercícios (`quiz`/`text`/`audio`/`speak`, sem `code`), todos
> validados por `check()` e por `python -m app.seed`. Aprofunda a
> pronúncia/fluência do B1 (contrações, connected speech, reduções) e traz o
> vocabulário informal/idiomático do B2.

**Módulo 15 — Speaking (B2)**
Debates · Apresentações · Discussões · Negociações · Explicando ideias
complexas · Defendendo uma opinião · Contestando um argumento · Dando
exemplos · Especulando · Formulando hipóteses · Persuadindo · Esclarecendo
mal-entendidos.

> ✅ **Construído** (slug `modulo-15-speaking-b2`, builder
> `build_modulo_15_speaking_b2` em `tools/build_ingles.py`): 12 tópicos,
> 72 exercícios (`quiz`/`text`/`audio`/`speak`, sem `code`), todos validados
> por `check()` e por `python -m app.seed`. Slug `apresentacoes` colidia com
> o A1, então o tópico usa `apresentacoes-orais`.

**Módulo 16 — Writing (B2)**
E-mails formais · E-mails informais · Relatórios · Redações (essays) ·
Argumentação · Resenhas · Resumos · Propostas · Comunicação profissional ·
Fundamentos de escrita acadêmica.

> ✅ **Construído** (slug `modulo-16-writing-b2`, builder
> `build_modulo_16_writing_b2` em `tools/build_ingles.py`): 10 tópicos,
> 60 exercícios (`quiz`/`text`/`audio`/`speak`, sem `code`), todos validados
> por `check()` e por `python -m app.seed`. Cada tópico traz a estrutura do
> gênero textual + frases-chave + exercícios.

### Nível C1 — avançado

**Módulo 17 — Gramática Avançada (C1)**
Condicionais avançados · Inversão formal/literária · Estruturas de ênfase ·
Cleft sentences · Elipse · Substituição · Estruturas passivas avançadas ·
Nominalização · Orações complexas · Orações relativas avançadas · Estruturas
de subjuntivo · Hedging (suavização de afirmações) · Nuance e modalidade.

> ✅ **Construído** (slug `modulo-17-gramatica-avancada-c1`, builder
> `build_modulo_17_gramatica_avancada_c1` em `tools/build_ingles.py`): 13
> tópicos, 78 exercícios (`quiz`/`text`/`audio`/`speak`, sem `code`), todos
> validados por `check()` e por `python -m app.seed`. Os tópicos de hedging e
> nuance têm exercícios focados em discordar com elegância, como o usuário
> pediu (ex.: "I'd venture to say...", "not necessarily").

> É aqui que mora o exemplo que o usuário deu como objetivo do C1: usar
> hedging/nuance pra discordar de alguém sem simplesmente dizer "you're
> wrong" — os tópicos de hedging e nuance devem ter exercícios de speaking/
> quiz centrados exatamente nesse tipo de situação.

**Módulo 18 — Vocabulário Avançado (C1)**
Vocabulário acadêmico · Vocabulário profissional · Vocabulário abstrato ·
Collocations · Expressões idiomáticas · Linguagem metafórica · Sinônimos com
nuance · Registro · Formal vs. informal · Precisão vocabular · Famílias de
palavras · Vocabulário contextual.

> ✅ **Construído** (slug `modulo-18-vocabulario-c1`, builder
> `build_modulo_18_vocabulario_c1` em `tools/build_ingles.py`): 12 tópicos,
> 72 exercícios (`quiz`/`text`/`audio`/`speak`, sem `code`), todos validados
> por `check()` e por `python -m app.seed`. Slugs diferenciados dos do B2
> (academico-avancado, profissional-avancado, collocations-avancadas,
> idioms-avancados, sinonimos-com-nuance, familias-de-palavras-c1).

**Módulo 19 — Speaking (C1)**
Discussões complexas · Debates · Apresentações · Entrevistas · Negociações ·
Persuasão · Pensamento crítico · Temas abstratos · Temas políticos · Questões
sociais · Discussões técnicas · Explicando temas complexos de forma simples ·
Expressando opiniões sutis · Lidando com discordância · Falando
espontaneamente.

> ✅ **Construído** (slug `modulo-19-speaking-c1`, builder
> `build_modulo_19_speaking_c1` em `tools/build_ingles.py`): 15 tópicos,
> 90 exercícios (`quiz`/`text`/`audio`/`speak`, sem `code`), todos validados
> por `check()` e por `python -m app.seed`. Slugs diferenciados dos níveis
> anteriores (debates-c1, apresentacoes-c1, negociacoes-c1, persuasao-c1,
> entrevistas).

**Módulo 20 — Listening (C1)**
Conversas nativas · Fala rápida · Sotaques diferentes · Podcasts ·
Entrevistas · Palestras · Notícias · Filmes · Séries · Conteúdo técnico ·
Humor e sarcasmo · Sentido implícito · Tom e intenção.

> ✅ **Construído** (slug `modulo-20-listening-c1`, builder
> `build_modulo_20_listening_c1` em `tools/build_ingles.py`): 13 tópicos,
> 78 exercícios (`quiz`/`text`/`audio`/`speak`, sem `code`), todos validados
> por `check()` e por `python -m app.seed`. Slugs diferenciados dos do B1
> (conversas-nativas, fala-rapida, sotaques-c1, podcasts-c1, entrevistas-c1,
> noticias-c1, filmes-c1, series-c1).

**Módulo 21 — Reading (C1)**
Notícias · Ensaios · Artigos de opinião · Textos acadêmicos · Documentação
técnica · Literatura · Jornalismo long-form · Documentação profissional ·
Identificando argumentos · Identificando viés · Entendendo sentido implícito
· Entendendo tom.

> ✅ **Construído** (slug `modulo-21-reading-c1`, builder
> `build_modulo_21_reading_c1` em `tools/build_ingles.py`): 12 tópicos,
> 72 exercícios (`quiz`/`text`/`audio`/`speak`, sem `code`), todos validados
> por `check()` e por `python -m app.seed`. Foca em estratégias de leitura +
> vocabulário de gênero (notícia, acadêmico, técnico, literário).

**Módulo 22 — Writing (C1)**
E-mails avançados · Relatórios · Redações (essays) · Propostas · Artigos ·
Resenhas · Escrita técnica · Escrita acadêmica · Escrita persuasiva · Escrita
argumentativa · Edição · Estilo · Coesão · Precisão · Registro.

> ✅ **Construído** (slug `modulo-22-writing-c1`, builder
> `build_modulo_22_writing_c1` em `tools/build_ingles.py`): 15 tópicos,
> 90 exercícios (`quiz`/`text`/`audio`/`speak`, sem `code`), todos validados
> por `check()` e por `python -m app.seed`. Slugs diferenciados dos do B2
> (emails-avancados, relatorios-c1, essays-c1, propostas-c1, resenhas-c1,
> escrita-academica-c1).

### Trilha aplicada (pós-C1) — não introduz gramática nova

**Módulo 23 — Inglês para o Trabalho**
Entrevistas de emprego · Currículo (CV/resume) · LinkedIn · Reuniões ·
Apresentações · E-mails · Comunicação por Slack/Teams · Discussões técnicas ·
Dando status updates · Pedindo esclarecimentos · Explicando problemas ·
Discutindo prazos · Dando feedback · Recebendo feedback · Negociando.

> ✅ **Construído** (slug `modulo-23-ingles-trabalho`, builder
> `build_modulo_23_ingles_trabalho` em `tools/build_ingles.py`): 15 tópicos,
> 90 exercícios (`quiz`/`text`/`audio`/`speak`, sem `code`), todos validados
> por `check()` e por `python -m app.seed`. Trilha aplicada: usa apenas
> estruturas já apresentadas até o C1.

**Módulo 24 — Inglês para Tecnologia**
Vocabulário de programação · Vocabulário de desenvolvimento de software ·
Lendo documentação · GitHub · Stack Overflow · Artigos técnicos · Code
review · Pull requests · Discussões de arquitetura · Vocabulário de system
design · Vocabulário de debugging · Vocabulário de IA · Vocabulário de cloud
· Vocabulário de DevOps.

> ✅ **Construído** (slug `modulo-24-ingles-tecnologia`, builder
> `build_modulo_24_ingles_tecnologia` em `tools/build_ingles.py`): 14
> tópicos, 84 exercícios (`quiz`/`text`/`audio`/`speak`, sem `code`), todos
> validados por `check()` e por `python -m app.seed`. Vocabulário do mundo
> tech, alinhado ao público da plataforma (que já estuda programação).

> Faz sentido priorizar este módulo mais cedo (ou até adiantar alguns
> tópicos dele para logo após o B1/B2): o público da plataforma já estuda
> programação em outros cursos daqui, então "inglês técnico" tem apelo
> imediato. Decisão de ordem fica para quando a Fase 23 for planejada —
> registrado aqui como sugestão, não como mudança de posição no roteiro.

**Módulo 25 — Treino de Fluência**
Pensando em inglês · Evitando tradução mental · Paráfrase · Circunlocução ·
Falando espontaneamente · Recall de vocabulário · Formação automática de
frases · Velocidade de conversa · Pronúncia · Entonação · Velocidade de
escuta · Alternância de contexto.

> ✅ **Construído** (slug `modulo-25-treino-fluencia`, builder
> `build_modulo_25_treino_fluencia` em `tools/build_ingles.py`): 12 tópicos,
> 72 exercícios (`quiz`/`text`/`audio`/`speak`, sem `code`), todos validados
> por `check()` e por `python -m app.seed`. Slugs diferenciados dos do C1
> anterior (espontaneidade-fluencia, pronuncia-fluencia, entonacao-fluencia,
> parafrase-fluencia).

**Módulo 26 — Domínio C1 (C1 Mastery)**
Entendendo nuance · Entendendo sentido implícito · Humor · Sarcasmo ·
Linguagem idiomática · Referências culturais · Registros diferentes ·
Linguagem formal · Linguagem informal · Linguagem profissional · Linguagem
acadêmica · Linguagem persuasiva · Comunicação precisa · Conversa natural.

> ✅ **Construído** (slug `modulo-26-dominio-c1`, builder
> `build_modulo_26_dominio_c1` em `tools/build_ingles.py`): 14 tópicos,
> 84 exercícios (`quiz`/`text`/`audio`/`speak`, sem `code`), todos validados
> por `check()` e por `python -m app.seed`. Slugs diferenciados dos do C1
> anterior (humor-c1, sarcasmo-c1, sentido-implicito-dominio).

**Módulo 27 — Imersão Final**
Ler livros em inglês · Assistir filmes sem legenda · Assistir conteúdo
técnico em inglês · Ouvir podcasts · Escrever todos os dias · Falar todos os
dias · Participar de discussões · Ler documentação técnica · Trabalhar
inteiramente em inglês · Pensar em inglês.

> ✅ **Construído** (slug `modulo-27-imersao-final`, builder
> `build_modulo_27_imersao_final` em `tools/build_ingles.py`): 10 tópicos,
> 60 exercícios (`quiz`/`text`/`audio`/`speak`, sem `code`), todos validados
> por `check()` e por `python -m app.seed`. Fecha a trilha: os 27 módulos do
> roteiro agora têm builder e aparecem no JSON publicado.

## Parecer de validação CEFR

**Veredito geral: o mapeamento por nível está correto e alinhado com grades
curriculares padrão de mercado** (Cambridge/EF/escolas de idiomas) — o
exemplo de A1 que o usuário colou bate com os módulos 1-4 daqui. Correções já
aplicadas na tabela acima:

1. Condicional Zero estava faltando entre o Primeiro (módulo 8) e o Terceiro
   (módulo 12) — adicionado ao módulo 8.
2. "Modal verbs" era um item só, genérico demais — separado em: Must/Have to
   (obrigação, A2/módulo 5), Should/May/Might (conselho e possibilidade,
   B1/módulo 8) e modais compostos (must have/should have/can't have,
   B2/módulo 12).
3. Discurso indireto, voz passiva e inversão aparecem em dois níveis cada
   (B1→B2 e B2→C1) — currículo em espiral, prática normal, mas cada
   ocorrência agora tem escopo explícito registrado no detalhamento do
   módulo para não duplicar conteúdo.
4. "Advérbios" genérico no A2 virou "Advérbios de modo", pra não colidir com
   "advérbios de frequência" do A1.
5. Módulos 23-27 foram rotulados como nível "Aplicado (pós-C1)" em vez de
   forçar uma letra CEFR — são prática do que já foi ensinado, não gramática
   nova.

## Fases de execução sugeridas

Um módulo numerado = uma fase (tamanho razoável de sessão, ~10-15 tópicos).
Os módulos 23-27 podem ser agrupados 2-3 por fase por serem mais enxutos.
Ordem sugerida: segue a numeração 1→27 (A1 até a trilha aplicada), mas pode
mudar a pedido do usuário — por exemplo, adiantar partes do módulo 24
(Inglês para Tecnologia) para logo após o B1, dado o público da plataforma.

Depois de cada fase: rodar `python tools/build_ingles.py`, depois
`python -m app.seed`, subir o app e conferir 1-2 tópicos no navegador antes
de marcar o checkbox e seguir. Não é preciso perguntar permissão para
continuar entre fases — só checar com o usuário se algo no plano parecer
errado.

**Antes da Fase 1** (✅ feito): migrar `build_ingles.py` para o padrão
incremental (ver seção "Padrão de autoria" acima). **As fases 1 a 27 foram
executadas**: todos os módulos do roteiro já têm builder, passaram por
`build_ingles.py` + `python -m app.seed`, e o curso completo está publicado
em `app/content/ingles-do-zero.json`. A validação final confirmou 27 módulos,
353 tópicos e 2106 exercícios carregando e renderizando no app.
