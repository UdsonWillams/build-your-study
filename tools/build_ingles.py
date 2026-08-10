# -*- coding: utf-8 -*-
"""Gera app/content/ingles-do-zero.json a partir de uma estrutura Python.

Mesma abordagem usada para o curso de russo (build_russo.py): construir como
dict Python e serializar com json.dump(ensure_ascii=False, indent=2) evita
risco de JSON quebrado em um arquivo grande com muito texto.
"""
import json
import re
from pathlib import Path

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


MODULES = []

# ============================================================
# MODULO 0 - Primeiros Passos (A1)
# ============================================================
MODULES.append(module(
    "primeiros-passos-ingles",
    "Módulo 0 — Primeiros Passos (A1 · iniciante total)",
    "Como funciona o curso, alfabeto e pronúncia, pronomes, o verbo to be, saudações e os primeiros números.",
    [
        topic(
            "o-que-e-o-cefr",
            "Como este curso funciona: os níveis A1 a C1",
            """
# Como este curso funciona: os níveis A1 a C1

Este curso segue o **CEFR** (Common European Framework of Reference for Languages) — a escala mais usada no mundo para medir o nível de um idioma. Você vai ver essas siglas nos títulos dos módulos:

| Nível | Nome | Você já consegue... |
|---|---|---|
| **A1** | Iniciante | Frases simples, se apresentar, pedir informações básicas |
| **A2** | Básico | Conversas do dia a dia, falar da rotina, do passado |
| **B1** | Intermediário | Contar histórias, dar opiniões, viajar sem depender de tradutor |
| **B2** | Intermediário avançado | Discutir temas variados, entender filmes/séries sem legenda |
| **C1** | Avançado | Se expressar com fluência, nuance e naturalidade |

## Como o curso está organizado

- Cada **módulo** traz uma sigla no título (ex.: *A1*, *B1*) indicando o nível daquele conteúdo — do mais simples ao mais avançado.
- Cada **tópico** explica uma regra de gramática em português, com bastante exemplo em inglês.
- Os **exercícios** variam: digitar a resposta, escolher a opção certa (quiz), ouvir uma frase em inglês e transcrever, ou falar em voz alta no microfone e receber feedback de pronúncia.

> 💡 Não se preocupe em decorar a sigla do nível — ela é só um mapa para você saber onde está. O importante é praticar um pouco todos os dias.

## Como aproveitar melhor os exercícios

Clique no ícone de alto-falante 🔊 sempre que aparecer, mesmo antes de responder — ouvir a pronúncia correta antes de tentar ajuda a fixar o som certo desde o início, em vez de praticar um erro. Nos exercícios de quiz, cada opção também tem seu próprio botão de áudio, então você pode ouvir todas as alternativas antes de escolher.
""",
            [
                ex("quiz", "Qual escala este curso usa para medir seu nível?",
                   "CEFR (A1 a C1)", ["CEFR (A1 a C1)", "TOEFL", "ENEM"], audio_lang="pt-BR"),
                ex("quiz", "O que a sigla do nível (A1, B1...) indica no título de cada módulo?",
                   "A dificuldade daquele conteúdo, do mais simples ao mais avançado",
                   ["A dificuldade daquele conteúdo, do mais simples ao mais avançado", "O número de exercícios do módulo", "Quanto tempo falta para terminar o curso"],
                   audio_lang="pt-BR"),
                ex("quiz", "Segundo a lição, o que vale a pena fazer antes mesmo de tentar responder um exercício de áudio/quiz?",
                   "Clicar no ícone de alto-falante para ouvir a pronúncia primeiro",
                   ["Clicar no ícone de alto-falante para ouvir a pronúncia primeiro", "Pular direto para o próximo módulo", "Decorar a sigla do nível"],
                   audio_lang="pt-BR"),
                ex("quiz", "Até que nível (CEFR) este curso pretende levar você?",
                   "C1", ["A2", "B1", "C1"], audio_lang="pt-BR"),
            ],
        ),
        topic(
            "alfabeto-e-pronuncia",
            "Alfabeto e pronúncia em inglês",
            """
# Alfabeto e pronúncia em inglês

Antes de montar frases, vale ouvir como soam as letras e alguns sons do inglês — muitos são bem diferentes do português.

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

## Sons de vogais

O inglês tem muito mais sons vocálicos do que letras vogais — por isso a mesma letra soa diferente em palavras diferentes: compare `cat` (o "a" curto), `car` (o "a" longo) e `cake` (o "a" que soa como "ei").

## Sons que não existem em português

Dois sons costumam ser os mais difíceis para brasileiros:

- **th** (como em `think` e `this`): a língua fica entre os dentes — não existe equivalente em português, e trocar por "f"/"t" muda o significado da palavra.
- **r final** (como em `car`, `better`): em muitos sotaques americanos, é um som gutural único, bem diferente do "r" do português.

> 🎧 A melhor forma de treinar pronúncia é **ouvir muito** e repetir em voz alta. Os exercícios abaixo já começam esse treino — clique em 🔊 para ouvir e 🎤 para tentar falar.
""",
            [
                ex("audio", "Escute a frase e transcreva o que você ouviu:",
                   "my name is anna", audio_text="My name is Anna."),
                ex("speak", "Repita a frase em voz alta:",
                   "hello how are you", audio_text="Hello, how are you?"),
                ex("quiz", 'Qual som NÃO existe em português e costuma ser difícil para brasileiros (ex: "think")?',
                   "th", ["th", "b", "m"], audio_lang="pt-BR"),
                ex("speak", "Repita a palavra em voz alta, prestando atenção no som de \"th\":",
                   "think", audio_text="think"),
            ],
        ),
        topic(
            "pronomes-pessoais",
            "Pronomes pessoais (I, you, he, she...)",
            """
# Pronomes pessoais

Os pronomes pessoais (sujeito) substituem nomes de pessoas ou coisas:

| Inglês | Português | Uso |
|---|---|---|
| **I** | eu | sempre maiúsculo, mesmo no meio da frase |
| **you** | você / vocês | serve tanto para singular quanto plural |
| **he** | ele | pessoa do sexo masculino |
| **she** | ela | pessoa do sexo feminino |
| **it** | ele/ela (coisa, animal) | objetos, animais, ideias |
| **we** | nós | |
| **they** | eles/elas | pessoas, coisas ou animais no plural |

## Exemplos

```
I am a student.        (Eu sou um estudante.)
She is my sister.      (Ela é minha irmã.)
It is a nice city.     (É/Ela é uma cidade legal.)
They are my friends.   (Eles são meus amigos.)
```

> 💡 Diferente do português, o inglês **quase sempre** precisa do pronome antes do verbo — não dá para simplesmente omitir.

## "you" não distingue formal/informal

Ao contrário do português (que tem "você" e "o senhor"/"a senhora"), o inglês usa **you** para qualquer grau de formalidade, singular ou plural. Quem decide o tom formal é o resto da frase (escolha de palavras, "please", etc.), não o pronome.
""",
            [
                ex("quiz", 'Qual pronome substitui **"my brother"** (meu irmão)?',
                   "he", ["he", "she", "it", "they"]),
                ex("quiz", 'Qual pronome substitui **"the book"** (o livro)?',
                   "it", ["he", "she", "it", "we"]),
                ex("text", "Complete em inglês: ___ am a student. (Eu sou um estudante.)",
                   "i"),
                ex("quiz", 'O pronome "you" muda dependendo se você está falando de forma formal ou informal?',
                   "Não, \"you\" serve para qualquer grau de formalidade", ["Não, \"you\" serve para qualquer grau de formalidade", "Sim, existe uma forma formal separada", "Só muda no plural"],
                   audio_lang="pt-BR"),
            ],
        ),
        topic(
            "verbo-to-be",
            "Verbo to be (am / is / are)",
            """
# Verbo to be (am / is / are)

O verbo **to be** ("ser/estar") é o primeiro verbo que todo estudante de inglês aprende — ele muda de acordo com o pronome:

| Pronome | to be | Contração |
|---|---|---|
| I | am | I'm |
| you | are | you're |
| he / she / it | is | he's / she's / it's |
| we | are | we're |
| they | are | they're |

## Afirmativo, negativo e interrogativo

```
I am happy.          ->  I'm not happy.          ->  Am I happy?
She is a doctor.     ->  She is not a doctor.    ->  Is she a doctor?
They are ready.      ->  They are not ready.     ->  Are they ready?
```

Na negativa, "is not" vira **isn't** e "are not" vira **aren't** (só "am not" não tem contração curta).

> ⚠️ Cuidado: verbo **to be** não é para ações, é para estados, características e identidade ("eu **sou**", "ela **está**", "isso **é**").

## Erro comum: usar "to be" com adjetivos de sensação

Em português dizemos "estou com fome/frio/sono", mas em inglês essas expressões usam **to be** + adjetivo, não um verbo de "ter":

```
I am hungry.     (Estou com fome — não "I have hungry".)
I am cold.       (Estou com frio.)
I am 25 years old.   (Tenho 25 anos — de novo, "to be", não "to have".)
```
""",
            [
                ex("quiz", 'Escolha a forma correta: "She ___ a doctor."',
                   "is", ["am", "is", "are"]),
                ex("text", "Traduza: Nós somos estudantes.",
                   "we are students"),
                ex("audio", "Escute e transcreva:",
                   "i am from brazil", audio_text="I am from Brazil."),
                ex("quiz", 'Como se diz "Estou com fome" corretamente em inglês?',
                   "I am hungry.", ["I am hungry.", "I have hungry.", "I hungry."]),
            ],
        ),
        topic(
            "saudacoes-e-apresentacoes",
            "Saudações e apresentações",
            """
# Saudações e apresentações

## Cumprimentos comuns

- **Hi!** / **Hello!** — Oi! / Olá!
- **Good morning** — Bom dia
- **Good afternoon** — Boa tarde
- **Good evening** — Boa noite (ao chegar)
- **Good night** — Boa noite (ao se despedir para dormir)

## Perguntando como a pessoa está

```
How are you?          Como você está?
I'm fine, thanks.     Estou bem, obrigado(a).
And you?              E você?
```

## Se apresentando

```
My name is Ana.           Meu nome é Ana.
I'm from Brazil.          Eu sou do Brasil.
Nice to meet you.         Prazer em conhecê-lo(a).
```

> 💡 "Nice to meet you" só se usa no **primeiro encontro** com alguém. Se já se conhecem, o correto é "Nice to see you" (Bom te ver).

## Se despedindo

- **Bye!** / **Goodbye!** — Tchau! / Adeus!
- **See you later!** — Até mais!
- **See you tomorrow!** — Até amanhã!
- **Take care!** — Se cuida!
""",
            [
                ex("speak", "Diga em voz alta:",
                   "nice to meet you", audio_text="Nice to meet you."),
                ex("text", "Traduza: Muito prazer, eu sou a Ana.",
                   "nice to meet you i am ana"),
                ex("quiz", 'Qual a resposta mais natural para "How are you?"',
                   "I'm fine, thanks.", ["I'm fine, thanks.", "Nice to meet you.", "Good night.", "My name is Ana."]),
                ex("quiz", 'Qual expressão de despedida você usaria dizendo que vai ver a pessoa de novo amanhã?',
                   "See you tomorrow!", ["See you tomorrow!", "Nice to meet you!", "Good morning!"]),
            ],
        ),
        topic(
            "numeros-e-there-is-are",
            "Números e There is / There are",
            """
# Números e There is / There are

## Números de 0 a 20

0 zero · 1 one · 2 two · 3 three · 4 four · 5 five · 6 six · 7 seven · 8 eight · 9 nine · 10 ten · 11 eleven · 12 twelve · 13 thirteen · 14 fourteen · 15 fifteen · 16 sixteen · 17 seventeen · 18 eighteen · 19 nineteen · 20 twenty

## There is / There are

Usamos para dizer que algo "existe" ou "há" em algum lugar:

- **There is** + singular: `There is a book on the table.` (Há um livro na mesa.)
- **There are** + plural: `There are two cats in the garden.` (Há dois gatos no jardim.)

Na negativa: `There isn't a book here.` / `There aren't any cats here.`
Na pergunta: `Is there a book here?` / `Are there any cats here?`

## Números de dezena (20 a 100)

20 twenty · 30 thirty · 40 forty · 50 fifty · 60 sixty · 70 seventy · 80 eighty · 90 ninety · 100 one hundred

Números compostos usam hífen: `twenty-one` (21), `thirty-five` (35).
""",
            [
                ex("quiz", 'Escolha a forma correta: "There ___ two cats in the garden."',
                   "are", ["is", "are", "am"]),
                ex("text", "Traduza: Há um livro na mesa.",
                   "there is a book on the table"),
                ex("audio", "Escute e transcreva:",
                   "there are twenty students in the class", audio_text="There are twenty students in the class."),
                ex("text", "Escreva por extenso, em inglês: 21",
                   "twenty-one"),
            ],
        ),
    ],
))

# ============================================================
# MODULO 1 - Presente (A1-A2)
# ============================================================
MODULES.append(module(
    "presente-ingles",
    "Módulo 1 — Presente (A1–A2)",
    "Simple present (afirmativo, negativo, interrogativo), artigos a/an/the, plural dos substantivos, present continuous e advérbios de frequência.",
    [
        topic(
            "simple-present-afirmativo",
            "Simple Present — afirmativo",
            """
# Simple Present — afirmativo

Usamos o **simple present** para hábitos, rotinas e verdades gerais.

## Estrutura

```
I / You / We / They  +  verbo (forma base)
He / She / It        +  verbo + s
```

## Exemplos

```
I work in an office.        (Eu trabalho em um escritório.)
You play tennis.            (Você joga tênis.)
She works in an office.     (Ela trabalha em um escritório.)
He plays tennis.            (Ele joga tênis.)
```

## Regras de ortografia do -s na 3ª pessoa

| Terminação do verbo | Regra | Exemplo |
|---|---|---|
| a maioria | + s | play -> plays |
| -o, -ch, -sh, -ss, -x | + es | go -> goes, watch -> watches |
| consoante + y | tira o y, + ies | study -> studies |

> 💡 "He / She / It" **sempre** leva o -s (ou -es) no simple present afirmativo — é o erro mais comum de quem está começando.

## have é irregular

O verbo `have` (ter) não segue a regra do -s: na 3ª pessoa ele vira **has**, não "haves":

```
I have a car.        She has a car.   (não "she haves")
```
""",
            [
                ex("quiz", 'Escolha a forma correta: "She ___ (work) in a bank."',
                   "works", ["work", "works", "working"]),
                ex("text", "Traduza: Eles moram em São Paulo.",
                   "they live in sao paulo"),
                ex("audio", "Escute e transcreva:",
                   "he plays tennis on saturdays", audio_text="He plays tennis on Saturdays."),
                ex("quiz", 'Qual a forma correta de "have" na 3ª pessoa (he/she/it)?',
                   "has", ["haves", "has", "have"]),
            ],
        ),
        topic(
            "simple-present-negativo-interrogativo",
            "Simple Present — negativo e interrogativo",
            """
# Simple Present — negativo e interrogativo

Para negar ou perguntar no simple present, usamos o verbo auxiliar **do** (ou **does** para he/she/it) + o verbo principal na forma base (sem -s!).

## Negativo

```
I do not (don't) like coffee.
She does not (doesn't) like coffee.
```

## Interrogativo

```
Do you like coffee?          Yes, I do. / No, I don't.
Does she like coffee?        Yes, she does. / No, she doesn't.
```

> ⚠️ Repare: quando usamos **does**, o verbo principal **perde o -s** ("Does she like...?" e não "Does she likes...?").

## Respostas curtas (short answers)

Em inglês, respostas de sim/não raramente são só "Yes"/"No" sozinhos — soa seco/rude. O natural é repetir o auxiliar:

```
Do you like coffee?    Yes, I do.        (não apenas "Yes.")
Does he work here?     No, he doesn't.   (não apenas "No.")
```
""",
            [
                ex("quiz", 'Complete: "___ you speak English?"',
                   "Do", ["Do", "Does", "Are"]),
                ex("text", "Traduza: Ela não gosta de café.",
                   "she doesn't like coffee"),
                ex("audio", "Escute e transcreva:",
                   "does he work on sundays", audio_text="Does he work on Sundays?"),
                ex("quiz", 'Qual a resposta curta mais natural para "Does she like pizza?" (afirmativa)?',
                   "Yes, she does.", ["Yes, she does.", "Yes, she likes.", "Yes, likes."]),
            ],
        ),
        topic(
            "artigos-a-an-the",
            "Artigos: a / an / the",
            """
# Artigos: a / an / the

## a vs an

Usamos **a** antes de som de consoante e **an** antes de som de vogal (é o **som**, não a letra escrita):

```
a car, a university      ("university" começa com som de "iú", consoante)
an apple, an hour        (o H de "hour" é mudo, então soa como vogal)
```

## the

Usamos **the** quando falamos de algo **específico**, já mencionado ou único:

```
I have a dog. The dog is brown.   (Tenho um cachorro. O cachorro é marrom.)
The sun is hot.                   (O sol é quente — só existe um sol.)
```

## Sem artigo

Para ideias gerais no plural, sem especificar: `I like dogs.` (não `I like the dogs`, a menos que fale de cães específicos).

## Sem artigo também com nomes próprios e refeições

Nomes próprios (`Brazil`, `Ana`) e refeições em geral (`breakfast`, `lunch`, `dinner`) normalmente não levam artigo:

```
I have breakfast at 7 am.     (não "the breakfast")
She lives in Brazil.          (não "the Brazil")
```
""",
            [
                ex("quiz", 'Escolha o artigo correto: "___ hour"',
                   "an", ["a", "an", "the"]),
                ex("quiz", 'Escolha o artigo correto: "___ apple a day"',
                   "an", ["a", "an", "the"]),
                ex("text", "Traduza: O sol é quente.",
                   "the sun is hot"),
                ex("quiz", 'Qual frase está correta?',
                   "I have breakfast at 7 am.", ["I have breakfast at 7 am.", "I have the breakfast at 7 am.", "I have a breakfast at 7 am."]),
            ],
        ),
        topic(
            "plural-dos-substantivos",
            "Plural dos substantivos",
            """
# Plural dos substantivos

## Regra geral

`book -> books`, `car -> cars` (só adiciona **s**)

## Terminações especiais

| Terminação | Regra | Exemplo |
|---|---|---|
| -s, -x, -z, -ch, -sh | + es | bus -> buses, box -> boxes |
| consoante + y | tira o y, + ies | city -> cities |
| -f / -fe (alguns casos) | tira f/fe, + ves | knife -> knives, leaf -> leaves |

## Plurais irregulares (vale decorar)

| Singular | Plural |
|---|---|
| man | men |
| woman | women |
| child | children |
| person | people |
| foot | feet |
| tooth | teeth |
| mouse | mice |

## Substantivos que não mudam no plural

Alguns substantivos têm a mesma forma no singular e no plural — o contexto (ou um número) é que indica a quantidade:

```
one sheep, two sheep       (ovelha/ovelhas)
one fish, two fish         (peixe/peixes)
```
""",
            [
                ex("quiz", 'Qual o plural de "child"?',
                   "children", ["childs", "childes", "children"]),
                ex("text", 'Escreva o plural de "city".',
                   "cities"),
                ex("quiz", 'Qual o plural de "man"?',
                   "men", ["mans", "men", "manes"]),
                ex("quiz", 'Qual destas palavras tem a MESMA forma no singular e no plural?',
                   "sheep", ["sheep", "child", "man"]),
            ],
        ),
        topic(
            "present-continuous",
            "Present Continuous (be + verbo-ing)",
            """
# Present Continuous (be + verbo-ing)

Usamos para ações acontecendo **agora**, neste exato momento, ou planos já combinados para o futuro próximo.

## Estrutura

```
sujeito + am/is/are + verbo-ing
```

## Exemplos

```
I am studying English now.       (Estou estudando inglês agora.)
She is watching TV.              (Ela está assistindo TV.)
They are traveling next week.    (Eles vão viajar semana que vem — plano já combinado.)
```

## Regras de ortografia do -ing

| Terminação | Regra | Exemplo |
|---|---|---|
| -e mudo no final | tira o e, + ing | make -> making |
| consoante-vogal-consoante (sílaba tônica) | dobra a última consoante | run -> running, stop -> stopping |
| a maioria | + ing | play -> playing |

> 💡 Simple present = hábito ("I play tennis every week"). Present continuous = acontecendo agora ("I am playing tennis right now").

## Verbos que normalmente NÃO usam continuous

Verbos de estado/percepção (`know`, `like`, `want`, `believe`, `understand`) quase nunca aparecem no continuous, mesmo falando do momento presente:

```
I know the answer.     (não "I am knowing the answer")
I want some coffee.    (não "I am wanting some coffee")
```
""",
            [
                ex("quiz", 'Complete: "She ___ (study) right now."',
                   "is studying", ["studies", "is studying", "study"]),
                ex("text", "Traduza: Eles estão viajando agora.",
                   "they are traveling now"),
                ex("audio", "Escute e transcreva:",
                   "i am learning english", audio_text="I am learning English."),
                ex("quiz", 'Qual frase está correta?',
                   "I know the answer.", ["I know the answer.", "I am knowing the answer.", "I knowing the answer."]),
            ],
        ),
        topic(
            "adverbios-de-frequencia",
            "Advérbios de frequência",
            """
# Advérbios de frequência

Indicam com que frequência algo acontece — combinam muito com o **simple present**.

| Advérbio | Frequência aproximada | Português |
|---|---|---|
| always | 100% | sempre |
| usually | ~80% | geralmente |
| often | ~60% | frequentemente |
| sometimes | ~40% | às vezes |
| rarely / seldom | ~10% | raramente |
| never | 0% | nunca |

## Onde colocar na frase

- **Antes** do verbo principal: `I always drink coffee in the morning.`
- **Depois** do verbo **to be**: `She is never late.`

## Perguntando sobre frequência: how often

```
How often do you exercise?      Com que frequência você se exercita?
I exercise three times a week.  Eu me exercito três vezes por semana.
```
""",
            [
                ex("quiz", 'Como se diz "às vezes" em inglês?',
                   "sometimes", ["always", "sometimes", "never", "often"]),
                ex("text", "Traduza: Eu sempre bebo café de manhã.",
                   "i always drink coffee in the morning"),
                ex("quiz", "Escolha a frase com a posição correta do advérbio:",
                   "She is never late.", ["She is never late.", "She never is late.", "Never she is late."]),
                ex("text", "Traduza a pergunta: Com que frequência você se exercita?",
                   "how often do you exercise"),
            ],
        ),
    ],
))

# ============================================================
# MODULO 2 - Passado (A2)
# ============================================================
MODULES.append(module(
    "passado-ingles",
    "Módulo 2 — Passado (A2)",
    "Simple past com verbos regulares e irregulares, negativo/interrogativo com did, past continuous, there was/were e used to para hábitos passados.",
    [
        topic(
            "simple-past-verbos-regulares",
            "Simple Past — verbos regulares",
            """
# Simple Past — verbos regulares

Usamos o **simple past** para ações completamente terminadas no passado.

## Verbos regulares: + ed

```
work  -> worked
play  -> played
study -> studied   (consoante + y: tira o y, + ied)
stop  -> stopped   (consoante-vogal-consoante: dobra a consoante)
```

## Exemplos

```
I worked yesterday.          (Eu trabalhei ontem.)
She studied for the exam.    (Ela estudou para a prova.)
They played football.        (Eles jogaram futebol.)
```

> 💡 No simple past afirmativo, **todos os sujeitos usam a mesma forma** — não existe -s de 3ª pessoa como no presente.

## Como o -ed é pronunciado

A terminação -ed tem três pronúncias diferentes, dependendo do último som do verbo: /t/ depois de sons surdos (`worked`), /d/ depois de sons sonoros (`played`), e /ɪd/ depois de "t"/"d" (`wanted`, `needed`). Não é sempre "êd".
""",
            [
                ex("text", "Traduza: Eu trabalhei ontem.",
                   "i worked yesterday"),
                ex("quiz", 'Qual o passado de "study"?',
                   "studied", ["studyed", "studied", "studed"]),
                ex("audio", "Escute e transcreva:",
                   "they played football yesterday", audio_text="They played football yesterday."),
                ex("speak", "Repita em voz alta, prestando atenção na pronúncia do -ed:",
                   "wanted", audio_text="wanted"),
            ],
        ),
        topic(
            "simple-past-verbos-irregulares",
            "Simple Past — verbos irregulares",
            """
# Simple Past — verbos irregulares

Muitos verbos comuns em inglês **não seguem a regra do -ed** — precisam ser decorados aos poucos.

| Base | Passado | Português |
|---|---|---|
| go | went | ir |
| have | had | ter |
| do | did | fazer |
| see | saw | ver |
| eat | ate | comer |
| make | made | fazer/criar |
| come | came | vir |
| take | took | pegar/levar |
| write | wrote | escrever |
| be | was/were | ser/estar |

## Exemplos

```
I went to the party.        (Eu fui à festa.)
She had a great time.       (Ela se divertiu muito.)
They ate pizza last night.  (Eles comeram pizza ontem à noite.)
```

> 🎯 Dica: aprenda os irregulares mais comuns em pequenos grupos, junto com frases de exemplo — decorar a lista toda de uma vez raramente funciona.
""",
            [
                ex("quiz", 'Qual o passado de "go"?',
                   "went", ["goed", "went", "gone"]),
                ex("text", "Traduza: Ela comeu pizza ontem.",
                   "she ate pizza yesterday"),
                ex("quiz", 'Qual o passado de "see"?',
                   "saw", ["saw", "seed", "seen"]),
                ex("audio", "Escute e transcreva:",
                   "they went to the party", audio_text="They went to the party."),
            ],
        ),
        topic(
            "simple-past-negativo-interrogativo",
            "Simple Past — negativo e interrogativo",
            """
# Simple Past — negativo e interrogativo

Assim como no presente, usamos um auxiliar — no passado, é sempre **did** (para todos os sujeitos), e o verbo principal volta para a forma base.

## Negativo

```
I did not (didn't) go to the party.
She did not (didn't) see the movie.
```

## Interrogativo

```
Did you go to the party?      Yes, I did. / No, I didn't.
Did she see the movie?        Yes, she did. / No, she didn't.
```

> ⚠️ Com **did**, o verbo principal **não muda** — nem regular ("did not worked" está errado; o certo é "did not work") nem irregular ("did not went" está errado; o certo é "did not go").
""",
            [
                ex("quiz", 'Complete: "___ you go to the party?"',
                   "Did", ["Did", "Do", "Does"]),
                ex("text", "Traduza: Ela não viu o filme.",
                   "she didn't see the movie"),
                ex("quiz", "Escolha a frase correta:",
                   "She didn't go home.", ["She didn't went home.", "She didn't go home.", "She don't went home."]),
                ex("audio", "Escute e transcreva:",
                   "did you go to the party", audio_text="Did you go to the party?"),
            ],
        ),
        topic(
            "past-continuous",
            "Past Continuous (was/were + verbo-ing)",
            """
# Past Continuous (was/were + verbo-ing)

Usamos para descrever uma ação **em andamento** em um momento específico do passado — muitas vezes interrompida por outra ação.

## Estrutura

```
I / he / she / it  + was  + verbo-ing
you / we / they     + were + verbo-ing
```

## Exemplos

```
I was studying when you called.     (Eu estava estudando quando você ligou.)
They were watching TV at 9 pm.      (Eles estavam assistindo TV às 21h.)
```

É muito comum combinar **past continuous** (ação longa, em andamento) com **simple past** (ação curta, que interrompe) usando **when**:

```
I was sleeping when the phone rang.
(Eu estava dormindo quando o telefone tocou.)
```

## while vs when

**while** também introduz a ação longa (em vez de "when"), e nesse caso costuma vir no início da frase, com as duas orações no continuous:

```
While I was cooking, she was setting the table.
(Enquanto eu cozinhava, ela estava pondo a mesa.)
```
""",
            [
                ex("quiz", 'Complete: "I ___ (study) when you called."',
                   "was studying", ["studied", "was studying", "am studying"]),
                ex("text", "Traduza: Eles estavam assistindo TV.",
                   "they were watching tv"),
                ex("audio", "Escute e transcreva:",
                   "i was sleeping when the phone rang", audio_text="I was sleeping when the phone rang."),
                ex("quiz", 'Qual conector normalmente introduz a ação mais LONGA, no início da frase?',
                   "while", ["while", "when", "did"]),
            ],
        ),
        topic(
            "there-was-were-e-marcadores-de-passado",
            "There was / there were e marcadores de tempo",
            """
# There was / there were e marcadores de tempo

## There was / there were

Versão no passado de "there is/are":

```
There was a party last night.        (Houve uma festa ontem à noite.) — singular
There were many people there.        (Havia muitas pessoas lá.) — plural
```

## Marcadores de tempo comuns no passado

- **yesterday** — ontem
- **last night / last week / last year** — ontem à noite / semana passada / ano passado
- **... ago** — atrás (`two days ago` = dois dias atrás)
- **in 2010** — em 2010

> 💡 Esses marcadores são uma ótima pista para saber que a frase deve estar no passado.
""",
            [
                ex("quiz", 'Complete: "There ___ many people at the party."',
                   "were", ["was", "were"]),
                ex("text", "Traduza: Havia uma festa ontem à noite.",
                   "there was a party last night"),
                ex("quiz", 'Como se diz "dois dias atrás"?',
                   "two days ago", ["two days ago", "two days last", "ago two days"]),
                ex("audio", "Escute e transcreva:",
                   "there were many people there", audio_text="There were many people there."),
            ],
        ),
        topic(
            "used-to-habitos-passados",
            "used to para hábitos passados",
            """
# used to para hábitos passados

**used to** + verbo (forma base) descreve um hábito ou estado que era verdade no passado, mas **não é mais** — algo que mudou.

## Estrutura

```
sujeito + used to + verbo (forma base)      (used to não muda com a pessoa)
```

## Exemplos

```
I used to play football every weekend.    (Eu costumava jogar futebol todo fim de semana — não jogo mais.)
She used to live in London.               (Ela costumava morar em Londres — não mora mais.)
There used to be a cinema here.           (Costumava haver um cinema aqui.)
```

## Negativo e interrogativo

Usa-se **did** (como no simple past), e "used" volta para "use":

```
I didn't use to like vegetables.      (Eu não costumava gostar de vegetais.)
Did you use to play football?         (Você costumava jogar futebol?)
```

> ⚠️ Não confunda com "be used to" (estar acostumado com algo, que continua verdade hoje) — "used to" sozinho é sempre sobre um hábito do **passado que já acabou**.
""",
            [
                ex("quiz", 'O que "used to" indica?',
                   "um hábito do passado que não é mais verdade", ["um hábito do passado que não é mais verdade", "uma ação acontecendo agora", "um plano para o futuro"]),
                ex("text", "Traduza: Ela costumava morar em Londres.",
                   "she used to live in london"),
                ex("quiz", 'Como fica "used to" na negativa?',
                   "didn't use to", ["didn't use to", "usedn't to", "don't used to"]),
                ex("audio", "Escute e transcreva:",
                   "i used to play football every weekend", audio_text="I used to play football every weekend."),
            ],
        ),
    ],
))

# ============================================================
# MODULO 3 - Futuro e Modais (A2-B1)
# ============================================================
MODULES.append(module(
    "futuro-e-modais-ingles",
    "Módulo 3 — Futuro e Modais (A2–B1)",
    "Going to e will para o futuro, e os verbos modais can/could, must/have to, should e may/might.",
    [
        topic(
            "futuro-going-to",
            "Futuro com going to",
            """
# Futuro com going to

Usamos **going to** para planos e intenções já decididas, ou previsões baseadas em algo que vemos agora.

## Estrutura

```
sujeito + am/is/are + going to + verbo (forma base)
```

## Exemplos

```
I am going to travel next month.            (Eu vou viajar mês que vem — já é um plano.)
Look at those clouds! It's going to rain.   (Vai chover — dá para ver pelas nuvens agora.)
```

Negativo: `I am not going to travel.` Interrogativo: `Are you going to travel?`

## Na fala informal: "gonna"

Em inglês falado (não na escrita formal), "going to" costuma ser pronunciado/escrito como **gonna**: `I'm gonna travel next month.` Vale reconhecer ao ouvir, mas prefira escrever "going to" em contextos formais.
""",
            [
                ex("quiz", 'Complete: "Look at the sky! It ___ to rain."',
                   "is going", ["is going", "will", "goes"]),
                ex("text", "Traduza: Eu vou estudar inglês amanhã.",
                   "i am going to study english tomorrow"),
                ex("audio", "Escute e transcreva:",
                   "we are going to visit my grandmother", audio_text="We are going to visit my grandmother."),
                ex("quiz", 'Como "going to" costuma soar na fala informal?',
                   "gonna", ["gonna", "gona", "goingto"]),
            ],
        ),
        topic(
            "futuro-will",
            "Futuro com will",
            """
# Futuro com will

Usamos **will** para decisões espontâneas (tomadas na hora), promessas, previsões sem evidência concreta, e ofertas.

## Estrutura

```
sujeito + will + verbo (forma base)      (will não muda com a pessoa)
```

## Exemplos

```
I think it will rain tomorrow.     (previsão/opinião, sem evidência)
I'll help you with that.           (decisão espontânea / oferta)
She will call you later.           (promessa)
```

Contração: **will -> 'll** (`I'll`, `she'll`, `they'll`). Negativo: **will not -> won't**.

## going to vs will

| going to | will |
|---|---|
| plano já decidido | decisão tomada na hora |
| evidência visível agora | opinião/previsão sem evidência |
""",
            [
                ex("quiz", "Escolha a frase de uma decisão espontânea, tomada na hora:",
                   "I'll answer the phone.", ["I'll answer the phone.", "I am going to answer the phone.", "I answer the phone."]),
                ex("text", "Traduza: Ela vai te ligar mais tarde.",
                   "she will call you later"),
                # "wont" nao pode ser alternativa: o corretor ignora apostrofos,
                # entao "wont" e "won't" ficariam ambos certos.
                ex("quiz", 'Qual é a contração de "will not"?',
                   "won't", ["won't", "willn't", "willnot"]),
                ex("audio", "Escute e transcreva:",
                   "i think it will rain tomorrow", audio_text="I think it will rain tomorrow."),
            ],
        ),
        topic(
            "modais-can-could",
            "Modais: can e could",
            """
# Modais: can e could

## can

Indica **habilidade** (saber fazer) ou **permissão informal**:

```
I can swim.               (Eu sei nadar / consigo nadar.)
Can I open the window?    (Posso abrir a janela?)
```

## could

É o passado de "can" (habilidade no passado) e também uma forma **mais educada** de pedir algo:

```
When I was a child, I could run very fast.   (habilidade no passado)
Could you help me, please?                   (pedido educado)
```

> 💡 Verbos modais (can, could, will, must...) **nunca** levam -s na 3ª pessoa e são sempre seguidos do verbo na forma base, sem "to": `She can swim` (não `She can to swim` nem `She cans swim`).
""",
            [
                ex("quiz", 'Complete: "She ___ speak three languages."',
                   "can", ["can", "cans", "canning"]),
                ex("text", "Traduza: Você poderia me ajudar, por favor?",
                   "could you help me please"),
                ex("quiz", "Qual modal indica habilidade no PASSADO?",
                   "could", ["can", "could", "will"]),
                ex("audio", "Escute e transcreva:",
                   "can i open the window", audio_text="Can I open the window?"),
            ],
        ),
        topic(
            "modais-must-have-to",
            "Modais: must e have to",
            """
# Modais: must e have to

Ambos expressam **obrigação**, mas com uma diferença sutil:

- **must**: obrigação que vem de quem fala (opinião pessoal) ou regra muito forte: `You must wear a seatbelt.` (é lei/regra)
- **have to**: obrigação que vem de fora (regras, circunstâncias externas): `I have to work on Saturday.` (meu chefe pediu, não é minha opinião)

## Negativo — atenção, o significado muda!

- **must not (mustn't)**: proibição, "não pode": `You mustn't smoke here.` (é proibido)
- **don't have to**: não é necessário, mas pode se quiser: `You don't have to come if you're tired.` (você não é obrigado)

> ⚠️ Esse é um dos erros mais comuns de quem estuda inglês: "mustn't" e "don't have to" **não** são sinônimos!
""",
            [
                ex("quiz", 'Qual frase significa "é proibido"?',
                   "You mustn't smoke here.", ["You mustn't smoke here.", "You don't have to smoke here.", "You can smoke here."]),
                ex("text", "Traduza: Eu tenho que trabalhar no sábado.",
                   "i have to work on saturday"),
                ex("quiz", 'Qual frase significa "não é obrigatório, mas pode se quiser"?',
                   "You don't have to come.", ["You mustn't come.", "You don't have to come.", "You must come."]),
                ex("audio", "Escute e transcreva:",
                   "you must wear a seatbelt", audio_text="You must wear a seatbelt."),
            ],
        ),
        topic(
            "modais-should-may-might",
            "Modais: should, may e might",
            """
# Modais: should, may e might

## should

Usado para **conselhos e recomendações** ("deveria"):

```
You should study more.             (Você deveria estudar mais.)
You shouldn't eat so much sugar.   (Você não deveria comer tanto açúcar.)
```

## may / might

Usados para **possibilidade** ("pode ser que"), sendo *might* uma possibilidade um pouco menor que *may*:

```
It may rain later.        (Pode ser que chova mais tarde.)
She might be at home.     (Ela pode estar em casa — não tenho certeza.)
```

**may** também é usado para pedir permissão de forma bem formal: `May I come in?` (Posso entrar?)
""",
            [
                ex("quiz", "Qual modal expressa um CONSELHO?",
                   "should", ["can", "should", "must"]),
                ex("text", "Traduza: Pode ser que chova mais tarde.",
                   "it may rain later"),
                ex("quiz", 'Complete de forma educada e formal: "___ I come in?"',
                   "May", ["Can", "May", "Must"]),
                ex("audio", "Escute e transcreva:",
                   "you should study more", audio_text="You should study more."),
            ],
        ),
    ],
))

# ============================================================
# MODULO 4 - Comparacoes e Preposicoes (B1)
# ============================================================
MODULES.append(module(
    "comparacoes-e-preposicoes-ingles",
    "Módulo 4 — Comparações e Preposições (B1)",
    "Comparativo e superlativo, comparações de igualdade, preposições de tempo e lugar, quantificadores e gerúndio vs infinitivo.",
    [
        topic(
            "comparativo-e-superlativo",
            "Comparativo e superlativo",
            """
# Comparativo e superlativo

## Adjetivos curtos (geralmente 1 sílaba)

```
tall -> taller (comparativo) -> the tallest (superlativo)
big  -> bigger  -> the biggest    (dobra a consoante final)
```

## Adjetivos longos (geralmente 2+ sílabas)

```
expensive   -> more expensive   -> the most expensive
interesting -> more interesting -> the most interesting
```

## Irregulares (vale decorar)

| Adjetivo | Comparativo | Superlativo |
|---|---|---|
| good | better | the best |
| bad | worse | the worst |
| far | farther/further | the farthest/furthest |

## Exemplos

```
This car is faster than that one.                 (comparativo: + than)
This is the most expensive restaurant in town.    (superlativo: the + most/-est)
```

## Adjetivos de 2 sílabas terminados em -y

Ficam no "meio do caminho": seguem a regra dos curtos, trocando -y por -ier/-iest: `happy -> happier -> the happiest`.
""",
            [
                ex("quiz", 'Qual o comparativo de "big"?',
                   "bigger", ["bigger", "more big", "biggest"]),
                ex("text", "Traduza: Este carro é mais rápido que aquele.",
                   "this car is faster than that one"),
                ex("quiz", 'Qual o superlativo de "good"?',
                   "the best", ["goodest", "the best", "more good"]),
                ex("quiz", 'Qual o comparativo de "happy" (2 sílabas, termina em -y)?',
                   "happier", ["happier", "more happy", "happyer"]),
            ],
        ),
        topic(
            "as-as-comparacoes-de-igualdade",
            "Comparações de igualdade: as...as",
            """
# Comparações de igualdade: as...as

Usamos **as + adjetivo + as** para dizer que duas coisas são iguais em alguma característica:

```
She is as tall as her brother.              (Ela é tão alta quanto o irmão.)
This book is as interesting as the movie.   (Este livro é tão interessante quanto o filme.)
```

Na negativa, **not as...as** indica que uma coisa é menos do que a outra:

```
This city is not as big as São Paulo.   (Esta cidade não é tão grande quanto São Paulo.)
```

## twice as...as, três vezes, etc.

Também dá para especificar a proporção com "twice"/"three times" + as...as:

```
This house is twice as big as mine.     (Esta casa é duas vezes maior que a minha.)
```
""",
            [
                ex("text", "Traduza: Ela é tão alta quanto o irmão.",
                   "she is as tall as her brother"),
                ex("quiz", 'Complete: "This city is not ___ big as São Paulo."',
                   "as", ["as", "than", "so"]),
                ex("audio", "Escute e transcreva:",
                   "this book is as interesting as the movie", audio_text="This book is as interesting as the movie."),
                ex("text", "Traduza: Esta casa é duas vezes maior que a minha.",
                   "this house is twice as big as mine"),
            ],
        ),
        topic(
            "preposicoes-de-tempo-in-on-at",
            "Preposições de tempo: in, on, at",
            """
# Preposições de tempo: in, on, at

| Preposição | Uso | Exemplo |
|---|---|---|
| **in** | meses, anos, estações, períodos longos | in July, in 2024, in the morning |
| **on** | dias e datas | on Monday, on July 4th |
| **at** | horários específicos | at 7 pm, at noon |

## Exemplos

```
My birthday is in July.
I have a meeting on Monday.
The class starts at 8 am.
```

> 💡 Truque para lembrar: **in** (período mais vago/longo) -> **on** (dia específico) -> **at** (hora exata) — do mais geral para o mais específico.

## Exceções que vale decorar

Algumas expressões fixas fogem da regra geral: `at night` (à noite, não "in the night"), `on time` (na hora certa), `in time` (a tempo, com folga).
""",
            [
                ex("quiz", 'Complete: "My birthday is ___ July."',
                   "in", ["in", "on", "at"]),
                ex("quiz", 'Complete: "The meeting is ___ Monday."',
                   "on", ["in", "on", "at"]),
                ex("text", "Traduza: A aula começa às 8 da manhã.",
                   "the class starts at 8 am"),
                ex("quiz", 'Como se diz "à noite" (expressão fixa, exceção à regra)?',
                   "at night", ["at night", "in the night", "on night"]),
            ],
        ),
        topic(
            "preposicoes-de-lugar",
            "Preposições de lugar: in, on, at",
            """
# Preposições de lugar: in, on, at

| Preposição | Uso | Exemplo |
|---|---|---|
| **in** | dentro de um espaço/área | in the box, in London, in the room |
| **on** | sobre uma superfície | on the table, on the wall |
| **at** | um ponto/local específico | at the door, at the bus stop, at home |

## Exemplos

```
The keys are in the box.
The picture is on the wall.
She is waiting at the bus stop.
```

## in/on/at com cidades, países e endereços

Para lugares maiores (país, cidade), usa-se **in**: `in Brazil`, `in São Paulo`. Para um endereço com número específico, usa-se **at**: `at 25 Baker Street`. Repare que a mesma lógica "geral -> específico" das preposições de tempo vale aqui também.
""",
            [
                ex("quiz", 'Complete: "The keys are ___ the box."',
                   "in", ["in", "on", "at"]),
                ex("quiz", 'Complete: "The picture is ___ the wall."',
                   "on", ["in", "on", "at"]),
                ex("text", "Traduza: Ela está esperando no ponto de ônibus.",
                   "she is waiting at the bus stop"),
                ex("quiz", 'Qual preposição se usa com um endereço específico (número da rua)?',
                   "at", ["in", "on", "at"]),
            ],
        ),
        topic(
            "quantificadores-some-any-much-many",
            "Quantificadores: some, any, much, many",
            """
# Quantificadores: some, any, much, many, a lot of

## some e any

- **some**: frases afirmativas — `I have some money.`
- **any**: frases negativas e perguntas — `I don't have any money.` / `Do you have any money?`

## much e many

- **much**: substantivos incontáveis (água, dinheiro, tempo) — `How much water do you drink?`
- **many**: substantivos contáveis (carros, livros, amigos) — `How many books do you have?`

## a lot of

Funciona para os dois casos, principalmente em frases afirmativas: `I have a lot of friends.` / `I have a lot of money.`

> 💡 Pergunta rápida para saber se é contável: dá para colocar um número na frente? "three books" sim (contável -> many); "three waters" não (incontável -> much).

## a few vs a little

Para quantidades pequenas, mas positivas ("um pouco/alguns"): **a few** + contável (`a few friends`), **a little** + incontável (`a little water`). Sem o "a", "few"/"little" sozinhos soam negativos ("quase nenhum").
""",
            [
                ex("quiz", 'Complete: "How ___ water do you drink?"',
                   "much", ["much", "many"]),
                ex("quiz", 'Complete: "How ___ books do you have?"',
                   "many", ["much", "many"]),
                ex("text", "Traduza: Eu tenho muitos amigos.",
                   "i have a lot of friends"),
                ex("quiz", 'Qual quantificador combina com substantivo INCONTÁVEL (ex: água)?',
                   "a little", ["a few", "a little", "many"]),
            ],
        ),
        topic(
            "gerundios-vs-infinitivos",
            "Gerúndio (-ing) vs infinitivo (to + verbo)",
            """
# Gerúndio (-ing) vs infinitivo (to + verbo)

Depois de certos verbos, o segundo verbo da frase deve ir no **gerúndio** (verb-ing); depois de outros, no **infinitivo** (to + verbo). Não é uma escolha livre — cada verbo "exige" uma forma, e isso precisa ser decorado caso a caso.

## Verbos seguidos de gerúndio (-ing)

```
enjoy, finish, avoid, suggest, mind, keep, imagine

I enjoy reading books.        (Eu gosto de ler livros.)
She finished studying.        (Ela terminou de estudar.)
```

## Verbos seguidos de infinitivo (to + verbo)

```
want, need, decide, plan, hope, promise, learn

I want to travel.             (Eu quero viajar.)
She decided to study medicine. (Ela decidiu estudar medicina.)
```

## Alguns aceitam os dois, com sentidos diferentes

```
I stopped smoking.       (Eu parei de fumar — parei o hábito.)
I stopped to smoke.      (Eu parei [o que estava fazendo] para fumar.)
```

> ⚠️ Não existe atalho: a melhor forma de aprender é memorizar cada verbo novo já junto com a forma que ele pede, como parte do vocabulário.
""",
            [
                ex("quiz", 'Complete: "I enjoy ___ (read) books."',
                   "reading", ["reading", "to read", "read"]),
                ex("text", "Traduza: Eu quero viajar.",
                   "i want to travel"),
                ex("quiz", 'Qual verbo é normalmente seguido de INFINITIVO (to + verbo)?',
                   "decide", ["enjoy", "avoid", "decide"]),
                ex("quiz", 'Qual a diferença entre "I stopped smoking" e "I stopped to smoke"?',
                   '"stopped smoking" = parei o hábito; "stopped to smoke" = parei algo para fumar',
                   ['"stopped smoking" = parei o hábito; "stopped to smoke" = parei algo para fumar', "são exatamente iguais", '"stopped to smoke" não existe em inglês']),
            ],
        ),
    ],
))

# ============================================================
# MODULO 5 - Perfect Tenses (B1-B2)
# ============================================================
MODULES.append(module(
    "perfect-tenses-ingles",
    "Módulo 5 — Perfect Tenses (B1–B2)",
    "Present perfect (ever/never/already/yet/just), present perfect vs simple past, present perfect continuous e past perfect.",
    [
        topic(
            "present-perfect-ever-never",
            "Present Perfect: ever e never",
            """
# Present Perfect (have/has + particípio)

Usamos o **present perfect** para falar de experiências de vida, sem dizer exatamente quando aconteceram — o foco é no resultado/experiência, não no momento exato.

## Estrutura

```
I / you / we / they  +  have  +  particípio
he / she / it         +  has   +  particípio
```

`have` -> `'ve`, `has` -> `'s` nas contrações.

## ever e never

- **ever** ("alguma vez"): usado em perguntas — `Have you ever been to Japan?`
- **never** ("nunca"): usado em afirmações negativas — `I have never been to Japan.`

## Exemplos

```
Have you ever eaten sushi?        Yes, I have. / No, I haven't.
She has never seen snow.
```

> 💡 O particípio de verbos regulares é igual ao passado (+ed): `worked`. Verbos irregulares têm uma 3ª forma própria: `go -> went -> gone`, `see -> saw -> seen`, `eat -> ate -> eaten`.
""",
            [
                ex("quiz", 'Complete: "Have you ___ been to Japan?"',
                   "ever", ["ever", "never", "yet"]),
                ex("text", "Traduza: Ela nunca viu neve.",
                   "she has never seen snow"),
                ex("audio", "Escute e transcreva:",
                   "have you ever eaten sushi", audio_text="Have you ever eaten sushi?"),
                ex("quiz", 'Qual o particípio de "go" (usado no present perfect)?',
                   "gone", ["gone", "went", "going"]),
            ],
        ),
        topic(
            "present-perfect-already-yet-just",
            "Present Perfect: already, yet e just",
            """
# Present Perfect: already, yet e just

## already ("já")

Usado em frases **afirmativas**, geralmente indicando que algo aconteceu antes do esperado:

```
I have already finished my homework.   (Eu já terminei minha lição de casa.)
```

## yet ("ainda"/"já")

Usado em **negativas** ("ainda não") e **perguntas** ("já...?"), sempre no final da frase:

```
I haven't finished my homework yet.    (Eu ainda não terminei.)
Have you finished your homework yet?   (Você já terminou?)
```

## just ("acabou de")

Indica que algo aconteceu há muito pouco tempo:

```
She has just arrived.    (Ela acabou de chegar.)
```

## Posição de already e just na frase

Diferente de "yet" (que vai no final), **already** e **just** normalmente ficam **entre** o auxiliar (have/has) e o particípio: `I have already finished`, não `I have finished already` (essa segunda ordem também existe, mas é menos comum).
""",
            [
                ex("quiz", "Qual palavra vai em frases NEGATIVAS/perguntas, sempre no final?",
                   "yet", ["already", "yet", "just"]),
                ex("text", "Traduza: Eu já terminei minha lição de casa.",
                   "i have already finished my homework"),
                ex("quiz", 'Complete: "She has ___ arrived." (acabou de)',
                   "just", ["already", "yet", "just"]),
                ex("audio", "Escute e transcreva:",
                   "i haven't finished my homework yet", audio_text="I haven't finished my homework yet."),
            ],
        ),
        topic(
            "present-perfect-vs-simple-past",
            "Present Perfect vs Simple Past",
            """
# Present Perfect vs Simple Past

Esse é um dos pontos que mais confunde quem fala português, porque no Brasil costumamos usar só uma forma de passado.

| Simple Past | Present Perfect |
|---|---|
| tempo específico e terminado | experiência, sem tempo específico |
| `I visited Paris in 2019.` | `I have visited Paris.` (alguma vez, não importa quando) |
| usa marcadores como *yesterday*, *last year*, *in 2019* | usa marcadores como *ever*, *never*, *already*, *yet*, *just* |

## Exemplos lado a lado

```
I saw that movie last week.       (passado específico -> simple past)
I have seen that movie.           (experiência, sem dizer quando -> present perfect)
```

> ⚠️ Se a frase tem uma data ou tempo específico (yesterday, in 2020, last week), use **simple past**. Se fala de experiência de vida sem hora marcada, use **present perfect**.
""",
            [
                ex("quiz", 'Complete: "I ___ that movie last week."',
                   "saw", ["saw", "have seen"]),
                ex("quiz", 'Complete (experiência, sem dizer quando): "I ___ that movie."',
                   "have seen", ["saw", "have seen"]),
                ex("text", "Traduza: Eu visitei Paris em 2019.",
                   "i visited paris in 2019"),
                ex("quiz", 'Qual pista na frase indica que se deve usar SIMPLE PAST em vez de present perfect?',
                   "uma data ou tempo específico, como \"last week\"", ["uma data ou tempo específico, como \"last week\"", "a palavra \"ever\"", "a palavra \"never\""]),
            ],
        ),
        topic(
            "present-perfect-continuous",
            "Present Perfect Continuous",
            """
# Present Perfect Continuous

Usamos para enfatizar a **duração** de uma ação que começou no passado e continua até agora.

## Estrutura

```
sujeito + have/has + been + verbo-ing
```

## Exemplos

```
I have been studying English for two years.     (Estudo inglês há dois anos — e continuo.)
She has been working here since 2020.           (Ela trabalha aqui desde 2020.)
```

## for vs since

- **for** + duração: `for two years`, `for a week`
- **since** + ponto no tempo: `since 2020`, `since Monday`
""",
            [
                ex("quiz", 'Complete: "I have been studying English ___ two years."',
                   "for", ["for", "since"]),
                ex("quiz", 'Complete: "She has worked here ___ 2020."',
                   "since", ["for", "since"]),
                ex("text", "Traduza: Ela trabalha aqui desde 2020.",
                   "she has been working here since 2020"),
                ex("audio", "Escute e transcreva:",
                   "i have been studying english for two years", audio_text="I have been studying English for two years."),
            ],
        ),
        topic(
            "past-perfect",
            "Past Perfect (had + particípio)",
            """
# Past Perfect (had + particípio)

Usamos para indicar que uma ação aconteceu **antes de outra ação no passado** — é o "passado do passado".

## Estrutura

```
sujeito + had + particípio
```

## Exemplo

```
When I arrived, the movie had already started.
(Quando eu cheguei, o filme já tinha começado.)
```

Repare na ordem dos eventos: **1)** o filme começou, **2)** depois eu cheguei. A ação que aconteceu primeiro (começar o filme) usa **had + particípio**; a segunda usa **simple past** (`arrived`).

> 💡 Se só há uma ação no passado, geralmente o simple past já basta. Use o past perfect quando precisar deixar claro **qual ação aconteceu primeiro**, entre duas.
""",
            [
                ex("text", "Traduza: Quando eu cheguei, o filme já tinha começado.",
                   "when i arrived the movie had already started"),
                ex("quiz", "Qual forma verbal indica a ação que aconteceu PRIMEIRO, entre duas no passado?",
                   "had + particípio", ["simple past", "had + particípio"]),
                ex("audio", "Escute e transcreva:",
                   "she had already left when i called", audio_text="She had already left when I called."),
                ex("quiz", 'Se há apenas UMA ação no passado (sem comparar com outra), qual tempo geralmente já basta?',
                   "simple past", ["simple past", "past perfect", "present perfect"]),
            ],
        ),
    ],
))

# ============================================================
# MODULO 6 - Voz Passiva e Condicionais (B2)
# ============================================================
MODULES.append(module(
    "voz-passiva-e-condicionais-ingles",
    "Módulo 6 — Voz Passiva e Condicionais (B2)",
    "Voz passiva no presente e no passado, e os condicionais tipo 0, 1, 2 e 3.",
    [
        topic(
            "voz-passiva-presente",
            "Voz Passiva no presente",
            """
# Voz Passiva no presente

Usamos a voz passiva quando o **foco é na ação ou em quem recebe a ação**, não em quem a pratica.

## Estrutura

```
sujeito + am/is/are + particípio  (+ by + agente, opcional)
```

## Ativa vs Passiva

```
Ativa:   The company makes these cars.         (A empresa faz esses carros.)
Passiva: These cars are made by the company.   (Esses carros são feitos pela empresa.)
```

Quando não importa (ou não se sabe) quem pratica a ação, o "by + agente" pode ser omitido:

```
English is spoken in many countries.   (O inglês é falado em muitos países.)
```
""",
            [
                ex("quiz", 'Complete: "These cars ___ made in Germany."',
                   "are", ["is", "are", "am"]),
                ex("text", "Traduza: O inglês é falado em muitos países.",
                   "english is spoken in many countries"),
                ex("audio", "Escute e transcreva:",
                   "this coffee is grown in brazil", audio_text="This coffee is grown in Brazil."),
                ex("quiz", 'Na frase passiva, quando o "by + agente" costuma ser OMITIDO?',
                   "quando não importa ou não se sabe quem pratica a ação", ["quando não importa ou não se sabe quem pratica a ação", "sempre, nunca se usa \"by\"", "só nas perguntas"]),
            ],
        ),
        topic(
            "voz-passiva-passado",
            "Voz Passiva no passado",
            """
# Voz Passiva no passado

## Estrutura

```
sujeito + was/were + particípio
```

## Exemplos

```
Ativa:   Shakespeare wrote this play.            (Shakespeare escreveu esta peça.)
Passiva: This play was written by Shakespeare.   (Esta peça foi escrita por Shakespeare.)
```

```
The windows were broken last night.   (As janelas foram quebradas ontem à noite.)
```

> 💡 A voz passiva é muito usada em notícias, relatórios científicos e textos formais — quando o importante é o fato, não quem fez.
""",
            [
                ex("quiz", 'Complete: "This play ___ written by Shakespeare."',
                   "was", ["was", "were"]),
                ex("text", "Traduza: As janelas foram quebradas ontem à noite.",
                   "the windows were broken last night"),
                ex("quiz", 'Escolha a versão passiva de "Someone stole my bike."',
                   "My bike was stolen.", ["My bike was stolen.", "My bike stole.", "My bike is stole."]),
                ex("audio", "Escute e transcreva:",
                   "this play was written by shakespeare", audio_text="This play was written by Shakespeare."),
            ],
        ),
        topic(
            "condicional-zero-e-primeiro",
            "Condicionais tipo 0 e tipo 1",
            """
# Condicionais: tipo 0 e tipo 1

## Condicional tipo 0 — verdades gerais

```
If + simple present, simple present
```

```
If you heat water to 100°C, it boils.
(Se você aquece a água a 100°C, ela ferve — sempre verdade.)
```

## Condicional tipo 1 — situações reais/possíveis no futuro

```
If + simple present, will + verbo
```

```
If it rains tomorrow, I will stay home.
(Se chover amanhã, eu vou ficar em casa.)
```

## Invertendo a ordem das orações

As duas ordens funcionam, mudando só a pontuação: com "if" no início, usa-se vírgula antes da segunda oração; com "if" no meio, não:

```
If it rains, I will stay home.
I will stay home if it rains.     (sem vírgula)
```
""",
            [
                ex("quiz", 'Condicional tipo 0: "If you heat water to 100°C, it ___."',
                   "boils", ["boils", "will boil", "boiled"]),
                ex("text", "Traduza: Se chover amanhã, eu vou ficar em casa.",
                   "if it rains tomorrow i will stay home"),
                ex("quiz", "Qual condicional descreve uma verdade geral/científica?",
                   "tipo 0", ["tipo 0", "tipo 1"]),
                ex("quiz", 'Quando "if" vem no MEIO da frase (depois da oração principal), usa-se vírgula antes dele?',
                   "Não", ["Não", "Sim, sempre", "Só em perguntas"]),
            ],
        ),
        topic(
            "condicional-segundo",
            "Condicional tipo 2",
            """
# Condicional tipo 2 — situações hipotéticas/improváveis

## Estrutura

```
If + simple past, would + verbo
```

## Exemplo

```
If I won the lottery, I would travel around the world.
(Se eu ganhasse na loteria, eu viajaria pelo mundo — hipotético, pouco provável.)
```

> ⚠️ Repare: apesar de usar o "simple past" (`won`), a frase **não fala do passado** — é uma situação hipotética no presente/futuro. Isso confunde muita gente!

Com o verbo **to be**, o mais comum (e mais formal) é usar **were** para todos os sujeitos: `If I were you, I would study more.` (Se eu fosse você, estudaria mais.)
""",
            [
                ex("quiz", 'Complete: "If I ___ you, I would study more."',
                   "were", ["was", "were"]),
                ex("text", "Traduza: Se eu ganhasse na loteria, eu viajaria pelo mundo.",
                   "if i won the lottery i would travel around the world"),
                ex("quiz", "Qual condicional descreve uma situação hipotética/pouco provável no presente?",
                   "tipo 2", ["tipo 1", "tipo 2", "tipo 3"]),
                ex("audio", "Escute e transcreva:",
                   "if i were you i would study more", audio_text="If I were you, I would study more."),
            ],
        ),
        topic(
            "condicional-terceiro",
            "Condicional tipo 3",
            """
# Condicional tipo 3 — passado hipotético (arrependimento)

Usado para falar de situações que **não aconteceram no passado** — muito comum para expressar arrependimento ou críticas.

## Estrutura

```
If + past perfect, would have + particípio
```

## Exemplo

```
If I had studied more, I would have passed the exam.
(Se eu tivesse estudado mais, eu teria passado na prova.)
```

A realidade é o oposto: eu **não estudei** e **não passei**. O condicional tipo 3 sempre fala de algo que já não tem mais solução — só serve para refletir sobre o passado.
""",
            [
                ex("text", "Traduza: Se eu tivesse estudado mais, eu teria passado na prova.",
                   "if i had studied more i would have passed the exam"),
                ex("quiz", "O condicional tipo 3 fala de:",
                   "passado que não aconteceu (arrependimento)", ["futuro possível", "situação hipotética no presente", "passado que não aconteceu (arrependimento)"]),
                ex("audio", "Escute e transcreva:",
                   "if i had known i would have called you", audio_text="If I had known, I would have called you."),
                ex("quiz", 'Na frase "If I had studied more, I would have passed the exam", o que realmente aconteceu?',
                   "A pessoa não estudou o suficiente e não passou", ["A pessoa não estudou o suficiente e não passou", "A pessoa estudou e passou", "Não dá para saber"]),
            ],
        ),
    ],
))

# ============================================================
# MODULO 7 - Discurso Indireto e Coesao (B2-C1)
# ============================================================
MODULES.append(module(
    "discurso-indireto-e-coesao-ingles",
    "Módulo 7 — Discurso Indireto e Coesão (B2–C1)",
    "Reported speech (afirmações, perguntas e ordens), phrasal verbs comuns e linking words para textos coesos.",
    [
        topic(
            "reported-speech-afirmacoes",
            "Reported Speech — afirmações",
            """
# Reported Speech — afirmações

Usamos o **discurso indireto** (reported speech) para contar o que outra pessoa disse, sem citar as palavras exatas entre aspas. Quando o verbo introdutório está no passado (`said`), os tempos verbais da frase original geralmente **voltam um passo** (backshift):

| Discurso direto | Discurso indireto |
|---|---|
| "I am tired," she said. | She said (that) she was tired. |
| "I work here," he said. | He said (that) he worked here. |
| "I will call you," she said. | She said (that) she would call me. |
| "I have finished," he said. | He said (that) he had finished. |

## Outras mudanças comuns

- Pronomes mudam de acordo com quem conta a história: `I` -> `she/he`.
- Expressões de tempo/lugar também mudam: `today` -> `that day`, `here` -> `there`, `tomorrow` -> `the next day`.

## "that" é opcional

A palavra "that" depois de "said" pode ser omitida sem mudar o sentido — é só uma questão de estilo, mais comum omitir na fala: `She said she was tired.` = `She said that she was tired.`
""",
            [
                ex("quiz", '"I am tired," she said. -> She said (that) she ___ tired.',
                   "was", ["is", "was", "were"]),
                ex("text", "Transforme para o discurso indireto: \"I work here,\" he said.",
                   "he said that he worked here"),
                ex("quiz", "Qual é a versão em discurso indireto de: \"I have finished,\" he said?",
                   "He said that he had finished.", ["He said that he has finished.", "He said that he had finished.", "He said that he finished."]),
                ex("quiz", 'A palavra "that" depois de "said" é obrigatória?',
                   "Não, é opcional", ["Não, é opcional", "Sim, sempre obrigatória", "Só em perguntas"]),
            ],
        ),
        topic(
            "reported-speech-perguntas",
            "Reported Speech — perguntas e ordens",
            """
# Reported Speech — perguntas e ordens

Para relatar perguntas, também aplicamos o backshift dos tempos verbais, mas a estrutura da frase muda: **não usamos a ordem de pergunta** (sem inverter o auxiliar) e não usamos ponto de interrogação.

## Perguntas com palavra interrogativa (what, where, when...)

```
"Where do you live?" she asked.  ->  She asked where I lived.
```

## Perguntas de sim/não (yes/no questions)

Usamos **if** ou **whether**:

```
"Do you like coffee?" he asked.  ->  He asked if I liked coffee.
```

> ⚠️ Repare: a ordem volta a ser afirmativa ("I lived", não "did I live") — manter a estrutura de pergunta no discurso indireto é um erro muito comum.

## Ordens e pedidos: tell/ask + to + verbo

Para relatar uma ordem ou pedido (imperativo no original), usa-se **tell/ask + pessoa + to + verbo**:

```
"Close the door," she said.       ->  She told me to close the door.
"Please help me," he said.        ->  He asked me to help him.
```
""",
            [
                ex("quiz", '"Where do you live?" she asked. -> She asked ___ I lived.',
                   "where", ["where", "if", "that"]),
                ex("text", "Transforme: \"Do you like coffee?\" he asked.",
                   "he asked if i liked coffee"),
                ex("quiz", "Qual estrutura é usada para perguntas de sim/não no discurso indireto?",
                   "if/whether + ordem afirmativa", ["what/where + ordem afirmativa", "if/whether + ordem afirmativa", "ordem de pergunta normal"]),
                ex("text", "Transforme uma ordem para discurso indireto: \"Close the door,\" she said. (she + told + me + to + close + the door)",
                   "she told me to close the door"),
            ],
        ),
        topic(
            "phrasal-verbs-comuns",
            "Phrasal Verbs comuns",
            """
# Phrasal Verbs comuns

Phrasal verbs são combinações de verbo + partícula (preposição/advérbio) que criam um significado próprio — muitas vezes bem diferente do verbo sozinho.

| Phrasal verb | Significado | Exemplo |
|---|---|---|
| give up | desistir | Don't give up! |
| look for | procurar | I'm looking for my keys. |
| find out | descobrir | I found out the truth. |
| get up | levantar (da cama) | I get up at 7 am. |
| turn off/on | desligar/ligar | Turn off the lights. |
| come up with | ter uma ideia | She came up with a great idea. |
| run out of | ficar sem | We ran out of milk. |

> 🎯 Não dá para "traduzir palavra por palavra" um phrasal verb — o jeito é aprender como uma expressão só, com exemplos.

## Mais alguns bem comuns no dia a dia

| Phrasal verb | Significado |
|---|---|
| put off | adiar |
| figure out | entender/resolver |
| get along (with) | se dar bem (com) |
| deal with | lidar com |
""",
            [
                ex("quiz", '"I\'m ___ my keys." (procurando)',
                   "looking for", ["looking for", "looking at", "looking up"]),
                ex("text", "Traduza: Não desista!",
                   "don't give up"),
                ex("quiz", '"We ___ milk." (ficamos sem)',
                   "ran out of", ["ran out of", "ran out", "ran off"]),
                ex("quiz", 'Qual phrasal verb significa "adiar"?',
                   "put off", ["put off", "get along", "deal with"]),
            ],
        ),
        topic(
            "linking-words-conectores",
            "Linking words (conectores)",
            """
# Linking words (conectores)

Conectores deixam o texto mais **coeso**, ligando ideias de contraste, adição, causa e consequência.

| Conector | Função | Exemplo |
|---|---|---|
| **however** | contraste (mais formal que "but") | The plan was good. However, it failed. |
| **although** | contraste, no meio da frase | Although it was raining, we went out. |
| **moreover / furthermore** | adição | The hotel is cheap. Moreover, it's close to the beach. |
| **therefore / so** | consequência | It was raining, so we stayed home. |
| **because / since** | causa | I stayed home because it was raining. |

> 💡 Usar conectores variados (em vez de só "and"/"but") é um dos jeitos mais rápidos de deixar sua escrita em inglês com nível mais avançado (B2/C1).

## in spite of / despite + substantivo ou -ing

Diferente de "although" (que vem antes de uma oração completa), **in spite of** e **despite** vêm antes de um substantivo ou verbo no gerúndio, sem "that":

```
Despite the rain, we went out.          (Apesar da chuva, saímos.)
In spite of being tired, she worked.    (Apesar de estar cansada, ela trabalhou.)
```
""",
            [
                ex("quiz", "Qual conector expressa contraste de forma mais formal?",
                   "however", ["however", "because", "so"]),
                ex("text", "Traduza: Estava chovendo, então ficamos em casa.",
                   "it was raining so we stayed home"),
                ex("quiz", 'Complete: "Although it was raining, ___."',
                   "we went out", ["we went out", "so we went out", "because we went out"]),
                ex("quiz", 'Qual palavra é seguida de um SUBSTANTIVO (não de uma oração completa), como em "___ the rain"?',
                   "Despite", ["Despite", "Although", "Because"]),
            ],
        ),
    ],
))

# ============================================================
# MODULO 8 - Estruturas Avancadas (C1)
# ============================================================
MODULES.append(module(
    "estruturas-avancadas-ingles",
    "Módulo 8 — Estruturas Avançadas (C1)",
    "Relative clauses, inversão para ênfase, subjuntivo em estruturas formais e uma revisão integrada do curso.",
    [
        topic(
            "relative-clauses",
            "Relative Clauses (orações relativas)",
            """
# Relative Clauses (orações relativas)

Orações relativas dão mais informação sobre um substantivo, usando pronomes relativos:

| Pronome | Uso | Exemplo |
|---|---|---|
| **who** | pessoas | The man who called you is my brother. |
| **which** | coisas/animais | The book which I read was great. |
| **that** | pessoas ou coisas (mais informal) | The book that I read was great. |
| **whose** | posse | The woman whose car was stolen called the police. |
| **where** | lugares | The city where I was born is small. |

## Restritivas vs não restritivas

- **Restritiva** (sem vírgula): informação essencial para identificar do que se fala — `The man who called you is my brother.`
- **Não restritiva** (com vírgulas): informação extra, que poderia ser removida — `My brother, who lives in London, called me.`

## Quando o pronome relativo pode ser omitido

Quando o pronome relativo é o **objeto** da oração (não o sujeito), ele pode ser omitido em frases restritivas: `The book (that) I read was great.` Mas se for o sujeito, não dá para omitir: `The man who called you...` precisa do "who".
""",
            [
                ex("quiz", 'Complete: "The man ___ called you is my brother."',
                   "who", ["who", "which", "where"]),
                ex("text", "Traduza: O livro que eu li foi ótimo.",
                   "the book that i read was great"),
                ex("quiz", 'Complete: "The city ___ I was born is small."',
                   "where", ["who", "which", "where"]),
                ex("quiz", 'Em qual caso o pronome relativo PODE ser omitido?',
                   "quando é o objeto da oração, não o sujeito", ["quando é o objeto da oração, não o sujeito", "sempre, em qualquer caso", "nunca pode ser omitido"]),
            ],
        ),
        topic(
            "inversao-para-enfase",
            "Inversão para ênfase",
            """
# Inversão para ênfase (nível avançado)

Em inglês formal/literário, é possível **inverter** a ordem sujeito-verbo para dar ênfase, geralmente começando a frase com um advérbio negativo.

## Exemplos

```
Never have I seen such a beautiful sunset.
(Nunca vi um pôr do sol tão bonito.)

Not only did she finish the project, but she also presented it.
(Ela não só terminou o projeto, como também o apresentou.)

Rarely do we see such dedication.
(Raramente vemos tanta dedicação.)
```

Repare que, depois da expressão negativa no início, a estrutura vira **de pergunta** (auxiliar antes do sujeito): `Never have I...`, `Rarely do we...`.

> 🎯 Essa estrutura é opcional e usada para dar ênfase em textos mais formais ou discursos — na fala do dia a dia, a ordem normal (`I have never seen...`) é perfeitamente natural e muito mais comum.

## Outras expressões que também disparam a inversão

`No sooner... than`, `Not until`, `Little`, `Under no circumstances` seguem o mesmo padrão: `No sooner had I arrived than it started to rain.` (Mal cheguei e começou a chover.)
""",
            [
                ex("quiz", "Qual frase usa a inversão para ênfase corretamente?",
                   "Never have I seen such a sunset.", ["Never I have seen such a sunset.", "Never have I seen such a sunset.", "I never have seen such a sunset."]),
                ex("text", "Traduza (com inversão): Raramente vemos tanta dedicação.",
                   "rarely do we see such dedication"),
                ex("quiz", "Depois de uma expressão negativa no início da frase (Never, Rarely...), a estrutura vira:",
                   "de pergunta (auxiliar antes do sujeito)", ["afirmativa normal", "de pergunta (auxiliar antes do sujeito)", "imperativa"]),
                ex("quiz", 'Qual expressão TAMBÉM dispara a inversão, além de "Never"/"Rarely"?',
                   "Not until", ["Not until", "Usually", "Sometimes"]),
            ],
        ),
        topic(
            "subjunctive-e-estruturas-formais",
            "Subjunctive e estruturas formais",
            """
# Subjunctive e estruturas formais

O **subjunctive** (subjuntivo) aparece em inglês formal, geralmente depois de verbos como *suggest*, *recommend*, *insist*, *demand* — usando o verbo na forma base, mesmo com he/she/it:

```
The doctor recommended that he rest for a week.
(O médico recomendou que ele descansasse por uma semana.)

I suggest that she call him immediately.
(Sugiro que ela ligue para ele imediatamente.)
```

Repare: não é "he rests" nem "she calls" — no subjuntivo, o verbo fica na forma base, mesmo na 3ª pessoa.

## It's important that...

A mesma estrutura aparece depois de expressões como *it's important/essential/vital that*:

```
It is essential that everyone arrive on time.
(É essencial que todos cheguem na hora.)
```

## O subjuntivo com "were" (situações hipotéticas)

Você já viu essa forma no condicional tipo 2 (Módulo 6): usar **were** para todos os sujeitos é tecnicamente o mesmo subjuntivo, aplicado a situações hipotéticas: `If I were rich...`, `I wish I were taller.`
""",
            [
                ex("quiz", 'Complete: "The doctor recommended that he ___ for a week."',
                   "rest", ["rests", "rest", "rested"]),
                ex("text", "Traduza: Sugiro que ela ligue para ele imediatamente.",
                   "i suggest that she call him immediately"),
                ex("quiz", 'Complete: "It is essential that everyone ___ on time."',
                   "arrive", ["arrives", "arrive", "arrived"]),
                ex("quiz", 'Qual forma do verbo "to be" é usada no subjuntivo hipotético (ex: "If I ___ rich...")?',
                   "were", ["were", "was", "am"]),
            ],
        ),
        topic(
            "revisao-integrada",
            "Revisão integrada: do A1 ao C1",
            """
# Revisão integrada: dos tempos verbais ao discurso formal

Chegou a hora de juntar tudo o que você aprendeu, do módulo 0 ao módulo 8. Os exercícios abaixo misturam vários pontos do curso — se você errar algum, vale voltar ao módulo correspondente para revisar.

## Panorama rápido

| Nível | O que você aprendeu |
|---|---|
| A1 | to be, pronomes, saudações |
| A2 | simple present/past, artigos, plural, used to |
| B1 | futuro, modais, comparativos, preposições, gerúndio vs infinitivo |
| B2 | perfect tenses, voz passiva, condicionais |
| C1 | discurso indireto, phrasal verbs, inversão, subjuntivo |

> 🏆 Parabéns por chegar até aqui! Gramática é só uma parte do idioma — o próximo passo é praticar bastante com leitura, áudio e conversação no dia a dia.
""",
            [
                ex("quiz", "Complete (present perfect continuous): \"She ___ in Brazil for ten years.\"",
                   "has been living", ["has been living", "lived", "is living"]),
                ex("quiz", "Complete (condicional tipo 2): \"If I ___ more time, I would travel more.\"",
                   "had", ["have", "had", "will have"]),
                ex("text", "Traduza (condicional tipo 3): Se eu tivesse sabido, eu teria ligado.",
                   "if i had known i would have called"),
                ex("quiz", "Qual é o discurso indireto correto de: \"I am busy,\" she said?",
                   "She said that she was busy.", ["She said that she is busy.", "She said that she was busy.", "She said she busy."]),
                ex("quiz", 'Revisão (Módulo 2): o que "used to" indica?',
                   "um hábito do passado que não é mais verdade", ["um hábito do passado que não é mais verdade", "uma ação no futuro", "uma ordem"]),
                ex("quiz", 'Revisão (Módulo 4): qual forma vem depois de "enjoy" — gerúndio ou infinitivo?',
                   "gerúndio (-ing)", ["gerúndio (-ing)", "infinitivo (to + verbo)", "forma base sem nada"]),
            ],
        ),
    ],
))


# ============================================================
# Serializacao final
# ============================================================
def finalize():
    for m_idx, m in enumerate(MODULES):
        m["position"] = m_idx
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
    return MODULES


def check(data):
    """Trava erros de autoria que o corretor do navegador nao pegaria."""
    problems = []
    for m in data["modules"]:
        for t in m["topics"]:
            if len(t["exercises"]) < 4:
                problems.append(f"{t['slug']}: so {len(t['exercises'])} exercicios")
            for e in t["exercises"]:
                loc = f"{t['slug']} #{e['position']}"
                if not e.get("solution"):
                    problems.append(f"{loc}: solution vazia")
                if e["type"] == "quiz":
                    opts = e.get("options") or []
                    norms = [normalize(o) for o in opts]
                    # Duas alternativas iguais depois de normalize deixariam o
                    # aluno acertar escolhendo a errada.
                    if len(set(norms)) != len(norms):
                        problems.append(f"{loc}: alternativas ambiguas apos normalize: {opts}")
                    if norms.count(normalize(e["solution"])) != 1:
                        problems.append(f"{loc}: solution nao casa com exatamente 1 alternativa: {opts}")
                if e["type"] in ("audio", "speak"):
                    if not e.get("audio_text"):
                        problems.append(f"{loc}: {e['type']} sem audio_text")
                    elif normalize(e["audio_text"]) != normalize(e["solution"]):
                        problems.append(f"{loc}: audio_text != solution")
    slugs = [t["slug"] for m in data["modules"] for t in m["topics"]]
    if len(set(slugs)) != len(slugs):
        problems.append("slugs de topico duplicados")
    return problems


def main():
    data = {
        "slug": "ingles-do-zero",
        "title": "Inglês do Zero",
        "description": "Uma trilha completa de gramática inglesa, do absoluto zero (A1) até um nível avançado (C1), incluindo used to, gerúndio vs infinitivo e discurso indireto de ordens. Cada tópico explica a regra em português, com bastante exemplo em inglês, e você pratica digitando, ouvindo, falando e respondendo quizzes direto no navegador — clique em qualquer opção de quiz ou frase de exemplo para ouvir a pronúncia.",
        "category": "Idiomas",
        "icon": "🇬🇧",
        "level": "Do zero ao avançado (A1–C1)",
        "position": 3,
        "modules": finalize(),
    }

    problems = check(data)
    if problems:
        print("ERROS - nada foi escrito:")
        for p in problems:
            print("  -", p)
        raise SystemExit(1)

    out_path = Path(__file__).resolve().parent.parent / "app" / "content" / "ingles-do-zero.json"
    with out_path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")

    n_topics = sum(len(m["topics"]) for m in data["modules"])
    n_ex = sum(len(t["exercises"]) for m in data["modules"] for t in m["topics"])
    n_pt = sum(1 for m in data["modules"] for t in m["topics"] for e in t["exercises"]
               if e.get("audio_lang") == "pt-BR")
    print(f"OK: {len(data['modules'])} modulos, {n_topics} topicos, {n_ex} exercicios "
          f"({n_pt} com voz pt-BR) -> {out_path}")


if __name__ == "__main__":
    main()