# Roteiro: Russo do Zero → Fluência (A1 → C1 + trilha aplicada)

Documento vivo, no mesmo espírito de `tools/ENGLISH_ROADMAP.md`. Se você é
uma sessão nova (Claude ou humano) pegando este trabalho do zero: leia isto
inteiro antes de mexer em qualquer coisa.

**Como continuar de onde parou**: veja a seção "Status" abaixo. Todo módulo
já construído tem checkbox marcado. Comece pelo primeiro módulo sem checkbox.

**Todo o conteúdo deste documento (e do curso) é em português (pt-BR)**,
inclusive os nomes dos pontos gramaticais. Só o conteúdo em russo em si
(palavras/frases que o aluno aprende) fica em cirílico — e, nos dois
primeiros módulos, com apoio de romanização (ver "Convenção de
transliteração").

## Contexto

O curso atual (`app/content/russo-do-zero.json`, gerado por
`tools/build_russo.py`) tem 16 módulos e 221 exercícios cobrindo os 6 casos
gramaticais, o aspecto verbal e os verbos de movimento. O problema: cada tema
é aprendido **uma vez só**, num módulo isolado, e nunca mais revisitado. O
aluno chega ao B1 sabendo "o que é o Genitivo", mas trava na hora de
conversar.

**Decisão confirmada com o usuário**: reescrever o curso do zero seguindo um
roteiro novo de **29 módulos**, onde casos/aspecto/verbos de movimento
aparecem cedo (já no Módulo 4, A1) e são revisitados em **pelo menos 3-4
níveis** até o C1 — a mesma lógica de "currículo em espiral" já aplicada ao
curso de inglês (`tools/ENGLISH_ROADMAP.md`). O curso atual é descartado (o
progresso salvo se perde; foi escolha consciente do usuário em troca de uma
estrutura muito mais completa).

**Frase-motivo do usuário** — o objetivo é que o aluno consiga falar algo
como:

> **"Я хотел бы поговорить с тобой о том, что произошло вчера"**
> ("Eu gostaria de conversar com você sobre o que aconteceu ontem")

no B1/B2 **sem travar pensando em qual caso é qual**. Cada peça dessa frase
exige espiral: "со мной" (Instrumental), "о том" (Preposicional), "что
произошло" (aspecto perfectivo no passado). Se o curso entregar essa frase de
cabeça erguida no B2, o desenho funcionou.

## Restrição técnica

Diferente do curso de Python, o curso de russo **não tem exercícios `code`** —
só `quiz`, `text`, `audio` e `speak`. Não há sandbox de execução a considerar.
O que importa é o **teclado cirílico virtual**: o template só mostra o teclado
quando `audio_lang` começa com `"ru"`. Portanto, **todo exercício `text`/`audio`
cuja resposta usa cirílico precisa de `audio_lang` começando com `"ru"`** — o
`check()` trava isso (regra herdada, ver `tools/README.md`).

## Padrão de autoria

Curso inteiro num único `app/content/russo-do-zero.json`, gerado por
`tools/build_russo.py`. **Nunca edite o JSON à mão** — edite o gerador e rode
`python tools/build_russo.py`. Reuse os helpers já existentes (`ex()`,
`topic()`, `module()`, `normalize()`, `CYRILLIC`).

`build_russo.py` está no **padrão antigo** (lista `MODULES.append(...)`
sequencial) e precisa ser **migrado** para o padrão incremental de
`build_python.py`/`build_ingles.py`: um dicionário `BUILDERS`
(slug do módulo -> função construtora) e uma lista `TARGET_ORDER` com a ordem
final dos 29 slugs do roteiro. A cada execução, só os módulos com builder
aparecem no JSON, na posição definida por `TARGET_ORDER`. É reescrita total,
então não há JSON legado a preservar como base (a "base" é o próprio código
Python).

Conteúdo do curso atual **pode (e deve)** ser reaproveitado como ponto de
partida ao escrever os tópicos equivalentes no novo esqueleto — mesmo que os
slugs mudem, o texto das lições e exercícios já existentes é um bom rascunho.

## Regras de validação herdadas (o `check()` do gerador trava antes de escrever)

- tópico com menos de **5 exercícios** (regra do `tools/README.md` — o
  `check()` atual do russo valida ≥4; ajustar para 5 na migração);
- alternativas de quiz que colidem depois de normalizadas (`normalize()`
  ignora maiúsculas/pontuação/espaços);
- `solution` que não bate com exatamente uma alternativa de quiz;
- exercício `audio`/`speak` cujo `audio_text` não bate (após normalize) com a
  `solution`;
- `audio_lang` começando com `"ru"` sempre que a resposta usa cirílico
  (senão o teclado virtual não aparece) — para exercícios `text`/`audio`;
- `audio_lang="pt-BR"` em alternativas de quiz que são teoria em português
  (o `finalize()` detecta isso automaticamente: se nenhuma alternativa tem
  cirílico, é teoria e a voz russa só produziria ruído);
- slugs de módulo/tópico duplicados — **dentro do curso e contra os outros 4
  arquivos** de `app/content/*.json` (sql, lógica, python, inglês) — checagem
  global, ver `tools/README.md`.

## Granularidade dos tópicos

Cada item alfabetado do detalhamento (a, b, c...) vira **um tópico só**.
Mínimo de 5 exercícios por tópico. Tópicos de gramática cobrem a estrutura
inteira no mesmo tópico (não separar por forma em tópicos diferentes).

## Convenção de transliteração (herdada do curso atual)

- **Módulos 1 e 2**: cirílico **+ romanização** lado a lado (a pronúncia
  escrita em letras latinas, tipo "privet"), para o aluno não se afogar logo
  de cara.
- **A partir do Módulo 3**: 100% cirílico, sem romanização — é assim que se
  aprende a ler russo de verdade.

## Diretriz de espiral (importante)

**Não é só responsabilidade dos módulos de gramática de casos/aspecto/
movimento carregar o espiral.** Os módulos de vocabulário/comunicação/speaking
dos níveis B1–C1 devem, quando fizer sentido, usar **frases com lacuna ou
tradução curta que obriguem a escolher o caso ou o aspecto certo** — em vez
de vocabulário isolado sem flexão. Ex.: num tópico de vocabulário B1, uma
lacuna como "Я думаю о ___" (наша семья) força o Preposicional; num tópico de
comunicação B2, uma frase como "Я ___ письмо вчера" (написать/писать) força
a escolha de aspecto. Vocabulário nunca é "palavra solta": vem sempre no
contexto de uma frase que flexiona.

## Status

| # | Módulo | Nível | Itens | Status |
|---|---|---|---|---|
| 1 | Alfabeto e Primeiros Passos | A1 | 5 | ✅ (5 tópicos, 25 exercícios) |
| 2 | Frases Básicas sem o Verbo "Ser" | A1 | 6 | ✅ (5 tópicos, 30 exercícios) |
| 3 | Perguntas e Negação | A1 | 4 | ✅ (4 tópicos, 22 exercícios) |
| 4 | Casos: Primeiro Contato | A1 | 6 | ✅ (6 tópicos, 32 exercícios) |
| 5 | Vocabulário e Comunicação | A1 | 6 | ✅ (6 tópicos, 36 exercícios) |
| 6 | Presente dos Verbos | A2 | 5 | ✅ (5 tópicos, 30 exercícios) |
| 7 | Vocabulário e Comunicação | A2 | 6 | ✅ (6 tópicos, 36 exercícios) |
| 8 | Casos Intermediários | A2 | 6 | ✅ (7 tópicos, 52 exercícios) |
| 9 | Aspecto Verbal: Conceito | B1 | 5 | ✅ (5 tópicos, 26 exercícios) |
| 10 | Passado e Futuro | B1 | 5 | ✅ (5 tópicos, 29 exercícios) |
| 11 | Casos Avançados | B1 | 6 | ✅ (6 tópicos, 36 exercícios) |
| 12 | Verbos de Movimento | B1 | 5 | ✅ (5 tópicos, 30 exercícios) |
| 13 | Comunicação | B1 | 6 | ✅ (6 tópicos, 36 exercícios) |
| 14 | Particípios, Gerúndios e Discurso Indireto | B2 | 6 | ✅ (5 tópicos, 27 exercícios) |
| 15 | Verbos de Movimento com Prefixo | B2 | 5 | ✅ (5 tópicos, 30 exercícios) |
| 16 | Imperativo e Aspecto | B2 | 4 | ✅ (5 tópicos, 30 exercícios) |
| 17 | Comparação, Pronomes e Reflexivos | B2 | 5 | ✅ (5 tópicos, 30 exercícios) |
| 18 | Vocabulário e Expressões | B2 | 6 | ✅ (6 tópicos, 36 exercícios) |
| 19 | Casos em Frases Complexas | C1 | 6 | ✅ (6 tópicos, 35 exercícios) |
| 20 | Aspecto e Nuance | C1 | 5 | ✅ (5 tópicos, 30 exercícios) |
| 21 | Registro e Estilo | C1 | 5 | ✅ (5 tópicos, 30 exercícios) |
| 22 | Speaking | C1 | 5 | ✅ (5 tópicos, 30 exercícios) |
| 23 | Listening e Reading | C1 | 5 | ✅ (5 tópicos, 30 exercícios) |
| 24 | Escrita | C1 | 5 | ✅ (5 tópicos, 30 exercícios) |
| 25 | Russo para o Trabalho | Aplicado (pós-C1) | 5 | ✅ (5 tópicos, 30 exercícios) |
| 26 | Russo para Tecnologia | Aplicado (pós-C1) | 5 | ✅ (5 tópicos, 30 exercícios) |
| 27 | Treino de Fluência | Aplicado (pós-C1) | 5 | ✅ (5 tópicos, 30 exercícios) |
| 28 | Domínio C1 | Aplicado (pós-C1) | 5 | ✅ (5 tópicos, 30 exercícios) |
| 29 | Imersão Final | Aplicado (pós-C1) | 5 | ✅ (5 tópicos, 30 exercícios) |

Os **29 módulos já foram construídos** — todos com builder em
`tools/build_russo.py` e presentes no JSON publicado (153 tópicos, 908
exercícios no total). O detalhamento item a item de cada módulo continua abaixo
como referência.

## Detalhamento por módulo

### Nível A1 — sobrevivência

**Módulo 1 — Alfabeto e Primeiros Passos**
Como o curso funciona (CEFR + espiral) · O alfabeto cirílico · Sons difíceis
(ь/ъ, vogais iotizadas, acento tônico) · Primeiras palavras e saudações ·
Números de 1 a 10.
> Convenção: **cirílico + romanização** neste módulo.

> ✅ **Construído** (slug `modulo-01-alfabeto-e-primeiros-passos`, builder
> `build_modulo_01_alfabeto_e_primeiros_passos` em `tools/build_russo.py`): 5
> tópicos, 25 exercícios (`quiz`/`text`/`audio`/`speak`, sem `code`), todos
> validados por `check()` e por `python -m app.seed`. Foi também a primeira
> execução do `build_russo.py` já migrado para o padrão incremental
> (`BUILDERS`/`TARGET_ORDER`) — os outros 28 módulos do `TARGET_ORDER` ainda
> não têm builder e por isso não aparecem no JSON publicado. Lição do tópico
> 1 já apresenta o currículo em espiral e a frase-motivo do curso
> ("Я хотел бы поговорить с тобой о том, что произошло вчера").

**Módulo 2 — Frases Básicas sem o Verbo "Ser"**
Pronomes pessoais (ты/вы) · Gênero dos substantivos · Frases sem o verbo
"ser/estar" (быть) no presente · Plural básico.
> Convenção: **cirílico + romanização** neste módulo (último com apoio).

**Módulo 3 — Perguntas e Negação**
Palavras interrogativas (кто/что/где/куда/когда/как/почему) · где vs куда ·
Negação com не.

**Módulo 4 — Casos: Primeiro Contato**
> ⚠️ **Nota de calibragem**: este módulo cobre os **6 casos**, mas tem que
> ser **RASO de propósito** — reconhecimento + frases fixas comuns por caso
> (ex.: "в школе" pro Preposicional, "меня зовут" pro Acusativo, "у меня
> есть" pro Genitivo), **sem tabela de declinação completa**. As declinações
> de verdade ficam pros **Módulos 8 (A2, "Casos intermediários")** e **11
> (B1, "Casos avançados")**.
Os 6 casos, de relance · Frases fixas por caso · O mapa da espiral (onde cada
caso será revisitado).

**Módulo 5 — Vocabulário e Comunicação (A1)**
Rotina · Família · Lugares · Comida · Apresentações e pedidos simples.
> Diretriz de espiral: frases fixas já flexionando casos vistos no M4.

### Nível A2 — básico

**Módulo 6 — Presente dos Verbos**
1ª conjugação (-ать/-ять) · 2ª conjugação (-ить) · Verbos irregulares comuns
(хотеть, идти, есть).

**Módulo 7 — Vocabulário e Comunicação (A2)**
Cidade · Viagem · Compras · Restaurante · Pedir, comprar, localizar.
> Diretriz de espiral: frases com lacuna flexionando os casos já vistos.

**Módulo 8 — Casos Intermediários**
> Declinações de verdade começam aqui (a versão completa do M4).
Preposicional (в/на, о/об, lugar e assunto) · Acusativo (objeto direto,
direção, animados) · Genitivo (posse, у+есть, нет, quantidades, из/для/до/
после) · Dativo (objeto indireto, мне нравится, к/по) · Instrumental (meio,
companhia, время) · Plural em todos os casos.

### Nível B1 — intermediário

**Módulo 9 — Aspecto Verbal: Conceito**
Perfectivo vs imperfectivo · Formação (prefixo про-/с-/на-, sufixo) · Escolha
do aspecto no presente e no infinitivo.

**Módulo 10 — Passado e Futuro**
Passado com concordância de gênero (-л/-ла/-ло/-ли) · Futuro simples
(perfectivo) vs composto (быть + infinitivo) · Modo condicional (бы).

**Módulo 11 — Casos Avançados**
Adjetivos e concordância em todos os casos · Pronomes pessoais em todos os
casos · Orações relativas com который nos casos.

**Módulo 12 — Verbos de Movimento**
идти/ходить · ехать/ездить · лететь/летать · плыть/плавать ·
бежать/бегать · unidirecional vs multidirecional.

**Módulo 13 — Comunicação (B1)**
Contar histórias (aspecto + passado) · Opinar · Falar de planos · Pedidos
educados (можно, хотел бы).
> Diretriz de espiral: lacunas forçando caso e aspecto certos.

### Nível B2 — intermediário avançado

**Módulo 14 — Particípios, Gerúndios e Discurso Indireto**
Particípios (причастия: ativos/passivos, longos) · Gerúndios
(деепричастия: -я / -в) · Discurso indireto (что/ли/чтобы, sem backshift).

**Módulo 15 — Verbos de Movimento com Prefixo**
при-/у-/в-/вы-/пере- etc. · Pares perfectivo/imperfectivo com movimento
(прийти/приходить).

**Módulo 16 — Imperativo e Aspecto**
Imperativo (informal/formal, -й/-те) · Imperativo negativo (не) · Escolha de
aspecto no imperativo.

**Módulo 17 — Comparação, Pronomes e Reflexivos**
Comparativo/superlativo (лучше, самый) · Forma curta dos adjetivos ·
Reflexivos (-ся/-сь).

**Módulo 18 — Vocabulário e Expressões (B2)**
Expressões idiomáticas · Colocações com casos · Frases prontas do dia a dia.
> Diretriz de espiral: cada expressão vem com a flexão correta.

### Nível C1 — avançado

**Módulo 19 — Casos em Frases Complexas**
Relativas avançadas (который em todos os casos) · Particípios concordando em
caso · Frases com várias orações.

**Módulo 20 — Aspecto e Nuance**
Escolha sutil do aspecto (processo vs resultado, repetição vs uma vez) ·
Nuance com prefixos · A frase-motivo do curso como exercício final de B1/B2.

**Módulo 21 — Registro e Estilo**
Formal vs informal · Registro escrito vs falado · Estilo e naturalidade.

**Módulo 22 — Speaking (C1)**
Debates · Opiniões sutis · Hipóteses · Recontar a frase-motivo com fluência.

**Módulo 23 — Listening e Reading (C1)**
Entender fala nativa · Notícias · Literatura · Entender aspectos implícitos.

**Módulo 24 — Escrita (C1)**
E-mails · Textos narrativos (aspecto na escrita) · Relatos com casos
precisos.

### Trilha aplicada (pós-C1) — não introduz gramática nova

**Módulo 25 — Russo para o Trabalho**
Entrevistas · Reuniões · E-mails profissionais · Feedback.

**Módulo 26 — Russo para Tecnologia**
Vocabulário técnico · Documentação · Discussões técnicas.

**Módulo 27 — Treino de Fluência**
Pensar em russo · Evitar tradução mental · Circunlocução · Recall.

**Módulo 28 — Domínio C1**
Nuance · Registros · Humor · Expressões idiomáticas avançadas.

**Módulo 29 — Imersão Final**
Ler livros · Filmes sem legenda · Podcasts · Escrever/falar todo dia ·
Trabalhar em russo · Pensar em russo.

## Mapa da espiral

Os três "temas espiral" — casos, aspecto verbal e verbos de movimento — são
visitados em pelo menos 3-4 níveis cada, do A1 ao C1:

| Tema | A1 | A2 | B1 | B2 | C1 |
|---|---|---|---|---|---|
| **Casos** | M4 (primeiro contato raso) | M8 (intermediários: declinações) | M11 (avançados: adjetivos/pronomes/который) | M14 (particípios concordam em caso) | M19 (frases complexas) |
| **Aspecto verbal** | — | M6/M9 (conceito) | M10 (passado/futuro), M13 (narrativa) | M16 (imperativo) | M20 (nuance), M24 (escrita) |
| **Verbos de movimento** | — | M7 (frases fixas) | M12 (básico) | M15 (prefixados) | M20 (figurativo/nuance) |

E os módulos de vocabulário/comunicação/speaking (5, 7, 13, 18, 22...) reforçam
o espiral com frases de lacuna que obrigam a flexionar — ver "Diretriz de
espiral".

## Fases de execução sugeridas

Um módulo numerado = uma fase (tamanho razoável de sessão, 4-6 tópicos).
Módulos 25-29 (trilha aplicada) podem ser agrupados 2-3 por fase por serem
mais enxutos. Ordem sugerida: segue a numeração 1→29.

Depois de cada fase: rodar `python tools/build_russo.py`, depois
`python -m app.seed`, subir o app e conferir 1-2 tópicos no navegador antes
de marcar o checkbox e seguir. Não é preciso perguntar permissão para
continuar entre fases — só checar com o usuário se algo no plano parecer
errado.

**Antes da Fase 1**: migrar `build_russo.py` para o padrão incremental
(`BUILDERS`/`TARGET_ORDER`) e criar este roteiro. **As fases 1 a 29 foram
executadas**: todos os módulos do roteiro já têm builder, passaram por
`build_russo.py` + `python -m app.seed`, e o curso completo está publicado em
`app/content/russo-do-zero.json` (29 módulos, 153 tópicos, 908 exercícios). A
validação final confirmou o carregamento e a renderização no app.
