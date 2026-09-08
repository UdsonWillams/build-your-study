# -*- coding: utf-8 -*-
"""Gera/expande app/content/ingles-do-zero.json a partir de uma estrutura Python.

Reescrita completa do curso de inglês (ver tools/ENGLISH_ROADMAP.md): a grade
antiga de 9 módulos foi descartada em favor de 27 módulos bem mais granulares
(A1 -> C1 + trilha aplicada). Como Python (tools/build_python.py), este script
usa o padrão **incremental**: um dicionário `BUILDERS` (slug do módulo ->
função que constrói aquele módulo) e uma lista `TARGET_ORDER` com a ordem
final de TODOS os 27 módulos do roteiro (inclusive os que ainda não têm
builder escrito). A cada execução, só os módulos com builder aparecem no JSON
final, na posição definida por TARGET_ORDER — módulos do roteiro ainda não
escritos simplesmente não existem no curso publicado até a fase deles ser
construída. Diferente de build_python.py, aqui não há JSON legado para
preservar como base: é reescrita do zero, então cada execução reconstrói do
zero todos os módulos que já têm builder no script (a "base" é o próprio
código Python, não o JSON gravado anteriormente).
"""
import json
import re
from copy import deepcopy
from functools import wraps
from pathlib import Path

CONTENT_DIR = Path(__file__).resolve().parent.parent / "app" / "content"
OUT_PATH = CONTENT_DIR / "ingles-do-zero.json"


# ============================================================
# Helpers de autoria (mesmo padrão dos outros geradores)
# ============================================================

# Espelha normalize() do web/static/js/runner.js: e' assim que o front-end
# compara a resposta do aluno com a solucao.
def normalize(s):
    s = s.lower().replace("ё", "е")
    s = re.sub(r"[.,!?;:'\"-]", "", s)
    return re.sub(r"\s+", " ", s).strip()


# Detecta portugues pra decidir em que idioma o botao de ouvir deve falar.
PT_HINT = re.compile(
    r"[áàâãéêíóôõúüç]|\w+mente\b|"
    r"\b(não|você|vocês|está|estão|estou|estamos|estava|são|sou|seja|eu|uma|umas|uns|com|para|pelo|pela|pelos|pelas|"
    r"que|isso|isto|aqui|ali|quando|também|então|mais|menos|muito|pouco|todos|todas|tudo|nada|porque|porém|mas|"
    r"como|onde|quem|qual|quais|sobre|entre|depois|antes|sempre|nunca|ainda|cada|mesmo|mesma|seu|sua|seus|suas|"
    r"nós|eles|elas|ele|ela|dos|das|nas|nos|faz|fazem|fazer|ser|ter|foi|era|eram|esse|essa|esses|essas|este|esta|"
    r"aquele|aquela|frase|verbo|verbos|palavra|forma|passado|futuro|presente|ação|hábito|pessoa|pessoas|coisa|coisas|"
    r"exemplo|regra|oração|sujeito|objeto|objetos|tempo|bem|obrigado|obrigada|sim|agora|hoje|ontem|meu|minha|nome|"
    r"gosto|quero|tenho|vou|vai|vamos|dizer|falar|ver|saber|jogar|mora|casa|livro|dia|dias|noite|ir|vir|comer|"
    r"escrever|pegar|levar|desistir|procurar|descobrir|levantar|desligar|ligar|adiar|entender|resolver|lidar|"
    r"contraste|causa|iniciante|básico|maioria|tira|mudo|consoante|vogal|ideias|animais|posse|lugares|datas|"
    r"artigos|voz|passiva|condicionais|ficar|alguns|casos|final|masculino|feminino|nível|letra|uso)\b",
    re.I)

def is_target_language(s):
    return bool(re.search(r"[A-Za-z]", s)) and not PT_HINT.search(s)


def ex(type, prompt, solution, options=None, audio_text=None, audio_lang="en-US"):
    d = {"type": type, "prompt": prompt, "solution": solution}
    if options is not None:
        d["options"] = options
    if audio_text is not None:
        d["audio_text"] = audio_text
    if audio_lang is not None:
        d["audio_lang"] = audio_lang
    return d

def topic(slug, title, lesson_md, exercises):
    return {"slug": slug, "title": title, "lesson_md": lesson_md.strip(), "exercises": exercises}

def module(slug, title, summary, topics):
    return {"slug": slug, "title": title, "summary": summary, "topics": topics}


def _expand_target_builder(builder):
    """Aplica o conteúdo complementar aos módulos com revisão registrada."""
    @wraps(builder)
    def wrapped():
        return _expand_target_module(builder())
    return wrapped


# ============================================================
# Validacao (roda ANTES de escrever qualquer coisa)
# ============================================================

def check(modules, active_module_slugs):
    """Trava erros de autoria antes de gravar o JSON.

    `active_module_slugs`: módulos sendo escritos/tocados NESTA fase. Os
    módulos com meta fechada exigem exatamente 10 exercícios por tópico; os
    demais módulos ativos seguem o mínimo geral de 5.
    """
    problems = []
    topic_slugs = []
    module_slugs = []

    for m in modules:
        module_slugs.append(m["slug"])
        for t in m["topics"]:
            topic_slugs.append(t["slug"])
            loc_base = f"{m['slug']}/{t['slug']}"
            if m["slug"] in EXACT_10_MODULE_SLUGS:
                if len(t["exercises"]) != 10:
                    problems.append(
                        f"{loc_base}: {len(t['exercises'])} exercícios (esperado 10)"
                    )
            elif m["slug"] in active_module_slugs and len(t["exercises"]) < 5:
                problems.append(f"{loc_base}: só {len(t['exercises'])} exercícios (mínimo 5)")
            for i, e in enumerate(t["exercises"]):
                loc = f"{loc_base} #{i}"
                if not e.get("solution"):
                    problems.append(f"{loc}: solution vazia")
                if e["type"] == "quiz":
                    opts = e.get("options") or []
                    norms = [normalize(o) for o in opts]
                    if len(set(norms)) != len(norms):
                        problems.append(f"{loc}: alternativas ambíguas após normalize: {opts}")
                    if norms.count(normalize(e["solution"])) != 1:
                        problems.append(f"{loc}: solution não bate com exatamente 1 alternativa: {opts}")
                if e["type"] in ("audio", "speak"):
                    if not e.get("audio_text"):
                        problems.append(f"{loc}: {e['type']} sem audio_text")
                    elif normalize(e["audio_text"]) != normalize(e["solution"]):
                        problems.append(f"{loc}: audio_text != solution")

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
        other_slugs = {other.get("slug")}
        for m in other.get("modules", []):
            other_slugs.add(m["slug"])
            for t in m.get("topics", []):
                other_slugs.add(t["slug"])
        collisions = (set(module_slugs) | set(topic_slugs)) & other_slugs
        if collisions:
            problems.append(f"slugs colidindo com {path.name}: {collisions}")

    return problems


# ============================================================
# MODULO 1 - Primeiros Passos (Sobrevivencia) - A1
# ============================================================

@_expand_target_builder
def build_modulo_01_primeiros_passos():
    return module(
        "modulo-01-primeiros-passos",
        "Módulo 1 — Primeiros Passos (Sobrevivência) — A1",
        "Ponto de partida absoluto: alfabeto e pronúncia, cumprimentos, apresentações, informações pessoais, números, datas e horas, países, família, cores, objetos e lugares, rotina, perguntas e respostas básicas, e o inglês essencial de sala de aula e de sobrevivência.",
        [
            topic(
                "alfabeto-e-pronuncia",
                "Alfabeto e pronúncia",
                """
# Alfabeto e pronúncia

Antes de montar qualquer frase, vale ouvir como soam as letras e alguns sons do inglês — muitos são bem diferentes do português.

## O alfabeto (26 letras)

A, B, C, D, E, F, G, H, I, J, K, L, M, N, O, P, Q, R, S, T, U, V, W, X, Y, Z

Algumas pronúncias que costumam surpreender:

| Letra | Soa como (aproximado) |
|---|---|
| **H** | "eitch" — o H é pronunciado, diferente do português |
| **J** | "djêi" |
| **R** | som mais "enrolado", puxado para trás |
| **W** | "dâbliu" |
| **Y** | "uái" |

## Soletrando (spelling)

É muito comum precisar soletrar o próprio nome em situações do dia a dia (por telefone, em cadastros, em hotéis):

```
How do you spell your name?     Como você soletra seu nome?
```

## Sons que não existem em português

Dois sons costumam ser os mais difíceis para brasileiros:

- **th** (como em `think` e `this`): a língua fica entre os dentes — não existe equivalente em português, e trocar por "f"/"t" muda o significado da palavra.
- **r final** (como em `car`, `hard`): em muitos sotaques americanos, é um som gutural único, bem diferente do "r" do português.

> 🎧 A melhor forma de treinar pronúncia é **ouvir muito** e repetir em voz alta. Clique em 🔊 para ouvir e 🎤 para tentar falar.
""",
                [
                    ex("quiz", "Quantas letras tem o alfabeto do inglês?",
                       "26", ["24", "26", "28"]),
                    ex("quiz", 'Qual letra é pronunciada "eitch" — diferente do português?',
                       "H", ["H", "W", "Y"]),
                    ex("audio", "Escute a frase e transcreva o que você ouviu:",
                       "my name is anna", audio_text="My name is Anna."),
                    ex("speak", "Repita a palavra em voz alta, prestando atenção no som de \"th\":",
                       "think", audio_text="think"),
                    ex("quiz", 'Qual som NÃO existe em português e aparece em "think" e "this"?',
                       "th", ["th", "ss", "ch"]),
                    ex("audio", "Escute e transcreva a pergunta:",
                       "how do you spell your name", audio_text="How do you spell your name?"),
                ],
            ),
            topic(
                "cumprimentos-basicos",
                "Cumprimentos básicos",
                """
# Cumprimentos básicos

## Ao chegar

- **Hi!** / **Hello!** — Oi! / Olá!
- **Good morning** — Bom dia
- **Good afternoon** — Boa tarde
- **Good evening** — Boa noite (ao chegar/encontrar alguém)

## Perguntando como a pessoa está

```
How are you?          Como você está?
I'm fine, thanks.     Estou bem, obrigado(a).
And you?              E você?
```

## Ao se despedir

- **Bye!** / **Goodbye!** — Tchau! / Adeus!
- **See you later!** — Até mais!
- **See you tomorrow!** — Até amanhã!
- **Take care!** — Se cuida!
- **Good night** — Boa noite (só ao se despedir para dormir — nunca ao chegar)

> 💡 Repare: **Good evening** cumprimenta alguém à noite quando você chega, e **Good night** só se usa para se despedir (ir dormir ou ir embora à noite) — não são a mesma coisa.
""",
                [
                    ex("quiz", "Qual cumprimento você usa ao encontrar alguém de manhã?",
                       "Good morning", ["Good morning", "Good night", "Goodbye"]),
                    ex("text", "Traduza: Bom dia.",
                       "good morning"),
                    ex("audio", "Escute e transcreva:",
                       "how are you", audio_text="How are you?"),
                    ex("speak", "Diga em voz alta:",
                       "i'm fine, thank you", audio_text="I'm fine, thank you."),
                    ex("quiz", "Qual expressão você usa para se despedir de alguém à noite, antes de dormir?",
                       "Good night", ["Good night", "Good evening", "Hello"]),
                    ex("quiz", 'Qual é a resposta mais natural para "How are you?"',
                       "I'm fine, thanks.", ["I'm fine, thanks.", "Good night.", "My name is Ana."]),
                ],
            ),
            topic(
                "apresentando-se",
                "Apresentando-se",
                """
# Apresentando-se

## Dizendo seu nome

```
My name is Ana.           Meu nome é Ana.
I'm Ana.                  Eu sou a Ana.
```

## Perguntando o nome de alguém

```
What's your name?         Qual é o seu nome?
```

## No primeiro encontro

```
Nice to meet you.         Prazer em conhecê-lo(a).
```

> 💡 "Nice to meet you" só se usa no **primeiro encontro** com alguém. Se já se conhecem, o correto é "Nice to see you" (Bom te ver).

## Dizendo de onde você é

```
I'm from Brazil.          Eu sou do Brasil.
```
""",
                [
                    ex("text", "Traduza: Meu nome é Ana.",
                       "my name is ana"),
                    ex("quiz", "Qual pergunta você usa para saber o nome de alguém?",
                       "What's your name?", ["What's your name?", "How are you?", "Where are you from?"]),
                    ex("audio", "Escute e transcreva:",
                       "nice to meet you", audio_text="Nice to meet you."),
                    ex("speak", "Diga em voz alta, se apresentando:",
                       "my name is ana", audio_text="My name is Ana."),
                    ex("quiz", '"Nice to meet you" é usado...',
                       "no primeiro encontro com alguém",
                       ["no primeiro encontro com alguém", "toda vez que você vê a pessoa", "apenas ao telefone"]),
                ],
            ),
            topic(
                "informacoes-pessoais",
                "Informações pessoais",
                """
# Informações pessoais

## Idade

```
How old are you?          Quantos anos você tem?
I am 20 years old.        Eu tenho 20 anos.
```

> ⚠️ Em inglês, idade usa o verbo **to be** ("eu sou 20 anos"), não "ter" como em português.

## Onde você mora

```
Where do you live?        Onde você mora?
I live in Brazil.         Eu moro no Brasil.
```

## Profissão (básico)

```
What do you do?           O que você faz (de profissão)?
I'm a student.             Eu sou estudante.
```
""",
                [
                    ex("text", "Traduza: Eu tenho 20 anos.",
                       "i am 20 years old"),
                    ex("quiz", "Qual pergunta você faz para saber a idade de alguém?",
                       "How old are you?", ["How old are you?", "What's your name?", "Where do you live?"]),
                    ex("quiz", 'Complete: "I ___ 20 years old."',
                       "am", ["am", "is", "are"]),
                    ex("audio", "Escute e transcreva:",
                       "where do you live", audio_text="Where do you live?"),
                    ex("text", "Traduza: Eu moro no Brasil.",
                       "i live in brazil"),
                ],
            ),
            topic(
                "numeros-em-ingles",
                "Números",
                """
# Números

## De 0 a 20

0 zero · 1 one · 2 two · 3 three · 4 four · 5 five · 6 six · 7 seven · 8 eight · 9 nine · 10 ten · 11 eleven · 12 twelve · 13 thirteen · 14 fourteen · 15 fifteen · 16 sixteen · 17 seventeen · 18 eighteen · 19 nineteen · 20 twenty

## Dezenas (20 a 100)

20 twenty · 30 thirty · 40 forty · 50 fifty · 60 sixty · 70 seventy · 80 eighty · 90 ninety · 100 one hundred

Números compostos usam hífen: `twenty-one` (21), `thirty-five` (35).

> 💡 Repare que "thirteen" a "nineteen" terminam em **-teen**, enquanto "thirty", "forty"... terminam em **-ty** — são sons parecidos, mas números bem diferentes. Preste atenção na pronúncia.
""",
                [
                    ex("quiz", "Como se escreve o número 15 em inglês?",
                       "fifteen", ["fifteen", "fifty", "fourteen"]),
                    ex("text", "Escreva por extenso, em inglês: 21",
                       "twenty-one"),
                    ex("audio", "Escute e transcreva:",
                       "i have three brothers", audio_text="I have three brothers."),
                    ex("quiz", 'Qual número vem logo depois de "nine" (9)?',
                       "ten", ["ten", "eleven", "eight"]),
                    ex("text", "Escreva por extenso, em inglês: 100",
                       "one hundred"),
                ],
            ),
            topic(
                "datas-e-horas",
                "Datas e horas",
                """
# Datas e horas

## Dias da semana

Sunday, Monday, Tuesday, Wednesday, Thursday, Friday, Saturday

## Perguntando as horas

```
What time is it?          Que horas são?
It's three o'clock.       São três horas.
```

## Marcadores de tempo básicos

- **today** — hoje
- **tomorrow** — amanhã
- **yesterday** — ontem

> 💡 Em inglês, os dias da semana e os meses **sempre** começam com letra maiúscula — diferente do português.
""",
                [
                    ex("quiz", 'Como se diz "segunda-feira" em inglês?',
                       "Monday", ["Monday", "Sunday", "Tuesday"]),
                    ex("text", "Traduza: Que horas são?",
                       "what time is it"),
                    ex("audio", "Escute e transcreva:",
                       "it's three o'clock", audio_text="It's three o'clock."),
                    ex("quiz", 'Como se diz "hoje" em inglês?',
                       "today", ["today", "tomorrow", "yesterday"]),
                    ex("text", "Traduza: Amanhã.",
                       "tomorrow"),
                    ex("speak", "Diga em voz alta:",
                       "what time is it", audio_text="What time is it?"),
                ],
            ),
            topic(
                "paises-e-nacionalidades",
                "Países e nacionalidades",
                """
# Países e nacionalidades

| País | Nacionalidade |
|---|---|
| Brazil | Brazilian |
| the United States | American |
| Portugal | Portuguese |
| England | English |

## Perguntando e respondendo de onde você é

```
Where are you from?       De onde você é?
I am from Brazil.         Eu sou do Brasil.
I am Brazilian.           Eu sou brasileiro(a).
```

> 💡 Nomes de países e de nacionalidades **sempre** começam com letra maiúscula em inglês, mesmo no meio da frase.
""",
                [
                    ex("quiz", "Qual é a nacionalidade de alguém do Brazil?",
                       "Brazilian", ["Brazilian", "American", "Portuguese"]),
                    ex("text", "Traduza: De onde você é?",
                       "where are you from"),
                    ex("audio", "Escute e transcreva:",
                       "i am from brazil", audio_text="I am from Brazil."),
                    ex("quiz", 'Qual país tem nacionalidade "American"?',
                       "the United States", ["the United States", "England", "Portugal"]),
                    ex("text", "Traduza: Eu sou brasileiro.",
                       "i am brazilian"),
                ],
            ),
            topic(
                "familia-em-ingles",
                "Família",
                """
# Família

| Inglês | Português |
|---|---|
| mother | mãe |
| father | pai |
| sister | irmã |
| brother | irmão |
| daughter | filha |
| son | filho |
| grandmother | avó |
| grandfather | avô |

## Exemplos

```
This is my mother.        Esta é minha mãe.
This is my father.        Este é meu pai.
I have two brothers.      Eu tenho dois irmãos.
```
""",
                [
                    ex("quiz", 'Como se diz "irmã" em inglês?',
                       "sister", ["sister", "brother", "mother"]),
                    ex("text", "Traduza: Este é meu pai.",
                       "this is my father"),
                    ex("audio", "Escute e transcreva:",
                       "this is my mother", audio_text="This is my mother."),
                    ex("quiz", 'Como se diz "filho" em inglês?',
                       "son", ["son", "daughter", "brother"]),
                    ex("text", "Traduza: Eu tenho dois irmãos.",
                       "i have two brothers"),
                ],
            ),
            topic(
                "cores-em-ingles",
                "Cores",
                """
# Cores

| Inglês | Português |
|---|---|
| red | vermelho |
| blue | azul |
| green | verde |
| yellow | amarelo |
| black | preto |
| white | branco |
| orange | laranja |
| purple | roxo |

## Exemplos

```
The house is red.         A casa é vermelha.
The car is black.         O carro é preto.
```
""",
                [
                    ex("quiz", 'Como se diz "azul" em inglês?',
                       "blue", ["blue", "red", "green"]),
                    ex("text", "Traduza: A casa é vermelha.",
                       "the house is red"),
                    ex("audio", "Escute e transcreva:",
                       "the car is black", audio_text="The car is black."),
                    ex("quiz", 'Como se diz "amarelo" em inglês?',
                       "yellow", ["yellow", "orange", "purple"]),
                    ex("text", "Traduza: Verde.",
                       "green"),
                ],
            ),
            topic(
                "objetos-e-lugares",
                "Objetos e lugares",
                """
# Objetos e lugares

## Objetos comuns

table (mesa) · chair (cadeira) · door (porta) · book (livro) · pen (caneta)

## Lugares comuns

school (escola) · house (casa) · store (loja) · park (parque)

## Dizendo onde algo/alguém está

```
The book is on the table.     O livro está na mesa.
Where is the school?          Onde fica a escola?
I am at home.                 Eu estou em casa.
```
""",
                [
                    ex("quiz", 'Como se diz "mesa" em inglês?',
                       "table", ["table", "chair", "door"]),
                    ex("text", "Traduza: O livro está na mesa.",
                       "the book is on the table"),
                    ex("audio", "Escute e transcreva:",
                       "where is the school", audio_text="Where is the school?"),
                    ex("quiz", 'Como se diz "escola" em inglês?',
                       "school", ["school", "store", "park"]),
                    ex("text", "Traduza: Eu estou em casa.",
                       "i am at home"),
                ],
            ),
            topic(
                "atividades-diarias",
                "Atividades diárias",
                """
# Atividades diárias

## Verbos comuns da rotina

wake up (acordar) · eat (comer) · work (trabalhar) · sleep (dormir) · go (ir)

## Exemplos (presente simples)

```
I wake up at 7 am.            Eu acordo às 7h.
I eat breakfast at 7.         Eu como café da manhã às 7h.
I go to work every day.       Eu vou trabalhar todos os dias.
She works every day.          Ela trabalha todos os dias.
```

> 💡 Com **he/she/it**, o verbo ganha um -s no final: `work -> works`.
""",
                [
                    ex("quiz", 'Complete: "I ___ up at 7 am." (acordar)',
                       "wake", ["wake", "wakes", "waking"]),
                    ex("text", "Traduza: Eu como café da manhã às 7.",
                       "i eat breakfast at 7"),
                    ex("audio", "Escute e transcreva:",
                       "i go to work every day", audio_text="I go to work every day."),
                    ex("quiz", 'Como se diz "dormir" em inglês?',
                       "sleep", ["sleep", "wake", "eat"]),
                    ex("text", "Traduza: Ela trabalha todos os dias.",
                       "she works every day"),
                ],
            ),
            topic(
                "perguntas-basicas",
                "Perguntas básicas",
                """
# Perguntas básicas (question words)

| Palavra | Português |
|---|---|
| What | O quê |
| Who | Quem |
| Where | Onde |
| When | Quando |
| Why | Por quê |
| How | Como |

## Exemplos

```
What is this?              O que é isso?
Who is that?                Quem é aquele(a)?
How are you?                Como você está?
```
""",
                [
                    ex("quiz", 'Qual palavra você usa para perguntar "onde"?',
                       "Where", ["Where", "What", "When"]),
                    ex("text", "Traduza: O que é isso?",
                       "what is this"),
                    ex("audio", "Escute e transcreva:",
                       "who is that", audio_text="Who is that?"),
                    ex("quiz", "Qual palavra você usa para perguntar o motivo (por quê)?",
                       "Why", ["Why", "How", "Who"]),
                    ex("text", "Traduza: Como você está?",
                       "how are you"),
                ],
            ),
            topic(
                "respostas-basicas",
                "Respostas básicas",
                """
# Respostas básicas

- **please** — por favor
- **thank you** / **thanks** — obrigado(a)
- **sorry** — desculpe
- **excuse me** — com licença (para chamar atenção educadamente)
- **I don't know** — eu não sei

## Exemplos

```
Excuse me, where is the bathroom?     Com licença, onde fica o banheiro?
I don't know.                          Eu não sei.
```
""",
                [
                    ex("quiz", 'Como se diz "por favor" em inglês?',
                       "please", ["please", "sorry", "thanks"]),
                    ex("text", "Traduza: Obrigado.",
                       "thank you"),
                    ex("audio", "Escute e transcreva:",
                       "i don't know", audio_text="I don't know."),
                    ex("quiz", 'Como se diz "com licença" (para chamar atenção educadamente)?',
                       "excuse me", ["excuse me", "sorry", "please"]),
                    ex("text", "Traduza: Desculpe.",
                       "sorry"),
                ],
            ),
            topic(
                "ingles-de-sala-de-aula",
                "Inglês de sala de aula",
                """
# Inglês de sala de aula

Expressões úteis para usar durante qualquer aula ou estudo de inglês:

```
I don't understand.                Eu não entendo.
Can you repeat, please?            Você pode repetir, por favor?
How do you say this in English?    Como se diz isso em inglês?
Can you help me?                   Você pode me ajudar?
```

> 💡 São frases curtas, mas extremamente úteis — vale decorá-las cedo, porque você vai usá-las sempre que travar durante o estudo.
""",
                [
                    ex("text", "Traduza: Eu não entendo.",
                       "i don't understand"),
                    ex("quiz", "Como você pede para o professor repetir, educadamente?",
                       "Can you repeat, please?",
                       ["Can you repeat, please?", "I don't understand.", "Excuse me."]),
                    ex("audio", "Escute e transcreva:",
                       "how do you say this in english", audio_text="How do you say this in English?"),
                    ex("quiz", '"I don\'t understand" significa, em português:',
                       "Eu não entendo", ["Eu não entendo", "Eu não sei", "Por favor, repita"]),
                    ex("text", "Traduza: Você pode me ajudar?",
                       "can you help me"),
                ],
            ),
            topic(
                "ingles-de-sobrevivencia",
                "Inglês de sobrevivência",
                """
# Inglês de sobrevivência

Frases essenciais para situações do dia a dia, como pedir ajuda ou fazer compras:

```
Help!                       Socorro!
Where is the bathroom?      Onde fica o banheiro?
How much is this?           Quanto custa isso?
I need help.                Eu preciso de ajuda.
```

> 🎯 Você não precisa de gramática avançada para sobreviver em inglês no dia a dia — frases curtas e diretas como essas resolvem a maioria das situações.
""",
                [
                    ex("quiz", "Como pedir socorro em uma emergência?",
                       "Help!", ["Help!", "Sorry!", "Please!"]),
                    ex("text", "Traduza: Onde fica o banheiro?",
                       "where is the bathroom"),
                    ex("audio", "Escute e transcreva:",
                       "how much is this", audio_text="How much is this?"),
                    ex("quiz", 'Como se diz "Eu preciso de ajuda" em inglês?',
                       "I need help.", ["I need help.", "I need water.", "I need money."]),
                    ex("text", "Traduza: Chame a polícia!",
                       "call the police"),
                ],
            ),
        ],
    )


# ============================================================
# MODULO 2 - Gramatica Essencial - A1
# ============================================================

@_expand_target_builder
def build_modulo_02_gramatica_essencial_a1():
    return module(
        "modulo-02-gramatica-essencial-a1",
        "Módulo 2 — Gramática Essencial — A1",
        "A base do sistema do inglês, explicada em português: pronomes, verbo to be, possessivos, artigos, plural, demonstrativos, there is/are, have/have got, presente simples, advérbios de frequência, imperativo, can/can't, preposições, question words e a ordem das palavras na frase.",
        [
            topic(
                "pronomes-pessoais",
                "Pronomes pessoais",
                """
# Pronomes pessoais (subject pronouns)

Os pronomes pessoais em inglês aparecem como **sujeito** da frase. São poucos
e não mudam conforme a pessoa — são o "quem" da ação.

| Pronome | Português |
|---|---|
| **I** | eu |
| **you** | você / vocês |
| **he** | ele |
| **she** | ela |
| **it** | ele/ela (coisas, animais, objetos) |
| **we** | nós |
| **they** | eles / elas / vocês |

## Regras que ajudam

- **I** (eu) sempre com letra maiúscula, mesmo no meio da frase.
- **he** e **she** são só para pessoas; para coisas e animais usa-se **it**.
- **you** serve tanto para "você" (singular) quanto para "vocês" (plural).

## Substituindo nomes por pronomes

```
Maria is my friend.  ->  She is my friend.
My friends and I are students.  ->  We are students.
The dog is big.  ->  It is big.
```

> 💡 Pergunte sempre: "qual pronome substitui esse nome?" — ela/ele = she/he;
> nós = we; eles/elas = they; objeto/animal = it.
""",
                [
                    ex("quiz", 'Qual pronome completa a frase "___ am a student." (eu)?',
                       "I", ["I", "You", "She"]),
                    ex("quiz", "Qual pronome substitui 'Maria' (ela)?",
                       "She", ["She", "He", "It"]),
                    ex("quiz", "Qual pronome substitui 'the dog' (animal)?",
                       "It", ["It", "He", "She"]),
                    ex("text", "Qual pronome significa 'nós' em inglês?",
                       "we"),
                    ex("text", "Qual pronome significa 'eles/elas' em inglês?",
                       "they"),
                    ex("quiz", "Para falar de você e seus amigos juntos ('eu + eles'), qual pronome usar?",
                       "We", ["We", "They", "You"]),
                ],
            ),
            topic(
                "verbo-to-be",
                "Verbo To Be (ser/estar)",
                """
# Verbo To Be (ser/estar)

O verbo **to be** (= ser ou estar) é o mais importante do inglês. Ele muda de
forma conforme a pessoa:

| Pessoa | Afirmativo | Forma contraída |
|---|---|---|
| I | I am | I'm |
| you | you are | you're |
| he / she / it | he is | he's |
| we | we are | we're |
| they | they are | they're |

## Forma negativa

Acrescente **not** depois do verbo:

```
I am not tired.     (eu não estou cansado)
She is not here.    (ela não está aqui)  ->  She isn't here.
They are not at home.  ->  They aren't at home.
```

## Forma interrogativa

O verbo vai **antes** do sujeito:

```
Are you a student?      Você é estudante?
Is she your sister?     Ela é sua irmã?
```

> 💡 Regra de ouro: **am** só com I, **is** com he/she/it (singular), **are**
> com you/we/they (plural).
""",
                [
                    ex("quiz", 'Complete: "She ___ my sister."',
                       "is", ["is", "are", "am"]),
                    ex("quiz", 'Complete: "They ___ from Brazil."',
                       "are", ["are", "is", "am"]),
                    ex("text", "Traduza: Nós não estamos em casa.",
                       "we are not at home"),
                    ex("quiz", 'Complete a pergunta: "___ you a student?"',
                       "Are", ["Are", "Is", "Am"]),
                    ex("audio", "Escute e transcreva:",
                       "she isn't from england", audio_text="She isn't from England."),
                    ex("quiz", 'Complete a pergunta: "Is ___ your brother?" (ele)',
                       "he", ["he", "him", "his"]),
                ],
            ),
            topic(
                "adjetivos-possessivos",
                "Adjetivos possessivos",
                """
# Adjetivos possessivos

Os **adjetivos possessivos** indicam de quem é algo. Vêm sempre **antes** do
substantivo.

| Pessoa | Possessivo | Português |
|---|---|---|
| I | my | meu / minha |
| you | your | seu / sua (de você) |
| he | his | dele |
| she | her | dela |
| it | its | dele/dela (coisa, animal) |
| we | our | nosso / nossa |
| they | their | deles / delas |

## Exemplos

```
My name is Ana.           Meu nome é Ana.
Her house is big.         A casa dela é grande.
Our school is near.       Nossa escola é perto.
```

> 💡 O possessivo concorda com o **dono**, não com o objeto: para falar do
> livro de uma mulher, é sempre **her book** — não importa se o livro é
> masculino ou feminino (diferente do português).
""",
                [
                    ex("quiz", 'Complete: "___ name is Ana." (meu/minha)',
                       "My", ["My", "Your", "His"]),
                    ex("quiz", 'Complete: "This is ___ book." (dele)',
                       "his", ["his", "her", "its"]),
                    ex("text", "Traduza: A casa deles.",
                       "their house"),
                    ex("audio", "Escute e transcreva:",
                       "her name is maria", audio_text="Her name is Maria."),
                    ex("quiz", 'Complete: "We love ___ school." (nosso/nossa)',
                       "our", ["our", "their", "your"]),
                    ex("text", "Traduza: Meu carro.",
                       "my car"),
                ],
            ),
            topic(
                "artigos-a-an-the",
                "Artigos (a, an, the)",
                """
# Artigos (a, an, the)

## a / an — "um / uma" (indefinidos)

Usamos **a** ou **an** antes de substantivos no singular quando falamos de
algo em geral, sem especificar qual.

- **a** antes de som de consoante: `a book`, `a car`.
- **an** antes de **som de vogal**: `an apple`, `an egg`, `an hour`.

> ⚠️ O que importa é o **som**, não a letra: dizemos **a university** (o "u"
> soa como "yu") e **an hour** (o "h" é mudo).

## the — "o/a" (definido)

Usamos **the** quando a pessoa já sabe **de qual** estamos falando (algo
específico, já mencionado ou único):

```
I have a car. The car is red.
```

> 💡 Não use artigo antes de idiomas, refeições e a maioria dos nomes de
> países: `I speak Portuguese.`, não "the Portuguese".
""",
                [
                    ex("quiz", 'Complete: "___ apple" (uma)',
                       "an", ["an", "a", "the"]),
                    ex("quiz", 'Complete: "___ book" (um)',
                       "a", ["a", "an", "the"]),
                    ex("text", "Escreva o artigo correto ('a' ou 'an') antes de 'egg'.",
                       "an"),
                    ex("quiz", "Qual artigo usamos quando falamos de algo específico que já conhecemos?",
                       "the", ["the", "a", "an"]),
                    ex("audio", "Escute e transcreva:",
                       "the house is big", audio_text="The house is big."),
                    ex("quiz", 'Complete: "___ hour" (o "h" é mudo, soa como vogal)',
                       "an", ["an", "a", "the"]),
                ],
            ),
            topic(
                "singular-e-plural",
                "Singular e plural",
                """
# Singular e plural

O plural em inglês é, na maioria das vezes, só acrescentar **-s**.

## Regras principais

| Terminação | Plural | Exemplos |
|---|---|---|
| consoante | + **s** | book -> books, cat -> cats |
| s, sh, ch, x, o | + **es** | bus -> buses, box -> boxes |
| consoante + y | troca y por **ies** | baby -> babies, city -> cities |
| vogal + y | + **s** | boy -> boys, day -> days |

## Plurais irregulares (decorar)

```
man -> men       child -> children
woman -> women   foot -> feet
person -> people tooth -> teeth
```

## Uso com números

Com plural usamos números e **no article** a/an:

```
one book, two books
a cat, three cats
```

> 💡 Depois de números maiores que um, o substantivo vai sempre para o plural:
> `five students`, nunca "five student".
""",
                [
                    ex("quiz", 'Qual é o plural de "cat"?',
                       "cats", ["cats", "cates", "caties"]),
                    ex("quiz", 'Qual é o plural de "bus"?',
                       "buses", ["buses", "busis", "busses"]),
                    ex("quiz", 'Qual é o plural de "child"?',
                       "children", ["children", "childs", "childes"]),
                    ex("text", "Escreva o plural de 'baby'.",
                       "babies"),
                    ex("audio", "Escute e transcreva:",
                       "two cats and a dog", audio_text="Two cats and a dog."),
                    ex("quiz", 'Qual é o plural de "man"?',
                       "men", ["men", "mans", "menes"]),
                ],
            ),
            topic(
                "demonstrativos",
                "Demonstrativos (this/that/these/those)",
                """
# Demonstrativos (this / that / these / those)

Os demonstrativos apontam para coisas, indicando se estão **perto** ou
**longe**, e se são singular ou plural.

| | Singular | Plural |
|---|---|---|
| **Perto** | this (este/esta) | these (estes/estas) |
| **Longe** | that (aquele/aquela) | those (aqueles/aquelas) |

## Exemplos

```
This is my phone.        Este é meu celular.   (perto, singular)
These are my keys.       Estas são minhas chaves.  (perto, plural)
That is your car.        Aquele é seu carro.   (longe, singular)
Those are our books.     Aqueles são nossos livros.  (longe, plural)
```

## Dica de memória

- **this / these** têm "t" duplo e são os de **perto** (como o "este").
- **that / those** têm "t" + "h/a/o/u" e são os de **longe**.
- Singular (this/that) com o verbo **is**; plural (these/those) com **are**.

> 💡 Use **this** para apresentar algo na mão e **that** para apontar algo
> distante: `This is my book.` vs `That is your book.`
""",
                [
                    ex("quiz", "Qual demonstrativo usamos para algo PERTO e no singular?",
                       "this", ["this", "these", "that"]),
                    ex("quiz", "Qual demonstrativo usamos para algo LONGE e no plural?",
                       "those", ["those", "these", "that"]),
                    ex("text", 'Complete: "___ are my books." (estes, perto)',
                       "these"),
                    ex("audio", "Escute e transcreva:",
                       "this is my phone", audio_text="This is my phone."),
                    ex("quiz", "Olhe para um pássaro LÁ LONGE. Qual frase você diz?",
                       "Look at that bird!", ["Look at that bird!", "Look at this bird!", "Look at these bird!"]),
                    ex("text", "Traduza: Essas são minhas chaves.",
                       "these are my keys"),
                ],
            ),
            topic(
                "there-is-there-are",
                "There is / There are (há)",
                """
# There is / There are (há)

Para dizer que **algo existe em algum lugar**, usamos *there is* (singular)
e *there are* (plural). Em português, os dois viram "há" ou "tem".

## Afirmativo

```
There is a book on the table.        Há um livro na mesa.
There are two windows in the room.   Há duas janelas no quarto.
```

## Negativo

```
There isn't a bank near here.   Não há um banco perto daqui.
There aren't any parks here.    Não há parques aqui.
```

## Interrogativo

```
Is there a bathroom?     Há um banheiro?
Are there any problems?  Há algum problema?
```

> 💡 Regra: **is** + singular, **are** + plural. O "there" não muda — quem
> muda é o verbo, de acordo com o que vem depois.
""",
                [
                    ex("quiz", 'Complete: "___ a book on the table." (há, singular)',
                       "There is", ["There is", "There are", "There am"]),
                    ex("quiz", 'Complete: "___ two windows in the room." (há, plural)',
                       "There are", ["There are", "There is", "There am"]),
                    ex("text", "Traduza: Há um gato no jardim.",
                       "there is a cat in the garden"),
                    ex("quiz", "Qual é a forma negativa de 'There is'?",
                       "There isn't", ["There isn't", "There aren't", "There not is"]),
                    ex("audio", "Escute e transcreva:",
                       "there are three students", audio_text="There are three students."),
                    ex("quiz", 'Complete a pergunta: "___ there a bank near here?"',
                       "Is", ["Is", "Are", "Do"]),
                ],
            ),
            topic(
                "have-have-got",
                "Have / Have got (ter)",
                """
# Have / Have got (ter)

O verbo **have** significa "ter". Com he/she/it vira **has**.

## Afirmativo

```
I have a car.          Eu tenho um carro.
She has a brother.     Ela tem um irmão.
```

Existe também a forma **have got / has got**, comum em algumas variedades do inglês, especialmente no inglês britânico:

```
I have got a car.   ->  I've got a car.
She has got a bike. ->  She's got a bike.
```

## Negativo (com have)

```
I don't have a car.      Eu não tenho um carro.
She doesn't have a car.  Ela não tem um carro.
```

## Interrogativo (com have)

```
Do you have a car?        Você tem um carro?
Does she have a car?      Ela tem um carro?
Have you got a pen?       Você tem uma caneta?
```

> 💡 Com **have got**, a negativa é **haven't got** e a pergunta inverte
> ("Have you got...?"). Com **have**, usamos **don't/doesn't have** e **Do/
> Does ... have**.
""",
                [
                    ex("quiz", 'Complete: "She ___ a car." (tem)',
                       "has", ["has", "have", "haves"]),
                    ex("quiz", 'Complete: "I ___ two brothers." (tenho)',
                       "have", ["have", "has", "had"]),
                    ex("text", "Traduza: Eu tenho um irmão.",
                       "i have a brother"),
                    ex("quiz", "Qual é a forma contraída de 'I have got'?",
                       "I've got", ["I've got", "I has got", "I have gots"]),
                    ex("audio", "Escute e transcreva:",
                       "have you got a pen", audio_text="Have you got a pen?"),
                    ex("quiz", 'Complete a negativa: "I ___ a car." (não tenho)',
                       "don't have", ["don't have", "doesn't have", "not have"]),
                ],
            ),
            topic(
                "presente-simples",
                "Presente Simples",
                """
# Presente Simples

O **presente simples** descreve rotinas, hábitos e fatos. Ele só muda na
terceira pessoa (he/she/it), que ganha **-s** no verbo.

## Afirmativo

```
I go to school every day.     Eu vou à escola todos os dias.
She goes to school.           Ela vai à escola.   (go -> goes)
He drinks coffee.             Ele bebe café.      (drink -> drinks)
```

> ⚠️ Cuidado com o -s da 3ª pessoa: he/she/it + verbo-s. Esse é o erro mais
> comum de quem está começando.

## Negativo

Use **don't** (I/you/we/they) ou **doesn't** (he/she/it). O verbo volta ao
normal (sem -s):

```
I don't like coffee.        Eu não gosto de café.
She doesn't eat meat.       Ela não come carne.
```

## Interrogativo

Use **Do** ou **Does** no começo. O verbo fica na forma base:

```
Do you speak English?       Você fala inglês?
Does he live here?          Ele mora aqui?
```

> 💡 **Does** já carrega o -s, então o verbo vem sem: "Does he lives?" está
> errado — o certo é "Does he live?".
""",
                [
                    ex("quiz", 'Complete: "He ___ coffee." (drinks)',
                       "drinks", ["drinks", "drink", "drinking"]),
                    ex("quiz", 'Complete: "I ___ to school every day." (go)',
                       "go", ["go", "goes", "going"]),
                    ex("text", "Escreva a forma negativa completa: 'They ___ (work) on Sundays.'",
                       "don't work"),
                    ex("quiz", 'Complete a pergunta: "___ you speak English?"',
                       "Do", ["Do", "Does", "Are"]),
                    ex("audio", "Escute e transcreva:",
                       "she doesn't eat meat", audio_text="She doesn't eat meat."),
                    ex("quiz", 'Complete: "Does he ___ in São Paulo?" (viver)',
                       "live", ["live", "lives", "living"]),
                ],
            ),
            topic(
                "adverbios-de-frequencia",
                "Advérbios de frequência",
                """
# Advérbios de frequência

Os **advérbios de frequência** dizem **com que frequência** algo acontece.

| Advérbio | Significado |
|---|---|
| always | sempre |
| usually | geralmente |
| often | frequentemente |
| sometimes | às vezes |
| rarely | raramente |
| never | nunca |

## Posição na frase

Com o **verbo comum**, eles ficam **antes** do verbo:

```
She always drinks tea.      Ela sempre toma chá.
They never eat out.         Eles nunca comem fora.
I sometimes watch TV.       Eu às vezes assisto TV.
```

Com o verbo **to be**, ficam **depois**:

```
He is always on time.       Ele está sempre na hora.
```

## Ordem de frequência

```
always  >  usually  >  often  >  sometimes  >  rarely  >  never
```

> 💡 Na pergunta "com que frequência?", usa-se **How often...?**:
> `How often do you exercise?` — "Com que frequência você se exercita?"
""",
                [
                    ex("quiz", "Qual advérbio significa 'nunca'?",
                       "never", ["never", "always", "sometimes"]),
                    ex("quiz", "Qual advérbio significa 'sempre'?",
                       "always", ["always", "never", "usually"]),
                    ex("quiz", "Em 'She always drinks tea', onde fica o advérbio 'always'?",
                       "antes do verbo 'drinks'", ["antes do verbo 'drinks'", "depois do verbo 'drinks'", "no final da frase"]),
                    ex("text", 'Complete: "I ___ get up at 6." (sempre)',
                       "always"),
                    ex("audio", "Escute e transcreva:",
                       "they never eat out", audio_text="They never eat out."),
                    ex("quiz", "Qual advérbio expressa 'às vezes'?",
                       "sometimes", ["sometimes", "rarely", "always"]),
                ],
            ),
            topic(
                "imperativo",
                "Imperativo (ordens e pedidos)",
                """
# Imperativo (ordens e pedidos)

O **imperativo** é a forma do verbo para dar ordens, fazer pedidos e dar
instruções. Usa a forma base do verbo, sem sujeito.

## Afirmativo

```
Open the door.            Abra a porta.
Please sit down.          Sente-se, por favor.
Listen to me.             Escute-me.
```

## Negativo: Don't

Para dizer "não faça isso", coloque **Don't** na frente:

```
Don't close the door.     Não feche a porta.
Don't worry.              Não se preocupe.
```

## Sugestões: Let's

Para sugerir fazermos algo juntos, use **Let's** (= vamos):

```
Let's go to the park.     Vamos ao parque.
Let's eat.                Vamos comer.
```

> 💡 Para ser educado, junte com **please**: "Close the door, please." ou
> "Please, close the door."
""",
                [
                    ex("quiz", "Qual dessas frases é um imperativo (uma ordem)?",
                       "Open the door.", ["Open the door.", "I open the door.", "I'm opening the door."]),
                    ex("text", "Traduza: Feche a janela, por favor.",
                       "close the window please"),
                    ex("quiz", "Qual é a forma negativa de 'Close the door'?",
                       "Don't close the door", ["Don't close the door", "No close the door", "Not close the door"]),
                    ex("audio", "Escute e transcreva:",
                       "please sit down", audio_text="Please sit down."),
                    ex("quiz", "O que 'Let's go!' expressa?",
                       "uma sugestão (vamos)", ["uma sugestão (vamos)", "uma ordem", "uma pergunta"]),
                    ex("speak", "Diga em voz alta:",
                       "don't worry", audio_text="Don't worry."),
                ],
            ),
            topic(
                "can-cant",
                "Can / Can't (habilidade e permissão)",
                """
# Can / Can't (habilidade e permissão)

O verbo **can** expressa **habilidade** (saber fazer) e **permissão** (poder
fazer). É igual para todas as pessoas — não muda nunca.

## Afirmativo

```
I can swim.                Eu sei nadar.
She can play the guitar.   Ela sabe tocar violão.
```

## Negativo: can't

```
I can't drive.             Eu não sei dirigir.
He can't speak French.     Ele não fala francês.
```

## Interrogativo

```
Can you help me?           Você pode me ajudar?
Can he swim?               Ele sabe nadar?
```

## Regras

- Depois de **can** / **can't**, o verbo fica na **forma base** (sem -s):
  `She can swim.`, nunca "She can swims."
- As respostas curtas são **Yes, I can.** / **No, I can't.**

> 💡 Como **can** já carrega a conjugação, não precisa de do/does nas
> perguntas: "Can you...?" — nunca "Do you can...?"
""",
                [
                    ex("quiz", 'Complete: "I ___ swim." (sei/posso nadar)',
                       "can", ["can", "cans", "can to"]),
                    ex("quiz", 'Complete: "She ___ drive." (não sabe dirigir)',
                       "can't", ["can't", "cann't", "don't can"]),
                    ex("text", "Traduza: Você pode me ajudar?",
                       "can you help me"),
                    ex("quiz", 'Complete a pergunta: "___ you play the guitar?"',
                       "Can", ["Can", "Do", "Are"]),
                    ex("audio", "Escute e transcreva:",
                       "he can't speak french", audio_text="He can't speak French."),
                    ex("quiz", "Depois de 'can', o verbo fica:",
                       "na forma base (sem -s)", ["na forma base (sem -s)", "com -s", "no gerúndio"]),
                ],
            ),
            topic(
                "preposicoes-basicas",
                "Preposições básicas",
                """
# Preposições básicas

As preposições ligam ideias e indicam **lugar** ou **tempo**. As mais comuns
no A1 são:

## Lugar

```
in     dentro de  ->  The keys are in my bag.   As chaves estão na bolsa.
on     em cima de ->  The book is on the table. O livro está na mesa.
under  embaixo de ->  The cat is under the bed. O gato está embaixo da cama.
next to  ao lado de ->  The bank is next to the store.
between  entre    ->  The park is between the school and the store.
```

## Tempo

```
at    em horários  ->  I wake up at 7 am.    Eu acordo às 7h.
in    em meses, anos, partes do dia  ->  in the morning, in 2026
on    em dias       ->  on Monday
```

## Cidades e lugares

- **in** + cidade/pais: `She lives in São Paulo.`
- **at** + ponto específico: `I'm at home.`, `We're at the store.`

> 💡 Dica rápida: **on** = superfície, **in** = dentro, **at** = ponto
> específico. Para tempo: **at** horas, **on** dias, **in** meses/anos.
""",
                [
                    ex("quiz", 'Complete: "The keys are ___ the table." (em cima de)',
                       "on", ["on", "in", "at"]),
                    ex("quiz", 'Complete: "She lives ___ São Paulo." (em, cidade)',
                       "in", ["in", "on", "at"]),
                    ex("text", "Traduza: O livro está embaixo da cadeira.",
                       "the book is under the chair"),
                    ex("quiz", 'Complete: "I wake up ___ 7 am." (às)',
                       "at", ["at", "in", "on"]),
                    ex("audio", "Escute e transcreva:",
                       "the cat is under the bed", audio_text="The cat is under the bed."),
                    ex("quiz", "Qual preposição indica 'ao lado de'?",
                       "next to", ["next to", "under", "between"]),
                ],
            ),
            topic(
                "question-words",
                "Palavras interrogativas (question words)",
                """
# Palavras interrogativas (question words)

As **question words** iniciam as perguntas e determinam **o que** se pergunta.
Vêm sempre no **começo** da frase.

| Palavra | Pergunta sobre | Exemplo |
|---|---|---|
| **What** | coisa, informação | What is your name? |
| **Who** | pessoa | Who is that man? |
| **Where** | lugar | Where are you from? |
| **When** | tempo | When is the party? |
| **Why** | motivo | Why are you sad? |
| **How** | maneira | How are you? |
| **Which** | escolha | Which one do you want? |

## Combinações com How

```
How old...?   idade   ->  How old are you?
How much...?  preço   ->  How much is this?
How many...?  quantidade ->  How many brothers do you have?
```

## Resposta direta

```
Where is the school?  ->  It's near the park.
Why are you late?     ->  Because the bus was late.
```

> 💡 Para escolher entre opções, use **which**: "Which color do you like?" —
> se a resposta é "sim ou não", aí não há question word, é só "Do you...?"
""",
                [
                    ex("quiz", "Qual question word pergunta 'quando'?",
                       "When", ["When", "Where", "What"]),
                    ex("quiz", "Qual question word pergunta o lugar (onde)?",
                       "Where", ["Where", "When", "Who"]),
                    ex("text", 'Complete: "___ is your name?" (o quê/qual)',
                       "what"),
                    ex("quiz", "Qual question word pergunta o motivo (por quê)?",
                       "Why", ["Why", "How", "Which"]),
                    ex("audio", "Escute e transcreva:",
                       "how old is your brother", audio_text="How old is your brother?"),
                    ex("quiz", "Qual question word pergunta a maneira (como)?",
                       "How", ["How", "Why", "Who"]),
                ],
            ),
            topic(
                "estrutura-basica-da-frase",
                "Estrutura básica da frase",
                """
# Estrutura básica da frase

A ordem das palavras em inglês é mais rígida que em português. A fórmula
básica da frase **afirmativa** é:

```
Sujeito  +  Verbo  +  Objeto
```

```
She   speaks   English.      Ela fala inglês.
They  study    every day.    Eles estudam todos os dias.
```

## Frase negativa

O negador entra entre o sujeito e o verbo (ou depois do verbo to be):

```
I don't like coffee.
She is not a teacher.
```

## Frase interrogativa

Nas perguntas, o auxiliar (ou o verbo to be) vai **antes** do sujeito:

```
Do you speak English?
Are you a student?
Is she at home?
```

## Resumo das ordens

| Tipo | Ordem |
|---|---|
| Afirmativa | Sujeito + Verbo + Objeto |
| Negativa | Sujeito + auxiliar/not + Verbo + Objeto |
| Interrogativa | Auxiliar/Verbo + Sujeito + Verbo + Objeto |

> 💡 Em inglês não se "inventa" ordem: cada tipo de frase tem seu lugar certo
> para cada palavra. Quando montar uma frase, pense sempre em qual dos três
> modelos acima ela se encaixa.
""",
                [
                    ex("quiz", "Qual é a ordem básica de uma frase afirmativa em inglês?",
                       "Sujeito + Verbo + Objeto", ["Sujeito + Verbo + Objeto", "Verbo + Sujeito + Objeto", "Objeto + Sujeito + Verbo"]),
                    ex("quiz", "Qual dessas frases está na ordem correta?",
                       "She speaks English.", ["She speaks English.", "Speaks she English.", "She English speaks."]),
                    ex("text", "Ordene as palavras para formar a frase: 'I / English / study'.",
                       "i study english"),
                    ex("quiz", "Em uma pergunta com 'do', a ordem é:",
                       "Do + sujeito + verbo", ["Do + sujeito + verbo", "sujeito + verbo + do", "verbo + do + sujeito"]),
                    ex("audio", "Escute e transcreva:",
                       "we study every day", audio_text="We study every day."),
                    ex("quiz", "Qual dessas é uma frase afirmativa correta?",
                       "She is a teacher.", ["She is a teacher.", "She a teacher is.", "Is she a teacher."]),
                ],
            ),
        ],
    )


# ============================================================
# MODULO 3 - Vocabulario Basico - A1
# ============================================================

@_expand_target_builder
def build_modulo_03_vocabulario_basico():
    return module(
        "modulo-03-vocabulario-basico",
        "Módulo 3 — Vocabulário Básico — A1",
        "As palavras do dia a dia para começar a se virar: família, casa, comida, roupas, escola, trabalho, transporte, clima, hobbies, compras, lugares, corpo, e os verbos, adjetivos e expressões mais comuns.",
        [
            topic(
                "membros-da-familia",
                "Membros da família",
                """
# Membros da família

Você já viu a família mais próxima no Módulo 1. Aqui ampliamos para a família
estendida.

| Inglês | Português |
|---|---|
| uncle | tio |
| aunt | tia |
| cousin | primo / prima |
| nephew | sobrinho |
| niece | sobrinha |
| husband | marido |
| wife | esposa |

## Exemplos

```
My uncle lives here.        Meu tio mora aqui.
Her cousin is a doctor.     O primo dela é médico.
```

> 💡 **uncle** e **aunt** não variam para "tio materno/paterno" — em inglês é
> uma palavra só para os dois lados da família.
""",
                [
                    ex("quiz", "Como se diz 'tio' em inglês?",
                       "uncle", ["uncle", "aunt", "cousin"]),
                    ex("quiz", "Como se diz 'primo/prima' em inglês?",
                       "cousin", ["cousin", "nephew", "niece"]),
                    ex("quiz", "Como se diz 'sobrinho' em inglês?",
                       "nephew", ["nephew", "niece", "cousin"]),
                    ex("text", "Traduza: Minha avó.",
                       "my grandmother"),
                    ex("audio", "Escute e transcreva:",
                       "my uncle lives here", audio_text="My uncle lives here."),
                    ex("text", "Traduza: Minha prima é médica.",
                       "my cousin is a doctor"),
                ],
            ),
            topic(
                "partes-da-casa",
                "Partes da casa",
                """
# Partes da casa

## Cômodos

| Inglês | Português |
|---|---|
| bedroom | quarto |
| bathroom | banheiro |
| kitchen | cozinha |
| living room | sala de estar |
| dining room | sala de jantar |
| garden | jardim |
| garage | garagem |

## Exemplos

```
The bathroom is small.        O banheiro é pequeno.
We eat in the kitchen.        Nós comemos na cozinha.
```

> 💡 **room** = quarto/sala (cômodo). Junte com o uso: **bed** (cama) +
> room = quarto; **bath** (banho) + room = banheiro.
""",
                [
                    ex("quiz", "Como se diz 'cozinha' em inglês?",
                       "kitchen", ["kitchen", "bathroom", "bedroom"]),
                    ex("quiz", "Como se diz 'banheiro' em inglês?",
                       "bathroom", ["bathroom", "bedroom", "kitchen"]),
                    ex("text", "Traduza: A sala de estar.",
                       "the living room"),
                    ex("quiz", "Qual cômodo é o 'bedroom'?",
                       "quarto", ["quarto", "cozinha", "sala de jantar"]),
                    ex("audio", "Escute e transcreva:",
                       "the bathroom is small", audio_text="The bathroom is small."),
                    ex("text", "Traduza: O jardim é grande.",
                       "the garden is big"),
                ],
            ),
            topic(
                "alimentos-e-bebidas",
                "Alimentos e bebidas",
                """
# Alimentos e bebidas

## Comida

| Inglês | Português |
|---|---|
| bread | pão |
| rice | arroz |
| meat | carne |
| chicken | frango |
| fish | peixe |
| fruit | fruta |
| apple | maçã |
| banana | banana |

## Bebida

| Inglês | Português |
|---|---|
| water | água |
| milk | leite |
| juice | suco |
| coffee | café |
| tea | chá |

## Exemplos

```
I drink milk every day.      Eu tomo leite todos os dias.
I like coffee.               Eu gosto de café.
```

> 💡 **drink** é tanto o verbo "beber" quanto o substantivo "bebida".
""",
                [
                    ex("quiz", "Como se diz 'pão' em inglês?",
                       "bread", ["bread", "rice", "meat"]),
                    ex("quiz", "Como se diz 'água' em inglês?",
                       "water", ["water", "milk", "juice"]),
                    ex("text", "Traduza: Eu gosto de café.",
                       "i like coffee"),
                    ex("quiz", "Como se diz 'arroz' em inglês?",
                       "rice", ["rice", "bread", "fish"]),
                    ex("audio", "Escute e transcreva:",
                       "i drink milk every day", audio_text="I drink milk every day."),
                    ex("quiz", "Qual é a fruta 'apple'?",
                       "maçã", ["maçã", "banana", "laranja"]),
                ],
            ),
            topic(
                "roupas-em-ingles",
                "Roupas",
                """
# Roupas

| Inglês | Português |
|---|---|
| shirt | camisa |
| pants | calça |
| dress | vestido |
| skirt | saia |
| shoes | sapatos |
| socks | meias |
| hat | chapéu |
| jacket | jaqueta |
| coat | casaco |

## Exemplos

```
Her dress is red.         O vestido dela é vermelho.
I need new shoes.         Eu preciso de sapatos novos.
```

> 💡 **pants** é "calça" — sempre no plural, como em português. **shoes** e
> **socks** também costumam aparecer no plural (são aos pares).
""",
                [
                    ex("quiz", "Como se diz 'camisa' em inglês?",
                       "shirt", ["shirt", "skirt", "dress"]),
                    ex("quiz", "Como se diz 'sapatos' em inglês?",
                       "shoes", ["shoes", "socks", "hat"]),
                    ex("text", "Traduza: O vestido é bonito.",
                       "the dress is beautiful"),
                    ex("quiz", "Como se diz 'chapéu' em inglês?",
                       "hat", ["hat", "coat", "jacket"]),
                    ex("audio", "Escute e transcreva:",
                       "her dress is red", audio_text="Her dress is red."),
                    ex("quiz", "Qual peça de roupa é a 'jacket'?",
                       "jaqueta", ["jaqueta", "saia", "camisa"]),
                ],
            ),
            topic(
                "escola-e-materiais",
                "Escola e materiais",
                """
# Escola e materiais

## Pessoas e lugares

| Inglês | Português |
|---|---|
| teacher | professor(a) |
| student | estudante |
| classroom | sala de aula |
| school | escola |

## Materiais

| Inglês | Português |
|---|---|
| book | livro |
| notebook | caderno |
| pen | caneta |
| pencil | lápis |
| desk | mesa/carteira |
| homework | dever de casa |

## Exemplos

```
The teacher is in the classroom.   O professor está na sala de aula.
I do my homework at night.         Eu faço meu dever de casa à noite.
```

> 💡 **homework** é incontável: não use "a homework" nem "homeworks" — é
> sempre "homework".
""",
                [
                    ex("quiz", "Como se diz 'professor' em inglês?",
                       "teacher", ["teacher", "student", "doctor"]),
                    ex("quiz", "Como se diz 'caderno' em inglês?",
                       "notebook", ["notebook", "book", "pencil"]),
                    ex("text", "Traduza: O dever de casa.",
                       "the homework"),
                    ex("quiz", "Como se diz 'caneta' em inglês?",
                       "pen", ["pen", "pencil", "desk"]),
                    ex("audio", "Escute e transcreva:",
                       "the teacher is in the classroom", audio_text="The teacher is in the classroom."),
                    ex("quiz", "Qual é o 'student'?",
                       "estudante", ["estudante", "professor", "livro"]),
                ],
            ),
            topic(
                "trabalho-e-profissoes",
                "Trabalho e profissões",
                """
# Trabalho e profissões

| Inglês | Português |
|---|---|
| work | trabalho / trabalhar |
| job | emprego |
| doctor | médico(a) |
| nurse | enfermeiro(a) |
| teacher | professor(a) |
| engineer | engenheiro(a) |
| driver | motorista |
| cook | cozinheiro(a) |
| police officer | policial |

## Exemplos

```
She is a nurse.             Ela é enfermeira.
I work in a hospital.       Eu trabalho em um hospital.
```

> 💡 Com profissões, usamos **a/an**: "She is a nurse." — sempre com artigo
> no singular, diferente do português ("ela é enfermeira" sem artigo).
""",
                [
                    ex("quiz", "Como se diz 'médico' em inglês?",
                       "doctor", ["doctor", "nurse", "cook"]),
                    ex("quiz", "Como se diz 'motorista' em inglês?",
                       "driver", ["driver", "engineer", "police officer"]),
                    ex("text", "Traduza: Eu trabalho em um hospital.",
                       "i work in a hospital"),
                    ex("quiz", "Qual é o 'engineer'?",
                       "engenheiro", ["engenheiro", "cozinheiro", "enfermeiro"]),
                    ex("audio", "Escute e transcreva:",
                       "she is a nurse", audio_text="She is a nurse."),
                    ex("quiz", "Como se diz 'cozinheiro' em inglês?",
                       "cook", ["cook", "driver", "teacher"]),
                ],
            ),
            topic(
                "meios-de-transporte",
                "Meios de transporte",
                """
# Meios de transporte

| Inglês | Português |
|---|---|
| car | carro |
| bus | ônibus |
| train | trem |
| plane | avião |
| bike | bicicleta |
| boat | barco |
| subway | metrô |
| taxi | táxi |

## Como você vai? (by + transporte)

```
I go to work by bus.        Eu vou trabalhar de ônibus.
She travels by plane.       Ela viaja de avião.
```

> 💡 Use **by** + transporte para dizer o meio: **by car**, **by train**.
> Só com **on foot** (a pé) é diferente — não dizemos "by foot".
""",
                [
                    ex("quiz", "Como se diz 'trem' em inglês?",
                       "train", ["train", "bus", "plane"]),
                    ex("quiz", "Como se diz 'ônibus' em inglês?",
                       "bus", ["bus", "car", "bike"]),
                    ex("text", "Traduza: Eu vou de ônibus.",
                       "i go by bus"),
                    ex("quiz", "Como se diz 'avião' em inglês?",
                       "plane", ["plane", "train", "boat"]),
                    ex("audio", "Escute e transcreva:",
                       "i go to work by train", audio_text="I go to work by train."),
                    ex("quiz", "Qual é o 'subway'?",
                       "metrô", ["metrô", "bicicleta", "táxi"]),
                ],
            ),
            topic(
                "clima-e-tempo",
                "Clima e tempo",
                """
# Clima e tempo

## Adjetivos do clima

| Inglês | Português |
|---|---|
| sunny | ensolarado |
| rainy | chuvoso |
| cloudy | nublado |
| windy | ventoso |
| hot | quente |
| cold | frio |
| warm | morno / quentinho |
| snow | neve |

## Como falar do tempo

Use **It is** (está/faz) + adjetivo:

```
It is sunny today.        Está ensolarado hoje.
It is cold outside.       Está frio lá fora.
It's raining.             Está chovendo.
```

> 💡 Em inglês o "it" do clima não tem tradução direta: "It is hot." = "Está
> quente" — o "it" não é "ele".
""",
                [
                    ex("quiz", "Como se diz 'chuvoso' em inglês?",
                       "rainy", ["rainy", "sunny", "cloudy"]),
                    ex("quiz", "Como se diz 'ensolarado' em inglês?",
                       "sunny", ["sunny", "rainy", "windy"]),
                    ex("text", "Traduza: Está frio hoje.",
                       "it is cold today"),
                    ex("quiz", "Qual é o 'hot'?",
                       "quente", ["quente", "frio", "nublado"]),
                     ex("audio", "Escute e transcreva:",
                        "it's raining today", audio_text="It's raining today."),
                    ex("quiz", "Como se diz 'ventoso' em inglês?",
                       "windy", ["windy", "warm", "cloudy"]),
                ],
            ),
            topic(
                "hobbies-e-lazer",
                "Hobbies e lazer",
                """
# Hobbies e lazer

## Verbos de lazer

| Inglês | Português |
|---|---|
| read | ler |
| watch TV | assistir TV |
| play games | jogar jogos |
| listen to music | ouvir música |
| run | correr |
| swim | nadar |
| dance | dançar |
| sing | cantar |
| draw | desenhar |
| travel | viajar |

## Exemplos

```
I watch TV at night.          Eu assisto TV à noite.
I like music.                 Eu gosto de música.
```

> 💡 Para falar de gostos, o padrão é **I like + atividade**: "I like to read"
> ou "I like reading" — os dois são corretos no A1.
""",
                [
                    ex("quiz", "Como se diz 'ler' em inglês?",
                       "read", ["read", "run", "sing"]),
                    ex("quiz", "Como se diz 'dançar' em inglês?",
                       "dance", ["dance", "draw", "swim"]),
                    ex("text", "Traduza: Eu gosto de música.",
                       "i like music"),
                    ex("quiz", "Como se diz 'nadar' em inglês?",
                       "swim", ["swim", "sing", "run"]),
                    ex("audio", "Escute e transcreva:",
                       "i watch tv at night", audio_text="I watch TV at night."),
                    ex("quiz", "Qual é o verbo 'draw'?",
                       "desenhar", ["desenhar", "correr", "dançar"]),
                ],
            ),
            topic(
                "compras-e-lojas",
                "Compras e lojas",
                """
# Compras e lojas

## Vocabulário de compras

| Inglês | Português |
|---|---|
| store | loja |
| market | mercado / feira |
| buy | comprar |
| sell | vender |
| money | dinheiro |
| cheap | barato |
| expensive | caro |
| price | preço |

## Exemplos

```
How much is this?            Quanto custa isso?
The store is expensive.      A loja é cara.
I want to buy a phone.       Eu quero comprar um celular.
```

> 💡 **How much...?** é a pergunta de preço: "How much is this?" — ela já
> veio no Módulo 1 e continua sendo essencial nas compras.
""",
                [
                    ex("quiz", "Como se diz 'loja' em inglês?",
                       "store", ["store", "market", "money"]),
                    ex("quiz", "Como se diz 'comprar' em inglês?",
                       "buy", ["buy", "sell", "pay"]),
                    ex("text", "Traduza: Quanto custa isso?",
                       "how much is this"),
                    ex("quiz", "Como se diz 'caro' em inglês?",
                       "expensive", ["expensive", "cheap", "free"]),
                    ex("audio", "Escute e transcreva:",
                       "the store is expensive", audio_text="The store is expensive."),
                    ex("quiz", "Como se diz 'barato' em inglês?",
                       "cheap", ["cheap", "expensive", "small"]),
                ],
            ),
            topic(
                "lugares-na-cidade",
                "Lugares na cidade",
                """
# Lugares na cidade

| Inglês | Português |
|---|---|
| bank | banco |
| hospital | hospital |
| school | escola |
| park | parque |
| supermarket | supermercado |
| restaurant | restaurante |
| hotel | hotel |
| museum | museu |
| police station | delegacia |

## Exemplos

```
Where is the bank?            Onde fica o banco?
The hotel is near the park.   O hotel fica perto do parque.
```

> 💡 Para dizer onde algo fica, use **near** (perto), **next to** (ao lado) e
> **between** (entre) — preposições que você viu no Módulo 2.
""",
                [
                    ex("quiz", "Como se diz 'hospital' em inglês?",
                       "hospital", ["hospital", "hotel", "museum"]),
                    ex("quiz", "Como se diz 'supermercado' em inglês?",
                       "supermarket", ["supermarket", "bank", "park"]),
                    ex("text", "Traduza: Onde fica o banco?",
                       "where is the bank"),
                    ex("quiz", "Como se diz 'restaurante' em inglês?",
                       "restaurant", ["restaurant", "museum", "school"]),
                    ex("audio", "Escute e transcreva:",
                       "the hotel is near the park", audio_text="The hotel is near the park."),
                    ex("quiz", "Qual é o 'museum'?",
                       "museu", ["museu", "banco", "mercado"]),
                ],
            ),
            topic(
                "partes-do-corpo",
                "Partes do corpo",
                """
# Partes do corpo

| Inglês | Português |
|---|---|
| head | cabeça |
| hair | cabelo |
| face | rosto |
| eyes | olhos |
| ears | orelhas |
| nose | nariz |
| mouth | boca |
| hand | mão |
| arm | braço |
| leg | perna |
| foot | pé |

## Exemplos

```
My head hurts.           Minha cabeça dói.
She has blue eyes.       Ela tem olhos azuis.
```

> 💡 Alguns plurais são irregulares: **foot -> feet** (pé/pés) e **tooth ->
> teeth** (dente/dentes).
""",
                [
                    ex("quiz", "Como se diz 'cabeça' em inglês?",
                       "head", ["head", "hand", "foot"]),
                    ex("quiz", "Como se diz 'olhos' em inglês?",
                       "eyes", ["eyes", "ears", "hands"]),
                    ex("text", "Traduza: Minha mão.",
                       "my hand"),
                    ex("quiz", "Como se diz 'nariz' em inglês?",
                       "nose", ["nose", "mouth", "ear"]),
                    ex("audio", "Escute e transcreva:",
                       "my head hurts", audio_text="My head hurts."),
                    ex("quiz", "Qual é o 'foot'?",
                       "pé", ["pé", "braço", "perna"]),
                ],
            ),
            topic(
                "verbos-comuns",
                "Verbos comuns",
                """
# Verbos comuns

Os verbos mais usados do inglês — muitos você já conhece; aqui entram os que
faltam no vocabulário ativo.

| Inglês | Português |
|---|---|
| be | ser / estar |
| have | ter |
| do | fazer |
| go | ir |
| come | vir |
| eat | comer |
| drink | beber |
| sleep | dormir |
| work | trabalhar |
| play | jogar / brincar |
| speak | falar |
| see | ver |
| want | querer |
| need | precisar |

## Exemplos

```
I want water.             Eu quero água.
I need help.              Eu preciso de ajuda.
```

> 💡 Estes verbos aparecem em quase toda frase. Vale **memorizar a lista**
> antes de seguir: é o vocabulário de maior retorno do curso.
""",
                [
                    ex("quiz", "Qual é o verbo 'comer' em inglês?",
                       "eat", ["eat", "drink", "sleep"]),
                    ex("quiz", "Qual é o verbo 'querer' em inglês?",
                       "want", ["want", "need", "go"]),
                    ex("text", "Traduza: Eu preciso de ajuda.",
                       "i need help"),
                    ex("quiz", "Qual é o verbo 'ver' em inglês?",
                       "see", ["see", "come", "do"]),
                    ex("audio", "Escute e transcreva:",
                       "i want water", audio_text="I want water."),
                    ex("quiz", "Qual é o verbo 'falar' em inglês?",
                       "speak", ["speak", "play", "eat"]),
                ],
            ),
            topic(
                "adjetivos-comuns",
                "Adjetivos comuns",
                """
# Adjetivos comuns

| Inglês | Português |
|---|---|
| big | grande |
| small | pequeno |
| new | novo |
| old | velho / antigo |
| good | bom |
| bad | ruim |
| happy | feliz |
| sad | triste |
| hot | quente |
| cold | frio |
| fast | rápido |
| slow | lento |
| beautiful | bonito / lindo |
| ugly | feio |

## Exemplos

```
The car is new.           O carro é novo.
She is happy today.       Ela está feliz hoje.
```

> 💡 Em inglês, o adjetivo não varia com o substantivo: "big car" e "big
> houses" — o **big** fica igual, diferente do português.
""",
                [
                    ex("quiz", "Qual é o adjetivo 'grande' em inglês?",
                       "big", ["big", "small", "old"]),
                    ex("quiz", "Qual é o adjetivo 'feliz' em inglês?",
                       "happy", ["happy", "sad", "bad"]),
                    ex("text", "Traduza: O carro é novo.",
                       "the car is new"),
                    ex("quiz", "Qual é o adjetivo 'rápido' em inglês?",
                       "fast", ["fast", "slow", "small"]),
                    ex("audio", "Escute e transcreva:",
                       "she is happy today", audio_text="She is happy today."),
                    ex("quiz", "Qual é o antônimo (oposto) de 'big'?",
                       "small", ["small", "new", "fast"]),
                ],
            ),
            topic(
                "expressoes-do-dia-a-dia",
                "Expressões do dia a dia",
                """
# Expressões do dia a dia

Frases prontas para situações comuns — você já viu algumas no Módulo 1; aqui
completamos o kit básico.

| Expressão | Português |
|---|---|
| You're welcome | De nada |
| No problem | Sem problema |
| Of course | É claro / Claro |
| Me too | Eu também |
| See you soon | Até logo |
| Have a nice day | Tenha um bom dia |
| Take care | Se cuida |
| I'm sorry | Desculpe / Sinto muito |

## Exemplos

```
Thanks for your help!  -  You're welcome.
See you soon!          -  See you! / Take care!
```

> 💡 **You're welcome** é a resposta para "thank you". **Me too** é o atalho
> para concordar: "I like pizza." - "Me too!"
""",
                [
                    ex("quiz", "Como se diz 'De nada' em inglês?",
                       "You're welcome", ["You're welcome", "Of course", "No problem"]),
                    ex("quiz", "Como se diz 'Sem problema' em inglês?",
                       "No problem", ["No problem", "Me too", "Of course"]),
                    ex("text", "Traduza: Tenha um bom dia!",
                       "have a nice day"),
                    ex("quiz", "Como se diz 'Eu também' em inglês?",
                       "Me too", ["Me too", "No problem", "Of course"]),
                    ex("audio", "Escute e transcreva:",
                       "see you soon", audio_text="See you soon."),
                    ex("quiz", "Como se diz 'É claro' / 'Claro' em inglês?",
                       "Of course", ["Of course", "You're welcome", "Sorry"]),
                ],
            ),
        ],
    )


# ============================================================
# MODULO 4 - Comunicacao - A1
# ============================================================

@_expand_target_builder
def build_modulo_04_comunicacao_a1():
    return module(
        "modulo-04-comunicacao-a1",
        "Módulo 4 — Comunicação — A1",
        "Frase pronta para a vida real: apresentar-se, pedir informações e direções, pedir comida, fazer compras, falar da família e da rotina, expressar gostos, fazer pedidos e entender conversas simples.",
        [
            topic(
                "apresentacoes",
                "Apresentando-se em situações",
                """
# Apresentando-se em situações

Além de dizer seu nome (Módulo 1), você vai apresentar outras pessoas e falar
um pouco de si em conversas reais.

## Apresentando um amigo

```
This is my friend, Pedro.    Este é meu amigo, Pedro.
```

## Dizendo de onde você é e o que faz

```
I am from Brazil.            Eu sou do Brasil.
I work in a bank.            Eu trabalho em um banco.
I am a student.              Eu sou estudante.
```

## No primeiro encontro

```
Nice to meet you.            Prazer em conhecê-lo(a).
Nice to meet you too.        Prazer também (em conhecê-lo).
```

> 💡 Apresente primeiro a pessoa, depois conte algo sobre você: "This is my
> friend. He is from Portugal."
""",
                [
                    ex("quiz", "Como você apresenta um amigo chamado Pedro?",
                       "This is my friend, Pedro.", ["This is my friend, Pedro.", "I am my friend Pedro.", "My name is friend Pedro."]),
                    ex("text", "Traduza: Eu sou do Brasil.",
                       "i am from brazil"),
                    ex("quiz", "No primeiro encontro, o que você diz?",
                       "Nice to meet you.", ["Nice to meet you.", "Good night.", "Thank you."]),
                    ex("audio", "Escute e transcreva:",
                       "this is my friend", audio_text="This is my friend."),
                    ex("text", "Traduza: Eu trabalho em um banco.",
                       "i work in a bank"),
                    ex("speak", "Diga em voz alta, se apresentando:",
                       "i am from brazil", audio_text="I am from Brazil."),
                ],
            ),
            topic(
                "pedindo-informacoes",
                "Pedindo informações",
                """
# Pedindo informações

Para pedir informação a um desconhecido, comece com **Excuse me** (com
licença) e seja educado com **please**.

## Modelos de pergunta

```
Excuse me, can you help me?      Com licença, você pode me ajudar?
Where is the station?            Onde fica a estação?
What time is it, please?         Que horas são, por favor?
What time does the store open?   A que horas abre a loja?
```

## Respostas comuns

```
Sure. / Of course.               Claro.
I'm sorry, I don't know.         Desculpe, eu não sei.
```

> 💡 **Can you...?** é o jeito educado de pedir: "Can you help me?" = "Você
> pode me ajudar?"
""",
                [
                    ex("quiz", "Como você pede informação educadamente a um estranho?",
                       "Excuse me, can you help me?", ["Excuse me, can you help me?", "Hey, give me information.", "Stop, I need you."]),
                    ex("text", "Traduza: Onde fica a estação?",
                       "where is the station"),
                    ex("quiz", "Como perguntar as horas educadamente?",
                       "What time is it, please?", ["What time is it, please?", "Give me the hour.", "Tell me the time now."]),
                    ex("audio", "Escute e transcreva:",
                       "can you help me", audio_text="Can you help me?"),
                    ex("text", "Traduza: A que horas abre a loja?",
                       "what time does the store open"),
                    ex("quiz", "Qual frase é um pedido de informação?",
                       "Where is the bathroom?", ["Where is the bathroom?", "I live here.", "The store is open."]),
                ],
            ),
            topic(
                "pedindo-direcoes",
                "Pedindo direções",
                """
# Pedindo direções

## Perguntando o caminho

```
Excuse me, how do I get to the bank?    Com licença, como chego ao banco?
Where is the park?                      Onde fica o parque?
```

## Entendendo as instruções

| Expressão | Português |
|---|---|
| Go straight | Siga em frente |
| Turn left | Vire à esquerda |
| Turn right | Vire à direita |
| It's near | É perto |
| It's far | É longe |

## Exemplo de resposta

```
Go straight and turn right at the corner.   Siga em frente e vire à direita na esquina.
The bank is near.                           O banco fica perto.
```

> 💡 **How do I get to...?** = "Como eu chego até...?" — a pergunta padrão de
> direção. Combine com as preposições do Módulo 2 (near, next to).
""",
                [
                    ex("quiz", "Como você pergunta o caminho para o banco?",
                       "How do I get to the bank?", ["How do I get to the bank?", "What is the bank?", "Do you like the bank?"]),
                    ex("text", "Traduza: Vire à direita.",
                       "turn right"),
                    ex("quiz", "O que significa 'go straight'?",
                       "siga em frente", ["siga em frente", "vire à esquerda", "pare aqui"]),
                    ex("audio", "Escute e transcreva:",
                       "turn left at the corner", audio_text="Turn left at the corner."),
                    ex("text", "Traduza: O banco fica perto.",
                       "the bank is near"),
                    ex("quiz", "Qual expressão indica CONTINUAR no mesmo caminho?",
                       "Go straight.", ["Go straight.", "Turn left.", "Turn right."]),
                ],
            ),
            topic(
                "pedindo-comida",
                "Pedindo comida",
                """
# Pedindo comida

Num restaurante ou café, peça com **Can I have...?** (posso ter?) ou
**I'd like...** (eu gostaria de...).

## Pedindo

```
Can I have a coffee, please?      Posso tomar um café, por favor?
I'd like a juice.                 Eu gostaria de um suco.
The menu, please.                 O cardápio, por favor.
```

## Pedindo a conta

```
The bill, please.                 A conta, por favor.
```

## Agradecendo

```
Thank you.  /  Thanks.            Obrigado(a).
You're welcome.                   De nada.
```

> 💡 **I'd like** é a contração de **I would like** — a forma mais educada de
> pedir em inglês. Use "please" sempre que puder.
""",
                [
                    ex("quiz", "Como você pede educadamente num restaurante?",
                       "Can I have a coffee, please?", ["Can I have a coffee, please?", "Give me coffee.", "I want coffee now."]),
                    ex("text", "Traduza: O cardápio, por favor.",
                       "the menu please"),
                    ex("quiz", "O que 'I'd like...' significa?",
                       "Eu gostaria de...", ["Eu gostaria de...", "Eu não gosto de...", "Eu tenho..."]),
                    ex("audio", "Escute e transcreva:",
                       "can i have water please", audio_text="Can I have water, please?"),
                    ex("text", "Traduza: Eu gostaria de um suco.",
                       "i would like a juice"),
                    ex("quiz", "Como você pede a conta?",
                       "The bill, please.", ["The bill, please.", "The menu, please.", "The table, please."]),
                ],
            ),
            topic(
                "fazendo-compras",
                "Fazendo compras",
                """
# Fazendo compras

## Perguntando preço

```
How much is this?            Quanto custa isso?
```

## O que você precisa

```
I need a shirt.              Eu preciso de uma camisa.
Do you have this in red?     Você tem isso em vermelho?
```

## Sobre o preço

```
It's cheap.                  É barato.
It's too expensive.          É caro demais.
```

## Fechando

```
I'll take it.                Vou levar.
Thanks a lot!                Muito obrigado!
```

> 💡 **too expensive** = caro **demais** (excessivo). **Do you have...?** é a
> pergunta padrão para saber se a loja tem um produto.
""",
                [
                    ex("quiz", "Como você pergunta o preço de algo?",
                       "How much is this?", ["How much is this?", "How old is this?", "Where is this?"]),
                    ex("text", "Traduza: Eu preciso de uma camisa.",
                       "i need a shirt"),
                    ex("quiz", "Como você pergunta se a loja tem um produto?",
                       "Do you have this in red?", ["Do you have this in red?", "Is you have this?", "Have you this red?"]),
                    ex("audio", "Escute e transcreva:",
                       "it is too expensive", audio_text="It is too expensive."),
                    ex("quiz", "O que significa 'too expensive'?",
                       "caro demais", ["caro demais", "muito barato", "pequeno demais"]),
                    ex("text", "Traduza: Quanto custa isso?",
                       "how much is this"),
                ],
            ),
            topic(
                "falando-da-familia",
                "Falando da família",
                """
# Falando da família

Para falar de família, use **I have** (eu tenho) e o possessivo **my**
(meu/minha).

## Quantidade de irmãos

```
I have two brothers.        Eu tenho dois irmãos.
I have one sister.          Eu tenho uma irmã.
I have no brothers.         Eu não tenho irmãos.
```

## O que eles fazem / onde vivem

```
My sister is a doctor.      Minha irmã é médica.
My mother lives here.       Minha mãe mora aqui.
We live together.           Nós moramos juntos.
```

> 💡 No presente simples, lembre-se do -s da terceira pessoa: **she lives**,
> **my mother lives** (Módulo 2).
""",
                [
                    ex("quiz", "Como dizer 'Eu tenho dois irmãos'?",
                       "I have two brothers.", ["I have two brothers.", "I am two brothers.", "I has two brothers."]),
                    ex("text", "Traduza: Minha irmã é médica.",
                       "my sister is a doctor"),
                    ex("quiz", "Como dizer 'Minha mãe mora aqui'?",
                       "My mother lives here.", ["My mother lives here.", "My mother live here.", "My mother living here."]),
                    ex("audio", "Escute e transcreva:",
                       "we live together", audio_text="We live together."),
                    ex("quiz", "O que 'I have no brothers' significa?",
                       "Eu não tenho irmãos", ["Eu não tenho irmãos", "Eu tenho muitos irmãos", "Eu tenho um irmão"]),
                    ex("text", "Traduza: Eu tenho uma irmã.",
                       "i have a sister"),
                ],
            ),
            topic(
                "falando-da-rotina",
                "Falando da rotina",
                """
# Falando da rotina

Para falar do que você faz todo dia, use o **presente simples** (Módulo 2)
com os horários do dia.

## Minha rotina

```
I wake up at 7.               Eu acordo às 7.
I eat breakfast at 7.         Eu tomo café da manhã às 7.
I go to work in the morning.  Eu vou trabalhar de manhã.
I have lunch at noon.         Eu almoço ao meio-dia.
I sleep at 11.                Eu durmo às 11.
```

## Marcadores de frequência

```
every day    todos os dias
in the morning    de manhã
at night     à noite
```

> 💡 Para descrever a rotina de outra pessoa, adicione -s no verbo: "She wakes
> up at 7." — mesmo padrão do presente simples.
""",
                [
                    ex("quiz", "Como dizer 'Eu acordo às 7'?",
                       "I wake up at 7.", ["I wake up at 7.", "I wake at 7 up.", "I wakes up at 7."]),
                    ex("text", "Traduza: Eu almoço ao meio-dia.",
                       "i have lunch at noon"),
                    ex("quiz", "O que 'every day' significa?",
                       "todos os dias", ["todos os dias", "de manhã", "à noite"]),
                    ex("audio", "Escute e transcreva:",
                       "i go to work in the morning", audio_text="I go to work in the morning."),
                    ex("quiz", 'Complete: "She ___ at 11 pm." (dormir)',
                       "sleeps", ["sleeps", "sleep", "sleeping"]),
                    ex("text", "Traduza: Eu como café da manhã às 7.",
                       "i eat breakfast at 7"),
                ],
            ),
            topic(
                "gostos-e-preferencias",
                "Gostos e preferências",
                """
# Gostos e preferências

## Como você se sente sobre algo

| Expressão | Português |
|---|---|
| I love... | Eu adoro... |
| I like... | Eu gosto de... |
| I don't like... | Eu não gosto de... |
| I hate... | Eu odeio... |
| I prefer... | Eu prefiro... |

## Perguntando o que a pessoa gosta

```
Do you like music?      Você gosta de música?
```

## Respostas

```
Yes, I do. / Yes, I love it.    Sim. / Sim, adoro!
No, I don't.                    Não.
```

> 💡 Nas respostas curtas com gostos, use **do**: "Do you like tea?" - "Yes,
> I do." / "No, I don't."
""",
                [
                    ex("quiz", "Como dizer 'Eu adoro pizza'?",
                       "I love pizza.", ["I love pizza.", "I hate pizza.", "I eat pizza."]),
                    ex("text", "Traduza: Eu não gosto de café.",
                       "i don't like coffee"),
                    ex("quiz", "Como perguntar se alguém gosta de música?",
                       "Do you like music?", ["Do you like music?", "You like music?", "Are you like music?"]),
                    ex("audio", "Escute e transcreva:",
                       "i prefer tea", audio_text="I prefer tea."),
                     ex("quiz", "O que 'I hate it' significa?",
                        "Eu odeio isso", ["Eu odeio isso", "Eu adoro isso", "Eu não sei"]),
                    ex("text", "Traduza: Eu gosto de música.",
                       "i like music"),
                ],
            ),
            topic(
                "pedidos-simples",
                "Fazendo pedidos simples",
                """
# Fazendo pedidos simples

Pedidos são diferentes de perguntas de informação: você quer **algo** (uma
coisa ou uma ação), não uma resposta.

## Pedindo coisas

```
Can I have some water, please?      Posso ter um pouco de água, por favor?
A coffee, please.                   Um café, por favor.
```

## Pedindo ações

```
Can you repeat, please?             Você pode repetir, por favor?
Can you help me?                    Você pode me ajudar?
```

## A ideia do Can I... / Can you...

- **Can I...?** = pede permissão (posso...?).
- **Can you...?** = pede uma ação (você pode...?).

> 💡 O "please" no fim (ou começo) transforma qualquer pedido em algo
> educado. Em dúvida, use sempre: "Can I have ..., please?"
""",
                [
                    ex("quiz", "Como pedir uma água educadamente?",
                       "Can I have some water, please?", ["Can I have some water, please?", "Water now!", "Give water."]),
                    ex("text", "Traduza: Você pode repetir, por favor?",
                       "can you repeat please"),
                    ex("quiz", "O que 'Can I...' pede numa pergunta?",
                       "permissão (posso...?)", ["permissão (posso...?)", "informação", "preço"]),
                    ex("audio", "Escute e transcreva:",
                       "can you help me please", audio_text="Can you help me, please?"),
                    ex("text", "Traduza: Um café, por favor.",
                       "a coffee please"),
                    ex("quiz", "Qual frase é um PEDIDO?",
                       "Can I have a menu, please?", ["Can I have a menu, please?", "What time is it?", "Where is the bank?"]),
                ],
            ),
            topic(
                "entendendo-conversas-simples",
                "Entendendo conversas simples",
                """
# Entendendo conversas simples

Nas primeiras conversas, treine reconhecer a pergunta e escolher a resposta
certa. As perguntas mais comuns têm respostas quase automáticas.

## Pergunta e resposta

```
What's your name?            ->  My name is Ana.
Where are you from?          ->  I'm from Brazil.
How old are you?             ->  I'm 20 years old.
What do you do?              ->  I'm a student.
Do you like music?           ->  Yes, I do.
```

## O que fazer quando não entender

```
I don't understand.          Eu não entendo.
Can you repeat, please?      Você pode repetir, por favor?
```

## Concordando na conversa

```
I like pizza.      -    Me too!      (Eu também!)
```

> 💡 Quando ouvir uma pergunta com "What's / Where / How / Do", foque na
> **primeira palavra** — ela já diz sobre o que é a pergunta.
""",
                [
                    ex("quiz", "Para 'What's your name?', qual é a resposta natural?",
                       "My name is Ana.", ["My name is Ana.", "I'm fine, thanks.", "Good morning."]),
                    ex("quiz", "Para 'Where are you from?', qual é a resposta natural?",
                       "I'm from Brazil.", ["I'm from Brazil.", "I'm 20.", "I'm a student."]),
                    ex("text", "Traduza: Eu não entendo.",
                       "i don't understand"),
                    ex("audio", "Escute e transcreva:",
                       "what is your name", audio_text="What is your name?"),
                    ex("quiz", "Numa conversa, 'Me too!' significa que você:",
                       "concorda com o que foi dito", ["concorda com o que foi dito", "discorda do que foi dito", "vai embora"]),
                    ex("audio", "Escute e transcreva:",
                       "nice to meet you too", audio_text="Nice to meet you too."),
                ],
            ),
        ],
    )


# ============================================================
# MODULO 5 - Gramatica Essencial - A2
# ============================================================

@_expand_target_builder
def build_modulo_05_gramatica_essencial_a2():
    return module(
        "modulo-05-gramatica-essencial-a2",
        "Módulo 5 — Gramática Essencial — A2",
        "O segundo tijolo do sistema: revisão do presente, presente contínuo, passado simples, futuro (going to e will), contáveis/incontáveis, some/any, much/many, a lot of, must/have to, comparativo/superlativo, advérbios de modo, pronomes objeto e possessivos, e conjunções.",
        [
            topic(
                "revisao-presente-simples",
                "Revisão do Presente Simples",
                """
# Revisão do Presente Simples

Recapitulando o que você viu no Módulo 2, agora com mais exemplos.

## Afirmativo

```
I work.      She works.     (verbo + -s na 3ª pessoa)
```

## Negativo

```
I don't work.       She doesn't work.
```

## Interrogativo

```
Do you work?        Does she work?
```

## Regra que nunca muda

- **I/you/we/they** + verbo base.
- **he/she/it** + verbo + **-s**.
- Negativa e pergunta usam **do/does** — e o verbo volta ao normal.

> 💡 Erro clássico: "She don't work" ou "Does she works?" — nas negativas e
> perguntas com does, o verbo NUNCA leva -s.
""",
                [
                    ex("quiz", 'Complete: "She ___ TV every night." (watch)',
                       "watches", ["watches", "watch", "watching"]),
                    ex("quiz", 'Complete a negativa: "They ___ coffee." (not/like)',
                       "don't like", ["don't like", "doesn't like", "not like"]),
                    ex("text", "Traduza: Você trabalha aos domingos?",
                       "do you work on sundays"),
                    ex("quiz", 'Complete: "He ___ to school by bus." (go)',
                       "goes", ["goes", "go", "going"]),
                    ex("audio", "Escute e transcreva:",
                       "she works in a hospital", audio_text="She works in a hospital."),
                    ex("quiz", "Qual é a forma negativa de 'I work'?",
                       "I don't work", ["I don't work", "I doesn't work", "I not work"]),
                ],
            ),
            topic(
                "presente-continuo",
                "Presente Contínuo",
                """
# Presente Contínuo

O **presente contínuo** descreve algo que está acontecendo **agora, neste
momento**. Forma: **am/is/are + verbo-ing**.

## Afirmativo

```
I am working now.          Eu estou trabalhando agora.
She is reading a book.     Ela está lendo um livro.
They are playing football. Eles estão jogando futebol.
```

## Negativo

```
I am not working.     ->  I'm not working.
She is not running.   ->  She isn't running.
```

## Interrogativo

```
Are you listening to me?     Você está me ouvindo?
Is he sleeping?              Ele está dormindo?
```

> 💡 Terminações do -ing: **read -> reading** (só -ing), **run -> running**
> (dobra a consoante), **make -> making** (cai o e).
""",
                [
                    ex("quiz", 'Complete: "I ___ working now." (estou)',
                       "am", ["am", "is", "are"]),
                    ex("quiz", 'Complete: "She is ___ a book." (read)',
                       "reading", ["reading", "read", "reads"]),
                    ex("text", "Traduza: Eles estão jogando futebol.",
                       "they are playing football"),
                    ex("quiz", "Qual é a negativa de 'She is running'?",
                       "She isn't running", ["She isn't running", "She not running", "She doesn't running"]),
                    ex("audio", "Escute e transcreva:",
                       "i am watching tv", audio_text="I am watching TV."),
                    ex("quiz", 'Complete a pergunta: "___ you listening to me?"',
                       "Are", ["Are", "Is", "Do"]),
                ],
            ),
            topic(
                "passado-simples",
                "Passado Simples",
                """
# Passado Simples

O **passado simples** descreve ações que já terminaram. Para formar: verbos
regulares ganham **-ed**; os irregulares mudam de forma (e é preciso
memorizar).

## Regulares

```
work -> worked      watch -> watched     live -> lived
```

## Irregulares comuns

```
go -> went       have -> had      see -> saw
eat -> ate       do -> did        make -> made
```

## Afirmativo

```
Yesterday, I went to the park.      Ontem eu fui ao parque.
We visited my grandmother.          Nós visitamos minha avó.
```

## Negativo: didn't + verbo base

```
She didn't eat breakfast.           Ela não tomou café da manhã.
```

## Interrogativo: Did + sujeito + verbo base

```
Did you see the movie?              Você viu o filme?
```

> 💡 Com **didn't** e **Did**, o verbo volta ao presente (forma base): "She
> didn't ate" está errado — o certo é "She didn't eat".
""",
                [
                    ex("quiz", "Qual é o passado de 'go'?",
                       "went", ["went", "gone", "goed"]),
                    ex("quiz", 'Complete: "Yesterday, I ___ to the park." (fui)',
                       "went", ["went", "go", "goes"]),
                    ex("text", "Escreva o passado do verbo 'watch'.",
                       "watched"),
                    ex("quiz", 'Complete a negativa: "She ___ breakfast." (not/eat)',
                       "didn't eat", ["didn't eat", "don't eat", "didn't ate"]),
                    ex("audio", "Escute e transcreva:",
                       "we visited my grandmother", audio_text="We visited my grandmother."),
                    ex("quiz", 'Complete a pergunta: "___ you see the movie?"',
                       "Did", ["Did", "Do", "Are"]),
                ],
            ),
            topic(
                "futuro-going-to",
                "Futuro com going to",
                """
# Futuro com going to

O **going to** expressa **planos** e **intenções** já decididos. Forma:
**am/is/are + going to + verbo base**.

## Afirmativo

```
I am going to buy a new car.        Eu vou comprar um carro novo.
She is going to visit her friends.  Ela vai visitar os amigos.
We are going to travel tomorrow.    Nós vamos viajar amanhã.
```

## Negativo

```
They are not going to come.         Eles não vão vir.
I'm not going to study tonight.     Eu não vou estudar hoje à noite.
```

## Interrogativo

```
Are you going to call her?          Você vai ligar para ela?
```

> 💡 O "going to" já carrega o verbo to be: **is/are going to**. Depois dele,
> o verbo vem na forma base: "going to buy", nunca "going to buying".
""",
                [
                    ex("quiz", 'Complete: "I am going to ___ a new car." (comprar)',
                       "buy", ["buy", "buying", "buys"]),
                    ex("quiz", 'Complete: "She is going to ___ her friends." (visitar)',
                       "visit", ["visit", "visiting", "visits"]),
                    ex("text", "Traduza: Nós vamos viajar amanhã.",
                       "we are going to travel tomorrow"),
                    ex("quiz", 'Complete a negativa: "They are ___ going to come." (não)',
                       "not", ["not", "no", "don't"]),
                    ex("audio", "Escute e transcreva:",
                       "i am going to study tonight", audio_text="I am going to study tonight."),
                    ex("quiz", 'Complete a pergunta: "___ you going to call her?"',
                       "Are", ["Are", "Do", "Will"]),
                ],
            ),
            topic(
                "futuro-will",
                "Futuro com will",
                """
# Futuro com will

O **will** expressa previsões, promessas e decisões tomadas **na hora**.
Forma: **will + verbo base** (igual para todas as pessoas).

## Afirmativo

```
I will help you.        Eu vou ajudar você.
She will be here soon.  Ela vai chegar logo.
```

## Negativo: will not / won't

```
It won't rain today.        Não vai chover hoje.
```

## Interrogativo

```
Will you help me?           Você vai me ajudar?
```

## Respostas curtas

```
Yes, I will. / No, I won't.
```

> 💡 **going to** = plano já decidido; **will** = previsão/decisão na hora.
> No A2, os dois valem para "futuro" — a nuance fina fica para o B1.
""",
                [
                    ex("quiz", 'Complete: "I will ___ you tomorrow." (ver)',
                       "see", ["see", "seeing", "saw"]),
                    ex("quiz", "Qual é a contração de 'will not'?",
                       "won't", ["won't", "willn't", "doesn't will"]),
                    ex("text", "Traduza: Eu vou ajudar você.",
                       "i will help you"),
                    ex("quiz", 'Complete: "It ___ rain today." (não vai, negativo)',
                       "won't", ["won't", "will", "isn't"]),
                    ex("audio", "Escute e transcreva:",
                       "she will be here soon", audio_text="She will be here soon."),
                    ex("quiz", 'Complete a pergunta: "___ you help me?"',
                       "Will", ["Will", "Do", "Are"]),
                ],
            ),
            topic(
                "contaveis-e-incontaveis",
                "Substantivos contáveis e incontáveis",
                """
# Substantivos contáveis e incontáveis

## Contáveis

Têm singular e plural e podem ser contados: **a book / two books**, **an
apple / three apples**.

## Incontáveis

Não têm plural e não se contam (em inglês): **water, milk, rice, money,
sugar, information, work**.

```
I need water.        (não "waters")
How much money?      (não "moneys")
```

## Regras rápidas

- Contável + contável: **one banana, two bananas**.
- Incontável: sempre no singular — **the water is cold** (não "are").
- Para "quantidade" de incontáveis, use palavras como **a glass of water**, 
  **a piece of information**.

> 💡 **money** é incontável em inglês! "Two moneys" está errado. Para contar,
> conte a moeda: "two dollars", "three reais".
""",
                [
                    ex("quiz", "Qual destas palavras é INCONTÁVEL?",
                       "water", ["water", "apple", "book"]),
                    ex("quiz", "Qual destas palavras é CONTÁVEL?",
                       "banana", ["banana", "milk", "rice"]),
                    ex("text", "Complete com 'is' ou 'are': 'The water ___ cold.'",
                       "is"),
                    ex("quiz", 'Complete: "How many ___ do you have?" (livros)',
                       "books", ["books", "book", "waters"]),
                    ex("audio", "Escute e transcreva:",
                       "i need water", audio_text="I need water."),
                    ex("quiz", "Qual destas palavras NÃO tem plural (é incontável)?",
                       "money", ["money", "cup", "egg"]),
                ],
            ),
            topic(
                "some-any",
                "Some / Any",
                """
# Some / Any

As duas servem para falar de "uma quantidade não exata". A regra:

- **some** em frases **afirmativas** (e em ofertas/pedidos).
- **any** em **negativas** e **perguntas**.

## Afirmativo

```
I have some money.          Eu tenho um pouco de dinheiro.
She has some friends here.  Ela tem alguns amigos aqui.
```

## Negativo

```
I don't have any apples.    Eu não tenho nenhuma maçã.
There isn't any milk.       Não há leite.
```

## Interrogativo

```
Do you have any water?      Você tem água?
```

> 💡 Em ofertas e pedidos, o "some" pode aparecer em pergunta (é mais
> educado): "Would you like some coffee?" — mas no A2, a regra geral é:
> afirmativa = some; negativa/pergunta = any.
""",
                [
                    ex("quiz", 'Complete: "I have ___ money." (afirmativo)',
                       "some", ["some", "any", "a"]),
                    ex("quiz", 'Complete a pergunta: "Do you have ___ water?"',
                       "any", ["any", "some", "a"]),
                    ex("text", "Complete: 'There isn't ___ milk.'",
                       "any"),
                    ex("quiz", "Complete a negativa: \"I don't have ___ apples.\"",
                       "any", ["any", "some", "a"]),
                    ex("audio", "Escute e transcreva:",
                       "she has some friends here", audio_text="She has some friends here."),
                    ex("quiz", "Em frases AFIRMATIVAS, usamos normalmente:",
                       "some", ["some", "any", "a"]),
                ],
            ),
            topic(
                "much-many",
                "Much / Many",
                """
# Much / Many

As duas perguntam "quanto/quantos" e falam de grande quantidade.

- **many** + contáveis (plural): **many books**.
- **much** + incontáveis: **much water**.

## Perguntas

```
How many books do you have?       Quantos livros você tem?
How much time do we have?         Quanto tempo nós temos?
```

## Negativas

```
I don't have many friends.        Eu não tenho muitos amigos.
There isn't much sugar.           Não há muito açúcar.
```

> 💡 Dica: se a palavra tem plural (books, friends), use **many**. Se não tem
> (time, sugar, water), use **much**.
""",
                [
                    ex("quiz", 'Complete: "How ___ books do you have?"',
                       "many", ["many", "much", "a lot"]),
                    ex("quiz", 'Complete: "How ___ time do we have?"',
                       "much", ["much", "many", "a"]),
                    ex("text", "Complete: 'I don't have ___ friends.' (muitos, contável)",
                       "many"),
                    ex("quiz", "Com palavras INCONTÁVEIS, usamos:",
                       "much", ["much", "many", "much e many"]),
                    ex("audio", "Escute e transcreva:",
                       "how many brothers do you have", audio_text="How many brothers do you have?"),
                    ex("quiz", 'Complete: "There is too ___ sugar in the coffee."',
                       "much", ["much", "many", "some"]),
                ],
            ),
            topic(
                "a-lot-of",
                "A lot of",
                """
# A lot of

**A lot of** significa "muito(s)/bastante" e serve tanto para contáveis
quanto para incontáveis — é a forma mais flexível.

## Usos

```
I have a lot of friends.        Eu tenho muitos amigos.   (contável)
She drinks a lot of coffee.     Ela toma muito café.      (incontável)
There are a lot of people here. Há muitas pessoas aqui.   (contável)
```

## Posição

**A lot of** vai antes do substantivo. Também existe **lots of** (informal),
com o mesmo sentido.

> 💡 Em frases afirmativas, **a lot of** é mais natural que many/much: "I have
> a lot of work" soa melhor que "I have much work".
""",
                [
                    ex("quiz", 'Complete: "I have ___ of friends." (muitos)',
                       "a lot", ["a lot", "much", "many"]),
                    ex("quiz", "Com quais tipos de palavra 'a lot of' pode ser usado?",
                       "contáveis e incontáveis", ["contáveis e incontáveis", "só contáveis", "só incontáveis"]),
                    ex("text", "Traduza: Eu tenho muito trabalho.",
                       "i have a lot of work"),
                    ex("quiz", 'Complete: "She drinks ___ of coffee."',
                       "a lot", ["a lot", "many", "much"]),
                    ex("audio", "Escute e transcreva:",
                       "there are a lot of people here", audio_text="There are a lot of people here."),
                    ex("quiz", "Qual a diferença de 'a lot of' para 'many'?",
                       "a lot of serve para contáveis e incontáveis; many só para contáveis", ["a lot of serve para contáveis e incontáveis; many só para contáveis", "many serve para tudo; a lot of não existe", "não há diferença"]),
                ],
            ),
            topic(
                "must-have-to",
                "Must / Have to (obrigação)",
                """
# Must / Have to (obrigação)

As duas expressam obrigação ou necessidade, com diferenças importantes.

## Must (obrigação/regra — o falante acha importante)

```
You must stop at the red light.   Você deve parar no sinal vermelho.
```

## Have to (necessidade externa, regra, fato)

```
I have to work tomorrow.          Eu tenho que trabalhar amanhã.
She has to study for the test.    Ela tem que estudar para a prova.
```

## Negativas — cuidado, sentidos DIFERENTES

```
You mustn't smoke here.      É proibido fumar aqui.   (proibição)
You don't have to come.      Você não precisa vir.    (não é obrigatório)
```

## Interrogativo

```
Do you have to work today?        Você tem que trabalhar hoje?
```

> 💡 **mustn't** = proibido; **don't have to** = não é preciso. Confundir os
> dois muda completamente o sentido!
""",
                [
                    ex("quiz", 'Complete: "You ___ stop at the red light." (deve)',
                       "must", ["must", "musts", "must to"]),
                    ex("quiz", 'Complete: "She has ___ work tomorrow." (ter de)',
                       "to", ["to", "that", "must"]),
                    ex("text", "Traduza: Eu tenho que estudar mais.",
                       "i have to study more"),
                    ex("quiz", "O que 'You mustn't smoke here' significa?",
                       "É proibido fumar aqui", ["É proibido fumar aqui", "Você não precisa fumar aqui", "É permitido fumar aqui"]),
                    ex("audio", "Escute e transcreva:",
                       "i have to work on saturday", audio_text="I have to work on Saturday."),
                    ex("quiz", "Qual frase indica PROIBIÇÃO?",
                       "You mustn't park here.", ["You mustn't park here.", "You must park here.", "You have to park here."]),
                ],
            ),
            topic(
                "comparativo-e-superlativo",
                "Comparativo e superlativo",
                """
# Comparativo e superlativo

## Comparativo (-er / more)

Compara duas coisas.

- Curtas (1 sílaba): **-er** -> `big -> bigger`.
- Longas (2+ sílabas): **more** -> `more expensive`.
- Irregulares: **good -> better**, **bad -> worse**.

```
My car is bigger than yours.      Meu carro é maior que o seu.
This phone is more expensive.     Este celular é mais caro.
```

## Superlativo (-est / most)

Fala do "mais" de um grupo.

- Curtas: **-est** -> `small -> smallest`.
- Longas: **most** -> `most beautiful`.
- Irregulares: **good -> best**, **bad -> worst**.

```
She is the smallest in the class.   Ela é a menor da turma.
This is the most expensive phone.   Este é o celular mais caro.
```

> 💡 Com **than** você compara dois: "bigger **than**". Com **the + -est/most**
> você fala do melhor de um grupo.
""",
                [
                    ex("quiz", "Qual é o comparativo de 'big'?",
                       "bigger", ["bigger", "more big", "biggest"]),
                    ex("quiz", "Qual é o superlativo de 'small'?",
                       "smallest", ["smallest", "smaller", "more small"]),
                    ex("text", "Escreva o comparativo de 'good'.",
                       "better"),
                    ex("quiz", "Com palavras longas (ex.: 'expensive'), o comparativo usa:",
                       "more", ["more", "-er", "most"]),
                    ex("audio", "Escute e transcreva:",
                       "she is taller than me", audio_text="She is taller than me."),
                    ex("quiz", "Qual é o superlativo de 'good'?",
                       "best", ["best", "better", "goodest"]),
                ],
            ),
            topic(
                "adverbios-de-modo",
                "Advérbios de modo",
                """
# Advérbios de modo

Os **advérbios de modo** dizem **como** uma ação é feita. A regra mais comum é
**adjetivo + -ly**.

```
quick -> quickly       slow -> slowly
careful -> carefully   quiet -> quietly
```

## Exemplos

```
Please speak slowly.        Por favor, fale devagar.
She drives carefully.       Ela dirige com cuidado.
He runs fast.               Ele corre rápido.
```

## Irregulares importantes

```
good -> well      (bem)
fast -> fast      (rápido — não muda)
hard -> hard      (com força, muito — não muda)
```

> 💡 Cuidado: **well** é o advérbio de **good**. "She speaks good" está
> errado — o certo é "She speaks well".
""",
                [
                    ex("quiz", "Qual é o advérbio correspondente a 'quick'?",
                       "quickly", ["quickly", "quick", "quicky"]),
                    ex("quiz", "O advérbio de 'good' é:",
                       "well", ["well", "goodly", "good"]),
                    ex("text", "Escreva o advérbio de 'slow'.",
                       "slowly"),
                    ex("quiz", "Qual é o advérbio de 'careful'?",
                       "carefully", ["carefully", "careful", "carefuly"]),
                    ex("audio", "Escute e transcreva:",
                       "please speak slowly", audio_text="Please speak slowly."),
                    ex("quiz", "Qual é a regra mais comum para formar advérbios?",
                       "adjetivo + ly", ["adjetivo + ly", "adjetivo + er", "adjetivo + est"]),
                ],
            ),
            topic(
                "pronomes-objeto",
                "Pronomes objeto",
                """
# Pronomes objeto

Os **pronomes objeto** substituem o nome que **recebe** a ação (objeto direto
ou indireto) — vêm depois do verbo ou da preposição.

| Sujeito | Objeto | Exemplo |
|---|---|---|
| I | me | Call me. (Ligue para mim.) |
| you | you | I love you. (Eu te amo.) |
| he | him | I saw him. (Eu o vi.) |
| she | her | Help her. (Ajude-a.) |
| it | it | I like it. (Eu gosto disso.) |
| we | us | Come with us. (Venha conosco.) |
| they | them | I called them. (Eu liguei para eles.) |

> 💡 Confusão comum: **I** (eu, sujeito) vs **me** (mim/me, objeto). Em "She
> loves I" está errado — o certo é "She loves me".
""",
                [
                    ex("quiz", "O pronome objeto de 'I' é:",
                       "me", ["me", "I", "my"]),
                    ex("quiz", "O pronome objeto de 'she' é:",
                       "her", ["her", "she", "hers"]),
                    ex("text", "Complete: 'Can you help ___?' (me)",
                       "me"),
                    ex("quiz", "O pronome objeto de 'they' é:",
                       "them", ["them", "they", "their"]),
                    ex("audio", "Escute e transcreva:",
                       "please call me", audio_text="Please call me."),
                    ex("quiz", 'Complete: "I love ___." (você)',
                       "you", ["you", "your", "yours"]),
                ],
            ),
            topic(
                "pronomes-possessivos",
                "Pronomes possessivos",
                """
# Pronomes possessivos

Os **pronomes possessivos** dizem de quem é algo **sem repetir o substantivo**.
Ficam sozinhos — diferente dos adjetivos possessivos (my, your...).

| Adjetivo (antes do nome) | Pronome (sozinho) | Exemplo |
|---|---|---|
| my | mine | This book is mine. (meu) |
| your | yours | The pen is yours. (seu) |
| his | his | It's his. (dele) |
| her | hers | The house is hers. (dela) |
| our | ours | This car is ours. (nosso) |
| their | theirs | Those are theirs. (deles) |

## Comparando

```
This is my book.      This book is mine.
```

> 💡 Regra: se o substantivo aparece, use o adjetivo (my book); se não
> aparece, use o pronome (mine). "This is mine book" está errado!
""",
                [
                    ex("quiz", "O pronome que substitui 'my book' é:",
                       "mine", ["mine", "my", "me"]),
                    ex("quiz", "O pronome de 'her house' é:",
                       "hers", ["hers", "her", "she"]),
                    ex("text", "Complete: 'This book is ___' (meu)",
                       "mine"),
                    ex("quiz", "Qual pronome substitui 'our car'?",
                       "ours", ["ours", "our", "we"]),
                    ex("audio", "Escute e transcreva:",
                       "the blue car is mine", audio_text="The blue car is mine."),
                    ex("quiz", "Diferente do adjetivo possessivo (my), o pronome possessivo (mine):",
                       "fica sozinho, sem o substantivo", ["fica sozinho, sem o substantivo", "vem antes do substantivo", "não existe"]),
                ],
            ),
            topic(
                "conjuncoes-basicas",
                "Conjunções básicas",
                """
# Conjunções básicas

As **conjunções** ligam ideias dentro da frase.

| Conjunção | Função | Exemplo |
|---|---|---|
| **and** | soma (e) | I like tea and coffee. |
| **but** | contraste (mas) | I like tea, but I don't like coffee. |
| **or** | escolha (ou) | Do you want tea or coffee? |
| **because** | causa (porque) | I stay home because it is cold. |
| **so** | consequência (então) | It was raining, so we stayed home. |

## Exemplos

```
I like music and movies.          Eu gosto de música e filmes.
She is tired, so she is sleeping. Ela está cansada, então está dormindo.
```

> 💡 **but** introduz uma ideia oposta; **so** introduz um resultado. As duas
> costumam vir separadas por vírgula antes da segunda ideia.
""",
                [
                    ex("quiz", 'Complete: "I like tea ___ coffee." (e)',
                       "and", ["and", "but", "or"]),
                    ex("quiz", 'Complete: "I like tea, ___ I don\'t like coffee." (mas)',
                       "but", ["but", "and", "or"]),
                    ex("text", "Traduza: Estou cansado, então vou dormir.",
                       "i am tired so i will sleep"),
                    ex("quiz", 'Complete a escolha: "Do you want tea ___ coffee?"',
                       "or", ["or", "and", "but"]),
                    ex("audio", "Escute e transcreva:",
                       "i like music and movies", audio_text="I like music and movies."),
                    ex("quiz", 'Complete: "It was raining, ___ we stayed home." (então)',
                       "so", ["so", "but", "or"]),
                ],
            ),
        ],
    )


# ============================================================
# MODULO 6 - Vocabulario - A2
# ============================================================

@_expand_target_builder
def build_modulo_06_vocabulario_a2():
    return module(
        "modulo-06-vocabulario-a2",
        "Módulo 6 — Ampliação de Vocabulário — A2",
        "Vocabulário para o mundo real: viagem, profissões, educação, saúde, tecnologia, entretenimento, relacionamentos, dinheiro, compras, restaurante, hotel, transporte, natureza, cidade e problemas do dia a dia.",
        [
            topic(
                "viagem",
                "Viagem",
                """
# Viagem

## Vocabulário essencial

| Inglês | Português |
|---|---|
| trip | viagem |
| to travel | viajar |
| luggage | bagagem |
| ticket | bilhete / passagem |
| passport | passaporte |
| map | mapa |
| flight | voo |

## Exemplos

```
We are planning a trip.       Estamos planejando uma viagem.
I need my passport.           Eu preciso do meu passaporte.
I like to travel.             Eu gosto de viajar.
```

> 💡 **trip** é a viagem (substantivo); **travel** é o verbo viajar:
> "I like to travel" e "It is a long trip".
""",
                [
                    ex("quiz", "Como se diz 'viagem' em inglês?",
                       "trip", ["trip", "ticket", "luggage"]),
                    ex("quiz", "Como se diz 'passaporte' em inglês?",
                       "passport", ["passport", "ticket", "map"]),
                    ex("text", "Traduza: Eu gosto de viajar.",
                       "i like to travel"),
                    ex("quiz", "Como se diz 'bagagem' em inglês?",
                       "luggage", ["luggage", "ticket", "flight"]),
                    ex("audio", "Escute e transcreva:",
                       "we are planning a trip", audio_text="We are planning a trip."),
                    ex("quiz", "Como se diz 'bilhete/passagem' em inglês?",
                       "ticket", ["ticket", "passport", "map"]),
                ],
            ),
            topic(
                "profissoes",
                "Profissões",
                """
# Profissões

Ampliando o vocabulário de profissões do Módulo 3.

| Inglês | Português |
|---|---|
| lawyer | advogado(a) |
| accountant | contador(a) |
| mechanic | mecânico |
| dentist | dentista |
| pilot | piloto |
| photographer | fotógrafo(a) |
| waiter | garçom |
| actor | ator |
| firefighter | bombeiro |

## Exemplos

```
He is a pilot.                Ele é piloto.
She works as a photographer.  Ela trabalha como fotógrafa.
```

> 💡 Com profissões, use **a/an**: "He is a pilot." — e o verbo **work as**
> para "trabalhar como".
""",
                [
                    ex("quiz", "Como se diz 'advogado' em inglês?",
                       "lawyer", ["lawyer", "accountant", "mechanic"]),
                    ex("quiz", "Como se diz 'dentista' em inglês?",
                       "dentist", ["dentist", "pilot", "waiter"]),
                    ex("text", "Traduza: Ele é piloto.",
                       "he is a pilot"),
                    ex("quiz", "Como se diz 'mecânico' em inglês?",
                       "mechanic", ["mechanic", "lawyer", "dentist"]),
                    ex("audio", "Escute e transcreva:",
                       "she works as a photographer", audio_text="She works as a photographer."),
                    ex("quiz", "Como se diz 'garçom' em inglês?",
                       "waiter", ["waiter", "actor", "firefighter"]),
                ],
            ),
            topic(
                "educacao",
                "Educação",
                """
# Educação

## Vocabulário de estudos

| Inglês | Português |
|---|---|
| subject | matéria (disciplina) |
| math | matemática |
| history | história |
| science | ciência |
| university | universidade |
| degree | diploma / curso superior |
| exam | prova / exame |
| class | aula |
| to learn | aprender |

## Exemplos

```
I study at the university.        Eu estudo na universidade.
History is my favorite subject.   História é minha matéria favorita.
I have an exam tomorrow.          Eu tenho prova amanhã.
```

> 💡 **class** pode ser "aula" ("I have class") ou "turma". **subject** é a
> disciplina em si (matemática, história...).
""",
                [
                    ex("quiz", "Como se diz 'matemática' em inglês?",
                       "math", ["math", "history", "science"]),
                    ex("quiz", "Como se diz 'universidade' em inglês?",
                       "university", ["university", "degree", "exam"]),
                    ex("text", "Traduza: Eu estudo na universidade.",
                       "i study at the university"),
                    ex("quiz", "Como se diz 'prova/exame' em inglês?",
                       "exam", ["exam", "class", "subject"]),
                    ex("audio", "Escute e transcreva:",
                       "history is my favorite subject", audio_text="History is my favorite subject."),
                    ex("quiz", "Como se diz 'matéria' (disciplina) em inglês?",
                       "subject", ["subject", "knowledge", "degree"]),
                ],
            ),
            topic(
                "saude",
                "Saúde",
                """
# Saúde

## Vocabulário de saúde

| Inglês | Português |
|---|---|
| medicine | remédio |
| sick | doente |
| healthy | saudável |
| headache | dor de cabeça |
| cold | resfriado |
| flu | gripe |
| pain | dor |
| appointment | consulta |

## Exemplos

```
I have a headache.           Eu estou com dor de cabeça.
I need to see a doctor.      Eu preciso ir ao médico.
Take this medicine.          Tome este remédio.
```

> 💡 "Estou com dor de cabeça" = **I have a headache** (não "I am a
> headache"!). **sick** = doente; **healthy** = saudável.
""",
                [
                    ex("quiz", "Como se diz 'remédio' em inglês?",
                       "medicine", ["medicine", "cold", "flu"]),
                    ex("quiz", "Como se diz 'doente' em inglês?",
                       "sick", ["sick", "healthy", "pain"]),
                    ex("text", "Traduza: Eu estou com dor de cabeça.",
                       "i have a headache"),
                    ex("quiz", "Como se diz 'resfriado' em inglês?",
                       "cold", ["cold", "flu", "pain"]),
                    ex("audio", "Escute e transcreva:",
                       "i need to see a doctor", audio_text="I need to see a doctor."),
                    ex("quiz", "Como se diz 'gripe' em inglês?",
                       "flu", ["flu", "cold", "medicine"]),
                ],
            ),
            topic(
                "tecnologia",
                "Tecnologia",
                """
# Tecnologia

| Inglês | Português |
|---|---|
| computer | computador |
| laptop | notebook |
| phone | celular |
| tablet | tablet |
| internet | internet |
| app | aplicativo |
| website | site |
| screen | tela |
| battery | bateria |
| email | e-mail |

## Exemplos

```
I use the computer at work.    Eu uso o computador no trabalho.
My phone is new.               Meu celular é novo.
The battery is low.            A bateria está fraca.
```

> 💡 **phone** sozinho costuma significar "celular". Para "telefone fixo",
> use **landline**.
""",
                [
                    ex("quiz", "Como se diz 'celular' em inglês?",
                       "phone", ["phone", "laptop", "tablet"]),
                    ex("quiz", "Como se diz 'internet' em inglês?",
                       "internet", ["internet", "app", "screen"]),
                    ex("text", "Traduza: Eu uso o computador no trabalho.",
                       "i use the computer at work"),
                    ex("quiz", "Como se diz 'bateria' em inglês?",
                       "battery", ["battery", "screen", "app"]),
                    ex("audio", "Escute e transcreva:",
                       "my phone is new", audio_text="My phone is new."),
                    ex("quiz", "Como se diz 'site' em inglês?",
                       "website", ["website", "email", "app"]),
                ],
            ),
            topic(
                "entretenimento",
                "Entretenimento",
                """
# Entretenimento

| Inglês | Português |
|---|---|
| movie | filme |
| series | série |
| music | música |
| game | jogo |
| concert | show musical |
| show | espetáculo |
| theater | teatro |
| party | festa |

## Exemplos

```
I like action movies.         Eu gosto de filmes de ação.
We went to a concert.         Nós fomos a um show.
Let's watch a series.         Vamos assistir uma série.
```

> 💡 **movie** é "filme" (americano); em inglês britânico, usa-se
> **film**. **show** é um espetáculo em geral.
""",
                [
                    ex("quiz", "Como se diz 'filme' em inglês?",
                       "movie", ["movie", "series", "show"]),
                    ex("quiz", "Como se diz 'música' em inglês?",
                       "music", ["music", "concert", "party"]),
                    ex("text", "Traduza: Eu gosto de filmes de ação.",
                       "i like action movies"),
                    ex("quiz", "Como se diz 'show musical' em inglês?",
                       "concert", ["concert", "theater", "game"]),
                    ex("audio", "Escute e transcreva:",
                       "we went to a concert", audio_text="We went to a concert."),
                    ex("quiz", "Como se diz 'festa' em inglês?",
                       "party", ["party", "concert", "theater"]),
                ],
            ),
            topic(
                "relacionamentos",
                "Relacionamentos",
                """
# Relacionamentos

| Inglês | Português |
|---|---|
| friend | amigo(a) |
| best friend | melhor amigo(a) |
| boyfriend | namorado |
| girlfriend | namorada |
| husband | marido |
| wife | esposa |
| colleague | colega de trabalho |
| neighbor | vizinho(a) |
| relationship | relacionamento |

## Exemplos

```
She is my best friend.      Ela é minha melhor amiga.
He is my boyfriend.         Ele é meu namorado.
She is my colleague.        Ela é minha colega de trabalho.
```

> 💡 **colleague** = colega de **trabalho**; **classmate** = colega de
> **classe**; **neighbor** = vizinho.
""",
                [
                    ex("quiz", "Como se diz 'namorada' em inglês?",
                       "girlfriend", ["girlfriend", "boyfriend", "colleague"]),
                    ex("quiz", "Como se diz 'vizinho' em inglês?",
                       "neighbor", ["neighbor", "friend", "partner"]),
                    ex("text", "Traduza: Ela é minha melhor amiga.",
                       "she is my best friend"),
                    ex("quiz", "Como se diz 'colega de trabalho' em inglês?",
                       "colleague", ["colleague", "neighbor", "girlfriend"]),
                    ex("audio", "Escute e transcreva:",
                       "he is my boyfriend", audio_text="He is my boyfriend."),
                    ex("quiz", "Como se diz 'relacionamento' em inglês?",
                       "relationship", ["relationship", "friendship", "meeting"]),
                ],
            ),
            topic(
                "dinheiro",
                "Dinheiro",
                """
# Dinheiro

| Inglês | Português |
|---|---|
| money | dinheiro |
| cash | dinheiro em espécie |
| card | cartão |
| credit card | cartão de crédito |
| wallet | carteira |
| change | troco |
| price | preço |
| cost | custo |
| to pay | pagar |

## Exemplos

```
Can you pay by card?          Você pode pagar com cartão?
Do you have any cash?         Você tem dinheiro em espécie?
Here is your change.          Aqui está seu troco.
```

> 💡 **change** tem dois sentidos: "mudança" e "troco". No contexto de
> pagamento, é sempre o troco.
""",
                [
                    ex("quiz", "Como se diz 'dinheiro em espécie' em inglês?",
                       "cash", ["cash", "card", "wallet"]),
                    ex("quiz", "Como se diz 'carteira' (de dinheiro) em inglês?",
                       "wallet", ["wallet", "cash", "change"]),
                    ex("text", "Traduza: Você pode pagar com cartão?",
                        "can you pay by card"),
                    ex("quiz", "Como se diz 'troco' em inglês?",
                       "change", ["change", "price", "cost"]),
                    ex("audio", "Escute e transcreva:",
                       "do you have any cash", audio_text="Do you have any cash?"),
                    ex("quiz", "Como se diz 'cartão de crédito' em inglês?",
                       "credit card", ["credit card", "debit note", "cash card"]),
                ],
            ),
            topic(
                "compras-e-pagamentos",
                "Compras e pagamentos",
                """
# Compras e pagamentos

| Inglês | Português |
|---|---|
| discount | desconto |
| receipt | recibo |
| size | tamanho |
| to try on | experimentar (roupa) |
| refund | reembolso/devolução |
| to return | devolver |
| cashier | caixa (pessoa) |

## Exemplos

```
Can I try it on?            Posso experimentar?
The shirt is too small.     A camisa é pequena demais.
I want a refund.            Eu quero o reembolso.
```

> 💡 **too + adjetivo** = "demais": too big (grande demais), too expensive
> (caro demais). Para pedir outro tamanho: "Do you have a bigger size?"
""",
                [
                    ex("quiz", "Como se diz 'desconto' em inglês?",
                       "discount", ["discount", "receipt", "refund"]),
                    ex("quiz", "Como se diz 'recibo' em inglês?",
                       "receipt", ["receipt", "discount", "size"]),
                    ex("text", "Traduza: Posso experimentar?",
                       "can i try it on"),
                    ex("quiz", "Como se diz 'reembolso' em inglês?",
                       "refund", ["refund", "receipt", "discount"]),
                    ex("audio", "Escute e transcreva:",
                       "the shirt is too small", audio_text="The shirt is too small."),
                    ex("quiz", "Como se diz 'tamanho' (de roupa) em inglês?",
                       "size", ["size", "color", "price"]),
                ],
            ),
            topic(
                "no-restaurante",
                "No restaurante",
                """
# No restaurante

| Inglês | Português |
|---|---|
| to order | pedir |
| dish | prato |
| meal | refeição |
| dessert | sobremesa |
| appetizer | entrada (aperitivo) |
| drink | bebida |
| reservation | reserva |
| tip | gorjeta |

## Exemplos

```
I want to make a reservation.      Eu quero fazer uma reserva.
I would like to order now.         Eu gostaria de pedir agora.
The dessert is delicious.          A sobremesa é deliciosa.
```

> 💡 **to order** = pedir (no restaurante); **tip** = gorjeta (em inglês
> britânico, também é "dica"). **dish** = o prato de comida.
""",
                [
                    ex("quiz", "Como se diz 'pedir' (no restaurante) em inglês?",
                       "order", ["order", "serve", "cook"]),
                    ex("quiz", "Como se diz 'sobremesa' em inglês?",
                       "dessert", ["dessert", "appetizer", "drink"]),
                    ex("text", "Traduza: Eu quero fazer uma reserva.",
                       "i want to make a reservation"),
                    ex("quiz", "Como se diz 'prato' (comida servida) em inglês?",
                       "dish", ["dish", "menu", "tip"]),
                    ex("audio", "Escute e transcreva:",
                       "i would like to order now", audio_text="I would like to order now."),
                    ex("quiz", "Como se diz 'gorjeta' em inglês?",
                       "tip", ["tip", "bill", "waiter"]),
                ],
            ),
            topic(
                "hoteis",
                "Hotéis",
                """
# Hotéis

| Inglês | Português |
|---|---|
| hotel | hotel |
| room | quarto |
| single room | quarto de solteiro |
| double room | quarto de casal |
| key | chave |
| reservation | reserva |
| check-in | check-in (entrada) |
| check-out | check-out (saída) |
| breakfast | café da manhã |
| reception | recepção |

## Exemplos

```
I have a reservation.              Eu tenho uma reserva.
I want a double room.              Eu quero um quarto de casal.
Breakfast is included.             O café da manhã está incluído.
```

> 💡 **check-in / check-out** são usados em inglês também no Brasil, mas
> cuidado: "fazer check-in" = **check in** (sem hífen quando verbo).
""",
                [
                    ex("quiz", "Como se diz 'fazer check-in' em inglês?",
                       "check in", ["check in", "check out", "reception"]),
                    ex("quiz", "Como se diz 'café da manhã' em inglês?",
                       "breakfast", ["breakfast", "lunch", "dinner"]),
                    ex("text", "Traduza: Eu tenho uma reserva.",
                       "i have a reservation"),
                    ex("quiz", "Como se diz 'quarto de casal' em inglês?",
                       "double room", ["double room", "single room", "elevator"]),
                    ex("audio", "Escute e transcreva:",
                       "the room is on the second floor", audio_text="The room is on the second floor."),
                    ex("quiz", "Como se diz 'recepção' (do hotel) em inglês?",
                       "reception", ["reception", "elevator", "key"]),
                ],
            ),
            topic(
                "transporte",
                "Transporte (ampliado)",
                """
# Transporte (ampliado)

Ampliando o vocabulário de transporte do Módulo 3, agora com foco em
viagens de trem, avião e ônibus.

| Inglês | Português |
|---|---|
| ticket | bilhete |
| platform | plataforma |
| gate | portão (aeroporto) |
| schedule | horário |
| departure | partida |
| arrival | chegada |
| delay | atraso |
| station | estação |
| airport | aeroporto |
| fare | tarifa / preço da passagem |

## Exemplos

```
The train is delayed.         O trem está atrasado.
The flight is delayed.        O voo está atrasado.
The bus is on time.           O ônibus está na hora.
```

> 💡 **on time** = na hora certa; **late** = atrasado; **delayed** = atrasado
> (para transportes).
""",
                [
                    ex("quiz", "Como se diz 'plataforma' (de trem) em inglês?",
                       "platform", ["platform", "gate", "fare"]),
                    ex("quiz", "Como se diz 'chegada' em inglês?",
                       "arrival", ["arrival", "departure", "delay"]),
                    ex("text", "Traduza: O trem está atrasado.",
                       "the train is delayed"),
                    ex("quiz", "Como se diz 'partida/saída' em inglês?",
                       "departure", ["departure", "arrival", "platform"]),
                    ex("audio", "Escute e transcreva:",
                       "the flight is delayed", audio_text="The flight is delayed."),
                    ex("quiz", "Como se diz 'horário' (de transporte) em inglês?",
                       "schedule", ["schedule", "fare", "gate"]),
                ],
            ),
            topic(
                "natureza",
                "Natureza",
                """
# Natureza

| Inglês | Português |
|---|---|
| nature | natureza |
| mountain | montanha |
| river | rio |
| ocean | oceano |
| sea | mar |
| forest | floresta |
| beach | praia |
| tree | árvore |
| flower | flor |
| animal | animal |
| sky | céu |

## Exemplos

```
I like nature.               Eu gosto da natureza.
The river is very long.      O rio é muito comprido.
Let's go to the beach.       Vamos à praia.
```

> 💡 **sea** é o "mar"; **ocean** é o oceano. Na praia, dizemos "the beach";
> na montanha, "the mountains" (geralmente no plural).
""",
                [
                    ex("quiz", "Como se diz 'montanha' em inglês?",
                       "mountain", ["mountain", "river", "forest"]),
                    ex("quiz", "Como se diz 'praia' em inglês?",
                       "beach", ["beach", "ocean", "tree"]),
                    ex("text", "Traduza: Eu gosto da natureza.",
                       "i like nature"),
                    ex("quiz", "Como se diz 'floresta' em inglês?",
                       "forest", ["forest", "mountain", "beach"]),
                    ex("audio", "Escute e transcreva:",
                       "the river is very long", audio_text="The river is very long."),
                    ex("quiz", "Como se diz 'animal' em inglês?",
                       "animal", ["animal", "flower", "sky"]),
                ],
            ),
            topic(
                "cidade-e-interior",
                "Cidade e interior",
                """
# Cidade e interior

| Inglês | Português |
|---|---|
| city | cidade |
| downtown | centro da cidade |
| suburb | subúrbio |
| countryside | interior / zona rural |
| village | vila |
| traffic | trânsito |
| pollution | poluição |
| crowd | multidão |
| quiet | quieto / calmo |

## Exemplos

```
I live in the countryside.      Eu moro no interior.
The city is very busy.          A cidade é muito movimentada.
The countryside is very quiet.  O interior é muito tranquilo.
```

> 💡 **city** vs **town**: city é uma cidade grande; town é uma cidade
> pequena. **countryside** é a zona rural (interior).
""",
                [
                    ex("quiz", "Como se diz 'centro da cidade' em inglês?",
                       "downtown", ["downtown", "suburb", "village"]),
                    ex("quiz", "Como se diz 'interior' (zona rural) em inglês?",
                       "countryside", ["countryside", "downtown", "suburb"]),
                    ex("text", "Traduza: Eu moro no interior.",
                       "i live in the countryside"),
                    ex("quiz", "Como se diz 'trânsito' em inglês?",
                       "traffic", ["traffic", "pollution", "crowd"]),
                    ex("audio", "Escute e transcreva:",
                       "the countryside is very quiet", audio_text="The countryside is very quiet."),
                    ex("quiz", "Como se diz 'vila' em inglês?",
                       "village", ["village", "downtown", "traffic"]),
                ],
            ),
            topic(
                "problemas-do-dia-a-dia",
                "Problemas do dia a dia",
                """
# Problemas do dia a dia

| Inglês | Português |
|---|---|
| problem | problema |
| broken | quebrado |
| lost | perdido |
| stuck | preso |
| to fix | consertar |
| to repair | reparar |
| late | atrasado |
| queue | fila |
| traffic jam | engarrafamento |

## Exemplos

```
My car is broken.           Meu carro está quebrado.
I am stuck in traffic.      Estou preso no trânsito.
Can you fix it?             Você pode consertar?
```

> 💡 **broken** = quebrado; **lost** = perdido; **stuck** = preso/travado.
> Três adjetivos muito usados em reclamações do dia a dia.
""",
                [
                    ex("quiz", "Como se diz 'quebrado' em inglês?",
                       "broken", ["broken", "lost", "stuck"]),
                    ex("quiz", "Como se diz 'perdido' (objeto) em inglês?",
                       "lost", ["lost", "broken", "late"]),
                    ex("text", "Traduza: Meu carro está quebrado.",
                       "my car is broken"),
                    ex("quiz", "Como se diz 'consertar' em inglês?",
                       "fix", ["fix", "lose", "break"]),
                    ex("audio", "Escute e transcreva:",
                       "i am stuck in traffic", audio_text="I am stuck in traffic."),
                    ex("quiz", "Como se diz 'atrasado' em inglês?",
                       "late", ["late", "lost", "broken"]),
                ],
            ),
        ],
    )


# ============================================================
# MODULO 7 - Comunicacao - A2
# ============================================================

@_expand_target_builder
def build_modulo_07_comunicacao_a2():
    return module(
        "modulo-07-comunicacao-a2",
        "Módulo 7 — Comunicação — A2",
        "Conversar de verdade: falar do passado e de planos, descrever pessoas e lugares, convidar, aceitar, recusar, sugerir, aconselhar, pedir ajuda, reclamar, contar experiências e dar opiniões.",
        [
            topic(
                "falando-sobre-o-passado",
                "Falando sobre o passado",
                """
# Falando sobre o passado

Para contar o que aconteceu, use o **passado simples** (Módulo 5) com
marcadores de tempo.

## Marcadores de passado

```
yesterday         ontem
last week         semana passada
last month        mês passado
two days ago      há dois dias
```

## Exemplos

```
Yesterday I went to the cinema.        Ontem eu fui ao cinema.
Last weekend I worked.                 No fim de semana passado eu trabalhei.
We visited my grandmother last month.  Nós visitamos minha avó mês passado.
```

> 💡 **ago** = "há (tempo atrás)": "two days ago" (há dois dias), "a year
> ago" (há um ano). É o marcador clássico do passado.
""",
                [
                    ex("quiz", "Como dizer 'Ontem eu fui ao cinema'?",
                       "Yesterday I went to the cinema.", ["Yesterday I went to the cinema.", "Yesterday I go to the cinema.", "Yesterday I going to the cinema."]),
                    ex("text", "Traduza: No fim de semana passado eu trabalhei.",
                       "last weekend i worked"),
                    ex("quiz", "Qual expressão indica PASSADO?",
                       "last week", ["last week", "next week", "tomorrow"]),
                    ex("audio", "Escute e transcreva:",
                       "we visited my grandmother last month", audio_text="We visited my grandmother last month."),
                    ex("quiz", "'Two days ago' significa:",
                       "há dois dias", ["há dois dias", "em dois dias", "daqui a dois dias"]),
                    ex("text", "Traduza: Eu almocei às 12.",
                       "i had lunch at 12"),
                ],
            ),
            topic(
                "falando-de-planos-futuros",
                "Falando de planos futuros",
                """
# Falando de planos futuros

Use **going to** para planos decididos e **will** para decisões na hora
(Módulo 5), com os marcadores de futuro.

## Marcadores de futuro

```
tomorrow          amanhã
next week         semana que vem
next month        mês que vem
this weekend      neste fim de semana
```

## Exemplos

```
Tomorrow I'm going to travel.            Amanhã eu vou viajar.
Next month I'm going to start a course.  Mês que vem eu vou começar um curso.
We're going to have a party this weekend.  Nós vamos fazer uma festa neste fim de semana.
```

> 💡 **will** aparece em decisões tomadas na hora ("OK, I'll call you") e em
> previsões; **going to** aparece quando o plano já existia.
""",
                [
                    ex("quiz", "Como dizer 'Amanhã eu vou viajar'?",
                       "Tomorrow I'm going to travel.", ["Tomorrow I'm going to travel.", "Tomorrow I traveled.", "Tomorrow I travel yesterday."]),
                    ex("text", "Traduza: Mês que vem eu vou começar um curso.",
                       "next month i am going to start a course"),
                    ex("quiz", "Qual expressão indica FUTURO?",
                       "next week", ["next week", "last week", "yesterday"]),
                    ex("audio", "Escute e transcreva:",
                       "i am going to buy a new phone", audio_text="I am going to buy a new phone."),
                    ex("quiz", "Para uma decisão tomada NA HORA, usamos:",
                       "will", ["will", "going to", "past simple"]),
                    ex("text", "Traduza: Nós vamos fazer uma festa neste fim de semana.",
                       "we are going to have a party this weekend"),
                ],
            ),
            topic(
                "descrevendo-pessoas",
                "Descrevendo pessoas",
                """
# Descrevendo pessoas

## Aparência

```
He is tall.        Ele é alto.        He is short.  Ele é baixo.
She has long hair.  Ela tem cabelo longo.
```

| Inglês | Português |
|---|---|
| tall / short | alto / baixo |
| long / short hair | cabelo longo / curto |
| young / old | jovem / velho |

## Personalidade

| Inglês | Português |
|---|---|
| friendly | simpático |
| funny | engraçado |
| kind | gentil |
| shy | tímido |
| serious | sério |
| hardworking | trabalhador |

## Exemplos

```
He is friendly.           Ele é simpático.
My sister is very kind.   Minha irmã é muito gentil.
```

> 💡 Para a aparência, use **to be** + adjetivo ("He is tall") e **have** +
> característica ("She has long hair") — não diga "He is long" para cabelo!
""",
                [
                    ex("quiz", "Como descrever alguém ALTO?",
                       "He is tall.", ["He is tall.", "He is short.", "He is long."]),
                    ex("quiz", "Como dizer 'Ela tem cabelo longo'?",
                       "She has long hair.", ["She has long hair.", "She is long hair.", "She has hair long."]),
                    ex("text", "Traduza: Ele é simpático.",
                       "he is friendly"),
                    ex("quiz", "Qual adjetivo descreve alguém ENGRAÇADO?",
                       "funny", ["funny", "shy", "serious"]),
                    ex("audio", "Escute e transcreva:",
                       "my sister is very kind", audio_text="My sister is very kind."),
                    ex("quiz", "Qual adjetivo é o oposto de 'tall'?",
                       "short", ["short", "long", "young"]),
                ],
            ),
            topic(
                "descrevendo-lugares",
                "Descrevendo lugares",
                """
# Descrevendo lugares

| Inglês | Português |
|---|---|
| beautiful | lindo |
| crowded | lotado / cheio de gente |
| quiet | tranquilo |
| noisy | barulhento |
| modern | moderno |
| safe | seguro |
| dangerous | perigoso |
| clean | limpo |

## Exemplos

```
The city is noisy.          A cidade é barulhenta.
The beach is beautiful.     A praia é linda.
There are many parks here.  Há muitos parques aqui.
```

> 💡 Para descrever um lugar, combine **to be** + adjetivo e **there is/are**
> para o que existe nele: "It is beautiful and there are many restaurants."
""",
                [
                    ex("quiz", "Como dizer 'A cidade é barulhenta'?",
                       "The city is noisy.", ["The city is noisy.", "The city is quiet.", "The city is safe."]),
                    ex("quiz", "Qual adjetivo descreve um lugar CHEIO DE GENTE?",
                       "crowded", ["crowded", "empty", "quiet"]),
                    ex("text", "Traduza: A praia é linda.",
                       "the beach is beautiful"),
                    ex("quiz", "Qual é o oposto de 'safe' (seguro)?",
                       "dangerous", ["dangerous", "clean", "modern"]),
                    ex("audio", "Escute e transcreva:",
                       "the restaurant is very modern", audio_text="The restaurant is very modern."),
                    ex("quiz", "Como dizer 'Há muitos parques aqui'?",
                       "There are many parks here.", ["There are many parks here.", "There is many parks here.", "There are much parks here."]),
                ],
            ),
            topic(
                "fazendo-convites",
                "Fazendo convites",
                """
# Fazendo convites

## Do you want to...?

```
Do you want to go to the movies?      Você quer ir ao cinema?
Do you want to have lunch with me?    Você quer almoçar comigo?
```

## Would you like to...? (mais educado)

```
Would you like to come?               Você gostaria de vir?
```

## Let's... (sugestão amigável)

```
Let's watch a movie.                  Vamos assistir um filme.
```

> 💡 **Do you want to...?** é o convite padrão. **Would you like to...?** é a
> versão mais educada. **Let's...** propõe fazermos algo juntos.
""",
                [
                    ex("quiz", "Como convidar alguém para ir ao cinema?",
                       "Do you want to go to the movies?", ["Do you want to go to the movies?", "You go to the movies?", "I go to the movies."]),
                    ex("text", "Traduza: Você quer dançar?",
                       "do you want to dance"),
                    ex("quiz", "Qual é um convite EDUCADO?",
                       "Would you like to come?", ["Would you like to come?", "Come now!", "You must come."]),
                    ex("audio", "Escute e transcreva:",
                       "do you want to have lunch with me", audio_text="Do you want to have lunch with me?"),
                    ex("quiz", "O que 'Let's watch a movie' propõe?",
                       "Vamos assistir um filme", ["Vamos assistir um filme", "Eu assisto um filme", "Ele assistiu um filme"]),
                    ex("quiz", "Qual convite soa como uma SUGESTÃO amigável?",
                       "Let's go!", ["Let's go!", "Go now!", "Leave!"]),
                ],
            ),
            topic(
                "aceitando-convites",
                "Aceitando convites",
                """
# Aceitando convites

Quando você quer aceitar um convite, mostre entusiasmo.

## Formas de aceitar

```
Yes, I'd love to!            Sim, eu adoraria!
Sure!                        Claro!
That sounds good.            Isso parece bom.
Great idea!                  Ótima ideia!
Why not?                     Por que não?
```

## Exemplos

```
Do you want to come?    ->    Yes, I'd love to!
Let's have coffee.      ->    Sure!
```

> 💡 **I'd love to** (de *I would love to*) é a resposta clássica e positiva.
> **That sounds good** funciona em qualquer contexto.
""",
                [
                    ex("quiz", "Como aceitar um convite com entusiasmo?",
                       "Yes, I'd love to!", ["Yes, I'd love to!", "No, thanks.", "Maybe later."]),
                    ex("text", "Traduza: Claro!",
                       "sure"),
                    ex("quiz", "Qual resposta ACEITA o convite?",
                       "That sounds good.", ["That sounds good.", "I'm busy.", "No, thanks."]),
                    ex("audio", "Escute e transcreva:",
                       "yes i would love to come", audio_text="Yes, I would love to come."),
                    ex("quiz", "O que 'Great idea!' significa?",
                       "Ótima ideia!", ["Ótima ideia!", "Não dá.", "Que pena."]),
                    ex("text", "Traduza: Ótima ideia!",
                       "great idea"),
                ],
            ),
            topic(
                "recusando-educadamente",
                "Recusando educadamente",
                """
# Recusando educadamente

Recusar com educação é uma habilidade essencial. Sempre comece com um
"obrigado/gostaria, mas" e ofereça um motivo.

## Formas de recusar

```
I'd love to, but I'm busy.       Eu adoraria, mas estou ocupado.
I'm afraid I can't.              Infelizmente, não posso.
Maybe next time.                 Talvez na próxima.
Sorry, I can't make it.          Desculpe, não vou conseguir.
```

## Exemplos

```
Do you want to come?    ->    I'd love to, but I have to work.
Let's go out.           ->    I'm sorry, I'm tired.
```

> 💡 **I'm afraid I can't** não significa "tenho medo" — é "infelizmente,
> não posso". É a recusa mais educada do inglês.
""",
                [
                    ex("quiz", "Como recusar educadamente?",
                       "I'd love to, but I'm busy.", ["I'd love to, but I'm busy.", "No, I don't want.", "Leave me alone."]),
                    ex("text", "Traduza: Desculpe, estou ocupado.",
                       "sorry i am busy"),
                    ex("quiz", "Qual resposta é uma recusa EDUCADA?",
                       "I'm afraid I can't.", ["I'm afraid I can't.", "Never.", "No way."]),
                    ex("audio", "Escute e transcreva:",
                       "maybe next time", audio_text="Maybe next time."),
                    ex("quiz", "O que 'I'm afraid I can't' significa?",
                       "Infelizmente, não posso", ["Infelizmente, não posso", "Tenho medo e não posso", "Não tenho medo"]),
                    ex("quiz", "Qual resposta NÃO é educada?",
                       "No way!", ["No way!", "Maybe next time.", "I'm sorry, I can't."]),
                ],
            ),
            topic(
                "fazendo-sugestoes",
                "Fazendo sugestões",
                """
# Fazendo sugestões

## Como sugerir

```
Why don't we go to the park?     Por que não vamos ao parque?
How about a coffee?              Que tal um café?
What about a movie?              Que tal um filme?
Let's study together.            Vamos estudar juntos.
```

> 💡 **Why don't we...?** e **Let's...** são as formas mais comuns. **How
> about / What about + substantivo** sugere uma coisa específica.
""",
                [
                    ex("quiz", "Como sugerir algo?",
                       "Why don't we go to the park?", ["Why don't we go to the park?", "You must go to the park.", "I went to the park."]),
                    ex("text", "Traduza: Que tal pizza?",
                       "how about pizza"),
                    ex("quiz", "O que 'How about a coffee?' significa?",
                       "Que tal um café?", ["Que tal um café?", "Quanto custa o café?", "Onde fica o café?"]),
                    ex("audio", "Escute e transcreva:",
                       "why don't we watch a movie", audio_text="Why don't we watch a movie?"),
                    ex("quiz", "Qual frase faz uma SUGESTÃO?",
                       "Let's study together.", ["Let's study together.", "I study alone.", "He studies a lot."]),
                    ex("quiz", "Qual é o sentido de 'Let's...' nas sugestões?",
                       "vamos...", ["vamos...", "eu vou...", "ele vai..."]),
                ],
            ),
            topic(
                "dando-conselhos",
                "Dando conselhos",
                """
# Dando conselhos

## You should...

**should** + verbo base = "você deveria" (conselho).

```
You should see a doctor.        Você deveria ir ao médico.
You should rest.                Você deveria descansar.
You should try this restaurant. Você deveria experimentar este restaurante.
```

## Outra forma: Why don't you...?

```
Why don't you call her?         Por que você não liga para ela?
```

> 💡 Depois de **should**, o verbo NÃO muda: "You should studies" está
> errado — o certo é "You should study".
""",
                [
                    ex("quiz", "Como dar um conselho?",
                       "You should see a doctor.", ["You should see a doctor.", "You see a doctor.", "You are a doctor."]),
                    ex("text", "Traduza: Você deveria descansar.",
                       "you should rest"),
                    ex("quiz", "Qual frase dá um CONSELHO?",
                       "You should study more.", ["You should study more.", "You study every day.", "I studied yesterday."]),
                    ex("audio", "Escute e transcreva:",
                       "you should try this restaurant", audio_text="You should try this restaurant."),
                    ex("quiz", "O que 'Why don't you call her?' aconselha?",
                       "que você ligue para ela", ["que você ligue para ela", "que você não ligue para ela", "que eu ligue para ela"]),
                    ex("quiz", "Depois de 'should', o verbo fica:",
                       "na forma base", ["na forma base", "com -s", "no passado"]),
                ],
            ),
            topic(
                "pedindo-ajuda",
                "Pedindo ajuda",
                """
# Pedindo ajuda

## Formas de pedir

```
Can you help me, please?        Você pode me ajudar, por favor?
Could you help me?              Você poderia me ajudar? (mais educado)
Can you do me a favor?          Você pode me fazer um favor?
I need help with the homework.  Eu preciso de ajuda com a lição.
```

## Respondendo

```
Sure! / Of course!              Claro!
Yes, no problem.                Sim, sem problema.
```

> 💡 **Could you...?** é a versão mais educada de **Can you...?**. Use **with**
> para dizer com o quê: "help me with this", "help with my homework".
""",
                [
                    ex("quiz", "Como pedir ajuda de forma educada?",
                       "Could you help me, please?", ["Could you help me, please?", "Help me now!", "You help me."]),
                    ex("text", "Traduza: Eu preciso de ajuda com a lição.",
                       "i need help with the homework"),
                    ex("quiz", "O que 'Can you do me a favor?' significa?",
                       "Você pode me fazer um favor?", ["Você pode me fazer um favor?", "Você pode me pagar?", "Você pode me seguir?"]),
                    ex("audio", "Escute e transcreva:",
                       "could you carry this bag", audio_text="Could you carry this bag?"),
                    ex("quiz", "Qual é um pedido de ajuda?",
                       "Can you help me with this?", ["Can you help me with this?", "I can help you.", "You are helpful."]),
                    ex("text", "Traduza: Obrigado pela ajuda.",
                       "thank you for your help"),
                ],
            ),
            topic(
                "fazendo-reclamacoes",
                "Fazendo reclamações",
                """
# Fazendo reclamações

Reclamar com educação começa com um pedido de desculpas e um problema claro.

## Modelo educado

```
I'm sorry, but there is a problem.     Desculpe, mas há um problema.
The room is dirty.                     O quarto está sujo.
The soup is cold.                      A sopa está fria.
It doesn't work.                       Não funciona.
My order is wrong.                     Meu pedido está errado.
```

> 💡 **It doesn't work** (não funciona) é a reclamação mais comum do dia a
> dia. Começar com **I'm sorry, but...** deixa a reclamação educada.
""",
                [
                    ex("quiz", "Como começar uma reclamação educada?",
                       "I'm sorry, but there is a problem.", ["I'm sorry, but there is a problem.", "This is terrible and you are bad.", "Shut up."]),
                    ex("text", "Traduza: O quarto está sujo.",
                       "the room is dirty"),
                    ex("quiz", "O que 'It doesn't work' significa?",
                       "Não funciona", ["Não funciona", "Funciona bem", "Está caro"]),
                    ex("audio", "Escute e transcreva:",
                       "my order is wrong", audio_text="My order is wrong."),
                    ex("quiz", "Qual frase é uma reclamação?",
                       "The soup is cold.", ["The soup is cold.", "The soup is delicious.", "I love the soup."]),
                    ex("quiz", "Para reclamar educadamente, você começa com:",
                       "I'm sorry, but...", ["I'm sorry, but...", "Hey!", "Listen here."]),
                ],
            ),
            topic(
                "falando-de-experiencias",
                "Falando de experiências",
                """
# Falando de experiências

Para contar experiências passadas, use o **passado simples** (Módulo 5) com
detalhes de quando/onde.

## Exemplos

```
I visited Paris last year.        Eu visitei Paris ano passado.
We saw the Eiffel Tower.          Nós vimos a Torre Eiffel.
I tried Japanese food.            Eu provei comida japonesa.
When I was a child, I swam in the river.  Quando eu era criança, eu nadava no rio.
```

## Perguntando sobre experiências

```
Did you try it?      Você experimentou?
What did you do there?   O que você fez lá?
```

> 💡 Para falar de experiências, os irregulares aparecem muito: **saw** (vi),
> **went** (fui), **had** (tive), **swam** (nadei). Reforce o Módulo 5.
""",
                [
                    ex("quiz", "Como dizer 'Eu visitei Paris no ano passado'?",
                       "I visited Paris last year.", ["I visited Paris last year.", "I visit Paris last year.", "I am visiting Paris last year."]),
                    ex("text", "Traduza: Eu provei comida japonesa.",
                       "i tried japanese food"),
                    ex("quiz", "Para perguntar sobre uma experiência passada:",
                       "Did you try it?", ["Did you try it?", "Do you try it?", "Will you try it?"]),
                    ex("audio", "Escute e transcreva:",
                       "we saw the eiffel tower", audio_text="We saw the Eiffel Tower."),
                    ex("quiz", "O que 'last year' significa?",
                       "ano passado", ["ano passado", "ano que vem", "este ano"]),
                    ex("text", "Traduza: Quando eu era criança, eu nadava no rio.",
                       "when i was a child i swam in the river"),
                ],
            ),
            topic(
                "expressando-opinioes",
                "Expressando opiniões",
                """
# Expressando opiniões

## Dando a sua opinião

```
I think it's great.           Eu acho que é ótimo.
In my opinion, it is very good.   Na minha opinião, é muito bom.
I believe it's a good idea.   Eu acredito que é uma boa ideia.
For me, this is the best.     Para mim, este é o melhor.
```

## Opinião negativa

```
I don't think it's a good idea.   Eu não acho que seja uma boa ideia.
```

## Pedindo a opinião de outra pessoa

```
What do you think?      O que você acha?
```

> 💡 **I think...** é a forma mais comum. Para suavizar, use **I don't
> think...**: "I don't think it's a good idea" em vez de "It's a bad idea".
""",
                [
                    ex("quiz", "Como dar sua opinião?",
                       "I think it's great.", ["I think it's great.", "It is great, I think not.", "Great it is."]),
                    ex("text", "Traduza: Na minha opinião, é muito bom.",
                       "in my opinion it is very good"),
                    ex("quiz", "O que 'I believe...' significa?",
                       "Eu acredito que...", ["Eu acredito que...", "Eu não acredito.", "Eu duvido que..."]),
                    ex("audio", "Escute e transcreva:",
                       "i think this movie is great", audio_text="I think this movie is great."),
                    ex("quiz", "Como expressar uma opinião NEGATIVA?",
                       "I don't think it's a good idea.", ["I don't think it's a good idea.", "I think it's a good idea.", "It is the best idea ever."]),
                    ex("quiz", "Qual frase pede a opinião de outra pessoa?",
                       "What do you think?", ["What do you think?", "I think so.", "You are thinking."]),
                ],
            ),
        ],
    )


# ============================================================
# Complementos revisados dos módulos 1 a 7
# ============================================================


def _lesson_revision(explanation, examples, errors, summary):
    example_lines = "\n".join(
        f"- **{english}** — {portuguese}"
        for english, portuguese in examples
    )
    error_lines = "\n".join(f"- {error}" for error in errors)
    return (
        "\n\n## Explicação prática\n"
        + explanation.strip()
        + "\n\n## Exemplos naturais\n"
        + example_lines
        + "\n\n## Erros comuns\n"
        + error_lines
        + "\n\n## Resumo prático\n"
        + summary.strip()
    )


TARGET_TOPIC_ENHANCEMENTS = {}


TARGET_TOPIC_ENHANCEMENTS.update({
    "alfabeto-e-pronuncia": {
        "lesson": _lesson_revision(
            "O nome de uma letra e o som que ela representa não são a mesma coisa. Na soletração, diga os nomes das letras separadamente e confirme a palavra inteira depois.",
            [
                ("How do you spell Anna?", "Como você soletra Anna?"),
                ("The word think starts with T.", "A palavra think começa com T."),
            ],
            [
                "Não trate o H como mudo: em inglês, a letra se chama **aitch**.",
                "Não troque o som de **th** pelo de **t** em *think*.",
            ],
            "Soletrar é dizer nomes de letras; pronunciar é produzir os sons da palavra. Ouça, repita devagar e depois tente no ritmo normal.",
        ),
        "exercises": [
            ex("quiz", "Qual letra vem depois de G no alfabeto inglês?", "H", ["H", "I", "F"]),
            ex("text", "Soletre em inglês, separando as letras: Anna.", "a n n a"),
            ex("audio", "Escute as letras e transcreva a soletração:", "a n n a", audio_text="A N N A."),
            ex("speak", "Repita em voz alta, destacando o som de th:", "this", audio_text="this"),
        ],
    },
    "cumprimentos-basicos": {
        "lesson": _lesson_revision(
            "O cumprimento depende do momento e da intenção. Ao chegar à noite, use **Good evening**; ao sair ou ir dormir, use **Good night**. Para manter a conversa, responda à pergunta sobre como você está e devolva a pergunta.",
            [
                ("Good evening. How are you?", "Boa noite. Como você está?"),
                ("I'm fine, thanks. And you?", "Estou bem, obrigado(a). E você?"),
            ],
            [
                "Não use **Good night** para iniciar uma conversa; essa expressão é normalmente uma despedida.",
                "Não confunda **See you later** (até mais) com **Goodbye** (adeus/tchau).",
            ],
            "Cumprimente com **Hi/Hello** ou com o período do dia, responda **I'm fine, thanks** e encerre com **See you** ou **Goodbye**.",
        ),
        "exercises": [
            ex("text", "Traduza: Até amanhã.", "see you tomorrow"),
            ex("quiz", "Você encontra uma pessoa à noite e vai iniciar a conversa. O que diz?", "Good evening", ["Good evening", "Good night", "See you tomorrow"]),
            ex("audio", "Escute e transcreva a despedida:", "see you later", audio_text="See you later."),
            ex("speak", "Diga em voz alta ao se despedir:", "take care", audio_text="Take care."),
        ],
    },
    "apresentando-se": {
        "lesson": _lesson_revision(
            "Uma apresentação curta costuma seguir uma ordem simples: nome, origem e uma informação sobre estudo ou trabalho. Em um primeiro encontro, finalize com **Nice to meet you**; a outra pessoa pode responder **Nice to meet you too**.",
            [
                ("I'm Lucas. I'm from Brazil.", "Eu sou Lucas. Sou do Brasil."),
                ("This is my friend, Ana. Nice to meet you.", "Esta é minha amiga, Ana. Prazer em conhecê-lo(a)."),
            ],
            [
                "Não diga **I have 20 years** para idade; essa estrutura será praticada no tópico de informações pessoais.",
                "Não use **Nice to meet you** como despedida habitual de alguém que você já conhece.",
            ],
            "Use **My name is...** ou **I'm...**, acrescente **I'm from...** e feche o primeiro encontro com **Nice to meet you**.",
        ),
        "exercises": [
            ex("text", "Traduza: Eu sou do Brasil.", "i'm from brazil"),
            ex("quiz", "Qual resposta combina com 'Nice to meet you?'", "Nice to meet you too.", ["Nice to meet you too.", "I'm fine, thanks.", "Good night."]),
            ex("audio", "Escute e transcreva a pergunta sobre origem:", "where are you from", audio_text="Where are you from?"),
            ex("speak", "Diga em voz alta uma apresentação curta:", "i'm ana nice to meet you", audio_text="I'm Ana. Nice to meet you."),
            ex("quiz", "Qual frase informa a profissão ou atividade de estudo?", "I'm a student.", ["I'm a student.", "I'm from Brazil.", "Nice to meet you."]),
        ],
    },
    "informacoes-pessoais": {
        "lesson": _lesson_revision(
            "Perguntas pessoais têm modelos fixos: **How old are you?** pergunta idade, **Where do you live?** pergunta moradia e **What do you do?** pergunta estudo ou profissão. Responda com uma frase completa, não apenas com uma palavra.",
            [
                ("How old is Maria? — She is 25 years old.", "Quantos anos Maria tem? — Ela tem 25 anos."),
                ("What do you do? — I'm a student.", "O que você faz? — Sou estudante."),
            ],
            [
                "Em inglês, idade usa **be**: **I am 20 years old**, não *I have 20 years*.",
                "**Where do you live?** pergunta onde a pessoa mora; não confunda com **Where are you from?**, sobre origem.",
            ],
            "Para idade use **I am ... years old**; para moradia, **I live in...**; para estudo ou profissão, **I'm a...**.",
        ),
        "exercises": [
            ex("quiz", "Maria is 25 years old. How old is Maria?", "She is 25 years old.", ["She is 25 years old.", "She lives in Brazil.", "She is a teacher."]),
            ex("text", "Traduza: Eu sou estudante.", "i'm a student"),
            ex("audio", "Escute e transcreva a pergunta sobre profissão:", "what do you do", audio_text="What do you do?"),
            ex("speak", "Diga onde você mora:", "i live in brazil", audio_text="I live in Brazil."),
            ex("quiz", "Qual pergunta descobre onde uma pessoa mora?", "Where do you live?", ["Where do you live?", "How old are you?", "What is your name?"]),
        ],
    },
    "numeros-em-ingles": {
        "lesson": _lesson_revision(
            "Números entre 13 e 19 terminam em **-teen**; as dezenas terminam em **-ty**. Ao escrever um número como 42, use hífen entre a dezena e a unidade: **forty-two**.",
            [
                ("I have two sisters.", "Eu tenho duas irmãs."),
                ("The ticket is thirty-five dollars.", "A passagem custa trinta e cinco dólares."),
            ],
            [
                "A grafia correta é **forty**, não *fourty*.",
                "Não confunda **thirteen** (13) com **thirty** (30); o final muda o número.",
            ],
            "Pratique a diferença entre **-teen** e **-ty**, escreva números compostos com hífen e use **one hundred** para 100.",
        ),
        "exercises": [
            ex("quiz", "Como se escreve 30 em inglês?", "thirty", ["thirty", "thirteen", "three"]),
            ex("text", "Escreva por extenso, em inglês: 42", "forty-two"),
            ex("audio", "Escute e transcreva:", "i have two sisters", audio_text="I have two sisters."),
            ex("speak", "Diga o número em voz alta:", "i am thirty years old", audio_text="I am thirty years old."),
            ex("quiz", "Em uma loja, qual frase informa um preço de 20 dólares?", "It is twenty dollars.", ["It is twenty dollars.", "It is twelve dollars.", "It is two dollars."]),
        ],
    },
    "datas-e-horas": {
        "lesson": _lesson_revision(
            "Para horas exatas, use **It's + número + o'clock**. Para dias, use **on**: **on Monday**. Dias e meses começam com maiúscula em inglês, mesmo no meio da frase.",
            [
                ("What day is it today? — It's Monday.", "Que dia é hoje? — É segunda-feira."),
                ("The party is on Friday.", "A festa é na sexta-feira."),
            ],
            [
                "Não escreva *monday* ou *friday* com minúscula; nomes de dias são sempre capitalizados.",
                "Não use **at** para o dia: diga **on Tuesday**, mas **at three o'clock**.",
            ],
            "Use **What time is it?** para a hora, **What day is it?** para o dia, **at** para horas e **on** para dias.",
        ),
        "exercises": [
            ex("quiz", "Qual dia vem depois de Thursday?", "Friday", ["Friday", "Wednesday", "Saturday"]),
            ex("text", "Traduza: A festa é na sexta-feira.", "the party is on friday"),
            ex("audio", "Escute e transcreva:", "it's five o'clock", audio_text="It's five o'clock."),
            ex("speak", "Pergunte as horas em voz alta:", "what time is it", audio_text="What time is it?"),
        ],
    },
    "paises-e-nacionalidades": {
        "lesson": _lesson_revision(
            "País, nacionalidade e idioma são palavras diferentes: **Brazil**, **Brazilian** e **Portuguese** não ocupam o mesmo lugar. Para origem, use **be from**; para nacionalidade, use **be + nacionalidade**.",
            [
                ("Where are you from? — I'm from Portugal.", "De onde você é? — Sou de Portugal."),
                ("She is American.", "Ela é americana."),
            ],
            [
                "Nomes de países e nacionalidades começam com maiúscula: **Brazil**, **Brazilian**.",
                "Não troque **Portugal** por **Portuguese**: o primeiro é o país; o segundo, a nacionalidade ou o idioma.",
            ],
            "Pergunte **Where are you from?**, responda **I'm from + país** ou **I'm + nacionalidade** e mantenha as maiúsculas.",
        ),
        "exercises": [
            ex("quiz", "Qual resposta combina com 'Where are you from?'", "I'm from Portugal.", ["I'm from Portugal.", "I'm Portuguese.", "I live 20 years."]),
            ex("text", "Traduza: Ela é americana.", "she is american"),
            ex("audio", "Escute e transcreva:", "where are you from", audio_text="Where are you from?"),
            ex("speak", "Diga sua nacionalidade em voz alta:", "i am portuguese", audio_text="I am Portuguese."),
            ex("quiz", "Qual palavra é o nome do país, e não da nacionalidade?", "Brazil", ["Brazil", "Brazilian", "American"]),
        ],
    },
    "familia-em-ingles": {
        "lesson": _lesson_revision(
            "Para apresentar um parente, use **This is my...**; para informar quantidade, use **I have...**. O possessivo **my** vem antes do nome da relação: **my sister**, **my father**.",
            [
                ("Who is this? — This is my sister.", "Quem é esta? — Esta é minha irmã."),
                ("My sister has a son.", "Minha irmã tem um filho."),
            ],
            [
                "Não confunda **son** (filho) com **daughter** (filha).",
                "Depois de **my**, coloque o substantivo: **my mother**, não *mother my*.",
            ],
            "Use **This is my...** para apresentar alguém e **I have...** para contar parentes; revise as relações masculinas e femininas.",
        ),
        "exercises": [
            ex("quiz", "Qual palavra significa 'esposa'?", "wife", ["wife", "husband", "daughter"]),
            ex("text", "Traduza: Meu tio trabalha aqui.", "my uncle works here"),
            ex("audio", "Escute e transcreva:", "her husband is a teacher", audio_text="Her husband is a teacher."),
            ex("speak", "Diga em voz alta quantas irmãs você tem:", "i have one sister", audio_text="I have one sister."),
            ex("quiz", "Você mostra uma pessoa da família. Qual pergunta e resposta combinam?", "This is my sister.", ["This is my sister.", "This are my sister.", "I am my sister."]),
        ],
    },
    "cores-em-ingles": {
        "lesson": _lesson_revision(
            "Para perguntar uma cor, use **What color is...?**. O adjetivo vem depois de **be** quando descreve o objeto: **The bag is red**. Antes de um substantivo, também pode vir antes: **a red bag**.",
            [
                ("What color is the sky? — It's blue.", "Qual é a cor do céu? — É azul."),
                ("My bag is red.", "Minha bolsa é vermelha."),
            ],
            [
                "Não traduza literalmente *color of what*; a pergunta natural é **What color is...?**.",
                "As cores em inglês não variam em gênero ou número: **red car** e **red houses**.",
            ],
            "Aprenda a cor como adjetivo invariável e pratique o par **What color...? — It's...** com objetos conhecidos.",
        ),
        "exercises": [
            ex("quiz", "What color is the sky on a clear day?", "blue", ["blue", "black", "purple"]),
            ex("text", "Traduza: A camisa é verde.", "the shirt is green"),
            ex("audio", "Escute e transcreva:", "my bag is red", audio_text="My bag is red."),
            ex("speak", "Diga a cor do carro em voz alta:", "the car is white", audio_text="The car is white."),
            ex("quiz", "What color is a banana?", "yellow", ["yellow", "orange", "green"]),
        ],
    },
    "objetos-e-lugares": {
        "lesson": _lesson_revision(
            "Para localizar um objeto, combine **Where is...?** com **in**, **on** ou **at**. Use **on** para uma superfície, **in** para dentro de algo e **at** para um local entendido como ponto ou atividade.",
            [
                ("Where is the pen? — It's on the table.", "Onde está a caneta? — Está sobre a mesa."),
                ("I am at the park.", "Eu estou no parque."),
            ],
            [
                "Não diga *The book is in the table* se o livro está sobre a superfície; use **on the table**.",
                "Em **at home**, não coloque **the** antes de home.",
            ],
            "Pergunte **Where is...?**, escolha **on/in/at** conforme a relação espacial e memorize os objetos com uma frase completa.",
        ),
        "exercises": [
            ex("quiz", "The book is on the table. Where is the book?", "on the table", ["on the table", "in the school", "at the park"]),
            ex("text", "Traduza: A caneta está na mesa.", "the pen is on the table"),
            ex("audio", "Escute e transcreva:", "i am at the park", audio_text="I am at the park."),
            ex("speak", "Descreva o objeto em voz alta:", "the door is open", audio_text="The door is open."),
            ex("quiz", "Where do you buy things?", "At the store.", ["At the store.", "At the school.", "On the table."]),
        ],
    },
    "atividades-diarias": {
        "lesson": _lesson_revision(
            "Rotinas usam o presente simples. Com **I/you/we/they**, use o verbo base; com **he/she/it**, acrescente **-s** ou **-es**. Horários vêm normalmente com **at**.",
            [
                ("She eats breakfast at eight.", "Ela toma café da manhã às oito."),
                ("He sleeps at night.", "Ele dorme à noite."),
            ],
            [
                "Não diga *She work*; diga **She works**.",
                "Não mova o **up** de **wake up**: a expressão é **wake up**, não *wake at 7 up*.",
            ],
            "Escolha o verbo da rotina, acrescente **-s** na terceira pessoa e use marcadores como **every day**, **at night** e **in the morning**.",
        ),
        "exercises": [
            ex("quiz", "Complete: 'She ___ breakfast at 8.' (eat)", "eats", ["eats", "eat", "eating"]),
            ex("text", "Traduza: Eu vou para a escola todos os dias.", "i go to school every day"),
            ex("audio", "Escute e transcreva:", "he sleeps at night", audio_text="He sleeps at night."),
            ex("speak", "Diga uma atividade da sua rotina:", "i work every day", audio_text="I work every day."),
            ex("quiz", "Qual expressão completa 'I wake up ___ 7 am'?", "at", ["at", "in", "on"]),
        ],
    },
    "perguntas-basicas": {
        "lesson": _lesson_revision(
            "A primeira palavra geralmente revela o tipo de informação desejada: **who** para pessoa, **where** para lugar, **when** para tempo, **what** para coisa e **how** para maneira ou estado.",
            [
                ("Who is she? — She is my teacher.", "Quem é ela? — Ela é minha professora."),
                ("When is the class? — On Monday.", "Quando é a aula? — Na segunda-feira."),
            ],
            [
                "Não confunda **who** (quem) com **whose**; o segundo não faz parte deste conjunto inicial.",
                "Depois de **What/Who/Where**, mantenha a ordem correta: **What is this?**, não *What this is?*.",
            ],
            "Identifique a palavra interrogativa antes de ouvir o restante e responda com a informação pedida: pessoa, lugar, tempo, coisa ou maneira.",
        ),
        "exercises": [
            ex("text", "Traduza: Quem é ela?", "who is she"),
            ex("quiz", "Qual palavra pergunta sobre um horário ou data?", "When", ["When", "Where", "Who"]),
            ex("audio", "Escute e transcreva:", "what do you want", audio_text="What do you want?"),
            ex("speak", "Pergunte de onde alguém é:", "where are you from", audio_text="Where are you from?"),
            ex("quiz", "Qual question word aparece em 'How are you?'", "How", ["How", "Why", "What"]),
        ],
    },
    "respostas-basicas": {
        "lesson": _lesson_revision(
            "Essas expressões funcionam como blocos prontos de educação. **Excuse me** chama a atenção; **sorry** pede desculpas; **please** acompanha pedidos; **thank you** agradece.",
            [
                ("Excuse me, please. Can you help me?", "Com licença, por favor. Você pode me ajudar?"),
                ("Thank you. — You're welcome.", "Obrigado(a). — De nada."),
            ],
            [
                "Não use **sorry** para chamar a atenção quando **excuse me** é a expressão mais adequada.",
                "Depois de um agradecimento, a resposta natural é **You're welcome** ou **No problem**, não *Please*.",
            ],
            "Associe cada situação ao bloco certo: chamar atenção, pedir, agradecer, pedir desculpas ou admitir que não sabe.",
        ),
        "exercises": [
            ex("quiz", "Qual é uma resposta natural para 'Thank you'?", "You're welcome.", ["You're welcome.", "Excuse me.", "I don't know."]),
            ex("text", "Traduza: Eu não sei.", "i don't know"),
            ex("audio", "Escute e transcreva:", "excuse me please", audio_text="Excuse me, please."),
            ex("speak", "Peça desculpas em voz alta:", "sorry", audio_text="Sorry."),
            ex("quiz", "Você precisa chamar a atenção de alguém educadamente. O que diz?", "Excuse me.", ["Excuse me.", "Good night.", "I don't know."]),
        ],
    },
    "ingles-de-sala-de-aula": {
        "lesson": _lesson_revision(
            "Frases de sala de aula permitem continuar aprendendo mesmo quando falta uma palavra. Use **Can you...?** para pedir uma ação e **How do you say...?** para perguntar a tradução ou o nome de algo.",
            [
                ("Can you repeat, please?", "Você pode repetir, por favor?"),
                ("How do you say 'janela' in English?", "Como se diz 'janela' em inglês?"),
            ],
            [
                "Não diga *How say this?*; mantenha a estrutura **How do you say this in English?**.",
                "**I don't understand** informa que você não entendeu; **I don't know** informa que você não sabe.",
            ],
            "Memorize quatro saídas: dizer que não entendeu, pedir repetição, perguntar uma palavra e pedir ajuda.",
        ),
        "exercises": [
            ex("quiz", "Qual frase significa 'Eu não entendo'?", "I don't understand.", ["I don't understand.", "I don't know.", "Can you help me?"]),
            ex("text", "Traduza: Como se diz isso em inglês?", "how do you say this in english"),
            ex("audio", "Escute e transcreva:", "can you repeat please", audio_text="Can you repeat, please?"),
            ex("speak", "Peça ajuda ao professor:", "can you help me", audio_text="Can you help me?"),
            ex("quiz", "Você não ouviu a frase do professor. Qual pedido é adequado?", "Can you repeat, please?", ["Can you repeat, please?", "I am a student.", "Good night."]),
        ],
    },
    "ingles-de-sobrevivencia": {
        "lesson": _lesson_revision(
            "Em uma situação urgente, use frases curtas e diretas. **Help!** pede socorro; **I need...** informa uma necessidade; **Where is...?** pede localização; **How much is...?** pergunta preço.",
            [
                ("I need water, please.", "Preciso de água, por favor."),
                ("Help! Call the police!", "Socorro! Chame a polícia!"),
            ],
            [
                "Não confunda **bathroom** (banheiro) com **bedroom** (quarto).",
                "Para chamar socorro, **Help!** é mais direto que apenas **Please!**.",
            ],
            "Escolha a frase pelo objetivo: socorro, localização, preço ou necessidade; acrescente **please** quando houver tempo para ser educado.",
        ),
        "exercises": [
            ex("quiz", "Você precisa de água. Qual frase comunica isso?", "I need water.", ["I need water.", "I need money.", "I need a ticket."]),
            ex("text", "Traduza: Preciso de água.", "i need water"),
            ex("audio", "Escute e transcreva:", "where is the bathroom", audio_text="Where is the bathroom?"),
            ex("speak", "Peça ajuda em voz alta:", "help me please", audio_text="Help me, please."),
            ex("quiz", "Qual frase você usa para chamar a polícia?", "Call the police!", ["Call the police!", "Call the store!", "Call the school!"]),
        ],
    },
})


EXACT_10_MODULE_SLUGS = {
    "modulo-01-primeiros-passos",
    "modulo-02-gramatica-essencial-a1",
    "modulo-03-vocabulario-basico",
    "modulo-04-comunicacao-a1",
    "modulo-05-gramatica-essencial-a2",
    "modulo-06-vocabulario-a2",
    "modulo-07-comunicacao-a2",
    "modulo-08-gramatica-essencial-b1",
    "modulo-09-vocabulario-b1",
    "modulo-10-speaking-b1",
    "modulo-11-listening-b1",
    "modulo-12-gramatica-essencial-b2",
    "modulo-13-vocabulario-b2",
    "modulo-14-ingles-natural-b2",
    "modulo-15-speaking-b2",
    "modulo-16-writing-b2",
}


def _expand_target_module(current_module):
    if current_module["slug"] not in EXACT_10_MODULE_SLUGS:
        return current_module

    for current_topic in current_module["topics"]:
        spec = TARGET_TOPIC_ENHANCEMENTS.get(current_topic["slug"])
        if spec is None:
            raise ValueError(
                f"Tópico sem complemento revisado: {current_topic['slug']}"
            )
        needed = 10 - len(current_topic["exercises"])
        if needed < 0:
            raise ValueError(
                "Tópico com mais de 10 exercícios antes da expansão: "
                f"{current_topic['slug']}"
            )
        if len(spec["exercises"]) < needed:
            raise ValueError(
                f"Complemento insuficiente para {current_topic['slug']}: "
                f"{len(spec['exercises'])} para {needed}"
            )
        current_topic["exercises"].extend(
            deepcopy(spec["exercises"][:needed])
        )
        current_topic["lesson_md"] = (
            current_topic["lesson_md"].rstrip() + spec["lesson"]
        )
    return current_module


TARGET_TOPIC_ENHANCEMENTS.update({
    "falando-sobre-o-passado": {
        "lesson": _lesson_revision(
            "Conte um acontecimento terminado com o passado simples e marque quando ele ocorreu. **Yesterday, last week** e **ago** ajudam o ouvinte a localizar a ação no tempo.",
            [
                ("I visited my friends yesterday.", "Eu visitei meus amigos ontem."),
                ("What did you do last weekend?", "O que você fez no fim de semana passado?"),
            ],
            [
                "Depois de **did**, use a forma base: **What did you do?**, não *What did you did?*.",
                "**Last week** é semana passada; **next week** é semana que vem.",
            ],
            "Escolha o marcador de passado, conjugue a afirmação e use **did/didn't + verbo base** para perguntas e negativas.",
        ),
        "exercises": [
            ex("text", "Traduza: Eu visitei meus amigos ontem.", "i visited my friends yesterday"),
            ex("quiz", "Qual é o passado de 'buy'?", "bought", ["bought", "buyed", "buys"]),
            ex("audio", "Escute e transcreva:", "what did you do last weekend", audio_text="What did you do last weekend?"),
            ex("speak", "Conte onde você foi ontem:", "i went to the park yesterday", audio_text="I went to the park yesterday."),
        ],
    },
    "falando-de-planos-futuros": {
        "lesson": _lesson_revision(
            "Para conversar sobre planos, use **going to** quando a intenção já está decidida e **will** para uma decisão na hora. Marcadores como **tomorrow** e **next month** deixam o plano claro.",
            [
                ("I'm going to visit my family next month.", "Vou visitar minha família no próximo mês."),
                ("I'll call you tonight.", "Vou ligar para você hoje à noite."),
            ],
            [
                "Não use **will** automaticamente para todo futuro; considere se o plano já foi decidido.",
                "Depois de **going to**, o verbo fica na forma base: **going to visit**.",
            ],
            "Diga quando o plano acontece, escolha **going to** ou **will** conforme a situação e mantenha a estrutura completa.",
        ),
        "exercises": [
            ex("text", "Traduza: Vou visitar minha família no próximo mês.", "i am going to visit my family next month"),
            ex("quiz", "Você decide agora ajudar um amigo. Qual frase é natural?", "I will help you.", ["I will help you.", "I helped you yesterday.", "I am helping yesterday."]),
            ex("audio", "Escute e transcreva:", "what are you going to do tomorrow", audio_text="What are you going to do tomorrow?"),
            ex("speak", "Faça uma promessa para hoje à noite:", "i'll call you tonight", audio_text="I'll call you tonight."),
        ],
    },
    "descrevendo-pessoas": {
        "lesson": _lesson_revision(
            "Use **be + adjetivo** para altura e personalidade, mas **have + característica** para cabelo e olhos. Adjetivos como **friendly, shy, hardworking** descrevem comportamento, não aparência.",
            [
                ("She is short and friendly.", "Ela é baixa e simpática."),
                ("He has short hair.", "Ele tem cabelo curto."),
            ],
            [
                "Não diga *He is long* para cabelo; diga **He has long hair**.",
                "Não confunda **short** (baixo/curto) sem olhar o substantivo: short person e short hair têm sentidos diferentes.",
            ],
            "Separe aparência de personalidade, escolha **be** ou **have** e combine dois adjetivos em uma descrição natural.",
        ),
        "exercises": [
            ex("text", "Traduza: Ela é baixa e simpática.", "she is short and friendly"),
            ex("quiz", "Qual adjetivo descreve uma pessoa em quem se pode confiar?", "reliable", ["reliable", "shy", "noisy"]),
            ex("audio", "Escute e transcreva:", "he has short hair", audio_text="He has short hair."),
            ex("speak", "Descreva seu irmão ou amigo:", "my brother is hardworking", audio_text="My brother is hardworking."),
        ],
    },
    "descrevendo-lugares": {
        "lesson": _lesson_revision(
            "Descreva um lugar com **be + adjetivo** e acrescente o que existe nele com **there is/are**. Assim, você combina qualidade e informação: **The city is safe and there are many parks**.",
            [
                ("The city is safe and clean.", "A cidade é segura e limpa."),
                ("There are many shops downtown.", "Há muitas lojas no centro."),
            ],
            [
                "Não diga *There is many parks*; **parks** é plural e pede **there are**.",
                "**Crowded** significa cheio de gente; não confunda com **noisy**, que é barulhento.",
            ],
            "Escolha um adjetivo para o lugar, use **there is/are** para os elementos e conecte ideias com **and**.",
        ),
        "exercises": [
            ex("text", "Traduza: A cidade é segura e limpa.", "the city is safe and clean"),
            ex("quiz", "Qual é o oposto de 'noisy'?", "quiet", ["quiet", "crowded", "dangerous"]),
            ex("audio", "Escute e transcreva:", "there are many shops downtown", audio_text="There are many shops downtown."),
            ex("speak", "Descreva um lugar bonito:", "the park is beautiful", audio_text="The park is beautiful."),
        ],
    },
    "fazendo-convites": {
        "lesson": _lesson_revision(
            "**Do you want to...?** é um convite comum; **Would you like to...?** é mais educado; **Let's...** sugere uma atividade que as duas pessoas farão juntas. Escolha a forma conforme a proximidade e o tom.",
            [
                ("Would you like to have dinner with me?", "Você gostaria de jantar comigo?"),
                ("Let's go to the park.", "Vamos ao parque."),
            ],
            [
                "Não confunda convite com afirmação: **Do you want to dance?** precisa do auxiliar **do**.",
                "Depois de **would like to**, use verbo base: **would like to come**, não *coming*.",
            ],
            "Escolha **Do you want to**, **Would you like to** ou **Let's**, diga a atividade e deixe claro com quem ela será feita.",
        ),
        "exercises": [
            ex("text", "Traduza: Você gostaria de jantar comigo?", "would you like to have dinner with me"),
            ex("quiz", "Qual resposta aceita um convite?", "Sure!", ["Sure!", "I'm busy.", "No, thanks."]),
            ex("audio", "Escute e transcreva:", "would you like to come with us", audio_text="Would you like to come with us?"),
            ex("speak", "Faça uma sugestão de passeio:", "let's go to the park", audio_text="Let's go to the park."),
        ],
    },
    "aceitando-convites": {
        "lesson": _lesson_revision(
            "Aceitar um convite pode ser curto (**Sure!**) ou entusiasmado (**Yes, I'd love to!**). **That sounds good** e **Great idea** mostram aprovação sem repetir toda a proposta.",
            [
                ("That sounds good. What time?", "Parece bom. Que horas?"),
                ("Great idea! Let's go.", "Ótima ideia! Vamos."),
            ],
            [
                "Não use **No, thanks** quando pretende aceitar; essa expressão normalmente recusa.",
                "**I'd love to** é a contração de *I would love to*; o **to** permanece quando a proposta é uma ação.",
            ],
            "Reconheça as respostas positivas, escolha uma expressão de entusiasmo e, se necessário, acrescente uma pergunta prática.",
        ),
        "exercises": [
            ex("text", "Traduza: Isso parece bom.", "that sounds good"),
            ex("quiz", "Qual resposta aceita o convite de forma amigável?", "Why not?", ["Why not?", "I'm afraid I can't.", "Maybe next time."]),
            ex("audio", "Escute e transcreva:", "great idea let's go", audio_text="Great idea! Let's go."),
            ex("speak", "Aceite o convite com entusiasmo:", "yes i'd love to", audio_text="Yes, I'd love to!"),
        ],
    },
    "recusando-educadamente": {
        "lesson": _lesson_revision(
            "Uma recusa educada reconhece o convite e oferece um motivo breve: **I'd love to, but...**, **I'm sorry, I can't** ou **Maybe next time**. O tom é tão importante quanto a gramática.",
            [
                ("Sorry, I can't make it.", "Desculpe, não vou conseguir."),
                ("I'd love to, but I'm busy.", "Eu adoraria, mas estou ocupado(a)."),
            ],
            [
                "Evite **No way!** em situações educadas; pode soar rude.",
                "Não use *I don't want* como resposta padrão quando o problema é falta de tempo; explique com **I'm busy**.",
            ],
            "Agradeça ou mostre interesse, use **but** para o motivo e encerre com **Maybe next time** quando fizer sentido.",
        ),
        "exercises": [
            ex("text", "Traduza: Talvez na próxima.", "maybe next time"),
            ex("quiz", "Qual resposta recusa sem ser grosseira?", "I'd love to, but I'm busy.", ["I'd love to, but I'm busy.", "No way!", "Leave me alone."]),
            ex("audio", "Escute e transcreva:", "sorry i can't make it", audio_text="Sorry, I can't make it."),
            ex("speak", "Diga por que você não pode ir:", "i'm busy today", audio_text="I'm busy today."),
        ],
    },
    "fazendo-sugestoes": {
        "lesson": _lesson_revision(
            "**Why don't we...?** e **Let's...** vêm seguidos de verbo; **How about...?** e **What about...?** podem vir seguidos de substantivo. Todas propõem uma atividade, mas a estrutura muda.",
            [
                ("What about a movie?", "Que tal um filme?"),
                ("Why don't we watch a movie?", "Por que não assistimos a um filme?"),
            ],
            [
                "Depois de **Why don't we**, use verbo base: **Why don't we go?**.",
                "Neste tópico, pratique **How about + substantivo**, como **How about pizza?**; não misture essa estrutura com **Why don't we + verbo**.",
            ],
            "Veja se a sugestão pede uma coisa ou uma ação, escolha a estrutura correspondente e responda aceitando ou recusando.",
        ),
        "exercises": [
            ex("text", "Traduza: Que tal um filme?", "what about a movie"),
            ex("quiz", "Complete uma sugestão com substantivo: 'How about ___?'", "a coffee", ["a coffee", "go coffee", "to coffee"]),
            ex("audio", "Escute e transcreva:", "let's study together", audio_text="Let's study together."),
            ex("speak", "Sugira sair:", "why don't we go out", audio_text="Why don't we go out?"),
        ],
    },
    "dando-conselhos": {
        "lesson": _lesson_revision(
            "**Should + verbo base** oferece um conselho. A pergunta **Why don't you...?** também pode sugerir uma solução. O tom é menos obrigatório que **must**.",
            [
                ("You should drink more water.", "Você deveria beber mais água."),
                ("Why don't you take a break?", "Por que você não faz uma pausa?"),
            ],
            [
                "Não acrescente **-s** depois de **should**: diga **should study**, não *should studies*.",
                "Não confunda conselho (**should**) com obrigação forte (**must**).",
            ],
            "Use **should + verbo base**, explique o conselho em contexto e suavize com **Why don't you...?** quando adequado.",
        ),
        "exercises": [
            ex("text", "Traduza: Você deveria beber mais água.", "you should drink more water"),
            ex("quiz", "Qual frase dá um conselho sobre descanso?", "You should rest.", ["You should rest.", "You rested.", "You are rest."]),
            ex("audio", "Escute e transcreva:", "why don't you take a break", audio_text="Why don't you take a break?"),
            ex("speak", "Dê um conselho para uma pessoa doente:", "you should call a doctor", audio_text="You should call a doctor."),
        ],
    },
    "pedindo-ajuda": {
        "lesson": _lesson_revision(
            "**Can you...?** é um pedido comum; **Could you...?** é mais polido. Para especificar a tarefa ou o assunto, use **help me with...**.",
            [
                ("Could you open the door?", "Você poderia abrir a porta?"),
                ("I need help with this.", "Preciso de ajuda com isto."),
            ],
            [
                "Não confunda **help me with** com *help me to* neste modelo; diga **help me with the homework** para o assunto.",
                "Depois de **could/can**, use verbo base: **Could you help...?**.",
            ],
            "Escolha o grau de polidez, diga a ação ou o assunto e esteja pronto para responder **Sure/Of course**.",
        ),
        "exercises": [
            ex("text", "Traduza: Você poderia abrir a porta?", "could you open the door"),
            ex("quiz", "Qual resposta combina com 'Could you help me?'", "Sure!", ["Sure!", "No, I am help.", "I helped yesterday."]),
            ex("audio", "Escute e transcreva:", "can you do me a favor", audio_text="Can you do me a favor?"),
            ex("speak", "Peça ajuda com um problema:", "i need help with this", audio_text="I need help with this."),
        ],
    },
    "fazendo-reclamacoes": {
        "lesson": _lesson_revision(
            "Uma reclamação clara tem três partes: abertura educada, problema e pedido implícito ou explícito. **I'm sorry, but...** reduz o tom de confronto; **It doesn't work** é um modelo muito útil.",
            [
                ("I'm sorry, but the soup is cold.", "Desculpe, mas a sopa está fria."),
                ("The room is dirty. Can you help me?", "O quarto está sujo. Você pode me ajudar?"),
            ],
            [
                "Não comece com insultos em um atendimento; **I'm sorry, but...** é mais eficaz e educado.",
                "**Wrong** significa errado; não confunda com **broken**, que significa quebrado.",
            ],
            "Nomeie o problema com uma frase curta, mantenha a educação e peça uma solução quando necessário.",
        ),
        "exercises": [
            ex("text", "Traduza: A sopa está fria.", "the soup is cold"),
            ex("quiz", "Qual abertura é educada para uma reclamação?", "I'm sorry, but...", ["I'm sorry, but...", "Hey, you!", "Shut up."]),
            ex("audio", "Escute e transcreva:", "the room is dirty", audio_text="The room is dirty."),
            ex("speak", "Diga que algo não funciona:", "it doesn't work", audio_text="It doesn't work."),
        ],
    },
    "falando-de-experiencias": {
        "lesson": _lesson_revision(
            "Neste nível, conte experiências com o passado simples e acrescente quando, onde e como foi. **Visited, tried, saw** e **was** ajudam a montar uma pequena narrativa concreta.",
            [
                ("I visited Rio last year.", "Eu visitei o Rio no ano passado."),
                ("It was fantastic.", "Foi fantástico."),
            ],
            [
                "Não use presente com marcador passado: diga **I visited last year**, não *I visit last year*.",
                "Depois de **Did you...?**, use o verbo base: **Did you try it?**.",
            ],
            "Diga o que aconteceu, acrescente tempo ou lugar e avalie a experiência com um adjetivo como **amazing** ou **boring**.",
        ),
        "exercises": [
            ex("text", "Traduza: Eu visitei o Rio no ano passado.", "i visited rio last year"),
            ex("quiz", "Qual frase dá um detalhe sobre uma experiência?", "I saw the Eiffel Tower.", ["I saw the Eiffel Tower.", "I see the Eiffel Tower every day.", "I will see the Eiffel Tower."]),
            ex("audio", "Escute e transcreva:", "did you enjoy your trip", audio_text="Did you enjoy your trip?"),
            ex("speak", "Avalie a experiência:", "it was fantastic", audio_text="It was fantastic."),
        ],
    },
    "expressando-opinioes": {
        "lesson": _lesson_revision(
            "Use **I think...** para uma opinião comum, **In my opinion...** para marcar seu ponto de vista e **I don't think...** para discordar de uma ideia sem soar tão direto. Pergunte **What do you think?** para incluir a outra pessoa.",
            [
                ("I don't think it's a good idea.", "Eu não acho que seja uma boa ideia."),
                ("What do you think?", "O que você acha?"),
            ],
            [
                "Não transforme **I think** em uma pergunta; para pedir opinião, use **What do you think?**.",
                "Depois de **I think**, mantenha uma frase completa: **I think it's great**, não *I think great*.",
            ],
            "Dê sua opinião, suavize uma avaliação negativa e peça a opinião do interlocutor com uma pergunta direta.",
        ),
        "exercises": [
            ex("text", "Traduza: Eu não acho que seja uma boa ideia.", "i don't think it's a good idea"),
            ex("quiz", "Qual frase pede a opinião de outra pessoa?", "What do you think?", ["What do you think?", "I think so.", "I am thinking."]),
            ex("audio", "Escute e transcreva:", "in my opinion it is too expensive", audio_text="In my opinion, it is too expensive."),
            ex("speak", "Dê uma opinião positiva:", "i think it's a good idea", audio_text="I think it's a good idea."),
        ],
    },
})


TARGET_TOPIC_ENHANCEMENTS.update({
    "viagem": {
        "lesson": _lesson_revision(
            "Separe o evento da ação: **trip** é a viagem, **travel** é viajar. Em um aeroporto ou estação, **ticket, passport, luggage** e **flight** formam um conjunto de sobrevivência.",
            [
                ("My flight leaves at eight.", "Meu voo sai às oito."),
                ("Where is my luggage?", "Onde está minha bagagem?"),
            ],
            [
                "Não use **travel** como substantivo contável em *a travel*; diga **a trip**.",
                "Não confunda **luggage** (bagagem, incontável) com **suitcase** (mala contável).",
            ],
            "Associe cada palavra à etapa da viagem: preparar, embarcar, localizar a bagagem ou seguir o voo.",
        ),
        "exercises": [
            ex("text", "Traduza: Meu voo sai às oito.", "my flight leaves at eight"),
            ex("quiz", "Qual documento de identificação você apresenta no aeroporto?", "passport", ["passport", "map", "luggage"]),
            ex("audio", "Escute e transcreva:", "where is my luggage", audio_text="Where is my luggage?"),
            ex("speak", "Diga o que você tem para a viagem:", "i have a ticket", audio_text="I have a ticket."),
        ],
    },
    "profissoes": {
        "lesson": _lesson_revision(
            "Profissões podem ser apresentadas com **be + a/an** ou com **work as**. Use o artigo no singular: **She is a dentist**; depois de **work as**, também é natural dizer **works as a photographer**.",
            [
                ("My sister is a dentist.", "Minha irmã é dentista."),
                ("The lawyer works in a company.", "O advogado trabalha em uma empresa."),
            ],
            [
                "Não omita o artigo: **He is a pilot**, não *He is pilot*.",
                "**Lawyer** é advogado; **accountant** é contador. Não escolha apenas pelo som inicial.",
            ],
            "Use a profissão em uma frase com artigo e conecte-a a pessoa, local de trabalho ou atividade.",
        ),
        "exercises": [
            ex("text", "Traduza: Minha irmã é dentista.", "my sister is a dentist"),
            ex("quiz", "Como se diz 'bombeiro' em inglês?", "firefighter", ["firefighter", "waiter", "actor"]),
            ex("audio", "Escute e transcreva:", "the lawyer works in a company", audio_text="The lawyer works in a company."),
            ex("speak", "Diga uma profissão que você gostaria de ter:", "i want to be a pilot", audio_text="I want to be a pilot."),
        ],
    },
    "educacao": {
        "lesson": _lesson_revision(
            "**Subject** é a disciplina; **class** é a aula ou turma; **degree** é o diploma/curso superior. Use **study at** para a instituição e **have an exam** para uma prova específica.",
            [
                ("I have an exam tomorrow.", "Tenho uma prova amanhã."),
                ("I am learning English.", "Estou aprendendo inglês."),
            ],
            [
                "Não use *I study in university* no padrão trabalhado; **I study at the university** é a forma natural.",
                "Não confunda **subject** (disciplina) com **class** (aula/turma).",
            ],
            "Nomeie a instituição, a disciplina ou a avaliação e monte uma frase com **study, learn** ou **have an exam**.",
        ),
        "exercises": [
            ex("text", "Traduza: Tenho uma prova amanhã.", "i have an exam tomorrow"),
            ex("quiz", "O que significa 'degree'?", "diploma ou curso superior", ["diploma ou curso superior", "aula", "prova"]),
            ex("audio", "Escute e transcreva:", "i am learning english", audio_text="I am learning English."),
            ex("speak", "Diga sua matéria favorita:", "science is my favorite subject", audio_text="Science is my favorite subject."),
        ],
    },
    "saude": {
        "lesson": _lesson_revision(
            "Para sintomas e necessidades de saúde, use combinações fixas: **have a headache**, **have a cold**, **need to see a doctor**. **Medicine** é o remédio; **appointment** é a consulta marcada.",
            [
                ("I need an appointment.", "Preciso de uma consulta."),
                ("I have a cold.", "Estou resfriado(a)."),
            ],
            [
                "Não diga *I am a headache*; diga **I have a headache**.",
                "Use **a** antes de **headache/cold** quando o sintoma é contado como uma condição específica.",
            ],
            "Memorize o sintoma com o verbo que o acompanha e use **need to see a doctor** para pedir atendimento.",
        ),
        "exercises": [
            ex("text", "Traduza: Preciso marcar uma consulta.", "i need an appointment"),
            ex("quiz", "Qual palavra significa 'remédio'?", "medicine", ["medicine", "appointment", "pain"]),
            ex("audio", "Escute e transcreva:", "i have a cold", audio_text="I have a cold."),
            ex("speak", "Diga como você está hoje:", "i am healthy today", audio_text="I am healthy today."),
        ],
    },
    "tecnologia": {
        "lesson": _lesson_revision(
            "Em tecnologia, diferencie o aparelho (**computer, laptop, phone, tablet**) do conteúdo ou serviço (**app, website, email**). **Battery is low** descreve pouca carga; não significa que o aparelho está quebrado.",
            [
                ("The battery is low.", "A bateria está fraca."),
                ("I use my laptop at home.", "Eu uso meu notebook em casa."),
            ],
            [
                "**Phone** costuma significar celular no contexto cotidiano; não confunda com **screen**, a tela.",
                "Não diga *the battery has low*; o padrão é **The battery is low**.",
            ],
            "Nomeie o dispositivo, diga o que você faz com ele e descreva uma condição simples, como novo ou sem carga.",
        ),
        "exercises": [
            ex("text", "Traduza: A bateria está fraca.", "the battery is low"),
            ex("quiz", "Onde você lê uma página na internet?", "website", ["website", "battery", "screen"]),
            ex("audio", "Escute e transcreva:", "i use my laptop at home", audio_text="I use my laptop at home."),
            ex("speak", "Descreva seu computador:", "my computer is new", audio_text="My computer is new."),
        ],
    },
    "entretenimento": {
        "lesson": _lesson_revision(
            "**Movie** é filme, **series** é série e **concert** é show musical. Use **watch** para filmes e séries e **go to** para eventos ou lugares, como **go to a concert**.",
            [
                ("Let's watch a movie.", "Vamos assistir a um filme."),
                ("The series is very interesting.", "A série é muito interessante."),
            ],
            [
                "Não confunda **concert** (show musical) com **theater** (teatro).",
                "Para assistir a um filme, use **watch a movie**, não *see a movie* no modelo básico deste tópico.",
            ],
            "Escolha o tipo de entretenimento, use o verbo adequado e acrescente preferência, convite ou experiência.",
        ),
        "exercises": [
            ex("text", "Traduza: Vamos assistir a um filme.", "let's watch a movie"),
            ex("quiz", "Qual evento normalmente envolve música ao vivo?", "concert", ["concert", "theater", "game"]),
            ex("audio", "Escute e transcreva:", "the series is very interesting", audio_text="The series is very interesting."),
            ex("speak", "Diga uma atividade de entretenimento:", "we went to the theater", audio_text="We went to the theater."),
        ],
    },
    "relacionamentos": {
        "lesson": _lesson_revision(
            "Use **best friend, boyfriend, girlfriend, husband, wife** para relações próximas e **colleague/neighbor** para relações do trabalho ou da vizinhança. O possessivo mostra a relação com quem fala.",
            [
                ("I trust my best friend.", "Eu confio no meu melhor amigo/minha melhor amiga."),
                ("She is my wife.", "Ela é minha esposa."),
            ],
            [
                "**Colleague** é colega de trabalho; para colega de classe, a palavra é **classmate**.",
                "Não confunda **boyfriend/girlfriend** com **friend**: o primeiro indica relacionamento romântico.",
            ],
            "Associe a palavra ao tipo de relação e use **my/his/her** para deixar claro de quem você está falando.",
        ),
        "exercises": [
            ex("text", "Traduza: Ele é meu colega de trabalho.", "he is my colleague"),
            ex("quiz", "Como se diz 'vizinha' em inglês?", "neighbor", ["neighbor", "colleague", "girlfriend"]),
            ex("audio", "Escute e transcreva:", "i trust my best friend", audio_text="I trust my best friend."),
            ex("speak", "Apresente sua esposa:", "she is my wife", audio_text="She is my wife."),
        ],
    },
    "dinheiro": {
        "lesson": _lesson_revision(
            "**Money** é dinheiro em geral; **cash** é dinheiro em espécie; **card** e **credit card** são meios de pagamento. **Price** é o preço, **cost** é o custo e **change** é o troco em uma compra.",
            [
                ("I need some cash.", "Preciso de dinheiro em espécie."),
                ("Can I pay by card?", "Posso pagar com cartão?"),
            ],
            [
                "Não confunda **change** como troco com uma pergunta sobre mudança; o contexto de pagamento resolve.",
                "**Money** é incontável; para quantificar, use **some money** ou uma moeda/valor específico.",
            ],
            "Identifique se a frase fala de dinheiro, forma de pagamento, preço ou troco e escolha o vocabulário correspondente.",
        ),
        "exercises": [
            ex("text", "Traduza: Eu preciso de dinheiro em espécie.", "i need some cash"),
            ex("quiz", "Qual palavra significa o valor cobrado por um produto?", "price", ["price", "change", "wallet"]),
            ex("audio", "Escute e transcreva:", "can i pay by card", audio_text="Can I pay by card?"),
            ex("speak", "Entregue o troco em voz alta:", "here is your change", audio_text="Here is your change."),
        ],
    },
    "compras-e-pagamentos": {
        "lesson": _lesson_revision(
            "Este cenário amplia a compra para depois da escolha: experimentar, verificar tamanho, pagar e pedir reembolso. **Try on** é usado para roupa; **receipt** é o recibo; **refund** é o reembolso.",
            [
                ("This shirt is too small.", "Esta camisa é pequena demais."),
                ("Can I get a refund?", "Posso receber um reembolso?"),
            ],
            [
                "Não confunda **refund** (reembolso) com **receipt** (recibo).",
                "Em **try it on**, o pronome vem entre verbo e partícula; não diga *try on it* no modelo estudado.",
            ],
            "Pratique o ciclo experimentar, avaliar o tamanho, pagar e resolver um problema com o produto.",
        ),
        "exercises": [
            ex("text", "Traduza: Esta camisa é pequena demais.", "this shirt is too small"),
            ex("quiz", "Quem recebe o pagamento em uma loja?", "cashier", ["cashier", "receipt", "discount"]),
            ex("audio", "Escute e transcreva:", "can i get a refund", audio_text="Can I get a refund?"),
            ex("speak", "Pergunte se pode experimentar:", "can i try it on", audio_text="Can I try it on?"),
        ],
    },
    "no-restaurante": {
        "lesson": _lesson_revision(
            "No restaurante, **order** é pedir, **dish** é o prato servido, **meal** é a refeição e **dessert** é a sobremesa. Use **would like** para um pedido educado e **make a reservation** para reservar.",
            [
                ("The dessert is delicious.", "A sobremesa está deliciosa."),
                ("Could we have the bill, please?", "Poderíamos ter a conta, por favor?"),
            ],
            [
                "Não confunda **dish** (prato de comida) com **plate** (prato físico), que não é o foco deste tópico.",
                "**Tip** é gorjeta no contexto da conta; não significa apenas 'dica'.",
            ],
            "Monte o pedido com **would like/order**, identifique a parte da refeição e use frases educadas para conta e reserva.",
        ),
        "exercises": [
            ex("text", "Traduza: A sobremesa está deliciosa.", "the dessert is delicious"),
            ex("quiz", "O que vem normalmente antes do prato principal?", "appetizer", ["appetizer", "dessert", "tip"]),
            ex("audio", "Escute e transcreva:", "could we have the bill please", audio_text="Could we have the bill, please?"),
            ex("speak", "Faça uma reserva:", "i would like to make a reservation", audio_text="I would like to make a reservation."),
        ],
    },
    "hoteis": {
        "lesson": _lesson_revision(
            "No hotel, combine o tipo de quarto com a reserva e a recepção. **Check in** é a ação de entrar/fazer registro; **check-in** é o substantivo usado para o processo.",
            [
                ("Breakfast is included.", "O café da manhã está incluído."),
                ("Could I have the room key, please?", "Eu poderia ter a chave do quarto, por favor?"),
            ],
            [
                "Não confunda **single room** (quarto de solteiro) com **double room** (quarto de casal).",
                "Como verbo, escreva **check in** sem hífen: **I want to check in**.",
            ],
            "Use **I have a reservation**, diga o tipo de quarto e peça chave, café da manhã ou ajuda na recepção.",
        ),
        "exercises": [
            ex("text", "Traduza: O café da manhã está incluído.", "breakfast is included"),
            ex("quiz", "Qual expressão significa sair do hotel?", "check out", ["check out", "check in", "check room"]),
            ex("audio", "Escute e transcreva:", "could i have the room key please", audio_text="Could I have the room key, please?"),
            ex("speak", "Diga qual quarto você reservou:", "i have a double room", audio_text="I have a double room."),
        ],
    },
    "transporte": {
        "lesson": _lesson_revision(
            "Em transportes, **departure** é partida e **arrival** é chegada. **Platform** costuma ser de trem/ônibus; **gate** é o portão de embarque do aeroporto; **schedule** é o horário.",
            [
                ("The flight arrives at ten.", "O voo chega às dez."),
                ("The train is on time.", "O trem está no horário."),
            ],
            [
                "Não confunda **arrival** com **departure**; uma é chegada, a outra é partida.",
                "**Delayed** significa atrasado por um imprevisto; **late** é a descrição geral de algo que não chegou no horário.",
            ],
            "Leia o painel de transporte procurando horário, partida, chegada, plataforma/portão e informação sobre atraso.",
        ),
        "exercises": [
            ex("text", "Traduza: O voo chega às dez.", "the flight arrives at ten"),
            ex("quiz", "Em um aeroporto, onde você embarca?", "gate", ["gate", "platform", "fare"]),
            ex("audio", "Escute e transcreva:", "what time is the departure", audio_text="What time is the departure?"),
            ex("speak", "Diga que o trem está no horário:", "the train is on time", audio_text="The train is on time."),
        ],
    },
    "natureza": {
        "lesson": _lesson_revision(
            "**Sea** e **ocean** são grandes extensões de água; **beach** é a praia, a faixa de areia. Use **there is/are** para descrever o que existe em uma paisagem.",
            [
                ("The sky is blue.", "O céu é azul."),
                ("There are trees near the river.", "Há árvores perto do rio."),
            ],
            [
                "Não use **beach** para a água; beach é a praia, enquanto **sea/ocean** são o mar/oceano.",
                "Com **trees**, use **there are**, não *there is*.",
            ],
            "Nomeie a paisagem, descreva-a com adjetivos e indique o que existe nela usando **there is/there are**.",
        ),
        "exercises": [
            ex("text", "Traduza: O céu é azul.", "the sky is blue"),
            ex("quiz", "Qual palavra significa 'mar'?", "sea", ["sea", "beach", "forest"]),
            ex("audio", "Escute e transcreva:", "there are trees near the river", audio_text="There are trees near the river."),
            ex("speak", "Faça um convite para a praia:", "let's go to the beach", audio_text="Let's go to the beach."),
        ],
    },
    "cidade-e-interior": {
        "lesson": _lesson_revision(
            "**Downtown** é o centro, **suburb** é uma área residencial próxima da cidade e **countryside** é a zona rural. Use adjetivos como **busy** e **quiet** para comparar ambientes.",
            [
                ("Downtown is busy.", "O centro é movimentado."),
                ("I live in a quiet suburb.", "Eu moro em um subúrbio tranquilo."),
            ],
            [
                "Não traduza **countryside** simplesmente como qualquer cidade pequena; é a zona rural/interior.",
                "**Traffic** é trânsito; **crowd** é multidão. Um pode causar o outro, mas não são a mesma coisa.",
            ],
            "Identifique o ambiente, escolha o lugar correto e descreva movimento, silêncio, trânsito ou poluição.",
        ),
        "exercises": [
            ex("text", "Traduza: O centro é movimentado.", "downtown is busy"),
            ex("quiz", "Qual lugar é a zona rural?", "countryside", ["countryside", "downtown", "suburb"]),
            ex("audio", "Escute e transcreva:", "there is a lot of traffic downtown", audio_text="There is a lot of traffic downtown."),
            ex("speak", "Descreva onde você mora:", "i live in a quiet suburb", audio_text="I live in a quiet suburb."),
        ],
    },
    "problemas-do-dia-a-dia": {
        "lesson": _lesson_revision(
            "Para relatar um problema, diga o que aconteceu e onde está a dificuldade: **My car is broken**, **I am stuck in traffic**, **I lost my wallet**. Depois, peça uma solução com **Can you...?**.",
            [
                ("Can you fix my computer?", "Você pode consertar meu computador?"),
                ("I am late because of traffic.", "Estou atrasado(a) por causa do trânsito."),
            ],
            [
                "Não use *I am stuck on traffic*; a expressão é **stuck in traffic**.",
                "**Lost** significa perdido; para dizer quebrado, use **broken**, não *lost*.",
            ],
            "Nomeie o problema, diga a consequência e faça um pedido claro para obter ajuda ou reparo.",
        ),
        "exercises": [
            ex("text", "Traduza: Perdi minha carteira.", "i lost my wallet"),
            ex("quiz", "O que significa 'I am stuck in traffic'?", "Estou preso no trânsito.", ["Estou preso no trânsito.", "Estou em casa.", "Estou consertando o carro."]),
            ex("audio", "Escute e transcreva:", "can you fix my computer", audio_text="Can you fix my computer?"),
            ex("speak", "Explique por que você está atrasado:", "i am late because of traffic", audio_text="I am late because of traffic."),
        ],
    },
})


TARGET_TOPIC_ENHANCEMENTS.update({
    "revisao-presente-simples": {
        "lesson": _lesson_revision(
            "No presente simples, separe a afirmação das formas com auxiliar. **She works** tem **-s**; **She doesn't work** e **Does she work?** usam o verbo base.",
            [
                ("She doesn't work on Sundays.", "Ela não trabalha aos domingos."),
                ("Do you usually walk to work?", "Você geralmente vai a pé para o trabalho?"),
            ],
            [
                "Não use *She don't*; a terceira pessoa pede **doesn't**.",
                "Depois de **does**, não repita a marca de terceira pessoa: **Does he play?**.",
            ],
            "Afirme com a conjugação correta, negue com **don't/doesn't** e pergunte com **Do/Does + verbo base**.",
        ),
        "exercises": [
            ex("text", "Traduza: Ela não trabalha aos domingos.", "she doesn't work on sundays"),
            ex("quiz", "Complete: '___ he play football?'", "Does", ["Does", "Do", "Is"]),
            ex("audio", "Escute e transcreva:", "do you usually walk to work", audio_text="Do you usually walk to work?"),
            ex("speak", "Diga onde ela mora:", "she lives near the school", audio_text="She lives near the school."),
        ],
    },
    "presente-continuo": {
        "lesson": _lesson_revision(
            "O presente contínuo mostra uma ação em andamento agora. Use **am/is/are + -ing** e observe as mudanças de escrita: **make/making**, **run/running**, **wait/waiting**.",
            [
                ("I am studying now.", "Estou estudando agora."),
                ("They are making dinner.", "Eles estão fazendo o jantar."),
            ],
            [
                "Não omita o verbo **be**: não diga *I studying*; diga **I am studying**.",
                "Depois de **are/is/am**, use **-ing**, não a forma simples do verbo.",
            ],
            "Escolha a forma de **be**, transforme o verbo em **-ing** e use marcadores como **now** quando a ação acontece neste momento.",
        ),
        "exercises": [
            ex("text", "Traduza: Estou estudando agora.", "i am studying now"),
            ex("quiz", "Complete: 'They are ___ dinner.' (make)", "making", ["making", "make", "made"]),
            ex("audio", "Escute e transcreva:", "what are you doing", audio_text="What are you doing?"),
            ex("speak", "Diga o que vocês estão fazendo:", "we are waiting for the bus", audio_text="We are waiting for the bus."),
        ],
    },
    "passado-simples": {
        "lesson": _lesson_revision(
            "Use o passado simples para uma ação terminada. Verbos regulares recebem **-ed**, mas verbos frequentes como **see/saw** e **have/had** são irregulares. Com **did/didn't**, o verbo volta à forma base.",
            [
                ("She saw the movie yesterday.", "Ela viu o filme ontem."),
                ("I visited my grandmother last weekend.", "Visitei minha avó no fim de semana passado."),
            ],
            [
                "Não diga *didn't ate*; diga **didn't eat**.",
                "Não use **-ed** em todo verbo: o passado de **see** é **saw**, não *seed*.",
            ],
            "Procure o marcador de passado, escolha o verbo regular ou irregular e use a forma base depois de **did/didn't**.",
        ),
        "exercises": [
            ex("text", "Traduza: Ela viu o filme ontem.", "she saw the movie yesterday"),
            ex("quiz", "Qual é o passado de 'have'?", "had", ["had", "haved", "has"]),
            ex("audio", "Escute e transcreva:", "did you enjoy the trip", audio_text="Did you enjoy the trip?"),
            ex("speak", "Conte uma ação passada:", "i visited my grandmother last weekend", audio_text="I visited my grandmother last weekend."),
        ],
    },
    "futuro-going-to": {
        "lesson": _lesson_revision(
            "Use **going to** quando o plano já está decidido. A estrutura completa é **am/is/are going to + verbo base**; a forma de **be** muda, mas **going to** e o verbo principal não.",
            [
                ("She is going to study tonight.", "Ela vai estudar hoje à noite."),
                ("Are you going to cook dinner?", "Você vai fazer o jantar?"),
            ],
            [
                "Não diga *I going to travel*; inclua **am**.",
                "Depois de **going to**, use verbo base: **going to buy**, não *going to buying*.",
            ],
            "Confirme se o plano já existe, escolha **am/is/are** e mantenha o verbo principal na forma base.",
        ),
        "exercises": [
            ex("text", "Traduza: Ela vai estudar hoje à noite.", "she is going to study tonight"),
            ex("quiz", "Você já comprou as passagens. Qual frase descreve o plano?", "I am going to travel.", ["I am going to travel.", "I traveled yesterday.", "I travel every day."]),
            ex("audio", "Escute e transcreva:", "are you going to cook dinner", audio_text="Are you going to cook dinner?"),
            ex("speak", "Diga um plano para amanhã:", "we are going to visit them tomorrow", audio_text="We are going to visit them tomorrow."),
        ],
    },
    "futuro-will": {
        "lesson": _lesson_revision(
            "**Will** serve para previsões, promessas e decisões tomadas no momento. Ele não muda com a pessoa e vem seguido do verbo base. A negativa curta é **won't**.",
            [
                ("I think it will rain.", "Acho que vai chover."),
                ("I'll answer the phone.", "Eu atendo o telefone. (decisão na hora)"),
            ],
            [
                "Não diga *will goes*; depois de **will**, use **go**.",
                "Não confunda **won't** com **want**; o primeiro é a negativa de **will**.",
            ],
            "Use **will + verbo base** para previsão ou decisão imediata e **won't + verbo base** para negar.",
        ),
        "exercises": [
            ex("text", "Traduza: Acho que vai chover.", "i think it will rain"),
            ex("quiz", "Alguém bate à porta agora. Qual decisão é natural?", "I'll answer the door.", ["I'll answer the door.", "I answered the door yesterday.", "I am answer the door."]),
            ex("audio", "Escute e transcreva:", "will you call me tonight", audio_text="Will you call me tonight?"),
            ex("speak", "Faça uma promessa negativa:", "i won't forget", audio_text="I won't forget."),
        ],
    },
    "contaveis-e-incontaveis": {
        "lesson": _lesson_revision(
            "Contáveis aceitam número e plural; incontáveis representam substâncias ou ideias como massa. Para contar uma substância, conte o recipiente ou a unidade: **two bottles of water** e **a piece of information**.",
            [
                ("I need two bottles of water.", "Preciso de duas garrafas de água."),
                ("Information is useful.", "Informação é útil."),
            ],
            [
                "Não diga *two waters* quando quer dizer dois recipientes; use **two bottles of water**.",
                "**Information** não recebe plural no inglês básico: diga **some information**.",
            ],
            "Pergunte se a palavra pode ser contada diretamente; use plural para contáveis e recipiente/medida para incontáveis.",
        ),
        "exercises": [
            ex("text", "Traduza: Duas garrafas de água.", "two bottles of water"),
            ex("quiz", "Qual palavra é incontável?", "information", ["information", "book", "apple"]),
            ex("audio", "Escute e transcreva:", "how much rice do we need", audio_text="How much rice do we need?"),
            ex("speak", "Peça uma informação:", "i need a piece of information", audio_text="I need a piece of information."),
        ],
    },
    "some-any": {
        "lesson": _lesson_revision(
            "Use **some** em afirmações e em ofertas/pedidos; use **any** em perguntas e negativas na regra geral. A escolha depende do tipo de frase e do substantivo que vem depois.",
            [
                ("I have some questions.", "Eu tenho algumas perguntas."),
                ("There aren't any eggs.", "Não há ovos."),
            ],
            [
                "Não use *I don't have some apples* na negativa padrão; diga **I don't have any apples**.",
                "Em uma oferta, **Would you like some coffee?** é natural e não contradiz o uso de **some** em ofertas.",
            ],
            "Afirmação normalmente pede **some**, pergunta/negação pede **any**, e o substantivo deve continuar contável ou incontável de modo coerente.",
        ),
        "exercises": [
            ex("text", "Traduza: Eu tenho algumas perguntas.", "i have some questions"),
            ex("quiz", "Complete: 'There aren't ___ eggs.'", "any", ["any", "some", "a"]),
            ex("audio", "Escute e transcreva:", "would you like some coffee", audio_text="Would you like some coffee?"),
            ex("quiz", "Complete a pergunta neutra: 'Do you have ___ water?'", "any", ["any", "many", "a"]),
        ],
    },
    "much-many": {
        "lesson": _lesson_revision(
            "**Many** acompanha contáveis no plural; **much** acompanha incontáveis. Em conversas afirmativas, **a lot of** costuma soar mais natural, mas **much/many** são importantes em perguntas e negativas.",
            [
                ("How many students are there?", "Quantos alunos há?"),
                ("I don't have much time.", "Não tenho muito tempo."),
            ],
            [
                "Não diga *How much books*; use **How many books**.",
                "Não use **many** com **time, money** ou **water** quando tratados como incontáveis.",
            ],
            "Veja se o substantivo tem plural: plural contável leva **many**; incontável leva **much**.",
        ),
        "exercises": [
            ex("text", "Traduza: Quantos alunos há na sala?", "how many students are there"),
            ex("quiz", "Complete: 'How ___ money do you have?'", "much", ["much", "many", "a lot"]),
            ex("audio", "Escute e transcreva:", "there aren't many people here", audio_text="There aren't many people here."),
            ex("speak", "Diga que você tem pouco tempo:", "i don't have much time", audio_text="I don't have much time."),
        ],
    },
    "a-lot-of": {
        "lesson": _lesson_revision(
            "**A lot of** vem antes do substantivo e funciona tanto com contáveis quanto com incontáveis. O verbo depois dele concorda com o substantivo: **There are a lot of shops**, mas **There is a lot of water**.",
            [
                ("There are a lot of shops in this city.", "Há muitas lojas nesta cidade."),
                ("She has a lot of work today.", "Ela tem muito trabalho hoje."),
            ],
            [
                "Não use *a lot* sozinho antes do substantivo; diga **a lot of shops**.",
                "Não trate **work** como plural nesse sentido: **a lot of work**, não *a lot of works*.",
            ],
            "Coloque **a lot of** antes do nome e escolha **is/are** conforme o substantivo que vem depois.",
        ),
        "exercises": [
            ex("text", "Traduza: Há muitas lojas nesta cidade.", "there are a lot of shops in this city"),
            ex("quiz", "Qual frase usa 'a lot of' com incontável?", "I drink a lot of water.", ["I drink a lot of water.", "I drink a lot water.", "I drink a lot of waters."]),
            ex("audio", "Escute e transcreva:", "she has a lot of work today", audio_text="She has a lot of work today."),
            ex("speak", "Diga o que vocês comem muito:", "we eat a lot of fruit", audio_text="We eat a lot of fruit."),
        ],
    },
    "must-have-to": {
        "lesson": _lesson_revision(
            "**Must** e **have to** expressam obrigação. A diferença mais importante está na negativa: **mustn't** proíbe; **don't have to** diz que algo não é necessário.",
            [
                ("You don't have to come tomorrow.", "Você não precisa vir amanhã."),
                ("You must wear a seat belt.", "Você deve usar cinto de segurança."),
            ],
            [
                "Não traduza **mustn't** como 'não precisa'; significa **é proibido**.",
                "Com **he/she**, use **has to**: **She has to study**, não *She have to study*.",
            ],
            "Separe obrigação, proibição e ausência de necessidade: **must/have to**, **mustn't**, **don't have to**.",
        ),
        "exercises": [
            ex("text", "Traduza: Você não precisa vir amanhã.", "you don't have to come tomorrow"),
            ex("quiz", "Qual frase diz que é proibido estacionar?", "You mustn't park here.", ["You mustn't park here.", "You don't have to park here.", "You have to park here."]),
            ex("audio", "Escute e transcreva:", "do i have to bring my passport", audio_text="Do I have to bring my passport?"),
            ex("speak", "Dê uma regra de segurança:", "you must wear a seat belt", audio_text="You must wear a seat belt."),
        ],
    },
    "comparativo-e-superlativo": {
        "lesson": _lesson_revision(
            "Use o comparativo para duas coisas e o superlativo para destacar uma dentro de um grupo. Adjetivos curtos costumam usar **-er/-est**; adjetivos longos usam **more/most**.",
            [
                ("This book is better than that one.", "Este livro é melhor que aquele."),
                ("This is the most interesting book.", "Este é o livro mais interessante."),
            ],
            [
                "O comparativo normalmente pede **than**: **better than**, não *better that*.",
                "Não misture **more** com **-er** no mesmo adjetivo: use **more expensive**, não *more expensiver*.",
            ],
            "Conte os elementos comparados, escolha **-er/more** ou **-est/most** e use **than** quando comparar dois.",
        ),
        "exercises": [
            ex("text", "Traduza: Este livro é melhor que aquele.", "this book is better than that one"),
            ex("quiz", "Qual é o comparativo de 'comfortable'?", "more comfortable", ["more comfortable", "comfortabler", "most comfortable"]),
            ex("audio", "Escute e transcreva:", "my new phone is cheaper than my old one", audio_text="My new phone is cheaper than my old one."),
            ex("speak", "Diga qual livro é o mais interessante:", "this is the most interesting book", audio_text="This is the most interesting book."),
        ],
    },
    "adverbios-de-modo": {
        "lesson": _lesson_revision(
            "Advérbios de modo respondem 'como?'. Muitos são formados com **-ly**, mas **good** vira **well**, e **fast** e **hard** mantêm a forma.",
            [
                ("She speaks English well.", "Ela fala inglês bem."),
                ("He drives very slowly.", "Ele dirige muito devagar."),
            ],
            [
                "Não use *She speaks good* para a maneira de falar; use **speaks well**.",
                "A grafia de **carefully** mantém o **-ful** antes de **-ly**; não escreva *carefuly*.",
            ],
            "Pergunte como a ação ocorre, forme o advérbio quando possível e memorize as exceções mais frequentes.",
        ),
        "exercises": [
            ex("text", "Traduza: Ela fala inglês bem.", "she speaks english well"),
            ex("quiz", "Qual é o advérbio de 'careful'?", "carefully", ["carefully", "carefuly", "careful"]),
            ex("audio", "Escute e transcreva:", "he drives very slowly", audio_text="He drives very slowly."),
            ex("speak", "Peça que alguém ouça com atenção:", "please listen carefully", audio_text="Please listen carefully."),
        ],
    },
    "pronomes-objeto": {
        "lesson": _lesson_revision(
            "O pronome objeto recebe a ação e costuma vir depois do verbo ou de uma preposição: **She knows me**, **Come with us**. A forma não pode ser escolhida pelo português de maneira automática.",
            [
                ("She knows me.", "Ela me conhece."),
                ("Can you help us?", "Você pode nos ajudar?"),
            ],
            [
                "Não use **I** depois do verbo: diga **She called me**, não *She called I*.",
                "Não confunda **them** (eles/elas como objeto) com **their** (deles/delas como possessivo).",
            ],
            "Identifique quem recebe a ação e escolha **me, you, him, her, it, us** ou **them** depois do verbo/preposição.",
        ),
        "exercises": [
            ex("text", "Complete: 'She knows ___.' (eu)", "me"),
            ex("quiz", "Complete: 'I called ___.' (eles)", "them", ["them", "they", "their"]),
            ex("audio", "Escute e transcreva:", "can you help us", audio_text="Can you help us?"),
            ex("speak", "Diga quem você viu:", "i saw him yesterday", audio_text="I saw him yesterday."),
        ],
    },
    "pronomes-possessivos": {
        "lesson": _lesson_revision(
            "Adjetivo possessivo acompanha o substantivo (**my car**); pronome possessivo substitui o grupo inteiro (**The car is mine**). Depois do pronome possessivo, não repita o substantivo.",
            [
                ("This pen is mine.", "Esta caneta é minha."),
                ("Is this bag yours?", "Esta bolsa é sua?"),
            ],
            [
                "Não diga *This is mine book*; use **This is my book** ou **This book is mine**.",
                "**Yours** não leva apóstrofo; *your's* está incorreto.",
            ],
            "Se o substantivo aparece, use **my/your/his/her/our/their**; se fica implícito, use **mine/yours/his/hers/ours/theirs**.",
        ),
        "exercises": [
            ex("text", "Traduza: Esta caneta é minha.", "this pen is mine"),
            ex("quiz", "Complete: 'That house is ___.' (deles)", "theirs", ["theirs", "their", "them"]),
            ex("audio", "Escute e transcreva:", "is this bag yours", audio_text="Is this bag yours?"),
            ex("speak", "Diga de quem é o carro:", "the red car is ours", audio_text="The red car is ours."),
        ],
    },
    "conjuncoes-basicas": {
        "lesson": _lesson_revision(
            "Conjunções conectam frases e mostram a relação entre ideias. **And** soma, **but** contrasta, **or** oferece escolha, **because** dá causa e **so** mostra resultado.",
            [
                ("I like tea, but I don't like coffee.", "Eu gosto de chá, mas não gosto de café."),
                ("I was tired, so I went home.", "Eu estava cansado, então fui para casa."),
            ],
            [
                "Não troque causa e resultado: **because** explica o motivo; **so** introduz a consequência.",
                "Use **or** para escolha entre alternativas, não **and**.",
            ],
            "Leia as duas ideias, identifique a relação e escolha **and/but/or/because/so** antes de completar a frase.",
        ),
        "exercises": [
            ex("text", "Traduza: Eu gosto de chá, mas não gosto de café.", "i like tea but i don't like coffee"),
            ex("quiz", "Complete: 'I stayed home ___ it was raining.'", "because", ["because", "but", "or"]),
            ex("audio", "Escute e transcreva:", "i was tired so i went home", audio_text="I was tired, so I went home."),
            ex("speak", "Ofereça duas opções:", "do you want tea or coffee", audio_text="Do you want tea or coffee?"),
        ],
    },
})


TARGET_TOPIC_ENHANCEMENTS.update({
    "apresentacoes": {
        "lesson": _lesson_revision(
            "Em uma situação real, combine apresentação e contexto: diga quem é a pessoa, de onde ela é ou o que faz. **Nice to meet you too** devolve a cordialidade do primeiro encontro.",
            [
                ("This is my sister, Ana. She is from Brazil.", "Esta é minha irmã, Ana. Ela é do Brasil."),
                ("I'm a student. Nice to meet you.", "Sou estudante. Prazer em conhecê-lo(a)."),
            ],
            [
                "Não diga *This are my friend*; uma pessoa singular pede **This is my friend**.",
                "**Nice to meet you** é encontro; ao reencontrar alguém, **Nice to see you** é mais natural.",
            ],
            "Apresente a pessoa com **This is...**, acrescente origem ou ocupação e responda ao primeiro encontro com **Nice to meet you too**.",
        ),
        "exercises": [
            ex("text", "Traduza: Esta é minha irmã, Ana.", "this is my sister ana"),
            ex("quiz", "Qual resposta combina com 'Nice to meet you.'?", "Nice to meet you too.", ["Nice to meet you too.", "I am from Brazil.", "Good night."]),
            ex("audio", "Escute e transcreva:", "he is from portugal", audio_text="He is from Portugal."),
            ex("speak", "Diga sua ocupação em voz alta:", "i am a student", audio_text="I am a student."),
        ],
    },
    "pedindo-informacoes": {
        "lesson": _lesson_revision(
            "Comece com **Excuse me** para chamar atenção e use uma pergunta completa. **Can you...?** faz um pedido educado; quando você não souber a resposta, diga isso diretamente e peça desculpas.",
            [
                ("Excuse me, where is the bank?", "Com licença, onde fica o banco?"),
                ("I'm sorry, I don't know.", "Desculpe, eu não sei."),
            ],
            [
                "Evite imperativos bruscos como *Give me information*; use **Excuse me, can you help me?**.",
                "Não confunda **What time does the store open?** com uma pergunta de preço.",
            ],
            "Chame a atenção, faça uma pergunta clara e agradeça ou aceite **I'm sorry, I don't know** quando não houver resposta.",
        ),
        "exercises": [
            ex("text", "Traduza: Com licença, onde fica o banco?", "excuse me where is the bank"),
            ex("quiz", "Você não sabe a informação. Qual resposta é educada?", "I'm sorry, I don't know.", ["I'm sorry, I don't know.", "Go away.", "I know nothing, you."]),
            ex("audio", "Escute e transcreva:", "what time does the museum open", audio_text="What time does the museum open?"),
            ex("speak", "Peça ajuda com educação:", "can you help me please", audio_text="Can you help me, please?"),
        ],
    },
    "pedindo-direcoes": {
        "lesson": _lesson_revision(
            "Para pedir um caminho, use **How do I get to...?**. Ao ouvir a resposta, procure verbos de movimento (**go**, **turn**) e referências de lugar (**corner**, **near**, **far**).",
            [
                ("Go straight and turn left at the corner.", "Siga em frente e vire à esquerda na esquina."),
                ("How do I get to the station?", "Como chego à estação?"),
            ],
            [
                "Não diga *How I get to...?*; o modelo inclui o auxiliar **do**.",
                "**Turn left** significa vire à esquerda; não confunda **left** com **right**.",
            ],
            "Pergunte com **How do I get to...?**, reconheça **go straight/turn** e confirme se o lugar é perto ou longe.",
        ),
        "exercises": [
            ex("text", "Traduza: Siga em frente e vire à esquerda.", "go straight and turn left"),
            ex("quiz", "Qual frase diz que o banco fica longe?", "The bank is far.", ["The bank is far.", "The bank is near.", "The bank is between."]),
            ex("audio", "Escute e transcreva:", "how do i get to the station", audio_text="How do I get to the station?"),
            ex("speak", "Dê uma instrução:", "turn right at the corner", audio_text="Turn right at the corner."),
        ],
    },
    "pedindo-comida": {
        "lesson": _lesson_revision(
            "No restaurante, transforme o desejo em pedido: **Can I have...?** é direto e educado; **I'd like...** expressa preferência de modo gentil. Para encerrar, peça **The bill, please**.",
            [
                ("I'd like a sandwich, please.", "Eu gostaria de um sanduíche, por favor."),
                ("Can I have the menu, please?", "Posso ter o cardápio, por favor?"),
            ],
            [
                "Evite *Give me coffee* em uma situação educada; use **Can I have...?**.",
                "Não confunda **menu** (cardápio) com **bill** (conta).",
            ],
            "Peça com **Can I have...** ou **I'd like...**, inclua **please** e use **The bill, please** quando quiser pagar.",
        ),
        "exercises": [
            ex("text", "Traduza: Posso ter o cardápio, por favor?", "can i have the menu please"),
            ex("quiz", "Qual frase pede uma bebida?", "I'd like a juice.", ["I'd like a juice.", "The bill, please.", "The menu, please."]),
            ex("audio", "Escute e transcreva:", "i'd like a sandwich please", audio_text="I'd like a sandwich, please."),
            ex("speak", "Peça a conta em voz alta:", "the bill please", audio_text="The bill, please."),
        ],
    },
    "fazendo-compras": {
        "lesson": _lesson_revision(
            "Uma conversa de compra pode seguir quatro passos: perguntar o preço, verificar uma cor ou tamanho, avaliar o preço e decidir. **I'll take it** mostra que você decidiu comprar.",
            [
                ("Do you have this shirt in blue?", "Você tem esta camisa em azul?"),
                ("It's too expensive. I'll take it.", "É caro demais. Vou levar."),
            ],
            [
                "Use **Do you have...?**; não monte a pergunta como *Is you have...?*.",
                "**Too expensive** significa caro demais, não apenas caro.",
            ],
            "Pergunte preço e disponibilidade, descreva o produto e encerre com **I'll take it** ou uma avaliação educada.",
        ),
        "exercises": [
            ex("text", "Traduza: Você tem esta camisa em azul?", "do you have this shirt in blue"),
            ex("quiz", "O que 'I'll take it' significa em uma loja?", "Vou levar.", ["Vou levar.", "Vou devolver.", "Vou experimentar."]),
            ex("audio", "Escute e transcreva:", "do you have this in blue", audio_text="Do you have this in blue?"),
            ex("speak", "Diga que o preço está alto demais:", "it's too expensive", audio_text="It's too expensive."),
        ],
    },
    "falando-da-familia": {
        "lesson": _lesson_revision(
            "Para falar de família, combine quantidade (**I have two brothers**) com uma informação sobre a pessoa (**My sister is a doctor**). Ao falar de outra pessoa no presente, observe o **-s** em **lives/works**.",
            [
                ("My mother works in a hospital.", "Minha mãe trabalha em um hospital."),
                ("How many brothers do you have? — I have two brothers.", "Quantos irmãos você tem? — Tenho dois irmãos."),
            ],
            [
                "Não diga *My mother work*; use **My mother works**.",
                "Depois de **I have**, use plural quando a quantidade for maior que um: **two brothers**.",
            ],
            "Diga quantos parentes você tem, apresente-os com **my** e descreva onde vivem ou o que fazem.",
        ),
        "exercises": [
            ex("text", "Traduza: Minha mãe trabalha em um hospital.", "my mother works in a hospital"),
            ex("quiz", "Qual resposta combina com 'How many brothers do you have?'", "I have two brothers.", ["I have two brothers.", "I am two brothers.", "I has two brothers."]),
            ex("audio", "Escute e transcreva:", "my father lives here", audio_text="My father lives here."),
            ex("speak", "Diga onde sua família mora:", "we live together", audio_text="We live together."),
        ],
    },
    "falando-da-rotina": {
        "lesson": _lesson_revision(
            "Uma rotina fica clara quando você combina ações com horários e períodos do dia. Use **at** com horas, **in the morning** para a manhã e **at night** para a noite.",
            [
                ("She wakes up at six.", "Ela acorda às seis."),
                ("I have lunch at noon.", "Eu almoço ao meio-dia."),
            ],
            [
                "Com **she**, escreva **wakes/sleeps**, não *wake/sleep* na afirmação.",
                "Não confunda **at night** com *in night*; a expressão fixa é **at night**.",
            ],
            "Organize a rotina em sequência, use presente simples, acrescente horários e revise o **-s** da terceira pessoa.",
        ),
        "exercises": [
            ex("text", "Traduza: Ela acorda às seis.", "she wakes up at six"),
            ex("quiz", "Qual resposta combina com 'What time do you go to work?'", "At eight.", ["At eight.", "In Brazil.", "With my sister."]),
            ex("audio", "Escute e transcreva:", "i have lunch at noon", audio_text="I have lunch at noon."),
            ex("speak", "Diga quando você dorme:", "i sleep at night", audio_text="I sleep at night."),
        ],
    },
    "gostos-e-preferencias": {
        "lesson": _lesson_revision(
            "Use **love, like, don't like, hate** e **prefer** para marcar intensidade ou escolha. Para confirmar uma pergunta com verbo comum, responda **Yes, I do** ou **No, I don't**.",
            [
                ("I prefer tea to coffee.", "Eu prefiro chá a café."),
                ("Do you like music? — Yes, I do.", "Você gosta de música? — Sim."),
            ],
            [
                "Não use **am** com **like**: diga **Do you like music?**, não *Are you like music?*.",
                "Em **prefer X to Y**, a preposição natural é **to**, não *than*.",
            ],
            "Diga a intensidade do gosto, pergunte com **Do you like...?** e responda usando o auxiliar **do**.",
        ),
        "exercises": [
            ex("text", "Traduza: Eu prefiro chá a café.", "i prefer tea to coffee"),
            ex("quiz", "Qual resposta curta é correta para 'Do you like music?'", "Yes, I do.", ["Yes, I do.", "Yes, I am.", "Yes, I like."]),
            ex("audio", "Escute e transcreva:", "i don't like rainy days", audio_text="I don't like rainy days."),
            ex("speak", "Diga algo de que você gosta muito:", "i love music", audio_text="I love music."),
        ],
    },
    "pedidos-simples": {
        "lesson": _lesson_revision(
            "**Can I...?** pede permissão ou algo para você; **Can you...?** pede que outra pessoa faça uma ação. O objeto do pedido vem depois de **have**, e **please** pode ficar no começo ou no fim.",
            [
                ("Can I have some tea, please?", "Posso ter um pouco de chá, por favor?"),
                ("Can you repeat, please?", "Você pode repetir, por favor?"),
            ],
            [
                "Não confunda o sujeito: **Can I have...?** é o pedido de quem fala; **Can you help...?** pede ação ao interlocutor.",
                "Não use *Can I to have*; depois de **can**, o verbo fica na forma base.",
            ],
            "Identifique quem fará a ação, escolha **Can I** ou **Can you**, acrescente o objeto e finalize com **please**.",
        ),
        "exercises": [
            ex("text", "Traduza: Você pode me ajudar?", "can you help me"),
            ex("quiz", "Qual frase pede algo para o próprio falante?", "Can I have some tea, please?", ["Can I have some tea, please?", "Can you repeat, please?", "Can you help me?"]),
            ex("audio", "Escute e transcreva:", "can i have some tea please", audio_text="Can I have some tea, please?"),
            ex("speak", "Peça repetição com educação:", "can you repeat please", audio_text="Can you repeat, please?"),
        ],
    },
    "entendendo-conversas-simples": {
        "lesson": _lesson_revision(
            "Para compreender uma conversa, identifique primeiro o tipo de pergunta e depois procure a resposta correspondente. **What's** pede nome/informação, **Where** pede origem/lugar, **How old** pede idade e **Do you like** pede sim ou não.",
            [
                ("What do you do? — I'm a student.", "O que você faz? — Sou estudante."),
                ("Can you repeat, please? — Sure.", "Você pode repetir, por favor? — Claro."),
            ],
            [
                "Não responda **How are you?** com seu nome; essa pergunta espera **I'm fine, thanks**.",
                "Ao não entender, use **I don't understand** e peça repetição em vez de abandonar a conversa.",
            ],
            "Ouça a primeira expressão, relacione pergunta e resposta e use frases de reparo quando uma parte da conversa escapar.",
        ),
        "exercises": [
            ex("quiz", "Para 'Where are you from?', qual resposta é natural?", "I'm from Brazil.", ["I'm from Brazil.", "I'm fine, thanks.", "I'm 20 years old."]),
            ex("text", "Traduza: Você pode repetir, por favor?", "can you repeat please"),
            ex("audio", "Escute e transcreva:", "what do you do", audio_text="What do you do?"),
            ex("speak", "Diga que você não entendeu:", "i don't understand", audio_text="I don't understand."),
        ],
    },
})


TARGET_TOPIC_ENHANCEMENTS.update({
    "membros-da-familia": {
        "lesson": _lesson_revision(
            "As palavras da família são usadas com possessivos e com **is/has**. **Cousin** serve para primo ou prima; o gênero só aparece quando o contexto exigir outra palavra, como **nephew** e **niece**.",
            [
                ("My uncle works here.", "Meu tio trabalha aqui."),
                ("Her husband is a teacher.", "O marido dela é professor."),
            ],
            [
                "Não confunda **nephew** (sobrinho) com **niece** (sobrinha).",
                "Não tente criar uma forma feminina de **cousin**; a mesma palavra vale para primo e prima.",
            ],
            "Revise a relação familiar, acrescente o possessivo correto e forme uma frase sobre onde a pessoa mora ou trabalha.",
        ),
        "exercises": [
            ex("quiz", "Como se diz 'esposa' em inglês?", "wife", ["wife", "husband", "aunt"]),
            ex("text", "Traduza: Meu tio trabalha aqui.", "my uncle works here"),
            ex("audio", "Escute e transcreva:", "her husband is a teacher", audio_text="Her husband is a teacher."),
            ex("speak", "Diga em voz alta:", "my aunt lives in brazil", audio_text="My aunt lives in Brazil."),
        ],
    },
    "partes-da-casa": {
        "lesson": _lesson_revision(
            "O nome do cômodo costuma aparecer com **the** quando falamos de um lugar específico. Use **in** para dizer em que cômodo algo acontece e associe cada cômodo à atividade mais natural.",
            [
                ("We eat dinner in the dining room.", "Nós jantamos na sala de jantar."),
                ("The car is in the garage.", "O carro está na garagem."),
            ],
            [
                "**Bedroom** é quarto; **bathroom** é banheiro. As palavras parecem semelhantes, mas não são intercambiáveis.",
                "Não retire o artigo em um cômodo específico: diga **in the kitchen**.",
            ],
            "Relacione cada cômodo a um objeto ou ação, use **in the** para localização e pratique frases curtas sobre sua casa.",
        ),
        "exercises": [
            ex("quiz", "Em qual cômodo você dorme?", "bedroom", ["bedroom", "kitchen", "garage"]),
            ex("text", "Traduza: Nós jantamos na sala de jantar.", "we eat dinner in the dining room"),
            ex("audio", "Escute e transcreva:", "the car is in the garage", audio_text="The car is in the garage."),
            ex("quiz", "Where do you take a shower?", "In the bathroom.", ["In the bathroom.", "In the garden.", "In the garage."]),
        ],
    },
    "alimentos-e-bebidas": {
        "lesson": _lesson_revision(
            "Use **eat** para comida e **drink** para líquidos. Para preferências, **I like...** é suficiente; para rotina, acrescente uma frequência como **every day**.",
            [
                ("I drink water every day.", "Eu bebo água todos os dias."),
                ("I eat rice and chicken.", "Eu como arroz e frango."),
            ],
            [
                "Não confunda o verbo **drink** com o substantivo bebida; o contexto e a posição na frase ajudam.",
                "Depois de **like**, não é obrigatório usar artigo com comida em sentido geral: **I like coffee**.",
            ],
            "Separe comida de bebida, use **eat/drink** no presente simples e combine o vocabulário com gostos e hábitos reais.",
        ),
        "exercises": [
            ex("text", "Traduza: Eu bebo água todos os dias.", "i drink water every day"),
            ex("quiz", "Qual destas palavras é uma bebida?", "juice", ["juice", "rice", "bread"]),
            ex("audio", "Escute e transcreva:", "i eat rice and chicken", audio_text="I eat rice and chicken."),
            ex("speak", "Diga algo de que você gosta:", "i like bananas", audio_text="I like bananas."),
        ],
    },
    "roupas-em-ingles": {
        "lesson": _lesson_revision(
            "Muitas roupas aparecem no plural porque são usadas aos pares ou têm formato de duas pernas, como **pants**. Use **wear** para falar do que veste e **need** para dizer o que precisa.",
            [
                ("I need a jacket.", "Eu preciso de uma jaqueta."),
                ("These pants are black.", "Esta calça é preta."),
            ],
            [
                "Não transforme **pants** em *pant* no uso normal; a palavra é plural.",
                "**Shoes** são sapatos e **socks** são meias; não troque as duas palavras por causa do uso em pares.",
            ],
            "Memorize a peça junto com uma cor ou uma ação: **wear shoes**, **need a jacket**, **a red dress**.",
        ),
        "exercises": [
            ex("text", "Traduza: Eu preciso de uma jaqueta.", "i need a jacket"),
            ex("quiz", "O que você usa na cabeça?", "a hat", ["a hat", "a jacket", "a shoe"]),
            ex("audio", "Escute e transcreva:", "these pants are black", audio_text="These pants are black."),
            ex("speak", "Diga a cor das suas meias:", "my socks are white", audio_text="My socks are white."),
        ],
    },
    "escola-e-materiais": {
        "lesson": _lesson_revision(
            "Diferencie a pessoa, o lugar e o material: **teacher** é professor, **classroom** é sala de aula e **notebook** é caderno. **Homework** é incontável e costuma aparecer sem artigo indefinido.",
            [
                ("My teacher is in the classroom.", "Minha professora está na sala de aula."),
                ("I have a pencil.", "Eu tenho um lápis."),
            ],
            [
                "Não diga *a homework* nem *homeworks*; use **some homework** ou simplesmente **homework**.",
                "**Notebook** é caderno; **book** é livro. Não use as palavras como sinônimas em uma lista de materiais.",
            ],
            "Associe cada palavra a uma cena de estudo e pratique **have**, **do homework** e localização na **classroom**.",
        ),
        "exercises": [
            ex("text", "Traduza: Minha professora está na sala de aula.", "my teacher is in the classroom"),
            ex("quiz", "O que significa 'homework'?", "dever de casa", ["dever de casa", "sala de aula", "lápis"]),
            ex("audio", "Escute e transcreva:", "i have a pencil", audio_text="I have a pencil."),
            ex("speak", "Apresente seu material:", "this is my notebook", audio_text="This is my notebook."),
        ],
    },
    "trabalho-e-profissoes": {
        "lesson": _lesson_revision(
            "Profissões no singular normalmente vêm com **a/an** depois de **be**: **She is a nurse**. Para falar do local, use **work in**; para a atividade profissional, use **work as**.",
            [
                ("She is an engineer.", "Ela é engenheira."),
                ("My brother is a doctor.", "Meu irmão é médico."),
            ],
            [
                "Não omita o artigo em **She is a nurse**; *She is nurse* não é o padrão.",
                "Use **an** antes do som de vogal, como em **an engineer**.",
            ],
            "Use **be + a/an + profissão**, e acrescente **work in** ou **work as** quando quiser dar mais contexto.",
        ),
        "exercises": [
            ex("text", "Traduza: Ela é engenheira.", "she is an engineer"),
            ex("quiz", "Como se diz 'policial' em inglês?", "police officer", ["police officer", "driver", "cook"]),
            ex("audio", "Escute e transcreva:", "my brother is a doctor", audio_text="My brother is a doctor."),
            ex("speak", "Diga uma profissão em voz alta:", "i am a teacher", audio_text="I am a teacher."),
        ],
    },
    "meios-de-transporte": {
        "lesson": _lesson_revision(
            "Use **by + transporte** para o meio geral: **by bus**, **by train**, **by bike**. O artigo desaparece depois de **by**; quando a ação é andar, a expressão fixa é **on foot**.",
            [
                ("She goes to work by bike.", "Ela vai trabalhar de bicicleta."),
                ("I travel by train.", "Eu viajo de trem."),
            ],
            [
                "Não diga *by the bus* para o meio de transporte em geral; diga **by bus**.",
                "A expressão é **on foot**, não *by foot*.",
            ],
            "Escolha o veículo, use **go/travel by...** e memorize **on foot** como exceção útil.",
        ),
        "exercises": [
            ex("text", "Traduza: Ela vai de bicicleta.", "she goes by bike"),
            ex("quiz", "Como se diz 'a pé'?", "on foot", ["on foot", "by foot", "in foot"]),
            ex("audio", "Escute e transcreva:", "the bus is late", audio_text="The bus is late."),
            ex("speak", "Diga como você viaja:", "i travel by train", audio_text="I travel by train."),
        ],
    },
    "clima-e-tempo": {
        "lesson": _lesson_revision(
            "O inglês usa **it** como sujeito obrigatório para o clima, mesmo quando o português não mostra um pronome. Combine **It is** com o adjetivo e, se quiser, com **today** ou **outside**.",
            [
                ("It is sunny today.", "Está ensolarado hoje."),
                ("It is hot outside.", "Está quente lá fora."),
            ],
            [
                "Não diga *Is sunny today*; inclua **It is**.",
                "**Hot** é quente e **cold** é frio; não confunda o clima com a temperatura de um objeto sem contexto.",
            ],
            "Para descrever o tempo, comece com **It is**, escolha o adjetivo e acrescente um marcador de lugar ou tempo.",
        ),
        "exercises": [
            ex("text", "Traduza: Hoje está ensolarado.", "it is sunny today"),
            ex("quiz", "O que significa 'It is cold'?", "Está frio.", ["Está frio.", "Está quente.", "Está ventando."]),
            ex("audio", "Escute e transcreva:", "it is hot outside", audio_text="It is hot outside."),
            ex("speak", "Descreva o tempo em voz alta:", "it is cloudy today", audio_text="It is cloudy today."),
        ],
    },
    "hobbies-e-lazer": {
        "lesson": _lesson_revision(
            "Para falar de lazer, use o verbo de atividade depois de **I like**. O padrão mais simples é **I like + substantivo** ou **I like to + verbo**; a atividade fica ligada a uma situação concreta.",
            [
                ("I like to read at night.", "Eu gosto de ler à noite."),
                ("She plays games at night.", "Ela joga à noite."),
            ],
            [
                "Não traduza *I like of music*; em inglês é **I like music**.",
                "Com **he/she**, lembre do **-s**: **She plays**, não *She play*.",
            ],
            "Escolha a atividade, forme **I like...** e acrescente quando ou onde ela acontece para criar uma frase natural.",
        ),
        "exercises": [
            ex("text", "Traduza: Eu gosto de ler.", "i like to read"),
            ex("quiz", "Qual frase significa 'Eu ouço música'?", "I listen to music.", ["I listen to music.", "I watch music.", "I read music."]),
            ex("audio", "Escute e transcreva:", "she plays games at night", audio_text="She plays games at night."),
            ex("speak", "Diga uma atividade de lazer:", "i like to travel", audio_text="I like to travel."),
        ],
    },
    "compras-e-lojas": {
        "lesson": _lesson_revision(
            "Em compras, **buy** é comprar e **sell** é vender. Para perguntar preço, use **How much is this?**; para dizer que quer algo, use **I want to buy...**.",
            [
                ("I want to buy a book.", "Eu quero comprar um livro."),
                ("How much is the shirt?", "Quanto custa a camisa?"),
            ],
            [
                "Não use **how many** para preço; a pergunta é **How much is...?**.",
                "**Cheap** é barato e **expensive** é caro; não confunda com **free**, que significa grátis.",
            ],
            "Pratique a sequência pedir preço, dizer o que quer comprar e avaliar se é **cheap** ou **expensive**.",
        ),
        "exercises": [
            ex("text", "Traduza: Eu quero comprar um livro.", "i want to buy a book"),
            ex("quiz", "Qual é o oposto de 'cheap'?", "expensive", ["expensive", "small", "free"]),
            ex("audio", "Escute e transcreva:", "how much is the shirt", audio_text="How much is the shirt?"),
            ex("speak", "Diga o que você precisa comprar:", "i need a new phone", audio_text="I need a new phone."),
        ],
    },
    "lugares-na-cidade": {
        "lesson": _lesson_revision(
            "O vocabulário fica mais fácil quando você liga o lugar à função: hospital para saúde, bank para dinheiro, restaurant para comida e museum para cultura. Para localizar, combine **Where is...?** com uma preposição.",
            [
                ("The hospital is next to the bank.", "O hospital fica ao lado do banco."),
                ("The restaurant is between the bank and the hotel.", "O restaurante fica entre o banco e o hotel."),
            ],
            [
                "Não confunda **hotel** com **hospital**; o som e o contexto são diferentes.",
                "Use **near** para perto e **next to** para imediatamente ao lado; não são sempre equivalentes.",
            ],
            "Identifique a função de cada lugar, pergunte **Where is...?** e descreva a posição com **near/next to/between**.",
        ),
        "exercises": [
            ex("text", "Traduza: O hospital fica ao lado do banco.", "the hospital is next to the bank"),
            ex("quiz", "Qual lugar é uma delegacia?", "police station", ["police station", "restaurant", "museum"]),
            ex("audio", "Escute e transcreva:", "the restaurant is between the bank and the hotel", audio_text="The restaurant is between the bank and the hotel."),
            ex("speak", "Diga onde você está:", "i am at the museum", audio_text="I am at the museum."),
        ],
    },
    "partes-do-corpo": {
        "lesson": _lesson_revision(
            "Partes do corpo aparecem com possessivos ou com **have**: **my hand**, **her eyes**, **I have blue eyes**. Para falar de dor, o inglês usa **have**: **My head hurts** ou **I have a headache**.",
            [
                ("She has brown eyes.", "Ela tem olhos castanhos."),
                ("My ears hurt.", "Minhas orelhas doem."),
            ],
            [
                "Não diga *I am a headache*; diga **I have a headache**.",
                "O plural de **foot** é **feet**, não *foots*.",
            ],
            "Use o possessivo para localizar a parte do corpo, **have** para características e **hurt** para dor.",
        ),
        "exercises": [
            ex("text", "Traduza: Meu braço.", "my arm"),
            ex("quiz", "Qual é o plural de 'foot'?", "feet", ["feet", "foots", "footses"]),
            ex("audio", "Escute e transcreva:", "she has brown eyes", audio_text="She has brown eyes."),
            ex("speak", "Diga em voz alta:", "my ears hurt", audio_text="My ears hurt."),
        ],
    },
    "verbos-comuns": {
        "lesson": _lesson_revision(
            "Aprenda cada verbo dentro de um pequeno contexto. **want** indica desejo, **need** necessidade, **see** percepção e **speak** comunicação. A mesma palavra pode ser mais fácil quando vem acompanhada de um objeto.",
            [
                ("I see my friends every week.", "Eu vejo meus amigos toda semana."),
                ("They play football on Saturdays.", "Eles jogam futebol aos sábados."),
            ],
            [
                "Não confunda **want** (querer) com **need** (precisar); o segundo expressa necessidade.",
                "Com **he/she**, aplique o presente simples: **She speaks**, não *She speak*.",
            ],
            "Revise o significado, use o verbo com um complemento e observe o **-s** da terceira pessoa no presente simples.",
        ),
        "exercises": [
            ex("text", "Traduza: Eu vejo meus amigos.", "i see my friends"),
            ex("quiz", "Qual frase expressa necessidade?", "I need water.", ["I need water.", "I want water.", "I see water."]),
            ex("audio", "Escute e transcreva:", "they play football", audio_text="They play football."),
            ex("speak", "Diga uma frase sobre idioma:", "i speak english", audio_text="I speak English."),
        ],
    },
    "adjetivos-comuns": {
        "lesson": _lesson_revision(
            "O adjetivo vem depois de **be** em frases como **The car is new** e antes do substantivo em **a new car**. Ele não ganha plural nem muda para masculino ou feminino.",
            [
                ("The house is big and beautiful.", "A casa é grande e bonita."),
                ("The new car is fast.", "O carro novo é rápido."),
            ],
            [
                "Não acrescente plural ao adjetivo: **big houses**, não *bigs houses*.",
                "**Good** é bom e **bad** é ruim; reserve **beautiful** para beleza, não para qualquer avaliação positiva.",
            ],
            "Coloque o adjetivo na posição certa, mantenha-o invariável e compare palavras por contraste, como **big/small** e **fast/slow**.",
        ),
        "exercises": [
            ex("text", "Traduza: A casa é grande e bonita.", "the house is big and beautiful"),
            ex("quiz", "Qual é o oposto de 'hot'?", "cold", ["cold", "fast", "new"]),
            ex("audio", "Escute e transcreva:", "the new car is fast", audio_text="The new car is fast."),
            ex("speak", "Diga como você está hoje:", "i am happy today", audio_text="I am happy today."),
        ],
    },
    "expressoes-do-dia-a-dia": {
        "lesson": _lesson_revision(
            "Expressões prontas são blocos de conversa. **You're welcome** responde a um agradecimento, **Me too** concorda com um gosto e **Take care** encerra a conversa de forma amigável.",
            [
                ("I'm sorry, I'm late.", "Desculpe, estou atrasado(a)."),
                ("Have a nice day! — You too!", "Tenha um bom dia! — Você também!"),
            ],
            [
                "Não responda **Thank you** com *No problem* em todo contexto sem perceber o sentido; **You're welcome** é a resposta direta.",
                "**See you soon** é uma despedida; não é uma forma de dizer que você está vendo alguém agora.",
            ],
            "Aprenda a expressão com a situação que a acompanha: agradecer, concordar, despedir-se ou desejar um bom dia.",
        ),
        "exercises": [
            ex("text", "Traduza: Desculpe, estou atrasado.", "i'm sorry i'm late"),
            ex("quiz", "Qual resposta combina com 'Have a nice day!'?", "You too!", ["You too!", "No problem!", "I don't know!"]),
            ex("audio", "Escute e transcreva:", "no problem see you soon", audio_text="No problem. See you soon."),
            ex("speak", "Despeça-se de forma amigável:", "take care", audio_text="Take care."),
        ],
    },
})


TARGET_TOPIC_ENHANCEMENTS.update({
    "pronomes-pessoais": {
        "lesson": _lesson_revision(
            "O pronome deve representar quem faz a ação. Escolha **he** ou **she** para pessoas, **it** para uma coisa ou animal e **we** quando o grupo inclui quem fala.",
            [
                ("Pedro and I are friends. We study together.", "Pedro e eu somos amigos. Nós estudamos juntos."),
                ("The dog is small. It is friendly.", "O cachorro é pequeno. Ele é dócil."),
            ],
            [
                "**I** sempre aparece com maiúscula, inclusive no meio da frase.",
                "Não use **he** ou **she** para objetos; para uma coisa, use **it**.",
            ],
            "Encontre o sujeito, escolha o pronome que o substitui e confira se **you** significa você ou vocês conforme o contexto.",
        ),
        "exercises": [
            ex("text", "Substitua 'Pedro and I' por um pronome: '___ are friends.'", "we"),
            ex("quiz", "Complete: '___ are from Brazil.' (eles)", "They", ["They", "We", "It"]),
            ex("audio", "Escute e transcreva:", "she is my friend", audio_text="She is my friend."),
            ex("speak", "Diga a frase em voz alta:", "they are students", audio_text="They are students."),
        ],
    },
    "verbo-to-be": {
        "lesson": _lesson_revision(
            "O verbo **to be** pode significar ser ou estar. A forma depende do sujeito: **am** com **I**, **is** com **he/she/it** e **are** com **you/we/they**. Na pergunta, ele vem antes do sujeito.",
            [
                ("Is she at home? — Yes, she is.", "Ela está em casa? — Sim, está."),
                ("They aren't tired.", "Eles não estão cansados."),
            ],
            [
                "Não use *I is* ou *you is*; memorize **I am** e **you are**.",
                "Na pergunta, não mantenha a ordem afirmativa: diga **Are you ready?**, não *You are ready?* em exercícios formais.",
            ],
            "Escolha **am/is/are**, acrescente **not** para negar e inverta o verbo com o sujeito para perguntar.",
        ),
        "exercises": [
            ex("text", "Traduza: Ela está em casa.", "she is at home"),
            ex("quiz", "Complete: 'They ___ tired.' (não estão)", "aren't", ["aren't", "isn't", "am not"]),
            ex("audio", "Escute e transcreva:", "are you ready", audio_text="Are you ready?"),
            ex("speak", "Diga a frase negativa em voz alta:", "i am not late", audio_text="I am not late."),
        ],
    },
    "adjetivos-possessivos": {
        "lesson": _lesson_revision(
            "O adjetivo possessivo vem antes do substantivo e concorda com quem possui algo, não com a coisa possuída. Assim, uma mulher tem **her book**, independentemente do gênero de *book*.",
            [
                ("Her name is Ana.", "O nome dela é Ana."),
                ("Their house is near the school.", "A casa deles é perto da escola."),
            ],
            [
                "Não use **she** antes de um substantivo para indicar posse; diga **her name**, não *she name*.",
                "Não confunda **its** (de coisa/animal) com **it's** (it is), que é uma contração diferente.",
            ],
            "Escolha **my, your, his, her, its, our** ou **their** pelo dono e coloque a palavra antes do substantivo.",
        ),
        "exercises": [
            ex("text", "Traduza: O nome dela é Ana.", "her name is ana"),
            ex("quiz", "Complete: 'This is ___ car.' (nosso)", "our", ["our", "their", "her"]),
            ex("audio", "Escute e transcreva:", "their house is near", audio_text="Their house is near."),
            ex("speak", "Diga uma informação sobre seu nome:", "my name is lucas", audio_text="My name is Lucas."),
        ],
    },
    "artigos-a-an-the": {
        "lesson": _lesson_revision(
            "Use **a/an** para uma coisa singular ainda não especificada e **the** quando o ouvinte sabe qual é. A escolha entre **a** e **an** depende do som inicial: **an orange**, mas **a university**.",
            [
                ("I see a dog. The dog is black.", "Eu vejo um cachorro. O cachorro é preto."),
                ("She studies at a university.", "Ela estuda em uma universidade."),
            ],
            [
                "Não escolha pelo desenho da primeira letra: **an hour** tem h mudo, mas **a university** começa com som de /y/.",
                "Não use **a/an** com substantivo plural ou incontável: diga **two books** e **some water**.",
            ],
            "Pergunte se o substantivo é singular e indefinido (**a/an**) ou específico (**the**); depois escute o som inicial.",
        ),
        "exercises": [
            ex("text", "Escreva a expressão correta para 'uma laranja'.", "an orange"),
            ex("quiz", "Complete: '___ university'", "a", ["a", "an", "the"]),
            ex("audio", "Escute e transcreva:", "i have a new phone", audio_text="I have a new phone."),
            ex("quiz", "Você já mencionou um cachorro e agora fala dele novamente. Complete: '___ dog is black.'", "The", ["The", "A", "An"]),
        ],
    },
    "singular-e-plural": {
        "lesson": _lesson_revision(
            "O plural regular costuma usar **-s**, mas terminações em **s, sh, ch, x** pedem **-es** e consoante + **y** vira **-ies**. Alguns plurais precisam ser memorizados, como **child/children**.",
            [
                ("There are three children in the park.", "Há três crianças no parque."),
                ("I have two boxes.", "Eu tenho duas caixas."),
            ],
            [
                "Depois de **two, three, five...**, use plural: **two boxes**, não *two box*.",
                "Não aplique a regra de **-s** a tudo: **woman/women** e **man/men** são irregulares.",
            ],
            "Observe a terminação da palavra, pratique alguns irregulares e confira se números maiores que um recebem substantivo no plural.",
        ),
        "exercises": [
            ex("quiz", "Qual é o plural de 'city'?", "cities", ["cities", "citys", "cityes"]),
            ex("text", "Escreva o plural de 'woman'.", "women"),
            ex("audio", "Escute e transcreva:", "three children are in the park", audio_text="Three children are in the park."),
            ex("quiz", "Qual frase tem o plural correto?", "I have two boxes.", ["I have two boxes.", "I have two box.", "I have two boxs."]),
        ],
    },
    "demonstrativos": {
        "lesson": _lesson_revision(
            "Pense em duas perguntas: está perto ou longe? É uma coisa ou mais de uma? **this/that** são singulares; **these/those** são plurais. O verbo acompanha: **is** no singular, **are** no plural.",
            [
                ("That is my car.", "Aquele é meu carro."),
                ("Those are your shoes.", "Aqueles são seus sapatos."),
            ],
            [
                "Não combine **these/those** com substantivo singular: diga **these books**, não *these book*.",
                "Não diga *this are*; perto e plural pede **these are**.",
            ],
            "Use **this/these** para perto, **that/those** para longe, e combine singular com **is** e plural com **are**.",
        ),
        "exercises": [
            ex("text", "Traduza: Aquele é meu carro.", "that is my car"),
            ex("quiz", "Você aponta para vários objetos perto de você. Complete: '___ are my books.'", "These", ["These", "This", "Those"]),
            ex("audio", "Escute e transcreva:", "those are your shoes", audio_text="Those are your shoes."),
            ex("speak", "Apresente um objeto próximo:", "this is my book", audio_text="This is my book."),
        ],
    },
    "there-is-there-are": {
        "lesson": _lesson_revision(
            "**There is/are** apresenta a existência de algo em um lugar. O verbo concorda com o item apresentado: **there is a bank**, mas **there are two banks**. Em perguntas, inverta **is/are** com **there**.",
            [
                ("There are two books on the table.", "Há dois livros sobre a mesa."),
                ("Is there a bank near here?", "Há um banco perto daqui?"),
            ],
            [
                "Não use **there is** com plural: diga **There are three students**.",
                "Não troque a estrutura por *it has* quando quer dizer que algo existe em um lugar.",
            ],
            "Confira o número do substantivo, escolha **there is/there are** e inverta para formar perguntas.",
        ),
        "exercises": [
            ex("text", "Traduza: Há dois livros na mesa.", "there are two books on the table"),
            ex("quiz", "Complete a negativa: '___ any parks here.'", "There aren't", ["There aren't", "There isn't", "There not are"]),
            ex("audio", "Escute e transcreva:", "is there a bank near here", audio_text="Is there a bank near here?"),
            ex("quiz", "Complete: '___ an apple in the bag.'", "There is", ["There is", "There are", "Is there"]),
        ],
    },
    "have-have-got": {
        "lesson": _lesson_revision(
            "**Have/has** expressa posse. Use **have** com I/you/we/they e **has** com he/she/it. Para pergunta e negativa com a forma simples, use **do/does**; com **have got**, a inversão é direta.",
            [
                ("She has two children.", "Ela tem dois filhos."),
                ("Does he have a car?", "Ele tem um carro?"),
            ],
            [
                "Depois de **does**, o verbo volta para **have**: **Does she have...?**, não *Does she has...?*.",
                "Não use *I has*; **has** só acompanha he, she e it.",
            ],
            "Use **have/has** na afirmação, **do/does + have** na pergunta e **don't/doesn't have** na negativa.",
        ),
        "exercises": [
            ex("text", "Traduza: Ela tem dois filhos.", "she has two children"),
            ex("quiz", "Complete: '___ he have a car?'", "Does", ["Does", "Do", "Is"]),
            ex("audio", "Escute e transcreva:", "she has a bike", audio_text="She has a bike."),
            ex("speak", "Diga em voz alta o que você tem:", "we have a problem", audio_text="We have a problem."),
        ],
    },
    "presente-simples": {
        "lesson": _lesson_revision(
            "O presente simples descreve hábitos e fatos. A terceira pessoa recebe **-s/-es** na afirmação, mas nas perguntas e negativas o auxiliar **does** já carrega essa marca e o verbo volta à forma base.",
            [
                ("She doesn't like tea.", "Ela não gosta de chá."),
                ("Do they live here?", "Eles moram aqui?"),
            ],
            [
                "Não diga *She don't like*; use **She doesn't like**.",
                "Não diga *Does he lives...?*; diga **Does he live...?**.",
            ],
            "Afirmação: sujeito + verbo; negativa: **don't/doesn't + base**; pergunta: **Do/Does + sujeito + base**.",
        ),
        "exercises": [
            ex("text", "Traduza: Ele trabalha todos os dias.", "he works every day"),
            ex("quiz", "Complete: 'She ___ like tea.' (não)", "doesn't", ["doesn't", "don't", "isn't"]),
            ex("audio", "Escute e transcreva:", "do they live here", audio_text="Do they live here?"),
            ex("speak", "Diga uma rotina de estudo:", "i study english every day", audio_text="I study English every day."),
        ],
    },
    "adverbios-de-frequencia": {
        "lesson": _lesson_revision(
            "Com verbos comuns, o advérbio costuma vir antes do verbo: **I usually work**. Com **to be**, vem depois: **She is always happy**. **How often...?** pergunta a frequência.",
            [
                ("She is always happy.", "Ela está sempre feliz."),
                ("I sometimes read at night.", "Às vezes eu leio à noite."),
            ],
            [
                "Não coloque o advérbio antes de **to be**: diga **He is often late**, não *He often is late* no padrão básico.",
                "**Never** já é negativo; não acrescente *don't* em **I never eat meat**.",
            ],
            "Defina a frequência, coloque o advérbio no lugar correto e use **How often...?** para perguntar sobre hábitos.",
        ),
        "exercises": [
            ex("text", "Traduza: Ele geralmente chega cedo.", "he usually arrives early"),
            ex("quiz", "Qual frase está correta com o verbo to be?", "She is always happy.", ["She is always happy.", "She always is happy.", "She always happy is."]),
            ex("audio", "Escute e transcreva:", "i sometimes read at night", audio_text="I sometimes read at night."),
            ex("quiz", "Complete: 'I ___ eat meat.' (nunca)", "never", ["never", "always", "usually"]),
        ],
    },
    "imperativo": {
        "lesson": _lesson_revision(
            "O imperativo usa o verbo na forma base e normalmente não mostra o sujeito. **Please** suaviza o pedido; **Don't** forma a negativa; **Let's** inclui quem fala em uma sugestão conjunta.",
            [
                ("Turn off the light, please.", "Apague a luz, por favor."),
                ("Let's study together.", "Vamos estudar juntos."),
            ],
            [
                "Não acrescente **to** ao imperativo: diga **Open the door**, não *To open the door*.",
                "Para proibir uma ação, use **Don't + verbo base**, não *No close the door*.",
            ],
            "Ordem ou pedido: **verbo base**; negativa: **Don't**; sugestão conjunta: **Let's**.",
        ),
        "exercises": [
            ex("text", "Traduza: Não abra a janela.", "don't open the window"),
            ex("quiz", "O que 'Let's study!' expressa?", "uma sugestão para estudarmos", ["uma sugestão para estudarmos", "uma pergunta sobre estudo", "uma ação passada"]),
            ex("audio", "Escute e transcreva:", "turn off the light please", audio_text="Turn off the light, please."),
            ex("speak", "Dê uma instrução educada:", "please listen", audio_text="Please listen."),
        ],
    },
    "can-cant": {
        "lesson": _lesson_revision(
            "**Can** é igual para todas as pessoas e vem seguido da forma base do verbo. Pode indicar habilidade ou pedido de permissão. A negativa é **can't** e a pergunta começa por **Can**.",
            [
                ("He can swim.", "Ele sabe nadar."),
                ("Can I use your phone?", "Posso usar seu celular?"),
            ],
            [
                "Não coloque **to** depois de **can**: diga **I can swim**, não *I can to swim*.",
                "Não use **does** com can: diga **Can you help me?**, não *Does you can...?*.",
            ],
            "Depois de **can/can't**, use verbo base; para habilidade ou permissão, forme a pergunta com **Can + sujeito + verbo?**.",
        ),
        "exercises": [
            ex("text", "Traduza: Ele sabe nadar.", "he can swim"),
            ex("quiz", "O que 'She can't drive' significa?", "Ela não sabe dirigir.", ["Ela não sabe dirigir.", "Ela dirige todos os dias.", "Ela quer dirigir."]),
            ex("audio", "Escute e transcreva:", "can i use your phone", audio_text="Can I use your phone?"),
            ex("speak", "Diga uma habilidade negativa:", "i can't drive", audio_text="I can't drive."),
        ],
    },
    "preposicoes-basicas": {
        "lesson": _lesson_revision(
            "Pense em imagens simples: **in** é dentro, **on** é sobre uma superfície e **at** é um ponto ou horário. Para tempo, use **at** com horas, **on** com dias e **in** com meses, anos e partes do dia.",
            [
                ("The keys are in the bag.", "As chaves estão na bolsa."),
                ("The bank is next to the school.", "O banco fica ao lado da escola."),
            ],
            [
                "Não diga *in Monday*; para dias, use **on Monday**.",
                "Não confunda **next to** (ao lado de) com **between** (entre duas coisas).",
            ],
            "Escolha a preposição pela relação: interior, superfície, ponto, lado ou posição entre; depois confira se é lugar ou tempo.",
        ),
        "exercises": [
            ex("text", "Traduza: As chaves estão na bolsa.", "the keys are in the bag"),
            ex("quiz", "Complete: 'The class is ___ Monday.'", "on", ["on", "at", "in"]),
            ex("audio", "Escute e transcreva:", "the bank is next to the school", audio_text="The bank is next to the school."),
            ex("quiz", "Complete: 'The park is ___ the school and the store.'", "between", ["between", "under", "at"]),
        ],
    },
    "question-words": {
        "lesson": _lesson_revision(
            "As question words têm uma função específica. **What** busca informação, **who** uma pessoa, **where** um lugar, **when** um momento, **why** um motivo, **how** uma maneira/estado e **which** uma escolha limitada.",
            [
                ("How many students are there?", "Quantos alunos há?"),
                ("Which color do you like?", "De qual cor você gosta?"),
            ],
            [
                "Não use **how much** para substantivo contável plural; diga **how many books**.",
                "**Which** pede escolha entre opções; para informação aberta, **what** costuma ser mais adequado.",
            ],
            "Identifique o tipo de resposta esperado antes de escolher a question word e mantenha a palavra interrogativa no início.",
        ),
        "exercises": [
            ex("text", "Traduza: Quando é a festa?", "when is the party"),
            ex("quiz", "Qual pergunta conta itens?", "How many brothers do you have?", ["How many brothers do you have?", "How old are you?", "How are you?"]),
            ex("audio", "Escute e transcreva:", "which color do you like", audio_text="Which color do you like?"),
            ex("speak", "Pergunte por que alguém está atrasado:", "why are you late", audio_text="Why are you late?"),
        ],
    },
    "estrutura-basica-da-frase": {
        "lesson": _lesson_revision(
            "A ordem básica evita traduções palavra por palavra. Na afirmação, coloque sujeito antes do verbo; na pergunta, coloque o auxiliar ou **to be** antes do sujeito; na negativa, coloque o negador na posição correta.",
            [
                ("She likes coffee.", "Ela gosta de café."),
                ("Are you at home?", "Você está em casa?"),
            ],
            [
                "Não copie a ordem de pergunta do português: **Do you speak English?**, não *You speak English?* no modelo estudado.",
                "Com **does**, o verbo principal fica sem **-s**: **Does she work?**.",
            ],
            "Monte primeiro o sujeito, depois o verbo e o complemento; para perguntar, mova o auxiliar ou **to be** para a frente.",
        ),
        "exercises": [
            ex("text", "Ordene: 'She / likes / coffee'.", "she likes coffee"),
            ex("quiz", "Qual é a negativa correta de 'They speak Spanish'?", "They don't speak Spanish.", ["They don't speak Spanish.", "They not speak Spanish.", "They doesn't speak Spanish."]),
            ex("audio", "Escute e transcreva:", "are you at home", audio_text="Are you at home?"),
            ex("speak", "Diga a frase afirmativa em voz alta:", "we live in brazil", audio_text="We live in Brazil."),
        ],
    },
})


# ============================================================
# MODULO 8 - Gramatica Essencial - B1
# ============================================================

def build_modulo_08_gramatica_essencial_b1():
    return module(
        "modulo-08-gramatica-essencial-b1",
        "Módulo 8 — Gramática Essencial — B1",
        "O salto para o intermediário: presente perfeito, contrastes com o passado, passado contínuo e perfeito, formas de futuro, condicionais zero/primeiro/segundo, modais should/may/might, relativas, gerúndio, infinitivo, voz passiva, discurso indireto, question tags e phrasal verbs.",
        [
            topic(
                "presente-perfeito",
                "Presente Perfeito",
                """
# Presente Perfeito

O **presente perfeito** conecta o passado com o **agora**: experiências,
resultados no presente e ações que continuam. Forma: **have/has + particípio
passado**.

## Afirmativo

```
I have been to Paris.          Eu já estive em Paris.
She has finished her homework. Ela terminou o dever de casa.
```

## Negativo

```
I haven't seen that movie.     Eu não vi aquele filme.
```

## Interrogativo

```
Have you ever eaten sushi?     Você já comeu sushi?
```

## Marcadores típicos

```
ever / never   já / nunca
already / yet  já / ainda (não)
just           acabou de
```

## Particípios comuns (não confunda com o passado simples)

```
go - went - gone      see - saw - seen
eat - ate - eaten     do - did - done
```

> 💡 Regra: **presente perfeito** NÃO usa tempo definido (yesterday, last
> year). Quando aparece tempo definido, é passado simples (próximo tópico).
""",
                [
                    ex("quiz", 'Complete: "I have ___ to Paris." (been)',
                       "been", ["been", "be", "was"]),
                    ex("quiz", 'Complete: "She has ___ her homework." (finished)',
                       "finished", ["finished", "finish", "finishes"]),
                    ex("text", "Traduza: Você já comeu sushi?",
                       "have you ever eaten sushi"),
                    ex("quiz", "Qual é o particípio passado de 'go'?",
                       "gone", ["gone", "went", "goed"]),
                    ex("audio", "Escute e transcreva:",
                       "i have never seen that movie", audio_text="I have never seen that movie."),
                    ex("quiz", "O que 'I have already eaten' significa?",
                       "Eu já comi", ["Eu já comi", "Eu ainda não comi", "Eu vou comer"]),
                ],
            ),
            topic(
                "presente-perfeito-vs-passado",
                "Presente Perfeito vs. Passado Simples",
                """
# Presente Perfeito vs. Passado Simples

A diferença mais importante do B1:

## Passado simples = tempo definido, ação terminada

```
I visited Paris in 2020.     (quando? em 2020)
She worked there last year.  (quando? ano passado)
```

## Presente perfeito = conexão com agora, sem tempo definido

```
I have lost my keys.         (resultado: não consigo entrar agora)
She has been to Brazil.      (experiência na vida dela)
```

## Como decidir

| Situação | Tempo |
|---|---|
| Tem "yesterday / last year / in 2020" | passado simples |
| Tem "ever / never / already / just / yet" | presente perfeito |
| Resultado visível no presente | presente perfeito |

> 💡 Pergunte: "tem um tempo definido?" Se sim, passado simples. Se não, e há
> conexão com o agora, presente perfeito.
""",
                [
                    ex("quiz", "Qual tempo usamos com 'yesterday'?",
                       "passado simples", ["passado simples", "presente perfeito", "presente contínuo"]),
                    ex("quiz", 'Complete: "I ___ my keys. I can\'t find them." (perdi — resultado agora)',
                       "have lost", ["have lost", "lost", "lose"]),
                    ex("text", "Complete com o tempo certo: 'She ___ (visit) Paris in 2020.'",
                       "visited"),
                    ex("quiz", "Para experiências sem tempo definido ('ever/never'), usamos:",
                       "presente perfeito", ["presente perfeito", "passado simples", "going to"]),
                    ex("audio", "Escute e transcreva:",
                       "i have never been to japan", audio_text="I have never been to Japan."),
                    ex("quiz", 'Complete: "He ___ (work) there last year."',
                       "worked", ["worked", "has worked", "works"]),
                ],
            ),
            topic(
                "passado-continuo",
                "Passado Contínuo",
                """
# Passado Contínuo

O **passado contínuo** descreve uma ação que estava **em andamento** em um
ponto do passado. Forma: **was/were + verbo-ing**.

## Afirmativo

```
I was watching TV when you called.   Eu estava assistindo TV quando você ligou.
They were sleeping at 10 pm.         Eles estavam dormindo às 22h.
```

## Negativo

```
She wasn't working that day.         Ela não estava trabalhando naquele dia.
```

## Interrogativo

```
Were you listening to me?            Você estava me ouvindo?
```

## Ação interrompida

```
I was reading when he arrived.       Eu estava lendo quando ele chegou.
```

> 💡 Padrão clássico: **passado contínuo** (ação em andamento) + **when** +
> **passado simples** (ação que interrompeu).
""",
                [
                    ex("quiz", 'Complete: "I was ___ TV when you called." (watch)',
                       "watching", ["watching", "watched", "watch"]),
                    ex("quiz", 'Complete: "They ___ sleeping at 10 pm."',
                       "were", ["were", "was", "are"]),
                    ex("text", "Traduza: Eu estava lendo quando ele chegou.",
                       "i was reading when he arrived"),
                    ex("quiz", "O passado contínuo usa:",
                       "was/were + verbo-ing", ["was/were + verbo-ing", "verbo + -s", "will + verbo"]),
                    ex("audio", "Escute e transcreva:",
                       "she was cooking when i called", audio_text="She was cooking when I called."),
                    ex("quiz", "Qual combinação descreve uma ação interrompida?",
                       "passado contínuo + passado simples", ["passado contínuo + passado simples", "presente simples + passado contínuo", "passado contínuo + futuro"]),
                ],
            ),
            topic(
                "passado-perfeito",
                "Passado Perfeito",
                """
# Passado Perfeito

O **passado perfeito** descreve uma ação que aconteceu **antes** de outra no
passado. Forma: **had + particípio passado**.

## Afirmativo

```
When I arrived, she had left.        Quando cheguei, ela já tinha saído.
They had already eaten when I arrived.  Eles já tinham comido quando cheguei.
```

## Negativo

```
He hadn't sent the email.            Ele não tinha enviado o e-mail.
```

## Interrogativo

```
Had you seen that movie before?      Você já tinha visto aquele filme?
```

## A ordem dos acontecimentos

```
[had left]  ...  [arrived]  ...  agora
  (antes)         (depois)
```

> 💡 O passado perfeito é o "passado do passado": o verbo mais antigo vai
> para **had + particípio**, e o mais recente fica no passado simples.
""",
                [
                    ex("quiz", 'Complete: "When I arrived, she had ___." (left)',
                       "left", ["left", "leave", "leaved"]),
                    ex("quiz", 'Complete: "He said he had ___ the email." (sent)',
                       "sent", ["sent", "send", "sending"]),
                    ex("text", "Traduza: Quando chegamos, o filme já tinha começado.",
                       "when we arrived the movie had already started"),
                    ex("quiz", "O passado perfeito usa:",
                       "had + particípio", ["had + particípio", "has + particípio", "did + verbo"]),
                    ex("audio", "Escute e transcreva:",
                       "they had already eaten when i arrived", audio_text="They had already eaten when I arrived."),
                    ex("quiz", "O passado perfeito expressa:",
                       "uma ação anterior a outra no passado", ["uma ação anterior a outra no passado", "uma ação futura", "uma ação em andamento"]),
                ],
            ),
            topic(
                "formas-de-futuro",
                "Formas de futuro",
                """
# Formas de futuro

No B1, o "futuro" tem quatro formas, cada uma com um uso.

## will — previsões e decisões na hora

```
It will rain tomorrow.          Vai chover amanhã.
```

## going to — planos decididos

```
I'm going to travel next month.  Vou viajar mês que vem.
```

## presente contínuo — compromissos marcados

```
I'm meeting her tomorrow.       Vou encontrar ela amanhã (marcado).
```

## presente simples — horários fixos

```
The train leaves at 7.          O trem parte às 7 (horário fixo).
```

> 💡 Resumo: horário fixo = presente simples; compromisso marcado = presente
> contínuo; plano = going to; previsão/decisão = will.
""",
                [
                    ex("quiz", "Para um HORÁRIO fixo (ex.: o trem às 7), usamos:",
                       "presente simples", ["presente simples", "will", "going to"]),
                    ex("quiz", "Para um COMPROMISSO já marcado, usamos:",
                       "presente contínuo", ["presente contínuo", "passado simples", "presente perfeito"]),
                    ex("text", "Traduza: O trem parte às 7.",
                       "the train leaves at 7"),
                    ex("quiz", "Para planos já decididos, usamos:",
                       "going to", ["going to", "past simple", "present perfect"]),
                    ex("audio", "Escute e transcreva:",
                       "i am meeting her tomorrow", audio_text="I am meeting her tomorrow."),
                    ex("quiz", "Para uma previsão ('It ___ rain'), a forma comum é:",
                       "will", ["will", "went", "was"]),
                ],
            ),
            topic(
                "condicional-zero-e-primeiro",
                "Condicional Zero e Primeiro",
                """
# Condicional Zero e Primeiro

## Condicional Zero — fatos gerais

**If + presente simples, presente simples.**

```
If you heat water, it boils.        Se você aquece água, ela ferve.
```

Sempre verdade, sem condição especial.

## Primeiro Condicional — futuro real

**If + presente simples, will + verbo.**

```
If it rains, we will stay home.     Se chover, vamos ficar em casa.
If she comes, we will be happy.     Se ela vier, ficaremos felizes.
```

> 💡 A regra de ouro: depois de **if**, o verbo NUNCA vai com will — é
> presente simples. "If it will rain" está errado!
""",
                [
                    ex("quiz", 'Complete o condicional ZERO: "If you ___ water, it boils." (heat)',
                       "heat", ["heat", "heated", "will heat"]),
                    ex("quiz", "O condicional zero expressa:",
                       "fatos gerais", ["fatos gerais", "situações improváveis", "passado"]),
                    ex("text", "Complete o primeiro condicional: 'If it rains, we ___ (stay) home.'",
                       "will stay"),
                    ex("quiz", "O primeiro condicional usa:",
                       "if + presente, will + verbo", ["if + presente, will + verbo", "if + passado, would + verbo", "if + presente, presente"]),
                    ex("audio", "Escute e transcreva:",
                       "if you study you will pass", audio_text="If you study, you will pass."),
                    ex("quiz", 'Complete: "If she ___ (come), we will be happy."',
                       "comes", ["comes", "come", "will come"]),
                ],
            ),
            topic(
                "condicional-segundo",
                "Condicional Segundo",
                """
# Condicional Segundo

O **segundo condicional** descreve situações **hipotéticas ou improváveis**
(imaginárias). Forma: **If + passado simples, would + verbo**.

## Afirmativo

```
If I had a lot of money, I would travel.   Se eu tivesse muito dinheiro, eu viajaria.
If I were you, I would study more.         Se eu fosse você, eu estudaria mais.
```

> ⚠️ Com o segundo condicional, use **were** para todas as pessoas: "If I
> were you", "If she were here" (mesmo com I/she).

## Negativo

```
If I didn't have to work, I would go.   Se eu não tivesse que trabalhar, eu iria.
```

## Interrogativo

```
What would you do if you won the lottery?   O que você faria se ganhasse na loteria?
```

> 💡 Regra de ouro: depois de **if**, passado simples; depois de **would**,
> verbo na forma base. "If I would have" está errado!
""",
                [
                    ex("quiz", "O segundo condicional expressa:",
                       "situações hipotéticas/improváveis", ["situações hipotéticas/improváveis", "fatos gerais", "passado real"]),
                    ex("quiz", 'Complete: "If I ___ a lot of money, I would travel." (had)',
                       "had", ["had", "have", "will have"]),
                    ex("text", "Complete: 'If I were you, I ___ (study) more.'",
                       "would study"),
                    ex("quiz", "No segundo condicional, depois de 'would' o verbo fica:",
                       "na forma base", ["na forma base", "no passado", "com -s"]),
                    ex("audio", "Escute e transcreva:",
                       "if i had time i would help you", audio_text="If I had time, I would help you."),
                    ex("quiz", 'Complete: "She would call you if she ___ your number." (know)',
                       "knew", ["knew", "knows", "will know"]),
                ],
            ),
            topic(
                "should-may-might",
                "Should / May / Might",
                """
# Should / May / Might

Três modais com usos diferentes:

## should — conselho (você deveria)

```
You should see a doctor.      Você deveria ir ao médico.
```

## may — permissão / possibilidade

```
He may be at home.            Ele pode estar em casa.
May I come in?                Posso entrar?
```

## might — possibilidade (mais incerta que may)

```
It might rain.                Pode ser que chova.
```

## A diferença de incerteza

```
It will rain.   (vai chover — certeza)
It may rain.    (pode chover)
It might rain.  (talvez chova — mais incerto)
```

> 💡 Depois de **should / may / might**, o verbo sempre na forma base: "You
> should study", nunca "should studies".
""",
                [
                    ex("quiz", "Qual modal expressa CONSELHO?",
                       "should", ["should", "may", "might"]),
                    ex("quiz", "Qual modal expressa POSSIBILIDADE?",
                       "may", ["may", "should", "must"]),
                    ex("text", "Traduza: Ele pode estar em casa.",
                       "he may be at home"),
                    ex("quiz", "O que 'It might rain' significa?",
                       "Pode ser que chova", ["Pode ser que chova", "Vai chover com certeza", "Já choveu"]),
                    ex("audio", "Escute e transcreva:",
                       "you should see a doctor", audio_text="You should see a doctor."),
                    ex("quiz", "Depois de should/may/might, o verbo:",
                       "fica na forma base", ["fica na forma base", "ganha -s", "fica no passado"]),
                ],
            ),
            topic(
                "oracoes-relativas",
                "Orações relativas",
                """
# Orações relativas (who / which / that / where)

As **orações relativas** juntam duas ideias sobre a mesma pessoa/coisa.

| Pronome | Uso | Exemplo |
|---|---|---|
| **who** | pessoas | The man who lives next door is my uncle. |
| **which** | coisas | The movie which we watched was great. |
| **that** | pessoas ou coisas | This is the book that I bought. |
| **where** | lugares | This is the city where I was born. |

## Exemplos

```
The woman who works with me is Brazilian.   A mulher que trabalha comigo é brasileira.
The car that I bought is blue.              O carro que comprei é azul.
```

> 💡 **who** = pessoas, **which** = coisas, **that** = os dois, **where** =
> lugares. Em conversa, **that** é o mais comum.
""",
                [
                    ex("quiz", "Para PESSOAS, usamos:",
                       "who", ["who", "which", "where"]),
                    ex("quiz", "Para COISAS, usamos:",
                       "which", ["which", "who", "where"]),
                    ex("text", "Complete: 'The man ___ lives next door is my uncle.' (pessoa)",
                       "who"),
                    ex("quiz", "Para LUGARES, usamos:",
                       "where", ["where", "who", "which"]),
                    ex("audio", "Escute e transcreva:",
                       "this is the book that i bought", audio_text="This is the book that I bought."),
                    ex("quiz", 'Complete: "The movie ___ we watched was great." (coisa)',
                       "which", ["which", "who", "where"]),
                ],
            ),
            topic(
                "gerundio",
                "Gerúndio (-ing)",
                """
# Gerúndio (-ing)

O **gerúndio** (verbo + -ing) funciona como substantivo e aparece depois de
certos verbos e preposições.

## Depois de verbos de gosto/opinião

```
I enjoy listening to music.    Eu gosto de ouvir música.
He finished writing the report.  Ele terminou de escrever o relatório.
I like swimming.               Eu gosto de nadar.
```

## Como sujeito da frase

```
Swimming is good for you.      Nadar faz bem para você.
```

## Depois de preposições

```
I'm good at cooking.           Eu sou bom em cozinhar.
```

> 💡 Verbos comuns que pedem gerúndio: **enjoy, finish, avoid, mind, keep,
> suggest**. "I enjoy swim" está errado — é "I enjoy swimming".
""",
                [
                    ex("quiz", "Depois de 'enjoy', usamos:",
                       "gerúndio", ["gerúndio", "infinitivo", "passado"]),
                    ex("quiz", 'Complete: "I enjoy ___ to music." (listen)',
                       "listening", ["listening", "listen", "listened"]),
                    ex("text", "Traduza: Eu gosto de nadar.",
                       "i like swimming"),
                    ex("quiz", 'Complete: "He finished ___ the report." (write)',
                       "writing", ["writing", "write", "wrote"]),
                    ex("audio", "Escute e transcreva:",
                       "i enjoy cooking on weekends", audio_text="I enjoy cooking on weekends."),
                    ex("quiz", 'Complete com o gerúndio como sujeito: "___ (swim) is good for you."',
                       "Swimming", ["Swimming", "Swim", "To swim"]),
                ],
            ),
            topic(
                "infinitivo",
                "Infinitivo (to + verbo)",
                """
# Infinitivo (to + verbo)

O **infinitivo** (to + verbo) aparece depois de verbos como want, need,
decide, hope, plan — e para expressar **finalidade** (para quê).

## Depois de certos verbos

```
I want to buy a new phone.      Eu quero comprar um celular novo.
I need to learn English.        Eu preciso aprender inglês.
She decided to accept the job.  Ela decidiu aceitar o emprego.
I hope to see you soon.         Eu espero te ver em breve.
```

## Para expressar finalidade (para...)

```
I study to improve my English.   Eu estudo para melhorar meu inglês.
```

> 💡 Verbos comuns que pedem infinitivo: **want, need, decide, hope, plan,
> learn, agree**. "I want buy" está errado — é "I want to buy".
""",
                [
                    ex("quiz", 'Complete: "I want ___ a new phone." (buy)',
                       "to buy", ["to buy", "buying", "buy"]),
                    ex("quiz", "Para expressar FINALIDADE ('para...'), usamos:",
                       "to + verbo", ["to + verbo", "gerúndio", "passado"]),
                    ex("text", "Traduza: Eu preciso aprender inglês.",
                       "i need to learn english"),
                    ex("quiz", 'Complete: "She decided ___ the job." (aceitar)',
                       "to accept", ["to accept", "accepting", "accept"]),
                    ex("audio", "Escute e transcreva:",
                       "i hope to see you soon", audio_text="I hope to see you soon."),
                    ex("quiz", "Depois de 'want/need/decide/hope', usamos:",
                       "to + verbo", ["to + verbo", "verbo + -ing", "verbo base"]),
                ],
            ),
            topic(
                "voz-passiva",
                "Voz passiva (presente e passado simples)",
                """
# Voz passiva (presente e passado simples)

Na **voz passiva**, o foco está no objeto da ação, não em quem a faz.
Forma: **be + particípio passado**.

## Presente (am/is/are + particípio)

```
The cake is made by my mother.     O bolo é feito pela minha mãe.
English is spoken in many countries.  O inglês é falado em muitos países.
```

## Passado (was/were + particípio)

```
This house was built in 1990.      Esta casa foi construída em 1990.
The window was broken last night.  A janela foi quebrada ontem à noite.
```

## Quem faz a ação? use BY

```
The book was written by a Brazilian.   O livro foi escrito por um brasileiro.
```

> 💡 Na passiva, o particípio é o mesmo do presente perfeito: **made, built,
> written, broken**.
""",
                [
                    ex("quiz", 'Complete a voz passiva no PRESENTE: "The cake ___ made by my mother."',
                       "is", ["is", "are", "was"]),
                    ex("quiz", 'Complete a passiva no PASSADO: "This house ___ built in 1990."',
                       "was", ["was", "is", "were"]),
                    ex("text", "Traduza: O livro foi escrito por um brasileiro.",
                       "the book was written by a brazilian"),
                    ex("quiz", "A voz passiva no presente usa:",
                       "am/is/are + particípio", ["am/is/are + particípio", "did + verbo", "has + particípio"]),
                    ex("audio", "Escute e transcreva:",
                       "the window was broken last night", audio_text="The window was broken last night."),
                    ex("quiz", "Para dizer QUEM faz a ação na passiva, usamos:",
                       "by", ["by", "with", "for"]),
                ],
            ),
            topic(
                "discurso-indireto",
                "Discurso indireto (afirmações)",
                """
# Discurso indireto (afirmações)

O **discurso indireto** relata o que alguém disse, sem aspas. Use **said
(that)** e "desloque" os tempos para trás (backshift).

## O backshift

| Direto | Indireto |
|---|---|
| "I am tired" | He said (that) he was tired. |
| "I like coffee" | She said (that) she liked coffee. |
| "I will come" | He said (that) he would come. |
| "I can swim" | She said (that) she could swim. |

## Exemplos

```
He said, "I am busy."    ->    He said he was busy.
She said, "I will help." ->    She said she would help.
```

> 💡 Regra do backshift: presente vira passado, **will** vira **would**,
> **can** vira **could**. O **that** é opcional.
""",
                [
                    ex("quiz", "Como relatar 'He said: I am tired'?",
                       "He said he was tired.", ["He said he was tired.", "He said he is tired.", "He said I am tired."]),
                    ex("quiz", "No discurso indireto, 'will' vira:",
                       "would", ["would", "will", "was"]),
                    ex("text", "Relate: 'She said, \"I like coffee\"' -> She said that she ___ coffee.",
                       "liked"),
                    ex("quiz", "No discurso indireto, o presente vira:",
                       "passado", ["passado", "futuro", "presente"]),
                    ex("audio", "Escute e transcreva:",
                       "he said he was busy", audio_text="He said he was busy."),
                    ex("quiz", "O que 'She said that she would come' significa?",
                       "Ela disse que viria", ["Ela disse que viria", "Ela disse que vem", "Ela disse que veio"]),
                ],
            ),
            topic(
                "question-tags",
                "Question tags",
                """
# Question tags

**Question tags** são as "perguntinhas" no fim da frase para confirmar ou
pedir concordância.

## A regra

- Frase **afirmativa** -> tag **negativa**.
- Frase **negativa** -> tag **afirmativa**.
- A tag repete o verbo/auxiliar e o sujeito.

## Exemplos

```
It's cold, isn't it?            Está frio, não está?
You like coffee, don't you?     Você gosta de café, não gosta?
She isn't here, is she?         Ela não está aqui, está?
They were happy, weren't they?  Eles estavam felizes, não estavam?
You are coming, aren't you?     Você vai vir, não vai?
```

> 💡 A tag usa o **auxiliar** da frase: do/does/did para verbos comuns,
> am/is/are/was/were para o verbo to be.
""",
                [
                    ex("quiz", 'Complete: "It\'s cold, ___ it?"',
                       "isn't", ["isn't", "is", "was"]),
                    ex("quiz", 'Complete: "You like coffee, ___ you?"',
                       "don't", ["don't", "do", "doesn't"]),
                    ex("text", "Complete: 'She isn't here, ___ she?'",
                       "is"),
                    ex("quiz", 'Complete: "They were happy, ___ they?"',
                       "weren't", ["weren't", "were", "are"]),
                    ex("audio", "Escute e transcreva:",
                       "you are coming aren't you", audio_text="You are coming, aren't you?"),
                    ex("quiz", "Depois de uma frase AFIRMATIVA, a tag geralmente é:",
                       "negativa", ["negativa", "afirmativa", "interrogativa"]),
                ],
            ),
            topic(
                "phrasal-verbs",
                "Phrasal verbs comuns",
                """
# Phrasal verbs comuns

**Phrasal verbs** são verbo + partícula (in/on/up...). O significado quase
sempre muda do verbo sozinho.

| Phrasal verb | Significado |
|---|---|
| get up | levantar-se |
| turn on / turn off | ligar / desligar |
| put on | vestir |
| take off | tirar (roupa) / decolar |
| look for | procurar |
| look after | cuidar de |
| give up | desistir |
| find out | descobrir |

## Exemplos

```
I get up at 7.                Eu me levanto às 7.
Please turn off the lights.   Por favor, apague as luzes.
I'm looking for my keys.      Estou procurando minhas chaves.
```

> 💡 **look for** = procurar (a coisa procurada vem depois); **look after** =
> cuidar. São dos mais usados — memorize aos poucos, no contexto.
""",
                [
                    ex("quiz", "O que 'get up' significa?",
                       "levantar-se", ["levantar-se", "sentar", "correr"]),
                    ex("quiz", "O que 'turn on' significa?",
                       "ligar", ["ligar", "desligar", "comprar"]),
                    ex("text", "Traduza: Eu estou procurando minhas chaves.",
                       "i am looking for my keys"),
                    ex("quiz", "O que 'give up' significa?",
                       "desistir", ["desistir", "continuar", "começar"]),
                    ex("audio", "Escute e transcreva:",
                       "please turn off the lights", audio_text="Please turn off the lights."),
                    ex("quiz", "O que 'take off' (roupa) significa?",
                       "tirar", ["tirar", "vestir", "comprar"]),
                ],
            ),
        ],
    )


# ============================================================
# MODULO 9 - Vocabulario - B1
# ============================================================

def build_modulo_09_vocabulario_b1():
    return module(
        "modulo-09-vocabulario-b1",
        "Módulo 9 — Vocabulário — B1",
        "Vocabulário para temas do mundo real: trabalho, carreira, mundo digital, ciência, política, sociedade, meio ambiente, educação, cultura, mídia, negócios, emoções, personalidade, relações e conceitos abstratos.",
        [
            topic(
                "trabalho-b1",
                "Trabalho (B1)",
                """
# Trabalho (B1)

Vocabulário de trabalho para o dia a dia profissional.

| Inglês | Português |
|---|---|
| deadline | prazo (de entrega) |
| meeting | reunião |
| salary | salário |
| raise | aumento (de salário) |
| boss | chefe |
| experience | experiência |
| skill | habilidade |
| teamwork | trabalho em equipe |
| promotion | promoção |

## Exemplos

```
I have a meeting at 10.         Eu tenho uma reunião às 10.
We have a deadline tomorrow.    Temos um prazo amanhã.
```

> 💡 **deadline** = prazo final para entregar algo. **raise** = aumento;
> **promotion** = promoção de cargo.
""",
                [
                    ex("quiz", "Como se diz 'prazo' (de entrega) em inglês?",
                       "deadline", ["deadline", "salary", "raise"]),
                    ex("quiz", "Como se diz 'salário' em inglês?",
                       "salary", ["salary", "raise", "skill"]),
                    ex("text", "Traduza: Eu tenho uma reunião às 10.",
                       "i have a meeting at 10"),
                    ex("quiz", "Como se diz 'promoção' (no trabalho) em inglês?",
                       "promotion", ["promotion", "deadline", "teamwork"]),
                    ex("audio", "Escute e transcreva:",
                       "we have a deadline tomorrow", audio_text="We have a deadline tomorrow."),
                    ex("quiz", "Como se diz 'aumento' (de salário) em inglês?",
                       "raise", ["raise", "salary", "boss"]),
                ],
            ),
            topic(
                "carreira",
                "Carreira",
                """
# Carreira

| Inglês | Português |
|---|---|
| career | carreira |
| goal | objetivo / meta |
| to achieve | alcançar / atingir |
| success | sucesso |
| opportunity | oportunidade |
| to apply for | candidatar-se a |
| to hire | contratar |
| to resign | pedir demissão |
| experience | experiência |

## Exemplos

```
I want to achieve my goals.      Eu quero alcançar meus objetivos.
She has a lot of experience.     Ela tem muita experiência.
```

> 💡 **apply for a job** = candidatar-se a um emprego. **hire** = contratar
> (o empregador); **resign** = pedir demissão (o empregado).
""",
                [
                    ex("quiz", "Como se diz 'carreira' em inglês?",
                       "career", ["career", "goal", "success"]),
                    ex("quiz", "Como se diz 'oportunidade' em inglês?",
                       "opportunity", ["opportunity", "success", "experience"]),
                    ex("text", "Traduza: Eu quero alcançar meus objetivos.",
                       "i want to achieve my goals"),
                    ex("quiz", "Como se diz 'candidatar-se' (a um emprego) em inglês?",
                       "apply for", ["apply for", "hire", "resign"]),
                    ex("audio", "Escute e transcreva:",
                       "she has a lot of experience", audio_text="She has a lot of experience."),
                    ex("quiz", "Como se diz 'sucesso' em inglês?",
                       "success", ["success", "career", "skill"]),
                ],
            ),
            topic(
                "mundo-digital",
                "Mundo digital",
                """
# Mundo digital

| Inglês | Português |
|---|---|
| password | senha |
| username | nome de usuário |
| account | conta |
| to download | baixar |
| to upload | enviar (para a internet) |
| to update | atualizar |
| device | dispositivo |
| data | dados |
| social media | redes sociais |
| connection | conexão |

## Exemplos

```
I forgot my password.          Esqueci minha senha.
I need to update the app.      Eu preciso atualizar o aplicativo.
```

> 💡 **download** = baixar (trazer); **upload** = enviar (subir). **data**
> é incontável: "The data is important" (não "are").
""",
                [
                    ex("quiz", "Como se diz 'senha' em inglês?",
                       "password", ["password", "username", "account"]),
                    ex("quiz", "Como se diz 'baixar' (arquivo) em inglês?",
                       "download", ["download", "upload", "update"]),
                    ex("text", "Traduza: Eu preciso atualizar o aplicativo.",
                       "i need to update the app"),
                    ex("quiz", "Como se diz 'dados' (informação) em inglês?",
                       "data", ["data", "password", "device"]),
                    ex("audio", "Escute e transcreva:",
                       "i forgot my password", audio_text="I forgot my password."),
                    ex("quiz", "Como se diz 'redes sociais' em inglês?",
                       "social media", ["social media", "data", "password"]),
                ],
            ),
            topic(
                "ciencia",
                "Ciência",
                """
# Ciência

| Inglês | Português |
|---|---|
| research | pesquisa (científica) |
| experiment | experimento |
| discovery | descoberta |
| scientist | cientista |
| theory | teoria |
| evidence | evidência |
| laboratory | laboratório |
| science | ciência |

## Exemplos

```
The experiment was successful.      O experimento foi bem-sucedido.
Science explains the world.         A ciência explica o mundo.
```

> 💡 **research** é incontável: "We do research" (não "a research").
""",
                [
                    ex("quiz", "Como se diz 'pesquisa' (científica) em inglês?",
                       "research", ["research", "experiment", "theory"]),
                    ex("quiz", "Como se diz 'cientista' em inglês?",
                       "scientist", ["scientist", "laboratory", "discovery"]),
                    ex("text", "Traduza: A ciência explica o mundo.",
                       "science explains the world"),
                    ex("quiz", "Como se diz 'descoberta' em inglês?",
                       "discovery", ["discovery", "research", "evidence"]),
                    ex("audio", "Escute e transcreva:",
                       "the experiment was successful", audio_text="The experiment was successful."),
                    ex("quiz", "Como se diz 'teoria' em inglês?",
                       "theory", ["theory", "experiment", "laboratory"]),
                ],
            ),
            topic(
                "politica",
                "Política",
                """
# Política

| Inglês | Português |
|---|---|
| government | governo |
| election | eleição |
| to vote | votar |
| law | lei |
| president | presidente |
| citizen | cidadão |
| candidate | candidato |
| rights | direitos |
| debate | debate |

## Exemplos

```
The election will be in November.   A eleição será em novembro.
Every citizen has rights.           Todo cidadão tem direitos.
```

> 💡 **election** (eleição), **vote** (voto/votar), **law** (lei) — as três
> palavras-chave para entender notícias de política.
""",
                [
                    ex("quiz", "Como se diz 'governo' em inglês?",
                       "government", ["government", "election", "law"]),
                    ex("quiz", "Como se diz 'votar' em inglês?",
                       "vote", ["vote", "debate", "citizen"]),
                    ex("text", "Traduza: As eleições serão em novembro.",
                       "the election will be in november"),
                    ex("quiz", "Como se diz 'cidadão' em inglês?",
                       "citizen", ["citizen", "candidate", "policy"]),
                    ex("audio", "Escute e transcreva:",
                       "every citizen has rights", audio_text="Every citizen has rights."),
                    ex("quiz", "Como se diz 'lei' em inglês?",
                       "law", ["law", "vote", "debate"]),
                ],
            ),
            topic(
                "sociedade",
                "Sociedade",
                """
# Sociedade

| Inglês | Português |
|---|---|
| society | sociedade |
| community | comunidade |
| population | população |
| equality | igualdade |
| freedom | liberdade |
| poverty | pobreza |
| responsibility | responsabilidade |
| values | valores |

## Exemplos

```
Society is changing.         A sociedade está mudando.
Education changes lives.     A educação muda vidas.
```

> 💡 **community** = comunidade (pessoas próximas); **society** = sociedade
> (como um todo). **responsibility** = responsabilidade.
""",
                [
                    ex("quiz", "Como se diz 'comunidade' em inglês?",
                       "community", ["community", "population", "freedom"]),
                    ex("quiz", "Como se diz 'igualdade' em inglês?",
                       "equality", ["equality", "poverty", "freedom"]),
                    ex("text", "Traduza: A sociedade está mudando.",
                       "society is changing"),
                    ex("quiz", "Como se diz 'liberdade' em inglês?",
                       "freedom", ["freedom", "responsibility", "values"]),
                    ex("audio", "Escute e transcreva:",
                       "education changes lives", audio_text="Education changes lives."),
                    ex("quiz", "Como se diz 'responsabilidade' em inglês?",
                       "responsibility", ["responsibility", "equality", "poverty"]),
                ],
            ),
            topic(
                "meio-ambiente",
                "Meio ambiente",
                """
# Meio ambiente

| Inglês | Português |
|---|---|
| environment | meio ambiente |
| pollution | poluição |
| climate change | mudança climática |
| to recycle | reciclar |
| waste | lixo / desperdício |
| energy | energia |
| renewable | renovável |
| to protect | proteger |
| damage | dano |

## Exemplos

```
We need to protect the planet.    Precisamos proteger o planeta.
We should recycle more.           Devemos reciclar mais.
```

> 💡 **climate change** = mudança climática; **renewable energy** = energia
> renovável. **waste** pode ser "lixo" ou "desperdício".
""",
                [
                    ex("quiz", "Como se diz 'meio ambiente' em inglês?",
                       "environment", ["environment", "waste", "energy"]),
                    ex("quiz", "Como se diz 'mudança climática' em inglês?",
                       "climate change", ["climate change", "renewable", "pollution"]),
                    ex("text", "Traduza: Nós precisamos proteger o planeta.",
                       "we need to protect the planet"),
                    ex("quiz", "Como se diz 'reciclar' em inglês?",
                       "recycle", ["recycle", "pollute", "waste"]),
                    ex("audio", "Escute e transcreva:",
                       "we should recycle more", audio_text="We should recycle more."),
                    ex("quiz", "Como se diz 'lixo/desperdício' em inglês?",
                       "waste", ["waste", "energy", "damage"]),
                ],
            ),
            topic(
                "educacao-e-aprendizado",
                "Educação e aprendizado",
                """
# Educação e aprendizado

| Inglês | Português |
|---|---|
| knowledge | conhecimento |
| skill | habilidade |
| course | curso |
| training | treinamento |
| certificate | certificado |
| to improve | melhorar |
| practice | prática |
| mistake | erro / engano |
| to understand | entender |

## Exemplos

```
I want to improve my English.     Eu quero melhorar meu inglês.
Practice is very important.       A prática é muito importante.
```

> 💡 **mistake** = erro (fazer um erro: "make a mistake"). **training** =
> treinamento; **course** = curso.
""",
                [
                    ex("quiz", "Como se diz 'conhecimento' em inglês?",
                       "knowledge", ["knowledge", "skill", "training"]),
                    ex("quiz", "Como se diz 'treinamento' em inglês?",
                       "training", ["training", "certificate", "mistake"]),
                    ex("text", "Traduza: Eu quero melhorar meu inglês.",
                       "i want to improve my english"),
                    ex("quiz", "Como se diz 'erro' em inglês?",
                       "mistake", ["mistake", "knowledge", "practice"]),
                    ex("audio", "Escute e transcreva:",
                       "practice is very important", audio_text="Practice is very important."),
                    ex("quiz", "Como se diz 'habilidade' em inglês?",
                       "skill", ["skill", "course", "certificate"]),
                ],
            ),
            topic(
                "cultura",
                "Cultura",
                """
# Cultura

| Inglês | Português |
|---|---|
| culture | cultura |
| tradition | tradição |
| festival | festival |
| art | arte |
| literature | literatura |
| heritage | patrimônio |
| language | idioma |
| artist | artista |

## Exemplos

```
I like modern art.            Eu gosto de arte moderna.
Every country has its own culture.   Cada país tem sua própria cultura.
```

> 💡 **heritage** = patrimônio cultural. **tradition** = tradição.
""",
                [
                    ex("quiz", "Como se diz 'tradição' em inglês?",
                       "tradition", ["tradition", "festival", "heritage"]),
                    ex("quiz", "Como se diz 'literatura' em inglês?",
                       "literature", ["literature", "art", "language"]),
                    ex("text", "Traduza: Eu gosto de arte moderna.",
                       "i like modern art"),
                    ex("quiz", "Como se diz 'festival' em inglês?",
                       "festival", ["festival", "tradition", "museum"]),
                    ex("audio", "Escute e transcreva:",
                       "every country has its own culture", audio_text="Every country has its own culture."),
                    ex("quiz", "Como se diz 'patrimônio' (cultural) em inglês?",
                       "heritage", ["heritage", "artist", "language"]),
                ],
            ),
            topic(
                "midia",
                "Mídia",
                """
# Mídia

| Inglês | Português |
|---|---|
| news | notícias |
| newspaper | jornal |
| article | artigo |
| channel | canal |
| journalist | jornalista |
| report | reportagem |
| audience | público (audiência) |
| advertisement | anúncio |

## Exemplos

```
I read the news every day.       Eu leio as notícias todos os dias.
The report is very interesting.  A reportagem é muito interessante.
```

> 💡 **news** é incontável e singular: "The news is good" (não "are").
""",
                [
                    ex("quiz", "Como se diz 'notícias' em inglês?",
                       "news", ["news", "article", "channel"]),
                    ex("quiz", "Como se diz 'jornalista' em inglês?",
                       "journalist", ["journalist", "audience", "report"]),
                    ex("text", "Traduza: Eu leio as notícias todos os dias.",
                       "i read the news every day"),
                    ex("quiz", "Como se diz 'artigo' (de jornal) em inglês?",
                       "article", ["article", "news", "channel"]),
                    ex("audio", "Escute e transcreva:",
                       "the report is very interesting", audio_text="The report is very interesting."),
                    ex("quiz", "Como se diz 'público' (audiência) em inglês?",
                       "audience", ["audience", "journalist", "article"]),
                ],
            ),
            topic(
                "negocios",
                "Negócios",
                """
# Negócios

| Inglês | Português |
|---|---|
| business | negócio / empresa |
| company | empresa |
| customer | cliente |
| client | cliente (de serviço) |
| product | produto |
| market | mercado |
| profit | lucro |
| brand | marca |
| deal | acordo / negócio |

## Exemplos

```
The company grew this year.     A empresa cresceu este ano.
Our customers are happy.        Nossos clientes estão felizes.
```

> 💡 **customer** (quem compra em loja) e **client** (quem contrata serviço)
> os dois são "cliente". **profit** = lucro.
""",
                [
                    ex("quiz", "Como se diz 'empresa' em inglês?",
                       "company", ["company", "customer", "product"]),
                    ex("quiz", "Como se diz 'cliente' em inglês?",
                       "client", ["client", "brand", "profit"]),
                    ex("text", "Traduza: A empresa cresceu este ano.",
                       "the company grew this year"),
                    ex("quiz", "Como se diz 'lucro' em inglês?",
                       "profit", ["profit", "deal", "market"]),
                    ex("audio", "Escute e transcreva:",
                       "our customers are happy", audio_text="Our customers are happy."),
                    ex("quiz", "Como se diz 'marca' em inglês?",
                       "brand", ["brand", "strategy", "profit"]),
                ],
            ),
            topic(
                "emocoes",
                "Emoções",
                """
# Emoções

| Inglês | Português |
|---|---|
| angry | com raiva |
| nervous | nervoso |
| excited | animado / empolgado |
| worried | preocupado |
| scared | com medo |
| proud | orgulhoso |
| relaxed | relaxado |
| disappointed | decepcionado |

## Exemplos

```
I am worried about the exam.     Estou preocupado com a prova.
She is very excited about the trip.  Ela está muito animada com a viagem.
```

> 💡 **excited** = animado (positivo); **nervous** = nervoso (ansioso). Use
> **about** para dizer com o quê: "excited about", "worried about".
""",
                [
                    ex("quiz", "Como se diz 'nervoso' em inglês?",
                       "nervous", ["nervous", "relaxed", "proud"]),
                    ex("quiz", "Como se diz 'animado/empolgado' em inglês?",
                       "excited", ["excited", "worried", "scared"]),
                    ex("text", "Traduza: Eu estou preocupado com a prova.",
                       "i am worried about the exam"),
                    ex("quiz", "Como se diz 'com raiva' em inglês?",
                       "angry", ["angry", "proud", "disappointed"]),
                    ex("audio", "Escute e transcreva:",
                       "she is very excited about the trip", audio_text="She is very excited about the trip."),
                    ex("quiz", "Como se diz 'orgulhoso' em inglês?",
                       "proud", ["proud", "relaxed", "nervous"]),
                ],
            ),
            topic(
                "personalidade",
                "Personalidade",
                """
# Personalidade

| Inglês | Português |
|---|---|
| confident | confiante |
| honest | honesto |
| patient | paciente |
| ambitious | ambicioso |
| creative | criativo |
| reliable | confiável |
| selfish | egoísta |
| generous | generoso |
| stubborn | teimoso |
| optimistic | otimista |

## Exemplos

```
He is very creative.          Ele é muito criativo.
She is very optimistic.       Ela é muito otimista.
```

> 💡 **reliable** = confiável (dá para contar); **selfish** = egoísta
> (oposto de **generous** = generoso).
""",
                [
                    ex("quiz", "Como se diz 'confiante' em inglês?",
                       "confident", ["confident", "shy", "patient"]),
                    ex("quiz", "Como se diz 'honesto' em inglês?",
                       "honest", ["honest", "selfish", "stubborn"]),
                    ex("text", "Traduza: Ele é muito criativo.",
                       "he is very creative"),
                    ex("quiz", "Como se diz 'ambicioso' em inglês?",
                       "ambitious", ["ambitious", "generous", "relaxed"]),
                    ex("audio", "Escute e transcreva:",
                       "she is very optimistic", audio_text="She is very optimistic."),
                    ex("quiz", "Como se diz 'paciente' em inglês?",
                       "patient", ["patient", "selfish", "stubborn"]),
                ],
            ),
            topic(
                "relacoes-interpessoais",
                "Relações interpessoais",
                """
# Relações interpessoais

| Inglês | Português |
|---|---|
| trust | confiança / confiar |
| respect | respeito / respeitar |
| support | apoio / apoiar |
| to argue | discutir (de palavras) |
| to forgive | perdoar |
| to apologize | pedir desculpas |
| compromise | acordo / conciliação |
| loyalty | lealdade |
| to communicate | comunicar-se |

## Exemplos

```
It is important to respect others.      É importante respeitar os outros.
Communication is key in relationships.  A comunicação é fundamental nos relacionamentos.
```

> 💡 **to argue** = discutir (argumentar); **to forgive** = perdoar;
> **to apologize** = pedir desculpas. São verbos centrais de qualquer
> relacionamento.
""",
                [
                    ex("quiz", "Como se diz 'confiança' em inglês?",
                       "trust", ["trust", "respect", "support"]),
                    ex("quiz", "Como se diz 'discutir' (de palavras) em inglês?",
                       "argue", ["argue", "forgive", "support"]),
                    ex("text", "Traduza: É importante respeitar os outros.",
                       "it is important to respect others"),
                    ex("quiz", "Como se diz 'perdoar' em inglês?",
                       "forgive", ["forgive", "apologize", "compromise"]),
                    ex("audio", "Escute e transcreva:",
                       "communication is key in relationships", audio_text="Communication is key in relationships."),
                    ex("quiz", "Como se diz 'lealdade' em inglês?",
                       "loyalty", ["loyalty", "trust", "respect"]),
                ],
            ),
            topic(
                "conceitos-abstratos",
                "Conceitos abstratos",
                """
# Conceitos abstratos

| Inglês | Português |
|---|---|
| truth | verdade |
| idea | ideia |
| justice | justiça |
| peace | paz |
| courage | coragem |
| happiness | felicidade |
| meaning | significado |
| value | valor |
| freedom | liberdade |

## Exemplos

```
Freedom is important.            A liberdade é importante.
Happiness is not about money.    Felicidade não é sobre dinheiro.
```

> 💡 **truth** (verdade) vs **true** (verdadeiro). **justice** (justiça) e
> **peace** (paz) aparecem muito em notícias e discussões.
""",
                [
                    ex("quiz", "Como se diz 'verdade' em inglês?",
                       "truth", ["truth", "idea", "peace"]),
                    ex("quiz", "Como se diz 'justiça' em inglês?",
                       "justice", ["justice", "courage", "meaning"]),
                    ex("text", "Traduza: A liberdade é importante.",
                       "freedom is important"),
                    ex("quiz", "Como se diz 'coragem' em inglês?",
                       "courage", ["courage", "happiness", "value"]),
                    ex("audio", "Escute e transcreva:",
                       "happiness is not about money", audio_text="Happiness is not about money."),
                    ex("quiz", "Como se diz 'paz' em inglês?",
                       "peace", ["peace", "truth", "justice"]),
                ],
            ),
        ],
    )


# ============================================================
# MODULO 10 - Speaking - B1
# ============================================================

def build_modulo_10_speaking_b1():
    return module(
        "modulo-10-speaking-b1",
        "Módulo 10 — Speaking — B1",
        "Falar com desenvoltura: opinar, concordar, discordar, explicar ideias, contar histórias, descrever experiências, dar razões, comparar, argumentar, aconselhar, discutir problemas e falar de planos e objetivos.",
        [
            topic(
                "dando-sua-opiniao",
                "Expressando opiniões",
                """
# Expressando opiniões

Para opinar de forma natural, use expressões variadas — assim você não repete
sempre "I think".

## Expressões úteis

```
In my opinion, ...              Na minha opinião, ...
I think (that) ...              Eu acho que ...
From my point of view, ...      Do meu ponto de vista, ...
As far as I'm concerned, ...    No que me diz respeito, ...
```

## Exemplos

```
In my opinion, this is the best option.   Na minha opinião, esta é a melhor opção.
I think we should wait.                  Eu acho que devemos esperar.
```

> 💡 **As far as I'm concerned** é uma forma um pouco mais formal de
> "na minha opinião". Use **In my opinion** para dar ênfase.
""",
                [
                    ex("quiz", "Como dar opinião de forma um pouco mais formal?",
                       "In my opinion, ...", ["In my opinion, ...", "I don't care.", "Maybe."]),
                    ex("text", "Traduza: Do meu ponto de vista, está certo.",
                       "from my point of view it is right"),
                    ex("quiz", "O que 'As far as I'm concerned...' significa?",
                       "No que me diz respeito...", ["No que me diz respeito...", "Até agora...", "Eu não sei..."]),
                    ex("audio", "Escute e transcreva:",
                       "in my opinion this is the best option", audio_text="In my opinion, this is the best option."),
                    ex("quiz", "Qual frase expressa opinião?",
                       "I think we should wait.", ["I think we should wait.", "Let's wait, ok.", "Wait now."]),
                    ex("speak", "Diga em voz alta:",
                       "in my opinion it is a good idea", audio_text="In my opinion, it is a good idea."),
                ],
            ),
            topic(
                "concordando",
                "Concordando",
                """
# Concordando

## Formas de concordar

```
I agree (with you).         Concordo (com você).
You're right.               Você tem razão.
That's true.                É verdade.
Exactly!                    Exatamente!
I think you're right.       Acho que você tem razão.
```

## Concordância parcial

```
You have a point, but...    Você tem um ponto, mas...
```

> 💡 Para concordar, repita a ideia: "Yes, I think so too." Para concordar
> parcialmente, use **You have a point, but...**.
""",
                [
                    ex("quiz", "Como concordar com alguém?",
                       "I agree with you.", ["I agree with you.", "I disagree with you.", "I don't know."]),
                    ex("text", "Traduza: Você tem razão.",
                       "you are right"),
                    ex("quiz", "O que 'Exactly!' expressa?",
                       "Exatamente!", ["Exatamente!", "Nunca!", "Talvez."]),
                    ex("audio", "Escute e transcreva:",
                       "that is true", audio_text="That is true."),
                    ex("quiz", "Qual resposta CONCORDA?",
                       "I think you're right.", ["I think you're right.", "I don't think so.", "No way."]),
                    ex("quiz", "Para concordar PARCIALMENTE, você diz:",
                       "You have a point, but...", ["You have a point, but...", "You are wrong.", "Never."]),
                ],
            ),
            topic(
                "discordando",
                "Discordando",
                """
# Discordando

Discordar com educação é uma habilidade-chave do B1. Sempre suavize com
"mas", "não tenho certeza" e "acho".

## Formas educadas

```
I disagree (with you).          Eu discordo (de você).
I don't think so.               Eu não acho.
I see your point, but...        Eu entendo seu ponto, mas...
That's not how I see it.        Não é assim que eu vejo.
I'm not sure I agree.           Não tenho certeza se concordo.
```

> 💡 Em vez de "That's wrong!" (rude), diga "I'm not sure about that."
> — a mesma discordância, com muito mais educação.
""",
                [
                    ex("quiz", "Como discordar educadamente?",
                       "I see your point, but I disagree.", ["I see your point, but I disagree.", "You are stupid.", "No."]),
                    ex("text", "Traduza: Eu não acho.",
                       "i don't think so"),
                    ex("quiz", "O que 'That's not how I see it' significa?",
                       "Não é assim que eu vejo", ["Não é assim que eu vejo", "É exatamente assim", "Eu não sei"]),
                    ex("audio", "Escute e transcreva:",
                       "i disagree with that", audio_text="I disagree with that."),
                    ex("quiz", "Qual é uma discordância EDUCADA?",
                       "I'm not sure I agree.", ["I'm not sure I agree.", "That's wrong!", "You're wrong."]),
                    ex("quiz", "Para discordar sem ser rude, use:",
                       "I'm not sure about that.", ["I'm not sure about that.", "This is terrible.", "Impossible."]),
                ],
            ),
            topic(
                "explicando-ideias",
                "Explicando ideias",
                """
# Explicando ideias

Quando a outra pessoa não entende, você precisa reformular.

## Reformulando e exemplificando

```
Let me explain.               Deixe-me explicar.
What I mean is...             O que quero dizer é...
In other words, ...           Em outras palavras, ...
For example, ...              Por exemplo, ...
```

## Exemplos

```
What I mean is that we need more time.   O que quero dizer é que precisamos de mais tempo.
For example, we could start later.       Por exemplo, poderíamos começar mais tarde.
```

> 💡 **What I mean is...** clarifica; **In other words...** reafirma com
> outras palavras; **For example...** dá um exemplo concreto.
""",
                [
                    ex("quiz", "Como reformular uma ideia com outras palavras?",
                       "In other words, ...", ["In other words, ...", "Anyway, ...", "By the way, ..."]),
                    ex("text", "Traduza: Deixe-me explicar.",
                       "let me explain"),
                    ex("quiz", "Para dar um exemplo, use:",
                       "For example, ...", ["For example, ...", "However, ...", "Therefore, ..."]),
                    ex("audio", "Escute e transcreva:",
                       "what i mean is that we need more time", audio_text="What I mean is that we need more time."),
                    ex("quiz", "O que 'What I mean is...' introduz?",
                       "uma clarificação (o que quero dizer)", ["uma clarificação (o que quero dizer)", "uma despedida", "uma pergunta"]),
                    ex("quiz", "Para reafirmar com outras palavras, use:",
                       "In other words, ...", ["In other words, ...", "First, ...", "Goodbye."]),
                ],
            ),
            topic(
                "contando-historias",
                "Contando histórias",
                """
# Contando histórias

Para contar uma história, organize o tempo com conectores e use os tempos do
passado (passado simples/contínuo/perfeito).

## Conectores de sequência

```
First, ...        Primeiro, ...
Then, ...         Então, ...
After that, ...   Depois disso, ...
Suddenly, ...     De repente, ...
Finally, ...      Finalmente, ...
```

## Exemplo

```
First, we arrived. Then, we had dinner. Finally, we went home.
Primeiro chegamos. Depois jantamos. Finalmente, fomos para casa.
```

> 💡 **Suddenly** introduz o momento inesperado da história — o que deixa a
> narrativa interessante.
""",
                [
                    ex("quiz", "Qual palavra marca o INÍCIO de uma história?",
                       "First, ...", ["First, ...", "Finally, ...", "Also, ..."]),
                    ex("quiz", "Qual palavra marca o FIM da história?",
                       "Finally, ...", ["Finally, ...", "First, ...", "Suddenly, ..."]),
                    ex("text", "Ordene as palavras: 'came / He / home / and / slept.'",
                       "he came home and slept"),
                    ex("audio", "Escute e transcreva:",
                       "first we arrived then we had dinner", audio_text="First, we arrived. Then, we had dinner."),
                    ex("quiz", "Para continuar a sequência da história, use:",
                       "After that, ...", ["After that, ...", "However, ...", "In my opinion, ..."]),
                    ex("quiz", "O que 'Suddenly' indica numa história?",
                       "um acontecimento inesperado", ["um acontecimento inesperado", "o final", "uma opinião"]),
                ],
            ),
            topic(
                "descrevendo-experiencias",
                "Descrevendo experiências",
                """
# Descrevendo experiências

Use o **presente perfeito** para a experiência em si e o **passado simples**
para os detalhes de quando aconteceu.

## Exemplos

```
I've traveled abroad.            Já viajei para fora.
I have been to Japan twice.      Já estive no Japão duas vezes.
I've never tried it.             Nunca experimentei.
It was amazing.                  Foi incrível.
```

## Adjetivos de experiência

```
amazing / fantastic / incredible     incrível
terrible / awful                     terrível
boring / interesting                 chato / interessante
```

> 💡 Padrão: **presente perfeito** (experiência) + **passado simples**
> (detalhe): "I've been to Paris. It was beautiful."
""",
                [
                    ex("quiz", "Como dizer 'Eu já viajei para fora'?",
                       "I've traveled abroad.", ["I've traveled abroad.", "I travel abroad.", "I will travel abroad."]),
                    ex("text", "Traduza: Foi incrível.",
                       "it was amazing"),
                    ex("quiz", "Qual adjetivo descreve uma experiência ÓTIMA?",
                       "amazing", ["amazing", "terrible", "boring"]),
                    ex("audio", "Escute e transcreva:",
                       "i have been to japan twice", audio_text="I have been to Japan twice."),
                    ex("quiz", "Para dar o DETALHE de quando a experiência aconteceu, use o:",
                       "passado simples", ["passado simples", "presente contínuo", "futuro"]),
                    ex("quiz", "O que 'I've never tried it' significa?",
                       "Eu nunca experimentei", ["Eu nunca experimentei", "Eu já experimentei", "Eu vou experimentar"]),
                ],
            ),
            topic(
                "dando-razoes",
                "Dando razões",
                """
# Dando razões

Para explicar o PORQUÊ das coisas, use conectores de causa.

## Conectores

```
because            porque
since              já que / porque (mais formal)
that's why         é por isso que
the reason is      o motivo é
because of         por causa de
```

## Exemplos

```
I stayed home because it was raining.       Fiquei em casa porque estava chovendo.
I was late because of the traffic.          Atrasei por causa do trânsito.
I'm tired, that's why I'm sleeping early.   Estou cansado, é por isso que vou dormir cedo.
```

> 💡 **because** + frase; **because of** + substantivo: "because it rained"
> vs "because of the rain".
""",
                [
                    ex("quiz", "Para dar uma razão, use:",
                       "because", ["because", "but", "so"]),
                    ex("text", "Traduza: Eu fiquei em casa porque estava chovendo.",
                       "i stayed home because it was raining"),
                    ex("quiz", "O que 'That's why...' significa?",
                       "É por isso que...", ["É por isso que...", "Porém...", "Então..."]),
                    ex("audio", "Escute e transcreva:",
                       "i was late because of the traffic", audio_text="I was late because of the traffic."),
                    ex("quiz", "Qual frase dá a RAZÃO?",
                       "I'm tired because I worked a lot.", ["I'm tired because I worked a lot.", "I'm tired, so I sleep.", "I'm tired but happy."]),
                    ex("quiz", "Um sinônimo mais formal de 'because' é:",
                       "since", ["since", "but", "or"]),
                ],
            ),
            topic(
                "comparando-coisas",
                "Comparando coisas",
                """
# Comparando coisas

Use comparativos e superlativos (Módulo 5) para comparar.

## Comparando dois

```
A is better than B.             A é melhor que B.
This car is faster than that one.   Este carro é mais rápido que aquele.
```

## Comparando com "compared to"

```
Compared to my old phone, this one is amazing.   Comparado com meu celular antigo, este é incrível.
```

## Igualdade: as ... as

```
This book is as good as that one.   Este livro é tão bom quanto aquele.
```

> 💡 **than** + a segunda coisa ("better than"). **as ... as** diz que são
> iguais. **the most/-est** diz o melhor de um grupo.
""",
                [
                    ex("quiz", "Como comparar duas coisas?",
                       "A is better than B.", ["A is better than B.", "A is better that B.", "A is good that B."]),
                    ex("text", "Traduza: Este carro é mais rápido que aquele.",
                       "this car is faster than that one"),
                    ex("quiz", "O que 'compared to' significa?",
                       "comparado com", ["comparado com", "por causa de", "apesar de"]),
                    ex("audio", "Escute e transcreva:",
                       "this phone is more expensive than the other", audio_text="This phone is more expensive than the other."),
                    ex("quiz", "Para dizer que duas coisas são IGUAIS, use:",
                       "as ... as", ["as ... as", "more ... than", "the most"]),
                    ex("quiz", "O que 'It's the best option' significa?",
                       "É a melhor opção", ["É a melhor opção", "É uma boa opção", "É a pior opção"]),
                ],
            ),
            topic(
                "construindo-argumentos",
                "Construindo argumentos",
                """
# Construindo argumentos

Para defender uma ideia, organize: introdução -> pontos -> contraponto ->
conclusão.

## Organizadores

```
First of all, ...          Primeiramente, ...
Another point is ...       Outro ponto é ...
Moreover, ...              Além disso, ...
However, ...               Porém, ...
In conclusion, ...         Para concluir, ...
```

## Exemplo

```
First of all, it is cheap. Moreover, it is fast. However, there are some problems.
Primeiramente, é barato. Além disso, é rápido. Porém, há alguns problemas.
```

> 💡 **Moreover** acrescenta; **However** muda de direção; **In conclusion**
> resume. Com esses três, você estrutura qualquer opinião.
""",
                [
                    ex("quiz", "Como COMEÇAR um argumento?",
                       "First of all, ...", ["First of all, ...", "Finally, ...", "Anyway, ..."]),
                    ex("text", "Traduza: Além disso, é barato.",
                       "moreover it is cheap"),
                    ex("quiz", "Para acrescentar um ponto, use:",
                       "Another point is ...", ["Another point is ...", "However ...", "In conclusion ..."]),
                    ex("audio", "Escute e transcreva:",
                       "however there are some problems", audio_text="However, there are some problems."),
                    ex("quiz", "Para CONCLUIR um argumento, use:",
                       "In conclusion, ...", ["In conclusion, ...", "First, ...", "So far, ..."]),
                    ex("quiz", "O que 'Moreover' significa?",
                       "Além disso", ["Além disso", "Porém", "Finalmente"]),
                ],
            ),
            topic(
                "aconselhando",
                "Dando conselhos",
                """
# Dando conselhos

Além de **should** (Módulo 5), o B1 usa formas mais suaves.

## Formas de aconselhar

```
You should take a break.           Você deveria dar uma pausa.
You shouldn't work so much.        Você não deveria trabalhar tanto.
If I were you, I would wait.       Se eu fosse você, eu esperaria.
You'd better rest.                 É melhor você descansar.
I'd advise you to try again.       Eu aconselho você a tentar de novo.
```

> 💡 **If I were you, I'd...** é o conselho mais clássico do inglês (segundo
> condicional). **You'd better** é um conselho forte ("é melhor você...").
""",
                [
                    ex("quiz", "Como aconselhar de forma suave?",
                       "If I were you, I would wait.", ["If I were you, I would wait.", "You must wait now.", "Wait or else."]),
                    ex("text", "Traduza: Você não deveria trabalhar tanto.",
                       "you shouldn't work so much"),
                    ex("quiz", "O que 'You'd better rest' significa?",
                       "É melhor você descansar", ["É melhor você descansar", "Você descansa depois", "Não descanse"]),
                    ex("audio", "Escute e transcreva:",
                       "if i were you i would study more", audio_text="If I were you, I would study more."),
                    ex("quiz", "Qual frase dá um CONSELHO?",
                       "You should take a break.", ["You should take a break.", "You take a break.", "I took a break."]),
                    ex("quiz", "O que 'I'd advise you to...' é?",
                       "uma forma formal de aconselhar", ["uma forma formal de aconselhar", "uma pergunta", "uma ordem"]),
                ],
            ),
            topic(
                "discutindo-problemas",
                "Discutindo problemas",
                """
# Discutindo problemas

Para discutir problemas, nomeie o problema, proponha soluções e pergunte a
opinião dos outros.

## Frases úteis

```
The problem is that...          O problema é que...
We need to solve this.          Precisamos resolver isso.
What should we do?              O que devemos fazer?
Let's think about options.      Vamos pensar nas opções.
We could try a different approach.  Poderíamos tentar uma abordagem diferente.
```

> 💡 **solve** = resolver. Para propor solução: "We could..." (poderíamos)
> é a forma suave e colaborativa.
""",
                [
                    ex("quiz", "Como iniciar a discussão de um problema?",
                       "The problem is that...", ["The problem is that...", "I love this.", "See you."]),
                    ex("text", "Traduza: O que devemos fazer?",
                       "what should we do"),
                    ex("quiz", "O que 'Let's think about options' propõe?",
                       "Vamos pensar nas opções", ["Vamos pensar nas opções", "Vamos embora", "Não há solução"]),
                    ex("audio", "Escute e transcreva:",
                       "we need to solve this problem", audio_text="We need to solve this problem."),
                    ex("quiz", "Para propor uma solução, diga:",
                       "We could try a different approach.", ["We could try a different approach.", "This is impossible.", "I don't know anything."]),
                    ex("quiz", "O que 'solve' significa?",
                       "resolver", ["resolver", "criar", "ignorar"]),
                ],
            ),
            topic(
                "falando-de-planos",
                "Falando de planos",
                """
# Falando de planos

Para falar de intenções, use várias formas — nem sempre "going to".

## Formas de falar de planos

```
I'm planning to travel.           Estou planejando viajar.
I intend to finish this month.    Pretendo terminar este mês.
I'm thinking of changing jobs.    Estou pensando em mudar de emprego.
I hope to see you soon.           Espero te ver em breve.
```

> 💡 **planning to / intend to** = planos mais decididos; **thinking of +
> gerúndio** e **hope to** = planos menos certos.
""",
                [
                    ex("quiz", "Como dizer 'Eu pretendo viajar'?",
                       "I'm planning to travel.", ["I'm planning to travel.", "I traveled.", "I travel every day."]),
                    ex("text", "Traduza: Eu estou pensando em mudar de emprego.",
                       "i am thinking of changing jobs"),
                    ex("quiz", "O que 'I intend to...' significa?",
                       "Eu pretendo...", ["Eu pretendo...", "Eu me recuso a...", "Eu costumava..."]),
                    ex("audio", "Escute e transcreva:",
                       "i hope to finish this month", audio_text="I hope to finish this month."),
                    ex("quiz", "Para planos menos certos, use:",
                       "I'm thinking of...", ["I'm thinking of...", "I'm going to...", "I will..."]),
                    ex("quiz", "Qual frase fala de um PLANO?",
                       "I'm planning to start a course.", ["I'm planning to start a course.", "I started a course.", "I start courses often."]),
                ],
            ),
            topic(
                "falando-de-objetivos",
                "Falando de objetivos",
                """
# Falando de objetivos

Para falar de metas, use **goal**, **aim** e **target**, e diga o que está
fazendo para alcançá-las.

## Frases úteis

```
My goal is to learn English.        Meu objetivo é aprender inglês.
I want to achieve my goals.         Quero alcançar meus objetivos.
My main goal is to save money.      Meu principal objetivo é economizar dinheiro.
I'm working towards my goal.        Estou trabalhando para alcançar meu objetivo.
```

## Tipos de objetivo

```
short-term goal      objetivo de curto prazo
long-term goal       objetivo de longo prazo
```

> 💡 **achieve** = alcançar (uma meta). **work towards** = trabalhar rumo a
> um objetivo.
""",
                [
                    ex("quiz", "Como dizer 'Meu objetivo é aprender inglês'?",
                       "My goal is to learn English.", ["My goal is to learn English.", "My goal is learned English.", "My goal learn English."]),
                    ex("text", "Traduza: Eu quero alcançar meus objetivos.",
                       "i want to achieve my goals"),
                    ex("quiz", "O que 'long-term goal' significa?",
                       "objetivo de longo prazo", ["objetivo de longo prazo", "objetivo de curto prazo", "objetivo final"]),
                    ex("audio", "Escute e transcreva:",
                       "my main goal is to save money", audio_text="My main goal is to save money."),
                    ex("quiz", "Para falar do que está fazendo rumo ao objetivo, diga:",
                       "I'm working towards my goal.", ["I'm working towards my goal.", "I have no goals.", "Goals are boring."]),
                    ex("quiz", "O que 'achieve' significa?",
                       "alcançar / atingir", ["alcançar / atingir", "abandonar", "começar"]),
                ],
            ),
        ],
    )


# ============================================================
# MODULO 11 - Listening - B1
# ============================================================

def build_modulo_11_listening_b1():
    return module(
        "modulo-11-listening-b1",
        "Módulo 11 — Listening — B1",
        "Treinar o ouvido: entender fala natural, sotaques, fala reduzida e conectada, contrações, palavras-chave, contexto, conversas, podcasts e vídeos.",
        [
            topic(
                "entendendo-fala-natural",
                "Entendendo fala natural",
                """
# Entendendo fala natural

A fala nativa parece rápida porque as palavras se **juntam** e se **reduzem**.
Não se desespere: você não precisa ouvir cada letra.

## Por que parece tão rápido?

- Os falantes **reduzem** sons: "going to" vira "gonna".
- As palavras se **conectam**: "turn it off" soa como "tur-nit-off".
- Muitas palavras pequenas são ditas rapidinho e quase "somem".

## A estratégia certa

1. **Foque nas palavras-chave** (substantivos e verbos).
2. **Use o contexto** para completar o que faltou.
3. **Ouça de novo** — cada repetição pega algo novo.

> 💡 Você não precisa entender 100% — o objetivo é pegar o sentido geral.
""",
                [
                    ex("quiz", "Por que a fala nativa parece rápida demais?",
                       "porque há reduções, junções e contrações", ["porque há reduções, junções e contrações", "porque os falantes gritam", "porque não usam gramática"]),
                    ex("audio", "Escute e transcreva:",
                       "what are you doing", audio_text="What are you doing?"),
                    ex("quiz", "A melhor estratégia para fala rápida é:",
                       "focar nas palavras-chave e no contexto", ["focar nas palavras-chave e no contexto", "tentar ouvir cada letra", "pausar a cada palavra"]),
                    ex("audio", "Escute e transcreva:",
                       "i'm going to the store", audio_text="I'm going to the store."),
                    ex("quiz", "O que 'gonna' significa (muito usado na fala)?",
                       "going to", ["going to", "want to", "have to"]),
                    ex("audio", "Escute e transcreva:",
                       "where are you from", audio_text="Where are you from?"),
                ],
            ),
            topic(
                "sotaques-diferentes",
                "Sotaques diferentes",
                """
# Sotaques diferentes

O inglês tem muitos sotaques: americano, britânico, australiano... A
gramática é quase a mesma — mudam a **pronúncia**, o **ritmo** e algumas
**palavras**.

## Palavras diferentes

| Americano | Britânico |
|---|---|
| color | colour |
| apartment | flat |
| elevator | lift |
| movie | film |

## Como lidar

- **Não entre em pânico**: o contexto resolve quase tudo.
- **Peça para repetir**: "Sorry, can you repeat that?"
- **Exponha-se**: ouça sotaques diferentes de propósito.

> 💡 Quanto mais sotaques você ouvir, mais fácil fica cada um deles. É
> treino de exposição.
""",
                [
                    ex("quiz", "O equivalente britânico de 'color' é:",
                       "colour", ["colour", "colorr", "culor"]),
                    ex("audio", "Escute e transcreva:",
                       "i can't come today", audio_text="I can't come today."),
                    ex("quiz", "O que muda entre sotaques do inglês?",
                       "pronúncia, ritmo e algumas palavras", ["pronúncia, ritmo e algumas palavras", "a gramática inteira", "tudo, é outra língua"]),
                    ex("audio", "Escute e transcreva:",
                       "do you want some tea", audio_text="Do you want some tea?"),
                    ex("quiz", "Diante de um sotaque desconhecido, o melhor é:",
                       "pedir para repetir e ouvir o contexto", ["pedir para repetir e ouvir o contexto", "fingir que entendeu", "desligar"]),
                    ex("quiz", "O equivalente britânico de 'apartment' é:",
                       "flat", ["flat", "house", "room"]),
                ],
            ),
            topic(
                "fala-reduzida",
                "Fala reduzida",
                """
# Fala reduzida

Na conversa informal, palavras viram versões **reduzidas**.

## As mais comuns

| Fala | Significado |
|---|---|
| gonna | going to |
| wanna | want to |
| gotta | have got to (tenho que) |
| kinda | kind of (meio que) |
| lemme | let me |

## Exemplos

```
I wanna go home.      Eu quero ir para casa.  (I want to go home)
I gotta leave now.    Tenho que ir agora.
It's kinda late.      Está meio tarde.
```

> 💡 As reduções aparecem em conversas informais, músicas, filmes e séries.
> No texto formal ou em provas, use a forma completa.
""",
                [
                    ex("quiz", "O que 'wanna' significa?",
                       "want to", ["want to", "going to", "have to"]),
                    ex("quiz", "O que 'gotta' significa?",
                       "have got to (tenho que)", ["have got to (tenho que)", "want to", "going to"]),
                    ex("audio", "Escute e transcreva:",
                       "i want to go home", audio_text="I want to go home."),
                    ex("quiz", "O que 'kinda' significa?",
                       "kind of (meio que)", ["kind of (meio que)", "can't", "don't"]),
                    ex("quiz", "As reduções aparecem:",
                       "na fala informal e em músicas/filmes", ["na fala informal e em músicas/filmes", "só em textos formais", "nunca"]),
                    ex("audio", "Escute e transcreva:",
                       "do you want to come", audio_text="Do you want to come?"),
                ],
            ),
            topic(
                "fala-conectada",
                "Fala conectada",
                """
# Fala conectada

O inglês conecta palavras: o fim de uma "gruda" no começo da próxima. É o
**connected speech**.

## Exemplos

```
turn it off    soa como  "tur-nit-off"
come in        soa como  "co-min"
```

Não é erro de pronúncia — é como o inglês flui naturalmente.

## Como treinar

- **Ouça** a mesma frase várias vezes.
- **Repita** em voz alta, tentando imitar a junção.
- Não traduza palavra por palavra — ouça o **bloco**.

> 💡 Entender fala conectada é o que separa "entender em câmera lenta" de
> "acompanhar uma conversa real".
""",
                [
                    ex("quiz", "O que é 'connected speech'?",
                       "palavras que se juntam na fala", ["palavras que se juntam na fala", "palavras que não existem", "gírias"]),
                    ex("audio", "Escute e transcreva:",
                       "turn it off", audio_text="Turn it off."),
                    ex("quiz", "Em 'turn it off', o 'n' de 'turn':",
                       "junta-se ao 'i' de 'it'", ["junta-se ao 'i' de 'it'", "some", "vira 'r'"]),
                    ex("audio", "Escute e transcreva:",
                       "he is coming at ten", audio_text="He is coming at ten."),
                    ex("quiz", "Para treinar a fala conectada, o ideal é:",
                       "ouvir a mesma frase várias vezes e repetir", ["ouvir a mesma frase várias vezes e repetir", "só ler", "nunca ouvir"]),
                    ex("quiz", "Na fala reduzida, 'wanna' vem de:",
                       "want to", ["want to", "went to", "will not"]),
                ],
            ),
            topic(
                "contracoes-comuns",
                "Contrações comuns",
                """
# Contrações comuns

As contrações juntam duas palavras e são onipresentes na fala.

## Com o verbo to be e have

```
I'm  (I am)      You're  (you are)    He's  (he is/has)
It's (it is)     We're   (we are)     They're (they are)
```

## Com auxiliares e modais

```
don't (do not)     didn't (did not)    won't (will not)
can't (can not)    isn't  (is not)     aren't (are not)
I'll  (I will)     I'd    (I would/had)
```

> 💡 Cuidado com os que soam iguais mas têm sentido diferente: **it's**
> (it is) vs **its** (dele); **they're** (they are) vs **their** (deles) vs
> **there** (lá).
""",
                [
                    ex("quiz", "'I'll' é a contração de:",
                       "I will", ["I will", "I am", "I had"]),
                    ex("quiz", "'Won't' é a contração de:",
                       "will not", ["will not", "would not", "want not"]),
                    ex("audio", "Escute e transcreva:",
                       "she doesn't like it", audio_text="She doesn't like it."),
                    ex("quiz", "O que 'I'd like' significa?",
                       "I would like", ["I would like", "I did like", "I am like"]),
                    ex("quiz", "'They're' pode significar:",
                       "they are", ["they are", "their", "there"]),
                    ex("audio", "Escute e transcreva:",
                       "i will call you later", audio_text="I will call you later."),
                ],
            ),
            topic(
                "identificando-palavras-chave",
                "Identificando palavras-chave",
                """
# Identificando palavras-chave

Ao ouvir, as palavras **não** têm o mesmo peso. As **palavras de conteúdo**
(substantivos, verbos, adjetivos) carregam o sentido; as **palavras de
função** (artigos, preposições) são ditas rapidinho.

## Exemplo

```
The MEETING is at THREE.
```

As palavras-chave são **meeting** e **three** — o resto é estrutura.

## Estratégia

1. Capture as palavras fortes (as que você "ouve bem").
2. Monte o sentido com elas.
3. Preencha o resto pelo contexto.

> 💡 É por isso que "ouvir e entender o assunto" vem antes de entender cada
> palavra: o assunto está nas palavras-chave.
""",
                [
                    ex("quiz", "Quais palavras carregam mais significado?",
                       "substantivos e verbos", ["substantivos e verbos", "artigos e preposições", "todas igual"]),
                    ex("audio", "Escute e transcreva:",
                       "the meeting is at three", audio_text="The meeting is at three."),
                    ex("quiz", "Em 'The book is on the table', as palavras-chave são:",
                       "book e table", ["book e table", "the, is e on", "todas são chave"]),
                    ex("audio", "Escute e transcreva:",
                       "she bought a new car", audio_text="She bought a new car."),
                    ex("quiz", "Ao ouvir, comece tentando captar:",
                       "o assunto e as palavras principais", ["o assunto e as palavras principais", "cada artigo", "a pontuação"]),
                    ex("quiz", "Qual é a melhor prática de listening?",
                       "ouvir com frequência, mesmo sem entender tudo", ["ouvir com frequência, mesmo sem entender tudo", "só ouvir uma vez por mês", "nunca ouvir"]),
                ],
            ),
            topic(
                "entendendo-contexto",
                "Entendendo pelo contexto",
                """
# Entendendo pelo contexto

Você não precisa conhecer toda palavra: o **contexto** (situação, tom de voz,
o que veio antes) completa o sentido.

## Usando a situação

```
Num restaurante: "I'd like the menu, please." -> um pedido educado.
Na rua: "Excuse me, where is the station?"   -> um pedido de direção.
```

## Usando o tom de voz

O mesmo "Really?" pode ser pergunta, surpresa ou dúvida — dependendo do tom.

## Quando não entender

```
Could you repeat that, please?     Você pode repetir, por favor?
Can you say it in other words?     Pode dizer de outro jeito?
```

> 💡 Perguntar de novo NÃO é sinal de fraqueza — é a forma mais rápida de
> aprender e de manter a conversa viva.
""",
                [
                    ex("quiz", "Quando você não conhece uma palavra, o contexto ajuda a:",
                       "adivinhar o sentido", ["adivinhar o sentido", "traduzir palavra por palavra", "ignorar tudo"]),
                    ex("audio", "Escute e transcreva:",
                       "it is raining outside", audio_text="It is raining outside."),
                    ex("quiz", "Num restaurante, 'I'd like the menu, please' indica:",
                       "um pedido educado", ["um pedido educado", "uma pergunta de direção", "uma reclamação"]),
                    ex("audio", "Escute e transcreva:",
                       "could you repeat that please", audio_text="Could you repeat that, please?"),
                    ex("quiz", "O tom de voz ajuda a entender:",
                       "a intenção (pergunta, ordem, surpresa)", ["a intenção (pergunta, ordem, surpresa)", "a gramática exata", "a ortografia"]),
                    ex("quiz", "A melhor reação quando você não entende:",
                       "pedir para repetir ou parafrasear", ["pedir para repetir ou parafrasear", "continuar fingindo", "sair"]),
                ],
            ),
            topic(
                "entendendo-conversas",
                "Entendendo conversas",
                """
# Entendendo conversas

Conversas têm pergunta -> resposta e muitos **preenchedores** (fillers).
Para acompanhar, foque no par pergunta/resposta.

## Estrutura típica

```
A: Do you like pizza?          (pergunta)
B: Yes, I do. I love pizza.    (resposta)
```

## Preenchedores comuns

```
Uh-huh     concordo / estou ouvindo
You know   sabe
Well, ...  bom, ...
Right.     certo
```

## Como acompanhar

1. Identifique a **pergunta** (do/does, is/are, question words).
2. Ouça a **resposta** — ela está logo em seguida.
3. Não trave em uma palavra; deixe o fluxo continuar.

> 💡 **Uh-huh** não significa raiva — é um "entendido" natural, usado o tempo
> todo.
""",
                [
                    ex("quiz", "Numa conversa, para entender, foque em:",
                       "a pergunta e a resposta", ["a pergunta e a resposta", "só no começo", "no silêncio"]),
                    ex("audio", "Escute e transcreva:",
                       "do you like pizza", audio_text="Do you like pizza?"),
                    ex("quiz", "'Uh-huh' numa conversa significa:",
                       "concordo / estou ouvindo", ["concordo / estou ouvindo", "estou bravo", "pare"]),
                    ex("audio", "Escute e transcreva:",
                       "yes i do i love pizza", audio_text="Yes, I do. I love pizza."),
                    ex("quiz", "'You know...' numa conversa é um:",
                       "preenchedor (filler)", ["preenchedor (filler)", "verbo", "adjetivo"]),
                    ex("quiz", "O que ajuda a acompanhar conversas rápidas?",
                       "praticar com áudios curtos todos os dias", ["praticar com áudios curtos todos os dias", "desistir", "só ler"]),
                ],
            ),
            topic(
                "entendendo-podcasts",
                "Entendendo podcasts",
                """
# Entendendo podcasts

Podcasts são ótimos para treinar porque você controla o ritmo e pode repetir.

## Como começar

- Escolha podcasts **curtos** e de nível mais **simples**.
- Ouça uma vez para o sentido geral.
- Ouça de novo e use a **transcrição** se disponível.

## Dicas

```
Play again.      Ouça de novo.
Repeat.          Repita.
Slow it down.    Desacelere (velocidade 0,75 ou 0,5).
```

> 💡 A vantagem do podcast: você escolhe o tema, o ritmo e a duração. Pouco
> todo dia (5-10 minutos) rende mais que muito uma vez por semana.
""",
                [
                    ex("quiz", "Para começar a ouvir podcasts, o ideal é:",
                       "áudios curtos e mais lentos", ["áudios curtos e mais lentos", "podcasts avançados de uma vez", "só músicas"]),
                    ex("audio", "Escute e transcreva:",
                       "welcome to the show", audio_text="Welcome to the show."),
                    ex("quiz", "O que ajuda a entender melhor um podcast?",
                       "ouvir de novo e ler a transcrição", ["ouvir de novo e ler a transcrição", "pular tudo", "ouvir uma única vez"]),
                    ex("audio", "Escute e transcreva:",
                       "today we talk about travel", audio_text="Today we talk about travel."),
                    ex("quiz", "A vantagem do podcast é:",
                       "você escolhe o ritmo e repete", ["você escolhe o ritmo e repete", "ser automático", "não ter áudio"]),
                    ex("quiz", "Para melhorar, o recomendado é ouvir:",
                       "um pouco todos os dias", ["um pouco todos os dias", "horas de uma vez no domingo", "nunca"]),
                ],
            ),
            topic(
                "entendendo-videos",
                "Entendendo vídeos",
                """
# Entendendo vídeos

Vídeos são os melhores amigos do listening: você tem **imagem**, **gestos** e
**legenda** como apoio.

## Estratégia em 3 passos

1. **Primeira vez**: legenda em inglês + imagem.
2. **Segunda vez**: sem legenda, tentando entender.
3. **Cheque**: volte na parte difícil e veja o que perdeu.

## Vocabulário de vídeo

```
Subtitles      legendas
Close captions legendas (fechadas)
Play / Pause   tocar / pausar
Rewind         voltar
```

> 💡 **Close captions** são as legendas que também descrevem sons ("door
> slams"). Assista o mesmo vídeo mais de uma vez — cada vez você pega algo
> novo.
""",
                [
                    ex("quiz", "A vantagem do vídeo sobre o áudio é:",
                       "pistas visuais e legenda", ["pistas visuais e legenda", "ser mais difícil", "não ter repetição"]),
                    ex("audio", "Escute e transcreva:",
                       "let's get started", audio_text="Let's get started."),
                    ex("quiz", "O uso recomendado de legendas é:",
                       "legenda em inglês e depois sem legenda", ["legenda em inglês e depois sem legenda", "legenda em português sempre", "sem nunca usar"]),
                    ex("audio", "Escute e transcreva:",
                       "watch this video again", audio_text="Watch this video again."),
                    ex("quiz", "Ao assistir duas vezes, você:",
                       "pega o que perdeu na primeira", ["pega o que perdeu na primeira", "perde tempo", "piora"]),
                    ex("quiz", "O que significa 'close captions'?",
                       "legendas", ["legendas", "volume", "pausa"]),
                ],
            ),
        ],
    )


# ============================================================
# MODULO 12 - Gramatica Essencial - B2
# ============================================================

def build_modulo_12_gramatica_essencial_b2():
    return module(
        "modulo-12-gramatica-essencial-b2",
        "Módulo 12 — Gramática Essencial — B2",
        "A gramática do intermediário avançado: presente perfeito contínuo, terceiro condicional, condicionais mistas, modais compostos, passiva com modais, causativo, discurso indireto avançado, inversão, relativas reduzidas, gerúndio/infinitivo avançados e frases complexas.",
        [
            topic(
                "presente-perfeito-avancado",
                "Presente Perfeito avançado",
                """
# Presente Perfeito avançado

O **presente perfeito contínuo** enfatiza que uma ação começou no passado e
continua (ou terminou há pouco). Forma: **have/has been + verbo-ing**.

## Afirmativo

```
I have been studying English for three years.   Estudo inglês há três anos.
He has been working a lot lately.               Ele tem trabalhado muito ultimamente.
```

## Negativo / Interrogativo

```
She hasn't been sleeping well.       Ela não tem dormido bem.
Have you been waiting long?          Você está esperando há muito tempo?
```

## for vs since

```
for + duração    ->  for three years (há três anos)
since + ponto    ->  since 2020 (desde 2020)
```

> 💡 **Presente perfeito contínuo** enfatiza a DURAÇÃO/ação em progresso;
> **presente perfeito** simples enfatiza o resultado/conclusão.
""",
                [
                    ex("quiz", 'Complete: "I have been ___ here for two hours." (wait)',
                       "waiting", ["waiting", "waited", "wait"]),
                    ex("quiz", "O presente perfeito contínuo expressa:",
                       "uma ação que começou no passado e continua (ou é recente)", ["uma ação que começou no passado e continua (ou é recente)", "uma ação terminada", "um fato geral"]),
                    ex("text", "Traduza: Ele tem trabalhado muito ultimamente.",
                       "he has been working a lot lately"),
                    ex("quiz", "'Since' indica:",
                       "o ponto inicial (desde)", ["o ponto inicial (desde)", "a duração total", "o futuro"]),
                    ex("audio", "Escute e transcreva:",
                       "i have been studying english for three years", audio_text="I have been studying English for three years."),
                    ex("quiz", 'Complete: "She has been ___ all day." (study)',
                       "studying", ["studying", "studied", "study"]),
                ],
            ),
            topic(
                "terceiro-condicional",
                "Terceiro Condicional",
                """
# Terceiro Condicional

O **terceiro condicional** fala de situações **irreais no passado** — o
arrependimento. Forma: **If + past perfect, would have + particípio**.

## Afirmativo

```
If I had known, I would have called.      Se eu soubesse, eu teria ligado.
If she had studied, she would have passed.  Se ela tivesse estudado, ela teria passado.
```

## Negativo

```
If we hadn't left early, we would have been late.   Se não tivéssemos saído cedo, teríamos chegado atrasados.
```

## Interrogativo

```
What would you have done?      O que você teria feito?
```

> 💡 Regra de ouro: **if + had + particípio**, depois **would have +
> particípio**. "If I would have known" está errado!
""",
                [
                    ex("quiz", 'Complete: "If I had known, I ___ have called."',
                       "would", ["would", "will", "had"]),
                    ex("quiz", "O terceiro condicional fala de:",
                       "situações irreais no passado (arrependimento)", ["situações irreais no passado (arrependimento)", "fatos", "futuro"]),
                    ex("text", "Complete: 'If she had studied, she ___ (pass) the exam.'",
                       "would have passed"),
                    ex("quiz", "A estrutura do terceiro condicional é:",
                       "if + past perfect, would have + particípio", ["if + past perfect, would have + particípio", "if + presente, will + verbo", "if + passado, would + verbo"]),
                    ex("audio", "Escute e transcreva:",
                       "if we had left earlier we would have arrived on time", audio_text="If we had left earlier, we would have arrived on time."),
                    ex("quiz", 'Complete: "If I had seen him, I ___ have said hello."',
                       "would", ["would", "will", "had"]),
                ],
            ),
            topic(
                "condicionais-mistas",
                "Condicionais mistas",
                """
# Condicionais mistas

As **condicionais mistas** combinam o segundo e o terceiro condicional.

## Tipo mais comum: condição no passado + resultado no presente

```
If I had taken the job, I would be rich now.
Se eu tivesse aceitado o emprego, eu seria rico agora.
```

(passado: não aceitei; presente: não sou rico)

## Tipo inverso: condição no presente + resultado no passado

```
If I were you, I would have done it.
Se eu fosse você, eu teria feito.
```

> 💡 A combinação mais usada: **if + past perfect** (passado) + **would +
> verbo** (presente). Observe que o resultado fica no presente.
""",
                [
                    ex("quiz", "Uma condicional mista comum é:",
                       "condição no passado + resultado no presente", ["condição no passado + resultado no presente", "só passado", "só futuro"]),
                    ex("quiz", 'Complete (mista): "If I had taken the job, I ___ be rich now."',
                       "would", ["would", "would have", "will"]),
                    ex("text", "Complete: 'If she ___ (study) more, she would be here now.'",
                       "had studied"),
                    ex("quiz", "Condicionais mistas combinam:",
                       "segundo e terceiro condicional", ["segundo e terceiro condicional", "zero e primeiro condicional", "presente e futuro"]),
                    ex("audio", "Escute e transcreva:",
                       "if he had listened he wouldn't have problems now", audio_text="If he had listened, he wouldn't have problems now."),
                    ex("quiz", 'Complete: "If I were you, I ___ have done it."',
                       "would", ["would", "will", "had"]),
                ],
            ),
            topic(
                "modais-compostos",
                "Modais compostos",
                """
# Modais compostos (must have / should have / can't have)

Forma: **modal + have + particípio** — para falar do **passado**.

| Modal composto | Uso | Exemplo |
|---|---|---|
| **must have + pp** | dedução (quase certeza) | He must have left. |
| **should have + pp** | arrependimento / conselho no passado | I should have studied. |
| **can't have + pp** | impossibilidade | She can't have forgotten. |

## Exemplos

```
He must have left.             Ele deve ter saído.      (dedução)
You should have told me.       Você deveria ter me contado.  (arrependimento)
She can't have forgotten.      Ela não pode ter esquecido.  (impossibilidade)
```

> 💡 **must have** é DEDUÇÃO (quase certeza), não obrigação. **should have**
> = arrependimento do que não foi feito.
""",
                [
                    ex("quiz", "O que 'He must have left' expressa?",
                       "dedução (ele deve ter saído)", ["dedução (ele deve ter saído)", "arrependimento", "permissão"]),
                    ex("quiz", "O que 'I should have studied' expressa?",
                       "arrependimento (eu deveria ter estudado)", ["arrependimento (eu deveria ter estudado)", "obrigação futura", "permissão"]),
                    ex("text", "Traduza: Ela deve ter esquecido.",
                       "she must have forgotten"),
                    ex("quiz", "O que 'can't have done' expressa?",
                       "impossibilidade (não pode ter feito)", ["impossibilidade (não pode ter feito)", "certeza de que fez", "sugestão"]),
                    ex("audio", "Escute e transcreva:",
                       "you should have told me", audio_text="You should have told me."),
                    ex("quiz", "A estrutura do modal composto é:",
                       "modal + have + particípio", ["modal + have + particípio", "modal + verbo", "modal + -ing"]),
                ],
            ),
            topic(
                "passiva-avancada",
                "Passiva avançada (com modais)",
                """
# Passiva avançada (com modais)

A voz passiva (Módulo 8) pode combinar com modais e com o presente perfeito.

## Passiva com modal: modal + be + particípio

```
The work can be done today.        O trabalho pode ser feito hoje.
The project should be finished by Friday.   O projeto deve ser terminado até sexta.
```

## Passiva no presente perfeito: have/has been + particípio

```
The house has been sold.           A casa foi vendida.
The report has been finished.      O relatório foi terminado.
```

> 💡 Repare: **can/should + be + pp** (passiva com modal) e **has been + pp**
> (passiva no presente perfeito) — o "be/been" é o que muda.
""",
                [
                    ex("quiz", 'Complete: "The work can ___ done today."',
                       "be", ["be", "been", "is"]),
                    ex("quiz", 'Complete: "The report has ___ finished."',
                       "been", ["been", "being", "be"]),
                    ex("text", "Traduza: O projeto deve ser terminado até sexta.",
                       "the project should be finished by friday"),
                    ex("quiz", "A passiva com modal usa:",
                       "modal + be + particípio", ["modal + be + particípio", "modal + particípio", "be + modal"]),
                    ex("audio", "Escute e transcreva:",
                       "the house has been sold", audio_text="The house has been sold."),
                    ex("quiz", "A passiva no presente perfeito usa:",
                       "has/have been + particípio", ["has/have been + particípio", "was/were + particípio", "is/are + particípio"]),
                ],
            ),
            topic(
                "causativo",
                "Causativo (have/get something done)",
                """
# Causativo (have/get something done)

O **causativo** diz que **alguém fez algo POR VOCÊ** (geralmente um serviço).
Forma: **have/get + objeto + particípio**.

## Exemplos

```
I had my car fixed.          Consertei meu carro (mandando consertar).
She got her nails done.      Ela fez as unhas (mandou fazer).
We had the house painted.    Pintamos a casa (contratando).
I had my hair cut.           Cortei o cabelo.
```

> 💡 A diferença: "I cut my hair" (você mesmo cortou) vs "I had my hair cut"
> (o cabeleireiro cortou). A forma **get** é mais informal que **have**.
""",
                [
                    ex("quiz", 'Complete: "I had my car ___." (consertado)',
                       "fixed", ["fixed", "fixing", "fix"]),
                    ex("quiz", "O causativo 'have something done' significa:",
                       "pagar/arranjar alguém para fazer algo por você", ["pagar/arranjar alguém para fazer algo por você", "fazer você mesmo", "pedir permissão"]),
                    ex("text", "Traduza: Eu cortei o cabelo (mandando cortar).",
                       "i had my hair cut"),
                    ex("quiz", 'Complete: "She got her nails ___." (feitas)',
                       "done", ["done", "doing", "do"]),
                    ex("audio", "Escute e transcreva:",
                       "we had the house painted last year", audio_text="We had the house painted last year."),
                    ex("quiz", "A estrutura do causativo é:",
                       "have/get + objeto + particípio", ["have/get + objeto + particípio", "have + particípio + objeto", "get + particípio"]),
                ],
            ),
            topic(
                "discurso-indireto-avancado",
                "Discurso indireto avançado",
                """
# Discurso indireto avançado

Além das afirmações (Módulo 8), agora relatar **perguntas**, **ordens** e
usar **verbos de citação**.

## Perguntas

```
Sim/não:  "Are you tired?"  ->  He asked if I was tired.
Com wh:   "Where do you live?"  ->  He asked me where I lived.
```

## Imperativos

```
"He said, 'Leave!'"  ->  She told me to leave.   (told/asked + to)
"He said, 'Don't go!'"  ->  She told me not to go.
```

## Verbos de citação

```
She suggested taking a break.      Ela sugeriu dar uma pausa.
He denied taking the money.        Ele negou ter pego o dinheiro.
She insisted on paying.            Ela insistiu em pagar.
```

> 💡 Depois de **suggest/deny/insist**, use gerúndio (suggest taking, deny
> taking, insist on paying).
""",
                [
                    ex("quiz", 'Complete: "He asked ___ I was tired." (pergunta sim/não)',
                       "if", ["if", "that", "what"]),
                    ex("quiz", 'Complete: "She told me ___ leave." (imperativo)',
                       "to", ["to", "that", "if"]),
                    ex("text", "Relate: 'He said, \"Where do you live?\"' -> He asked me where I ___.",
                       "lived"),
                    ex("quiz", "Depois de 'suggest', usamos:",
                       "gerúndio", ["gerúndio", "infinitivo", "that + would"]),
                    ex("audio", "Escute e transcreva:",
                       "she suggested taking a break", audio_text="She suggested taking a break."),
                    ex("quiz", "'He denied taking the money' significa:",
                       "ele negou ter pego o dinheiro", ["ele negou ter pego o dinheiro", "ele admitiu", "ele perguntou"]),
                ],
            ),
            topic(
                "inversao-adverbios-negativos",
                "Inversão com advérbios negativos",
                """
# Inversão com advérbios negativos

Quando um **advérbio negativo** vem no começo da frase, a ordem inverte
(auxiliar + sujeito).

## Exemplos

```
Never have I seen such a beautiful place.    Nunca vi um lugar tão bonito.
Rarely do they go out.                       Raramente eles saem.
Not only did she sing, but she also danced.  Não só ela cantou, como também dançou.
```

## A ordem normal vs a invertida

```
Normal:  I have never seen...
Invertida:  Never have I seen...
```

> 💡 Advérbios que causam inversão: **never, rarely, seldom, not only, no
> sooner, hardly**. É uma estrutura formal/literária — comum em textos e
> discursos.
""",
                [
                    ex("quiz", 'Complete: "Never ___ I seen such a beautiful place."',
                       "have", ["have", "I have", "has"]),
                    ex("quiz", "Depois de 'Never/Rarely/Not only', a ordem é:",
                       "inversão (auxiliar + sujeito)", ["inversão (auxiliar + sujeito)", "ordem normal", "verbo + objeto"]),
                    ex("text", "Complete: 'Rarely ___ (do) they go out.'",
                       "do"),
                    ex("quiz", "O que 'Never have I tried that' significa?",
                       "Nunca experimentei aquilo", ["Nunca experimentei aquilo", "Eu experimentei aquilo", "Sempre experimento aquilo"]),
                    ex("audio", "Escute e transcreva:",
                       "not only did she sing but she also danced", audio_text="Not only did she sing, but she also danced."),
                    ex("quiz", "A inversão acontece com:",
                       "advérbios negativos no início da frase", ["advérbios negativos no início da frase", "advérbios positivos", "preposições"]),
                ],
            ),
            topic(
                "oracoes-relativas-reduzidas",
                "Orações relativas e reduzidas",
                """
# Orações relativas e reduzidas (participle clauses)

Frases com **who/which/that** podem ser **reduzidas** usando particípios —
deixam o texto mais fluido e avançado.

## Redução com -ing (ação ativa)

```
The man who is sitting next to me = The man sitting next to me.
The woman who is standing there = The woman standing there.
```

## Redução com particípio passado (ação passiva)

```
The car that was bought = the car bought.
```

## Particípio passivo/ativo

```
-ing = ação ativa (algo/alguém fazendo)
-ado/-ido (particípio) = ação passiva (feito)
```

> 💡 Para reduzir, remova **who/which + be** e deixe o particípio:
> "the man who is running" vira "the man running".
""",
                [
                    ex("quiz", 'Complete a relativa reduzida: "The man ___ next to me is my brother." (sitting)',
                       "sitting", ["sitting", "who sitting", "sits"]),
                    ex("quiz", "Uma 'participle clause' usa:",
                       "particípio (sitting/done)", ["particípio (sitting/done)", "that + verbo", "who + verbo"]),
                    ex("text", "Complete: 'The book ___ on the table is mine.' (lying)",
                       "lying"),
                    ex("quiz", "Para reduzir 'the car that was bought', dizemos:",
                       "the car bought", ["the car bought", "the car buying", "the car buy"]),
                    ex("audio", "Escute e transcreva:",
                       "the woman standing there is my teacher", audio_text="The woman standing there is my teacher."),
                    ex("quiz", "Particípios em -ing descrevem uma ação:",
                       "ativa (algo/alguém fazendo)", ["ativa (algo/alguém fazendo)", "passiva (feito)", "futura"]),
                ],
            ),
            topic(
                "gerundio-infinitivo-avancado",
                "Gerúndio e infinitivo avançados",
                """
# Gerúndio e infinitivo avançados

Alguns verbos mudam de sentido conforme usamos gerúndio ou infinitivo.

## remember / forget / stop / try

```
I remember locking the door.       Lembro de ter fechado a porta. (passado)
I remembered to lock the door.     Lembrei de fechar a porta. (não esqueci)
She stopped smoking.               Ela parou de fumar.
She stopped to smoke.              Ela parou (o que fazia) para fumar.
```

## try

```
I tried to open the door.    Tentei abrir a porta. (esforço)
Try opening the door.        Experimente abrir a porta. (teste)
```

## O infinitivo perfeito (to have done)

```
He claims to have seen it.    Ele afirma ter visto.  (passado em relação ao verbo)
```

> 💡 **remember + -ing** = memória do passado; **remember + to** = não
> esquecer de fazer. **stop + -ing** = parar de; **stop + to** = parar para.
""",
                [
                    ex("quiz", 'Complete: "I remember ___ the door." (fechar — memória do passado)',
                       "closing", ["closing", "to close", "close"]),
                    ex("quiz", 'Complete: "I remembered ___ the door." (para não esquecer)',
                       "to lock", ["to lock", "locking", "lock"]),
                    ex("text", "Complete: 'She stopped ___ (smoke) two years ago.'",
                       "smoking"),
                    ex("quiz", "Em 'try', a forma 'try to do' sugere:",
                       "tentar (esforço)", ["tentar (esforço)", "experimentar como teste", "desistir"]),
                    ex("audio", "Escute e transcreva:",
                       "i regret telling her the secret", audio_text="I regret telling her the secret."),
                    ex("quiz", "O infinitivo perfeito 'to have done' expressa:",
                       "passado em relação ao verbo principal", ["passado em relação ao verbo principal", "futuro", "presente"]),
                ],
            ),
            topic(
                "estruturas-de-frase-complexas",
                "Estruturas de frase complexas",
                """
# Estruturas de frase complexas

Frases **complexas** têm mais de uma oração, ligadas por conectivos.

## Concessão e contraste

```
although / even though      embora
whereas / while             enquanto (contraste)
however                     porém
```

```
Although he was tired, he finished the work.   Embora cansado, ele terminou o trabalho.
She likes tea, whereas he prefers coffee.      Ela gosta de chá, enquanto ele prefere café.
```

## Causa e consequência

```
because / since     porque
therefore           portanto
as a result         como resultado
```

> 💡 **although/even though** + oração ("although he was tired"); **however**
> + oração nova ("He was tired. However, he finished the work").
""",
                [
                    ex("quiz", "O que 'although' introduz?",
                       "uma concessão (embora)", ["uma concessão (embora)", "uma causa", "uma conclusão"]),
                    ex("quiz", "O que 'whereas' significa?",
                       "enquanto (em contraste)", ["enquanto (em contraste)", "porque", "então"]),
                    ex("text", "Traduza: Embora estivesse cansado, ele terminou o trabalho.",
                       "although he was tired he finished the work"),
                    ex("quiz", "Uma frase complexa tem:",
                       "mais de uma oração", ["mais de uma oração", "só um verbo", "nenhum verbo"]),
                    ex("audio", "Escute e transcreva:",
                       "even though it was raining we went out", audio_text="Even though it was raining, we went out."),
                    ex("quiz", "Qual é um bom conectivo de CONTRASTE?",
                       "whereas", ["whereas", "therefore", "moreover"]),
                ],
            ),
        ],
    )


# ============================================================
# MODULO 13 - Vocabulario Avancado - B2
# ============================================================

def build_modulo_13_vocabulario_b2():
    return module(
        "modulo-13-vocabulario-b2",
        "Módulo 13 — Vocabulário Avançado — B2",
        "Precisão e naturalidade: collocations, phrasal verbs, expressões idiomáticas, sinônimos, antônimos, formação de palavras, prefixos, sufixos, vocabulário acadêmico e profissional, e registro formal e informal.",
        [
            topic(
                "collocations",
                "Collocations",
                """
# Collocations

**Collocations** são combinações de palavras que "andam juntas" em inglês.
Aprender a combinação certa é o que dá naturalidade.

## As mais importantes

```
make a decision     tomar uma decisão
make a mistake      cometer um erro
do your homework    fazer o dever de casa
heavy rain          chuva forte
strong coffee       café forte
fast food           comida rápida
```

> ⚠️ Não traduza "fazer" direto: é **make a decision**, mas **do your
> homework**. Fazer a combinação errada soa estranho para o nativo.
""",
                [
                    ex("quiz", "Qual é a collocation certa com 'a decision'?",
                       "make", ["make", "do", "have"]),
                    ex("quiz", "Com 'your homework', usamos:",
                       "do", ["do", "make", "get"]),
                    ex("text", "Complete: 'I need to ___ a choice.' (fazer)",
                       "make"),
                    ex("quiz", "Chuva FORTE em inglês é:",
                       "heavy rain", ["heavy rain", "strong rain", "big rain"]),
                    ex("audio", "Escute e transcreva:",
                       "i made a mistake", audio_text="I made a mistake."),
                    ex("quiz", "Café FORTE em inglês é:",
                       "strong coffee", ["strong coffee", "heavy coffee", "big coffee"]),
                ],
            ),
            topic(
                "phrasal-verbs-avancados",
                "Phrasal verbs avançados",
                """
# Phrasal verbs avançados

Ampliando os phrasal verbs do B1 (Módulo 8).

| Phrasal verb | Significado |
|---|---|
| come across | encontrar por acaso |
| run out of | ficar sem |
| put off | adiar |
| carry on | continuar |
| get along with | dar-se bem com |
| look forward to | ansioso para |

## Exemplos

```
We ran out of time.                  Ficamos sem tempo.
I came across an old photo.          Encontrei uma foto antiga por acaso.
I'm looking forward to seeing you.   Estou ansioso para te ver.
```

> 💡 **look forward to** sempre seguido de gerúndio: "looking forward to
> seeing", nunca "to see".
""",
                [
                    ex("quiz", "O que 'come across' significa?",
                       "encontrar por acaso", ["encontrar por acaso", "perder", "esquecer"]),
                    ex("quiz", "O que 'run out of' significa?",
                       "ficar sem", ["ficar sem", "terminar com sucesso", "encontrar"]),
                    ex("text", "Traduza: Estou ansioso para te ver.",
                       "i am looking forward to seeing you"),
                    ex("quiz", "O que 'put off' significa?",
                       "adiar", ["adiar", "acelerar", "cancelar"]),
                    ex("audio", "Escute e transcreva:",
                       "we ran out of time", audio_text="We ran out of time."),
                    ex("quiz", "O que 'get along with' significa?",
                       "dar-se bem com", ["dar-se bem com", "ficar bravo com", "correr atrás de"]),
                ],
            ),
            topic(
                "expressoes-idiomaticas",
                "Expressões idiomáticas (idioms)",
                """
# Expressões idiomáticas (idioms)

**Idioms** têm sentido figurado — não traduza palavra por palavra!

| Idiom | Significado |
|---|---|
| piece of cake | algo muito fácil |
| break a leg | boa sorte |
| hit the books | estudar muito |
| under the weather | doente / indisposto |
| once in a blue moon | raramente |

## Exemplos

```
The test was a piece of cake.       A prova foi muito fácil.
I'm feeling under the weather.      Estou me sentindo mal.
```

> 💡 **break a leg** não é "quebre a perna" — é como os atores dizem "boa
> sorte" antes de um show.
""",
                [
                    ex("quiz", "O que 'piece of cake' significa?",
                       "algo muito fácil", ["algo muito fácil", "algo delicioso", "um pedaço de bolo literal"]),
                    ex("quiz", "O que 'break a leg' significa?",
                       "boa sorte", ["boa sorte", "quebrar a perna", "desculpe"]),
                    ex("text", "Complete: 'I'm feeling ___ the weather today.' (doente)",
                       "under"),
                    ex("quiz", "O que 'once in a blue moon' significa?",
                       "raramente", ["raramente", "sempre", "nunca"]),
                    ex("audio", "Escute e transcreva:",
                       "the test was a piece of cake", audio_text="The test was a piece of cake."),
                    ex("quiz", "O que 'hit the books' significa?",
                       "estudar muito", ["estudar muito", "bater nos livros literalmente", "desistir"]),
                ],
            ),
            topic(
                "sinonimos",
                "Sinônimos",
                """
# Sinônimos

Ampliar sinônimos deixa o vocabulário mais rico e evita repetição.

| Comum | Sinônimo |
|---|---|
| big | large |
| happy | glad |
| important | essential |
| buy | purchase |
| start | begin |
| smart | intelligent |

## Exemplos

```
It is an important decision.   =  It is an essential decision.
She is a smart student.        =  She is an intelligent student.
```

> 💡 **purchase** é a versão formal de **buy**. Escolher o registro certo é
> parte do nível B2.
""",
                [
                    ex("quiz", "Um sinônimo de 'big' é:",
                       "large", ["large", "small", "tiny"]),
                    ex("quiz", "Um sinônimo de 'happy' é:",
                       "glad", ["glad", "sad", "angry"]),
                    ex("text", "Escreva um sinônimo de 'start'.",
                       "begin"),
                    ex("quiz", "A versão mais formal de 'buy' é:",
                       "purchase", ["purchase", "sell", "pay"]),
                    ex("audio", "Escute e transcreva:",
                       "it is an important decision", audio_text="It is an important decision."),
                    ex("quiz", "Um sinônimo de 'important' é:",
                       "essential", ["essential", "useless", "minor"]),
                ],
            ),
            topic(
                "antonimos",
                "Antônimos",
                """
# Antônimos

Os **antônimos** são opostos — úteis para descrever contrastes.

| Palavra | Antônimo |
|---|---|
| strong | weak |
| expensive | cheap |
| always | never |
| increase | decrease |
| fail | pass |
| happy | sad |

## Exemplos

```
The opposite of happy is sad.       O oposto de feliz é triste.
Sales increased, then decreased.    As vendas aumentaram e depois caíram.
```

> 💡 Formar pares de antônimos ajuda a memorizar os dois de uma vez:
> strong/weak, cheap/expensive, increase/decrease.
""",
                [
                    ex("quiz", "O antônimo de 'strong' é:",
                       "weak", ["weak", "powerful", "heavy"]),
                    ex("quiz", "O antônimo de 'expensive' é:",
                       "cheap", ["cheap", "costly", "valuable"]),
                    ex("text", "Escreva o antônimo de 'always'.",
                       "never"),
                    ex("quiz", "O antônimo de 'increase' é:",
                       "decrease", ["decrease", "grow", "rise"]),
                    ex("audio", "Escute e transcreva:",
                       "the opposite of happy is sad", audio_text="The opposite of happy is sad."),
                    ex("quiz", "O antônimo de 'fail' é:",
                       "pass", ["pass", "lose", "miss"]),
                ],
            ),
            topic(
                "formacao-de-palavras",
                "Formação de palavras",
                """
# Formação de palavras

Palavras vêm em **famílias**: verbo, substantivo, adjetivo e advérbio da
mesma raiz.

## A família de "care"

```
care (verbo/substantivo)  ->  careful (adjetivo)  ->  carefully (advérbio)
```

## Outras famílias

```
act -> action -> active -> actively
beauty -> beautiful
succeed -> success -> successful -> successfully
```

## Por que importa?

Conhecer a família ajuda a **adivinhar** o sentido de palavras novas: se você
sabe que "-ful" forma adjetivo, "hopeful" faz sentido.

> 💡 Ao aprender uma palavra, aprenda a família toda: `decide - decision -
> decisive`.
""",
                [
                    ex("quiz", "A família de 'care' — o ADVÉRBIO é:",
                       "carefully", ["carefully", "careful", "careless"]),
                    ex("quiz", "De 'act', o SUBSTANTIVO é:",
                       "action", ["action", "active", "actively"]),
                    ex("text", "Escreva o adjetivo de 'beauty'.",
                       "beautiful"),
                    ex("quiz", "De 'possible', o SUBSTANTIVO é:",
                       "possibility", ["possibility", "possibly", "possible"]),
                    ex("audio", "Escute e transcreva:",
                       "she is a successful writer", audio_text="She is a successful writer."),
                    ex("quiz", "Conhecer famílias de palavras ajuda a:",
                       "adivinhar o sentido de palavras novas", ["adivinhar o sentido de palavras novas", "decorar mais rápido", "ignorar prefixos"]),
                ],
            ),
            topic(
                "prefixos",
                "Prefixos",
                """
# Prefixos

**Prefixos** vêm antes da palavra e mudam (ou invertem) o sentido.

## Prefixos de oposição

```
un-   happy -> unhappy    (infeliz)
in-/im-  possible -> impossible
dis-  appear -> disappear
```

## Prefixos de repetição e erro

```
re-   read -> reread      (relê)
mis-  understand -> misunderstand   (entender errado)
```

## Outros

```
pre-  before: preview     (prévia)
over-  more than: overwork (trabalho demais)
```

> 💡 **re-** = de novo (rewrite, rebuild); **mis-** = errado (misspell);
> **un-/in-/im-/dis-** = oposição.
""",
                [
                    ex("quiz", "O prefixo 'un-' forma o oposto de 'happy':",
                       "unhappy", ["unhappy", "rehappy", "prehappy"]),
                    ex("quiz", "O prefixo que significa 'fazer de novo' é:",
                       "re-", ["re-", "un-", "mis-"]),
                    ex("text", "Forme o oposto de 'possible' com um prefixo.",
                       "impossible"),
                    ex("quiz", "O prefixo 'mis-' indica:",
                       "erro (errado)", ["erro (errado)", "repetição", "oposição"]),
                    ex("audio", "Escute e transcreva:",
                       "please reread the instructions", audio_text="Please reread the instructions."),
                    ex("quiz", "O oposto de 'appear' é:",
                       "disappear", ["disappear", "reappear", "misappear"]),
                ],
            ),
            topic(
                "sufixos",
                "Sufixos",
                """
# Sufixos

**Sufixos** vêm depois da palavra e costumam indicar a classe gramatical.

## Sufixos comuns

```
-ful   cheio de: help -> helpful
-less  sem: care -> careless
-er/-or  pessoa que faz: teach -> teacher
-ness  substantivo de qualidade: happy -> happiness
-tion/-ment  substantivo de ação: decide -> decision, agree -> agreement
-ly    advérbio: quick -> quickly
```

> 💡 Sabendo o sufixo, você reconhece a classe: **-ness/-tion/-ment** =
> substantivo; **-ful/-less** = adjetivo; **-ly** = advérbio.
""",
                [
                    ex("quiz", "O sufixo '-ful' em 'helpful' significa:",
                       "cheio de (que ajuda)", ["cheio de (que ajuda)", "sem", "ação"]),
                    ex("quiz", "O sufixo '-less' em 'careless' significa:",
                       "sem (descuido)", ["sem (descuido)", "cheio de", "pessoa que"]),
                    ex("text", "Forme o adjetivo de 'hope' com '-ful'.",
                       "hopeful"),
                    ex("quiz", "O sufixo '-er' em 'teacher' indica:",
                       "pessoa que faz a ação", ["pessoa que faz a ação", "lugar", "tempo"]),
                    ex("audio", "Escute e transcreva:",
                       "she is a careful driver", audio_text="She is a careful driver."),
                    ex("quiz", "O sufixo '-ness' forma:",
                       "substantivos (happiness)", ["substantivos (happiness)", "adjetivos", "advérbios"]),
                ],
            ),
            topic(
                "vocabulario-academico",
                "Vocabulário acadêmico",
                """
# Vocabulário acadêmico

Palavras-chave para ler e escrever em contextos acadêmicos.

| Inglês | Português |
|---|---|
| analyze | analisar |
| significant | significativo |
| evidence | evidência |
| hypothesis | hipótese |
| conclusion | conclusão |
| approach | abordagem |
| data | dados |
| theory | teoria |

## Exemplos

```
The conclusion of the study is clear.   A conclusão do estudo é clara.
The data supports the theory.           Os dados apoiam a teoria.
```

> 💡 **data** é incontável em inglês acadêmico: "The data is..." (não "are").
""",
                [
                    ex("quiz", "Como se diz 'analisar' em inglês?",
                       "analyze", ["analyze", "summarize", "ignore"]),
                    ex("quiz", "Como se diz 'significativo' em inglês?",
                       "significant", ["significant", "small", "common"]),
                    ex("text", "Traduza: A conclusão do estudo é clara.",
                       "the conclusion of the study is clear"),
                    ex("quiz", "Como se diz 'abordagem' em inglês?",
                       "approach", ["approach", "conclusion", "evidence"]),
                    ex("audio", "Escute e transcreva:",
                       "the data supports the theory", audio_text="The data supports the theory."),
                    ex("quiz", "Como se diz 'hipótese' em inglês?",
                       "hypothesis", ["hypothesis", "result", "question"]),
                ],
            ),
            topic(
                "vocabulario-profissional",
                "Vocabulário profissional",
                """
# Vocabulário profissional

| Inglês | Português |
|---|---|
| stakeholder | parte interessada |
| deliverables | entregáveis |
| to implement | implementar |
| to negotiate | negociar |
| agenda | pauta da reunião |
| feedback | retorno / avaliação |
| strategy | estratégia |
| contract | contrato |

## Exemplos

```
Let's negotiate the contract.      Vamos negociar o contrato.
The feedback was very useful.      O retorno foi muito útil.
```

> 💡 **agenda** = pauta (não "agenda de contatos" — para isso é
> **schedule** ou **calendar**).
""",
                [
                    ex("quiz", "Como se diz 'entregáveis' (do projeto) em inglês?",
                       "deliverables", ["deliverables", "stakeholders", "agenda"]),
                    ex("quiz", "Como se diz 'implementar' em inglês?",
                       "implement", ["implement", "delete", "review"]),
                    ex("text", "Traduza: Vamos negociar o contrato.",
                       "let's negotiate the contract"),
                    ex("quiz", "Quem são os 'stakeholders'?",
                       "as partes interessadas", ["as partes interessadas", "os funcionários", "os clientes"]),
                    ex("audio", "Escute e transcreva:",
                       "the feedback was very useful", audio_text="The feedback was very useful."),
                    ex("quiz", "Como se diz 'pauta da reunião' em inglês?",
                       "agenda", ["agenda", "schedule", "deadline"]),
                ],
            ),
            topic(
                "registro-formal",
                "Registro formal",
                """
# Registro formal

O registro **formal** é usado em e-mails profissionais, cartas e textos
oficiais.

## Formas formais

| Informal | Formal |
|---|---|
| I want to | I would like to |
| Also | Furthermore |
| About | Regarding |
| I'm writing to tell you | I am writing to inform you |

## Exemplos

```
I would like to schedule a meeting.     Gostaria de agendar uma reunião.
I am writing to confirm the meeting.    Escrevo para confirmar a reunião.
```

> 💡 Formal = frases completas, sem contrações ("I am" em vez de "I'm"),
> vocabulário mais neutro.
""",
                [
                    ex("quiz", "Qual é a versão formal de 'I want to'?",
                       "I would like to", ["I would like to", "I wanna", "I want"]),
                    ex("quiz", "Para iniciar um e-mail formal, use:",
                       "I am writing to...", ["I am writing to...", "Hey!", "Listen..."]),
                    ex("text", "Traduza: Gostaria de agendar uma reunião.",
                       "i would like to schedule a meeting"),
                    ex("quiz", "O que 'regarding' significa?",
                       "a respeito de", ["a respeito de", "com certeza", "apesar de"]),
                    ex("audio", "Escute e transcreva:",
                       "i am writing to confirm the meeting", audio_text="I am writing to confirm the meeting."),
                    ex("quiz", "Um sinônimo formal de 'also' é:",
                       "furthermore", ["furthermore", "plus", "anyway"]),
                ],
            ),
            topic(
                "registro-informal",
                "Registro informal",
                """
# Registro informal

O registro **informal** é o da conversa, mensagens e com amigos.

## Formas informais

| Formal | Informal |
|---|---|
| Good morning | Hey! / Hi! |
| I am going to | I'm gonna |
| How are you? | How's it going? |
| No problem | No worries |
| Goodbye | Catch you later / See ya |

## Exemplos

```
Hey! How's it going?          E aí! Como vai?
No worries!                   Sem problema!
Catch you later!              Até mais!
```

> 💡 **How's it going?** é a saudação informal mais comum — a resposta usual
> é "Pretty good" ou "Not bad".
""",
                [
                    ex("quiz", "Qual é informal?",
                       "Hey! How's it going?", ["Hey! How's it going?", "Good morning.", "I would like to..."]),
                    ex("quiz", "O que 'No worries' significa?",
                       "sem problema", ["sem problema", "não se preocupe com saúde", "de nada, sempre"]),
                    ex("text", "Traduza (informal): Até mais!",
                       "catch you later"),
                    ex("quiz", "O que 'How's it going?' significa?",
                       "como vai?", ["como vai?", "a que horas?", "onde?"]),
                    ex("audio", "Escute e transcreva:",
                       "see you later", audio_text="See you later!"),
                    ex("quiz", "Em texto informal, 'gonna' significa:",
                       "going to", ["going to", "want to", "have to"]),
                ],
            ),
        ],
    )


# ============================================================
# MODULO 14 - Ingles Natural - B2
# ============================================================

def build_modulo_14_ingles_natural_b2():
    return module(
        "modulo-14-ingles-natural-b2",
        "Módulo 14 — Inglês Natural — B2",
        "Soar como nativo: contrações naturais, fala conectada, reduções, entonação, acentuação, ritmo, preenchedores, marcadores de conversa, expressões informais, gírias, idioms e fraseado natural.",
        [
            topic(
                "contracoes-naturais",
                "Contrações naturais",
                """
# Contrações naturais

No B2, você também reconhece **contrações duplas**, muito comuns na fala.

## Contrações simples e duplas

```
they've   (they have)
I'd've    (I would have)
wouldn't've  (would not have)
there's   (there is)
```

## Na prática

```
I'd've helped you.     Eu teria ajudado você.
There's a problem.     Há um problema.
```

> 💡 **Contrações duplas** (I'd've, shouldn't've) não são usadas em texto
> formal — mas você vai ouvi-las o tempo todo em filmes, séries e conversas.
""",
                [
                    ex("quiz", "'I'd have' contraído na fala informal fica:",
                       "I'd've", ["I'd've", "I'd has", "I'd was"]),
                    ex("quiz", "'Wouldn't've' significa:",
                       "would not have", ["would not have", "would never", "want not"]),
                    ex("text", "Complete: '___ finished by now.' (they have)",
                       "they've"),
                    ex("quiz", "Contrações duplas como 'shouldn't've' aparecem:",
                       "na fala informal", ["na fala informal", "em textos legais", "nunca"]),
                    ex("audio", "Escute e transcreva:",
                       "i would have helped you", audio_text="I would have helped you."),
                    ex("quiz", "O que 'There's' contrai?",
                       "there is", ["there is", "there are", "there was"]),
                ],
            ),
            topic(
                "fala-conectada-avancada",
                "Fala conectada avançada",
                """
# Fala conectada avançada

A fala conectada (Módulo 11) tem regras que você pode reconhecer:

## Ligação consoante + vogal

```
an apple      soa como  a-napple
come in       soa como  co-min
```

## Elision (omitir um som)

```
want to  ->  wanna     (o "t" some)
going to ->  gonna
```

## Assimilação

```
Don't you  ->  Donchoo      (o "t" + "y" vira "ch")
```

> 💡 Para treinar, repita a frase **em bloco** (como um nativo fala), não
> palavra por palavra.
""",
                [
                    ex("quiz", "Em 'an apple', a ligação soa como:",
                       "a-napple", ["a-napple", "an apple bem separado", "applen"]),
                    ex("quiz", "O que é 'elision' na fala?",
                       "omitir um som", ["omitir um som", "adicionar um som", "gritar"]),
                    ex("audio", "Escute e transcreva:",
                       "i ate an apple", audio_text="I ate an apple."),
                    ex("quiz", "Em 'want to', a fala informal elide para:",
                       "wanna", ["wanna", "went to", "wanty"]),
                    ex("quiz", "Para treinar ligações, repita frases como:",
                       "turn it off em bloco", ["turn it off em bloco", "palavra por palavra", "só em silêncio"]),
                    ex("audio", "Escute e transcreva:",
                       "come in please", audio_text="Come in, please."),
                ],
            ),
            topic(
                "reducoes-naturais",
                "Reduções naturais",
                """
# Reduções naturais

As reduções informais mais comuns do inglês falado.

| Fala | Forma completa |
|---|---|
| gonna | going to |
| wanna | want to |
| gotta | have got to |
| lemme | let me |
| dunno | don't know |
| kinda / sorta | kind of / sort of |
| cuz | because |

## Exemplos

```
I dunno.                  Não sei.
Lemme think.              Deixa eu pensar.
Cuz I'm busy.             Porque estou ocupado.
```

> 💡 São da fala informal. Na escrita formal, use a forma completa.
""",
                [
                    ex("quiz", "'Dunno' significa:",
                       "don't know", ["don't know", "do know", "don't go"]),
                    ex("quiz", "'Cuz' significa:",
                       "because", ["because", "going", "want"]),
                    ex("text", "Complete: 'I ___ know.' (não sei, redução)",
                       "dunno"),
                    ex("quiz", "'Lemme' significa:",
                       "let me", ["let me", "love me", "less me"]),
                    ex("audio", "Escute e transcreva:",
                       "i don't know", audio_text="I don't know."),
                    ex("quiz", "'Sorta' significa:",
                       "sort of", ["sort of", "some of", "see you"]),
                ],
            ),
            topic(
                "entonacao",
                "Entonação",
                """
# Entonação

A **entoação** (subir ou descer a voz) muda o sentido da frase.

## Perguntas sim/não: tom sobe

```
Do you like it? ↗      Você gosta?
```

## Perguntas com wh e afirmações: tom desce

```
Where are you? ↘       Onde você está?
I'm tired. ↘           Estou cansado.
```

## O mesmo "Really?" muda de sentido

- `Really? ↗` = pergunta (sério?)
- `Really! ↘` = surpresa (sério!)
- `Really? ↗↘` = dúvida

> 💡 Treine a entonação repetindo em voz alta — o "tom" é tão parte da frase
> quanto as palavras.
""",
                [
                    ex("quiz", "Perguntas sim/não ('Do you like it?') terminam com:",
                       "tom ascendente", ["tom ascendente", "tom descendente", "tom neutro"]),
                    ex("quiz", "Perguntas com wh ('Where are you?') terminam com:",
                       "tom descendente", ["tom descendente", "tom ascendente", "grito"]),
                    ex("audio", "Escute e transcreva:",
                       "do you want some coffee", audio_text="Do you want some coffee?"),
                    ex("quiz", "A entonação descendente numa afirmação indica:",
                       "fim da frase", ["fim da frase", "dúvida", "pergunta"]),
                    ex("quiz", "Com a mesma frase, subir o tom no fim pode indicar:",
                       "pergunta ou surpresa", ["pergunta ou surpresa", "certeza", "raiva"]),
                    ex("audio", "Escute e transcreva:",
                       "where are you from", audio_text="Where are you from?"),
                ],
            ),
            topic(
                "acentuacao-stress",
                "Acentuação (stress)",
                """
# Acentuação (stress)

Cada palavra tem uma **sílaba tônica** — e a ênfase pode até mudar a classe
da palavra.

## Stress dentro da palavra

```
pho-TO-gra-pher     (fotógrafo — ênfase em "tog")
PHO-to-graph        (fotografia — ênfase em "pho")
```

## Stress muda a classe da palavra

```
REcord   (substantivo: registro)
reCORD   (verbo: registrar)
```

## Stress na frase

As palavras **de conteúdo** (substantivos, verbos) recebem ênfase; as **de
função** (the, and, to) são ditas rapidinho.

> 💡 Para treinar, ouça a palavra isolada e repita marcando a sílaba forte.
""",
                [
                    ex("quiz", "A sílaba tônica de 'photographer' está em:",
                       "tog", ["tog", "pho", "fer"]),
                    ex("quiz", "Em frases, as palavras de conteúdo (substantivos/verbos) normalmente:",
                       "recebem mais ênfase", ["recebem mais ênfase", "não têm ênfase", "somem"]),
                    ex("audio", "Escute e transcreva:",
                       "she is going to travel", audio_text="She is going to travel."),
                    ex("quiz", "'Record' (substantivo) vs 'record' (verbo):",
                       "substantivo na 1ª sílaba, verbo na 2ª", ["substantivo na 1ª sílaba, verbo na 2ª", "sempre igual", "nunca muda"]),
                    ex("quiz", "Para treinar o stress, o ideal é:",
                       "ouvir e repetir a palavra isolada", ["ouvir e repetir a palavra isolada", "só ler", "ignorar"]),
                    ex("quiz", "Mudar a sílaba tônica pode mudar:",
                       "a classe da palavra (record vs record)", ["a classe da palavra (record vs record)", "o significado nunca", "a língua"]),
                ],
            ),
            topic(
                "ritmo-da-fala",
                "Ritmo",
                """
# Ritmo

O inglês tem um ritmo **baseado em acentos** (stress-timed): as palavras
fortes batem em intervalos regulares, e as fracas "se espremem" no meio.

## Na prática

```
I WANT to GO to the STORE.
```

As palavras fortes (WANT, GO, STORE) marcam o ritmo; "I, to, to, the" são
ditas rapidinho entre elas.

## Fala real

```
I want to go  ->  I wanna go
I need to leave now.  ->  I needa leave now.
```

> 💡 O ritmo é o que dá o "balanço" do inglês. Pratique repetindo frases
> inteiras sem pausar palavra por palavra.
""",
                [
                    ex("quiz", "O ritmo do inglês é:",
                       "baseado em acentos (stress-timed)", ["baseado em acentos (stress-timed)", "baseado em sílabas iguais", "inexistente"]),
                    ex("quiz", "Palavras de função (the, and, to) na fala:",
                       "são ditas rapidinho, quase sem destaque", ["são ditas rapidinho, quase sem destaque", "são gritadas", "sempre iguais"]),
                    ex("audio", "Escute e transcreva:",
                       "the car is in the garage", audio_text="The car is in the garage."),
                    ex("quiz", "A frase 'I want to go' na fala real soa como:",
                       "I wanna go", ["I wanna go", "I want to go (bem lento)", "I goes"]),
                    ex("quiz", "Para melhorar o ritmo, pratique:",
                       "repetir frases inteiras em bloco", ["repetir frases inteiras em bloco", "palavra por palavra", "nunca falar"]),
                    ex("audio", "Escute e transcreva:",
                       "i need to leave now", audio_text="I need to leave now."),
                ],
            ),
            topic(
                "preenchedores-fillers",
                "Preenchedores naturais (fillers)",
                """
# Preenchedores naturais (fillers)

**Fillers** dão tempo para pensar e fazem a fala soar natural — todo nativo
usa.

## Os mais comuns

```
Well, ...        bom, ...
You know...      sabe...
Actually, ...    na verdade...
I mean, ...      quero dizer...
Sort of...       meio que...
```

## Exemplos

```
Well, I think it's fine.        Bom, eu acho que está tudo bem.
Actually, I disagree.           Na verdade, eu discordo.
```

> 💡 Fillers **não são erros** — são parte natural da conversa. Usar "well"
> e "actually" deixa sua fala muito mais nativa.
""",
                [
                    ex("quiz", "Para ganhar tempo ao pensar, os nativos usam:",
                       "well", ["well", "because", "therefore"]),
                    ex("quiz", "'Actually' é usado para:",
                       "corrigir ou introduzir um fato (na verdade)", ["corrigir ou introduzir um fato (na verdade)", "perguntar", "despedir"]),
                    ex("text", "Complete: '___ you know, I like it.' (bom...)",
                       "well"),
                    ex("quiz", "'You know what I mean?' serve para:",
                       "confirmar se a pessoa entendeu", ["confirmar se a pessoa entendeu", "despedir", "pedir comida"]),
                    ex("audio", "Escute e transcreva:",
                       "well i think it's fine", audio_text="Well, I think it's fine."),
                    ex("quiz", "Fillers deixam a fala:",
                       "mais natural", ["mais natural", "mais formal", "mais rápida demais"]),
                ],
            ),
            topic(
                "marcadores-de-conversa",
                "Marcadores de conversa",
                """
# Marcadores de conversa

**Marcadores** organizam a conversa: mudar de assunto, retomar, confirmar.

## Os mais comuns

```
Anyway, ...            enfim (mudando de assunto)
By the way, ...        a propósito
So, ...                então (retomando/concluindo)
Right.                 certo (confirmando)
As I was saying...     como eu estava dizendo...
```

## Exemplos

```
By the way, did you see the news?    A propósito, você viu as notícias?
So, what do you think?               Então, o que você acha?
```

> 💡 **Anyway** encerra um assunto e muda de tema. **Right!** confirma que
> você entendeu o que a pessoa disse.
""",
                [
                    ex("quiz", "Para mudar de assunto, os nativos usam:",
                       "anyway", ["anyway", "because", "therefore"]),
                    ex("quiz", "'By the way' serve para:",
                       "acrescentar algo fora do assunto", ["acrescentar algo fora do assunto", "concluir", "perguntar horas"]),
                    ex("text", "Complete: '___ as I was saying, the meeting is at 3.' (então)",
                       "so"),
                    ex("quiz", "'Right!' numa conversa confirma:",
                       "entendimento", ["entendimento", "raiva", "despedida"]),
                    ex("audio", "Escute e transcreva:",
                       "so what do you think", audio_text="So, what do you think?"),
                    ex("quiz", "Marcadores de conversa são usados para:",
                       "organizar e sinalizar a conversa", ["organizar e sinalizar a conversa", "preencher silêncio só", "decorar"]),
                ],
            ),
            topic(
                "expressoes-informais",
                "Expressões informais",
                """
# Expressões informais

| Expressão | Significado |
|---|---|
| No big deal | sem problema, não é grande coisa |
| That's cool | legal |
| Sounds good | parece ótimo |
| I'm good | estou bem (recusando algo) |
| It's up to you | a decisão é sua |
| For sure | com certeza |

## Exemplos

```
It's up to you.             A decisão é sua.
For sure!                   Com certeza!
No big deal.                Sem problema.
```

> 💡 **I'm good** respondendo a um oferecimento = "não preciso, obrigado":
> "Want more coffee?" - "I'm good, thanks."
""",
                [
                    ex("quiz", "'No big deal' significa:",
                       "sem problema, não é grande coisa", ["sem problema, não é grande coisa", "grande negócio", "cuidado"]),
                    ex("quiz", "'I'm good' (recusando algo) significa:",
                       "estou bem, não preciso", ["estou bem, não preciso", "estou ótimo", "sou bom"]),
                    ex("text", "Traduza: A decisão é sua.",
                       "it's up to you"),
                    ex("quiz", "'For sure!' significa:",
                       "com certeza", ["com certeza", "talvez", "nunca"]),
                    ex("audio", "Escute e transcreva:",
                       "it's up to you", audio_text="It's up to you."),
                    ex("quiz", "'That's cool!' significa:",
                       "legal", ["legal", "frio", "caro"]),
                ],
            ),
            topic(
                "girias-slang",
                "Gírias (slang)",
                """
# Gírias (slang)

Gírias são informais e mudam com o tempo — mas algumas são estáveis.

## As mais comuns

```
cool / awesome       legal / incrível
dude                 cara
hang out             passar tempo junto
chill                relaxar
whatever             tanto faz
no worries           sem problema
```

## Exemplos

```
Let's hang out.         Vamos sair juntos.
Just chill.             Só relaxa.
```

> 💡 Use gírias com **amigos** — em e-mails formais ou entrevistas, elas
> destoam. Saber **reconhecer** é mais importante que usar.
""",
                [
                    ex("quiz", "O que 'hang out' significa?",
                       "passar tempo junto", ["passar tempo junto", "pendurar", "trabalhar"]),
                    ex("quiz", "O que 'awesome' significa?",
                       "incrível", ["incrível", "horrível", "comum"]),
                    ex("text", "Complete: 'We usually ___ out on Saturdays.' (sair juntos)",
                       "hang"),
                    ex("quiz", "O que 'chill' (verbo) significa?",
                       "relaxar", ["relaxar", "correr", "gritar"]),
                    ex("audio", "Escute e transcreva:",
                       "let's hang out", audio_text="Let's hang out."),
                    ex("quiz", "Gírias são apropriadas em:",
                       "conversas informais entre amigos", ["conversas informais entre amigos", "e-mails formais", "entrevistas de emprego"]),
                ],
            ),
            topic(
                "idioms-comuns",
                "Idioms comuns",
                """
# Idioms comuns

| Idiom | Significado |
|---|---|
| break the ice | quebrar o gelo (iniciar conversa) |
| feel blue | estar triste |
| in the same boat | na mesma situação |
| get cold feet | ficar com medo no último momento |
| hit the sack | ir dormir |
| once in a blue moon | raramente |

## Exemplos

```
I'm feeling blue today.           Estou triste hoje.
We are in the same boat.          Estamos na mesma situação.
I think I'll hit the sack.        Acho que vou dormir.
```

> 💡 Idioms têm sentido **figurado** — não dá para traduzir palavra por
> palavra. Aprenda o idiom como um bloco só.
""",
                [
                    ex("quiz", "O que 'break the ice' significa?",
                       "quebrar o gelo (iniciar conversa)", ["quebrar o gelo (iniciar conversa)", "quebrar algo", "ficar frio"]),
                    ex("quiz", "O que 'feel blue' significa?",
                       "estar triste", ["estar triste", "estar feliz", "estar com frio"]),
                    ex("text", "Complete: 'I'm feeling ___ today.' (triste)",
                       "blue"),
                    ex("quiz", "O que 'get cold feet' significa?",
                       "ficar com medo no último momento", ["ficar com medo no último momento", "ficar com frio", "desistir sempre"]),
                    ex("audio", "Escute e transcreva:",
                       "we are in the same boat", audio_text="We are in the same boat."),
                    ex("quiz", "O que 'hit the sack' significa?",
                       "ir dormir", ["ir dormir", "bater", "trabalhar"]),
                ],
            ),
            topic(
                "fraseado-nativo",
                "Fraseado natural",
                """
# Fraseado natural (native-like)

O fraseado natural vem de aprender **blocos prontos** (chunks), não de
traduzir palavra por palavra.

## Chunks úteis

```
It's not that bad.          Não é tão ruim.
I wouldn't say that.        Eu não diria isso.  (discordância suave)
What I meant was...         O que eu quis dizer foi...
I'm not a big fan of...     Não sou muito fã de...
It depends.                 Depende.
```

## Exemplos

```
What I meant was that we need more time.   O que quis dizer é que precisamos de mais tempo.
It's not that bad, really.                 Não é tão ruim, sério.
```

> 💡 A chave do nível avançado é **pensar em blocos**: "What I meant was",
> "It's up to you", "That's not how I see it" — prontos, sem montar do zero.
""",
                [
                    ex("quiz", "Para suavizar uma discordância, diga:",
                       "I wouldn't say that.", ["I wouldn't say that.", "That's terrible.", "You're wrong."]),
                    ex("quiz", "'It's not that bad' significa:",
                       "não é tão ruim", ["não é tão ruim", "é horrível", "é ótimo"]),
                    ex("text", "Traduza: O que eu quis dizer foi...",
                       "what i meant was"),
                    ex("quiz", "Para parecer nativo, use:",
                       "blocos prontos (chunks) e collocations", ["blocos prontos (chunks) e collocations", "tradução palavra por palavra", "palavras soltas"]),
                    ex("audio", "Escute e transcreva:",
                       "it's not that bad really", audio_text="It's not that bad, really."),
                    ex("quiz", "A chave do fraseado natural é:",
                       "aprender blocos prontos", ["aprender blocos prontos", "gramática isolada", "só vocabulário"]),
                ],
            ),
        ],
    )


# ============================================================
# MODULO 15 - Speaking - B2
# ============================================================

def build_modulo_15_speaking_b2():
    return module(
        "modulo-15-speaking-b2",
        "Módulo 15 — Speaking — B2",
        "Falar com precisão e persuasão: debates, apresentações, discussões, negociações, explicações complexas, defesa e contestação de argumentos, exemplos, especulação, hipóteses, persuasão e esclarecimento de mal-entendidos.",
        [
            topic(
                "debates",
                "Debates",
                """
# Debates

No debate, você precisa estruturar argumentos e responder ao outro com
educação.

## Frases úteis

```
I'd like to argue that...        Gostaria de argumentar que...
That's a valid point, but...     É um ponto válido, mas...
Let me clarify...                Deixe-me esclarecer...
I'd like to respond to that.     Gostaria de responder a isso.
```

> 💡 Num debate, o oponente NÃO é inimigo: reconheça o ponto válido dele
> ("That's a valid point") antes de contrapor — isso torna seu argumento
> mais forte.
""",
                [
                    ex("quiz", "Para iniciar um argumento num debate:",
                       "I'd like to argue that...", ["I'd like to argue that...", "Let's go.", "I'm tired."]),
                    ex("quiz", "Para reconhecer o ponto do outro e contrapor:",
                       "That's a valid point, but...", ["That's a valid point, but...", "You're wrong.", "Silence."]),
                    ex("text", "Traduza: Gostaria de responder a isso.",
                       "i would like to respond to that"),
                    ex("audio", "Escute e transcreva:",
                       "that is a valid point but i disagree", audio_text="That is a valid point, but I disagree."),
                    ex("quiz", "Num debate, 'Let me clarify' serve para:",
                       "esclarecer o que quis dizer", ["esclarecer o que quis dizer", "desistir", "mudar de assunto"]),
                    ex("quiz", "Qual frase estrutura um debate com educação?",
                       "I see your point, however...", ["I see your point, however...", "You are totally wrong.", "Stop talking."]),
                ],
            ),
            topic(
                "apresentacoes-orais",
                "Apresentações",
                """
# Apresentações

Uma apresentação tem começo, meio e fim claros — com frases que sinalizam
cada parte.

## Começo, meio e fim

```
Good morning everyone, I'd like to start by...   Bom dia a todos, gostaria de começar por...
Let's move on to...                              Vamos passar para...
To sum up, ...                                   Para resumir, ...
Thank you for your attention.                    Obrigado pela atenção.
```

## Exemplo de estrutura

```
First, I'd like to introduce the topic.
Then, I'll show the data.
In conclusion, I'll share my opinion.
```

> 💡 Sinalize a estrutura: "First... Then... Finally..." — o público sempre
> sabe onde você está.
""",
                [
                    ex("quiz", "Para COMEÇAR uma apresentação:",
                       "Good morning everyone, I'd like to start by...", ["Good morning everyone, I'd like to start by...", "Hey, let's begin.", "Bye."]),
                    ex("quiz", "Para passar para a próxima parte:",
                       "Let's move on to...", ["Let's move on to...", "I'm done.", "Wait here."]),
                    ex("text", "Traduza: Para resumir...",
                       "to sum up"),
                    ex("audio", "Escute e transcreva:",
                       "thank you for your attention", audio_text="Thank you for your attention."),
                    ex("quiz", "Para ENCERRAR uma apresentação:",
                       "In conclusion, ...", ["In conclusion, ...", "Let's start.", "Goodbye forever."]),
                    ex("quiz", "Qual frase sinaliza a estrutura da apresentação?",
                       "First, I'd like to introduce...", ["First, I'd like to introduce...", "I like pizza.", "What time is it?"]),
                ],
            ),
            topic(
                "discussoes",
                "Discussões",
                """
# Discussões

Numa discussão produtiva, você pergunta a opinião dos outros e organiza as
ideias.

## Frases úteis

```
What's your take on this?        Qual é a sua opinião sobre isso?
I'd like to hear your opinion.   Gostaria de ouvir sua opinião.
Let's weigh the pros and cons.   Vamos pesar os prós e contras.
Let's discuss this.              Vamos discutir isso.
```

> 💡 **take** aqui significa "opinião": "What's your take on it?" = "O que
> você acha?". **Pros and cons** = pontos a favor e contra.
""",
                [
                    ex("quiz", "Para pedir a opinião de alguém:",
                       "What's your take on this?", ["What's your take on this?", "Tell me the answer.", "Stop."]),
                    ex("quiz", "O que 'pros and cons' significa?",
                       "prós e contras", ["prós e contras", "prós e prós", "contras e nada"]),
                    ex("text", "Traduza: Vamos discutir isso.",
                       "let's discuss this"),
                    ex("audio", "Escute e transcreva:",
                       "what is your take on the plan", audio_text="What is your take on the plan?"),
                    ex("quiz", "Para estruturar uma discussão:",
                       "Let's weigh the pros and cons.", ["Let's weigh the pros and cons.", "It doesn't matter.", "Whatever."]),
                    ex("quiz", "Em uma discussão, 'I'd like to hear your opinion' é:",
                       "um convite ao diálogo", ["um convite ao diálogo", "uma ordem", "uma despedida"]),
                ],
            ),
            topic(
                "negociacoes",
                "Negociações",
                """
# Negociações

Negociar é buscar um meio-termo em que os dois lados ganham.

## Frases úteis

```
Let's find a middle ground.          Vamos encontrar um meio-termo.
I'm willing to compromise.           Estou disposto a ceder.
What would it take to close the deal?   O que seria preciso para fechar o acordo?
Can we make a deal?                  Podemos fazer um acordo?
```

> 💡 **middle ground** = meio-termo; **compromise** = ceder/meio-termo;
> **close the deal** = fechar o negócio.
""",
                [
                    ex("quiz", "Para propor um acordo:",
                       "Let's find a middle ground.", ["Let's find a middle ground.", "Give me everything.", "No deal ever."]),
                    ex("quiz", "O que 'compromise' significa?",
                       "acordo/meio-termo", ["acordo/meio-termo", "competição", "recusa"]),
                    ex("text", "Traduza: Estou disposto a ceder.",
                       "i am willing to compromise"),
                    ex("audio", "Escute e transcreva:",
                       "can we make a deal", audio_text="Can we make a deal?"),
                    ex("quiz", "Para perguntar a condição do outro:",
                       "What would it take to close the deal?", ["What would it take to close the deal?", "It's my way or nothing.", "Never."]),
                    ex("quiz", "Numa negociação, um bom começo é:",
                       "Let's discuss the terms.", ["Let's discuss the terms.", "I want everything.", "Goodbye."]),
                ],
            ),
            topic(
                "explicando-ideias-complexas",
                "Explicando ideias complexas",
                """
# Explicando ideias complexas

Explicar algo difícil de forma clara é uma marca do nível avançado.

## Frases úteis

```
To put it simply, ...        Em termos simples, ...
The key point is...          O ponto-chave é...
What this means is...        O que isso significa é...
Let me break it down.        Deixe-me decompor isso.
```

> 💡 **break it down** = dividir em partes menores. Uma boa explicação usa
> simplicidade e exemplos, não jargão.
""",
                [
                    ex("quiz", "Para simplificar uma ideia:",
                       "To put it simply, ...", ["To put it simply, ...", "It's complicated forever.", "No."]),
                    ex("quiz", "O que 'break it down' significa?",
                       "decompor em partes", ["decompor em partes", "quebrar", "terminar"]),
                    ex("text", "Traduza: O ponto-chave é...",
                       "the key point is"),
                    ex("audio", "Escute e transcreva:",
                       "let me break it down for you", audio_text="Let me break it down for you."),
                    ex("quiz", "Para reafirmar o sentido:",
                       "What this means is...", ["What this means is...", "What time is it?", "See you."]),
                    ex("quiz", "Explicar ideia complexa para um leigo exige:",
                       "simplicidade e exemplos", ["simplicidade e exemplos", "jargão máximo", "gritar"]),
                ],
            ),
            topic(
                "defendendo-uma-opiniao",
                "Defendendo uma opinião",
                """
# Defendendo uma opinião

Defender sua posição exige postura e evidência.

## Frases úteis

```
I stand by my opinion.          Mantenho minha opinião.
Let me justify that.            Deixe-me justificar isso.
I have reasons to believe that. Tenho razões para acreditar nisso.
Evidence shows that...          A evidência mostra que...
```

> 💡 **stand by** = manter-se firme. Defesa forte combina convicção
> ("I stand by...") com lógica ("Evidence shows...").
""",
                [
                    ex("quiz", "Para defender sua opinião:",
                       "I stand by my opinion.", ["I stand by my opinion.", "I don't care.", "Maybe."]),
                    ex("quiz", "Para justificar:",
                       "Let me justify that.", ["Let me justify that.", "Trust me, ok.", "Leave me alone."]),
                    ex("text", "Traduza: Tenho razões para acreditar nisso.",
                       "i have reasons to believe that"),
                    ex("audio", "Escute e transcreva:",
                       "i stand by what i said", audio_text="I stand by what I said."),
                    ex("quiz", "Para citar evidência:",
                       "Evidence shows that...", ["Evidence shows that...", "I think maybe...", "Whatever."]),
                    ex("quiz", "O que fortalece a defesa de uma opinião?",
                       "argumentos e evidência", ["argumentos e evidência", "gritar mais alto", "ignorar o outro"]),
                ],
            ),
            topic(
                "contestando-um-argumento",
                "Contestando um argumento",
                """
# Contestando um argumento

Contestar com educação é diferente de atacar a pessoa.

## Frases úteis

```
I'd like to challenge that.          Gostaria de contestar isso.
That doesn't hold up.                Isso não se sustenta.
There's a flaw in your argument.     Há uma falha no seu argumento.
That's an overgeneralization.        Isso é uma generalização exagerada.
```

> 💡 Ataque o **argumento**, não a pessoa: "There's a flaw in your argument"
> é bem mais forte (e educado) que "You're wrong".
""",
                [
                    ex("quiz", "Para contestar educadamente:",
                       "I'd like to challenge that.", ["I'd like to challenge that.", "That's a lie.", "Shut up."]),
                    ex("quiz", "O que 'there's a flaw in your argument' significa?",
                       "há uma falha no seu argumento", ["há uma falha no seu argumento", "seu argumento é perfeito", "eu concordo"]),
                    ex("text", "Traduza: Isso não se sustenta.",
                       "that doesn't hold up"),
                    ex("audio", "Escute e transcreva:",
                       "there is a flaw in your argument", audio_text="There is a flaw in your argument."),
                    ex("quiz", "O que é uma 'overgeneralization'?",
                       "generalização exagerada", ["generalização exagerada", "um fato", "uma pergunta"]),
                    ex("quiz", "Para apontar o erro do outro com educação:",
                       "I'm not sure that's accurate.", ["I'm not sure that's accurate.", "You're so wrong.", "Impossible."]),
                ],
            ),
            topic(
                "dando-exemplos",
                "Dando exemplos",
                """
# Dando exemplos

Exemplos concretizam e fortalecem qualquer argumento.

## Frases úteis

```
For instance, ...               Por exemplo, ...
Take Brazil, for example.       Pegue o Brasil, por exemplo.
A case in point is...           Um exemplo perfeito é...
...such as...                   ...tais como...
```

## Exemplo

```
Many countries, such as Brazil, have beautiful beaches.
Muitos países, como o Brasil, têm praias lindas.
```

> 💡 **for instance** é sinônimo de **for example**. **such as** lista
> exemplos dentro da própria frase.
""",
                [
                    ex("quiz", "Um sinônimo de 'for example' é:",
                       "For instance", ["For instance", "However", "Therefore"]),
                    ex("quiz", "Para introduzir um exemplo:",
                       "Take Brazil, for example.", ["Take Brazil, for example.", "Anyway.", "Finally."]),
                    ex("text", "Complete: 'Many countries, ___ as Brazil, have beaches.' (tais como)",
                       "such"),
                    ex("audio", "Escute e transcreva:",
                       "for instance the weather is great", audio_text="For instance, the weather is great."),
                    ex("quiz", "O que 'a case in point is' significa?",
                       "um exemplo perfeito é", ["um exemplo perfeito é", "não sei", "talvez"]),
                    ex("quiz", "Exemplos tornam o argumento:",
                       "mais concreto e convincente", ["mais concreto e convincente", "mais vago", "mais curto"]),
                ],
            ),
            topic(
                "especulando",
                "Especulando",
                """
# Especulando

Especular é falar de possibilidades, sem afirmar com certeza.

## Frases úteis

```
It could be that...         Pode ser que...
Perhaps...                  Talvez...
It's possible that...       É possível que...
I imagine...                Eu imagino...
```

## Exemplo

```
It could be that they are late.     Pode ser que estejam atrasados.
Perhaps it will rain.               Talvez chova.
```

> 💡 Especulação usa modais de possibilidade: **could, might, may**. Evite
> "it is definitely" quando estiver especulando!
""",
                [
                    ex("quiz", "Para especular:",
                       "It could be that...", ["It could be that...", "It is definitely...", "I know exactly."]),
                    ex("quiz", "O que 'perhaps' significa?",
                       "talvez", ["talvez", "com certeza", "nunca"]),
                    ex("text", "Complete: '___ it will rain.' (talvez)",
                       "perhaps"),
                    ex("audio", "Escute e transcreva:",
                       "it could be that they are late", audio_text="It could be that they are late."),
                    ex("quiz", "Especulação expressa:",
                       "incerteza", ["incerteza", "certeza absoluta", "ordem"]),
                    ex("quiz", "Outra forma de especular:",
                       "I imagine...", ["I imagine...", "I guarantee...", "I forbid..."]),
                ],
            ),
            topic(
                "formulando-hipoteses",
                "Formulando hipóteses",
                """
# Formulando hipóteses

Hipóteses são cenários imaginários — usam os condicionais segundo e terceiro.

## Frases úteis

```
Suppose we tried a new approach.      Suponha que tentássemos uma nova abordagem.
What would happen if we changed it?   O que aconteceria se mudássemos?
Hypothetically, ...                   Hipoteticamente, ...
If that were true, ...                Se isso fosse verdade, ...
```

> 💡 "What if...?" é o atalho para propor cenários: "What if we started
> earlier?" O condicional (Módulos 8 e 12) é a estrutura natural.
""",
                [
                    ex("quiz", "Para formular uma hipótese:",
                       "Suppose we tried a new approach.", ["Suppose we tried a new approach.", "We did it.", "It's done."]),
                    ex("quiz", "O que 'hypothetically' significa?",
                       "hipoteticamente", ["hipoteticamente", "com certeza", "hoje"]),
                    ex("text", "Complete: '___ would happen if we changed it?' (o que)",
                       "what"),
                    ex("audio", "Escute e transcreva:",
                       "if that were true we would be happy", audio_text="If that were true, we would be happy."),
                    ex("quiz", "Hipóteses usam, em geral:",
                       "o segundo/terceiro condicional", ["o segundo/terceiro condicional", "o presente simples", "o imperativo"]),
                    ex("quiz", "Para propor um cenário imaginário:",
                       "What if we...?", ["What if we...?", "We are done.", "No way."]),
                ],
            ),
            topic(
                "persuadindo",
                "Persuadindo",
                """
# Persuadindo

Persuadir é convencer com lógica e apelo ao interesse do outro — não com
pressão.

## Frases úteis

```
Wouldn't you agree that...?      Você não concordaria que...?
Consider the benefits.           Considere as vantagens.
This is in your best interest.   Isso é do seu interesse.
Don't you think this makes sense?   Você não acha que isso faz sentido?
```

> 💡 Persuadir de verdade responde a pergunta: "o que a outra pessoa ganha
> com isso?". Apelo ao interesse do outro > imposição.
""",
                [
                    ex("quiz", "Para persuadir com uma pergunta:",
                       "Wouldn't you agree that...?", ["Wouldn't you agree that...?", "Agree or else.", "Do it now."]),
                    ex("quiz", "Para destacar vantagens:",
                       "Consider the benefits.", ["Consider the benefits.", "Ignore everything.", "Too bad."]),
                    ex("text", "Traduza: Isso é do seu interesse.",
                       "this is in your best interest"),
                    ex("audio", "Escute e transcreva:",
                       "i am sure you can see the advantages", audio_text="I am sure you can see the advantages."),
                    ex("quiz", "Persuasão eficaz apela:",
                       "à lógica e ao interesse do outro", ["à lógica e ao interesse do outro", "só ao grito", "à ameaça"]),
                    ex("quiz", "Para envolver a pessoa:",
                       "Don't you think this makes sense?", ["Don't you think this makes sense?", "Trust me blindly.", "Whatever."]),
                ],
            ),
            topic(
                "esclarecendo-mal-entendidos",
                "Esclarecendo mal-entendidos",
                """
# Esclarecendo mal-entendidos

Quando algo é entendido errado, esclareça com calma e clareza.

## Frases úteis

```
That's not what I meant.            Não foi isso que quis dizer.
Let me clarify...                   Deixe-me esclarecer...
I think there's a misunderstanding. Acho que houve um mal-entendido.
What I meant to say was...          O que eu quis dizer foi...
```

> 💡 A pior atitude num mal-entendido é reagir na hora com raiva. Esclareça
> primeiro: "Let me clarify what I said."
""",
                [
                    ex("quiz", "Para corrigir um mal-entendido:",
                       "That's not what I meant.", ["That's not what I meant.", "You're crazy.", "Bye."]),
                    ex("quiz", "O que 'misunderstanding' significa?",
                       "mal-entendido", ["mal-entendido", "acordo", "surpresa"]),
                    ex("text", "Traduza: Acho que houve um mal-entendido.",
                       "i think there is a misunderstanding"),
                    ex("audio", "Escute e transcreva:",
                       "let me clarify what i said", audio_text="Let me clarify what I said."),
                    ex("quiz", "Para reformular o que disse:",
                       "What I meant to say was...", ["What I meant to say was...", "Never mind.", "Whatever."]),
                    ex("quiz", "A melhor atitude num mal-entendido:",
                       "esclarecer com calma", ["esclarecer com calma", "gritar", "ir embora"]),
                ],
            ),
        ],
    )


# ============================================================
# MODULO 16 - Writing - B2
# ============================================================

def build_modulo_16_writing_b2():
    return module(
        "modulo-16-writing-b2",
        "Módulo 16 — Writing — B2",
        "Escrever com estrutura e propósito: e-mails formais e informais, relatórios, redações, argumentação, resenhas, resumos, propostas, comunicação profissional e escrita acadêmica.",
        [
            topic(
                "emails-formais",
                "E-mails formais",
                """
# E-mails formais

O e-mail formal tem estrutura fixa: saudação, abertura, corpo, fechamento.

## Estrutura

```
Subject: Meeting request

Dear Sir or Madam,

I am writing to request a meeting next week.
I would appreciate it if you could confirm.

I look forward to your reply.

Yours sincerely,
Ana
```

## Frases-chave

```
I am writing to...          Escrevo para...
I would appreciate...       Agradeceria se...
I look forward to your reply.   Aguardo sua resposta.
```

> 💡 Em e-mail formal, evite contrações ("I am", não "I'm") e gírias.
""",
                [
                    ex("quiz", "A saudação formal para alguém desconhecido é:",
                       "Dear Sir or Madam,", ["Dear Sir or Madam,", "Hey!", "Hi there,"]),
                    ex("quiz", "Para abrir um e-mail formal:",
                       "I am writing to...", ["I am writing to...", "Wanna tell you...", "Listen,"]),
                    ex("text", "Complete: 'I would ___ it if you could reply soon.' (agradecer)",
                       "appreciate"),
                    ex("audio", "Escute e transcreva:",
                       "i look forward to your reply", audio_text="I look forward to your reply."),
                    ex("quiz", "O fechamento formal 'Yours sincerely' acompanha:",
                       "um e-mail formal", ["um e-mail formal", "um texto informal", "uma mensagem de WhatsApp"]),
                    ex("quiz", "Em e-mail formal, evite:",
                       "contrações e gírias", ["contrações e gírias", "frases completas", "vocabulário polido"]),
                ],
            ),
            topic(
                "emails-informais",
                "E-mails informais",
                """
# E-mails informais

E-mail para amigos é mais solto, mas ainda organizado.

## Estrutura

```
Subject: About Saturday

Hi Anna,

Hope you're well!
Just letting you know I'll be late.

Talk to you soon!

Best,
Ana
```

## Frases-chave

```
Hope you're well!        Espero que esteja bem!
Just letting you know... Só te avisando...
Talk to you soon!        Falamos logo!
```

> 💡 Em e-mail informal, contrações e expressões amigáveis são normais — é o
> oposto do formal.
""",
                [
                    ex("quiz", "A abertura de e-mail INFORMAL é:",
                       "Hi Anna!", ["Hi Anna!", "Dear Sir or Madam,", "To whom it may concern,"]),
                    ex("quiz", "Para avisar algo casualmente:",
                       "Just letting you know...", ["Just letting you know...", "I am writing to formally inform...", "Kindly note..."]),
                    ex("text", "Complete: 'Hope you're ___!' (bem)",
                       "well"),
                    ex("audio", "Escute e transcreva:",
                       "talk to you soon", audio_text="Talk to you soon!"),
                    ex("quiz", "O fechamento INFORMAL é:",
                       "Best, Ana", ["Best, Ana", "Yours faithfully,", "Sincerely,"]),
                    ex("quiz", "E-mail informal permite:",
                       "contrações e expressões amigáveis", ["contrações e expressões amigáveis", "jargão jurídico", "só formalidade"]),
                ],
            ),
            topic(
                "relatorios",
                "Relatórios",
                """
# Relatórios

Um relatório formal tem seções claras e tom neutro.

## Estrutura

```
1. Introduction      (objetivo)
2. Findings          (resultados/dados)
3. Conclusion        (conclusão)
4. Recommendation    (recomendação)
```

## Frases úteis

```
The data shows that...        Os dados mostram que...
The findings indicate...      Os resultados indicam...
In conclusion, ...            Em conclusão, ...
It is recommended that...     Recomenda-se que...
```

> 💡 Relatório formal usa voz passiva e tom impessoal: "It is recommended
> that..." em vez de "I think you should...".
""",
                [
                    ex("quiz", "A seção que apresenta os RESULTADOS é:",
                       "Findings", ["Findings", "Introduction", "Recommendation"]),
                    ex("quiz", "Para citar números num relatório:",
                       "The data shows...", ["The data shows...", "I guess...", "Maybe..."]),
                    ex("text", "Complete: 'In ___ , the results are positive.' (conclusão)",
                       "conclusion"),
                    ex("audio", "Escute e transcreva:",
                       "the findings show a clear trend", audio_text="The findings show a clear trend."),
                    ex("quiz", "A seção que SUGERE o que fazer é:",
                       "Recommendation", ["Recommendation", "Introduction", "Summary"]),
                    ex("quiz", "Relatório formal usa:",
                       "voz passiva e tom neutro", ["voz passiva e tom neutro", "gírias", "emojis"]),
                ],
            ),
            topic(
                "redacoes-essays",
                "Redações (essays)",
                """
# Redações (essays)

Um essay tem introdução (com tese), parágrafos de desenvolvimento e
conclusão.

## Estrutura

```
Introdução:  apresenta o tema + tese
Corpo:       1 ideia principal por parágrafo
Conclusão:   retoma e sintetiza
```

## Frases úteis

```
This essay will discuss...          Este texto vai discutir...
Moreover, ... / However, ...        Além disso, ... / Porém, ...
In conclusion, I believe that...    Em conclusão, acredito que...
```

> 💡 Uma boa **thesis statement** (tese) é específica e defensável — não
> vaga ("Things are good") nem uma pergunta.
""",
                [
                    ex("quiz", "A introdução de um essay deve ter:",
                       "uma tese (thesis statement)", ["uma tese (thesis statement)", "só uma piada", "só a conclusão"]),
                    ex("quiz", "Cada parágrafo do corpo deve ter:",
                       "uma ideia principal", ["uma ideia principal", "várias ideias soltas", "nenhuma"]),
                    ex("text", "Complete: 'In ___ , I believe that...' (conclusão)",
                       "conclusion"),
                    ex("audio", "Escute e transcreva:",
                       "this essay will discuss two main points", audio_text="This essay will discuss two main points."),
                    ex("quiz", "Para ligar parágrafos, use:",
                       "Moreover e However", ["Moreover e However", "nada", "emojis"]),
                    ex("quiz", "Uma boa tese é:",
                       "específica e defensável", ["específica e defensável", "vaga", "uma pergunta"]),
                ],
            ),
            topic(
                "argumentacao-escrita",
                "Argumentação",
                """
# Argumentação

Um texto argumentativo combina **afirmação** (claim) + **evidência** +
consideração do **contra-argumento**.

## Estrutura de um parágrafo argumentativo

```
Claim:      This is the best solution.
Evidence:   The data shows a 20% improvement.
Counter:    Some may argue that it is expensive.
Concession: While that is true, the long-term gain is bigger.
```

## Frases úteis

```
Some may argue that...        Alguns podem argumentar que...
While it is true that...      Embora seja verdade que...
Based on the evidence...      Com base na evidência...
```

> 💡 Reconhecer o contra-argumento ("Some may argue...") mostra maturidade —
> e torna sua posição mais forte.
""",
                [
                    ex("quiz", "O que é uma 'claim'?",
                       "uma afirmação/posição", ["uma afirmação/posição", "um exemplo", "um erro"]),
                    ex("quiz", "Para apresentar o contra-argumento:",
                       "Some may argue that...", ["Some may argue that...", "It is done.", "No."]),
                    ex("text", "Complete: '___ on the evidence, the conclusion is clear.' (com base)",
                       "based"),
                    ex("audio", "Escute e transcreva:",
                       "some may argue that it is too expensive", audio_text="Some may argue that it is too expensive."),
                    ex("quiz", "Para conceder um ponto antes de contrapor:",
                       "While it is true that..., ...", ["While it is true that..., ...", "It is false.", "Whatever."]),
                    ex("quiz", "Um argumento forte combina:",
                       "afirmação + evidência", ["afirmação + evidência", "só opinião", "só emoção"]),
                ],
            ),
            topic(
                "resenhas",
                "Resenhas",
                """
# Resenhas

Uma resenha combina **resumo** + **opinião** + **recomendação**.

## Estrutura

```
Resumo breve:  do que se trata
Opinião:       o que foi bom/ruim
Recomendação:  vale a pena? para quem?
```

## Frases úteis

```
The acting is outstanding.       A atuação é excepcional.
The plot is gripping.            O enredo é envolvente.
The ending could be better.      O final poderia ser melhor.
Overall, I recommend this...     No geral, recomendo...
```

> 💡 Critique com moderação: em vez de "It's terrible", diga "The ending
> could be better" — mais útil e mais maduro.
""",
                [
                    ex("quiz", "Uma resenha deve ter:",
                       "resumo + opinião + recomendação", ["resumo + opinião + recomendação", "só a sinopse", "só a nota"]),
                    ex("quiz", "Para elogiar:",
                       "The acting is outstanding.", ["The acting is outstanding.", "It is terrible.", "I don't know."]),
                    ex("text", "Complete: 'Overall, I ___ this movie.' (recomendo)",
                       "recommend"),
                    ex("audio", "Escute e transcreva:",
                       "the plot is gripping", audio_text="The plot is gripping."),
                    ex("quiz", "Para criticar com moderação:",
                       "The ending could be better.", ["The ending could be better.", "It's garbage.", "Never watch it."]),
                    ex("quiz", "A conclusão de uma resenha costuma ter:",
                       "uma recomendação", ["uma recomendação", "um spoiler", "uma pergunta"]),
                ],
            ),
            topic(
                "resumos",
                "Resumos",
                """
# Resumos

Resumir é captar a **ideia principal** e os pontos-chave, com suas próprias
palavras (paráfrase).

## Frases úteis

```
The text discusses...        O texto discute...
The article focuses on...    O artigo foca em...
In summary, the main point is...   Em resumo, o ponto principal é...
```

## O que NÃO fazer

- Não copie trechos (use paráfrase).
- Não dê sua opinião.
- Não inclua detalhes irrelevantes.

> 💡 Parafrasear = dizer a mesma ideia com outras palavras. Se você só copia,
> não está resumindo — está colando.
""",
                [
                    ex("quiz", "Um resumo deve:",
                       "captar a ideia principal", ["captar a ideia principal", "copiar tudo", "dar opinião"]),
                    ex("quiz", "Para iniciar um resumo:",
                       "The text discusses...", ["The text discusses...", "I love this text.", "Bye."]),
                    ex("text", "Complete: 'In ___ , the main point is...' (resumo)",
                       "summary"),
                    ex("audio", "Escute e transcreva:",
                       "the article focuses on education", audio_text="The article focuses on education."),
                    ex("quiz", "Parafrasear significa:",
                       "dizer a mesma ideia com outras palavras", ["dizer a mesma ideia com outras palavras", "copiar", "traduzir palavra por palavra"]),
                    ex("quiz", "Um resumo NÃO deve incluir:",
                       "detalhes irrelevantes", ["detalhes irrelevantes", "a ideia principal", "os pontos-chave"]),
                ],
            ),
            topic(
                "propostas",
                "Propostas",
                """
# Propostas

Uma proposta formal apresenta um **plano** com objetivo, custos e
benefícios.

## Estrutura

```
Purpose:      por que a proposta?
Plan:         o que será feito
Timeline:     cronograma
Budget:       custos
Benefits:     benefícios
```

## Frases úteis

```
I propose that...              Proponho que...
This proposal aims to...       Esta proposta visa...
The goal is to...              O objetivo é...
The timeline is...             O cronograma é...
```

> 💡 Uma proposta vende uma ideia: destaque os **benefícios** para quem vai
> aprová-la.
""",
                [
                    ex("quiz", "Para propor algo:",
                       "I propose that...", ["I propose that...", "I don't care.", "Whatever."]),
                    ex("quiz", "O que a seção de 'budget' traz?",
                       "os custos", ["os custos", "a opinião", "o cronograma"]),
                    ex("text", "Complete: 'The ___ is to increase sales.' (objetivo)",
                       "goal"),
                    ex("audio", "Escute e transcreva:",
                       "this proposal aims to reduce costs", audio_text="This proposal aims to reduce costs."),
                    ex("quiz", "Uma boa proposta destaca:",
                       "os benefícios", ["os benefícios", "só os problemas", "nada"]),
                    ex("quiz", "Para falar de cronograma:",
                       "The timeline is...", ["The timeline is...", "Maybe...", "It's fine."]),
                ],
            ),
            topic(
                "comunicacao-profissional",
                "Comunicação profissional",
                """
# Comunicação profissional

A comunicação profissional (Slack, Teams, e-mail interno) é **clara**,
**concisa** e **educada**.

## Frases úteis

```
Please find attached...         Em anexo...
Let's touch base.               Vamos alinhar/entrar em contato.
Keep me posted.                 Mantenha-me informado.
Can you follow up on this?      Pode acompanhar isso?
```

## Exemplo

```
Hi, please find attached the report.
Let's touch base next week to review it.
Keep me posted on any changes.
```

> 💡 **touch base** = fazer um contato rápido para alinhar. **keep me
> posted** = me mantenha informado.
""",
                [
                    ex("quiz", "Para anexar um arquivo:",
                       "Please find attached...", ["Please find attached...", "Here is the file maybe.", "Look."]),
                    ex("quiz", "O que 'touch base' significa?",
                       "alinhar/entrar em contato", ["alinhar/entrar em contato", "tocar na base", "desligar"]),
                    ex("text", "Complete: 'Please find ___ the report.' (em anexo)",
                       "attached"),
                    ex("audio", "Escute e transcreva:",
                       "let's touch base next week", audio_text="Let's touch base next week."),
                    ex("quiz", "O que 'keep me posted' significa?",
                       "mantenha-me informado", ["mantenha-me informado", "me pague", "me esqueça"]),
                    ex("quiz", "Escrita profissional é:",
                       "clara, concisa e educada", ["clara, concisa e educada", "longa e vaga", "cheia de gírias"]),
                ],
            ),
            topic(
                "escrita-academica",
                "Fundamentos de escrita acadêmica",
                """
# Fundamentos de escrita acadêmica

Escrita acadêmica é **formal**, **impessoal** e usa **hedging** (suavização).

## Frases úteis

```
According to Smith, ...         Segundo Smith, ...
This study examines...          Este estudo examina...
It is argued that...            Argumenta-se que...
It could be argued that...      Pode-se argumentar que...
```

## Hedging: suavizar afirmações

```
Avoid:  "This proves..."
Better: "This suggests..."
```

> 💡 Na academia, evite primeira pessoa ("I think") e afirmações absolutas.
> Prefira "It could be argued that..." — é o padrão do meio.
""",
                [
                    ex("quiz", "Escrita acadêmica evita:",
                       "primeira pessoa e gírias", ["primeira pessoa e gírias", "voz passiva", "citações"]),
                    ex("quiz", "Para citar uma fonte:",
                       "According to Smith, ...", ["According to Smith, ...", "I think Smith...", "Smith says I guess"]),
                    ex("text", "Complete: 'This study ___ the effects of sleep.' (examina)",
                       "examines"),
                    ex("audio", "Escute e transcreva:",
                       "it is argued that education is essential", audio_text="It is argued that education is essential."),
                    ex("quiz", "Hedging em escrita acadêmica é:",
                       "suavizar afirmações (may, suggests)", ["suavizar afirmações (may, suggests)", "exagerar", "gritar"]),
                    ex("quiz", "Em vez de 'I think', o acadêmico escreve:",
                       "It could be argued that...", ["It could be argued that...", "I really think...", "Trust me..."]),
                ],
            ),
        ],
    )


# ============================================================
# Revisao didatica e complementos dos modulos 8 a 16
# ============================================================


def _b1_b2_lesson(title, objective, concept, examples, contrast, summary):
    example_lines = "\n".join(
        f"- **{english}** — {portuguese}"
        for english, portuguese in examples
    )
    return (
        f"# {title}\n\n"
        f"## Objetivo\n{objective.strip()}\n\n"
        f"## Conceito\n{concept.strip()}\n\n"
        f"## Exemplos traduzidos\n{example_lines}\n\n"
        f"## Contraste e erro comum\n{contrast.strip()}\n\n"
        f"## Resumo\n{summary.strip()}"
    )


def _b1_b2_exercises(
    text_prompt,
    text_solution,
    quiz_prompt,
    quiz_solution,
    quiz_options,
    audio_solution,
    speak_prompt,
    speak_solution,
):
    return [
        ex("text", text_prompt, text_solution),
        ex("quiz", quiz_prompt, quiz_solution, quiz_options),
        ex(
            "audio",
            "Escute e transcreva a frase:",
            audio_solution,
            audio_text=audio_solution,
        ),
        ex("speak", speak_prompt, speak_solution, audio_text=speak_solution),
    ]


def _b1_b2_spec(
    title,
    objective,
    concept,
    examples,
    contrast,
    summary,
    exercises,
):
    return {
        "lesson": _b1_b2_lesson(
            title, objective, concept, examples, contrast, summary
        ),
        "exercises": exercises,
    }


B1_B2_TOPIC_ENHANCEMENTS = {
    "presente-perfeito": _b1_b2_spec(
        "Presente Perfeito",
        "Usar o presente perfeito para falar de experiências, resultados recentes e ações ligadas ao presente.",
        "A estrutura é **have/has + particípio passado**. Use *ever* e *never* para experiências, *already* e *just* para ações concluídas recentemente e *yet* em perguntas e negativas. O tempo do evento não é apresentado como um momento terminado e definido.",
        [
            ("I have already finished the report.", "Eu já terminei o relatório."),
            ("Have you ever visited Canada?", "Você já visitou o Canadá?"),
        ],
        "Não use o presente perfeito com *yesterday*, *last week* ou outro momento fechado. Diga **I visited Canada last year**, mas **I have visited Canada** quando o foco é a experiência.",
        "Forme **have/has + particípio**, escolha o marcador adequado e mantenha a conexão com o presente.",
        _b1_b2_exercises(
            "Traduza: Eu já terminei o relatório.",
            "i have already finished the report",
            "Qual frase descreve uma experiência sem momento definido?",
            "I have visited Canada.",
            ["I have visited Canada.", "I visited Canada last year.", "I am visiting Canada now."],
            "have you ever tried sushi",
            "Diga que você nunca viu neve.",
            "i have never seen snow",
        ),
    ),
    "presente-perfeito-vs-passado": _b1_b2_spec(
        "Presente Perfeito vs. Passado Simples",
        "Escolher entre presente perfeito e passado simples conforme o foco seja a experiência/consequência ou um momento terminado.",
        "O passado simples acompanha um período encerrado, como *in 2022* ou *yesterday*. O presente perfeito apresenta uma experiência ou um resultado relevante agora: **She has lost her keys** sugere que ainda não consegue entrar.",
        [
            ("We visited London in 2022.", "Nós visitamos Londres em 2022."),
            ("She has lost her keys.", "Ela perdeu as chaves e isso importa agora."),
        ],
        "Não escolha o tempo apenas pela tradução de ‘já’. **I have seen it** fala de experiência; **I saw it yesterday** informa quando aconteceu.",
        "Procure um tempo definido. Se houver, use passado simples; se o foco for experiência ou resultado atual, use presente perfeito.",
        _b1_b2_exercises(
            "Traduza: Nós visitamos Londres em 2022.",
            "we visited london in 2022",
            "As chaves continuam perdidas. Qual frase é adequada?",
            "She has lost her keys.",
            ["She has lost her keys.", "She lost her keys yesterday.", "She loses her keys every day."],
            "i saw that film yesterday",
            "Diga que você nunca esteve no Japão.",
            "i have never been to japan",
        ),
    ),
    "passado-continuo": _b1_b2_spec(
        "Passado Contínuo",
        "Descrever uma ação que estava em andamento em determinado momento do passado.",
        "Use **was/were + verbo-ing** para o cenário ou a ação em progresso. O passado simples costuma apresentar o evento curto que interrompe ou acontece durante esse cenário: **I was reading when the lights went out**.",
        [
            ("While I was studying, my brother was watching TV.", "Enquanto eu estudava, meu irmão assistia TV."),
            ("What were you doing when I called?", "O que você estava fazendo quando liguei?"),
        ],
        "Não diga *I was read* nem use o contínuo para uma ação pontual já encerrada. A forma correta é **was reading** para a ação em curso e **called** para o evento curto.",
        "Escolha **was** ou **were**, acrescente **-ing** e combine a ação em andamento com o passado simples quando houver interrupção.",
        _b1_b2_exercises(
            "Traduza: Enquanto eu estudava, meu irmão assistia TV.",
            "while i was studying my brother was watching tv",
            "Complete: 'At 8 p.m. yesterday, they ___ dinner.'",
            "were having",
            ["were having", "was having", "had have"],
            "what were you doing when i called",
            "Diga que você estava lendo quando as luzes se apagaram.",
            "i was reading when the lights went out",
        ),
    ),
    "passado-perfeito": _b1_b2_spec(
        "Passado Perfeito",
        "Mostrar que uma ação ocorreu antes de outra ação já situada no passado.",
        "Use **had + particípio passado** para o ‘passado do passado’. A ação mais antiga fica no passado perfeito e a mais recente, normalmente, no passado simples: **When I arrived, they had left**.",
        [
            ("When I arrived, they had already left.", "Quando cheguei, eles já tinham saído."),
            ("Had you eaten before the meeting?", "Você tinha comido antes da reunião?"),
        ],
        "Não use *have* ou *has* para uma sequência totalmente passada. O auxiliar é sempre **had**, e o verbo seguinte deve ser particípio: **had gone**, não *had went*.",
        "Localize os dois eventos no passado, use **had + particípio** para o primeiro e passado simples para o segundo.",
        _b1_b2_exercises(
            "Traduza: Quando cheguei, eles já tinham saído.",
            "when i arrived they had already left",
            "Qual ação aconteceu primeiro em 'When I arrived, she had left'?",
            "She had left.",
            ["She had left.", "I arrived.", "She was leaving tomorrow."],
            "they had finished dinner before the guests arrived",
            "Diga que você já tinha visto o filme antes.",
            "i had seen the movie before",
        ),
    ),
    "formas-de-futuro": _b1_b2_spec(
        "Formas de futuro",
        "Escolher a forma de futuro que combina com previsão, decisão, plano, compromisso ou horário fixo.",
        "Use **will** para decisão tomada na hora ou previsão, **be going to** para plano ou evidência, presente contínuo para compromisso marcado e presente simples para horários oficiais. O contexto define a escolha.",
        [
            ("I am going to visit my parents on Saturday.", "Vou visitar meus pais no sábado."),
            ("The bus leaves at six.", "O ônibus sai às seis."),
        ],
        "Não use **will** automaticamente para todo futuro. **The train leaves at seven** é um horário fixo; **I am meeting Ana tomorrow** é um compromisso já marcado.",
        "Pergunte se é horário, compromisso, plano ou previsão; depois escolha presente simples, presente contínuo, *going to* ou *will*.",
        _b1_b2_exercises(
            "Traduza: Eu vou visitar meus pais no sábado.",
            "i am going to visit my parents on saturday",
            "Qual frase informa um horário fixo?",
            "The bus leaves at six.",
            ["The bus leaves at six.", "The bus will maybe leave.", "I am going to buy a bus."],
            "i am meeting my manager tomorrow",
            "Faça uma previsão simples: vai chover amanhã.",
            "it will rain tomorrow",
        ),
    ),
    "condicional-zero-e-primeiro": _b1_b2_spec(
        "Condicional Zero e Primeiro",
        "Distinguir fatos gerais de possibilidades reais no futuro.",
        "O condicional zero usa **if + presente, presente** para leis, hábitos e resultados gerais. O primeiro usa **if + presente, will + verbo** para uma condição futura possível. A oração com *if* não recebe *will*.",
        [
            ("If you heat ice, it melts.", "Se você aquece gelo, ele derrete."),
            ("If it rains, we will stay home.", "Se chover, nós ficaremos em casa."),
        ],
        "Não diga *If it will rain*. Depois de **if**, use presente simples: **If it rains, we will stay home**. A diferença é entre resultado geral e situação futura específica.",
        "Zero: presente + presente para fatos. Primeiro: presente + **will** para uma possibilidade real.",
        _b1_b2_exercises(
            "Traduza: Se você aquecer gelo, ele derrete.",
            "if you heat ice it melts",
            "Qual completa o primeiro condicional? 'If you study, you ___ the test.'",
            "will pass",
            ["will pass", "pass", "passed"],
            "if we leave now we will arrive on time",
            "Diga um fato geral: se você mistura azul e amarelo, obtém verde.",
            "if you mix blue and yellow you get green",
        ),
    ),
    "condicional-segundo": _b1_b2_spec(
        "Condicional Segundo",
        "Falar de situações hipotéticas, improváveis ou imaginárias no presente e no futuro.",
        "Use **if + passado simples, would + verbo base**. Em situações hipotéticas, **were** é a forma tradicional com todas as pessoas em **If I were you**. O resultado com *would* não leva *to* nem termina em *-s*.",
        [
            ("If I had more time, I would learn French.", "Se eu tivesse mais tempo, aprenderia francês."),
            ("If I were you, I would ask for help.", "Se eu fosse você, pediria ajuda."),
        ],
        "Não use *would* na oração com **if**: diga **If I had time, I would help**, não *If I would have time*. Também não confunda hipótese presente com arrependimento passado do terceiro condicional.",
        "Use passado após **if**, **would + verbo base** no resultado e **were** em conselhos hipotéticos.",
        _b1_b2_exercises(
            "Traduza: Se eu tivesse mais tempo, aprenderia francês.",
            "if i had more time i would learn french",
            "Qual frase apresenta uma situação hipotética?",
            "If I won the lottery, I would travel.",
            ["If I won the lottery, I would travel.", "I won the lottery last year.", "I am buying a ticket now."],
            "what would you do if you had a free month",
            "Dê um conselho usando 'If I were you'.",
            "if i were you i would wait",
        ),
    ),
    "should-may-might": _b1_b2_spec(
        "Should, May e Might",
        "Usar modais para aconselhar, pedir permissão e expressar diferentes graus de possibilidade.",
        "**Should** introduz conselho; **may** pode indicar permissão ou possibilidade; **might** indica possibilidade mais incerta. Depois de qualquer modal, use o verbo na forma base, sem *to* e sem *-s*.",
        [
            ("You should take a break.", "Você deveria fazer uma pausa."),
            ("She might be at home.", "Talvez ela esteja em casa."),
        ],
        "Não diga *You should to rest* ou *She might is home*. O modal já funciona como auxiliar: **should rest**, **might be**.",
        "Escolha **should** para conselho, **may/might** para possibilidade e mantenha o verbo seguinte na forma base.",
        _b1_b2_exercises(
            "Traduza: Talvez ela esteja em casa.",
            "she might be at home",
            "Qual frase dá um conselho?",
            "You should see a doctor.",
            ["You should see a doctor.", "You may see a doctor tomorrow.", "You might be at home."],
            "may i open the window",
            "Diga que talvez chova esta noite.",
            "it might rain tonight",
        ),
    ),
    "oracoes-relativas": _b1_b2_spec(
        "Orações relativas",
        "Unir duas informações em uma frase usando pronomes relativos adequados.",
        "Use **who** para pessoas, **which** para coisas, **that** para pessoas ou coisas em contexto definidor e **where** para lugares. A oração relativa vem logo depois do nome que ela explica.",
        [
            ("The woman who lives next door is a doctor.", "A mulher que mora ao lado é médica."),
            ("This is the café where we met.", "Este é o café onde nos conhecemos."),
        ],
        "Não use *who* para uma coisa nem *where* para uma pessoa. Também não separe com vírgula uma informação necessária para identificar o nome em uma relativa definidora.",
        "Identifique se o antecedente é pessoa, coisa ou lugar e escolha **who**, **which/that** ou **where**.",
        _b1_b2_exercises(
            "Traduza: A mulher que mora ao lado é médica.",
            "the woman who lives next door is a doctor",
            "Complete: 'The laptop ___ I bought is very fast.'",
            "that",
            ["that", "who", "where"],
            "this is the town where my parents met",
            "Diga que o professor que trabalha aqui é muito paciente.",
            "the teacher who works here is very patient",
        ),
    ),
    "gerundio": _b1_b2_spec(
        "Gerúndio (-ing)",
        "Usar o gerúndio como substantivo, depois de certos verbos e depois de preposições.",
        "Depois de **enjoy, avoid, finish, mind** e de uma preposição, o verbo fica em **-ing**: **I enjoy reading** e **She is good at cooking**. O gerúndio também pode ocupar o lugar de sujeito.",
        [
            ("I avoid driving at night.", "Eu evito dirigir à noite."),
            ("Swimming is good for you.", "Nadar faz bem para você."),
        ],
        "Não diga *I enjoy to read* quando o verbo pede gerúndio. Depois de uma preposição, também não use a forma base: **good at cooking**, não *good at cook*.",
        "Reconheça verbos e preposições que pedem **verbo + -ing** e observe o gerúndio como sujeito.",
        _b1_b2_exercises(
            "Traduza: Eu evito dirigir à noite.",
            "i avoid driving at night",
            "Complete: 'She is interested in ___ English.'",
            "learning",
            ["learning", "learn", "to learn"],
            "he finished writing the email",
            "Diga que cozinhar relaxa você.",
            "cooking relaxes me",
        ),
    ),
    "infinitivo": _b1_b2_spec(
        "Infinitivo (to + verbo)",
        "Usar o infinitivo para completar certos verbos e para explicar finalidade.",
        "Depois de **want, need, decide, hope, plan** e verbos semelhantes, use **to + verbo base**. A mesma forma apresenta finalidade: **I study to improve** significa ‘estudo para melhorar’.",
        [
            ("They decided to move to another city.", "Eles decidiram mudar de cidade."),
            ("I study to improve my English.", "Eu estudo para melhorar meu inglês."),
        ],
        "Não retire o **to** depois de *want* ou *decide*: *I want buy* está errado. Depois de um modal, porém, use a forma base sem **to**, como em **can help**.",
        "Use **to + verbo** depois dos verbos adequados e para responder ‘para quê?’.",
        _b1_b2_exercises(
            "Traduza: Eles decidiram mudar de cidade.",
            "they decided to move to another city",
            "Por que alguém usa 'I went to the library to study'?",
            "Para expressar finalidade.",
            ["Para expressar finalidade.", "Para formar o passado.", "Para fazer uma comparação."],
            "she hopes to find a new job",
            "Diga que você precisa descansar.",
            "i need to rest",
        ),
    ),
    "voz-passiva": _b1_b2_spec(
        "Voz passiva",
        "Focar na ação ou no resultado, e não necessariamente em quem realizou a ação.",
        "A passiva usa uma forma de **be + particípio passado**. No presente, use **am/is/are**; no passado, **was/were**. Use **by** apenas quando o agente for importante: **The book was written by Maya**.",
        [
            ("The letters are delivered every day.", "As cartas são entregues todos os dias."),
            ("The bridge was built in 1990.", "A ponte foi construída em 1990."),
        ],
        "Não confunda passiva com presente perfeito. **The bridge was built** é passado simples; **The bridge has been built** destaca o resultado até agora. O particípio não pode ser substituído pelo passado simples irregular.",
        "Escolha o tempo de **be**, acrescente o particípio e mencione o agente com **by** somente se necessário.",
        _b1_b2_exercises(
            "Traduza: As cartas são entregues todos os dias.",
            "the letters are delivered every day",
            "Qual frase está na voz passiva?",
            "The window was broken last night.",
            ["The window was broken last night.", "Someone broke the window.", "The window breaks easily."],
            "the meal was prepared by the chef",
            "Diga que o inglês é falado em muitos países.",
            "english is spoken in many countries",
        ),
    ),
    "discurso-indireto": _b1_b2_spec(
        "Discurso indireto",
        "Relatar afirmações de outra pessoa sem repetir exatamente as palavras entre aspas.",
        "Use **said (that)** e ajuste pronomes e tempos quando o verbo de relato estiver no passado: *am* costuma virar *was*, *will* vira *would* e *can* vira *could*. O **that** pode ser omitido em muitas afirmações.",
        [
            ("He said that he was tired.", "Ele disse que estava cansado."),
            ("She said she would help us.", "Ela disse que nos ajudaria."),
        ],
        "Não mantenha automaticamente o pronome da fala original: ‘I am tired’ relatado por ele vira **he was tired**. O ajuste depende de quem está contando a frase.",
        "Identifique quem falou, ajuste pronomes e faça o *backshift* básico: presente para passado e **will** para **would**.",
        _b1_b2_exercises(
            "Traduza: Ele disse que estava cansado.",
            "he said that he was tired",
            "Como relatar 'I will call you' depois de 'She said'?",
            "She said she would call me.",
            ["She said she would call me.", "She said she will called me.", "She says I would call her."],
            "he said he could help us",
            "Relate: Ana disse que gostava de café.",
            "ana said that she liked coffee",
        ),
    ),
    "question-tags": _b1_b2_spec(
        "Question tags",
        "Confirmar uma informação usando uma pequena pergunta no final da frase.",
        "Uma afirmação normalmente recebe uma tag negativa e uma negativa recebe uma tag afirmativa. Repita o auxiliar e o sujeito: **You like tea, don’t you?**; **She isn’t late, is she?**.",
        [
            ("You like music, don't you?", "Você gosta de música, não gosta?"),
            ("They were ready, weren't they?", "Eles estavam prontos, não estavam?"),
        ],
        "Não use *isn't* com um verbo comum no presente. Em **You work here, don’t you?**, o auxiliar é **do**; com **to be**, use **is/are/was/were**.",
        "Veja se a frase é afirmativa ou negativa, copie o auxiliar e inverta o sinal na tag.",
        _b1_b2_exercises(
            "Traduza: Você gosta de música, não gosta?",
            "you like music don't you",
            "Complete: 'She can drive, ___ she?'",
            "can't",
            ["can't", "can", "doesn't"],
            "we are meeting at six aren't we",
            "Confirme que ele não está atrasado.",
            "he isn't late is he",
        ),
    ),
    "phrasal-verbs": _b1_b2_spec(
        "Phrasal verbs comuns",
        "Entender e usar combinações frequentes de verbo e partícula em situações cotidianas.",
        "Um *phrasal verb* combina verbo e partícula, e o conjunto pode ter sentido próprio: **look for** é procurar e **look after** é cuidar. Aprenda a expressão com seu complemento e com uma situação real.",
        [
            ("Please look after my dog.", "Por favor, cuide do meu cachorro."),
            ("I need to find out the truth.", "Preciso descobrir a verdade."),
        ],
        "Não traduza a partícula isoladamente. **Take off** pode ser tirar uma roupa ou decolar; **turn off** é desligar, enquanto **turn on** é ligar.",
        "Memorize o bloco completo, observe o contexto e pratique a expressão em uma frase, não apenas como uma lista.",
        _b1_b2_exercises(
            "Traduza: Por favor, cuide do meu cachorro.",
            "please look after my dog",
            "O que fazemos quando queremos descobrir uma informação?",
            "We find out.",
            ["We find out.", "We get up.", "We turn off."],
            "please turn off the lights",
            "Diga que você está procurando suas chaves.",
            "i am looking for my keys",
        ),
    ),
}


# ============================================================
# Complementos do modulo 9 - Vocabulario B1
# ============================================================

B1_B2_TOPIC_ENHANCEMENTS.update({
    "trabalho-b1": _b1_b2_spec(
        "Trabalho (B1)",
        "Usar vocabulário de trabalho para descrever tarefas, prazos, reuniões e desenvolvimento profissional.",
        "**Meeting** é reunião, **deadline** é o prazo final e **salary** é salário. **Raise** é aumento salarial, enquanto **promotion** é uma promoção de cargo; as palavras ficam mais naturais quando aparecem em frases sobre uma situação real.",
        [
            ("We have a deadline tomorrow.", "Temos um prazo amanhã."),
            ("She is asking for a raise.", "Ela está pedindo um aumento."),
        ],
        "Não confunda *deadline* com qualquer data no calendário: é o limite para entregar algo. Também não use *promotion* para salário; promoção é mudança de cargo.",
        "Associe cada palavra à tarefa profissional: reunião, prazo, salário, habilidade, equipe ou crescimento na carreira.",
        _b1_b2_exercises(
            "Traduza: Temos um prazo amanhã.",
            "we have a deadline tomorrow",
            "Você quer ganhar mais no mesmo cargo. Qual palavra descreve isso?",
            "a raise",
            ["a raise", "a deadline", "a meeting"],
            "teamwork is an important skill",
            "Diga que você tem uma reunião às dez.",
            "i have a meeting at ten",
        ),
    ),
    "carreira": _b1_b2_spec(
        "Carreira",
        "Falar sobre metas profissionais, oportunidades e movimentos de carreira.",
        "Use **career** para a trajetória profissional, **goal** para meta, **opportunity** para oportunidade e **experience** para experiência. **Apply for** significa candidatar-se; **hire** descreve a ação do empregador e **resign** a decisão do empregado de pedir demissão.",
        [
            ("She applied for a job.", "Ela se candidatou a um emprego."),
            ("I want to achieve my career goals.", "Quero alcançar minhas metas profissionais."),
        ],
        "Não confunda **apply for** com **hire**: o candidato *applies for a job*, mas a empresa *hires* alguém. Para pedir demissão, o verbo é **resign**, não *retire*.",
        "Descreva a meta, a oportunidade e a ação profissional com o verbo adequado e a preposição **for** em *apply for*.",
        _b1_b2_exercises(
            "Traduza: Ela se candidatou a um emprego.",
            "she applied for a job",
            "Quem normalmente 'hires' alguém?",
            "The employer.",
            ["The employer.", "The applicant.", "The deadline."],
            "i want to achieve my career goals",
            "Diga que você está procurando uma nova oportunidade.",
            "i am looking for a new opportunity",
        ),
    ),
    "mundo-digital": _b1_b2_spec(
        "Mundo digital",
        "Descrever ações básicas com contas, dispositivos, arquivos e conexão à internet.",
        "**Password**, **username** e **account** formam o vocabulário de acesso. **Download** traz um arquivo para o dispositivo; **upload** envia o arquivo para um serviço. **Update** é atualizar um aplicativo ou sistema.",
        [
            ("I forgot my password.", "Esqueci minha senha."),
            ("Please upload the file to the account.", "Envie o arquivo para a conta, por favor."),
        ],
        "Não troque *download* por *upload*: a direção da transferência muda. **Device** é o aparelho; **account** é a conta usada no serviço.",
        "Pense na ação e na direção: acessar, baixar, enviar, atualizar ou resolver um problema de conexão.",
        _b1_b2_exercises(
            "Traduza: Esqueci minha senha.",
            "i forgot my password",
            "Você envia uma foto para uma plataforma. Qual verbo é adequado?",
            "upload",
            ["upload", "download", "update"],
            "i need to update the app",
            "Diga que sua conexão está lenta.",
            "my internet connection is slow",
        ),
    ),
    "ciencia": _b1_b2_spec(
        "Ciência",
        "Compreender e produzir frases sobre pesquisa, experimentos, evidências e descobertas.",
        "**Research** é pesquisa em sentido amplo e normalmente não recebe artigo indefinido. **Experiment** é o teste realizado, **evidence** sustenta uma conclusão e **discovery** é o que foi descoberto.",
        [
            ("The experiment produced useful evidence.", "O experimento produziu evidências úteis."),
            ("The scientist made an important discovery.", "O cientista fez uma descoberta importante."),
        ],
        "Não use *a research* para falar de pesquisa em geral; diga **do research** ou **a research project**. Também não confunda uma teoria com uma evidência que a apoia.",
        "Relacione área, método e resultado: cientistas fazem pesquisa e experimentos para obter evidências e explicar descobertas.",
        _b1_b2_exercises(
            "Traduza: O cientista fez uma descoberta importante.",
            "the scientist made an important discovery",
            "O que sustenta uma conclusão científica?",
            "Evidence.",
            ["Evidence.", "A password.", "A salary."],
            "the experiment was successful",
            "Diga que a ciência explica o mundo.",
            "science helps explain the world",
        ),
    ),
    "politica": _b1_b2_spec(
        "Política",
        "Entender vocabulário básico de eleições, governo, leis e participação cidadã.",
        "**Government** é governo, **election** é eleição e **candidate** é candidato. O cidadão pode **vote**, e **rights** são direitos protegidos por uma lei ou por uma constituição.",
        [
            ("Every citizen has the right to vote.", "Todo cidadão tem o direito de votar."),
            ("The election will be held in November.", "A eleição será realizada em novembro."),
        ],
        "Não confunda **vote** como verbo com **a vote** como substantivo. **Candidate** é a pessoa que concorre; **president** é o cargo ou a pessoa que o ocupa.",
        "Use o vocabulário para identificar quem governa, quem se candidata, quando se vota e quais direitos estão em discussão.",
        _b1_b2_exercises(
            "Traduza: Todo cidadão tem o direito de votar.",
            "every citizen has the right to vote",
            "Quem participa de uma eleição para tentar vencer?",
            "A candidate.",
            ["A candidate.", "A laboratory.", "A deadline."],
            "the government announced a new law",
            "Diga que a eleição será em novembro.",
            "the election will be in november",
        ),
    ),
    "sociedade": _b1_b2_spec(
        "Sociedade",
        "Falar sobre comunidade, população, igualdade, liberdade e responsabilidade social.",
        "**Society** trata do conjunto social; **community** é um grupo ou comunidade mais próximo. **Equality**, **freedom** e **responsibility** nomeiam valores e deveres, enquanto **poverty** descreve uma condição social.",
        [
            ("Our community supports local families.", "Nossa comunidade apoia famílias locais."),
            ("Equality is an important social value.", "A igualdade é um valor social importante."),
        ],
        "Não trate *society* e *community* como sinônimos perfeitos: a sociedade é mais ampla. Além disso, **freedom** é liberdade, não ‘livre’ (*free*).",
        "Escolha a palavra pelo alcance da ideia e descreva valores sociais com substantivos e frases completas.",
        _b1_b2_exercises(
            "Traduza: A igualdade é um valor social importante.",
            "equality is an important social value",
            "Qual palavra descreve um grupo local de pessoas?",
            "community",
            ["community", "population", "poverty"],
            "society is changing quickly",
            "Diga que a liberdade é um direito importante.",
            "freedom is an important right",
        ),
    ),
    "meio-ambiente": _b1_b2_spec(
        "Meio ambiente",
        "Descrever problemas ambientais e ações para proteger o planeta.",
        "**Pollution** é poluição, **waste** pode ser lixo ou desperdício e **renewable energy** é energia renovável. Use **protect**, **recycle** e **reduce** para apresentar ações concretas.",
        [
            ("We should recycle more plastic.", "Deveríamos reciclar mais plástico."),
            ("Renewable energy can reduce pollution.", "A energia renovável pode reduzir a poluição."),
        ],
        "Não confunda **waste** com **recycle**: o primeiro é o problema ou o material descartado; o segundo é a ação de reciclar. **Climate change** é mudança climática, não apenas ‘tempo’.",
        "Nomeie o problema ambiental, use um modal para sugerir uma ação e explique o possível resultado.",
        _b1_b2_exercises(
            "Traduza: Deveríamos reciclar mais plástico.",
            "we should recycle more plastic",
            "Qual fonte de energia se renova naturalmente?",
            "Renewable energy.",
            ["Renewable energy.", "Waste energy.", "Pollution energy."],
            "we need to protect the planet",
            "Diga que a poluição prejudica o meio ambiente.",
            "pollution damages the environment",
        ),
    ),
    "educacao-e-aprendizado": _b1_b2_spec(
        "Educação e aprendizado",
        "Falar sobre cursos, prática, habilidades, treinamento e progresso no aprendizado.",
        "**Course** é curso, **training** é treinamento e **certificate** é certificado. **Practice** pode ser prática como atividade ou verbo, enquanto **skill** é uma habilidade desenvolvida.",
        [
            ("Practice helps me improve my English.", "A prática me ajuda a melhorar meu inglês."),
            ("She completed a training course.", "Ela concluiu um curso de treinamento."),
        ],
        "Não confunda **practice** com **knowledge**: prática é o exercício; conhecimento é o que se sabe. Para dizer ‘cometer um erro’, a combinação natural é **make a mistake**.",
        "Combine uma ação de estudo com o resultado: praticar desenvolve habilidades, aumenta o conhecimento e ajuda a entender melhor.",
        _b1_b2_exercises(
            "Traduza: A prática me ajuda a melhorar meu inglês.",
            "practice helps me improve my english",
            "O que você desenvolve ao aprender a fazer algo bem?",
            "A skill.",
            ["A skill.", "A mistake only.", "A deadline."],
            "learning from mistakes is important",
            "Diga que você precisa de mais prática.",
            "i need more practice",
        ),
    ),
    "cultura": _b1_b2_spec(
        "Cultura",
        "Descrever tradições, arte, festivais, patrimônio e identidade cultural.",
        "**Culture** é cultura, **tradition** é tradição e **heritage** é patrimônio transmitido entre gerações. **Art**, **literature** e **festival** aparecem como partes ou manifestações de uma cultura.",
        [
            ("Every country has its own culture.", "Cada país tem sua própria cultura."),
            ("The festival celebrates our heritage.", "O festival celebra nosso patrimônio."),
        ],
        "Não use *tradition* para qualquer evento único: tradição implica continuidade. **Heritage** é legado cultural, histórico ou familiar; não significa apenas ‘herança em dinheiro’.",
        "Fale de uma manifestação cultural, diga o que ela representa e use possessivos para relacioná-la a um povo ou lugar.",
        _b1_b2_exercises(
            "Traduza: O festival celebra nosso patrimônio.",
            "the festival celebrates our heritage",
            "Qual palavra significa uma prática transmitida ao longo do tempo?",
            "tradition",
            ["tradition", "channel", "salary"],
            "i enjoy modern art",
            "Diga que cada país tem sua própria cultura.",
            "every country has its own culture",
        ),
    ),
    "midia": _b1_b2_spec(
        "Mídia",
        "Compreender e produzir frases sobre notícias, artigos, reportagens, canais e público.",
        "**News** é normalmente incontável e leva verbo no singular: **The news is surprising**. **Newspaper** é jornal, **article** é artigo, **report** é reportagem ou relatório e **audience** é o público que acompanha o conteúdo.",
        [
            ("I read the news every morning.", "Leio as notícias todas as manhãs."),
            ("The journalist wrote an interesting article.", "O jornalista escreveu um artigo interessante."),
        ],
        "Não diga *the news are* no uso padrão; diga **the news is**. Também não confunda *journalist* (pessoa) com *newspaper* (publicação).",
        "Identifique o meio, o conteúdo, quem o produz e quem o recebe; use **news** como substantivo incontável.",
        _b1_b2_exercises(
            "Traduza: O jornalista escreveu um artigo interessante.",
            "the journalist wrote an interesting article",
            "Quem normalmente escreve uma reportagem?",
            "A journalist.",
            ["A journalist.", "An audience.", "A channel."],
            "the news is on every channel",
            "Diga que você lê as notícias todas as manhãs.",
            "i read the news every morning",
        ),
    ),
    "negocios": _b1_b2_spec(
        "Negócios",
        "Falar sobre empresas, clientes, produtos, mercados, marcas e resultados financeiros.",
        "**Company** é empresa, **business** pode ser negócio ou atividade empresarial, **customer** é quem compra e **client** costuma contratar um serviço. **Profit** é lucro; **deal** é acordo ou negócio fechado.",
        [
            ("The company grew this year.", "A empresa cresceu este ano."),
            ("Our customers are happy with the product.", "Nossos clientes estão satisfeitos com o produto."),
        ],
        "Não use *client* para toda situação de compra: uma loja geralmente tem **customers**, enquanto um escritório de consultoria atende **clients**. **Profit** não é receita total; é o lucro.",
        "Escolha o termo conforme a relação comercial: empresa, pessoa atendida, produto, marca, mercado ou resultado.",
        _b1_b2_exercises(
            "Traduza: A empresa cresceu este ano.",
            "the company grew this year",
            "Quem compra um produto em uma loja é normalmente um...",
            "customer",
            ["customer", "client only", "competitor"],
            "our customers are happy with the product",
            "Diga que o acordo foi importante para a empresa.",
            "the deal was important for the company",
        ),
    ),
    "emocoes": _b1_b2_spec(
        "Emoções",
        "Descrever estados emocionais e explicar o motivo de preocupação, entusiasmo ou decepção.",
        "Adjetivos como **worried**, **excited**, **proud** e **disappointed** descrevem como alguém se sente. Use **about** para indicar o assunto: **worried about the exam** e **excited about the trip**.",
        [
            ("I am worried about the exam.", "Estou preocupado com a prova."),
            ("She is excited about the trip.", "Ela está animada com a viagem."),
        ],
        "Não confunda **excited** (animado) com *exciting* (que causa animação). A pessoa fica **excited**; o evento pode ser **exciting**.",
        "Use **be + adjetivo** para o estado e acrescente **about + assunto** para explicar o motivo.",
        _b1_b2_exercises(
            "Traduza: Estou preocupado com a prova.",
            "i am worried about the exam",
            "Qual frase descreve a emoção da pessoa, e não a causa?",
            "She is excited.",
            ["She is excited.", "The trip is exciting.", "She travels tomorrow."],
            "he feels nervous before interviews",
            "Diga que você está orgulhoso do seu trabalho.",
            "i am proud of my work",
        ),
    ),
    "personalidade": _b1_b2_spec(
        "Personalidade",
        "Descrever características de personalidade com precisão e em contexto.",
        "Adjetivos como **reliable**, **patient**, **ambitious**, **generous** e **stubborn** descrevem traços relativamente estáveis. Use **be + adjetivo** e dê uma evidência comportamental quando possível.",
        [
            ("She is reliable and always keeps her promises.", "Ela é confiável e sempre cumpre suas promessas."),
            ("He is creative but sometimes stubborn.", "Ele é criativo, mas às vezes teimoso."),
        ],
        "Não confunda **reliable** com *responsible* em todos os contextos: *reliable* é alguém em quem se pode confiar. **Patient** pode significar paciente ou, como substantivo, pessoa atendida em saúde.",
        "Escolha o adjetivo pelo comportamento observado e conecte características com **and**, **but** ou um exemplo.",
        _b1_b2_exercises(
            "Traduza: Ela é confiável e sempre cumpre suas promessas.",
            "she is reliable and always keeps her promises",
            "Qual pessoa é 'generous'?",
            "Someone who is willing to give and share.",
            ["Someone who is willing to give and share.", "Someone who never listens.", "Someone who is always late."],
            "he is confident but not selfish",
            "Diga que sua colega é muito paciente.",
            "my colleague is very patient",
        ),
    ),
    "relacoes-interpessoais": _b1_b2_spec(
        "Relações interpessoais",
        "Falar sobre confiança, respeito, apoio, conflito, desculpas e conciliação.",
        "**Trust** é confiança ou confiar, **support** é apoio ou apoiar e **respect** funciona como substantivo e verbo. **Argue** é discutir, **apologize** é pedir desculpas e **forgive** é perdoar.",
        [
            ("It is important to respect other people.", "É importante respeitar outras pessoas."),
            ("They apologized and reached a compromise.", "Eles pediram desculpas e chegaram a um acordo."),
        ],
        "Não confunda **argue** com ‘provar que está certo’: em relações, geralmente significa discutir. **Apologize** é pedir desculpas; **forgive** é aceitar as desculpas.",
        "Nomeie o problema, use uma ação respeitosa e descreva como a comunicação pode reconstruir a confiança.",
        _b1_b2_exercises(
            "Traduza: É importante respeitar outras pessoas.",
            "it is important to respect other people",
            "O que uma pessoa faz quando reconhece que errou?",
            "She apologizes.",
            ["She apologizes.", "She argues forever.", "She ignores everyone."],
            "communication is important in relationships",
            "Diga que amigos devem apoiar uns aos outros.",
            "friends should support each other",
        ),
    ),
    "conceitos-abstratos": _b1_b2_spec(
        "Conceitos abstratos",
        "Usar substantivos abstratos para falar de valores, ideias, justiça, paz e significado.",
        "Substantivos como **truth**, **justice**, **courage**, **happiness** e **meaning** nomeiam ideias, não objetos físicos. Eles aparecem frequentemente como sujeitos: **Freedom is important**; adjetivos correspondentes podem mudar a classe, como *truth* e *true*.",
        [
            ("Freedom is important to everyone.", "A liberdade é importante para todos."),
            ("The meaning of the idea is clear.", "O significado da ideia é claro."),
        ],
        "Não confunda **truth** (verdade, substantivo) com **true** (verdadeiro, adjetivo). **Peace** é paz; **piece** é pedaço, embora tenham pronúncia semelhante.",
        "Identifique a ideia abstrata, escolha a classe gramatical correta e conecte-a a uma opinião ou exemplo concreto.",
        _b1_b2_exercises(
            "Traduza: A liberdade é importante para todos.",
            "freedom is important to everyone",
            "Qual palavra significa 'o que algo quer dizer'?",
            "meaning",
            ["meaning", "courage", "value"],
            "happiness is not only about money",
            "Diga que a justiça é importante em uma sociedade.",
            "justice is important in a society",
        ),
    ),
})


# ============================================================
# Complementos do modulo 10 - Speaking B1
# ============================================================

B1_B2_TOPIC_ENHANCEMENTS.update({
    "dando-sua-opiniao": _b1_b2_spec(
        "Expressando opiniões",
        "Dar uma opinião clara, indicar o grau de certeza e escolher um registro adequado à conversa.",
        "Use **I think**, **In my opinion** ou **From my point of view** para apresentar uma posição. **As far as I’m concerned** é mais formal e **I believe** pode soar um pouco mais forte do que uma opinião casual.",
        [
            ("In my opinion, this is the best option.", "Na minha opinião, esta é a melhor opção."),
            ("From my point of view, we should wait.", "Do meu ponto de vista, deveríamos esperar."),
        ],
        "Não trate **I think** como tradução de ‘eu penso’ em qualquer contexto: aqui ele introduz opinião. Para não soar absoluto, acrescente **I believe** ou explique a razão.",
        "Apresente a opinião, indique a perspectiva e sustente-a com uma razão ou exemplo.",
        _b1_b2_exercises(
            "Traduza: Do meu ponto de vista, precisamos de mais tempo.",
            "from my point of view we need more time",
            "Qual expressão introduz uma opinião pessoal?",
            "In my opinion, ...",
            ["In my opinion, ...", "As a result, ...", "Goodbye, ..."],
            "i believe this is a good solution",
            "Dê sua opinião sobre a proposta.",
            "in my opinion the proposal is useful",
        ),
    ),
    "concordando": _b1_b2_spec(
        "Concordando",
        "Concordar totalmente ou parcialmente sem apenas repetir a frase da outra pessoa.",
        "**I agree**, **You’re right**, **That’s true** e **Exactly** expressam concordância. Para concordar em parte, use **You have a point, but...** e acrescente uma ressalva.",
        [
            ("I agree with you about the deadline.", "Concordo com você sobre o prazo."),
            ("You have a point, but we need more evidence.", "Você tem razão em parte, mas precisamos de mais evidências."),
        ],
        "Não diga *I am agree*: **agree** é verbo e pede **I agree**. Use **with** para a pessoa ou ideia: **I agree with you**.",
        "Mostre se a concordância é total ou parcial e use **with** quando mencionar a pessoa ou a posição.",
        _b1_b2_exercises(
            "Traduza: Concordo com você sobre o prazo.",
            "i agree with you about the deadline",
            "Qual resposta demonstra concordância parcial?",
            "You have a point, but...",
            ["You have a point, but...", "I completely disagree.", "I have no idea."],
            "yes i think you are right",
            "Concorde educadamente: você tem razão.",
            "you are right",
        ),
    ),
    "discordando": _b1_b2_spec(
        "Discordando",
        "Discordar com firmeza e respeito, sem transformar a conversa em um ataque pessoal.",
        "Use **I disagree**, **I don’t think so** e **I see your point, but...**. Formas como **I’m not sure I agree** suavizam a discordância e deixam espaço para continuar o diálogo.",
        [
            ("I see your point, but I disagree.", "Entendo seu ponto, mas discordo."),
            ("I’m not sure I agree with that conclusion.", "Não tenho certeza de que concordo com essa conclusão."),
        ],
        "Evite *You’re wrong* quando o objetivo é colaborar. Ataque a ideia, não a pessoa, e acrescente uma razão para a discordância.",
        "Reconheça o ponto do outro, marque a discordância e explique sua própria perspectiva com tom respeitoso.",
        _b1_b2_exercises(
            "Traduza: Entendo seu ponto, mas discordo.",
            "i see your point but i disagree",
            "Qual frase é uma discordância educada?",
            "I'm not sure I agree.",
            ["I'm not sure I agree.", "You're completely stupid.", "No way, stop."],
            "i do not think that is the best option",
            "Discorde suavemente da ideia.",
            "i am not sure i agree with that",
        ),
    ),
    "explicando-ideias": _b1_b2_spec(
        "Explicando ideias",
        "Reformular uma ideia, explicar sua intenção e oferecer um exemplo compreensível.",
        "**What I mean is...** esclarece a intenção; **in other words...** reformula; **for example...** concretiza. Use uma sequência curta em vez de repetir a mesma frase mais alto.",
        [
            ("What I mean is that we need more time.", "O que quero dizer é que precisamos de mais tempo."),
            ("In other words, the plan is too expensive.", "Em outras palavras, o plano é caro demais."),
        ],
        "Não confunda **in other words** com **however**: o primeiro reformula; o segundo introduz contraste. **For example** deve apresentar um caso concreto.",
        "Diga a intenção, reformule com palavras simples e acrescente um exemplo quando a ideia for abstrata.",
        _b1_b2_exercises(
            "Traduza: O que quero dizer é que precisamos de mais tempo.",
            "what i mean is that we need more time",
            "Qual expressão reformula uma ideia?",
            "In other words, ...",
            ["In other words, ...", "At first, ...", "Good night, ..."],
            "for example we could start tomorrow",
            "Explique que o plano é caro demais, em outras palavras.",
            "in other words the plan is too expensive",
        ),
    ),
    "contando-historias": _b1_b2_spec(
        "Contando histórias",
        "Organizar uma narrativa curta com sequência temporal, cenário e acontecimento inesperado.",
        "Use **first**, **then**, **after that**, **suddenly** e **finally** para guiar quem ouve. Combine passado contínuo para o cenário com passado simples para eventos concluídos ou inesperados.",
        [
            ("First, we arrived. Then, we had dinner.", "Primeiro, chegamos. Depois, jantamos."),
            ("Suddenly, the lights went out.", "De repente, as luzes se apagaram."),
        ],
        "Não use **finally** para iniciar uma sequência e não empilhe ações sem conectores. **Suddenly** marca uma mudança inesperada, não apenas o próximo passo.",
        "Planeje começo, desenvolvimento e fim; use conectores e alterne cenário em progresso com eventos pontuais.",
        _b1_b2_exercises(
            "Ordene e traduza: 'First / we / arrived / then / we / had dinner'.",
            "first we arrived then we had dinner",
            "Qual conector apresenta o último evento?",
            "Finally, ...",
            ["Finally, ...", "First, ...", "Suddenly, ..."],
            "suddenly the phone rang",
            "Comece uma história dizendo que você chegou em casa.",
            "first i arrived home",
        ),
    ),
    "descrevendo-experiencias": _b1_b2_spec(
        "Descrevendo experiências",
        "Contar uma experiência, acrescentar detalhes e avaliar o que aconteceu.",
        "Use o presente perfeito para apresentar a experiência sem data definida e o passado simples para detalhes: **I’ve been to Rome. It was beautiful**. Adjetivos como *amazing*, *boring* e *challenging* comunicam avaliação.",
        [
            ("I have traveled abroad twice.", "Já viajei para o exterior duas vezes."),
            ("The trip was challenging but rewarding.", "A viagem foi desafiadora, mas gratificante."),
        ],
        "Não misture a data fechada com presente perfeito: diga **I went to Rome in 2023**, mas **I have been to Rome** quando a data não importa.",
        "Apresente a experiência, dê um detalhe no passado e termine com uma avaliação ou sentimento.",
        _b1_b2_exercises(
            "Traduza: A viagem foi desafiadora, mas gratificante.",
            "the trip was challenging but rewarding",
            "Qual frase apresenta uma experiência sem informar quando?",
            "I've traveled abroad.",
            ["I've traveled abroad.", "I traveled abroad last summer.", "I am traveling abroad tomorrow."],
            "i have visited mexico twice",
            "Diga que foi uma experiência incrível.",
            "it was an amazing experience",
        ),
    ),
    "dando-razoes": _b1_b2_spec(
        "Dando razões",
        "Explicar por que algo acontece usando conectores de causa e consequência.",
        "Use **because/since + oração** e **because of + substantivo**. **That’s why** apresenta uma consequência ou conclusão: **I was tired, so I went home** ou **I was tired; that’s why I went home**.",
        [
            ("I stayed home because it was raining.", "Fiquei em casa porque estava chovendo."),
            ("We were late because of the traffic.", "Chegamos atrasados por causa do trânsito."),
        ],
        "Não diga *because of it was raining*: depois de **because of**, use nome ou expressão nominal; depois de **because**, use uma oração com sujeito e verbo.",
        "Escolha **because** para uma causa em forma de oração e **because of** para um substantivo; use **that’s why** para o resultado.",
        _b1_b2_exercises(
            "Traduza: Chegamos atrasados por causa do trânsito.",
            "we were late because of the traffic",
            "Qual frase explica a causa com uma oração completa?",
            "I stayed home because it was raining.",
            ["I stayed home because it was raining.", "I stayed home because of raining.", "I stayed home although rain."],
            "i was tired that is why i went home",
            "Dê uma razão para estudar inglês.",
            "i study english because i want to communicate",
        ),
    ),
    "comparando-coisas": _b1_b2_spec(
        "Comparando coisas",
        "Comparar duas ou mais coisas com comparativos, superlativos e estruturas de igualdade.",
        "Use **-er + than** com adjetivos curtos, **more + adjetivo + than** com adjetivos longos e **as + adjetivo + as** para igualdade. O superlativo usa **the -est** ou **the most** quando se compara um grupo.",
        [
            ("This phone is more expensive than the other one.", "Este celular é mais caro que o outro."),
            ("My new desk is as comfortable as the old one.", "Minha mesa nova é tão confortável quanto a antiga."),
        ],
        "Não use *more better* nem troque **than** por *that*. Com **as...as**, não use o comparativo: diga **as fast as**, não *as faster as*.",
        "Defina o número de elementos, escolha o formato do adjetivo e acrescente **than**, **as...as** ou **the most/-est**.",
        _b1_b2_exercises(
            "Traduza: Este celular é mais caro que o outro.",
            "this phone is more expensive than the other one",
            "Qual frase indica igualdade?",
            "The two rooms are as bright as each other.",
            ["The two rooms are as bright as each other.", "One room is brighter than the other.", "This is the brightest room."],
            "my current job is better than my old job",
            "Compare duas cidades dizendo que uma é mais tranquila.",
            "this city is quieter than that one",
        ),
    ),
    "construindo-argumentos": _b1_b2_spec(
        "Construindo argumentos",
        "Organizar uma posição em introdução, razões, contraponto e conclusão.",
        "Use **first of all** para iniciar, **another point** e **moreover** para acrescentar, **however** para apresentar contraste e **in conclusion** para fechar. Cada conector deve sinalizar uma relação real entre as ideias.",
        [
            ("First of all, the plan is affordable.", "Primeiramente, o plano é acessível."),
            ("However, it may take more time.", "Porém, ele pode levar mais tempo."),
        ],
        "Não use **however** como sinônimo de ‘além disso’: ele muda a direção do argumento. Para acrescentar, use **moreover** ou **another point is**.",
        "Apresente a ideia, desenvolva razões, reconheça um limite e conclua sem introduzir uma informação nova no fim.",
        _b1_b2_exercises(
            "Traduza: Primeiramente, o plano é acessível.",
            "first of all the plan is affordable",
            "Qual conector acrescenta um ponto?",
            "Moreover, ...",
            ["Moreover, ...", "However, ...", "In conclusion, ..."],
            "however the plan has some risks",
            "Conclua um argumento sobre a proposta.",
            "in conclusion the proposal is worth considering",
        ),
    ),
    "aconselhando": _b1_b2_spec(
        "Dando conselhos",
        "Dar conselhos com diferentes graus de força e de formalidade.",
        "**Should** é conselho comum; **shouldn’t** recomenda não fazer algo; **If I were you, I would...** suaviza a sugestão; **You’d better...** é mais forte. **I’d advise you to...** é uma forma mais formal.",
        [
            ("If I were you, I would take a break.", "Se eu fosse você, faria uma pausa."),
            ("I’d advise you to check the details.", "Eu aconselharia você a verificar os detalhes."),
        ],
        "Não diga *If I was you* em um conselho hipotético cuidadoso: **If I were you** é a forma tradicional. Depois de **should**, não use **to**.",
        "Escolha o modal conforme a força do conselho e explique a razão para que ele soe colaborativo.",
        _b1_b2_exercises(
            "Traduza: Se eu fosse você, faria uma pausa.",
            "if i were you i would take a break",
            "Qual conselho é mais forte e urgente?",
            "You'd better leave now.",
            ["You'd better leave now.", "You might leave someday.", "I left yesterday."],
            "you should check the instructions",
            "Aconselhe alguém a pedir ajuda.",
            "if i were you i would ask for help",
        ),
    ),
    "discutindo-problemas": _b1_b2_spec(
        "Discutindo problemas",
        "Nomear um problema, convidar a colaboração e propor soluções possíveis.",
        "Comece com **The problem is that...**, pergunte **What should we do?** e proponha com **We could...** ou **Let’s...**. A linguagem colaborativa mantém a discussão focada no problema, não na culpa.",
        [
            ("The problem is that we need more time.", "O problema é que precisamos de mais tempo."),
            ("We could try a different approach.", "Poderíamos tentar uma abordagem diferente."),
        ],
        "Não trate **could** como certeza nem use *We can to try*. Depois de **could**, use verbo base: **could try**.",
        "Descreva o problema, faça uma pergunta aberta e ofereça uma ou mais soluções com linguagem cooperativa.",
        _b1_b2_exercises(
            "Traduza: Poderíamos tentar uma abordagem diferente.",
            "we could try a different approach",
            "Qual pergunta convida o grupo a buscar uma solução?",
            "What should we do?",
            ["What should we do?", "Who is to blame?", "Why bother?"],
            "we need to solve this problem together",
            "Apresente um problema: precisamos de mais tempo.",
            "the problem is that we need more time",
        ),
    ),
    "falando-de-planos": _b1_b2_spec(
        "Falando de planos",
        "Descrever planos decididos, intenções e possibilidades futuras com naturalidade.",
        "**Plan to** e **intend to** apresentam intenção mais definida; **be thinking of + -ing** apresenta uma ideia em consideração; **hope to** expressa desejo. O verbo depois de *thinking of* fica no gerúndio.",
        [
            ("I am planning to travel next month.", "Estou planejando viajar no mês que vem."),
            ("I am thinking of changing jobs.", "Estou pensando em mudar de emprego."),
        ],
        "Não diga *thinking to change*: a combinação natural é **thinking of changing**. **Plan to** leva infinitivo: **plan to travel**.",
        "Indique o grau de decisão: plano definido, intenção, ideia em avaliação ou esperança.",
        _b1_b2_exercises(
            "Traduza: Estou pensando em mudar de emprego.",
            "i am thinking of changing jobs",
            "Qual frase apresenta um plano mais definido?",
            "I am planning to start a course.",
            ["I am planning to start a course.", "I am thinking of starting a course.", "I hope to start someday."],
            "i intend to finish the project this month",
            "Diga que você espera viajar em breve.",
            "i hope to travel soon",
        ),
    ),
    "falando-de-objetivos": _b1_b2_spec(
        "Falando de objetivos",
        "Apresentar metas de curto e longo prazo e explicar as ações para alcançá-las.",
        "Use **goal** para objetivo, **achieve** para alcançar e **work towards** para trabalhar rumo a uma meta. **Short-term** e **long-term** indicam o horizonte de tempo.",
        [
            ("My goal is to improve my English.", "Meu objetivo é melhorar meu inglês."),
            ("I am working towards a long-term goal.", "Estou trabalhando para alcançar um objetivo de longo prazo."),
        ],
        "Não diga *achieve to my goal*: **achieve** recebe o objeto diretamente (**achieve a goal**). Depois de **goal is**, use **to + verbo** para a ação pretendida.",
        "Nomeie a meta, marque seu prazo e diga qual ação concreta você está realizando para alcançá-la.",
        _b1_b2_exercises(
            "Traduza: Meu objetivo é melhorar meu inglês.",
            "my goal is to improve my english",
            "O que significa 'short-term goal'?",
            "Um objetivo de curto prazo.",
            ["Um objetivo de curto prazo.", "Um objetivo impossível.", "Um objetivo de outra pessoa."],
            "i am working towards my main goal",
            "Diga que você quer alcançar seus objetivos.",
            "i want to achieve my goals",
        ),
    ),
})


# ============================================================
# Complementos do modulo 11 - Listening B1
# ============================================================

B1_B2_TOPIC_ENHANCEMENTS.update({
    "entendendo-fala-natural": _b1_b2_spec(
        "Entendendo fala natural",
        "Desenvolver estratégias para compreender fala contínua sem tentar decodificar cada som isoladamente.",
        "Na fala natural, palavras pequenas podem ser reduzidas e palavras vizinhas podem se ligar. Primeiro procure verbos, substantivos e números; depois use o contexto e uma segunda escuta para reconstruir a frase.",
        [
            ("I didn't catch the last part.", "Não entendi a última parte."),
            ("Could you say that again, please?", "Você poderia dizer isso novamente, por favor?"),
        ],
        "Não conclua que uma frase é impossível só porque não ouviu cada palavra. **Gonna** é comum na fala informal, mas em texto formal prefira **going to**.",
        "Capte a ideia geral, identifique palavras-chave, peça repetição quando necessário e só então confira os detalhes.",
        _b1_b2_exercises(
            "Traduza: Não entendi a última parte.",
            "i didn't catch the last part",
            "Qual é a melhor primeira estratégia para fala rápida?",
            "Focar nas palavras-chave e no contexto.",
            ["Focar nas palavras-chave e no contexto.", "Ouvir cada letra separadamente.", "Parar a conversa imediatamente."],
            "what are you doing after work",
            "Peça educadamente para a pessoa repetir.",
            "could you say that again please",
        ),
    ),
    "sotaques-diferentes": _b1_b2_spec(
        "Sotaques diferentes",
        "Reconhecer variações de pronúncia e vocabulário sem concluir que o falante está usando outra língua.",
        "Sotaques podem mudar sons, ritmo e entonação; algumas variedades também preferem palavras diferentes, como **apartment/flat** e **elevator/lift**. A gramática central continua sendo inglês.",
        [
            ("I am learning to understand different accents.", "Estou aprendendo a entender sotaques diferentes."),
            ("In British English, people often say 'flat'.", "No inglês britânico, as pessoas costumam dizer ‘flat’."),
        ],
        "Não trate uma diferença de sotaque como erro. Se a palavra não for clara, use o contexto ou peça repetição: **Sorry, could you repeat that?**.",
        "Ouça variedades diferentes, anote palavras equivalentes e concentre-se no sentido antes de julgar a pronúncia.",
        _b1_b2_exercises(
            "Traduza: Estou aprendendo a entender sotaques diferentes.",
            "i am learning to understand different accents",
            "Qual palavra britânica corresponde a 'elevator'?",
            "lift",
            ["lift", "flat", "movie"],
            "sorry could you repeat that",
            "Diga que sotaques podem ter ritmos diferentes.",
            "accents can have different rhythms",
        ),
    ),
    "fala-reduzida": _b1_b2_spec(
        "Fala reduzida",
        "Reconhecer formas informais reduzidas em conversas, músicas e filmes, sem usá-las indiscriminadamente na escrita.",
        "**Gonna** corresponde a *going to*, **wanna** a *want to*, **gotta** a *have got to* e **kinda** a *kind of*. Essas formas representam pronúncia informal e não substituem automaticamente as formas completas em textos formais.",
        [
            ("I wanna go home.", "Quero ir para casa."),
            ("We gotta leave now.", "Temos que sair agora."),
        ],
        "Não use *wanna* antes de um substantivo como se fosse *want a*: **I want a coffee** não vira *I wanna coffee*. Em um e-mail formal, prefira a forma completa.",
        "Reconheça a redução pelo contexto, expanda mentalmente para a forma completa e ajuste o registro ao falar ou escrever.",
        _b1_b2_exercises(
            "Traduza: Temos que sair agora.",
            "we gotta leave now",
            "Em conversa informal, 'gonna' corresponde a:",
            "going to",
            ["going to", "want to", "have to"],
            "i wanna call you later",
            "Diga a forma completa de 'I gotta study'.",
            "i have got to study",
        ),
    ),
    "fala-conectada": _b1_b2_spec(
        "Fala conectada",
        "Perceber como os sons se ligam entre palavras e repetir blocos de fala com mais fluidez.",
        "Na fala conectada, o final de uma palavra pode se aproximar do início da seguinte: **turn it off** e **come in** formam blocos sonoros. A escrita não muda; muda a maneira como a frase flui.",
        [
            ("Turn it off before you leave.", "Desligue antes de sair."),
            ("Come in and take a seat.", "Entre e sente-se."),
        ],
        "Não tente inserir pausas entre todas as palavras. A ligação não cria palavras novas; ela apenas reduz a fronteira sonora entre palavras conhecidas.",
        "Ouça um bloco curto, marque onde os sons se ligam, repita devagar e depois imite o ritmo natural.",
        _b1_b2_exercises(
            "Traduza: Desligue antes de sair.",
            "turn it off before you leave",
            "O que é fala conectada?",
            "A ligação de sons entre palavras na fala.",
            ["A ligação de sons entre palavras na fala.", "Uma nova regra de ortografia.", "Uma lista de gírias."],
            "he is coming at ten",
            "Repita a frase conectando as palavras naturalmente.",
            "come in and take a seat",
        ),
    ),
    "contracoes-comuns": _b1_b2_spec(
        "Contrações comuns",
        "Reconhecer contrações frequentes e distinguir palavras que têm som parecido, mas função diferente.",
        "Contrações juntam palavras: **I’m = I am**, **they’re = they are**, **won’t = will not** e **can’t = cannot**. Na escuta, compare o contexto para não confundir **it’s/its**, **they’re/their/there**.",
        [
            ("They're waiting outside.", "Eles estão esperando lá fora."),
            ("It's a problem, but it isn't serious.", "É um problema, mas não é grave."),
        ],
        "Não confunda **they’re** (they are) com **their** (deles) nem **there** (lá). A pronúncia pode ser parecida, mas a função e o contexto mudam.",
        "Expanda a contração mentalmente, confirme o sentido pelo contexto e reconheça a forma negativa correta.",
        _b1_b2_exercises(
            "Traduza: Eles estão esperando lá fora.",
            "they are waiting outside",
            "Qual é a expansão de 'won't'?",
            "will not",
            ["will not", "would not", "want not"],
            "she doesn't like noisy places",
            "Diga que você ligará mais tarde.",
            "i will call you later",
        ),
    ),
    "identificando-palavras-chave": _b1_b2_spec(
        "Identificando palavras-chave",
        "Captar o tema e as informações principais de um áudio mesmo quando palavras pequenas não ficam claras.",
        "Substantivos, verbos, adjetivos, números e nomes próprios carregam grande parte do sentido. Artigos e preposições ajudam na gramática, mas normalmente recebem menos destaque na pronúncia.",
        [
            ("The meeting is at three on Friday.", "A reunião é às três na sexta-feira."),
            ("Maria bought a new laptop yesterday.", "Maria comprou um laptop novo ontem."),
        ],
        "Não ignore tudo que não for substantivo: marcadores de tempo e negações, como **not**, podem mudar a mensagem. Use as palavras-chave como pistas, não como a frase inteira.",
        "Ouça primeiro quem, o quê, quando e onde; depois preencha as palavras de ligação e confirme a negação.",
        _b1_b2_exercises(
            "Traduza: A reunião é às três na sexta-feira.",
            "the meeting is at three on friday",
            "Em um áudio sobre uma compra, quais palavras são mais úteis primeiro?",
            "A pessoa, o objeto e o momento.",
            ["A pessoa, o objeto e o momento.", "Somente os artigos.", "A pontuação escrita."],
            "the train leaves at seven tomorrow",
            "Diga em inglês: A aula começa às nove.",
            "the class starts at nine",
        ),
    ),
    "entendendo-contexto": _b1_b2_spec(
        "Entendendo pelo contexto",
        "Usar situação, tom e informações vizinhas para inferir uma palavra ou intenção desconhecida.",
        "O contexto inclui o lugar, o que aconteceu antes, a relação entre as pessoas e o tom. Em um restaurante, **I’d like the menu** é um pedido; na rua, **Where is the station?** é uma pergunta de direção.",
        [
            ("I'd like the menu, please.", "Eu gostaria do cardápio, por favor."),
            ("Could you repeat that in other words?", "Você poderia dizer isso com outras palavras?"),
        ],
        "Não traduza uma palavra isolada antes de ouvir a situação inteira. **Really?** pode mostrar surpresa, dúvida ou interesse conforme a entonação.",
        "Use as pistas disponíveis, formule uma hipótese de sentido e peça esclarecimento se ainda faltar informação.",
        _b1_b2_exercises(
            "Traduza: Eu gostaria do cardápio, por favor.",
            "i would like the menu please",
            "O que fazer ao encontrar uma palavra desconhecida em um áudio?",
            "Usar o contexto e as palavras ao redor.",
            ["Usar o contexto e as palavras ao redor.", "Parar sem ouvir o resto.", "Traduzir cada som isolado."],
            "it is raining outside today",
            "Peça para a pessoa dizer de outro jeito.",
            "could you say that in other words",
        ),
    ),
    "entendendo-conversas": _b1_b2_spec(
        "Entendendo conversas",
        "Acompanhar uma conversa identificando perguntas, respostas, mudança de turno e preenchedores.",
        "Em uma conversa, a pergunta cria uma expectativa e a resposta vem em seguida. **Well**, **you know**, **right** e **uh-huh** organizam o turno ou mostram que alguém está ouvindo, mas não carregam todo o conteúdo.",
        [
            ("Do you like pizza? — Yes, I do.", "Você gosta de pizza? — Sim, gosto."),
            ("Well, I think we should wait.", "Bem, acho que deveríamos esperar."),
        ],
        "Não trate **uh-huh** como uma palavra de conteúdo ou como sinal de raiva. Ele costuma indicar atenção ou concordância; escute o restante para saber qual dos dois.",
        "Localize a pergunta, antecipe o tipo de resposta, ignore o filler quando necessário e acompanhe a troca de turnos.",
        _b1_b2_exercises(
            "Traduza: Você gosta de pizza? — Sim, gosto.",
            "do you like pizza yes i do",
            "Qual parte da conversa normalmente responde à pergunta?",
            "A fala seguinte do interlocutor.",
            ["A fala seguinte do interlocutor.", "O silêncio final.", "A primeira palavra apenas."],
            "well i think we should wait",
            "Mostre que você está ouvindo com uma resposta curta.",
            "uh huh i understand",
        ),
    ),
    "entendendo-podcasts": _b1_b2_spec(
        "Entendendo podcasts",
        "Criar uma rotina de escuta de podcasts curtos, usando repetição e transcrição de forma estratégica.",
        "Na primeira escuta, procure tema e ideia geral; na segunda, anote palavras-chave; depois confira a transcrição e repita trechos difíceis. Reduzir a velocidade ajuda no começo, mas o objetivo é voltar gradualmente ao ritmo normal.",
        [
            ("Welcome to the show. Today we talk about travel.", "Bem-vindos ao programa. Hoje falamos sobre viagens."),
            ("Please play that part again.", "Por favor, reproduza essa parte novamente."),
        ],
        "Não transforme a transcrição em tradução palavra por palavra. Ela serve para confirmar o que foi ouvido e revelar padrões que você tentará reconhecer na próxima vez.",
        "Escolha um áudio curto, ouça pelo sentido geral, repita com apoio da transcrição e registre uma pequena meta para a próxima escuta.",
        _b1_b2_exercises(
            "Traduza: Hoje falamos sobre viagens.",
            "today we talk about travel",
            "Qual sequência favorece o aprendizado com um podcast?",
            "Ouvir pelo sentido, repetir e conferir a transcrição.",
            ["Ouvir pelo sentido, repetir e conferir a transcrição.", "Traduzir cada palavra antes de ouvir.", "Ouvir uma vez e nunca revisar."],
            "welcome to the show",
            "Peça para reproduzir uma parte novamente.",
            "please play that part again",
        ),
    ),
    "entendendo-videos": _b1_b2_spec(
        "Entendendo vídeos",
        "Combinar imagem, gestos, legendas e áudio para compreender vídeos em inglês.",
        "Na primeira vez, use imagem e legenda em inglês para construir contexto; depois tente sem legenda e volte apenas ao trecho difícil. **Rewind**, **pause**, **subtitles** e **captions** são comandos úteis durante o estudo.",
        [
            ("Let's get started.", "Vamos começar."),
            ("Watch this video again without subtitles.", "Assista a este vídeo novamente sem legendas."),
        ],
        "Não dependa sempre de legendas em português: elas podem desviar a atenção do som. Legendas em inglês ajudam a ligar o que você ouve ao que está escrito.",
        "Use a imagem para prever o sentido, a legenda em inglês para conferir e uma segunda exibição sem apoio para testar a compreensão.",
        _b1_b2_exercises(
            "Traduza: Assista a este vídeo novamente sem legendas.",
            "watch this video again without subtitles",
            "Qual apoio é específico do vídeo e não está disponível em um áudio puro?",
            "Imagem e gestos.",
            ["Imagem e gestos.", "Somente a pontuação.", "Um dicionário automático."],
            "let's get started with the video",
            "Diga para pausar o vídeo.",
            "pause the video please",
        ),
    ),
})


# ============================================================
# Complementos do modulo 12 - Gramatica B2
# ============================================================

B1_B2_TOPIC_ENHANCEMENTS.update({
    "presente-perfeito-avancado": _b1_b2_spec(
        "Presente Perfeito Contínuo",
        "Enfatizar a duração ou a atividade recente de uma ação que começou no passado.",
        "Use **have/has been + verbo-ing** com **for** para duração e **since** para o ponto inicial. O contínuo destaca o processo; o presente perfeito simples destaca mais o resultado ou a quantidade concluída.",
        [
            ("I have been studying for three hours.", "Estou estudando há três horas."),
            ("She has been working since Monday.", "Ela está trabalhando desde segunda-feira."),
        ],
        "Não diga *I have been study*; depois de **been**, use **-ing**. **For three years** indica duração, enquanto **since 2020** indica o início.",
        "Use **have/has been + -ing**, escolha **for/since** corretamente e compare duração com resultado quando necessário.",
        _b1_b2_exercises(
            "Traduza: Estou estudando há três horas.",
            "i have been studying for three hours",
            "Qual frase enfatiza a duração de uma ação?",
            "They have been waiting since noon.",
            ["They have been waiting since noon.", "They waited yesterday.", "They will wait tomorrow."],
            "have you been working all morning",
            "Diga que ela está aprendendo inglês desde 2020.",
            "she has been learning english since 2020",
        ),
    ),
    "terceiro-condicional": _b1_b2_spec(
        "Terceiro Condicional",
        "Falar de uma condição irreal no passado e de um resultado que não aconteceu.",
        "A estrutura é **if + past perfect, would have + particípio**: **If I had known, I would have called**. Ela é útil para arrependimentos, explicações alternativas e hipóteses sobre eventos concluídos.",
        [
            ("If she had studied, she would have passed.", "Se ela tivesse estudado, teria passado."),
            ("If we had left earlier, we would have arrived on time.", "Se tivéssemos saído mais cedo, teríamos chegado na hora."),
        ],
        "Não coloque *would* na oração com **if**. Diga **If I had known**, não *If I would have known*; o resultado recebe **would have + particípio**.",
        "Identifique que os dois eventos ficaram no passado, use **had + particípio** na condição e **would have + particípio** no resultado.",
        _b1_b2_exercises(
            "Traduza: Se ela tivesse estudado, teria passado.",
            "if she had studied she would have passed",
            "O terceiro condicional fala de:",
            "Uma possibilidade irreal no passado.",
            ["Uma possibilidade irreal no passado.", "Uma rotina atual.", "Um horário futuro fixo."],
            "if i had known i would have helped you",
            "Diga o que você teria feito se tivesse mais informação.",
            "i would have acted differently if i had known",
        ),
    ),
    "condicionais-mistas": _b1_b2_spec(
        "Condicionais mistas",
        "Relacionar uma condição passada a um resultado presente, ou uma condição presente a um resultado passado.",
        "No padrão mais comum, use **if + past perfect** para a condição passada e **would + verbo** para o resultado atual: **If I had taken the job, I would be richer now**. A combinação de tempos mostra que causa e consequência pertencem a momentos diferentes.",
        [
            ("If I had taken the job, I would be happier now.", "Se eu tivesse aceitado o emprego, estaria mais feliz agora."),
            ("If I were more organized, I would have finished yesterday.", "Se eu fosse mais organizado, teria terminado ontem."),
        ],
        "Não trate toda condicional como terceiro condicional. Se o resultado contém **now**, normalmente ele descreve o presente e pede **would + verbo**, não **would have + particípio**.",
        "Localize o tempo da condição e o tempo do resultado; combine passado perfeito e resultado presente quando essa for a relação.",
        _b1_b2_exercises(
            "Traduza: Se eu tivesse aceitado o emprego, estaria mais feliz agora.",
            "if i had taken the job i would be happier now",
            "Qual frase relaciona uma decisão passada a um resultado presente?",
            "If I had moved, I would live closer now.",
            ["If I had moved, I would live closer now.", "If I move, I will call you.", "If I moved yesterday, I called."],
            "if she had planned better she would have more time now",
            "Diga que, se você fosse mais organizado, teria terminado ontem.",
            "if i were more organized i would have finished yesterday",
        ),
    ),
    "modais-compostos": _b1_b2_spec(
        "Modais compostos",
        "Fazer deduções, críticas e avaliações sobre acontecimentos passados.",
        "Use **modal + have + particípio**. **Must have** indica uma dedução forte, **should have** indica algo esperado ou um arrependimento e **can’t have** indica impossibilidade. O modal não recebe *-s*.",
        [
            ("He must have missed the train.", "Ele deve ter perdido o trem."),
            ("You should have told me earlier.", "Você deveria ter me contado antes."),
        ],
        "**Must have** aqui não é obrigação passada; é dedução. Não diga *should had told*: a forma é **should have told**.",
        "Escolha o modal pelo sentido, use **have** e finalize com o particípio do verbo principal.",
        _b1_b2_exercises(
            "Traduza: Ele deve ter perdido o trem.",
            "he must have missed the train",
            "Qual frase expressa arrependimento?",
            "I should have called you.",
            ["I should have called you.", "I must call you tomorrow.", "I can call you now."],
            "she can't have forgotten the meeting",
            "Diga que eles provavelmente chegaram cedo.",
            "they must have arrived early",
        ),
    ),
    "passiva-avancada": _b1_b2_spec(
        "Passiva avançada",
        "Combinar voz passiva com modais e presente perfeito para expressar obrigação, possibilidade e resultado.",
        "A passiva com modal segue **modal + be + particípio**: **The report should be finished**. No presente perfeito, use **has/have been + particípio**: **The report has been completed**.",
        [
            ("The project should be finished by Friday.", "O projeto deve ser concluído até sexta-feira."),
            ("The report has been sent to the client.", "O relatório foi enviado ao cliente."),
        ],
        "Não diga *should is finished* nem *has been finish*. O modal pede **be** e o perfeito pede **been**; ambos precisam do particípio final.",
        "Identifique o auxiliar de modalidade ou de perfeito, acrescente **be/been** e mantenha o particípio da ação.",
        _b1_b2_exercises(
            "Traduza: O projeto deve ser concluído até sexta-feira.",
            "the project should be finished by friday",
            "Qual completa: 'The files have ___ uploaded'?",
            "been",
            ["been", "be", "being"],
            "the work can be completed today",
            "Diga que o relatório foi enviado ao cliente.",
            "the report has been sent to the client",
        ),
    ),
    "causativo": _b1_b2_spec(
        "Causativo",
        "Dizer que outra pessoa realizou um serviço para você usando **have/get something done**.",
        "Use **have/get + objeto + particípio**: **I had my car fixed** significa que alguém consertou o carro para mim. **Get** é mais informal; a estrutura não afirma que o sujeito realizou o serviço pessoalmente.",
        [
            ("I had my hair cut yesterday.", "Cortei o cabelo ontem, mandando cortar."),
            ("She got her computer repaired.", "Ela mandou consertar o computador."),
        ],
        "**I cut my hair** sugere que eu mesmo cortei o cabelo; **I had my hair cut** indica um serviço. Depois do objeto, use particípio: **had the car fixed**, não *had the car fix*.",
        "Escolha **have/get**, coloque o objeto no meio e use o particípio para o serviço realizado por outra pessoa.",
        _b1_b2_exercises(
            "Traduza: Ela mandou consertar o computador.",
            "she got her computer repaired",
            "O que a estrutura causativa enfatiza?",
            "Outra pessoa fez o serviço.",
            ["Outra pessoa fez o serviço.", "O sujeito fez tudo sozinho.", "Ninguém fez o serviço."],
            "we had the kitchen painted last year",
            "Diga que você mandou revisar o carro.",
            "i had my car checked",
        ),
    ),
    "discurso-indireto-avancado": _b1_b2_spec(
        "Discurso indireto avançado",
        "Relatar perguntas, ordens, pedidos e sugestões sem reproduzir a fala diretamente.",
        "Para perguntas de sim/não, use **asked if/whether**; para perguntas com *wh*, preserve a palavra interrogativa e use ordem afirmativa. Para ordens, use **told/asked + objeto + to**; para proibições, **not to**.",
        [
            ("He asked me where I lived.", "Ele me perguntou onde eu morava."),
            ("She told us not to leave.", "Ela nos disse para não sairmos."),
        ],
        "Não mantenha a ordem de pergunta dentro do discurso indireto: diga **He asked where I lived**, não *where did I live*. Depois de **told me**, inclua a pessoa antes de **to**.",
        "Identifique o tipo de fala, escolha **if**, uma *wh-word* ou **to/not to**, e ajuste o tempo quando necessário.",
        _b1_b2_exercises(
            "Traduza: Ele me perguntou onde eu morava.",
            "he asked me where i lived",
            "Como relatar 'Are you ready?'?",
            "She asked if I was ready.",
            ["She asked if I was ready.", "She asked that I am ready.", "She told if I ready."],
            "she told me not to worry",
            "Relate uma ordem: 'Please wait.'",
            "he asked me to wait",
        ),
    ),
    "inversao-adverbios-negativos": _b1_b2_spec(
        "Inversão com advérbios negativos",
        "Reconhecer e formar a inversão formal que ocorre quando certos advérbios negativos iniciam a frase.",
        "Com **never, rarely, seldom** e **not only** no início, coloque o auxiliar antes do sujeito: **Never have I seen...** e **Rarely do they travel**. A estrutura é mais formal e não muda o significado básico.",
        [
            ("Never have I seen such a view.", "Nunca vi uma vista assim."),
            ("Not only did she sing, but she also danced.", "Ela não só cantou, como também dançou."),
        ],
        "Não use a ordem normal *Never I have seen*. Se a frase não tiver auxiliar, acrescente **do/does/did** conforme o tempo: **Rarely do they complain**.",
        "Coloque o advérbio negativo primeiro, inverta auxiliar e sujeito e mantenha o verbo principal na forma adequada.",
        _b1_b2_exercises(
            "Traduza: Nunca vi uma vista assim.",
            "never have i seen such a view",
            "Qual frase apresenta inversão correta?",
            "Rarely do they complain.",
            ["Rarely do they complain.", "Rarely they do complain.", "Rarely complain they do."],
            "not only did he apologize but he also changed",
            "Diga que você raramente assiste a esse programa.",
            "rarely do i watch this show",
        ),
    ),
    "oracoes-relativas-reduzidas": _b1_b2_spec(
        "Orações relativas reduzidas",
        "Tornar frases mais concisas removendo **who/which + be** quando a redução for clara.",
        "Use **-ing** quando o antecedente realiza a ação: **the woman sitting there**. Use particípio passado quando o antecedente recebe a ação: **the documents signed yesterday**. O sujeito da oração reduzida precisa ser o mesmo do nome explicado.",
        [
            ("The woman sitting there is my teacher.", "A mulher sentada ali é minha professora."),
            ("The documents signed yesterday are ready.", "Os documentos assinados ontem estão prontos."),
        ],
        "Não reduza uma oração se isso criar ambiguidade ou trocar o agente. **The man running** é ativo; **the car repaired** é passivo.",
        "Identifique se o antecedente faz ou recebe a ação, remova a parte redundante e preserve **-ing** ou o particípio.",
        _b1_b2_exercises(
            "Traduza: A mulher sentada ali é minha professora.",
            "the woman sitting there is my teacher",
            "Qual é a forma reduzida de 'the documents that were signed yesterday'?",
            "the documents signed yesterday",
            ["the documents signed yesterday", "the documents signing yesterday", "the documents that signing"],
            "the people waiting outside are my friends",
            "Diga que o relatório enviado ontem está completo.",
            "the report sent yesterday is complete",
        ),
    ),
    "gerundio-infinitivo-avancado": _b1_b2_spec(
        "Gerúndio e infinitivo avançados",
        "Distinguir mudanças de sentido causadas por gerúndio ou infinitivo depois de verbos como remember, stop, try e regret.",
        "**Remember + -ing** recorda uma ação passada; **remember + to** significa não esquecer uma ação. **Stop + -ing** encerra uma atividade; **stop + to** interrompe algo para fazer outra coisa. **Try to** indica esforço e **try + -ing**, uma tentativa como solução.",
        [
            ("I remember locking the door.", "Lembro-me de ter trancado a porta."),
            ("She stopped to answer the phone.", "Ela parou para atender o telefone."),
        ],
        "Não trate as duas formas como intercambiáveis: **I stopped smoking** significa que parei de fumar; **I stopped to smoke** significa que parei outra atividade para fumar.",
        "Observe o sentido temporal ou de finalidade, escolha **-ing** ou **to + verbo** e confira o verbo que governa a estrutura.",
        _b1_b2_exercises(
            "Traduza: Ela parou para atender o telefone.",
            "she stopped to answer the phone",
            "Qual frase significa que a pessoa encerrou uma atividade?",
            "He stopped smoking.",
            ["He stopped smoking.", "He stopped to smoke.", "He remembered smoking."],
            "i tried opening the window but it was stuck",
            "Diga que você se lembrou de enviar o e-mail.",
            "i remembered to send the email",
        ),
    ),
    "estruturas-de-frase-complexas": _b1_b2_spec(
        "Estruturas de frase complexas",
        "Ligar ideias de contraste, causa e consequência em períodos claros e bem pontuados.",
        "**Although/even though** introduzem concessão com uma oração; **whereas** contrasta dois fatos; **therefore** e **as a result** apresentam consequência. **However** normalmente liga uma nova oração ou frase, não substitui *although* dentro da mesma estrutura.",
        [
            ("Although he was tired, he finished the work.", "Embora estivesse cansado, ele terminou o trabalho."),
            ("The costs increased; therefore, we changed the plan.", "Os custos aumentaram; portanto, mudamos o plano."),
        ],
        "Não diga *Although he was tired, but he finished*. **Although** já marca o contraste; use **however** em uma nova estrutura, sem duplicar a conjunção.",
        "Escolha o conectivo pela relação lógica, una as orações com pontuação clara e evite repetir duas marcas da mesma relação.",
        _b1_b2_exercises(
            "Traduza: Embora estivesse cansado, ele terminou o trabalho.",
            "although he was tired he finished the work",
            "Qual conectivo introduz consequência?",
            "Therefore, ...",
            ["Therefore, ...", "Although, ...", "Whereas, ..."],
            "even though it was late we continued working",
            "Una as ideias com contraste: ela gosta de chá, enquanto ele prefere café.",
            "she likes tea whereas he prefers coffee",
        ),
    ),
})


# ============================================================
# Complementos do modulo 13 - Vocabulario B2
# ============================================================

B1_B2_TOPIC_ENHANCEMENTS.update({
    "collocations": _b1_b2_spec(
        "Collocations",
        "Escolher combinações de palavras que soam naturais em inglês em vez de traduzir cada palavra isoladamente.",
        "Uma *collocation* é uma combinação frequente, como **make a decision**, **do homework**, **heavy rain** e **strong coffee**. O verbo português ‘fazer’ pode corresponder a **make** ou **do**, conforme a combinação.",
        [
            ("I need to make a decision.", "Preciso tomar uma decisão."),
            ("We had heavy rain yesterday.", "Tivemos chuva forte ontem."),
        ],
        "Não diga *do a decision* ou *strong rain*. Aprenda o bloco completo e observe se a palavra descreve atividade, criação, intensidade ou rotina.",
        "Memorize combinações em frases, destaque a palavra que acompanha o termo principal e revise o bloco como uma unidade.",
        _b1_b2_exercises(
            "Traduza: Preciso tomar uma decisão.",
            "i need to make a decision",
            "Qual combinação significa 'café forte'?",
            "strong coffee",
            ["strong coffee", "heavy coffee", "power coffee"],
            "we made a serious mistake",
            "Diga para alguém prestar atenção.",
            "please pay attention",
        ),
    ),
    "phrasal-verbs-avancados": _b1_b2_spec(
        "Phrasal verbs avançados",
        "Usar phrasal verbs frequentes em contextos de trabalho, tempo, relações e planos.",
        "**Run out of** significa ficar sem, **put off** significa adiar, **come across** encontrar por acaso e **carry on** continuar. **Look forward to** é seguido de substantivo ou gerúndio: **look forward to seeing you**.",
        [
            ("We ran out of time.", "Ficamos sem tempo."),
            ("I am looking forward to seeing you.", "Estou ansioso para ver você."),
        ],
        "Em **look forward to**, o **to** é preposição, não marcador de infinitivo; por isso dizemos **seeing**, não *to see*. Não confunda **put off** com cancelar definitivamente.",
        "Aprenda o sentido pelo contexto, observe a partícula fixa e verifique se o complemento exige gerúndio.",
        _b1_b2_exercises(
            "Traduza: Ficamos sem tempo.",
            "we ran out of time",
            "Complete: 'I look forward to ___ you.'",
            "seeing",
            ["seeing", "see", "saw"],
            "i came across an old photo",
            "Diga que você está ansioso para ver seus amigos.",
            "i am looking forward to seeing my friends",
        ),
    ),
    "expressoes-idiomaticas": _b1_b2_spec(
        "Expressões idiomáticas",
        "Compreender expressões figuradas comuns e escolher quando usá-las em situações informais.",
        "Idioms são blocos cujo sentido não é a soma literal das palavras: **piece of cake** significa algo muito fácil, **under the weather** indica indisposição e **hit the books** significa estudar bastante.",
        [
            ("The exam was a piece of cake.", "A prova foi muito fácil."),
            ("I am feeling under the weather today.", "Estou me sentindo indisposto hoje."),
        ],
        "Não traduza *break a leg* como um desejo literal de machucado: em contexto de apresentação, é uma forma tradicional de desejar boa sorte.",
        "Aprenda o idiom com uma situação e uma frase completa; confirme o sentido figurado antes de usá-lo.",
        _b1_b2_exercises(
            "Traduza: A prova foi muito fácil.",
            "the exam was a piece of cake",
            "Se alguém está 'under the weather', como está?",
            "Indisposto ou doente.",
            ["Indisposto ou doente.", "Muito rico.", "Com muita pressa."],
            "i am feeling under the weather today",
            "Deseje boa sorte a alguém que vai se apresentar.",
            "break a leg",
        ),
    ),
    "sinonimos": _b1_b2_spec(
        "Sinônimos",
        "Substituir palavras comuns por sinônimos adequados sem ignorar registro e nuance.",
        "Sinônimos compartilham parte do sentido, mas podem variar em formalidade ou intensidade. **Large** é próximo de *big*, **purchase** é mais formal que *buy* e **essential** é mais forte que *important* em alguns contextos.",
        [
            ("We purchased a new laptop.", "Compramos um laptop novo."),
            ("This is an essential part of the plan.", "Esta é uma parte essencial do plano."),
        ],
        "Não substitua palavras apenas porque aparecem no dicionário. **Purchase** funciona como verbo ou substantivo formal; em uma conversa casual, **buy** costuma ser mais natural.",
        "Compare sentido, registro e intensidade antes de trocar uma palavra por um sinônimo.",
        _b1_b2_exercises(
            "Traduza usando uma palavra mais formal: Compramos um laptop novo.",
            "we purchased a new laptop",
            "Qual é um sinônimo natural de 'begin'?",
            "start",
            ["start", "finish", "stop"],
            "this is an important decision",
            "Diga 'comprar' em um registro formal.",
            "purchase",
        ),
    ),
    "antonimos": _b1_b2_spec(
        "Antônimos",
        "Formar contrastes claros usando pares de palavras opostas em descrições e argumentos.",
        "Antônimos podem ser adjetivos (**strong/weak**), advérbios (**always/never**) ou verbos (**increase/decrease**). O contexto determina se o contraste descreve uma mudança ou dois estados simultâneos.",
        [
            ("Sales increased, then decreased.", "As vendas aumentaram e depois diminuíram."),
            ("The old phone was expensive, but the new one is cheap.", "O celular antigo era caro, mas o novo é barato."),
        ],
        "Não confunda **cheap** com *low-cost* em todo contexto: *cheap* pode sugerir baixa qualidade. Também não use **decrease** como adjetivo; é verbo ou substantivo.",
        "Aprenda os pares em uma frase de contraste e observe a classe gramatical de cada palavra.",
        _b1_b2_exercises(
            "Traduza: As vendas aumentaram e depois diminuíram.",
            "sales increased then decreased",
            "Qual é o antônimo de 'reliable'?",
            "unreliable",
            ["unreliable", "careful", "accurate"],
            "the opposite of expensive is cheap",
            "Diga que o novo plano é mais barato que o antigo.",
            "the new plan is cheaper than the old one",
        ),
    ),
    "formacao-de-palavras": _b1_b2_spec(
        "Formação de palavras",
        "Reconhecer famílias de palavras e escolher verbo, substantivo, adjetivo ou advérbio conforme a frase.",
        "Uma raiz pode formar várias classes: **succeed, success, successful, successfully**. Sufixos e mudanças de forma ajudam a prever a função, mas a frase mostra qual classe é necessária.",
        [
            ("She succeeded because she worked successfully.", "Ela teve sucesso porque trabalhou com sucesso."),
            ("The decision was difficult.", "A decisão foi difícil."),
        ],
        "Não escolha uma palavra da mesma família sem olhar a posição: depois de **the**, costuma vir um substantivo; depois de **be**, um adjetivo; depois de um verbo, pode vir um advérbio.",
        "Identifique a raiz, observe a função da lacuna e selecione a forma da família que combina com a estrutura.",
        _b1_b2_exercises(
            "Traduza: A decisão foi difícil.",
            "the decision was difficult",
            "Qual é o substantivo de 'decide'?",
            "decision",
            ["decision", "decisive", "decidingly"],
            "she completed the task successfully",
            "Diga que o resultado foi um sucesso.",
            "the result was a success",
        ),
    ),
    "prefixos": _b1_b2_spec(
        "Prefixos",
        "Inferir ou formar palavras com prefixos de negação, repetição, erro e excesso.",
        "Prefixos vêm antes da raiz. **un-/in-/im-/dis-** frequentemente negam, **re-** indica repetição, **mis-** indica erro e **over-** sugere excesso. A forma depende da palavra: *possible* vira **impossible**.",
        [
            ("Please reread the instructions.", "Por favor, releia as instruções."),
            ("The answer is impossible to verify.", "É impossível verificar a resposta."),
        ],
        "Não escolha o prefixo apenas pela tradução de ‘não’: algumas combinações são fixas, como **impossible**, não *unpossible*. O prefixo não substitui a revisão da grafia.",
        "Reconheça a raiz, associe o prefixo ao sentido e confira a forma convencional da palavra resultante.",
        _b1_b2_exercises(
            "Traduza: Por favor, releia as instruções.",
            "please reread the instructions",
            "Qual prefixo significa 'de novo'?",
            "re-",
            ["re-", "mis-", "over-"],
            "this answer is impossible to verify",
            "Forme o oposto de 'reliable'.",
            "unreliable",
        ),
    ),
    "sufixos": _b1_b2_spec(
        "Sufixos",
        "Usar sufixos para reconhecer ou formar substantivos, adjetivos e advérbios.",
        "**-ful** e **-less** formam adjetivos, **-ness**, **-tion** e **-ment** formam substantivos e **-ly** costuma formar advérbios. A raiz pode sofrer pequena mudança de grafia, como *happy → happiness*.",
        [
            ("She is a careful driver.", "Ela é uma motorista cuidadosa."),
            ("His kindness helped everyone.", "A bondade dele ajudou todos."),
        ],
        "Não confunda **careful** (cuidadoso) com **carefully** (cuidadosamente) nem **careless** (descuidado) com ‘sem cuidado’ como uma ação. A posição na frase revela a classe.",
        "Observe a função necessária, escolha o sufixo correspondente e revise a grafia da raiz transformada.",
        _b1_b2_exercises(
            "Traduza: Ela é uma motorista cuidadosa.",
            "she is a careful driver",
            "Qual sufixo forma um substantivo de qualidade em 'kindness'?",
            "-ness",
            ["-ness", "-ful", "-ly"],
            "he answered the question carefully",
            "Forme o adjetivo de 'hope' com '-ful'.",
            "hopeful",
        ),
    ),
    "vocabulario-academico": _b1_b2_spec(
        "Vocabulário acadêmico",
        "Ler e produzir frases sobre análise, dados, hipóteses, evidências e conclusões.",
        "**Analyze** é analisar, **evidence** é evidência, **hypothesis** é hipótese e **conclusion** é conclusão. **Significant** pode significar significativo ou importante; o contexto acadêmico mostra o sentido.",
        [
            ("The study analyzes the available data.", "O estudo analisa os dados disponíveis."),
            ("The evidence supports the hypothesis.", "As evidências apoiam a hipótese."),
        ],
        "Não confunda **conclusion** com *summary*: uma conclusão interpreta ou fecha o raciocínio; um resumo apenas apresenta os pontos principais.",
        "Use o vocabulário em uma sequência de pesquisa: analisar dados, testar hipótese, avaliar evidências e chegar a uma conclusão.",
        _b1_b2_exercises(
            "Traduza: As evidências apoiam a hipótese.",
            "the evidence supports the hypothesis",
            "Qual palavra significa 'abordagem' em um estudo?",
            "approach",
            ["approach", "conclusion", "mistake"],
            "the study presents significant results",
            "Diga que o estudo analisa os dados disponíveis.",
            "the study analyzes the available data",
        ),
    ),
    "vocabulario-profissional": _b1_b2_spec(
        "Vocabulário profissional",
        "Usar termos de projetos, reuniões, partes interessadas, entregáveis e negociação.",
        "**Stakeholder** é parte interessada, **deliverable** é entregável, **implement** é implementar e **feedback** é retorno ou avaliação. Em reuniões, **agenda** é pauta; para agenda pessoal, prefira **calendar** ou **schedule**.",
        [
            ("The stakeholders reviewed the deliverables.", "As partes interessadas revisaram os entregáveis."),
            ("We need feedback before we implement the plan.", "Precisamos de retorno antes de implementar o plano."),
        ],
        "Não traduza automaticamente **agenda** como agenda de compromissos. Em uma reunião, é a lista de assuntos; o calendário pessoal é **calendar**.",
        "Identifique as pessoas afetadas, o que será entregue, como será implementado e qual retorno ainda é necessário.",
        _b1_b2_exercises(
            "Traduza: Precisamos de retorno antes de implementar o plano.",
            "we need feedback before we implement the plan",
            "Quem é um stakeholder?",
            "Uma parte interessada no projeto.",
            ["Uma parte interessada no projeto.", "Um erro de digitação.", "Um horário do calendário."],
            "let's negotiate the contract tomorrow",
            "Diga que os entregáveis estão prontos para revisão.",
            "the deliverables are ready for review",
        ),
    ),
    "registro-formal": _b1_b2_spec(
        "Registro formal",
        "Adaptar vocabulário e estruturas a e-mails profissionais, cartas e comunicações oficiais.",
        "No registro formal, prefira frases completas, cortesia e formas como **I would like to**, **I am writing to** e **Regarding**. Contrações e gírias são menos adequadas quando a audiência espera distância profissional.",
        [
            ("I am writing to confirm the meeting.", "Escrevo para confirmar a reunião."),
            ("I would like to request further information.", "Gostaria de solicitar mais informações."),
        ],
        "Não use *Hey, send me the file* em uma solicitação formal. **I would like to request** é polido e não significa que você está sendo indeciso.",
        "Identifique a audiência, substitua a forma casual pela formal e mantenha o pedido claro e cortês.",
        _b1_b2_exercises(
            "Traduza em registro formal: Gostaria de solicitar mais informações.",
            "i would like to request further information",
            "Qual abertura é adequada para um e-mail profissional?",
            "I am writing to confirm...",
            ["I am writing to confirm...", "Hey, check this!", "Wanna know..."],
            "regarding your request we need more details",
            "Faça um pedido formal para receber uma resposta.",
            "i would appreciate your reply",
        ),
    ),
    "registro-informal": _b1_b2_spec(
        "Registro informal",
        "Reconhecer e usar expressões naturais em mensagens para amigos e conversas descontraídas.",
        "No registro informal, contrações e expressões como **Hey**, **How’s it going?**, **No worries** e **Catch you later** são comuns. A informalidade não elimina a clareza; ela apenas ajusta o tom à relação.",
        [
            ("Hey! How's it going?", "E aí! Como vai?"),
            ("No worries. Catch you later!", "Sem problema. Até mais!"),
        ],
        "Não use **gonna** ou gíria em qualquer texto: a escolha depende da audiência. Uma mensagem a um amigo pode ser informal; um relatório profissional pede outra linguagem.",
        "Reconheça a relação e o canal, use contrações com naturalidade e evite informalidade quando o contexto exigir formalidade.",
        _b1_b2_exercises(
            "Traduza em registro informal: E aí! Como vai?",
            "hey how's it going",
            "Qual resposta combina com 'How's it going?'?",
            "Pretty good, thanks.",
            ["Pretty good, thanks.", "Dear Sir or Madam.", "I hereby request."],
            "no worries catch you later",
            "Despeça-se informalmente de um amigo.",
            "catch you later",
        ),
    ),
})


# ============================================================
# Complementos do modulo 14 - Ingles Natural B2
# ============================================================

B1_B2_TOPIC_ENHANCEMENTS.update({
    "contracoes-naturais": _b1_b2_spec(
        "Contrações naturais",
        "Reconhecer contrações simples e duplas que aparecem na fala informal e escolher quando escrevê-las.",
        "Contrações simples são comuns em fala e escrita informal: **I’m**, **they’ve**, **won’t**. Contrações duplas, como **I’d’ve** (= *I would have*), são principalmente faladas e devem ser expandidas em texto formal.",
        [
            ("They've already left.", "Eles já foram embora."),
            ("I'd have helped if I had known.", "Eu teria ajudado se soubesse."),
        ],
        "Não confunda **I’d** sem contexto: pode significar *I would* ou *I had*. Em um relatório, prefira **I would have** em vez de uma contração dupla.",
        "Reconheça a contração pelo auxiliar e pelo contexto, expanda mentalmente e adapte a forma ao registro.",
        _b1_b2_exercises(
            "Traduza: Eles já foram embora.",
            "they have already left",
            "O que 'I'd've' representa na fala?",
            "I would have",
            ["I would have", "I had been", "I will have"],
            "i wouldn't have done that",
            "Diga a forma completa de 'they've finished'.",
            "they have finished",
        ),
    ),
    "fala-conectada-avancada": _b1_b2_spec(
        "Fala conectada avançada",
        "Reconhecer ligações entre consoante e vogal e praticar frases como blocos sonoros.",
        "Quando uma palavra termina em consoante e a seguinte começa em vogal, os sons podem se ligar: **pick it up** flui como um bloco. O objetivo é ouvir a sequência, não alterar a ortografia nem inserir sons aleatórios.",
        [
            ("Pick it up from the floor.", "Pegue isso do chão."),
            ("I want to eat outside.", "Quero comer fora."),
        ],
        "Não transforme a ligação em uma nova palavra no texto. Ela é um fenômeno de pronúncia e varia com velocidade, sotaque e ênfase.",
        "Marque os limites entre palavras, ouça a ligação, repita em blocos e mantenha a forma escrita original.",
        _b1_b2_exercises(
            "Traduza: Pegue isso do chão.",
            "pick it up from the floor",
            "O que a fala conectada muda principalmente?",
            "O fluxo dos sons entre palavras.",
            ["O fluxo dos sons entre palavras.", "A ortografia oficial.", "O significado de todos os verbos."],
            "i want to eat outside tonight",
            "Repita a frase como dois blocos: 'pick it up'.",
            "pick it up",
        ),
    ),
    "reducoes-naturais": _b1_b2_spec(
        "Reduções naturais",
        "Compreender reduções frequentes e diferenciar fala espontânea de escrita formal.",
        "Em fala informal, **going to** pode soar como *gonna*, **want to** como *wanna*, **have to** como *hafta* e **let me** como *lemme*. São pistas de escuta e escolhas de registro, não novas regras gramaticais.",
        [
            ("I'm gonna call you later.", "Vou ligar para você mais tarde."),
            ("Lemme check the schedule.", "Deixe-me verificar o horário."),
        ],
        "Não escreva *gonna* em uma redação formal sem uma razão estilística. E não confunda **wanna** com **want a**: o complemento mostra se vem verbo ou substantivo.",
        "Expanda a redução para confirmar o sentido, pratique a pronúncia em uma frase e escolha a forma completa quando o registro exigir.",
        _b1_b2_exercises(
            "Traduza: Vou ligar para você mais tarde.",
            "i am gonna call you later",
            "Em um relatório formal, qual forma é preferível?",
            "I am going to",
            ["I am going to", "I'm gonna", "Wanna"],
            "lemme check the schedule",
            "Diga informalmente: quero ir para casa.",
            "i wanna go home",
        ),
    ),
    "entonacao": _b1_b2_spec(
        "Entonação",
        "Usar e reconhecer a melodia da fala para indicar pergunta, conclusão, surpresa ou continuidade.",
        "Perguntas de sim/não frequentemente sobem no final; afirmações e muitas perguntas com *wh* tendem a cair. A entonação também expressa atitude, portanto o mesmo **Really?** pode soar surpreso, desconfiado ou interessado.",
        [
            ("Are you ready?", "Você está pronto?"),
            ("Where are you going?", "Para onde você está indo?"),
        ],
        "Não use uma subida automática em toda frase. Uma pergunta com *wh* pode soar incompleta com a entonação errada, e uma afirmação pode parecer pergunta se subir demais.",
        "Observe o tipo de frase, ouça a queda ou subida final e repita tentando manter a intenção, não apenas as palavras.",
        _b1_b2_exercises(
            "Traduza: Você está pronto?",
            "are you ready",
            "Qual frase normalmente termina com entonação ascendente?",
            "Are you coming?",
            ["Are you coming?", "Where do you live?", "I live nearby."],
            "really you finished already",
            "Faça uma pergunta de sim ou não com entonação natural.",
            "do you need help",
        ),
    ),
    "acentuacao-stress": _b1_b2_spec(
        "Acentuação e stress",
        "Perceber qual sílaba ou palavra recebe destaque e usar esse destaque para comunicar contraste.",
        "O *word stress* destaca uma sílaba dentro da palavra; o *sentence stress* destaca palavras importantes na frase. Mudar o destaque pode corrigir uma informação: **I wanted the blue one**, não o vermelho.",
        [
            ("I wanted the BLUE one.", "Eu queria o azul."),
            ("She ordered a PREsent for him.", "Ela pediu um presente para ele."),
        ],
        "Não confunda *present* substantivo com *present* adjetivo/verbo: o stress pode mudar. Na frase, não dê o mesmo peso a artigos e preposições sem motivo.",
        "Encontre a informação nova, destaque a sílaba ou palavra relevante e reduza as palavras de apoio sem apagá-las.",
        _b1_b2_exercises(
            "Traduza: Eu queria o azul.",
            "i wanted the blue one",
            "O que o stress de uma palavra pode indicar?",
            "A sílaba mais proeminente da palavra.",
            ["A sílaba mais proeminente da palavra.", "A tradução completa.", "A pontuação da frase."],
            "i wanted the blue one not the green one",
            "Destaque oralmente 'tomorrow' em uma frase sobre um plano.",
            "i am leaving tomorrow",
        ),
    ),
    "ritmo-da-fala": _b1_b2_spec(
        "Ritmo da fala",
        "Acompanhar o ritmo do inglês agrupando palavras de conteúdo e reduzindo palavras funcionais.",
        "O inglês tende a dar mais tempo às palavras de conteúdo, como substantivos e verbos, e menos às palavras funcionais, como artigos e preposições. Falar em grupos de sentido é mais útil do que pronunciar cada palavra com a mesma duração.",
        [
            ("The TRAIN leaves at EIGHT.", "O trem sai às oito."),
            ("I NEED to FINISH the REPORT today.", "Preciso terminar o relatório hoje."),
        ],
        "Ritmo não significa falar rápido nem engolir sons sem controle. Mantenha as palavras gramaticais audíveis, mas dê destaque ao que traz a informação principal.",
        "Divida a frase em grupos, marque as palavras fortes e repita mantendo o sentido e a respiração naturais.",
        _b1_b2_exercises(
            "Traduza: O trem sai às oito.",
            "the train leaves at eight",
            "Quais palavras tendem a receber mais destaque?",
            "Substantivos, verbos, adjetivos e números.",
            ["Substantivos, verbos, adjetivos e números.", "Todos os artigos igualmente.", "Somente as vírgulas."],
            "i need to finish the report today",
            "Diga a frase em dois grupos de sentido: o trem chega às seis.",
            "the train arrives at six",
        ),
    ),
    "preenchedores-fillers": _b1_b2_spec(
        "Preenchedores (fillers)",
        "Usar pequenos marcadores para ganhar tempo, sinalizar hesitação e manter o turno de fala.",
        "**Well**, **um**, **you know**, **actually** e **basically** podem introduzir uma resposta, organizar uma ideia ou mostrar que o falante ainda está pensando. Eles não devem aparecer em toda frase.",
        [
            ("Well, I need to think about it.", "Bem, preciso pensar nisso."),
            ("Actually, I disagree with that idea.", "Na verdade, discordo dessa ideia."),
        ],
        "Não traduza cada filler literalmente: **you know** nem sempre pede informação, e **well** pode apenas ganhar tempo. Em escrita formal, reduza esses marcadores.",
        "Escolha um filler pelo efeito desejado, faça uma pausa curta e volte à ideia principal sem perder o turno.",
        _b1_b2_exercises(
            "Traduza: Bem, preciso pensar nisso.",
            "well i need to think about it",
            "Qual filler costuma introduzir uma correção ou informação inesperada?",
            "Actually, ...",
            ["Actually, ...", "Goodbye, ...", "Yesterday, ..."],
            "um i am not sure about the answer",
            "Ganhe tempo para responder usando 'well'.",
            "well let me think",
        ),
    ),
    "marcadores-de-conversa": _b1_b2_spec(
        "Marcadores de conversa",
        "Organizar mudança de assunto, retomada, conclusão e confirmação em conversas naturais.",
        "**By the way** introduz um assunto relacionado, **anyway** retoma ou encerra uma linha de pensamento, **so** pode iniciar uma conclusão e **right?** busca confirmação. O sentido depende da posição e do tom.",
        [
            ("By the way, did you call Anna?", "A propósito, você ligou para Anna?"),
            ("Anyway, let's get back to work.", "Enfim, vamos voltar ao trabalho."),
        ],
        "Não confunda **by the way** com **on the way**: o primeiro muda ou acrescenta assunto; o segundo indica estar a caminho.",
        "Identifique a função do marcador, use-o no ponto certo e mantenha a frase principal clara.",
        _b1_b2_exercises(
            "Traduza: A propósito, você ligou para Anna?",
            "by the way did you call anna",
            "Qual marcador retoma o assunto e pode encerrar uma digressão?",
            "Anyway, ...",
            ["Anyway, ...", "By the way, ...", "At the way, ..."],
            "so what should we do next",
            "Mude brevemente de assunto usando 'by the way'.",
            "by the way how was your trip",
        ),
    ),
    "expressoes-informais": _b1_b2_spec(
        "Expressões informais",
        "Reconhecer expressões casuais que tornam uma conversa entre conhecidos mais natural.",
        "Expressões como **hang out** (passar tempo junto), **grab a bite** (comer algo) e **no big deal** (não é problema) são blocos informais. Elas são adequadas quando a relação permite um tom descontraído.",
        [
            ("Do you want to hang out this weekend?", "Você quer passar um tempo comigo neste fim de semana?"),
            ("No big deal, we can try again.", "Não tem problema, podemos tentar de novo."),
        ],
        "Não use **grab a bite** em um documento formal sem explicar o contexto. A expressão significa fazer uma refeição rápida, não pegar uma mordida literalmente.",
        "Aprenda a expressão como um bloco, associe-a a uma situação social e ajuste o registro à pessoa com quem fala.",
        _b1_b2_exercises(
            "Traduza: Você quer passar um tempo comigo neste fim de semana?",
            "do you want to hang out this weekend",
            "O que significa 'no big deal'?",
            "Não tem problema.",
            ["Não tem problema.", "É um negócio enorme.", "É muito caro."],
            "let's grab a bite after work",
            "Diga informalmente que está tudo bem.",
            "no big deal",
        ),
    ),
    "girias-slang": _b1_b2_spec(
        "Gírias (slang)",
        "Reconhecer gírias comuns pelo contexto e evitar usá-las fora da relação ou do registro apropriado.",
        "Gíria é vocabulário muito informal e variável. **Awesome** pode significar ‘incrível’, **chill** pode significar ‘relaxar’ ou ‘tranquilo’ e **low-key** pode indicar algo discreto. O sentido depende da comunidade e da situação.",
        [
            ("That concert was awesome!", "Aquele show foi incrível!"),
            ("Let's just chill at home tonight.", "Vamos só relaxar em casa hoje à noite."),
        ],
        "Não use gíria em um e-mail formal sem intenção clara. Além disso, o significado pode mudar entre países e gerações; confirme o contexto em vez de adivinhar pela tradução literal.",
        "Reconheça a gíria, identifique a situação social e escolha uma alternativa neutra quando houver dúvida.",
        _b1_b2_exercises(
            "Traduza: Aquele show foi incrível!",
            "that concert was awesome",
            "Em uma mensagem informal, 'chill' pode significar:",
            "relaxar ou ficar tranquilo",
            ["relaxar ou ficar tranquilo", "trabalhar com urgência", "escrever um relatório"],
            "we had an awesome time together",
            "Diga que você quer relaxar em casa.",
            "i want to chill at home",
        ),
    ),
    "idioms-comuns": _b1_b2_spec(
        "Idioms comuns",
        "Compreender idioms muito frequentes e usá-los em situações em que o sentido figurado é esperado.",
        "**Break the ice** significa iniciar uma interação com menos tensão; **get the ball rolling** significa começar uma atividade; **be on the same page** significa compartilhar entendimento ou objetivo.",
        [
            ("The game helped break the ice.", "O jogo ajudou a quebrar o gelo."),
            ("Let's get the ball rolling on the project.", "Vamos começar o projeto."),
        ],
        "Não traduza o idiom literalmente sem olhar a situação. **On the same page** não fala de uma página física, mas de entendimento comum.",
        "Aprenda o idiom com a intenção comunicativa, reconheça o contexto e prefira uma paráfrase neutra quando necessário.",
        _b1_b2_exercises(
            "Traduza: O jogo ajudou a quebrar o gelo.",
            "the game helped break the ice",
            "O que significa 'be on the same page'?",
            "Ter o mesmo entendimento.",
            ["Ter o mesmo entendimento.", "Ler a mesma página em silêncio.", "Chegar atrasado."],
            "let's get the ball rolling on the project",
            "Diga que a atividade ajudou a iniciar a conversa.",
            "the activity helped break the ice",
        ),
    ),
    "fraseado-nativo": _b1_b2_spec(
        "Fraseado nativo",
        "Substituir traduções literais por blocos e combinações que os falantes realmente usam.",
        "Fraseado natural depende de *chunks*: **That makes sense**, **I was wondering if...** e **What do you feel like doing?**. A gramática continua importante, mas a escolha da combinação dá fluidez e adequação.",
        [
            ("I was wondering if you could help me.", "Eu queria saber se você poderia me ajudar."),
            ("What do you feel like doing tonight?", "O que você está com vontade de fazer hoje à noite?"),
        ],
        "Não traduza ‘estou me perguntando’ literalmente em um pedido polido: **I was wondering if...** é uma fórmula convencional. Aprenda a expressão inteira com seu tom.",
        "Observe blocos frequentes em situações reais, compare com traduções literais e pratique a fórmula completa.",
        _b1_b2_exercises(
            "Traduza de forma natural: Eu queria saber se você poderia me ajudar.",
            "i was wondering if you could help me",
            "Qual frase confirma que uma ideia é compreensível?",
            "That makes sense.",
            ["That makes sense.", "That makes a sense.", "That does sense it."],
            "what do you feel like doing tonight",
            "Faça um pedido polido usando 'I was wondering if'.",
            "i was wondering if you could send the file",
        ),
    ),
})


# ============================================================
# Complementos do modulo 15 - Speaking B2
# ============================================================

B1_B2_TOPIC_ENHANCEMENTS.update({
    "debates": _b1_b2_spec(
        "Debates",
        "Apresentar uma posição, reconhecer um ponto válido e responder com uma razão clara.",
        "Um debate produtivo combina **I’d like to argue that...**, reconhecimento (**That’s a valid point**) e resposta (**However...**). A cortesia não enfraquece o argumento; ela mostra que você entendeu a posição oposta.",
        [
            ("That's a valid point, but the evidence is limited.", "É um ponto válido, mas as evidências são limitadas."),
            ("I'd like to respond to that concern.", "Gostaria de responder a essa preocupação."),
        ],
        "Não use *You are wrong* como único argumento. Reconheça o ponto, apresente a diferença e sustente sua resposta com evidência ou exemplo.",
        "Estruture a fala em posição, reconhecimento, contraste e justificativa; termine deixando clara a conclusão.",
        _b1_b2_exercises(
            "Traduza: É um ponto válido, mas as evidências são limitadas.",
            "that's a valid point but the evidence is limited",
            "Qual expressão reconhece o argumento do outro antes da resposta?",
            "That's a valid point, but...",
            ["That's a valid point, but...", "You are completely wrong.", "I have nothing to add."],
            "i would like to respond to that concern",
            "Inicie uma posição em um debate.",
            "i'd like to argue that this is the best option",
        ),
    ),
    "apresentacoes-orais": _b1_b2_spec(
        "Apresentações orais",
        "Guiar o público por uma apresentação com abertura, transições, síntese e encerramento.",
        "Sinalize a estrutura com **I’d like to start by...**, **Let’s move on to...**, **To sum up...** e **Thank you for your attention**. O público precisa saber quando um ponto termina e outro começa.",
        [
            ("I'd like to start by introducing the topic.", "Gostaria de começar apresentando o tema."),
            ("To sum up, the results are encouraging.", "Para resumir, os resultados são animadores."),
        ],
        "Não leia os slides sem orientar a audiência. **Let’s move on to** faz a transição; **to sum up** resume e não deve introduzir um argumento totalmente novo.",
        "Abra com o objetivo, sinalize cada etapa, destaque a mensagem principal e agradeça ao público no final.",
        _b1_b2_exercises(
            "Traduza: Gostaria de começar apresentando o tema.",
            "i'd like to start by introducing the topic",
            "Qual expressão sinaliza uma transição?",
            "Let's move on to...",
            ["Let's move on to...", "Thank you for your attention.", "In my opinion only."],
            "to sum up the main point is clear",
            "Encerre uma apresentação agradecendo ao público.",
            "thank you for your attention",
        ),
    ),
    "discussoes": _b1_b2_spec(
        "Discussões",
        "Convidar outras pessoas para falar, comparar vantagens e organizar uma discussão produtiva.",
        "**What’s your take on...?** pede a opinião de alguém; **pros and cons** nomeia pontos positivos e negativos; **Let’s weigh...** convida o grupo a comparar antes de decidir.",
        [
            ("What's your take on the new plan?", "Qual é a sua opinião sobre o novo plano?"),
            ("Let's weigh the pros and cons first.", "Vamos avaliar os prós e os contras primeiro."),
        ],
        "Não confunda **take** nesse contexto com ‘pegar’. **What’s your take?** significa ‘qual é sua opinião?’, enquanto **take a break** significa fazer uma pausa.",
        "Peça opiniões, resuma os pontos favoráveis e contrários e convide o grupo a responder ao que foi dito.",
        _b1_b2_exercises(
            "Traduza: Vamos avaliar os prós e os contras primeiro.",
            "let's weigh the pros and cons first",
            "Qual pergunta pede a opinião de alguém?",
            "What's your take on this?",
            ["What's your take on this?", "What is your deadline?", "Where is the report?"],
            "i'd like to hear your opinion",
            "Pergunte a opinião de alguém sobre o plano.",
            "what's your take on the plan",
        ),
    ),
    "negociacoes": _b1_b2_spec(
        "Negociações",
        "Propor concessões, buscar um meio-termo e verificar condições para fechar um acordo.",
        "Use **find a middle ground** para buscar equilíbrio, **be willing to compromise** para mostrar flexibilidade e **close the deal** para concluir. Perguntas com **What would it take...?** exploram o que a outra parte precisa.",
        [
            ("I'm willing to compromise on the delivery date.", "Estou disposto a ceder quanto à data de entrega."),
            ("What would it take to close the deal?", "O que seria preciso para fechar o acordo?"),
        ],
        "Comprometer-se em uma negociação não significa aceitar tudo: **compromise** é encontrar um meio-termo. Evite prometer algo que não pode cumprir só para encerrar a conversa.",
        "Expresse a necessidade, reconheça a margem de concessão, proponha um meio-termo e confirme os termos finais.",
        _b1_b2_exercises(
            "Traduza: Estou disposto a ceder quanto à data de entrega.",
            "i am willing to compromise on the delivery date",
            "Qual frase busca uma solução equilibrada?",
            "Let's find a middle ground.",
            ["Let's find a middle ground.", "I want everything immediately.", "There is no discussion."],
            "can we make a deal today",
            "Pergunte o que seria preciso para fechar o acordo.",
            "what would it take to close the deal",
        ),
    ),
    "explicando-ideias-complexas": _b1_b2_spec(
        "Explicando ideias complexas",
        "Tornar um conceito difícil compreensível usando linguagem simples, etapas e exemplos.",
        "Use **To put it simply**, **The key point is...**, **What this means is...** e **Let me break it down** para controlar a explicação. Dividir uma ideia não é simplificá-la de modo incorreto; é revelar sua estrutura.",
        [
            ("To put it simply, the system saves time.", "Em termos simples, o sistema economiza tempo."),
            ("Let me break it down into three steps.", "Deixe-me dividir isso em três etapas."),
        ],
        "Não despeje jargão para parecer avançado. **Break it down** significa organizar em partes; depois de cada parte, verifique se a pessoa acompanhou.",
        "Apresente a ideia central, divida-a em partes, dê um exemplo e confirme a compreensão.",
        _b1_b2_exercises(
            "Traduza: Em termos simples, o sistema economiza tempo.",
            "to put it simply the system saves time",
            "Qual expressão introduz a ideia principal?",
            "The key point is...",
            ["The key point is...", "The minor detail was...", "I have no explanation."],
            "let me break it down into three steps",
            "Explique que você vai dividir a ideia em partes.",
            "let me break it down for you",
        ),
    ),
    "defendendo-uma-opiniao": _b1_b2_spec(
        "Defendendo uma opinião",
        "Sustentar uma opinião com justificativa, evidência e uma formulação confiante, mas responsável.",
        "**I stand by my opinion** mostra que você mantém a posição; **Let me justify that** abre a explicação; **Evidence shows that...** liga a opinião a dados. Convicção deve vir acompanhada de razões.",
        [
            ("I stand by my opinion because the evidence is clear.", "Mantenho minha opinião porque as evidências são claras."),
            ("I have reasons to believe that this will work.", "Tenho razões para acreditar que isso funcionará."),
        ],
        "Não apresente **I’m sure** como substituto de evidência. Uma posição pode ser firme sem ser absoluta; explique que dado ou experiência sustenta a conclusão.",
        "Declare a posição, apresente a razão, cite evidência e reconheça limites quando isso aumentar a credibilidade.",
        _b1_b2_exercises(
            "Traduza: Mantenho minha opinião porque as evidências são claras.",
            "i stand by my opinion because the evidence is clear",
            "Qual frase introduz uma justificativa?",
            "Let me justify that.",
            ["Let me justify that.", "Let me change the subject.", "Let me leave now."],
            "evidence shows that the plan is effective",
            "Defenda sua posição dizendo que tem razões para acreditar nela.",
            "i have reasons to believe that",
        ),
    ),
    "contestando-um-argumento": _b1_b2_spec(
        "Contestando um argumento",
        "Apontar uma limitação no argumento de outra pessoa sem atacar sua identidade ou intenção.",
        "Use **I’d like to challenge that**, **That doesn’t hold up** e **There’s a flaw in the argument**. **Overgeneralization** nomeia uma conclusão ampla demais para as evidências apresentadas.",
        [
            ("I'd like to challenge that assumption.", "Gostaria de contestar essa suposição."),
            ("There is a flaw in that argument.", "Há uma falha nesse argumento."),
        ],
        "Não diga *You are a failure* quando a crítica é sobre uma ideia. Ataque a suposição, a evidência ou a ligação lógica, e explique o motivo.",
        "Reconheça o tema, nomeie a limitação com precisão e ofereça uma alternativa ou evidência contrária.",
        _b1_b2_exercises(
            "Traduza: Há uma falha nesse argumento.",
            "there is a flaw in that argument",
            "O que é uma 'overgeneralization'?",
            "Uma conclusão ampla demais.",
            ["Uma conclusão ampla demais.", "Uma evidência muito precisa.", "Uma pergunta de esclarecimento."],
            "i'd like to challenge that assumption",
            "Conteste com cuidado dizendo que isso não se sustenta.",
            "that doesn't hold up",
        ),
    ),
    "dando-exemplos": _b1_b2_spec(
        "Dando exemplos",
        "Tornar uma afirmação concreta e convincente por meio de exemplos bem introduzidos.",
        "**For instance** e **for example** introduzem um caso; **such as** aparece dentro de uma lista; **a case in point is...** destaca um exemplo especialmente relevante.",
        [
            ("Many cities, such as London, have reliable public transport.", "Muitas cidades, como Londres, têm transporte público confiável."),
            ("For instance, we could reduce the cost.", "Por exemplo, poderíamos reduzir o custo."),
        ],
        "Não use *such as* sozinho no começo de uma frase sem uma categoria anterior. Diga **cities such as London** ou use **For instance** para iniciar uma frase.",
        "Apresente a afirmação geral, escolha o marcador adequado e conecte o exemplo diretamente ao ponto que ele ilustra.",
        _b1_b2_exercises(
            "Traduza: Muitas cidades, como Londres, têm transporte público confiável.",
            "many cities such as london have reliable public transport",
            "Qual expressão pode iniciar um exemplo?",
            "For instance, ...",
            ["For instance, ...", "Nevertheless, ...", "In conclusion, ..."],
            "for example we could start with a small pilot",
            "Dê um exemplo usando 'such as'.",
            "some cities such as london use this system",
        ),
    ),
    "especulando": _b1_b2_spec(
        "Especulando",
        "Falar de possibilidades sem apresentar uma hipótese como certeza.",
        "Use **may, might, could, perhaps** e **It’s possible that...** para marcar incerteza. A escolha de um modal permite graduar a possibilidade; **definitely** expressa certeza e não combina com uma especulação cautelosa.",
        [
            ("It could be that they are late.", "Pode ser que eles estejam atrasados."),
            ("Perhaps the meeting will start later.", "Talvez a reunião comece mais tarde."),
        ],
        "Não use **will** quando você só está supondo, a menos que o contexto mostre uma previsão forte. **Might** não significa que o evento certamente acontecerá.",
        "Apresente a possibilidade, escolha o modal pelo grau de certeza e evite linguagem absoluta quando faltarem dados.",
        _b1_b2_exercises(
            "Traduza: Pode ser que eles estejam atrasados.",
            "it could be that they are late",
            "Qual palavra indica possibilidade, não certeza?",
            "Perhaps",
            ["Perhaps", "Definitely", "Certainly"],
            "they might have missed the bus",
            "Especule que o plano talvez funcione.",
            "the plan might work",
        ),
    ),
    "formulando-hipoteses": _b1_b2_spec(
        "Formulando hipóteses",
        "Propor cenários imaginários e perguntar sobre suas possíveis consequências.",
        "Use **Suppose...**, **What if...?** e **Hypothetically...** para abrir um cenário. O segundo condicional trata de hipóteses presentes ou futuras; o terceiro trata de alternativas a um passado concluído.",
        [
            ("What would happen if we changed the plan?", "O que aconteceria se mudássemos o plano?"),
            ("Suppose we started earlier.", "Suponha que começássemos mais cedo."),
        ],
        "Não confunda **What if** com uma pergunta sobre um fato já confirmado. Em hipótese, use a forma condicional adequada e não coloque *would* depois de **if**.",
        "Apresente o cenário, escolha segundo ou terceiro condicional conforme o tempo e pergunte pelo resultado possível.",
        _b1_b2_exercises(
            "Traduza: O que aconteceria se mudássemos o plano?",
            "what would happen if we changed the plan",
            "Qual expressão abre um cenário imaginário?",
            "Suppose...",
            ["Suppose...", "It is certain...", "This happened..."],
            "what if we started the meeting earlier",
            "Formule uma hipótese sobre ter mais tempo.",
            "if we had more time we would improve the plan",
        ),
    ),
    "persuadindo": _b1_b2_spec(
        "Persuadindo",
        "Convencer alguém apresentando benefícios, lógica e uma pergunta que convide à concordância.",
        "Use **Consider the benefits**, **This is in your best interest** e **Wouldn’t you agree that...?**. A persuasão eficaz relaciona a proposta ao que a outra pessoa valoriza, sem transformar o pedido em ameaça.",
        [
            ("Consider the benefits before you decide.", "Considere as vantagens antes de decidir."),
            ("Wouldn't you agree that this is more efficient?", "Você não concordaria que isso é mais eficiente?"),
        ],
        "Não confunda persuasão com ordem: *Do it or else* pressiona, mas não apresenta razões. Explique o benefício e permita uma resposta.",
        "Mostre o benefício, conecte-o ao interesse do interlocutor e convide-o a avaliar a proposta.",
        _b1_b2_exercises(
            "Traduza: Considere as vantagens antes de decidir.",
            "consider the benefits before you decide",
            "Qual pergunta convida a pessoa a concordar?",
            "Wouldn't you agree that...?",
            ["Wouldn't you agree that...?", "Agree or else.", "Do this immediately."],
            "this is in your best interest",
            "Persuada alguém dizendo que a opção é mais eficiente.",
            "wouldn't you agree that this is more efficient",
        ),
    ),
    "esclarecendo-mal-entendidos": _b1_b2_spec(
        "Esclarecendo mal-entendidos",
        "Corrigir uma interpretação errada com calma, reformulação e confirmação final.",
        "Use **That’s not what I meant**, **Let me clarify** e **What I meant to say was...**. Primeiro corrija a intenção, depois reformule a mensagem e confirme se a outra pessoa entendeu.",
        [
            ("That's not what I meant.", "Não foi isso que eu quis dizer."),
            ("What I meant to say was that we need more time.", "O que eu quis dizer foi que precisamos de mais tempo."),
        ],
        "Não responda ao mal-entendido com acusação. **You misunderstood me** pode soar duro; uma reformulação com **Let me clarify** mantém a cooperação.",
        "Nomeie o mal-entendido sem culpar, reformule a mensagem e peça confirmação ou dúvida específica.",
        _b1_b2_exercises(
            "Traduza: Não foi isso que eu quis dizer.",
            "that's not what i meant",
            "Qual frase introduz uma reformulação?",
            "What I meant to say was...",
            ["What I meant to say was...", "You are impossible.", "Forget the context."],
            "let me clarify what i meant",
            "Esclareça que você quis dizer que precisamos de mais tempo.",
            "what i meant to say was that we need more time",
        ),
    ),
})


# ============================================================
# Complementos do modulo 16 - Writing B2
# ============================================================

B1_B2_TOPIC_ENHANCEMENTS.update({
    "emails-formais": _b1_b2_spec(
        "E-mails formais",
        "Planejar um e-mail profissional com assunto, saudação, objetivo, pedido, fechamento e assinatura.",
        "Um e-mail formal deve deixar claro por que você escreve e o que espera do leitor. Use **Dear...**, **I am writing to...**, **I would appreciate...** e **I look forward to your reply**; evite gírias e contrações quando o contexto for formal.",
        [
            ("I am writing to request a meeting next week.", "Escrevo para solicitar uma reunião na próxima semana."),
            ("I would appreciate it if you could confirm the time.", "Eu agradeceria se você pudesse confirmar o horário."),
        ],
        "Não comece um e-mail formal desconhecido com *Hey* nem termine com *See ya*. **Yours sincerely** e **Yours faithfully** dependem do tipo de saudação e mantêm o registro adequado.",
        "Defina o objetivo logo no início, faça um pedido específico, agradeça e encerre com uma fórmula coerente com a saudação.",
        _b1_b2_exercises(
            "Escreva uma abertura formal para solicitar uma reunião.",
            "i am writing to request a meeting",
            "Qual fechamento combina com um e-mail formal?",
            "Yours sincerely,",
            ["Yours sincerely,", "See ya,", "Cheers mate,"],
            "i look forward to your reply",
            "Leia em voz alta o pedido formal.",
            "i would appreciate your confirmation",
        ),
    ),
    "emails-informais": _b1_b2_spec(
        "E-mails informais",
        "Escrever uma mensagem amigável, clara e organizada para alguém conhecido.",
        "Um e-mail informal pode usar **Hi**, contrações, frases curtas e fechamentos como **Best** ou **Talk to you soon**. Mesmo assim, inclua o motivo da mensagem e a informação necessária para o leitor.",
        [
            ("Hope you're well! Just letting you know I'll be late.", "Espero que esteja bem! Só estou avisando que vou me atrasar."),
            ("Talk to you soon!", "Falamos em breve!"),
        ],
        "Informal não significa desorganizado nem rude. **Hi Anna** é adequado para uma amiga, mas não para um destinatário desconhecido em uma reclamação profissional.",
        "Cumprimente de forma natural, informe o motivo, acrescente detalhes essenciais e termine com uma despedida amigável.",
        _b1_b2_exercises(
            "Escreva uma frase informal avisando que você vai se atrasar.",
            "just letting you know i'll be late",
            "Qual abertura combina com uma amiga?",
            "Hi Anna!",
            ["Hi Anna!", "Dear Sir or Madam,", "To whom it may concern,"],
            "talk to you soon",
            "Despeça-se de modo informal.",
            "talk to you soon",
        ),
    ),
    "relatorios": _b1_b2_spec(
        "Relatórios",
        "Organizar um relatório objetivo em introdução, resultados, conclusão e recomendação.",
        "A introdução apresenta o objetivo; **Findings** apresenta dados e observações; **Conclusion** interpreta o conjunto; **Recommendation** propõe uma ação. O tom deve ser neutro e as afirmações devem estar ligadas aos dados.",
        [
            ("The findings indicate a clear improvement.", "Os resultados indicam uma melhoria clara."),
            ("It is recommended that the team review the process.", "Recomenda-se que a equipe revise o processo."),
        ],
        "Não misture opinião pessoal e resultado na mesma frase sem sinalizar. **The data shows** apresenta evidência; **I think** pode ser inadequado quando o relatório precisa de tom impessoal.",
        "Apresente objetivo, evidência, interpretação e recomendação em seções separadas e conectadas.",
        _b1_b2_exercises(
            "Escreva a frase de recomendação: Recomenda-se que a equipe revise o processo.",
            "it is recommended that the team review the process",
            "Qual seção apresenta os dados observados?",
            "Findings",
            ["Findings", "Greeting", "Signature"],
            "the findings indicate a clear improvement",
            "Apresente oralmente a conclusão de um relatório.",
            "in conclusion the results are encouraging",
        ),
    ),
    "redacoes-essays": _b1_b2_spec(
        "Redações (essays)",
        "Planejar uma redação com tese, parágrafos de desenvolvimento e conclusão coerente.",
        "A introdução contextualiza e apresenta uma **thesis statement** específica. Cada parágrafo do corpo desenvolve uma ideia principal com explicação ou exemplo; a conclusão retoma a posição sem apenas copiar a introdução.",
        [
            ("This essay will discuss two advantages of remote work.", "Esta redação discutirá duas vantagens do trabalho remoto."),
            ("In conclusion, flexible work can improve productivity.", "Em conclusão, o trabalho flexível pode melhorar a produtividade."),
        ],
        "Não use uma tese vaga como *Technology is good*. Uma tese defensável delimita o tema e apresenta uma posição que os parágrafos podem sustentar.",
        "Planeje tese, um ponto por parágrafo, conectores e uma conclusão que sintetize a resposta ao tema.",
        _b1_b2_exercises(
            "Escreva uma tese sobre trabalho remoto: ele pode melhorar a produtividade.",
            "remote work can improve productivity",
            "O que uma boa thesis statement deve ser?",
            "Específica e defensável.",
            ["Específica e defensável.", "Uma pergunta sem posição.", "Uma lista de palavras soltas."],
            "this essay will discuss two advantages of remote work",
            "Leia a conclusão de uma redação.",
            "in conclusion flexible work can improve productivity",
        ),
    ),
    "argumentacao-escrita": _b1_b2_spec(
        "Argumentação escrita",
        "Construir um parágrafo argumentativo com afirmação, evidência, contra-argumento e resposta.",
        "**Claim** é a posição; **evidence** sustenta a posição; **Some may argue that...** apresenta o contraponto; **While it is true that...** concede algo antes de responder. Essa estrutura mostra raciocínio, não apenas preferência.",
        [
            ("The claim is supported by recent data.", "A afirmação é sustentada por dados recentes."),
            ("While it is true that the plan costs more, it saves time.", "Embora seja verdade que o plano custa mais, ele economiza tempo."),
        ],
        "Não use **however** para esconder a falta de evidência. Um contra-argumento deve ser apresentado de modo justo e respondido com uma razão ou dado relevante.",
        "Declare a posição, mostre evidência, reconheça a objeção e explique por que sua conclusão ainda se sustenta.",
        _b1_b2_exercises(
            "Escreva a concessão: Embora o plano custe mais, ele economiza tempo.",
            "while it is true that the plan costs more it saves time",
            "O que é uma claim?",
            "Uma afirmação ou posição defendida.",
            ["Uma afirmação ou posição defendida.", "A saudação do texto.", "Um detalhe sem relação."],
            "some may argue that the plan is too expensive",
            "Apresente um contra-argumento.",
            "some may argue that it is too expensive",
        ),
    ),
    "resenhas": _b1_b2_spec(
        "Resenhas",
        "Escrever uma avaliação equilibrada com resumo, opinião sobre aspectos específicos e recomendação.",
        "Uma resenha informa do que a obra trata, avalia elementos como atuação ou enredo e diz para quem a obra pode ser indicada. **Outstanding**, **gripping** e **could be better** permitem avaliar sem depender de ‘good’ ou ‘bad’.",
        [
            ("The plot is gripping, but the ending could be better.", "O enredo é envolvente, mas o final poderia ser melhor."),
            ("Overall, I recommend this film to mystery fans.", "No geral, recomendo este filme a fãs de mistério."),
        ],
        "Não transforme a resenha em apenas uma sinopse ou uma nota. Dê uma avaliação sustentada por detalhes e evite revelar o final sem avisar.",
        "Resuma brevemente, avalie aspectos concretos e conclua indicando se, e para quem, a obra vale a pena.",
        _b1_b2_exercises(
            "Escreva uma crítica moderada: O final poderia ser melhor.",
            "the ending could be better",
            "Quais três partes uma resenha costuma combinar?",
            "Resumo, opinião e recomendação.",
            ["Resumo, opinião e recomendação.", "Saudação, endereço e assinatura.", "Hipótese, fórmula e tabela."],
            "the plot is gripping but the ending could be better",
            "Recomende um filme a fãs de mistério.",
            "i recommend this film to mystery fans",
        ),
    ),
    "resumos": _b1_b2_spec(
        "Resumos",
        "Reduzir um texto às ideias principais usando paráfrase, neutralidade e seleção de informações.",
        "Um resumo responde ‘sobre o que é o texto?’ e preserva os pontos essenciais. Use **The text discusses...**, **The article focuses on...** e **In summary...**; não copie frases nem acrescente sua opinião.",
        [
            ("The article focuses on access to education.", "O artigo se concentra no acesso à educação."),
            ("In summary, the main point is that practice matters.", "Em resumo, o ponto principal é que a prática importa."),
        ],
        "Parafrasear não é trocar uma palavra e copiar o resto. Também não transforme o resumo em resenha: avaliação pessoal não é ideia principal do texto-fonte.",
        "Identifique tema e pontos-chave, reescreva com suas palavras, corte detalhes secundários e mantenha tom neutro.",
        _b1_b2_exercises(
            "Escreva uma abertura de resumo: O artigo se concentra no acesso à educação.",
            "the article focuses on access to education",
            "O que um resumo deve evitar?",
            "Detalhes irrelevantes e opinião pessoal.",
            ["Detalhes irrelevantes e opinião pessoal.", "A ideia principal.", "Os pontos-chave."],
            "in summary the main point is that practice matters",
            "Diga em voz alta como você conclui um resumo.",
            "in summary the main point is clear",
        ),
    ),
    "propostas": _b1_b2_spec(
        "Propostas",
        "Apresentar um plano com objetivo, etapas, cronograma, orçamento e benefícios para um leitor que decidirá.",
        "Uma proposta responde ao problema e mostra como a solução será executada. Organize **Purpose**, **Plan**, **Timeline**, **Budget** e **Benefits**; use **This proposal aims to...** e **The goal is to...** para orientar o leitor.",
        [
            ("This proposal aims to reduce waiting times.", "Esta proposta visa reduzir os tempos de espera."),
            ("The benefits include lower costs and better service.", "Os benefícios incluem custos menores e um serviço melhor."),
        ],
        "Não liste apenas uma ideia. Uma proposta precisa explicar como, quando e com quais recursos a ideia será realizada, além de mostrar por que vale a pena.",
        "Defina o objetivo, descreva o plano, informe prazo e custo e destaque benefícios mensuráveis.",
        _b1_b2_exercises(
            "Escreva uma frase de objetivo: Esta proposta visa reduzir os tempos de espera.",
            "this proposal aims to reduce waiting times",
            "Qual seção apresenta os custos?",
            "Budget",
            ["Budget", "Timeline", "Purpose"],
            "the benefits include lower costs and better service",
            "Apresente o cronograma de uma proposta.",
            "the timeline is three months",
        ),
    ),
    "comunicacao-profissional": _b1_b2_spec(
        "Comunicação profissional",
        "Escrever mensagens internas claras, concisas, educadas e orientadas para uma ação.",
        "Use **Please find attached...** para anexos, **Let’s touch base** para alinhar e **Keep me posted** para pedir atualizações. Uma mensagem profissional informa contexto, ação esperada e prazo sem excesso de palavras.",
        [
            ("Please find attached the revised report.", "Em anexo, está o relatório revisado."),
            ("Keep me posted on any changes.", "Mantenha-me informado sobre qualquer mudança."),
        ],
        "Não use **touch base** em uma mensagem que exige instruções jurídicas ou muita precisão sem explicar a ação. A expressão é natural em comunicação interna, mas o conteúdo ainda precisa ser específico.",
        "Diga o que está sendo enviado, qual ação é esperada e quando será o próximo contato.",
        _b1_b2_exercises(
            "Escreva uma frase para enviar um relatório revisado em anexo.",
            "please find attached the revised report",
            "Qual frase pede atualizações?",
            "Keep me posted on any changes.",
            ["Keep me posted on any changes.", "Forget the report.", "No information is needed."],
            "let's touch base next week",
            "Peça para alinhar novamente na próxima semana.",
            "let's touch base next week",
        ),
    ),
    "escrita-academica": _b1_b2_spec(
        "Fundamentos de escrita acadêmica",
        "Adotar tom formal, impessoal e cauteloso ao apresentar fontes, resultados e interpretações.",
        "Use **According to...** para atribuir uma ideia, **This study examines...** para descrever o trabalho e **This suggests...** para fazer *hedging*. O cuidado evita transformar evidência limitada em certeza absoluta.",
        [
            ("According to Smith, regular practice improves retention.", "Segundo Smith, a prática regular melhora a retenção."),
            ("The results suggest a possible relationship.", "Os resultados sugerem uma possível relação."),
        ],
        "Não diga *This proves* quando os dados apenas sugerem uma tendência. **This suggests** é mais responsável; também evite gírias e afirmações sem fonte.",
        "Cite a fonte, descreva o estudo, use verbos precisos e suavize conclusões quando a evidência não for definitiva.",
        _b1_b2_exercises(
            "Escreva uma formulação cautelosa: Os resultados sugerem uma possível relação.",
            "the results suggest a possible relationship",
            "Qual expressão atribui uma informação a uma fonte?",
            "According to Smith, ...",
            ["According to Smith, ...", "Trust me, ...", "Everybody knows, ..."],
            "this study examines the effects of sleep",
            "Apresente uma conclusão acadêmica suavizada.",
            "it could be argued that education is essential",
        ),
    ),
})


def _expand_b1_b2_module(current_module):
    if current_module["slug"] not in {
        "modulo-08-gramatica-essencial-b1",
        "modulo-09-vocabulario-b1",
        "modulo-10-speaking-b1",
        "modulo-11-listening-b1",
        "modulo-12-gramatica-essencial-b2",
        "modulo-13-vocabulario-b2",
        "modulo-14-ingles-natural-b2",
        "modulo-15-speaking-b2",
        "modulo-16-writing-b2",
    }:
        return current_module

    for current_topic in current_module["topics"]:
        spec = B1_B2_TOPIC_ENHANCEMENTS.get(current_topic["slug"])
        if spec is None:
            raise ValueError(
                f"Tópico B1/B2 sem complemento revisado: {current_topic['slug']}"
            )
        needed = 10 - len(current_topic["exercises"])
        if needed < 0:
            raise ValueError(
                "Tópico B1/B2 com mais de 10 exercícios antes da expansão: "
                f"{current_topic['slug']}"
            )
        if len(spec["exercises"]) != needed:
            raise ValueError(
                f"Complemento B1/B2 incorreto para {current_topic['slug']}: "
                f"{len(spec['exercises'])} para {needed}"
            )
        current_topic["exercises"].extend(deepcopy(spec["exercises"]))
        current_topic["lesson_md"] = spec["lesson"]
    return current_module


def _expand_b1_b2_builder(builder):
    @wraps(builder)
    def wrapped():
        return _expand_b1_b2_module(builder())
    return wrapped


for _b1_b2_builder_name in (
    "build_modulo_08_gramatica_essencial_b1",
    "build_modulo_09_vocabulario_b1",
    "build_modulo_10_speaking_b1",
    "build_modulo_11_listening_b1",
    "build_modulo_12_gramatica_essencial_b2",
    "build_modulo_13_vocabulario_b2",
    "build_modulo_14_ingles_natural_b2",
    "build_modulo_15_speaking_b2",
    "build_modulo_16_writing_b2",
):
    globals()[_b1_b2_builder_name] = _expand_b1_b2_builder(
        globals()[_b1_b2_builder_name]
    )


# ============================================================
# MODULO 17 - Gramatica Avancada - C1
# ============================================================

def build_modulo_17_gramatica_avancada_c1():
    return module(
        "modulo-17-gramatica-avancada-c1",
        "Módulo 17 — Gramática Avançada — C1",
        "Precisão no nível avançado: condicionais invertidos, inversão formal, ênfase e cleft sentences, elipse, substituição, passivas de relato, nominalização, orações e relativas avançadas, subjuntivo, hedging e nuance modal.",
        [
            topic(
                "condicionais-avancados",
                "Condicionais avançados",
                """
# Condicionais avançados

Além dos condicionais do B1/B2, o C1 usa **condicionais invertidos** e
conectivos de condição.

## Condicional invertido (formal)

```
If I had known...  ->  Had I known...
If I were you...   ->  Were I you...
```

## Conectivos de condição

```
unless            a menos que
provided that     desde que (condição)
in case           caso (para prevenir)
```

## Exemplos

```
Had I known, I would have called.      Se eu soubesse, teria ligado.
You can come, provided that you're on time.   Pode vir, desde que seja pontual.
Take an umbrella in case it rains.     Leve um guarda-chuva caso chova.
```

> 💡 Na inversão, remova o **if** e inverta sujeito/verbo: "If I had
> known" vira "Had I known".
""",
                [
                    ex("quiz", "A forma invertida de 'If I had known' é:",
                       "Had I known", ["Had I known", "I had known", "If had known"]),
                    ex("quiz", "O que 'unless' significa?",
                       "a menos que", ["a menos que", "desde que", "porque"]),
                    ex("text", "Complete: '___ I known, I would have called.' (forma invertida)",
                       "had"),
                    ex("audio", "Escute e transcreva:",
                       "had i known i would have called", audio_text="Had I known, I would have called."),
                    ex("quiz", "O que 'provided that' significa?",
                       "desde que (condição)", ["desde que (condição)", "apesar de", "quando"]),
                    ex("quiz", "Em 'Take an umbrella in case it rains', a ideia é:",
                       "prevenir-se de uma possibilidade", ["prevenir-se de uma possibilidade", "certeza", "passado"]),
                ],
            ),
            topic(
                "inversao-formal",
                "Inversão formal/literária",
                """
# Inversão formal/literária

A inversão (Módulo 12) também aparece em estruturas formais e literárias.

## Estruturas com inversão

```
No sooner had I arrived than it started to rain.
Mal tinha chegado quando começou a chover.

Only when I saw her did I understand.
Só quando a vi é que entendi.

Not until I tried it did I like it.
Só depois de experimentar é que gostei.
```

## A regra

Depois de **no sooner / only when / not until / rarely**, o verbo vem antes
do sujeito: **did I understand**, **had I arrived**.

> 💡 É uma estrutura de texto literário e formal — você vai encontrá-la em
> livros, artigos e discursos.
""",
                [
                    ex("quiz", "O que 'No sooner had I arrived than...' significa?",
                       "mal tinha chegado quando...", ["mal tinha chegado quando...", "eu cheguei antes", "nunca cheguei"]),
                    ex("quiz", "A inversão formal com 'Only after' faz:",
                       "o verbo vir antes do sujeito", ["o verbo vir antes do sujeito", "o sujeito antes do verbo", "nada"]),
                    ex("text", "Complete: 'No sooner ___ I arrived than it started to rain.'",
                       "had"),
                    ex("audio", "Escute e transcreva:",
                       "only when i saw her did i understand", audio_text="Only when I saw her did I understand."),
                    ex("quiz", "Inversão formal é usada em:",
                       "textos literários e formais", ["textos literários e formais", "WhatsApp", "gírias"]),
                    ex("quiz", "Em 'Not until I tried it ___ I like it.', a lacuna é:",
                       "did", ["did", "do", "was"]),
                ],
            ),
            topic(
                "estruturas-de-enfase",
                "Estruturas de ênfase",
                """
# Estruturas de ênfase

Para dar destaque, o C1 usa o **auxiliar enfático** e conectivos de ênfase.

## Auxiliar enfático (do/did)

```
I do believe you.          Eu realmente acredito em você.
I did tell you.            Eu te avisei mesmo.
```

## Outras formas

```
What matters most is...        O que mais importa é...
It was so good that I cried.   Foi tão bom que chorei.
```

> 💡 O **do/did** enfático reforça o verbo — no afirmativo comum ele não
> aparece, então quando aparece, é ênfase.
""",
                [
                    ex("quiz", "Para ENFATIZAR uma afirmação com verbo comum:",
                       "I do believe you.", ["I do believe you.", "I believe you.", "I believing you."]),
                    ex("quiz", "O auxiliar enfático no passado é:",
                       "did", ["did", "does", "do"]),
                    ex("text", "Complete: 'I ___ need your help.' (enfático, presente)",
                       "do"),
                    ex("audio", "Escute e transcreva:",
                       "i do understand your point", audio_text="I do understand your point."),
                    ex("quiz", "O que 'what matters most is...' enfatiza?",
                       "a prioridade", ["a prioridade", "o passado", "a dúvida"]),
                    ex("quiz", "Em 'It was so good ___ I cried.', a lacuna é:",
                       "that", ["that", "than", "as"]),
                ],
            ),
            topic(
                "cleft-sentences",
                "Cleft sentences",
                """
# Cleft sentences

As **cleft sentences** dividem a frase para focar em um elemento.

## Estruturas

```
It was Ana who called.          Foi a Ana quem ligou.
What I need is more time.       O que eu preciso é de mais tempo.
The reason why I came was to help.   O motivo de eu ter vindo era ajudar.
```

> 💡 **It + be + foco + who/that...** destaca a pessoa/coisa. **What + sujeito
> + verbo + is...** destaca o que o sujeito precisa/quere.
""",
                [
                    ex("quiz", "Para focar em QUEM fez a ação:",
                       "It was Ana who called.", ["It was Ana who called.", "Ana called.", "Called Ana."]),
                    ex("quiz", "O que 'What I need is...' destaca?",
                       "o que eu preciso", ["o que eu preciso", "quem eu sou", "onde estou"]),
                    ex("text", "Complete: 'It ___ my brother who broke the window.' (was)",
                       "was"),
                    ex("audio", "Escute e transcreva:",
                       "what i want is more time", audio_text="What I want is more time."),
                    ex("quiz", "A estrutura cleft 'It was X who...' serve para:",
                       "dar ênfase a um elemento", ["dar ênfase a um elemento", "fazer pergunta", "negar"]),
                    ex("quiz", "Em 'The reason why I came ___ to help.', a lacuna é:",
                       "was", ["was", "were", "is"]),
                ],
            ),
            topic(
                "elipse",
                "Elipse",
                """
# Elipse

**Elipse** é omitir palavras que o contexto já deixa claras — deixa a fala e
a escrita mais naturais.

## Exemplos

```
I can help, if you want me to (help).    Posso ajudar, se quiser.
She sings better than I do (sing).       Ela canta melhor do que eu.
I love pizza and she loves sushi.        (sem elipse — repete "loves")
```

> 💡 A elipse aparece muito em conversa: "Want some?" (em vez de "Do you want
> some?") ou "Coming?" (em vez de "Are you coming?").
""",
                [
                    ex("quiz", "Elipse é:",
                       "omitir palavras que o contexto já diz", ["omitir palavras que o contexto já diz", "repetir tudo", "inventar palavras"]),
                    ex("quiz", "Em 'I can help, if you want me to', o que foi elidido?",
                       "help", ["help", "want", "if"]),
                    ex("text", "Complete com elipse: 'She sings better than I ___' (do)",
                       "do"),
                    ex("audio", "Escute e transcreva:",
                       "i can if you want me to", audio_text="I can, if you want me to."),
                    ex("quiz", "A elipse aparece mais em:",
                       "conversa e textos naturais", ["conversa e textos naturais", "linguagem jurídica", "nenhum lugar"]),
                    ex("quiz", "Em 'I love pizza and she ___ sushi.', a lacuna é:",
                       "loves", ["loves", "love", "is"]),
                ],
            ),
            topic(
                "substituicao",
                "Substituição",
                """
# Substituição

**Substituição** troca palavras repetidas por **so / one / that** para evitar
repetição.

## Exemplos

```
Do you think it will rain?  -  I think so.        (so = que vai chover)
I like this book more than the one you have.      (one = livro)
I'm tired.  -  I thought so.                      (so = que você está cansado)
```

> 💡 **so** substitui uma ideia inteira (após think, hope, believe, guess).
> **one/ones** substitui um substantivo contável já dito.
""",
                [
                    ex("quiz", "Para evitar repetir uma ideia:",
                       "I think so.", ["I think so.", "I think it.", "I think yes."]),
                    ex("quiz", "Em 'Do you like this one?', 'one' substitui:",
                       "um substantivo já dito", ["um substantivo já dito", "um verbo", "uma pergunta"]),
                    ex("text", "Complete: 'I don't think ___' (acho que não)",
                       "so"),
                    ex("audio", "Escute e transcreva:",
                       "i think so but i'm not sure", audio_text="I think so, but I'm not sure."),
                    ex("quiz", "Substituição evita:",
                       "repetição de palavras", ["repetição de palavras", "erros de gramática", "pausas"]),
                    ex("quiz", "Em 'This book is better than the ___ I read.', a lacuna é:",
                       "one", ["one", "it", "so"]),
                ],
            ),
            topic(
                "passivas-avancadas",
                "Estruturas passivas avançadas",
                """
# Estruturas passivas avançadas

A passiva com **verbos de relato** deixa o texto impessoal e formal.

## It is said that...

```
It is said that she is very talented.      Diz-se que ela é muito talentosa.
It is believed that the company will grow.  Acredita-se que a empresa vai crescer.
```

## Subject + be believed to...

```
He is believed to be rich.      Acredita-se que ele é rico.
She is known to be kind.        Sabe-se que ela é gentil.
```

> 💡 Verbos de relato comuns: **say, believe, know, think, report**. A forma
> "be believed to + verbo" é a mais sofisticada.
""",
                [
                    ex("quiz", "A passiva com verbo de relato:",
                       "It is said that...", ["It is said that...", "I say that...", "He says..."]),
                    ex("quiz", "Em 'He is believed to be rich', o sentido é:",
                       "acredita-se que ele é rico", ["acredita-se que ele é rico", "ele acredita", "ele é rico com certeza"]),
                    ex("text", "Complete: 'It is ___ that the company will grow.' (dito)",
                       "said"),
                    ex("audio", "Escute e transcreva:",
                       "it is said that she is very talented", audio_text="It is said that she is very talented."),
                    ex("quiz", "A passiva com 'be believed to' usa:",
                       "to + infinitivo", ["to + infinitivo", "gerúndio", "particípio só"]),
                    ex("quiz", "A passiva de relato deixa o texto:",
                       "impessoal e formal", ["impessoal e formal", "pessoal e informal", "mais curto só"]),
                ],
            ),
            topic(
                "nominalizacao",
                "Nominalização",
                """
# Nominalização

**Nominalização** transforma verbos/adjetivos em substantivos — característica
do texto formal e acadêmico.

## Exemplos

```
to decide  ->  the decision
to improve ->  the improvement
to complete ->  the completion
to fail    ->  the failure
```

```
The improvement was significant.    A melhoria foi significativa.
The completion of the project was a success.   A conclusão do projeto foi um sucesso.
```

> 💡 A nominalização deixa o texto mais **denso e formal**: "They decided"
> vira "the decision". É comum em relatórios e artigos.
""",
                [
                    ex("quiz", "A nominalização de 'to decide' é:",
                       "the decision", ["the decision", "deciding", "decided"]),
                    ex("quiz", "Nominalização deixa o texto:",
                       "mais formal e conciso", ["mais formal e conciso", "mais informal", "mais longo sempre"]),
                    ex("text", "Escreva o substantivo de 'to improve'.",
                       "improvement"),
                    ex("audio", "Escute e transcreva:",
                       "the improvement was significant", audio_text="The improvement was significant."),
                    ex("quiz", "Em 'the ___ of the project was a success', (concluir) entra:",
                       "completion", ["completion", "complete", "completing"]),
                    ex("quiz", "Nominalização é comum em:",
                       "textos acadêmicos e formais", ["textos acadêmicos e formais", "conversas de bar", "gírias"]),
                ],
            ),
            topic(
                "oracoes-complexas-avancadas",
                "Orações complexas avançadas",
                """
# Orações complexas avançadas

No C1, as frases combinam várias subordinadas, incluindo **participle
clauses**.

## Participle clauses

```
Having finished the work, she left.    Tendo terminado o trabalho, ela saiu.
Being tired, he went to bed.           Como estava cansado, ele foi dormir.
```

**having + particípio** = ação concluída antes de outra.

## Orações bem organizadas

```
After having analyzed the data, the team concluded that...
Após ter analisado os dados, o time concluiu que...
```

> 💡 Em frases complexas, a clareza vem da **organização** — cada oração no
> seu lugar, com conectivos claros.
""",
                [
                    ex("quiz", "A participle clause de passado: '___ the work, she left.'",
                       "Having finished", ["Having finished", "Finished", "To finish"]),
                    ex("quiz", "A forma 'having + particípio' expressa:",
                       "ação concluída antes de outra", ["ação concluída antes de outra", "ação futura", "ação simultânea"]),
                    ex("text", "Complete: '___ tired, he went to bed.' (particípio presente)",
                       "being"),
                    ex("audio", "Escute e transcreva:",
                       "having finished the report she went home", audio_text="Having finished the report, she went home."),
                    ex("quiz", "Orações complexas têm:",
                       "várias subordinadas bem organizadas", ["várias subordinadas bem organizadas", "só uma oração", "nenhum verbo"]),
                    ex("quiz", "Para evitar ambiguidade em frase complexa, o ideal é:",
                       "manter clara a relação entre as orações", ["manter clara a relação entre as orações", "encher de vírgulas", "usar só palavras soltas"]),
                ],
            ),
            topic(
                "relativas-avancadas",
                "Orações relativas avançadas",
                """
# Orações relativas avançadas

## Relativa NÃO definidora (com vírgula)

Traz informação **extra**, não essencial:

```
She passed the test, which surprised everyone.
Ela passou no teste, o que surpreendeu a todos.
```

Aqui, **which** se refere à frase inteira.

## whose (posse) e where (lugar)

```
The man whose car was stolen is my neighbor.   O homem cujo carro foi roubado é meu vizinho.
The house where I was born is old.             A casa onde nasci é antiga.
```

> 💡 Com vírgula = informação extra; sem vírgula = informação essencial para
> identificar a coisa.
""",
                [
                    ex("quiz", "Relativa NÃO definidora (com vírgula) traz:",
                       "informação extra, não essencial", ["informação extra, não essencial", "informação essencial", "nada"]),
                    ex("quiz", "'whose' indica:",
                       "posse (cujo)", ["posse (cujo)", "lugar", "tempo"]),
                    ex("text", "Complete: 'The man ___ car was stolen is my neighbor.' (cujo)",
                       "whose"),
                    ex("audio", "Escute e transcreva:",
                       "she passed the test which surprised everyone", audio_text="She passed the test, which surprised everyone."),
                    ex("quiz", "Em 'The house ___ I was born is old.', a lacuna é:",
                       "where", ["where", "which", "who"]),
                    ex("quiz", "'which' referindo-se à frase inteira:",
                       "comenta a ideia toda", ["comenta a ideia toda", "só o nome", "nunca"]),
                ],
            ),
            topic(
                "subjuntivo",
                "Estruturas de subjuntivo",
                """
# Estruturas de subjuntivo

O **subjuntivo** expressa importância, recomendação, exigência ou desejo.
Após **suggest/recommend/insist + that**, o verbo fica na **forma base**.

## Exemplos

```
I suggest that he go now.              Sugiro que ele vá agora.
I recommend that you take a break.     Recomendo que você faça uma pausa.
It is essential that she be on time.   É essencial que ela chegue na hora.
```

> 💡 Repare: "that he **go**" (sem -s!) e "that she **be**" — o verbo fica
> na base, mesmo com he/she. É o subjuntivo.
""",
                [
                    ex("quiz", "Depois de 'suggest/recommend that', o verbo:",
                       "fica na forma base", ["fica na forma base", "ganha -s", "vira passado"]),
                    ex("quiz", "Em 'I suggest that he ___ (go)', a lacuna é:",
                       "go", ["go", "goes", "going"]),
                    ex("text", "Complete: 'It is essential that she ___ (be) on time.'",
                       "be"),
                    ex("audio", "Escute e transcreva:",
                       "i recommend that you take a break", audio_text="I recommend that you take a break."),
                    ex("quiz", "O subjuntivo também aparece em 'It is important that...' — o verbo:",
                       "fica na forma base", ["fica na forma base", "no passado", "no gerúndio"]),
                    ex("quiz", "O subjuntivo expressa:",
                       "importância/recomendação/desejo", ["importância/recomendação/desejo", "fato", "rotina"]),
                ],
            ),
            topic(
                "hedging",
                "Hedging (suavização de afirmações)",
                """
# Hedging (suavização de afirmações)

**Hedging** é suavizar afirmações para não soar agressivo — essencial para
discordar com elegância.

## Formas de suavizar

```
It seems to me that...          Parece-me que...
I would argue that...           Eu argumentaria que...
I'd venture to say that...      Ousaria dizer que...
It could be argued that...      Pode-se argumentar que...
```

## Discordar sem ofender

```
Em vez de:  "You're wrong."
Use:        "I would argue the opposite, respectfully."
```

> 💡 O C1 não diz "you're wrong" — diz "I'd venture to say the opposite".
> Suavizar não é ser fraco: é ter precisão e elegância.
""",
                [
                    ex("quiz", "Para discordar de forma sutil:",
                       "I'd venture to say...", ["I'd venture to say...", "You're wrong.", "No."]),
                    ex("quiz", "O que 'It seems to me that...' faz?",
                       "suaviza a opinião", ["suaviza a opinião", "afirma com certeza", "pergunta"]),
                    ex("text", "Complete: 'It ___ to me that this is a good idea.' (parece)",
                       "seems"),
                    ex("audio", "Escute e transcreva:",
                       "i would argue the opposite respectfully", audio_text="I would argue the opposite, respectfully."),
                    ex("quiz", "Hedging é essencial para:",
                       "discordar sem ofender", ["discordar sem ofender", "gritar", "ser vago demais"]),
                    ex("quiz", "Qual frase é a mais HEDGED (suavizada)?",
                       "It could be argued that...", ["It could be argued that...", "This is wrong.", "Absolutely not."]),
                ],
            ),
            topic(
                "nuance-e-modalidade",
                "Nuance e modalidade",
                """
# Nuance e modalidade

A modalidade sofisticada expressa **graus de certeza, possibilidade e
polidez**.

## Graus de certeza

```
She must have known.      Ela deve ter sabido. (quase certa)
She might have known.     Ela pode ter sabido. (possível)
She can't have known.     Ela não pode ter sabido. (impossível)
```

## Suavizando críticas

```
That's not necessarily true.    Isso não é necessariamente verdade.
People tend to prefer coffee.   As pessoas tendem a preferir café.
```

> 💡 **not necessarily** e **tend to** são os cavalos de batalha do C1:
> expressam nuance sem afirmar nada absoluto.
""",
                [
                    ex("quiz", "Para suavizar uma crítica com nuance:",
                       "That's not necessarily true.", ["That's not necessarily true.", "That's a lie.", "Nonsense."]),
                    ex("quiz", "O que 'tend to' expressa?",
                       "tendência (geralmente)", ["tendência (geralmente)", "certeza", "proibição"]),
                    ex("text", "Complete: 'People ___ to prefer coffee.' (tendem)",
                       "tend"),
                    ex("audio", "Escute e transcreva:",
                       "it's not necessarily a bad thing", audio_text="It's not necessarily a bad thing."),
                    ex("quiz", "Em 'She ___ have known' (podia ter sabido, possível), entra:",
                       "might", ["might", "must", "should"]),
                    ex("quiz", "A modalidade sofisticada permite:",
                       "expressar graus de certeza e polidez", ["expressar graus de certeza e polidez", "só ordem", "só proibição"]),
                ],
            ),
        ],
    )


# ============================================================
# MODULO 18 - Vocabulario Avancado - C1
# ============================================================

def build_modulo_18_vocabulario_c1():
    return module(
        "modulo-18-vocabulario-c1",
        "Módulo 18 — Vocabulário Avançado — C1",
        "Vocabulário de precisão: acadêmico e profissional avançados, abstrações, collocations e idioms avançados, linguagem metafórica, sinônimos com nuance, registro, formal vs informal, precisão, famílias de palavras e vocabulário contextual.",
        [
            topic(
                "academico-avancado",
                "Vocabulário acadêmico avançado",
                """
# Vocabulário acadêmico avançado

Para textos acadêmicos e formais, estas palavras são essenciais.

| Inglês | Português |
|---|---|
| enhance | aprimorar / melhorar |
| demonstrate | demonstrar |
| subsequent | subsequente |
| moreover | além disso |
| hence | portanto |
| substantial | substancial / considerável |
| facilitate | facilitar |
| propose | propor |

## Exemplos

```
This study demonstrates the impact.      Este estudo demonstra o impacto.
Hence, the results are clear.            Portanto, os resultados são claros.
```

> 💡 **hence** = portanto (mais formal que "so"). **moreover** = além disso.
""",
                [
                    ex("quiz", "Como se diz 'aprimorar/melhorar' (formal)?",
                       "enhance", ["enhance", "worsen", "keep"]),
                    ex("quiz", "Como se diz 'subsequente'?",
                       "subsequent", ["subsequent", "previous", "before"]),
                    ex("text", "Traduza: Portanto, os resultados são claros.",
                       "hence the results are clear"),
                    ex("audio", "Escute e transcreva:",
                       "this study demonstrates the impact", audio_text="This study demonstrates the impact."),
                    ex("quiz", "Como se diz 'facilitar'?",
                       "facilitate", ["facilitate", "complicate", "avoid"]),
                    ex("quiz", "O sinônimo acadêmico de 'big' é:",
                       "substantial", ["substantial", "huge informal", "small"]),
                ],
            ),
            topic(
                "profissional-avancado",
                "Vocabulário profissional avançado",
                """
# Vocabulário profissional avançado

| Inglês | Português |
|---|---|
| oversee | supervisionar |
| liaise with | fazer a ponte com |
| streamline | otimizar (processo) |
| comply with | cumprir (regras) |
| prioritize | priorizar |
| delegate | delegar |
| initiate | iniciar (formal) |

## Exemplos

```
We must comply with the rules.      Devemos cumprir as regras.
I need to liaise with the team.     Preciso alinhar com o time.
```

> 💡 **comply with** = cumprir (regras/leis). **liaise with** = manter
> comunicação/alinhamento entre partes.
""",
                [
                    ex("quiz", "Como se diz 'supervisionar'?",
                       "oversee", ["oversee", "ignore", "forget"]),
                    ex("quiz", "Como se diz 'otimizar' (um processo)?",
                       "streamline", ["streamline", "complicate", "stop"]),
                    ex("text", "Complete: 'I need to ___ with the team.' (fazer a ponte)",
                       "liaise"),
                    ex("audio", "Escute e transcreva:",
                       "we must comply with the rules", audio_text="We must comply with the rules."),
                    ex("quiz", "Como se diz 'priorizar'?",
                       "prioritize", ["prioritize", "postpone", "cancel"]),
                    ex("quiz", "Como se diz 'delegar'?",
                       "delegate", ["delegate", "keep", "decide"]),
                ],
            ),
            topic(
                "vocabulario-abstrato",
                "Vocabulário abstrato",
                """
# Vocabulário abstrato

Conceitos abstratos aparecem em discussões e textos de nível avançado.

| Inglês | Português |
|---|---|
| assumption | suposição |
| perception | percepção |
| dilemma | dilema |
| notion | noção |
| implication | implicação |
| consensus | consenso |
| ambiguity | ambiguidade |

## Exemplos

```
That is a common perception.      Essa é uma percepção comum.
It is a difficult dilemma.        É um dilema difícil.
```

> 💡 **implication** = consequência indireta ("what are the implications?").
""",
                [
                    ex("quiz", "Como se diz 'suposição'?",
                       "assumption", ["assumption", "result", "fact"]),
                    ex("quiz", "Como se diz 'percepção'?",
                       "perception", ["perception", "conclusion", "question"]),
                    ex("text", "Traduza: É um dilema difícil.",
                       "it is a difficult dilemma"),
                    ex("audio", "Escute e transcreva:",
                       "that is a common perception", audio_text="That is a common perception."),
                    ex("quiz", "Como se diz 'ambiguidade'?",
                       "ambiguity", ["ambiguity", "clarity", "certainty"]),
                    ex("quiz", "Como se diz 'consenso'?",
                       "consensus", ["consensus", "disagreement", "doubt"]),
                ],
            ),
            topic(
                "collocations-avancadas",
                "Collocations avançadas",
                """
# Collocations avançadas

As collocations do nível avançado:

```
make an effort        fazer um esforço
take into account     levar em conta
pay attention         prestar atenção
draw a conclusion     tirar uma conclusão
bear in mind          ter em mente
come to a decision    chegar a uma decisão
```

## Exemplos

```
We must take into account the costs.   Devemos levar em conta os custos.
Bear in mind the deadline.             Tenha em mente o prazo.
```

> 💡 Não dá para "traduzir" collocations: **pay attention** (não "give
> attention"), **make an effort** (não "do an effort").
""",
                [
                    ex("quiz", "A collocation com 'an effort' é:",
                       "make", ["make", "do", "have"]),
                    ex("quiz", "Com 'attention', usamos:",
                       "pay", ["pay", "give", "make"]),
                    ex("text", "Complete: 'We must take into ___ the costs.' (conta)",
                       "account"),
                    ex("audio", "Escute e transcreva:",
                       "bear in mind the deadline", audio_text="Bear in mind the deadline."),
                    ex("quiz", "A collocation com 'a conclusion' é:",
                       "draw", ["draw", "take", "make"]),
                    ex("quiz", "Em 'come to a ___', a lacuna (decisão) é:",
                       "decision", ["decision", "idea", "plan"]),
                ],
            ),
            topic(
                "idioms-avancados",
                "Expressões idiomáticas avançadas",
                """
# Expressões idiomáticas avançadas

| Idiom | Significado |
|---|---|
| bite the bullet | encarar algo difícil |
| spill the beans | contar o segredo |
| hit the nail on the head | acertar em cheio |
| cost an arm and a leg | custar muito caro |
| a blessing in disguise | um mal que veio para o bem |

## Exemplos

```
You hit the nail on the head.      Você acertou em cheio.
It costs an arm and a leg.         Custa os olhos da cara.
```

> 💡 Idioms avançados exigem contexto — use-os com moderação e naturalidade,
> não em todo parágrafo.
""",
                [
                    ex("quiz", "O que 'bite the bullet' significa?",
                       "encarar algo difícil", ["encarar algo difícil", "morder uma bala", "desistir"]),
                    ex("quiz", "O que 'spill the beans' significa?",
                       "contar o segredo", ["contar o segredo", "derramar feijão", "cozinhar"]),
                    ex("text", "Complete: 'You hit the ___ on the head.' (exatamente)",
                       "nail"),
                    ex("audio", "Escute e transcreva:",
                       "it costs an arm and a leg", audio_text="It costs an arm and a leg."),
                    ex("quiz", "O que 'hit the nail on the head' significa?",
                       "acertar em cheio", ["acertar em cheio", "errar", "machucar"]),
                    ex("quiz", "O que 'cost an arm and a leg' significa?",
                       "custar muito caro", ["custar muito caro", "custar barato", "ser grátis"]),
                ],
            ),
            topic(
                "linguagem-metaforica",
                "Linguagem metafórica",
                """
# Linguagem metafórica

As **metáforas** emprestam imagens concretas para ideias abstratas — são
marca do C1.

## Metáforas comuns

```
the heart of the matter    o cerne da questão
a storm of emotions        uma onda de emoções
a ray of hope              um raio de esperança
time is money              tempo é dinheiro
```

## Exemplos

```
Let's get to the heart of the matter.   Vamos ao cerne da questão.
There is a ray of hope in the results.  Há um raio de esperança nos resultados.
```

> 💡 Metáforas tornam a linguagem mais vívida e expressiva — mas use as que
> os nativos realmente usam, para não soar estranho.
""",
                [
                    ex("quiz", "O que 'the heart of the matter' significa?",
                       "o cerne da questão", ["o cerne da questão", "o coração físico", "o início"]),
                    ex("quiz", "A metáfora 'time is money' significa:",
                       "tempo é valioso", ["tempo é valioso", "tempo não existe", "dinheiro é tempo literal"]),
                    ex("text", "Complete: 'There is a ray of ___ in the results.' (esperança)",
                       "hope"),
                    ex("audio", "Escute e transcreva:",
                       "let's get to the heart of the matter", audio_text="Let's get to the heart of the matter."),
                    ex("quiz", "Metáforas tornam a linguagem:",
                       "mais vívida e expressiva", ["mais vívida e expressiva", "mais confusa sempre", "mais curta"]),
                    ex("quiz", "O que 'a storm of emotions' sugere?",
                       "uma onda forte de sentimentos", ["uma onda forte de sentimentos", "uma tempestade literal", "calma"]),
                ],
            ),
            topic(
                "sinonimos-com-nuance",
                "Sinônimos com nuance",
                """
# Sinônimos com nuance

Sinônimos não são idênticos — cada um carrega **intensidade** e **tom**
diferentes.

## Escala de intensidade

```
happy  ->  content  ->  delighted  ->  thrilled
angry  ->  annoyed  ->  upset  ->  furious
important  ->  significant  ->  vital  ->  crucial
```

## Exemplos

```
She was absolutely delighted.    Ela ficou absolutamente encantada.
This is absolutely crucial.      Isso é absolutamente essencial.
```

> 💡 Escolher entre sinônimos é escolher a **intensidade exata**: "annoyed" é
> diferente de "furious".
""",
                [
                    ex("quiz", "Qual é MAIS forte que 'happy'?",
                       "thrilled", ["thrilled", "content", "ok"]),
                    ex("quiz", "Qual é MAIS forte que 'angry'?",
                       "furious", ["furious", "annoyed", "upset"]),
                    ex("text", "Complete: 'This is absolutely ___ to the project.' (essencial)",
                       "crucial"),
                    ex("audio", "Escute e transcreva:",
                       "she was absolutely delighted", audio_text="She was absolutely delighted."),
                    ex("quiz", "O que 'vital' significa?",
                       "vital (essencial)", ["vital (essencial)", "opcional", "pequeno"]),
                    ex("quiz", "Sinônimos com nuance permitem:",
                       "expressar intensidade e precisão", ["expressar intensidade e precisão", "repetir sempre a mesma", "simplificar demais"]),
                ],
            ),
            topic(
                "registro-c1",
                "Registro (C1)",
                """
# Registro (C1)

**Registro** é o nível de formalidade adequado a cada contexto. Escolher o
registro certo é uma habilidade de C1.

## Formal (e-mail, relatório)

```
I would like to request...      Gostaria de solicitar...
Please accept our apologies.    Por favor, aceite nossas desculpas.
```

## Informal (amigos)

```
Can you...? / Could you...?     Você pode...?
Sorry about that!               Desculpa por isso!
```

> 💡 O registro depende do **contexto e da audiência**: o mesmo pedido muda
> totalmente de forma entre um e-mail formal e uma mensagem para um amigo.
""",
                [
                    ex("quiz", "Em um e-mail formal, use:",
                       "I would like to request...", ["I would like to request...", "Give me...", "Wanna..."]),
                    ex("quiz", "A escolha de registro depende de:",
                       "contexto e audiência", ["contexto e audiência", "do humor", "da sorte"]),
                    ex("text", "Complete: 'I would ___ it if you could...' (agradecer, formal)",
                       "appreciate"),
                    ex("audio", "Escute e transcreva:",
                       "please accept our apologies", audio_text="Please accept our apologies."),
                    ex("quiz", "Em conversa com amigos, o registro é:",
                       "informal e descontraído", ["informal e descontraído", "formal", "jurídico"]),
                    ex("quiz", "Registro inadequado pode:",
                       "passar a impressão errada", ["passar a impressão errada", "nunca importar", "deixar mais bonito"]),
                ],
            ),
            topic(
                "formal-vs-informal",
                "Formal vs. informal",
                """
# Formal vs. informal

Pares de palavras formal/informal — saber os dois é essencial.

| Formal | Informal |
|---|---|
| begin | start |
| purchase | buy |
| assist | help |
| obtain | get |
| inquire | ask |
| terminate | end |

## Exemplos

```
I would like to inquire about...      Gostaria de perguntar sobre...
He obtained the results.              Ele obteve os resultados.
```

> 💡 **begin/purchase/assist/obtain/inquire** são as versões formais de
> start/buy/help/get/ask — usadas em textos e e-mails formais.
""",
                [
                    ex("quiz", "A versão formal de 'help' é:",
                       "assist", ["assist", "aid informal", "help"]),
                    ex("quiz", "A versão formal de 'get' é:",
                       "obtain", ["obtain", "receive informal", "grab"]),
                    ex("text", "Escreva a versão formal de 'start'.",
                       "begin"),
                    ex("audio", "Escute e transcreva:",
                       "i would like to inquire about", audio_text="I would like to inquire about..."),
                    ex("quiz", "A versão formal de 'ask' é:",
                       "inquire", ["inquire", "question informal", "say"]),
                    ex("quiz", "Saber os pares formal/informal é essencial para:",
                       "adequar a fala ao contexto", ["adequar a fala ao contexto", "decorar sem usar", "falar igual sempre"]),
                ],
            ),
            topic(
                "precisao-vocabular",
                "Precisão vocabular",
                """
# Precisão vocabular

No C1, palavras vagas como **nice/good/bad** dão lugar a palavras **precisas**.

## Substituindo o vago

```
nice        ->  remarkable / delightful / elegant
very good   ->  outstanding / exceptional
very bad    ->  appalling / dreadful
ok / fine   ->  mediocre / acceptable / decent
```

## Exemplos

```
The performance was remarkable.     A apresentação foi notável.
The result was mediocre, not great.   O resultado foi mediano, não ótimo.
```

> 💡 A precisão escolhe a palavra que expressa **exatamente** o grau e o tom —
> é o que diferencia o C1 do B2.
""",
                [
                    ex("quiz", "Em vez de 'nice', um sinônimo PRECISO é:",
                       "remarkable", ["remarkable", "ok", "fine"]),
                    ex("quiz", "Em vez de 'very bad', diga:",
                       "appalling", ["appalling", "okay", "small"]),
                    ex("text", "Complete: 'The result was ___ (mediano), not great.'",
                       "mediocre"),
                    ex("audio", "Escute e transcreva:",
                       "the performance was remarkable", audio_text="The performance was remarkable."),
                    ex("quiz", "Palavras vagas (nice, good) são:",
                       "imprecisas demais para o C1", ["imprecisas demais para o C1", "sempre melhores", "proibidas"]),
                    ex("quiz", "Para precisão, escolha a palavra que:",
                       "expressa exatamente o grau/tom", ["expressa exatamente o grau/tom", "é a mais comprida", "é a mais rara"]),
                ],
            ),
            topic(
                "familias-de-palavras-c1",
                "Famílias de palavras (C1)",
                """
# Famílias de palavras (C1)

Conhecer a família inteira permite usar a **classe certa** no contexto.

## Famílias importantes

```
economy (subst.) - economic (adj.) - economize (verbo)
analyze (verbo) - analysis (subst.) - analytical (adj.)
theory (subst.) - theoretical (adj.)
```

## Exemplos

```
The economic implications are clear.      As implicações econômicas são claras.
The analysis is very detailed.            A análise é muito detalhada.
```

> 💡 Aprenda a família toda junto: verbo, substantivo, adjetivo — assim você
> nunca erra a classe no texto.
""",
                [
                    ex("quiz", "O VERBO da família de 'economy' é:",
                       "economize", ["economize", "economic", "economical"]),
                    ex("quiz", "O ADJETIVO de 'analysis' é:",
                       "analytical", ["analytical", "analyze", "analyzed"]),
                    ex("text", "Escreva o adjetivo de 'theory'.",
                       "theoretical"),
                    ex("audio", "Escute e transcreva:",
                       "the analysis is very detailed", audio_text="The analysis is very detailed."),
                    ex("quiz", "Conhecer a família inteira permite:",
                       "usar a classe certa no contexto", ["usar a classe certa no contexto", "só decorar", "evitar usar"]),
                    ex("quiz", "Em 'the ___ implications', (econômico) entra:",
                       "economic", ["economic", "economy", "economize"]),
                ],
            ),
            topic(
                "vocabulario-contextual",
                "Vocabulário contextual",
                """
# Vocabulário contextual

Palavras mudam de sentido conforme o **contexto** — e você descobre o sentido
pelas pistas ao redor.

## A mesma palavra, sentidos diferentes

```
"run a company" (dirigir)  vs  "run fast" (correr)
"light food" (leve)  vs  "light on" (acesa)
```

## Como usar o contexto

1. Leia a frase inteira, não só a palavra.
2. Procure pistas (palavras vizinhas, tom).
3. Confirme o sentido com o parágrafo.

> 💡 **Conotação** é o tom que a palavra carrega (positivo/negativo/neutro).
> No C1, o vocabulário é aprendido em blocos e contextos, não palavra por
> palavra.
""",
                [
                    ex("quiz", "Para descobrir o sentido de palavra nova num texto:",
                       "use o contexto e as pistas ao redor", ["use o contexto e as pistas ao redor", "desista", "traduza letra a letra"]),
                    ex("quiz", "A mesma palavra pode mudar de sentido:",
                       "conforme o contexto", ["conforme o contexto", "nunca", "só em poesia"]),
                    ex("text", "Complete: 'The word \"run\" ___ on the context.' (depende)",
                       "depends"),
                    ex("audio", "Escute e transcreva:",
                       "the context determines the meaning", audio_text="The context determines the meaning."),
                    ex("quiz", "Conotação é:",
                       "o tom/sentimento que a palavra carrega", ["o tom/sentimento que a palavra carrega", "a gramática", "o tamanho"]),
                    ex("quiz", "No C1, o vocabulário é aprendido:",
                       "em contexto e blocos", ["em contexto e blocos", "isolado, palavra por palavra", "nunca"]),
                ],
            ),
        ],
    )


# ============================================================
# MODULO 19 - Speaking - C1
# ============================================================

def build_modulo_19_speaking_c1():
    return module(
        "modulo-19-speaking-c1",
        "Módulo 19 — Speaking — C1",
        "Falar em alto nível: discussões complexas, debates, apresentações, entrevistas, negociações, persuasão, pensamento crítico, temas abstratos/políticos/sociais, discussões técnicas, explicações simples, opiniões sutis, discordância e espontaneidade.",
        [
            topic(
                "discussoes-complexas",
                "Discussões complexas",
                """
# Discussões complexas

Em discussões profundas, você aprofunda, constrói sobre o ponto do outro e
sintetiza.

## Frases úteis

```
Let's delve into this.              Vamos aprofundar nisso.
To build on that point...           Somando a esse ponto...
That raises an important question.  Isso levanta uma questão importante.
Let's break this into parts.        Vamos dividir isso em partes.
```

> 💡 **delve into** = aprofundar. **To build on that point** acrescenta a
> ideia do outro — sinal de escuta ativa.
""",
                [
                    ex("quiz", "Para aprofundar um tema:",
                       "Let's delve into this.", ["Let's delve into this.", "Let's go home.", "Okay bye."]),
                    ex("quiz", "Para acrescentar ao ponto do outro:",
                       "To build on that point...", ["To build on that point...", "You're wrong.", "Silence."]),
                    ex("text", "Traduza: Isso levanta uma questão importante.",
                       "that raises an important question"),
                    ex("audio", "Escute e transcreva:",
                       "let's delve into the details", audio_text="Let's delve into the details."),
                    ex("quiz", "Em discussão complexa, 'to sum up' serve para:",
                       "sintetizar o que foi dito", ["sintetizar o que foi dito", "mudar de assunto", "despedir"]),
                    ex("quiz", "Para organizar uma discussão longa:",
                       "Let's break this into parts.", ["Let's break this into parts.", "Let's stop.", "Whatever."]),
                ],
            ),
            topic(
                "debates-c1",
                "Debates (C1)",
                """
# Debates (C1)

No debate de nível avançado, conteste com firmeza mas reconheça os bons
argumentos.

## Frases úteis

```
I take issue with that.              Discordo disso (formal).
That's a compelling argument.        É um argumento convincente.
Let me offer a counterpoint.         Deixe-me oferecer um contraponto.
So you're saying that...             Então você está dizendo que...
```

> 💡 **I take issue with** é uma discordância firme e educada. **compelling**
# ===== convencente =====
""",
                [
                    ex("quiz", "Para contestar com firmeza:",
                       "I take issue with that.", ["I take issue with that.", "That's fine.", "Maybe."]),
                    ex("quiz", "Para elogiar o argumento do oponente:",
                       "That's a compelling argument.", ["That's a compelling argument.", "That's terrible.", "Never."]),
                    ex("text", "Complete: 'Let me offer a ___ .' (contraponto)",
                       "counterpoint"),
                    ex("audio", "Escute e transcreva:",
                       "i take issue with that assumption", audio_text="I take issue with that assumption."),
                    ex("quiz", "Em debate, 'compelling' significa:",
                       "convincente", ["convincente", "fraco", "confuso"]),
                    ex("quiz", "Para reformular a posição do oponente antes de rebater:",
                       "So you're saying that...", ["So you're saying that...", "No.", "Bye."]),
                ],
            ),
            topic(
                "apresentacoes-c1",
                "Apresentações (C1)",
                """
# Apresentações (C1)

Apresentação de alto nível guia o público e destaca as ideias principais.

## Frases úteis

```
I'd like to walk you through...      Gostaria de guiá-los por...
Let me give you the big picture.     Deixe-me dar a visão geral.
The main takeaway is...              A principal ideia é...
```

> 💡 **walk you through** = guiar passo a passo. **takeaway** = a lição/
> ideia principal que se leva. **the big picture** = a visão geral.
""",
                [
                    ex("quiz", "Para guiar o público:",
                       "I'd like to walk you through...", ["I'd like to walk you through...", "I'm done.", "Hey."]),
                    ex("quiz", "O que 'the takeaway' significa?",
                       "a principal lição/ideia", ["a principal lição/ideia", "o lanche", "a saída"]),
                    ex("text", "Complete: 'Let me give you the ___ picture.' (visão geral)",
                       "big"),
                    ex("audio", "Escute e transcreva:",
                       "the main takeaway is simple", audio_text="The main takeaway is simple."),
                    ex("quiz", "Para dar a visão geral primeiro:",
                       "Let me give you the big picture.", ["Let me give you the big picture.", "Let's jump to the end.", "Never."]),
                    ex("quiz", "Uma apresentação C1 engaja o público:",
                       "com perguntas e interação", ["com perguntas e interação", "lendo slides", "em silêncio"]),
                ],
            ),
            topic(
                "entrevistas",
                "Entrevistas",
                """
# Entrevistas

A entrevista exige apresentar-se bem, falar de pontos fortes e encerrar com
elegância.

## Frases úteis

```
My strengths include...              Meus pontos fortes incluem...
I have five years of experience...   Tenho cinco anos de experiência...
I'm confident I can contribute...    Estou confiante que posso contribuir...
Thank you for this opportunity.      Obrigado por esta oportunidade.
```

> 💡 Ao final, faça uma boa pergunta: "What does a typical day look like?" —
> mostra interesse real pela vaga.
""",
                [
                    ex("quiz", "Para falar dos seus pontos fortes:",
                       "My strengths include...", ["My strengths include...", "I have no skills.", "Whatever."]),
                    ex("quiz", "Para encerrar bem a entrevista:",
                       "Thank you for this opportunity.", ["Thank you for this opportunity.", "I'm leaving.", "Bye."]),
                    ex("text", "Complete: 'I'm confident I can ___ to the team.' (contribuir)",
                       "contribute"),
                    ex("audio", "Escute e transcreva:",
                       "could you tell me about yourself", audio_text="Could you tell me about yourself?"),
                    ex("quiz", "Ao falar de experiência:",
                       "I have five years of experience in...", ["I have five years of experience in...", "I know nothing.", "Trust me."]),
                    ex("quiz", "Uma boa pergunta do candidato ao final:",
                       "What does a typical day look like?", ["What does a typical day look like?", "When can I leave?", "Do I have to work?"]),
                ],
            ),
            topic(
                "negociacoes-c1",
                "Negociações (C1)",
                """
# Negociações (C1)

No nível avançado, negocia-se com flexibilidade e busca-se o ganha-ganha.

## Frases úteis

```
I'm prepared to meet you halfway.    Estou disposto a encontrar um meio-termo.
Let's explore other options.         Vamos explorar outras opções.
Can we revisit the terms?            Podemos revisar os termos?
```

> 💡 **meet someone halfway** = ceder até o meio-termo. **revisit the terms**
# ===== reconsiderar os termos =====
""",
                [
                    ex("quiz", "Para ceder parcialmente:",
                       "I'm prepared to meet you halfway.", ["I'm prepared to meet you halfway.", "Take it or leave it.", "Never."]),
                    ex("quiz", "O que 'meet you halfway' significa?",
                       "encontrar um meio-termo", ["encontrar um meio-termo", "te encontrar na metade", "desistir"]),
                    ex("text", "Complete: 'Can we ___ the terms?' (revisar)",
                       "revisit"),
                    ex("audio", "Escute e transcreva:",
                       "i'm prepared to meet you halfway", audio_text="I'm prepared to meet you halfway."),
                    ex("quiz", "Para explorar alternativas:",
                       "Let's explore other options.", ["Let's explore other options.", "No alternatives exist.", "Done."]),
                    ex("quiz", "Boa negociação busca:",
                       "ganha-ganha", ["ganha-ganha", "só vencer", "humilhar"]),
                ],
            ),
            topic(
                "persuasao-c1",
                "Persuasão (C1)",
                """
# Persuasão (C1)

Persuasão sofisticada combina lógica, emoção e credibilidade.

## Frases úteis

```
I'd like to put forward...           Gostaria de apresentar...
There's a strong case for...         Há fortes razões para...
Imagine the outcome if...            Imagine o resultado se...
```

> 💡 **put forward** = apresentar (uma proposta). **a strong case for** =
> fortes argumentos a favor. Apelar à imaginação ("Imagine if...") engaja.
""",
                [
                    ex("quiz", "Para apresentar sua proposta:",
                       "I'd like to put forward...", ["I'd like to put forward...", "I want this.", "No."]),
                    ex("quiz", "O que 'there's a strong case for' significa?",
                       "há fortes razões para", ["há fortes razões para", "não há razão", "talvez"]),
                    ex("text", "Complete: 'There's a strong ___ for this change.' (caso)",
                       "case"),
                    ex("audio", "Escute e transcreva:",
                       "there is a strong case for the proposal", audio_text="There is a strong case for the proposal."),
                    ex("quiz", "Para apelar à imaginação:",
                       "Imagine the outcome if...", ["Imagine the outcome if...", "Do it now.", "Whatever."]),
                    ex("quiz", "Persuasão sofisticada combina:",
                       "lógica + emoção + credibilidade", ["lógica + emoção + credibilidade", "só gritaria", "só ameaça"]),
                ],
            ),
            topic(
                "pensamento-critico",
                "Pensamento crítico",
                """
# Pensamento crítico

Pensamento crítico é **avaliar** antes de aceitar — questionar suposições e
pedir evidência.

## Frases úteis

```
Let's question that assumption.       Vamos questionar essa suposição.
What's the evidence for this?         Qual é a evidência disso?
There's another way to look at this.  Há outra forma de ver isso.
Let's consider the counterargument.   Vamos considerar o contra-argumento.
```

> 💡 Pensamento crítico não é negar tudo — é avaliar com evidência e
> considerar o outro lado.
""",
                [
                    ex("quiz", "Para questionar uma suposição:",
                       "Let's question that assumption.", ["Let's question that assumption.", "Sounds great.", "Okay."]),
                    ex("quiz", "Para pedir evidência:",
                       "What's the evidence for this?", ["What's the evidence for this?", "Trust me.", "No."]),
                    ex("text", "Complete: 'There's another ___ to look at this.' (maneira)",
                       "way"),
                    ex("audio", "Escute e transcreva:",
                       "let's question that assumption", audio_text="Let's question that assumption."),
                    ex("quiz", "Pensamento crítico é:",
                       "avaliar antes de aceitar", ["avaliar antes de aceitar", "aceitar tudo", "negar tudo"]),
                    ex("quiz", "Para considerar o outro lado:",
                       "Let's consider the counterargument.", ["Let's consider the counterargument.", "It's perfect.", "Nothing more."]),
                ],
            ),
            topic(
                "temas-abstratos",
                "Temas abstratos",
                """
# Temas abstratos

Temas como liberdade, felicidade e justiça não têm resposta única — discutir
exige nuance.

## Frases úteis

```
That's an abstract concept.          É um conceito abstrato.
It's a matter of interpretation.     É uma questão de interpretação.
How do you define freedom?           Como você define liberdade?
On a philosophical level...          Em um nível filosófico...
```

> 💡 Em temas abstratos, **perguntar** é tão importante quanto opinar:
> "How do you define X?" abre a discussão.
""",
                [
                    ex("quiz", "Para falar de algo abstrato:",
                       "That's an abstract concept.", ["That's an abstract concept.", "It's a fact.", "No."]),
                    ex("quiz", "O que 'it's a matter of interpretation' significa?",
                       "depende da interpretação", ["depende da interpretação", "é um fato", "é impossível"]),
                    ex("text", "Complete: 'On a ___ level, ...' (filosófico)",
                       "philosophical"),
                    ex("audio", "Escute e transcreva:",
                       "happiness is a matter of interpretation", audio_text="Happiness is a matter of interpretation."),
                    ex("quiz", "Temas abstratos não têm:",
                       "resposta única e simples", ["resposta única e simples", "nenhum sentido", "só uma visão"]),
                    ex("quiz", "Para abrir uma discussão abstrata:",
                       "How do you define freedom?", ["How do you define freedom?", "What time is it?", "Let's eat."]),
                ],
            ),
            topic(
                "temas-politicos",
                "Temas políticos",
                """
# Temas políticos

Falar de política com maturidade é ouvir os dois lados e usar linguagem
neutra.

## Frases úteis

```
From a political standpoint...       Do ponto de vista político...
The policy raises concerns.          A política levanta preocupações.
Both sides have valid points.        Os dois lados têm pontos válidos.
It depends on your perspective.      Depende da sua perspectiva.
```

> 💡 Discutir política não é impor opinião — é **analisar** com isenção:
# ===== "Both sides have valid points" =====
""",
                [
                    ex("quiz", "Para falar sem partidarismo:",
                       "From a political standpoint...", ["From a political standpoint...", "My party is right.", "You're wrong."]),
                    ex("quiz", "O que 'raises concerns' significa?",
                       "levanta preocupações", ["levanta preocupações", "resolve tudo", "não importa"]),
                    ex("text", "Complete: 'The policy ___ valid concerns.' (levanta)",
                       "raises"),
                    ex("audio", "Escute e transcreva:",
                       "both sides have valid points", audio_text="Both sides have valid points."),
                    ex("quiz", "Discussão política madura:",
                       "ouve os dois lados", ["ouve os dois lados", "só grita", "só concorda"]),
                    ex("quiz", "Para não impor opinião:",
                       "It depends on your perspective.", ["It depends on your perspective.", "You must agree.", "No debate."]),
                ],
            ),
            topic(
                "questoes-sociais",
                "Questões sociais",
                """
# Questões sociais

Para discutir problemas sociais, nomeie o problema, proponha e analise.

## Frases úteis

```
This is a pressing issue.           Este é um problema urgente.
We need to address the root cause.  Precisamos atacar a causa raiz.
There's a gap between...            Há uma lacuna entre...
It's a systemic problem.            É um problema sistêmico.
```

> 💡 **pressing** = urgente. **systemic** = estrutural (não pontual).
# ===== address = tratar/enfrentar =====
""",
                [
                    ex("quiz", "Para chamar atenção a um problema:",
                       "This is a pressing issue.", ["This is a pressing issue.", "It's fine.", "Whatever."]),
                    ex("quiz", "O que 'address a problem' significa?",
                       "tratar/enfrentar um problema", ["tratar/enfrentar um problema", "endereçar (envio)", "ignorar"]),
                    ex("text", "Complete: 'We need to ___ the root cause.' (tratar)",
                       "address"),
                    ex("audio", "Escute e transcreva:",
                       "this is a pressing social issue", audio_text="This is a pressing social issue."),
                    ex("quiz", "O que 'systemic' significa?",
                       "sistêmico (estrutural)", ["sistêmico (estrutural)", "superficial", "temporário"]),
                    ex("quiz", "Para discutir uma solução social:",
                       "We should invest in education.", ["We should invest in education.", "Nothing works.", "It's hopeless."]),
                ],
            ),
            topic(
                "discussoes-tecnicas",
                "Discussões técnicas",
                """
# Discussões técnicas

Falar de tecnologia com clareza é explicar o **porquê e o como**, não só o
resultado.

## Frases úteis

```
In technical terms, ...             Em termos técnicos, ...
Let's look at the implementation.   Vamos ver a implementação.
The trade-off is between...         A compensação é entre...
Could you walk me through that?     Pode me guiar por isso?
```

> 💡 **trade-off** = a desvantagem aceita em troca de uma vantagem (ex.:
# ===== velocidade x custo). walk me through = explicar passo a passo =====
""",
                [
                    ex("quiz", "Para falar em termos técnicos:",
                       "In technical terms, ...", ["In technical terms, ...", "Trust me, it works.", "No."]),
                    ex("quiz", "O que 'trade-off' significa?",
                       "compensação/desvantagem aceita", ["compensação/desvantagem aceita", "vantagem total", "erro"]),
                    ex("text", "Complete: 'Let's look at the ___ .' (implementação)",
                       "implementation"),
                    ex("audio", "Escute e transcreva:",
                       "the trade-off is between speed and cost", audio_text="The trade-off is between speed and cost."),
                    ex("quiz", "Discussão técnica clara:",
                       "explica o porquê e o como", ["explica o porquê e o como", "só mostra resultado", "esconde detalhes"]),
                    ex("quiz", "Para perguntar um detalhe técnico:",
                       "Could you walk me through that?", ["Could you walk me through that?", "I don't care.", "Bye."]),
                ],
            ),
            topic(
                "explicando-simples",
                "Explicando temas complexos de forma simples",
                """
# Explicando temas complexos de forma simples

O teste de uma boa explicação é: **a outra pessoa entendeu**.

## Frases úteis

```
In plain English, ...              Em termos simples, ...
Think of it as a bridge.           Pense nisso como uma ponte.
To put it in a nutshell...         Em resumo...
The simplest way to say it is...   A forma mais simples de dizer é...
```

> 💡 Use **analogias** ("Think of it as...") e exemplos — é a forma mais
> rápida de simplificar o complexo.
""",
                [
                    ex("quiz", "Para explicar sem jargão:",
                       "In plain English, ...", ["In plain English, ...", "Technically speaking, blabla.", "No."]),
                    ex("quiz", "O que 'in a nutshell' significa?",
                       "em resumo", ["em resumo", "dentro de uma casca", "em detalhes"]),
                    ex("text", "Complete: 'Think of it ___ a bridge.' (como)",
                       "as"),
                    ex("audio", "Escute e transcreva:",
                       "in plain english it is very simple", audio_text="In plain English, it is very simple."),
                    ex("quiz", "O teste de uma explicação simples é:",
                       "a outra pessoa entender", ["a outra pessoa entender", "você falar bonito", "o jargão"]),
                    ex("quiz", "Para simplificar, use:",
                       "analogias e exemplos", ["analogias e exemplos", "termos técnicos", "siglas"]),
                ],
            ),
            topic(
                "opinioes-sutis",
                "Expressando opiniões sutis",
                """
# Expressando opiniões sutis

Opiniões de nível C1 admitem **nuance**: ressalvas, exceções e graus.

## Frases úteis

```
I'm inclined to think that...       Estou inclinado a achar que...
I'd be inclined to agree, though...  Eu tenderia a concordar, embora...
I can't entirely agree.             Não posso concordar inteiramente.
```

> 💡 **inclined to** = inclinado a (não é certeza, é tendência). A opinião
# ===== sutil não diz "100% sim ou não" — diz o grau e a exceção =====
""",
                [
                    ex("quiz", "Para dar opinião com ressalva:",
                       "I'd be inclined to agree, though...", ["I'd be inclined to agree, though...", "I agree 100%.", "No way."]),
                    ex("quiz", "O que 'inclined to' expressa?",
                       "inclinação (tendência a)", ["inclinação (tendência a)", "certeza", "proibição"]),
                    ex("text", "Complete: 'I'm inclined to ___ that...' (pensar)",
                       "think"),
                    ex("audio", "Escute e transcreva:",
                       "i am inclined to think it's a good idea", audio_text="I am inclined to think it's a good idea."),
                    ex("quiz", "Opinião sutil admite:",
                       "nuances e exceções", ["nuances e exceções", "só um lado", "só certezas"]),
                    ex("quiz", "Para suavizar um desacordo total:",
                       "I can't entirely agree.", ["I can't entirely agree.", "You're completely wrong.", "Never."]),
                ],
            ),
            topic(
                "lidando-com-discordancia",
                "Lidando com discordância",
                """
# Lidando com discordância

Discordar sem quebrar a relação é uma arte — reconheça o ponto do outro.

## Frases úteis

```
I understand where you're coming from, but...   Entendo seu ponto de vista, mas...
I hear you, but...                              Entendo o que você diz, mas...
Let's agree to disagree.                        Vamos concordar em discordar.
```

> 💡 "I understand where you're coming from" = reconhece a perspectiva antes
# ===== de contrapor. "Agree to disagree" encerra de forma madura =====
""",
                [
                    ex("quiz", "Para discordar sem ferir:",
                       "I understand where you're coming from, but...", ["I understand where you're coming from, but...", "You're wrong.", "No."]),
                    ex("quiz", "O que 'agree to disagree' significa?",
                       "concordar em discordar", ["concordar em discordar", "concordar totalmente", "desistir"]),
                    ex("text", "Complete: 'Let's ___ to disagree.' (concordar)",
                       "agree"),
                    ex("audio", "Escute e transcreva:",
                       "let's agree to disagree", audio_text="Let's agree to disagree."),
                    ex("quiz", "Para reconhecer o ponto do outro:",
                       "I hear you, but...", ["I hear you, but...", "Shut up.", "Whatever."]),
                    ex("quiz", "Lidar bem com discordância mantém:",
                       "o relacionamento e a conversa", ["o relacionamento e a conversa", "o silêncio", "a briga"]),
                ],
            ),
            topic(
                "falando-espontaneamente",
                "Falando espontaneamente",
                """
# Falando espontaneamente

Falar sem preparo exige **vocabulário automático** e frases-ponte para ganhar
tempo.

## Frases-ponte

```
Let me think for a moment.            Deixe-me pensar um momento.
That's a great question.              É uma ótima pergunta.
Off the top of my head...             De cabeça, sem pensar muito...
Let me put it this way.               Deixe-me colocar desta forma.
```

> 💡 As frases-ponte dão 2-3 segundos para organizar a resposta — tempo
# ===== suficiente para formular bem =====
""",
                [
                    ex("quiz", "Para ganhar tempo ao pensar:",
                       "Let me think for a moment.", ["Let me think for a moment.", "I don't know.", "Bye."]),
                    ex("quiz", "O que 'off the top of my head' significa?",
                       "de cabeça, sem pensar muito", ["de cabeça, sem pensar muito", "no topo da cabeça literal", "nunca"]),
                    ex("text", "Complete: 'That's a ___ question.' (ótima)",
                       "great"),
                    ex("audio", "Escute e transcreva:",
                       "off the top of my head i'd say yes", audio_text="Off the top of my head, I'd say yes."),
                    ex("quiz", "Para reformular na hora:",
                       "Let me put it this way.", ["Let me put it this way.", "Whatever.", "No."]),
                    ex("quiz", "Falar espontâneo melhora com:",
                       "prática e vocabulário automático", ["prática e vocabulário automático", "silêncio", "decorar tudo"]),
                ],
            ),
        ],
    )


# ============================================================
# MODULO 20 - Listening - C1
# ============================================================

def build_modulo_20_listening_c1():
    return module(
        "modulo-20-listening-c1",
        "Módulo 20 — Listening — C1",
        "Ouvido avançado: conversas nativas, fala rápida, sotaques, podcasts, entrevistas, palestras, notícias, filmes, séries, conteúdo técnico, humor, sarcasmo, sentido implícito e tom.",
        [
            topic(
                "conversas-nativas",
                "Conversas nativas",
                """
# Conversas nativas

Conversas entre nativos são **rápidas**, **idiomáticas** e cheias de
**sobreposição** (um fala por cima do outro).

## Como acompanhar

1. Foque no **fluxo da ideia**, não em cada palavra.
2. Reconheça **chunks** prontos ("I was like...", "You know what I mean?").
3. Use o contexto para preencher o que passou.

## Exemplos de fala nativa

```
I was like, really?          Eu fiquei tipo, sério?
You know what I mean?        Entende o que quero dizer?
```

> 💡 "I was like..." é usado para **relatar** o que pensou/sentiu — muito
> comum entre nativos.
""",
                [
                    ex("quiz", "Conversas nativas são difíceis porque:",
                       "rápidas, idiomáticas e sobrepostas", ["rápidas, idiomáticas e sobrepostas", "sempre com palavras fáceis", "nunca mudam"]),
                    ex("audio", "Escute e transcreva:",
                       "you know what i mean", audio_text="You know what I mean?"),
                    ex("quiz", "Para acompanhar conversa nativa, foque em:",
                       "o fluxo da ideia, não cada palavra", ["o fluxo da ideia, não cada palavra", "cada letra", "só o início"]),
                    ex("audio", "Escute e transcreva:",
                       "i was like really", audio_text="I was like, really?"),
                    ex("quiz", "'I was like...' é usado para:",
                       "relatar o que pensou/sentiu", ["relatar o que pensou/sentiu", "perguntar", "despedir"]),
                    ex("quiz", "A prática para conversas nativas é:",
                       "exposição frequente a fala real", ["exposição frequente a fala real", "só ler", "nunca ouvir"]),
                ],
            ),
            topic(
                "fala-rapida",
                "Fala rápida",
                """
# Fala rápida

Fala acelerada exige estratégia — e não há vergonha em pedir para repetir.

## Estratégias

- **Capte o sentido geral** — você não precisa de cada sílaba.
- **Peça para desacelerar**: "Could you speak more slowly, please?"
- **Peça para repetir**: "Sorry, could you say that again?"

> 💡 Pedir repetição é **normal e esperado** — até nativos fazem. É o oposto
# ===== de fraqueza =====
""",
                [
                    ex("quiz", "Quando a fala está rápida demais:",
                       "peça para desacelerar educadamente", ["peça para desacelerar educadamente", "desista", "grite"]),
                    ex("quiz", "Como pedir para falar mais devagar:",
                       "Could you speak more slowly, please?", ["Could you speak more slowly, please?", "Stop.", "Bye."]),
                    ex("text", "Complete: 'Could you ___ down a bit?' (desacelerar)",
                       "slow"),
                    ex("audio", "Escute e transcreva:",
                       "could you speak more slowly please", audio_text="Could you speak more slowly, please?"),
                    ex("quiz", "Em fala rápida, o importante é:",
                       "captar o sentido geral", ["captar o sentido geral", "cada sílaba", "a gramática"]),
                    ex("quiz", "Pedir repetição é:",
                       "normal e esperado", ["normal e esperado", "sinal de fraqueza", "proibido"]),
                ],
            ),
            topic(
                "sotaques-c1",
                "Sotaques (C1)",
                """
# Sotaques (C1)

No C1, você precisa entender uma variedade maior de sotaques.

## Sotaques comuns além de americano/britânico

```
australiano       (diferente ritmo e vogais)
indiano           (ritmo próprio)
sul-africano      (pronúncia distinta)
```

## A defesa é a exposição

Quanto mais sotaques você ouvir, mais fácil cada um fica. Treine com
entrevistas, podcasts e vídeos de países diferentes.

> 💘 **A única defesa contra sotaques é exposição variada e repetida.**
""",
                [
                    ex("quiz", "Além de americano/britânico, é comum ouvir:",
                       "australiano, indiano, sul-africano", ["australiano, indiano, sul-africano", "só um", "nenhum"]),
                    ex("audio", "Escute e transcreva:",
                       "it's a different accent", audio_text="It's a different accent."),
                    ex("quiz", "A melhor defesa contra sotaques é:",
                       "exposição variada", ["exposição variada", "evitar", "só ouvir um"]),
                    ex("quiz", "Palavras podem mudar de pronúncia por sotaque:",
                       "sim, além de algumas palavras (color/colour)", ["sim, além de algumas palavras (color/colour)", "nunca", "só em poesia"]),
                    ex("audio", "Escute e transcreva:",
                       "could you repeat that please", audio_text="Could you repeat that, please?"),
                    ex("quiz", "Entender sotaques novos é questão de:",
                       "treino de exposição", ["treino de exposição", "inteligência", "sorte"]),
                ],
            ),
            topic(
                "podcasts-c1",
                "Podcasts (C1)",
                """
# Podcasts (C1)

No nível avançado, podcasts são o treino ideal: temas variados e fala real.

## Como aproveitar

1. Escolha temas que **interessam** e que você quer aprender.
2. Pratique **escuta ativa**: preveja, tome notas, resuma.
3. Depois de ouvir, **resuma** o que entendeu em voz alta.

## Vocabulário

```
subscribe       inscrever-se
episode         episódio
host            apresentador
```

> 💡 Podcasts melhoram compreensão de fala real, vocabulário e — se você
> resumir — até a fala.
""",
                [
                    ex("quiz", "Para podcasts avançados, escolha:",
                       "temas que você gosta e quer aprender", ["temas que você gosta e quer aprender", "temas impossíveis", "só músicas"]),
                    ex("quiz", "Escuta ATIVA inclui:",
                       "tomar notas e resumir", ["tomar notas e resumir", "dormir", "pausar sempre"]),
                    ex("text", "Complete: 'I'm ___ to this podcast.' (inscrito)",
                       "subscribed"),
                    ex("audio", "Escute e transcreva:",
                       "welcome back to the podcast", audio_text="Welcome back to the podcast."),
                    ex("quiz", "Depois de ouvir, o ideal é:",
                       "resumir o que entendeu", ["resumir o que entendeu", "esquecer", "pular"]),
                    ex("quiz", "Podcasts melhoram:",
                       "compreensão de fala real e vocabulário", ["compreensão de fala real e vocabulário", "só leitura", "nada"]),
                ],
            ),
            topic(
                "entrevistas-c1",
                "Entrevistas (C1)",
                """
# Entrevistas (C1)

Entrevistas (rádio, TV, trabalho) seguem o padrão **pergunta -> resposta
desenvolvida**.

## O que o entrevistado faz

- Desenvolve a resposta com **exemplos** e **contexto**.
- Faz pausas e reformula ("Let me put it this way...").

## Para acompanhar

1. Identifique a **pergunta**.
2. Ouça o **exemplo** e a **conclusão**.
3. Não trave em detalhes — siga o fluxo.

> 💡 A estrutura típica é: pergunta -> resposta desenvolvida (não sim/não).
""",
                [
                    ex("quiz", "Numa entrevista, o entrevistado:",
                       "desenvolve a resposta com exemplos", ["desenvolve a resposta com exemplos", "responde sim/não", "foge"]),
                    ex("audio", "Escute e transcreva:",
                       "could you tell us about your career", audio_text="Could you tell us about your career?"),
                    ex("quiz", "Para entender a resposta, foque em:",
                       "o exemplo e a conclusão", ["o exemplo e a conclusão", "o início só", "o silêncio"]),
                    ex("quiz", "Entrevistas de trabalho testam:",
                       "como você pensa e se comunica", ["como você pensa e se comunica", "só o currículo", "a sorte"]),
                    ex("audio", "Escute e transcreva:",
                       "that's a very good question", audio_text="That's a very good question."),
                    ex("quiz", "A estrutura típica de entrevista é:",
                       "pergunta -> resposta desenvolvida", ["pergunta -> resposta desenvolvida", "resposta -> pergunta", "nada"]),
                ],
            ),
            topic(
                "palestras",
                "Palestras (TED talks)",
                """
# Palestras (TED talks)

Palestras usam **signposting** — frases que guiam o ouvinte pela estrutura.

## Signposting comum

```
First, I'll explain...         Primeiro, vou explicar...
Let me tell you a story.       Deixe-me contar uma história.
Now, let's look at the data.   Agora, vamos ver os dados.
To sum up...                   Para resumir...
```

## Como acompanhar

- Anote as **ideias-chave** e os **exemplos**.
- Preste atenção nas frases de transição.

> 💡 Palestras têm estrutura clara — por isso são um dos melhores treinos de
> listening para temas variados.
""",
                [
                    ex("quiz", "Palestras usam 'signposting' para:",
                       "guiar o ouvinte pela estrutura", ["guiar o ouvinte pela estrutura", "confundir", "decorar"]),
                    ex("quiz", "O que 'First, I'll explain...' faz?",
                       "sinaliza a estrutura", ["sinaliza a estrutura", "termina", "pergunta"]),
                    ex("text", "Complete: 'Let me ___ you a story.' (contar)",
                       "tell"),
                    ex("audio", "Escute e transcreva:",
                       "let me tell you a story", audio_text="Let me tell you a story."),
                    ex("quiz", "Para acompanhar uma palestra, anote:",
                       "as ideias-chave e exemplos", ["as ideias-chave e exemplos", "cada palavra", "a decoração"]),
                    ex("quiz", "Palestras são ótimo treino porque:",
                       "têm estrutura clara e tópicos variados", ["têm estrutura clara e tópicos variados", "são curtas demais", "não têm áudio"]),
                ],
            ),
            topic(
                "noticias-c1",
                "Notícias (C1)",
                """
# Notícias (C1)

Notícias usam vocabulário **formal e específico** de política, economia e
sociedade.

## Estrutura

```
Headline:      título curto e direto
Lead:          primeiro parágrafo (o que, quem, onde, quando)
Body:          detalhes e contexto
```

## Vocabulário de notícia

```
announce        anunciar
to rise / fall  subir / cair
concerns        preocupações
policy          política (medida)
```

> 💡 Ler/ouvir um pouco de notícia todo dia é uma forma rápida de absorver
> vocabulário formal em contexto.
""",
                [
                    ex("quiz", "Notícias em inglês usam vocabulário:",
                       "formal e específico", ["formal e específico", "só gírias", "só informal"]),
                    ex("quiz", "O lead (primeiro parágrafo) responde:",
                       "o que, quem, onde, quando", ["o que, quem, onde, quando", "só quando", "nada"]),
                    ex("text", "Complete: 'The government ___ a new policy.' (anunciou)",
                       "announced"),
                    ex("audio", "Escute e transcreva:",
                       "the government announced a new policy", audio_text="The government announced a new policy."),
                    ex("quiz", "Para acompanhar notícias, leia/ouça:",
                       "um pouco todo dia", ["um pouco todo dia", "uma vez por ano", "nunca"]),
                    ex("quiz", "Notícias expõem vocabulário de:",
                       "política, economia e sociedade", ["política, economia e sociedade", "só esporte", "nada"]),
                ],
            ),
            topic(
                "filmes-c1",
                "Filmes (C1)",
                """
# Filmes (C1)

Filmes são treino completo: fala natural, rápida e cheia de expressões.

## Estratégia

1. **1ª vez**: legenda em inglês.
2. **2ª vez**: sem legenda.
3. **Cenas difíceis**: rever com legenda para conectar som e escrita.

## Vocabulário

```
subtitles    legendas
classic      clássico
plot         enredo
ending       final
```

> 💡 Filmes ajudam principalmente com fala rápida e coloquial — o inglês
> real, fora da sala de aula.
""",
                [
                    ex("quiz", "Para treinar com filmes:",
                       "legenda em inglês e depois sem", ["legenda em inglês e depois sem", "legenda em português sempre", "sem nunca usar"]),
                    ex("quiz", "Filmes têm linguagem:",
                       "natural e variada (incluindo gírias)", ["natural e variada (incluindo gírias)", "formal só", "sem fala"]),
                    ex("text", "Complete: 'I watched it with English ___ .' (legendas)",
                       "subtitles"),
                    ex("audio", "Escute e transcreva:",
                       "this movie is a classic", audio_text="This movie is a classic."),
                    ex("quiz", "Rever cenas difíceis com legenda ajuda a:",
                       "conectar som e escrita", ["conectar som e escrita", "decorar sem ouvir", "nada"]),
                    ex("quiz", "Filmes ajudam com:",
                       "fala rápida e coloquial", ["fala rápida e coloquial", "só gramática", "nada"]),
                ],
            ),
            topic(
                "series-c1",
                "Séries (C1)",
                """
# Séries (C1)

Séries são **treino de longo prazo**: você acompanha os mesmos personagens e
contextos por muitos episódios.

## Por que funcionam

- **Contexto recorrente**: o vocabulário se repete e fixa.
- **Fala natural**: conversas rápidas, gírias e expressões.
- **Consistência**: você se acostuma com o ritmo dos personagens.

## Estratégia

Comece com a legenda em inglês e, gradualmente, tire a legenda em episódios
que você já assistiu.

> 💡 Séries ensinam fala natural com repetição de padrões — a combinação
> ideal para o listening.
""",
                [
                    ex("quiz", "Vantagem das séries:",
                       "consistência de personagens e contexto", ["consistência de personagens e contexto", "são curtas demais", "não têm áudio"]),
                    ex("quiz", "O contexto recorrente das séries:",
                       "facilita entender vocabulário novo", ["facilita entender vocabulário novo", "atrapalha", "não existe"]),
                    ex("text", "Complete: 'I'm on season three of this ___ .' (série)",
                       "series"),
                    ex("audio", "Escute e transcreva:",
                       "i'm on season three", audio_text="I'm on season three."),
                    ex("quiz", "Para acompanhar série sem legenda:",
                       "exponha-se gradualmente", ["exponha-se gradualmente", "tente tudo de uma vez", "desista"]),
                    ex("quiz", "Séries ensinam:",
                       "fala natural e repetição de padrões", ["fala natural e repetição de padrões", "só escrita", "nada"]),
                ],
            ),
            topic(
                "conteudo-tecnico",
                "Conteúdo técnico",
                """
# Conteúdo técnico

Vídeos e podcasts técnicos (programação, TI) usam **inglês técnico** — e o
vocabulário se aprende no contexto.

## Vocabulário técnico comum

```
source code     código-fonte
debug           depurar
error           erro
deploy          publicar/implementar
implementation  implementação
```

## Como acompanhar

- Assista com **pausas** e **repetição**.
- Anote o vocabulário novo no contexto.

> 💡 Para quem vai trabalhar com tecnologia, o inglês técnico é uma das
> habilidades mais valiosas — e treina o listening ao mesmo tempo.
""",
                [
                    ex("quiz", "Conteúdo técnico exige:",
                       "entender o vocabulário no contexto", ["entender o vocabulário no contexto", "decorar jargão solto", "evitar"]),
                    ex("quiz", "Vídeos de programação usam:",
                       "inglês técnico e passo a passo", ["inglês técnico e passo a passo", "só português", "gírias"]),
                    ex("text", "Complete: 'Let's look at the ___ code.' (código-fonte)",
                       "source"),
                    ex("audio", "Escute e transcreva:",
                       "let's debug this error", audio_text="Let's debug this error."),
                    ex("quiz", "Para entender tutoriais, assista:",
                       "com pausas e repetição", ["com pausas e repetição", "uma vez rápido", "nunca"]),
                    ex("quiz", "Vocabulário técnico em inglês é valioso para:",
                       "o mercado de tecnologia", ["o mercado de tecnologia", "só literatura", "nada"]),
                ],
            ),
            topic(
                "humor-e-sarcasmo",
                "Humor e sarcasmo",
                """
# Humor e sarcasmo

O **sarcasmo** diz o **oposto** do que as palavras significam — o tom
revela a intenção.

## Como funciona

```
"Great job!" (com tom irônico) = crítica disfarçada
"Oh great, it's raining again." = frustração
```

## Para detectar

- Preste atenção no **tom** e no **contexto**.
- Se a frase parece boa demais para a situação, é provável sarcasmo.

> 💡 Sarcasmo e ironia são comuns em séries e conversas — entender é parte
> do C1.
""",
                [
                    ex("quiz", "O sarcasmo costuma dizer:",
                       "o oposto do que significa", ["o oposto do que significa", "exatamente o que diz", "nada"]),
                    ex("quiz", "'Great job!' com tom irônico significa:",
                       "crítica disfarçada", ["crítica disfarçada", "elogio sincero", "pergunta"]),
                    ex("text", "Complete: 'He said it with a ___ tone.' (sarcástico)",
                       "sarcastic"),
                    ex("audio", "Escute e transcreva:",
                       "oh great it's raining again", audio_text="Oh great, it's raining again."),
                    ex("quiz", "Para detectar sarcasmo, preste atenção ao:",
                       "tom e contexto", ["tom e contexto", "só às palavras", "ao tamanho"]),
                    ex("quiz", "Ironia e sarcasmo aparecem muito em:",
                       "séries e conversas", ["séries e conversas", "documentos legais", "manuais"]),
                ],
            ),
            topic(
                "sentido-implicito",
                "Sentido implícito",
                """
# Sentido implícito

**Sentido implícito** é o que se entende **sem estar dito** — ler as
entrelinhas.

## Exemplos

```
"I'm fine." (tom seco)  ->  na verdade, não está bem.
"If you know what I mean."  ->  há um sentido nas entrelinhas.
```

## Como captar

- Use o **contexto** e o **tom**.
- Compare o que foi dito com a situação real.

> 💡 Implícitos são comuns em conversas e humor. No C1, você capta o que
> ficou nas entrelinhas.
""",
                [
                    ex("quiz", "'I'm fine' com tom seco pode significar:",
                       "o oposto (não está bem)", ["o oposto (não está bem)", "está ótimo", "é uma pergunta"]),
                    ex("quiz", "Sentido implícito é:",
                       "o que se entende sem estar dito", ["o que se entende sem estar dito", "o que está escrito", "nada"]),
                    ex("text", "Complete: 'You need to read ___ the lines.' (nas entrelinhas)",
                       "between"),
                    ex("audio", "Escute e transcreva:",
                       "if you know what i mean", audio_text="If you know what I mean."),
                    ex("quiz", "Para captar sentido implícito, use:",
                       "contexto e tom", ["contexto e tom", "só o dicionário", "a sorte"]),
                    ex("quiz", "Implícitos são comuns em:",
                       "conversas e humor", ["conversas e humor", "manuais técnicos", "formulários"]),
                ],
            ),
            topic(
                "tom-e-intencao",
                "Tom e intenção",
                """
# Tom e intenção

O **tom de voz** revela a intenção: pedido, ordem, sarcasmo, urgência.

## Exemplos

```
"Could you...?" (tom educado)  = pedido
"Could you...?" (tom seco)     = quase uma ordem
```

## Como combinar

Entenda juntando **tom + palavras + contexto**:

```
tom + palavras + contexto = intenção
```

> 💡 A mesma frase muda totalmente de sentido com o tom. No C1, você lê o
> tom como parte da mensagem.
""",
                [
                    ex("quiz", "O tom indica a:",
                       "intenção (pedido, urgência, sarcasmo)", ["intenção (pedido, urgência, sarcasmo)", "gramática", "ortografia"]),
                    ex("quiz", "'Could you...?' com tom educado indica:",
                       "pedido", ["pedido", "ordem", "piada"]),
                    ex("text", "Complete: 'Her ___ showed she was upset.' (tom de voz)",
                       "tone"),
                    ex("audio", "Escute e transcreva:",
                       "could you help me with this", audio_text="Could you help me with this?"),
                    ex("quiz", "A mesma frase muda de sentido com:",
                       "o tom", ["o tom", "o tamanho", "a cor"]),
                    ex("quiz", "Para entender a intenção, combine:",
                       "tom + palavras + contexto", ["tom + palavras + contexto", "só palavras", "só contexto"]),
                ],
            ),
        ],
    )


# ============================================================
# MODULO 21 - Reading - C1
# ============================================================

def build_modulo_21_reading_c1():
    return module(
        "modulo-21-reading-c1",
        "Módulo 21 — Reading — C1",
        "Leitura avançada: notícias, ensaios, artigos de opinião, textos acadêmicos, documentação técnica, literatura, jornalismo long-form, documentação profissional, e as habilidades de identificar argumentos, viés, sentido implícito e tom.",
        [
            topic(
                "lendo-noticias",
                "Lendo notícias (C1)",
                """
# Lendo notícias (C1)

Notícias têm estrutura própria: **manchete** + **lead** + **corpo**.

## Manchetes compactas

```
Ban Raises Rates      O banco aumenta as taxas.
Leaders Meet in Paris  Líderes se reúnem em Paris.
```

As manchetes omitem artigos e verbos para caber em uma linha.

## Lead

O primeiro parágrafo responde: o que, quem, onde, quando.

> 💡 Vocabulário formal de notícia: **announce** (anunciar), **surge**
# ===== (disparar), decline (cair), concern (preocupação) =====
""",
                [
                    ex("quiz", "Manchetes em inglês costumam:",
                       "omitir palavras (títulos compactos)", ["omitir palavras (títulos compactos)", "ser frases longas", "ser informais"]),
                    ex("quiz", "O que 'Ban Raises Rates' significa?",
                       "o banco aumenta as taxas", ["o banco aumenta as taxas", "o banco baixa as taxas", "o banco fecha"]),
                    ex("text", "Complete: 'The newspaper ___ the article.' (publicou)",
                       "published"),
                    ex("audio", "Escute e transcreva:",
                       "the article covers the crisis", audio_text="The article covers the crisis."),
                    ex("quiz", "No lead, a informação essencial é:",
                       "o que, quem, onde, quando", ["o que, quem, onde, quando", "só o título", "só o final"]),
                    ex("quiz", "Vocabulário formal de notícia inclui:",
                       "announce, surge, decline", ["announce, surge, decline", "gírias", "emojis"]),
                ],
            ),
            topic(
                "lendo-ensaios",
                "Lendo ensaios",
                """
# Lendo ensaios

Um ensaio segue: **tese** (introdução) -> **argumentos** (corpo) ->
**conclusão**.

## Para seguir o argumento

- Encontre a **tese** na introdução.
- Siga os **conectivos**: however, moreover, therefore.
- Veja como a **conclusão** retoma a tese.

## Vocabulário

```
the author argues that...   o autor argumenta que...
the essay examines...       o ensaio examina...
```

> 💡 Ensaio acadêmico usa hedging e tom formal: "The author argues",
> # ===== não "I think" =====
""",
                [
                    ex("quiz", "Num ensaio, a tese aparece:",
                       "na introdução", ["na introdução", "só no fim", "nunca"]),
                    ex("quiz", "Para seguir o argumento, procure:",
                       "os conectivos (however, moreover)", ["os conectivos (however, moreover)", "só os nomes", "nada"]),
                    ex("text", "Complete: 'The author ___ that...' (argumenta)",
                       "argues"),
                    ex("audio", "Escute e transcreva:",
                       "the author argues that change is needed", audio_text="The author argues that change is needed."),
                    ex("quiz", "A conclusão de um ensaio:",
                       "retoma a tese e sintetiza", ["retoma a tese e sintetiza", "introduz tema novo", "pergunta"]),
                    ex("quiz", "Ensaio acadêmico usa:",
                       "hedging e tom formal", ["hedging e tom formal", "gírias", "primeira pessoa o tempo todo"]),
                ],
            ),
            topic(
                "artigos-de-opiniao",
                "Artigos de opinião",
                """
# Artigos de opinião

Um **artigo de opinião** (op-ed) defende uma posição com argumentos e
evidência.

## Para reconhecer a posição do autor

- Leia o **título** e o **primeiro parágrafo**.
- Leia o **último parágrafo** (a conclusão).
- Identifique a linguagem opinativa: "I believe", "it is clear".

## Vocabulário

```
opinion piece     artigo de opinião
makes a strong case   apresenta fortes argumentos
```

> 💡 Opinião se apoia em **evidência e argumentos** — não só emoção.
""",
                [
                    ex("quiz", "Um artigo de opinião defende:",
                       "uma posição específica", ["uma posição específica", "só fatos", "nada"]),
                    ex("quiz", "Para reconhecer a posição do autor:",
                       "leia título, 1º e último parágrafo", ["leia título, 1º e último parágrafo", "só o meio", "nada"]),
                    ex("text", "Complete: 'In my ___ , the policy is unfair.' (opinião)",
                       "opinion"),
                    ex("audio", "Escute e transcreva:",
                       "this opinion piece makes a strong case", audio_text="This opinion piece makes a strong case."),
                    ex("quiz", "Opinião se apoia em:",
                       "evidência e argumentos", ["evidência e argumentos", "só emoção", "só autoridade"]),
                    ex("quiz", "Linguagem opinativa inclui:",
                       "I believe, it is clear", ["I believe, it is clear", "it is said (neutro)", "maybe not"]),
                ],
            ),
            topic(
                "textos-academicos",
                "Textos acadêmicos",
                """
# Textos acadêmicos

O artigo acadêmico tem **abstract**, **metodologia**, **resultados**,
**discussão** e **conclusão**.

## Estratégia de leitura

1. Leia o **abstract** (resumo) e a **conclusão** primeiro.
2. Depois, vá para a **discussão**.
3. Por fim, os detalhes da metodologia.

## Vocabulário

```
abstract        resumo
suggests        sugere
evidence        evidência
significant     significativo
```

> 💡 Citações dão crédito e apoio ao argumento. Hedging ("may",
> # ===== "suggests") suaviza as afirmações =====
""",
                [
                    ex("quiz", "O 'abstract' de um artigo:",
                       "resume o estudo (objetivo, método, resultado)", ["resume o estudo (objetivo, método, resultado)", "é a conclusão longa", "é o título"]),
                    ex("quiz", "Citações em texto acadêmico:",
                       "dão crédito e apoio ao argumento", ["dão crédito e apoio ao argumento", "são proibidas", "são opcionais sempre"]),
                    ex("text", "Complete: 'The study ___ a positive effect.' (sugere)",
                       "suggests"),
                    ex("audio", "Escute e transcreva:",
                       "the results suggest a significant change", audio_text="The results suggest a significant change."),
                    ex("quiz", "Hedging acadêmico ('may', 'suggests'):",
                       "suaviza afirmações", ["suaviza afirmações", "afirma com certeza", "nega"]),
                    ex("quiz", "Para ler artigo acadêmico, comece pelo:",
                       "abstract e conclusão", ["abstract e conclusão", "meio", "índice de figuras"]),
                ],
            ),
            topic(
                "documentacao-tecnica",
                "Documentação técnica",
                """
# Documentação técnica

Documentação (README, manuais, API docs) usa **instruções diretas e
precisas**.

## Vocabulário comum

```
install        instalar
run            rodar
configure      configurar
deploy         publicar
```

## Exemplos

```
Install the package first.     Instale o pacote primeiro.
For more info, see the docs.   Para mais informações, veja a documentação.
```

> 💡 README explica o que o projeto faz e como usar. O tom é imperativo e
# ===== objetivo =====
""",
                [
                    ex("quiz", "Documentação técnica usa:",
                       "instruções diretas e precisas", ["instruções diretas e precisas", "linguagem poética", "gírias"]),
                    ex("quiz", "Em manuais, 'Press the button' é:",
                       "um comando direto", ["um comando direto", "uma pergunta", "uma piada"]),
                    ex("text", "Complete: 'For more info, see the ___ below.' (documentação)",
                       "docs"),
                    ex("audio", "Escute e transcreva:",
                       "install the package first", audio_text="Install the package first."),
                    ex("quiz", "README explica:",
                       "o que o projeto faz e como usar", ["o que o projeto faz e como usar", "a história do autor", "piadas"]),
                    ex("quiz", "Vocabulário de docs inclui:",
                       "install, run, configure, deploy", ["install, run, configure, deploy", "só poesia", "emojis"]),
                ],
            ),
            topic(
                "literatura",
                "Literatura",
                """
# Literatura

A leitura literária exige atenção a **tom**, **tema** e **subtexto**.

## Vocabulário literário

```
novel          romance (livro)
is set in...   se passa em...
foreshadowing  prenúncio
theme          tema
```

## Exemplos

```
The novel is set in Paris.     O romance se passa em Paris.
The author uses irony.         O autor usa ironia.
```

> 💡 Personagens e cenários revelam o tema. **Foreshadowing** dá pistas do
# ===== que virá =====
""",
                [
                    ex("quiz", "Narrativa literária usa:",
                       "linguagem figurativa e tom", ["linguagem figurativa e tom", "só fatos", "só diálogo"]),
                    ex("quiz", "O que 'foreshadowing' significa?",
                       "prenúncio (pista do futuro)", ["prenúncio (pista do futuro)", "flashback", "descrição"]),
                    ex("text", "Complete: 'The novel ___ in the 19th century.' (se passa)",
                       "is set"),
                    ex("audio", "Escute e transcreva:",
                       "the novel is set in paris", audio_text="The novel is set in Paris."),
                    ex("quiz", "Personagens e cenários revelam:",
                       "o tema e o tom", ["o tema e o tom", "só o enredo", "nada"]),
                    ex("quiz", "Para ler literatura, foque em:",
                       "tom, tema e subtexto", ["tom, tema e subtexto", "contar palavras", "só diálogo"]),
                ],
            ),
            topic(
                "jornalismo-long-form",
                "Jornalismo long-form",
                """
# Jornalismo long-form

**Long-form journalism** é a reportagem longa, com narrativa, dados e
análise.

## Como ler

- Use os **subtítulos** para navegar.
- Anote os pontos principais de cada seção.
- Perceba como narrativa + dados + análise se combinam.

## Vocabulário

```
investigation      investigação
exposed            revelou/expôs
evidence           evidência
analysis           análise
```

> 💡 Long-form combina história e contexto — não é só opinião nem só fato.
""",
                [
                    ex("quiz", "Long-form journalism é:",
                       "reportagem longa com análise e contexto", ["reportagem longa com análise e contexto", "um tuíte", "um headline"]),
                    ex("quiz", "Para acompanhar reportagem longa, use:",
                       "subtítulos e parágrafos-chave", ["subtítulos e parágrafos-chave", "só o fim", "nada"]),
                    ex("text", "Complete: 'The investigation ___ corruption.' (revelou)",
                       "exposed"),
                    ex("audio", "Escute e transcreva:",
                       "the investigation exposed a serious problem", audio_text="The investigation exposed a serious problem."),
                    ex("quiz", "Long-form combina:",
                       "narrativa + dados + análise", ["narrativa + dados + análise", "só opinião", "só fotos"]),
                    ex("quiz", "Ao ler long-form, anote:",
                       "os pontos principais por seção", ["os pontos principais por seção", "cada palavra", "o número de parágrafos"]),
                ],
            ),
            topic(
                "documentacao-profissional",
                "Documentação profissional",
                """
# Documentação profissional

Relatórios, propostas e contratos usam linguagem **formal, clara e
objetiva**.

## Vocabulário formal

```
whereas         considerando que
hereby          por meio deste
pursuant to     em conformidade com
shall           deverá (obrigação)
```

## Exemplos

```
The contract must be signed.     O contrato deve ser assinado.
The report summarizes the results.   O relatório resume os resultados.
```

> 💡 **shall** em contratos = obrigação. Para ler proposta, procure o
# ===== objetivo, o custo e o cronograma =====
""",
                [
                    ex("quiz", "Documentos profissionais são:",
                       "formais, claros e objetivos", ["formais, claros e objetivos", "informais", "cheios de gírias"]),
                    ex("quiz", "Em contrato, 'shall' significa:",
                       "obrigação (deverá)", ["obrigação (deverá)", "opção", "pergunta"]),
                    ex("text", "Complete: 'The report ___ the results.' (resume)",
                       "summarizes"),
                    ex("audio", "Escute e transcreva:",
                       "the contract must be signed", audio_text="The contract must be signed."),
                    ex("quiz", "Para ler uma proposta, procure:",
                       "objetivo, custo e cronograma", ["objetivo, custo e cronograma", "só a capa", "só assinaturas"]),
                    ex("quiz", "Linguagem de documento oficial inclui:",
                       "whereas, hereby, pursuant to", ["whereas, hereby, pursuant to", "gírias", "emojis"]),
                ],
            ),
            topic(
                "identificando-argumentos",
                "Identificando argumentos",
                """
# Identificando argumentos

Mapear um texto é separar **afirmação** (claim), **evidência** e
**conclusão**.

## Os três elementos

```
Claim:       a posição defendida.
Evidence:    os dados/exemplos que apoiam.
Conclusion:  a síntese lógica do argumento.
```

## Exemplo

```
Claim:    Remote work is better.
Evidence: Productivity rose 20% in the survey.
Conclusion: Therefore, remote work benefits companies.
```

> 💡 Ao ler, pergunte: "Qual é a afirmação? O que a apoia? O que o autor
# ===== conclui?" =====
""",
                [
                    ex("quiz", "O que é a 'claim' num texto?",
                       "a afirmação/posição defendida", ["a afirmação/posição defendida", "o exemplo", "a pergunta"]),
                    ex("quiz", "A 'evidence' serve para:",
                       "apoiar a afirmação", ["apoiar a afirmação", "negar tudo", "decorar"]),
                    ex("text", "Complete: 'The author concludes ___...' (que)",
                       "that"),
                    ex("audio", "Escute e transcreva:",
                       "the main claim is difficult to prove", audio_text="The main claim is difficult to prove."),
                    ex("quiz", "Para mapear um argumento:",
                       "separe afirmação, evidência e conclusão", ["separe afirmação, evidência e conclusão", "leia rápido", "ignore"]),
                    ex("quiz", "Uma 'conclusion' é:",
                       "a síntese lógica do argumento", ["a síntese lógica do argumento", "o título", "a introdução"]),
                ],
            ),
            topic(
                "identificando-vies",
                "Identificando viés",
                """
# Identificando viés

**Viés** é uma inclinação que distorce a neutralidade de um texto.

## Sinais de viés

- **Linguagem emocional** demais (disastrous, outrageous).
- **Omissão** de um lado da história.
- Fontes que só apoiam uma visão.

## Como detectar

Pergunte: "Quem está falando? O que foi omitido? De onde vem a
informação?"

> 💘 Um texto neutro apresenta os dois lados; um texto tendencioso
> # ===== escolhe só as palavras e fatos que apoiam uma posição =====
""",
                [
                    ex("quiz", "Viés num texto é:",
                       "uma inclinação que distorce a neutralidade", ["uma inclinação que distorce a neutralidade", "um fato", "uma pergunta"]),
                    ex("quiz", "Linguagem emocional demais pode indicar:",
                       "viés", ["viés", "objetividade", "ciência"]),
                    ex("text", "Complete: 'The article is ___ toward one side.' (parcial)",
                       "biased"),
                    ex("audio", "Escute e transcreva:",
                       "the report is clearly biased", audio_text="The report is clearly biased."),
                    ex("quiz", "Para detectar viés, pergunte:",
                       "o que foi omitido e de onde vem a informação?", ["o que foi omitido e de onde vem a informação?", "quantas páginas tem?", "qual a cor?"]),
                    ex("quiz", "Adjetivos extremos ('disastrous', 'outrageous') sugerem:",
                       "viés/emoção", ["viés/emoção", "neutralidade", "precisão"]),
                ],
            ),
            topic(
                "sentido-implicito-leitura",
                "Sentido implícito (na leitura)",
                """
# Sentido implícito (na leitura)

**Subtexto** é o sentido por trás das palavras — ler as entrelinhas.

## Como detectar

- Note o **tom** e a **ironia**.
- Compare o que é dito com o **contexto**.
- Pergunte: "O que o autor está sugerindo sem dizer?"

## Exemplos

```
"Of course you know everything."   (ironia = crítica)
His words suggest hidden criticism.  (subtexto)
```

> 💡 O implícito aparece em literatura, humor e análise — o leitor C1
# ===== capta o que ficou nas entrelinhas =====
""",
                [
                    ex("quiz", "Subtexto é:",
                       "o sentido por trás das palavras", ["o sentido por trás das palavras", "o título", "o rodapé"]),
                    ex("quiz", "Para captar subtexto, note:",
                       "tom, ironia e contexto", ["tom, ironia e contexto", "só a gramática", "o tamanho"]),
                    ex("text", "Complete: 'The tone ___ irony.' (sugere)",
                       "suggests"),
                    ex("audio", "Escute e transcreva:",
                       "his words suggest hidden criticism", audio_text="His words suggest hidden criticism."),
                    ex("quiz", "Ironia na leitura: o autor diz:",
                       "uma coisa querendo dizer outra", ["uma coisa querendo dizer outra", "só o literal", "nada"]),
                    ex("quiz", "Implícito aparece em:",
                       "literatura, humor e análise", ["literatura, humor e análise", "manuais técnicos", "formulários"]),
                ],
            ),
            topic(
                "entendendo-tom-escrito",
                "Entendendo tom",
                """
# Entendendo tom

O **tom** de um texto é a atitude/emoção que o autor transmite.

## Tons comuns

```
formal      (oficial, impessoal)
informal    (amigável, próximo)
sarcastic   (irônico, oposto do literal)
nostalgic   (saudoso do passado)
urgent      (urgente)
```

## Como identificar

Preste atenção ao **vocabulário** e às **escolhas** do autor — cada palavra
carrega tom.

> 💡 O tom responde: "como o autor se sente sobre o assunto?" — e como ele
# ===== quer que o leitor se sinta =====
""",
                [
                    ex("quiz", "O tom de um texto é:",
                       "a atitude/emoção transmitida", ["a atitude/emoção transmitida", "o tamanho", "a fonte"]),
                    ex("quiz", "Tom sarcástico na escrita usa:",
                       "ironia e exagero", ["ironia e exagero", "só fatos", "formalidade"]),
                    ex("text", "Complete: 'The tone is clearly ___ .' (formal)",
                       "formal"),
                    ex("audio", "Escute e transcreva:",
                       "the tone of the letter is formal", audio_text="The tone of the letter is formal."),
                    ex("quiz", "Tom nostálgico expressa:",
                       "saudade do passado", ["saudade do passado", "raiva", "pressa"]),
                    ex("quiz", "Para identificar o tom, preste atenção:",
                       "ao vocabulário e às escolhas do autor", ["ao vocabulário e às escolhas do autor", "só ao título", "ao número de páginas"]),
                ],
            ),
        ],
    )


# ============================================================
# MODULO 22 - Writing - C1
# ============================================================

def build_modulo_22_writing_c1():
    return module(
        "modulo-22-writing-c1",
        "Módulo 22 — Writing — C1",
        "Escrita avançada: e-mails, relatórios, redações, propostas, artigos, resenhas, escrita técnica/acadêmica/persuasiva/argumentativa, edição, estilo, coesão, precisão e registro.",
        [
            topic(
                "emails-avancados",
                "E-mails avançados",
                """
# E-mails avançados

No C1, o e-mail usa cortesia sofisticada e clareza.

## Frases sofisticadas

```
I trust this finds you well.        Espero que esteja bem.
I would be grateful if...           Ficaria grato se...
Please do not hesitate to...        Não hesite em...
I look forward to hearing from you.  Aguardo seu retorno.
```

> 💡 **I would be grateful if...** é o pedido mais educado do inglês. Use em
> e-mails formais e sensíveis.
""",
                [
                    ex("quiz", "Uma abertura sofisticada:",
                       "I trust this finds you well.", ["I trust this finds you well.", "Yo!", "What's up?"]),
                    ex("quiz", "Para pedir algo com educação máxima:",
                       "I would be grateful if...", ["I would be grateful if...", "Give me...", "Now."]),
                    ex("text", "Complete: 'Please do not ___ to contact me.' (hesitar)",
                       "hesitate"),
                    ex("audio", "Escute e transcreva:",
                       "i would be grateful for your reply", audio_text="I would be grateful for your reply."),
                    ex("quiz", "Para fechar com cortesia:",
                       "I look forward to hearing from you.", ["I look forward to hearing from you.", "Bye.", "See ya."]),
                    ex("quiz", "E-mail avançado mantém:",
                       "tom polido e clareza", ["tom polido e clareza", "gírias", "ambiguidade"]),
                ],
            ),
            topic(
                "relatorios-c1",
                "Relatórios (C1)",
                """
# Relatórios (C1)

O relatório avançado tem **executive summary**, dados, interpretação e
recomendação.

## Estrutura

```
Executive summary:  o essencial para decisão
Findings:           os dados
Implications:       o que os dados significam
Recommendation:     o que fazer
```

## Frases úteis

```
The figures indicate...                Os números indicam...
The implications are clear.            As implicações são claras.
It is strongly recommended that...     Recomenda-se fortemente que...
```

> 💡 Relatório C1 não é só números: é **dados + interpretação +
# ===== recomendação =====
""",
                [
                    ex("quiz", "O 'executive summary' resume:",
                       "o essencial para a decisão", ["o essencial para a decisão", "todo o texto", "só a capa"]),
                    ex("quiz", "Para interpretar dados:",
                       "The figures indicate...", ["The figures indicate...", "I guess...", "Whatever."]),
                    ex("text", "Complete: 'The ___ are clear from the data.' (implicações)",
                       "implications"),
                    ex("audio", "Escute e transcreva:",
                       "the figures indicate a steady growth", audio_text="The figures indicate a steady growth."),
                    ex("quiz", "Relatório C1 apresenta:",
                       "dados + interpretação + recomendação", ["dados + interpretação + recomendação", "só números", "só opinião"]),
                    ex("quiz", "Para recomendar com autoridade:",
                       "It is strongly recommended that...", ["It is strongly recommended that...", "Maybe...", "I think so."]),
                ],
            ),
            topic(
                "essays-c1",
                "Redações (C1)",
                """
# Redações (C1)

O essay C1 tem **tese matizada**, argumentos equilibrados e tom acadêmico.

## Características

- Tese **específica e defensável** (com nuance).
- Mostra os **dois lados** com equilíbrio.
- Usa hedging e conectivos sofisticados.

## Frases úteis

```
This essay examines both sides.       Este texto examina os dois lados.
While it is true that..., it is also...   Embora seja verdade que..., também é...
```

> 💡 Ensaio C1 **reconhece o outro lado** antes de defender o seu — isso
# ===== fortalece o argumento =====
""",
                [
                    ex("quiz", "Uma tese C1 é:",
                       "matizada e específica", ["matizada e específica", "simples e óbvia", "uma pergunta"]),
                    ex("quiz", "Para mostrar equilíbrio:",
                       "While it is true that..., it is also...", ["While it is true that..., it is also...", "Only my view matters.", "No."]),
                    ex("text", "Complete: 'This essay will ___ the arguments.' (examinar)",
                       "examine"),
                    ex("audio", "Escute e transcreva:",
                       "this essay examines both sides of the issue", audio_text="This essay examines both sides of the issue."),
                    ex("quiz", "Ensaio C1 usa:",
                       "hedging e conectivos sofisticados", ["hedging e conectivos sofisticados", "gírias", "primeira pessoa excessiva"]),
                    ex("quiz", "A conclusão C1:",
                       "sintetiza e abre uma reflexão", ["sintetiza e abre uma reflexão", "repete a introdução", "muda de tema"]),
                ],
            ),
            topic(
                "propostas-c1",
                "Propostas (C1)",
                """
# Propostas (C1)

A proposta C1 convence com **viabilidade**, **custo** e **benefícios**.

## Estrutura

```
Objetivo + Plano + Cronograma + Custo + Benefícios + Riscos
```

## Frases úteis

```
This is feasible because...           Isso é viável porque...
We need to assess the risk.           Precisamos avaliar o risco.
The long-term benefits outweigh the costs.   Os benefícios de longo prazo superam os custos.
```

> 💡 Proposta convincente **antecipa as objeções** — mostre que você já
# ===== pensou nos riscos =====
""",
                [
                    ex("quiz", "Uma proposta forte inclui:",
                       "objetivo, plano, custo e benefícios", ["objetivo, plano, custo e benefícios", "só o pedido", "só a capa"]),
                    ex("quiz", "Para justificar a viabilidade:",
                       "This is feasible because...", ["This is feasible because...", "Trust me.", "Whatever."]),
                    ex("text", "Complete: 'We need to assess the ___ .' (risco)",
                       "risk"),
                    ex("audio", "Escute e transcreva:",
                       "this approach is both feasible and cost-effective", audio_text="This approach is both feasible and cost-effective."),
                    ex("quiz", "Para destacar o retorno:",
                       "The long-term benefits outweigh the costs.", ["The long-term benefits outweigh the costs.", "No benefits.", "Too bad."]),
                    ex("quiz", "Proposta convincente antecipa:",
                       "objeções e riscos", ["objeções e riscos", "nada", "só elogios"]),
                ],
            ),
            topic(
                "artigos-escritos",
                "Artigos (escritos)",
                """
# Artigos (escritos)

Um artigo (blog, revista) começa com um **hook** e mantém o leitor engajado.

## Estrutura

```
Hook (prende o leitor) + desenvolvimento + conclusão
```

## Frases úteis

```
This article offers practical tips.     Este artigo oferece dicas práticas.
The headline grabbed my attention.      A manchete chamou minha atenção.
```

> 💡 O **hook** é a primeira frase que prende o leitor: uma pergunta, um dado
# ===== surpreendente ou uma história curta =====
""",
                [
                    ex("quiz", "O 'hook' de um artigo serve para:",
                       "prender o leitor no início", ["prender o leitor no início", "resumir", "terminar"]),
                    ex("quiz", "Artigo usa tom:",
                       "envolvente, adequado ao público", ["envolvente, adequado ao público", "sempre formal", "sempre informal"]),
                    ex("text", "Complete: 'The ___ grabbed my attention.' (manchete/título)",
                       "headline"),
                    ex("audio", "Escute e transcreva:",
                       "this article offers practical tips", audio_text="This article offers practical tips."),
                    ex("quiz", "Boa estrutura de artigo:",
                       "introdução -> pontos -> conclusão", ["introdução -> pontos -> conclusão", "só parágrafos soltos", "só título"]),
                    ex("quiz", "Para engajar, o artigo:",
                       "usa exemplos e histórias", ["usa exemplos e histórias", "só dados brutos", "só jargão"]),
                ],
            ),
            topic(
                "resenhas-c1",
                "Resenhas (C1)",
                """
# Resenhas (C1)

A resenha crítica avalia com **equilíbrio**: pontos fortes e fracos.

## Como criticar com nuance

```
While the pacing is slow, the character depth is strong.
Embora o ritmo seja lento, a profundidade dos personagens é forte.
```

## Palavras de avaliação C1

```
compelling    convincente
flawed        com falhas
nuanced       matizado
worth watching  vale a pena assistir
```

> 💡 Resenha C1 conclui com **recomendação qualificada**: "Despite its
# ===== flaws, the film is worth watching." =====
""",
                [
                    ex("quiz", "Resenha crítica avalia:",
                       "pontos fortes e fracos com equilíbrio", ["pontos fortes e fracos com equilíbrio", "só elogios", "só ataques"]),
                    ex("quiz", "Para criticar com nuance:",
                       "While the pacing is slow, the character depth is strong.", ["While the pacing is slow, the character depth is strong.", "It's boring.", "It's perfect."]),
                    ex("text", "Complete: 'The author's ___ is evident throughout.' (talento)",
                       "skill"),
                    ex("audio", "Escute e transcreva:",
                       "despite its flaws the film is worth watching", audio_text="Despite its flaws, the film is worth watching."),
                    ex("quiz", "Resenha conclui com:",
                       "recomendação qualificada", ["recomendação qualificada", "spoiler", "só nota"]),
                    ex("quiz", "Palavras de avaliação C1:",
                       "compelling, flawed, nuanced", ["compelling, flawed, nuanced", "ok, nice, bad", "uau"]),
                ],
            ),
            topic(
                "escrita-tecnica",
                "Escrita técnica",
                """
# Escrita técnica

Escrita técnica prioriza **clareza** e **precisão** — sem ambiguidade.

## Como escrever

```
First, ... Then, ... Finally, ...   passo a passo claro
This function processes the data.   o que faz, por que e como
```

## Vocabulário

```
process        processar
debug          depurar
configure      configurar
```

> 💡 Boa documentação responde: o que é, por que usar e como usar. Evite
# ===== jargão desnecessário e ambiguidade =====
""",
                [
                    ex("quiz", "Escrita técnica prioriza:",
                       "clareza e precisão", ["clareza e precisão", "beleza literária", "ambiguidade"]),
                    ex("quiz", "Para documentar passo a passo:",
                       "First, ... Then, ... Finally, ...", ["First, ... Then, ... Finally, ...", "Whatever.", "Good luck."]),
                    ex("text", "Complete: 'This function ___ the data.' (processa)",
                       "processes"),
                    ex("audio", "Escute e transcreva:",
                       "follow these steps carefully", audio_text="Follow these steps carefully."),
                    ex("quiz", "Boa documentação:",
                       "diz o que, por que e como", ["diz o que, por que e como", "só o que", "só o como"]),
                    ex("quiz", "Evite em docs:",
                       "jargão desnecessário e ambiguidade", ["jargão desnecessário e ambiguidade", "termos técnicos claros", "exemplos"]),
                ],
            ),
            topic(
                "escrita-academica-c1",
                "Escrita acadêmica (C1)",
                """
# Escrita acadêmica (C1)

A escrita acadêmica avança para **síntese de fontes** e **análise crítica**.

## Vocabulário

```
literature review    revisão da literatura
synthesize           sintetizar
cite                 citar
require              exigir
```

## Frases úteis

```
Several studies agree that...       Vários estudos concordam que...
The findings require further investigation.   Os resultados exigem mais investigação.
```

> 💘 Citação acadêmica usa **autor + ano** (ex.: Smith, 2020). A análise
# ===== crítica questiona suposições e evidência =====
""",
                [
                    ex("quiz", "A 'literature review':",
                       "resume e analisa pesquisas existentes", ["resume e analisa pesquisas existentes", "é a conclusão", "é o título"]),
                    ex("quiz", "Para sintetizar fontes:",
                       "Several studies agree that...", ["Several studies agree that...", "One study says.", "Trust me."]),
                    ex("text", "Complete: 'The findings ___ further investigation.' (exigem)",
                       "require"),
                    ex("audio", "Escute e transcreva:",
                       "several studies agree on this point", audio_text="Several studies agree on this point."),
                    ex("quiz", "Análise crítica questiona:",
                       "suposições e evidência", ["suposições e evidência", "tudo", "nada"]),
                    ex("quiz", "Citação acadêmica usa:",
                       "autor + ano", ["autor + ano", "só o site", "nada"]),
                ],
            ),
            topic(
                "escrita-persuasiva",
                "Escrita persuasiva",
                """
# Escrita persuasiva

Persuasão combina **logos** (lógica), **pathos** (emoção) e **ethos**
(credibilidade), e termina com uma **call to action**.

## Os três apelos

```
Logos   ->  lógica e dados
Pathos  ->  emoção e histórias
Ethos   ->  credibilidade e autoridade
```

## Frases úteis

```
Act now before it is too late.      Aja agora antes que seja tarde.
Join us and make the difference.    Junte-se a nós e faça a diferença.
```

> 💡 A **call to action** é o pedido final: "Join us", "Act now", "Sign
# ===== the petition". Sem ela, a persuasão não fecha =====
""",
                [
                    ex("quiz", "Persuasão usa três apelos:",
                       "lógica, emoção e credibilidade", ["lógica, emoção e credibilidade", "só dinheiro", "só medo"]),
                    ex("quiz", "O que é a 'call to action'?",
                       "o pedido final (faça X)", ["o pedido final (faça X)", "o título", "a assinatura"]),
                    ex("text", "Complete: 'Join us and ___ the difference.' (faça)",
                       "make"),
                    ex("audio", "Escute e transcreva:",
                       "act now before it is too late", audio_text="Act now before it is too late."),
                    ex("quiz", "Ethos é o apelo à:",
                       "credibilidade", ["credibilidade", "emoção", "lógica"]),
                    ex("quiz", "Pathos é o apelo à:",
                       "emoção", ["emoção", "lógica", "credibilidade"]),
                ],
            ),
            topic(
                "escrita-argumentativa",
                "Escrita argumentativa",
                """
# Escrita argumentativa

O texto argumentativo estrutura: **claim** -> **counterclaim** ->
**rebuttal**.

## Estrutura

```
Claim:        sua posição
Counterclaim: o argumento contrário
Rebuttal:     refutação do contrário
```

## Frases úteis

```
Critics argue that...            Os críticos argumentam que...
While critics object, the evidence is strong.   Embora os críticos objetem, a evidência é forte.
```

> 💡 Argumentação madura **reconhece o contra-argumento e o refuta** — não
# ===== finge que ele não existe =====
""",
                [
                    ex("quiz", "O 'counterclaim' é:",
                       "o argumento contrário", ["o argumento contrário", "a prova", "a conclusão"]),
                    ex("quiz", "A 'rebuttal':",
                       "refuta o contra-argumento", ["refuta o contra-argumento", "concorda", "ignora"]),
                    ex("text", "Complete: 'Critics ___ that it is too costly.' (argumentam)",
                       "argue"),
                    ex("audio", "Escute e transcreva:",
                       "while critics object the evidence is strong", audio_text="While critics object, the evidence is strong."),
                    ex("quiz", "Argumentação madura reconhece:",
                       "o contra-argumento e refuta", ["o contra-argumento e refuta", "só o seu lado", "nada"]),
                    ex("quiz", "Estrutura argumentativa:",
                       "claim -> counterclaim -> rebuttal", ["claim -> counterclaim -> rebuttal", "só claim", "só opinião"]),
                ],
            ),
            topic(
                "edicao",
                "Edição",
                """
# Edição

Editar é onde o texto bom vira excelente: **revise**, **enxugue** e
**proofread**.

## As três etapas

```
Revise:       melhore conteúdo e estrutura.
Cut:          remova redundância e palavras desnecessárias.
Proofread:    corrija ortografia e gramática finais.
```

> 💘 **Proofread** é a última passada — sempre antes de enviar ou publicar.
""",
                [
                    ex("quiz", "Revisar (revise) significa:",
                       "melhorar conteúdo e estrutura", ["melhorar conteúdo e estrutura", "só corrigir ortografia", "reescrever do zero"]),
                    ex("quiz", "'Proofread' é:",
                       "corrigir erros finais (ortografia/gramática)", ["corrigir erros finais (ortografia/gramática)", "reestruturar tudo", "publicar"]),
                    ex("text", "Complete: 'Cut the ___ words.' (redundantes)",
                       "redundant"),
                    ex("audio", "Escute e transcreva:",
                       "always proofread before you send", audio_text="Always proofread before you send."),
                    ex("quiz", "Na edição, remova:",
                       "redundância e palavras desnecessárias", ["redundância e palavras desnecessárias", "ideias-chave", "conectivos"]),
                    ex("quiz", "Editar melhora:",
                       "clareza e impacto", ["clareza e impacto", "o comprimento só", "nada"]),
                ],
            ),
            topic(
                "estilo-de-escrita",
                "Estilo",
                """
# Estilo

O estilo de escrita depende de escolhas: voz **ativa** vs **passiva**, e
**concisão**.

## Voz ativa vs passiva

```
Ativa:   The team made the decision.     (direta)
Passiva: The decision was made.          (impessoal)
```

## Quando usar cada uma

- **Ativa**: textos diretos e claros.
- **Passiva**: formal/impessoal (relatórios, academia).

> 💡 Regra geral: prefira a **ativa** para clareza; use a passiva quando o
# ===== agente for irrelevante ou desconhecido =====
""",
                [
                    ex("quiz", "Voz ativa ('The team made the decision'):",
                       "direta e clara", ["direta e clara", "passiva", "confusa"]),
                    ex("quiz", "Voz passiva ('The decision was made'):",
                       "usa-se para impessoalidade", ["usa-se para impessoalidade", "é proibida", "sempre melhor"]),
                    ex("text", "Converta para ativa: 'The report was written by Ana.' -> 'Ana ___ the report.'",
                       "wrote"),
                    ex("audio", "Escute e transcreva:",
                       "the team made the decision quickly", audio_text="The team made the decision quickly."),
                    ex("quiz", "Bom estilo favorece:",
                       "concisão e clareza", ["concisão e clareza", "frases gigantes", "palavras raras só"]),
                    ex("quiz", "Em escrita formal, a passiva:",
                       "é aceitável para impessoalidade", ["é aceitável para impessoalidade", "nunca se usa", "é erro"]),
                ],
            ),
            topic(
                "coesao",
                "Coesão",
                """
# Coesão

**Coesão** conecta frases e parágrafos — o texto flui sem repetição.

## Como criar coesão

- **Referências**: this, it, such (evitam repetir a palavra).
- **Conectivos**: however, furthermore, therefore.
- **Ordem lógica**: uma ideia puxa a próxima.

## Exemplo

```
The results were strong. Therefore, the team celebrated.
```

> 💡 Texto coeso flui naturalmente; texto sem coesão "salta" de ideia em
# ===== ideia =====
""",
                [
                    ex("quiz", "Coesão é:",
                       "conectar frases e parágrafos sem repetição", ["conectar frases e parágrafos sem repetição", "usar palavras difíceis", "encher de pontos"]),
                    ex("quiz", "Para referenciar sem repetir:",
                       "this, it, such", ["this, it, such", "repetir sempre", "nada"]),
                    ex("text", "Complete: 'The results were strong. ___ , the team celebrated.' (portanto)",
                       "therefore"),
                    ex("audio", "Escute e transcreva:",
                       "this approach however has limits", audio_text="This approach, however, has limits."),
                    ex("quiz", "Conectivos como 'furthermore' melhoram:",
                       "a coesão do texto", ["a coesão do texto", "o tamanho só", "nada"]),
                    ex("quiz", "Texto coeso:",
                       "flui naturalmente de uma ideia à outra", ["flui naturalmente de uma ideia à outra", "salta ideias", "repete tudo"]),
                ],
            ),
            topic(
                "precisao-escrita",
                "Precisão (escrita)",
                """
# Precisão (escrita)

Precisão é escolher a **palavra exata** — sem vagueza.

## Substitua o vago

```
a lot of things  ->  several issues
stuff            ->  details / materials
good             ->  effective / strong
```

## Exemplos

```
The report covers several topics.    O relatório cobre vários tópicos.
Please be specific about the numbers.   Por favor, seja específico sobre os números.
```

> 💘 A vagueza ("stuff", "things") enfraquece o texto. No C1, cada ideia
# ===== tem a palavra certa =====
""",
                [
                    ex("quiz", "Precisão evita:",
                       "palavras vagas (thing, stuff)", ["palavras vagas (thing, stuff)", "termos exatos", "exemplos"]),
                    ex("quiz", "Em vez de 'a lot of things', escreva:",
                       "several issues", ["several issues", "a lot of stuff", "many things"]),
                    ex("text", "Complete: 'The report covers ___ topics.' (vários)",
                       "several"),
                    ex("audio", "Escute e transcreva:",
                       "please be specific about the numbers", audio_text="Please be specific about the numbers."),
                    ex("quiz", "Escrita precisa usa:",
                       "o termo exato para cada ideia", ["o termo exato para cada ideia", "palavras genéricas", "só sinônimos"]),
                    ex("quiz", "A vagueza ('stuff', 'things'):",
                       "enfraquece o texto", ["enfraquece o texto", "fortalece", "não importa"]),
                ],
            ),
            topic(
                "registro-escrito",
                "Registro (escrita)",
                """
# Registro (escrita)

O registro deve ser **adequado ao público** e **consistente** do início ao
fim.

## Como escolher

Pergunte: "**Quem lê** e **qual o objetivo**?"

```
E-mail ao chefe  ->  formal
Mensagem ao amigo ->  informal
Texto acadêmico  ->  formal e impessoal
```

> 💡 **Misturar registros** num mesmo texto confunde o leitor. Mantenha um
# ===== registro consistente do início ao fim =====
""",
                [
                    ex("quiz", "O registro adequado depende de:",
                       "público e objetivo", ["público e objetivo", "do humor", "da sorte"]),
                    ex("quiz", "Texto acadêmico usa registro:",
                       "formal e impessoal", ["formal e impessoal", "informal", "com gírias"]),
                    ex("text", "Complete: 'Maintain a ___ tone throughout.' (consistente)",
                       "consistent"),
                    ex("audio", "Escute e transcreva:",
                       "keep the register consistent", audio_text="Keep the register consistent."),
                    ex("quiz", "Misturar registros num texto:",
                       "confunde o leitor", ["confunde o leitor", "é sempre bom", "é proibido"]),
                    ex("quiz", "Para escolher o registro, pergunte:",
                       "quem lê e qual o objetivo?", ["quem lê e qual o objetivo?", "qual a cor?", "quantas páginas?"]),
                ],
            ),
        ],
    )


# ============================================================
# MODULO 23 - Ingles para o Trabalho (aplicado, pos-C1)
# ============================================================

def build_modulo_23_ingles_trabalho():
    return module(
        "modulo-23-ingles-trabalho",
        "Módulo 23 — Inglês para o Trabalho",
        "O inglês do dia a dia profissional: entrevistas, currículo, LinkedIn, reuniões, apresentações, e-mails, Slack/Teams, discussões técnicas, status updates, esclarecimentos, problemas, prazos, feedback e negociação.",
        [
            topic(
                "entrevistas-de-emprego",
                "Entrevistas de emprego",
                """
# Entrevistas de emprego

A entrevista em inglês exige frases prontas para se apresentar e responder.

## Frases úteis

```
Tell me about yourself.              Conte-me sobre você.
My greatest strength is...           Meu maior ponto forte é...
I'm looking for a role where...      Estou procurando um cargo onde...
I believe I'm qualified for this position.   Acredito que sou qualificado para esta vaga.
```

> 💡 Sobre pontos fracos, mostre **consciência e melhoria**: "I used to
# ===== struggle with X, so I worked on Y." =====
""",
                [
                    ex("quiz", "Para falar dos pontos fortes:",
                       "My greatest strength is...", ["My greatest strength is...", "I have none.", "Whatever."]),
                    ex("quiz", "Para falar do que busca:",
                       "I'm looking for a role where...", ["I'm looking for a role where...", "Any job.", "No idea."]),
                    ex("text", "Complete: 'I believe I ___ for this position.' (sou qualificado)",
                       "am qualified"),
                    ex("audio", "Escute e transcreva:",
                       "tell me about yourself", audio_text="Tell me about yourself."),
                    ex("quiz", "Sobre pontos fracos, o ideal é:",
                       "mostrar consciência e melhoria", ["mostrar consciência e melhoria", "negar", "fingir"]),
                    ex("quiz", "Para perguntar sobre a vaga:",
                       "Could you tell me more about the role?", ["Could you tell me more about the role?", "How much?", "Bye."]),
                ],
            ),
            topic(
                "curriculo-cv",
                "Currículo (CV/resume)",
                """
# Currículo (CV/resume)

O currículo em inglês tem seções claras e verbos de ação.

## Seções

```
Work Experience    experiência profissional
Education          formação
Skills             habilidades
```

## Verbos de ação

```
managed    gerenciei
led        liderei
developed  desenvolvi
improved   melhorei
```

> 💡 Para a maioria dos países, use **resume** (1-2 páginas). Comece frases
# ===== com verbos de ação no passado: "Led a team of ten people." =====
""",
                [
                    ex("quiz", "A seção de empregos no CV é:",
                       "Work Experience", ["Work Experience", "Hobbies", "References"]),
                    ex("quiz", "Um bom verbo de ação para o CV:",
                       "managed", ["managed", "did", "was"]),
                    ex("text", "Complete: 'Led a team of ___ people.' (10)",
                       "ten"),
                    ex("audio", "Escute e transcreva:",
                       "i have five years of experience", audio_text="I have five years of experience."),
                    ex("quiz", "CV em inglês para a maioria dos países:",
                       "resume (1-2 páginas)", ["resume (1-2 páginas)", "muito longo", "sem objetivo"]),
                    ex("quiz", "Para listar habilidades:",
                       "Skills: Python, SQL, Communication", ["Skills: Python, SQL, Communication", "I like things", "Stuff"]),
                ],
            ),
            topic(
                "linkedin",
                "LinkedIn",
                """
# LinkedIn

O LinkedIn é o "cartão de visitas" profissional.

## Elementos-chave

```
Headline:    seu título profissional (ex.: Software Engineer)
Summary:     resumo com impacto e objetivos
Open to work: indicador de que busca vaga
```

## Frases úteis

```
I'm open to new opportunities.      Estou aberto a novas oportunidades.
Let's connect on LinkedIn.          Vamos conectar no LinkedIn.
I'd like to connect with you.       Gostaria de me conectar com você.
```

> 💘 Um bom summary mostra **impacto e objetivos** — não é só lista de
# ===== empresas =====
""",
                [
                    ex("quiz", "O headline do LinkedIn é:",
                       "seu título profissional (ex.: Software Engineer)", ["seu título profissional (ex.: Software Engineer)", "sua foto", "seu signo"]),
                    ex("quiz", "Para indicar que busca vaga:",
                       "Open to work", ["Open to work", "Not interested", "Closed"]),
                    ex("text", "Complete: 'I'm ___ to new opportunities.' (aberto)",
                       "open"),
                    ex("audio", "Escute e transcreva:",
                       "let's connect on linkedin", audio_text="Let's connect on LinkedIn."),
                    ex("quiz", "Um bom summary:",
                       "mostra impacto e objetivos", ["mostra impacto e objetivos", "é genérico", "só lista empresas"]),
                    ex("quiz", "Ao pedir conexão:",
                       "I'd like to connect with you.", ["I'd like to connect with you.", "Add me now.", "Hey you."]),
                ],
            ),
            topic(
                "reunioes",
                "Reuniões",
                """
# Reuniões

Frases essenciais para conduzir e participar de reuniões.

## Frases úteis

```
Let's get started.                Vamos começar.
Shall we move on to the next point?   Vamos passar para o próximo ponto?
Let's circle back to that later.   Vamos voltar a isso depois.
What are your thoughts on this?    O que vocês acham disso?
Let's wrap up.                     Vamos encerrar.
```

> 💘 **circle back** = voltar a um assunto depois. **wrap up** = encerrar.
""",
                [
                    ex("quiz", "Para começar a reunião:",
                       "Let's get started.", ["Let's get started.", "We're done.", "Bye."]),
                    ex("quiz", "O que 'circle back to that' significa?",
                       "voltar a um assunto depois", ["voltar a um assunto depois", "desistir", "ignorar"]),
                    ex("text", "Complete: 'Shall we ___ on to the next point?' (passar)",
                       "move"),
                    ex("audio", "Escute e transcreva:",
                       "let's circle back to that later", audio_text="Let's circle back to that later."),
                    ex("quiz", "Para encerrar a reunião:",
                       "Let's wrap up.", ["Let's wrap up.", "Goodbye forever.", "Never."]),
                    ex("quiz", "Para pedir opinião na reunião:",
                       "What are your thoughts on this?", ["What are your thoughts on this?", "Silence.", "Whatever."]),
                ],
            ),
            topic(
                "apresentacoes-trabalho",
                "Apresentações (trabalho)",
                """
# Apresentações (trabalho)

Apresentar no trabalho é guiar, destacar e abrir para perguntas.

## Frases úteis

```
Let me walk you through...        Deixe-me guiá-los por...
The key takeaway is...            A principal ideia é...
The main point here is...         O ponto principal aqui é...
Any questions?                    Alguma pergunta?
```

> 💘 Uma boa apresentação termina com **resumo e próximos passos**, e abre
# ===== espaço para perguntas =====
""",
                [
                    ex("quiz", "Para guiar pela apresentação:",
                       "Let me walk you through...", ["Let me walk you through...", "I'm done.", "Hey."]),
                    ex("quiz", "Para encerrar e abrir perguntas:",
                       "Any questions?", ["Any questions?", "No questions allowed.", "Bye."]),
                    ex("text", "Complete: 'The ___ takeaway is...' (principal)",
                       "key"),
                    ex("audio", "Escute e transcreva:",
                       "let me walk you through the numbers", audio_text="Let me walk you through the numbers."),
                    ex("quiz", "Para destacar o importante:",
                       "The main point here is...", ["The main point here is...", "Blah blah.", "Whatever."]),
                    ex("quiz", "Apresentação boa termina com:",
                       "resumo e próximos passos", ["resumo e próximos passos", "piada sem contexto", "silêncio"]),
                ],
            ),
            topic(
                "emails-trabalho",
                "E-mails (trabalho)",
                """
# E-mails (trabalho)

O e-mail de trabalho é **curto, claro e com próximo passo**.

## Estrutura

```
Assunto: ação específica ("Meeting rescheduled to Friday")
Abrir:   o porquê
Pedido:  a ação (com prazo)
Fechar:  cortesia + próximo passo
```

## Frases úteis

```
Could you please review this by Friday?   Pode revisar isso até sexta?
Please let me know if you have any questions.   Avise se tiver dúvidas.
Would Thursday work for you?              Quinta-feira funciona para você?
```

> 💘 E-mail bom tem **uma ação clara** e **um prazo** — não é um texto vago.
""",
                [
                    ex("quiz", "Um assunto de e-mail eficaz:",
                       "Meeting rescheduled to Friday", ["Meeting rescheduled to Friday", "hi", "????"]),
                    ex("quiz", "Para pedir uma ação:",
                       "Could you please review this by Friday?", ["Could you please review this by Friday?", "Review now.", "Whatever."]),
                    ex("text", "Complete: 'Please let me know if you have any ___ .' (perguntas)",
                       "questions"),
                    ex("audio", "Escute e transcreva:",
                       "please review the attached file", audio_text="Please review the attached file."),
                    ex("quiz", "E-mail de trabalho é:",
                       "curto, claro e com próximo passo", ["curto, claro e com próximo passo", "longo e vago", "sem assunto"]),
                    ex("quiz", "Para agendar:",
                       "Would Thursday work for you?", ["Would Thursday work for you?", "Show up.", "No."]),
                ],
            ),
            topic(
                "slack-teams",
                "Slack/Teams",
                """
# Slack/Teams

O chat do trabalho tem abreviações e frases curtas.

## Abreviações

```
FYI    for your information (para sua informação)
ASAP   as soon as possible (o quanto antes)
TL;DR  too long; didn't read (resumo)
```

## Frases úteis

```
Ping me later.                 Me chama depois.
Keep me in the loop.           Mantenha-me atualizado.
Can you follow up on this?     Pode dar continuidade nisso?
```

> 💘 **in the loop** = informado/ciente. **ping me** = me avise/contate.
""",
                [
                    ex("quiz", "O que 'FYI' significa?",
                       "para sua informação", ["para sua informação", "fim de ano", "faça você mesmo"]),
                    ex("quiz", "O que 'ping me' significa?",
                       "me chame/avise", ["me chame/avise", "me pague", "me ignore"]),
                    ex("text", "Complete: 'Keep me in the ___ .' (atualizado)",
                       "loop"),
                    ex("audio", "Escute e transcreva:",
                       "please keep me in the loop", audio_text="Please keep me in the loop."),
                    ex("quiz", "O que 'ASAP' significa?",
                       "o quanto antes", ["o quanto antes", "depois", "nunca"]),
                    ex("quiz", "Em chat do trabalho, use:",
                       "frases curtas e claras", ["frases curtas e claras", "parágrafos gigantes", "gírias pesadas"]),
                ],
            ),
            topic(
                "discussoes-tecnicas-trabalho",
                "Discussões técnicas (trabalho)",
                """
# Discussões técnicas (trabalho)

Falar de tecnologia no trabalho exige vocabulário de projeto.

## Frases úteis

```
This is a blocker.                 Isso é um impedimento.
The system is composed of...       O sistema é composto por...
I suggest we refactor this.        Sugiro refatorarmos isso.
```

> 💘 **blocker** = impedimento que trava a entrega. Proposta técnica boa
# ===== ouve, propõe e explica o porquê =====
""",
                [
                    ex("quiz", "O que 'blocker' significa no trabalho?",
                       "impedimento", ["impedimento", "bloco de código", "sorriso"]),
                    ex("quiz", "Para propor solução técnica:",
                       "I suggest we refactor this.", ["I suggest we refactor this.", "It's fine.", "Whatever."]),
                    ex("text", "Complete: 'This bug is a ___ for the release.' (impedimento)",
                       "blocker"),
                    ex("audio", "Escute e transcreva:",
                       "this is a blocker for the deadline", audio_text="This is a blocker for the deadline."),
                    ex("quiz", "Para explicar arquitetura:",
                       "The system is composed of three services.", ["The system is composed of three services.", "Trust me.", "No."]),
                    ex("quiz", "Discussão técnica produtiva:",
                       "ouve e propõe", ["ouve e propõe", "só impõe", "só critica"]),
                ],
            ),
            topic(
                "status-updates",
                "Dando status updates",
                """
# Dando status updates

O status update mantém o time alinhado sobre o andamento.

## Frases úteis

```
Let me update you on the project.     Deixe-me atualizá-los sobre o projeto.
I'm on track.                         Estou em dia.
I'm running behind schedule.          Estou atrasado.
We hit an issue with the deployment.  Enfrentamos um problema no deploy.
```

> 💘 Um bom status tem: **o que fez + o que falta + bloqueios**.
""",
                [
                    ex("quiz", "Para dizer que está em dia:",
                       "I'm on track.", ["I'm on track.", "I'm lost.", "Whatever."]),
                    ex("quiz", "Para dizer que está atrasado:",
                       "I'm running behind schedule.", ["I'm running behind schedule.", "I'm perfect.", "No."]),
                    ex("text", "Complete: 'Let me ___ you on the project.' (atualizar)",
                       "update"),
                    ex("audio", "Escute e transcreva:",
                       "we are on track for friday", audio_text="We are on track for Friday."),
                    ex("quiz", "Um status update claro inclui:",
                       "o que fez, o que falta e bloqueios", ["o que fez, o que falta e bloqueios", "só elogios", "só reclamação"]),
                    ex("quiz", "Para reportar um problema:",
                       "We hit an issue with the deployment.", ["We hit an issue with the deployment.", "Nothing works.", "Good luck."]),
                ],
            ),
            topic(
                "pedindo-esclarecimentos",
                "Pedindo esclarecimentos",
                """
# Pedindo esclarecimentos

No trabalho, perguntar é **profissional** — nunca fraqueza.

## Frases úteis

```
Could you clarify what you mean?      Pode esclarecer o que quer dizer?
Could you elaborate on that point?    Pode detalhar esse ponto?
Just to be clear, we meet at 3.       Só para deixar claro, nos vemos às 3.
So, to confirm, the deadline is Friday.   Então, para confirmar, o prazo é sexta.
```

> 💘 Confirmar o entendimento evita retrabalho: "So, to confirm..." é ouro.
""",
                [
                    ex("quiz", "Para pedir esclarecimento:",
                       "Could you clarify what you mean?", ["Could you clarify what you mean?", "I know.", "Bye."]),
                    ex("quiz", "O que 'elaborate' significa?",
                       "explicar em detalhes", ["explicar em detalhes", "encurtar", "terminar"]),
                    ex("text", "Complete: 'Just to be ___, we meet at 3.' (claro)",
                       "clear"),
                    ex("audio", "Escute e transcreva:",
                       "could you elaborate on that point", audio_text="Could you elaborate on that point?"),
                    ex("quiz", "Pedir esclarecimento é:",
                       "sinal de profissionalismo", ["sinal de profissionalismo", "de fraqueza", "proibido"]),
                    ex("quiz", "Para confirmar entendimento:",
                       "So, to confirm, the deadline is Friday.", ["So, to confirm, the deadline is Friday.", "Maybe.", "No."]),
                ],
            ),
            topic(
                "explicando-problemas",
                "Explicando problemas",
                """
# Explicando problemas

Explicar um problema com clareza = **sintoma + causa + solução**.

## Frases úteis

```
We're experiencing an issue with...   Estamos com um problema em...
We have identified the root cause.    Identificamos a causa raiz.
Here's the workaround.                Aqui está a solução paliativa.
This affects all users.               Isso afeta todos os usuários.
```

> 💘 **root cause** = causa raiz. **workaround** = solução paliativa
# ===== enquanto a definitiva não sai =====
""",
                [
                    ex("quiz", "Para reportar um problema:",
                       "We're experiencing an issue with...", ["We're experiencing an issue with...", "All good.", "Whatever."]),
                    ex("quiz", "O que 'workaround' significa?",
                       "solução paliativa", ["solução paliativa", "solução final", "erro"]),
                    ex("text", "Complete: 'The ___ cause is a configuration error.' (causa raiz)",
                       "root"),
                    ex("audio", "Escute e transcreva:",
                       "we have identified the root cause", audio_text="We have identified the root cause."),
                    ex("quiz", "Para descrever o impacto:",
                       "This affects all users.", ["This affects all users.", "It's nothing.", "No."]),
                    ex("quiz", "Explicação de problema clara:",
                       "sintoma + causa + solução", ["sintoma + causa + solução", "só sintoma", "só culpa"]),
                ],
            ),
            topic(
                "discutindo-prazos",
                "Discutindo prazos",
                """
# Discutindo prazos

Falar de prazos exige realismo e proatividade.

## Frases úteis

```
The deadline is Friday.              O prazo é sexta.
Can we push the deadline to Monday?  Podemos adiar o prazo para segunda?
I need an extension.                 Preciso de uma prorrogação.
We can meet the deadline.            Damos conta do prazo.
```

> 💘 **push the deadline** = adiar o prazo. **meet the deadline** = cumprir
# ===== o prazo =====
""",
                [
                    ex("quiz", "Para pedir mais tempo:",
                       "Could we push the deadline to Monday?", ["Could we push the deadline to Monday?", "I can't.", "No."]),
                    ex("quiz", "O que 'extension' (de prazo) significa?",
                       "prorrogação", ["prorrogação", "extensão de arquivo", "erro"]),
                    ex("text", "Complete: 'The ___ is Friday.' (prazo)",
                       "deadline"),
                    ex("audio", "Escute e transcreva:",
                       "can we push the deadline to next week", audio_text="Can we push the deadline to next week?"),
                    ex("quiz", "Para confirmar que dá para cumprir:",
                       "We can meet the deadline.", ["We can meet the deadline.", "Impossible.", "Whatever."]),
                    ex("quiz", "Ao negociar prazo, seja:",
                       "realista e proativo", ["realista e proativo", "vago", "negativo"]),
                ],
            ),
            topic(
                "dando-feedback",
                "Dando feedback",
                """
# Dando feedback

Feedback construtivo é **específico** e **bem-intencionado**.

## Frases úteis

```
I appreciate your work on...          Aprecio seu trabalho em...
Have you considered...?               Você já considerou...?
One thing to improve is...            Uma coisa a melhorar é...
```

> 💘 O "sanduíche" clássico: **positivo + melhoria + positivo**. E seja
# ===== específico — "bom trabalho" genérico não ajuda =====
""",
                [
                    ex("quiz", "Para começar feedback positivo:",
                       "I appreciate your work on...", ["I appreciate your work on...", "It's all wrong.", "No."]),
                    ex("quiz", "Para sugerir melhoria:",
                       "Have you considered...?", ["Have you considered...?", "Fix it now.", "Terrible."]),
                    ex("text", "Complete: 'One thing to ___ is the timing.' (melhorar)",
                       "improve"),
                    ex("audio", "Escute e transcreva:",
                       "i appreciate your effort on this", audio_text="I appreciate your effort on this."),
                    ex("quiz", "Feedback eficaz é:",
                       "específico e construtivo", ["específico e construtivo", "genérico", "só negativo"]),
                    ex("quiz", "O 'sanduíche' de feedback:",
                       "positivo + melhoria + positivo", ["positivo + melhoria + positivo", "só crítica", "só elogio"]),
                ],
            ),
            topic(
                "recebendo-feedback",
                "Recebendo feedback",
                """
# Recebendo feedback

Receber bem o feedback mostra **maturidade profissional**.

## Frases úteis

```
Thank you for the feedback.           Obrigado pelo retorno.
That's a fair point.                  É um ponto justo.
I'll work on that.                    Vou trabalhar nisso.
Could you give me an example?         Pode me dar um exemplo?
```

> 💘 A pior atitude é se defender na hora. Agradeça, considere e peça
# ===== detalhes se precisar =====
""",
                [
                    ex("quiz", "Ao receber feedback, o ideal é:",
                       "agradecer e considerar", ["agradecer e considerar", "se defender", "ignorar"]),
                    ex("quiz", "Para aceitar um ponto:",
                       "That's a fair point.", ["That's a fair point.", "You're wrong.", "No."]),
                    ex("text", "Complete: 'Thank you for the ___ .' (retorno)",
                       "feedback"),
                    ex("audio", "Escute e transcreva:",
                       "that is a fair point i will work on it", audio_text="That is a fair point, I will work on it."),
                    ex("quiz", "Para pedir mais detalhes:",
                       "Could you give me an example?", ["Could you give me an example?", "Whatever.", "Bye."]),
                    ex("quiz", "Receber bem o feedback mostra:",
                       "maturidade profissional", ["maturidade profissional", "fraqueza", "indiferença"]),
                ],
            ),
            topic(
                "negociando-no-trabalho",
                "Negociando (no trabalho)",
                """
# Negociando (no trabalho)

Negociação (salário, termos, prazos) exige respeito e base em dados.

## Frases úteis

```
Could we discuss the compensation?       Podemos discutir a remuneração?
I was expecting a salary of...          Eu esperava um salário de...
Let's find a middle ground.             Vamos encontrar um meio-termo.
Let me consider the offer.              Deixe-me considerar a oferta.
```

> 💘 Negociação profissional é **respeitosa e baseada em dados** — nada de
# ===== agressividade ou pressa =====
""",
                [
                    ex("quiz", "Para falar de salário:",
                       "Could we discuss the compensation?", ["Could we discuss the compensation?", "How much is it? Grito.", "No."]),
                    ex("quiz", "Para propor meio-termo:",
                       "Let's find a middle ground.", ["Let's find a middle ground.", "Take it or leave it.", "Never."]),
                    ex("text", "Complete: 'I was ___ a salary of...' (esperando)",
                       "expecting"),
                    ex("audio", "Escute e transcreva:",
                       "could we discuss the compensation package", audio_text="Could we discuss the compensation package?"),
                    ex("quiz", "Para comprar tempo ao decidir:",
                       "Let me consider the offer.", ["Let me consider the offer.", "Yes, anything.", "No."]),
                    ex("quiz", "Negociação profissional é:",
                       "respeitosa e baseada em dados", ["respeitosa e baseada em dados", "agressiva", "apressada"]),
                ],
            ),
        ],
    )


# ============================================================
# MODULO 24 - Ingles para Tecnologia (aplicado, pos-C1)
# ============================================================

def build_modulo_24_ingles_tecnologia():
    return module(
        "modulo-24-ingles-tecnologia",
        "Módulo 24 — Inglês para Tecnologia",
        "O inglês do mundo tech: programação, desenvolvimento de software, documentação, GitHub, Stack Overflow, artigos técnicos, code review, pull requests, arquitetura, system design, debugging, IA, cloud e DevOps.",
        [
            topic(
                "vocabulario-de-programacao",
                "Vocabulário de programação",
                """
# Vocabulário de programação

| Inglês | Português |
|---|---|
| code | código |
| bug | erro (em código) |
| variable | variável |
| function | função |
| loop | laço |
| to run | executar |
| library | biblioteca |
| framework | framework |
| API | API |

## Exemplos

```
The code runs on the server.      O código roda no servidor.
This function processes the data.  Esta função processa os dados.
```

> 💘 **bug** = erro. **run** = executar. **library/framework** = código
# ===== pronto para reutilizar =====
""",
                [
                    ex("quiz", "Como se diz 'variável'?",
                       "variable", ["variable", "function", "loop"]),
                    ex("quiz", "Como se diz 'erro' (em código)?",
                       "bug", ["bug", "feature", "deploy"]),
                    ex("text", "Complete: 'This function ___ the data.' (processa)",
                       "processes"),
                    ex("audio", "Escute e transcreva:",
                       "the code runs on the server", audio_text="The code runs on the server."),
                    ex("quiz", "Como se diz 'executar' (código)?",
                       "run", ["run", "write", "delete"]),
                    ex("quiz", "Como se diz 'biblioteca' (de código)?",
                       "library", ["library", "function", "bug"]),
                ],
            ),
            topic(
                "vocabulario-de-software",
                "Vocabulário de desenvolvimento de software",
                """
# Vocabulário de desenvolvimento de software

| Inglês | Português |
|---|---|
| requirements | requisitos |
| architecture | arquitetura |
| frontend | frontend (parte visual) |
| backend | backend (dados/lógica) |
| database | banco de dados |
| feature | funcionalidade |
| release | versão publicada |
| deployment | implantação/deploy |

## Exemplos

```
This is a new feature.          Esta é uma nova funcionalidade.
We release a new version monthly.   Publicamos uma nova versão mensalmente.
```

> 💘 **feature** = funcionalidade nova. **deployment** = colocar o software
# ===== no ar =====
""",
                [
                    ex("quiz", "Como se diz 'requisitos'?",
                       "requirements", ["requirements", "release", "bug"]),
                    ex("quiz", "Como se diz 'banco de dados'?",
                       "database", ["database", "frontend", "version"]),
                    ex("text", "Complete: 'This is a new ___ .' (funcionalidade)",
                       "feature"),
                    ex("audio", "Escute e transcreva:",
                       "we release a new version monthly", audio_text="We release a new version monthly."),
                    ex("quiz", "Como se diz 'implantação' (de software)?",
                       "deployment", ["deployment", "debugging", "design"]),
                    ex("quiz", "Frontend vs backend: o backend lida com:",
                       "dados e lógica", ["dados e lógica", "aparência", "fotos"]),
                ],
            ),
            topic(
                "lendo-documentacao",
                "Lendo documentação",
                """
# Lendo documentação

A documentação (README, docs) tem seções padrão.

## Seções comuns

```
Installation    instalação
Usage           como usar
API reference   referência da API
Examples        exemplos
```

## Exemplos

```
Check the documentation for details.   Consulte a documentação para detalhes.
See the API reference for all methods.  Veja a referência da API para todos os métodos.
```

> 💘 Boa documentação inclui **exemplos e casos de uso** — não só o logo.
""",
                [
                    ex("quiz", "A seção de instalação é:",
                       "Installation", ["Installation", "License", "Credits"]),
                    ex("quiz", "O que 'Usage' explica?",
                       "como usar", ["como usar", "como instalar", "a licença"]),
                    ex("text", "Complete: 'See the ___ section for examples.' (referência)",
                       "reference"),
                    ex("audio", "Escute e transcreva:",
                       "check the documentation for details", audio_text="Check the documentation for details."),
                    ex("quiz", "Boa documentação inclui:",
                       "exemplos e casos de uso", ["exemplos e casos de uso", "só o logo", "só o autor"]),
                    ex("quiz", "Em docs, 'e.g.' significa:",
                       "por exemplo", ["por exemplo", "isto é", "fim"]),
                ],
            ),
            topic(
                "github",
                "GitHub",
                """
# GitHub

O vocabulário de GitHub e Git.

| Inglês | Português |
|---|---|
| repository | repositório |
| branch | ramo |
| to clone | copiar (repo) |
| to push | enviar (commits) |
| to pull | puxar (do remoto) |
| issue | tarefa/bug registrado |
| pull request | pedido de revisão |

## Comandos

```
git clone        copia o repositório
git push         envia commits
git pull         baixa mudanças
```

> 💘 **issue** registra tarefa ou bug. **PR** propõe mudança para revisão.
""",
                [
                    ex("quiz", "Como se diz 'repositório'?",
                       "repository", ["repository", "release", "error"]),
                    ex("quiz", "Para copiar um repo localmente:",
                       "git clone", ["git clone", "git push", "git merge"]),
                    ex("text", "Complete: 'Create a ___ for this feature.' (ramo)",
                       "branch"),
                    ex("audio", "Escute e transcreva:",
                       "please review my pull request", audio_text="Please review my pull request."),
                    ex("quiz", "O que uma 'issue' registra?",
                       "tarefa ou bug", ["tarefa ou bug", "o deploy", "a versão"]),
                    ex("quiz", "Para enviar commits ao remoto:",
                       "git push", ["git push", "git pull", "git status"]),
                ],
            ),
            topic(
                "stack-overflow",
                "Stack Overflow",
                """
# Stack Overflow

Para perguntar bem no Stack Overflow, descreva o problema com código.

## Como perguntar

```
I'm getting a SyntaxError.        Estou com um SyntaxError.
Here's my code.                   Aqui está meu código.
Has anyone solved this problem?   Alguém já resolveu esse problema?
```

## A resposta boa

```
Accepted answer    resposta marcada como correta
```

> 💘 Boa pergunta inclui **código + erro**. Antes de perguntar, procure se
# ===== alguém já perguntou =====
""",
                [
                    ex("quiz", "Para descrever um erro:",
                       "I'm getting a SyntaxError.", ["I'm getting a SyntaxError.", "It doesn't work.", "Help."]),
                    ex("quiz", "Boa pergunta inclui:",
                       "código e o erro", ["código e o erro", "só o erro", "só reclamação"]),
                    ex("text", "Complete: 'Has anyone ___ this problem?' (resolveu)",
                       "solved"),
                    ex("audio", "Escute e transcreva:",
                       "can anyone help me debug this", audio_text="Can anyone help me debug this?"),
                    ex("quiz", "A resposta marcada como correta é:",
                       "the accepted answer", ["the accepted answer", "a mais longa", "a primeira"]),
                    ex("quiz", "Antes de perguntar, procure:",
                       "se alguém já perguntou", ["se alguém já perguntou", "desista", "pergunte tudo"]),
                ],
            ),
            topic(
                "artigos-tecnicos",
                "Artigos técnicos",
                """
# Artigos técnicos

Artigos técnicos (blogs, tutoriais) seguem: **problema -> solução ->
conclusão**.

## Frases úteis

```
This tutorial explains step by step.   Este tutorial explica passo a passo.
This article explains how to scale.    Este artigo explica como escalar.
```

> 💘 Para julgar um artigo, veja se **resolve o problema** — e teste o que
# ===== aprendeu na prática =====
""",
                [
                    ex("quiz", "Artigo técnico geralmente segue:",
                       "problema -> solução -> conclusão", ["problema -> solução -> conclusão", "só piadas", "só código"]),
                    ex("quiz", "Para julgar se o artigo é bom:",
                       "veja se resolve o problema", ["veja se resolve o problema", "só o título", "o número de likes"]),
                    ex("text", "Complete: 'This tutorial ___ step by step.' (explica)",
                       "explains"),
                    ex("audio", "Escute e transcreva:",
                       "this article explains how to scale", audio_text="This article explains how to scale."),
                    ex("quiz", "Ao ler, teste o que aprendeu:",
                       "na prática", ["na prática", "só decorando", "nunca"]),
                    ex("quiz", "Bons artigos técnicos têm:",
                       "exemplos de código", ["exemplos de código", "só texto", "só fotos"]),
                ],
            ),
            topic(
                "code-review",
                "Code review",
                """
# Code review

Revisar código exige vocabulário gentil e preciso.

## Frases úteis

```
LGTM                          looks good to me (está bom pra mim)
Minor: could you fix the spacing?   Menor: pode corrigir o espaçamento?
This looks good to me.        Isso parece bom para mim.
```

> 💘 **LGTM** = looks good to me — aprovação comum em PRs. Review gentil
# ===== **sugere**, não impõe =====
""",
                [
                    ex("quiz", "O que 'LGTM' significa?",
                       "looks good to me", ["looks good to me", "let go to market", "long good time"]),
                    ex("quiz", "Para apontar um pequeno ajuste:",
                       "Minor: could you fix the spacing?", ["Minor: could you fix the spacing?", "Rewrite everything.", "Terrible."]),
                    ex("text", "Complete: 'This looks ___ to me.' (bom)",
                       "good"),
                    ex("audio", "Escute e transcreva:",
                       "could you fix this small issue", audio_text="Could you fix this small issue?"),
                    ex("quiz", "Code review gentil:",
                       "sugere, não impõe", ["sugere, não impõe", "manda reescrever", "critica a pessoa"]),
                    ex("quiz", "O que é 'nitpick'?",
                       "apontar detalhes mínimos", ["apontar detalhes mínimos", "aprovar tudo", "ignorar"]),
                ],
            ),
            topic(
                "pull-requests",
                "Pull requests",
                """
# Pull requests

A linguagem do PR: abrir, revisar, pedir mudanças, aprovar e mergear.

## Frases úteis

```
Please review my changes.        Por favor, revise minhas mudanças.
I've pushed the changes.         Enviei (push) as mudanças.
Requested changes                mudanças solicitadas
Looks good, merging now.         Parece bom, mergeando agora.
```

> 💘 Um PR descritivo explica **o que mudou e por quê** — não só o título.
""",
                [
                    ex("quiz", "Ao abrir um PR:",
                       "Please review my changes.", ["Please review my changes.", "It's done, bye.", "No."]),
                    ex("quiz", "O que 'requested changes' significa?",
                       "mudanças solicitadas", ["mudanças solicitadas", "aprovação", "rejeição total"]),
                    ex("text", "Complete: 'I've ___ the changes.' (enviado/push)",
                       "pushed"),
                    ex("audio", "Escute e transcreva:",
                       "i pushed the changes to the branch", audio_text="I pushed the changes to the branch."),
                    ex("quiz", "Ao aprovar e juntar:",
                       "Looks good, merging now.", ["Looks good, merging now.", "Never.", "Whatever."]),
                    ex("quiz", "PR descritivo explica:",
                       "o que mudou e por quê", ["o que mudou e por quê", "só o título", "nada"]),
                ],
            ),
            topic(
                "discussoes-de-arquitetura",
                "Discussões de arquitetura",
                """
# Discussões de arquitetura

Falar de arquitetura é discutir **escolhas e trade-offs**.

## Frases úteis

```
We should consider using...       Devemos considerar usar...
This scales well with users.      Isso escala bem com usuários.
The trade-off of this approach is complexity.   A desvantagem desta abordagem é a complexidade.
```

> 💘 **scales well** = aguenta crescimento. **trade-off** = desvantagem
# ===== aceita em troca de uma vantagem =====
""",
                [
                    ex("quiz", "Para propor arquitetura:",
                       "We should consider using...", ["We should consider using...", "Trust me.", "No."]),
                    ex("quiz", "O que 'scales well' significa?",
                       "escala bem (aguenta crescimento)", ["escala bem (aguenta crescimento)", "fica pequeno", "quebra"]),
                    ex("text", "Complete: 'The ___ of this approach is complexity.' (desvantagem)",
                       "trade-off"),
                    ex("audio", "Escute e transcreva:",
                       "this architecture scales well with users", audio_text="This architecture scales well with users."),
                    ex("quiz", "Discussão de arquitetura pesa:",
                       "prós e contras", ["prós e contras", "só a opinião do chefe", "o tamanho do time"]),
                    ex("quiz", "O que é 'microservices'?",
                       "serviços pequenos e independentes", ["serviços pequenos e independentes", "um servidor gigante", "um bug"]),
                ],
            ),
            topic(
                "system-design",
                "Vocabulário de system design",
                """
# Vocabulário de system design

| Inglês | Português |
|---|---|
| latency | latência (tempo de resposta) |
| throughput | vazão (quanto processa) |
| cache | cache (dados rápidos) |
| load balancer | balanceador de carga |
| availability | disponibilidade |
| queue | fila |

## Exemplos

```
We added a cache to reduce latency.   Adicionamos um cache para reduzir a latência.
We need a load balancer.              Precisamos de um balanceador de carga.
```

> 💘 **latency** = tempo de resposta; **throughput** = quanto o sistema
# ===== processa por unidade de tempo =====
""",
                [
                    ex("quiz", "O que 'latency' significa?",
                       "latência (tempo de resposta)", ["latência (tempo de resposta)", "custo", "memória"]),
                    ex("quiz", "O que 'throughput' significa?",
                       "vazão (quanto processa)", ["vazão (quanto processa)", "atraso", "erro"]),
                    ex("text", "Complete: 'We need a load ___ .' (balanceador)",
                       "balancer"),
                    ex("audio", "Escute e transcreva:",
                       "we added a cache to reduce latency", audio_text="We added a cache to reduce latency."),
                    ex("quiz", "O que 'cache' faz?",
                       "guarda dados para acesso rápido", ["guarda dados para acesso rápido", "apaga tudo", "roda o servidor"]),
                    ex("quiz", "O que 'availability' significa?",
                       "disponibilidade (sempre no ar)", ["disponibilidade (sempre no ar)", "velocidade", "tamanho"]),
                ],
            ),
            topic(
                "vocabulario-de-debugging",
                "Vocabulário de debugging",
                """
# Vocabulário de debugging

| Inglês | Português |
|---|---|
| traceback | rastreamento do erro |
| to reproduce | reproduzir |
| breakpoint | ponto de parada |
| stack trace | trilha da pilha |
| log | registro |

## Exemplos

```
Can you reproduce the error?      Você consegue reproduzir o erro?
Let's check the error log.        Vamos ver o registro de erros.
```

> 💘 O primeiro passo do debug: **ler o erro e reproduzir**. Um
# ===== breakpoint pausa o código para inspeção =====
""",
                [
                    ex("quiz", "O que 'traceback' mostra?",
                       "o caminho do erro", ["o caminho do erro", "o sucesso", "a versão"]),
                    ex("quiz", "Para 'reproduzir' um bug:",
                       "Can you reproduce the issue?", ["Can you reproduce the issue?", "It's random.", "No."]),
                    ex("text", "Complete: 'Let's check the error ___ .' (registro/log)",
                       "log"),
                    ex("audio", "Escute e transcreva:",
                       "can you reproduce the error", audio_text="Can you reproduce the error?"),
                    ex("quiz", "Um 'breakpoint' pausa:",
                       "o código para inspeção", ["o código para inspeção", "o deploy", "o git"]),
                    ex("quiz", "Ao depurar, o primeiro passo é:",
                       "ler o erro e reproduzir", ["ler o erro e reproduzir", "reescrever tudo", "culpar alguém"]),
                ],
            ),
            topic(
                "vocabulario-de-ia",
                "Vocabulário de IA",
                """
# Vocabulário de IA

| Inglês | Português |
|---|---|
| model | modelo |
| training | treinamento |
| dataset | conjunto de dados |
| inference | inferência (usar o modelo) |
| prompt | instrução ao modelo |
| token | pedaço de texto |
| neural network | rede neural |

## Exemplos

```
We trained the model on new data.   Treinamos o modelo com dados novos.
The model was trained on a large dataset.   O modelo foi treinado em um grande conjunto de dados.
```

> 💘 **training** = treinar com dados; **inference** = usar o modelo
# ===== treinado para prever =====
""",
                [
                    ex("quiz", "O que é 'training' (em ML)?",
                       "treinar o modelo com dados", ["treinar o modelo com dados", "executar", "apagar"]),
                    ex("quiz", "O que 'inference' significa?",
                       "usar o modelo treinado para prever", ["usar o modelo treinado para prever", "treinar", "coletar dados"]),
                    ex("text", "Complete: 'The model was trained on a large ___ .' (conjunto de dados)",
                       "dataset"),
                    ex("audio", "Escute e transcreva:",
                       "we trained the model on new data", audio_text="We trained the model on new data."),
                    ex("quiz", "Em LLMs, um 'token' é:",
                       "um pedaço de texto", ["um pedaço de texto", "um erro", "uma função"]),
                    ex("quiz", "O que 'prompt' significa em IA?",
                       "a instrução dada ao modelo", ["a instrução dada ao modelo", "o resultado", "o treino"]),
                ],
            ),
            topic(
                "vocabulario-de-cloud",
                "Vocabulário de cloud",
                """
# Vocabulário de cloud

| Inglês | Português |
|---|---|
| cloud | nuvem (servidores remotos) |
| instance | máquina virtual |
| provider | provedor (AWS, Azure, GCP) |
| scaling | escalar (recursos sob demanda) |
| serverless | sem gerenciar servidores |
| region | região |

## Exemplos

```
We deployed to the cloud.         Publicamos na nuvem.
We host the app on a cloud provider.   Hospedamos o app em um provedor de nuvem.
```

> 💘 **scaling** ajusta recursos sob demanda. **serverless** = você não
# ===== gerencia servidores =====
""",
                [
                    ex("quiz", "O que 'cloud' significa em TI?",
                       "computação na nuvem (servidores remotos)", ["computação na nuvem (servidores remotos)", "chuva", "wifi"]),
                    ex("quiz", "O que 'instance' é na nuvem?",
                       "uma máquina virtual", ["uma máquina virtual", "um arquivo", "um erro"]),
                    ex("text", "Complete: 'We host the app on a cloud ___ .' (provedor)",
                       "provider"),
                    ex("audio", "Escute e transcreva:",
                       "we deployed to the cloud", audio_text="We deployed to the cloud."),
                    ex("quiz", "O que 'serverless' significa?",
                       "sem gerenciar servidores", ["sem gerenciar servidores", "sem internet", "sem dados"]),
                    ex("quiz", "O que 'scaling' (na nuvem) faz?",
                       "aumenta/diminui recursos sob demanda", ["aumenta/diminui recursos sob demanda", "apaga", "trava"]),
                ],
            ),
            topic(
                "vocabulario-de-devops",
                "Vocabulário de DevOps",
                """
# Vocabulário de DevOps

| Inglês | Português |
|---|---|
| CI/CD | integração/entrega contínuas |
| pipeline | pipeline (fluxo automatizado) |
| container | container (ambiente isolado) |
| deployment | deploy |
| monitoring | monitoramento |
| rollback | voltar versão anterior |
| alert | alerta |

## Exemplos

```
The deployment pipeline is automated.   O pipeline de deploy é automatizado.
The pipeline runs on every commit.      O pipeline roda a cada commit.
```

> 💘 **CI/CD** automatiza build, teste e deploy. **rollback** volta para a
# ===== versão anterior em caso de problema =====
""",
                [
                    ex("quiz", "O que 'CI/CD' envolve?",
                       "integração e entrega contínuas", ["integração e entrega contínuas", "design", "documentação"]),
                    ex("quiz", "O que é um 'container' (Docker)?",
                       "ambiente isolado para rodar o app", ["ambiente isolado para rodar o app", "um arquivo", "um bug"]),
                    ex("text", "Complete: 'The pipeline runs on every ___ .' (commit)",
                       "commit"),
                    ex("audio", "Escute e transcreva:",
                       "the deployment pipeline is automated", audio_text="The deployment pipeline is automated."),
                    ex("quiz", "O que 'rollback' faz?",
                       "volta para a versão anterior", ["volta para a versão anterior", "avança", "reinicia o git"]),
                    ex("quiz", "O que 'monitoring' faz?",
                       "observa a saúde do sistema", ["observa a saúde do sistema", "instala pacotes", "roda testes"]),
                ],
            ),
        ],
    )


# ============================================================
# MODULO 25 - Treino de Fluencia (aplicado, pos-C1)
# ============================================================

def build_modulo_25_treino_fluencia():
    return module(
        "modulo-25-treino-fluencia",
        "Módulo 25 — Treino de Fluência",
        "Falar sem travar: pensar em inglês, evitar a tradução mental, parafrasear, circumlocução, espontaneidade, recall de vocabulário, frases automáticas, velocidade, pronúncia, entonação, escuta rápida e alternância de contexto.",
        [
            topic(
                "pensando-em-ingles",
                "Pensando em inglês",
                """
# Pensando em inglês

A fluência real começa quando você **pensa direto em inglês** — sem traduzir
mentalmente.

## Como praticar

- **Rotule** objetos ao redor em inglês (tabela, cadeira, janela).
- **Narre** o que faz: "I'm opening the door", "I need my keys".
- Forme pensamentos simples direto no idioma.

> 💡 Pensar em inglês deixa a fala mais **rápida e natural** — porque você
# ===== pula a etapa da tradução =====
""",
                [
                    ex("quiz", "Pensar em inglês significa:",
                       "formar os pensamentos direto em inglês", ["formar os pensamentos direto em inglês", "traduzir mentalmente", "não pensar"]),
                    ex("quiz", "Um exercício simples para começar:",
                       "rotular objetos ao redor em inglês", ["rotular objetos ao redor em inglês", "traduzir tudo", "dormir"]),
                    ex("text", "Complete: 'Try to think in ___ .' (inglês)",
                       "english"),
                    ex("audio", "Escute e transcreva:",
                       "i need to think in english", audio_text="I need to think in English."),
                    ex("quiz", "Pensar em inglês deixa a fala:",
                       "mais rápida e natural", ["mais rápida e natural", "mais lenta", "impossível"]),
                    ex("quiz", "Para praticar, narre:",
                       "o que você faz, em voz baixa", ["o que você faz, em voz baixa", "nada", "só no papel"]),
                ],
            ),
            topic(
                "evitando-traducao-mental",
                "Evitando tradução mental",
                """
# Evitando tradução mental

A tradução palavra a palavra **atrasa** e gera erros. Aprenda em **blocos**.

## O que fazer

- Aprenda **chunks** (blocos prontos): "It depends", "What I meant was".
- Associe a palavra à **imagem/ideia**, não ao português.
- Não abra o dicionário a cada palavra — use o contexto.

> 💘 Blocos prontos como "It depends" são aprendidos **como um todo** — não
# ===== traduzidos palavra por palavra =====
""",
                [
                    ex("quiz", "A tradução mental palavra a palavra:",
                       "atrasa e gera erros", ["atrasa e gera erros", "ajuda sempre", "não existe"]),
                    ex("quiz", "Em vez de traduzir, aprenda:",
                       "blocos prontos (chunks)", ["blocos prontos (chunks)", "gramática isolada", "só palavras soltas"]),
                    ex("text", "Complete: 'Avoid translating ___ by word.' (palavra)",
                       "word"),
                    ex("audio", "Escute e transcreva:",
                       "don't translate word by word", audio_text="Don't translate word by word."),
                    ex("quiz", "Blocos prontos como 'It depends' são:",
                       "aprendidos como um todo", ["aprendidos como um todo", "traduzidos", "proibidos"]),
                    ex("quiz", "O que ajuda a evitar a tradução:",
                       "associação direta palavra -> ideia", ["associação direta palavra -> ideia", "dicionário em cada palavra", "tradução sempre"]),
                ],
            ),
            topic(
                "parafrase-fluencia",
                "Paráfrase",
                """
# Paráfrase

**Parafrasear** é dizer a mesma ideia com outras palavras — essencial quando
você trava numa palavra.

## Exemplos

```
I'm tired.   ->   I'm exhausted.
She is very happy.   ->   She is delighted.
```

## Quando usar

- Você esqueceu a palavra exata.
- O ouvinte não entendeu.
- Você quer evitar repetição.

> 💘 Paráfrase + sinônimos = o socorro da fluência quando falta a palavra.
""",
                [
                    ex("quiz", "Parafrasear é:",
                       "dizer a mesma ideia com outras palavras", ["dizer a mesma ideia com outras palavras", "copiar", "traduzir"]),
                    ex("quiz", "Quando trava numa palavra, você:",
                       "parafraseia com o que sabe", ["parafraseia com o que sabe", "desiste", "muda de idioma"]),
                    ex("text", "Complete com sinônimo: 'I'm tired' -> 'I'm ___ .' (cansadíssimo)",
                       "exhausted"),
                    ex("audio", "Escute e transcreva:",
                       "can you say it in other words", audio_text="Can you say it in other words?"),
                    ex("quiz", "Paráfrase é essencial para:",
                       "fluência e circumlocução", ["fluência e circumlocução", "decorar", "nada"]),
                    ex("quiz", "Para parafrasear, use:",
                       "sinônimos e reestruturação", ["sinônimos e reestruturação", "só a palavra exata", "o dicionário em voz alta"]),
                ],
            ),
            topic(
                "circunlocucao",
                "Circunlocução",
                """
# Circunlocução

**Circunlocução** é descrever uma palavra que você não lembra — mantém a
conversa fluindo.

## Como descrever sem a palavra

```
"It's the thing you use to keep food cold."   (refrigerador)
"It's the tool you use to cut paper."         (tesoura)
```

## Por que importa

Em vez de travar ("I don't know the word"), você **descreve** — e o nativo
te ajuda ou você se faz entender.

> 💘 Circunlocução = falar ao redor da palavra. Treine descrevendo objetos
# ===== do dia a dia sem dizer o nome =====
""",
                [
                    ex("quiz", "Circunlocução é:",
                       "descrever a palavra que você não lembra", ["descrever a palavra que você não lembra", "desistir", "traduzir"]),
                    ex("quiz", "Para descrever 'refrigerador' sem a palavra:",
                       "The thing you use to keep food cold.", ["The thing you use to keep food cold.", "I don't know.", "Bye."]),
                    ex("text", "Complete: 'It's the ___ you use to cut paper.' (coisa)",
                       "thing"),
                    ex("audio", "Escute e transcreva:",
                       "it's the thing you use to open a bottle", audio_text="It's the thing you use to open a bottle."),
                    ex("quiz", "Circunlocução mantém a conversa:",
                       "fluindo sem travar", ["fluindo sem travar", "parada", "em português"]),
                    ex("quiz", "Para treinar, descreva:",
                       "objetos do dia a dia sem o nome", ["objetos do dia a dia sem o nome", "só palavras fáceis", "nada"]),
                ],
            ),
            topic(
                "espontaneidade-fluencia",
                "Falando espontaneamente",
                """
# Falando espontaneamente

Falar sem ensaio exige **frases-ponte** para ganhar tempo e responder.

## Frases-ponte

```
Let me think for a moment.         Deixe-me pensar um momento.
That's a great question.           É uma ótima pergunta.
Off the top of my head...          De cabeça, sem pensar muito...
```

## Ao não saber responder

- **Reformule** e tente ("Let me put it this way...").
- Não fique em silêncio — o nativo também hesita.

> 💘 Espontaneidade melhora com **prática de resposta rápida** — não com
# ===== silêncio =====
""",
                [
                    ex("quiz", "Para reagir sem ensaio:",
                       "use frases-ponte e responda", ["use frases-ponte e responda", "congele", "desista"]),
                    ex("quiz", "Uma frase-ponte é:",
                       "Let me think for a moment.", ["Let me think for a moment.", "I don't know.", "Bye."]),
                    ex("text", "Complete: 'That's a ___ question.' (ótima)",
                       "great"),
                    ex("audio", "Escute e transcreva:",
                       "off the top of my head i'd say yes", audio_text="Off the top of my head, I'd say yes."),
                    ex("quiz", "Espontaneidade melhora com:",
                       "prática de resposta rápida", ["prática de resposta rápida", "silêncio", "decorar discursos"]),
                    ex("quiz", "Ao não saber responder, o ideal é:",
                       "reformular e tentar", ["reformular e tentar", "ficar calado", "fugir"]),
                ],
            ),
            topic(
                "recall-de-vocabulario",
                "Recall de vocabulário",
                """
# Recall de vocabulário

**Recall ativo** é lembrar a palavra **sem ajuda** — muito mais forte que só
reconhecer.

## Como treinar

- **Teste-se**: veja a tradução e diga a palavra em inglês.
- Use **repetição espaçada** (revisar em intervalos).
- Antes de conferir, tente **recordar**.

> 💘 Reler a lista não é recall — **testar-se** é. Quem se testa lembra
# ===== muito mais =====
""",
                [
                    ex("quiz", "Recall ativo é:",
                       "lembrar a palavra sem ajuda", ["lembrar a palavra sem ajuda", "reconhecer só", "decorar"]),
                    ex("quiz", "A repetição espaçada melhora:",
                       "a memória de longo prazo", ["a memória de longo prazo", "só o curto prazo", "nada"]),
                    ex("text", "Complete: 'Test yourself to ___ words.' (recordar)",
                       "recall"),
                    ex("audio", "Escute e transcreva:",
                       "recall the word before you check", audio_text="Recall the word before you check."),
                    ex("quiz", "Para fortalecer o recall:",
                       "testar-se ativamente", ["testar-se ativamente", "só reler", "dormir"]),
                    ex("quiz", "Em vez de só ler a lista, você deve:",
                       "se testar", ["se testar", "fechar os olhos", "pular"]),
                ],
            ),
            topic(
                "formacao-automatica-de-frases",
                "Formação automática de frases",
                """
# Formação automática de frases

Fluência é montar frases **sem pensar muito** — automatizando estruturas.

## Templates para automatizar

```
I'm planning to ___.          Estou planejando...
I'm looking forward to ___.   Estou ansioso para...
I'm used to ___.              Estou acostumado a...
```

## Como praticar

Repita os templates em voz alta com vocabulário diferente até saírem
automáticos.

> 💘 Com o tempo, as frases saem **sozinhas** — sem montar do zero cada vez.
""",
                [
                    ex("quiz", "Formação automática significa:",
                       "montar frases sem pensar muito", ["montar frases sem pensar muito", "traduzir sempre", "hesitar"]),
                    ex("quiz", "Templates (ex.: 'I'm planning to ___') ajudam a:",
                       "automatizar estruturas", ["automatizar estruturas", "decorar sem usar", "nada"]),
                    ex("text", "Complete o template: 'I'm looking forward to ___ .' (te ver)",
                       "seeing you"),
                    ex("audio", "Escute e transcreva:",
                       "i am used to working late", audio_text="I am used to working late."),
                    ex("quiz", "Praticar templates em voz alta:",
                       "automatiza a fala", ["automatiza a fala", "não ajuda", "só cansa"]),
                    ex("quiz", "Com o tempo, as frases saem:",
                       "automaticamente, sem montar do zero", ["automaticamente, sem montar do zero", "sempre traduzidas", "nunca"]),
                ],
            ),
            topic(
                "velocidade-de-conversa",
                "Velocidade de conversa",
                """
# Velocidade de conversa

Fale em uma velocidade **natural e equilibrada** — nem lenta demais, nem
correndo.

## O problema de cada extremo

```
Muito devagar:  soa inseguro e cansa o ouvinte.
Muito rápido:   compromete a clareza.
```

## Como melhorar

- Pratique **frases inteiras** (não palavra por palavra).
- Automatize vocabulário e estruturas.

> 💘 A velocidade vem da **automatização**, não da pressa. Fale confortável
# ===== e deixe o vocabulário fluir =====
""",
                [
                    ex("quiz", "Velocidade natural de fala:",
                       "equilibrada, nem lenta nem rápida demais", ["equilibrada, nem lenta nem rápida demais", "sempre muito rápida", "sempre muito lenta"]),
                    ex("quiz", "Falar muito devagar pode:",
                       "soar inseguro", ["soar inseguro", "soar profissional", "ajudar sempre"]),
                    ex("text", "Complete: 'Speak at a ___ pace.' (natural)",
                       "natural"),
                    ex("audio", "Escute e transcreva:",
                       "speak at a comfortable pace", audio_text="Speak at a comfortable pace."),
                    ex("quiz", "Para ganhar velocidade, pratique:",
                       "frases inteiras em bloco", ["frases inteiras em bloco", "palavra por palavra", "só leitura"]),
                    ex("quiz", "A velocidade vem com:",
                       "automatização do vocabulário", ["automatização do vocabulário", "pressa", "adivinhação"]),
                ],
            ),
            topic(
                "pronuncia-fluencia",
                "Pronúncia (fluência)",
                """
# Pronúncia (fluência)

Na fluência, o objetivo é **clareza** — ser entendido — mais do que um
sotaque perfeito.

## O que treinar

- **Pares mínimos**: ship/sheep, bit/beat (sons que mudam a palavra).
- **Ritmo e ligação**: a fala conectada (Módulo 14).
- **Shadowing**: repetir o áudio em voz alta, imitando.

> 💘 **Clareza > perfeição**: você não precisa soar britânico ou americano —
# ===== precisa ser entendido =====
""",
                [
                    ex("quiz", "O mais importante na pronúncia é:",
                       "a clareza (ser entendido)", ["a clareza (ser entendido)", "sotaque perfeito", "nunca errar"]),
                    ex("quiz", "Pares mínimos (ship/sheep) treinam:",
                       "sons que diferenciam palavras", ["sons que diferenciam palavras", "gramática", "escrita"]),
                    ex("text", "Complete: 'Practice the ___ sounds.' (difíceis)",
                       "difficult"),
                    ex("audio", "Escute e transcreva:",
                       "focus on clear pronunciation", audio_text="Focus on clear pronunciation."),
                    ex("quiz", "Repetir em voz alta (shadowing) melhora:",
                       "pronúncia e ritmo", ["pronúncia e ritmo", "só a escrita", "nada"]),
                    ex("quiz", "'Clareza > perfeição' significa:",
                       "ser entendido importa mais que sotaque perfeito", ["ser entendido importa mais que sotaque perfeito", "nunca falar", "decorar fonética"]),
                ],
            ),
            topic(
                "entonacao-fluencia",
                "Entonação (fluência)",
                """
# Entonação (fluência)

A **entonação** (subir/descer a voz) muda o significado e a intenção.

## Regras básicas

```
Pergunta sim/não:  tom sobe no fim  ("Ready? ↗")
Afirmação / wh:    tom desce       ("I'm tired. ↘")
```

## Como treinar

- **Repita imitando** o tom do nativo (shadowing).
- Note como a mesma frase muda com o tom.

> 💘 "It's really interesting" com tom diferente pode ser elogio ou ironia —
# ===== o tom é parte do significado =====
""",
                [
                    ex("quiz", "A entonação afeta:",
                       "o significado e a intenção", ["o significado e a intenção", "só o volume", "nada"]),
                    ex("quiz", "Perguntas sim/não sobem o tom:",
                       "no fim", ["no fim", "no início", "nunca"]),
                    ex("text", "Complete: 'Match the ___ to the meaning.' (tom)",
                       "tone"),
                    ex("audio", "Escute e transcreva:",
                       "it's really interesting", audio_text="It's really interesting."),
                    ex("quiz", "Treinar entonação = repetir:",
                       "imitando o tom do nativo", ["imitando o tom do nativo", "sem som", "só lendo"]),
                    ex("quiz", "A mesma frase com tom diferente:",
                       "muda de sentido", ["muda de sentido", "nunca muda", "só muda o volume"]),
                ],
            ),
            topic(
                "velocidade-de-escuta",
                "Velocidade de escuta",
                """
# Velocidade de escuta

Treine o ouvido com velocidades crescentes até o natural parecer claro.

## Como treinar

- Aumente a velocidade do áudio **aos poucos** (1.1x, 1.25x, 1.5x).
- Quando você entende a 1.5x, a fala normal parece lenta e clara.

> 💘 O segredo é a **exposição frequente** — não é um teste, é um treino de
# ===== adaptação =====
""",
                [
                    ex("quiz", "Para treinar escuta rápida:",
                       "aumente a velocidade aos poucos", ["aumente a velocidade aos poucos", "comece no máximo", "não treine"]),
                    ex("quiz", "Ouvir a 1.25x-1.5x:",
                       "acostuma o ouvido à velocidade", ["acostuma o ouvido à velocidade", "piora", "é proibido"]),
                    ex("text", "Complete: 'Increase the speed ___ .' (gradualmente)",
                       "gradually"),
                    ex("audio", "Escute e transcreva:",
                       "try listening at a faster speed", audio_text="Try listening at a faster speed."),
                    ex("quiz", "Escuta rápida + compreensão vem com:",
                       "exposição frequente", ["exposição frequente", "pular", "dormir"]),
                    ex("quiz", "Se você entende a 1.5x, a fala normal:",
                       "parece lenta e clara", ["parece lenta e clara", "impossível", "igual"]),
                ],
            ),
            topic(
                "alternancia-de-contexto",
                "Alternância de contexto",
                """
# Alternância de contexto

Fluência total é **adaptar a linguagem** a cada situação — formal, informal,
técnica, social.

## Como praticar

- Fale do **mesmo assunto** em registros diferentes.
- Pratique em temas variados: trabalho, lazer, notícias, tecnologia.
- Observe como a linguagem muda com o ambiente.

> 💘 No nível avançado, você alterna **com naturalidade**: e-mail formal de
# ===== manhã, conversa informal à noite, discussão técnica no meio =====
""",
                [
                    ex("quiz", "Alternar contextos treina:",
                       "adaptar a linguagem ao ambiente", ["adaptar a linguagem ao ambiente", "só um registro", "nada"]),
                    ex("quiz", "Falar formal e informal exige:",
                       "flexibilidade de registro", ["flexibilidade de registro", "rigidez", "decoração"]),
                    ex("text", "Complete: 'Switch between ___ and formal.' (informal)",
                       "informal"),
                    ex("audio", "Escute e transcreva:",
                       "adapt your language to the situation", audio_text="Adapt your language to the situation."),
                    ex("quiz", "Praticar em temas variados:",
                       "amplia vocabulário e confiança", ["amplia vocabulário e confiança", "atrapalha", "não muda nada"]),
                    ex("quiz", "No nível avançado, você consegue:",
                       "alternar registros com naturalidade", ["alternar registros com naturalidade", "falar igual sempre", "nunca adaptar"]),
                ],
            ),
        ],
    )


# ============================================================
# MODULO 26 - Dominio C1 (aplicado, pos-C1)
# ============================================================

def build_modulo_26_dominio_c1():
    return module(
        "modulo-26-dominio-c1",
        "Módulo 26 — Domínio C1 (C1 Mastery)",
        "O acabamento final: nuance, sentido implícito, humor, sarcasmo, linguagem idiomática, referências culturais, registros, linguagem formal/informal/profissional/acadêmica/persuasiva, precisão e conversa natural.",
        [
            topic(
                "entendendo-nuance",
                "Entendendo nuance",
                """
# Entendendo nuance

**Nuance** é a sutileza de significado — a diferença entre "annoyed" e
"furious", ou entre "It's fine" e "It's great".

## Exemplos de nuance

```
annoyed (chateado)  <  angry (bravo)  <  furious (furioso)
It's fine.   (ok, meio insatisfeito)
It's great.  (entusiasmado)
```

> 💘 Captar nuance exige atenção ao **tom e ao contexto** — não só ao
# ===== dicionário =====
""",
                [
                    ex("quiz", "Nuance é:",
                       "a sutileza de significado", ["a sutileza de significado", "o erro", "o tamanho"]),
                    ex("quiz", "'Annoyed' vs 'furious' mostram:",
                       "graus de intensidade", ["graus de intensidade", "a mesma coisa", "erro"]),
                    ex("text", "Complete: 'Choose words with the right ___ .' (nuance)",
                       "nuance"),
                    ex("audio", "Escute e transcreva:",
                       "the nuance changes the meaning", audio_text="The nuance changes the meaning."),
                    ex("quiz", "Captar nuance exige:",
                       "atenção ao tom e ao contexto", ["atenção ao tom e ao contexto", "só o dicionário", "pressa"]),
                    ex("quiz", "'It could be worse' transmite:",
                       "insatisfação disfarçada", ["insatisfação disfarçada", "alegria total", "surpresa"]),
                ],
            ),
            topic(
                "sentido-implicito-dominio",
                "Sentido implícito (domínio)",
                """
# Sentido implícito (domínio)

No domínio C1, você lê as **entrelinhas** — inclusive em negociações.

## Exemplos

```
"I'll think about it."   ->  muitas vezes é um "não" educado.
"That's interesting."    ->  pode ser indiferença ou desaprovação.
```

## Como captar

Observe **tom, contexto e hesitação** — não só as palavras.

> 💘 Em conversas sutis (negociação, feedback), o implícito manda. Quem só
# ===== ouve o literal perde metade da mensagem =====
""",
                [
                    ex("quiz", "Sentido implícito é:",
                       "o que se entende sem estar dito", ["o que se entende sem estar dito", "o literal", "o título"]),
                    ex("quiz", "'I'll think about it' pode significar:",
                       "um não educado", ["um não educado", "um sim entusiasmado", "uma pergunta"]),
                    ex("text", "Complete: 'Read between the ___ .' (linhas)",
                       "lines"),
                    ex("audio", "Escute e transcreva:",
                       "i will think about it", audio_text="I will think about it."),
                    ex("quiz", "Para captar o implícito, observe:",
                       "tom, contexto e hesitação", ["tom, contexto e hesitação", "só palavras", "nada"]),
                    ex("quiz", "O implícito domina em:",
                       "negociações e conversas sutis", ["negociações e conversas sutis", "manuais", "formulários"]),
                ],
            ),
            topic(
                "humor-c1",
                "Humor (C1)",
                """
# Humor (C1)

Entender humor em inglês exige **cultura**, **contexto** e **ironia**.

## Tipos comuns

```
Wordplay     jogo de palavras
Ironia       dizer o contrário com tom
Referência   piada que depende de cultura/filme/série
```

## Se a piada não funciona

Provavelmente faltou a **referência cultural** — não é que seu inglês seja
fraco.

> 💘 Quanto mais filmes, séries e notícias você consome, mais referências
# ===== você acumula — e mais humor você entende =====
""",
                [
                    ex("quiz", "Humor em inglês usa muito:",
                       "ironia, wordplay e referências", ["ironia, wordplay e referências", "só piadas prontas", "nada"]),
                    ex("quiz", "O que é 'wordplay'?",
                       "jogo de palavras", ["jogo de palavras", "piada de física", "erro"]),
                    ex("text", "Complete: 'He has a great sense of ___ .' (humor)",
                       "humor"),
                    ex("audio", "Escute e transcreva:",
                       "that was a good joke", audio_text="That was a good joke."),
                    ex("quiz", "Entender humor exige:",
                       "cultura e contexto", ["cultura e contexto", "só gramática", "nada"]),
                    ex("quiz", "Se a piada não funciona, provavelmente:",
                       "faltou referência cultural", ["faltou referência cultural", "o inglês é fraco", "é impossível"]),
                ],
            ),
            topic(
                "sarcasmo-c1",
                "Sarcasmo (C1)",
                """
# Sarcasmo (C1)

**Sarcasmo** diz o **oposto** do significado literal, usando o tom.

## Exemplos

```
"Great, another meeting."   (frustração)
"Oh, perfect timing!"       (na verdade, péssimo timing)
```

## Cuidado

- Use sarcasmo com quem **conhece seu tom** — com estranhos, pode soar rude.
- O tom costuma ser **plano ou exagerado**.

> 💘 Entender sarcasmo é essencial; **produzir** sarcasmo exige contexto e
# ===== confiança =====
""",
                [
                    ex("quiz", "Sarcasmo diz:",
                       "o oposto do significado literal", ["o oposto do significado literal", "o literal", "nada"]),
                    ex("quiz", "'Great, another meeting' (sarcástico) significa:",
                       "frustração", ["frustração", "alegria", "pedido"]),
                    ex("text", "Complete: 'He said it ___ .' (sarcasticamente)",
                       "sarcastically"),
                    ex("audio", "Escute e transcreva:",
                       "great another meeting", audio_text="Great, another meeting."),
                    ex("quiz", "Para não ser mal-entendido, use sarcasmo:",
                       "com pessoas que conhecem seu tom", ["com pessoas que conhecem seu tom", "com estranhos sempre", "nunca"]),
                    ex("quiz", "O tom do sarcasmo geralmente:",
                       "é plano ou exagerado", ["é plano ou exagerado", "é sempre feliz", "é sempre gritado"]),
                ],
            ),
            topic(
                "linguagem-idiomatica",
                "Linguagem idiomática",
                """
# Linguagem idiomática

No domínio C1, você usa idioms com **naturalidade** — e sem exagerar.

## Idioms comuns do dia a dia

```
It's a no-brainer.      É óbvio.
I'm on the fence.       Estou em cima do muro (indeciso).
It slipped my mind.     Me escapou (esqueci).
```

> 💘 Idioms demais soam **forçados**. Use com moderação, no contexto certo —
# ===== como um nativo faria =====
""",
                [
                    ex("quiz", "Linguagem idiomática é:",
                       "natural e figurada", ["natural e figurada", "literal", "formal sempre"]),
                    ex("quiz", "O que 'it's a no-brainer' significa?",
                       "é óbvio", ["é óbvio", "é difícil", "é erro"]),
                    ex("text", "Complete: 'It's a no-___ .' (brainer)",
                       "brainer"),
                    ex("audio", "Escute e transcreva:",
                       "it's a no-brainer", audio_text="It's a no-brainer."),
                    ex("quiz", "Usar idioms demais:",
                       "pode soar forçado", ["pode soar forçado", "é sempre ótimo", "é proibido"]),
                    ex("quiz", "Idioms são aprendidos:",
                       "em contexto e blocos", ["em contexto e blocos", "isolados", "nunca"]),
                ],
            ),
            topic(
                "referencias-culturais",
                "Referências culturais",
                """
# Referências culturais

Referências a filmes, séries, história e cultura aparecem o tempo todo.

## Exemplos

```
"That's so 'to Google it'!"   (o Google virou verbo)
"He's the new Steve Jobs."    (referência a inovação)
```

## Por que importam

Sem a referência, a piada ou o comentário **perde o sentido**.

> 💘 Para acumular referências, consuma **filmes, séries e notícias em
# ===== inglês** — é a cultura que completa a língua =====
""",
                [
                    ex("quiz", "Referências culturais aparecem em:",
                       "humor, filmes e conversas", ["humor, filmes e conversas", "manuais", "formulários"]),
                    ex("quiz", "Sem a referência, a piada:",
                       "perde o sentido", ["perde o sentido", "fica mais engraçada", "muda de idioma"]),
                    ex("text", "Complete: 'That's a reference to a famous ___ .' (filme)",
                       "movie"),
                    ex("audio", "Escute e transcreva:",
                       "that is a famous cultural reference", audio_text="That is a famous cultural reference."),
                    ex("quiz", "Para entender referências, consuma:",
                       "filmes, séries e notícias em inglês", ["filmes, séries e notícias em inglês", "nada", "só livros técnicos"]),
                    ex("quiz", "Referência cultural conhecida do mundo tech:",
                       "to Google it", ["to Google it", "to read it", "to eat it"]),
                ],
            ),
            topic(
                "registros-diferentes",
                "Registros diferentes",
                """
# Registros diferentes

Domínio total é **alternar registros** com naturalidade.

## O mesmo assunto, registros diferentes

```
Formal:   "I would like to request a meeting."
Semiformal: "Can we schedule a meeting?"
Informal: "Wanna meet up?"
```

> 💘 Quem domina o C1 não fala igual em todos os lugares — **adapta** o
# ===== registro ao público e à situação =====
""",
                [
                    ex("quiz", "Registros diferentes exigem:",
                       "adaptar vocabulário e tom", ["adaptar vocabulário e tom", "sempre o mesmo", "nada"]),
                    ex("quiz", "Entre amigos, o registro é:",
                       "informal", ["informal", "formal", "jurídico"]),
                    ex("text", "Complete: 'Adjust the ___ to the audience.' (registro)",
                       "register"),
                    ex("audio", "Escute e transcreva:",
                       "adapt your register to the situation", audio_text="Adapt your register to the situation."),
                    ex("quiz", "Em reunião profissional, o registro é:",
                       "formal ou semiformal", ["formal ou semiformal", "de gíria", "informal total"]),
                    ex("quiz", "Dominar registros =:",
                       "flexibilidade total", ["flexibilidade total", "rigidez", "esquecer o informal"]),
                ],
            ),
            topic(
                "linguagem-formal",
                "Linguagem formal",
                """
# Linguagem formal

A linguagem formal usa **frases completas** e **vocabulário polido**.

## Padrões formais

```
I would appreciate it if...     Ficaria grato se...
Please be advised that...       Informo que...
We would be most grateful.      Ficaríamos muito gratos.
```

> 💘 Em formal, **evite contrações** ("I am", não "I'm") e gírias. É o
# ===== padrão de e-mails, documentos e discursos =====
""",
                [
                    ex("quiz", "Linguagem formal usa:",
                       "frases completas e vocabulário polido", ["frases completas e vocabulário polido", "gírias", "contrações"]),
                    ex("quiz", "Em formal, evite:",
                       "contrações e gírias", ["contrações e gírias", "frases completas", "cortesia"]),
                    ex("text", "Complete: 'I would ___ it if...' (agradecer)",
                       "appreciate"),
                    ex("audio", "Escute e transcreva:",
                       "we would be most grateful", audio_text="We would be most grateful."),
                    ex("quiz", "'Please be advised that...' é:",
                       "formal", ["formal", "informal", "gíria"]),
                    ex("quiz", "Formal em e-mail de trabalho:",
                       "padrão esperado", ["padrão esperado", "erro", "opcional"]),
                ],
            ),
            topic(
                "linguagem-informal",
                "Linguagem informal",
                """
# Linguagem informal

A linguagem informal usa **contrações**, **gírias** e **expressões**.

## Exemplos

```
Wanna hang out?          Quer sair?
No worries!              Sem problema!
Catch you later!         Até mais!
```

> 💘 Saber **quando NÃO** usar o informal é parte do domínio: amigos e
# ===== conversas sim; e-mail formal, tese ou entrevista, não =====
""",
                [
                    ex("quiz", "Linguagem informal inclui:",
                       "contrações, gírias e expressões", ["contrações, gírias e expressões", "só formalidade", "jargão legal"]),
                    ex("quiz", "'Wanna hang out?' é:",
                       "informal", ["informal", "formal", "jurídico"]),
                    ex("text", "Complete: 'No ___ !' (problema, informal)",
                       "worries"),
                    ex("audio", "Escute e transcreva:",
                       "let's hang out later", audio_text="Let's hang out later."),
                    ex("quiz", "Informal serve para:",
                       "amigos e conversas", ["amigos e conversas", "e-mails formais", "teses"]),
                    ex("quiz", "Saber quando NÃO usar informal:",
                       "é parte do domínio", ["é parte do domínio", "não importa", "é proibido"]),
                ],
            ),
            topic(
                "linguagem-profissional",
                "Linguagem profissional",
                """
# Linguagem profissional

A linguagem profissional é **clara, concisa e educada**.

## Frases úteis

```
Could you please take a look?      Pode dar uma olhada, por favor?
Let's schedule a follow-up.        Vamos agendar um acompanhamento.
Please let me know your decision.  Avise-me sua decisão.
```

> 💘 Profissional **assertivo** pede sem agredir: "Could you please..."
# ===== é firme e educado ao mesmo tempo =====
""",
                [
                    ex("quiz", "Linguagem profissional é:",
                       "clara, concisa e educada", ["clara, concisa e educada", "longa", "informal"]),
                    ex("quiz", "Para pedir algo profissionalmente:",
                       "Could you please take a look?", ["Could you please take a look?", "Look now.", "Whatever."]),
                    ex("text", "Complete: 'Please let me know your ___ .' (decisão)",
                       "decision"),
                    ex("audio", "Escute e transcreva:",
                       "let's schedule a follow-up", audio_text="Let's schedule a follow-up."),
                    ex("quiz", "Em profissional, evite:",
                       "ambiguidade e gírias", ["ambiguidade e gírias", "clareza", "objetividade"]),
                    ex("quiz", "Comunicação profissional assertiva:",
                       "pede sem agredir", ["pede sem agredir", "grita", "silencia"]),
                ],
            ),
            topic(
                "linguagem-academica",
                "Linguagem acadêmica",
                """
# Linguagem acadêmica

A linguagem acadêmica é **impessoal** e com **hedging**.

## Padrões acadêmicos

```
It could be argued that...       Pode-se argumentar que...
The evidence suggests that...    A evidência sugere que...
According to Smith...            Segundo Smith...
```

> 💘 No acadêmico, **citações dão credibilidade** e o **hedging** suaviza as
# ===== afirmações — nada de "I think" ou certezas absolutas =====
""",
                [
                    ex("quiz", "Linguagem acadêmica é:",
                       "impessoal e com hedging", ["impessoal e com hedging", "informal", "com gírias"]),
                    ex("quiz", "Em vez de 'I think', o acadêmico diz:",
                       "It could be argued that...", ["It could be argued that...", "Trust me.", "No."]),
                    ex("text", "Complete: 'The data ___ that...' (sugere)",
                       "suggests"),
                    ex("audio", "Escute e transcreva:",
                       "the evidence suggests a clear trend", audio_text="The evidence suggests a clear trend."),
                    ex("quiz", "No acadêmico, cita-se fontes:",
                       "para dar credibilidade", ["para dar credibilidade", "por obrigação sem sentido", "nunca"]),
                    ex("quiz", "Hedging acadêmico:",
                       "suaviza afirmações", ["suaviza afirmações", "afirma tudo", "nega"]),
                ],
            ),
            topic(
                "linguagem-persuasiva",
                "Linguagem persuasiva",
                """
# Linguagem persuasiva

A linguagem persuasiva combina **lógica, emoção e credibilidade** e termina
com uma **ação**.

## Frases úteis

```
Imagine the benefits.          Imagine as vantagens.
This is a unique opportunity.  Esta é uma oportunidade única.
Act now!                       Aja agora!
```

> 💘 Persuasão de nível usa **verbos de ação** e foca no **benefício** para
# ===== o outro — e encerra com uma call to action =====
""",
                [
                    ex("quiz", "Persuasão eficaz apela:",
                       "à lógica, emoção e credibilidade", ["à lógica, emoção e credibilidade", "só ao medo", "só ao grito"]),
                    ex("quiz", "'Imagine the benefits' apela:",
                       "à emoção/imagem", ["à emoção/imagem", "à lógica pura", "à ameaça"]),
                    ex("text", "Complete: 'This is a ___ opportunity.' (única)",
                       "unique"),
                    ex("audio", "Escute e transcreva:",
                       "this is a unique opportunity for you", audio_text="This is a unique opportunity for you."),
                    ex("quiz", "Linguagem persuasiva usa:",
                       "verbos de ação e benefícios", ["verbos de ação e benefícios", "só passiva", "só dúvidas"]),
                    ex("quiz", "A call to action encerra:",
                       "pedindo uma ação", ["pedindo uma ação", "com silêncio", "com dúvida"]),
                ],
            ),
            topic(
                "comunicacao-precisa",
                "Comunicação precisa",
                """
# Comunicação precisa

**Comunicação precisa** evita ambiguidade — essencial em prazos, números e
decisões.

## Frases úteis

```
Please specify the exact date.     Especifique a data exata.
Just to be clear...                Só para ficar claro...
Could you clarify the timeline?    Pode esclarecer o cronograma?
```

> 💘 "Just to be clear..." confirma a precisão e evita retrabalho — é a
# ===== marca da comunicação profissional =====
""",
                [
                    ex("quiz", "Comunicação precisa evita:",
                       "ambiguidade e vagueza", ["ambiguidade e vagueza", "clareza", "exemplos"]),
                    ex("quiz", "'Please specify...' pede:",
                       "mais detalhes", ["mais detalhes", "menos", "nada"]),
                    ex("text", "Complete: 'Could you ___ the timeline?' (especificar)",
                       "specify"),
                    ex("audio", "Escute e transcreva:",
                       "please specify the exact date", audio_text="Please specify the exact date."),
                    ex("quiz", "Precisão evita mal-entendidos:",
                       "em prazos e números", ["em prazos e números", "em tudo", "nunca"]),
                    ex("quiz", "Para confirmar precisão:",
                       "Just to be clear...", ["Just to be clear...", "Whatever.", "Trust me."]),
                ],
            ),
            topic(
                "conversa-natural",
                "Conversa natural",
                """
# Conversa natural

Conversa natural tem **troca de turnos**, **reações** e **perguntas**.

## Reações naturais

```
Oh, really? That's great!      Sério? Que ótimo!
I see what you mean.           Entendo o que você quer dizer.
By the way, have you heard?    A propósito, você ouviu?
```

## Pegando o turno

```
Can I add something here?      Posso acrescentar algo?
```

> 💘 Conversa flui com **escuta ativa** — reagir e perguntar mantém o
# ===== diálogo vivo =====
""",
                [
                    ex("quiz", "Conversa natural tem:",
                       "troca de turnos e reações", ["troca de turnos e reações", "monólogos", "silêncio"]),
                    ex("quiz", "Para reagir naturalmente:",
                       "Oh, really? That's great!", ["Oh, really? That's great!", "Ok.", "Silence."]),
                    ex("text", "Complete: 'By the way, ___ you heard?' (você)",
                       "have"),
                    ex("audio", "Escute e transcreva:",
                       "oh really that is great news", audio_text="Oh really, that is great news."),
                    ex("quiz", "Pegar o turno educadamente:",
                       "Can I add something here?", ["Can I add something here?", "Shut up.", "No."]),
                    ex("quiz", "Conversa natural flui com:",
                       "escuta ativa e perguntas", ["escuta ativa e perguntas", "só falar", "só ouvir"]),
                ],
            ),
        ],
    )


# ============================================================
# MODULO 27 - Imersao Final (aplicado, pos-C1)
# ============================================================

def build_modulo_27_imersao_final():
    return module(
        "modulo-27-imersao-final",
        "Módulo 27 — Imersão Final",
        "O fechamento do curso: ler livros, assistir filmes sem legenda, consumir conteúdo técnico, ouvir podcasts, escrever e falar todos os dias, participar de discussões, ler documentação, trabalhar em inglês e pensar em inglês.",
        [
            topic(
                "ler-livros-em-ingles",
                "Ler livros em inglês",
                """
# Ler livros em inglês

Ler é uma das formas mais ricas de imersão — e deve ser **progressiva**.

## Como começar

- Escolha livros **curtos e do seu nível**.
- Leia **um pouco todo dia** (2-3 páginas).
- Ao encontrar palavra nova, **tente adivinhar pelo contexto** antes do
  dicionário.

> 💘 Ler em voz alta de vez em quando também treina **pronúncia e ritmo**.
""",
                [
                    ex("quiz", "Para começar a ler em inglês:",
                       "livros curtos e do seu nível", ["livros curtos e do seu nível", "clássicos difíceis", "nada"]),
                    ex("quiz", "Ler todo dia cria:",
                       "ritmo e vocabulário automático", ["ritmo e vocabulário automático", "cansaço sem ganho", "nada"]),
                    ex("text", "Complete: 'Read a ___ every day.' (pouco)",
                       "little"),
                    ex("audio", "Escute e transcreva:",
                       "i read a few pages every day", audio_text="I read a few pages every day."),
                    ex("quiz", "Ao encontrar palavra nova:",
                       "tente adivinhar pelo contexto", ["tente adivinhar pelo contexto", "pare tudo", "traduza tudo"]),
                    ex("quiz", "Ler em voz alta ajuda:",
                       "pronúncia e ritmo", ["pronúncia e ritmo", "só a escrita", "nada"]),
                ],
            ),
            topic(
                "filmes-sem-legenda",
                "Assistir filmes sem legenda",
                """
# Assistir filmes sem legenda

Largar a legenda é **progressivo** — e um marco da imersão.

## Como fazer

1. **1ª fase**: legenda em inglês.
2. **2ª fase**: cenas conhecidas sem legenda.
3. **3ª fase**: episódios/filmes inteiros sem legenda.

Ao travar, **rever a cena com legenda** — é assim que se conecta som e
escrita.

> 💘 Re-assistir algo que você já conhece sem legenda usa o **contexto**
# ===== para preencher o que não ouviu =====
""",
                [
                    ex("quiz", "Para largar a legenda:",
                       "tire gradualmente (cenas -> episódios)", ["tire gradualmente (cenas -> episódios)", "de uma vez", "nunca"]),
                    ex("quiz", "Ao re-assistir algo conhecido sem legenda:",
                       "o contexto ajuda a entender", ["o contexto ajuda a entender", "atrapalha", "nada"]),
                    ex("text", "Complete: 'Watch with ___ subtitles first.' (inglês)",
                       "english"),
                    ex("audio", "Escute e transcreva:",
                       "i can watch this without subtitles", audio_text="I can watch this without subtitles."),
                    ex("quiz", "Filme sem legenda treina:",
                       "escuta real e fala rápida", ["escuta real e fala rápida", "só leitura", "nada"]),
                    ex("quiz", "Se travar, o ideal é:",
                       "rever a cena com legenda", ["rever a cena com legenda", "desistir", "pular tudo"]),
                ],
            ),
            topic(
                "conteudo-tecnico-imersao",
                "Conteúdo técnico em inglês",
                """
# Conteúdo técnico em inglês

Tutoriais, palestras e docs em inglês são a imersão perfeita para quem
trabalha com tecnologia.

## Como aproveitar

- Assista **tutoriais e talks** em inglês.
- **Pause e repita** os trechos importantes.
- Fixe o vocabulário **no contexto real**.

> 💘 Code reviews, palestras e docs em inglês treinam o vocabulário técnico
# ===== que você vai usar de verdade =====
""",
                [
                    ex("quiz", "Conteúdo técnico em inglês:",
                       "aparece em tutoriais, docs e palestras", ["aparece em tutoriais, docs e palestras", "não existe", "é proibido"]),
                    ex("quiz", "Para acompanhar um tutorial:",
                       "pausar e repetir trechos", ["pausar e repetir trechos", "correr", "dormir"]),
                    ex("text", "Complete: 'Watch technical ___ in English.' (palestras)",
                       "talks"),
                    ex("audio", "Escute e transcreva:",
                       "i follow tech talks in english", audio_text="I follow tech talks in English."),
                    ex("quiz", "O vocabulário técnico fixa:",
                       "no contexto real", ["no contexto real", "só na lista", "nunca"]),
                    ex("quiz", "Assistir code review em inglês:",
                       "treina vocabulário técnico real", ["treina vocabulário técnico real", "não ajuda", "é erro"]),
                ],
            ),
            topic(
                "ouvir-podcasts-imersao",
                "Ouvir podcasts (imersão)",
                """
# Ouvir podcasts (imersão)

Podcasts são imersão que **cabe em qualquer rotina**.

## Como aproveitar

- Ouça **no deslocamento** (commute), academia ou tarefas.
- Escolha temas do seu **interesse**.
- Depois, **resuma em voz alta** — treina escuta E fala.

> 💘 Um pouco todo dia rende mais que horas no domingo. Constância é a
# ===== chave =====
""",
                [
                    ex("quiz", "Podcasts cabem na rotina porque:",
                       "dá para ouvir em qualquer lugar", ["dá para ouvir em qualquer lugar", "são longos demais", "não têm áudio"]),
                    ex("quiz", "A rotina ideal:",
                       "um pouco todo dia", ["um pouco todo dia", "horas no domingo", "nunca"]),
                    ex("text", "Complete: 'Listen to podcasts on your ___ .' (deslocamento)",
                       "commute"),
                    ex("audio", "Escute e transcreva:",
                       "i listen to podcasts on my commute", audio_text="I listen to podcasts on my commute."),
                    ex("quiz", "Escolha podcasts:",
                       "do seu interesse", ["do seu interesse", "impossíveis", "aleatórios"]),
                    ex("quiz", "Podcast + resumo em voz alta:",
                       "treina escuta E fala", ["treina escuta E fala", "só escuta", "nada"]),
                ],
            ),
            topic(
                "escrever-todos-os-dias",
                "Escrever todos os dias",
                """
# Escrever todos os dias

A escrita diária constrói **consistência** e **vocabulário ativo**.

## Como fazer

- Escreva um **diário** em inglês: "Today I...".
- Não **traduza palavra a palavra** — use o que você já sabe.
- Revise às vezes, mas **escreva todo dia**.

> 💘 Escrever consolida o vocabulário **ativo** — aquele que você consegue
# ===== produzir, não só reconhecer =====
""",
                [
                    ex("quiz", "Escrever todo dia cria:",
                       "consistência e confiança", ["consistência e confiança", "pressão", "nada"]),
                    ex("quiz", "Um bom início de diário:",
                       "Today I...", ["Today I...", "Blah.", "Whatever."]),
                    ex("text", "Complete: 'Write a ___ entry every day.' (diário)",
                       "journal"),
                    ex("audio", "Escute e transcreva:",
                       "i write a journal in english", audio_text="I write a journal in English."),
                    ex("quiz", "Ao escrever, evite:",
                       "traduzir palavra a palavra", ["traduzir palavra a palavra", "blocos prontos", "revisar"]),
                    ex("quiz", "Escrever consolida:",
                       "o vocabulário ativo", ["o vocabulário ativo", "só a caligrafia", "nada"]),
                ],
            ),
            topic(
                "falar-todos-os-dias",
                "Falar todos os dias",
                """
# Falar todos os dias

Falar diariamente é o treino que fecha a fluência.

## Como praticar sem interlocutor

- **Shadowing**: repetir em voz alta o que ouve (áudio, série, podcast).
- **Fale sozinho**: narre sua rotina ou descreva o que vê.
- Se puder, **app/amigo**: 10 minutos de conversa real.

> 💘 A **constância importa mais que a duração**: 10 minutos todo dia vencem
# ===== 2 horas uma vez por semana =====
""",
                [
                    ex("quiz", "Falar todo dia exige:",
                       "oportunidades (shadowing, app, amigo)", ["oportunidades (shadowing, app, amigo)", "silêncio", "só leitura"]),
                    ex("quiz", "Shadowing (repetir áudio) treina:",
                       "fala sem precisar de interlocutor", ["fala sem precisar de interlocutor", "nada", "só escrita"]),
                    ex("text", "Complete: 'Speak ___ , even alone.' (em voz alta)",
                       "aloud"),
                    ex("audio", "Escute e transcreva:",
                       "practice speaking every single day", audio_text="Practice speaking every single day."),
                    ex("quiz", "Falar sozinho em inglês:",
                       "treina fluência", ["treina fluência", "é inútil", "é proibido"]),
                    ex("quiz", "A constância importa mais que:",
                       "a duração", ["a duração", "o vocabulário", "tudo"]),
                ],
            ),
            topic(
                "participar-de-discussoes",
                "Participar de discussões",
                """
# Participar de discussões

Discussões reais colocam seu inglês à prova — e treinam o pensamento.

## Onde participar

- **Fóruns** (Reddit, Stack Overflow, comunidades).
- **Grupos** de idiomas e meetups.
- Comentários em **inglês** (notícias, YouTube).

> 💘 Discutir ativamente treina **produção e pensamento em inglês**. Não
# ===== tenha medo de errar — errar faz parte de aprender =====
""",
                [
                    ex("quiz", "Para praticar discussão:",
                       "participe de fóruns e grupos", ["participe de fóruns e grupos", "só leia", "evite"]),
                    ex("quiz", "Em fórum técnico (ex.: Reddit/Stack Overflow):",
                       "responda e comente em inglês", ["responda e comente em inglês", "só leia", "traduza"]),
                    ex("text", "Complete: 'Join online ___ .' (comunidades)",
                       "communities"),
                    ex("audio", "Escute e transcreva:",
                       "i joined an english discussion group", audio_text="I joined an English discussion group."),
                    ex("quiz", "Discutir ativamente treina:",
                       "produção e pensamento em inglês", ["produção e pensamento em inglês", "só escuta", "nada"]),
                    ex("quiz", "Não tenha medo de errar:",
                       "errar faz parte de aprender", ["errar faz parte de aprender", "pare de falar", "só escreva"]),
                ],
            ),
            topic(
                "ler-documentacao-tecnica",
                "Ler documentação técnica",
                """
# Ler documentação técnica

A documentação real é uma das melhores fontes de **inglês técnico autêntico**.

## Como aproveitar

- Leia a **docs** das ferramentas que você usa.
- Anote **expressões úteis** (install, configure, deploy).
- Replique em conversas e textos.

> 💘 Docs ensinam frases **reais de uso técnico** — o inglês exato do
# ===== dia a dia de quem trabalha com tecnologia =====
""",
                [
                    ex("quiz", "Documentação técnica real:",
                       "é a melhor fonte de inglês técnico", ["é a melhor fonte de inglês técnico", "é inútil", "é só formal"]),
                    ex("quiz", "Ao ler docs, anote:",
                       "expressões úteis", ["expressões úteis", "o número de páginas", "nada"]),
                    ex("text", "Complete: 'Read the ___ of your tools.' (documentação)",
                       "docs"),
                    ex("audio", "Escute e transcreva:",
                       "i read the documentation of every tool", audio_text="I read the documentation of every tool."),
                    ex("quiz", "Docs ensinam:",
                       "frases reais de uso técnico", ["frases reais de uso técnico", "só teoria", "nada"]),
                    ex("quiz", "Trabalhar com docs em inglês:",
                       "profissionaliza o inglês técnico", ["profissionaliza o inglês técnico", "atrapalha", "é opcional"]),
                ],
            ),
            topic(
                "trabalhar-em-ingles",
                "Trabalhar inteiramente em inglês",
                """
# Trabalhar inteiramente em inglês

O ambiente de trabalho 100% em inglês é a imersão profissional completa.

## O que envolve

```
e-mails e chats em inglês
reuniões e apresentações
código, docs e code reviews
```

## O essencial

- **Vocabulário técnico** + **comunicação clara**.
- Os chunks do dia a dia do trabalho (Módulo 23).

> 💘 A imersão total acelera a fluência como nada mais — mas exige a base
# ===== que você construiu até aqui =====
""",
                [
                    ex("quiz", "Trabalhar em inglês inclui:",
                       "e-mails, reuniões e código", ["e-mails, reuniões e código", "só e-mail", "nada"]),
                    ex("quiz", "Para isso, o essencial é:",
                       "vocabulário técnico + comunicação clara", ["vocabulário técnico + comunicação clara", "só gramática", "só gíria"]),
                    ex("text", "Complete: 'Work in an English-speaking ___ .' (ambiente)",
                       "environment"),
                    ex("audio", "Escute e transcreva:",
                       "i work fully in english", audio_text="I work fully in English."),
                    ex("quiz", "Imersão total acelera:",
                       "a fluência", ["a fluência", "o desânimo", "nada"]),
                    ex("quiz", "O inglês profissional real usa:",
                       "chunks do dia a dia do trabalho", ["chunks do dia a dia do trabalho", "só formalismo", "só informal"]),
                ],
            ),
            topic(
                "pensar-em-ingles-imersao",
                "Pensar em inglês (imersão)",
                """
# Pensar em inglês (imersão)

Pensar em inglês é o **sinal máximo** de fluência consolidada.

## Como chegar lá

- **Narre sua rotina** em inglês (em pensamento ou voz baixa).
- Responda a si mesmo em inglês.
- Aos poucos, os sonhos também migram para o inglês — um grande marco!

> 💘 Quando você **sonha** em inglês, a imersão virou parte de você.
# ===== Parabéns: este é o fim do curso, e o começo da autonomia =====
""",
                [
                    ex("quiz", "Pensar em inglês é o sinal de:",
                       "fluência consolidada", ["fluência consolidada", "erro", "moda"]),
                    ex("quiz", "Para chegar lá, pratique:",
                       "narrar a rotina em inglês", ["narrar a rotina em inglês", "nunca", "só sonhos"]),
                    ex("text", "Complete: 'Narrate your ___ in English.' (rotina)",
                       "routine"),
                    ex("audio", "Escute e transcreva:",
                       "i try to think in english", audio_text="I try to think in English."),
                    ex("quiz", "Quando você sonha em inglês:",
                       "é um grande marco", ["é um grande marco", "é erro", "é impossível"]),
                    ex("quiz", "O curso termina com:",
                       "a autonomia de continuar sozinho", ["a autonomia de continuar sozinho", "a dependência do curso", "nada"]),
                ],
            ),
        ],
    )


# ============================================================
# Montagem final: monta o curso na ordem do roteiro
# ============================================================

# Ordem final dos 27 módulos do roteiro (tools/ENGLISH_ROADMAP.md). Módulos
# cujo builder ainda não existe (fases futuras não escritas) simplesmente não
# aparecem no JSON até a fase deles ser construída.
TARGET_ORDER = [
    "modulo-01-primeiros-passos",
    "modulo-02-gramatica-essencial-a1",
    "modulo-03-vocabulario-basico",
    "modulo-04-comunicacao-a1",
    "modulo-05-gramatica-essencial-a2",
    "modulo-06-vocabulario-a2",
    "modulo-07-comunicacao-a2",
    "modulo-08-gramatica-essencial-b1",
    "modulo-09-vocabulario-b1",
    "modulo-10-speaking-b1",
    "modulo-11-listening-b1",
    "modulo-12-gramatica-essencial-b2",
    "modulo-13-vocabulario-b2",
    "modulo-14-ingles-natural-b2",
    "modulo-15-speaking-b2",
    "modulo-16-writing-b2",
    "modulo-17-gramatica-avancada-c1",
    "modulo-18-vocabulario-c1",
    "modulo-19-speaking-c1",
    "modulo-20-listening-c1",
    "modulo-21-reading-c1",
    "modulo-22-writing-c1",
    "modulo-23-ingles-trabalho",
    "modulo-24-ingles-tecnologia",
    "modulo-25-treino-fluencia",
    "modulo-26-dominio-c1",
    "modulo-27-imersao-final",
]

BUILDERS = {
    "modulo-01-primeiros-passos": build_modulo_01_primeiros_passos,
    "modulo-02-gramatica-essencial-a1": build_modulo_02_gramatica_essencial_a1,
    "modulo-03-vocabulario-basico": build_modulo_03_vocabulario_basico,
    "modulo-04-comunicacao-a1": build_modulo_04_comunicacao_a1,
    "modulo-05-gramatica-essencial-a2": build_modulo_05_gramatica_essencial_a2,
    "modulo-06-vocabulario-a2": build_modulo_06_vocabulario_a2,
    "modulo-07-comunicacao-a2": build_modulo_07_comunicacao_a2,
    "modulo-08-gramatica-essencial-b1": build_modulo_08_gramatica_essencial_b1,
    "modulo-09-vocabulario-b1": build_modulo_09_vocabulario_b1,
    "modulo-10-speaking-b1": build_modulo_10_speaking_b1,
    "modulo-11-listening-b1": build_modulo_11_listening_b1,
    "modulo-12-gramatica-essencial-b2": build_modulo_12_gramatica_essencial_b2,
    "modulo-13-vocabulario-b2": build_modulo_13_vocabulario_b2,
    "modulo-14-ingles-natural-b2": build_modulo_14_ingles_natural_b2,
    "modulo-15-speaking-b2": build_modulo_15_speaking_b2,
    "modulo-16-writing-b2": build_modulo_16_writing_b2,
    "modulo-17-gramatica-avancada-c1": build_modulo_17_gramatica_avancada_c1,
    "modulo-18-vocabulario-c1": build_modulo_18_vocabulario_c1,
    "modulo-19-speaking-c1": build_modulo_19_speaking_c1,
    "modulo-20-listening-c1": build_modulo_20_listening_c1,
    "modulo-21-reading-c1": build_modulo_21_reading_c1,
    "modulo-22-writing-c1": build_modulo_22_writing_c1,
    "modulo-23-ingles-trabalho": build_modulo_23_ingles_trabalho,
    "modulo-24-ingles-tecnologia": build_modulo_24_ingles_tecnologia,
    "modulo-25-treino-fluencia": build_modulo_25_treino_fluencia,
    "modulo-26-dominio-c1": build_modulo_26_dominio_c1,
    "modulo-27-imersao-final": build_modulo_27_imersao_final,
}


def finalize_modules(modules):
    for m_idx, m in enumerate(modules):
        m["position"] = m_idx
        # Renumera o título "Módulo N" pra bater com a posição nova (1-indexado).
        m["title"] = re.sub(r"^Módulo \d+", f"Módulo {m_idx + 1}", m["title"])
        for t_idx, t in enumerate(m["topics"]):
            t["position"] = t_idx
            for e_idx, e in enumerate(t["exercises"]):
                e["position"] = e_idx
                # O botao de ouvir de cada alternativa le a propria alternativa:
                # se elas sao teoria em portugues, a voz tem que ser pt-BR.
                if e["type"] == "quiz":
                    opts = e.get("options") or []
                    alvo = sum(1 for o in opts if is_target_language(o))
                    if alvo <= len(opts) - alvo:
                        e["audio_lang"] = "pt-BR"
    return modules


def main():
    by_slug = {}
    for slug, builder in BUILDERS.items():
        by_slug[slug] = builder()

    modules = [by_slug[slug] for slug in TARGET_ORDER if slug in by_slug]
    modules = finalize_modules(modules)

    # Os módulos 1 a 16 têm a meta fechada de 10; os demais seguem o mínimo
    # geral de 5 exercícios/tópico (regra do tools/README.md).
    active_module_slugs = set(BUILDERS)
    problems = check(modules, active_module_slugs)
    if problems:
        print("ERROS - nada foi escrito:")
        for p in problems:
            print("  -", p)
        raise SystemExit(1)

    data = {
        "slug": "ingles-do-zero",
        "title": "Inglês do Zero",
        "description": "Uma trilha completa de inglês, do absoluto zero (A1) até um nível avançado (C1), organizada em 27 módulos por nível e habilidade (gramática, vocabulário, comunicação, speaking, listening, writing), mais uma trilha aplicada de trabalho, tecnologia e fluência. Cada tópico explica o conteúdo em português, com bastante exemplo em inglês, e você pratica digitando, ouvindo, falando e respondendo quizzes direto no navegador — clique em qualquer opção de quiz ou frase de exemplo para ouvir a pronúncia.",
        "category": "Idiomas",
        "icon": "🇬🇧",
        "level": "Do zero ao avançado (A1–C1)",
        "position": 3,
        "modules": modules,
    }

    with OUT_PATH.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")

    n_topics = sum(len(m["topics"]) for m in data["modules"])
    n_ex = sum(len(t["exercises"]) for m in data["modules"] for t in m["topics"])
    n_pt = sum(1 for m in data["modules"] for t in m["topics"] for e in t["exercises"]
               if e.get("audio_lang") == "pt-BR")
    print(f"OK: {len(data['modules'])} modulos, {n_topics} topicos, {n_ex} exercicios "
          f"({n_pt} com voz pt-BR) -> {OUT_PATH}")


if __name__ == "__main__":
    main()
