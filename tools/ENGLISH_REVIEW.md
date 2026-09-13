# Revisão de qualidade — Inglês do Zero

Revisão do curso inteiro (27 módulos, 353 tópicos, 2.950 exercícios), feita em
2026-09-13 depois da revisão do curso de russo (ver `tools/RUSSIAN_REVIEW.md`). O
objetivo foi caçar **erros**, não reescrever o curso.

Toda correção é feita em `tools/build_ingles.py` (nunca no JSON), seguida de
`python tools/build_ingles.py` e do seed (`python -m app.seed` com o Python que roda
o servidor).

## O que conta como erro

1. **Conteúdo errado**: regra gramatical, tradução, exemplo ou resposta incorretos.
2. **Correção injusta**: o aluno escreve a forma ensinada e o corretor recusa.
3. **Voz trocada**: alternativa em português lida com voz inglesa (ou o contrário).
4. **Exercício repetido** no mesmo tópico (mesma pergunta com outra redação).
5. **Lacuna óbvia**: regra ensinada pela metade, tabela incompleta, exceção comum sem aviso.
6. **Cobrança antes da hora**: exercício que exige algo que a lição ainda não ensinou.
7. **Texto quebrado**: frase sem sentido, palavra trocada, dica que entrega a resposta.

## Auditoria automática (curso inteiro)

| Verificação | Encontrado | Situação |
|---|---|---|
| Exercícios repetidos no mesmo tópico | 33 pela regra do russo (parte eram exercícios legítimos de artigo/preposição) + repetidos achados na leitura | corrigidos; `check()` agora barra |
| Quizzes com alternativa em português lida pela voz inglesa | ~120 | resolvido no `runner.js` (voz por alternativa) |
| Dica entre parênteses igual à resposta ("He ___ coffee. (drinks)") | 23 | 16 corrigidos; 7 eram legítimos (dica na forma base: go, heat, be) |
| Quadro de dica quebrado em título "# ===== ... =====" (M19–M27) | 86 linhas | corrigidas |
| Marcador 💘 no lugar de 💡 | 67 | corrigidos |
| Tabelas quebradas, blocos de código abertos, palavras repetidas, aspas curvas em respostas | 0 | — |

## Correções sistêmicas

- [x] `normalize()` ignora travessão/meia-risca (feito na revisão do russo; vale para todos os cursos).
- [x] `normalize()` ignora aspas curvas e reticências (’ ‘ “ ” …): o teclado do celular troca "don't" por "don’t".
- [x] **Contrações**: o corretor aceita a forma longa e a contraída ("I'm a student" = "I am a student", "I'd like" = "I would like", "can't" = "cannot"), sem perder o que já era aceito ("dont" = "don't"). `runner.js` (`sameAnswer`) + `normalize()`/`plain()` nos geradores.
- [x] Voz do 🔊 por alternativa (`runner.js`): alternativa com pista de português (acento ou palavra comum), fora dos parênteses de glosa, é lida em pt-BR.
- [x] `check()` barra exercício repetido no mesmo tópico (quiz: mesmo enunciado; demais tipos: mesmo tipo + mesma frase de resposta com 2+ palavras) e alternativas que empatam em qualquer uma das duas leituras do corretor.

## Revisão manual — concluída

Todos os módulos tiveram lição e exercícios lidos. Principais correções:

- [x] M1 · r final descrito como "gutural"; repetido em datas/horas; enunciado de família.
- [x] M2 · "they" não é "vocês"; o sujeito não se omite; plural em -o; dica dos demonstrativos sem sentido; "no article"; "país"; dica que entregava "drinks".
- [x] M3 · "snow" na lista de adjetivos (→ snowy); "pants, como em português"; dor com "hurt".
- [x] M4 · exemplo contraditório ("caro demais. Vou levar"); 2 repetidos.
- [x] M5 · alternativa "willn't" empatava com "won't"; repetidos em some/any, advérbios e must/have to; "Contável + contável"; dica que entregava "me".
- [x] M6 · 6 repetidos (voo, saudável, tela, teatro, amizade, subúrbio).
- [x] M7 · 3 repetidos (inclusive enunciado idêntico em opiniões).
- [x] M8 · dicas que entregavam been/finished/left/sent/had; tradução sem indicar o gerúndio; repetido em phrasal verbs.
- [x] M9 · "As eleições" esperava singular; fala que pedia uma frase e esperava outra; 5 repetidos.
- [x] M10 · "Ordene e traduza" com palavras já em ordem; "as bright as each other"; 4 repetidos.
- [x] M11 · "close captions"; fala que esperava "uh huh" (reconhecimento de voz não transcreve); tradução que exigia gíria sem avisar; 4 repetidos.
- [x] M12 · lição não ensinava suggest/deny + -ing nem o infinitivo perfeito; dicas sitting/lying; 4 repetidos.
- [x] M13 · 4 repetidos (café forte, abordagem, stakeholder, áudio).
- [x] M14 · "I ___ know" esperando "dunno" (virava "I dunno know"); traduções que exigiam gonna/"up to" sem avisar.
- [x] M15 · "houve um mal-entendido" esperava "there is"; "talvez" aceitava só "perhaps"; 1 repetido.
- [x] M16 · 5 repetidos.
- [x] M17 · "quere"; dicas que entregavam was/do.
- [x] M18 · escala de intensidade trocada (angry abaixo de annoyed; content acima de happy); alternativas quebradas ("aid informal").
- [x] M19 · quadros de dica quebrados; "convencente".
- [x] M20 · quadros quebrados.
- [x] M21 · manchete "Ban Raises Rates" traduzida como "O banco…" (→ Bank); "manchetes omitem verbos" (→ auxiliares); dica que entregava a resposta.
- [x] M22 · "(talento)" esperando "skill"; quadros quebrados.
- [x] M23 · "(10)" sem pedir número por extenso; quadros quebrados.
- [x] M24 · dica que entregava a resposta; quadros quebrados.
- [x] M25 · "tabela" como tradução de *table*; "circumlocução"; 2 dicas que entregavam a resposta.
- [x] M26 · exemplo "That's so 'to Google it'!"; "It could be worse" = "insatisfação disfarçada"; 3 dicas que entregavam a resposta.
- [x] M27 · quadros quebrados.

## Pendências conhecidas (não são erros)

- **Várias traduções válidas**: exercícios de tradução aceitam uma única frase ("I like
  swimming" × "I like to swim", "have dinner" × "eat dinner"). As contrações já são
  aceitas; o resto exigiria uma lista de respostas alternativas por exercício (o campo
  `options`, hoje sem uso em exercícios `text`, poderia guardá-la).
- Módulos 17–27 têm 6 exercícios por tópico (os demais têm 10). Expansão é decisão editorial.
- Alguns tópicos têm pares de exercícios parecidos que a trava não pega (mesma resposta,
  enunciado diferente); não são erro, só reduzem a variedade.
