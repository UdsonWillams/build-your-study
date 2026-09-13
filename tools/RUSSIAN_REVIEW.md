# Revisão de qualidade — Russo do Zero

Revisão do curso inteiro (29 módulos, 153 tópicos, 1305 exercícios), pedida em
2026-09-13 depois de encontrarmos a lição do alfabeto com 11 das 33 letras faltando.
O objetivo é caçar **erros**, não reescrever o curso: conteúdo errado, correção
injusta, voz/teclado trocados, exercícios repetidos e lacunas óbvias nas lições.

Toda correção é feita em `tools/build_russo.py` (nunca no JSON), seguida de
`python tools/build_russo.py` e do seed (`python -m app.seed` com o Python que roda
o servidor).

## O que conta como erro

1. **Conteúdo errado**: regra gramatical, tradução, exemplo ou resposta incorretos.
2. **Correção injusta**: o aluno escreve a forma ensinada e o corretor recusa
   (pontuação, travessão, variante válida não aceita).
3. **Voz ou teclado trocados**: português lido com voz russa (ou o contrário), ou
   teclado cirílico num exercício com resposta em português.
4. **Exercício repetido** no mesmo tópico (mesma pergunta com outra redação).
5. **Romanização**: só nos Módulos 1–2 e sempre no mesmo sistema (abaixo). A partir
   do Módulo 3 o curso é 100% cirílico.
6. **Lacuna óbvia**: regra ensinada pela metade, ou pronúncia traiçoeira sem aviso.
7. **Cobrança antes da hora**: exercício que exige algo que a lição ainda não ensinou.

### Sistema de romanização (Módulos 1–2)

Transliteração simples, letra a letra, igual à usada nos "Exemplos guiados":
я=ya, ю=yu, ё=yo, е=e (ye no início da palavra ou depois de vogal), й=y, ы=y,
х=kh, ж=zh, ш=sh, щ=shch, ц=ts, ч=ch, ь=' (apóstrofo). Ex.: окно = okno,
она = ona, город = gorod, нет = net, есть = yest'. A pronúncia real (о átono
soando "a", consoante final ensurdecida) é ensinada na lição de sons e pelo áudio,
não pela romanização.

## Correções sistêmicas (valem para o curso todo)

- [x] `normalize()` (front-end e geradores) ignora travessão/meia-risca: "Москва — столица России" é aceita.
- [x] Voz do 🔊 de cada alternativa de quiz sai do alfabeto da própria alternativa (`runner.js`), não do exercício inteiro — resolve os 26 quizzes com alternativas mistas.
- [x] `check()` barra exercício repetido no mesmo tópico (quiz: mesma resposta + mesmas alternativas; demais tipos: mesmo tipo + mesma frase de resposta com 2+ palavras).
- [x] `finalize_modules()` força voz pt-BR em exercício `text` cuja resposta não tem cirílico (sem teclado cirílico à toa).
- [x] Auditoria de palavras com alfabetos misturados (letra cirílica em palavra portuguesa ou o contrário, ex.: "Генitivo", "vстал") — zerada no curso todo.

## Revisão manual por módulo

Legenda: [x] revisado e corrigido · notas curtas do que mudou.

- [x] M1 — Alfabeto e primeiros passos · alfabeto com as 33 letras; vogais que amolecem (и não é iotizada); aviso do в mudo em Здравствуйте; exercício repetido trocado.
- [x] M2 — Frases básicas sem o verbo "ser" · romanização padronizada; plural completo (-а→-ы, -я, -ь, -й); exercício repetido trocado.
- [x] M3 — Perguntas e negação · "livro é seu"→"meu"; exercício "да нет" trocado; repetido trocado.
- [x] M4 — Casos: primeiro contato · instrumento sem с (пишу ручкой); 2 repetidos trocados.
- [x] M5 — Vocabulário e comunicação A1 · russo colado no português ("перед", "Генitivo"); exercício "Obrigado!/Por favor!" trocado.
- [x] M6 — Presente dos verbos · verbos em -еть; есть com as 6 pessoas; lacuna sem sentido "Мы ___ есть".
- [x] M7 — Vocabulário e comunicação A2 · lacuna "Я иду ___ с тобой"; "объект direto"; repetido em compras.
- [x] M8 — Casos intermediários · -ия→-ии; на além de "em cima"; -я→-ю no Acusativo; Acusativo plural animado; "(obo)".
- [x] M9 — Aspecto verbal: conceito · буду antecipado na lição; перед сном na lição; repetido de решать.
- [x] M10 — Passado e futuro · "particípio passado"→forma do passado; мог ≠ conseguiu; nomes do subjuntivo; жить regular no passado.
- [x] M11 — Casos avançados · nota "-ые/-ые"; н- dos pronomes após preposição; которого = Acusativo animado (tabela e exercício); "s"→"с".
- [x] M12 — Verbos de movimento · на машине é Preposicional; nota "-ть/-ать" contraditória.
- [x] M13 — Comunicação B1 · "два eventos"; воды × воду; tradução que não batia com o enunciado; repetido.
- [x] M14 — Particípios, gerúndios e discurso indireto · "não há mudança de tempo"→"normalmente".
- [x] M15 — Verbos de movimento prefixados · tabela de prefixos (к não é prefixo); lacuna "в ___ комнату"; repetido; letra cirílica no enunciado.
- [x] M16 — Imperativo e aspecto · "conte"→"convite"; "não +"→"не +"; exercícios que cobravam forma não ensinada.
- [x] M17 — Comparação, pronomes e reflexivos · вставать e отдыхать não são reflexivos (tabela da rotina); "na работу"; alternativa sem sentido "встать нет".
- [x] M18 — Vocabulário e expressões B2 · На здоровье é Acusativo (lição e exercício); сказать não é "говорить + с-"; exercício sobre o по- de понять trocado; tradução literal de бить баклуши; "idiom"→"expressão".
- [x] M19 — Casos em frases complexas · nenhum erro encontrado.
- [x] M20 — Aspecto e nuance · "Ты когда-нибудь...?" costuma pedir imperfectivo; alternativa "два cenários".
- [x] M21 — Registro e estilo · nenhum erro encontrado.
- [x] M22 — Speaking C1 · "М4" com letra cirílica e referência errada; "hedging"/"sutilidade".
- [x] M23 — Listening e reading C1 · "participio" sem acento.
- [x] M24 — Escrita C1 · "vстал"; рассматривается é passiva com -ся, não "de resultado"; "а não"→"e não".
- [x] M25 — Russo para o trabalho · "меня интересует" não é impessoal.
- [x] M26 — Russo para tecnologia · pull request = запрос на слияние.
- [x] M27 — Treino de fluência · marcador 💘→💡; "circumlocução"→"circunlocução".
- [x] M28 — Domínio C1 · "idioms"→"expressões idiomáticas"; 💘→💡.
- [x] M29 — Imersão final · 💘→💡.

## Pendências observadas (não são erros; ficaram fora desta revisão)

- Expandir os Módulos 19–29 (hoje 5–7 exercícios por tópico e lições curtas) para o
  padrão de 10 exercícios dos Módulos 1–18. É decisão editorial separada. Adiado em
  2026-09-13: são ~220 exercícios novos, melhor numa sessão dedicada.
- Exercícios de tradução aceitam uma única ordem de palavras; o russo tem ordem livre, então
  uma resposta correta em outra ordem é recusada. Resolver exigiria aceitar várias soluções.
- Termos em inglês que ainda aparecem nos Módulos 21 e 27 ("chunks", "recall").
- Formas só masculinas em frases-modelo (я хотел бы); uma aluna escreveria хотела бы e
  seria recusada nos exercícios de digitação. Mantido assim por decisão do usuário
  (2026-09-13).
