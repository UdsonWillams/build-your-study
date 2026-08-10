# -*- coding: utf-8 -*-
"""Gera/expande app/content/python-do-zero.json a partir de uma estrutura Python.

Mesma ideia de build_russo.py/build_ingles.py (ver tools/README.md), com uma
diferença: em vez de reconstruir o curso do zero, este script **carrega o JSON
atual como base** e só insere os módulos da fase em andamento nas posições
certas — os módulos já existentes (e os slugs de quem já tem progresso salvo)
ficam intactos. O plano completo de expansão do curso está em
tools/PYTHON_ROADMAP.md.
"""
import contextlib
import io
import json
import re
from pathlib import Path

CONTENT_DIR = Path(__file__).resolve().parent.parent / "app" / "content"
OUT_PATH = CONTENT_DIR / "python-do-zero.json"


# ============================================================
# Helpers de autoria (mesmo padrão dos outros geradores)
# ============================================================

def normalize(s):
    """Espelha normalize() de web/static/js/runner.js."""
    s = s.lower().replace("ё", "е")
    s = re.sub(r"[.,!?;:'\"-]", "", s)
    return re.sub(r"\s+", " ", s).strip()


def quiz(prompt, solution, options):
    return {"type": "quiz", "prompt": prompt, "solution": solution, "options": options}


def text(prompt, solution):
    return {"type": "text", "prompt": prompt, "solution": solution}


def code(prompt, solution, test_code, starter_code=""):
    return {
        "type": "code",
        "prompt": prompt,
        "solution": solution,
        "test_code": test_code,
        "starter_code": starter_code or "# escreva seu código aqui\n",
    }


def topic(slug, title, lesson_md, exercises):
    return {"slug": slug, "title": title, "lesson_md": lesson_md.strip(), "exercises": exercises}


def module(slug, title, summary, topics):
    return {"slug": slug, "title": title, "summary": summary, "topics": topics}


# ============================================================
# Validacao (roda ANTES de escrever qualquer coisa)
# ============================================================

def _validate_code_exercise(ex, loc):
    """Roda solution + test_code de verdade — mesmo mecanismo do app/seed.py
    (_validate_code_exercise), pra pegar bug de autoria antes de rodar o app."""
    ns = {"_student_code": ex["solution"]}
    try:
        with contextlib.redirect_stdout(io.StringIO()):
            exec(ex["solution"], ns)
            exec(ex["test_code"], ns)
    except Exception as e:
        return [f"{loc}: code invalido ({type(e).__name__}: {e})"]
    return []


def check(modules, active_module_slugs):
    """Trava erros de autoria antes de gravar o JSON.

    `active_module_slugs`: módulos sendo escritos/tocados NESTA fase — só
    eles precisam cumprir o mínimo de 5 exercícios/tópico. Módulos legados
    ainda não migrados (outras fases do roteiro) só passam pela validação
    estrutural (quiz/code), sem travar a build por uma meta que ainda não é
    a fase deles.
    """
    problems = []
    topic_slugs = []
    module_slugs = []

    for m in modules:
        module_slugs.append(m["slug"])
        for t in m["topics"]:
            topic_slugs.append(t["slug"])
            loc_base = f"{m['slug']}/{t['slug']}"
            # Tópicos sem a chave "exercises" são intencionalmente só de leitura
            # (padrão já usado no módulo "Hello World" existente) — só valida o
            # mínimo de 5 quando a chave existe e o módulo é da fase atual.
            if m["slug"] in active_module_slugs and "exercises" in t and len(t["exercises"]) < 5:
                problems.append(f"{loc_base}: só {len(t['exercises'])} exercícios (mínimo 5)")
            for i, e in enumerate(t.get("exercises", [])):
                loc = f"{loc_base} #{i}"
                etype = e.get("type", "code")
                if not e.get("solution") and etype != "code":
                    problems.append(f"{loc}: solution vazia")
                if etype == "quiz":
                    opts = e.get("options") or []
                    norms = [normalize(o) for o in opts]
                    if len(set(norms)) != len(norms):
                        problems.append(f"{loc}: alternativas ambíguas após normalize: {opts}")
                    if norms.count(normalize(e["solution"])) != 1:
                        problems.append(f"{loc}: solution não bate com exatamente 1 alternativa: {opts}")
                if etype == "code":
                    problems.extend(_validate_code_exercise(e, loc))

    if len(set(topic_slugs)) != len(topic_slugs):
        dupes = {s for s in topic_slugs if topic_slugs.count(s) > 1}
        problems.append(f"slugs de tópico duplicados dentro do curso: {dupes}")
    if len(set(module_slugs)) != len(module_slugs):
        dupes = {s for s in module_slugs if module_slugs.count(s) > 1}
        problems.append(f"slugs de módulo duplicados dentro do curso: {dupes}")

    # Slugs precisam ser únicos em TODO o banco (índice único em models.py),
    # não só dentro deste curso — checa contra os outros 4 arquivos.
    for path in CONTENT_DIR.glob("*.json"):
        if path.name == OUT_PATH.name:
            continue
        other = json.loads(path.read_text(encoding="utf-8"))
        other_slugs = {other["slug"]}
        for m in other.get("modules", []):
            other_slugs.add(m["slug"])
            for t in m.get("topics", []):
                other_slugs.add(t["slug"])
        collisions = (set(module_slugs) | set(topic_slugs)) & other_slugs
        if collisions:
            problems.append(f"slugs colidindo com {path.name}: {collisions}")

    return problems


# ============================================================
# MODULO 1 - Logica de Programacao (novo, Fase 1 do roteiro)
# ============================================================

def build_modulo_logica():
    return module(
        "logica-de-programacao-hero",
        "Módulo 1 — Lógica de Programação",
        "Pensar como um programador antes de escrever a primeira linha de Python: algoritmos, como o computador executa instruções, os 3 pilares da lógica e pseudocódigo.",
        [
            topic(
                "algoritmos-passo-a-passo",
                "O que é um algoritmo?",
                """
# O que é um algoritmo?

Um **algoritmo** é uma sequência finita e bem definida de passos para resolver
um problema. Antes de aprender a sintaxe de qualquer linguagem, você precisa
aprender a pensar em passos — é isso que separa "eu sei o que eu quero" de
"eu sei como fazer o computador entender o que eu quero".

## As 3 características que um algoritmo precisa ter

- **Finito**: tem que terminar em algum momento. Um algoritmo que nunca para
  não resolve problema nenhum.
- **Preciso (sem ambiguidade)**: cada passo tem que ser claro o suficiente
  para ser seguido sem interpretação. "Coloque um pouco de sal" não é preciso;
  "coloque 1 colher de chá de sal" é.
- **Executável**: cada passo precisa ser algo que dá pra fazer de verdade, com
  os recursos disponíveis.

## Exemplo do dia a dia: trocar uma lâmpada

1. Desligue o interruptor.
2. Pegue uma lâmpada nova.
3. Retire a lâmpada queimada.
4. Coloque a lâmpada nova.
5. Ligue o interruptor.

Repare: os passos estão em **ordem**, são **claros** e o processo **termina**.
Isso é um algoritmo — programar é basicamente traduzir algoritmos como esse
para uma linguagem que o computador entende.

> 💡 Antes de escrever qualquer código, tente descrever o problema em passos,
> em português mesmo. Se você não consegue explicar o passo a passo, também
> não vai conseguir programá-lo.
""",
                [
                    quiz(
                        "Qual característica um algoritmo PRECISA ter?",
                        "Ser finito (terminar em algum momento)",
                        ["Ser finito (terminar em algum momento)", "Ser escrito em Python", "Ter pelo menos 10 passos"],
                    ),
                    quiz(
                        "Qual das opções abaixo é um algoritmo bem definido?",
                        "Uma receita com passos numerados e quantidades exatas",
                        ["Uma receita com passos numerados e quantidades exatas", "Uma foto do prato pronto", "A frase \"cozinhe até ficar bom\""],
                    ),
                    quiz(
                        "\"Coloque um pouco de açúcar\" NÃO é um bom passo de algoritmo porque:",
                        "É ambíguo — não diz exatamente quanto",
                        ["É ambíguo — não diz exatamente quanto", "É longo demais", "Usa uma palavra em português"],
                    ),
                    quiz(
                        "Um algoritmo que roda para sempre, sem nunca terminar, falha em qual característica?",
                        "Ser finito",
                        ["Ser finito", "Ser preciso", "Ser executável"],
                    ),
                    text(
                        "Complete a frase: programar é basicamente traduzir ___ para uma linguagem que o computador entende.",
                        "algoritmos",
                    ),
                ],
            ),
            topic(
                "como-o-computador-executa",
                "Como o computador executa um programa",
                """
# Como o computador executa um programa

Você escreve código em Python, mas o computador só entende uma coisa: **sinais
elétricos representados como 0s e 1s** (binário). Entender essa distância
ajuda a entender por que certas coisas em programação funcionam do jeito que
funcionam.

## Código-fonte, tradução e execução

- **Código-fonte**: o que você escreve (`print("Olá")`).
- **Tradução**: algo converte esse texto para instruções que o processador
  entende. Existem dois jeitos principais de fazer isso:
  - **Compilar**: traduz o programa inteiro de uma vez, antes de rodar,
    gerando um arquivo executável (comum em C, Go, Rust).
  - **Interpretar**: traduz e executa linha por linha, na hora (comum em
    Python, JavaScript).
- **Execução**: o processador (CPU) executa as instruções traduzidas, uma
  atrás da outra, bilhões de vezes por segundo.

## Python é interpretado

Isso tem um efeito prático: você roda um arquivo `.py` e ele já executa, sem
precisar de um passo separado de "compilação". É um dos motivos de Python ser
tão popular para aprender — o ciclo de "escrever → testar" é bem rápido.

> 🎯 Não se preocupe em decorar os detalhes técnicos agora — o que importa é a
> ideia geral: seu código em português-com-sintaxe vira instruções bem mais
> simples e diretas que o processador consegue seguir.
""",
                [
                    quiz(
                        "O processador (CPU) entende diretamente qual tipo de instrução?",
                        "Instruções binárias (0s e 1s)",
                        ["Instruções binárias (0s e 1s)", "Código Python diretamente", "Português"],
                    ),
                    quiz(
                        "Qual a diferença central entre compilar e interpretar?",
                        "Compilar traduz tudo antes de rodar; interpretar traduz e executa linha por linha",
                        ["Compilar traduz tudo antes de rodar; interpretar traduz e executa linha por linha", "Só compiladores existem de verdade", "Interpretar é mais rápido em todos os casos"],
                    ),
                    quiz(
                        "Python é uma linguagem:",
                        "Interpretada",
                        ["Interpretada", "Só compilada", "Que roda direto em binário sem tradução"],
                    ),
                    quiz(
                        "O que é \"código-fonte\"?",
                        "O texto que você escreve numa linguagem de programação",
                        ["O texto que você escreve numa linguagem de programação", "O arquivo binário final", "Um tipo de erro"],
                    ),
                    text(
                        "Qual sigla representa o \"cérebro\" do computador que executa as instruções? (3 letras)",
                        "cpu",
                    ),
                ],
            ),
            topic(
                "sequencia-decisao-repeticao",
                "Os 3 pilares da lógica: sequência, decisão e repetição",
                """
# Os 3 pilares da lógica: sequência, decisão e repetição

Por trás de **toda** linguagem de programação que existe (Python, JavaScript,
C, Java...) tem só **3 estruturas básicas** controlando o fluxo de um
programa. Aprender a reconhecer essas 3 é a base de tudo.

## 1. Sequência

Passos executados **um depois do outro**, na ordem em que aparecem.

```
1. Pegue os ingredientes
2. Misture
3. Asse
```

## 2. Decisão (seleção)

O programa escolhe um caminho diferente **dependendo de uma condição**.

```
SE está chovendo ENTÃO
    leve guarda-chuva
SENÃO
    não leve
```

## 3. Repetição (iteração)

Um mesmo bloco de passos se repete **enquanto** (ou **até que**) uma condição
seja satisfeita.

```
ENQUANTO tiver louça suja
    lave um prato
```

> 🎯 Qualquer programa, por mais complexo que pareça, é feito combinando essas
> 3 estruturas. Quando você for aprender `if`, `for` e `while` em Python (já
> já!), vai estar só colocando um nome de sintaxe nessas mesmas 3 ideias.
""",
                [
                    quiz(
                        "\"Leia o nome, depois leia a idade, depois mostre os dois\" usa qual estrutura?",
                        "Sequência",
                        ["Sequência", "Decisão", "Repetição"],
                    ),
                    quiz(
                        "\"SE idade >= 18 ENTÃO pode dirigir SENÃO não pode\" usa qual estrutura?",
                        "Decisão",
                        ["Decisão", "Sequência", "Repetição"],
                    ),
                    quiz(
                        "\"ENQUANTO houver e-mails na caixa, leia um e-mail\" usa qual estrutura?",
                        "Repetição",
                        ["Repetição", "Decisão", "Sequência"],
                    ),
                    quiz(
                        "Quantas estruturas básicas de controle de fluxo existem, segundo a lição?",
                        "3",
                        ["3", "5", "10"],
                    ),
                    quiz(
                        "Um programa complexo, com centenas de linhas, é construído combinando:",
                        "As 3 estruturas básicas repetidas e combinadas de várias formas",
                        ["As 3 estruturas básicas repetidas e combinadas de várias formas", "Estruturas totalmente diferentes para cada programa", "Só sequência, sem decisão nem repetição"],
                    ),
                ],
            ),
            topic(
                "variaveis-e-dados-conceito",
                "Variáveis e dados (o conceito, antes da sintaxe)",
                """
# Variáveis e dados (o conceito, antes da sintaxe)

Antes de aprender **como** criar uma variável em Python (isso vem no Módulo
3), vale entender **o que** uma variável é, de forma independente de
linguagem.

## Variável é uma caixa com etiqueta

Pense numa caixa de papelão com uma etiqueta escrita "idade". Dentro dela você
guarda um valor, por exemplo `25`. Sempre que o programa precisar da idade,
ele olha dentro dessa caixa — e se o valor mudar, é só trocar o que está
dentro, sem trocar a etiqueta.

```
CAIXA nome  <- "Ana"
CAIXA idade <- 25
```

## Por que isso é útil

- Permite **guardar** um valor para usar depois.
- Permite **reutilizar** o mesmo valor várias vezes sem repeti-lo.
- Permite que o valor **mude** ao longo da execução (ex.: um contador que vai
  aumentando).

## Tipos de dado, de forma geral

Toda variável guarda um valor de um certo **tipo**: um número, um texto, um
valor verdadeiro/falso, ou uma coleção de outros valores. Cada linguagem tem
seus próprios nomes para esses tipos — em Python você vai ver `int`, `float`,
`str`, `bool` no Módulo 3.

> 💡 Um bom nome de variável **descreve o que ela guarda**. `idade` é bom;
> `x` ou `coisa1` não diz nada sobre o que está lá dentro.
""",
                [
                    quiz(
                        "A melhor analogia para uma variável, segundo a lição, é:",
                        "Uma caixa com etiqueta guardando um valor",
                        ["Uma caixa com etiqueta guardando um valor", "Um algoritmo completo", "Um tipo de erro"],
                    ),
                    quiz(
                        "Qual a vantagem de usar variáveis em vez de repetir o valor toda vez?",
                        "Permite reutilizar e trocar o valor sem mudar o resto do programa",
                        ["Permite reutilizar e trocar o valor sem mudar o resto do programa", "Deixa o programa mais lento de propósito", "É a única forma de escrever texto"],
                    ),
                    quiz(
                        "Qual desses é um BOM nome de variável para guardar o preço de um produto?",
                        "preco",
                        ["preco", "x", "coisa1"],
                    ),
                    quiz(
                        "O valor guardado numa variável pode mudar ao longo da execução do programa?",
                        "Sim, é justamente pra isso que ela serve",
                        ["Sim, é justamente pra isso que ela serve", "Não, uma vez definido nunca muda", "Só se o programa for reiniciado"],
                    ),
                    text(
                        "Complete: toda variável guarda um valor de um certo ___.",
                        "tipo",
                    ),
                ],
            ),
            topic(
                "entrada-e-saida-conceito",
                "Entrada e saída (o conceito)",
                """
# Entrada e saída (o conceito)

Praticamente todo programa útil segue um padrão: **recebe dados, processa, e
devolve um resultado**. Essas duas pontas têm nome:

- **Entrada (input)**: dado que chega de fora para dentro do programa — o que
  o usuário digita, um arquivo lido, uma resposta de sensor, um clique.
- **Saída (output)**: o que o programa devolve para fora — texto na tela, um
  arquivo salvo, um som, um comando enviado a outro sistema.

```
[Entrada] -> [Processamento] -> [Saída]

Ex.: você digita 2 números  ->  o programa soma  ->  mostra o resultado
```

## Exemplos do dia a dia

| Situação | Entrada | Processamento | Saída |
|---|---|---|---|
| Caixa eletrônico | senha digitada | verificar se está correta | liberar ou negar acesso |
| Termômetro digital | temperatura captada | converter para °C | mostrar no visor |
| App de música | você aperta "play" | localizar a música | tocar o áudio |

> 🎯 Quando você for descrever um problema para programar, uma boa primeira
> pergunta é sempre: "qual é a entrada, e qual é a saída esperada?". Isso já
> organiza metade do raciocínio.
""",
                [
                    quiz(
                        "O que é \"entrada\" (input) num programa?",
                        "Dado que chega de fora para dentro do programa",
                        ["Dado que chega de fora para dentro do programa", "O resultado final mostrado ao usuário", "Um erro de execução"],
                    ),
                    quiz(
                        "Num caixa eletrônico, qual das opções é uma SAÍDA?",
                        "Liberar ou negar o acesso",
                        ["Liberar ou negar o acesso", "A senha digitada", "O cartão inserido"],
                    ),
                    quiz(
                        "Qual pergunta a lição sugere fazer primeiro ao encarar um problema novo?",
                        "Qual é a entrada e qual é a saída esperada?",
                        ["Qual é a entrada e qual é a saída esperada?", "Quantas linhas de código isso vai ter?", "Qual a cor do texto na tela?"],
                    ),
                    quiz(
                        "Mostrar um resultado na tela é um exemplo de:",
                        "Saída",
                        ["Saída", "Entrada", "Nem entrada nem saída"],
                    ),
                    text(
                        "Complete o padrão: [Entrada] -> [Processamento] -> [___]",
                        "saída",
                    ),
                ],
            ),
            topic(
                "operadores-conceito",
                "Operadores (o conceito)",
                """
# Operadores (o conceito)

**Operadores** são símbolos que combinam ou comparam valores para produzir um
resultado. Você já usa isso na matemática do dia a dia — programação só dá
nomes mais formais para as categorias.

## As 3 grandes categorias

- **Aritméticos**: fazem contas — somar, subtrair, multiplicar, dividir.
  Ex.: `preço + frete`.
- **Relacionais (comparação)**: comparam dois valores e o resultado é sempre
  verdadeiro ou falso. Ex.: "a idade é maior que 18?".
- **Lógicos**: combinam resultados verdadeiro/falso entre si. Ex.: "está
  chovendo **e** está frio?".

## Precedência (ordem das operações)

Assim como na matemática da escola, operadores têm uma ordem de prioridade —
multiplicação e divisão acontecem antes de soma e subtração, a menos que você
use parênteses para mudar isso:

```
2 + 3 * 4   =  2 + 12  =  14   (multiplicação primeiro)
(2 + 3) * 4 =  5 * 4   =  20   (parênteses mudam a ordem)
```

> 💡 Na dúvida sobre a ordem, use parênteses — deixa a intenção clara tanto
> para o computador quanto para quem for ler seu código depois (inclusive
> você mesmo, no futuro!).
""",
                [
                    quiz(
                        "\"Idade maior que 18?\" é um exemplo de operador:",
                        "Relacional",
                        ["Relacional", "Aritmético", "Lógico"],
                    ),
                    quiz(
                        "\"Está chovendo E está frio\" combina dois resultados verdadeiro/falso — isso é um operador:",
                        "Lógico",
                        ["Lógico", "Aritmético", "Relacional"],
                    ),
                    quiz(
                        "Qual o resultado de 2 + 3 * 4, seguindo a ordem normal de precedência?",
                        "14",
                        ["14", "20", "9"],
                    ),
                    quiz(
                        "O que fazer quando não se tem certeza da ordem de um cálculo?",
                        "Usar parênteses para deixar claro",
                        ["Usar parênteses para deixar claro", "Escrever a conta em outra linha", "Ignorar, o computador sempre acerta sozinho"],
                    ),
                    quiz(
                        "Um operador relacional (como \"maior que\") sempre resulta em:",
                        "Verdadeiro ou falso",
                        ["Verdadeiro ou falso", "Um número", "Um texto"],
                    ),
                ],
            ),
            topic(
                "condicionais-em-pseudocodigo",
                "Estruturas condicionais em pseudocódigo",
                """
# Estruturas condicionais em pseudocódigo

**Pseudocódigo** é escrever um algoritmo numa linguagem quase natural, sem se
prender à sintaxe exata de Python (ou qualquer outra linguagem) — serve para
planejar o raciocínio antes de codar.

## SE / SENÃO

```
SE nota >= 7 ENTÃO
    ESCREVER "Aprovado"
SENÃO
    ESCREVER "Reprovado"
```

## Fazendo um "dry run" (executar na cabeça, passo a passo)

Ler pseudocódigo e prever o que ele faz é um exercício essencial. Vamos
praticar com este:

```
LER idade
SE idade >= 18 ENTÃO
    ESCREVER "Pode dirigir"
SENÃO
    ESCREVER "Não pode dirigir"
```

Se `idade` for `20`: a condição `20 >= 18` é verdadeira, então o programa
escreve **"Pode dirigir"**. Se `idade` for `15`: a condição é falsa, então cai
no `SENÃO` e escreve **"Não pode dirigir"**.

> 🎯 Treinar esse "dry run" — seguir o pseudocódigo linha por linha, à mão,
> anotando o que cada variável vale — é uma das habilidades mais úteis que
> existem para debugar código de verdade depois.
""",
                [
                    quiz(
                        "No pseudocódigo do exemplo, se idade = 20, o que é escrito?",
                        "Pode dirigir",
                        ["Pode dirigir", "Não pode dirigir", "Nada é escrito"],
                    ),
                    quiz(
                        "No mesmo pseudocódigo, se idade = 10, o que é escrito?",
                        "Não pode dirigir",
                        ["Não pode dirigir", "Pode dirigir", "Erro"],
                    ),
                    quiz(
                        "O que é fazer um \"dry run\" de um pseudocódigo?",
                        "Seguir o código linha por linha, à mão, prevendo o resultado",
                        ["Seguir o código linha por linha, à mão, prevendo o resultado", "Rodar o código de verdade no computador", "Apagar o código e escrever de novo"],
                    ),
                    quiz(
                        "Dado \"SE nota >= 7 ENTÃO Aprovado SENÃO Reprovado\", qual o resultado para nota = 7?",
                        "Aprovado",
                        ["Aprovado", "Reprovado", "Depende de outra condição"],
                    ),
                    quiz(
                        "Por que vale a pena escrever pseudocódigo antes de programar de verdade?",
                        "Ajuda a organizar o raciocínio sem se preocupar com sintaxe ainda",
                        ["Ajuda a organizar o raciocínio sem se preocupar com sintaxe ainda", "Porque o computador executa pseudocódigo direto", "Porque é obrigatório em toda linguagem"],
                    ),
                ],
            ),
            topic(
                "repeticao-em-pseudocodigo",
                "Estruturas de repetição em pseudocódigo",
                """
# Estruturas de repetição em pseudocódigo

## ENQUANTO (repete enquanto uma condição for verdadeira)

```
contador <- 1
ENQUANTO contador <= 3 FAÇA
    ESCREVER contador
    contador <- contador + 1
```

Vamos fazer o dry run: `contador` começa em `1`. A condição `1 <= 3` é
verdadeira, então escreve `1` e `contador` vira `2`. De novo: `2 <= 3` é
verdadeira, escreve `2`, `contador` vira `3`. De novo: `3 <= 3` é verdadeira,
escreve `3`, `contador` vira `4`. Agora `4 <= 3` é **falsa** — o laço para.
Saída: `1`, `2`, `3`.

## O perigo do loop infinito

Se você esquecer de atualizar a variável que a condição depende (o
`contador <- contador + 1` no exemplo), a condição nunca fica falsa — e o
programa repete para sempre. Todo `ENQUANTO` precisa de um jeito de,
eventualmente, tornar a condição falsa.

## PARA (repete um número já conhecido de vezes)

```
PARA i DE 1 ATÉ 5 FAÇA
    ESCREVER i
```

Isso escreve `1, 2, 3, 4, 5` — usado quando você já sabe de antemão quantas
vezes quer repetir, ao contrário do `ENQUANTO`, que repete até uma condição
mudar (não necessariamente um número fixo de vezes).
""",
                [
                    quiz(
                        "No dry run do pseudocódigo com ENQUANTO, quais valores são escritos?",
                        "1, 2, 3",
                        ["1, 2, 3", "1, 2, 3, 4", "0, 1, 2"],
                    ),
                    quiz(
                        "O que causa um \"loop infinito\"?",
                        "A condição do ENQUANTO nunca se torna falsa",
                        ["A condição do ENQUANTO nunca se torna falsa", "Usar PARA em vez de ENQUANTO", "Escrever ESCREVER duas vezes"],
                    ),
                    quiz(
                        "Qual estrutura você usaria quando já sabe exatamente quantas vezes quer repetir?",
                        "PARA",
                        ["PARA", "ENQUANTO", "SE"],
                    ),
                    quiz(
                        "\"PARA i DE 1 ATÉ 5 FAÇA ESCREVER i\" escreve quais valores?",
                        "1, 2, 3, 4, 5",
                        ["1, 2, 3, 4, 5", "1, 2, 3, 4", "0 até 5"],
                    ),
                    text(
                        "No exemplo do ENQUANTO, qual linha impede o loop infinito, atualizando a variável da condição?",
                        "contador <- contador + 1",
                    ),
                ],
            ),
            topic(
                "funcoes-conceito-e-desafios",
                "Funções (o conceito) e desafios de lógica",
                """
# Funções (o conceito) e desafios de lógica

## Função: uma "máquina" reutilizável

Pense numa função como uma máquina: você coloca algo dentro (a **entrada**,
também chamada de **parâmetro**), ela processa, e devolve um resultado (a
**saída**, também chamada de **retorno**).

```
FUNÇÃO dobro(numero)
    RETORNAR numero * 2

dobro(5)   ->  10
dobro(10)  ->  20
```

A grande vantagem: você define a lógica **uma vez** e reutiliza quantas vezes
quiser, com entradas diferentes, sem copiar e colar o mesmo bloco de código
repetidamente. Isso tem até um nome: o princípio **DRY** (*Don't Repeat
Yourself* — não se repita).

## Desafios de lógica (revisão do módulo)

Hora de juntar tudo: sequência, decisão, repetição, variáveis, operadores e
funções — todos fazem parte do raciocínio por trás de qualquer programa, não
importa a linguagem. No próximo módulo você vai preparar o ambiente, e no
Módulo 3 vai finalmente aplicar tudo isso escrevendo Python de verdade.
""",
                [
                    quiz(
                        "Na analogia da máquina, o que entra numa função é chamado de:",
                        "Parâmetro (entrada)",
                        ["Parâmetro (entrada)", "Retorno", "Algoritmo"],
                    ),
                    quiz(
                        "O que uma função devolve é chamado de:",
                        "Retorno (saída)",
                        ["Retorno (saída)", "Parâmetro", "Variável global"],
                    ),
                    quiz(
                        "Qual a principal vantagem de usar uma função em vez de copiar e colar o mesmo bloco de código várias vezes?",
                        "Define a lógica uma vez e reutiliza com entradas diferentes",
                        ["Define a lógica uma vez e reutiliza com entradas diferentes", "Deixa o programa maior", "É a única forma de usar variáveis"],
                    ),
                    quiz(
                        "O princípio \"não se repita\" (evitar copiar e colar lógica) é conhecido pela sigla:",
                        "DRY",
                        ["DRY", "CPU", "I/O"],
                    ),
                    quiz(
                        "Combine: um algoritmo que LÊ uma nota, DECIDE se passou (SE/SENÃO) e REPETE isso pra vários alunos (ENQUANTO) usa quais dos 3 pilares do módulo?",
                        "Sequência, decisão e repetição, os três juntos",
                        ["Sequência, decisão e repetição, os três juntos", "Só decisão", "Nenhum dos três, porque tem variável"],
                    ),
                    quiz(
                        "Depois deste módulo conceitual, o que vem a seguir na trilha?",
                        "Preparar o ambiente e depois aplicar tudo isso escrevendo Python de verdade",
                        ["Preparar o ambiente e depois aplicar tudo isso escrevendo Python de verdade", "O curso termina aqui", "Voltar directly para funções avançadas"],
                    ),
                ],
            ),
        ],
    )


# ============================================================
# MODULO 2 - Preparando o Ambiente (novo, Fase 2 do roteiro)
# Conceitual: exercícios quiz/text; lição sugere rodar comandos
# no terminal próprio do aluno.
# ============================================================

def build_modulo_ambiente():
    return module(
        "preparando-o-ambiente",
        "Módulo 2 — Preparando o Ambiente",
        "Colocar o Python de pé na sua máquina: o que é a linguagem, instalação, terminal, REPL e a escolha de um editor de código.",
        [
            topic(
                "o-que-e-python",
                "O que é Python?",
                """
# O que é Python?

Python é uma linguagem de programação **interpretada**, criada por **Guido van
Rossum** no início dos anos 90, com uma proposta central: código **legível**. A
sintaxe foi desenhada para parecer quase com inglês, o que a torna uma das
melhores primeiras linguagens para aprender.

## Por que Python é tão popular?

- **Fácil de ler**: menos símbolos e regras do que outras linguagens.
- **Versátil**: serve para desenvolvimento web, automação, análise de dados,
  inteligência artificial, scripts do dia a dia e muito mais.
- **Comunidade enorme**: milhares de bibliotecas prontas para quase qualquer
  problema.
- **Multiparadigma**: dá para escrever código do jeito mais simples para cada
  tarefa.

## Onde o Python roda?

Python roda em praticamente qualquer lugar: Windows, macOS, Linux, servidores,
nuvem — e até dentro do navegador, como nos exercícios deste curso! É por isso
que ele é usado tanto por iniciantes quanto por gigantes da tecnologia.

> 💻 Nos próximos tópicos você vai instalar o Python na sua máquina. O site
> oficial é o **python.org** — é de lá que sai o instalador oficial.
""",
                [
                    quiz(
                        "Quem criou a linguagem Python?",
                        "Guido van Rossum",
                        ["Guido van Rossum", "Bill Gates", "Linus Torvalds"],
                    ),
                    quiz(
                        "Qual é a proposta central do design do Python?",
                        "Código legível, parecido com inglês",
                        ["Código legível, parecido com inglês", "Código o mais curto possível sempre", "Rodar apenas em Windows"],
                    ),
                    quiz(
                        "Python serve para quais áreas?",
                        "Web, automação, dados e inteligência artificial",
                        ["Web, automação, dados e inteligência artificial", "Apenas desenvolvimento web", "Apenas jogos de última geração"],
                    ),
                    quiz(
                        "Em quais lugares o Python consegue rodar?",
                        "Windows, macOS, Linux e até no navegador",
                        ["Windows, macOS, Linux e até no navegador", "Apenas no Windows", "Somente em servidores gigantes"],
                    ),
                    text(
                        "Complete: a proposta central do Python é um código ___ (fácil de ler).",
                        "legível",
                    ),
                ],
            ),
            topic(
                "instalando-o-python",
                "Instalando o Python",
                """
# Instalando o Python

## 1. Baixe o instalador

Acesse **python.org**, entre em *Downloads* e baixe a versão mais recente
recomendada (uma versão `3.x`).

## 2. Instale

Rode o instalador baixado. Dica importante no Windows: marque a opção
**"Add Python to PATH"** antes de clicar em instalar — ela permite usar o
comando `python` direto no terminal.

## 3. Verifique a instalação

Abra o **terminal** (no Windows, procure por "Prompt de Comando" ou
"PowerShell") e digite:

```bash
python --version
```

O Python responde com algo como:

```text
Python 3.13.1
```

Se você viu um número de versão, o Python está instalado e funcionando!

> 💻 Hora de testar: abra seu terminal e rode `python --version`. Se aparecer
> um número começando com `3`, a instalação deu certo.
""",
                [
                    quiz(
                        "De onde você baixa o instalador oficial do Python?",
                        "python.org",
                        ["python.org", "google.com", "store.apple.com"],
                    ),
                    quiz(
                        "No Windows, qual opção do instalador permite usar o comando `python` direto no terminal?",
                        "Add Python to PATH",
                        ["Add Python to PATH", "Add Python to Desktop", "Enable Turbo Mode"],
                    ),
                    quiz(
                        "Qual comando, no terminal, mostra a versão do Python instalada?",
                        "python --version",
                        ["python --version", "versao python", "show python"],
                    ),
                    quiz(
                        "Se `python --version` responde com `Python 3.13.1`, o que isso significa?",
                        "O Python está instalado e funcionando",
                        ["O Python está instalado e funcionando", "A instalação falhou", "Faltou instalar"],
                    ),
                    quiz(
                        "Qual é a família de versões atual e recomendada do Python?",
                        "3.x",
                        ["3.x", "2.x", "1.x"],
                    ),
                ],
            ),
            topic(
                "terminal-e-comandos-basicos",
                "Terminal e linha de comando",
                """
# Terminal e linha de comando

O **terminal** é um programa que recebe comandos de texto e executa ações no
computador. Você já usa programas com botões (interface gráfica); o terminal é
o jeito de controlar o computador por texto — e é onde você vai rodar Python.

## Abrindo o terminal

- **Windows**: pesquise por "Prompt de Comando" ou "PowerShell".
- **macOS/Linux**: procure o app chamado "Terminal".

## Comandos básicos para se orientar

| O que você quer | Windows | macOS/Linux |
|---|---|---|
| Ver o que tem na pasta atual | `dir` | `ls` |
| Entrar numa pasta | `cd nome` | `cd nome` |
| Subir uma pasta | `cd ..` | `cd ..` |
| Limpar a tela | `cls` | `clear` |

## Rodando Python pelo terminal

Você vai usar o terminal o tempo todo com Python. O comando do tópico anterior
continua valendo para conferir que está tudo certo:

```bash
python --version
```

> 💻 Abra seu terminal e rode `dir` (no Windows) ou `ls` (no macOS/Linux).
> Veja a lista de arquivos da sua pasta atual. Depois rode `python --version`
> de novo — agora você já sabe o que cada comando faz.
""",
                [
                    quiz(
                        "O que é o terminal?",
                        "Um programa que recebe comandos de texto e executa ações",
                        ["Um programa que recebe comandos de texto e executa ações", "Um tipo de arquivo do Python", "Um editor de código"],
                    ),
                    quiz(
                        "No Windows, qual comando lista os arquivos da pasta atual?",
                        "dir",
                        ["dir", "ls", "list"],
                    ),
                    quiz(
                        "Qual comando muda de pasta (diretório)?",
                        "cd",
                        ["cd", "cls", "del"],
                    ),
                    quiz(
                        "O comando `python --version` no terminal serve para:",
                        "Verificar a versão do Python instalada",
                        ["Verificar a versão do Python instalada", "Listar os arquivos da pasta", "Limpar a tela"],
                    ),
                    text(
                        "Complete: no Windows, o comando para limpar a tela do terminal é ___.",
                        "cls",
                    ),
                ],
            ),
            topic(
                "repl-e-primeiros-passos",
                "REPL e seus primeiros comandos",
                """
# REPL e seus primeiros comandos

**REPL** é a sigla em inglês para *Read-Eval-Print-Loop* (Ler, Avaliar,
Imprimir, Repetir). É o **modo interativo** do Python: você digita um comando,
o Python executa e mostra o resultado na hora, e fica esperando o próximo.

## Abrindo o REPL

No terminal, digite:

```bash
python
```

O Python entra no modo interativo e mostra um símbolo `>>>` — é ele indicando
"estou pronto, pode digitar". Experimente:

```python
>>> print("Olá, mundo!")
Olá, mundo!

>>> 2 + 3
5
```

Perceba: você não precisou criar arquivo nenhum. O REPL executa cada linha na
hora — ótimo para testar ideias rápidas.

## Saindo do REPL

Quando quiser sair, digite:

```python
>>> exit()
```

> 💻 No seu terminal, rode `python`, digite `2 + 3` e veja o `5`. Depois
> escreva `print("Olá, mundo!")`. Por fim, saia com `exit()`.
""",
                [
                    quiz(
                        "O que significa a sigla REPL?",
                        "Read-Eval-Print-Loop",
                        ["Read-Eval-Print-Loop", "Run-Edit-Print-Loop", "Reload-Execute-Print-Log"],
                    ),
                    quiz(
                        "Qual comando, no terminal, abre o modo interativo do Python?",
                        "python",
                        ["python", "start", "play"],
                    ),
                    quiz(
                        "O símbolo `>>>` no REPL indica que:",
                        "o Python está pronto para receber um comando",
                        ["o Python está pronto para receber um comando", "ocorreu um erro grave", "o programa terminou"],
                    ),
                    quiz(
                        "Dentro do REPL, ao digitar `2 + 3` e dar Enter, o que aparece?",
                        "5",
                        ["5", "23", "um erro"],
                    ),
                    quiz(
                        "Qual comando sai do modo interativo do Python?",
                        "exit()",
                        ["exit()", "fechar()", "sair()"],
                    ),
                ],
            ),
            topic(
                "editores-e-ides",
                "Editores e IDEs",
                """
# Editores e IDEs

Você pode escrever programas Python em qualquer editor de texto simples, mas
usar uma ferramenta feita para código deixa a vida muito mais fácil.

## Editor de código vs. IDE

- **Editor de código**: programa leve para escrever e editar texto, com
  recursos úteis para programação (realce de sintaxe, autocompletar). Ex.:
  **VS Code**, **Sublime Text**.
- **IDE** (*Integrated Development Environment*): um editor com muito mais
  ferramentas embutidas — terminal, depurador, testes, gerenciamento de
  projetos. Ex.: **PyCharm**.

O **VS Code** é uma escolha popular para começar: leve, gratuito e com
milhares de extensões para Python.

## O IDLE (vem com o Python)

Quando você instala o Python, ele vem com um editor simples chamado **IDLE**.
Não é o mais completo, mas serve para testar os primeiros programas sem
instalar nada extra.

## Rodando um arquivo .py

Você cria um arquivo com a extensão `.py`, escreve seu código nele e roda pelo
terminal:

```bash
python meu_programa.py
```

> 💻 Crie um arquivo chamado `meu_programa.py` no seu editor, escreva
> `print("Olá!")`, salve, e rode `python meu_programa.py` no terminal.
""",
                [
                    quiz(
                        "Qual a diferença básica entre editor de código e IDE?",
                        "A IDE traz mais ferramentas integradas (terminal, depurador, testes)",
                        ["A IDE traz mais ferramentas integradas (terminal, depurador, testes)", "A IDE é um site e o editor é um programa", "São a mesma coisa, só muda o nome"],
                    ),
                    quiz(
                        "Qual destes é um editor de código popular para Python?",
                        "VS Code",
                        ["VS Code", "Microsoft Word", "Paint"],
                    ),
                    quiz(
                        "Qual editor bem simples acompanha a instalação padrão do Python?",
                        "IDLE",
                        ["IDLE", "WordPad", "Navegador"],
                    ),
                    quiz(
                        "Para rodar o arquivo `meu_programa.py` no terminal, você digita:",
                        "python meu_programa.py",
                        ["python meu_programa.py", "run meu_programa.py", "open meu_programa.py"],
                    ),
                    text(
                        "Complete: um arquivo de programa Python tem a extensão ___.",
                        ".py",
                    ),
                ],
            ),
        ],
    )


# ============================================================
# MODULO 3 - Fundamentos do Python (reescrito, Fase 2 do roteiro)
# Código: exercícios `code` rodam de verdade no Pyodide.
# Mantém os 4 slugs existentes (preserva progresso) e adiciona
# entrada do usuário + comentários/boas práticas.
# ============================================================

def build_modulo_fundamentos():
    return module(
        "fundamentos",
        "Módulo 3 — Fundamentos do Python",
        "Os tijolos da linguagem: variáveis, tipos, números, textos, booleanos, entrada do usuário e boas práticas de nomes.",
        [
            topic(
                "variaveis-e-tipos",
                "Variáveis e tipos",
                """
# Variáveis e tipos

Uma **variável** é uma caixa com nome onde guardamos um valor:

```python
nome = "Ana"
idade = 25
```

Usamos o sinal `=` para **atribuir** (guardar) um valor na variável. Depois é só usar o nome:

```python
print(nome)   # Ana
print(idade)  # 25
```

## Tipos básicos

Cada valor tem um **tipo**:

- `str` (texto / *string*): `"Ana"`, `'Python'`
- `int` (número inteiro): `25`, `-3`, `0`
- `float` (número com vírgula): `3.14`, `-0.5`
- `bool` (verdadeiro ou falso): `True`, `False`

Você pode descobrir o tipo com `type()`:

```python
print(type("Ana"))  # <class 'str'>
print(type(25))     # <class 'int'>
```

## Regras para nomes de variáveis

- Use nomes que descrevem o conteúdo: `preco`, `total_alunos`.
- Sem espaços (use `_`): `nome_completo`.
- Não pode começar com número.
""",
                [
                    code(
                        "Crie uma variável chamada `cidade` com o valor `\"São Paulo\"` e uma variável `ano` com o valor `2026`.",
                        "cidade = \"São Paulo\"\nano = 2026",
                        "assert 'cidade' in dir(), 'A variável cidade não foi criada'\nassert cidade == 'São Paulo', f'cidade deveria ser \\'São Paulo\\', mas é {cidade!r}'\nassert 'ano' in dir(), 'A variável ano não foi criada'\nassert ano == 2026, f'ano deveria ser 2026, mas é {ano!r}'",
                    ),
                    code(
                        "Crie uma variável `linguagem` com o texto `\"Python\"` e uma variável `versao` com o número `3.13`.",
                        "linguagem = \"Python\"\nversao = 3.13",
                        "assert 'linguagem' in dir(), 'Crie a variável linguagem'\nassert linguagem == 'Python', f'linguagem ficou: {linguagem!r}'\nassert type(linguagem) == str, 'linguagem deveria ser um texto (str)'\nassert 'versao' in dir(), 'Crie a variável versao'\nassert versao == 3.13, f'versao ficou: {versao!r}'\nassert type(versao) == float, 'versao deveria ser um número com vírgula (float)'",
                    ),
                    code(
                        "Crie uma variável `ativo` que valha `True` (verdadeiro).",
                        "ativo = True",
                        "assert 'ativo' in dir(), 'Crie a variável ativo'\nassert ativo == True, 'ativo deveria ser True'\nassert type(ativo) == bool, 'ativo deveria ser um booleano (bool)'",
                    ),
                    code(
                        "Crie a variável `pontos = 10`. Na linha seguinte, atualize `pontos` para `15`.",
                        "pontos = 10\npontos = 15",
                        "assert 'pontos' in dir(), 'Crie a variável pontos'\nassert pontos == 15, f'pontos deveria ser 15, mas é {pontos!r}'",
                        starter_code="pontos = 10\n",
                    ),
                    code(
                        "Dada a variável `valor = 3.14`, crie a variável `tipo_do_valor` com o tipo dela (use `type(valor)`).",
                        "valor = 3.14\ntipo_do_valor = type(valor)",
                        "assert 'tipo_do_valor' in dir(), 'Crie a variável tipo_do_valor'\nassert tipo_do_valor == float, 'tipo_do_valor deveria ser float'",
                        starter_code="valor = 3.14\n# crie tipo_do_valor\n",
                    ),
                    quiz(
                        "Qual desses é um nome de variável VÁLIDO em Python?",
                        "nome_completo",
                        ["nome_completo", "2nome", "nome-completo", "nome completo"],
                    ),
                    quiz(
                        "Para ATRIBUIR (guardar) um valor numa variável, usamos:",
                        "=",
                        ["=", "==", "->"],
                    ),
                ],
            ),
            topic(
                "numeros-e-operadores",
                "Números e operadores",
                """
# Números e operadores

Python é uma ótima calculadora. Operadores aritméticos:

| Operador | Operação | Exemplo | Resultado |
|---|---|---|---|
| `+` | soma | `2 + 3` | `5` |
| `-` | subtração | `5 - 2` | `3` |
| `*` | multiplicação | `4 * 3` | `12` |
| `/` | divisão | `10 / 4` | `2.5` |
| `//` | divisão inteira | `10 // 4` | `2` |
| `%` | resto da divisão | `10 % 3` | `1` |
| `**` | potência | `2 ** 3` | `8` |

```python
total = 10 + 5 * 2   # 20 (multiplicação primeiro!)
media = (8 + 6) / 2  # 7.0
```

> 💡 Assim como na matemática, `*` e `/` vêm antes de `+` e `-`. Use parênteses para mudar a ordem.

## O resto (`%`) é muito útil

Serve para saber, por exemplo, se um número é par:

```python
8 % 2   # 0  -> par
7 % 2   # 1  -> ímpar
```
""",
                [
                    code(
                        "Uma loja vende um produto por R$ 49 a unidade. Calcule o preço de 7 unidades e guarde na variável `total`.",
                        "preco = 49\nquantidade = 7\ntotal = preco * quantidade",
                        "assert 'total' in dir(), 'Crie a variável total'\nassert total == 343, f'total deveria ser 343, mas é {total!r}'",
                        starter_code="preco = 49\nquantidade = 7\n# calcule total\n",
                    ),
                    code(
                        "Calcule o resto da divisão de 17 por 5 e guarde na variável `resto`.",
                        "resto = 17 % 5",
                        "assert 'resto' in dir(), 'Crie a variável resto'\nassert resto == 2, f'resto deveria ser 2, mas é {resto!r}'",
                    ),
                    code(
                        "Com 20 lápis, quantas caixas de 3 cabem inteiras e quanto sobra? Guarde em `caixas` (parte inteira) e `sobrando` (resto).",
                        "caixas = 20 // 3\nsobrando = 20 % 3",
                        "assert 'caixas' in dir(), 'Crie a variável caixas'\nassert caixas == 6, f'caixas deveria ser 6, mas é {caixas!r}'\nassert 'sobrando' in dir(), 'Crie a variável sobrando'\nassert sobrando == 2, f'sobrando deveria ser 2, mas é {sobrando!r}'",
                    ),
                    code(
                        "Calcule `2 ** 10` e guarde o resultado na variável `resultado`.",
                        "resultado = 2 ** 10",
                        "assert 'resultado' in dir(), 'Crie a variável resultado'\nassert resultado == 1024, f'resultado deveria ser 1024, mas é {resultado!r}'",
                    ),
                    code(
                        "As notas de Ana foram 7, 8 e 9. Calcule a média e guarde na variável `media`.",
                        "media = (7 + 8 + 9) / 3",
                        "assert 'media' in dir(), 'Crie a variável media'\nassert media == 8.0, f'media deveria ser 8.0, mas é {media!r}'",
                    ),
                    quiz(
                        "Qual o resultado de `10 - 2 * 3`, seguindo a ordem de precedência?",
                        "4",
                        ["4", "24", "16"],
                    ),
                    quiz(
                        "Qual operador faz divisão e retorna apenas a parte inteira do resultado?",
                        "//",
                        ["//", "/", "%"],
                    ),
                    quiz(
                        "Qual operador retorna o resto de uma divisão?",
                        "%",
                        ["%", "/", "**"],
                    ),
                ],
            ),
            topic(
                "strings",
                "Strings (textos)",
                """
# Strings (textos)

Uma *string* é um texto, entre aspas simples `'...'` ou duplas `"..."`.

## Juntar textos (concatenação)

```python
nome = "Ana"
saudacao = "Olá, " + nome + "!"   # "Olá, Ana!"
```

## f-strings (a forma moderna e prática)

Coloque um `f` antes das aspas e use `{}` para inserir variáveis:

```python
nome = "Ana"
idade = 25
print(f"{nome} tem {idade} anos")   # Ana tem 25 anos
```

## Métodos úteis

```python
texto = "Python"
len(texto)          # 6  (tamanho)
texto.upper()       # "PYTHON"
texto.lower()       # "python"
texto.replace("P", "J")  # "Jython"
"  oi  ".strip()    # "oi"  (remove espaços nas pontas)
```
""",
                [
                    code(
                        "Dada a variável `nome`, crie uma variável `mensagem` com o texto `Bem-vindo(a), <nome>!` usando uma f-string. Ex.: se nome for `\"Ana\"`, mensagem deve ser `\"Bem-vindo(a), Ana!\"`.",
                        "nome = \"Ana\"\nmensagem = f\"Bem-vindo(a), {nome}!\"",
                        "assert 'mensagem' in dir(), 'Crie a variável mensagem'\nassert mensagem == 'Bem-vindo(a), Ana!', f'mensagem ficou: {mensagem!r}'",
                        starter_code="nome = \"Ana\"\n# crie mensagem usando f-string\n",
                    ),
                    code(
                        "Dada a variável `nome = \"Carlos\"`, crie a variável `saudacao` juntando `\"Olá, \"`, o nome e `\"!\"` usando concatenação (com `+`).",
                        "nome = \"Carlos\"\nsaudacao = \"Olá, \" + nome + \"!\"",
                        "assert 'saudacao' in dir(), 'Crie a variável saudacao'\nassert saudacao == 'Olá, Carlos!', f'saudacao ficou: {saudacao!r}'",
                        starter_code="nome = \"Carlos\"\n# crie saudacao por concatenação\n",
                    ),
                    code(
                        "Dada a variável `frase = \"Python é incrível\"`, crie `frase_upper` (tudo maiúsculo) e `frase_lower` (tudo minúsculo).",
                        "frase = \"Python é incrível\"\nfrase_upper = frase.upper()\nfrase_lower = frase.lower()",
                        "assert 'frase_upper' in dir(), 'Crie a variável frase_upper'\nassert frase_upper == 'PYTHON É INCRÍVEL', f'frase_upper ficou: {frase_upper!r}'\nassert 'frase_lower' in dir(), 'Crie a variável frase_lower'\nassert frase_lower == 'python é incrível', f'frase_lower ficou: {frase_lower!r}'",
                        starter_code="frase = \"Python é incrível\"\n# crie frase_upper e frase_lower\n",
                    ),
                    code(
                        "Dado `texto = \"Python\"`, crie a variável `tamanho` com o número de caracteres (use `len`).",
                        "texto = \"Python\"\ntamanho = len(texto)",
                        "assert 'tamanho' in dir(), 'Crie a variável tamanho'\nassert tamanho == 6, f'tamanho deveria ser 6, mas é {tamanho!r}'",
                        starter_code="texto = \"Python\"\n# crie tamanho\n",
                    ),
                    code(
                        "Dada a variável `frase = \"Amo Python\"`, crie `frase_nova` substituindo `\"Python\"` por `\"programar\"` (use `replace`).",
                        "frase = \"Amo Python\"\nfrase_nova = frase.replace(\"Python\", \"programar\")",
                        "assert 'frase_nova' in dir(), 'Crie a variável frase_nova'\nassert frase_nova == 'Amo programar', f'frase_nova ficou: {frase_nova!r}'",
                        starter_code="frase = \"Amo Python\"\n# crie frase_nova\n",
                    ),
                    quiz(
                        "Qual método remove espaços em branco das pontas de uma string?",
                        "strip()",
                        ["strip()", "cut()", "trim()"],
                    ),
                    quiz(
                        "Qual o resultado de `f\"{2 + 3}\"`?",
                        "o texto \"5\"",
                        ["o texto \"5\"", "o número 5", "um erro"],
                    ),
                    quiz(
                        "Para usar uma f-string, você coloca ___ antes das aspas.",
                        "a letra f",
                        ["a letra f", "a letra s", "o sinal de #"],
                    ),
                ],
            ),
            topic(
                "booleanos-e-comparacoes",
                "Booleanos e comparações",
                """
# Booleanos e comparações

Um valor **booleano** (`bool`) só pode ser `True` (verdadeiro) ou `False` (falso). Eles aparecem quando comparamos coisas.

## Operadores de comparação

| Operador | Significado | Exemplo | Resultado |
|---|---|---|---|
| `==` | igual a | `3 == 3` | `True` |
| `!=` | diferente de | `3 != 5` | `True` |
| `>` | maior que | `5 > 2` | `True` |
| `<` | menor que | `5 < 2` | `False` |
| `>=` | maior ou igual | `5 >= 5` | `True` |
| `<=` | menor ou igual | `4 <= 3` | `False` |

> ⚠️ Cuidado: `=` **atribui** um valor; `==` **compara**. São coisas diferentes!

## Combinando condições

- `and` — verdadeiro se **ambos** forem verdadeiros
- `or` — verdadeiro se **pelo menos um** for verdadeiro
- `not` — inverte (verdadeiro vira falso)

```python
idade = 20
idade >= 18 and idade < 60   # True
not (idade == 20)            # False
```
""",
                [
                    code(
                        "Crie uma variável `maior_de_idade` que seja `True` se a variável `idade` for maior ou igual a 18, e `False` caso contrário. Use uma comparação (não escreva True/False direto).",
                        "idade = 20\nmaior_de_idade = idade >= 18",
                        "assert 'maior_de_idade' in dir(), 'Crie a variável maior_de_idade'\nassert maior_de_idade == True, 'Com idade 20 deveria ser True'",
                        starter_code="idade = 20\n# crie maior_de_idade a partir de uma comparação\n",
                    ),
                    code(
                        "Com as variáveis `idade = 20` e `tem_ingresso = True`, crie `pode_entrar` que seja `True` apenas se `idade >= 18` **e** `tem_ingresso`.",
                        "idade = 20\ntem_ingresso = True\npode_entrar = idade >= 18 and tem_ingresso",
                        "assert 'pode_entrar' in dir(), 'Crie a variável pode_entrar'\nassert pode_entrar == True, 'Com idade 20 e ingresso, deveria ser True'",
                        starter_code="idade = 20\ntem_ingresso = True\n# crie pode_entrar usando and\n",
                    ),
                    code(
                        "Dada a variável `numero = 8`, crie `eh_par` que seja `True` se o número for par (use o operador `%`).",
                        "numero = 8\neh_par = numero % 2 == 0",
                        "assert 'eh_par' in dir(), 'Crie a variável eh_par'\nassert eh_par == True, '8 é par, eh_par deveria ser True'",
                        starter_code="numero = 8\n# crie eh_par usando o operador %\n",
                    ),
                    code(
                        "Com `idade = 16` e `tem_autorizacao = True`, crie `pode_entrar` que seja `True` se `idade >= 18` **ou** `tem_autorizacao`.",
                        "idade = 16\ntem_autorizacao = True\npode_entrar = idade >= 18 or tem_autorizacao",
                        "assert 'pode_entrar' in dir(), 'Crie a variável pode_entrar'\nassert pode_entrar == True, 'Com autorização, deveria ser True'",
                        starter_code="idade = 16\ntem_autorizacao = True\n# crie pode_entrar usando or\n",
                    ),
                    quiz(
                        "Qual operador COMPARA dois valores (resultando em verdadeiro ou falso)?",
                        "==",
                        ["==", "=", "->"],
                    ),
                    quiz(
                        "`not True` resulta em:",
                        "False",
                        ["False", "True", "erro"],
                    ),
                    quiz(
                        "`True or False` resulta em:",
                        "True",
                        ["True", "False", "erro"],
                    ),
                    quiz(
                        "`True and False` resulta em:",
                        "False",
                        ["False", "True", "erro"],
                    ),
                ],
            ),
            topic(
                "entrada-do-usuario",
                "Entrada do usuário (input)",
                """
# Entrada do usuário (input)

Um programa mais útil geralmente **recebe dados de quem está usando** e
responde com base neles. Em Python, a função `input()` faz isso.

## Como funciona o input()

Quando o Python encontra `input()`, ele **pausa o programa, espera você digitar
algo e apertar Enter**, e então devolve o que foi digitado:

```python
nome = input("Digite seu nome: ")
print("Olá, " + nome + "!")
```

## Atenção: input() sempre devolve texto

Por mais que o usuário digite um número, `input()` devolve uma **string**:

```python
idade = input("Quantos anos você tem? ")
print(idade + 1)   # ERRO! Não dá para somar texto com número
```

Para usar como número, é preciso **converter**:

| Função | Converte para | Exemplo |
|---|---|---|
| `int()` | número inteiro | `int("25")` -> `25` |
| `float()` | número com vírgula | `float("3.5")` -> `3.5` |
| `str()` | texto | `str(25)` -> `"25"` |

```python
idade = int(input("Quantos anos você tem? "))
print(idade + 1)   # agora funciona!
```

> 💻 `input()` não roda de forma interativa dentro do navegador, mas funciona
> no Python instalado na sua máquina. Abra seu terminal, rode `python` e
> digite: `nome = input("Seu nome: ")`, depois `print(nome)`. Teste também
> `int("25")` para ver a conversão.
""",
                [
                    quiz(
                        "A função `input()` serve para:",
                        "ler o que o usuário digitar",
                        ["ler o que o usuário digitar", "mostrar texto na tela", "criar um arquivo"],
                    ),
                    quiz(
                        "`input()` SEMPRE devolve o valor digitado como:",
                        "texto (string)",
                        ["texto (string)", "número inteiro", "booleano"],
                    ),
                    quiz(
                        "Se o usuário digita `18` e o programa lê com `input()`, o valor guardado é o texto `'18'`. Para comparar com o número 18, o programa precisa:",
                        "converter com int()",
                        ["converter com int()", "comparar direto com 18", "nada, já funciona"],
                    ),
                    code(
                        "Converta o texto `'25'` para número inteiro e guarde na variável `idade`.",
                        "idade = int(\"25\")",
                        "assert 'idade' in dir(), 'Crie a variável idade'\nassert idade == 25 and type(idade) == int, f'idade deveria ser o inteiro 25, mas é {idade!r}'",
                    ),
                    code(
                        "Converta o texto `'3.5'` para número com vírgula e guarde na variável `nota`.",
                        "nota = float(\"3.5\")",
                        "assert 'nota' in dir(), 'Crie a variável nota'\nassert nota == 3.5 and type(nota) == float, f'nota deveria ser o float 3.5, mas é {nota!r}'",
                    ),
                    code(
                        "Converta `'10'` e `'5'` para números e guarde a **soma** deles na variável `total`.",
                        "total = int(\"10\") + int(\"5\")",
                        "assert 'total' in dir(), 'Crie a variável total'\nassert total == 15, f'total deveria ser 15, mas é {total!r}'",
                    ),
                    text(
                        "Qual função converte um texto para número inteiro? (sem parênteses)",
                        "int",
                    ),
                ],
            ),
            topic(
                "comentarios-e-nomes",
                "Comentários e boas práticas de nomes",
                """
# Comentários e boas práticas de nomes

## Comentários com #

Um **comentário** é um texto que o Python **ignora** ao executar — serve para
explicar o código para quem lê (inclusive para você mesmo no futuro). Começa
com `#`:

```python
# Calcula o preço com 10% de desconto
preco_final = preco - preco * 0.10
```

Comentários não deixam o programa mais rápido nem mais lento; o que eles fazem
é deixar a **intenção** clara.

## Nomes de variáveis: snake_case

Python tem uma convenção de nomes chamada **snake_case**: letras minúsculas e
palavras separadas por `_`.

| Estilo | Exemplo | Válido em Python? |
|---|---|---|
| snake_case | `preco_total` | ✅ (o padrão) |
| camelCase | `precoTotal` | ✅ funciona, mas não é o padrão |
| kebab-case | `preco-total` | ❌ o `-` é lido como subtração |
| UpperCamelCase | `PrecoTotal` | reservado para nomes de classes (POO) |

**Regra de ouro**: o nome deve dizer **o que a variável guarda**. `preco_total`
é um bom nome; `x` ou `coisa1` não dizem nada.

> 💡 Escrever código pensando em quem vai ler depois — inclusive você mesmo,
> semanas depois — é uma das marcas de um bom programador.
""",
                [
                    code(
                        "Escreva uma linha de comentário (começando com `#`) explicando o que a linha `soma = 2 + 2` faz, e depois a própria linha `soma = 2 + 2`.",
                        "# soma os dois números\nsoma = 2 + 2",
                        "assert '#' in _student_code, 'Adicione um comentário com #'\nassert 'soma' in dir() and soma == 4, 'Crie soma = 2 + 2'",
                    ),
                    code(
                        "Crie uma variável em snake_case que guarde o salário bruto: `salario_bruto = 3000`.",
                        "salario_bruto = 3000",
                        "assert 'salario_bruto' in dir(), 'Crie a variável salario_bruto'\nassert salario_bruto == 3000, f'salario_bruto deveria ser 3000, mas é {salario_bruto!r}'",
                    ),
                    quiz(
                        "Como se escreve um comentário de uma linha em Python?",
                        "# comentário",
                        ["# comentário", "// comentário", "/* comentário */"],
                    ),
                    quiz(
                        "Qual o propósito de um comentário?",
                        "explicar o código para quem for ler",
                        ["explicar o código para quem for ler", "deixar o programa mais rápido", "impedir o programa de rodar"],
                    ),
                    quiz(
                        "Qual é o padrão de nomes de variáveis usado em Python?",
                        "palavras minúsculas separadas por _",
                        ["palavras minúsculas separadas por _", "palavras maiúsculas juntas", "palavras separadas por -"],
                    ),
                    quiz(
                        "Qual desses é um nome de variável VÁLIDO e no padrão Python?",
                        "preco_total",
                        ["preco_total", "preco-total", "2preco"],
                    ),
                    text(
                        "Complete: o símbolo que inicia um comentário em Python é ___.",
                        "#",
                    ),
                ],
            ),
        ],
    )


# ============================================================
# MODULO 4 - Estruturas de Controle (reescrito, Fase 3 do roteiro)
# Código. Expande o módulo "controle-de-fluxo" existente; as
# comprehensions saem daqui (foram para Estruturas de Dados).
# ============================================================

def build_modulo_controle():
    return module(
        "controle-de-fluxo",
        "Módulo 4 — Estruturas de Controle",
        "Decidir e repetir: if/elif/else, for, while e o controle fino de um laço com break e continue.",
        [
            topic(
                "condicionais",
                "Condicionais (if / elif / else)",
                """
# Condicionais (if / elif / else)

Um programa decide o que fazer usando condições. Em Python isso é o `if`
(se), o `elif` (senão se) e o `else` (senão):

```python
idade = 15

if idade >= 18:
    print("Maior de idade")
elif idade >= 12:
    print("Adolescente")
else:
    print("Criança")
```

## Regras de sintaxe

- A condição vem seguida de **dois-pontos** (`:`).
- O bloco é marcado por **indentação** (4 espaços) — sem indentação, o Python
  nem entende que o código faz parte do `if`.
- O `elif` só é testado se o `if` for falso; o `else` pega tudo o que sobrou.
- Só **um** bloco roda: a primeira condição verdadeira.

## Um número pode ser par ou ímpar

```python
numero = 7
if numero % 2 == 0:
    print("par")
else:
    print("ímpar")
```

> 💡 Se você esquecer os dois-pontos, o Python reclama com `SyntaxError` —
> e se esquecer a indentação, com `IndentationError`. Os dois são erros de
> "faltou algo na estrutura", não de lógica.
""",
                [
                    code(
                        "Dada a variável `nota`, crie a variável `situacao` que vale `\"aprovado\"` se `nota >= 7` e `\"reprovado\"` caso contrário. Use um `if`/`else`.",
                        "nota = 8\nif nota >= 7:\n    situacao = \"aprovado\"\nelse:\n    situacao = \"reprovado\"",
                        "assert 'situacao' in dir(), 'Crie a variável situacao'\nassert situacao == 'aprovado', f'Com nota 8, situacao deveria ser aprovado, mas é {situacao!r}'",
                        starter_code="nota = 8\n# escreva o if/else que define situacao\n",
                    ),
                    code(
                        "Dada a variável `idade`, crie `faixa` que valha `\"crianca\"` se `idade < 12`, `\"adolescente\"` se `idade < 18` e `\"adulto\"` caso contrário. Use `if`/`elif`/`else`.",
                        "idade = 15\nif idade < 12:\n    faixa = \"crianca\"\nelif idade < 18:\n    faixa = \"adolescente\"\nelse:\n    faixa = \"adulto\"",
                        "assert 'faixa' in dir(), 'Crie a variável faixa'\nassert faixa == 'adolescente', f'Com idade 15, faixa deveria ser adolescente, mas é {faixa!r}'",
                        starter_code="idade = 15\n# escreva o if/elif/else que define faixa\n",
                    ),
                    code(
                        "Dada a variável `numero`, crie `paridade` que valha `\"par\"` se o número for par (use `%`) e `\"impar\"` caso contrário.",
                        "numero = 7\nif numero % 2 == 0:\n    paridade = \"par\"\nelse:\n    paridade = \"impar\"",
                        "assert 'paridade' in dir(), 'Crie a variável paridade'\nassert paridade == 'impar', f'Com numero 7, paridade deveria ser impar, mas é {paridade!r}'",
                        starter_code="numero = 7\n# escreva o if/else que define paridade\n",
                    ),
                    quiz(
                        "O que vem logo depois da condição de um `if`?",
                        "dois-pontos (:)",
                        ["dois-pontos (:)", "um ponto-e-vírgula (;)", "nada, a linha termina"],
                    ),
                    quiz(
                        "Como o Python sabe qual código faz parte do bloco do `if`?",
                        "Pela indentação",
                        ["Pela indentação", "Por chaves {}", "Pelo comando end"],
                    ),
                    quiz(
                        "Dado `nota = 6` e o código `if nota >= 7: situacao = \"aprovado\" else: situacao = \"reprovado\"`, qual é a situação?",
                        "reprovado",
                        ["reprovado", "aprovado", "um erro de sintaxe"],
                    ),
                    text(
                        "Complete: o `elif` só é testado se o ___ anterior for falso.",
                        "if",
                    ),
                ],
            ),
            topic(
                "loops",
                "Repetição com for",
                """
# Repetição com for

O `for` percorre uma sequência — uma lista, uma string, um `range(...)` — e
repele o bloco uma vez para cada elemento:

```python
for nome in ["Ana", "Bia", "Caio"]:
    print(nome)
```

## range(): sequência de números

`range(inicio, fim)` gera números de `inicio` até `fim - 1`:

```python
for i in range(1, 4):   # 1, 2, 3
    print(i)
```

```python
for i in range(3):      # 0, 1, 2 (começa no 0)
    print(i)
```

## Acumulador: somando dentro do laço

Um padrão clássico é uma variável que vai acumulando um valor:

```python
soma = 0
for i in range(1, 6):
    soma = soma + i     # 1 + 2 + 3 + 4 + 5 = 15
```

## Percorrendo uma lista e construindo outra

```python
nomes = ["ana", "bia"]
maiusculos = []
for nome in nomes:
    maiusculos.append(nome.upper())
```

> 💡 O `for` é a estrutura de repetição mais usada em Python. Se você sabe
> percorrer, você já resolveu metade dos problemas com listas.
""",
                [
                    code(
                        "Some os números de 1 a 5 usando um `for` com `range(1, 6)` e guarde o total em `soma`.",
                        "soma = 0\nfor i in range(1, 6):\n    soma = soma + i",
                        "assert 'soma' in dir(), 'Crie a variável soma'\nassert soma == 15, f'soma deveria ser 15, mas é {soma!r}'",
                    ),
                    code(
                        "Dada a lista `nomes`, crie uma lista `maiusculos` (vazia no começo) e adicione cada nome em letras maiúsculas usando um `for` e `append`.",
                        "nomes = [\"ana\", \"bia\"]\nmaiusculos = []\nfor nome in nomes:\n    maiusculos.append(nome.upper())",
                        "assert 'maiusculos' in dir(), 'Crie a lista maiusculos'\nassert maiusculos == ['ANA', 'BIA'], f'maiusculos ficou: {maiusculos!r}'",
                        starter_code="nomes = [\"ana\", \"bia\"]\nmaiusculos = []\n# percorra nomes e adicione em maiusculos\n",
                    ),
                    code(
                        "Dada a lista `numeros`, crie `dobros` (vazia) e adicione o dobro de cada número usando um `for`.",
                        "numeros = [1, 2, 3]\ndobros = []\nfor n in numeros:\n    dobros.append(n * 2)",
                        "assert 'dobros' in dir(), 'Crie a lista dobros'\nassert dobros == [2, 4, 6], f'dobros ficou: {dobros!r}'",
                        starter_code="numeros = [1, 2, 3]\ndobros = []\n# percorra numeros e adicione o dobro\n",
                    ),
                    quiz(
                        "O que `range(1, 4)` gera?",
                        "1, 2, 3",
                        ["1, 2, 3", "1, 2, 3, 4", "0, 1, 2"],
                    ),
                    quiz(
                        "O que `range(3)` gera?",
                        "0, 1, 2",
                        ["0, 1, 2", "1, 2, 3", "0, 1, 2, 3"],
                    ),
                    quiz(
                        "O `for` pode percorrer quais tipos de valor?",
                        "Listas, strings e range",
                        ["Listas, strings e range", "Somente números inteiros", "Somente dicionários"],
                    ),
                ],
            ),
            topic(
                "loops-while",
                "Repetição com while",
                """
# Repetição com while

O `while` repete **enquanto** uma condição for verdadeira. Ao contrário do
`for`, que já sabe quantas vezes vai rodar, o `while` repete até a condição
mudar:

```python
contador = 1
while contador <= 3:
    print(contador)
    contador = contador + 1
```

Saída: `1`, `2`, `3`.

## O perigo do loop infinito

Se a condição nunca ficar falsa, o programa **nunca para**:

```python
contador = 1
while contador <= 3:     # esqueceu de atualizar contador!
    print("infinito")
```

Todo `while` precisa de um jeito de tornar a condição falsa em algum momento —
geralmente atualizando a variável da condição dentro do laço.

## Usando um valor sentinela

Um padrão comum é repetir até o usuário digitar um valor de parada:

```python
resposta = ""
while resposta != "sair":
    resposta = input("Digite algo (sair para parar): ")
```

> 💡 Regra prática: se você **sabe quantas vezes** repetir, use `for`; se a
> repetição depende de **uma condição**, use `while`.
""",
                [
                    code(
                        "Use um `while` para somar 1 + 2 + ... + 10. Guarde o resultado em `soma`.",
                        "soma = 0\ncontador = 1\nwhile contador <= 10:\n    soma = soma + contador\n    contador = contador + 1",
                        "assert 'soma' in dir(), 'Crie a variável soma'\nassert soma == 55, f'soma deveria ser 55, mas é {soma!r}'",
                    ),
                    code(
                        "Dada a variável `limite = 3`, use um `while` para contar de 1 até `limite`, adicionando cada número à lista `vistos`.",
                        "limite = 3\nvistos = []\ncontador = 1\nwhile contador <= limite:\n    vistos.append(contador)\n    contador = contador + 1",
                        "assert 'vistos' in dir(), 'Crie a lista vistos'\nassert vistos == [1, 2, 3], f'vistos ficou: {vistos!r}'",
                        starter_code="limite = 3\nvistos = []\n# use um while para preencher vistos\n",
                    ),
                    quiz(
                        "O que causa um loop infinito num `while`?",
                        "A condição nunca se torna falsa",
                        ["A condição nunca se torna falsa", "Usar range no while", "Escrever o corpo com indentação"],
                    ),
                    quiz(
                        "Quando usar `for` em vez de `while`?",
                        "Quando já sei quantas vezes quero repetir",
                        ["Quando já sei quantas vezes quero repetir", "Quando quero repetir até uma condição mudar", "Sempre, o while é obsoleto"],
                    ),
                    quiz(
                        "No código `while contador <= 3`, o que precisa acontecer dentro do laço para ele terminar?",
                        "contador precisa aumentar até passar de 3",
                        ["contador precisa aumentar até passar de 3", "Nada, ele termina sozinho", "O print precisa vir primeiro"],
                    ),
                    text(
                        "Complete: o `while` repete ___ a condição for verdadeira.",
                        "enquanto",
                    ),
                ],
            ),
            topic(
                "break-e-continue",
                "break e continue",
                """
# break e continue

Duas palavras-chave controlam o fluxo **dentro** de um laço (`for` ou `while`).

## break: para o laço inteiro

Quando `break` é executado, o laço **termina na hora**, mesmo que a condição
ainda seja verdadeira:

```python
for numero in [1, 2, 3, 4, 5]:
    if numero == 3:
        break
    print(numero)      # só imprime 1 e 2
```

## continue: pula para a próxima repetição

`continue` **interrompe a repetição atual** e vai direto para a próxima,
pulando o que vier depois dele:

```python
for numero in range(1, 6):
    if numero % 2 == 0:
        continue       # pula os pares
    print(numero)      # imprime 1, 3, 5
```

## Resumo

| Palavra | O que faz |
|---|---|
| `break` | encerra o laço imediatamente |
| `continue` | pula a volta atual e vai para a próxima |

> 💡 Ambos funcionam em `for` e em `while`. Use com moderação — código cheio
> de `break`/`continue` fica difícil de acompanhar.
""",
                [
                    code(
                        "Percorra `numeros = [1, 2, 3, 4, 5]` e use `break` para parar quando encontrar o `3`. Guarde o último valor percorrido em `ultimo`.",
                        "numeros = [1, 2, 3, 4, 5]\nultimo = 0\nfor n in numeros:\n    ultimo = n\n    if n == 3:\n        break",
                        "assert 'ultimo' in dir(), 'Crie a variável ultimo'\nassert ultimo == 3, f'ultimo deveria ser 3, mas é {ultimo!r}'",
                        starter_code="numeros = [1, 2, 3, 4, 5]\n# use break para parar no 3 e guarde em ultimo\n",
                    ),
                    code(
                        "De 1 a 10, use `continue` para pular os números pares e some apenas os ímpares. Guarde o total em `soma`.",
                        "soma = 0\nfor n in range(1, 11):\n    if n % 2 == 0:\n        continue\n    soma = soma + n",
                        "assert 'soma' in dir(), 'Crie a variável soma'\nassert soma == 25, f'soma deveria ser 25, mas é {soma!r}'",
                    ),
                    code(
                        "Percorra `letras = [\"a\", \"b\", \"x\", \"c\"]` e, usando `break`, pare ao encontrar `\"x\"`. Guarde em `achou` o valor `True` se encontrou (o loop para porque achou).",
                        "letras = [\"a\", \"b\", \"x\", \"c\"]\nachou = False\nfor l in letras:\n    if l == \"x\":\n        achou = True\n        break",
                        "assert 'achou' in dir(), 'Crie a variável achou'\nassert achou == True, 'achou deveria ser True'",
                        starter_code="letras = [\"a\", \"b\", \"x\", \"c\"]\nachou = False\n# percorra e use break ao encontrar x\n",
                    ),
                    quiz(
                        "O que o comando `break` faz dentro de um laço?",
                        "Encerra o laço imediatamente",
                        ["Encerra o laço imediatamente", "Pula apenas a volta atual", "Reinicia o laço do zero"],
                    ),
                    quiz(
                        "O que o comando `continue` faz dentro de um laço?",
                        "Pula a volta atual e vai para a próxima",
                        ["Pula a volta atual e vai para a próxima", "Encerra o laço", "Sai do programa"],
                    ),
                    quiz(
                        "`break` e `continue` funcionam em quais estruturas?",
                        "Tanto em `for` quanto em `while`",
                        ["Tanto em `for` quanto em `while`", "Somente em `for`", "Somente em `while`"],
                    ),
                ],
            ),
        ],
    )


# ============================================================
# MODULO 5 - Estruturas de Dados (reescrito, Fase 3 do roteiro)
# Código. Expande o módulo existente e recebe as comprehensions
# que estavam em Estruturas de Controle.
# ============================================================

def build_modulo_dados():
    return module(
        "estruturas-de-dados",
        "Módulo 5 — Estruturas de Dados",
        "Guardar e organizar valores: listas, tuplas, sets, dicionários e comprehensions — as coleções que o Python usa no dia a dia.",
        [
            topic(
                "listas",
                "Listas",
                """
# Listas

Uma **lista** guarda vários valores em ordem, entre colchetes:

```python
frutas = ["maçã", "banana", "uva"]
```

## Acessando posições

A lista é indexada a partir de **0**. Índices negativos contam do fim:

```python
frutas[0]    # "maçã"
frutas[2]    # "uva"
frutas[-1]   # "uva"  (o último)
```

## Modificando listas

```python
frutas.append("pera")        # adiciona no fim
frutas.remove("banana")      # remove pelo valor
frutas[0] = "manga"          # troca uma posição
len(frutas)                  # quantos elementos
"uva" in frutas              # True (pertinência)
```

## Fatiamento (slicing)

`lista[inicio:fim]` pega do `inicio` até `fim - 1`:

```python
numeros = [10, 20, 30, 40]
numeros[1:3]   # [20, 30]
```

> 💡 Listas são **mutáveis**: dá para alterar, adicionar e remover depois de
> criadas — ao contrário das tuplas (próximo tópico).
""",
                [
                    code(
                        "Crie uma lista `frutas` com `\"maçã\"`, `\"banana\"` e `\"uva\"`, e depois adicione `\"pera\"` com `append`.",
                        "frutas = [\"maçã\", \"banana\", \"uva\"]\nfrutas.append(\"pera\")",
                        "assert 'frutas' in dir(), 'Crie a lista frutas'\nassert frutas == ['maçã', 'banana', 'uva', 'pera'], f'frutas ficou: {frutas!r}'",
                    ),
                    code(
                        "Dada a lista `nomes = [\"Ana\", \"Bia\", \"Caio\"]`, crie `primeiro` com o primeiro nome e `ultimo` com o último (use índice negativo).",
                        "nomes = [\"Ana\", \"Bia\", \"Caio\"]\nprimeiro = nomes[0]\nultimo = nomes[-1]",
                        "assert 'primeiro' in dir(), 'Crie a variável primeiro'\nassert primeiro == 'Ana', f'primeiro deveria ser Ana, mas é {primeiro!r}'\nassert 'ultimo' in dir(), 'Crie a variável ultimo'\nassert ultimo == 'Caio', f'ultimo deveria ser Caio, mas é {ultimo!r}'",
                        starter_code="nomes = [\"Ana\", \"Bia\", \"Caio\"]\n# crie primeiro e ultimo\n",
                    ),
                    code(
                        "Dada a lista `numeros = [10, 20, 30, 40, 50]`, crie `fatia` com os elementos das posições 1 a 3 (use slicing).",
                        "numeros = [10, 20, 30, 40, 50]\nfatia = numeros[1:3]",
                        "assert 'fatia' in dir(), 'Crie a variável fatia'\nassert fatia == [20, 30], f'fatia ficou: {fatia!r}'",
                        starter_code="numeros = [10, 20, 30, 40, 50]\n# crie fatia com slicing\n",
                    ),
                    code(
                        "Dada a lista `cidades = [\"SP\", \"RJ\", \"MG\"]`, crie a variável `tem_mg` verificando se `\"MG\"` está na lista (use `in`).",
                        "cidades = [\"SP\", \"RJ\", \"MG\"]\ntem_mg = \"MG\" in cidades",
                        "assert 'tem_mg' in dir(), 'Crie a variável tem_mg'\nassert tem_mg == True, 'tem_mg deveria ser True'",
                        starter_code="cidades = [\"SP\", \"RJ\", \"MG\"]\n# crie tem_mg com o operador in\n",
                    ),
                    quiz(
                        "Qual o resultado de `numeros = [10, 20, 30]` e depois `numeros[-1]`?",
                        "30",
                        ["30", "10", "um erro"],
                    ),
                    quiz(
                        "Qual método adiciona um elemento no fim de uma lista?",
                        "append()",
                        ["append()", "add()", "insert_end()"],
                    ),
                    quiz(
                        "Qual o resultado de `len([1, 2, 3, 4])`?",
                        "4",
                        ["4", "3", "um erro"],
                    ),
                ],
            ),
            topic(
                "tuplas-e-sets",
                "Tuplas e sets",
                """
# Tuplas e sets

## Tupla: sequência imutável

Uma **tupla** guarda valores em ordem como uma lista, mas **não pode ser
modificada** depois de criada. Usa parênteses:

```python
ponto = (3, 5)
ponto[0]       # 3
ponto[0] = 9   # ERRO! tuplas são imutáveis
```

Use tuplas para dados que não devem mudar (ex.: coordenadas, configurações).

## Set: conjunto sem duplicados

Um **set** guarda valores **únicos** (sem repetição) e usa chaves:

```python
cores = {"vermelho", "azul", "vermelho"}
# cores fica {"vermelho", "azul"} — a duplicada foi descartada
len(cores)       # 2
"azul" in cores  # True (verificar pertinência é muito rápido)
```

O set **não tem ordem garantida** — não use índices nele.

## Resumo

| Coleção | Ordenada | Mutável | Duplicados |
|---|---|---|---|
| lista `[]` | sim | sim | sim |
| tupla `()` | sim | não | sim |
| set `{}` | não | sim | não |
""",
                [
                    code(
                        "Crie uma tupla `ponto = (3, 5)` e depois crie `x` com a primeira coordenada.",
                        "ponto = (3, 5)\nx = ponto[0]",
                        "assert 'x' in dir(), 'Crie a variável x'\nassert x == 3, f'x deveria ser 3, mas é {x!r}'",
                    ),
                    code(
                        "A partir da lista `numeros = [1, 1, 2, 3, 3, 3]`, crie um set `unicos` com os valores sem repetição e guarde o total de únicos em `total`.",
                        "numeros = [1, 1, 2, 3, 3, 3]\nunicos = set(numeros)\ntotal = len(unicos)",
                        "assert 'unicos' in dir(), 'Crie o set unicos'\nassert unicos == {1, 2, 3}, f'unicos ficou: {unicos!r}'\nassert 'total' in dir(), 'Crie a variável total'\nassert total == 3, f'total deveria ser 3, mas é {total!r}'",
                        starter_code="numeros = [1, 1, 2, 3, 3, 3]\n# crie unicos e total\n",
                    ),
                    code(
                        "Dado o set `cores = {\"azul\", \"verde\"}`, adicione `\"vermelho\"` com `add`.",
                        "cores = {\"azul\", \"verde\"}\ncores.add(\"vermelho\")",
                        "assert 'cores' in dir(), 'Crie o set cores'\nassert cores == {\"azul\", \"verde\", \"vermelho\"}, f'cores ficou: {cores!r}'",
                        starter_code="cores = {\"azul\", \"verde\"}\n# adicione vermelho com add\n",
                    ),
                    quiz(
                        "Qual das coleções é IMUTÁVEL (não pode ser modificada depois de criada)?",
                        "Tupla",
                        ["Tupla", "Lista", "Set"],
                    ),
                    quiz(
                        "O que acontece se você tentar `tupla[0] = 5`?",
                        "Levanta um erro (TypeError)",
                        ["Levanta um erro (TypeError)", "Funciona normalmente", "Converte a tupla em lista"],
                    ),
                    quiz(
                        "O que um `set` faz com valores repetidos?",
                        "Descarta as duplicatas, mantendo um único",
                        ["Descarta as duplicatas, mantendo um único", "Mantém todos, na ordem", "Levanta um erro"],
                    ),
                ],
            ),
            topic(
                "dicionarios",
                "Dicionários",
                """
# Dicionários

Um **dicionário** guarda pares **chave: valor** — como uma lista telefônica,
onde o nome (chave) aponta para o número (valor). Usa chaves e dois-pontos:

```python
aluno = {"nome": "Ana", "idade": 20}
```

## Acessando e modificando

```python
aluno["nome"]            # "Ana"
aluno["cidade"] = "SP"   # adiciona uma chave nova
aluno["idade"] = 21      # atualiza um valor
```

## Métodos úteis

```python
aluno.keys()      # as chaves
aluno.values()    # os valores
aluno.items()     # pares (chave, valor)
aluno.get("nome", "não informado")   # valor com padrão
```

A chave é usada como **índice** — diferente da lista, que usa posições.

## Percorrendo um dicionário

```python
for chave, valor in aluno.items():
    print(chave, "->", valor)
```

> 💡 O `get()` evita o erro `KeyError` quando a chave pode não existir: em vez
> de quebrar, ele devolve o valor padrão.
""",
                [
                    code(
                        "Crie um dicionário `usuario` com chave `\"nome\"` valendo `\"Ana\"` e chave `\"idade\"` valendo `20`.",
                        "usuario = {\"nome\": \"Ana\", \"idade\": 20}",
                        "assert 'usuario' in dir(), 'Crie o dicionário usuario'\nassert usuario['nome'] == 'Ana', f'nome deveria ser Ana, mas é {usuario[\"nome\"]!r}'\nassert usuario['idade'] == 20, f'idade deveria ser 20, mas é {usuario[\"idade\"]!r}'",
                    ),
                    code(
                        "Dado o dicionário `aluno`, adicione a chave `\"curso\"` com o valor `\"Python\"`.",
                        "aluno = {\"nome\": \"Ana\"}\naluno[\"curso\"] = \"Python\"",
                        "assert 'aluno' in dir(), 'Crie o dicionário aluno'\nassert aluno.get('curso') == 'Python', f'curso deveria ser Python, mas é {aluno.get(\"curso\")!r}'",
                        starter_code="aluno = {\"nome\": \"Ana\"}\n# adicione a chave curso\n",
                    ),
                    code(
                        "Dado o dicionário `produto`, crie `preco` usando `get` para a chave `\"preco\"`, e `desconhecido` usando `get` para a chave `\"cor\"` com padrão `\"sem cor\"`.",
                        "produto = {\"nome\": \"Camiseta\", \"preco\": 29.9}\npreco = produto.get(\"preco\")\ndesconhecido = produto.get(\"cor\", \"sem cor\")",
                        "assert 'preco' in dir(), 'Crie a variável preco'\nassert preco == 29.9, f'preco deveria ser 29.9, mas é {preco!r}'\nassert 'desconhecido' in dir(), 'Crie a variável desconhecido'\nassert desconhecido == 'sem cor', f'desconhecido deveria ser sem cor, mas é {desconhecido!r}'",
                        starter_code="produto = {\"nome\": \"Camiseta\", \"preco\": 29.9}\n# crie preco e desconhecido com get\n",
                    ),
                    code(
                        "Dado o dicionário `aluno`, crie a variável `total_chaves` com a quantidade de chaves (use `len`).",
                        "aluno = {\"nome\": \"Ana\", \"idade\": 20, \"curso\": \"Python\"}\ntotal_chaves = len(aluno)",
                        "assert 'total_chaves' in dir(), 'Crie a variável total_chaves'\nassert total_chaves == 3, f'total_chaves deveria ser 3, mas é {total_chaves!r}'",
                        starter_code="aluno = {\"nome\": \"Ana\", \"idade\": 20, \"curso\": \"Python\"}\n# crie total_chaves\n",
                    ),
                    quiz(
                        "Num dicionário, o acesso é feito por:",
                        "chave",
                        ["chave", "posição (índice)", "endereço de memória"],
                    ),
                    quiz(
                        "Para que serve `dicionario.get(\"chave\", \"padrão\")`?",
                        "Devolver o valor da chave ou um padrão se ela não existir",
                        ["Devolver o valor da chave ou um padrão se ela não existir", "Adicionar a chave com o padrão", "Apagar a chave"],
                    ),
                    quiz(
                        "O método `items()` de um dicionário devolve:",
                        "pares (chave, valor)",
                        ["pares (chave, valor)", "apenas as chaves", "apenas os valores"],
                    ),
                ],
            ),
            topic(
                "comprehensions",
                "Comprehensions",
                """
# Comprehensions

Uma **comprehension** cria uma lista (ou dict, ou set) de forma compacta, com
uma única expressão em vez de um `for` completo. É o jeito pythônico de
construir coleções.

## Lista a partir de um for

O padrão abaixo (criar lista vazia + for + append):

```python
quadrados = []
for x in range(1, 6):
    quadrados.append(x ** 2)
```

vira uma linha só:

```python
quadrados = [x ** 2 for x in range(1, 6)]
# [1, 4, 9, 16, 25]
```

## Com condição (if)

Adicione um `if` no fim para filtrar:

```python
pares = [x for x in range(1, 11) if x % 2 == 0]
# [2, 4, 6, 8, 10]
```

## Também dá para dicionários e sets

```python
dobros = {x: x * 2 for x in range(1, 4)}
# {1: 2, 2: 4, 3: 6}

unicos = {letra for letra in "banana"}
# {'b', 'a', 'n'}
```

> 💡 Estrutura: `[expressão for item in sequência if condição]`. A expressão é
> o que cada elemento da nova coleção vai conter.
""",
                [
                    code(
                        "Crie a lista `quadrados` com os quadrados de 1 a 5 usando uma comprehension (`[x ** 2 for x in range(1, 6)]`).",
                        "quadrados = [x ** 2 for x in range(1, 6)]",
                        "assert 'quadrados' in dir(), 'Crie a lista quadrados'\nassert quadrados == [1, 4, 9, 16, 25], f'quadrados ficou: {quadrados!r}'",
                    ),
                    code(
                        "Crie a lista `pares` com os números pares de 1 a 10 usando uma comprehension com `if`.",
                        "pares = [x for x in range(1, 11) if x % 2 == 0]",
                        "assert 'pares' in dir(), 'Crie a lista pares'\nassert pares == [2, 4, 6, 8, 10], f'pares ficou: {pares!r}'",
                    ),
                    code(
                        "Dada a lista `nomes = [\"ana\", \"bia\"]`, crie a lista `maiusculos` com os nomes em maiúsculo usando uma comprehension.",
                        "nomes = [\"ana\", \"bia\"]\nmaiusculos = [n.upper() for n in nomes]",
                        "assert 'maiusculos' in dir(), 'Crie a lista maiusculos'\nassert maiusculos == ['ANA', 'BIA'], f'maiusculos ficou: {maiusculos!r}'",
                        starter_code="nomes = [\"ana\", \"bia\"]\n# crie maiusculos com uma comprehension\n",
                    ),
                    quiz(
                        "Qual o resultado de `[x * 2 for x in range(3)]`?",
                        "[0, 2, 4]",
                        ["[0, 2, 4]", "[2, 4, 6]", "[1, 2, 3]"],
                    ),
                    quiz(
                        "Na comprehension `[x for x in range(10) if x > 5]`, o que o `if` faz?",
                        "Filtra: só entram os valores maiores que 5",
                        ["Filtra: só entram os valores maiores que 5", "Duplica os valores", "Encerra a lista no 5"],
                    ),
                    text(
                        "Complete a estrutura: `[expressão for item in sequência ___ condição]`.",
                        "if",
                    ),
                ],
            ),
        ],
    )


# ============================================================
# MODULO 6 - Funções (novo, Fase 4 do roteiro)
# Código. Substitui o tópico raso "funcoes" de organizando-o-codigo.
# ============================================================

def build_modulo_funcoes():
    return module(
        "funcoes",
        "Módulo 6 — Funções",
        "Empacotar lógica reutilizável: definir e chamar funções, parâmetros, escopo, retorno e argumentos variáveis.",
        [
            topic(
                "definindo-funcoes",
                "Definindo funções",
                """
# Definindo funções

Uma **função** é um bloco de código com nome, que roda quando você a **chama**.
Você a define uma vez e reutiliza quantas vezes quiser:

```python
def dobro(n):
    return n * 2
```

- `def` inicia a definição.
- `dobro` é o nome; `(n)` são os **parâmetros** (entradas).
- Os dois-pontos e a **indentação** marcam o corpo.
- `return` devolve um resultado para quem chamou.

Depois é só chamar:

```python
resultado = dobro(5)   # 10
```

## Exemplo: função que devolve texto

```python
def saudar(nome):
    return "Olá, " + nome + "!"

saudar("Ana")   # "Olá, Ana!"
```

> 💡 Sem `return`, a função devolve `None` implicitamente (mais no tópico de
> retorno). Por isso as funções acima usam `return` para entregar o resultado.
""",
                [
                    code(
                        "Defina uma função `dobro(n)` que retorna `n * 2`.",
                        "def dobro(n):\n    return n * 2",
                        "assert dobro(4) == 8, 'dobro(4) deveria ser 8'\nassert dobro(0) == 0, 'dobro(0) deveria ser 0'",
                    ),
                    code(
                        "Defina uma função `saudar(nome)` que retorna a string `Olá, <nome>!`.",
                        "def saudar(nome):\n    return \"Olá, \" + nome + \"!\"",
                        "assert saudar('Ana') == 'Olá, Ana!', f'saudar deu {saudar(\"Ana\")!r}'",
                    ),
                    code(
                        "Defina uma função `eh_par(n)` que retorna `True` se `n` for par e `False` caso contrário (use `%`).",
                        "def eh_par(n):\n    return n % 2 == 0",
                        "assert eh_par(4) == True, 'eh_par(4) deveria ser True'\nassert eh_par(3) == False, 'eh_par(3) deveria ser False'",
                    ),
                    quiz(
                        "Qual palavra inicia a definição de uma função em Python?",
                        "def",
                        ["def", "fun", "func"],
                    ),
                    quiz(
                        "O que a palavra `return` faz numa função?",
                        "Devolve um resultado para quem chamou",
                        ["Devolve um resultado para quem chamou", "Imprime o resultado na tela", "Encerra o programa"],
                    ),
                    quiz(
                        "Como você chama a função `dobro` passando o argumento 5?",
                        "dobro(5)",
                        ["dobro(5)", "call dobro 5", "dobro = 5"],
                    ),
                ],
            ),
            topic(
                "parametros-e-argumentos",
                "Parâmetros e argumentos",
                """
# Parâmetros e argumentos

**Parâmetros** são os nomes que a função declara; **argumentos** são os valores
que você passa na chamada.

## Argumentos posicionais

```python
def area(largura, altura):
    return largura * altura

area(4, 5)   # 20  — na ordem: largura=4, altura=5
```

## Argumentos nomeados (keyword)

```python
area(altura=5, largura=4)   # 20 — a ordem não importa
```

## Valores padrão (default)

Um parâmetro pode ter um valor padrão, usado quando nada é passado:

```python
def potencia(base, expoente=2):
    return base ** expoente

potencia(3)      # 9   (expoente padrão = 2)
potencia(2, 3)   # 8   (expoente = 3)
```

> 💡 Parâmetros com valor padrão vêm **depois** dos obrigatórios na definição.
> Na chamada, você pode misturar posicionais e nomeados — mas os posicionais
> primeiro.
""",
                [
                    code(
                        "Defina `potencia(base, expoente=2)` que retorna `base ** expoente`.",
                        "def potencia(base, expoente=2):\n    return base ** expoente",
                        "assert potencia(3) == 9, 'potencia(3) deveria ser 9'\nassert potencia(2, 3) == 8, 'potencia(2, 3) deveria ser 8'",
                    ),
                    code(
                        "Defina `area(largura, altura)` que retorna `largura * altura`.",
                        "def area(largura, altura):\n    return largura * altura",
                        "assert area(4, 5) == 20, 'area(4, 5) deveria ser 20'\nassert area(altura=2, largura=7) == 14, 'area nomeada deveria ser 14'",
                    ),
                    code(
                        "Defina `apresentar(nome, cidade=\"desconhecida\")` que retorna a string `f\"{nome} é de {cidade}\"`.",
                        "def apresentar(nome, cidade=\"desconhecida\"):\n    return f\"{nome} é de {cidade}\"",
                        "assert apresentar('Ana') == 'Ana é de desconhecida', f'deu {apresentar(\"Ana\")!r}'\nassert apresentar('Bia', 'SP') == 'Bia é de SP', f'deu {apresentar(\"Bia\", \"SP\")!r}'",
                    ),
                    quiz(
                        "Na definição `def area(largura, altura)`, `largura` e `altura` são:",
                        "parâmetros",
                        ["parâmetros", "argumentos", "retornos"],
                    ),
                    quiz(
                        "Na chamada `area(4, 5)`, os valores 4 e 5 são:",
                        "argumentos",
                        ["argumentos", "parâmetros", "variáveis globais"],
                    ),
                    quiz(
                        "`potencia(3)` com a função `def potencia(base, expoente=2)`:",
                        "usa o valor padrão 2 do expoente",
                        ["usa o valor padrão 2 do expoente", "levanta um erro", "retorna None"],
                    ),
                ],
            ),
            topic(
                "escopo-de-variaveis",
                "Escopo de variáveis",
                """
# Escopo de variáveis

O **escopo** define onde uma variável é visível.

## Variável local

Uma variável criada **dentro** de uma função é **local**: ela só existe ali,
enquanto a função roda. Não dá para usá-la fora:

```python
def soma_locais(a, b):
    resultado = a + b   # local!
    return resultado

soma_locais(3, 4)       # 7
print(resultado)        # NameError — resultado não existe aqui fora!
```

## Variável global

Uma variável criada no **nível principal** do programa é **global**: pode ser
lida de dentro das funções:

```python
saudacao = "Olá"        # global

def mensagem():
    return saudacao     # lê a global

mensagem()   # "Olá"
```

> ⚠️ Ler uma global é normal; **modificar** uma global dentro de função exige
> `global` (e geralmente é má prática). Prefira passar valores como parâmetros
> e devolver resultados via `return`.
""",
                [
                    code(
                        "Defina `soma_locais(a, b)` que cria uma variável local `resultado` dentro da função, calculando `a + b`, e a retorna.",
                        "def soma_locais(a, b):\n    resultado = a + b\n    return resultado",
                        "assert soma_locais(3, 4) == 7, 'soma_locais(3, 4) deveria ser 7'\nassert 'resultado' not in dir(), 'resultado não deveria vazar para fora da função'",
                    ),
                    code(
                        "Defina uma função `mensagem()` que retorna o valor da variável global `saudacao`. (A global já existe no starter.)",
                        "saudacao = \"Olá\"\ndef mensagem():\n    return saudacao",
                        "assert mensagem() == 'Olá', f'mensagem() deveria retornar a global, mas deu {mensagem()!r}'",
                        starter_code="saudacao = \"Olá\"\n# defina mensagem() que retorna saudacao\n",
                    ),
                    quiz(
                        "Uma variável criada dentro de uma função é visível fora dela?",
                        "Não, ela é local e some ao terminar a função",
                        ["Não, ela é local e some ao terminar a função", "Sim, sempre", "Só se começar com letra maiúscula"],
                    ),
                    quiz(
                        "O que acontece ao tentar usar fora da função uma variável local?",
                        "Levanta NameError (variável não existe)",
                        ["Levanta NameError (variável não existe)", "Retorna None", "Cria a variável automaticamente"],
                    ),
                    quiz(
                        "Uma variável criada no nível principal do programa é chamada de:",
                        "global",
                        ["global", "local", "privada"],
                    ),
                    text(
                        "Complete: uma variável local é visível somente ___ da função.",
                        "dentro",
                    ),
                ],
            ),
            topic(
                "retornando-valores",
                "Retornando valores",
                """
# Retornando valores

O `return` entrega um resultado para quem chamou. Funções **sem** `return`
devolvem `None` (o "nada" do Python).

## Múltiplos retornos

Um `return` pode devolver vários valores de uma vez — na prática, uma **tupla**
que é desempacotada na chamada:

```python
def divisao(n, d):
    return n // d, n % d

quociente, resto = divisao(17, 5)
# quociente = 3, resto = 2
```

## Função sem return devolve None

```python
def so_imprime():
    print("oi")

resultado = so_imprime()
print(resultado)   # None
```

## Desempacotando na chamada

```python
def min_max(lista):
    return min(lista), max(lista)

menor, maior = min_max([4, 1, 9, 3])
# menor = 1, maior = 9
```

> 💡 `None` é um valor como outro qualquer — dá para comparar com `is None` e
> guardar em variável. É o padrão usado para "essa função não devolve nada".
""",
                [
                    code(
                        "Defina `divisao(n, d)` que retorna dois valores: o quociente inteiro (`n // d`) e o resto (`n % d`).",
                        "def divisao(n, d):\n    return n // d, n % d",
                        "q, r = divisao(17, 5)\nassert (q, r) == (3, 2), f'divisao(17, 5) deveria ser (3, 2), mas deu {(q, r)!r}'",
                    ),
                    code(
                        "Defina `min_max(lista)` que retorna o menor e o maior valor da lista.",
                        "def min_max(lista):\n    return min(lista), max(lista)",
                        "menor, maior = min_max([4, 1, 9, 3])\nassert menor == 1, 'menor deveria ser 1'\nassert maior == 9, 'maior deveria ser 9'",
                    ),
                    code(
                        "Defina `sem_retorno()` que apenas faz `print(\"oi\")` (sem `return`) e depois crie `resultado = sem_retorno()`.",
                        "def sem_retorno():\n    print(\"oi\")\nresultado = sem_retorno()",
                        "assert resultado is None, 'função sem return deve devolver None'",
                    ),
                    quiz(
                        "O que uma função devolve quando não tem `return`?",
                        "None",
                        ["None", "0", "um erro"],
                    ),
                    quiz(
                        "`a, b = funcao()` — esse padrão é chamado de:",
                        "desempacotamento de tupla",
                        ["desempacotamento de tupla", "concatenação de listas", "sobrecarga de função"],
                    ),
                    quiz(
                        "Como você retorna vários valores de uma só vez?",
                        "return valor1, valor2",
                        ["return valor1, valor2", "return [valor1, valor2]", "print(valor1); return valor2"],
                    ),
                ],
            ),
            topic(
                "args-e-kwargs",
                "*args e **kwargs",
                """
# *args e **kwargs

Às vezes a função precisa aceitar uma quantidade **variável** de argumentos.
O Python resolve isso com `*args` e `**kwargs`.

## *args: N argumentos posicionais

O `*args` junta todos os argumentos posicionais extras numa **tupla**:

```python
def soma_todos(*numeros):
    total = 0
    for n in numeros:
        total = total + n
    return total

soma_todos(1, 2, 3)      # 6
soma_todos(10, 20)       # 30
```

## **kwargs: N argumentos nomeados

O `**kwargs` junta os argumentos nomeados extras num **dicionário**:

```python
def quantos(**campos):
    return len(campos)

quantos(nome="Ana", idade=20)   # 2
```

## Usando os dois juntos

```python
def configura(prefixo, *args, **kwargs):
    # prefixo é obrigatório; args e kwargs são extras
    ...
```

> 💡 O nome `args`/`kwargs` é convenção — o que importa são os `*`/`**`.
> `*` = "junte os posicionais em tupla"; `**` = "junte os nomeados em dict".
""",
                [
                    code(
                        "Defina `soma_todos(*numeros)` que soma todos os argumentos passados e retorna o total.",
                        "def soma_todos(*numeros):\n    total = 0\n    for n in numeros:\n        total = total + n\n    return total",
                        "assert soma_todos(1, 2, 3) == 6, 'soma_todos(1, 2, 3) deveria ser 6'\nassert soma_todos(10, 20, 30, 40) == 100, 'soma_todos(10,20,30,40) deveria ser 100'",
                    ),
                    code(
                        "Defina `quantos(**campos)` que retorna o número de argumentos nomeados passados (use `len(campos)`).",
                        "def quantos(**campos):\n    return len(campos)",
                        "assert quantos(nome=\"Ana\", idade=20) == 2, 'quantos deveria ser 2'\nassert quantos(a=1) == 1, 'quantos deveria ser 1'",
                    ),
                    quiz(
                        "O que `*args` representa?",
                        "argumentos posicionais em quantidade variável",
                        ["argumentos posicionais em quantidade variável", "argumentos nomeados em quantidade variável", "um argumento chamado args obrigatório"],
                    ),
                    quiz(
                        "O que `**kwargs` representa?",
                        "argumentos nomeados em quantidade variável",
                        ["argumentos nomeados em quantidade variável", "argumentos posicionais em quantidade variável", "um dicionário fixo"],
                    ),
                    quiz(
                        "`*args` chega dentro da função como:",
                        "uma tupla",
                        ["uma tupla", "uma lista", "um dicionário"],
                    ),
                    quiz(
                        "`**kwargs` chega dentro da função como:",
                        "um dicionário",
                        ["um dicionário", "uma tupla", "uma string"],
                    ),
                ],
            ),
        ],
    )


# ============================================================
# MODULO 7 - Tratamento de Erros (novo, Fase 4 do roteiro)
# Código. Substitui o tópico raso "tratamento-de-erros" de
# organizando-o-codigo (o slug do tópico vira o slug do módulo).
# ============================================================

def build_modulo_erros():
    return module(
        "tratamento-de-erros",
        "Módulo 7 — Tratamento de Erros",
        "Erros não precisam derrubar o programa: conhecer as exceções, capturá-las com try/except, e levantá-las quando algo dá errado.",
        [
            topic(
                "tipos-de-erro",
                "Tipos de erro (exceções)",
                """
# Tipos de erro (exceções)

Quando o Python encontra um problema, ele **levanta uma exceção** e o programa
para — a menos que você a capture (próximo tópico). Conhecer os nomes das
exceções mais comuns ajuda a entender e consertar erros rápido.

| Exceção | Quando acontece | Exemplo |
|---|---|---|
| `SyntaxError` | erro na estrutura do código (antes mesmo de rodar) | esquecer os `:` do `if` |
| `NameError` | usar uma variável que não existe | `print(idade)` sem criar `idade` |
| `TypeError` | operação inválida entre tipos | `"5" + 5` |
| `ValueError` | valor inválido para a função | `int("abc")` |
| `ZeroDivisionError` | dividir por zero | `10 / 0` |
| `IndexError` | acessar posição fora da lista | `[1, 2][5]` |
| `KeyError` | acessar chave que não existe no dict | `{"a": 1}["b"]` |

## Como ler um erro

O erro vem com uma mensagem e um **traceback** (a trilha de onde o erro
aconteceu). A última linha é a mais importante: o tipo e a mensagem.

> 💡 Não decore os nomes — basta saber que **existem** e que a mensagem do
> traceback quase sempre diz o que fazer.
""",
                [
                    quiz(
                        "Qual exceção acontece ao tentar dividir por zero?",
                        "ZeroDivisionError",
                        ["ZeroDivisionError", "TypeError", "ValueError"],
                    ),
                    quiz(
                        "Qual exceção acontece ao usar uma variável que não foi definida?",
                        "NameError",
                        ["NameError", "SyntaxError", "KeyError"],
                    ),
                    quiz(
                        "Qual exceção acontece ao fazer `\"5\" + 5`?",
                        "TypeError",
                        ["TypeError", "ValueError", "NameError"],
                    ),
                    quiz(
                        "Qual exceção acontece ao fazer `int(\"abc\")`?",
                        "ValueError",
                        ["ValueError", "TypeError", "IndexError"],
                    ),
                    quiz(
                        "Qual exceção acontece quando falta o `:` depois do `if`?",
                        "SyntaxError",
                        ["SyntaxError", "NameError", "ZeroDivisionError"],
                    ),
                    quiz(
                        "Qual exceção acontece ao acessar `[1, 2][5]`?",
                        "IndexError",
                        ["IndexError", "KeyError", "ValueError"],
                    ),
                    text(
                        "Complete: `ZeroDivisionError` acontece ao dividir por ___.",
                        "zero",
                    ),
                ],
            ),
            topic(
                "try-except",
                "Capturando erros com try / except",
                """
# Capturando erros com try / except

Nem todo erro precisa derrubar o programa. Com `try`/`except` você **tenta**
rodar um código e **captura** o erro se ele acontecer:

```python
try:
    resultado = 10 / divisor
except ZeroDivisionError:
    resultado = 0
```

Se `divisor` for `0`, em vez de quebrar, `resultado` vira `0`.

## Capturando qualquer erro

Você pode usar `except` sem nome — captura qualquer exceção:

```python
try:
    numero = int(texto)
except:
    numero = 0
```

Mas o ideal é capturar **tipos específicos** primeiro, porque aí o código
consegue responder de forma diferente para cada situação.

## Capturando mais de um tipo

```python
try:
    numero = int(texto)
except (ValueError, TypeError):
    numero = 0
```

> 💡 O código do `try` roda normal se não houver erro; o `except` só entra
> quando a exceção acontece. Depois dele, o programa **continua** — essa é a
> grande vantagem.
""",
                [
                    code(
                        "Dado `divisor = 0`, use `try`/`except` para tentar `10 / divisor`. Se der `ZeroDivisionError`, `resultado` deve virar `0`.",
                        "divisor = 0\ntry:\n    resultado = 10 / divisor\nexcept ZeroDivisionError:\n    resultado = 0",
                        "assert 'resultado' in dir(), 'Crie a variável resultado'\nassert resultado == 0, f'resultado deveria ser 0, mas é {resultado!r}'",
                        starter_code="divisor = 0\n# escreva o try/except\n",
                    ),
                    code(
                        "Dado `texto = \"abc\"`, use `try`/`except` para tentar `int(texto)`. Se der `ValueError`, `numero` deve virar `0`.",
                        "texto = \"abc\"\ntry:\n    numero = int(texto)\nexcept ValueError:\n    numero = 0",
                        "assert 'numero' in dir(), 'Crie a variável numero'\nassert numero == 0, f'numero deveria ser 0, mas é {numero!r}'",
                        starter_code="texto = \"abc\"\n# escreva o try/except\n",
                    ),
                    code(
                        "Dado `divisor = 0`, use `try`/`except` (sem especificar o tipo) para tentar `10 / divisor`. Se der erro, `mensagem` deve virar `\"deu erro\"`.",
                        "divisor = 0\ntry:\n    10 / divisor\n    mensagem = \"ok\"\nexcept:\n    mensagem = \"deu erro\"",
                        "assert 'mensagem' in dir(), 'Crie a variável mensagem'\nassert mensagem == 'deu erro', f'mensagem deveria ser deu erro, mas é {mensagem!r}'",
                        starter_code="divisor = 0\n# escreva o try/except\n",
                    ),
                    quiz(
                        "Qual bloco é executado quando acontece um erro dentro do `try`?",
                        "except",
                        ["except", "else", "finally"],
                    ),
                    quiz(
                        "Se NÃO houver erro no `try`, o que acontece com o `except`?",
                        "Ele não é executado",
                        ["Ele não é executado", "Ele é executado mesmo assim", "Ele vira um loop"],
                    ),
                    quiz(
                        "Por que é melhor capturar tipos específicos (ex.: `except ValueError`) do que `except` genérico?",
                        "Porque o código consegue responder de forma diferente para cada erro",
                        ["Porque o código consegue responder de forma diferente para cada erro", "Porque genérico é proibido", "Porque genérico deixa o programa mais lento"],
                    ),
                    text(
                        "Complete: o programa ___ depois do except, em vez de quebrar.",
                        "continua",
                    ),
                ],
            ),
            topic(
                "else-e-finally",
                "else e finally",
                """
# else e finally

Além de `try` e `except`, um bloco de tratamento pode ter `else` e `finally`.

## else: roda só quando NÃO houve erro

```python
try:
    numero = int(texto)
except ValueError:
    numero = 0
else:
    print("Conversão funcionou!")
```

O `else` é o lugar certo para código que só deve rodar no sucesso — evita
colocar coisas no `try` que não precisam de proteção.

## finally: roda SEMPRE

O `finally` roda **com ou sem erro** — é usado para limpeza (fechar arquivo,
fechar conexão) que precisa acontecer de qualquer jeito:

```python
try:
    arquivo = open("dados.txt")
    conteudo = arquivo.read()
finally:
    arquivo.close()   # roda sempre, com ou sem erro
```

## Ordem completa

```python
try:
    ...
except:
    ...
else:
    ...   # só se não houve erro
finally:
    ...   # sempre
```

> 💡 Resumo: `except` captura o erro; `else` roda no sucesso; `finally` roda
> sempre. Essa ordem é o padrão do Python para lidar com recursos.
""",
                [
                    code(
                        "Complete com `try`/`except`/`else`: tente `int(\"5\")`. Se der `ValueError`, `status` vira `\"erro\"`; no `else`, `status` vira `\"ok\"`.",
                        "try:\n    int(\"5\")\nexcept ValueError:\n    status = \"erro\"\nelse:\n    status = \"ok\"",
                        "assert 'status' in dir(), 'Crie a variável status'\nassert status == 'ok', f'status deveria ser ok, mas é {status!r}'",
                    ),
                    code(
                        "Complete com `try`/`except`/`finally`: tente `1 / divisor`. Se der erro, `resultado` vira `0`. No `finally`, `rodou` vira `True`.",
                        "divisor = 0\ntry:\n    resultado = 1 / divisor\nexcept ZeroDivisionError:\n    resultado = 0\nfinally:\n    rodou = True",
                        "assert 'resultado' in dir(), 'Crie a variável resultado'\nassert resultado == 0, f'resultado deveria ser 0, mas é {resultado!r}'\nassert 'rodou' in dir() and rodou == True, 'rodou deveria ser True (finally sempre roda)'",
                        starter_code="divisor = 0\n# escreva o try/except/finally\n",
                    ),
                    quiz(
                        "Quando o bloco `else` de um `try`/`except` é executado?",
                        "Somente se nenhum erro aconteceu no try",
                        ["Somente se nenhum erro aconteceu no try", "Somente se houve erro", "Sempre, como o finally"],
                    ),
                    quiz(
                        "Quando o bloco `finally` é executado?",
                        "Sempre, tenha havido erro ou não",
                        ["Sempre, tenha havido erro ou não", "Somente se houve erro", "Somente se não houve erro"],
                    ),
                    quiz(
                        "Para que o `finally` costuma ser usado?",
                        "Limpeza que precisa rodar sempre (fechar arquivo, conexão)",
                        ["Limpeza que precisa rodar sempre (fechar arquivo, conexão)", "Guardar o resultado da operação", "Aumentar a velocidade do programa"],
                    ),
                ],
            ),
            topic(
                "levantando-erros",
                "Levantando erros com raise",
                """
# Levantando erros com raise

Além de **capturar** erros, você pode **levantar** os seus próprios erros com
`raise` — ótimo para validar entradas e dar mensagens claras:

```python
def idade_valida(n):
    if n < 0:
        raise ValueError("Idade não pode ser negativa")
    return n
```

Quando `idade_valida(-1)` é chamada, a exceção `ValueError` é levantada com a
mensagem `Idade não pode ser negativa` — quem chamou pode capturá-la com
`try`/`except`.

## Escolhendo a exceção certa

- `ValueError`: valor faz sentido mas é inválido para o contexto.
- `TypeError`: tipo errado.
- `RuntimeError`: algo deu errado em geral.

```python
def dividir(a, b):
    if b == 0:
        raise ZeroDivisionError("Divisor não pode ser zero")
    return a / b
```

## Capturando o seu próprio erro

```python
try:
    idade_valida(-5)
except ValueError as erro:
    print(erro)   # "Idade não pode ser negativa"
```

> 💡 `raise` transforma um "problema silencioso" num erro claro e
> capturável — é a diferença entre o programa falhar sem explicação e falhar
> com uma mensagem útil.
""",
                [
                    code(
                        "Defina `idade_valida(n)` que levanta `ValueError` se `n < 0` e retorna `n` caso contrário.",
                        "def idade_valida(n):\n    if n < 0:\n        raise ValueError(\"Idade não pode ser negativa\")\n    return n",
                        "assert idade_valida(18) == 18, 'idade_valida(18) deveria ser 18'\ntry:\n    idade_valida(-1)\n    raise AssertionError('idade_valida(-1) deveria ter levantado ValueError')\nexcept ValueError:\n    pass",
                    ),
                    code(
                        "Defina `dividir(a, b)` que levanta `ZeroDivisionError` se `b == 0` e retorna `a / b` caso contrário.",
                        "def dividir(a, b):\n    if b == 0:\n        raise ZeroDivisionError(\"Divisor não pode ser zero\")\n    return a / b",
                        "assert dividir(6, 2) == 3.0, 'dividir(6, 2) deveria ser 3.0'\ntry:\n    dividir(6, 0)\n    raise AssertionError('dividir(6, 0) deveria ter levantado ZeroDivisionError')\nexcept ZeroDivisionError:\n    pass",
                    ),
                    quiz(
                        "Qual palavra levanta (dispara) uma exceção manualmente?",
                        "raise",
                        ["raise", "throw", "error"],
                    ),
                    quiz(
                        "Para que serve levantar erros no seu próprio código?",
                        "Validar entradas e dar mensagens de erro claras e capturáveis",
                        ["Validar entradas e dar mensagens de erro claras e capturáveis", "Deixar o programa mais rápido", "Impedir o uso de funções"],
                    ),
                    quiz(
                        "Dado `raise ValueError(\"mensagem\")`, quem chama a função pode:",
                        "capturar o erro com try/except e ler a mensagem",
                        ["capturar o erro com try/except e ler a mensagem", "ignorar, pois é silencioso", "fazer o programa reiniciar"],
                    ),
                    text(
                        "Complete: `raise` ___ uma exceção de propósito.",
                        "levanta",
                    ),
                ],
            ),
        ],
    )


# ============================================================
# MODULO 8 - Módulos e Pacotes (novo, Fase 4 do roteiro)
# Misto: import/biblioteca padrão rodam (código); criar módulos,
# __name__ e pacotes/pip são conceituais.
# ============================================================

def build_modulo_modulos():
    return module(
        "modulos-e-imports",
        "Módulo 8 — Módulos e Pacotes",
        "Organizar e reutilizar código: importar módulos, usar a biblioteca padrão, criar módulos próprios e instalar pacotes.",
        [
            topic(
                "importando-modulos",
                "Importando módulos",
                """
# Importando módulos

Um **módulo** é um arquivo `.py` com código. Para usar o que ele contém,
você o **importa**. O Python já vem com muitos módulos prontos (biblioteca
padrão), como `math`:

```python
import math

print(math.sqrt(9))   # 3.0
print(math.pi)        # 3.141592...
```

## Importando apenas partes

Se você quer só uma função (ou variável), use `from ... import ...`:

```python
from math import sqrt

print(sqrt(16))   # 4.0  — sem precisar escrever math.sqrt
```

## A diferença na prática

| Forma | Uso no código | O que fica no seu namespace |
|---|---|---|
| `import math` | `math.sqrt(9)` | o módulo inteiro, sob o nome `math` |
| `from math import sqrt` | `sqrt(9)` | só a função `sqrt` |

> 💡 Antes de usar qualquer coisa de um módulo, você precisa importá-lo — caso
> contrário, `NameError`. Importe no topo do arquivo, por convenção.
""",
                [
                    code(
                        "Importe o módulo `math` e use `math.sqrt(9)` guardando o resultado em `raiz`.",
                        "import math\nraiz = math.sqrt(9)",
                        "assert 'raiz' in dir(), 'Crie a variável raiz'\nassert raiz == 3.0, f'raiz deveria ser 3.0, mas é {raiz!r}'",
                    ),
                    code(
                        "Use `from math import floor` e guarde `baixo = floor(3.7)`.",
                        "from math import floor\nbaixo = floor(3.7)",
                        "assert 'baixo' in dir(), 'Crie a variável baixo'\nassert baixo == 3, f'baixo deveria ser 3, mas é {baixo!r}'",
                    ),
                    code(
                        "Importe o módulo `math` e use `math.pi` para calcular o perímetro de um círculo de raio 2: guarde em `perimetro` como `2 * math.pi * 2`.",
                        "import math\nperimetro = 2 * math.pi * 2",
                        "assert 'perimetro' in dir(), 'Crie a variável perimetro'\nassert abs(perimetro - 2 * math.pi * 2) < 1e-9, 'perimetro deveria ser 2 * math.pi * 2'",
                    ),
                    quiz(
                        "Qual comando importa o módulo `math` inteiro?",
                        "import math",
                        ["import math", "use math", "include math"],
                    ),
                    quiz(
                        "Com `from math import sqrt`, como você chama a raiz quadrada de 9?",
                        "sqrt(9)",
                        ["sqrt(9)", "math.sqrt(9)", "from.sqrt(9)"],
                    ),
                    text(
                        "Complete: para usar `math.sqrt`, primeiro você precisa ___ o módulo math.",
                        "importar",
                    ),
                ],
            ),
            topic(
                "biblioteca-padrao",
                "Biblioteca padrão",
                """
# Biblioteca padrão

A **biblioteca padrão** é o conjunto de módulos que vem **junto com o Python**,
sem instalar nada. É um dos pontos fortes da linguagem: tem ferramenta pronta
para quase tudo.

## Módulos úteis no dia a dia

```python
import random
dado = random.randint(1, 6)        # número aleatório entre 1 e 6
item = random.choice(["a", "b"])   # escolhe um item da lista
```

```python
import datetime
hoje = datetime.date.today()       # a data de hoje
natal = datetime.date(2026, 12, 25)  # uma data específica
```

```python
import math
math.factorial(5)   # 120
math.sqrt(16)       # 4.0
```

## Outros módulos que você vai encontrar

- `os` e `pathlib`: arquivos e pastas.
- `json`: trabalhar com dados JSON.
- `csv`: arquivos CSV.
- `re`: expressões regulares.
- `random`, `datetime`, `math`: números, datas e matemática.

> 💻 Num dos próximos módulos você vai mexer com arquivos e JSON. Por ora,
> importe `random` e rode `random.randint(1, 6)` no seu terminal para "jogar
> um dado" (comando `python` abre o REPL, como você viu no Módulo 2).
""",
                [
                    code(
                        "Importe `random` e chame `random.randint(1, 6)` guardando em `dado`.",
                        "import random\ndado = random.randint(1, 6)",
                        "assert 'dado' in dir(), 'Crie a variável dado'\nassert 1 <= dado <= 6, f'dado deveria estar entre 1 e 6, mas é {dado!r}'",
                    ),
                    code(
                        "Importe `datetime` e crie a variável `natal` com a data `2026-12-25` usando `datetime.date(2026, 12, 25)`.",
                        "import datetime\nnatal = datetime.date(2026, 12, 25)",
                        "assert 'natal' in dir(), 'Crie a variável natal'\nassert natal == datetime.date(2026, 12, 25), f'natal deveria ser 2026-12-25, mas é {natal!r}'",
                    ),
                    code(
                        "Importe `math` e calcule `math.factorial(5)` guardando em `fatorial`.",
                        "import math\nfatorial = math.factorial(5)",
                        "assert 'fatorial' in dir(), 'Crie a variável fatorial'\nassert fatorial == 120, f'fatorial deveria ser 120, mas é {fatorial!r}'",
                    ),
                    quiz(
                        "A biblioteca padrão do Python:",
                        "vem instalada junto com o Python, sem instalar nada",
                        ["vem instalada junto com o Python, sem instalar nada", "precisa ser baixada separadamente", "só existe em computadores grandes"],
                    ),
                    quiz(
                        "Qual módulo da biblioteca padrão gera números aleatórios?",
                        "random",
                        ["random", "datetime", "math"],
                    ),
                    quiz(
                        "Qual módulo da biblioteca padrão trabalha com datas?",
                        "datetime",
                        ["datetime", "random", "csv"],
                    ),
                ],
            ),
            topic(
                "criando-modulos",
                "Criando seus próprios módulos",
                """
# Criando seus próprios módulos

Todo arquivo `.py` é um módulo. Se você tem um arquivo `calculos.py` com:

```python
# calculos.py
def somar(a, b):
    return a + b

def dobrar(n):
    return n * 2
```

em outro arquivo, no mesmo diretório, você pode importá-lo:

```python
import calculos

print(calculos.somar(2, 3))     # 5
print(calculos.dobrar(4))       # 8
```

ou importar só o que precisa:

```python
from calculos import somar
```

## O que acontece ao importar

Ao importar um módulo, o Python **executa o código dele uma vez** (definindo
funções, variáveis etc.) e guarda num cache. Importar de novo não roda de novo.

## Por que usar módulos?

- **Organização**: código separado por assunto, em arquivos menores.
- **Reuso**: escreva uma vez, use em vários programas.
- **Colaboração**: cada pessoa cuida de um módulo.

> 💻 Crie um arquivo `calculos.py` no seu editor, escreva a função `somar`,
> crie um arquivo `main.py` com `import calculos` e rode `python main.py` no
> seu terminal — como você viu no Módulo 2.
""",
                [
                    quiz(
                        "O que é um módulo em Python?",
                        "Um arquivo .py com código que pode ser importado",
                        ["Um arquivo .py com código que pode ser importado", "Um tipo de variável", "Uma função especial"],
                    ),
                    quiz(
                        "Se você tem o arquivo `calculos.py`, como o importa em outro arquivo?",
                        "import calculos",
                        ["import calculos", "use calculos", "open calculos"],
                    ),
                    quiz(
                        "Com `import calculos`, como você chama a função `somar` que está nele?",
                        "calculos.somar(2, 3)",
                        ["calculos.somar(2, 3)", "somar(2, 3)", "import somar"],
                    ),
                    quiz(
                        "O que acontece quando você importa um módulo pela primeira vez?",
                        "O código dele é executado uma vez",
                        ["O código dele é executado uma vez", "Nada acontece até você chamar as funções", "Ele é transformado em um programa executável"],
                    ),
                    text(
                        "Complete: todo arquivo `.py` é um ___.",
                        "módulo",
                    ),
                ],
            ),
            topic(
                "name-main",
                "O bloco if __name__ == \"__main__\"",
                """
# O bloco if __name__ == "__main__"

Cada módulo tem uma variável especial `__name__`. Ela muda conforme o contexto:

- Quando o arquivo é **executado diretamente** (`python meus_scripts.py`),
  `__name__` vale `"__main__"`.
- Quando o arquivo é **importado** por outro, `__name__` vale o **nome do
  módulo**.

## Por que isso importa?

Sem o guard, todo código no topo nível do arquivo roda **na importação** — o
que pode ser um efeito colateral indesejado:

```python
# ferramentas.py
print("Ferramentas carregadas!")   # roda ao importar!

def util():
    ...
```

Ao fazer `import ferramentas`, o `print` roda mesmo se você só queria a função.

## A solução

```python
def util():
    ...

if __name__ == "__main__":
    # código que só roda quando executado direto
    print(util())
```

O código dentro do guard **não roda na importação** — só quando o arquivo é o
principal.

> 💡 Esse é o padrão para fazer um arquivo funcionar tanto como "biblioteca
> importável" quanto como "script executável".
""",
                [
                    quiz(
                        "Quando o arquivo é executado diretamente, `__name__` vale:",
                        "__main__",
                        ["__main__", "o nome do módulo", "None"],
                    ),
                    quiz(
                        "Quando o arquivo é importado por outro, `__name__` vale:",
                        "o nome do módulo",
                        ["o nome do módulo", "__main__", "import"],
                    ),
                    quiz(
                        "Para que serve `if __name__ == \"__main__\":`?",
                        "Rodar o código só quando o arquivo é executado direto, não ao ser importado",
                        ["Rodar o código só quando o arquivo é executado direto, não ao ser importado", "Deixar o programa mais rápido", "Impedir o arquivo de ser importado"],
                    ),
                    quiz(
                        "Sem esse guard, o que acontece ao importar um módulo que tem `print` no topo?",
                        "O print roda na hora da importação",
                        ["O print roda na hora da importação", "O print nunca roda", "O Python dá erro"],
                    ),
                    text(
                        "Complete: `if __name__ == \"___\":`",
                        "__main__",
                    ),
                ],
            ),
            topic(
                "pacotes-e-pypi",
                "Pacotes e o PyPI",
                """
# Pacotes e o PyPI

Você pode organizar módulos em **pacotes** — diretórios com um arquivo
especial `__init__.py` (pode ser vazio) que os marca como importáveis:

```
meu_projeto/
├── __init__.py
├── main.py
└── util/
    ├── __init__.py
    └── textos.py
```

## Pacotes de terceiros: o PyPI

Além da biblioteca padrão, a comunidade publica milhões de pacotes no
**PyPI** (*Python Package Index*) — o "mercado de módulos" do Python. Para
instalar, usa-se o **pip**:

```bash
pip install requests
```

Depois de instalar, é só importar como qualquer módulo:

```python
import requests
```

## O pip faz parte do Python

O `pip` vem junto com a instalação padrão do Python. É ele que baixa e
gerencia os pacotes do PyPI na sua máquina.

> 💻 O comando `pip install requests` é a cara dos próximos módulos. Abra seu
> terminal e rode `pip --version` para ver se o pip está instalado (comando já
> explicado: é só digitar `pip --version`).
""",
                [
                    quiz(
                        "O que é um pacote em Python?",
                        "Um diretório com módulos organizados, marcado com __init__.py",
                        ["Um diretório com módulos organizados, marcado com __init__.py", "Um único arquivo .py", "Um tipo de função"],
                    ),
                    quiz(
                        "De onde você baixa pacotes criados pela comunidade?",
                        "PyPI",
                        ["PyPI", "GitHub", "python.org"],
                    ),
                    quiz(
                        "Qual comando instala um pacote de terceiros?",
                        "pip install requests",
                        ["pip install requests", "install requests", "apt get requests"],
                    ),
                    quiz(
                        "O que o arquivo `__init__.py` faz num pacote?",
                        "Marca o diretório como um pacote importável",
                        ["Marca o diretório como um pacote importável", "Guarda o código principal do programa", "Substitui o main.py"],
                    ),
                    text(
                        "Complete: o gerenciador de pacotes que vem com o Python é o ___.",
                        "pip",
                    ),
                ],
            ),
        ],
    )


# ============================================================
# MODULO 9 - Programação Orientada a Objetos (novo, Fase 5)
# Código. Maior módulo: classes, métodos, encapsulamento,
# herança, polimorfismo, dunder methods e dataclasses.
# ============================================================

def build_modulo_poo():
    return module(
        "poo",
        "Módulo 9 — Programação Orientada a Objetos",
        "Modelar o mundo em objetos: classes, instâncias, métodos, encapsulamento, herança, polimorfismo, métodos mágicos e dataclasses.",
        [
            topic(
                "classes-e-objetos",
                "Classes e objetos",
                """
# Classes e objetos

**POO** (Programação Orientada a Objetos) organiza o código em **objetos**:
estruturas que juntam dados (atributos) e comportamentos (métodos).

Uma **classe** é o "molde"; o **objeto** é a "peça" feita a partir do molde.

## Definindo uma classe

```python
class Pessoa:
    def __init__(self, nome, idade):
        self.nome = nome
        self.idade = idade
```

- `class Pessoa:` cria o molde.
- `__init__` é o **construtor**: roda na criação do objeto e guarda os
  atributos.
- `self` representa **a instância** que está sendo criada — é por ele que você
  guarda `self.nome`.

## Criando objetos (instanciando)

```python
ana = Pessoa("Ana", 20)
print(ana.nome)    # Ana
print(ana.idade)   # 20
```

Cada objeto criado é **independente**: `ana` e `bia` têm seus próprios
atributos, mesmo vindo da mesma classe.

> 💡 Analogia: a classe é o molde do biscoito; cada objeto é um biscoito feito
> dele. Mesmo molde, biscoitos diferentes.
""",
                [
                    code(
                        "Defina uma classe `Pessoa` com `__init__(self, nome, idade)` que guarda `self.nome` e `self.idade`.",
                        "class Pessoa:\n    def __init__(self, nome, idade):\n        self.nome = nome\n        self.idade = idade",
                        "p = Pessoa('Ana', 20)\nassert p.nome == 'Ana', f'nome deveria ser Ana, mas é {p.nome!r}'\nassert p.idade == 20, f'idade deveria ser 20, mas é {p.idade!r}'",
                    ),
                    code(
                        "Defina uma classe `Cachorro` com `__init__(self, nome)` que guarda `self.nome` e `self.raca = \"vira-lata\"`.",
                        "class Cachorro:\n    def __init__(self, nome):\n        self.nome = nome\n        self.raca = \"vira-lata\"",
                        "c = Cachorro('Rex')\nassert c.nome == 'Rex', f'nome deveria ser Rex, mas é {c.nome!r}'\nassert c.raca == 'vira-lata', f'raca deveria ser vira-lata, mas é {c.raca!r}'",
                    ),
                    quiz(
                        "O que o `self` representa dentro de uma classe?",
                        "A instância (o objeto) que está sendo criada",
                        ["A instância (o objeto) que está sendo criada", "A classe em si", "O arquivo do programa"],
                    ),
                    quiz(
                        "Para que serve o método `__init__`?",
                        "Inicializar o objeto (guardar atributos) quando ele é criado",
                        ["Inicializar o objeto (guardar atributos) quando ele é criado", "Destruir o objeto", "Imprimir o objeto"],
                    ),
                    quiz(
                        "Como você cria um objeto da classe `Pessoa` com nome Ana e idade 20?",
                        "Pessoa(\"Ana\", 20)",
                        ["Pessoa(\"Ana\", 20)", "new Pessoa(\"Ana\", 20)", "Pessoa.instanciar(\"Ana\", 20)"],
                    ),
                    text(
                        "Complete: criar um objeto a partir de uma classe se chama ___.",
                        "instanciar",
                    ),
                ],
            ),
            topic(
                "metodos",
                "Métodos de instância",
                """
# Métodos de instância

Um **método** é uma função definida dentro da classe — um comportamento que os
objetos daquela classe sabem fazer. Todo método de instância recebe `self`
como primeiro parâmetro:

```python
class Retangulo:
    def __init__(self, largura, altura):
        self.largura = largura
        self.altura = altura

    def area(self):
        return self.largura * self.altura
```

Chamar um método usa a sintaxe `objeto.metodo(...)`:

```python
r = Retangulo(4, 5)
r.area()   # 20
```

O `self` passa "de graça": quando você escreve `r.area()`, o Python chama
`area(r)`.

## Métodos que alteram o objeto

```python
class Contador:
    def __init__(self):
        self.valor = 0

    def incrementar(self):
        self.valor = self.valor + 1
```

```python
c = Contador()
c.incrementar()
c.incrementar()
c.valor   # 2
```

> 💡 Método sem `return` devolve `None`, como qualquer função. Se ele precisa
> entregar um valor (ex.: `area()`), use `return`.
""",
                [
                    code(
                        "Defina uma classe `Retangulo` com `__init__(self, largura, altura)` e um método `area(self)` que retorna `self.largura * self.altura`.",
                        "class Retangulo:\n    def __init__(self, largura, altura):\n        self.largura = largura\n        self.altura = altura\n\n    def area(self):\n        return self.largura * self.altura",
                        "r = Retangulo(4, 5)\nassert r.area() == 20, f'area deveria ser 20, mas é {r.area()!r}'",
                    ),
                    code(
                        "Defina uma classe `Contador` com `__init__(self)` zerando `self.valor = 0` e um método `incrementar(self)` que soma 1 a `self.valor`.",
                        "class Contador:\n    def __init__(self):\n        self.valor = 0\n\n    def incrementar(self):\n        self.valor = self.valor + 1",
                        "c = Contador()\nassert c.valor == 0, 'valor deveria começar em 0'\nc.incrementar()\nc.incrementar()\nassert c.valor == 2, f'valor deveria ser 2, mas é {c.valor!r}'",
                    ),
                    code(
                        "Defina uma classe `Pessoa` com `__init__(self, nome, idade)` e um método `apresentacao(self)` que retorna `f\"{self.nome} tem {self.idade} anos\"`.",
                        "class Pessoa:\n    def __init__(self, nome, idade):\n        self.nome = nome\n        self.idade = idade\n\n    def apresentacao(self):\n        return f\"{self.nome} tem {self.idade} anos\"",
                        "p = Pessoa('Ana', 20)\nassert p.apresentacao() == 'Ana tem 20 anos', f'apresentacao deu {p.apresentacao()!r}'",
                    ),
                    quiz(
                        "Qual é o primeiro parâmetro de todo método de instância?",
                        "self",
                        ["self", "this", "cls"],
                    ),
                    quiz(
                        "Tendo `r = Retangulo(4, 5)`, como você chama o método `area`?",
                        "r.area()",
                        ["r.area()", "area(r)", "Retangulo.area"],
                    ),
                    quiz(
                        "O que um método devolve se não tiver `return`?",
                        "None",
                        ["None", "0", "self"],
                    ),
                ],
            ),
            topic(
                "encapsulamento-e-properties",
                "Encapsulamento e properties",
                """
# Encapsulamento e properties

**Encapsulamento** é a ideia de esconder os detalhes internos de um objeto e
expor apenas o que importa. Em Python, o `_` no início do nome sinaliza
"atributo interno, não mexa de fora":

```python
class Conta:
    def __init__(self, saldo_inicial):
        self._saldo = saldo_inicial
```

É uma **convenção** — o Python não impede o acesso direto, mas o `_` avisa.

## Property: acesso controlado

Com `@property` você expõe um atributo interno como se fosse público, mas com
controle — por exemplo, só leitura:

```python
class Conta:
    def __init__(self, saldo_inicial):
        self._saldo = saldo_inicial

    @property
    def saldo(self):
        return self._saldo
```

```python
c = Conta(100)
c.saldo        # 100  (lê o _saldo por trás das cortinas)
c.saldo = 50   # AttributeError, se não houver setter
```

## Setter: validando na atribuição

```python
    @saldo.setter
    def saldo(self, valor):
        if valor < 0:
            raise ValueError("Saldo não pode ser negativo")
        self._saldo = valor
```

Agora `c.saldo = -10` levanta erro, em vez de corromper o estado.

> 💡 Property permite adicionar validação e controle **sem mudar a interface**:
> quem usa o objeto continua escrevendo `c.saldo`.
""",
                [
                    code(
                        "Defina uma classe `Conta` com `__init__(self, saldo_inicial)` guardando `self._saldo`, e uma `@property` `saldo` (só leitura) que retorna `self._saldo`.",
                        "class Conta:\n    def __init__(self, saldo_inicial):\n        self._saldo = saldo_inicial\n\n    @property\n    def saldo(self):\n        return self._saldo",
                        "c = Conta(100)\nassert c.saldo == 100, f'saldo deveria ser 100, mas é {c.saldo!r}'\nassert c._saldo == 100, '_saldo deveria ser 100'",
                    ),
                    code(
                        "Defina uma classe `Conta` com atributo interno `_saldo` e property `saldo` com getter e `@saldo.setter` que levanta `ValueError` se o valor for menor que 0.",
                        "class Conta:\n    def __init__(self, saldo_inicial):\n        self._saldo = saldo_inicial\n\n    @property\n    def saldo(self):\n        return self._saldo\n\n    @saldo.setter\n    def saldo(self, valor):\n        if valor < 0:\n            raise ValueError(\"Saldo não pode ser negativo\")\n        self._saldo = valor",
                        "c = Conta(100)\nc.saldo = 50\nassert c.saldo == 50, 'após setar 50, saldo deveria ser 50'\ntry:\n    c.saldo = -10\n    raise AssertionError('saldo negativo deveria levantar ValueError')\nexcept ValueError:\n    pass",
                    ),
                    quiz(
                        "O que o `_` no início de um nome de atributo sinaliza em Python?",
                        "Que o atributo é interno (convenção: não mexer de fora)",
                        ["Que o atributo é interno (convenção: não mexer de fora)", "Que o atributo é privado de verdade e o acesso é bloqueado", "Que o atributo é público"],
                    ),
                    quiz(
                        "Para que serve a `@property`?",
                        "Expor um atributo interno como se fosse público, com controle",
                        ["Expor um atributo interno como se fosse público, com controle", "Deletar o atributo", "Criar um novo objeto"],
                    ),
                    quiz(
                        "O que o `@saldo.setter` permite fazer?",
                        "Controlar a atribuição (ex.: validar antes de salvar)",
                        ["Controlar a atribuição (ex.: validar antes de salvar)", "Tornar o atributo somente leitura", "Imprimir o atributo"],
                    ),
                    text(
                        "Complete: o `@property` transforma um ___ em uma propriedade com acesso controlado.",
                        "método",
                    ),
                ],
            ),
            topic(
                "heranca",
                "Herança",
                """
# Herança

**Herança** permite criar uma classe nova a partir de uma existente: a filha
**ganha tudo** do pai (atributos e métodos) e pode **adicionar** ou **sobrescrever**
comportamentos.

```python
class Animal:
    def __init__(self, nome):
        self.nome = nome

    def falar(self):
        return "..."
```

```python
class Cachorro(Animal):     # Cachorro herda de Animal
    def falar(self):
        return "Au au"
```

```python
rex = Cachorro("Rex")
rex.nome      # "Rex"  (herdado do pai)
rex.falar()   # "Au au"  (sobrescrito)
```

## super(): chamando o pai

Quando a filha precisa usar o `__init__` do pai (e adicionar mais coisas),
use `super()`:

```python
class Aluno(Pessoa):
    def __init__(self, nome, idade, curso):
        super().__init__(nome, idade)   # roda o __init__ de Pessoa
        self.curso = curso
```

> 💡 Termos: a classe de cima é a **pai** (base/superclasse); a de baixo é a
> **filha** (derivada/subclasse). Herança promove reuso e organização.
""",
                [
                    code(
                        "Defina `class Animal` com `__init__(self, nome)` e método `falar(self)` retornando `\"...\"`. Depois `class Cachorro(Animal)` com `falar(self)` retornando `\"Au au\"`.",
                        "class Animal:\n    def __init__(self, nome):\n        self.nome = nome\n\n    def falar(self):\n        return \"...\"\n\nclass Cachorro(Animal):\n    def falar(self):\n        return \"Au au\"",
                        "rex = Cachorro('Rex')\nassert rex.nome == 'Rex', 'nome deveria ser herdado'\nassert rex.falar() == 'Au au', f'falar de Cachorro deveria ser Au au, mas é {rex.falar()!r}'",
                    ),
                    code(
                        "Defina `class Pessoa` com `__init__(self, nome, idade)`. Depois `class Aluno(Pessoa)` cujo `__init__` chama `super().__init__(nome, idade)` e guarda `self.curso`.",
                        "class Pessoa:\n    def __init__(self, nome, idade):\n        self.nome = nome\n        self.idade = idade\n\nclass Aluno(Pessoa):\n    def __init__(self, nome, idade, curso):\n        super().__init__(nome, idade)\n        self.curso = curso",
                        "a = Aluno('Bia', 19, 'Python')\nassert a.nome == 'Bia', 'nome deveria vir do __init__ do pai'\nassert a.idade == 19, 'idade deveria vir do __init__ do pai'\nassert a.curso == 'Python', f'curso deveria ser Python, mas é {a.curso!r}'",
                    ),
                    code(
                        "Defina `class Forma` com método `area(self)` retornando `0`, e `class Quadrado(Forma)` com `__init__(self, lado)` guardando `self.lado`, sobrescrevendo `area(self)` para retornar `self.lado ** 2`.",
                        "class Forma:\n    def area(self):\n        return 0\n\nclass Quadrado(Forma):\n    def __init__(self, lado):\n        self.lado = lado\n\n    def area(self):\n        return self.lado ** 2",
                        "q = Quadrado(3)\nassert q.area() == 9, f'area do quadrado deveria ser 9, mas é {q.area()!r}'\nf = Forma()\nassert f.area() == 0, 'area da Forma base deveria ser 0'",
                    ),
                    quiz(
                        "Em `class Cachorro(Animal)`, quem é a classe pai?",
                        "Animal",
                        ["Animal", "Cachorro", "Nenhuma, Cachorro é independente"],
                    ),
                    quiz(
                        "O que uma classe filha ganha da classe pai?",
                        "Os atributos e métodos do pai",
                        ["Os atributos e métodos do pai", "Apenas o nome", "Nada automaticamente"],
                    ),
                    quiz(
                        "O que `super()` faz dentro de um método da classe filha?",
                        "Chama o método correspondente da classe pai",
                        ["Chama o método correspondente da classe pai", "Cria uma cópia do objeto", "Apaga o objeto"],
                    ),
                ],
            ),
            topic(
                "polimorfismo",
                "Polimorfismo",
                """
# Polimorfismo

**Polimorfismo** é a capacidade de objetos de classes diferentes responderem
ao **mesmo método** com comportamentos próprios.

```python
class Gato:
    def falar(self):
        return "Miau"

class Cachorro:
    def falar(self):
        return "Au au"
```

Agora o mesmo comando funciona para os dois:

```python
gato = Gato()
cachorro = Cachorro()

print(gato.falar())      # Miau
print(cachorro.falar())  # Au au
```

## Por que isso é útil?

Você escreve **um** código que trata objetos diferentes sem saber (nem
precisar saber) de qual classe cada um é:

```python
animais = [Gato(), Cachorro()]
for animal in animais:
    print(animal.falar())   # cada um fala do seu jeito
```

O código só exige que cada objeto tenha o método `falar()` — a implementação
é de cada classe.

> 💡 "Interface única, comportamentos diferentes": é isso que permite construir
> sistemas extensíveis sem mudar o código que usa os objetos.
""",
                [
                    code(
                        "Defina `class Gato` e `class Cachorro`, cada uma com método `falar(self)` retornando `\"Miau\"` e `\"Au au\"` respectivamente.",
                        "class Gato:\n    def falar(self):\n        return \"Miau\"\n\nclass Cachorro:\n    def falar(self):\n        return \"Au au\"",
                        "assert Gato().falar() == 'Miau', 'Gato.falar deveria ser Miau'\nassert Cachorro().falar() == 'Au au', 'Cachorro.falar deveria ser Au au'",
                    ),
                    code(
                        "Defina `class Gato` com `falar(self)` retornando `\"Miau\"` e `class Cachorro` com `falar(self)` retornando `\"Au au\"`. Depois defina `emitir_sons(animais)` que retorna uma lista com o `falar()` de cada animal.",
                        "class Gato:\n    def falar(self):\n        return \"Miau\"\n\nclass Cachorro:\n    def falar(self):\n        return \"Au au\"\n\ndef emitir_sons(animais):\n    return [a.falar() for a in animais]",
                        "sons = emitir_sons([Gato(), Cachorro(), Gato()])\nassert sons == ['Miau', 'Au au', 'Miau'], f'sons ficou: {sons!r}'",
                    ),
                    quiz(
                        "O que é polimorfismo?",
                        "Objetos de classes diferentes respondendo ao mesmo método, cada um do seu jeito",
                        ["Objetos de classes diferentes respondendo ao mesmo método, cada um do seu jeito", "Uma classe com vários __init__", "Copiar código de uma classe para outra"],
                    ),
                    quiz(
                        "`gato.falar()` e `cachorro.falar()` retornarem coisas diferentes é um exemplo de:",
                        "polimorfismo",
                        ["polimorfismo", "herança", "encapsulamento"],
                    ),
                    quiz(
                        "Qual a grande vantagem do polimorfismo?",
                        "Escrever um código único que trata objetos diferentes sem saber a classe de cada um",
                        ["Escrever um código único que trata objetos diferentes sem saber a classe de cada um", "Deixar o código maior", "Impedir a criação de objetos"],
                    ),
                ],
            ),
            topic(
                "dunder-methods",
                "Métodos mágicos (dunder)",
                """
# Métodos mágicos (dunder)

Métodos como `__init__` são chamados de **dunder methods** (*double
underscore*). Eles dão comportamento a objetos em operações do dia a dia:
print, comparação, tamanho, soma...

## __str__: o que o print mostra

```python
class Pessoa:
    def __init__(self, nome, idade):
        self.nome = nome
        self.idade = idade

    def __str__(self):
        return f"{self.nome} ({self.idade} anos)"

print(Pessoa("Ana", 20))   # Ana (20 anos)
```

## __eq__: comparar com ==

```python
    def __eq__(self, outro):
        return self.nome == outro.nome and self.idade == outro.idade
```

Agora `Pessoa("Ana", 20) == Pessoa("Ana", 20)` é `True`.

## __len__: o que len() retorna

```python
class Equipe:
    def __init__(self, membros):
        self.membros = membros

    def __len__(self):
        return len(self.membros)

len(Equipe(["Ana", "Bia"]))   # 2
```

> 💡 Sem `__str__`, o `print` mostra algo como `<__main__.Pessoa object at
> 0x...>` — pouco útil. Dunder methods deixam os objetos "comportarem-se como
> nativos".
""",
                [
                    code(
                        "Defina `class Pessoa` com `__init__(self, nome, idade)` e `__str__(self)` retornando `f\"{self.nome} ({self.idade} anos)\"`.",
                        "class Pessoa:\n    def __init__(self, nome, idade):\n        self.nome = nome\n        self.idade = idade\n\n    def __str__(self):\n        return f\"{self.nome} ({self.idade} anos)\"",
                        "p = Pessoa('Ana', 20)\nassert str(p) == 'Ana (20 anos)', f'str deveria ser Ana (20 anos), mas é {str(p)!r}'",
                    ),
                    code(
                        "Defina `class Pessoa` com `__init__(self, nome, idade)` e `__eq__(self, outro)` retornando `self.nome == outro.nome and self.idade == outro.idade`.",
                        "class Pessoa:\n    def __init__(self, nome, idade):\n        self.nome = nome\n        self.idade = idade\n\n    def __eq__(self, outro):\n        return self.nome == outro.nome and self.idade == outro.idade",
                        "p1 = Pessoa('Ana', 20)\np2 = Pessoa('Ana', 20)\np3 = Pessoa('Bia', 20)\nassert p1 == p2, 'pessoas iguais deveriam ser == '\nassert p1 != p3, 'pessoas diferentes não deveriam ser =='",
                    ),
                    code(
                        "Defina `class Equipe` com `__init__(self, membros)` guardando `self.membros`, e `__len__(self)` retornando `len(self.membros)`.",
                        "class Equipe:\n    def __init__(self, membros):\n        self.membros = membros\n\n    def __len__(self):\n        return len(self.membros)",
                        "eq = Equipe(['Ana', 'Bia', 'Caio'])\nassert len(eq) == 3, f'len deveria ser 3, mas é {len(eq)!r}'",
                    ),
                    quiz(
                        "O que o método `__str__` controla?",
                        "O que print()/str() mostram do objeto",
                        ["O que print()/str() mostram do objeto", "O tamanho do objeto", "A comparação com =="],
                    ),
                    quiz(
                        "Para comparar dois objetos com `==` de forma personalizada, você implementa:",
                        "__eq__",
                        ["__eq__", "__str__", "__len__"],
                    ),
                    quiz(
                        "O que acontece com o `print` de um objeto sem `__str__`?",
                        "Mostra algo pouco útil, como o endereço de memória",
                        ["Mostra algo pouco útil, como o endereço de memória", "Levanta um erro", "Mostra os atributos automaticamente"],
                    ),
                    text(
                        "Complete: métodos mágicos começam e terminam com dois ___.",
                        "underscores",
                    ),
                ],
            ),
            topic(
                "dataclasses",
                "Dataclasses",
                """
# Dataclasses

Para classes que são, principalmente, **agregados de dados** (só guardam
campos), o Python oferece as **dataclasses**: com um `@dataclass`, o `__init__`,
`__repr__` e `__eq__` são gerados automaticamente.

```python
from dataclasses import dataclass

@dataclass
class Pessoa:
    nome: str
    idade: int
```

O que antes exigia escrever tudo na mão:

```python
class Pessoa:
    def __init__(self, nome, idade):
        self.nome = nome
        self.idade = idade

    def __repr__(self):
        return f"Pessoa(nome={self.nome!r}, idade={self.idade!r})"

    def __eq__(self, outro):
        return self.nome == outro.nome and self.idade == outro.idade
```

vira só o `@dataclass` + os campos anotados.

## Na prática

```python
p1 = Pessoa("Ana", 20)
p2 = Pessoa("Ana", 20)
p1 == p2                 # True (__eq__ automático)
print(p1)                # Pessoa(nome='Ana', idade=20)  (__repr__ automático)
```

> 💡 Dataclasses geram código repetitivo de forma segura. São a escolha
> moderna para "classes de dados" — você já viu type hints (como `nome: str`)
> e vai aprofundar no Módulo 11.
""",
                [
                    code(
                        "Importe `dataclass` de `dataclasses` e defina `@dataclass class Pessoa` com campos `nome: str` e `idade: int`.",
                        "from dataclasses import dataclass\n\n@dataclass\nclass Pessoa:\n    nome: str\n    idade: int",
                        "p1 = Pessoa('Ana', 20)\np2 = Pessoa('Ana', 20)\nassert p1.nome == 'Ana', 'nome deveria ser Ana'\nassert p1 == p2, 'duas pessoas com os mesmos campos deveriam ser iguais'",
                    ),
                    code(
                        "Importe `dataclass` e defina `@dataclass class Ponto` com campos `x: int` e `y: int`.",
                        "from dataclasses import dataclass\n\n@dataclass\nclass Ponto:\n    x: int\n    y: int",
                        "pt = Ponto(3, 5)\nassert pt.x == 3, 'x deveria ser 3'\nassert pt.y == 5, 'y deveria ser 5'\nassert pt == Ponto(3, 5), 'Pontos iguais deveriam ser iguais com =='",
                    ),
                    quiz(
                        "O que o `@dataclass` gera automaticamente?",
                        "__init__, __repr__ e __eq__",
                        ["__init__, __repr__ e __eq__", "Somente __init__", "Nada, só decora"],
                    ),
                    quiz(
                        "Qual import é necessário para usar dataclass?",
                        "from dataclasses import dataclass",
                        ["from dataclasses import dataclass", "import dataclass", "from data import dataclass"],
                    ),
                    quiz(
                        "Com uma dataclass, `Pessoa(\"Ana\", 20) == Pessoa(\"Ana\", 20)` resulta em:",
                        "True, pois o __eq__ é gerado automaticamente",
                        ["True, pois o __eq__ é gerado automaticamente", "False, pois são objetos diferentes", "Um erro"],
                    ),
                    text(
                        "Complete: dataclasses são ótimas para classes que são principalmente agregados de ___.",
                        "dados",
                    ),
                ],
            ),
        ],
    )


# ============================================================
# MODULO 10 - Python Avançado (novo, Fase 6 do roteiro)
# Código. lambda/map/filter, generators, decorators e context
# managers — o que separa código funcional de código elegante.
# ============================================================

def build_modulo_avancado():
    return module(
        "python-avancado",
        "Módulo 10 — Python Avançado",
        "Ferramentas de poder: lambdas, map/filter, generators com yield, decorators e context managers.",
        [
            topic(
                "funcoes-lambda",
                "Funções lambda, map e filter",
                """
# Funções lambda, map e filter

Uma **lambda** é uma função anônima de uma linha:

```python
dobro = lambda x: x * 2
dobro(5)   # 10
```

A esquerda dos `:` são os parâmetros; a direita é a expressão retornada.

## map: aplicar uma função a cada elemento

`map(f, sequencia)` aplica `f` em cada item:

```python
numeros = [1, 2, 3]
dobrados = list(map(lambda x: x * 2, numeros))
# [2, 4, 6]
```

## filter: manter só o que passar no teste

`filter(f, sequencia)` mantém os itens para os quais `f` retorna `True`:

```python
numeros = [1, 2, 3, 4, 5, 6]
pares = list(filter(lambda x: x % 2 == 0, numeros))
# [2, 4, 6]
```

## Ou com comprehension (muitas vezes mais legível)

```python
dobrados = [x * 2 for x in numeros]
pares = [x for x in numeros if x % 2 == 0]
```

> 💡 `map`/`filter` devolvem um **iterador** (por isso o `list(...)` para
> materializar). Em Python, comprehensions costumam ser a escolha mais clara —
> mas entender map/filter é importante para ler código de outras pessoas.
""",
                [
                    code(
                        "Crie a lambda `dobro = lambda x: x * 2` e depois `resultado = list(map(dobro, [1, 2, 3]))`.",
                        "dobro = lambda x: x * 2\nresultado = list(map(dobro, [1, 2, 3]))",
                        "assert 'resultado' in dir(), 'Crie a variável resultado'\nassert resultado == [2, 4, 6], f'resultado ficou: {resultado!r}'",
                    ),
                    code(
                        "Use `filter` com uma lambda para guardar em `pares` apenas os números pares de `[1, 2, 3, 4, 5, 6]`.",
                        "numeros = [1, 2, 3, 4, 5, 6]\npares = list(filter(lambda x: x % 2 == 0, numeros))",
                        "assert 'pares' in dir(), 'Crie a lista pares'\nassert pares == [2, 4, 6], f'pares ficou: {pares!r}'",
                        starter_code="numeros = [1, 2, 3, 4, 5, 6]\n# use filter + lambda\n",
                    ),
                    code(
                        "Use `map` com uma lambda para converter `[\"ana\", \"bia\"]` em uma lista de nomes maiúsculos, guardando em `maiusculos`.",
                        "nomes = [\"ana\", \"bia\"]\nmaiusculos = list(map(lambda n: n.upper(), nomes))",
                        "assert 'maiusculos' in dir(), 'Crie a lista maiusculos'\nassert maiusculos == ['ANA', 'BIA'], f'maiusculos ficou: {maiusculos!r}'",
                        starter_code="nomes = [\"ana\", \"bia\"]\n# use map + lambda\n",
                    ),
                    quiz(
                        "O que é uma função lambda em Python?",
                        "Uma função anônima de uma linha",
                        ["Uma função anônima de uma linha", "Uma função que só pode ser chamada uma vez", "Um tipo de variável"],
                    ),
                    quiz(
                        "O que `map(f, lista)` faz?",
                        "Aplica f em cada elemento da lista",
                        ["Aplica f em cada elemento da lista", "Filtra os elementos da lista", "Ordena a lista"],
                    ),
                    quiz(
                        "O que `filter(f, lista)` faz?",
                        "Mantém apenas os elementos para os quais f retorna True",
                        ["Mantém apenas os elementos para os quais f retorna True", "Aplica f em cada elemento", "Inverte a lista"],
                    ),
                ],
            ),
            topic(
                "generators",
                "Generators (yield)",
                """
# Generators (yield)

Um **generator** é uma função que produz uma **sequência** de valores sob
demanda, um de cada vez — em vez de gerar tudo de uma vez e guardar na
memória. A palavra-chave é `yield`:

```python
def contar(n):
    for i in range(1, n + 1):
        yield i

for valor in contar(3):
    print(valor)   # 1, 2, 3
```

## Diferença para uma função comum

Uma função com `return` termina e devolve um valor só. Uma função com `yield`
**pausa** a cada `yield`, devolve aquele valor, e quando é pedido de novo,
**continua de onde parou**.

```python
g = contar(3)
next(g)   # 1
next(g)   # 2
next(g)   # 3
```

## Materializando com list()

Você pode transformar um generator numa lista quando precisa de tudo de uma
vez:

```python
list(contar(3))   # [1, 2, 3]
```

## Por que usar?

- **Memória**: sequências enormes não ficam inteiras na memória.
- **Lazy**: os valores são calculados só quando pedidos.

> 💡 Todo generator é um **iterador**: você o percorre com `for` ou `next()`.
> Se a sequência for pequena, uma lista/comprehension normal resolve; para
> sequências grandes ou infinitas, generator é a ferramenta certa.
""",
                [
                    code(
                        "Defina um generator `contar(n)` que usa `yield` para produzir os números de 1 a `n`.",
                        "def contar(n):\n    for i in range(1, n + 1):\n        yield i",
                        "assert list(contar(3)) == [1, 2, 3], f'contar(3) deveria ser [1, 2, 3], mas deu {list(contar(3))!r}'\nassert list(contar(1)) == [1], 'contar(1) deveria ser [1]'",
                    ),
                    code(
                        "Defina um generator `dobros(limite)` que produz `i * 2` para `i` de 1 até `limite`.",
                        "def dobros(limite):\n    for i in range(1, limite + 1):\n        yield i * 2",
                        "assert list(dobros(3)) == [2, 4, 6], f'dobros(3) deveria ser [2, 4, 6], mas deu {list(dobros(3))!r}'",
                    ),
                    code(
                        "Use `next()` para obter o primeiro valor do generator `contar(10)` e guarde em `primeiro`.",
                        "def contar(n):\n    for i in range(1, n + 1):\n        yield i\n\nprimeiro = next(contar(10))",
                        "assert 'primeiro' in dir(), 'Crie a variável primeiro'\nassert primeiro == 1, f'primeiro deveria ser 1, mas é {primeiro!r}'",
                    ),
                    quiz(
                        "Qual palavra-chave transforma uma função em generator?",
                        "yield",
                        ["yield", "return", "loop"],
                    ),
                    quiz(
                        "Um generator devolve todos os valores de uma vez, como uma lista?",
                        "Não, ele produz um valor por vez, sob demanda (lazy)",
                        ["Não, ele produz um valor por vez, sob demanda (lazy)", "Sim, todos de uma vez", "Depende do tamanho"],
                    ),
                    quiz(
                        "Qual a principal vantagem de um generator para sequências grandes?",
                        "Não guarda a sequência inteira na memória",
                        ["Não guarda a sequência inteira na memória", "É sempre mais rápido que listas", "Permite usar yield e return juntos"],
                    ),
                    text(
                        "Complete: generators produzem os valores sob ___ (lazy).",
                        "demanda",
                    ),
                ],
            ),
            topic(
                "decorators",
                "Decorators",
                """
# Decorators

Um **decorator** é uma função que **recebe uma função** e **devolve uma versão
modificada** dela — um jeito elegante de adicionar comportamento sem mexer no
código original.

## Decorator na mão

```python
def dobrar_retorno(funcao):
    def interna(*args, **kwargs):
        return funcao(*args, **kwargs) * 2
    return interna
```

## Aplicando com @

```python
@dobrar_retorno
def get_cinco():
    return 5

get_cinco()   # 10
```

`@dobrar_retorno` é açúcar sintático para `get_cinco = dobrar_retorno(get_cinco)`.

## O que está acontecendo?

1. `get_cinco` é passada para `dobrar_retorno`.
2. `dobrar_retorno` devolve a função `interna` (que envolve a original).
3. Chamar `get_cinco()` agora chama `interna`, que chama a original e dobra.

## Casos de uso comuns

- Logar chamadas de função.
- Medir tempo de execução.
- Exigir autenticação (em web).

> 💡 `*args` e `**kwargs` na função interna garantem que o decorator funcione
> com qualquer assinatura — você viu esses dois no Módulo 6.
""",
                [
                    code(
                        "Defina um decorator `dobrar_retorno(funcao)` que devolve `interna(*args, **kwargs)` chamando a função original e retornando o dobro. Aplique com `@dobrar_retorno` numa função `get_cinco()` que retorna 5.",
                        "def dobrar_retorno(funcao):\n    def interna(*args, **kwargs):\n        return funcao(*args, **kwargs) * 2\n    return interna\n\n@dobrar_retorno\ndef get_cinco():\n    return 5",
                        "assert get_cinco() == 10, f'get_cinco() deveria ser 10, mas é {get_cinco()!r}'",
                    ),
                    code(
                        "Defina um decorator `somar_1(funcao)` que devolve `interna(*args, **kwargs)` retornando `funcao(*args, **kwargs) + 1`. Aplique em `base()` que retorna 41.",
                        "def somar_1(funcao):\n    def interna(*args, **kwargs):\n        return funcao(*args, **kwargs) + 1\n    return interna\n\n@somar_1\ndef base():\n    return 41",
                        "assert base() == 42, f'base() deveria ser 42, mas é {base()!r}'",
                    ),
                    quiz(
                        "O que um decorator faz?",
                        "Recebe uma função e devolve uma versão modificada dela",
                        ["Recebe uma função e devolve uma versão modificada dela", "Cria uma nova classe", "Deleta a função original"],
                    ),
                    quiz(
                        "Como você aplica o decorator `log` a uma função `f`?",
                        "@log acima da linha do def",
                        ["@log acima da linha do def", "log(f) dentro do corpo", "f.log()"],
                    ),
                    quiz(
                        "`@meu_decorator` em `def f():` é açúcar sintático para:",
                        "f = meu_decorator(f)",
                        ["f = meu_decorator(f)", "f = f.meu_decorator()", "meu_decorator = f"],
                    ),
                    text(
                        "Complete: decorators são aplicados com o símbolo ___ seguido do nome.",
                        "@",
                    ),
                ],
            ),
            topic(
                "context-managers",
                "Context managers (with)",
                """
# Context managers (with)

Um **context manager** garante que um recurso seja **preparado e liberado
corretamente**, mesmo quando um erro acontece. A sintaxe é o `with`:

```python
with open("dados.txt", "w") as arquivo:
    arquivo.write("olá")
# o arquivo é fechado automaticamente ao sair do with
```

Sem `with`, você teria que lembrar de fechar o arquivo na mão — e, num erro,
corria o risco de esquecer.

## Como funciona por dentro

O `with` chama dois métodos no objeto:

1. `__enter__`: roda ao **entrar** no bloco (prepara o recurso).
2. `__exit__`: roda ao **sair** do bloco, com ou sem erro (libera o recurso).

```python
class Marca:
    def __enter__(self):
        return "dentro do bloco"

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass   # limpeza

with Marca() as valor:
    print(valor)   # "dentro do bloco"
```

## Para que serve na prática

- Abrir/fechar arquivos e conexões.
- Travar e destravar recursos compartilhados.
- Garantir limpeza mesmo quando o código dentro lança exceção.

> 💡 O `finally` do tratamento de erros também garante execução — o `with`
> é a forma declarativa de fazer isso para recursos que têm "fim".
""",
                [
                    code(
                        "Defina a classe `Marca` com `__enter__` retornando `\"dentro\"` e `__exit__(self, exc_type, exc_val, exc_tb)` com `pass`. Use `with Marca() as valor:` para guardar o resultado em `resultado`.",
                        "class Marca:\n    def __enter__(self):\n        return \"dentro\"\n\n    def __exit__(self, exc_type, exc_val, exc_tb):\n        pass\n\nwith Marca() as valor:\n    resultado = valor",
                        "assert 'resultado' in dir(), 'Crie a variável resultado'\nassert resultado == 'dentro', f'resultado deveria ser dentro, mas é {resultado!r}'",
                    ),
                    code(
                        "Use `with open(\"notas.txt\", \"w\") as arquivo:` para escrever `\"10\"` no arquivo. Depois, fora do with, leia o arquivo com `open(\"notas.txt\")` e guarde o conteúdo em `conteudo`.",
                        "with open(\"notas.txt\", \"w\") as arquivo:\n    arquivo.write(\"10\")\nwith open(\"notas.txt\") as arquivo:\n    conteudo = arquivo.read()",
                        "assert 'conteudo' in dir(), 'Crie a variável conteudo'\nassert conteudo == '10', f'conteudo deveria ser 10, mas é {conteudo!r}'",
                    ),
                    quiz(
                        "O que o `with` garante ao trabalhar com recursos?",
                        "Que o recurso é liberado corretamente, mesmo com erro no bloco",
                        ["Que o recurso é liberado corretamente, mesmo com erro no bloco", "Que o recurso fica aberto para sempre", "Que o programa nunca falhe"],
                    ),
                    quiz(
                        "Quais dois métodos o `with` usa no objeto?",
                        "__enter__ e __exit__",
                        ["__enter__ e __exit__", "__init__ e __del__", "__str__ e __eq__"],
                    ),
                    quiz(
                        "Quando o `__exit__` é executado?",
                        "Ao sair do bloco, tenha havido erro ou não",
                        ["Ao sair do bloco, tenha havido erro ou não", "Somente se houve erro", "Somente se não houve erro"],
                    ),
                    text(
                        "Complete: o `with` é usado para gerenciar ___ (arquivos, conexões).",
                        "recursos",
                    ),
                ],
            ),
        ],
    )


# ============================================================
# MODULO 11 - Type Hints (novo, Fase 6 do roteiro)
# Código. Anotações rodam no Pyodide (são sintaxe pura).
# ============================================================

def build_modulo_type_hints():
    return module(
        "type-hints",
        "Módulo 11 — Type Hints",
        "Documentar e validar tipos com anotações: variáveis, coleções, funções e boas práticas de uso.",
        [
            topic(
                "anotacoes-basicas",
                "Anotações de tipo básicas",
                """
# Anotações de tipo básicas

**Type hints** (anotações de tipo) são a forma de **declarar** qual tipo um
valor deve ter. Usam dois-pontos na variável:

```python
nome: str = "Ana"
idade: int = 20
altura: float = 1.75
ativo: bool = True
```

## O que as anotações FAZEM?

- **Documentam** o código: deixam claro o que cada coisa é.
- **Ajudam ferramentas**: editores, IDEs e verificadores como `mypy` apontam
  erros antes de rodar.
- **Não mudam o runtime**: o Python ignora as anotações na execução.

## Um aviso importante

```python
idade: int = "vinte"   # anotou int, mas passou str...
print(idade)           # ...funciona! Python não obriga o tipo
```

As anotações são um **contrato para humanos e ferramentas**, não uma regra
forçada pelo interpretador.

> 💡 Pense em type hints como "documentação executável": leitura melhor para
> você e para quem lê seu código, e checagem gratuita em editores.
""",
                [
                    code(
                        "Crie `nome: str = \"Ana\"` e `idade: int = 20`.",
                        "nome: str = \"Ana\"\nidade: int = 20",
                        "assert nome == 'Ana', 'nome deveria ser Ana'\nassert type(nome) == str, 'nome deveria ser str'\nassert idade == 20, 'idade deveria ser 20'\nassert type(idade) == int, 'idade deveria ser int'",
                    ),
                    code(
                        "Crie `altura: float = 1.75` e `ativo: bool = True`.",
                        "altura: float = 1.75\nativo: bool = True",
                        "assert altura == 1.75 and type(altura) == float, 'altura deveria ser float 1.75'\nassert ativo == True and type(ativo) == bool, 'ativo deveria ser bool True'",
                    ),
                    quiz(
                        "Para que servem as anotações de tipo?",
                        "Documentar o código e ajudar ferramentas (editores, mypy)",
                        ["Documentar o código e ajudar ferramentas (editores, mypy)", "Acelerar a execução do programa", "Impedir erros de tipo em tempo de execução"],
                    ),
                    quiz(
                        "Anotações de tipo mudam o comportamento do programa em execução?",
                        "Não, o Python as ignora no runtime",
                        ["Não, o Python as ignora no runtime", "Sim, obrigam o tipo", "Só se o tipo for int"],
                    ),
                    quiz(
                        "O que acontece se você anota `idade: int = \"vinte\"`?",
                        "Funciona normalmente, pois o Python não obriga o tipo",
                        ["Funciona normalmente, pois o Python não obriga o tipo", "Levanta um TypeError", "O código não compila"],
                    ),
                    text(
                        "Complete: type hints são um contrato para humanos e ___.",
                        "ferramentas",
                    ),
                ],
            ),
            topic(
                "tipos-para-colecoes",
                "Tipos para coleções",
                """
# Tipos para coleções

Coleções também podem ser anotadas com o tipo dos elementos dentro de
colchetes (Python 3.9+):

```python
nomes: list[str] = ["Ana", "Bia"]
idades: dict[str, int] = {"Ana": 20}
notas: tuple[float, float] = (7.5, 8.0)
cores: set[str] = {"azul", "verde"}
```

## O que cada anotação significa

| Anotação | Significado |
|---|---|
| `list[str]` | lista de strings |
| `dict[str, int]` | dicionário com chave `str` e valor `int` |
| `tuple[int, int]` | tupla com 2 inteiros |
| `set[str]` | conjunto de strings |

## Valores opcionais

Um valor que pode ser `None` é anotado com `str | None` (Python 3.10+) ou
`Optional[str]`:

```python
def achar(nome: str) -> str | None:
    ...
```

> 💡 A ordem importa no `dict`: primeiro o tipo da **chave**, depois o do
> **valor**. No `tuple`, cada posição pode ter seu tipo.
""",
                [
                    code(
                        "Crie `nomes: list[str] = [\"Ana\"]` e `idades: dict[str, int] = {\"Ana\": 20}`.",
                        "nomes: list[str] = [\"Ana\"]\nidades: dict[str, int] = {\"Ana\": 20}",
                        "assert nomes == ['Ana'], 'nomes deveria ser [Ana]'\nassert idades['Ana'] == 20, 'idades deveria conter Ana: 20'",
                    ),
                    code(
                        "Crie `notas: tuple[float, float] = (7.5, 8.0)` e `cores: set[str] = {\"azul\"}`.",
                        "notas: tuple[float, float] = (7.5, 8.0)\ncores: set[str] = {\"azul\"}",
                        "assert notas == (7.5, 8.0), 'notas deveria ser (7.5, 8.0)'\nassert cores == {'azul'}, 'cores deveria ser {azul}'",
                    ),
                    quiz(
                        "O que `list[str]` significa?",
                        "Uma lista cujos elementos são strings",
                        ["Uma lista cujos elementos são strings", "Uma string que é uma lista", "Uma lista de listas"],
                    ),
                    quiz(
                        "O que `dict[str, int]` significa?",
                        "Dicionário com chave str e valor int",
                        ["Dicionário com chave str e valor int", "Dicionário com chave int e valor str", "Uma string com números"],
                    ),
                    quiz(
                        "Como se anota um valor que pode ser `str` ou `None`?",
                        "str | None",
                        ["str | None", "str & None", "Optional[str] é proibido"],
                    ),
                    text(
                        "Complete: no `dict[str, int]`, primeiro vem o tipo da ___, depois o do valor.",
                        "chave",
                    ),
                ],
            ),
            topic(
                "anotacoes-em-funcoes",
                "Anotações em funções",
                """
# Anotações em funções

Os parâmetros recebem anotação com `: tipo`, e o retorno com `-> tipo`:

```python
def dobro(n: int) -> int:
    return n * 2

def saudar(nome: str) -> str:
    return f"Olá, {nome}!"
```

## Lendo a assinatura

```python
def somar(a: int, b: int) -> int:
    return a + b
```

- `a: int` — o parâmetro `a` deve ser um inteiro.
- `b: int` — o parâmetro `b` deve ser um inteiro.
- `-> int` — a função retorna um inteiro.

## O que a ferramenta avisa

Com um verificador (ex.: `mypy`) ou o editor aberto, chamar `somar("x", 2)`
fica marcado como suspeito — o tipo do argumento não bate com a assinatura.
O Python em si **roda normalmente**.

## Sem anotação de retorno

Uma função sem `-> tipo` tem retorno "não anotado"; para deixar explícito que
retorna `None`, use `-> None`:

```python
def logar(mensagem: str) -> None:
    print(mensagem)
```

> 💡 Assinaturas anotadas funcionam como um **contrato** da função: quem chama
> sabe o que entra e o que sai sem precisar ler o corpo.
""",
                [
                    code(
                        "Defina `def dobro(n: int) -> int:` que retorna `n * 2`.",
                        "def dobro(n: int) -> int:\n    return n * 2",
                        "assert dobro(4) == 8, 'dobro(4) deveria ser 8'",
                    ),
                    code(
                        "Defina `def saudar(nome: str) -> str:` que retorna `f\"Olá, {nome}!\"`.",
                        "def saudar(nome: str) -> str:\n    return f\"Olá, {nome}!\"",
                        "assert saudar('Ana') == 'Olá, Ana!', f'saudar deu {saudar(\"Ana\")!r}'",
                    ),
                    code(
                        "Defina `def somar(a: int, b: int) -> int:` que retorna `a + b`.",
                        "def somar(a: int, b: int) -> int:\n    return a + b",
                        "assert somar(3, 4) == 7, 'somar(3, 4) deveria ser 7'",
                    ),
                    quiz(
                        "O que o `-> int` indica na definição de uma função?",
                        "O tipo do valor de retorno",
                        ["O tipo do valor de retorno", "Que a função imprime um int", "O número de parâmetros"],
                    ),
                    quiz(
                        "Onde ficam os type hints de uma função?",
                        "Nos parâmetros e no retorno",
                        ["Nos parâmetros e no retorno", "Somente no retorno", "No nome da função"],
                    ),
                    quiz(
                        "Uma função `def logar(m: str) -> None:` retorna:",
                        "None",
                        ["None", "a string m", "0"],
                    ),
                    text(
                        "Complete: a seta que indica o tipo de retorno é escrita como ___ tipo.",
                        "->",
                    ),
                ],
            ),
            topic(
                "quando-usar",
                "Quando e por que usar type hints",
                """
# Quando e por que usar type hints

Type hints **não são obrigatórios** — mas em projetos de verdade eles valem
muito a pena. A régua que a comunidade costuma usar:

- **Scripts rápidos e experimentos**: tudo bem sem hints.
- **Bibliotecas e projetos maiores**: hints quase sempre.
- **Interfaces públicas (funções que outros usam)**: sempre que possível.

## O que eles dão de concreto

- **Autocompletar no editor**: o IDE sugere métodos do tipo anotado.
- **Pegar bugs cedo**: ferramentas como `mypy` analisam o código **sem
  executar** (checagem estática) e apontam inconsistências.
- **Código que se explica**: a assinatura já conta o contrato.

## Ferramentas populares

| Ferramenta | O que faz |
|---|---|
| `mypy` | verificação estática de tipos |
| `pyright` | verificação de tipos (usado pelo VS Code / Pylance) |
| `ruff` | linter que também entende de tipos (chega no Módulo 15) |

## O essencial

Type hints são **recomendação forte**, não regra dura. O Python roda com ou
sem eles; quem ganha é você (e quem ler seu código).

> 💡 Em projetos pequenos de estudo, anote quando ajudar; em projetos que vão
> crescer, anote desde o começo — é muito mais fácil manter um código com os
> tipos declarados.
""",
                [
                    quiz(
                        "Type hints são obrigatórios em Python?",
                        "Não, são opcionais",
                        ["Não, são opcionais", "Sim, desde o Python 3", "Só em classes"],
                    ),
                    quiz(
                        "O que um verificador como `mypy` faz?",
                        "Analisa o código sem executar e aponta inconsistências de tipo",
                        ["Analisa o código sem executar e aponta inconsistências de tipo", "Roda o programa mais rápido", "Instala pacotes"],
                    ),
                    quiz(
                        "Qual é um benefício prático dos type hints no editor?",
                        "Autocompletar e avisos de tipo ao escrever",
                        ["Autocompletar e avisos de tipo ao escrever", "Deixar o arquivo menor", "Impedir o uso de variáveis"],
                    ),
                    quiz(
                        "Em qual cenário type hints valem mais a pena?",
                        "Projetos maiores e interfaces que outras pessoas usam",
                        ["Projetos maiores e interfaces que outras pessoas usam", "Scripts de uma linha", "Em nenhum cenário"],
                    ),
                    text(
                        "Complete: type hints são uma ___ forte, não uma regra dura.",
                        "recomendação",
                    ),
                ],
            ),
        ],
    )


# ============================================================
# MODULO 12 - Arquivos e Dados (novo, Fase 7 do roteiro)
# Código. I/O de arquivo funciona no Pyodide (sistema de arquivos
# virtual em memória). CSV e JSON usam a biblioteca padrão.
# ============================================================

def build_modulo_arquivos():
    return module(
        "arquivos-e-dados",
        "Módulo 12 — Arquivos e Dados",
        "Guardar e ler dados de verdade: ler e escrever arquivos de texto, e trabalhar com CSV e JSON.",
        [
            topic(
                "lendo-arquivos",
                "Lendo arquivos",
                """
# Lendo arquivos

Para ler um arquivo, use `open()` dentro de um `with` (o `with` garante que o
arquivo será fechado):

```python
with open("dados.txt") as arquivo:
    conteudo = arquivo.read()

print(conteudo)
```

## Três formas de ler

```python
conteudo = arquivo.read()       # o conteúdo inteiro, numa string
linhas = arquivo.readlines()    # uma lista, um item por linha
```

Também dá para percorrer linha por linha com `for`:

```python
with open("nomes.txt") as arquivo:
    for linha in arquivo:
        print(linha.strip())
```

## O modo de abertura

O segundo argumento do `open()` é o modo. Para leitura, é o `"r"` — que é o
**padrão**, então pode ser omitido:

```python
open("dados.txt")        # idêntico a open("dados.txt", "r")
```

> 💡 `read()` devolve o texto com as quebras de linha inclusas. O `strip()` é
> útil para tirar o `\\n` de cada linha ao processar.
""",
                [
                    code(
                        "Crie o arquivo `nomes.txt` escrevendo `Ana\\nBia` e depois leia o conteúdo inteiro com `with open(...)` guardando em `conteudo`.",
                        "with open(\"nomes.txt\", \"w\") as f:\n    f.write(\"Ana\\nBia\")\nwith open(\"nomes.txt\") as f:\n    conteudo = f.read()",
                        "assert 'conteudo' in dir(), 'Crie a variável conteudo'\nassert conteudo == 'Ana\\nBia', f'conteudo deveria ser Ana\\nBia, mas é {conteudo!r}'",
                    ),
                    code(
                        "Crie o arquivo `cidades.txt` com `SP\\nRJ\\nMG` e depois leia as linhas com `readlines()` guardando em `linhas`.",
                        "with open(\"cidades.txt\", \"w\") as f:\n    f.write(\"SP\\nRJ\\nMG\")\nwith open(\"cidades.txt\") as f:\n    linhas = f.readlines()",
                        "assert 'linhas' in dir(), 'Crie a variável linhas'\nassert linhas == ['SP\\n', 'RJ\\n', 'MG'], f'linhas ficou: {linhas!r}'",
                    ),
                    code(
                        "Crie o arquivo `nums.txt` com `1\\n2\\n3`, leia linha por linha com um `for` e some os números (convertendo com `int`), guardando o total em `total`.",
                        "with open(\"nums.txt\", \"w\") as f:\n    f.write(\"1\\n2\\n3\")\ntotal = 0\nwith open(\"nums.txt\") as f:\n    for linha in f:\n        total = total + int(linha.strip())",
                        "assert 'total' in dir(), 'Crie a variável total'\nassert total == 6, f'total deveria ser 6, mas é {total!r}'",
                    ),
                    quiz(
                        "Qual é o modo padrão do `open()` (que abre para leitura)?",
                        "r",
                        ["r", "w", "a"],
                    ),
                    quiz(
                        "O que o método `read()` de um arquivo retorna?",
                        "O conteúdo inteiro, como uma string",
                        ["O conteúdo inteiro, como uma string", "Uma lista de linhas", "O tamanho do arquivo"],
                    ),
                    quiz(
                        "O que o método `readlines()` retorna?",
                        "Uma lista com uma string por linha",
                        ["Uma lista com uma string por linha", "O conteúdo inteiro numa string", "Um dicionário"],
                    ),
                ],
            ),
            topic(
                "escrevendo-arquivos",
                "Escrevendo arquivos",
                """
# Escrevendo arquivos

Para **escrever** em um arquivo, passe o modo no `open()`:

```python
with open("saida.txt", "w") as arquivo:
    arquivo.write("Olá, mundo!")
```

## Os modos de escrita

| Modo | Comportamento |
|---|---|
| `"w"` | **sobrescreve** (apaga o conteúdo anterior e escreve) |
| `"a"` | **adiciona** ao final (append), sem apagar o que já existe |

## Exemplo de append

```python
with open("log.txt", "a") as arquivo:
    arquivo.write("nova linha\\n")
```

Se o arquivo não existir, tanto `"w"` quanto `"a"` **criam** o arquivo.

## Vários write seguidos

Cada `write()` continua de onde o anterior parou:

```python
with open("texto.txt", "w") as f:
    f.write("Primeira parte, ")
    f.write("segunda parte.")
```

> ⚠️ Cuidado com `"w"`: ele apaga tudo do arquivo antes de escrever. Se você
> quer acrescentar, use `"a"`.
""",
                [
                    code(
                        "Escreva `\"Olá, arquivo!\"` num arquivo `saida.txt` usando modo `\"w\"`, e depois leia de volta confirmando em `conteudo`.",
                        "with open(\"saida.txt\", \"w\") as f:\n    f.write(\"Olá, arquivo!\")\nwith open(\"saida.txt\") as f:\n    conteudo = f.read()",
                        "assert 'conteudo' in dir(), 'Crie a variável conteudo'\nassert conteudo == 'Olá, arquivo!', f'conteudo deveria ser Olá, arquivo!, mas é {conteudo!r}'",
                    ),
                    code(
                        "Crie `log.txt` com `linha 1` usando `\"w\"`; depois use modo `\"a\"` para adicionar `\\nlinha 2`; leia o arquivo e guarde em `conteudo`.",
                        "with open(\"log.txt\", \"w\") as f:\n    f.write(\"linha 1\")\nwith open(\"log.txt\", \"a\") as f:\n    f.write(\"\\nlinha 2\")\nwith open(\"log.txt\") as f:\n    conteudo = f.read()",
                        "assert 'conteudo' in dir(), 'Crie a variável conteudo'\nassert conteudo == 'linha 1\\nlinha 2', f'conteudo deveria ser linha 1\\nlinha 2, mas é {conteudo!r}'",
                    ),
                    code(
                        "Escreva `\"1\"` num arquivo `num.txt` com `\"w\"`, depois escreva `\"2\"` de novo com `\"w\"` (sobrescrevendo) e leia, guardando em `conteudo`.",
                        "with open(\"num.txt\", \"w\") as f:\n    f.write(\"1\")\nwith open(\"num.txt\", \"w\") as f:\n    f.write(\"2\")\nwith open(\"num.txt\") as f:\n    conteudo = f.read()",
                        "assert 'conteudo' in dir(), 'Crie a variável conteudo'\nassert conteudo == '2', f'com w duas vezes, conteudo deveria ser 2, mas é {conteudo!r}'",
                    ),
                    quiz(
                        "O que o modo `\"w\"` faz com o conteúdo anterior do arquivo?",
                        "Apaga e sobrescreve",
                        ["Apaga e sobrescreve", "Adiciona ao final", "Não mexe no conteúdo"],
                    ),
                    quiz(
                        "O que o modo `\"a\"` faz?",
                        "Adiciona ao final, sem apagar o que já existe",
                        ["Adiciona ao final, sem apagar o que já existe", "Apaga e sobrescreve", "Impede a escrita"],
                    ),
                    quiz(
                        "Se o arquivo não existe e você usa `\"w\"`, o que acontece?",
                        "O arquivo é criado",
                        ["O arquivo é criado", "Levanta um erro", "Nada é feito"],
                    ),
                    text(
                        "Complete: para acrescentar ao final de um arquivo, use o modo ___.",
                        "a",
                    ),
                ],
            ),
            topic(
                "trabalhando-com-csv",
                "Trabalhando com CSV",
                """
# Trabalhando com CSV

**CSV** (*Comma-Separated Values*) é um formato de dados em texto, onde cada
linha é um registro e os valores são separados por vírgula:

```csv
nome,idade
Ana,20
Bia,19
```

O módulo `csv` da biblioteca padrão lê e escreve isso sem esforço.

## Escrevendo um CSV

```python
import csv

with open("pessoas.csv", "w", newline="") as arquivo:
    escritor = csv.writer(arquivo)
    escritor.writerow(["nome", "idade"])
    escritor.writerow(["Ana", 20])
```

## Lendo um CSV

```python
import csv

with open("pessoas.csv") as arquivo:
    leitor = csv.reader(arquivo)
    linhas = list(leitor)   # [["nome","idade"], ["Ana","20"], ...]
```

## Lendo como dicionários

Com `DictReader`, a primeira linha vira as chaves:

```python
with open("pessoas.csv") as arquivo:
    for pessoa in csv.DictReader(arquivo):
        print(pessoa["nome"])   # Ana
```

> 💡 O `newline=""` no `open` ao escrever evita linhas em branco extras em
> alguns sistemas. Valores lidos vêm como texto — converta com `int()` quando
> precisar de número.
""",
                [
                    code(
                        "Crie `pessoas.csv` com `csv.writer` escrevendo as linhas `[\"nome\", \"idade\"]` e `[\"Ana\", 20]` (use `writerow` duas vezes). Depois leia com `csv.reader` guardando tudo em `linhas`.",
                        "import csv\nwith open(\"pessoas.csv\", \"w\", newline=\"\") as f:\n    escritor = csv.writer(f)\n    escritor.writerow([\"nome\", \"idade\"])\n    escritor.writerow([\"Ana\", 20])\nwith open(\"pessoas.csv\") as f:\n    linhas = list(csv.reader(f))",
                        "assert 'linhas' in dir(), 'Crie a variável linhas'\nassert linhas == [[\"nome\", \"idade\"], [\"Ana\", \"20\"]], f'linhas ficou: {linhas!r}'",
                    ),
                    code(
                        "Crie `notas.csv` com `csv.writer` escrevendo `[\"aluno\", \"nota\"]` e `[\"Ana\", 10]`. Depois leia com `csv.DictReader` e guarde a nota da Ana em `nota_ana` (convertendo com `int`).",
                        "import csv\nwith open(\"notas.csv\", \"w\", newline=\"\") as f:\n    escritor = csv.writer(f)\n    escritor.writerow([\"aluno\", \"nota\"])\n    escritor.writerow([\"Ana\", 10])\nwith open(\"notas.csv\") as f:\n    for linha in csv.DictReader(f):\n        nota_ana = int(linha[\"nota\"])",
                        "assert 'nota_ana' in dir(), 'Crie a variável nota_ana'\nassert nota_ana == 10, f'nota_ana deveria ser 10, mas é {nota_ana!r}'",
                    ),
                    quiz(
                        "O que significa a sigla CSV?",
                        "Valores separados por vírgula",
                        ["Valores separados por vírgula", "Comando de sistema virtual", "Dados salvos em cache"],
                    ),
                    quiz(
                        "Qual módulo da biblioteca padrão lê e escreve CSV?",
                        "csv",
                        ["csv", "json", "sqlite3"],
                    ),
                    quiz(
                        "Qual classe do módulo csv usa a primeira linha como chaves?",
                        "DictReader",
                        ["DictReader", "reader", "Writer"],
                    ),
                    text(
                        "Complete: os valores lidos de um CSV vêm como ___.",
                        "texto",
                    ),
                ],
            ),
            topic(
                "trabalhando-com-json",
                "Trabalhando com JSON",
                """
# Trabalhando com JSON

**JSON** (*JavaScript Object Notation*) é o formato mais usado para trocar
dados entre sistemas (APIs). Ele parece com um dicionário Python:

```json
{"nome": "Ana", "idade": 20}
```

O módulo `json` converte entre Python e JSON.

## Para strings: dumps e loads

```python
import json

# Python -> string JSON
texto = json.dumps({"nome": "Ana", "idade": 20})
# '{"nome": "Ana", "idade": 20}'

# string JSON -> Python
dados = json.loads('{"nome": "Ana"}')
# {'nome': 'Ana'}
```

## Para arquivos: dump e load

```python
with open("dados.json", "w") as f:
    json.dump({"nome": "Ana"}, f)

with open("dados.json") as f:
    dados = json.load(f)
```

> 💡 Dica de memória: `dumps`/`loads` (com `s`) são **strings**;
> `dump`/`load` (sem `s`) são **arquivos**.
""",
                [
                    code(
                        "Importe `json` e serialize `pessoa = {\"nome\": \"Ana\", \"idade\": 20}` com `json.dumps`, guardando em `texto`.",
                        "import json\npessoa = {\"nome\": \"Ana\", \"idade\": 20}\ntexto = json.dumps(pessoa)",
                        "assert 'texto' in dir(), 'Crie a variável texto'\nassert texto == '{\"nome\": \"Ana\", \"idade\": 20}', f'texto ficou: {texto!r}'",
                    ),
                    code(
                        "Importe `json` e converta a string `'{\"nome\": \"Ana\"}'` de volta para um dicionário com `json.loads`, guardando em `dados`.",
                        "import json\ndados = json.loads('{\"nome\": \"Ana\"}')",
                        "assert 'dados' in dir(), 'Crie a variável dados'\nassert dados == {'nome': 'Ana'}, f'dados ficou: {dados!r}'",
                    ),
                    code(
                        "Use `json.dump` para salvar `{\"cidade\": \"SP\"}` no arquivo `dados.json` e depois leia de volta com `json.load`, guardando em `carregado`.",
                        "import json\nwith open(\"dados.json\", \"w\") as f:\n    json.dump({\"cidade\": \"SP\"}, f)\nwith open(\"dados.json\") as f:\n    carregado = json.load(f)",
                        "assert 'carregado' in dir(), 'Crie a variável carregado'\nassert carregado == {'cidade': 'SP'}, f'carregado ficou: {carregado!r}'",
                    ),
                    quiz(
                        "O que `json.dumps` faz?",
                        "Converte um objeto Python em uma string JSON",
                        ["Converte um objeto Python em uma string JSON", "Converte uma string JSON em um objeto Python", "Salva um objeto num arquivo"],
                    ),
                    quiz(
                        "O que `json.loads` faz?",
                        "Converte uma string JSON em um objeto Python",
                        ["Converte uma string JSON em um objeto Python", "Converte um objeto Python em string JSON", "Lê um arquivo JSON"],
                    ),
                    quiz(
                        "Qual a diferença entre `dumps` e `dump`?",
                        "dumps mexe em strings; dump em arquivos",
                        ["dumps mexe em strings; dump em arquivos", "São idênticos", "dumps é mais rápido que dump"],
                    ),
                    text(
                        "Complete: `dump`/`load` (sem s) trabalham com ___; `dumps`/`loads` com strings.",
                        "arquivos",
                    ),
                ],
            ),
        ],
    )


# ============================================================
# MODULO 13 - Bibliotecas e Dependências (novo, Fase 7 do roteiro)
# Conceitual. pip/venv/requirements não rodam no Pyodide.
# ============================================================

def build_modulo_dependencias():
    return module(
        "bibliotecas-e-dependencias",
        "Módulo 13 — Bibliotecas e Dependências",
        "Não reinventar a roda: o que são bibliotecas, como o pip instala pacotes, ambientes virtuais e o ecossistema Python.",
        [
            topic(
                "o-que-sao-bibliotecas",
                "O que são bibliotecas?",
                """
# O que são bibliotecas?

Uma **biblioteca** é um conjunto de código pronto, empacotado, que você
**importa** para usar em vez de escrever do zero. É o famoso "não reinventar
a roda".

## Biblioteca padrão vs. de terceiros

| Tipo | De onde vem | Exemplos |
|---|---|---|
| Padrão | já vem com o Python | `math`, `json`, `csv`, `random`, `os` |
| Terceiros | baixados do PyPI | `requests`, `numpy`, `fastapi`, `pandas` |

## Por que usar bibliotecas?

- **Economia**: problemas complexos já resolvidos por especialistas.
- **Confiabilidade**: bibliotecas populares são testadas por milhares de
  pessoas.
- **Foco**: você escreve só a parte específica do seu problema.

```python
import math          # padrão — vem com o Python
import requests      # terceiros — precisa instalar com pip
```

> 💡 O Módulo 8 mostrou o `import` e a biblioteca padrão. A diferença aqui:
  bibliotecas de terceiros precisam ser **instaladas** antes de importar.
""",
                [
                    quiz(
                        "O que é uma biblioteca em Python?",
                        "Um conjunto de código pronto, empacotado, para reutilizar",
                        ["Um conjunto de código pronto, empacotado, para reutilizar", "Um tipo de variável", "Um comando do terminal"],
                    ),
                    quiz(
                        "Qual é a diferença entre biblioteca padrão e de terceiros?",
                        "A padrão vem com o Python; a de terceiros é baixada do PyPI",
                        ["A padrão vem com o Python; a de terceiros é baixada do PyPI", "A padrão é paga; a de terceiros é grátis", "Não há diferença"],
                    ),
                    quiz(
                        "Qual é a principal vantagem de usar bibliotecas?",
                        "Não reinventar a roda: usar código pronto e testado",
                        ["Não reinventar a roda: usar código pronto e testado", "Deixar o código maior", "Evitar usar import"],
                    ),
                    quiz(
                        "Qual dessas é uma biblioteca de TERCEIROS (precisa instalar)?",
                        "requests",
                        ["requests", "math", "json"],
                    ),
                    text(
                        "Complete: bibliotecas de terceiros precisam ser ___ antes de importar.",
                        "instaladas",
                    ),
                ],
            ),
            topic(
                "pip-e-instalacao",
                "O pip e a instalação de pacotes",
                """
# O pip e a instalação de pacotes

O **pip** é o gerenciador de pacotes do Python. Ele baixa bibliotecas do
**PyPI** e as instala na sua máquina.

## Comandos essenciais

```bash
pip install requests       # instala a biblioteca requests
pip install numpy pandas   # instala várias de uma vez
pip list                   # lista o que está instalado
pip uninstall requests     # desinstala
```

## O fluxo típico

```bash
pip install requests
```

```python
import requests   # agora funciona!
```

## De onde vêm os pacotes

O PyPI (*Python Package Index*) é o repositório público onde a comunidade
publica milhões de pacotes. Quando você roda `pip install`, o pip procura lá,
baixa e instala — inclusive as dependências do pacote.

> 💻 No seu terminal, rode `pip --version` para confirmar que o pip está
> instalado (Módulo 8). Depois, num diretório de teste, rode
> `pip install requests` e tente `import requests` no REPL (`python`).
""",
                [
                    quiz(
                        "O que é o pip?",
                        "O gerenciador de pacotes padrão do Python",
                        ["O gerenciador de pacotes padrão do Python", "Um editor de código", "Um navegador"],
                    ),
                    quiz(
                        "Qual comando instala a biblioteca `requests`?",
                        "pip install requests",
                        ["pip install requests", "install requests", "pip get requests"],
                    ),
                    quiz(
                        "De onde o pip baixa os pacotes?",
                        "Do PyPI",
                        ["Do PyPI", "Do GitHub", "De uma loja de apps"],
                    ),
                    quiz(
                        "Qual comando mostra os pacotes instalados?",
                        "pip list",
                        ["pip list", "pip show all", "list pip"],
                    ),
                    text(
                        "Complete: o pip instala as bibliotecas e suas ___ automaticamente.",
                        "dependências",
                    ),
                ],
            ),
            topic(
                "ambientes-virtuais",
                "Ambientes virtuais (venv)",
                """
# Ambientes virtuais (venv)

Um **ambiente virtual** é uma cópia isolada do Python dentro do seu projeto.
Cada projeto pode ter suas próprias versões de bibliotecas, sem conflitar com
outros projetos.

## Por que isso é importante?

Sem isolamento, dois projetos no mesmo computador podem querer **versões
diferentes** da mesma biblioteca — e uma quebra a outra. Com venv, cada um
fica no seu canto.

## Criando e usando um venv

No terminal, dentro do diretório do projeto:

```bash
python -m venv venv
```

Isso cria uma pasta `venv/` com um Python isolado. Depois é preciso
**ativar**:

| Sistema | Comando de ativação |
|---|---|
| Windows | `venv\\Scripts\\activate` |
| macOS/Linux | `source venv/bin/activate` |

Com o ambiente ativo, o `pip install` instala **dentro do venv**, não no
Python global.

## Quando desativar

```bash
deactivate
```

> 💻 No seu terminal, crie uma pasta de teste, rode `python -m venv venv`,
> ative conforme seu sistema, e confira que o prompt do terminal muda
> (geralmente mostra `(venv)` antes do caminho).
""",
                [
                    quiz(
                        "O que é um ambiente virtual?",
                        "Uma cópia isolada do Python para um projeto",
                        ["Uma cópia isolada do Python para um projeto", "Uma pasta com o código-fonte do Python", "Um tipo de biblioteca"],
                    ),
                    quiz(
                        "Qual é o principal motivo para usar venv?",
                        "Cada projeto tem suas versões de bibliotecas, sem conflito",
                        ["Cada projeto tem suas versões de bibliotecas, sem conflito", "Deixar o computador mais rápido", "Evitar usar o pip"],
                    ),
                    quiz(
                        "Qual comando cria um ambiente virtual chamado venv?",
                        "python -m venv venv",
                        ["python -m venv venv", "venv create", "pip create venv"],
                    ),
                    quiz(
                        "Qual comando ativa o venv no Windows?",
                        "venv\\Scripts\\activate",
                        ["venv\\Scripts\\activate", "source venv/bin/activate", "activate venv"],
                    ),
                    text(
                        "Complete: com o ambiente ativo, o pip instala ___ do venv, não no Python global.",
                        "dentro",
                    ),
                ],
            ),
            topic(
                "requirements-e-pyproject",
                "Requirements e pyproject.toml",
                """
# Requirements e pyproject.toml

Para que outra pessoa (ou você, num computador novo) consiga rodar seu
projeto, é preciso registrar as dependências — as bibliotecas que ele usa.

## requirements.txt

Um arquivo simples, uma dependência por linha:

```text
requests==2.32.3
numpy>=1.26
fastapi
```

Para instalar tudo de uma vez:

```bash
pip install -r requirements.txt
```

## pyproject.toml

Formato mais novo e completo de configurar um projeto Python (usado pelo
pip moderno, poetry, etc.). Além das dependências, guarda metadados, a
ferramenta de build e configuração de linters.

```toml
[project]
name = "meu-projeto"
version = "0.1.0"
dependencies = [
    "requests>=2.31",
]
```

## Por que versionar dependências?

**Reprodutibilidade**: fixar versões (ex.: `requests==2.32.3`) garante que o
projeto rode igual hoje e daqui a um ano. Uma biblioteca nova pode quebrar
compatibilidade.

> 💡 Regra prática: use `requirements.txt` para projetos simples e
> `pyproject.toml` quando quiser um projeto com metadados completos e
> configuração de ferramentas.
""",
                [
                    quiz(
                        "O que é o arquivo `requirements.txt`?",
                        "A lista de dependências (bibliotecas) do projeto",
                        ["A lista de dependências (bibliotecas) do projeto", "O código-fonte principal", "O log de erros"],
                    ),
                    quiz(
                        "Como você instala todas as dependências listadas num requirements.txt?",
                        "pip install -r requirements.txt",
                        ["pip install -r requirements.txt", "pip install requirements", "run requirements.txt"],
                    ),
                    quiz(
                        "O que é o `pyproject.toml`?",
                        "O arquivo de configuração moderno do projeto Python",
                        ["O arquivo de configuração moderno do projeto Python", "Um arquivo de imagem", "Um tipo de requirements"],
                    ),
                    quiz(
                        "Por que fixar versões de dependências (ex.: `requests==2.32.3`)?",
                        "Para o projeto rodar igual em qualquer momento (reprodutibilidade)",
                        ["Para o projeto rodar igual em qualquer momento (reprodutibilidade)", "Para o pip ficar mais rápido", "Porque versões sempre são melhores"],
                    ),
                    text(
                        "Complete: registrar as dependências permite ___ o projeto em qualquer máquina.",
                        "rodar",
                    ),
                ],
            ),
            topic(
                "ecossistema-python",
                "O ecossistema Python",
                """
# O ecossistema Python

Uma das maiores forças do Python é o **ecossistema**: milhares de bibliotecas
prontas para quase toda área. Algumas que você vai encontrar com frequência:

| Área | Bibliotecas |
|---|---|
| Web / APIs | `FastAPI`, `Flask`, `Django` |
| Dados / tabelas | `pandas`, `numpy` |
| Visualização | `matplotlib`, `seaborn`, `plotly` |
| Requisições HTTP | `requests`, `httpx` |
| Testes | `pytest` |
| IA / ML | `scikit-learn`, `pytorch`, `tensorflow` |
| LLMs | `openai`, `langchain` |

## Como escolher uma biblioteca

- **Popularidade**: quantas pessoas usam (milhões = testada).
- **Manutenção**: tem releases recentes e mantenedores ativos?
- **Documentação**: tem exemplos bons e claros?
- **Comunidade**: é fácil achar respostas quando trava?

## O ciclo

```
pip install <biblioteca>  ->  import <biblioteca>  ->  usar
```

> 💡 Você não precisa decorar nenhuma lista — mas quanto mais áreas você
> conhecer, mais fácil é "saber o que existe" antes de programar do zero.
> Nas fases finais do curso, FastAPI (web) e IA usam esse ecossistema.
""",
                [
                    quiz(
                        "Quais bibliotecas são comuns para trabalhar com dados em tabelas?",
                        "pandas e numpy",
                        ["pandas e numpy", "requests e httpx", "fastapi e flask"],
                    ),
                    quiz(
                        "Qual biblioteca é usada para fazer requisições HTTP?",
                        "requests",
                        ["requests", "pandas", "matplotlib"],
                    ),
                    quiz(
                        "Qual biblioteca é usada para criar APIs web (usada mais adiante no curso)?",
                        "FastAPI",
                        ["FastAPI", "pytest", "numpy"],
                    ),
                    quiz(
                        "Qual destes é um critério para escolher uma biblioteca?",
                        "Popularidade e manutenção ativa",
                        ["Popularidade e manutenção ativa", "Ter o nome mais curto", "Estar sempre na primeira versão"],
                    ),
                    text(
                        "Complete o ciclo: pip install -> ___ -> usar.",
                        "import",
                    ),
                ],
            ),
        ],
    )


# ============================================================
# MODULO 14 - Git e GitHub (novo, Fase 7 do roteiro)
# Conceitual. Git não roda no Pyodide; lição sugere rodar no
# terminal próprio, sempre comando já explicado.
# ============================================================

def build_modulo_git():
    return module(
        "git-e-github",
        "Módulo 14 — Git e GitHub",
        "Versionar código e colaborar: o que é Git, comandos essenciais, branches, GitHub e o fluxo de trabalho com pull requests.",
        [
            topic(
                "o-que-e-git",
                "O que é o Git?",
                """
# O que é o Git?

O **Git** é um **sistema de controle de versão**: ele registra o histórico de
mudanças do seu código, permitindo voltar a qualquer ponto, comparar versões e
colaborar sem pisar no trabalho dos outros.

Criado por **Linus Torvalds** (mesmo criador do Linux), é o padrão da indústria.

## Conceitos-chave

- **Repositório (repo)**: a pasta do projeto que o Git acompanha, com todo o
  histórico de versões.
- **Commit**: um "retrato" (snapshot) do código num momento. Cada commit tem
  uma mensagem que explica o que mudou.
- **Histórico**: a linha do tempo de commits, onde você pode navegar e voltar.

## O que o controle de versão resolve

- "Apaguei um arquivo sem querer" → recupera do histórico.
- "Isso funcionava semana passada" → compara versões e acha a mudança.
- "Duas pessoas mexendo no mesmo projeto" → Git junta as mudanças.

> 💻 Confira se o Git está instalado no seu terminal: rode `git --version`
> (o mesmo padrão do `python --version` que você já conhece do Módulo 2).
""",
                [
                    quiz(
                        "O que é o Git?",
                        "Um sistema de controle de versão",
                        ["Um sistema de controle de versão", "Um editor de código", "Um navegador"],
                    ),
                    quiz(
                        "O que é um repositório (repo)?",
                        "A pasta do projeto acompanhada pelo Git, com histórico",
                        ["A pasta do projeto acompanhada pelo Git, com histórico", "Um arquivo de configuração", "Um tipo de commit"],
                    ),
                    quiz(
                        "O que é um commit?",
                        "Um retrato do código num momento, com mensagem",
                        ["Um retrato do código num momento, com mensagem", "Um erro do programa", "Uma branch"],
                    ),
                    quiz(
                        "Quem criou o Git?",
                        "Linus Torvalds",
                        ["Linus Torvalds", "Guido van Rossum", "Bill Gates"],
                    ),
                    text(
                        "Complete: o Git registra o ___ de mudanças do código.",
                        "histórico",
                    ),
                ],
            ),
            topic(
                "comandos-basicos",
                "Comandos básicos do Git",
                """
# Comandos básicos do Git

O ciclo diário do Git gira em torno de 4 comandos:

## 1. git init — inicia um repositório

```bash
git init
```

Cria a estrutura interna do Git na pasta atual (uma pasta oculta `.git`).

## 2. git status — mostra o estado

```bash
git status
```

Mostra quais arquivos mudaram, quais estão prontos para o commit etc.

## 3. git add — prepara arquivos (stage)

```bash
git add arquivo.py     # um arquivo
git add .              # tudo na pasta atual
```

"Preparar" (stage) escolhe o que vai entrar no próximo commit.

## 4. git commit — registra a versão

```bash
git commit -m "adiciona cálculo de média"
```

Guarda o snapshot com uma **mensagem** descrevendo a mudança.

## Bônus: git log

```bash
git log
```

Mostra o histórico de commits.

> 💻 O ciclo do dia a dia: mude o código, `git status` para ver, `git add`,
> `git commit -m "mensagem"`. Rode isso num projeto de teste no seu terminal —
> são os 4 comandos que você usará o tempo todo.
""",
                [
                    quiz(
                        "Qual comando inicia um repositório Git numa pasta?",
                        "git init",
                        ["git init", "git start", "git new"],
                    ),
                    quiz(
                        "Qual comando mostra o estado atual dos arquivos?",
                        "git status",
                        ["git status", "git state", "git show now"],
                    ),
                    quiz(
                        "Qual comando prepara os arquivos para o commit (stage)?",
                        "git add",
                        ["git add", "git commit", "git push"],
                    ),
                    quiz(
                        "Qual comando registra uma versão com mensagem?",
                        "git commit -m \"mensagem\"",
                        ["git commit -m \"mensagem\"", "git save -m \"mensagem\"", "git version -m \"mensagem\""],
                    ),
                    quiz(
                        "Qual comando mostra o histórico de commits?",
                        "git log",
                        ["git log", "git history", "git list"],
                    ),
                    text(
                        "Complete: o ciclo básico é: mudar código, git ___, git commit.",
                        "add",
                    ),
                ],
            ),
            topic(
                "branches",
                "Branches (ramificações)",
                """
# Branches (ramificações)

Uma **branch** é uma linha de desenvolvimento separada. O projeto principal
costuma ficar na branch `main` (antes chamada de `master`), e você cria
branches para desenvolver sem quebrar o que já funciona.

## Visualizando

```bash
git branch            # lista as branches
git branch nova-feat  # cria a branch nova-feat
git checkout nova-feat  # muda para ela
# atalho: git checkout -b nova-feat  (cria e muda)
```

## Por que usar?

- Trabalhar numa feature sem mexer no `main`.
- Experimentar sem medo de estragar.
- Cada pessoa trabalha na sua branch e depois juntam.

## Juntando (merge)

Quando a branch está pronta, você volta para `main` e junta:

```bash
git checkout main
git merge nova-feat
```

> 💡 A branch `main` é a versão "estável". Desenvolver em branches separadas e
> só juntar o que está pronto é a base do fluxo profissional (próximos tópicos).
""",
                [
                    quiz(
                        "O que é uma branch no Git?",
                        "Uma linha de desenvolvimento separada",
                        ["Uma linha de desenvolvimento separada", "Um commit apagado", "Um repositório remoto"],
                    ),
                    quiz(
                        "Qual é o nome padrão da branch principal?",
                        "main",
                        ["main", "principal", "root"],
                    ),
                    quiz(
                        "Qual comando cria uma branch chamada nova-feat?",
                        "git branch nova-feat",
                        ["git branch nova-feat", "git create nova-feat", "git new nova-feat"],
                    ),
                    quiz(
                        "Qual comando junta a branch nova-feat na branch atual?",
                        "git merge nova-feat",
                        ["git merge nova-feat", "git join nova-feat", "git combine nova-feat"],
                    ),
                    text(
                        "Complete: branches permitem desenvolver sem quebrar a branch ___.",
                        "main",
                    ),
                ],
            ),
            topic(
                "github-e-remotes",
                "GitHub e repositórios remotos",
                """
# GitHub e repositórios remotos

O **Git** é local (funciona no seu computador). O **GitHub** é um serviço
online que hospeda repositórios Git — a "versão na nuvem" onde o time
colabora. (Existem alternativas como GitLab e Bitbucket.)

## Remotes: o endereço da nuvem

O repositório local aponta para um **remote** (um repositório na internet):

```bash
git remote add origin https://github.com/usuario/projeto.git
```

## Os 3 comandos essenciais

```bash
git clone https://github.com/usuario/projeto.git   # copia um repositório
git push origin main                               # envia commits para o remoto
git pull origin main                               # baixa as mudanças do remoto
```

- **clone**: traz um projeto para a sua máquina (com todo o histórico).
- **push**: envia seus commits locais para o remoto.
- **pull**: traz os commits dos outros para o seu local.

> 💻 Num projeto de estudo, crie um repositório vazio no GitHub e rode
> `git push origin main` para ver seus commits aparecerem lá. Se preferir,
> `git clone` um repositório público para praticar.
""",
                [
                    quiz(
                        "O que é o GitHub?",
                        "Um serviço online que hospeda repositórios Git",
                        ["Um serviço online que hospeda repositórios Git", "Outro nome para o Git local", "Um editor de código"],
                    ),
                    quiz(
                        "Qual comando envia seus commits para o repositório remoto?",
                        "git push",
                        ["git push", "git pull", "git clone"],
                    ),
                    quiz(
                        "Qual comando baixa as mudanças do remoto para o seu local?",
                        "git pull",
                        ["git pull", "git push", "git add"],
                    ),
                    quiz(
                        "Qual comando copia um repositório inteiro para sua máquina?",
                        "git clone",
                        ["git clone", "git copy", "git download"],
                    ),
                    text(
                        "Complete: o `git push` envia commits do local para o ___.",
                        "remoto",
                    ),
                ],
            ),
            topic(
                "fluxo-de-trabalho",
                "Fluxo de trabalho: pull requests e issues",
                """
# Fluxo de trabalho: pull requests e issues

No GitHub, o trabalho em equipe segue um fluxo bem definido.

## Issues: tarefas e bugs

Uma **issue** é um item registrado no projeto — um bug para corrigir, uma
feature para criar, uma pergunta. Cada issue tem número e discussão.

## Pull Request (PR)

Um **pull request** é a **proposta de mudança** para revisão antes de juntar
na `main`:

1. Crie uma branch (`git checkout -b corrige-bug`).
2. Faça os commits (`git add` + `git commit`).
3. Envie a branch (`git push origin corrige-bug`).
4. Abra um **PR** no GitHub de `corrige-bug` para `main`.
5. O time revisa, comenta e aprova (**code review**).
6. Ao aprovar, o PR é **mergeado** na `main`.

## Por que revisar código?

- **Qualidade**: outro par de olhos pega bugs e ideias melhores.
- **Conhecimento**: o time inteiro entende as mudanças.
- **Segurança**: nada entra na `main` sem revisão.

> 💡 Esse fluxo (branch → commits → push → PR → review → merge) é o padrão em
> praticamente todas as empresas que usam Git.
""",
                [
                    quiz(
                        "O que é uma issue no GitHub?",
                        "Um item registrado: bug, feature ou pergunta",
                        ["Um item registrado: bug, feature ou pergunta", "Um commit grande", "Uma branch antiga"],
                    ),
                    quiz(
                        "O que é um Pull Request?",
                        "Uma proposta de mudança para ser revisada e juntada",
                        ["Uma proposta de mudança para ser revisada e juntada", "Uma cópia do repositório", "Um comando do Git"],
                    ),
                    quiz(
                        "Qual é a ordem típica do fluxo com PR?",
                        "branch -> commits -> push -> PR -> review -> merge",
                        ["branch -> commits -> push -> PR -> review -> merge", "push -> PR -> branch -> commit", "merge -> push -> branch -> commit"],
                    ),
                    quiz(
                        "Por que fazer code review antes de mergear?",
                        "Qualidade: outro par de olhos pega bugs e melhora o código",
                        ["Qualidade: outro par de olhos pega bugs e melhora o código", "Porque o Git não deixa mergear sem isso", "Para deixar o repositório maior"],
                    ),
                    text(
                        "Complete: o processo de revisar e aprovar um PR é chamado de code ___.",
                        "review",
                    ),
                ],
            ),
        ],
    )


# ============================================================
# MODULO 15 - Qualidade de Código (novo, Fase 8 do roteiro)
# Misto: PEP 8/nomes/docstrings dá para avaliar com quiz/code;
# linters e formatters são conceituais (não rodam no Pyodide).
# ============================================================

def build_modulo_qualidade():
    return module(
        "qualidade-de-codigo",
        "Módulo 15 — Qualidade de Código",
        "Escrever código que outros (e você) entendem: PEP 8, bons nomes, docstrings, linters, formatters e refatoração.",
        [
            topic(
                "pep8-e-estilo",
                "PEP 8 e o estilo do código",
                """
# PEP 8 e o estilo do código

O **PEP 8** é o guia de estilo oficial do Python: um conjunto de convenções
para deixar o código **uniforme** e fácil de ler. Não é obrigatório, mas é
seguido pela comunidade — e pelo próprio Python, que usa essas regras.

## As regras mais conhecidas

- **Indentação de 4 espaços** (não tabs).
- **Limite de 79 caracteres** por linha (recomendado).
- **Espaços ao redor de operadores**: `x = 1` em vez de `x=1`.
- **Uma linha em branco** entre funções; **duas** entre classes/top-level.
- **Nomes**: `snake_case` para variáveis e funções, `CamelCase` para classes.

```python
# Estilo recomendado
preco_total = preco * quantidade

# Evite
preco_total=preco*quantidade
```

## Por que seguir um estilo?

- **Consistência**: todo código Python parece "da mesma família".
- **Legibilidade**: reduz atrito para quem lê.
- **Automação**: ferramentas (linters/formatters) conseguem verificar e até
  corrigir o estilo sozinhas.

> 💡 Você não precisa decorar o PEP 8 — mas escrever com 4 espaços, espaços
> nos operadores e bons nomes já cobre 90% do que importa no dia a dia.
""",
                [
                    quiz(
                        "O que é o PEP 8?",
                        "O guia de estilo oficial do Python",
                        ["O guia de estilo oficial do Python", "Uma biblioteca de testes", "Um erro comum"],
                    ),
                    quiz(
                        "Qual indentação o PEP 8 recomenda?",
                        "4 espaços",
                        ["4 espaços", "2 espaços", "1 tab"],
                    ),
                    quiz(
                        "Qual limite de caracteres por linha o PEP 8 recomenda?",
                        "79 caracteres",
                        ["79 caracteres", "200 caracteres", "não há limite"],
                    ),
                    quiz(
                        "Qual a forma de escrever uma atribuição seguindo o PEP 8?",
                        "preco_total = 10",
                        ["preco_total = 10", "preco_total=10", "precoTotal = 10"],
                    ),
                    quiz(
                        "Quais nomes usam `snake_case`?",
                        "Variáveis e funções",
                        ["Variáveis e funções", "Classes", "Arquivos de configuração"],
                    ),
                    text(
                        "Complete: nomes de classes usam ___ (CamelCase).",
                        "CamelCase",
                    ),
                ],
            ),
            topic(
                "nomes-e-legibilidade",
                "Nomes e legibilidade",
                """
# Nomes e legibilidade

Um dos maiores fatores de qualidade do código é a **escolha de nomes**. Código
bom se explica sozinho — sem precisar de comentários para cada linha.

## Regras rápidas

- O nome **descreve o conteúdo**: `total_alunos`, `preco_final`, `nome_completo`.
- **Variáveis e funções**: `snake_case` (`calcular_media`).
- **Classes**: `CamelCase`/`UpperCamelCase` (`Pessoa`, `ContaBancaria`).
- **Constantes**: letras maiúsculas (`TAXA_JUROS`).
- Evite nomes curtos demais (`x`, `d`) e números no nome (`coisa1`).

## Comparando

```python
# Difícil de entender
v = t * 2

# Claro
tempo_dobrado = tempo * 2
```

## O teste do "estranho"

Se você voltar ao código daqui a 3 meses, os nomes ainda vão dizer o que cada
coisa faz? Se não, troque os nomes.

> 💡 Bom nome vale mais que comentário: `total_alunos` se explica; `x` exige
> investigar.
""",
                [
                    code(
                        "Crie variáveis seguindo o padrão snake_case: `quantidade_alunos = 30` e `media_nota = 7.5`.",
                        "quantidade_alunos = 30\nmedia_nota = 7.5",
                        "assert quantidade_alunos == 30, 'quantidade_alunos deveria ser 30'\nassert media_nota == 7.5, 'media_nota deveria ser 7.5'",
                    ),
                    quiz(
                        "Qual é o melhor nome para uma variável que guarda a quantidade de alunos?",
                        "quantidade_alunos",
                        ["quantidade_alunos", "q", "n1"],
                    ),
                    quiz(
                        "Qual convenção é usada para nomes de classes?",
                        "UpperCamelCase (Pessoa, ContaBancaria)",
                        ["UpperCamelCase (Pessoa, ContaBancaria)", "snake_case", "kebab-case"],
                    ),
                    quiz(
                        "Por que evitar nomes como `x` ou `coisa1`?",
                        "Eles não descrevem o que a variável guarda",
                        ["Eles não descrevem o que a variável guarda", "Porque Python não aceita", "Porque deixam o código mais rápido"],
                    ),
                    quiz(
                        "Como se escrevem nomes de constantes por convenção?",
                        "EM_MAIÚSCULAS",
                        ["EM_MAIÚSCULAS", "snake_case", "com underline no fim"],
                    ),
                    text(
                        "Complete: bons nomes valem mais que ___.",
                        "comentários",
                    ),
                ],
            ),
            topic(
                "docstrings-e-comentarios",
                "Docstrings e comentários",
                """
# Docstrings e comentários

**Comentários** (`#`) explicam **trechos** de código — o "porquê" de uma linha
complicada. **Docstrings** documentam **unidades inteiras** (função, classe,
módulo) e são a primeira coisa dentro delas:

```python
def calcular_media(notas):
    \"\"\"Retorna a média das notas da lista.\"\"\"
    return sum(notas) / len(notas)
```

## Como a docstring aparece

A docstring fica acessível como atributo `__doc__` e aparece nas ajudas e nos
editores:

```python
help(calcular_media)   # mostra a docstring
```

## Comentário vs. docstring

| | Comentário `#` | Docstring `\"\"\"...\"\"\"` |
|---|---|---|
| Onde | em qualquer linha | início da função/classe/módulo |
| Documenta | um trecho/porquê | a unidade inteira |
| Vira `__doc__` | não | sim |

## Regra de ouro

- Comente o **porquê** (decisões, armadilhas), não o "o quê" (o código já
  mostra o quê).
- Escreva docstrings nas funções que outras pessoas vão usar.

> 💡 Código bom não precisa de comentário óbvio como `# soma os números`. Use
> comentário para explicar **decisões** — o "porquê".
""",
                [
                    code(
                        "Defina a função `calcular_media(notas)` com uma docstring (aspas triplas) que diz `Retorna a média das notas da lista.` e retorna `sum(notas) / len(notas)`.",
                        "def calcular_media(notas):\n    \"\"\"Retorna a média das notas da lista.\"\"\"\n    return sum(notas) / len(notas)",
                        "assert calcular_media([7, 8, 9]) == 8.0, 'média deveria ser 8.0'\nassert 'Retorna a média' in (calcular_media.__doc__ or ''), 'a função deveria ter docstring'",
                    ),
                    quiz(
                        "O que é uma docstring?",
                        "Uma string de documentação no início de uma função, classe ou módulo",
                        ["Uma string de documentação no início de uma função, classe ou módulo", "Um comentário com #", "Um tipo de variável"],
                    ),
                    quiz(
                        "Como se escreve uma docstring?",
                        "Entre aspas triplas, na primeira linha da unidade",
                        ["Entre aspas triplas, na primeira linha da unidade", "Com # no começo da linha", "Entre aspas simples no fim do arquivo"],
                    ),
                    quiz(
                        "Qual a diferença principal entre comentário e docstring?",
                        "A docstring documenta a unidade inteira e vira __doc__",
                        ["A docstring documenta a unidade inteira e vira __doc__", "Comentários são mais longos", "Não há diferença"],
                    ),
                    quiz(
                        "O que vale mais a pena comentar?",
                        "O porquê de uma decisão ou armadilha",
                        ["O porquê de uma decisão ou armadilha", "O óbvio, como soma os números", "Todas as linhas"],
                    ),
                    text(
                        "Complete: docstrings aparecem nas ajudas e ficam no atributo ___.",
                        "__doc__",
                    ),
                ],
            ),
            topic(
                "linters-e-formatters",
                "Linters e formatters",
                """
# Linters e formatters

Duas ferramentas automáticas elevam a qualidade do código sem esforço manual.

## Linter

Um **linter** analisa o código e **aponta problemas**: estilo fora do PEP 8,
variáveis não usadas, import não usado, possíveis bugs. Exemplos: **ruff**,
**pylint**, **flake8**.

```bash
ruff check .
```

Seu papel: **avisar** o que está errado. Não corrige (em geral).

## Formatter

Um **formatter** **reescreve** o código para seguir o estilo automaticamente —
indentação, espaços, quebras de linha. Exemplos: **black**, **ruff format**.

```bash
black .
```

Seu papel: **formatar** sem você pensar em estilo.

## Por que usar

- **Consistência**: todo mundo no time com o mesmo estilo.
- **Menos discussão**: ninguém briga por espaços.
- **Bugs a menos**: linters pegam erros que passariam despercebidos.

> 💻 Instale no seu ambiente (`pip install ruff` — Módulo 13) e rode
> `ruff check .` numa pasta de testes. Ele vai apontar os problemas de estilo
> do seu código.
""",
                [
                    quiz(
                        "O que um linter faz?",
                        "Analisa o código e aponta problemas de estilo e possíveis bugs",
                        ["Analisa o código e aponta problemas de estilo e possíveis bugs", "Formata o código automaticamente", "Executa os testes"],
                    ),
                    quiz(
                        "O que um formatter faz?",
                        "Reescreve o código seguindo o estilo automaticamente",
                        ["Reescreve o código seguindo o estilo automaticamente", "Aponta problemas sem corrigir", "Instala bibliotecas"],
                    ),
                    quiz(
                        "Qual destes é um linter de Python?",
                        "ruff",
                        ["ruff", "black", "pytest"],
                    ),
                    quiz(
                        "Qual destes é um formatter de Python?",
                        "black",
                        ["black", "pylint", "flake8"],
                    ),
                    quiz(
                        "Qual benefício de usar linters e formatters no time?",
                        "Consistência de estilo e menos discussão sobre formatação",
                        ["Consistência de estilo e menos discussão sobre formatação", "Deixar o código mais lento", "Substituir os testes"],
                    ),
                    text(
                        "Complete: o linter ___ os problemas; o formatter os ___.",
                        "aponta",
                    ),
                ],
            ),
            topic(
                "refatoracao-e-dry",
                "Refatoração e o princípio DRY",
                """
# Refatoração e o princípio DRY

**Refatorar** é **melhorar o código sem mudar o comportamento**: renomear
variáveis, extrair funções, remover duplicação. O programa faz as mesmas
coisas, mas o código fica mais claro.

## O princípio DRY

**DRY** = *Don't Repeat Yourself* (não se repita). Código duplicado é
problema porque, ao mudar uma lógica, você precisa lembrar de mudar **em todos
os lugares** — e esquecer algum gera bugs.

```python
# Duplicado: a mesma conta em dois lugares
preco_1 = 10 * 1.1
preco_2 = 20 * 1.1

# DRY: uma função para a regra
def com_acrescimo(valor):
    return valor * 1.1

preco_1 = com_acrescimo(10)
preco_2 = com_acrescimo(20)
```

## Sinais de que vale refatorar

- O mesmo trecho aparece repetido.
- Função grande demais (faz coisas demais).
- Nomes ruins.
- Precisa de comentário para entender cada passo.

## Cuidado importante

Refatorar **sem testes** é arriscado — é por isso que o próximo módulo (16)
vem logo: testes dão a rede de segurança para refatorar sem medo.

> 💡 Ciclo: teste → refatore → rode o teste de novo. Se tudo continua
> passando, o comportamento não mudou.
""",
                [
                    quiz(
                        "O que é refatorar?",
                        "Melhorar o código sem mudar o comportamento",
                        ["Melhorar o código sem mudar o comportamento", "Adicionar novas funcionalidades", "Apagar o código"],
                    ),
                    quiz(
                        "O que significa o princípio DRY?",
                        "Não se repita (Don't Repeat Yourself)",
                        ["Não se repita (Don't Repeat Yourself)", "Duplique sempre que puder", "Escreva tudo numa linha"],
                    ),
                    quiz(
                        "Por que código duplicado é perigoso?",
                        "Mudar uma lógica exige lembrar de mudar em todos os lugares",
                        ["Mudar uma lógica exige lembrar de mudar em todos os lugares", "Deixa o código mais rápido", "O Python não aceita"],
                    ),
                    quiz(
                        "Refatorar muda o resultado que o programa produz?",
                        "Não, o comportamento continua o mesmo",
                        ["Não, o comportamento continua o mesmo", "Sim, sempre muda", "Depende do linter"],
                    ),
                    code(
                        "Refatore: dadas as variáveis, defina uma função `com_acrescimo(valor)` que retorna `valor * 1.1`, e use-a para calcular `preco_1 = com_acrescimo(10)` e `preco_2 = com_acrescimo(20)`.",
                        "def com_acrescimo(valor):\n    return valor * 1.1\n\npreco_1 = com_acrescimo(10)\npreco_2 = com_acrescimo(20)",
                        "assert preco_1 == 11.0, 'preco_1 deveria ser 11.0'\nassert preco_2 == 22.0, 'preco_2 deveria ser 22.0'",
                    ),
                    text(
                        "Complete: refatorar sem ___ é arriscado — por isso o módulo de testes vem logo.",
                        "testes",
                    ),
                ],
            ),
        ],
    )


# ============================================================
# MODULO 16 - Testes Automatizados (novo, Fase 8 do roteiro)
# Misto: assert e funções test_* rodam no Pyodide (código);
# fixtures/mocks/TDD e o framework pytest são conceituais.
# ============================================================

def build_modulo_testes():
    return module(
        "testes-automatizados",
        "Módulo 16 — Testes Automatizados",
        "Código que verifica código: por que testar, assert, pytest, fixtures, mocks e o ciclo TDD.",
        [
            topic(
                "por-que-testar",
                "Por que testar?",
                """
# Por que testar?

**Testes automatizados** são programas que **verificam outros programas**: você
escreve o resultado esperado e o teste confere se o código entregou.

## O que eles resolvem

- **Mudanças seguras**: refatorar e adicionar features sem medo de quebrar o
  que já funciona.
- **Regressão**: quando uma mudança quebra algo que funcionava antes, o teste
  pega na hora.
- **Documentação viva**: o teste mostra como a função deve ser usada.

## Testar manualmente não basta?

Testar na mão funciona no começo, mas:

- é lento e repetitivo;
- esquecemos casos;
- cada mudança exige testar tudo de novo.

## O ciclo ideal

```
código  +  testes  ->  mudou algo?  ->  rode os testes  ->  confiante
```

> 💡 Nos próximos tópicos você vai escrever testes de verdade. Este módulo é a
> base: entender *por que* o teste é a rede de segurança do código.
""",
                [
                    quiz(
                        "O que são testes automatizados?",
                        "Programas que verificam se o código entrega o resultado esperado",
                        ["Programas que verificam se o código entrega o resultado esperado", "Manuais de instruções", "Comentários do código"],
                    ),
                    quiz(
                        "Qual é um dos principais benefícios dos testes?",
                        "Poder mudar o código sem medo de quebrar o que funciona",
                        ["Poder mudar o código sem medo de quebrar o que funciona", "Deixar o código mais curto", "Impedir o uso de bibliotecas"],
                    ),
                    quiz(
                        "O que é uma regressão?",
                        "Uma funcionalidade que quebrou depois de uma mudança",
                        ["Uma funcionalidade que quebrou depois de uma mudança", "Um teste que passa", "Um erro de sintaxe"],
                    ),
                    quiz(
                        "Por que testar só manualmente não basta em projetos que crescem?",
                        "É lento, repetitivo e esquecemos casos",
                        ["É lento, repetitivo e esquecemos casos", "Porque manual é proibido", "Porque só linters funcionam"],
                    ),
                    text(
                        "Complete: testes funcionam como uma ___ de segurança para mudanças.",
                        "rede",
                    ),
                ],
            ),
            topic(
                "assert",
                "Testando com assert",
                """
# Testando com assert

A forma mais simples de testar é o **`assert`**: uma afirmação. Se a condição
for **falsa**, ele levanta `AssertionError` — e o teste falha.

```python
def dobro(n):
    return n * 2

assert dobro(4) == 8     # passa
assert dobro(3) == 8     # AssertionError! (3 * 2 = 6)
```

## Com mensagem

```python
assert dobro(4) == 8, "dobro de 4 deveria ser 8"
```

A mensagem aparece quando a assertiva falha — ajuda a entender o que era
esperado.

## Vários casos no mesmo teste

```python
assert dobro(0) == 0
assert dobro(1) == 2
assert dobro(-3) == -6
```

Se qualquer um falhar, o programa para com `AssertionError`.

> 💡 `assert` serve para validar **suposições** (como em testes). Em produção,
> prefira levantar exceções explícitas — mas para testar, `assert` é a base.
""",
                [
                    code(
                        "Defina `dobro(n)` retornando `n * 2` e escreva asserts que validam `dobro(4) == 8` e `dobro(0) == 0`.",
                        "def dobro(n):\n    return n * 2\n\nassert dobro(4) == 8\nassert dobro(0) == 0",
                        "assert dobro(5) == 10, 'dobro(5) deveria ser 10'",
                    ),
                    code(
                        "Defina `eh_par(n)` retornando `n % 2 == 0` e escreva asserts validando `eh_par(4)` é `True` e `eh_par(3)` é `False`.",
                        "def eh_par(n):\n    return n % 2 == 0\n\nassert eh_par(4) == True\nassert eh_par(3) == False",
                        "assert eh_par(10) == True, 'eh_par(10) deveria ser True'",
                    ),
                    code(
                        "Defina `somar(a, b)` retornando `a + b` e escreva um assert com mensagem verificando que `somar(2, 3)` é `5`.",
                        "def somar(a, b):\n    return a + b\n\nassert somar(2, 3) == 5, 'somar(2, 3) deveria ser 5'",
                        "assert somar(10, 20) == 30, 'somar(10, 20) deveria ser 30'",
                    ),
                    quiz(
                        "O que acontece quando uma condição de `assert` é falsa?",
                        "Levanta AssertionError e o programa para",
                        ["Levanta AssertionError e o programa para", "Continua normalmente", "Imprime um aviso"],
                    ),
                    quiz(
                        "Para que serve a mensagem em `assert condicao, \"mensagem\"`?",
                        "Ajuda a entender o que era esperado quando o teste falha",
                        ["Ajuda a entender o que era esperado quando o teste falha", "Deixa o teste mais rápido", "É obrigatória"],
                    ),
                    text(
                        "Complete: se qualquer assert de uma sequência falhar, o programa ___.",
                        "para",
                    ),
                ],
            ),
            topic(
                "pytest-basico",
                "Pytest básico",
                """
# Pytest básico

O **pytest** é o framework de testes mais popular do Python. Ele descobre e
roda seus testes sozinho.

## Escrevendo um teste

O padrão é criar funções com nome começando em **`test_`**:

```python
def dobro(n):
    return n * 2

def test_dobro():
    assert dobro(4) == 8
    assert dobro(0) == 0
```

O pytest procura funções `test_*` e roda cada uma. Se nenhum `assert` falhar,
o teste **passa**.

## Rodando

```bash
pytest
```

ou num arquivo específico:

```bash
pytest test_calculos.py
```

Saída típica: pontos verdes `.` para cada teste que passou e `F` para os que
falharam.

## Convenções do pytest

- Arquivos de teste costumam chamar `test_*.py`.
- Funções de teste começam com `test_`.
- Um teste passa se nenhuma asserção dentro dele falhar.

> 💻 Aqui você escreve a função `test_*` como exercício de código. Para rodar
> de verdade o pytest, instale (`pip install pytest` — Módulo 13) e rode
> `pytest` no terminal.
""",
                [
                    code(
                        "Defina `dobro(n)` e uma função `test_dobro()` com `assert` validando `dobro(4) == 8` e `dobro(0) == 0`.",
                        "def dobro(n):\n    return n * 2\n\ndef test_dobro():\n    assert dobro(4) == 8\n    assert dobro(0) == 0",
                        "test_dobro()\nassert callable(test_dobro), 'test_dobro deveria ser uma função'",
                    ),
                    code(
                        "Defina `inverter(texto)` retornando `texto[::-1]` e uma função `test_inverter()` validando `inverter(\"abc\") == \"cba\"`.",
                        "def inverter(texto):\n    return texto[::-1]\n\ndef test_inverter():\n    assert inverter(\"abc\") == \"cba\"",
                        "test_inverter()",
                    ),
                    quiz(
                        "Como o pytest encontra os testes?",
                        "Funções que começam com test_",
                        ["Funções que começam com test_", "Qualquer função", "Funções com nome teste"],
                    ),
                    quiz(
                        "Qual comando roda os testes com pytest?",
                        "pytest",
                        ["pytest", "test", "run test"],
                    ),
                    quiz(
                        "Um teste passa quando:",
                        "nenhum assert dentro dele falha",
                        ["nenhum assert dentro dele falha", "pelo menos um assert passa", "ele não tem asserts"],
                    ),
                    text(
                        "Complete: arquivos de teste costumam se chamar ___.",
                        "test_",
                    ),
                ],
            ),
            topic(
                "fixtures-e-mocks",
                "Fixtures e mocks",
                """
# Fixtures e mocks

Em projetos de verdade, testes precisam de **preparação** e **isolamento**.

## Fixture: a preparação

Uma **fixture** é um código de preparação (setup) compartilhado entre testes —
criar um objeto, conectar num banco de teste, carregar dados:

```python
import pytest

@pytest.fixture
def cliente():
    # cria e devolve um objeto pronto para os testes usarem
    return Cliente(nome="Ana")
```

Os testes recebem a fixture como parâmetro:

```python
def test_cliente_ativa(cliente):
    assert cliente.ativo == True
```

## Mock: o objeto falso

Um **mock** é um **objeto falso** que imita um objeto real, para o teste não
depender de coisas externas (API, rede, relógio, arquivo):

```python
def test_envia_email(cliente, monkeypatch):
    # substitui o envio real por um fake
    monkeypatch.setattr(cliente, "enviar_email", lambda: "enviado")
    assert cliente.enviar_email() == "enviado"
```

## Por que mockar?

- **Velocidade**: não espera rede nem disco.
- **Determinismo**: o teste não depende de o serviço estar no ar.
- **Isolamento**: se o teste falha, o problema é do seu código, não do externo.

> 💡 Fixtures = preparação; mocks = falsificação de dependências. Ambos são
> ferramentas do pytest para testes limpos e confiáveis.
""",
                [
                    quiz(
                        "O que é uma fixture no pytest?",
                        "Uma preparação (setup) compartilhada entre testes",
                        ["Uma preparação (setup) compartilhada entre testes", "Uma função que testa outra", "Um tipo de assert"],
                    ),
                    quiz(
                        "Como uma fixture é disponibilizada para o teste?",
                        "Como parâmetro da função de teste",
                        ["Como parâmetro da função de teste", "Só com import", "Não dá para usar"],
                    ),
                    quiz(
                        "O que é um mock?",
                        "Um objeto falso que imita um objeto real",
                        ["Um objeto falso que imita um objeto real", "Um teste que falha", "Um erro de sintaxe"],
                    ),
                    quiz(
                        "Por que mockar dependências externas nos testes?",
                        "Para o teste ser rápido, determinístico e isolado",
                        ["Para o teste ser rápido, determinístico e isolado", "Para o teste depender da internet", "Para substituir o assert"],
                    ),
                    text(
                        "Complete: fixtures são a ___; mocks são a falsificação de dependências.",
                        "preparação",
                    ),
                ],
            ),
            topic(
                "tdd",
                "TDD: Test-Driven Development",
                """
# TDD: Test-Driven Development

O **TDD** (*Test-Driven Development*) inverte a ordem: você escreve o **teste
primeiro**, vê ele falhar, e só então escreve o código para fazê-lo passar.

## O ciclo Red-Green-Refactor

1. **Red**: escreva um teste para a próxima funcionalidade e rode — ele
   **falha** (ainda não existe código).
2. **Green**: escreva o código mínimo para o teste **passar**.
3. **Refactor**: melhore o código (Módulo 15) mantendo o teste verde.

Repita o ciclo para cada pequena funcionalidade.

## Exemplo

```python
# 1. RED — o teste vem primeiro
def test_area_quadrado():
    assert area_quadrado(3) == 9
```

Roda, falha (`NameError: area_quadrado não existe`).

```python
# 2. GREEN — o código mínimo
def area_quadrado(lado):
    return lado * lado
```

Roda, passa. Pronto para o próximo ciclo.

## Por que TDD?

- Você pensa no **contrato** (comportamento) antes da implementação.
- Cada teste registra um caso que **não volta a quebrar**.
- A confiança para refatorar cresce a cada ciclo.

> 💡 TDD não é a única forma de trabalhar, mas é uma prática valiosa —
> especialmente para lógica de negócio e funções puras.
""",
                [
                    quiz(
                        "O que significa a sigla TDD?",
                        "Test-Driven Development (desenvolvimento dirigido a testes)",
                        ["Test-Driven Development (desenvolvimento dirigido a testes)", "Test-Debug-Develop", "Total-Data-Development"],
                    ),
                    quiz(
                        "No TDD, o teste é escrito:",
                        "antes do código que vai fazê-lo passar",
                        ["antes do código que vai fazê-lo passar", "depois do código pronto", "só no final do projeto"],
                    ),
                    quiz(
                        "Qual é a ordem do ciclo TDD?",
                        "red, green, refactor",
                        ["red, green, refactor", "green, red, refactor", "refactor, red, green"],
                    ),
                    quiz(
                        "Na fase 'red', o teste:",
                        "falha, porque o código ainda não existe",
                        ["falha, porque o código ainda não existe", "passa de primeira", "nem é executado"],
                    ),
                    text(
                        "Complete: a fase em que o teste passa pela primeira vez é o ___.",
                        "green",
                    ),
                ],
            ),
        ],
    )


# ============================================================
# MODULO 17 - Programação Web (novo, Fase 9 do roteiro)
# Conceitual. Não roda servidor HTTP no Pyodide.
# ============================================================

def build_modulo_web():
    return module(
        "programacao-web",
        "Módulo 17 — Programação Web",
        "Como a web funciona por baixo: HTTP, HTML/CSS/JS, frontend vs backend, APIs com JSON e como colocar um site no ar.",
        [
            topic(
                "como-a-web-funciona",
                "Como a web funciona",
                """
# Como a web funciona

Toda a web roda sobre um modelo de **requisição e resposta** entre dois lados:

- **Cliente**: quem pede (seu navegador, um app).
- **Servidor**: quem responde (uma máquina com o site/app).

## O protocolo HTTP

O **HTTP** (*HyperText Transfer Protocol*) é o protocolo dessa conversa. Uma
**requisição (request)** tem método, endereço (URL) e dados; o servidor
devolve uma **resposta (response)** com status e conteúdo.

## Códigos de status

A resposta vem com um número que resume o resultado:

| Código | Significado |
|---|---|
| `200` | OK — deu certo |
| `404` | Não encontrado |
| `500` | Erro interno do servidor |

## A viagem de um clique

```
[Cliente] --requisição HTTP--> [Servidor] --banco de dados-- ...
[Cliente] <--resposta HTTP---- [Servidor] (HTML/JSON/imagem)
```

> 💻 Dá para "ver" o HTTP no seu navegador: abra o DevTools (F12), aba
> *Network*, e recarregue uma página — cada recurso carregado aparece como
> uma requisição com seu status.
""",
                [
                    quiz(
                        "O que é o HTTP?",
                        "O protocolo de comunicação entre cliente e servidor na web",
                        ["O protocolo de comunicação entre cliente e servidor na web", "Uma linguagem de programação", "Um tipo de banco de dados"],
                    ),
                    quiz(
                        "Na web, quem faz a requisição?",
                        "O cliente (navegador ou app)",
                        ["O cliente (navegador ou app)", "O servidor", "O banco de dados"],
                    ),
                    quiz(
                        "O que o servidor devolve para o cliente?",
                        "Uma resposta (response) com status e conteúdo",
                        ["Uma resposta (response) com status e conteúdo", "Outra requisição", "Nada"],
                    ),
                    quiz(
                        "O que significa o status HTTP 404?",
                        "Não encontrado",
                        ["Não encontrado", "OK, deu certo", "Erro interno do servidor"],
                    ),
                    quiz(
                        "O que significa o status HTTP 200?",
                        "OK — deu certo",
                        ["OK — deu certo", "Não encontrado", "Erro interno"],
                    ),
                    text(
                        "Complete: o código 500 significa erro interno do ___.",
                        "servidor",
                    ),
                ],
            ),
            topic(
                "html-css-javascript",
                "HTML, CSS e JavaScript",
                """
# HTML, CSS e JavaScript

Uma página web é construída com três tecnologias que trabalham juntas no
navegador:

## HTML — a estrutura

O **HTML** define o conteúdo e a estrutura (títulos, parágrafos, botões,
imagens) com *tags*:

```html
<h1>Olá, mundo!</h1>
<button>Clique aqui</button>
```

## CSS — o estilo

O **CSS** define a aparência: cores, tamanhos, espaçamento, fonte.

```css
h1 {
  color: blue;
  font-size: 24px;
}
```

## JavaScript — o comportamento

O **JavaScript** define a interatividade: o que acontece quando o usuário
clica, digita, rola a página.

```js
document.querySelector("button").onclick = () => alert("Oi!");
```

## Quem interpreta tudo isso?

O **navegador** interpreta HTML + CSS + JS. É por isso que o mesmo site
"funciona" em qualquer máquina: a renderização acontece no navegador.

> 💡 Python (o que você está aprendendo) vive mais no **backend** — a parte do
> servidor. O trio HTML/CSS/JS é a cara do frontend.
""",
                [
                    quiz(
                        "O que o HTML define numa página?",
                        "A estrutura e o conteúdo",
                        ["A estrutura e o conteúdo", "As cores e fontes", "O comportamento dos cliques"],
                    ),
                    quiz(
                        "O que o CSS define?",
                        "A aparência (cores, tamanhos, fonte)",
                        ["A aparência (cores, tamanhos, fonte)", "A estrutura", "A lógica do servidor"],
                    ),
                    quiz(
                        "O que o JavaScript define?",
                        "O comportamento e a interatividade no navegador",
                        ["O comportamento e a interatividade no navegador", "A estrutura da página", "O banco de dados"],
                    ),
                    quiz(
                        "Quem interpreta HTML, CSS e JS?",
                        "O navegador",
                        ["O navegador", "O Python", "O servidor, sempre"],
                    ),
                    text(
                        "Complete: HTML usa ___ para marcar elementos (títulos, botões).",
                        "tags",
                    ),
                ],
            ),
            topic(
                "frontend-vs-backend",
                "Frontend vs backend",
                """
# Frontend vs backend

Um sistema web tem dois mundos:

## Frontend

A parte **visível**, com a qual o usuário interage — o que roda no navegador.
Feito com HTML, CSS e JavaScript (e frameworks como React).

## Backend

A parte **invisível**, que roda no servidor: regras de negócio, autenticação,
conexão com o banco de dados. Aqui é o reino de **Python** (FastAPI, Django,
Flask), mas também Java, Node.js, Go...

## Como eles conversam

O frontend faz requisições HTTP para o backend, que responde com dados (quase
sempre **JSON**):

```
[Frontend (navegador)] --HTTP + JSON--> [Backend (Python) -> banco de dados]
```

## Onde entra o Python?

Python é fortíssimo em backend — e é exatamente isso que o próximo módulo
(FastAPI) vai mostrar.

> 💡 Não precisa escolher "só um" hoje. Mas saber qual é qual ajuda a entender
> onde cada tecnologia se encaixa.
""",
                [
                    quiz(
                        "O que é o frontend?",
                        "A parte visível, com a qual o usuário interage",
                        ["A parte visível, com a qual o usuário interage", "A lógica no servidor", "O banco de dados"],
                    ),
                    quiz(
                        "O que é o backend?",
                        "A lógica e os dados que rodam no servidor",
                        ["A lógica e os dados que rodam no servidor", "A parte visual da página", "O CSS do site"],
                    ),
                    quiz(
                        "Python é mais comumente usado em qual lado?",
                        "Backend",
                        ["Backend", "Frontend", "Só em HTML"],
                    ),
                    quiz(
                        "Quem conversa com o banco de dados normalmente?",
                        "O backend",
                        ["O backend", "O frontend", "O CSS"],
                    ),
                    text(
                        "Complete: o frontend conversa com o backend por requisições ___, geralmente trocando JSON.",
                        "http",
                    ),
                ],
            ),
            topic(
                "apis-e-json",
                "APIs e JSON",
                """
# APIs e JSON

Uma **API** (*Application Programming Interface*) é a **interface** que um
sistema expõe para outros sistemas conversarem. Uma **API web** responde a
requisições HTTP com dados.

## O formato JSON

O **JSON** é o formato padrão desses dados (você já mexeu nele no Módulo 12):

```json
{"usuario": "ana", "idade": 20}
```

## Métodos HTTP (verbos)

Em APIs REST, o método indica a intenção:

| Método | Ação | Exemplo |
|---|---|---|
| `GET` | **buscar** dados | `GET /usuarios` |
| `POST` | **criar** dados | `POST /usuarios` |
| `PUT` | **atualizar** dados | `PUT /usuarios/1` |
| `DELETE` | **remover** dados | `DELETE /usuarios/1` |

## A conversa completa

```
GET /usuarios   ->  [200 OK]  ->  [{"usuario": "ana"}, ...]
POST /usuarios  <-  {"usuario": "bia"}  ->  [201 Criado]
```

> 💡 Lembra da biblioteca `requests` do Módulo 13? Ela existe exatamente para
> seu código Python conversar com APIs desse jeito.
""",
                [
                    quiz(
                        "O que é uma API?",
                        "A interface que sistemas usam para conversar entre si",
                        ["A interface que sistemas usam para conversar entre si", "Um banco de dados", "Um tipo de navegador"],
                    ),
                    quiz(
                        "Qual formato de dados é o padrão nas APIs web?",
                        "JSON",
                        ["JSON", "CSV", "PDF"],
                    ),
                    quiz(
                        "Qual método HTTP é usado para BUSCAR dados?",
                        "GET",
                        ["GET", "POST", "DELETE"],
                    ),
                    quiz(
                        "Qual método HTTP é usado para CRIAR dados?",
                        "POST",
                        ["POST", "GET", "PUT"],
                    ),
                    text(
                        "Complete: o método ___ é usado para remover dados.",
                        "delete",
                    ),
                ],
            ),
            topic(
                "servidores-e-deploy",
                "Servidores e deploy",
                """
# Servidores e deploy

## O que é um servidor?

No contexto web, **servidor** é a máquina (ou serviço) que fica no ar,
recebendo requisições e respondendo. Pode ser um computador dedicado, uma
máquina virtual ou um serviço gerenciado na nuvem.

## O que é deploy?

**Deploy** é **colocar o seu aplicativo no ar** — enviar o código para o
servidor para que outras pessoas acessem.

## O que é um domínio?

O **domínio** é o endereço amigável que aponta para o servidor:
`meusite.com.br`. Quando você digita, o navegador descobre o servidor por trás
dele (via DNS) e faz a requisição.

## Serviços populares para deploy

- **Vercel**, **Netlify**: ótimos para frontend.
- **Render**, **Railway**: simples para backend Python.
- **Fly.io**, **AWS**, **Google Cloud**: opções profissionais.

## O fluxo do deploy

```
código local -> git push -> a plataforma builda e sobe o app -> URL no ar
```

> 💡 Deploy une vários módulos deste curso: Git (Módulo 14), dependências
> (Módulo 13) e, em breve, uma API FastAPI (próximo módulo).
""",
                [
                    quiz(
                        "O que é um servidor web?",
                        "A máquina que fica no ar recebendo requisições e respondendo",
                        ["A máquina que fica no ar recebendo requisições e respondendo", "O navegador do usuário", "Um arquivo HTML"],
                    ),
                    quiz(
                        "O que é deploy?",
                        "Colocar o aplicativo no ar para outras pessoas acessarem",
                        ["Colocar o aplicativo no ar para outras pessoas acessarem", "Apagar o projeto", "Testar localmente"],
                    ),
                    quiz(
                        "O que é um domínio?",
                        "O endereço amigável que aponta para o servidor",
                        ["O endereço amigável que aponta para o servidor", "O código-fonte", "Um tipo de banco de dados"],
                    ),
                    quiz(
                        "Qual desses é um serviço usado para colocar apps no ar?",
                        "Render",
                        ["Render", "PyPI", "pip"],
                    ),
                    text(
                        "Complete: o fluxo de deploy envolve o código local, o ___ e a plataforma.",
                        "git",
                    ),
                ],
            ),
        ],
    )


# ============================================================
# MODULO 18 - FastAPI (novo, Fase 9 do roteiro)
# Conceitual, com trechos de código de exemplo (não roda servidor
# no Pyodide). Lição sugere rodar no terminal próprio.
# ============================================================

def build_modulo_fastapi():
    return module(
        "fastapi",
        "Módulo 18 — FastAPI",
        "Criar APIs modernas com Python: o framework, rotas, parâmetros, validação com pydantic e a documentação automática.",
        [
            topic(
                "o-que-e-fastapi",
                "O que é o FastAPI?",
                """
# O que é o FastAPI?

O **FastAPI** é um framework web moderno para criar **APIs** com Python. Ele
se destaca por ser:

- **Rápido de desenvolver**: pouco código para muita funcionalidade.
- **Rápido de executar**: performance comparável a frameworks de outras
  linguagens.
- **Autodocumentável**: gera a documentação da API sozinho.
- **Tipado**: aproveita type hints (Módulo 11) para validar dados.

```python
from fastapi import FastAPI

app = FastAPI()

@app.get("/")
def raiz():
    return {"mensagem": "Olá, API!"}
```

## O que ele faz por você

Com anotações de tipo, o FastAPI **valida**, **converte** e **documenta** os
dados automaticamente — sem você escrever código de validação na mão.

> 💡 O FastAPI é a ponte entre o Python que você já conhece (funções, type
> hints) e o mundo web do módulo anterior (HTTP, APIs, JSON).
""",
                [
                    quiz(
                        "O que é o FastAPI?",
                        "Um framework web moderno para criar APIs com Python",
                        ["Um framework web moderno para criar APIs com Python", "Um banco de dados", "Um editor de código"],
                    ),
                    quiz(
                        "Qual é uma das características principais do FastAPI?",
                        "Documentação automática e validação via type hints",
                        ["Documentação automática e validação via type hints", "Exige JavaScript", "Não usa Python"],
                    ),
                    quiz(
                        "Como o FastAPI valida os dados de entrada?",
                        "Usando as anotações de tipo dos parâmetros",
                        ["Usando as anotações de tipo dos parâmetros", "Com CSS", "Não valida"],
                    ),
                    quiz(
                        "Quem cria o objeto `app` no exemplo?",
                        "FastAPI()",
                        ["FastAPI()", "app()", "server()"],
                    ),
                    text(
                        "Complete: FastAPI aproveita os ___ hints do Python para validar dados.",
                        "type",
                    ),
                ],
            ),
            topic(
                "primeira-api",
                "Sua primeira API",
                """
# Sua primeira API

O jeito mais simples de criar uma API FastAPI tem três partes: importar,
instanciar o app e declarar uma rota.

```python
from fastapi import FastAPI

app = FastAPI()

@app.get("/")
def raiz():
    return {"mensagem": "Olá, mundo!"}
```

## Entendendo cada pedaço

- `app = FastAPI()` — cria a aplicação.
- `@app.get("/")` — **decorator** (Módulo 10) que registra: requisição `GET`
  na URL `/` é respondida por esta função.
- A função retorna um dicionário → o FastAPI o converte para **JSON**
  automaticamente.

## Rodando

```bash
pip install fastapi uvicorn
uvicorn main:app --reload
```

`main` é o arquivo; `app` é a variável da aplicação. Com `--reload`, o servidor
reinicia sozinho a cada mudança.

## Testando

Abra `http://127.0.0.1:8000/` no navegador — você vê o JSON de resposta.

> 💻 Este é um código de exemplo: rode no seu computador para valer. Crie um
> `main.py` com esse conteúdo, instale com `pip install fastapi uvicorn` e
> rode `uvicorn main:app --reload`. Abra `http://127.0.0.1:8000/`.
""",
                [
                    quiz(
                        "O que o decorator `@app.get(\"/\")` faz?",
                        "Registra que um GET na rota / é respondido pela função",
                        ["Registra que um GET na rota / é respondido pela função", "Cria o banco de dados", "Formata o JSON"],
                    ),
                    quiz(
                        "O que a função da rota retorna no exemplo?",
                        "Um dicionário, que vira JSON automaticamente",
                        ["Um dicionário, que vira JSON automaticamente", "Um arquivo HTML", "Um erro"],
                    ),
                    quiz(
                        "Qual comando roda o servidor de desenvolvimento?",
                        "uvicorn main:app --reload",
                        ["uvicorn main:app --reload", "python app", "start server"],
                    ),
                    quiz(
                        "Para que serve o `--reload`?",
                        "Reiniciar o servidor automaticamente a cada mudança",
                        ["Reiniciar o servidor automaticamente a cada mudança", "Apagar o código", "Acelerar o banco"],
                    ),
                    text(
                        "Complete: o app é criado com `app = ___()`.",
                        "fastapi",
                    ),
                ],
            ),
            topic(
                "rotas-e-parametros",
                "Rotas e parâmetros",
                """
# Rotas e parâmetros

Uma API real recebe **parâmetros** de várias formas.

## Parâmetro de caminho (path)

O `{item_id}` na rota é capturado e passado à função:

```python
@app.get("/items/{item_id}")
def item(item_id: int):
    return {"item_id": item_id}
```

Ao acessar `/items/42`, `item_id` vale `42` (já convertido para `int` pela
anotação!).

## Parâmetro de consulta (query)

Valores após `?` na URL (`?busca=python`) viram parâmetros com valor padrão:

```python
@app.get("/buscar")
def buscar(busca: str = "", limite: int = 10):
    return {"busca": busca, "limite": limite}
```

Acessar `/buscar?busca=python&limite=5` retorna `{"busca": "python", "limite": 5}`.

## A anotação é a validação

Se você anota `item_id: int` e alguém acessa `/items/abc`, o FastAPI responde
com erro de validação (`422`) em vez de quebrar o servidor.

> 💻 Rode o exemplo no seu terminal (mesmo fluxo do tópico anterior) e teste
> URLs como `/items/42` e `/buscar?busca=python`.
""",
                [
                    quiz(
                        "Na rota `/items/{item_id}`, de onde vem o valor de `item_id`?",
                        "Do caminho (path) da URL",
                        ["Do caminho (path) da URL", "De um arquivo", "Do banco de dados"],
                    ),
                    quiz(
                        "O que `item_id: int` na função faz no FastAPI?",
                        "Valida e converte o valor automaticamente",
                        ["Valida e converte o valor automaticamente", "Nada, é só documentação", "Apaga o item"],
                    ),
                    quiz(
                        "O que acontece ao acessar `/items/abc` com `item_id: int`?",
                        "O FastAPI responde com erro de validação (422)",
                        ["O FastAPI responde com erro de validação (422)", "O servidor quebra", "Retorna abc mesmo assim"],
                    ),
                    quiz(
                        "Onde ficam os parâmetros de consulta (query)?",
                        "Na URL, depois do ? (ex.: ?busca=python)",
                        ["Na URL, depois do ? (ex.: ?busca=python)", "No corpo do HTML", "No nome do arquivo"],
                    ),
                    text(
                        "Complete: parâmetros na URL com `?` são chamados de parâmetros de ___.",
                        "consulta",
                    ),
                ],
            ),
            topic(
                "schemas-e-validacao",
                "Schemas e validação (pydantic)",
                """
# Schemas e validação (pydantic)

Para receber dados mais complexos (ex.: um corpo de requisição POST), o
FastAPI usa **schemas** definidos com **pydantic**:

```python
from pydantic import BaseModel

class Usuario(BaseModel):
    nome: str
    idade: int
```

## Usando o schema numa rota

```python
@app.post("/usuarios")
def criar_usuario(usuario: Usuario):
    return {"recebido": usuario.nome}
```

O `usuario: Usuario` diz ao FastAPI: "leia o corpo da requisição como JSON,
valide contra esse schema e entregue o objeto".

## O que a validação garante

- `nome` deve existir e ser texto; `idade` deve existir e ser inteiro.
- Se o JSON não bater, o FastAPI responde `422` com a descrição do erro.
- Campos sem valor padrão são **obrigatórios**.

```json
{"nome": "Ana", "idade": 20}   // válido
{"idade": 20}                  // 422: falta "nome"
```

> 💡 O pydantic é a base do FastAPI: é ele que transforma type hints em
> validação de verdade na entrada e na saída.
""",
                [
                    quiz(
                        "O que é um schema no contexto do FastAPI?",
                        "Um modelo (BaseModel) que define e valida os dados",
                        ["Um modelo (BaseModel) que define e valida os dados", "Um arquivo CSS", "Uma rota GET"],
                    ),
                    quiz(
                        "Qual biblioteca o FastAPI usa para validação de schemas?",
                        "pydantic",
                        ["pydantic", "requests", "numpy"],
                    ),
                    quiz(
                        "Em `class Usuario(BaseModel)`, o que os campos anotados sem valor padrão representam?",
                        "Campos obrigatórios",
                        ["Campos obrigatórios", "Campos opcionais", "Campos de consulta"],
                    ),
                    quiz(
                        "Se o corpo da requisição não bater com o schema, o FastAPI responde:",
                        "422 com a descrição do erro de validação",
                        ["422 com a descrição do erro de validação", "200 OK", "404 não encontrado"],
                    ),
                    text(
                        "Complete: schemas com pydantic transformam type hints em ___ de verdade.",
                        "validação",
                    ),
                ],
            ),
            topic(
                "documentacao-e-deploy",
                "Documentação automática e deploy",
                """
# Documentação automática e deploy

## A documentação grátis

O FastAPI **gera a documentação da sua API sozinho**, baseada nos schemas e
nas rotas. Com o servidor rodando:

- `http://127.0.0.1:8000/docs` — interface **Swagger UI**, onde você testa os
  endpoints pelo navegador.
- `http://127.0.0.1:8000/redoc` — outra visualização da documentação.

A base disso é o padrão **OpenAPI** (antigo Swagger): um JSON que descreve
toda a API — rotas, métodos, parâmetros e schemas.

## Do desenvolvimento à produção

Durante o desenvolvimento, o `uvicorn` com `--reload` é suficiente. Para
**produção** (usuários reais), o recomendado é:

- rodar atrás de um servidor mais robusto (`uvicorn` com mais workers, ou
  gunicorn + uvicorn);
- **deploy** numa plataforma (Render, Railway, Fly.io...) — como você viu no
  Módulo 17.

## O ciclo completo

```bash
pip install fastapi uvicorn
# escreva as rotas...
uvicorn main:app --reload     # desenvolvimento
# deploy -> URL no ar -> /docs para a documentação
```

> 💻 Rode sua API localmente e abra `/docs` — a documentação interativa
> gerada automaticamente é uma das coisas mais legais do FastAPI.
""",
                [
                    quiz(
                        "Onde fica a documentação interativa (Swagger) do FastAPI?",
                        "Em /docs",
                        ["Em /docs", "Em /redoc", "Em /json"],
                    ),
                    quiz(
                        "Qual padrão o FastAPI usa para descrever a API automaticamente?",
                        "OpenAPI",
                        ["OpenAPI", "HTML", "CSV"],
                    ),
                    quiz(
                        "Para produção, o recomendado é:",
                        "Rodar atrás de um servidor mais robusto e fazer deploy",
                        ["Rodar atrás de um servidor mais robusto e fazer deploy", "Continuar com --reload para sempre", "Não fazer deploy"],
                    ),
                    quiz(
                        "A documentação automática permite ao desenvolvedor:",
                        "Testar os endpoints direto pelo navegador",
                        ["Testar os endpoints direto pelo navegador", "Apagar o servidor", "Instalar pacotes"],
                    ),
                    text(
                        "Complete: o padrão que descreve toda a API (rotas, parâmetros, schemas) é o ___.",
                        "openapi",
                    ),
                ],
            ),
        ],
    )


# ============================================================
# MODULO 19 - Programação Assíncrona (novo, Fase 10 do roteiro)
# Misto: a sintaxe async/await roda no Pyodide (código);
# conceitos de I/O real ficam conceituais.
# ============================================================

def build_modulo_async():
    return module(
        "programacao-assincrona",
        "Módulo 19 — Programação Assíncrona",
        "Esperar sem travar: o problema do I/O, a sintaxe async/await, asyncio e quando a assincronia vale a pena.",
        [
            topic(
                "io-e-bloqueio",
                "I/O e o problema do bloqueio",
                """
# I/O e o problema do bloqueio

**I/O** (entrada/saída) é toda operação que lê ou escreve algo de fora do
programa: pedir dado à internet, ler um arquivo, esperar uma resposta de um
banco de dados, ler o teclado.

## O problema: esperar é lento

Essas operações levam **milissegundos (ou mais)** — uma eternidade para a
velocidade do processador. Num programa **sequencial** (o que você conhece até
aqui), enquanto o programa espera um I/O, ele **fica parado (bloqueado)**:

```python
import time

print("buscando...")
time.sleep(2)          # simula uma espera (rede/banco)
print("achei!")
```

Durante os 2 segundos, o programa não faz mais nada.

## O desperdício

Se o programa tivesse outras coisas para fazer (responder outros usuários,
processar outros dados), esse tempo de espera é **desperdiçado**.

## As três estratégias

| Estratégia | Ideia |
|---|---|
| **Assíncrono** (`asyncio`) | enquanto espera um I/O, vai fazer outra coisa e **volta depois** |
| **Threads** | vários fluxos de execução no mesmo processo |
| **Processos** | programas paralelos de verdade, um por núcleo |

Este módulo foca na primeira; o próximo, em threads/processos.

> 💡 Em uma frase: assíncrono é "não fique parado esperando — vá fazer outra
> coisa e volte quando a resposta chegar".
""",
                [
                    quiz(
                        "O que é I/O (entrada/saída)?",
                        "Operações que leem ou escrevem algo externo (rede, disco, teclado)",
                        ["Operações que leem ou escrevem algo externo (rede, disco, teclado)", "Só cálculos matemáticos", "Imprimir no console"],
                    ),
                    quiz(
                        "Num programa sequencial, durante uma espera de rede o programa:",
                        "fica parado (bloqueado), sem fazer mais nada",
                        ["fica parado (bloqueado), sem fazer mais nada", "continua processando outras coisas", "se reinicia"],
                    ),
                    quiz(
                        "Qual é o problema de esperar parado?",
                        "O tempo de espera é desperdiçado, mesmo havendo outras coisas para fazer",
                        ["O tempo de espera é desperdiçado, mesmo havendo outras coisas para fazer", "O computador esquenta", "Os dados ficam corrompidos"],
                    ),
                    quiz(
                        "A ideia da programação assíncrona é:",
                        "enquanto espera um I/O, fazer outra coisa e voltar quando a resposta chegar",
                        ["enquanto espera um I/O, fazer outra coisa e voltar quando a resposta chegar", "eliminar todo I/O do programa", "usar mais memória"],
                    ),
                    text(
                        "Complete: uma operação de rede, arquivo ou banco de dados é chamada de operação de ___.",
                        "io",
                    ),
                ],
            ),
            topic(
                "async-e-await",
                "A sintaxe async / await",
                """
# A sintaxe async / await

A base da programação assíncrona em Python é a sintaxe `async`/`await`.

## Definindo uma coroutine

Uma função declarada com `async def` é uma **coroutine**: ela pode ser
**pausada** num `await` e **retomada** depois:

```python
async def saudacao():
    return "oi"
```

## Esperando com await

```python
import asyncio

async def esperar():
    await asyncio.sleep(0.01)   # pausa aqui, sem travar o programa
    return "pronto"
```

O `await` diz: "chame isso e espere o resultado". Enquanto espera, o event
loop pode rodar **outras** coroutines.

## Rodando: asyncio.run

Uma coroutine **só executa quando é aguardada**. Para começar do zero:

```python
resultado = asyncio.run(saudacao())   # roda e devolve "oi"
```

`asyncio.run` cria o event loop, roda a coroutine e fecha tudo.

> 💡 Se você chamar `saudacao()` sem `await`/`asyncio.run`, ela **não
> executa** — você ganha só o objeto coroutine.
""",
                [
                    code(
                        "Importe `asyncio` e defina `async def saudacao()` que retorna `\"oi\"`.",
                        "import asyncio\nasync def saudacao():\n    return \"oi\"",
                        "import inspect\nassert inspect.iscoroutinefunction(saudacao), 'saudacao deveria ser uma coroutine (async def)'\ncoro = saudacao()\nassert asyncio.iscoroutine(coro), 'chamar saudacao() deveria devolver um objeto coroutine'\ncoro.close()",
                    ),
                    code(
                        "Importe `asyncio` e defina `async def somar(a, b)` que retorna `a + b`.",
                        "import asyncio\nasync def somar(a, b):\n    return a + b",
                        "import inspect\nassert inspect.iscoroutinefunction(somar), 'somar deveria ser uma coroutine (async def)'",
                    ),
                    code(
                        "Importe `asyncio` e defina `async def esperar()` que faz `await asyncio.sleep(0.01)` e retorna `\"pronto\"`.",
                        "import asyncio\nasync def esperar():\n    await asyncio.sleep(0.01)\n    return \"pronto\"",
                        "import inspect\nassert inspect.iscoroutinefunction(esperar), 'esperar deveria ser uma coroutine (async def)'\nassert 'await asyncio.sleep' in _student_code, 'use await asyncio.sleep(0.01) dentro da coroutine'",
                    ),
                    quiz(
                        "O que o `await` faz numa coroutine?",
                        "Chama a coroutine e espera o resultado, pausando sem travar o programa",
                        ["Chama a coroutine e espera o resultado, pausando sem travar o programa", "Encerra o programa", "Cria um processo"],
                    ),
                    quiz(
                        "O que é uma coroutine?",
                        "Uma função async def que pode ser pausada e retomada",
                        ["Uma função async def que pode ser pausada e retomada", "Uma thread", "Um tipo de lista"],
                    ),
                    quiz(
                        "Chamar `saudacao()` (uma async def) sem await ou asyncio.run:",
                        "não executa a função; só cria o objeto coroutine",
                        ["não executa a função; só cria o objeto coroutine", "executa normalmente", "levanta um erro sempre"],
                    ),
                ],
            ),
            topic(
                "asyncio-e-tarefas",
                "asyncio e tarefas simultâneas",
                """
# asyncio e tarefas simultâneas

## asyncio.run

`asyncio.run(coroutine)` cria o **event loop**, roda a coroutine principal e
fecha tudo. É o ponto de entrada padrão:

```python
asyncio.run(main())
```

## asyncio.gather: várias de uma vez

`asyncio.gather(...)` recebe várias coroutines, roda **intercalando** as
esperas e devolve a lista de resultados na ordem:

```python
import asyncio

async def dobro(n):
    await asyncio.sleep(0.01)   # simula um I/O
    return n * 2

async def main():
    return await asyncio.gather(dobro(2), dobro(3), dobro(4))

resultados = asyncio.run(main())
# [4, 6, 8]
```

Enquanto uma coroutine espera o `sleep`, as outras avançam — é isso que faz
o tempo total ficar perto do mais lento, e não da soma.

## Importante: intercalado, não paralelo

O `asyncio` roda tudo num **único** thread. O ganho vem de **não ficar
parado** durante esperas (I/O), não de rodar em vários núcleos. Isso é o
próximo módulo.

> 💡 No navegador (Pyodide) a sintaxe roda, mas não há I/O de rede real para
> testar o ganho — o `sleep` pequeno serve só para demonstrar o mecanismo.
""",
                [
                    code(
                        "Importe `asyncio`, defina `async def dobro(n)` que retorna `n * 2` e `async def main()` que retorna `await asyncio.gather(dobro(2), dobro(3))`.",
                        "import asyncio\nasync def dobro(n):\n    return n * 2\nasync def main():\n    return await asyncio.gather(dobro(2), dobro(3))",
                        "import inspect\nassert inspect.iscoroutinefunction(dobro), 'dobro deveria ser uma coroutine (async def)'\nassert inspect.iscoroutinefunction(main), 'main deveria ser uma coroutine (async def)'\nassert 'gather' in _student_code, 'use asyncio.gather dentro de main'",
                    ),
                    quiz(
                        "O que `asyncio.gather(a(), b())` faz?",
                        "Roda as coroutines intercalando as esperas e devolve os resultados na ordem",
                        ["Roda as coroutines intercalando as esperas e devolve os resultados na ordem", "Roda uma só, ignorando a outra", "Cria processos paralelos"],
                    ),
                    quiz(
                        "O que `asyncio.run(coroutine)` faz?",
                        "Cria o event loop, roda a coroutine principal e fecha tudo",
                        ["Cria o event loop, roda a coroutine principal e fecha tudo", "Compila o programa", "Abre um arquivo"],
                    ),
                    quiz(
                        "O asyncio roda em quantos threads?",
                        "um único thread",
                        ["um único thread", "um por coroutine", "dois"],
                    ),
                    text(
                        "Complete: o ganho do asyncio vem de não ficar ___ durante as esperas de I/O.",
                        "parado",
                    ),
                ],
            ),
            topic(
                "quando-usar-assincronia",
                "Quando usar assincronia",
                """
# Quando usar assincronia

`async`/`await` não é para todo código — é uma **ferramenta para I/O**.

## Use async quando houver muito I/O

- chamadas a APIs externas;
- consultas a banco de dados;
- leitura/escrita de arquivos e redes.

Nesses casos, o ganho de não ficar parado na espera é enorme (ex.: o FastAPI
do Módulo 18 aceita rotas `async` justamente por isso).

## NÃO use async para cálculo pesado

Operações que usam **muito CPU** (processamento, loops longos) não esperam
nada — o `await` não ajuda, e a complexidade só atrapalha. Para isso, o
próximo módulo (processos/paralelismo) é a resposta.

## Regra prática

| Situação | Abordagem ideal |
|---|---|
| Muitas esperas de rede/banco | `asyncio` (async/await) |
| Muito cálculo de CPU | multiprocessing (próximo módulo) |
| Pouco de tudo | código sequencial simples |

> 💡 Comece sempre **sequencial**. Só adicione async quando a espera de I/O
> for de fato um gargalo — código async é mais difícil de ler e depurar.
""",
                [
                    quiz(
                        "Quando a programação assíncrona vale a pena?",
                        "Quando há muito I/O (rede, banco, arquivos)",
                        ["Quando há muito I/O (rede, banco, arquivos)", "Quando há muito cálculo de CPU", "Em qualquer situação"],
                    ),
                    quiz(
                        "Para código com muito cálculo de CPU, async:",
                        "não ajuda, pois o await não acelera processamento",
                        ["não ajuda, pois o await não acelera processamento", "acelera de verdade", "trava o programa"],
                    ),
                    quiz(
                        "Qual é a melhor abordagem para um problema simples e curto?",
                        "Código sequencial simples",
                        ["Código sequencial simples", "async desde o início", "multiprocessing"],
                    ),
                    quiz(
                        "O FastAPI (Módulo 18) aceita rotas `async` porque:",
                        "APIs web lidam com muito I/O (requisições, banco, rede)",
                        ["APIs web lidam com muito I/O (requisições, banco, rede)", "é obrigatório", "async deixa o HTML bonito"],
                    ),
                    text(
                        "Complete: comece sempre pelo código ___, e só adicione async se a espera for um gargalo.",
                        "sequencial",
                    ),
                ],
            ),
        ],
    )


# ============================================================
# MODULO 20 - Concorrência e Paralelismo (novo, Fase 10 do roteiro)
# Conceitual. threads/processos de verdade não rodam no Pyodide.
# ============================================================

def build_modulo_concorrencia():
    return module(
        "concorrencia-e-paralelismo",
        "Módulo 20 — Concorrência e Paralelismo",
        "Threads, processos e o GIL: as diferenças entre lidar com muitas tarefas ao mesmo tempo e rodar em paralelo de verdade.",
        [
            topic(
                "concorrencia-vs-paralelismo",
                "Concorrência vs paralelismo",
                """
# Concorrência vs paralelismo

Os dois termos parecem sinônimos, mas são diferentes:

## Concorrência

Lidar com **várias tarefas ao mesmo tempo** — intercalando o trabalho. Uma
única pessoa (ou núcleo) alterna entre tarefas, dando passos em cada uma.

## Paralelismo

**Executar de verdade ao mesmo tempo** — cada tarefa num núcleo próprio. São
muitos "cérebro" trabalhando juntos.

## A analogia

- **Concorrência**: uma cozinheira com três panelas — alterna entre elas,
  mas é uma pessoa só.
- **Paralelismo**: três cozinheiras, cada uma com sua panela.

## Na prática

| | Concorrência | Paralelismo |
|---|---|---|
| Quantos núcleos | um já basta | precisa de vários |
| Resultado | intercalado (parece simultâneo) | simultâneo de verdade |
| Em Python | asyncio, threads | multiprocessing |

> 💡 Um programa com muitos núcleos disponíveis pode fazer paralelismo; com
> um núcleo só, o máximo é concorrência (intercalação).
""",
                [
                    quiz(
                        "O que é concorrência?",
                        "Lidar com várias tarefas ao mesmo tempo, intercalando o trabalho",
                        ["Lidar com várias tarefas ao mesmo tempo, intercalando o trabalho", "Rodar de verdade em vários núcleos", "Fazer uma tarefa por vez"],
                    ),
                    quiz(
                        "O que é paralelismo?",
                        "Executar tarefas de verdade ao mesmo tempo, em núcleos diferentes",
                        ["Executar tarefas de verdade ao mesmo tempo, em núcleos diferentes", "Intercalar tarefas num núcleo só", "Não há diferença"],
                    ),
                    quiz(
                        "Num computador com um único núcleo, é possível:",
                        "concorrência (intercalação), não paralelismo de verdade",
                        ["concorrência (intercalação), não paralelismo de verdade", "paralelismo de verdade", "nenhum dos dois"],
                    ),
                    quiz(
                        "Para paralelismo de verdade é preciso:",
                        "vários núcleos (processadores) executando juntos",
                        ["vários núcleos (processadores) executando juntos", "apenas uma thread", "mais memória RAM"],
                    ),
                    text(
                        "Complete: a cozinheira com três panelas alternando entre elas é uma analogia de ___.",
                        "concorrência",
                    ),
                ],
            ),
            topic(
                "threads",
                "Threads",
                """
# Threads

Uma **thread** é um fluxo de execução **dentro de um processo**. Um programa
pode ter várias threads, cada uma rodando seu pedaço de código.

## O que as threads compartilham

Todas as threads de um processo compartilham a **mesma memória** — o que
facilita a comunicação, mas também é fonte clássica de bugs (duas threads
mexendo no mesmo dado ao mesmo tempo).

## Onde threads brilham

Em tarefas de **I/O** (esperar rede, banco, arquivo): enquanto uma thread
espera, outra trabalha — é concorrência na prática:

```python
import threading

def tarefa(nome):
    print(f"{nome} rodando")

t1 = threading.Thread(target=tarefa, args=("A",))
t1.start()
```

## A pegadinha do Python: o GIL

Em Python (CPython), threads **não** dão paralelismo de CPU — o **GIL**
(tópico próprio) limita. Para processamento pesado, threads quase não ajudam.

> 💡 Regra rápida: threads = bom para **esperar** (I/O); não para **calcular**
> (CPU), por causa do GIL.
""",
                [
                    quiz(
                        "O que é uma thread?",
                        "Um fluxo de execução leve dentro de um processo",
                        ["Um fluxo de execução leve dentro de um processo", "Um programa separado com memória própria", "Um arquivo de configuração"],
                    ),
                    quiz(
                        "As threads de um mesmo processo compartilham:",
                        "a memória do processo",
                        ["a memória do processo", "nada", "apenas o arquivo principal"],
                    ),
                    quiz(
                        "Threads são especialmente boas para:",
                        "tarefas de I/O, onde há espera (rede, banco, arquivo)",
                        ["tarefas de I/O, onde há espera (rede, banco, arquivo)", "cálculo pesado de CPU", "qualquer tarefa igualmente"],
                    ),
                    quiz(
                        "Em Python, threads NÃO dão paralelismo de CPU por causa do:",
                        "GIL",
                        ["GIL", "pip", "PyPI"],
                    ),
                    text(
                        "Complete: threads são boas para esperar (I/O), não para ___ (CPU).",
                        "calcular",
                    ),
                ],
            ),
            topic(
                "processos",
                "Processos",
                """
# Processos

Um **processo** é um programa em execução, com **memória própria**. Quando o
sistema operacional roda processos em núcleos diferentes, temos **paralelismo
de verdade**.

## A diferença para threads

| | Thread | Processo |
|---|---|---|
| Memória | compartilhada | própria |
| Criar um novo | leve/rápido | mais pesado |
| Comunicação | direta (variáveis) | precisa de mecanismos (IPC) |
| Contorna o GIL | não | sim (cada processo tem o seu GIL) |

## O módulo multiprocessing

O Python tem o módulo `multiprocessing`, que roda funções em processos
separados — ótimo para **cálculo pesado de CPU**:

```python
from multiprocessing import Pool

def dobro(n):
    return n * 2

with Pool(4) as p:
    resultados = p.map(dobro, [1, 2, 3, 4])   # [2, 4, 6, 8]
```

## Quando usar processos

- Trabalho pesado de CPU que pode ser dividido.
- Precisa de paralelismo de verdade em máquinas com vários núcleos.

> 💡 O custo: processos são mais "pesados" de criar e não compartilham estado
> facilmente — use com bom motivo.
""",
                [
                    quiz(
                        "O que é um processo?",
                        "Um programa em execução, com memória própria",
                        ["Um programa em execução, com memória própria", "Uma função async", "Uma thread leve"],
                    ),
                    quiz(
                        "Processos são especialmente bons para:",
                        "trabalho pesado de CPU, com paralelismo de verdade",
                        ["trabalho pesado de CPU, com paralelismo de verdade", "esperar rede", "qualquer tarefa"],
                    ),
                    quiz(
                        "Processos compartilham memória entre si?",
                        "Não, cada um tem a sua",
                        ["Não, cada um tem a sua", "Sim, totalmente", "Só se forem threads"],
                    ),
                    quiz(
                        "Qual módulo do Python cria processos para paralelismo de CPU?",
                        "multiprocessing",
                        ["multiprocessing", "threading", "asyncio"],
                    ),
                    text(
                        "Complete: cada processo tem o ___ próprio, então multiprocessing contorna o GIL.",
                        "gil",
                    ),
                ],
            ),
            topic(
                "gil",
                "O GIL (Global Interpreter Lock)",
                """
# O GIL (Global Interpreter Lock)

O **GIL** (*Global Interpreter Lock*) é um mecanismo do CPython (o Python
padrão): apenas **uma thread** executa bytecode Python por vez.

## Qual o impacto?

- **Threads não dão paralelismo de CPU**: mesmo com 8 núcleos, duas threads
  Python não rodam cálculos ao mesmo tempo.
- **I/O continua se beneficiando**: durante uma espera, a thread libera o GIL
  e outra roda — por isso threads ainda ajudam em rede/banco/arquivo.

## Por que ele existe?

O GIL simplifica o gerenciamento de memória do CPython (torna o coletor de
lixo seguro e código C embutido mais simples), em troca de performance em
multithread de CPU.

## Como contornar

- **Cálculo pesado**: use **processos** (`multiprocessing`) — cada processo
  tem seu próprio GIL.
- **I/O**: threads ou `asyncio` (o GIL é liberado na espera).
- **Código C/nativo**: bibliotecas como `numpy` liberam o GIL e rodam em
  paralelo de verdade.

> 💡 Em resumo: o GIL não é "fim do mundo" — é só entender que em Python,
> threads servem para I/O e processos para CPU.
""",
                [
                    quiz(
                        "O que é o GIL?",
                        "Um bloqueio do CPython que permite apenas uma thread executando bytecode por vez",
                        ["Um bloqueio do CPython que permite apenas uma thread executando bytecode por vez", "Um gerenciador de pacotes", "Um tipo de processo"],
                    ),
                    quiz(
                        "Qual é o impacto prático do GIL?",
                        "Threads não dão paralelismo de CPU em Python",
                        ["Threads não dão paralelismo de CPU em Python", "Threads não podem ser criadas", "I/O fica impossível"],
                    ),
                    quiz(
                        "Durante uma espera de I/O, a thread:",
                        "libera o GIL, permitindo outra thread rodar",
                        ["libera o GIL, permitindo outra thread rodar", "trava o GIL para sempre", "é encerrada"],
                    ),
                    quiz(
                        "Para contornar o GIL em cálculos pesados, usa-se:",
                        "processos (multiprocessing)",
                        ["processos (multiprocessing)", "mais threads", "menos memória"],
                    ),
                    text(
                        "Complete: bibliotecas nativas como numpy ___ o GIL e rodam em paralelo de verdade.",
                        "liberam",
                    ),
                ],
            ),
            topic(
                "escolhendo-a-ferramenta",
                "Escolhendo a ferramenta certa",
                """
# Escolhendo a ferramenta certa

A decisão de usar sequencial, async, threads ou processos depende do tipo de
trabalho.

## A árvore de decisão

| Situação | Ferramenta |
|---|---|
| Uma tarefa simples, sem gargalo | código **sequencial** |
| Muitas **esperas** (rede, banco, arquivo) | `asyncio` ou **threads** |
| Muito **cálculo de CPU** que dá para dividir | **multiprocessing** |
| Tudo isso misturado | combinar com cuidado |

## Complexidade crescente

Da mais simples para a mais complexa:

```
sequencial  ->  asyncio  ->  threads  ->  processos
```

Cada degrau traz mais poder, mas também mais armadilhas (bugs de
concorrência, comunicação entre processos...).

## A regra de ouro

**Não otimize antes da hora.** Comece sequencial, meça, e só suba de
complexidade se o gargalo real pedir. Código concorrente é mais difícil de
testar e depurar — não é brinde, é custo.

> 💡 Em entrevistas e projetos, saber *justificar a escolha* vale mais do que
> decorar APIs. Use a tabela acima como guia mental.
""",
                [
                    quiz(
                        "Muitas esperas de rede/banco — qual abordagem?",
                        "asyncio ou threads",
                        ["asyncio ou threads", "multiprocessing", "código sequencial"],
                    ),
                    quiz(
                        "Cálculo pesado de CPU que pode ser dividido — qual abordagem?",
                        "multiprocessing",
                        ["multiprocessing", "asyncio", "threads"],
                    ),
                    quiz(
                        "Um problema simples, sem gargalo — qual abordagem?",
                        "código sequencial",
                        ["código sequencial", "async", "processos"],
                    ),
                    quiz(
                        "Qual a ordem da menor para a maior complexidade?",
                        "sequencial, asyncio, threads, processos",
                        ["sequencial, asyncio, threads, processos", "processos, threads, asyncio, sequencial", "threads, sequencial, processos, asyncio"],
                    ),
                    text(
                        "Complete: a regra de ouro é não ___ antes da hora — comece sequencial.",
                        "otimizar",
                    ),
                ],
            ),
        ],
    )


# ============================================================
# MODULO 21 - Python para IA (novo, Fase 11 do roteiro)
# Conceitual, com trechos de código de exemplo (não roda treino/
# LLMs no Pyodide). Fecha o curso.
# ============================================================

def build_modulo_ia():
    return module(
        "python-para-ia",
        "Módulo 21 — Python para IA",
        "Fechando o ciclo: inteligência artificial, machine learning, as bibliotecas de IA, LLMs e o fluxo de um projeto real.",
        [
            topic(
                "o-que-e-inteligencia-artificial",
                "O que é inteligência artificial?",
                """
# O que é inteligência artificial?

**Inteligência Artificial (IA)** é a área que cria sistemas capazes de fazer
tarefas que normalmente exigiriam inteligência humana — reconhecer imagens,
entender texto, tomar decisões, conversar.

## Os termos que você vai ver

| Termo | O que é |
|---|---|
| **IA** | a área inteira, o guarda-chuva |
| **Machine Learning (ML)** | subárea da IA: o computador **aprende com dados** em vez de regras escritas à mão |
| **Deep Learning** | ML com redes neurais profundas |
| **LLM** | modelo de linguagem grande (ex.: GPT) — um tipo de deep learning para texto |

## Como o ML funciona, em uma frase

Em vez de programar regras ("se e-mail contém X, é spam"), você **mostra
exemplos** ao modelo, e ele descobre os padrões sozinho.

## Por que Python?

Python é a linguagem **dominante** da IA: bibliotecas maduras, comunidade
enorme e ecossistema completo — exatamente o que você construiu neste curso.

> 💡 Você não precisa ser PhD em matemática para começar: entender dados,
> Python e os conceitos deste módulo já abre portas para projetos reais.
""",
                [
                    quiz(
                        "O que é Inteligência Artificial?",
                        "A área que cria sistemas capazes de tarefas que exigiriam inteligência humana",
                        ["A área que cria sistemas capazes de tarefas que exigiriam inteligência humana", "Um tipo de banco de dados", "Um framework web"],
                    ),
                    quiz(
                        "O que é Machine Learning (ML)?",
                        "Uma subárea da IA onde o computador aprende padrões a partir de dados",
                        ["Uma subárea da IA onde o computador aprende padrões a partir de dados", "Regras escritas à mão pelo programador", "Um editor de código"],
                    ),
                    quiz(
                        "Como o ML difere da programação tradicional?",
                        "Em vez de regras, o modelo aprende com exemplos de dados",
                        ["Em vez de regras, o modelo aprende com exemplos de dados", "Não há diferença", "ML não usa dados"],
                    ),
                    quiz(
                        "Por que Python é a linguagem dominante em IA?",
                        "Bibliotecas maduras, comunidade enorme e ecossistema completo",
                        ["Bibliotecas maduras, comunidade enorme e ecossistema completo", "É a mais rápida em tudo", "Só funciona para IA"],
                    ),
                    text(
                        "Complete: ML é uma ___ da IA em que o computador aprende com dados.",
                        "subárea",
                    ),
                ],
            ),
            topic(
                "machine-learning-basico",
                "Machine learning na prática",
                """
# Machine learning na prática

## O fluxo de um modelo de ML

1. **Dados**: você tem exemplos (linhas) com características (colunas).
2. **Treino**: o modelo aprende os padrões a partir dos dados de treino.
3. **Avaliação**: você testa o modelo em dados **que ele nunca viu**.
4. **Previsão**: o modelo faz previsões em dados novos.

## Exemplo com scikit-learn

```python
from sklearn.ensemble import RandomForestClassifier

modelo = RandomForestClassifier()
modelo.fit(X_treino, y_treino)        # treino
previsao = modelo.predict(X_novo)     # previsão
```

## Dados de treino vs. teste

Separar é essencial: se você avaliar o modelo com os **mesmos dados** do
treino, ele "decora" (overfitting) e parece ótimo — mas falha na vida real.

```python
from sklearn.model_selection import train_test_split

X_treino, X_teste, y_treino, y_teste = train_test_split(X, y, test_size=0.2)
```

## Tarefas comuns

- **Classificação**: e-mail é spam ou não? A imagem é gato ou cachorro?
- **Regressão**: quanto será o preço da casa?
- **Agrupamento**: dividir clientes em grupos parecidos.

> 💻 Este é um trecho de exemplo. Para rodar de verdade, instale
> (`pip install scikit-learn` — Módulo 13) e siga um tutorial com o famoso
> dataset de íris.
""",
                [
                    quiz(
                        "O que é o treinamento de um modelo?",
                        "O modelo aprende padrões a partir dos dados de treino",
                        ["O modelo aprende padrões a partir dos dados de treino", "O modelo é apagado", "O modelo vira um site"],
                    ),
                    quiz(
                        "Para que servem os dados de TESTE?",
                        "Medir se o modelo generaliza para dados que ele nunca viu",
                        ["Medir se o modelo generaliza para dados que ele nunca viu", "Treinar o modelo de novo", "Gerar mais dados"],
                    ),
                    quiz(
                        "Por que não avaliar o modelo com os mesmos dados do treino?",
                        "Ele pode 'decorar' (overfitting) e parecer melhor do que é",
                        ["Ele pode 'decorar' (overfitting) e parecer melhor do que é", "Porque os dados somem", "Porque é mais lento"],
                    ),
                    quiz(
                        "Qual é um exemplo de tarefa de classificação?",
                        "Dizer se um e-mail é spam ou não",
                        ["Dizer se um e-mail é spam ou não", "Prever o preço de uma casa", "Agrupar clientes sem rótulo"],
                    ),
                    text(
                        "Complete: a ordem típica é dados, ___, avaliação e previsão.",
                        "treino",
                    ),
                ],
            ),
            topic(
                "bibliotecas-de-ia",
                "As bibliotecas de IA",
                """
# As bibliotecas de IA

O ecossistema de IA em Python gira em torno de poucas bibliotecas centrais.

## A base

| Biblioteca | Para quê |
|---|---|
| **numpy** | arrays e matemática numérica — a fundação de tudo |
| **pandas** | tabelas e análise de dados (você viu o conceito em dados) |
| **matplotlib** | gráficos e visualização |

## Machine learning

| Biblioteca | Para quê |
|---|---|
| **scikit-learn** | ML clássico: classificação, regressão, agrupamento |
| **statsmodels** | estatística |

## Deep learning e LLMs

| Biblioteca | Para quê |
|---|---|
| **pytorch** / **tensorflow** | redes neurais / deep learning |
| **transformers** | modelos de linguagem (LLMs como GPT) |

## Um exemplo de fluxo com pandas + scikit-learn

```python
import pandas as pd
from sklearn.ensemble import RandomForestClassifier

dados = pd.read_csv("clientes.csv")          # pandas
modelo = RandomForestClassifier()
modelo.fit(dados[["idade", "renda"]], dados["comprou"])   # sklearn
```

> 💡 Não tente decorar tudo. O que importa: saber **quais problemas cada
> biblioteca resolve** para escolher a certa quando precisar.
""",
                [
                    quiz(
                        "Qual biblioteca é a base de arrays e matemática numérica?",
                        "numpy",
                        ["numpy", "pandas", "matplotlib"],
                    ),
                    quiz(
                        "Qual biblioteca trabalha com tabelas e análise de dados?",
                        "pandas",
                        ["pandas", "numpy", "scikit-learn"],
                    ),
                    quiz(
                        "Qual biblioteca faz machine learning clássico (classificação, regressão)?",
                        "scikit-learn",
                        ["scikit-learn", "transformers", "matplotlib"],
                    ),
                    quiz(
                        "Qual biblioteca é usada para modelos de linguagem (LLMs)?",
                        "transformers",
                        ["transformers", "pandas", "numpy"],
                    ),
                    text(
                        "Complete: deep learning é feito principalmente com pytorch ou ___.",
                        "tensorflow",
                    ),
                ],
            ),
            topic(
                "llms-e-prompts",
                "LLMs e engenharia de prompt",
                """
# LLMs e engenharia de prompt

## O que é um LLM?

Um **LLM** (*Large Language Model*) é um modelo gigante treinado em **muito
texto** — como o GPT e o Claude. Ele entende e gera linguagem natural.

## Como ele "pensa"

Na essência, um LLM prevê **o próximo token** (pedaço de texto) dado o que veio
antes, repetindo isso para gerar respostas inteiras. O tamanho e a qualidade
do treino é que fazem isso parecer "inteligente".

## O que é um prompt?

O **prompt** é a instrução/texto que você dá ao modelo. A mesma ferramenta
pode responder muito bem ou muito mal dependendo de **como** você pergunta.

## Engenharia de prompt

Técnicas para obter respostas melhores:

- **Seja específico**: "resuma em 3 marcadores" melhor que "resuma".
- **Dê contexto**: diga quem é o público, o objetivo, o formato.
- **Exemplifique**: mostre um exemplo do formato esperado.
- **Peça passo a passo**: para problemas de lógica, peça raciocínio.
- **Role**: "você é um tutor de Python" muda o estilo da resposta.

## Integrando LLMs no seu código

```python
import openai

resposta = openai.chat.completions.create(
    model="gpt-4o-mini",
    messages=[{"role": "user", "content": "Explique for em uma frase."}],
)
print(resposta.choices[0].message.content)
```

> 💻 Esse código precisa de chave de API e rede — rode na sua máquina se
> quiser testar (requer `pip install openai`). Aqui, o foco é o conceito.
""",
                [
                    quiz(
                        "O que é um LLM?",
                        "Um modelo de linguagem grande, treinado em muito texto, que gera linguagem natural",
                        ["Um modelo de linguagem grande, treinado em muito texto, que gera linguagem natural", "Um banco de dados", "Um framework web"],
                    ),
                    quiz(
                        "Em essência, um LLM gera texto:",
                        "prevendo o próximo token dado o que veio antes",
                        ["prevendo o próximo token dado o que veio antes", "copiando de uma enciclopédia", "escolhendo aleatoriamente"],
                    ),
                    quiz(
                        "O que é um prompt?",
                        "A instrução/texto que você dá ao modelo",
                        ["A instrução/texto que você dá ao modelo", "O código-fonte do modelo", "A saída do modelo"],
                    ),
                    quiz(
                        "Uma boa técnica de engenharia de prompt é:",
                        "ser específico e dar contexto sobre o formato esperado",
                        ["ser específico e dar contexto sobre o formato esperado", "perguntar sem detalhes", "sempre pedir respostas curtas"],
                    ),
                    text(
                        "Complete: o LLM prevê o próximo ___ dado o texto que veio antes.",
                        "token",
                    ),
                ],
            ),
            topic(
                "fluxo-de-um-projeto-de-ia",
                "O fluxo de um projeto de IA",
                """
# O fluxo de um projeto de IA

Um projeto de IA de verdade segue etapas — e, surpresa, quase todas usam o
Python que você aprendeu neste curso.

## As etapas

1. **Entender o problema** — qual pergunta queremos responder? Qual o dado?
2. **Coletar e limpar os dados** — dados bons são a base (Módulo 12: arquivos,
   CSV, JSON!).
3. **Explorar** — gráficos e estatísticas para conhecer os dados (pandas,
   matplotlib).
4. **Treinar o modelo** — separar treino/teste, escolher o algoritmo
   (scikit-learn).
5. **Avaliar** — medir a performance em dados que o modelo não viu.
6. **Melhorar** — ajustar parâmetros, mais dados, limpeza melhor.
7. **Deploy** — expor o modelo como API (Módulo 18: FastAPI!).

## Por que isso fecha o curso

Veja como tudo se conecta:

- Módulos 3-12: manipular dados e arquivos.
- Módulo 13: instalar numpy/pandas/sklearn.
- Módulo 14: versionar o projeto com Git.
- Módulo 16: testar o pipeline.
- Módulo 18: servir o modelo com FastAPI.

## A real

A maior parte do trabalho em IA **não é treinar modelo** — é entender,
limpar e preparar dados. E isso é exatamente o que um bom programador Python
sabe fazer.

> 🎉 Parabéns: você chegou ao fim da trilha do zero ao hero. O próximo passo é
> pegar um problema pequeno, de preferência com dados reais, e fazer o fluxo
> completo — do dado ao deploy.
""",
                [
                    quiz(
                        "Qual é o primeiro passo de um projeto de IA?",
                        "Entender o problema e conhecer os dados",
                        ["Entender o problema e conhecer os dados", "Treinar o modelo", "Fazer o deploy"],
                    ),
                    quiz(
                        "Qual é a ordem típica do fluxo?",
                        "problema -> dados -> treino -> avaliação -> deploy",
                        ["problema -> dados -> treino -> avaliação -> deploy", "treino -> deploy -> dados -> problema", "deploy -> avaliação -> treino -> dados"],
                    ),
                    quiz(
                        "Qual a parte mais demorada na maioria dos projetos de IA?",
                        "Entender, limpar e preparar os dados",
                        ["Entender, limpar e preparar os dados", "Escolher o modelo", "Escrever o prompt"],
                    ),
                    quiz(
                        "O que este curso te preparou para fazer no fluxo de IA?",
                        "Tudo: de mexer com dados e arquivos até servir o modelo com FastAPI",
                        ["Tudo: de mexer com dados e arquivos até servir o modelo com FastAPI", "Apenas treinar modelos", "Apenas escrever prompts"],
                    ),
                    text(
                        "Complete: dados ruins geram modelos ___, por isso limpar dados é essencial.",
                        "ruins",
                    ),
                ],
            ),
        ],
    )


# ============================================================
# Montagem final: monta o curso na ordem do roteiro
# ============================================================

# Ordem final dos módulos no curso publicado. Módulos cujo builder ainda não
# existe (fases futuras não escritas) ficam intactos no JSON, só reposicionados.
TARGET_ORDER = [
    "hello-world",
    "logica-de-programacao-hero",
    "preparando-o-ambiente",
    "fundamentos",
    "controle-de-fluxo",
    "estruturas-de-dados",
    "funcoes",
    "tratamento-de-erros",
    "modulos-e-imports",
    "poo",
    "python-avancado",
    "type-hints",
    "arquivos-e-dados",
    "bibliotecas-e-dependencias",
    "git-e-github",
    "qualidade-de-codigo",
    "testes-automatizados",
    "programacao-web",
    "fastapi",
    "programacao-assincrona",
    "concorrencia-e-paralelismo",
    "python-para-ia",
]

# Módulos legados que serão removidos (substituídos/splitados pelos novos).
LEGACY_GONE: list[str] = ["organizando-o-codigo"]

BUILDERS = {
    "logica-de-programacao-hero": build_modulo_logica,
    "preparando-o-ambiente": build_modulo_ambiente,
    "fundamentos": build_modulo_fundamentos,
    "controle-de-fluxo": build_modulo_controle,
    "estruturas-de-dados": build_modulo_dados,
    "funcoes": build_modulo_funcoes,
    "tratamento-de-erros": build_modulo_erros,
    "modulos-e-imports": build_modulo_modulos,
    "poo": build_modulo_poo,
    "python-avancado": build_modulo_avancado,
    "type-hints": build_modulo_type_hints,
    "arquivos-e-dados": build_modulo_arquivos,
    "bibliotecas-e-dependencias": build_modulo_dependencias,
    "git-e-github": build_modulo_git,
    "qualidade-de-codigo": build_modulo_qualidade,
    "testes-automatizados": build_modulo_testes,
    "programacao-web": build_modulo_web,
    "fastapi": build_modulo_fastapi,
    "programacao-assincrona": build_modulo_async,
    "concorrencia-e-paralelismo": build_modulo_concorrencia,
    "python-para-ia": build_modulo_ia,
}


def main():
    data = json.loads(OUT_PATH.read_text(encoding="utf-8"))
    by_slug = {m["slug"]: m for m in data["modules"]}

    for slug in LEGACY_GONE:
        by_slug.pop(slug, None)

    # Reconstrói (ou insere) os módulos com builder desta execução. O resto
    # permanece como está no JSON — slugs (e progresso) preservados.
    for slug, builder in BUILDERS.items():
        by_slug[slug] = builder()

    modules = []
    seen = set()
    for slug in TARGET_ORDER:
        if slug in by_slug and slug not in seen:
            modules.append(by_slug[slug])
            seen.add(slug)
    # Sobras que não estão na ordem alvo (segurança) vão para o fim.
    for slug in list(by_slug):
        if slug not in seen:
            modules.append(by_slug[slug])

    for i, m in enumerate(modules):
        m["position"] = i
        # Renumera o título "Módulo N" pra bater com a posição nova.
        m["title"] = re.sub(r"^Módulo \d+", f"Módulo {i}", m["title"])
        for j, t in enumerate(m["topics"]):
            t["position"] = j
            for k, e in enumerate(t.get("exercises", [])):
                e["position"] = k

    # Só os módulos reconstruídos nesta execução precisam cumprir o mínimo de
    # 5 exercícios/tópico; os legados (fases futuras) passam só na validação
    # estrutural (quiz/code), como sempre.
    active_module_slugs = set(BUILDERS)
    problems = check(modules, active_module_slugs)
    if problems:
        print("ERROS - nada foi escrito:")
        for p in problems:
            print("  -", p)
        raise SystemExit(1)

    with OUT_PATH.open("w", encoding="utf-8") as f:
        json.dump({"slug": data["slug"], "title": data["title"], "modules": modules}, f, ensure_ascii=False, indent=2)
        f.write("\n")

    n_topics = sum(len(m["topics"]) for m in modules)
    n_ex = sum(len(t.get("exercises", [])) for m in modules for t in m["topics"])
    print(f"OK: {len(modules)} módulos, {n_topics} tópicos, {n_ex} exercícios -> {OUT_PATH}")


if __name__ == "__main__":
    main()
