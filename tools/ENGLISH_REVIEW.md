# Revisão de qualidade — Inglês do Zero

Revisão do curso inteiro (27 módulos, 344 tópicos, 3.030 exercícios), pedida em
2026-09-13 depois da revisão do curso de russo (ver `tools/RUSSIAN_REVIEW.md`). O
objetivo é caçar **erros**, não reescrever o curso.

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
7. **Texto quebrado**: frase sem sentido, palavra trocada, lacuna que já contém a resposta.

## Auditoria automática inicial

| Verificação | Resultado |
|---|---|
| Exercícios repetidos no mesmo tópico | 33 |
| Quizzes com alternativa em português lida pela voz inglesa | ~120 |
| Tabelas markdown com colunas desiguais | 0 |
| Blocos de código sem fechamento | 0 |
| Palavras repetidas ("the the") | 0 |
| Aspas curvas/reticências em respostas | 0 |
| Áudio (`audio_text`) diferente da resposta | 0 |

## Correções sistêmicas

- [x] `normalize()` ignora travessão/meia-risca (feito na revisão do russo; vale para todos os cursos).
- [x] `normalize()` ignora aspas curvas e reticências (’ ‘ “ ” …): o teclado do celular troca "don't" por "don’t" e o corretor recusava.
- [x] Voz do 🔊 por alternativa (`runner.js`): em exercício de inglês, alternativa com pista de português (acento ou palavra comum como "não", "que", "ou", "de"), fora dos parênteses de glosa, é lida em pt-BR.
- [ ] `check()` barra exercício repetido no mesmo tópico (mesma regra do russo).

## Revisão manual

Ordem de prioridade (o curso é grande; o que ficar pendente continua marcado aqui):

1. Os 33 exercícios repetidos.
2. Módulos de gramática (2, 5, 8, 12, 17): lição + exercícios.
3. Exercícios dos demais módulos.
4. Lições dos demais módulos.

Legenda: [x] revisado e corrigido · [~] só exercícios revisados · [ ] pendente.

- [ ] M1 — Primeiros passos (sobrevivência) — A1
- [ ] M2 — Gramática essencial — A1
- [ ] M3 — Vocabulário básico — A1
- [ ] M4 — Comunicação — A1
- [ ] M5 — Gramática essencial — A2
- [ ] M6 — Ampliação de vocabulário — A2
- [ ] M7 — Comunicação — A2
- [ ] M8 — Gramática essencial — B1
- [ ] M9 — Vocabulário — B1
- [ ] M10 — Speaking — B1
- [ ] M11 — Listening — B1
- [ ] M12 — Gramática essencial — B2
- [ ] M13 — Vocabulário avançado — B2
- [ ] M14 — Inglês natural — B2
- [ ] M15 — Speaking — B2
- [ ] M16 — Writing — B2
- [ ] M17 — Gramática avançada — C1
- [ ] M18 — Vocabulário avançado — C1
- [ ] M19 — Speaking — C1
- [ ] M20 — Listening — C1
- [ ] M21 — Reading — C1
- [ ] M22 — Writing — C1
- [ ] M23 — Inglês para o trabalho
- [ ] M24 — Inglês para tecnologia
- [ ] M25 — Treino de fluência
- [ ] M26 — Domínio C1
- [ ] M27 — Imersão final

## Pendências conhecidas (não são erros)

- Exercícios de tradução aceitam uma única resposta; "do not" × "don't" ou outra ordem
  válida são recusados. Resolver exige aceitar várias soluções por exercício.
- Módulos 17–27 têm 6 exercícios por tópico (os demais têm 10). Expansão é decisão editorial.
