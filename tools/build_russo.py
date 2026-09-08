# -*- coding: utf-8 -*-
"""Gera/expande app/content/russo-do-zero.json a partir de uma estrutura Python.

Reescrita completa do curso de russo (ver tools/RUSSIAN_ROADMAP.md): a grade
antiga de 16 módulos (221 exercícios, cada tema visto uma vez só) foi
descartada em favor de 29 módulos em "currículo em espiral", onde casos,
aspecto verbal e verbos de movimento aparecem cedo (Módulo 4, A1) e são
revisitados em vários níveis até o C1.

Como inglês/python (build_ingles.py/build_python.py), este script usa o padrão
**incremental**: um dicionário `BUILDERS` (slug do módulo -> função construtora)
e uma lista `TARGET_ORDER` com a ordem final de TODOS os 29 módulos do roteiro.
A cada execução, só os módulos com builder aparecem no JSON, na posição definida
por TARGET_ORDER. É reescrita do zero: a "base" é o próprio código Python, não
um JSON legado.
"""
import json
import re
from copy import deepcopy
from pathlib import Path

CONTENT_DIR = Path(__file__).resolve().parent.parent / "app" / "content"
OUT_PATH = CONTENT_DIR / "russo-do-zero.json"

EARLY_MODULE_SLUGS = frozenset({
    "modulo-01-alfabeto-e-primeiros-passos",
    "modulo-02-frases-basicas-sem-verbo-ser",
    "modulo-03-perguntas-e-negacao",
    "modulo-04-casos-primeiro-contato",
    "modulo-05-vocabulario-e-comunicacao-a1",
    "modulo-06-presente-dos-verbos",
    "modulo-07-vocabulario-e-comunicacao-a2",
    "modulo-08-casos-intermediarios",
})

EXPANDED_MODULE_SLUGS = frozenset({
    "modulo-09-aspecto-verbal-conceito",
    "modulo-10-passado-e-futuro",
    "modulo-11-casos-avancados",
    "modulo-12-verbos-de-movimento",
    "modulo-13-comunicacao-b1",
    "modulo-14-participios-gerundios-e-discurso-indireto",
    "modulo-15-verbos-de-movimento-prefixados",
    "modulo-16-imperativo-e-aspecto",
    "modulo-17-comparacao-pronomes-e-reflexivos",
    "modulo-18-vocabulario-e-expressoes-b2",
})


# ============================================================
# Helpers de autoria (mesmo padrão dos outros geradores)
# ============================================================

# Espelha normalize() do web/static/js/runner.js: e' assim que o front-end
# compara a resposta do aluno com a solucao.
def normalize(s):
    s = s.lower().replace("ё", "е")
    s = re.sub(r"[.,!?;:'\"-]", "", s)
    return re.sub(r"\s+", " ", s).strip()


CYRILLIC = re.compile(r"[А-Яа-яЁё]")


def ex(type, prompt, solution, options=None, audio_text=None, audio_lang="ru-RU"):
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


# ============================================================
# Validacao (roda ANTES de escrever qualquer coisa)
# ============================================================

def check(modules, active_module_slugs):
    """Trava erros de autoria antes de gravar o JSON.

    `active_module_slugs`: módulos sendo escritos/tocados NESTA fase — os
    módulos 1–18 precisam ter exatamente 10 exercícios/tópico; os demais ativos
    seguem o mínimo de 5.
    """
    problems = []
    topic_slugs = []
    module_slugs = []

    for m in modules:
        module_slugs.append(m["slug"])
        for t in m["topics"]:
            topic_slugs.append(t["slug"])
            loc_base = f"{m['slug']}/{t['slug']}"
            if m["slug"] in active_module_slugs:
                if (m["slug"] in EARLY_MODULE_SLUGS
                        or m["slug"] in EXPANDED_MODULE_SLUGS) and len(t["exercises"]) != 10:
                    problems.append(f"{loc_base}: {len(t['exercises'])} exercícios (esperado exatamente 10)")
                elif (m["slug"] not in EARLY_MODULE_SLUGS
                        and m["slug"] not in EXPANDED_MODULE_SLUGS
                        and len(t["exercises"]) < 5):
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
                # Digitar cirilico so e' viavel com o teclado virtual, que o
                # template so mostra quando audio_lang comeca com "ru".
                if e["type"] in ("text", "audio") and CYRILLIC.search(e.get("solution", "")):
                    if not e.get("audio_lang", "").startswith("ru"):
                        problems.append(f"{loc}: resposta em cirilico sem teclado virtual")

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
# MODULO 1 - Alfabeto e Primeiros Passos (A1)
# ============================================================

def build_modulo_01_alfabeto_e_primeiros_passos():
    return module(
        "modulo-01-alfabeto-e-primeiros-passos",
        "Módulo 1 — Alfabeto e Primeiros Passos — A1",
        "Como funciona o curso (níveis CEFR e o currículo em espiral), o alfabeto cirílico, os sons difíceis, as primeiras palavras e saudações e os números de 1 a 10 — ainda com apoio de romanização.",
        [
            topic(
                "como-o-curso-funciona",
                "Como este curso funciona: CEFR e currículo em espiral",
                """
# Como este curso funciona: CEFR e currículo em espiral

Este curso segue o **CEFR** (Common European Framework of Reference for Languages) — a mesma escala usada no curso de inglês:

| Nível | Nome | Você já consegue... |
|---|---|---|
| **A1** | Iniciante | Ler o alfabeto, frases simples, se apresentar |
| **A2** | Básico | Declinar os casos mais comuns, falar da rotina |
| **B1** | Intermediário | Usar os 6 casos com segurança, escolher o aspecto verbal |
| **B2** | Intermediário avançado | Verbos de movimento com prefixo, particípios e gerúndios |
| **C1** | Avançado | Nuance, registro, fluência real |

## O currículo em espiral

Os três temas mais difíceis do russo — os **6 casos gramaticais**, o
**aspecto verbal** e os **verbos de movimento** — não são aprendidos uma vez
só. Eles aparecem **cedo** (os casos já no Módulo 4, ainda no A1) e são
**revisitados em vários níveis** até o C1. A cada volta, você aprofunda um
pouco mais.

**O objetivo do curso** é você conseguir falar uma frase como:

> **Я хотел бы поговорить с тобой о том, что произошло вчера.**
> ("Eu gostaria de conversar com você sobre o que aconteceu ontem.")

...no B1/B2, **sem travar pensando em qual caso é qual**. Cada pedaço dessa
frase exige o espiral: "с тобой" (Instrumental), "о том" (Preposicional),
"что произошло" (aspecto perfectivo no passado). Quando essa frase sair de
cabeça erguida, o curso cumpriu seu papel.

## Um aviso importante sobre o russo

Russo é uma língua **muito mais distante do português** do que o inglês:

- Um **alfabeto novo** (cirílico) — calma, são só 33 letras.
- **6 casos gramaticais**: substantivos e adjetivos mudam de terminação
  conforme a função na frase (sujeito, objeto, posse...). É o coração da
  gramática russa.
- **Gênero gramatical** (masculino/feminino/neutro), afetando muito mais
  coisas que no português.
- **Aspecto verbal**: cada ação tem dois verbos — um para "ação completa" e
  outro para "ação em andamento/repetida".

> 💡 Nos **dois primeiros módulos** vamos usar **cirílico + romanização** (a
> pronúncia escrita em letras latinas, tipo "privet"). A partir do Módulo 3,
> o curso passa a ser 100% em cirílico — é assim que se aprende a ler russo
> de verdade.

## Como aproveitar bem este curso

- **Clique nas palavras em russo** ao longo das lições para ouvir a
  pronúncia — todo texto em cirílico do curso é clicável.
- Use o **teclado cirílico virtual** nos exercícios de digitação.
- Não pule os exercícios de escuta e fala — russo tem sons que não existem
  em português, e só treinar o ouvido resolve isso.
""",
                [
                    ex("quiz", "Qual escala este curso usa para medir seu nível?",
                       "CEFR (A1 a C1)", ["CEFR (A1 a C1)", "TOEFL", "ENEM"], audio_lang="pt-BR"),
                    ex("quiz", "Por que o russo costuma ser mais desafiador para falantes de português do que o inglês?",
                       "Tem alfabeto novo, 6 casos gramaticais e aspecto verbal",
                       ["Tem alfabeto novo, 6 casos gramaticais e aspecto verbal", "Não tem nenhuma diferença relevante", "É quase idêntico ao português"],
                       audio_lang="pt-BR"),
                    ex("quiz", "A partir de qual módulo o curso passa a ser 100% em cirílico, sem romanização?",
                       "A partir do Módulo 3", ["A partir do Módulo 3", "Nunca, sempre haverá romanização", "Só no último módulo (C1)"],
                       audio_lang="pt-BR"),
                    ex("quiz", "O que é o 'currículo em espiral' deste curso?",
                       "Os casos, o aspecto e os verbos de movimento são revisitados em vários níveis",
                       ["Os casos, o aspecto e os verbos de movimento são revisitados em vários níveis", "Cada tema é visto uma única vez", "Não há revisões, tudo é novo o tempo todo"],
                       audio_lang="pt-BR"),
                    ex("quiz", "Segundo a lição, qual é a melhor forma de treinar os sons novos do russo?",
                       "Fazer os exercícios de escuta e fala, sem pular",
                       ["Fazer os exercícios de escuta e fala, sem pular", "Ler só em silêncio, sem ouvir nada", "Decorar o alfabeto latino primeiro"],
                       audio_lang="pt-BR"),
                ],
            ),
            topic(
                "alfabeto-cirilico",
                "O alfabeto cirílico",
                """
# O alfabeto cirílico

O alfabeto russo tem 33 letras. Muitas parecem letras latinas, mas têm sons diferentes — preste atenção nisso!

## Letras parecidas com o português (mesmo som)

| Letra | Som | Exemplo |
|---|---|---|
| а | a | мама (mama) |
| о | o | дом (dom) |
| м | m | мама (mama) |
| к | k | кот (kot) |

## Letras que enganam (parecem uma coisa, soam outra)

| Letra | Soa como | Não confunda com |
|---|---|---|
| В в | "v" | não é "b" |
| Н н | "n" | não é "h" |
| Р р | "r" vibrante | não é "p" |
| С с | "s" | não é "c" |
| У у | "u" | não é "y" |

## Letras totalmente novas

| Letra | Som aproximado |
|---|---|
| Б б | "b" |
| Г г | "g" (sempre duro, como em "gato") |
| Д д | "d" |
| Ж ж | "j" francês (como em "jour") |
| Ш ш | "ch" (como em "chuva", mais duro) |
| Щ щ | "chtch" (mais longo que ш) |
| Ц ц | "ts" |
| Ч ч | "tch" |
| Э э | "é" aberto |
| Ю ю | "iu" |
| Я я | "ia" |
| Ы ы | som gutural sem equivalente em português |
| Й й | "i" curto/semivogal |

## Um truque para memorizar mais rápido

Separe as letras em três grupos ao estudar: (1) as que já soam como no português (а, о, м, к, т...), (2) as "falsas amigas" que soam diferente do que parecem (В, Н, Р, С, У), e (3) as totalmente novas. O grupo (2) é o que mais confunde iniciantes — revise-o com calma antes de seguir em frente.

> 🎧 Não se preocupe em decorar tudo de uma vez — os exercícios abaixo já começam a fixar isso.
""",
                [
                    ex("quiz", 'Qual letra russa soa como "v" (e não "b")?',
                       "В", ["В", "Б", "Н"]),
                    ex("quiz", 'Qual letra russa soa como "n" (e não "h")?',
                       "Н", ["Н", "П", "И"]),
                    ex("audio", "Escute e transcreva em cirílico:",
                       "мама", audio_text="мама"),
                    ex("quiz", 'Qual letra soa como o "j" do francês (ex: "jour")?',
                       "Ж", ["Ж", "Ш", "Ч"]),
                    ex("speak", "Repita a palavra em voz alta:", "кот", audio_text="кот"),
                ],
            ),
            topic(
                "sons-dificeis-do-russo",
                "Sons difíceis do russo",
                """
# Sons difíceis do russo

## O sinal mole (ь) e o sinal duro (ъ)

Esses dois símbolos não têm som próprio — eles **alteram a pronúncia da consoante anterior**:

- **ь** (sinal mole, мягкий знак): "amolece" (palataliza) a consoante anterior. Ex.: `мать` (mãe).
- **ъ** (sinal duro, твёрдый знак): bem mais raro, mantém a consoante "dura" antes de uma vogal iotizada. Ex.: `объект` (objeto).

## Vogais iotizadas

Algumas vogais "amolecem" a consoante anterior: **я, ё, ю, е, и** (opostas a **а, о, у, э, ы**, que mantêm a consoante "dura"). Isso é sutil no início — o ouvido vai se acostumando com a prática.

## O acento tônico (ударение)

O **acento tônico** pode cair em qualquer sílaba da palavra, e isso muda a pronúncia das vogais átonas (um "o" átono, por exemplo, costuma soar como "a"). Nos textos do dia a dia o acento não é marcado — por isso ouvir bastante é fundamental.

Exemplo clássico: **молоко** (leite) tem o acento na última sílaba, então soa como "malakó" — o primeiro e o segundo "о" (átonos) viram um som de "a", e só o último "о" (tônico) soa como "o" de verdade.

> ⚠️ Isso significa que ler uma palavra russa em voz alta letra por letra quase nunca dá a pronúncia certa — é preciso saber onde cai o acento.
""",
                [
                    ex("quiz", "O que o sinal mole (ь) faz?",
                       "Amolece a consoante anterior",
                       ["Amolece a consoante anterior", "Cria um novo som vocálico", "Não faz nada"]),
                    ex("speak", "Repita a palavra em voz alta:", "мать", audio_text="мать"),
                    ex("quiz", "O que faz o sinal duro (ъ)?",
                       "Mantém a consoante \"dura\" antes de uma vogal iotizada",
                       ["Mantém a consoante \"dura\" antes de uma vogal iotizada", "Amolece a consoante anterior", "Não existe no alfabeto russo"]),
                    ex("audio", "Escute e transcreva:", "объект", audio_text="объект"),
                    ex("quiz", 'Em "молоко", por que o primeiro e o segundo "о" soam como "a"?',
                       "Porque são vogais átonas, sem o acento tônico",
                       ["Porque são vogais átonas, sem o acento tônico", "Porque \"о\" sempre soa como \"a\" em russo", "É um erro de pronúncia comum, não uma regra"]),
                ],
            ),
            topic(
                "primeiras-palavras-e-saudacoes",
                "Primeiras palavras e saudações",
                """
# Primeiras palavras e saudações

| Cirílico | Romanização | Português |
|---|---|---|
| Привет | Privet | Oi (informal) |
| Здравствуйте | Zdravstvuyte | Olá (formal) |
| Пока | Poka | Tchau (informal) |
| До свидания | Do svidaniya | Até logo (formal) |
| Спасибо | Spasibo | Obrigado(a) |
| Пожалуйста | Pozhaluysta | Por favor / De nada |
| Да | Da | Sim |
| Нет | Net | Não |
| Извините | Izvinite | Desculpe / Com licença |

## Perguntando e respondendo "como vai"

| Cirílico | Português |
|---|---|
| Как дела? | Como vai? (informal) |
| Хорошо! | Bem! |
| Так себе | Mais ou menos |
| Как тебя зовут? | Qual é o seu nome? (informal) |
| Меня зовут... | Meu nome é... |

> 💡 "Пожалуйста" serve tanto para "por favor" quanto para responder "de nada" — repare pelo contexto.
""",
                [
                    ex("text", "Traduza para o russo (em cirílico): Obrigado(a)",
                       "спасибо"),
                    ex("quiz", 'Como se diz "Olá" de forma FORMAL?',
                       "Здравствуйте", ["Привет", "Здравствуйте", "Пока"]),
                    ex("audio", "Escute e transcreva:", "пожалуйста", audio_text="Пожалуйста"),
                    ex("speak", "Repita em voz alta:", "здравствуйте", audio_text="здравствуйте"),
                    ex("text", "Traduza: Como vai? (Как + дела)",
                       "как дела"),
                ],
            ),
            topic(
                "numeros-1-a-10-russo",
                "Números de 1 a 10",
                """
# Números de 1 a 10

| Número | Cirílico | Romanização |
|---|---|---|
| 0 | ноль | nol' |
| 1 | один | odin |
| 2 | два | dva |
| 3 | три | tri |
| 4 | четыре | chetyre |
| 5 | пять | pyat' |
| 6 | шесть | shest' |
| 7 | семь | sem' |
| 8 | восемь | vosem' |
| 9 | девять | devyat' |
| 10 | десять | desyat' |

> 🎯 Repare que muitos números terminam com o sinal mole (ь) — a pronúncia "amolece" no final.

> 💡 Você vai reencontrar esses números nos módulos de casos (a partir do Módulo 4): quando contam, eles mudam a terminação do substantivo que acompanham.
""",
                [
                    ex("text", "Escreva em cirílico o número 5.", "пять"),
                    ex("quiz", 'Qual número é "четыре"?', "4", ["3", "4", "5"]),
                    ex("audio", "Escute e transcreva o número:", "восемь", audio_text="восемь"),
                    ex("speak", "Repita o número em voz alta:", "семь", audio_text="семь"),
                    ex("text", "Escreva em cirílico o número 10.", "десять"),
                ],
            ),
        ],
    )


# ============================================================
# MODULO 2 - Frases Basicas sem o Verbo "Ser" (A1)
# ============================================================

def build_modulo_02_frases_basicas_sem_verbo_ser():
    return module(
        "modulo-02-frases-basicas-sem-verbo-ser",
        "Módulo 2 — Frases Básicas sem o Verbo \"Ser\" — A1",
        "Pronomes pessoais, gênero dos substantivos, frases sem o verbo \"ser\" no presente e o plural básico — ainda com apoio de romanização (último módulo com esse apoio).",
        [
            topic(
                "pronomes-pessoais-russo",
                "Pronomes pessoais",
                """
# Pronomes pessoais

| Russo | Romanização | Português |
|---|---|---|
| я | ya | eu |
| ты | ty | tu / você (informal) |
| он | on | ele |
| она | ana | ela |
| оно | ano | ele/ela (neutro) |
| мы | my | nós |
| вы | vy | vocês / você (formal) |
| они | ani | eles/elas |

> 💡 "вы" é usado tanto para "vocês" (plural) quanto como forma **formal** de "você" no singular — parecido com o "vous" do francês.

## Quando usar "ты" e quando usar "вы"

Use **ты** com amigos, família, crianças e colegas próximos. Use **вы** com desconhecidos, superiores, pessoas mais velhas ou em contextos formais — na dúvida, comece sempre com "вы" e espere a outra pessoa sugerir mudar para "ты".
""",
                [
                    ex("quiz", 'Qual pronome é usado tanto para "vocês" quanto como forma FORMAL de "você"?',
                       "вы", ["ты", "вы", "они"]),
                    ex("text", "Traduza: eu", "я"),
                    ex("audio", "Escute e transcreva:", "мы", audio_text="мы"),
                    ex("quiz", "Com quem você normalmente usaria \"ты\" em vez de \"вы\"?",
                       "Um amigo próximo", ["Um amigo próximo", "O chefe, na primeira reunião", "Um desconhecido na rua"]),
                    ex("speak", "Repita em voz alta:", "они", audio_text="они"),
                    ex("quiz", 'Qual pronome é "ela"?',
                       "она", ["она", "он", "оно"]),
                ],
            ),
            topic(
                "genero-dos-substantivos",
                "Gênero dos substantivos",
                """
# Gênero dos substantivos

Todo substantivo russo tem um gênero: **masculino**, **feminino** ou **neutro**. Ao contrário do português, dá para adivinhar o gênero pela **terminação** da palavra, na maioria dos casos:

| Terminação | Gênero | Exemplo |
|---|---|---|
| consoante | masculino | стол (stol, mesa) |
| -а / -я | feminino | книга (kniga, livro), земля (zemlya, terra) |
| -о / -е | neutro | окно (akno, janela), море (morye, mar) |
| -ь (varia, precisa decorar) | masculino ou feminino | словарь (dicionário, masc.), дверь (porta, fem.) |

## Por que o gênero importa tanto

Diferente do português, em russo o gênero não afeta só o artigo (que nem existe!) — ele muda a terminação de **adjetivos**, do **verbo no passado** e de vários **pronomes**. É por isso que vale a pena memorizar o gênero de cada palavra nova desde já, junto com o significado.

> 🎯 Palavras terminadas em -ь são as mais imprevisíveis: não tem como adivinhar o gênero só pela terminação, então essas precisam ser decoradas caso a caso (dicionários sempre indicam).
""",
                [
                    ex("quiz", "Qual o gênero de uma palavra terminada em consoante (ex: стол)?",
                       "masculino", ["masculino", "feminino", "neutro"]),
                    ex("quiz", "Qual o gênero de uma palavra terminada em -о (ex: окно)?",
                       "neutro", ["masculino", "feminino", "neutro"]),
                    ex("quiz", 'Qual o gênero de "книга" (livro)?',
                       "feminino", ["masculino", "feminino", "neutro"]),
                    ex("quiz", "Por que as palavras terminadas em -ь são mais difíceis quanto ao gênero?",
                       "Podem ser masculinas ou femininas, sem regra fixa",
                       ["Podem ser masculinas ou femininas, sem regra fixa", "São sempre neutras", "Não existem palavras assim"]),
                    ex("audio", "Escute e transcreva:", "дверь", audio_text="дверь"),
                    ex("text", 'Escreva o gênero de "стол": masculino ou feminino?',
                       "masculino"),
                ],
            ),
            topic(
                "frases-sem-verbo-ser",
                'Frases sem o verbo "ser/estar"',
                """
# Frases sem o verbo "ser/estar"

No **presente**, o russo **não usa** o verbo "ser/estar" (быть) — a frase simplesmente junta sujeito e predicado:

```
Я студент.        (ya student — Eu [sou] estudante.)
Она врач.         (ana vrach — Ela [é] médica.)
Это книга.        (eta kniga — Isso [é] um livro.)
```

Repare: não existe um "é"/"sou" no meio da frase! Isso é bem diferente do português e do inglês.

## O travessão no lugar do verbo "ser"

Quando os dois lados da frase são substantivos (não pronomes), a língua escrita costuma marcar essa ausência de verbo com um travessão:

```
Москва — столица России.     Moscou é a capital da Rússia.
```

> ⚠️ O verbo "быть" existe (você vai usá-lo no passado e no futuro, no Módulo 10), só não aparece no **presente**.
""",
                [
                    ex("text", "Traduza: Eu [sou] estudante. (я + студент)", "я студент"),
                    ex("quiz", 'Como se traduz "Isso é um livro" (это + книга)?',
                       "Это книга.", ["Это книга.", "Это есть книга.", "Книга это."]),
                    ex("audio", "Escute e transcreva:", "она врач", audio_text="она врач"),
                    ex("quiz", "O que substitui o verbo \"ser\" por escrito entre dois substantivos, como em \"Москва — столица России\"?",
                       "Um travessão (—)", ["Um travessão (—)", "A palavra \"есть\"", "Nada, nem sinal nenhum"]),
                    ex("speak", "Repita em voz alta:", "я студент", audio_text="я студент"),
                    ex("text", "Traduza: Isso [é] um livro. (это + книга)", "это книга"),
                ],
            ),
            topic(
                "plural-basico-russo",
                "Plural básico",
                """
# Plural básico

A regra geral: substantivos masculinos e femininos terminados em consoante ou -а/-я trocam para **-ы** ou **-и** no plural:

| Singular | Plural | Regra |
|---|---|---|
| стол (mesa) | столы | consoante -> +ы |
| студент (estudante) | студенты | consoante -> +ы |
| книга (livro) | книги | -а -> -и (depois de г, к, х, ш, ж, ч, щ sempre -и) |

Substantivos neutros (-о/-е) trocam para **-а/-я**:

| Singular | Plural |
|---|---|
| окно (janela) | окна |
| море (mar) | моря |

## Por que às vezes é -ы e às vezes é -и

A troca por **-и** em vez de **-ы** acontece depois de sete consoantes específicas (г, к, х, ш, ж, ч, щ) — regra de ortografia do russo que vale para vários outros sufixos, não só o plural. Vale memorizar essas sete letras como um grupo.

> 💡 Assim como em português, existem exceções (друг -> друзья, "amigo -> amigos") — mas essa regra cobre a maioria dos casos no início.
""",
                [
                    ex("quiz", 'Qual o plural de "стол" (mesa)?', "столы", ["столы", "столо", "столе"]),
                    ex("text", 'Escreva o plural de "книга" (livro).', "книги"),
                    ex("quiz", 'Qual o plural de "окно" (janela)?', "окна", ["окны", "окна", "окне"]),
                    ex("quiz", "Depois de quais consoantes o plural usa -и em vez de -ы?",
                       "г, к, х, ш, ж, ч, щ", ["г, к, х, ш, ж, ч, щ", "б, в, д", "apenas depois de vogais"]),
                    ex("audio", "Escute e transcreva:", "студенты", audio_text="студенты"),
                    ex("text", 'Escreva o plural de "окно" (janela).', "окна"),
                ],
            ),
            topic(
                "isso-e-palavras-comuns",
                '"Это" (isto é) e palavras comuns',
                """
# "Это" (isto é) e palavras comuns

A palavra **это** (isto/esta) é a chave para apresentar qualquer coisa:

```
Это стол.          Isto é uma mesa.
Это книга.         Isto é um livro.
Это мой дом.       Esta é a minha casa.
```

## Palavras comuns do dia a dia

| Russo | Romanização | Português |
|---|---|---|
| дом | dom | casa |
| стол | stol | mesa |
| книга | kniga | livro |
| окно | akno | janela |
| город | gorat | cidade |
| человек | chelaviek | pessoa |

> 💡 "Это" funciona para qualquer gênero e número — "это книга", "это дом", "это окно" — não muda! (O "это" como apresentador é invariável.)
""",
                [
                    ex("text", "Traduza: Isto é uma mesa. (это + стол)", "это стол"),
                    ex("quiz", 'Como se diz "casa" (дом)?', "дом", ["дом", "книга", "окно"]),
                    ex("audio", "Escute e transcreva:", "это мой дом", audio_text="это мой дом"),
                    ex("quiz", 'A palavra "это" (isto é) muda de forma conforme o gênero?',
                       "Não, é invariável", ["Não, é invariável", "Sim, muda com o gênero", "Só muda no plural"]),
                    ex("speak", "Repita em voz alta:", "это книга", audio_text="это книга"),
                    ex("text", "Traduza: Isto é um livro. (это + книга)", "это книга"),
                ],
            ),
        ],
    )


# ============================================================
# MODULO 3 - Perguntas e Negacao (A1)
# ============================================================

def build_modulo_03_perguntas_e_negacao():
    return module(
        "modulo-03-perguntas-e-negacao",
        "Módulo 3 — Perguntas e Negação — A1",
        "As palavras interrogativas, a diferença entre где e куда, a negação com не e as respostas curtas. A partir daqui, o curso é 100% em cirílico.",
        [
            topic(
                "palavras-interrogativas-russo",
                "Palavras interrogativas",
                """
# Palavras interrogativas

| Russo | Português |
|---|---|
| кто? | quem? |
| что? | o quê? |
| где? | onde? |
| куда? | para onde? |
| когда? | quando? |
| как? | como? |
| почему? | por quê? |
| сколько? | quanto(s)? |

## Exemplos

```
Кто это?          Quem é esse/essa?
Что это?          O que é isso?
Где ты?           Onde você está?
Как дела?         Como vai? (literalmente "como [vão] as coisas?")
```

> 💡 Frases com palavra interrogativa não precisam de nenhuma partícula extra — a entonação e a palavra já deixam claro que é uma pergunta.
""",
                [
                    ex("quiz", 'Qual palavra significa "onde?"', "где", ["где", "куда", "когда"]),
                    ex("text", "Traduza: O que é isso? (что + это)", "что это"),
                    ex("audio", "Escute e transcreva:", "как дела", audio_text="как дела"),
                    ex("quiz", 'Qual palavra pergunta "quando?"', "когда", ["когда", "где", "как"]),
                    ex("speak", "Repita em voz alta:", "почему", audio_text="почему"),
                    ex("quiz", 'Qual palavra pergunta "quem?"', "кто", ["кто", "что", "сколько"]),
                ],
            ),
            topic(
                "gde-vs-kuda",
                "где vs куда (onde vs para onde)",
                """
# где vs куда (onde vs para onde)

Repare que existem duas palavras para "onde":

- **где** pergunta sobre **localização parada** ("onde você está?").
- **куда** pergunta sobre **destino/direção** ("para onde você vai?").

```
Где ты?           Onde você está? (localização)
Куда ты идёшь?    Para onde você vai? (destino)
```

> 🎯 Essa mesma distinção (localização x direção) aparece nos casos gramaticais — Preposicional x Acusativo (Módulos 4 e 8). É um padrão que se repete bastante em russo, então vale fixar desde já.
""",
                [
                    ex("quiz", 'Qual palavra pergunta o DESTINO ("para onde")?',
                       "куда", ["куда", "где", "когда"]),
                    ex("text", "Traduza: Onde você está? (где + ты)", "где ты"),
                    ex("quiz", "Qual é a diferença entre \"где\" e \"куда\"?",
                       '"где" pergunta localização, "куда" pergunta destino',
                       ['"где" pergunta localização, "куда" pergunta destino', "são sinônimos perfeitos", '"куда" só se usa no passado']),
                    ex("audio", "Escute e transcreva:", "куда ты идёшь", audio_text="куда ты идёшь"),
                    ex("speak", "Repita em voz alta:", "где ты", audio_text="где ты"),
                    ex("quiz", 'Qual pergunta é sobre LOCALIZAÇÃO parada?',
                       "Где ты?", ["Где ты?", "Куда ты идёшь?", "Почему ты?"]),
                ],
            ),
            topic(
                "negacao-com-nao",
                'Negação com "не"',
                """
# Negação com "не"

Para negar uma frase, basta colocar **не** antes da palavra que se quer negar (geralmente o verbo):

```
Я студент.             Eu sou estudante.
Я не студент.          Eu não sou estudante.

Он говорит по-русски.       Ele fala russo.
Он не говорит по-русски.    Ele não fala russo.
```

## Negando outras partes da frase

"не" sempre nega a palavra logo depois dele, não a frase inteira — então também dá para negar só um pedaço:

```
Это не моя книга.      Isso não é o meu livro. (nega "моя", "meu", não o fato de ser um livro)
```

> 💡 "не" é uma palavra curtinha e sempre vem **antes** da palavra negada — bem mais simples que o "do/does not" do inglês!
""",
                [
                    ex("text", "Traduza: Eu não sou estudante. (я + не + студент)", "я не студент"),
                    ex("quiz", 'Onde "не" deve ficar na frase?',
                       "Antes da palavra negada", ["Antes da palavra negada", "Depois da palavra negada", "No final da frase"]),
                    ex("audio", "Escute e transcreva:", "он не говорит по-русски", audio_text="он не говорит по-русски"),
                    ex("quiz", 'Em "Это не моя книга", o que exatamente "не" está negando?',
                       '"моя" (meu) — que o livro é seu', ['"моя" (meu) — que o livro é seu', "que é um livro", "nada, a frase inteira não tem sentido"]),
                    ex("text", "Traduza: Ele não fala russo. (он + не + говорит + по-русски)", "он не говорит по-русски"),
                ],
            ),
            topic(
                "respostas-curtas",
                "Respostas curtas: да e нет",
                """
# Respostas curtas: да e нет

As respostas sim/não em russo são simples:

```
Да.        Sim.
Нет.       Não.
```

## Respondendo perguntas

```
Это книга?       Isto é um livro?
Да, книга.       Sim, é um livro.
Нет, это не книга.  Não, não é um livro.
```

## нет também nega existência

Além de "não", **нет** aparece em "não há / não tem" (você vai ver isso com o Genitivo, a partir do Módulo 4):

```
У меня нет времени.    Não tenho tempo. (literalmente "junto a mim não há tempo")
```

> 💡 Repare: "Да, книга" sem o verbo "é" — o russo responde curto, sem repetir o "é".
""",
                [
                    ex("text", "Traduza: Sim. / Não.", "да нет"),
                    ex("quiz", 'Como responder "sim" em russo?', "Да", ["Да", "Нет", "Пока"]),
                    ex("audio", "Escute e transcreva:", "нет это не книга", audio_text="Нет, это не книга."),
                    ex("quiz", "Além de \"não\", o que \"нет\" também expressa?",
                       "não há / não tem (inexistência)", ["não há / não tem (inexistência)", "sim", "por favor"]),
                    ex("text", "Traduza a resposta: Não, não é um livro. (нет + это + не + книга)", "нет это не книга"),
                ],
            ),
        ],
    )


# ============================================================
# MODULO 4 - Casos: Primeiro Contato (A1) - RASO de proposito
# ============================================================

def build_modulo_04_casos_primeiro_contato():
    return module(
        "modulo-04-casos-primeiro-contato",
        "Módulo 4 — Casos: Primeiro Contato — A1",
        "Os 6 casos gramaticais de relance: reconhecimento e frases fixas comuns por caso, sem tabela de declinação completa. As declinações de verdade ficam para os Módulos 8 (A2) e 11 (B1).",
        [
            topic(
                "o-que-sao-os-casos",
                "O que são os casos gramaticais?",
                """
# O que são os casos gramaticais?

O russo tem **6 casos gramaticais**. Cada um muda a terminação de substantivos, adjetivos e pronomes conforme a **função** deles na frase. É o coração da gramática russa.

## O mapa dos 6 casos

| Caso | Função principal | Exemplo fixo |
|---|---|---|
| Nominativo | sujeito | Студент читает. (O estudante lê.) |
| Acusativo | objeto direto / direção | Меня зовут Анна. (Me chamam Anna.) |
| Genitivo | posse / "de" | У меня есть книга. (Tenho um livro.) |
| Dativo | objeto indireto / sensação | Мне нравится музыка. (Gosto de música.) |
| Instrumental | meio / companhia | Я иду с другом. (Vou com um amigo.) |
| Preposicional | lugar / assunto | Я в школе. (Estou na escola.) |

> ⚠️ **Nota de calibragem**: neste módulo (A1) os casos são só **reconhecimento + frases fixas** — sem tabela de declinação completa. Você vai declinar de verdade no **Módulo 8 (A2)** e aprofundar no **Módulo 11 (B1)**. Por enquanto, memorize as frases como blocos.
""",
                [
                    ex("quiz", "Quantos casos gramaticais o russo tem?",
                       "6", ["4", "6", "8"]),
                    ex("quiz", "O caso do SUJEITO da frase é o:",
                       "Nominativo", ["Nominativo", "Acusativo", "Genitivo"]),
                    ex("quiz", 'Em "У меня есть книга", qual caso é usado para "меня"?',
                       "Genitivo", ["Genitivo", "Dativo", "Instrumental"]),
                    ex("quiz", "O caso que indica LUGAR (ex: в школе) é o:",
                       "Preposicional", ["Preposicional", "Instrumental", "Dativo"]),
                    ex("audio", "Escute e transcreva:", "мне нравится музыка", audio_text="мне нравится музыка"),
                    ex("text", "Complete: os casos mudam a ___ das palavras conforme a função na frase.",
                       "terminação"),
                ],
            ),
            topic(
                "caso-nominativo-contato",
                "Nominativo: o caso do sujeito",
                """
# Nominativo: o caso do sujeito

O **Nominativo** é o caso do **sujeito** — quem pratica a ação, ou do que se fala. É também a forma que aparece nos dicionários (a forma "padrão").

```
Студент читает.        (O estudante lê.)
Книга на столе.        (O livro está na mesa.)
```

> 🎯 Você já vem usando o Nominativo desde o Módulo 1, sem saber! É a forma "básica" de todas as palavras novas que você aprende.
""",
                [
                    ex("quiz", "Para que serve o caso Nominativo?",
                       "Indicar o sujeito da frase", ["Indicar o sujeito da frase", "Indicar posse", "Indicar objeto direto"]),
                    ex("text", "Traduza: O estudante lê. (студент + читает)", "студент читает"),
                    ex("quiz", "A forma do dicionário (a \"padrão\" de toda palavra) é o caso:",
                       "Nominativo", ["Nominativo", "Acusativo", "Dativo"]),
                    ex("audio", "Escute e transcreva:", "книга на столе", audio_text="книга на столе"),
                    ex("speak", "Repita em voz alta:", "студент читает", audio_text="студент читает"),
                ],
            ),
            topic(
                "caso-acusativo-contato",
                "Acusativo: objeto direto e \"меня зовут\"",
                """
# Acusativo: objeto direto e "меня зовут"

O **Acusativo** marca o **objeto direto** (quem recebe a ação) e aparece em frases fixas muito comuns.

## Frases fixas com Acusativo

```
Меня зовут Анна.      Me chamam Anna. / Meu nome é Anna. (меня = Acusativo de я)
Я читаю книгу.        Eu leio o livro. (книгу = Acusativo de книга)
Я вижу студента.      Eu vejo o estudante. (студента = Acusativo animado)
```

> 🎯 **Меня зовут...** ("meu nome é...") é a frase fixa mais importante do Acusativo — memorize como bloco. No Módulo 8 você vai aprender as terminações (feminino -а -> -у, etc.).
""",
                [
                    ex("quiz", 'Como se diz "Meu nome é Anna" (forma fixa)?',
                       "Меня зовут Анна.", ["Меня зовут Анна.", "Я зовут Анна.", "Меня имя Анна."]),
                    ex("text", "Traduza: Eu leio o livro. (я + читаю + книгу)", "я читаю книгу"),
                    ex("quiz", "O caso Acusativo marca o:",
                       "objeto direto", ["objeto direto", "sujeito", "posse"]),
                    ex("audio", "Escute e transcreva:", "я вижу студента", audio_text="я вижу студента"),
                    ex("quiz", 'Em "Я читаю книгу", a palavra "книгу" é o caso:', 
                       "Acusativo", ["Acusativo", "Nominativo", "Genitivo"]),
                ],
            ),
            topic(
                "caso-genitivo-contato",
                "Genitivo: posse e \"у меня есть\"",
                """
# Genitivo: posse e "у меня есть"

O **Genitivo** indica **posse** — equivalente ao "de" do português ("o livro DA Ana"). Também é a base da construção "ter" do russo.

## A construção "ter": у + Genitivo + есть

```
У меня есть книга.      Eu tenho um livro. (literalmente "junto a mim há um livro")
У него есть машина.     Ele tem um carro.
```

> 🎯 **У меня есть...** ("eu tenho...") é a frase fixa mais importante do Genitivo. As declinações de verdade (книга -> книги) ficam para o Módulo 8.
""",
                [
                    ex("quiz", "Como se diz \"eu tenho\" em russo (construção com у + Genitivo)?",
                       "у меня есть", ["у меня есть", "я имею", "я есть"]),
                    ex("text", "Traduza: Eu tenho um livro. (у + меня + есть + книга)", "у меня есть книга"),
                    ex("quiz", "O caso Genitivo indica:",
                       "posse (de quem/de quê)", ["posse (de quem/de quê)", "objeto direto", "lugar"]),
                    ex("audio", "Escute e transcreva:", "у него есть машина", audio_text="у него есть машина"),
                    ex("speak", "Repita em voz alta:", "у меня есть книга", audio_text="у меня есть книга"),
                ],
            ),
            topic(
                "caso-dativo-contato",
                "Dativo: objeto indireto e \"мне нравится\"",
                """
# Dativo: objeto indireto e "мне нравится"

O **Dativo** marca o **objeto indireto** (para quem algo é dado/dito) e aparece em construções impessoais muito comuns.

## Construção impessoal: Dativo + нравится/нужно

```
Мне нравится музыка.      Eu gosto de música. (literalmente "para mim agrada música")
Мне нужно время.          Eu preciso de tempo. ("para mim é necessário tempo")
```

> 🎯 **Мне нравится...** ("eu gosto de...") é a frase fixa mais importante do Dativo. A lógica é invertida: "para mim agrada" em vez de "eu gosto". No Módulo 8 você aprende as terminações.
""",
                [
                    ex("text", "Traduza: Eu gosto de música. (мне + нравится + музыка)", "мне нравится музыка"),
                    ex("quiz", "O caso Dativo marca:",
                       "o objeto indireto (para quem)", ["o objeto indireto (para quem)", "o sujeito", "posse"]),
                    ex("quiz", 'Qual a forma de "я" (eu) no Dativo?',
                       "мне", ["мне", "меня", "мной"]),
                    ex("audio", "Escute e transcreva:", "мне нужно время", audio_text="мне нужно время"),
                    ex("quiz", 'Em "Мне нравится музыка", a lógica é:',
                       "para mim agrada música", ["para mim agrada música", "eu agrado música", "música me tem"]),
                ],
            ),
            topic(
                "caso-instrumental-e-preposicional-contato",
                "Instrumental e Preposicional: \"с другом\" e \"в школе\"",
                """
# Instrumental e Preposicional: "с другом" e "в школе"

Os dois últimos casos, também com frases fixas clássicas:

## Instrumental (meio/companhia)

```
Я иду с другом.          Eu vou com um amigo. (с + другом = Instrumental)
Я пишу ручкой.           Eu escrevo com uma caneta. (ручкой = Instrumental)
```

## Preposicional (lugar/assunto) — só existe depois de preposição

```
Я в школе.               Eu estou na escola. (в + школе = Preposicional)
Я думаю о тебе.          Eu penso em você. (о + тебе = Preposicional)
```

> 🎯 Duas frases fixas valiosas: **с другом** ("com um amigo", Instrumental) e **в школе** ("na escola", Preposicional). Elas voltam no Módulo 8 com as terminações completas.
""",
                [
                    ex("text", "Traduza: Eu estou na escola. (я + в + школе)", "я в школе"),
                    ex("quiz", 'Em "Я иду с другом", qual caso é "с другом"?',
                       "Instrumental", ["Instrumental", "Acusativo", "Nominativo"]),
                    ex("quiz", "O caso Preposicional só aparece:",
                       "depois de uma preposição (в, на, о)", ["depois de uma preposição (в, на, о)", "sozinho, sem preposição", "apenas no plural"]),
                    ex("audio", "Escute e transcreva:", "я думаю о тебе", audio_text="я думаю о тебе"),
                    ex("quiz", 'Em "Я в школе", qual caso é "в школе"?',
                       "Preposicional", ["Preposicional", "Instrumental", "Dativo"]),
                    ex("speak", "Repita em voz alta:", "я иду с другом", audio_text="я иду с другом"),
                ],
            ),
        ],
    )


# ============================================================
# MODULO 5 - Vocabulario e Comunicacao (A1)
# ============================================================

def build_modulo_05_vocabulario_e_comunicacao_a1():
    return module(
        "modulo-05-vocabulario-e-comunicacao-a1",
        "Módulo 5 — Vocabulário e Comunicação — A1",
        "Rotina, família, lugares, comida, apresentações e pedidos simples — com frases fixas que já flexionam os casos vistos no Módulo 4.",
        [
            topic(
                "rotina-diaria",
                "Rotina diária",
                """
# Rotina diária

| Russo | Português |
|---|---|
| я встаю | eu me levanto |
| я завтракаю | eu tomo café da manhã |
| я работаю | eu trabalho |
| я учусь | eu estudo |
| я отдыхаю | eu descanso |
| я сплю | eu durmo |

## Exemplos

```
Я встаю в семь часов.       Eu me levanto às sete horas.
Я работаю в офисе.          Eu trabalho no escritório. (в + офисе = Preposicional, M4)
Я учусь в школе.            Eu estudo na escola.
```

> 🎯 Repare no espiral: "в офисе", "в школе" já usam o Preposicional visto no Módulo 4. A rotina é um ótimo lugar para praticar o caso fixo "в + lugar".
""",
                [
                    ex("text", "Traduza: Eu me levanto. (я + встаю)", "я встаю"),
                    ex("quiz", 'Como se diz "eu trabalho"?', "я работаю", ["я работаю", "я отдыхаю", "я сплю"]),
                    ex("quiz", 'Em "Я работаю в офисе", o caso de "в офисе" é:', 
                       "Preposicional", ["Preposicional", "Nominativo", "Acusativo"]),
                    ex("audio", "Escute e transcreva:", "я учусь в школе", audio_text="я учусь в школе"),
                    ex("speak", "Repita em voz alta:", "я встаю в семь часов", audio_text="я встаю в семь часов"),
                    ex("text", "Traduza: Eu estudo na escola. (я + учусь + в + школе)", "я учусь в школе"),
                ],
            ),
            topic(
                "familia-e-pessoas",
                "Família e pessoas",
                """
# Família e pessoas

| Russo | Português |
|---|---|
| мама | mãe |
| папа | pai |
| брат | irmão |
| сестра | irmã |
| друг | amigo |
| семья | família |
| человек | pessoa |

## Exemplos

```
Это моя мама.        Esta é a minha mãe.
У меня есть брат.    Eu tenho um irmão. (у + меня = Genitivo, M4)
Я иду с другом.      Eu vou com um amigo. (с + другом = Instrumental, M4)
```

> 🎯 Três casos do Módulo 4 aparecem aqui: Nominativo ("это моя мама"), Genitivo ("у меня есть брат") e Instrumental ("с другом").
""",
                [
                    ex("text", "Traduza: Esta é a minha mãe. (это + моя + мама)", "это моя мама"),
                    ex("quiz", 'Como se diz "irmã"?', "сестра", ["сестра", "брат", "мама"]),
                    ex("quiz", 'Em "У меня есть брат", o caso de "меня" é:', 
                       "Genitivo", ["Genitivo", "Dativo", "Acusativo"]),
                    ex("audio", "Escute e transcreva:", "у меня есть брат", audio_text="у меня есть брат"),
                    ex("quiz", 'Em "Я иду с другом", o caso de "с другом" é:', 
                       "Instrumental", ["Instrumental", "Preposicional", "Nominativo"]),
                    ex("text", "Traduza: Eu vou com um amigo. (я + иду + с + другом)", "я иду с другом"),
                ],
            ),
            topic(
                "lugares-na-cidade-russo",
                "Lugares na cidade",
                """
# Lugares na cidade

| Russo | Português |
|---|---|
| школа | escola |
| магазин | loja |
| дом | casa |
| город | cidade |
| парк | parque |
| работа | trabalho (local) |
| улица | rua |

## Exemplos

```
Я иду в школу.        Eu vou para a escola. (в + школу = Acusativo de direção, M4)
Я в магазине.         Eu estou na loja. (в + магазине = Preposicional de lugar, M4)
Это мой город.        Esta é a minha cidade.
```

> 🎯 Contraste clássico: **в школу** (para onde vou — Acusativo) vs **в магазине** (onde estou — Preposicional). No Módulo 8 isso fica completo.
""",
                [
                    ex("text", "Traduza: Eu estou na loja. (я + в + магазине)", "я в магазине"),
                    ex("quiz", 'Em "Я иду в школу", o caso é (direção):', 
                       "Acusativo", ["Acusativo", "Preposicional", "Nominativo"]),
                    ex("quiz", 'Em "Я в магазине", o caso é (lugar):', 
                       "Preposicional", ["Preposicional", "Acusativo", "Genitivo"]),
                    ex("audio", "Escute e transcreva:", "я иду в школу", audio_text="я иду в школу"),
                    ex("speak", "Repita em voz alta:", "это мой город", audio_text="это мой город"),
                    ex("quiz", 'Como se diz "casa"?', "дом", ["дом", "школа", "парк"]),
                ],
            ),
            topic(
                "comida-e-bebida",
                "Comida e bebida",
                """
# Comida e bebida

| Russo | Português |
|---|---|
| хлеб | pão |
| вода | água |
| чай | chá |
| кофе | café |
| молоко | leite |
| яблоко | maçã |
| еда | comida |

## Exemplos

```
Я пью чай.          Eu bebo chá. (чай = Acusativo, M4)
Я люблю кофе.       Eu gosto de café.
Мне нравится хлеб.  Eu gosto de pão. (мне = Dativo, M4)
```

> 🎯 Repare: "я пью чай" (objeto direto no Acusativo) e "мне нравится хлеб" (Dativo impessoal) — dois casos do Módulo 4 em frases de comida.
""",
                [
                    ex("text", "Traduza: Eu bebo chá. (я + пью + чай)", "я пью чай"),
                    ex("quiz", 'Como se diz "água"?', "вода", ["вода", "хлеб", "чай"]),
                    ex("quiz", 'Em "Я пью чай", o caso de "чай" é:', 
                       "Acusativo", ["Acusativo", "Nominativo", "Dativo"]),
                    ex("audio", "Escute e transcreva:", "я люблю кофе", audio_text="я люблю кофе"),
                    ex("quiz", 'Em "Мне нравится хлеб", o caso de "мне" é:', 
                       "Dativo", ["Dativo", "Genitivo", "Preposicional"]),
                    ex("text", "Traduza: Eu gosto de pão (impessoal). (мне + нравится + хлеб)", "мне нравится хлеб"),
                ],
            ),
            topic(
                "apresentacoes-basicas",
                "Apresentações básicas",
                """
# Apresentações básicas

| Russo | Português |
|---|---|
| Как тебя зовут? | Qual é o seu nome? (informal) |
| Меня зовут... | Meu nome é... |
| Это мой друг. | Este é o meu amigo. |
| Очень приятно! | Muito prazer! |
| Откуда ты? | De onde você é? |
| Я из Бразилии. | Eu sou do Brasil. (из + Бразилии = Genitivo, M4) |

> 🎯 "Меня зовут" (Acusativo) e "Я из Бразилии" (Genitivo) — duas frases fixas que já flexionam casos. Memorize como blocos.
""",
                [
                    ex("quiz", 'Como se diz "Meu nome é..." (frase fixa)?',
                       "Меня зовут...", ["Меня зовут...", "Я зовут...", "Меня имя..."]),
                    ex("text", "Traduza: Muito prazer! (Очень + приятно)", "очень приятно"),
                    ex("quiz", 'Em "Я из Бразилии", o caso de "из Бразилии" é:', 
                       "Genitivo", ["Genitivo", "Acusativo", "Dativo"]),
                    ex("audio", "Escute e transcreva:", "я из бразилии", audio_text="Я из Бразилии."),
                    ex("speak", "Repita em voz alta:", "меня зовут анна", audio_text="Меня зовут Анна."),
                    ex("quiz", 'Como se pergunta "De onde você é?" (informal)?',
                       "Откуда ты?", ["Откуда ты?", "Где ты?", "Куда ты?"]),
                ],
            ),
            topic(
                "pedidos-simples-russo",
                "Pedidos simples",
                """
# Pedidos simples

| Russo | Português |
|---|---|
| Можно...? | Pode...? / Posso...? |
| Дайте, пожалуйста... | Dê-me, por favor... |
| Спасибо! | Obrigado! |
| Пожалуйста! | Por favor / De nada! |
| Извините! | Desculpe / Com licença! |

## Exemplos

```
Можно воды?              Posso [ter] água? (воды = Genitivo de quantidade, M4)
Дайте, пожалуйста, чай.  Dê-me chá, por favor. (чай = Acusativo)
Спасибо большое!         Muito obrigado!
```

> 🎯 "Можно воды?" usa o Genitivo para "um pouco de água" — mesmo caso de "у меня нет времени". O espiral continua!
""",
                [
                    ex("text", "Traduza: Obrigado! / Por favor!", "спасибо пожалуйста"),
                    ex("quiz", 'Como pedir educadamente "Posso [ter] água?"',
                       "Можно воды?", ["Можно воды?", "Дайте вода!", "Хочу вода!"]),
                    ex("quiz", 'Em "Можно воды?", o caso de "воды" é:', 
                       "Genitivo", ["Genitivo", "Acusativo", "Dativo"]),
                    ex("audio", "Escute e transcreva:", "дайте пожалуйста чай", audio_text="Дайте, пожалуйста, чай."),
                    ex("speak", "Repita em voz alta:", "спасибо большое", audio_text="Спасибо большое!"),
                    ex("quiz", 'Como se diz "Desculpe / Com licença"?', 
                       "Извините", ["Извините", "Пожалуйста", "Привет"]),
                ],
            ),
        ],
    )


# ============================================================
# MODULO 6 - Presente dos Verbos (A2)
# ============================================================

def build_modulo_06_presente_dos_verbos():
    return module(
        "modulo-06-presente-dos-verbos",
        "Módulo 6 — Presente dos Verbos — A2",
        "As duas conjugações do presente, os verbos irregulares mais comuns, verbos da rotina e perguntas/negação no presente.",
        [
            topic(
                "primeira-conjugacao",
                "Presente: 1ª conjugação",
                """
# Presente: 1ª conjugação

Verbos russos têm duas conjugações principais no presente. Vamos começar pela **1ª conjugação**, com verbos terminados em **-ать/-ять** no infinitivo (ex: читать, "ler"):

| Pessoa | читать (ler) |
|---|---|
| я | читаю |
| ты | читаешь |
| он/она | читает |
| мы | читаем |
| вы | читаете |
| они | читают |

> 🎯 Repare no padrão: -ю/-у, -ешь, -ет, -ем, -ете, -ют/-ут — essas terminações se repetem em quase todos os verbos da 1ª conjugação.

## Outro exemplo: работать (trabalhar)

```
я работаю        eu trabalho
ты работаешь     você trabalha
он работает      ele trabalha
```

Repare que é exatamente o mesmo padrão de terminações de читать — uma vez que você memoriza o padrão, ele se aplica a centenas de verbos.
""",
                [
                    ex("quiz", 'Complete: "Я ___ книгу." (eu leio)',
                       "читаю", ["читаю", "читаешь", "читает"]),
                    ex("text", "Traduza: Ela lê. (она + читает)", "она читает"),
                    ex("quiz", 'Qual a terminação de "вы" (vocês/você formal) na 1ª conjugação?',
                       "-ете", ["-ете", "-ешь", "-ют"]),
                    ex("audio", "Escute e transcreva:", "он работает", audio_text="он работает"),
                    ex("speak", "Repita em voz alta:", "я читаю книгу", audio_text="я читаю книгу"),
                    ex("text", "Complete: Я ___ (leio) книгу.", "читаю"),
                ],
            ),
            topic(
                "segunda-conjugacao",
                "Presente: 2ª conjugação",
                """
# Presente: 2ª conjugação

A **2ª conjugação** é usada por verbos terminados em **-ить** no infinitivo (ex: говорить, "falar"):

| Pessoa | говорить (falar) |
|---|---|
| я | говорю |
| ты | говоришь |
| он/она | говорит |
| мы | говорим |
| вы | говорите |
| они | говорят |

> 💡 Repare que a 2ª conjugação usa -у/-ю, -ишь, -ит, -им, -ите, -ят/-ат — parecido com a 1ª, mas com "и" no meio da maioria das terminações.

## Como saber qual conjugação usar

A regra prática: olhe a terminação do **infinitivo**. Termina em **-ить**? Quase sempre 2ª conjugação. Termina em **-ать/-ять/-еть/-уть** (e outras)? Geralmente 1ª conjugação. Como todo padrão em russo, há exceções (você já viu uma: хотеть, no próximo tópico).
""",
                [
                    ex("quiz", 'Complete: "Он ___ по-русски." (ele fala russo)',
                       "говорит", ["говорит", "говорю", "говорят"]),
                    ex("text", "Traduza: Nós falamos. (мы + говорим)", "мы говорим"),
                    ex("quiz", "Qual terminação de infinitivo geralmente indica a 2ª conjugação?",
                       "-ить", ["-ить", "-ать", "-еть"]),
                    ex("audio", "Escute e transcreva:", "вы говорите", audio_text="вы говорите"),
                    ex("speak", "Repita em voz alta:", "я говорю по-русски", audio_text="я говорю по-русски"),
                    ex("quiz", 'Complete: "Они ___ по-русски." (eles falam russo)',
                       "говорят", ["говорят", "говорит", "говоришь"]),
                ],
            ),
            topic(
                "verbos-irregulares-comuns",
                "Verbos irregulares comuns",
                """
# Verbos irregulares comuns

Alguns verbos muito usados fogem das duas conjugações regulares — vale decorar de cor.

## хотеть (querer) — mistura as duas conjugações!

| Pessoa | хотеть |
|---|---|
| я | хочу |
| ты | хочешь |
| он/она | хочет |
| мы | хотим |
| вы | хотите |
| они | хотят |

## идти (ir, a pé, agora)

| Pessoa | идти |
|---|---|
| я | иду |
| ты | идёшь |
| он/она | идёт |
| мы | идём |
| вы | идёте |
| они | идут |

## есть (comer) — outro irregular comum

```
я ем        eu como
ты ешь      você come
он ест      ele come
мы едим     nós comemos
```
""",
                [
                    ex("quiz", 'Complete: "Я ___ есть." (eu quero comer)',
                       "хочу", ["хочу", "хочешь", "хотим"]),
                    ex("text", "Traduza: Eu vou (a pé, agora). (я + иду)", "я иду"),
                    ex("quiz", 'Como se diz "ele come"?',
                       "он ест", ["он ест", "он ем", "он едим"]),
                    ex("audio", "Escute e transcreva:", "они хотят", audio_text="они хотят"),
                    ex("speak", "Repita em voz alta:", "я иду домой", audio_text="я иду домой"),
                    ex("quiz", 'Complete: "Мы ___ есть." (nós comemos)',
                       "едим", ["едим", "ем", "ест"]),
                ],
            ),
            topic(
                "verbos-comuns-da-rotina",
                "Verbos comuns da rotina",
                """
# Verbos comuns da rotina

Verbos que você vai usar todos os dias, nas duas conjugações:

| Infinitivo | Significado | 1ª pessoa (я) |
|---|---|---|
| работать | trabalhar | работаю |
| жить | morar / viver | живу |
| понимать | entender | понимаю |
| любить | amar / gostar | люблю |
| хотеть | querer | хочу |
| знать | saber | знаю |

## Exemplos

```
Я живу в Бразилии.        Eu moro no Brasil. (в + Бразилии = Preposicional, M4/M5)
Я понимаю по-русски.     Eu entendo russo.
Я люблю музыку.          Eu gosto de música. (музыку = Acusativo, M4)
```

> 🎯 Observe o espiral: "я живу в Бразилии" (Preposicional) e "я люблю музыку" (Acusativo) — os casos do Módulo 4 em verbos da rotina.
""",
                [
                    ex("text", "Traduza: Eu moro no Brasil. (я + живу + в + Бразилии)", "я живу в бразилии"),
                    ex("quiz", 'Como se diz "eu entendo"?', "я понимаю", ["я понимаю", "я работаю", "я знаю"]),
                    ex("quiz", 'Em "Я люблю музыку", o caso de "музыку" é:', 
                       "Acusativo", ["Acusativo", "Nominativo", "Dativo"]),
                    ex("audio", "Escute e transcreva:", "я понимаю по-русски", audio_text="я понимаю по-русски"),
                    ex("speak", "Repita em voz alta:", "я живу в бразилии", audio_text="Я живу в Бразилии."),
                    ex("quiz", 'Como se diz "eu sei"?', "я знаю", ["я знаю", "я люблю", "я живу"]),
                ],
            ),
            topic(
                "perguntas-e-negacao-no-presente",
                "Perguntas e negação no presente",
                """
# Perguntas e negação no presente

No presente, perguntar é só usar a entonação (ou uma palavra interrogativa) — o verbo não muda de ordem:

```
Ты говоришь по-русски?     Você fala russo?
Что ты читаешь?            O que você lê?
```

## Negação com не

```
Я не говорю по-русски.     Eu não falo russo.
Он не работает сегодня.    Ele não trabalha hoje.
```

## A resposta curta

```
— Ты работаешь?      — Você trabalha?
— Да, работаю.       — Sim, trabalho.
— Нет, не работаю.   — Não, não trabalho.
```

> 💡 Diferente do inglês (do/does), no russo basta **não** (не) antes do verbo e a entonação para perguntar.
""",
                [
                    ex("text", "Traduza: Você fala russo? (ты + говоришь + по-русски)", "ты говоришь по-русски"),
                    ex("quiz", 'Como se nega "Я работаю"?',
                       "Я не работаю.", ["Я не работаю.", "Я работаю не.", "Не я работаю."]),
                    ex("audio", "Escute e transcreva:", "я не говорю по-русски", audio_text="я не говорю по-русски"),
                    ex("quiz", 'Para responder "Não, não trabalho", você diz:',
                       "Нет, не работаю.", ["Нет, не работаю.", "Да, работаю.", "Нет, работаю."]),
                    ex("speak", "Repita em voz alta:", "ты говоришь по-русски", audio_text="Ты говоришь по-русски?"),
                    ex("quiz", 'Qual pergunta pergunta "o que você lê?"',
                       "Что ты читаешь?", ["Что ты читаешь?", "Как ты читаешь?", "Где ты читаешь?"]),
                ],
            ),
        ],
    )


# ============================================================
# MODULO 7 - Vocabulario e Comunicacao (A2)
# ============================================================

def build_modulo_07_vocabulario_e_comunicacao_a2():
    return module(
        "modulo-07-vocabulario-e-comunicacao-a2",
        "Módulo 7 — Vocabulário e Comunicação — A2",
        "Cidade e direções, viagem, compras, restaurante, pedidos educados e localização — com lacunas que obrigam a flexionar os casos já vistos.",
        [
            topic(
                "cidade-e-direcoes",
                "Cidade e direções",
                """
# Cidade e direções

| Russo | Português |
|---|---|
| где находится...? | onde fica...? |
| налево | à esquerda |
| направо | à direita |
| прямо | em frente |
| рядом | perto |
| далеко | longe |

## Exemplos

```
Где находится вокзал?       Onde fica a estação?
Идите прямо.                Vá em frente.
Магазин рядом с домом.      A loja é perto de casa. (с + домом = Instrumental)
```

> 🎯 Lacuna de caso: "Магазин рядом с ___" (дом) exige o **Instrumental** (домом). O espiral do Módulo 4 aparece aqui.
""",
                [
                    ex("text", "Traduza: Onde fica a estação? (где + находится + вокзал)", "где находится вокзал"),
                    ex("quiz", 'Complete no Instrumental: "Магазин рядом с ___." (дом)',
                       "домом", ["домом", "дом", "дома"]),
                    ex("quiz", 'Como se diz "à direita"?', "направо", ["направо", "налево", "прямо"]),
                    ex("audio", "Escute e transcreva:", "идите прямо", audio_text="Идите прямо."),
                    ex("speak", "Repita em voz alta:", "где находится вокзал", audio_text="Где находится вокзал?"),
                    ex("quiz", 'Complete no Instrumental: "Я иду ___ с тобой." (junto, с)',
                       "с тобой", ["с тобой", "с ты", "с тебя"]),
                ],
            ),
            topic(
                "viagem-em-russo",
                "Viagem",
                """
# Viagem

| Russo | Português |
|---|---|
| билет | bilhete / passagem |
| поезд | trem |
| самолёт | avião |
| вокзал | estação (trem) |
| аэропорт | aeroporto |
| поездка | viagem |
| багаж | bagagem |

## Exemplos

```
Я покупаю билет.           Eu compro o bilhete. (билет = Acusativo)
Он едет на поезде.         Ele vai de trem. (на + поезде = Preposicional de meio)
Сколько стоит билет?       Quanto custa o bilhete?
```

> 🎯 Lacunas de caso: "билет" no Acusativo ("я покупаю ___") e "на поезде" no Preposicional ("он едет на ___"). Os casos do Módulo 4 em ação.
""",
                [
                    ex("text", "Traduza: Eu compro o bilhete. (я + покупаю + билет)", "я покупаю билет"),
                    ex("quiz", 'Complete no Acusativo: "Я покупаю ___." (bilhete)',
                       "билет", ["билет", "билета", "билете"]),
                    ex("quiz", 'Complete no Preposicional: "Он едет на ___." (trem)',
                       "поезде", ["поезде", "поезд", "поезда"]),
                    ex("audio", "Escute e transcreva:", "сколько стоит билет", audio_text="Сколько стоит билет?"),
                    ex("quiz", 'Como se diz "aeroporto"?', "аэропорт", ["аэропорт", "вокзал", "билет"]),
                    ex("speak", "Repita em voz alta:", "я покупаю билет", audio_text="Я покупаю билет."),
                ],
            ),
            topic(
                "compras",
                "Compras",
                """
# Compras

| Russo | Português |
|---|---|
| сколько стоит...? | quanto custa...? |
| купить | comprar |
| магазин | loja |
| деньги | dinheiro |
| дорого | caro |
| дёшево | barato |

## Exemplos

```
Сколько стоит это?        Quanto custa isso?
Я хочу купить хлеб.       Eu quero comprar pão. (хлеб = Acusativo)
Это дорого!               Isto é caro!
```

> 🎯 Lacuna de caso: "купить ___" (objeto direto) exige o **Acusativo**: "Я хочу купить хлеб", "купить книгу".
""",
                [
                    ex("text", "Traduza: Eu quero comprar pão. (я + хочу + купить + хлеб)", "я хочу купить хлеб"),
                    ex("quiz", 'Complete no Acusativo: "Я хочу купить ___." (livro)',
                       "книгу", ["книгу", "книга", "книге"]),
                    ex("quiz", 'Como se diz "caro"?', "дорого", ["дорого", "дёшево", "магазин"]),
                    ex("audio", "Escute e transcreva:", "сколько стоит это", audio_text="Сколько стоит это?"),
                    ex("speak", "Repita em voz alta:", "это дорого", audio_text="Это дорого!"),
                    ex("quiz", 'Como se pergunta "Quanto custa isso?"',
                       "Сколько стоит это?", ["Сколько стоит это?", "Где это?", "Куда это?"]),
                ],
            ),
            topic(
                "restaurante",
                "Restaurante",
                """
# Restaurante

| Russo | Português |
|---|---|
| меню | cardápio |
| заказать | pedir |
| счёт | conta |
| суп | sopa |
| салат | salada |
| вкусно | gostoso |

## Exemplos

```
Можно меню, пожалуйста?        Pode me dar o cardápio, por favor?
Я хочу заказать суп.            Eu quero pedir uma sopa. (суп = Acusativo)
Счёт, пожалуйста!               A conta, por favor!
```

> 🎯 Lacuna de caso: "заказать ___" (объект direto) exige o **Acusativo**: "заказать суп", "заказать салат".
""",
                [
                    ex("text", "Traduza: Eu quero pedir uma sopa. (я + хочу + заказать + суп)", "я хочу заказать суп"),
                    ex("quiz", 'Complete no Acusativo: "Я хочу заказать ___." (salada)',
                       "салат", ["салат", "салата", "салате"]),
                    ex("quiz", 'Como se pede a conta?', "Счёт, пожалуйста!", ["Счёт, пожалуйста!", "Меню, пожалуйста!", "Спасибо!"]),
                    ex("audio", "Escute e transcreva:", "можно меню пожалуйста", audio_text="Можно меню, пожалуйста?"),
                    ex("speak", "Repita em voz alta:", "я хочу заказать суп", audio_text="Я хочу заказать суп."),
                    ex("quiz", 'Como se diz "gostoso"?', "вкусно", ["вкусно", "дорого", "прямо"]),
                ],
            ),
            topic(
                "pedidos-educados",
                "Pedidos educados",
                """
# Pedidos educados

| Russo | Português |
|---|---|
| Можно...? | Pode...? / Posso...? |
| Дайте, пожалуйста... | Dê-me, por favor... |
| Помогите, пожалуйста! | Ajude-me, por favor! |
| Извините! | Desculpe / Com licença! |

## Exemplos

```
Помогите мне, пожалуйста!        Ajude-me, por favor! (мне = Dativo)
Можно мне воды?                  Posso [ter] um pouco de água? (мне = Dativo, воды = Genitivo)
Дайте, пожалуйста, меню.         Dê-me o cardápio, por favor. (меню = Acusativo)
```

> 🎯 Lacuna de caso: "Помогите ___" exige o **Dativo** (мне). E "Можно ___ воды?" combina Dativo (мне) + Genitivo (воды) — dois casos do Módulo 4 na mesma frase!
""",
                [
                    ex("text", "Traduza: Ajude-me, por favor! (Помогите + мне + пожалуйста)", "помогите мне пожалуйста"),
                    ex("quiz", 'Complete no Dativo: "Помогите ___ , пожалуйста!" (eu)',
                       "мне", ["мне", "меня", "мной"]),
                    ex("quiz", 'Em "Можно мне воды?", qual caso é "воды"?', 
                       "Genitivo", ["Genitivo", "Acusativo", "Dativo"]),
                    ex("audio", "Escute e transcreva:", "можно мне воды", audio_text="Можно мне воды?"),
                    ex("speak", "Repita em voz alta:", "помогите мне пожалуйста", audio_text="Помогите мне, пожалуйста!"),
                    ex("quiz", 'Qual é um pedido educado?',
                       "Можно мне чай?", ["Можно мне чай?", "Хочу чай!", "Чай сейчас!"]),
                ],
            ),
            topic(
                "localizar-objetos",
                "Localizando objetos",
                """
# Localizando objetos

Para dizer onde algo está, use **в/на + Preposicional** — o caso de lugar do Módulo 4:

| Russo | Português |
|---|---|
| где мой...? | onde está meu...? |
| на столе | sobre a mesa |
| в сумке | na bolsa |
| под столом | debaixo da mesa (Instrumental) |
| рядом | perto |

## Exemplos

```
Где мой телефон?          Onde está meu telefone?
Телефон на столе.        O telefone está sobre a mesa. (на + столе = Preposicional)
Ключи в сумке.           As chaves estão na bolsa. (в + сумке = Preposicional)
```

> 🎯 Lacuna de caso: "на ___" (стол) e "в ___" (сумка) exigem o **Preposicional**: столе, сумке. O espiral do M4 vira rotina.
""",
                [
                    ex("text", "Traduza: O telefone está sobre a mesa. (телефон + на + столе)", "телефон на столе"),
                    ex("quiz", 'Complete no Preposicional: "Ключи в ___." (bolsa)',
                       "сумке", ["сумке", "сумка", "сумку"]),
                    ex("quiz", 'Complete no Preposicional: "Книга на ___." (mesa)',
                       "столе", ["столе", "стол", "стола"]),
                    ex("audio", "Escute e transcreva:", "где мой телефон", audio_text="Где мой телефон?"),
                    ex("speak", "Repita em voz alta:", "телефон на столе", audio_text="Телефон на столе."),
                    ex("quiz", 'Como se diz "na bolsa"?', "в сумке", ["в сумке", "на сумке", "под сумке"]),
                ],
            ),
        ],
    )


# ============================================================
# MODULO 8 - Casos Intermediarios (A2)
# ============================================================

def build_modulo_08_casos_intermediarios():
    return module(
        "modulo-08-casos-intermediarios",
        "Módulo 8 — Casos Intermediários — A2",
        "As declinações de verdade dos casos: Preposicional, Acusativo, Genitivo, Dativo, Instrumental e o plural em todos os casos — aprofundando o primeiro contato do Módulo 4.",
        [
            topic(
                "preposicional-lugar-e-assunto",
                "Preposicional: lugar (в/на) e assunto (о/об)",
                """
# Preposicional: lugar (в/на) e assunto (о/об)

O **Preposicional** é o caso de **lugar** (com в/на) e de **assunto** (com о/об). Ele só existe **depois de uma preposição** — por isso o nome.

## Terminações no Preposicional (singular)

| Gênero | Terminação | Exemplo (Nominativo -> Preposicional) |
|---|---|---|
| Masculino/Neutro | -е | стол -> столе, окно -> окне |
| Feminino (-а) | -е | комната -> комнате |
| Feminino (-ь) | -и | дверь -> двери |

## Lugar: в (dentro de) e на (em cima de)

```
Книга на столе.         O livro está na mesa.
Я в комнате.             Eu estou no quarto.
Он живёт в Москве.       Ele mora em Moscou.
```

## Assunto: о/об (sobre)

```
Я думаю о тебе.             Eu penso em você.
Мы говорим о книге.         Nós falamos sobre o livro.
Она рассказывает об Америке. Ela fala sobre a América. (об antes de vogal)
```

> 🎯 Repare: о vira **об** antes de palavra iniciada por som de vogal. E "я в комнате" já significa "eu estou no quarto", sem verbo "estar".
""",
                [
                    ex("text", 'Complete a frase com a forma correta de "стол" no Preposicional: "Книга на ___."',
                       "столе"),
                    ex("quiz", 'Qual preposição indica "dentro de" + Preposicional?',
                       "в", ["в", "на", "о"]),
                    ex("text", "Traduza: Ele mora em Moscou. (он + живёт + в + Москве)",
                       "он живёт в москве"),
                    ex("quiz", "Qual forma de \"о\" se usa antes de palavra iniciada por som de vogal?",
                       "об", ["об", "о", "на"]),
                    ex("text", "Traduza: Nós falamos sobre o livro. (мы + говорим + о + книге)",
                       "мы говорим о книге"),
                    ex("audio", "Escute e transcreva:", "я в комнате", audio_text="я в комнате"),
                    ex("speak", "Repita em voz alta:", "книга на столе", audio_text="книга на столе"),
                ],
            ),
            topic(
                "preposicional-pronomes",
                "Preposicional dos pronomes pessoais",
                """
# Preposicional dos pronomes pessoais

Assim como os substantivos, os pronomes pessoais também mudam de forma no Preposicional:

| Nominativo | Preposicional (о + ...) |
|---|---|
| я | обо мне |
| ты | о тебе |
| он/оно | о нём |
| она | о ней |
| мы | о нас |
| вы | о вас |
| они | о них |

```
Он думает обо мне.       Ele pensa em mim.
Мы говорим о них.        Nós falamos sobre eles.
```

> ⚠️ Repare em "обо мне" — antes de "мне" o "о" ganha um "о" extra (obo) só por causa da pronúncia, é uma exceção que vale decorar de cor.
""",
                [
                    ex("quiz", 'Qual a forma de "я" (eu) depois de "о" no Preposicional?',
                       "обо мне", ["обо мне", "о мне", "о меня"]),
                    ex("text", "Traduza: Nós falamos sobre eles. (мы + говорим + о + них)",
                       "мы говорим о них"),
                    ex("quiz", 'Qual a forma de "она" (ela) no Preposicional?',
                       "о ней", ["о ней", "о она", "о неё"]),
                    ex("audio", "Escute e transcreva:", "он думает обо мне", audio_text="он думает обо мне"),
                    ex("quiz", 'Qual a forma de "ты" (você) no Preposicional?',
                       "о тебе", ["о тебе", "о ты", "о тебя"]),
                    ex("text", "Complete: Я думаю ___ (sobre você).", "о тебе"),
                ],
            ),
            topic(
                "acusativo-objeto-e-direcao",
                "Acusativo: objeto direto, direção e animados",
                """
# Acusativo: objeto direto, direção e animados

O **Acusativo** marca o **objeto direto** e o **destino** (para onde).

## Terminações no Acusativo (singular)

| Gênero | Regra | Exemplo |
|---|---|---|
| Masculino inanimado | igual ao Nominativo | Я читаю журнал. (Eu leio a revista.) |
| Masculino animado | igual ao Genitivo | Я вижу студента. (Eu vejo o estudante.) |
| Feminino (-а -> -у) | -а vira -у | Я читаю книгу. (Eu leio o livro.) |
| Neutro | igual ao Nominativo | Я вижу окно. (Eu vejo a janela.) |

> ⚠️ Repare na diferença entre substantivos **animados** (pessoas/animais) e **inanimados** (objetos) — isso afeta a terminação no masculino.

## Direção: в/на + Acusativo (para onde)

```
Я в школе.           (Preposicional) Eu estou NA escola.
Я иду в школу.       (Acusativo)     Eu vou PARA a escola.
```

## Pronomes no Acusativo

я -> меня, ты -> тебя, он/оно -> его, она -> её, мы -> нас, вы -> вас, они -> их

```
Я люблю тебя.         Eu te amo.
Он видит меня.        Ele me vê.
```
""",
                [
                    ex("quiz", 'Como fica "книга" (livro) no Acusativo?',
                       "книгу", ["книгу", "книге", "книги"]),
                    ex("text", "Traduza: Eu leio o livro. (я + читаю + книгу)",
                       "я читаю книгу"),
                    ex("quiz", "No Acusativo, um substantivo masculino INANIMADO (ex: журнал):",
                       "fica igual ao Nominativo", ["fica igual ao Nominativo", "muda para -а", "muda para -у"]),
                    ex("quiz", 'Qual caso indica "PARA ONDE" (movimento/direção)?',
                       "Acusativo", ["Acusativo", "Preposicional", "Nominativo"]),
                    ex("text", "Traduza: Eu vou para a escola. (я + иду + в + школу)",
                       "я иду в школу"),
                    ex("quiz", 'Qual a forma de "я" (eu) no Acusativo?',
                       "меня", ["меня", "мне", "я"]),
                    ex("audio", "Escute e transcreva:", "я вижу студента", audio_text="я вижу студента"),
                    ex("speak", "Repita em voz alta:", "я читаю книгу", audio_text="я читаю книгу"),
                ],
            ),
            topic(
                "genitivo-posse-e-quantidade",
                "Genitivo: posse, у+есть, нет e quantidades",
                """
# Genitivo: posse, у+есть, нет e quantidades

O **Genitivo** indica **posse**, é a base da construção "ter" e das quantidades.

## Terminações no Genitivo (singular)

| Gênero | Terminação | Exemplo |
|---|---|---|
| Masculino/Neutro | -а/-я | стол -> стола, окно -> окна |
| Feminino (-а) | -ы/-и | книга -> книги |

## A construção "ter": у + Genitivo + есть

```
У меня есть книга.       Eu tenho um livro.
У него есть машина.      Ele tem um carro.
```

## "Não há / não tenho" — нет + Genitivo

```
У меня нет книги.        Eu não tenho um livro.
Здесь нет воды.          Aqui não há água.
```

## Quantidades

Depois de **2, 3, 4**: Genitivo **singular**. Depois de **5+**: Genitivo **plural**.

```
одна книга          (1 livro — Nominativo)
две книги           (2 livros — Genitivo singular)
пять книг           (5 livros — Genitivo plural)
```

## Preposições com Genitivo

у (perto de / na casa de), для (para), из (vindo de), до (até), после (depois de)

```
Я из Бразилии.          Eu sou/venho do Brasil.
Это подарок для мамы.   Isso é um presente para a mãe.
```
""",
                [
                    ex("quiz", "Como se diz \"eu tenho\" em russo (construção com у + Genitivo)?",
                       "у меня есть", ["у меня есть", "я имею", "я есть"]),
                    ex("text", "Traduza: Eu tenho um livro. (у + меня + есть + книга)",
                       "у меня есть книга"),
                    ex("text", "Traduza: Eu não tenho um livro. (у + меня + нет + книги)",
                       "у меня нет книги"),
                    ex("quiz", "Depois do número 5, o substantivo vai para:",
                       "Genitivo plural", ["Genitivo plural", "Genitivo singular", "Nominativo"]),
                    ex("quiz", 'Qual preposição indica origem ("vindo de")?',
                       "из", ["из", "для", "до"]),
                    ex("text", "Traduza: Eu sou do Brasil. (я + из + Бразилии)",
                       "я из бразилии"),
                    ex("quiz", 'Qual a forma de "она" (ela) no Genitivo?',
                       "неё", ["неё", "него", "них"]),
                    ex("audio", "Escute e transcreva:", "у него есть машина", audio_text="у него есть машина"),
                ],
            ),
            topic(
                "dativo-objeto-e-impessoais",
                "Dativo: objeto indireto e construções impessoais",
                """
# Dativo: objeto indireto e construções impessoais

O **Dativo** marca o **objeto indireto** (para quem) e aparece em construções impessoais.

## Terminações no Dativo (singular)

| Gênero | Terminação | Exemplo |
|---|---|---|
| Masculino/Neutro | -у/-ю | стол -> столу, окно -> окну |
| Feminino (-а) | -е | сестра -> сестре |

## Objeto indireto

```
Я даю книгу сестре.      Eu dou o livro para a irmã. (сестре = Dativo)
Он пишет другу.          Ele escreve para o amigo.
```

## Construções impessoais: Dativo + нравится/нужно

```
Мне нравится музыка.       Eu gosto de música.
Мне нужно время.           Eu preciso de tempo.
Ей двадцать лет.           Ela tem vinte anos.
```

## Preposições к (em direção a) e по (por/ao longo de)

```
Я иду к врачу.             Eu vou ao médico.
Он говорит по телефону.    Ele fala por telefone.
```

## Pronomes no Dativo

я -> мне, ты -> тебе, он/оно -> ему, она -> ей, мы -> нам, вы -> вам, они -> им
""",
                [
                    ex("text", 'Complete no Dativo: "Я даю книгу ___." (para a irmã: сестра)',
                       "сестре"),
                    ex("quiz", "O caso Dativo marca:",
                       "o objeto indireto (para quem)", ["o objeto indireto (para quem)", "o sujeito", "posse"]),
                    ex("text", "Traduza: Eu gosto de música. (мне + нравится + музыка)",
                       "мне нравится музыка"),
                    ex("quiz", 'Qual a forma de "она" (ela) no Dativo?',
                       "ей", ["ей", "её", "неё"]),
                    ex("quiz", 'Qual preposição indica "em direção a" uma pessoa/lugar?',
                       "к", ["к", "по", "у"]),
                    ex("text", "Traduza: Eu vou ao médico. (я + иду + к + врачу)",
                       "я иду к врачу"),
                    ex("audio", "Escute e transcreva:", "он пишет другу", audio_text="он пишет другу"),
                    ex("speak", "Repita em voz alta:", "мне нравится музыка", audio_text="мне нравится музыка"),
                ],
            ),
            topic(
                "instrumental-meio-e-tempo",
                "Instrumental: meio, companhia e tempo",
                """
# Instrumental: meio, companhia e tempo

O **Instrumental** indica **com o quê** (meio/instrumento), **com quem** (companhia) e certas **expressões de tempo**.

## Terminações no Instrumental (singular)

| Gênero | Terminação | Exemplo |
|---|---|---|
| Masculino/Neutro | -ом/-ем | стол -> столом, окно -> окном |
| Feminino (-а) | -ой/-ей | ручка -> ручкой |

## Meio/instrumento

```
Я пишу ручкой.          Eu escrevo com uma caneta.
Он ест вилкой.          Ele come com um garfo.
```

## Companhia: с + Instrumental

```
Я иду с другом.          Eu vou com um amigo.
Она говорит с мамой.     Ela fala com a mãe.
```

## Expressões de tempo

```
зимой (no inverno)      летом (no verão)
утром (de manhã)        вечером (à noite)
```

## Instrumental no plural: -ами/-ями (para todos os gêneros)

```
столы -> столами        (com as mesas)
книги -> книгами        (com os livros)
```

> 💡 Essa uniformidade no plural (todo mundo vira -ами/-ями, não importa o gênero) é uma boa notícia: o Instrumental plural é mais fácil que o singular.
""",
                [
                    ex("text", 'Complete no Instrumental: "Я пишу ___." (com uma caneta: ручка)',
                       "ручкой"),
                    ex("quiz", "O caso Instrumental indica:",
                       "o meio/instrumento de uma ação", ["o meio/instrumento de uma ação", "posse", "objeto direto"]),
                    ex("text", "Traduza: Eu vou com um amigo. (я + иду + с + другом)",
                       "я иду с другом"),
                    ex("quiz", 'Como se diz "no inverno" em russo?',
                       "зимой", ["зимой", "зима", "зиму"]),
                    ex("text", "Traduza: De manhã eu tomo café. (утром + я + пью + кофе)",
                       "утром я пью кофе"),
                    ex("quiz", "No plural, qual terminação o Instrumental usa (para todos os gêneros)?",
                       "-ами/-ями", ["-ами/-ями", "-ом/-ем", "-ой/-ей"]),
                    ex("audio", "Escute e transcreva:", "он ест вилкой", audio_text="он ест вилкой"),
                    ex("speak", "Repita em voz alta:", "я пишу ручкой", audio_text="я пишу ручкой"),
                ],
            ),
            topic(
                "plural-nos-casos",
                "O plural em todos os casos",
                """
# O plural em todos os casos

Assim como no singular, cada caso tem sua terminação de **plural**. Aqui vai o panorama das terminações de plural para **стол (mesa), книга (livro) e окно (janela)**:

| Caso | стол -> столы | книга -> книги | окно -> окна |
|---|---|---|---|
| Nominativo | столы | книги | окна |
| Genitivo | столов | книг | окон |
| Dativo | столам | книгам | окнам |
| Acusativo | столы | книги | окна |
| Instrumental | столами | книгами | окнами |
| Preposicional | столах | книгах | окнах |

## Regras gerais de plural

- **Nominativo**: -ы/-и (masc./fem.), -а/-я (neutro) — visto no Módulo 2.
- **Dativo**: -ам/-ям (para todos os gêneros!).
- **Instrumental**: -ами/-ями (para todos os gêneros!).
- **Preposicional**: -ах/-ях (para todos os gêneros!).
- **Genitivo**: varia bastante (-ов, -ей, terminação zero...) — o mais difícil.

> 🎯 Boa notícia: **Dativo, Instrumental e Preposicional** têm padrões regulares de plural para todos os gêneros (-ам/-ям, -ами/-ями e -ах/-ях). Só o Genitivo exige atenção extra.
""",
                [
                    ex("quiz", 'No plural, a terminação do DATIVO é (para todos os gêneros):',
                       "-ам/-ям", ["-ам/-ям", "-ами/-ями", "-ах/-ях"]),
                    ex("text", "Complete no Preposicional plural: \"Они говорят о ___\" (книги).",
                       "книгах"),
                    ex("quiz", 'No plural, a terminação do PREPOSICIONAL é:',
                       "-ах/-ях", ["-ах/-ях", "-ам/-ям", "-ами/-ями"]),
                    ex("quiz", 'No plural, a terminação do INSTRUMENTAL é:',
                       "-ами/-ями", ["-ами/-ями", "-ам/-ям", "-ах/-ях"]),
                    ex("text", "Complete no Instrumental plural: \"Я иду с ___\" (друзья).",
                       "друзьями"),
                    ex("audio", "Escute e transcreva:", "я иду с друзьями", audio_text="я иду с друзьями"),
                    ex("quiz", "Qual caso tem o plural mais irregular (mais formas diferentes)?",
                       "Genitivo", ["Genitivo", "Dativo", "Instrumental"]),
                ],
            ),
        ],
    )


# ============================================================
# MODULO 9 - Aspecto Verbal: Conceito (B1)
# ============================================================

def build_modulo_09_aspecto_verbal_conceito():
    return module(
        "modulo-09-aspecto-verbal-conceito",
        "Módulo 9 — Aspecto Verbal: Conceito — B1",
        "Perfectivo vs imperfectivo, como formar o perfectivo e como a escolha do aspecto muda o sentido no presente, no infinitivo e no passado.",
        [
            topic(
                "o-que-e-aspecto-verbal",
                "O que é aspecto verbal?",
                """
# O que é aspecto verbal?

Esse é o conceito mais difícil (e mais importante) da gramática russa: quase todo verbo tem **dois aspectos** — **imperfectivo** e **perfectivo** — que descrevem COMO a ação acontece, não QUANDO.

| Aspecto | Uso | Exemplo |
|---|---|---|
| Imperfectivo | ação em andamento, repetida, ou o processo em si | читать (ler / estar lendo / ler várias vezes) |
| Perfectivo | ação completa, com resultado, uma vez só | прочитать (ler até o fim, terminar de ler) |

```
Я читал книгу.          (imperfectivo) Eu estava lendo o livro / lia o livro. (processo, sem garantia de ter terminado)
Я прочитал книгу.       (perfectivo)   Eu li o livro (até o fim, terminei).
```

> 🎯 Isso NÃO é a mesma coisa que tempo verbal (presente/passado/futuro) — é uma camada extra. Cada verbo tem uma versão de cada aspecto, e você escolhe qual usar dependendo do que quer dizer.

## Por que isso é tão importante

Escolher o aspecto errado não é só um "erro de gramática" pequeno — muitas vezes muda completamente o sentido da frase (ver o tópico 4 deste módulo) ou soa muito estranho para um falante nativo. É um dos poucos pontos em que vale mais a pena "sentir" o padrão com muito exemplo do que decorar uma regra fixa.
""",
                [
                    ex("quiz", "O aspecto PERFECTIVO indica:",
                       "uma ação completa, com resultado", ["uma ação completa, com resultado", "uma ação repetida", "uma ação no futuro"]),
                    ex("quiz", "O aspecto IMPERFECTIVO indica:",
                       "processo, ação em andamento ou repetida", ["processo, ação em andamento ou repetida", "só o futuro", "só o passado"]),
                    ex("quiz", "Aspecto verbal é a mesma coisa que tempo verbal (presente/passado/futuro)?",
                       "Não, é uma categoria independente do tempo", ["Não, é uma categoria independente do tempo", "Sim, são sinônimos", "Só existe no futuro"]),
                    ex("audio", "Escute e transcreva:", "я прочитал книгу", audio_text="я прочитал книгу"),
                    ex("quiz", "Qual frase indica PROCESSO (sem garantir que terminou)?",
                       "Я читал книгу.", ["Я читал книгу.", "Я прочитал книгу.", "Я прочитаю книгу."]),
                ],
            ),
            topic(
                "formando-o-perfectivo",
                "Formando o perfectivo",
                """
# Formando o perfectivo

Não existe uma regra única — mas dois padrões comuns:

## 1. Adicionando um prefixo

```
читать -> прочитать        (ler -> ler até o fim)
делать -> сделать          (fazer -> terminar de fazer)
писать -> написать         (escrever -> terminar de escrever)
```

## 2. Trocando um sufixo

```
решать -> решить           (resolver, no processo -> resolver, concluído)
покупать -> купить         (comprar, no processo -> comprar, concluído)
```

> 💡 Não tem jeito: os pares de aspecto precisam ser decorados verbo por verbo, como "vocabulário duplo". Com o tempo, os padrões vão ficando mais intuitivos.
""",
                [
                    ex("quiz", 'Qual é o perfectivo de "читать" (ler)?',
                       "прочитать", ["прочитать", "читать", "читал"]),
                    ex("text", 'Escreva o perfectivo de "делать" (fazer), formado com o prefixo с-.',
                       "сделать"),
                    ex("quiz", 'Qual é o perfectivo de "покупать" (comprar, processo)?',
                       "купить", ["купить", "покупал", "покупает"]),
                    ex("audio", "Escute e transcreva:", "написать", audio_text="написать"),
                    ex("quiz", 'Qual é o perfectivo de "писать" (escrever)?',
                       "написать", ["написать", "писать", "писал"]),
                ],
            ),
            topic(
                "aspecto-no-presente-e-infinitivo",
                "Aspecto no presente e no infinitivo",
                """
# Aspecto no presente e no infinitivo

## Presente: só imperfectivo

No **presente**, só o **imperfectivo** existe — o perfectivo conjugado como presente vira **futuro**:

```
Я читаю.           (presente) Eu leio / estou lendo.
Я прочитаю.        (futuro!) Eu vou ler até o fim. (a forma perfectiva "no presente" significa futuro)
```

## Infinitivo: a escolha muda o pedido

Com "хотеть" (querer), "надо" (preciso), "можно" (pode):

```
Я хочу читать.          Quero ler (no processo, sem foco no fim).
Я хочу прочитать.       Quero ler até o fim (resultado).
```

> 🎯 Regra de ouro: **presente = imperfectivo**. Se você vê um verbo perfectivo com terminação de presente, ele está no **futuro**.
""",
                [
                    ex("quiz", "No PRESENTE, qual aspecto existe?",
                       "imperfectivo", ["imperfectivo", "perfectivo", "os dois"]),
                    ex("quiz", "Um verbo perfectivo com terminação de presente significa:",
                       "futuro", ["futuro", "presente", "passado"]),
                    ex("text", 'Complete no infinitivo (perfectivo, com resultado): "Я хочу ___ книгу." (прочитать/читать)',
                       "прочитать"),
                    ex("audio", "Escute e transcreva:", "я хочу прочитать книгу", audio_text="я хочу прочитать книгу"),
                    ex("quiz", 'Em "Я читаю", o sentido é:',
                       "eu leio / estou lendo (processo)", ["eu leio / estou lendo (processo)", "eu vou ler até o fim", "eu li"]),
                ],
            ),
            topic(
                "usando-aspecto-no-passado",
                "Usando o aspecto no passado",
                """
# Usando o aspecto no passado

A escolha do aspecto no passado muda o sentido da frase:

```
Я писал письмо.          (imperfectivo) Eu escrevia/estava escrevendo uma carta. (processo, talvez não terminou)
Я написал письмо.        (perfectivo)   Eu escrevi a carta. (terminei, resultado pronto)
```

Use **imperfectivo** quando quiser destacar:
- Que a ação estava em andamento
- Que a ação se repetiu várias vezes
- Só o fato de que a ação aconteceu (sem focar no resultado)

Use **perfectivo** quando quiser destacar:
- Que a ação foi concluída
- Um resultado específico e único
""",
                [
                    ex("quiz", "Qual frase enfatiza que a carta FOI TERMINADA?",
                       "Я написал письмо.", ["Я написал письмо.", "Я писал письмо.", "Я пишу письмо."]),
                    ex("text", "Traduza usando o IMPERFECTIVO (processo, sem garantir que terminou): Eu escrevia uma carta. (я + писал + письмо)",
                       "я писал письмо"),
                    ex("quiz", 'Se alguém diz "Я читал эту книгу" (imperfectivo), o que isso sugere?',
                       "Que ele leu o livro em algum momento, sem foco no resultado/se terminou",
                       ["Que ele leu o livro em algum momento, sem foco no resultado/se terminou", "Que ele com certeza terminou o livro", "Que ele nunca leu o livro"]),
                    ex("audio", "Escute e transcreva:", "я писал письмо", audio_text="я писал письмо"),
                    ex("quiz", "Qual frase indica PROCESSO, talvez não terminado?",
                       "Я писал письмо.", ["Я писал письмо.", "Я написал письмо.", "Я напишу письмо."]),
                ],
            ),
            topic(
                "pares-comuns-de-aspecto",
                "Pares comuns de aspecto",
                """
# Pares comuns de aspecto

Os pares mais usados do dia a dia — memorize como "vocabulário duplo":

| Imperfectivo (processo) | Perfectivo (resultado) |
|---|---|
| читать | прочитать (ler até o fim) |
| делать | сделать (terminar de fazer) |
| писать | написать (terminar de escrever) |
| покупать | купить (comprar, concluído) |
| решать | решить (resolver, concluído) |
| говорить | сказать (dizer, uma vez) |

```
Что ты делаешь?        O que você está fazendo? (imperfectivo)
Я сделал домашнее задание.  Eu fiz o dever de casa. (perfectivo, concluído)
```

> 💡 "говорить" (falar, processo) e "сказать" (dizer, pontual) é um dos pares mais comuns — vale fixar bem.
""",
                [
                    ex("quiz", 'Qual é o perfectivo de "говорить" (falar)?',
                       "сказать", ["сказать", "говорил", "говорить"]),
                    ex("text", 'Escreva o perfectivo de "решать" (resolver).',
                       "решить"),
                    ex("quiz", 'Qual é o perfectivo de "покупать" (comprar)?',
                       "купить", ["купить", "покупаю", "покупать"]),
                    ex("audio", "Escute e transcreva:", "я сделал домашнее задание", audio_text="я сделал домашнее задание"),
                    ex("quiz", 'O par "говорить/сказать" mostra:',
                       "processo (falar) vs pontual (dizer uma vez)", ["processo (falar) vs pontual (dizer uma vez)", "passado vs futuro", "singular vs plural"]),
                    ex("text", 'Complete com o perfectivo: "Я ___ домашнее задание." (сделать)',
                       "сделал"),
                ],
            ),
        ],
    )


# ============================================================
# MODULO 10 - Passado e Futuro (B1)
# ============================================================

def build_modulo_10_passado_e_futuro():
    return module(
        "modulo-10-passado-e-futuro",
        "Módulo 10 — Passado e Futuro — B1",
        "O passado com concordância de gênero, os verbos irregulares no passado, o futuro simples vs composto, a negação no futuro e o modo condicional com бы.",
        [
            topic(
                "passado-com-genero",
                "Passado: concordância de gênero",
                """
# Passado: concordância de gênero

Uma particularidade única do russo: verbos no **passado** concordam em **gênero** com o sujeito (não com a pessoa gramatical, como no presente)!

## Formação: raiz + -л (masc.) / -ла (fem.) / -ло (neutro) / -ли (plural)

| Sujeito | читать no passado |
|---|---|
| он (ele) | читал |
| она (ela) | читала |
| оно (isso, neutro) | читало |
| они / мы / вы (plural) | читали |

```
Он читал книгу.          Ele lia/leu o livro.
Она читала книгу.        Ela lia/leu o livro.
Они читали книгу.        Eles liam/leram o livro.
```

> 🎯 Repare: não importa se é "eu", "tu" ou "ele" — o que importa para a terminação do passado é o **gênero** (e se é plural) do sujeito.
""",
                [
                    ex("quiz", "Qual a terminação do passado para sujeito FEMININO?",
                       "-ла", ["-ла", "-л", "-ло"]),
                    ex("text", "Traduza: Ela leu o livro. (она + читала + книгу)",
                       "она читала книгу"),
                    ex("quiz", 'Complete: "Они ___ письмо." (eles escreveram uma carta — писать no passado)',
                       "писали", ["писали", "писал", "писала"]),
                    ex("audio", "Escute e transcreva:", "он читал книгу", audio_text="он читал книгу"),
                    ex("speak", "Repita em voz alta:", "она читала книгу", audio_text="она читала книгу"),
                    ex("quiz", "O que determina a terminação do verbo no passado?",
                       "o gênero e o número do sujeito", ["o gênero e o número do sujeito", "a pessoa gramatical (eu/tu/ele)", "o tempo do verbo"]),
                ],
            ),
            topic(
                "passado-dos-irregulares",
                "Passado dos verbos irregulares",
                """
# Passado dos verbos irregulares

Alguns verbos comuns têm passado irregular — o -л pode sumir no masculino:

| Infinitivo | Masculino | Feminino | Plural |
|---|---|---|---|
| идти (ir) | шёл | шла | шли |
| есть (comer) | ел | ела | ели |
| мочь (poder) | мог | могла | могли |
| жить (morar) | жил | жила | жили |

```
Он шёл домой.          Ele ia para casa.
Она шла домой.         Ela ia para casa.
Мы жили в Москве.      Nós morávamos em Moscou. (в + Москве = Preposicional, M8)
```

> 🎯 Repare em "шёл" (masculino, sem -л) vs "шла" (feminino, com -ла). E o espiral: "в Москве" é o Preposicional do Módulo 8.
""",
                [
                    ex("quiz", 'Qual o passado masculino de "идти" (ir)?',
                       "шёл", ["шёл", "шла", "шли"]),
                    ex("text", "Traduza: Ela ia para casa. (она + шла + домой)",
                       "она шла домой"),
                    ex("quiz", 'Qual o passado masculino de "мочь" (poder)?',
                       "мог", ["мог", "могла", "могли"]),
                    ex("audio", "Escute e transcreva:", "мы жили в москве", audio_text="мы жили в москве"),
                    ex("speak", "Repita em voz alta:", "он шёл домой", audio_text="он шёл домой"),
                    ex("quiz", 'Complete: "Они ___ в Москве." (moravam — жить, plural)',
                       "жили", ["жили", "жил", "жила"]),
                ],
            ),
            topic(
                "futuro-simples-e-composto",
                "Futuro: simples e composto",
                """
# Futuro: simples e composto

O futuro em russo depende do **aspecto** do verbo (Módulo 9):

## Futuro simples (verbos perfectivos)

Basta conjugar o verbo perfectivo como se fosse presente — a forma já tem sentido de futuro:

```
Я прочитаю книгу.        Eu vou ler o livro até o fim. (prefixo про- já indica perfectivo)
```

## Futuro composto (verbos imperfectivos)

Usa-se **быть** (ser/estar, conjugado no futuro) + o infinitivo imperfectivo:

```
Я буду читать книгу.     Eu vou ficar lendo o livro. (processo, sem foco no fim)
```

| Pessoa | быть (futuro) |
|---|---|
| я | буду |
| ты | будешь |
| он/она | будет |
| мы | будем |
| вы | будете |
| они | будут |
""",
                [
                    ex("quiz", "Qual estrutura forma o futuro de um verbo IMPERFECTIVO?",
                       "быть (futuro) + infinitivo", ["быть (futuro) + infinitivo", "prefixo + presente", "não existe futuro imperfectivo"]),
                    ex("text", "Traduza: Eu vou ficar lendo o livro. (я + буду + читать + книгу)",
                       "я буду читать книгу"),
                    ex("quiz", 'Como se forma o futuro de um verbo PERFECTIVO (ex: прочитать)?',
                       "conjugando normalmente, como se fosse presente", ["conjugando normalmente, como se fosse presente", "com быть + infinitivo", "não tem futuro"]),
                    ex("audio", "Escute e transcreva:", "я прочитаю книгу", audio_text="я прочитаю книгу"),
                    ex("quiz", 'Qual é o futuro de "быть" na 1ª pessoa (я)?',
                       "буду", ["буду", "будешь", "будет"]),
                    ex("text", "Complete: Я ___ (vou) читать книгу.",
                       "буду"),
                ],
            ),
            topic(
                "negacao-no-futuro",
                "Negação no futuro",
                """
# Negação no futuro

Para negar no futuro, a escolha do aspecto muda o sentido:

## Imperfectivo: "não vou (não pretendo)"

```
Я не буду читать.         Eu não vou ler (não pretendo / não vou ficar lendo).
```

## Perfectivo: "não vou conseguir / não vai acontecer"

```
Я не прочитаю это.        Eu não vou conseguir ler isso até o fim.
Он не придёт.             Ele não vai vir. (perfectivo — a ação não vai acontecer)
```

## A regra

- **не + буду + imperfectivo** = negação de intenção/processo.
- **не + perfectivo (futuro simples)** = negação de resultado/evento pontual.

> 🎯 "Он не придёт" (não vai vir, evento pontual) usa o perfectivo — você vai ver esse padrão de novo no Módulo 16 (imperativo) e no Módulo 20 (nuance).
""",
                [
                    ex("text", "Traduza: Ele não vai vir. (он + не + придёт)",
                       "он не придёт"),
                    ex("quiz", 'Qual forma nega a INTENÇÃO/processo ("não vou ler")?',
                       "не буду читать", ["не буду читать", "не прочитаю", "не читаю"]),
                    ex("quiz", 'Qual forma nega o RESULTADO ("não vou conseguir ler até o fim")?',
                       "не прочитаю", ["не прочитаю", "не буду читать", "не читал"]),
                    ex("audio", "Escute e transcreva:", "я не буду читать", audio_text="я не буду читать"),
                    ex("quiz", 'Em "Он не придёт", o aspecto é:',
                       "perfectivo (evento pontual)", ["perfectivo (evento pontual)", "imperfectivo (processo)", "não tem aspecto"]),
                ],
            ),
            topic(
                "modo-condicional",
                "O modo condicional (бы)",
                """
# O modo condicional (бы)

Para expressar algo hipotético ("eu faria", "se eu fizesse"), o russo usa o verbo no **passado** + a partícula **бы** — sem nenhuma conjugação especial extra:

```
Я бы пошёл.              Eu iria. / Eu teria ido.
Если бы у меня было время, я бы читал больше.
   Se eu tivesse tempo, eu leria mais.
```

## O ponto interessante: uma forma só para tudo

Diferente do português (que tem "eu faria" no futuro do pretérito, "eu tivesse feito" no pretérito imperfeito do subjuntivo, etc.), o russo usa **sempre a mesma construção** — verbo no passado + бы — não importa se a condição é sobre presente, passado ou futuro. O contexto é que esclarece.

> 💡 "бы" é uma partícula solta, não um sufixo — ela pode até mudar de posição na frase, geralmente ficando logo depois do verbo ou da palavra mais enfatizada.
""",
                [
                    ex("quiz", "Como se forma o condicional em russo?",
                       "verbo no passado + бы", ["verbo no passado + бы", "verbo no futuro + бы", "быть + бы + infinitivo"]),
                    ex("text", "Traduza: Eu iria. (я + бы + пошёл)", "я бы пошёл"),
                    ex("quiz", "O russo usa formas diferentes de condicional para presente, passado e futuro hipotéticos?",
                       "Não, usa sempre a mesma construção (passado + бы)", ["Não, usa sempre a mesma construção (passado + бы)", "Sim, uma forma para cada tempo", "Não existe condicional em russo"]),
                    ex("audio", "Escute e transcreva:", "если бы у меня было время", audio_text="если бы у меня было время"),
                    ex("quiz", "A partícula \"бы\" pode mudar de posição na frase?",
                       "Sim, é uma partícula solta", ["Sim, é uma partícula solta", "Não, fica sempre no final", "Ela é um sufixo fixo"]),
                    ex("text", "Traduza: Se eu tivesse tempo, eu leria. (если бы + у меня + было + время + я бы + читал)", "если бы у меня было время я бы читал"),
                ],
            ),
        ],
    )


# ============================================================
# MODULO 11 - Casos Avancados (B1)
# ============================================================

def build_modulo_11_casos_avancados():
    return module(
        "modulo-11-casos-avancados",
        "Módulo 11 — Casos Avançados — B1",
        "Concordância de adjetivos em todos os casos, a tabela completa dos pronomes pessoais e as orações relativas com который.",
        [
            topic(
                "adjetivos-no-nominativo",
                "Concordância de adjetivos no Nominativo",
                """
# Concordância de adjetivos no Nominativo

Adjetivos em russo concordam em **gênero, número e caso** com o substantivo que descrevem — assim como no português ("gato preto" / "gata preta"), mas com muito mais variações por causa dos casos.

## Terminações no Nominativo

| Gênero | Terminação | Exemplo |
|---|---|---|
| Masculino | -ый/-ой/-ий | новый дом (uma casa nova) |
| Feminino | -ая/-яя | новая книга (um livro novo) |
| Neutro | -ое/-ее | новое окно (uma janela nova) |
| Plural | -ые/-ие | новые дома (casas novas) |

```
Новый дом.        Uma casa nova.
Новая книга.      Um livro novo.
Новое окно.       Uma janela nova.
Новые дома.       Casas novas.
```
""",
                [
                    ex("quiz", "Qual terminação de adjetivo combina com um substantivo FEMININO no Nominativo?",
                       "-ая", ["-ая", "-ый", "-ое"]),
                    ex("text", "Traduza: Um livro novo. (новая + книга)", "новая книга"),
                    ex("quiz", "Qual terminação de adjetivo combina com PLURAL?",
                       "-ые", ["-ые", "-ая", "-ое"]),
                    ex("audio", "Escute e transcreva:", "новые дома", audio_text="новые дома"),
                    ex("speak", "Repita em voz alta:", "новый дом", audio_text="новый дом"),
                    ex("quiz", "Adjetivos concordam com o substantivo em:",
                       "gênero, número e caso", ["gênero, número e caso", "apenas gênero", "apenas número"]),
                ],
            ),
            topic(
                "adjetivos-nos-casos",
                "Adjetivos nos casos oblíquos",
                """
# Adjetivos nos casos oblíquos

Os adjetivos mudam de terminação em cada caso — aqui vai o panorama com **новый** (novo):

| Caso | Masculino | Feminino |
|---|---|---|
| Nominativo | новый | новая |
| Genitivo | нового | новой |
| Dativo | новому | новой |
| Acusativo | новый/нового | новую |
| Instrumental | новым | новой |
| Preposicional | новом | новой |

```
Я вижу новый дом.          Eu vejo uma casa nova. (Acusativo)
Он живёт в новом доме.     Ele mora numa casa nova. (Preposicional)
Это ключ от нового дома.   Esta é a chave da casa nova. (Genitivo)
```

> 🎯 Padrão que ajuda: o Genitivo/Dativo/Instrumental/Preposicional masculino usa **нов-ого/ому/ым/ом**, e o feminino quase sempre **нов-ой**. Reconhecer o "nov-" + terminação de caso desbloqueia a concordância.
""",
                [
                    ex("quiz", 'Complete no Preposicional masculino: "Он живёт в ___ доме." (новый)',
                       "новом", ["новом", "новый", "нового"]),
                    ex("text", "Traduza: Eu vejo uma casa nova. (я + вижу + новый + дом)",
                       "я вижу новый дом"),
                    ex("quiz", 'Complete no Genitivo feminino: "Это ключ от ___ квартиры." (новая)',
                       "новой", ["новой", "новую", "новая"]),
                    ex("audio", "Escute e transcreva:", "он живёт в новом доме", audio_text="он живёт в новом доме"),
                    ex("quiz", "No feminino, quase todos os casos oblíquos usam a terminação:",
                       "-ой", ["-ой", "-ая", "-ую"]),
                    ex("text", "Complete no Acusativo feminino: \"Я вижу ___ книгу.\" (новая)",
                       "новую"),
                ],
            ),
            topic(
                "pronomes-em-todos-os-casos",
                "Pronomes pessoais em todos os casos",
                """
# Pronomes pessoais em todos os casos

Agora a tabela completa dos pronomes nos 6 casos — o espiral do Módulo 4 completo:

| Nominativo | Genitivo | Dativo | Acusativo | Instrumental | Preposicional |
|---|---|---|---|---|---|
| я | меня | мне | меня | мной | обо мне |
| ты | тебя | тебе | тебя | тобой | о тебе |
| он/оно | его | ему | его | им | о нём |
| она | её | ей | её | ей | о ней |
| мы | нас | нам | нас | нами | о нас |
| вы | вас | вам | вас | вами | о вас |
| они | их | им | их | ими | о них |

```
Он думает обо мне.         Ele pensa em mim. (Preposicional)
Я говорю с тобой.          Eu falo com você. (с + тобой = Instrumental)
Она идёт к нам.            Ela vem até nós. (к + нам = Dativo)
```

> 🎯 Repare nos padrões: **меня/тебя/его/её/нас/вас/их** servem para Genitivo E Acusativo; **мне/тебе/ему/ей/нам/вам/им** para Dativo (e aparecem em "мне нравится").
""",
                [
                    ex("quiz", 'Qual a forma de "я" (eu) no Instrumental (com с)?',
                       "мной", ["мной", "меня", "мне"]),
                    ex("text", "Traduza: Eu falo com você. (я + говорю + с + тобой)",
                       "я говорю с тобой"),
                    ex("quiz", "Quais casos compartilham as mesmas formas (меня, тебя, его...)?",
                       "Genitivo e Acusativo", ["Genitivo e Acusativo", "Dativo e Instrumental", "Preposicional e Nominativo"]),
                    ex("quiz", 'Qual a forma de "она" (ela) no Dativo?',
                       "ей", ["ей", "её", "неё"]),
                    ex("audio", "Escute e transcreva:", "она идёт к нам", audio_text="она идёт к нам"),
                    ex("speak", "Repita em voz alta:", "я говорю с тобой", audio_text="я говорю с тобой"),
                ],
            ),
            topic(
                "oracoes-com-kotoryi",
                "Orações relativas: который (quem/que)",
                """
# Orações relativas: который (quem/que)

Para dizer "a pessoa QUE...", "o livro QUE...", o russo usa **который** — que concorda em gênero e número com a palavra que descreve:

| Substantivo | который |
|---|---|
| мужчина (masc.) | который |
| женщина (fem.) | которая |
| окно (neutro) | которое |
| люди (plural) | которые |

```
Мужчина, который читает, — мой брат.      O homem que lê é meu irmão.
Женщина, которая работает здесь, — врач.  A mulher que trabalha aqui é médica.
Книга, которая на столе, — новая.         O livro que está na mesa é novo.
```

> 🎯 Diferente do inglês (that/who sem flexão), o russo flexiona o "que" conforme o gênero e o número do antecedente.
""",
                [
                    ex("quiz", 'Para descrever uma mulher, qual forma de "который" usamos?',
                       "которая", ["которая", "который", "которое"]),
                    ex("text", "Traduza: A mulher que trabalha aqui é médica. (женщина + которая + работает + здесь + врач)",
                       "женщина которая работает здесь врач"),
                    ex("quiz", 'Para descrever uma coisa neutra (ex: окно), usamos:',
                       "которое", ["которое", "который", "которые"]),
                    ex("audio", "Escute e transcreva:", "мужчина который читает мой брат", audio_text="Мужчина, который читает, мой брат."),
                    ex("quiz", '"который" concorda em:', 
                       "gênero e número com o antecedente", ["gênero e número com o antecedente", "sempre fica igual", "apenas no plural"]),
                    ex("text", "Complete: \"Книга, ___ на столе, — новая.\" (que)",
                       "которая"),
                ],
            ),
            topic(
                "kotoryi-nos-casos",
                "который nos casos oblíquos",
                """
# который nos casos oblíquos

Quando o pronome relativo desempenha outra função na oração (objeto, posse...), **который declina** como um adjetivo:

| Caso | Masculino | Feminino | Exemplo |
|---|---|---|---|
| Nominativo | который | которая | Женщина, которая читает... |
| Acusativo | которого/который | которую | Дом, который я вижу... |
| Genitivo | которого | которой | Человек, которого я знаю... |
| Dativo | которому | которой | Друг, которому я пишу... |
| Instrumental | которым | которой | Друг, с которым я иду... |
| Preposicional | котором | которой | Город, о котором я думаю... |

```
Друг, с которым я иду, — русский.        O amigo com quem eu vou é russo. (с + которым = Instrumental)
Город, о котором я думаю, — Москва.      A cidade na qual penso é Moscou. (о + котором = Preposicional)
Дом, который я вижу, — новый.            A casa que vejo é nova. (Acusativo)
```

> 🎯 A lacuna do espiral: "с которым" (Instrumental), "о котором" (Preposicional), "которого" (Genitivo/Acusativo) — todos os casos do Módulo 8 aplicados ao "que".
""",
                [
                    ex("quiz", 'Complete no Instrumental: "Друг, с ___ я иду, — русский." (который)',
                       "которым", ["которым", "который", "которого"]),
                    ex("text", "Complete no Preposicional: \"Город, о ___ я думаю, — Москва.\" (который)",
                       "котором"),
                    ex("quiz", 'Complete no Acusativo: "Дом, ___ я вижу, — новый." (который)',
                       "который", ["который", "которого", "котором"]),
                    ex("audio", "Escute e transcreva:", "друг с которым я иду русский", audio_text="Друг, с которым я иду, русский."),
                    ex("quiz", "Qual caso \"с которым\" representa?",
                       "Instrumental", ["Instrumental", "Nominativo", "Acusativo"]),
                    ex("text", "Complete no Genitivo: \"Человек, ___ я знаю, — мой друг.\" (который)",
                       "которого"),
                ],
            ),
            topic(
                "adjetivos-no-plural",
                "Adjetivos no plural (todos os casos)",
                """
# Adjetivos no plural (todos os casos)

No plural, os adjetivos têm UMA terminação por caso (para todos os gêneros) — como os substantivos viram -ами/-ям/-ах, os adjetivos também uniformizam:

| Caso | Terminação plural | Exemplo (новые дома) |
|---|---|---|
| Nominativo | -ые/-ие | новые дома |
| Genitivo | -ых/-их | новых домов |
| Dativo | -ым/-им | новым домам |
| Acusativo | -ые/-ие (ou -ых/-их animado) | новые дома |
| Instrumental | -ыми/-ими | новыми домами |
| Preposicional | -ых/-их | новых домах |

```
Я вижу новые дома.          Eu vejo casas novas. (Acusativo)
Он живёт в новых домах.     Ele mora em casas novas. (Preposicional)
Мы идём с новыми друзьями.  Vamos com novos amigos. (Instrumental)
```

> 🎯 Boa notícia: no plural, só duas terminações de adjetivo por caso — **-ые/-ые** na linha de cima (Nom./Acus.) e **-ых/-ым/-ыми/-ых** nas demais. Muito mais fácil que o singular!
""",
                [
                    ex("quiz", "No plural, a terminação dos adjetivos no PREPOSICIONAL é:",
                       "-ых/-их", ["-ых/-их", "-ыми/-ими", "-ым/-им"]),
                    ex("text", "Complete no Preposicional plural: \"Он живёт в ___ домах.\" (новый)",
                       "новых"),
                    ex("quiz", "No plural, a terminação dos adjetivos no INSTRUMENTAL é:",
                       "-ыми/-ими", ["-ыми/-ими", "-ых/-их", "-ым/-им"]),
                    ex("quiz", "No plural, quantas terminações de adjetivo existem por caso (para todos os gêneros)?",
                       "uma por caso", ["uma por caso", "três (uma por gênero)", "nenhuma, fica invariável"]),
                    ex("audio", "Escute e transcreva:", "мы идём с новыми друзьями", audio_text="Мы идём с новыми друзьями."),
                    ex("text", "Complete no Instrumental plural: \"Мы идём с ___ друзьями.\" (новый)",
                       "новыми"),
                ],
            ),
        ],
    )


# ============================================================
# MODULO 12 - Verbos de Movimento (B1)
# ============================================================

def build_modulo_12_verbos_de_movimento():
    return module(
        "modulo-12-verbos-de-movimento",
        "Módulo 12 — Verbos de Movimento — B1",
        "O capítulo clássico do russo: идти/ходить, ехать/ездить, лететь/летать, плыть/плавать e бежать/бегать — unidirecional vs multidirecional.",
        [
            topic(
                "idti-vs-khodit",
                "Verbos de movimento: идти vs ходить",
                """
# Verbos de movimento: идти vs ходить

O russo distingue movimento **unidirecional** (numa direção só, uma vez) de movimento **multidirecional** (ida e volta, repetido, ou sem direção definida) — para ir **a pé**.

| Verbo | Uso |
|---|---|
| идти | unidirecional: indo numa direção específica, AGORA |
| ходить | multidirecional: indo e voltando, repetidamente, ou "saber andar" em geral |

```
Я иду в школу.               Eu estou indo para a escola (agora, numa direção).
Я хожу в школу каждый день.  Eu vou à escola todo dia (repetição, ida e volta).
```

> 🎯 Isso é diferente do aspecto verbal (perfectivo/imperfectivo) — é uma categoria própria, só para verbos de movimento.
""",
                [
                    ex("quiz", 'Qual verbo se usa para uma ação repetida (ex: "vou à escola todo dia")?',
                       "ходить", ["ходить", "идти", "быть"]),
                    ex("text", "Traduza (movimento agora, numa direção): Eu estou indo para a escola. (я + иду + в + школу)",
                       "я иду в школу"),
                    ex("quiz", 'Qual verbo você usaria para dizer "meu filho já sabe andar" (habilidade geral, não uma vez só)?',
                       "ходить", ["ходить", "идти", "ехать"]),
                    ex("audio", "Escute e transcreva:", "я хожу в школу каждый день", audio_text="я хожу в школу каждый день"),
                    ex("quiz", 'Qual verbo indica ir AGORA, numa direção específica (a pé)?',
                       "идти", ["идти", "ходить", "бежать"]),
                    ex("speak", "Repita em voz alta:", "я иду в школу", audio_text="я иду в школу"),
                ],
            ),
            topic(
                "ekhat-vs-ezdit",
                "Verbos de movimento: ехать vs ездить",
                """
# Verbos de movimento: ехать vs ездить

O mesmo padrão de идти/ходить se aplica para ir **de veículo** (carro, ônibus, trem):

| Verbo | Uso |
|---|---|
| ехать | unidirecional: indo de veículo numa direção específica, AGORA |
| ездить | multidirecional: indo e voltando de veículo, repetidamente |

```
Я еду в Москву.              Eu estou indo para Moscou (agora, de veículo).
Я езжу на работу на машине.  Eu vou ao trabalho de carro (todo dia, repetição).
```

> 🎯 Atenção à conjugação: **еду/едет/едут** (ехать) vs **езжу/ездит/ездят** (ездить) — o "з" aparece no multidirecional.
""",
                [
                    ex("quiz", "Qual verbo indica ir de veículo AGORA, numa direção?",
                       "ехать", ["ехать", "ездить", "идти"]),
                    ex("text", "Traduza: Eu estou indo para Moscou. (я + еду + в + Москву)",
                       "я еду в москву"),
                    ex("quiz", "Qual verbo indica ir de carro TODO DIA (repetição)?",
                       "ездить", ["ездить", "ехать", "ходить"]),
                    ex("audio", "Escute e transcreva:", "я езжу на работу на машине", audio_text="я езжу на работу на машине"),
                    ex("quiz", 'Qual a 1ª pessoa de "ехать"?',
                       "еду", ["еду", "езжу", "едет"]),
                    ex("speak", "Repita em voz alta:", "я еду в москву", audio_text="я еду в москву"),
                ],
            ),
            topic(
                "letet-vs-letat",
                "Verbos de movimento: лететь vs летать",
                """
# Verbos de movimento: лететь vs летать

O mesmo padrão para voar:

| Verbo | Uso |
|---|---|
| лететь | unidirecional: voando numa direção específica, AGORA |
| летать | multidirecional: voando de um lado para outro, repetidamente, ou "saber voar" |

```
Самолёт летит в Москву.        O avião está voando para Moscou (agora).
Я часто летаю в Россию.        Eu voo frequentemente para a Rússia (repetição).
```

> 🎯 Mesma lógica: **-ть** unidirecional (лететь) vs **-ать** multidirecional (летать). Vale para os próximos pares também.
""",
                [
                    ex("quiz", "Qual verbo indica voar AGORA, numa direção?",
                       "лететь", ["лететь", "летать", "ехать"]),
                    ex("text", "Traduza: Eu voo frequentemente para a Rússia. (я + часто + летаю + в + Россию)",
                       "я часто летаю в россию"),
                    ex("quiz", "Qual verbo indica voar REPETIDAMENTE?",
                       "летать", ["летать", "лететь", "ездить"]),
                    ex("audio", "Escute e transcreva:", "самолёт летит в москву", audio_text="самолёт летит в москву"),
                    ex("quiz", 'Qual a 3ª pessoa singular de "лететь"?',
                       "летит", ["летит", "летает", "летят"]),
                    ex("speak", "Repita em voz alta:", "я часто летаю в россию", audio_text="я часто летаю в россию"),
                ],
            ),
            topic(
                "plyt-vs-plavat",
                "Verbos de movimento: плыть vs плавать",
                """
# Verbos de movimento: плыть vs плавать

E o padrão para nadar:

| Verbo | Uso |
|---|---|
| плыть | unidirecional: nadando numa direção específica, AGORA |
| плавать | multidirecional: nadando de um lado para outro, repetidamente, ou "saber nadar" |

```
Я плыву к берегу.          Eu estou nadando para a margem (agora).
Он хорошо плавает.         Ele nada bem (habilidade geral).
```

> 🎯 "плавать" também é usado para "saber nadar" (habilidade) — como "ходить" para "saber andar". É o padrão multidirecional de habilidade/repetição.
""",
                [
                    ex("quiz", "Qual verbo indica nadar AGORA, numa direção?",
                       "плыть", ["плыть", "плавать", "лететь"]),
                    ex("text", "Traduza: Ele nada bem. (он + хорошо + плавает)",
                       "он хорошо плавает"),
                    ex("quiz", 'Qual verbo indica "saber nadar" (habilidade geral)?',
                       "плавать", ["плавать", "плыть", "ходить"]),
                    ex("audio", "Escute e transcreva:", "я плыву к берегу", audio_text="я плыву к берегу"),
                    ex("quiz", 'Qual a 1ª pessoa de "плыть"?',
                       "плыву", ["плыву", "плаваю", "плывёт"]),
                    ex("speak", "Repita em voz alta:", "он хорошо плавает", audio_text="он хорошо плавает"),
                ],
            ),
            topic(
                "bezhat-vs-begat",
                "Verbos de movimento: бежать vs бегать",
                """
# Verbos de movimento: бежать vs бегать

E o último par comum — correr:

| Verbo | Uso |
|---|---|
| бежать | unidirecional: correndo numa direção específica, AGORA |
| бегать | multidirecional: correndo de um lado para outro, repetidamente, ou "saber correr" |

```
Я бегу в парк.            Eu estou correndo para o parque (agora).
Я бегаю по утрам.         Eu corro de manhã (repetição).
```

## O panorama dos pares de movimento

| Meio | Unidirecional | Multidirecional |
|---|---|---|
| a pé | идти | ходить |
| veículo | ехать | ездить |
| voo | лететь | летать |
| água | плыть | плавать |
| corrida | бежать | бегать |

> 🎯 Há uma tendência visível nos infinitivos (**идти/ходить**, **лететь/летать**), mas não transforme **-ть** versus **-ать** em regra universal. A distinção é lexical e aparece na conjugação: compare **я бегу/я бегаю** e **я плыву/я плаваю**. Memorize os cinco pares em contexto.
""",
                [
                    ex("quiz", "Qual verbo indica correr AGORA, numa direção?",
                       "бежать", ["бежать", "бегать", "идти"]),
                    ex("text", "Traduza: Eu corro de manhã. (я + бегаю + по утрам)",
                       "я бегаю по утрам"),
                    ex("quiz", 'Qual é o par unidirecional/multidirecional para VOAR?',
                       "лететь / летать", ["лететь / летать", "плыть / плавать", "бежать / бегать"]),
                    ex("quiz", "Qual verbo é usado para HABILIDADE geral (ex: \"saber nadar\")?",
                       "o multidirecional (плавать)", ["o multidirecional (плавать)", "o unidirecional (плыть)", "nenhum dos dois"]),
                    ex("audio", "Escute e transcreva:", "я бегу в парк", audio_text="я бегу в парк"),
                    ex("speak", "Repita em voz alta:", "я бегаю по утрам", audio_text="я бегаю по утрам"),
                ],
            ),
        ],
    )


# ============================================================
# MODULO 13 - Comunicacao (B1)
# ============================================================

def build_modulo_13_comunicacao_b1():
    return module(
        "modulo-13-comunicacao-b1",
        "Módulo 13 — Comunicação — B1",
        "Contar histórias com aspecto, opinar, falar de planos, pedidos educados, gostos e justificativas — com lacunas que forçam o caso e o aspecto certos.",
        [
            topic(
                "contando-historias-russo",
                "Contando histórias",
                """
# Contando histórias

Para narrar, combine o **passado** com a escolha de **aspecto** (Módulo 9) e os casos:

```
Вчера я читал книгу, а потом я прочитал её.
Ontem eu estava lendo o livro e depois o terminei.
(читал = processo; прочитал = resultado)

Он шёл домой и вдруг увидел друга.
Ele ia para casa e de repente viu um amigo.
(шёл = imperfectivo, ação em andamento; увидел = perfectivo, evento pontual)
```

> 🎯 O padrão da narrativa russa: **imperfectivo para o cenário/processo** + **perfectivo para o evento que aconteceu**. É a combinação mais natural ao contar histórias.
""",
                [
                    ex("quiz", 'Numa história, qual aspecto descreve o CENÁRIO/processo em andamento?',
                       "imperfectivo", ["imperfectivo", "perfectivo", "nenhum"]),
                    ex("text", "Traduza: Ontem eu li o livro até o fim. (вчера + я + прочитал + книгу)",
                       "вчера я прочитал книгу"),
                    ex("quiz", 'Em "Он шёл домой и увидел друга", qual verbo é o EVENTO pontual?',
                       "увидел", ["увидел", "шёл", "два eventos iguais"]),
                    ex("audio", "Escute e transcreva:", "он шёл домой и увидел друга", audio_text="Он шёл домой и увидел друга."),
                    ex("quiz", 'Complete com o perfectivo: "Вчера я ___ письмо другу." (написать)',
                       "написал", ["написал", "писал", "пишу"]),
                    ex("speak", "Repita em voz alta:", "вчера я прочитал книгу", audio_text="Вчера я прочитал книгу."),
                ],
            ),
            topic(
                "opinando",
                "Opiniões",
                """
# Opiniões

Para dar opinião em russo:

```
Я думаю, что...          Eu acho que...
По-моему, ...            Na minha opinião...
Я считаю, что...         Eu considero que...
```

## Exemplos

```
Я думаю, что это хорошая идея.     Eu acho que é uma boa ideia.
По-моему, этот фильм скучный.      Na minha opinião, este filme é chato.
Я считаю, что он прав.             Eu acho que ele tem razão.
```

> 🎯 Lacuna de caso: "этот фильм" (Nominativo), "о нём" (Preposicional). Ao opinar sobre alguém: "Я думаю о нём хорошо" (o + нём = Preposicional, M8).
""",
                [
                    ex("text", "Traduza: Eu acho que é uma boa ideia. (я + думаю + что + это + хорошая + идея)",
                       "я думаю что это хорошая идея"),
                    ex("quiz", 'Como se diz "na minha opinião"?',
                       "По-моему", ["По-моему", "Я думаю", "Где"]),
                    ex("quiz", 'Complete no Preposicional: "Я думаю о ___." (ele)',
                       "нём", ["нём", "него", "ним"]),
                    ex("audio", "Escute e transcreva:", "я считаю что он прав", audio_text="Я считаю, что он прав."),
                    ex("quiz", 'Qual expressão significa "eu considero que..."?',
                       "Я считаю, что...", ["Я считаю, что...", "По-моему...", "Сколько..."]),
                    ex("speak", "Repita em voz alta:", "по-моему этот фильм скучный", audio_text="По-моему, этот фильм скучный."),
                ],
            ),
            topic(
                "falando-de-planos-russo",
                "Falando de planos",
                """
# Falando de planos

Para falar do futuro (Módulo 10), escolha entre futuro composto (processo) e simples (resultado):

```
Я буду работать в Москве.      Eu vou trabalhar em Moscou. (futuro composto, imperfectivo)
Я куплю машину.                Eu vou comprar um carro. (futuro simples, perfectivo, resultado)
Я хочу поехать в Россию.       Eu quero viajar para a Rússia. (хочу + perfectivo infinitivo)
```

> 🎯 Lacuna de caso: "работать в Москве" (Preposicional), "поехать в Россию" (Acusativo de direção). Planos = futuro + casos.
""",
                [
                    ex("text", "Traduza: Eu quero viajar para a Rússia. (я + хочу + поехать + в + Россию)",
                       "я хочу поехать в россию"),
                    ex("quiz", 'Complete no futuro composto: "Я ___ работать в Москве." (быть, 1ª pessoa)',
                       "буду", ["буду", "будешь", "будет"]),
                    ex("quiz", 'Complete no futuro simples: "Я ___ машину." (купить)',
                       "куплю", ["куплю", "покупаю", "буду купить"]),
                    ex("audio", "Escute e transcreva:", "я хочу поехать в россию", audio_text="Я хочу поехать в Россию."),
                    ex("quiz", 'Em "работать в Москве", o caso é:', 
                       "Preposicional", ["Preposicional", "Acusativo", "Genitivo"]),
                    ex("speak", "Repita em voz alta:", "я куплю машину", audio_text="Я куплю машину."),
                ],
            ),
            topic(
                "pedidos-educados-b1",
                "Pedidos educados",
                """
# Pedidos educados

O B1 tem formas mais educadas de pedir:

```
Можно мне...?            Posso...?
Я хотел бы...            Eu gostaria de...
Не могли бы вы...?       O senhor/a senhora poderia...? (muito educado)
Пожалуйста!              Por favor!
```

## Exemplos

```
Я хотел бы поговорить с тобой.      Eu gostaria de conversar com você.
Не могли бы вы помочь мне?          Você poderia me ajudar? (мне = Dativo)
Можно мне ещё чая?                 Posso [ter] mais chá? (ещё чая = Genitivo)
```

> 🎯 A frase-motivo do curso começa aqui: **"Я хотел бы поговорить с тобой о том, что произошло вчера"** — "с тобой" (Instrumental), "о том" (Preposicional), "произошло" (perfectivo passado). Cada peça é um espiral que você já viu!
""",
                [
                    ex("text", "Traduza: Eu gostaria de conversar com você. (я + хотел бы + поговорить + с + тобой)",
                       "я хотел бы поговорить с тобой"),
                    ex("quiz", 'Complete no Dativo: "Не могли бы вы помочь ___ ?" (eu)',
                       "мне", ["мне", "меня", "мной"]),
                    ex("quiz", 'Em "Я хотел бы поговорить с тобой", o caso de "с тобой" é:', 
                       "Instrumental", ["Instrumental", "Preposicional", "Genitivo"]),
                    ex("audio", "Escute e transcreva:", "я хотел бы поговорить с тобой", audio_text="Я хотел бы поговорить с тобой."),
                    ex("quiz", 'Qual é a forma mais educada de pedir ("o senhor poderia...")?',
                       "Не могли бы вы...?", ["Не могли бы вы...?", "Хочу!", "Дайте!"]),
                    ex("speak", "Repita em voz alta:", "не могли бы вы помочь мне", audio_text="Не могли бы вы помочь мне?"),
                ],
            ),
            topic(
                "expressando-gostos",
                "Expressando gostos",
                """
# Expressando gostos

Para falar de gostos e preferências:

```
Мне нравится...          Eu gosto de... (Dativo impessoal, M8)
Я люблю...               Eu amo/gosto muito de... (Acusativo)
Я предпочитаю...         Eu prefiro... (Acusativo)
```

## Exemplos

```
Мне нравится русская музыка.     Eu gosto de música russa. (мне = Dativo)
Я люблю чай.                     Eu adoro chá. (чай = Acusativo)
Я предпочитаю кофе.              Eu prefiro café. (кофе = Acusativo)
```

> 🎯 Lacuna de caso: "Мне нравится ___" (o que agrada fica no Nominativo: музыка) vs "Я люблю ___" (o que amo fica no Acusativo: чай). Dois casos diferentes para "gostar"!
""",
                [
                    ex("text", "Traduza: Eu adoro chá. (я + люблю + чай)",
                       "я люблю чай"),
                    ex("quiz", 'Complete: "Мне ___ русская музыка." (agrada)',
                       "нравится", ["нравится", "люблю", "предпочитаю"]),
                    ex("quiz", 'Em "Я люблю чай", o caso de "чай" é:', 
                       "Acusativo", ["Acusativo", "Nominativo", "Dativo"]),
                    ex("audio", "Escute e transcreva:", "мне нравится русская музыка", audio_text="Мне нравится русская музыка."),
                    ex("quiz", 'Complete no Acusativo: "Я предпочитаю ___." (café)',
                       "кофе", ["кофе", "кофею", "кофем"]),
                    ex("speak", "Repita em voz alta:", "я люблю чай", audio_text="Я люблю чай."),
                ],
            ),
            topic(
                "desculpas-e-justificativas",
                "Desculpas e justificativas",
                """
# Desculpas e justificativas

Para se desculpar e explicar o porquê:

```
Извините!                 Desculpe!
К сожалению, ...          Infelizmente, ...
Потому что...             Porque...
Я не смог...              Eu não consegui... (perfectivo no passado)
```

## Exemplos

```
Извините за опоздание!          Desculpe o atraso!
Я не смог прийти, потому что был занят.   Não consegui vir porque estava ocupado.
К сожалению, я не успел.        Infelizmente, não consegui a tempo.
```

> 🎯 Lacuna de aspecto: "Я не смог прийти" (perfectivo — evento que não aconteceu) vs "Я не мог прийти" (imperfectivo — não tinha como, processo). A escolha muda o sentido!
""",
                [
                    ex("text", "Traduza: Desculpe o atraso! (Извините + за + опоздание)",
                       "извините за опоздание"),
                    ex("quiz", 'Complete com o perfectivo: "Я не ___ прийти." (consegui — смочь)',
                       "смог", ["смог", "мог", "могу"]),
                    ex("quiz", 'Qual frase indica que o evento NÃO aconteceu (não consegui vir)?',
                       "Я не смог прийти.", ["Я не смог прийти.", "Я не мог прийти.", "Я могу прийти."]),
                    ex("audio", "Escute e transcreva:", "извините за опоздание", audio_text="Извините за опоздание!"),
                    ex("quiz", 'Como se diz "porque"?',
                       "потому что", ["потому что", "поэтому", "к сожалению"]),
                    ex("speak", "Repita em voz alta:", "я не смог прийти", audio_text="Я не смог прийти."),
                ],
            ),
        ],
    )


# ============================================================
# MODULO 14 - Participios, Gerundios e Discurso Indireto (B2)
# ============================================================

def build_modulo_14_participios_gerundios_e_discurso_indireto():
    return module(
        "modulo-14-participios-gerundios-e-discurso-indireto",
        "Módulo 14 — Particípios, Gerúndios e Discurso Indireto — B2",
        "As formas verbais mais avançadas: particípios (причастия), gerúndios (деепричастия), o particípio passivo curto e o discurso indireto.",
        [
            topic(
                "participios",
                "Particípios (причастия)",
                """
# Particípios (причастия)

Os **particípios** são formas do verbo que funcionam como adjetivos — podem corresponder a "que está lendo" ou "que foi lido" em português, mas concordam em gênero/caso/número como qualquer adjetivo.

## Particípio ativo (quem pratica a ação)

```
читать -> читающий        (o que está lendo)
человек, читающий книгу    a pessoa que está lendo o livro
```

## Particípio passivo (quem sofre a ação)

```
читать -> читаемый        (o que é lido)
книга, читаемая всеми     o livro que está sendo lido por todos
```

> 🎯 Particípios são muito comuns na escrita formal/literária russa, mas raros na fala cotidiana — no dia a dia, russos preferem orações com "который" (Módulo 11): "человек, который читает книгу" em vez de "человек, читающий книгу".
""",
                [
                    ex("quiz", "O particípio ATIVO indica:",
                       "quem pratica a ação", ["quem pratica a ação", "quem sofre a ação", "o tempo verbal"]),
                    ex("quiz", "Na fala cotidiana, russos costumam substituir particípios por orações com:",
                       "который (que)", ["который (que)", "и (e)", "но (mas)"]),
                    ex("text", "Traduza usando \"который\" (mais natural na fala): a pessoa que lê o livro. (человек + который + читает + книгу)",
                       "человек который читает книгу"),
                    ex("audio", "Escute e transcreva:", "книга читаемая всеми", audio_text="книга, читаемая всеми"),
                    ex("quiz", "O particípio passivo (читаемый) indica:",
                       "quem sofre a ação (o que é lido)", ["quem sofre a ação (o que é lido)", "quem pratica a ação", "o tempo futuro"]),
                ],
            ),
            topic(
                "gerundios-russo",
                "Gerúndios (деепричастия)",
                """
# Gerúndios (деепричастия)

Os **gerúndios russos** (деепричастия) equivalem ao nosso "-ndo" (lendo, fazendo) — mas descrevem uma ação **secundária**, simultânea ou anterior à ação principal, e **não concordam** com nada (são invariáveis).

## Gerúndio imperfectivo (ação simultânea)

```
читать -> читая            lendo
Он шёл, читая книгу.       Ele andava, lendo um livro. (as duas ações ao mesmo tempo)
```

## Gerúndio perfectivo (ação anterior, já concluída)

```
прочитать -> прочитав       tendo lido
Прочитав книгу, он пошёл спать.   Tendo lido o livro, ele foi dormir.
```
""",
                [
                    ex("quiz", "O gerúndio russo (деепричастие) é:",
                       "invariável (não concorda com nada)", ["invariável (não concorda com nada)", "concorda em gênero", "concorda em caso"]),
                    ex("quiz", "Qual gerúndio indica uma ação JÁ CONCLUÍDA antes da principal?",
                       "perfectivo (ex: прочитав)", ["perfectivo (ex: прочитав)", "imperfectivo (ex: читая)", "nenhum dos dois"]),
                    ex("text", "Escreva o gerúndio imperfectivo de \"читать\" (ler), correspondente a \"lendo\".",
                       "читая"),
                    ex("audio", "Escute e transcreva:", "прочитав книгу он пошёл спать", audio_text="Прочитав книгу, он пошёл спать"),
                    ex("quiz", "O gerúndio IMPERFECTIVO (читая) indica ação:",
                       "simultânea à principal", ["simultânea à principal", "anterior e concluída", "futura"]),
                ],
            ),
            topic(
                "participio-passivo-curto",
                "O particípio passivo curto",
                """
# O particípio passivo curto

Assim como os adjetivos (Módulo 11), o particípio passivo também tem uma **forma curta**, e ela é extremamente comum — muito mais que a forma longa (-ый/-ая/-ое) no dia a dia, especialmente para descrever o resultado de uma ação.

## Formação e uso

A forma curta se forma cortando a terminação e concorda só em gênero/número (não em caso):

```
написанный -> написан / написана / написано / написаны

Письмо написано.        A carta está escrita. (resultado de "escrever")
Дверь закрыта.          A porta está fechada.
Магазин закрыт.         A loja está fechada.
```

> 🎯 Essa construção (particípio passivo curto + быть implícito) é como o russo forma a "voz passiva de resultado" — equivalente a "está feito/fechado/escrito" em português. É uma das estruturas mais usadas do nível B2 e vale a pena reconhecer de cara.
""",
                [
                    ex("quiz", 'Qual a forma curta feminina de "закрытый" (fechado)?',
                       "закрыта", ["закрыта", "закрытая", "закрыто"]),
                    ex("text", "Traduza: A carta está escrita. (письмо + написано)", "письмо написано"),
                    ex("quiz", "O particípio passivo curto concorda em:",
                       "gênero e número (não em caso)", ["gênero e número (não em caso)", "caso e gênero", "nada, é sempre invariável"]),
                    ex("audio", "Escute e transcreva:", "магазин закрыт", audio_text="магазин закрыт"),
                    ex("quiz", 'Complete a forma curta: "Дверь ___." (fechada — закрыть)',
                       "закрыта", ["закрыта", "закрыт", "закрыто"]),
                ],
            ),
            topic(
                "discurso-indireto-russo",
                "Discurso indireto",
                """
# Discurso indireto

O discurso indireto em russo é mais simples que em português/inglês: **não há mudança de tempo verbal** (backshift)! Só trocam os pronomes:

```
Он сказал: "Я устал".        Ele disse: "Estou cansado".
Он сказал, что он устал.     Ele disse que estava cansado. (o tempo continua o mesmo da fala original)
```

## Perguntas indiretas

Para perguntas com palavra interrogativa, usa-se a própria palavra; para perguntas de sim/não, usa-se **ли**:

```
Она спросила: "Где ты?"          Ela perguntou: "Onde você está?"
Она спросила, где я.             Ela perguntou onde eu estava.

Он спросил: "Ты идёшь?"          Ele perguntou: "Você vem?"
Он спросил, иду ли я.            Ele perguntou se eu vinha.
```

## Pedidos e ordens indiretos

Para transformar uma ordem/pedido em discurso indireto, usa-se **чтобы** + verbo no passado (mesmo se o original era imperativo):

```
Он сказал: "Читай книгу!"       Ele disse: "Leia o livro!"
Он сказал, чтобы я читал книгу. Ele disse para eu ler o livro.
```
""",
                [
                    ex("quiz", "No discurso indireto russo, comparado ao português, o tempo verbal normalmente:",
                       "é preservado quando o contexto continua válido", ["é preservado quando o contexto continua válido", "sempre vira passado", "sempre vira futuro"]),
                    ex("quiz", "Qual partícula é usada para transformar perguntas de SIM/NÃO em discurso indireto?",
                       "ли", ["ли", "что", "где"]),
                    ex("quiz", "Qual construção transforma um pedido/ordem em discurso indireto?",
                       "чтобы + passado", ["чтобы + passado", "что + presente", "ли + futuro"]),
                    ex("audio", "Escute e transcreva:", "она спросила где я", audio_text="она спросила, где я"),
                    ex("speak", "Repita em voz alta:", "он сказал что он устал", audio_text="он сказал, что он устал"),
                    ex("text", "Traduza: Ele disse para eu ler o livro. (он + сказал + чтобы + я + читал + книгу)",
                       "он сказал чтобы я читал книгу"),
                ],
            ),
            topic(
                "verbos-de-citacao",
                "Verbos de citação",
                """
# Verbos de citação

Para relatar, use verbos de fala com as conjunções certas:

| Verbo | Sentido | Conjunção |
|---|---|---|
| сказать | dizer | что (que) |
| спросить | perguntar | ли / palavra interrogativa |
| ответить | responder | что |
| объяснить | explicar | что / почему |
| попросить | pedir | чтобы |

## Exemplos

```
Он ответил, что не знает.       Ele respondeu que não sabe.
Она объяснила, почему опоздала.  Ela explicou por que se atrasou.
Он попросил, чтобы я подождал.   Ele pediu que eu esperasse.
```

> 🎯 Lacuna de espiral: "Он попросил, чтобы я подождал" usa **чтобы + passado** — o padrão de ordens indiretas do tópico anterior, agora com попросить (pedir).
""",
                [
                    ex("text", "Traduza: Ele respondeu que não sabe. (он + ответил + что + не + знает)",
                       "он ответил что не знает"),
                    ex("quiz", 'Qual verbo usa "чтобы" no relato?',
                       "попросить (pedir)", ["попросить (pedir)", "ответить (responder)", "объяснить (explicar)"]),
                    ex("quiz", 'Para relatar uma pergunta SIM/NÃO, usamos:',
                       "ли", ["ли", "что", "чтобы"]),
                    ex("audio", "Escute e transcreva:", "она объяснила почему опоздала", audio_text="Она объяснила, почему опоздала."),
                    ex("speak", "Repita em voz alta:", "он попросил чтобы я подождал", audio_text="Он попросил, чтобы я подождал."),
                    ex("quiz", 'Qual verbo significa "perguntar"?',
                       "спросить", ["спросить", "ответить", "объяснить"]),
                ],
            ),
        ],
    )


# ============================================================
# MODULO 15 - Verbos de Movimento com Prefixo (B2)
# ============================================================

def build_modulo_15_verbos_de_movimento_prefixados():
    return module(
        "modulo-15-verbos-de-movimento-prefixados",
        "Módulo 15 — Verbos de Movimento com Prefixo — B2",
        "Os prefixos при-/у-/в-/вы-/пере- combinados aos verbos de movimento, formando pares de aspecto e precisão de direção.",
        [
            topic(
                "prefixos-chegar-e-sair",
                "Prefixos при- (chegar) e у- (sair)",
                """
# Prefixos при- (chegar) e у- (sair)

Adicionar um prefixo a идти/ехать cria verbos novos com sentido preciso de direção — e, de quebra, já forma pares de aspecto perfectivo/imperfectivo (Módulo 9)!

| Prefixo | Sentido | A pé | De veículo |
|---|---|---|---|
| при- | chegar | прийти | приехать |
| у- | sair, ir embora | уйти | уехать |

```
Он пришёл домой.        Ele chegou em casa. (perfectivo)
Он ушёл с работы.       Ele saiu do trabalho. (perfectivo)
Мы приехали в Москву.   Chegamos a Moscou (de veículo). (в + Москву = Acusativo de direção)
```

> 🎯 Repare no espiral dos casos: "приехали в Москву" (Acusativo de direção, M8). O prefixo dá a direção; o caso confirma o destino.
""",
                [
                    ex("quiz", 'Qual prefixo indica "chegar"?',
                       "при-", ["при-", "у-", "вы-"]),
                    ex("text", "Traduza: Ele chegou em casa. (он + пришёл + домой)",
                       "он пришёл домой"),
                    ex("quiz", 'Qual verbo significa "sair, ir embora" (a pé)?',
                       "уйти", ["уйти", "прийти", "перейти"]),
                    ex("audio", "Escute e transcreva:", "мы приехали в москву", audio_text="Мы приехали в Москву."),
                    ex("quiz", 'Em "Мы приехали в Москву", o caso de "в Москву" é:', 
                       "Acusativo (direção)", ["Acusativo (direção)", "Preposicional (lugar)", "Genitivo"]),
                    ex("speak", "Repita em voz alta:", "он ушёл с работы", audio_text="Он ушёл с работы."),
                ],
            ),
            topic(
                "prefixos-entrar-e-sair",
                "Prefixos в- (entrar) e вы- (sair de dentro)",
                """
# Prefixos в- (entrar) e вы- (sair de dentro)

| Prefixo | Sentido | A pé | De veículo |
|---|---|---|---|
| в(о)- | entrar | войти | въехать |
| вы- | sair de dentro | выйти | выехать |

```
Он вошёл в комнату.        Ele entrou na sala. (в + комнату = Acusativo de direção)
Она вышла из комнаты.      Ela saiu da sala. (из + комнаты = Genitivo de origem, M8)
Машина выехала из города.  O carro saiu da cidade.
```

> 🎯 Contraste clássico do espiral: **в + Acusativo** (para onde entrou) vs **из + Genitivo** (de onde saiu). Os dois casos de movimento de M8 em ação.
""",
                [
                    ex("quiz", 'Qual verbo significa "entrar" (a pé)?',
                       "войти", ["войти", "выйти", "прийти"]),
                    ex("text", "Traduza: Ele entrou na sala. (он + вошёл + в + комнату)",
                       "он вошёл в комнату"),
                    ex("quiz", 'Em "Она вышла из комнаты", o caso de "из комнаты" é:', 
                       "Genitivo (origem)", ["Genitivo (origem)", "Acusativo (direção)", "Preposicional (lugar)"]),
                    ex("audio", "Escute e transcreva:", "она вышла из комнаты", audio_text="Она вышла из комнаты."),
                    ex("quiz", 'Qual prefixo indica "sair de dentro"?',
                       "вы-", ["вы-", "в(о)-", "у-"]),
                    ex("speak", "Repita em voz alta:", "он вошёл в комнату", audio_text="Он вошёл в комнату."),
                ],
            ),
            topic(
                "prefixo-pere",
                "Prefixo пере- (atravessar) e outros",
                """
# Prefixo пере- (atravessar) e outros

| Prefixo | Sentido | Exemplo (a pé) |
|---|---|---|
| пере- | atravessar / mudar de lugar | перейти (atravessar) |
| под- | aproximar-se (até bem perto) | подойти (chegar perto) |
| от- | afastar-se | отойти (afastar-se) |
| за- | passar rápido / de passagem | зайти (entrar de passagem) |

```
Мы перешли улицу.          Nós atravessamos a rua.
Он подошёл к окну.         Ele se aproximou da janela. (к + окну = Dativo, M8)
Он зашёл к другу.          Ele passou na casa de um amigo. (к + другу = Dativo)
```

> 🎯 Lacuna de caso: "подошёл к окну" e "зашёл к другу" usam **к + Dativo** (M8) — movimento até uma pessoa/coisa. O prefixo + caso trabalham juntos.
""",
                [
                    ex("quiz", 'Qual verbo significa "atravessar" (a pé)?',
                       "перейти", ["перейти", "подойти", "выйти"]),
                    ex("text", "Traduza: Nós atravessamos a rua. (мы + перешли + улицу)",
                       "мы перешли улицу"),
                    ex("quiz", 'Em "Он подошёл к окну", o caso de "к окну" é:', 
                       "Dativo", ["Dativo", "Acusativo", "Genitivo"]),
                    ex("audio", "Escute e transcreva:", "он подошёл к окну", audio_text="Он подошёл к окну."),
                    ex("quiz", 'Qual prefixo indica "passar de passagem" (зайти)?',
                       "за-", ["за-", "пере-", "от-"]),
                    ex("speak", "Repita em voz alta:", "мы перешли улицу", audio_text="Мы перешли улицу."),
                ],
            ),
            topic(
                "pares-imperfectivos-de-movimento",
                "Pares imperfectivos dos prefixados",
                """
# Pares imperfectivos dos prefixados

Muitos verbos de movimento prefixados são **perfectivos**, mas não todos: **войти** é perfectivo, enquanto **входить** é imperfectivo. Para formar o par imperfectivo, costuma-se trocar a raiz -йти/-ехать por -ходить/-езжать:

| Perfectivo | Imperfectivo | Sentido |
|---|---|---|
| прийти | приходить | chegar (a pé) |
| уйти | уходить | sair (a pé) |
| войти | входить | entrar |
| выйти | выходить | sair de dentro |
| перейти | переходить | atravessar |
| приехать | приезжать | chegar (de veículo) |

```
Он пришёл.              Ele chegou. (perfectivo, uma vez)
Он часто приходит.      Ele chega/vem com frequência. (imperfectivo, repetição)
Он приходит в 9 часов.  Ele chega às 9. (imperfectivo, rotina)
```

> 🎯 A escolha perfectivo/imperfectivo é o espiral do Módulo 9 aplicado ao movimento: perfectivo = uma vez/resultado; imperfectivo = repetição/rotina.
""",
                [
                    ex("quiz", 'Qual é o imperfectivo de "прийти" (chegar a pé)?',
                       "приходить", ["приходить", "пришёл", "приедет"]),
                    ex("text", "Traduza: Ele chega às 9. (он + приходит + в + 9 + часов)",
                       "он приходит в 9 часов"),
                    ex("quiz", 'Em "Он часто приходит", o aspecto é:', 
                       "imperfectivo (repetição)", ["imperfectivo (repetição)", "perfectivo (uma vez)", "não tem aspecto"]),
                    ex("audio", "Escute e transcreva:", "он часто приходит", audio_text="Он часто приходит."),
                    ex("quiz", 'Qual é o imperfectivo de "приехать" (chegar de veículo)?',
                       "приезжать", ["приезжать", "приехал", "приедет"]),
                    ex("speak", "Repita em voz alta:", "он приходит в 9 часов", audio_text="Он приходит в 9 часов."),
                ],
            ),
            topic(
                "movimento-prefixado-e-casos",
                "Movimento prefixado e os casos",
                """
# Movimento prefixado e os casos

Os prefixos de movimento exigem casos específicos no destino/origem:

| Prefixo | Caso do lugar | Exemplo |
|---|---|---|
| при-, в-, за- | Acusativo (direção, com в/на) | приехать в Москву |
| у-, вы- | Genitivo (origem, com из/с/от) | уехать из города |
| под-, за-, к | Dativo (aproximação, com к) | подойти к окну |
| пере- | Acusativo (atravessar) | перейти улицу |

```
Он приехал в Москву.        Ele chegou a Moscou. (в + Acusativo)
Она уехала из Москвы.       Ela saiu de Moscou. (из + Genitivo)
Я подошёл к другу.          Eu me aproximei do amigo. (к + Dativo)
```

> 🎯 Esse é o resumo do espiral de movimento + casos: cada prefixo "puxa" o destino/origem para o caso certo. Domine os três (Acusativo/Genitivo/Dativo) e o movimento fica automático.
""",
                [
                    ex("quiz", 'Para "chegar a" um lugar (приехать в...), o destino fica no:', 
                       "Acusativo", ["Acusativo", "Genitivo", "Dativo"]),
                    ex("text", "Traduza: Ela saiu de Moscou. (она + уехала + из + Москвы)",
                       "она уехала из москвы"),
                    ex("quiz", 'Para "aproximar-se de" alguém (подойти к...), usa-se:', 
                       "Dativo", ["Dativo", "Acusativo", "Preposicional"]),
                    ex("quiz", 'Para "sair de" um lugar (уехать из...), a origem fica no:', 
                       "Genitivo", ["Genitivo", "Acusativo", "Dativo"]),
                    ex("audio", "Escute e transcreva:", "она уехала из москвы", audio_text="Она уехала из Москвы."),
                    ex("speak", "Repita em voz alta:", "я подошёл к другу", audio_text="Я подошёл к другу."),
                ],
            ),
        ],
    )


# ============================================================
# MODULO 16 - Imperativo e Aspecto (B2)
# ============================================================

def build_modulo_16_imperativo_e_aspecto():
    return module(
        "modulo-16-imperativo-e-aspecto",
        "Módulo 16 — Imperativo e Aspecto — B2",
        "O modo imperativo (formal e informal), o imperativo negativo e a escolha de aspecto nas ordens e pedidos.",
        [
            topic(
                "modo-imperativo",
                "Modo imperativo",
                """
# Modo imperativo

O imperativo (dar ordens/pedidos) geralmente se forma a partir do radical do presente:

| Infinitivo | Imperativo (tu/você informal) | Imperativo (vocês/formal) |
|---|---|---|
| читать (ler) | читай! | читайте! |
| говорить (falar) | говори! | говорите! |
| идти (ir) | иди! | идите! |

```
Читай книгу!         Leia o livro! (informal)
Читайте книгу!       Leiam o livro! (formal/plural)
```

> 💡 A forma "вы" do imperativo sempre termina em **-те** — é um sinal fácil de reconhecer.
""",
                [
                    ex("quiz", "Qual terminação marca o imperativo formal/plural (вы)?",
                       "-те", ["-те", "-й", "-ешь"]),
                    ex("text", "Traduza (imperativo informal): Leia o livro! (читай + книгу)",
                       "читай книгу"),
                    ex("quiz", 'Qual o imperativo informal de "идти" (ir)?',
                       "иди", ["иди", "идёшь", "идите"]),
                    ex("audio", "Escute e transcreva:", "говорите", audio_text="говорите!"),
                    ex("quiz", 'Qual o imperativo informal de "читать" (ler)?',
                       "читай", ["читай", "читайте", "читаешь"]),
                    ex("speak", "Repita em voz alta:", "читай книгу", audio_text="Читай книгу!"),
                ],
            ),
            topic(
                "imperativo-negativo",
                "Imperativo negativo e o aspecto no imperativo",
                """
# Imperativo negativo e o aspecto no imperativo

## Negando uma ordem: не + imperativo

Basta colocar **не** antes do imperativo, exatamente como na negação comum (Módulo 3):

```
Не читай эту книгу!       Não leia esse livro!
Не говорите так!          Não fale assim! (formal)
```

## Qual aspecto usar no imperativo

A escolha entre imperfectivo e perfectivo (Módulo 9) também vale para ordens, e muda o tom:

- **Perfectivo**: um pedido pontual, focado no resultado — "Прочитай это!" (Leia isso [até o fim]!).
- **Imperfectivo**: um convite mais neutro, uma instrução geral, ou justamente para **proibir/pedir para não continuar** algo — "Не читай!" (Não leia! / Pare de ler!).
- **Perfectivo negativo**: também é natural quando se evita um evento ou resultado pontual — "Не забудь!" (Não esqueça!), "Не опоздай!" (Não se atrase!).

> ⚠️ Esse é um padrão curioso: o imperativo negativo prefere o imperfectivo mesmo quando a versão afirmativa da mesma ideia usaria o perfectivo — vale notar como exceção à intuição.
""",
                [
                    ex("quiz", "Como se nega um imperativo?",
                       "не + imperativo", ["не + imperativo", "imperativo + не", "нет + imperativo"]),
                    ex("text", "Traduza: Não leia esse livro! (не + читай + эту + книгу)",
                       "не читай эту книгу"),
                    ex("quiz", "Para uma proibição geral, qual aspecto costuma ser preferido no imperativo negativo?",
                       "imperfectivo", ["imperfectivo", "perfectivo", "não faz diferença"]),
                    ex("audio", "Escute e transcreva:", "не говорите так", audio_text="не говорите так"),
                    ex("quiz", "O imperativo PERFECTIVO (ex: Прочитай!) indica:",
                       "um pedido pontual, focado no resultado", ["um pedido pontual, focado no resultado", "uma instrução geral", "uma proibição"]),
                    ex("speak", "Repita em voz alta:", "не читай эту книгу", audio_text="Не читай эту книгу!"),
                ],
            ),
            topic(
                "aspecto-no-imperativo",
                "Escolhendo o aspecto no imperativo",
                """
# Escolhendo o aspecto no imperativo

A escolha do aspecto muda o tom do pedido:

| Aspecto | Tom | Exemplo |
|---|---|---|
| Perfectivo | pedido pontual, resultado | Позвони мне! (Ligue para mim!) |
| Imperfectivo | convite, instrução geral, repetição | Звони мне! (Ligue-me [sempre]!) |
| Imperfectivo negativo | proibição | Не звони! (Não ligue!) |

```
Позвони мне вечером!       Ligue para mim à noite! (perfectivo, uma vez)
Звони мне каждую неделю!   Ligue-me toda semana! (imperfectivo, repetição)
Открой окно!               Abra a janela! (perfectivo, resultado)
Открывай дверь!            Vá abrindo a porta! (imperfectivo, processo)
```

> 🎯 Regra prática: **perfectivo = ação única com resultado**; **imperfectivo = repetição/processo/conte**; **imperfectivo negativo = não faça**. O espiral do Módulo 9 aplicado às ordens.
""",
                [
                    ex("quiz", 'Para um pedido pontual ("ligue uma vez"), usamos:', 
                       "perfectivo (Позвони!)", ["perfectivo (Позвони!)", "imperfectivo (Звони!)", "não tem aspecto"]),
                    ex("text", "Traduza: Ligue-me toda semana! (Звони + мне + каждую + неделю)",
                       "звони мне каждую неделю"),
                    ex("quiz", 'Em "Открой окно!", o aspecto é:', 
                       "perfectivo (resultado)", ["perfectivo (resultado)", "imperfectivo (processo)", "nenhum"]),
                    ex("audio", "Escute e transcreva:", "позвони мне вечером", audio_text="Позвони мне вечером!"),
                    ex("quiz", 'Para PROIBIR ("não ligue!"), usamos:', 
                       "imperfectivo (Не звони!)", ["imperfectivo (Не звони!)", "perfectivo (Не позвони!)", "qualquer um"]),
                    ex("speak", "Repita em voz alta:", "позвони мне вечером", audio_text="Позвони мне вечером!"),
                ],
            ),
            topic(
                "imperativo-formal",
                "Imperativo formal (вы) e polidez",
                """
# Imperativo formal (вы) e polidez

Para ser educado, use a forma **вы** (-те) e acrescente "пожалуйста":

| Informal | Formal (вы) | Sentido |
|---|---|---|
| Скажи! | Скажите! | Diga! |
| Подожди! | Подождите! | Espere! |
| Помоги! | Помогите! | Ajude! |
| Скажи, пожалуйста! | Скажите, пожалуйста! | Diga, por favor! |

```
Скажите, пожалуйста, где вокзал?     Diga-me, por favor, onde fica a estação?
Подождите, пожалуйста!               Espere, por favor!
Помогите мне, пожалуйста!            Ajude-me, por favor! (мне = Dativo, M8)
```

> 🎯 Lacuna de caso: "Помогите ___" (мне) e "Скажите ___" (мне) exigem o **Dativo** — o espiral dos casos em pedidos educados.
""",
                [
                    ex("text", "Traduza: Diga-me, por favor, onde fica a estação? (Скажите + пожалуйста + где + вокзал)",
                       "скажите пожалуйста где вокзал"),
                    ex("quiz", 'Complete no Dativo: "Помогите ___ , пожалуйста!" (eu)',
                       "мне", ["мне", "меня", "мной"]),
                    ex("quiz", 'Qual é a forma FORMAL de "Подожди!"?',
                       "Подождите!", ["Подождите!", "Подожди!", "Подожду!"]),
                    ex("audio", "Escute e transcreva:", "скажите пожалуйста где вокзал", audio_text="Скажите, пожалуйста, где вокзал?"),
                    ex("speak", "Repita em voz alta:", "подождите пожалуйста", audio_text="Подождите, пожалуйста!"),
                    ex("quiz", "A forma formal do imperativo termina em:",
                       "-те", ["-те", "-й", "-ишь"]),
                ],
            ),
            topic(
                "pedidos-com-imperativo",
                "Pedidos com imperativo no dia a dia",
                """
# Pedidos com imperativo no dia a dia

Frases prontas com imperativo para o cotidiano:

```
Дай мне, пожалуйста...      Dê-me, por favor... (мне = Dativo)
Принеси мне...              Traga-me...
Покажи мне...               Mostre-me...
Расскажи мне...             Conte-me... (мне = Dativo)
```

```
Дай мне, пожалуйста, воды.       Dê-me água, por favor. (воды = Genitivo de quantidade)
Покажи мне свою фотографию.      Mostre-me sua foto. (фотографию = Acusativo)
Расскажи мне о себе.             Conte-me sobre você. (о + себе = Preposicional)
```

> 🎯 Três casos em três frases: **мне** (Dativo), **воды** (Genitivo de quantidade), **о себе** (Preposicional). O imperativo puxa o Dativo; o que se dá/traz puxa o Acusativo ou Genitivo.
""",
                [
                    ex("text", "Traduza: Dê-me, por favor, água. (Дай + мне + пожалуйста + воды)",
                       "дай мне пожалуйста воды"),
                    ex("quiz", 'Complete no Dativo: "Принеси ___ , пожалуйста, чай." (eu)',
                       "мне", ["мне", "меня", "мной"]),
                    ex("quiz", 'Em "Дай мне воды", o caso de "воды" é:', 
                       "Genitivo (quantidade)", ["Genitivo (quantidade)", "Acusativo", "Dativo"]),
                    ex("audio", "Escute e transcreva:", "покажи мне свою фотографию", audio_text="Покажи мне свою фотографию."),
                    ex("quiz", 'Em "Расскажи мне о себе", o caso de "о себе" é:', 
                       "Preposicional", ["Preposicional", "Acusativo", "Genitivo"]),
                    ex("speak", "Repita em voz alta:", "дай мне пожалуйста воды", audio_text="Дай мне, пожалуйста, воды."),
                ],
            ),
        ],
    )


# ============================================================
# MODULO 17 - Comparacao, Pronomes e Reflexivos (B2)
# ============================================================

def build_modulo_17_comparacao_pronomes_e_reflexivos():
    return module(
        "modulo-17-comparacao-pronomes-e-reflexivos",
        "Módulo 17 — Comparação, Pronomes e Reflexivos — B2",
        "Comparativo e superlativo, a comparação com чем, a forma curta dos adjetivos e os verbos reflexivos.",
        [
            topic(
                "comparativo-e-superlativo-russo",
                "Comparativo e superlativo",
                """
# Comparativo e superlativo

## Comparativo simples

A forma mais comum: troca a terminação do adjetivo por **-ее**:

```
новый -> новее          novo -> mais novo
красивый -> красивее    bonito -> mais bonito
```

Alguns são irregulares:

```
хороший -> лучше         bom -> melhor
плохой -> хуже           ruim -> pior
большой -> больше        grande -> maior
```

## Superlativo

A forma mais simples: **самый** + adjetivo (concordando em gênero/caso) + substantivo:

```
самый новый дом          a casa mais nova
```
""",
                [
                    ex("quiz", 'Qual o comparativo de "хороший" (bom)?',
                       "лучше", ["лучше", "хорошее", "более"]),
                    ex("text", "Traduza: mais bonito (красивее)", "красивее"),
                    ex("quiz", "Como se forma o superlativo de forma simples?",
                       "самый + adjetivo", ["самый + adjetivo", "adjetivo + -ее", "adjetivo + -ше"]),
                    ex("audio", "Escute e transcreva:", "самый новый дом", audio_text="самый новый дом"),
                    ex("quiz", 'Qual o comparativo de "плохой" (ruim)?',
                       "хуже", ["хуже", "плохее", "лучше"]),
                    ex("text", "Complete o superlativo: \"___ красивый город в мире.\" (самый)",
                       "самый"),
                ],
            ),
            topic(
                "comparacao-com-chem",
                "Comparando com чем",
                """
# Comparando com чем

Para dizer "A é melhor QUE B", use o comparativo + **чем** (que):

```
Он выше, чем я.            Ele é mais alto do que eu.
Москва больше, чем Сочи.   Moscou é maior do que Sochi.
Это лучше, чем то.         Isto é melhor do que aquilo.
```

Para igualdade: **такой же, как** (tão ... quanto):

```
Он такой же высокий, как я.    Ele é tão alto quanto eu.
```

> 🎯 Diferente do português, o segundo termo da comparação pode ficar no **Genitivo** em vez de "чем": "Он выше меня" (= "mais alto [do] que eu"). Duas formas equivalentes!
""",
                [
                    ex("text", "Traduza: Moscou é maior do que Sochi. (Москва + больше + чем + Сочи)",
                       "москва больше чем сочи"),
                    ex("quiz", "Qual palavra liga \"A é melhor QUE B\"?",
                       "чем", ["чем", "как", "чем-то"]),
                    ex("quiz", 'Outra forma de dizer "mais alto do que eu":',
                       "Он выше меня.", ["Он выше меня.", "Он выше я.", "Он выше чем."]),
                    ex("audio", "Escute e transcreva:", "москва больше чем сочи", audio_text="Москва больше, чем Сочи."),
                    ex("quiz", 'Para igualdade ("tão alto quanto"), usamos:',
                       "такой же, как", ["такой же, как", "более, чем", "самый"]),
                    ex("speak", "Repita em voz alta:", "он выше меня", audio_text="Он выше меня."),
                ],
            ),
            topic(
                "adjetivos-forma-curta",
                "A forma curta dos adjetivos",
                """
# A forma curta dos adjetivos

Além da forma "longa" que você já viu (новый, новая...), muitos adjetivos têm uma **forma curta**, usada como predicado (depois de "ser", que lembra: some no presente) — nunca antes do substantivo.

## Formação: tira a terminação

```
он рад            (curta, masc.) ele está feliz
она рада          (curta, fem.)  ela está feliz
они рады          (curta, plural) eles estão felizes

он счастлив       ele é feliz/afortunado
она свободна      ela está livre
```

## Longa x curta: qual usar

A forma **longa** descreve uma característica mais permanente ou vem antes do substantivo ("красивая девушка", uma moça bonita). A forma **curta** é usada como predicado e costuma soar mais formal ou descrever um estado momentâneo:

```
Девушка красивая.     A moça é bonita. (característica, forma longa)
Он рад.               Ele está feliz. (estado, só existe em forma curta para vários adjetivos)
```

> ⚠️ Nem todo adjetivo tem forma curta de uso comum — "рад" (feliz/contente), por exemplo, praticamente só existe na forma curta.
""",
                [
                    ex("quiz", 'Qual a forma curta feminina de "рад" (feliz)?',
                       "рада", ["рада", "радая", "радо"]),
                    ex("text", "Traduza (forma curta): Ele está feliz. (он + рад)", "он рад"),
                    ex("quiz", "A forma curta do adjetivo é usada:",
                       "como predicado, depois do sujeito", ["como predicado, depois do sujeito", "sempre antes do substantivo", "só no plural"]),
                    ex("audio", "Escute e transcreva:", "они рады", audio_text="они рады"),
                    ex("quiz", 'Qual a forma curta feminina de "свободный" (livre)?',
                       "свободна", ["свободна", "свободная", "свободно"]),
                    ex("text", "Traduza (forma curta): Ela está livre. (она + свободна)", "она свободна"),
                ],
            ),
            topic(
                "verbos-reflexivos",
                "Verbos reflexivos (-ся/-сь)",
                """
# Verbos reflexivos (-ся/-сь)

Muitos verbos russos ganham a partícula **-ся** (depois de consoante) ou **-сь** (depois de vogal) no final, indicando que a ação recai sobre o próprio sujeito, ou tem sentido recíproco/passivo:

```
мыть -> мыться           lavar -> lavar-se
одевать -> одеваться     vestir -> vestir-se
учить -> учиться         ensinar -> estudar (aprender por si mesmo)
```

## Conjugação

A partícula fica **grudada no final**, depois de todas as outras terminações:

```
я моюсь             eu me lavo
ты моешься          você se lava
он моется           ele se lava
```
""",
                [
                    ex("quiz", 'Qual a diferença entre "учить" e "учиться"?',
                       '"учить" é ensinar, "учиться" é estudar/aprender',
                       ['"учить" é ensinar, "учиться" é estudar/aprender', "são sinônimos exatos", '"учиться" não existe']),
                    ex("text", "Traduza: eu me lavo (я + моюсь)", "я моюсь"),
                    ex("quiz", 'Depois de qual tipo de som fica "-сь" em vez de "-ся"?',
                       "depois de vogal", ["depois de vogal", "depois de consoante", "nunca muda"]),
                    ex("audio", "Escute e transcreva:", "он одевается", audio_text="он одевается"),
                    ex("quiz", 'Qual é o reflexivo de "мыть" (lavar)?',
                       "мыться", ["мыться", "мыть", "мыл"]),
                    ex("speak", "Repita em voz alta:", "я моюсь", audio_text="я моюсь"),
                ],
            ),
            topic(
                "reflexivos-na-rotina",
                "Reflexivos na rotina",
                """
# Reflexivos na rotina

Muitos verbos da rotina são reflexivos:

| Verbo reflexivo | Sentido |
|---|---|
| просыпаться | acordar |
| вставать | levantar-se |
| мыться | lavar-se |
| одеваться | vestir-se |
| ложиться спать | deitar-se para dormir |
| отдыхать | descansar |

```
Я просыпаюсь в семь часов.      Eu acordo às sete.
Я одеваюсь и иду на работу.     Eu me visto e vou trabalhar. (на + работу = Acusativo)
Он ложится спать в одиннадцать.  Ele se deita às onze.
```

> 🎯 Lacuna de caso: "идти на работу" (Acusativo de direção, M8) depois do reflexivo "одеваюсь". A rotina junta reflexivos + casos + movimento — o espiral completo!
""",
                [
                    ex("text", "Traduza: Eu acordo às sete. (я + просыпаюсь + в + семь + часов)",
                       "я просыпаюсь в семь часов"),
                    ex("quiz", 'Como se diz "vestir-se"?',
                       "одеваться", ["одеваться", "одевать", "одеваю"]),
                    ex("quiz", 'Em "Я иду на работу", o caso é:', 
                       "Acusativo (direção)", ["Acusativo (direção)", "Preposicional (lugar)", "Genitivo"]),
                    ex("audio", "Escute e transcreva:", "он ложится спать в одиннадцать", audio_text="Он ложится спать в одиннадцать."),
                    ex("quiz", 'Como se diz "levantar-se"?',
                       "вставать", ["вставать", "встать нет", "стоять"]),
                    ex("speak", "Repita em voz alta:", "я одеваюсь и иду на работу", audio_text="Я одеваюсь и иду на работу."),
                ],
            ),
        ],
    )


# ============================================================
# MODULO 18 - Vocabulario e Expressoes (B2)
# ============================================================

def build_modulo_18_vocabulario_e_expressoes_b2():
    return module(
        "modulo-18-vocabulario-e-expressoes-b2",
        "Módulo 18 — Vocabulário e Expressões — B2",
        "Expressões do dia a dia, colocações com casos, verbos com prefixo, expressões de tempo, frases prontas e expressões idiomáticas.",
        [
            topic(
                "expressoes-do-dia-a-dia-russo",
                "Expressões do dia a dia",
                """
# Expressões do dia a dia

Frases prontas que flexionam casos:

```
Мне всё равно.           Para mim tanto faz. (мне = Dativo)
Я с удовольствием.       Com prazer. (с + удовольствием = Instrumental)
У меня нет времени.      Não tenho tempo. (нет + времени = Genitivo)
Мне надо работать.       Preciso trabalhar. (мне = Dativo)
```

> 🎯 Cada expressão fixa carrega um caso do espiral: **мне** (Dativo), **с удовольствием** (Instrumental), **нет времени** (Genitivo). Aprenda a expressão inteira — o caso vem junto.
""",
                [
                    ex("text", "Traduza: Não tenho tempo. (у + меня + нет + времени)",
                       "у меня нет времени"),
                    ex("quiz", 'Em "Мне всё равно", o caso de "мне" é:', 
                       "Dativo", ["Dativo", "Acusativo", "Genitivo"]),
                    ex("quiz", 'Em "Я с удовольствием", o caso é:', 
                       "Instrumental", ["Instrumental", "Preposicional", "Dativo"]),
                    ex("audio", "Escute e transcreva:", "мне всё равно", audio_text="Мне всё равно."),
                     ex("quiz", 'Qual forma está correta na expressão "com prazer"?',
                        "С удовольствием", ["С удовольствием", "С удовольствие", "С удовольствию"]),
                    ex("speak", "Repita em voz alta:", "мне надо работать", audio_text="Мне надо работать."),
                ],
            ),
            topic(
                "colocacoes-com-casos",
                "Colocações com casos",
                """
# Colocações com casos

Como no inglês (collocations), certas combinações exigem o caso certo:

| Colocação | Caso | Exemplo |
|---|---|---|
| интересоваться + Instrumental | Instrumental | интересоваться музыкой (interessar-se por música) |
| гордиться + Instrumental | Instrumental | гордиться сыном (orgulhar-se do filho) |
| ждать + Genitivo/Acusativo | Genitivo ou Acusativo | ждать автобуса / ждать автобус (conforme contexto) |
| бояться + Genitivo | Genitivo | бояться собак (ter medo de cães) |
| помогать + Dativo | Dativo | помогать маме (ajudar a mãe) |

```
Он интересуется музыкой.       Ele se interessa por música. (музыкой = Instrumental)
Я помогаю маме.                Eu ajudo minha mãe. (маме = Dativo)
Ребёнок боится собак.          A criança tem medo de cães. (собак = Genitivo)
```

> 🎯 O verbo "puxa" o caso — como "gostar DE" em português. Memorize verbo + caso juntos: "интересоваться музыкой", "помогать маме".
""",
                [
                    ex("text", "Traduza: Eu ajudo minha mãe. (я + помогаю + маме)",
                       "я помогаю маме"),
                    ex("quiz", 'Complete no Instrumental: "Он интересуется ___." (música)',
                       "музыкой", ["музыкой", "музыку", "музыка"]),
                    ex("quiz", 'Qual verbo exige Genitivo ("ter medo de")?',
                       "бояться", ["бояться", "гордиться", "помогать"]),
                    ex("audio", "Escute e transcreva:", "ребёнок боится собак", audio_text="Ребёнок боится собак."),
                    ex("quiz", 'Complete no Dativo: "Я помогаю ___." (mãe)',
                       "маме", ["маме", "маму", "мама"]),
                    ex("speak", "Repita em voz alta:", "он интересуется музыкой", audio_text="Он интересуется музыкой."),
                ],
            ),
            topic(
                "verbos-com-prefixo",
                "Verbos com prefixo (coloquial)",
                """
# Verbos com prefixo (coloquial)

Além dos de movimento (Módulo 15), muitos verbos comuns usam prefixos para criar novos sentidos:

| Verbo | Prefixo | Sentido |
|---|---|---|
| звонить -> позвонить | по- | ligar (ação única) |
| читать -> прочитать | про- | ler até o fim |
| делать -> сделать | с- | fazer (concluído) |
| говорить -> сказать | с- | dizer (uma vez) |
| понимать -> понять | по- | entender (de repente/completo) |

```
Я понял!                  Eu entendi! (perfectivo, de repente)
Он позвонил вчера.        Ele ligou ontem. (perfectivo, uma vez)
```

> 🎯 Um prefixo frequentemente cria um perfectivo, mas também pode acrescentar uma nuance lexical; confirme sempre o par. "Звонил" (processo) contrasta com "позвонил" (ligou uma vez), enquanto outros verbos prefixados precisam ser aprendidos como unidades.
""",
                [
                    ex("quiz", 'Qual é o perfectivo de "звонить" (ligar)?',
                       "позвонить", ["позвонить", "звоню", "звонит"]),
                    ex("text", "Traduza: Ele ligou ontem. (он + позвонил + вчера)",
                       "он позвонил вчера"),
                    ex("quiz", 'O prefixo "по-" em "понять" indica:', 
                       "ação completa/de repente", ["ação completa/de repente", "processo contínuo", "repetição"]),
                    ex("audio", "Escute e transcreva:", "я понял", audio_text="Я понял!"),
                    ex("quiz", 'Qual é o perfectivo de "понимать" (entender)?',
                       "понять", ["понять", "понимаю", "понимал"]),
                    ex("speak", "Repita em voz alta:", "он позвонил вчера", audio_text="Он позвонил вчера."),
                ],
            ),
            topic(
                "expressoes-de-tempo",
                "Expressões de tempo e os casos",
                """
# Expressões de tempo e os casos

As expressões de tempo usam vários casos:

| Expressão | Caso | Exemplo |
|---|---|---|
| в + dia da semana (Acusativo) | Acusativo | в понедельник (na segunda) |
| в + mês (Preposicional) | Preposicional | в мае (em maio) |
| через + tempo (Acusativo) | Acusativo | через час (daqui a uma hora) |
| назад + tempo (Acusativo) | Acusativo | год назад (há um ano) |
| с утра до вечера | Genitivo | (de manhã até à noite) |

```
Я работаю в понедельник.     Eu trabalho na segunda. (в + понедельник = Acusativo)
Мы встретимся через час.     Nós nos encontraremos daqui a uma hora.
Он уехал год назад.          Ele partiu há um ano.
```

> 🎯 Lacuna de caso: "в понедельник" (Acusativo), "в мае" (Preposicional), "с утра" (Genitivo) — as expressões de tempo são um mini-espiral dos casos.
""",
                [
                    ex("text", "Traduza: Eu trabalho na segunda. (я + работаю + в + понедельник)",
                       "я работаю в понедельник"),
                    ex("quiz", 'Em "в понедельник", o caso é:', 
                       "Acusativo", ["Acusativo", "Preposicional", "Genitivo"]),
                    ex("quiz", 'Em "в мае", o caso é:', 
                       "Preposicional", ["Preposicional", "Acusativo", "Nominativo"]),
                    ex("audio", "Escute e transcreva:", "мы встретимся через час", audio_text="Мы встретимся через час."),
                    ex("quiz", 'Em "год назад" (há um ano), a ideia é:', 
                       "tempo decorrido", ["tempo decorrido", "tempo futuro", "um horário fixo"]),
                    ex("speak", "Repita em voz alta:", "он уехал год назад", audio_text="Он уехал год назад."),
                ],
            ),
            topic(
                "frases-prontas",
                "Frases prontas do cotidiano",
                """
# Frases prontas do cotidiano

Expressões fixas que você usa toda hora — cada uma com seu caso:

```
Как дела?                  Como vai?
Всё хорошо!                Está tudo bem!
Ничего страшного!          Não tem problema!
Кстати, ...                Aliás, ...
К сожалению, ...           Infelizmente, ...
По-моему, ...              Na minha opinião, ...
На здоровье!               De nada! (literalmente "à saúde")
```

```
Кстати, я видел его вчера.       Aliás, eu o vi ontem.
К сожалению, я не могу прийти.   Infelizmente, não posso vir.
```

> 🎯 "На здоровье" usa o Preposicional (на + здоровье). "К сожалению" é fixo. Aprenda frases prontas como blocos — o caso vem embutido.
""",
                [
                    ex("text", "Traduza: Aliás, eu o vi ontem. (Кстати + я + видел + его + вчера)",
                       "кстати я видел его вчера"),
                    ex("quiz", 'Como se diz "Infelizmente, ..."?',
                       "К сожалению, ...", ["К сожалению, ...", "Кстати, ...", "По-моему, ..."]),
                    ex("quiz", 'Em "На здоровье!", o caso é:', 
                       "Preposicional", ["Preposicional", "Acusativo", "Genitivo"]),
                    ex("audio", "Escute e transcreva:", "к сожалению я не могу прийти", audio_text="К сожалению, я не могу прийти."),
                    ex("quiz", 'Como se diz "Não tem problema!"?',
                       "Ничего страшного!", ["Ничего страшного!", "Всё хорошо!", "Как дела?"]),
                    ex("speak", "Repita em voz alta:", "кстати я видел его вчера", audio_text="Кстати, я видел его вчера."),
                ],
            ),
            topic(
                "expressoes-idiomaticas-russo",
                "Expressões idiomáticas",
                """
# Expressões idiomáticas

Idioms russos — sentido figurado, caso embutido:

| Idiom | Tradução literal | Sentido |
|---|---|---|
| бить баклуши | bater nas panelas | não fazer nada, vadiar |
| витать в облаках | flutuar nas nuvens | sonhar acordado |
| сломя голову | quebrando a cabeça | a toda velocidade |
| зарубить на носу | marcar no nariz | gravar na memória |
| медведь на ухо наступил | o urso pisou na orelha | não ter ouvido musical |

```
Не бей баклуши!                   Não fique aí à toa!
Он витает в облаках на уроке.     Ele está nas nuvens na aula. (в + облаках = Preposicional plural)
```

> 🎯 Os idioms fixam o caso: "в облаках" (Preposicional plural, M8), "на носу" (Preposicional). Idiom + caso andam juntos.
""",
                [
                    ex("text", "Traduza: Ele está nas nuvens na aula. (он + витает + в + облаках + на + уроке)",
                       "он витает в облаках на уроке"),
                    ex("quiz", 'Em "витать в облаках", o caso é:', 
                       "Preposicional", ["Preposicional", "Acusativo", "Genitivo"]),
                    ex("quiz", 'Qual idiom significa "não fazer nada, vadiar"?',
                       "бить баклуши", ["бить баклуши", "зарубить на носу", "сломя голову"]),
                    ex("audio", "Escute e transcreva:", "он витает в облаках на уроке", audio_text="Он витает в облаках на уроке."),
                    ex("quiz", 'Em "в облаках", o número do substantivo é:', 
                       "plural", ["plural", "singular", "não tem número"]),
                    ex("speak", "Repita em voz alta:", "он витает в облаках", audio_text="Он витает в облаках."),
                ],
            ),
        ],
    )


# ============================================================
# MODULO 19 - Casos em Frases Complexas (C1)
# ============================================================

def build_modulo_19_casos_em_frases_complexas():
    return module(
        "modulo-19-casos-em-frases-complexas",
        "Módulo 19 — Casos em Frases Complexas — C1",
        "Orações relativas com который em todos os casos, particípios concordando em caso, frases com várias orações e a frase-motivo completa do curso.",
        [
            topic(
                "relativas-em-todos-os-casos",
                "Orações relativas: который em todos os casos",
                """
# Orações relativas: который em todos os casos

O pronome relativo **который** (Módulo 11) declina em todos os casos, conforme a função que desempenha na oração:

| Caso | Masculino | Feminino | Função |
|---|---|---|---|
| Nominativo | который | которая | sujeito |
| Acusativo | которого/который | которую | objeto |
| Genitivo | которого | которой | posse/negação |
| Dativo | которому | которой | objeto indireto |
| Instrumental | которым | которой | meio/companhia |
| Preposicional | котором | которой | lugar/assunto |

```
Человек, которому я пишу, — мой друг.        O homem a quem escrevo é meu amigo. (Dativo)
Книга, о которой я думаю, — интересная.      O livro no qual penso é interessante. (Preposicional)
Друг, с которым я работаю, — умный.          O amigo com quem trabalho é inteligente. (Instrumental)
```

> 🎯 Esse é o espiral dos casos aplicado ao "que" — todos os 6 casos do Módulo 8 aparecem aqui. Se você domina который, domina a relativização russa.
""",
                [
                    ex("text", "Traduza: O homem a quem escrevo é meu amigo. (Человек + которому + я + пишу + мой + друг)",
                       "человек которому я пишу мой друг"),
                    ex("quiz", 'Complete no Instrumental: "Друг, с ___ я работаю, — умный." (который)',
                       "которым", ["которым", "которому", "которого"]),
                    ex("quiz", 'Complete no Preposicional feminino: "Книга, о ___ я думаю, — интересная." (которая)',
                       "которой", ["которой", "которую", "которая"]),
                    ex("audio", "Escute e transcreva:", "книга о которой я думаю интересная", audio_text="Книга, о которой я думаю, интересная."),
                    ex("quiz", 'Complete no Dativo: "Человек, ___ я пишу, — мой друг." (который)',
                       "которому", ["которому", "которого", "которым"]),
                    ex("speak", "Repita em voz alta:", "друг с которым я работаю умный", audio_text="Друг, с которым я работаю, умный."),
                ],
            ),
            topic(
                "participios-em-casos",
                "Particípios concordando em caso",
                """
# Particípios concordando em caso

Como os particípios funcionam como adjetivos (Módulo 14), eles **concordam em caso** com o substantivo:

```
Я вижу человека, читающего книгу.       Eu vejo o homem que está lendo o livro.
(читающего = particípio no Acusativo, concordando com человека)

Он разговаривает с девушкой, читающей книгу.
Ele conversa com a moça que está lendo o livro.
(читающей = particípio no Instrumental, concordando com девушкой)
```

> 🎯 O particípio declina como um adjetivo: no Acusativo é "читающего" (masculino), no Instrumental "читающей" (feminino). É o espiral de M11/M14 aplicado.
""",
                [
                    ex("quiz", "Os particípios concordam com o substantivo em:",
                       "gênero, número e caso (como adjetivos)", ["gênero, número e caso (como adjetivos)", "apenas em número", "nada, são invariáveis"]),
                    ex("text", "Complete no Acusativo: \"Я вижу человека, ___ книгу.\" (читать)",
                       "читающего"),
                    ex("quiz", 'Complete no Instrumental feminino: "Он говорит с девушкой, ___ книгу." (читать)',
                       "читающей", ["читающей", "читающую", "читающая"]),
                    ex("audio", "Escute e transcreva:", "я вижу человека читающего книгу", audio_text="Я вижу человека, читающего книгу."),
                    ex("quiz", "Qual é a forma do particípio de \"читать\" que concorda com um substantivo MASCULINO no Acusativo?",
                       "читающего", ["читающего", "читающей", "читающий"]),
                ],
            ),
            topic(
                "frases-com-varias-oracoes",
                "Frases com várias orações",
                """
# Frases com várias orações

No C1, as frases combinam várias orações com conjunções e casos:

```
Я знаю, что он работает в банке.
Eu sei que ele trabalha no banco. (в + банке = Preposicional)

Она сказала, что видела человека, который работает с ней.
Ela disse que viu o homem que trabalha com ela. (с + ней = Instrumental)

Я надеюсь, что мы встретимся, хотя я очень занят.
Espero que nos encontremos, embora esteja muito ocupado.
```

> 🎯 Cada oração exige seus próprios casos: "в банке" (Preposicional), "с ней" (Instrumental), "который работает" (Nominativo). Frases complexas = casos em cascata.
""",
                [
                    ex("text", "Traduza: Eu sei que ele trabalha no banco. (я + знаю + что + он + работает + в + банке)",
                       "я знаю что он работает в банке"),
                    ex("quiz", 'Em "он работает в банке", o caso é:', 
                       "Preposicional", ["Preposicional", "Acusativo", "Genitivo"]),
                    ex("quiz", 'Em "который работает с ней", o caso de "с ней" é:', 
                       "Instrumental", ["Instrumental", "Preposicional", "Dativo"]),
                    ex("audio", "Escute e transcreva:", "она сказала что видела человека", audio_text="Она сказала, что видела человека."),
                    ex("quiz", 'Como se diz "embora"?',
                       "хотя", ["хотя", "потому что", "чтобы"]),
                    ex("speak", "Repita em voz alta:", "я знаю что он работает в банке", audio_text="Я знаю, что он работает в банке."),
                ],
            ),
            topic(
                "conjuncoes-complexas",
                "Conjunções complexas",
                """
# Conjunções complexas

Para construir frases complexas, use as conjunções certas:

| Conjunção | Sentido |
|---|---|
| хотя | embora |
| потому что | porque |
| чтобы | para que |
| если | se |
| когда | quando |
| который | que (relativo) |

```
Хотя он устал, он работает.          Embora esteja cansado, ele trabalha.
Я учусь, чтобы найти работу.          Eu estudo para encontrar trabalho. (чтобы + infinitivo)
Если будет время, я позвоню.          Se tiver tempo, ligarei. (se + futuro)
```

> 🎯 Lacuna de aspecto: "я позвоню" (perfectivo futuro — ação única) em "Если будет время". A conjunção + o aspecto trabalham juntos.
""",
                [
                    ex("text", "Traduza: Embora esteja cansado, ele trabalha. (Хотя + он + устал + он + работает)",
                       "хотя он устал он работает"),
                    ex("quiz", 'Qual conjunção significa "para que"?',
                       "чтобы", ["чтобы", "потому что", "хотя"]),
                    ex("quiz", 'Complete com o perfectivo futuro: "Если будет время, я ___." (ligar — позвонить)',
                       "позвоню", ["позвоню", "звоню", "буду звонить"]),
                    ex("audio", "Escute e transcreva:", "я учусь чтобы найти работу", audio_text="Я учусь, чтобы найти работу."),
                    ex("quiz", 'Qual conjunção significa "se"?',
                       "если", ["если", "когда", "хотя"]),
                    ex("speak", "Repita em voz alta:", "хотя он устал он работает", audio_text="Хотя он устал, он работает."),
                ],
            ),
            topic(
                "frase-motivo-completa",
                "A frase-motivo completa",
                """
# A frase-motivo completa

Lembra da meta do curso (Módulo 1)? Aqui está ela, peça por peça:

> **Я хотел бы поговорить с тобой о том, что произошло вчера.**
> ("Eu gostaria de conversar com você sobre o que aconteceu ontem.")

| Peça | Gramática |
|---|---|
| Я хотел бы | хотеть no passado + бы (condicional, M10) |
| поговорить | perfectivo infinitivo (ação completa, M9) |
| с тобой | с + Instrumental (M8) |
| о том | Preposicional (M8) |
| что произошло | oração relativa (M11) |
| вчера | advérbio de tempo |

```
Я хотел бы поговорить с тобой о том, что произошло вчера.
```

> 🏆 Se você consegue **produzir** essa frase de cabeça, sem travar, o currículo em espiral cumpriu seu papel — cada peça foi vista e revisada ao longo dos níveis.
""",
                [
                    ex("text", "Complete a frase-motivo: \"Я хотел бы ___ с тобой о том, что произошло вчера.\" (поговорить)",
                       "поговорить"),
                    ex("quiz", 'Em "с тобой", o caso é:', 
                       "Instrumental", ["Instrumental", "Preposicional", "Dativo"]),
                    ex("quiz", 'Em "о том", o caso é:', 
                       "Preposicional", ["Preposicional", "Acusativo", "Genitivo"]),
                    ex("audio", "Escute e transcreva:", "я хотел бы поговорить с тобой о том что произошло вчера", audio_text="Я хотел бы поговорить с тобой о том, что произошло вчера."),
                    ex("quiz", 'Em "что произошло", o verbo "произошло" é:', 
                       "perfectivo no passado", ["perfectivo no passado", "imperfectivo no presente", "futuro composto"]),
                    ex("speak", "Repita em voz alta:", "я хотел бы поговорить с тобой о том что произошло вчера", audio_text="Я хотел бы поговорить с тобой о том, что произошло вчера."),
                ],
            ),
            topic(
                "relatando-acontecimentos",
                "Relatando acontecimentos",
                """
# Relatando acontecimentos

Para contar o que aconteceu, combine casos + aspecto + conjunções:

```
Вчера я был на работе, когда мне позвонили.
Ontem eu estava no trabalho quando me ligaram. (на + работе = Preposicional; мне = Dativo)

Я рассказал другу о том, что случилось.
Eu contei ao amigo o que aconteceu. (другу = Dativo; о том = Preposicional)

Мы поговорили обо всём, что произошло.
Nós conversamos sobre tudo o que aconteceu. (обо всём = Preposicional)
```

> 🎯 Três casos num relato: **на работе** (Preposicional), **мне/другу** (Dativo), **о том/обо всём** (Preposicional). E o perfectivo **позвонили/случилось/произошло** para eventos pontuais.
""",
                [
                    ex("text", "Traduza: Eu contei ao amigo o que aconteceu. (я + рассказал + другу + о том + что + случилось)",
                       "я рассказал другу о том что случилось"),
                    ex("quiz", 'Em "на работе", o caso é:', 
                       "Preposicional", ["Preposicional", "Acusativo", "Genitivo"]),
                    ex("quiz", 'Complete no Dativo: "Вчера ___ позвонили." (eu)',
                       "мне", ["мне", "меня", "мной"]),
                    ex("audio", "Escute e transcreva:", "вчера я был на работе когда мне позвонили", audio_text="Вчера я был на работе, когда мне позвонили."),
                    ex("quiz", 'Em "обо всём", o caso é:', 
                       "Preposicional", ["Preposicional", "Instrumental", "Dativo"]),
                    ex("speak", "Repita em voz alta:", "я рассказал другу о том что случилось", audio_text="Я рассказал другу о том, что случилось."),
                ],
            ),
        ],
    )


# ============================================================
# MODULO 20 - Aspecto e Nuance (C1)
# ============================================================

def build_modulo_20_aspecto_e_nuance():
    return module(
        "modulo-20-aspecto-e-nuance",
        "Módulo 20 — Aspecto e Nuance — C1",
        "A escolha sutil do aspecto (processo vs resultado, repetição vs uma vez), a nuance dos prefixos e o aspecto na conversa natural.",
        [
            topic(
                "processo-vs-resultado",
                "Processo vs resultado",
                """
# Processo vs resultado

A escolha do aspecto (Módulo 9) carrega nuance sutil no C1:

```
Я читал статью, но не закончил.      Eu lia o artigo, mas não terminei. (imperfectivo, processo)
Я прочитал статью.                  Eu li o artigo até o fim. (perfectivo, resultado)

Он писал письмо час.                Ele escreveu a carta por uma hora. (imperfectivo, duração)
Он написал письмо.                  Ele escreveu a carta. (perfectivo, concluída)
```

> 🎯 O imperfectivo destaca o **processo/duração**; o perfectivo o **resultado**. No C1, essa escolha é tão natural que muda a história que você conta.
""",
                [
                    ex("quiz", "Qual frase destaca a DURAÇÃO/processo?",
                       "Он писал письмо час.", ["Он писал письмо час.", "Он написал письмо.", "Он пишет письмо."]),
                    ex("text", "Complete com o perfectivo: \"Я ___ статью до конца.\" (ler — прочитать)",
                       "прочитал"),
                    ex("quiz", 'Em "Он писал письмо час", o aspecto é:', 
                       "imperfectivo (processo/duração)", ["imperfectivo (processo/duração)", "perfectivo (resultado)", "não tem"]),
                    ex("audio", "Escute e transcreva:", "я читал статью но не закончил", audio_text="Я читал статью, но не закончил."),
                    ex("quiz", "O imperfectivo no passado destaca:",
                       "o processo e a duração", ["o processo e a duração", "o resultado final", "o futuro"]),
                    ex("speak", "Repita em voz alta:", "я прочитал статью", audio_text="Я прочитал статью."),
                ],
            ),
            topic(
                "repeticao-vs-uma-vez",
                "Repetição vs uma vez",
                """
# Repetição vs uma vez

O aspecto distingue ações repetidas de ações únicas:

```
Я часто читал эту книгу.       Eu lia esse livro com frequência. (imperfectivo, repetição)
Я прочитал эту книгу вчера.    Eu li esse livro ontem (uma vez). (perfectivo, único)

Он иногда звонит мне.          Ele às vezes me liga. (imperfectivo, repetição)
Он позвонил мне вчера.         Ele me ligou ontem (uma vez). (perfectivo, pontual)
```

> 🎯 Palavras de repetição (часто, иногда, обычно, всегда) "pedem" o imperfectivo; ações pontuais únicas "pedem" o perfectivo.
""",
                [
                    ex("quiz", 'Com "часто" (frequentemente), usamos:', 
                       "imperfectivo", ["imperfectivo", "perfectivo", "qualquer um"]),
                    ex("text", "Traduza: Eu lia esse livro com frequência. (я + часто + читал + эту + книгу)",
                       "я часто читал эту книгу"),
                    ex("quiz", 'Em "Он позвонил мне вчера", o aspecto é:', 
                       "perfectivo (pontual)", ["perfectivo (pontual)", "imperfectivo (repetição)", "não tem"]),
                    ex("audio", "Escute e transcreva:", "он иногда звонит мне", audio_text="Он иногда звонит мне."),
                    ex("quiz", "Quais palavras costumam \"pedir\" o imperfectivo?",
                       "часто, иногда, обычно, всегда", ["часто, иногда, обычно, всегда", "вчера, один раз", "завтра, скоро"]),
                    ex("speak", "Repita em voz alta:", "я часто читал эту книгу", audio_text="Я часто читал эту книгу."),
                ],
            ),
            topic(
                "prefixos-e-nuance",
                "Nuance com prefixos",
                """
# Nuance com prefixos

Os prefixos (Módulo 15) adicionam nuance de direção e resultado:

| Verbo | Nuance |
|---|---|
| идти | andar (processo) |
| уйти | sair (afastar-se) |
| прийти | chegar |
| войти | entrar |
| выйти | sair de dentro |
| перейти | atravessar |
| зайти | passar de passagem |

```
Он зашёл к нам на минуту.       Ele passou aqui por um minuto. (к + нам = Dativo)
Мы вышли из дома и пошли в парк.  Saímos de casa e fomos ao parque. (из + дома = Genitivo; в + парк = Acusativo)
```

> 🎯 Cada prefixo muda o "cenário" do movimento — e puxa um caso diferente (M15). Nuance = prefixo + caso + aspecto juntos.
""",
                [
                    ex("quiz", 'Qual verbo indica "passar de passagem" (зайти)?',
                       "зайти", ["зайти", "выйти", "перейти"]),
                    ex("text", "Complete no Dativo: \"Он зашёл к ___ на минуту.\" (nós)",
                       "нам"),
                    ex("quiz", 'Em "Мы вышли из дома", o caso de "из дома" é:', 
                       "Genitivo", ["Genitivo", "Acusativo", "Preposicional"]),
                    ex("audio", "Escute e transcreva:", "мы вышли из дома и пошли в парк", audio_text="Мы вышли из дома и пошли в парк."),
                    ex("quiz", 'Em "пошли в парк", o caso é:', 
                       "Acusativo (direção)", ["Acusativo (direção)", "Preposicional (lugar)", "Genitivo"]),
                    ex("speak", "Repita em voz alta:", "он зашёл к нам на минуту", audio_text="Он зашёл к нам на минуту."),
                ],
            ),
            topic(
                "aspecto-na-conversa",
                "Aspecto na conversa natural",
                """
# Aspecto na conversa natural

Na conversa, o aspecto aparece em pedidos, reações e histórias:

```
— Ты уже прочитал книгу?     Você já leu o livro? (perfectivo, resultado)
— Нет, ещё читаю.            Não, ainda estou lendo. (imperfectivo, processo)

— Позвони мне позже!         Ligue-me mais tarde! (perfectivo, pedido pontual)
— Хорошо, позвоню.           Ok, ligarei. (perfectivo, futuro)

Расскажи, что случилось!     Conte o que aconteceu! (perfectivo)
```

> 🎯 Nas perguntas "Ты уже..." e "Ты когда-нибудь...", o perfectivo pergunta pelo RESULTADO; o imperfectivo pergunta pelo processo. A resposta acompanha.
""",
                [
                    ex("text", "Traduza: Não, ainda estou lendo. (Нет + ещё + читаю)",
                       "нет ещё читаю"),
                    ex("quiz", 'Em "Ты уже прочитал книгу?", o aspecto pergunta pelo:', 
                       "resultado", ["resultado", "processo", "futuro"]),
                    ex("quiz", 'Em "Позвони мне позже!", o imperativo é:', 
                       "perfectivo (pedido pontual)", ["perfectivo (pedido pontual)", "imperfectivo (instrução geral)", "não tem"]),
                    ex("audio", "Escute e transcreva:", "позвони мне позже", audio_text="Позвони мне позже!"),
                    ex("quiz", 'Qual resposta indica PROCESSO (ainda lendo)?',
                       "Ещё читаю.", ["Ещё читаю.", "Уже прочитал.", "Прочитаю завтра."]),
                    ex("speak", "Repita em voz alta:", "нет ещё читаю", audio_text="Нет, ещё читаю."),
                ],
            ),
            topic(
                "aspecto-em-relatos",
                "Aspecto em relatos avançados",
                """
# Aspecto em relatos avançados

Nos relatos, o aspecto cria o ritmo da história:

```
Я шёл домой, когда вдруг начался дождь.
Eu ia para casa quando, de repente, começou a chover.
(шёл = imperfectivo, cenário; начался = perfectivo, evento)

Я уже прочитал книгу и решил написать другу.
Eu já tinha lido o livro e decidi escrever ao amigo.
(прочитал = perfectivo, completado; решил = perfectivo, decisão)

Мы проговорили весь вечер о том, что произошло.
Conversamos a noite toda sobre o que aconteceu.
(проговорили = perfectivo com prefixo про-, ação completa com duração)
```

> 🎯 Padrão avançado: **imperfectivo para o cenário** + **perfectivo para os eventos**, e o prefixo **про-** num perfectivo (проговорили) pode até indicar "durante todo o tempo" — nuance fina do C1.
""",
                [
                    ex("quiz", 'Em "Я шёл домой, когда начался дождь", qual verbo é o CENÁRIO (imperfectivo)?',
                       "шёл", ["шёл", "начался", "два cenários"]),
                    ex("text", "Traduza: Eu já tinha lido o livro. (я + уже + прочитал + книгу)",
                       "я уже прочитал книгу"),
                    ex("quiz", 'O prefixo "про-" em "проговорили" pode indicar:', 
                       "ação completa que durou todo o tempo", ["ação completa que durou todo o tempo", "ação futura", "negação"]),
                    ex("audio", "Escute e transcreva:", "мы проговорили весь вечер о том что произошло", audio_text="Мы проговорили весь вечер о том, что произошло."),
                    ex("quiz", 'Em "о том, что произошло", o caso é:', 
                       "Preposicional", ["Preposicional", "Acusativo", "Instrumental"]),
                    ex("speak", "Repita em voz alta:", "я уже прочитал книгу и решил написать другу", audio_text="Я уже прочитал книгу и решил написать другу."),
                ],
            ),
        ],
    )


# ============================================================
# MODULO 21 - Registro e Estilo (C1)
# ============================================================

def build_modulo_21_registro_e_estilo():
    return module(
        "modulo-21-registro-e-estilo",
        "Módulo 21 — Registro e Estilo — C1",
        "Registro formal e informal, escrita vs fala, estilo e naturalidade e polidez avançada.",
        [
            topic(
                "registro-formal-russo",
                "Registro formal",
                """
# Registro formal

No registro formal (documentos, e-mails, discursos), use formas completas e vocabulário neutro:

| Informal | Formal |
|---|---|
| Привет! | Здравствуйте! |
| спасибо | благодарю |
| я хочу | я хотел бы / я прошу |
| да | да, конечно / безусловно |

```
Уважаемый Иван!          Prezado Ivan!
Я хотел бы попросить вас...   Gostaria de pedir-lhe...
С уважением, ...         Atenciosamente, ...
```

> 🎯 O formal usa o **вы** completo (Módulo 2) e evita contrações/coloquialismos. "Благодарю" é o "obrigado" formal.
""",
                [
                    ex("text", "Traduza (formal): Gostaria de pedir-lhe... (я + хотел бы + попросить + вас)",
                       "я хотел бы попросить вас"),
                    ex("quiz", 'Qual é o "obrigado" FORMAL?',
                       "благодарю", ["благодарю", "спасибо", "пожалуйста"]),
                    ex("quiz", 'Qual saudação é FORMAL?',
                       "Здравствуйте!", ["Здравствуйте!", "Привет!", "Пока!"]),
                    ex("audio", "Escute e transcreva:", "уважаемый иван", audio_text="Уважаемый Иван!"),
                    ex("quiz", 'Como se fecha um e-mail formal?',
                       "С уважением, ...", ["С уважением, ...", "Пока!", "До скорого!"]),
                    ex("speak", "Repita em voz alta:", "я хотел бы попросить вас", audio_text="Я хотел бы попросить вас..."),
                ],
            ),
            topic(
                "registro-informal-russo",
                "Registro informal",
                """
# Registro informal

Com amigos, o russo é coloquial e cheio de atalhos:

| Formal | Informal |
|---|---|
| Здравствуйте! | Привет! / Здорово! |
| спасибо | спасибо / спс |
| извините | извини / прости |
| что делаете? | чё делаешь? |

```
Привет! Как дела?         Oi! Como vai?
Ну, так себе.             Ah, mais ou menos.
Пока! До встречи!         Tchau! Até mais!
```

> 🎯 O informal usa **ты** (Módulo 2) e palavras coloquiais ("здорово", "чё"). Saber QUANDO usar é parte do C1.
""",
                [
                    ex("text", "Traduza (informal): Oi! Como vai? (Привет + как + дела)",
                       "привет как дела"),
                    ex("quiz", 'Qual saudação é INFORMAL?',
                       "Привет!", ["Привет!", "Здравствуйте!", "Добрый день!"]),
                    ex("quiz", 'Com amigos, usamos o pronome:', 
                       "ты", ["ты", "вы", "они"]),
                    ex("audio", "Escute e transcreva:", "ну так себе", audio_text="Ну, так себе."),
                    ex("quiz", 'Como se diz "Tchau! Até mais!" (informal)?',
                       "Пока! До встречи!", ["Пока! До встречи!", "До свидания!", "С уважением!"]),
                    ex("speak", "Repita em voz alta:", "привет как дела", audio_text="Привет! Как дела?"),
                ],
            ),
            topic(
                "escrito-vs-falado",
                "Escrita vs fala",
                """
# Escrita vs fala

O russo escrito e o falado diferem bastante:

| Fala | Escrita formal |
|---|---|
| щас | сейчас (agora) |
| чё | что (o quê) |
| типа | как будто (tipo) |
| очень много | множество (multidão de) |

```
Fala:   Щас приду!                  Já chego!
Escrita: Сейчас приду.

Fala:   Он типа умный.              Ele é, tipo, inteligente.
Escrita: Он кажется умным.          Ele parece inteligente. (кажется + Instrumental)
```

> 🎯 Na escrita formal, os casos são completos: "Он кажется умным" (кажется + умным = Instrumental). Na fala, tudo é atalho.
""",
                [
                    ex("text", "Escreva a forma formal de \"щас\":",
                       "сейчас"),
                    ex("quiz", 'Em "Он кажется умным", o caso de "умным" é:', 
                       "Instrumental", ["Instrumental", "Acusativo", "Nominativo"]),
                    ex("quiz", 'Qual é a forma coloquial de "что"?',
                       "чё", ["чё", "что", "чего"]),
                    ex("audio", "Escute e transcreva:", "сейчас приду", audio_text="Сейчас приду."),
                    ex("quiz", 'Na fala coloquial, o registro é:', 
                       "cheio de atalhos", ["cheio de atalhos", "idêntico ao escrito", "mais formal que o escrito"]),
                    ex("speak", "Repita em voz alta:", "он кажется умным", audio_text="Он кажется умным."),
                ],
            ),
            topic(
                "estilo-e-naturalidade",
                "Estilo e naturalidade",
                """
# Estilo e naturalidade

O estilo natural evita tradução palavra a palavra e usa blocos prontos:

```
Я хочу сказать, что...          Quero dizer que...
Если честно, ...                Sejamos honestos, ...
Честно говоря, ...              Falando honestamente, ...
На самом деле, ...              Na verdade, ...
```

```
Честно говоря, я не согласен.      Falando honestamente, eu não concordo.
На самом деле, это не так просто.  Na verdade, não é tão simples.
```

> 🎯 A naturalidade vem dos **chunks** (blocos prontos) — não de montar cada frase do zero. "Честно говоря" e "На самом деле" são o "well/actually" do russo.
""",
                [
                    ex("text", "Traduza: Falando honestamente, eu não concordo. (Честно + говоря + я + не + согласен)",
                       "честно говоря я не согласен"),
                    ex("quiz", 'Como se diz "Na verdade, ..."?',
                       "На самом деле, ...", ["На самом деле, ...", "Если честно, ...", "Привет!"]),
                    ex("quiz", 'Em "Честно говоря", a forma é:', 
                       "um bloco pronto (chunk)", ["um bloco pronto (chunk)", "tradução palavra a palavra", "um erro"]),
                    ex("audio", "Escute e transcreva:", "на самом деле это не так просто", audio_text="На самом деле, это не так просто."),
                    ex("quiz", 'O que "Если честно" significa?',
                       "Sejamos honestos / Para ser honesto", ["Sejamos honestos / Para ser honesto", "Se for mentira", "Não sei"]),
                    ex("speak", "Repita em voz alta:", "честно говоря я не согласен", audio_text="Честно говоря, я не согласен."),
                ],
            ),
            topic(
                "polidez-avancada",
                "Polidez avançada",
                """
# Polidez avançada

Formas mais polidas de pedir e recusar:

```
Не могли бы вы...?           O senhor/a senhora poderia...?
Будьте добры, ...            Faça o favor de...
К сожалению, я не могу.      Infelizmente, não posso.
С удовольствием!             Com prazer!

Не могли бы вы открыть окно?        O senhor poderia abrir a janela?
Будьте добры, передайте соль.       Faça o favor de passar o sal.
К сожалению, я не могу помочь.      Infelizmente, não posso ajudar.
```

> 🎯 A polidez avançada usa o **вы** + formas indiretas ("не могли бы вы"). É o padrão para desconhecidos e situações formais.
""",
                [
                    ex("text", "Traduza: O senhor poderia abrir a janela? (Не могли бы вы + открыть + окно)",
                       "не могли бы вы открыть окно"),
                    ex("quiz", 'Como se diz "Com prazer!"?',
                       "С удовольствием!", ["С удовольствием!", "К сожалению!", "Пока!"]),
                    ex("quiz", 'Qual é uma forma muito educada de pedir?',
                       "Не могли бы вы...?", ["Не могли бы вы...?", "Открой!", "Хочу!"]),
                    ex("audio", "Escute e transcreva:", "будьте добры передайте соль", audio_text="Будьте добры, передайте соль."),
                    ex("quiz", 'Em "Будьте добры", a forma é do imperativo:', 
                       "formal (вы)", ["formal (вы)", "informal (ты)", "não é imperativo"]),
                    ex("speak", "Repita em voz alta:", "не могли бы вы открыть окно", audio_text="Не могли бы вы открыть окно?"),
                ],
            ),
        ],
    )


# ============================================================
# MODULO 22 - Speaking (C1)
# ============================================================

def build_modulo_22_speaking_c1():
    return module(
        "modulo-22-speaking-c1",
        "Módulo 22 — Speaking — C1",
        "Debates, opiniões sutis, hipóteses, persuasão e conversa natural em russo.",
        [
            topic(
                "debates-russo",
                "Debates",
                """
# Debates

Para debater em russo, use conectivos de argumento:

```
Я считаю, что...          Eu considero que...
Во-первых, ...            Primeiramente, ...
С другой стороны, ...     Por outro lado, ...
Согласен, но...           Concordo, mas...
Вы правы, однако...       O senhor tem razão, no entanto...
```

```
Я считаю, что это правильное решение.
Eu considero que esta é a decisão certa.

Во-первых, это дёшево. С другой стороны, это медленно.
Primeiramente, é barato. Por outro lado, é lento.
```

> 🎯 Lacuna de caso: "согласен С + Instrumental" (с тобой), "с другой стороны" (Genitivo). Debater = argumentos + casos.
""",
                [
                    ex("text", "Traduza: Eu considero que esta é a decisão certa. (я + считаю + что + это + правильное + решение)",
                       "я считаю что это правильное решение"),
                    ex("quiz", 'Em "Согласен с тобой", o caso de "с тобой" é:', 
                       "Instrumental", ["Instrumental", "Preposicional", "Acusativo"]),
                    ex("quiz", 'Como se diz "Por outro lado, ..."?',
                       "С другой стороны, ...", ["С другой стороны, ...", "Во-первых, ...", "Потому что, ..."]),
                    ex("audio", "Escute e transcreva:", "во-первых это дёшево с другой стороны это медленно", audio_text="Во-первых, это дёшево. С другой стороны, это медленно."),
                    ex("quiz", 'Como se diz "Primeiramente, ..."?',
                       "Во-первых, ...", ["Во-первых, ...", "С другой стороны, ...", "Наконец, ..."]),
                    ex("speak", "Repita em voz alta:", "я считаю что это правильное решение", audio_text="Я считаю, что это правильное решение."),
                ],
            ),
            topic(
                "opinioes-sutis-russo",
                "Opiniões sutis",
                """
# Opiniões sutis

O C1 expressa opinião com nuance, não com certeza absoluta:

```
Мне кажется, что...        Parece-me que...
Возможно, ты прав.         Talvez você tenha razão.
Не совсем согласен.        Não concordo totalmente.
Отчасти да.                Em parte, sim.
```

```
Мне кажется, что это сложно.        Parece-me que isso é difícil.
Я не совсем согласен с этим.        Não concordo totalmente com isso.
```

> 🎯 A sutilidade usa o **Dativo impessoal** ("мне кажется" = "parece-me") e palavras de incerteza (возможно, отчасти) — o hedging do russo (Módulo 17, 20).
""",
                [
                    ex("text", "Traduza: Parece-me que isso é difícil. (Мне + кажется + что + это + сложно)",
                       "мне кажется что это сложно"),
                    ex("quiz", 'Em "Мне кажется", o caso de "мне" é:', 
                       "Dativo", ["Dativo", "Acusativo", "Genitivo"]),
                    ex("quiz", 'Como se diz "Não concordo totalmente"?',
                       "Не совсем согласен.", ["Не совсем согласен.", "Я не согласен ни в коем случае.", "Согласен на 100%."]),
                    ex("audio", "Escute e transcreva:", "возможно ты прав", audio_text="Возможно, ты прав."),
                    ex("quiz", 'Como se diz "Em parte, sim."?',
                       "Отчасти да.", ["Отчасти да.", "Полностью да.", "Нет, никогда."]),
                    ex("speak", "Repita em voz alta:", "я не совсем согласен с этим", audio_text="Я не совсем согласен с этим."),
                ],
            ),
            topic(
                "hipoteses",
                "Hipóteses",
                """
# Hipóteses

Para hipóteses, use o condicional (Módulo 10):

```
Если бы я был богатым, я бы путешествовал.
Se eu fosse rico, eu viajaria. (был/бы = condicional)

Я бы хотел узнать, что случилось.
Eu gostaria de saber o que aconteceu.

Что бы ты сделал на моём месте?
O que você faria no meu lugar? (на + месте = Preposicional)
```

> 🎯 Lacuna de caso: "на моём месте" (Preposicional, M8) e "о том, что случилось" (Preposicional). Hipóteses = condicional + casos.
""",
                [
                    ex("text", "Traduza: Se eu fosse rico, eu viajaria. (Если бы + я + был + богатым + я + бы + путешествовал)",
                       "если бы я был богатым я бы путешествовал"),
                    ex("quiz", 'Em "на моём месте", o caso é:', 
                       "Preposicional", ["Preposicional", "Acusativo", "Genitivo"]),
                    ex("quiz", 'Como se forma o condicional?',
                       "verbo no passado + бы", ["verbo no passado + бы", "verbo no futuro + бы", "быть + бы + infinitivo"]),
                    ex("audio", "Escute e transcreva:", "что бы ты сделал на моём месте", audio_text="Что бы ты сделал на моём месте?"),
                    ex("quiz", 'Em "Я бы хотел узнать, что случилось", o verbo "случилось" é:', 
                       "perfectivo no passado", ["perfectivo no passado", "imperfectivo no presente", "futuro"]),
                    ex("speak", "Repita em voz alta:", "если бы я был богатым я бы путешествовал", audio_text="Если бы я был богатым, я бы путешествовал."),
                ],
            ),
            topic(
                "persuadindo-russo",
                "Persuadindo",
                """
# Persuadindo

Para persuadir, use verbos de ação e apelo ao interesse:

```
Подумай об этом!           Pense nisso! (об + этом = Preposicional)
Это выгодно для тебя.      Isso é vantajoso para você. (для + тебя = Genitivo)
Ты не пожалеешь!           Você não vai se arrepender! (perfectivo futuro)
Попробуй!                  Experimente! (perfectivo imperativo)
```

```
Попробуй этот ресторан, ты не пожалеешь!
Experimente este restaurante, você não vai se arrepender!
```

> 🎯 Lacuna de caso: "об этом" (Preposicional), "для тебя" (Genitivo). E o perfectivo no imperativo/futuro para o "resultado garantido".
""",
                [
                    ex("text", "Traduza: Pense nisso! (Подумай + об + этом)",
                       "подумай об этом"),
                    ex("quiz", 'Em "об этом", o caso é:', 
                       "Preposicional", ["Preposicional", "Acusativo", "Instrumental"]),
                    ex("quiz", 'Em "Это выгодно для тебя", o caso de "для тебя" é:', 
                       "Genitivo", ["Genitivo", "Dativo", "Acusativo"]),
                    ex("audio", "Escute e transcreva:", "попробуй этот ресторан ты не пожалеешь", audio_text="Попробуй этот ресторан, ты не пожалеешь!"),
                    ex("quiz", 'Em "Ты не пожалеешь!", o aspecto é:', 
                       "perfectivo (resultado garantido)", ["perfectivo (resultado garantido)", "imperfectivo (processo)", "não tem"]),
                    ex("speak", "Repita em voz alta:", "подумай об этом", audio_text="Подумай об этом!"),
                ],
            ),
            topic(
                "conversa-natural-russo",
                "Conversa natural",
                """
# Conversa natural

Reações e marcadores para conversa espontânea:

```
Правда?!                  Sério?!
Вот это да!               Nossa!
Здорово!                  Legal!
Понятно.                  Entendido.
Ну и что?                 E daí?
Кстати, ...               Aliás, ...
```

```
— Я выиграл в лотерею!     — Eu ganhei na loteria!
— Правда?! Вот это да!    — Sério?! Nossa!
```

> 🎯 A conversa natural usa reações curtas e marcadores (М4: "кстати"), além do espiral dos casos nas perguntas e respostas rápidas.
""",
                [
                    ex("text", "Traduza: Sério?! (Правда)", "правда"),
                    ex("quiz", 'Como se diz "Nossa!" (surpresa)?',
                       "Вот это да!", ["Вот это да!", "Понятно.", "Ну и что?"]),
                    ex("quiz", 'Em "Кстати, ...", o sentido é:', 
                       "aliás / a propósito", ["aliás / a propósito", "porque", "finalmente"]),
                    ex("audio", "Escute e transcreva:", "правда вот это да", audio_text="Правда?! Вот это да!"),
                    ex("quiz", 'Como se diz "Entendido."?',
                       "Понятно.", ["Понятно.", "Здорово!", "Пока!"]),
                    ex("speak", "Repita em voz alta:", "здорово", audio_text="Здорово!"),
                ],
            ),
        ],
    )


# ============================================================
# MODULO 23 - Listening e Reading (C1)
# ============================================================

def build_modulo_23_listening_e_reading_c1():
    return module(
        "modulo-23-listening-e-reading-c1",
        "Módulo 23 — Listening e Reading — C1",
        "Entender fala nativa, notícias e artigos, literatura, filmes e séries, e captar o sentido implícito.",
        [
            topic(
                "entendendo-fala-nativa",
                "Entendendo fala nativa",
                """
# Entendendo fala nativa

A fala russa nativa é rápida e cheia de reduções:

| Escrito | Fala nativa |
|---|---|
| что | што / чё |
| сейчас | щас |
| говорить | грить |
| тысяча | тыща |

```
Щас приду!            (сейчас приду) Já chego!
Что ты сказал?        O que você disse?
Не понял, повтори!    Não entendi, repita!
```

> 🎯 Na fala real, "что" soa como "што", "его" como "ево". Treinar ouvindo muito é essencial — e pedir repetição é normal.
""",
                [
                    ex("text", "Escreva a forma coloquial de \"сейчас\":", "щас"),
                    ex("quiz", 'Na fala nativa, "что" costuma soar como:', 
                       "што", ["што", "что", "кто"]),
                    ex("quiz", 'Como se pede "Repita!"?',
                       "Повтори!", ["Повтори!", "Пока!", "Привет!"]),
                    ex("audio", "Escute e transcreva:", "не понял повтори", audio_text="Не понял, повтори!"),
                    ex("quiz", 'Em "не понял", o verbo é:', 
                       "perfectivo no passado", ["perfectivo no passado", "imperfectivo no presente", "futuro"]),
                    ex("speak", "Repita em voz alta:", "щас приду", audio_text="Щас приду!"),
                ],
            ),
            topic(
                "noticias-e-artigos",
                "Notícias e artigos",
                """
# Notícias e artigos

Notícias em russo usam vocabulário formal e casos:

| Vocabulário | Português |
|---|---|
| правительство | governo |
| выборы | eleições |
| экономика | economia |
| заявление | declaração |
| сообщает | informa (que) |

```
Правительство сообщает о новой программе.
O governo informa sobre um novo programa. (о + программе = Preposicional)

Выборы пройдут в мае.
As eleições acontecerão em maio. (в + мае = Preposicional)
```

> 🎯 Lacuna de caso: "о программе" (Preposicional), "в мае" (Preposicional), "для населения" (Genitivo). Notícias = vocabulário formal + casos.
""",
                [
                    ex("text", "Traduza: O governo informa sobre um novo programa. (Правительство + сообщает + о + новой + программе)",
                       "правительство сообщает о новой программе"),
                    ex("quiz", 'Em "о новой программе", o caso é:', 
                       "Preposicional", ["Preposicional", "Acusativo", "Genitivo"]),
                    ex("quiz", 'Como se diz "eleições"?',
                       "выборы", ["выборы", "правительство", "экономика"]),
                    ex("audio", "Escute e transcreva:", "выборы пройдут в мае", audio_text="Выборы пройдут в мае."),
                    ex("quiz", 'Em "в мае", o caso é:', 
                       "Preposicional", ["Preposicional", "Acusativo", "Nominativo"]),
                    ex("speak", "Repita em voz alta:", "правительство сообщает о новой программе", audio_text="Правительство сообщает о новой программе."),
                ],
            ),
            topic(
                "literatura-russo",
                "Literatura",
                """
# Literatura

Ler russo literário exige reconhecer particípios e casos avançados:

```
Он шёл по улице, думая о будущем.
Ele andava pela rua, pensando no futuro. (по + улице = Dativo; о + будущем = Preposicional)

Человек, читающий эту книгу, — мой друг.
O homem que está lendo este livro é meu amigo. (participio ativo)

Прочитав книгу, он заснул.
Tendo lido o livro, ele adormeceu. (gerúndio perfectivo)
```

> 🎯 A literatura reúne o espiral completo: gerúndios (M14), particípios (M14), который (M11) e casos (M8). Ler é a prova final.
""",
                [
                    ex("text", "Traduza: Ele andava pela rua, pensando no futuro. (Он + шёл + по + улице + думая + о + будущем)",
                       "он шёл по улице думая о будущем"),
                    ex("quiz", 'Em "по улице", o caso é:', 
                       "Dativo", ["Dativo", "Acusativo", "Preposicional"]),
                    ex("quiz", 'Em "читающий книгу", a forma é:', 
                       "particípio ativo", ["particípio ativo", "gerúndio", "infinitivo"]),
                    ex("audio", "Escute e transcreva:", "прочитав книгу он заснул", audio_text="Прочитав книгу, он заснул."),
                    ex("quiz", 'Em "думая о будущем", a forma é:', 
                       "gerúndio imperfectivo", ["gerúndio imperfectivo", "particípio", "verbo conjugado"]),
                    ex("speak", "Repita em voz alta:", "он шёл по улице думая о будущем", audio_text="Он шёл по улице, думая о будущем."),
                ],
            ),
            topic(
                "filmes-e-series",
                "Filmes e séries",
                """
# Filmes e séries

Vocabulário para entender filmes e séries em russo:

| Vocabulário | Português |
|---|---|
| фильм | filme |
| сериал | série |
| главный герой | protagonista |
| сюжет | enredo |
| концовка | final |
| смотреть | assistir |

```
Смотришь новый сериал?        Você está assistindo à nova série?
Мне нравится сюжет.           Eu gosto do enredo. (мне = Dativo; сюжет = Nominativo)
Концовка была неожиданной.    O final foi inesperado. (была + неожиданной = Instrumental)
```

> 🎯 Lacuna de caso: "мне нравится сюжет" (Dativo impessoal + Nominativo) e "была неожиданной" (Instrumental com быть no passado). Filmes = casos em contexto real.
""",
                [
                    ex("text", "Traduza: Eu gosto do enredo. (мне + нравится + сюжет)",
                       "мне нравится сюжет"),
                    ex("quiz", 'Em "была неожиданной", o caso de "неожиданной" é:', 
                       "Instrumental", ["Instrumental", "Acusativo", "Genitivo"]),
                    ex("quiz", 'Como se diz "final/desfecho"?',
                       "концовка", ["концовка", "сюжет", "сериал"]),
                    ex("audio", "Escute e transcreva:", "концовка была неожиданной", audio_text="Концовка была неожиданной."),
                    ex("quiz", 'Em "мне нравится сюжет", o caso de "сюжет" é:', 
                       "Nominativo", ["Nominativo", "Acusativo", "Dativo"]),
                    ex("speak", "Repita em voz alta:", "мне нравится сюжет", audio_text="Мне нравится сюжет."),
                ],
            ),
            topic(
                "sentido-implicito-russo",
                "Sentido implícito",
                """
# Sentido implícito

No C1, você entende o que NÃO está dito:

```
— Ты закончил работу?        — Você terminou o trabalho?
— Почти.                     — Quase. (implícito: ainda não)
```

```
Ну, мне пора.               Bom, está na hora de ir. (implícito: quero ir embora)
Давай как-нибудь встретимся.  Vamos marcar de nos encontrar um dia. (implícito: não agora)
```

> 🎯 "Почти" e "мне пора" são respostas curtas cheias de sentido implícito. O contexto e o tom completam o significado — como no discurso indireto (M14).
""",
                [
                    ex("text", "Traduza: Está na hora de ir. (мне + пора)",
                       "мне пора"),
                    ex("quiz", 'Em "— Ты закончил? — Почти.", o implícito é:', 
                       "ainda não terminou", ["ainda não terminou", "terminou tudo", "não começou"]),
                    ex("quiz", 'Em "Давай как-нибудь встретимся", o implícito é:', 
                       "não agora, um dia", ["não agora, um dia", "agora mesmo", "nunca"]),
                    ex("audio", "Escute e transcreva:", "мне пора", audio_text="Мне пора."),
                    ex("quiz", 'Em "Ты закончил работу?", o verbo é:', 
                       "perfectivo no passado", ["perfectivo no passado", "imperfectivo no presente", "futuro"]),
                    ex("speak", "Repita em voz alta:", "давай как-нибудь встретимся", audio_text="Давай как-нибудь встретимся."),
                ],
            ),
        ],
    )


# ============================================================
# MODULO 24 - Escrita (C1)
# ============================================================

def build_modulo_24_escrita_c1():
    return module(
        "modulo-24-escrita-c1",
        "Módulo 24 — Escrita — C1",
        "E-mails formais, textos narrativos com aspecto, relatos com casos precisos, edição e estilo e escrita acadêmica.",
        [
            topic(
                "emails-formais-russo",
                "E-mails formais",
                """
# E-mails formais

O e-mail formal em russo tem estrutura fixa:

```
Уважаемый Иван Петрович!            Prezado Ivan Petrovich!

Я пишу, чтобы подтвердить встречу.  Escrevo para confirmar a reunião.
Буду благодарен за быстрый ответ.   Ficarei grato pela resposta rápida.

С уважением,                        Atenciosamente,
Анна                               Anna
```

| Frase | Sentido |
|---|---|
| Я пишу, чтобы... | Escrevo para... |
| Буду благодарен за... | Ficarei grato por... (за + Acusativo) |
| С уважением | Atenciosamente |

> 🎯 Lacuna de caso: "за быстрый ответ" (за + Acusativo). O formal usa o вы completo (M21).
""",
                [
                    ex("text", "Traduza: Escrevo para confirmar a reunião. (я + пишу + чтобы + подтвердить + встречу)",
                       "я пишу чтобы подтвердить встречу"),
                    ex("quiz", 'Em "за быстрый ответ", o caso é:', 
                       "Acusativo", ["Acusativo", "Preposicional", "Genitivo"]),
                    ex("quiz", 'Como se abre um e-mail formal?',
                       "Уважаемый...!", ["Уважаемый...!", "Привет!", "Пока!"]),
                    ex("audio", "Escute e transcreva:", "буду благодарен за быстрый ответ", audio_text="Буду благодарен за быстрый ответ."),
                    ex("quiz", 'Como se fecha um e-mail formal?',
                       "С уважением, ...", ["С уважением, ...", "До скорого!", "Целую!"]),
                    ex("speak", "Repita em voz alta:", "я пишу чтобы подтвердить встречу", audio_text="Я пишу, чтобы подтвердить встречу."),
                ],
            ),
            topic(
                "textos-narrativos",
                "Textos narrativos com aspecto",
                """
# Textos narrativos com aspecto

Na escrita narrativa, o aspecto cria o ritmo:

```
Вчера я встал рано, выпил кофе и пошёл на работу.
Ontem acordei cedo, tomei café e fui ao trabalho.
(perfectivos: vстал, выпил, пошёл — ações completas em sequência)

Когда я шёл на работу, я думал о планах.
Quando eu ia ao trabalho, pensava nos planos.
(imperfectivos: шёл, думал — cenário/processo)
```

> 🎯 Regra de escrita: **perfectivo para a sequência de eventos** (ações concluídas) e **imperfectivo para o cenário** (o que estava acontecendo ao fundo).
""",
                [
                    ex("text", "Traduza: Ontem acordei cedo e fui ao trabalho. (Вчера + я + встал + рано + и + пошёл + на + работу)",
                       "вчера я встал рано и пошёл на работу"),
                    ex("quiz", 'Em "я встал, выпил, пошёл", os verbos são:', 
                       "perfectivos (sequência)", ["perfectivos (sequência)", "imperfectivos (cenário)", "futuros"]),
                    ex("quiz", 'Em "когда я шёл на работу", o verbo é:', 
                       "imperfectivo (cenário)", ["imperfectivo (cenário)", "perfectivo (evento)", "infinitivo"]),
                    ex("audio", "Escute e transcreva:", "вчера я встал рано выпил кофе и пошёл на работу", audio_text="Вчера я встал рано, выпил кофе и пошёл на работу."),
                    ex("quiz", 'Em "на работу", o caso é:', 
                       "Acusativo (direção)", ["Acusativo (direção)", "Preposicional (lugar)", "Genitivo"]),
                    ex("speak", "Repita em voz alta:", "вчера я встал рано и пошёл на работу", audio_text="Вчера я встал рано и пошёл на работу."),
                ],
            ),
            topic(
                "relatos-com-casos",
                "Relatos com casos precisos",
                """
# Relatos com casos precisos

Ao escrever um relato, cada caso precisa estar certo:

```
Я рассказал другу о поездке в Россию.
Eu contei ao amigo sobre a viagem à Rússia.
(другу = Dativo; о поездке = Preposicional; в Россию = Acusativo)

Мы говорили о проблемах на работе.
Nós falamos sobre os problemas no trabalho.
(о проблемах = Preposicional plural; на работе = Preposicional)

Он объяснил мне причину своего решения.
Ele me explicou o motivo da sua decisão.
(мне = Dativo; причину = Acusativo; решения = Genitivo)
```

> 🎯 Três casos num relato: **Dativo** (para quem), **Preposicional** (sobre o quê), **Acusativo** (objeto). Escrever relatos é o teste final dos casos.
""",
                [
                    ex("text", "Traduza: Eu contei ao amigo sobre a viagem à Rússia. (я + рассказал + другу + о + поездке + в + Россию)",
                       "я рассказал другу о поездке в россию"),
                    ex("quiz", 'Em "рассказал другу", o caso de "другу" é:', 
                       "Dativo", ["Dativo", "Acusativo", "Genitivo"]),
                    ex("quiz", 'Em "о поездке", o caso é:', 
                       "Preposicional", ["Preposicional", "Acusativo", "Instrumental"]),
                    ex("audio", "Escute e transcreva:", "он объяснил мне причину своего решения", audio_text="Он объяснил мне причину своего решения."),
                    ex("quiz", 'Em "своего решения", o caso é:', 
                       "Genitivo", ["Genitivo", "Dativo", "Preposicional"]),
                    ex("speak", "Repita em voz alta:", "я рассказал другу о поездке в россию", audio_text="Я рассказал другу о поездке в Россию."),
                ],
            ),
            topic(
                "edicao-e-estilo",
                "Edição e estilo",
                """
# Edição e estilo

Ao editar, verifique três coisas:

```
1. Os casos:      я писал другу (Dativo), а não "друга"
2. O aspecto:     написал (concluído) vs писал (processo)
3. A ordem:       sujeito - verbo - objeto

Antes:
Он написал письмо другу вчера вечером, и он был счастлив.

Depois:
Вчера вечером он написал письмо другу и был счастлив.
```

> 🎯 Na edição, revise os casos e o aspecto — os dois "erros" mais comuns de quem aprende russo. Ordem natural: tempo - sujeito - verbo - objeto.
""",
                [
                    ex("text", "Complete no Dativo: \"Я писал ___ письмо.\" (amigo)",
                       "другу"),
                    ex("quiz", 'Qual é o erro comum na frase "Я писал друга"?',
                       "o caso (deveria ser другу, Dativo)", ["o caso (deveria ser другу, Dativo)", "o verbo", "a ordem"]),
                    ex("quiz", 'Em "Он написал письмо", o verbo é:', 
                       "perfectivo (concluído)", ["perfectivo (concluído)", "imperfectivo (processo)", "futuro"]),
                    ex("audio", "Escute e transcreva:", "вчера вечером он написал письмо другу и был счастлив", audio_text="Вчера вечером он написал письмо другу и был счастлив."),
                    ex("quiz", 'Na ordem natural da frase russa, o tempo (вчера) vem:', 
                       "no início", ["no início", "no fim", "nunca aparece"]),
                    ex("speak", "Repita em voz alta:", "он написал письмо другу", audio_text="Он написал письмо другу."),
                ],
            ),
            topic(
                "escrita-academica-russo",
                "Escrita acadêmica",
                """
# Escrita acadêmica

A escrita acadêmica russa é impessoal e usa construções específicas:

```
В данной статье рассматривается...   Neste artigo é examinado... (passiva de resultado)
Следует отметить, что...             Deve-se notar que...
Таким образом, ...                   Assim, ...
По мнению автора, ...                Na opinião do autor, ... (по + мнению = Dativo)
```

```
В данной статье рассматривается проблема образования.
Neste artigo é examinado o problema da educação. (проблема = Nominativo; образования = Genitivo)

Таким образом, можно сделать вывод.
Assim, pode-se tirar a conclusão.
```

> 🎯 Lacuna de caso: "по мнению автора" (по + Dativo), "образования" (Genitivo). A academia russa usa a passiva de resultado (M14) e o Genitivo em cadeia.
""",
                [
                    ex("text", "Traduza: Neste artigo é examinado o problema da educação. (В + данной + статье + рассматривается + проблема + образования)",
                       "в данной статье рассматривается проблема образования"),
                    ex("quiz", 'Em "по мнению автора", o caso é:', 
                       "Dativo", ["Dativo", "Acusativo", "Genitivo"]),
                    ex("quiz", 'Em "проблема образования", o caso de "образования" é:', 
                       "Genitivo", ["Genitivo", "Nominativo", "Preposicional"]),
                    ex("audio", "Escute e transcreva:", "в данной статье рассматривается проблема образования", audio_text="В данной статье рассматривается проблема образования."),
                    ex("quiz", 'Como se diz "Deve-se notar que..."?',
                       "Следует отметить, что...", ["Следует отметить, что...", "Привет!", "Пока!"]),
                    ex("speak", "Repita em voz alta:", "по мнению автора", audio_text="По мнению автора, ..."),
                ],
            ),
        ],
    )


# ============================================================
# MODULO 25 - Russo para o Trabalho (aplicado, pos-C1)
# ============================================================

def build_modulo_25_russo_para_o_trabalho():
    return module(
        "modulo-25-russo-para-o-trabalho",
        "Módulo 25 — Russo para o Trabalho",
        "Entrevistas, reuniões, e-mails profissionais, feedback e negociação em russo.",
        [
            topic(
                "entrevistas-de-emprego-russo",
                "Entrevistas de emprego",
                """
# Entrevistas de emprego

Frases para entrevista em russo:

```
Расскажите о себе.            Conte sobre você. (о + себе = Preposicional)
Мой опыт работы — пять лет.   Minha experiência de trabalho é de cinco anos.
Я умею работать в команде.    Eu sei trabalhar em equipe. (в + команде = Preposicional)
Меня интересует эта должность.  Estou interessado nesta posição. (меня = Acusativo)

Мой главный навык — программирование.
Minha principal habilidade é a programação.
```

> 🎯 Lacuna de caso: "о себе" (Preposicional), "в команде" (Preposicional), "меня интересует" (Acusativo impessoal). A entrevista é um teste de casos!
""",
                [
                    ex("text", "Traduza: Conte sobre você. (Расскажите + о + себе)",
                       "расскажите о себе"),
                    ex("quiz", 'Em "о себе", o caso é:', 
                       "Preposicional", ["Preposicional", "Acusativo", "Dativo"]),
                    ex("quiz", 'Em "Я умею работать в команде", o caso é:', 
                       "Preposicional", ["Preposicional", "Genitivo", "Acusativo"]),
                    ex("audio", "Escute e transcreva:", "расскажите о себе", audio_text="Расскажите о себе."),
                    ex("quiz", 'Em "Меня интересует эта должность", o caso de "меня" é:', 
                       "Acusativo", ["Acusativo", "Dativo", "Nominativo"]),
                    ex("speak", "Repita em voz alta:", "мой главный навык программирование", audio_text="Мой главный навык программирование."),
                ],
            ),
            topic(
                "reunioes-russo",
                "Reuniões",
                """
# Reuniões

Frases para conduzir reuniões:

```
Давайте начнём.             Vamos começar.
Что у нас на повестке дня?  O que temos na pauta? (на + повестке = Preposicional)
Перейдём к следующему пункту.  Vamos ao próximo ponto. (к + пункту = Dativo)
Я хочу обсудить вопрос.     Quero discutir a questão. (вопрос = Acusativo)
Подведём итоги.             Vamos resumir.

Давайте начнём с отчёта.    Vamos começar pelo relatório. (с + отчёта = Genitivo)
Перейдём к вопросу о бюджете.  Vamos à questão do orçamento. (к + вопросу = Dativo; о + бюджете = Preposicional)
```

> 🎯 Lacuna de caso: "на повестке" (Preposicional), "к пункту" (Dativo), "с отчёта" (Genitivo). Reuniões = preposições + casos.
""",
                [
                    ex("text", "Traduza: Vamos começar. (Давайте + начнём)",
                       "давайте начнём"),
                    ex("quiz", 'Em "к вопросу о бюджете", o caso de "к вопросу" é:', 
                       "Dativo", ["Dativo", "Preposicional", "Acusativo"]),
                    ex("quiz", 'Em "Давайте начнём с отчёта", o caso de "с отчёта" é:', 
                       "Genitivo", ["Genitivo", "Acusativo", "Dativo"]),
                    ex("audio", "Escute e transcreva:", "перейдём к следующему пункту", audio_text="Перейдём к следующему пункту."),
                    ex("quiz", 'Como se diz "Vamos resumir"?',
                       "Подведём итоги.", ["Подведём итоги.", "Давайте начнём.", "Пока!"]),
                    ex("speak", "Repita em voz alta:", "давайте начнём", audio_text="Давайте начнём."),
                ],
            ),
            topic(
                "emails-profissionais-russo",
                "E-mails profissionais",
                """
# E-mails profissionais

E-mails de trabalho em russo:

```
Добрый день!              Bom dia!
Во вложении вы найдёте...  Em anexo você encontrará... (во + вложении = Preposicional)
Пожалуйста, подтвердите получение.  Por favor, confirme o recebimento.
Буду рад обсудить детали.  Ficarei feliz em discutir os detalhes.

Спасибо за ваше внимание.  Obrigado pela sua atenção. (за + внимание = Acusativo)
Жду вашего ответа.         Aguardo sua resposta. (вашего ответа = Genitivo)
```

> 🎯 Lacuna de caso: "во вложении" (Preposicional), "за внимание" (Acusativo), "вашего ответа" (Genitivo). E-mails = cortesia + casos.
""",
                [
                    ex("text", "Traduza: Em anexo você encontrará... (Во + вложении + вы + найдёте)",
                       "во вложении вы найдёте"),
                    ex("quiz", 'Em "во вложении", o caso é:', 
                       "Preposicional", ["Preposicional", "Acusativo", "Genitivo"]),
                    ex("quiz", 'Em "Жду вашего ответа", o caso é:', 
                       "Genitivo", ["Genitivo", "Dativo", "Acusativo"]),
                    ex("audio", "Escute e transcreva:", "жду вашего ответа", audio_text="Жду вашего ответа."),
                    ex("quiz", 'Como se diz "Por favor, confirme o recebimento."?',
                       "Пожалуйста, подтвердите получение.", ["Пожалуйста, подтвердите получение.", "Привет!", "Пока!"]),
                    ex("speak", "Repita em voz alta:", "во вложении вы найдёте", audio_text="Во вложении вы найдёте..."),
                ],
            ),
            topic(
                "feedback-russo",
                "Feedback",
                """
# Feedback

Dar e receber feedback em russo:

```
Спасибо за вашу работу.       Obrigado pelo seu trabalho. (за + работу = Acusativo)
У вас хорошо получается.      Você vai bem nisso. (у + вас = Genitivo)
Стоит обратить внимание на...  Vale a pena prestar atenção em...
Я ценю вашу помощь.           Eu valorizo sua ajuda. (помощь = Acusativo)

Хорошая работа!               Bom trabalho!
Можно улучшить отчёт.         O relatório pode ser melhorado. (отчёт = Acusativo)
Спасибо за обратную связь!    Obrigado pelo feedback!
```

> 🎯 Lacuna de caso: "за работу" (Acusativo), "у вас" (Genitivo), "за обратную связь" (Acusativo). Feedback = verbos de valor + casos.
""",
                [
                    ex("text", "Traduza: Obrigado pelo seu trabalho. (Спасибо + за + вашу + работу)",
                       "спасибо за вашу работу"),
                    ex("quiz", 'Em "у вас хорошо получается", o caso de "у вас" é:', 
                       "Genitivo", ["Genitivo", "Dativo", "Acusativo"]),
                    ex("quiz", 'Em "за обратную связь", o caso é:', 
                       "Acusativo", ["Acusativo", "Preposicional", "Genitivo"]),
                    ex("audio", "Escute e transcreva:", "спасибо за обратную связь", audio_text="Спасибо за обратную связь!"),
                    ex("quiz", 'Como se diz "Bom trabalho!"?',
                       "Хорошая работа!", ["Хорошая работа!", "До свидания!", "Плохо!"]),
                    ex("speak", "Repita em voz alta:", "спасибо за вашу работу", audio_text="Спасибо за вашу работу."),
                ],
            ),
            topic(
                "negociando-no-trabalho-russo",
                "Negociando no trabalho",
                """
# Negociando no trabalho

Negociação em russo:

```
Давайте найдём компромисс.        Vamos encontrar um meio-termo.
Я могу пойти навстречу.            Posso ceder. (навстречу = Advérbio)
На каких условиях?                 Em que condições? (на + условиях = Preposicional)
Это для нас важно.                 Isso é importante para nós. (для + нас = Genitivo)

Я хотел бы обсудить зарплату.      Gostaria de discutir o salário.
Можно договориться о сроках.       Dá para negociar os prazos. (о + сроках = Preposicional)
```

> 🎯 Lacuna de caso: "для нас" (Genitivo), "о сроках" (Preposicional), "на условиях" (Preposicional). Negociação = polidez + casos.
""",
                [
                    ex("text", "Traduza: Vamos encontrar um meio-termo. (Давайте + найдём + компромисс)",
                       "давайте найдём компромисс"),
                    ex("quiz", 'Em "Это важно для нас", o caso de "для нас" é:', 
                       "Genitivo", ["Genitivo", "Acusativo", "Dativo"]),
                    ex("quiz", 'Em "договориться о сроках", o caso é:', 
                       "Preposicional", ["Preposicional", "Acusativo", "Genitivo"]),
                    ex("audio", "Escute e transcreva:", "давайте найдём компромисс", audio_text="Давайте найдём компромисс."),
                    ex("quiz", 'Como se diz "Em que condições?"?',
                       "На каких условиях?", ["На каких условиях?", "Сколько стоит?", "Пока!"]),
                    ex("speak", "Repita em voz alta:", "я хотел бы обсудить зарплату", audio_text="Я хотел бы обсудить зарплату."),
                ],
            ),
        ],
    )


# ============================================================
# MODULO 26 - Russo para Tecnologia (aplicado, pos-C1)
# ============================================================

def build_modulo_26_russo_para_tecnologia():
    return module(
        "modulo-26-russo-para-tecnologia",
        "Módulo 26 — Russo para Tecnologia",
        "Vocabulário de programação, Git/GitHub, documentação técnica, debugging e conversas técnicas em russo.",
        [
            topic(
                "vocabulario-de-programacao-russo",
                "Vocabulário de programação",
                """
# Vocabulário de programação

| Russo | Português |
|---|---|
| код | código |
| программа | programa |
| функция | função |
| переменная | variável |
| ошибка | erro |
| запускать | executar |
| библиотека | biblioteca |

```
В коде есть ошибка.          No código há um erro. (в + коде = Preposicional)
Эта функция возвращает результат.  Esta função retorna um resultado. (результат = Acusativo)
Я запускаю программу.        Eu executo o programa. (программу = Acusativo)
```

> 🎯 Lacuna de caso: "в коде" (Preposicional), "функцию/программу" (Acusativo). Vocabulário técnico sempre flexiona.
""",
                [
                    ex("text", "Traduza: No código há um erro. (В + коде + есть + ошибка)",
                       "в коде есть ошибка"),
                    ex("quiz", 'Em "в коде", o caso é:', 
                       "Preposicional", ["Preposicional", "Acusativo", "Genitivo"]),
                    ex("quiz", 'Em "Я запускаю программу", o caso de "программу" é:', 
                       "Acusativo", ["Acusativo", "Nominativo", "Dativo"]),
                    ex("audio", "Escute e transcreva:", "эта функция возвращает результат", audio_text="Эта функция возвращает результат."),
                    ex("quiz", 'Como se diz "erro"?',
                       "ошибка", ["ошибка", "код", "переменная"]),
                    ex("speak", "Repita em voz alta:", "я запускаю программу", audio_text="Я запускаю программу."),
                ],
            ),
            topic(
                "git-e-github-russo",
                "Git e GitHub",
                """
# Git e GitHub

| Russo | Português |
|---|---|
| репозиторий | repositório |
| ветка | branch |
| коммит | commit |
| отправить (push) | enviar |
| скачать (pull) | baixar |
| слияние | merge |

```
Создай новую ветку.           Crie um novo branch. (новую ветку = Acusativo)
Я отправил изменения.         Eu enviei as mudanças. (изменения = Acusativo)
Отправь запрос на изменения.  Envie um pull request. (запрос = Acusativo; на изменения = Acusativo)
```

> 🎯 Lacuna de caso: "создай ветку" (Acusativo), "запрос на изменения" (Acusativo). Os comandos do Git em russo usam o imperativo (M16).
""",
                [
                    ex("text", "Traduza: Crie um novo branch. (Создай + новую + ветку)",
                       "создай новую ветку"),
                    ex("quiz", 'Em "создай новую ветку", o caso é:', 
                       "Acusativo", ["Acusativo", "Preposicional", "Genitivo"]),
                    ex("quiz", 'Em "Я отправил изменения", o verbo é:', 
                       "perfectivo no passado", ["perfectivo no passado", "imperfectivo no presente", "futuro"]),
                    ex("audio", "Escute e transcreva:", "я отправил изменения", audio_text="Я отправил изменения."),
                    ex("quiz", 'Como se diz "repositório"?',
                       "репозиторий", ["репозиторий", "ветка", "ошибка"]),
                    ex("speak", "Repita em voz alta:", "создай новую ветку", audio_text="Создай новую ветку."),
                ],
            ),
            topic(
                "documentacao-tecnica-russo",
                "Documentação técnica",
                """
# Documentação técnica

| Russo | Português |
|---|---|
| установка | instalação |
| использование | uso |
| запустить | executar |
| настроить | configurar |
| инструкция | instrução |

```
Инструкция по установке.         Instrução de instalação. (по + установке = Dativo)
Запустите приложение.            Execute o aplicativo. (приложение = Acusativo)
Следуйте инструкциям.            Siga as instruções. (инструкциям = Dativo plural)
```

> 🎯 Lacuna de caso: "по установке" (по + Dativo), "следуйте инструкциям" (Dativo plural, M8). A documentação usa o imperativo formal (M16) + Dativo.
""",
                [
                    ex("text", "Traduza: Execute o aplicativo. (Запустите + приложение)",
                       "запустите приложение"),
                    ex("quiz", 'Em "инструкция по установке", o caso é:', 
                       "Dativo", ["Dativo", "Acusativo", "Genitivo"]),
                    ex("quiz", 'Em "Следуйте инструкциям", o caso é:', 
                       "Dativo plural", ["Dativo plural", "Acusativo", "Preposicional"]),
                    ex("audio", "Escute e transcreva:", "следуйте инструкциям", audio_text="Следуйте инструкциям."),
                    ex("quiz", 'Como se diz "configurar"?',
                       "настроить", ["настроить", "запустить", "установка"]),
                    ex("speak", "Repita em voz alta:", "запустите приложение", audio_text="Запустите приложение."),
                ],
            ),
            topic(
                "debugging-russo",
                "Debugging",
                """
# Debugging

| Russo | Português |
|---|---|
| отладить | depurar |
| воспроизвести | reproduzir |
| исправить | corrigir |
| сбой | falha |
| причина | causa |

```
Можешь воспроизвести ошибку?        Você consegue reproduzir o erro? (ошибку = Acusativo)
Я нашёл причину сбоя.               Eu encontrei a causa da falha. (причину = Acusativo; сбоя = Genitivo)
Давай исправим этот баг.            Vamos corrigir esse bug. (баг = Acusativo)
```

> 🎯 Lacuna de caso: "причину сбоя" (Acusativo + Genitivo), "этот баг" (Acusativo). Debugging = causa + objeto em casos.
""",
                [
                    ex("text", "Traduza: Você consegue reproduzir o erro? (Можешь + воспроизвести + ошибку)",
                       "можешь воспроизвести ошибку"),
                    ex("quiz", 'Em "причину сбоя", o caso de "сбоя" é:', 
                       "Genitivo", ["Genitivo", "Acusativo", "Dativo"]),
                    ex("quiz", 'Em "Я нашёл причину", o caso de "причину" é:', 
                       "Acusativo", ["Acusativo", "Preposicional", "Genitivo"]),
                    ex("audio", "Escute e transcreva:", "я нашёл причину сбоя", audio_text="Я нашёл причину сбоя."),
                    ex("quiz", 'Como se diz "reproduzir"?',
                       "воспроизвести", ["воспроизвести", "исправить", "запустить"]),
                    ex("speak", "Repita em voz alta:", "можешь воспроизвести ошибку", audio_text="Можешь воспроизвести ошибку?"),
                ],
            ),
            topic(
                "conversas-tecnicas",
                "Conversas técnicas",
                """
# Conversas técnicas

Para discutir tecnologia em russo:

```
Как ты это реализовал?          Como você implementou isso? (это = Acusativo)
Почему падает сервер?           Por que o servidor está caindo? (сервер = Nominativo)
Какая архитектура у проекта?    Qual é a arquitetura do projeto? (у + проекта = Genitivo)
Нам нужно увеличить скорость.   Precisamos aumentar a velocidade. (скорость = Acusativo)

Мы используем микросервисы.     Nós usamos microsserviços. (микросервисы = Acusativo)
Это решение масштабируется.     Esta solução escala.
```

> 🎯 Lacuna de caso: "у проекта" (Genitivo), "увеличить скорость" (Acusativo), "микросервисы" (Acusativo). A conversa técnica é o espiral completo em contexto real.
""",
                [
                    ex("text", "Traduza: Precisamos aumentar a velocidade. (Нам + нужно + увеличить + скорость)",
                       "нам нужно увеличить скорость"),
                    ex("quiz", 'Em "архитектура у проекта", o caso de "у проекта" é:', 
                       "Genitivo", ["Genitivo", "Acusativo", "Dativo"]),
                    ex("quiz", 'Em "увеличить скорость", o caso de "скорость" é:', 
                       "Acusativo", ["Acusativo", "Preposicional", "Genitivo"]),
                    ex("audio", "Escute e transcreva:", "мы используем микросервисы", audio_text="Мы используем микросервисы."),
                    ex("quiz", 'Em "Почему падает сервер?", o caso de "сервер" é:', 
                       "Nominativo", ["Nominativo", "Acusativo", "Genitivo"]),
                    ex("speak", "Repita em voz alta:", "нам нужно увеличить скорость", audio_text="Нам нужно увеличить скорость."),
                ],
            ),
        ],
    )


# ============================================================
# MODULO 27 - Treino de Fluencia (aplicado, pos-C1)
# ============================================================

def build_modulo_27_treino_de_fluencia():
    return module(
        "modulo-27-treino-de-fluencia",
        "Módulo 27 — Treino de Fluência",
        "Pensar em russo, evitar a tradução mental, parafrasear, circumlocução e recall de vocabulário.",
        [
            topic(
                "pensando-em-russo",
                "Pensando em russo",
                """
# Pensando em russo

A fluência real começa quando você **pensa direto em russo** — sem traduzir mentalmente.

## Como praticar

- **Rotule** objetos ao redor em russo (стол, окно, книга).
- **Narre** o que faz: "Я открываю дверь", "Мне нужны ключи".
- Forme pensamentos simples direto no idioma.

> 💡 Pensar em russo deixa a fala mais **rápida e natural** — porque você pula a etapa da tradução.
""",
                [
                    ex("quiz", "Pensar em russo significa:",
                       "formar os pensamentos direto em russo", ["formar os pensamentos direto em russo", "traduzir mentalmente", "não pensar"]),
                    ex("quiz", "Um exercício simples para começar:",
                       "rotular objetos ao redor em russo", ["rotular objetos ao redor em russo", "traduzir tudo", "dormir"]),
                    ex("text", "Complete: \"Я ___ дверь.\" (abro)",
                       "открываю"),
                    ex("audio", "Escute e transcreva:", "мне нужны ключи", audio_text="Мне нужны ключи."),
                    ex("quiz", "Pensar em russo deixa a fala:",
                       "mais rápida e natural", ["mais rápida e natural", "mais lenta", "impossível"]),
                    ex("speak", "Repita em voz alta:", "я открываю дверь", audio_text="Я открываю дверь."),
                ],
            ),
            topic(
                "evitando-traducao-mental-russo",
                "Evitando a tradução mental",
                """
# Evitando a tradução mental

A tradução palavra a palavra **atrasa** e gera erros. Aprenda em **blocos**.

## O que fazer

- Aprenda **chunks** (blocos prontos): "мне нравится", "у меня есть".
- Associe a palavra à **imagem/ideia**, não ao português.
- Não abra o dicionário a cada palavra — use o contexto.

> 💘 Blocos prontos como "мне нравится" são aprendidos **como um todo** — não traduzidos palavra por palavra.
""",
                [
                    ex("quiz", "A tradução mental palavra a palavra:",
                       "atrasa e gera erros", ["atrasa e gera erros", "ajuda sempre", "não existe"]),
                    ex("quiz", "Em vez de traduzir, aprenda:",
                       "blocos prontos (chunks)", ["blocos prontos (chunks)", "gramática isolada", "só palavras soltas"]),
                    ex("text", "Complete o chunk: \"___ нравится музыка.\" (para mim)",
                       "мне"),
                    ex("audio", "Escute e transcreva:", "у меня есть книга", audio_text="У меня есть книга."),
                    ex("quiz", "Blocos prontos como \"у меня есть\" são:",
                       "aprendidos como um todo", ["aprendidos como um todo", "traduzidos", "proibidos"]),
                    ex("speak", "Repita em voz alta:", "мне нравится музыка", audio_text="Мне нравится музыка."),
                ],
            ),
            topic(
                "parafrase-russo",
                "Paráfrase",
                """
# Paráfrase

**Parafrasear** é dizer a mesma ideia com outras palavras — essencial quando você trava numa palavra.

## Exemplos

```
Я устал.   ->   Я очень устал / Я без сил.
Она красивая.   ->   Она очень красивая / Она прекрасная.
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
                    ex("text", "Complete com sinônimo: \"Я устал\" -> \"Я ___ сил.\" (sem)",
                       "без"),
                    ex("audio", "Escute e transcreva:", "я без сил", audio_text="Я без сил."),
                    ex("quiz", "Paráfrase é essencial para:",
                       "fluência e circumlocução", ["fluência e circumlocução", "decorar", "nada"]),
                    ex("speak", "Repita em voz alta:", "я очень устал", audio_text="Я очень устал."),
                ],
            ),
            topic(
                "circunlocucao-russo",
                "Circumlocução",
                """
# Circumlocução

**Circumlocução** é descrever uma palavra que você não lembra — mantém a conversa fluindo.

## Como descrever sem a palavra

```
"Вещь, которой пишут."        "A coisa com que se escreve." (caneta)
"Место, где покупают еду."    "O lugar onde se compra comida." (loja)
```

## Por que importa

Em vez de travar ("Я не знаю это слово"), você **descreve** — e o nativo te ajuda ou você se faz entender.

> 💘 Circumlocução = falar ao redor da palavra. Treine descrevendo objetos do dia a dia sem dizer o nome.
""",
                [
                    ex("quiz", "Circumlocução é:",
                       "descrever a palavra que você não lembra", ["descrever a palavra que você não lembra", "desistir", "traduzir"]),
                    ex("quiz", "Para descrever 'caneta' sem a palavra:",
                       "Вещь, которой пишут.", ["Вещь, которой пишут.", "Я не знаю.", "Пока!"]),
                    ex("text", "Complete: \"Вещь, ___ пишут.\" (com que)",
                       "которой"),
                    ex("audio", "Escute e transcreva:", "вещь которой пишут", audio_text="Вещь, которой пишут."),
                    ex("quiz", "Circumlocução mantém a conversa:",
                       "fluindo sem travar", ["fluindo sem travar", "parada", "em português"]),
                    ex("speak", "Repita em voz alta:", "место где покупают еду", audio_text="Место, где покупают еду."),
                ],
            ),
            topic(
                "recall-de-vocabulario-russo",
                "Recall de vocabulário",
                """
# Recall de vocabulário

**Recall ativo** é lembrar a palavra **sem ajuda** — muito mais forte que só reconhecer.

## Como treinar

- **Teste-se**: veja a tradução e diga a palavra em russo.
- Use **repetição espaçada** (revisar em intervalos).
- Antes de conferir, tente **recordar**.

> 💘 Reler a lista não é recall — **testar-se** é. Quem se testa lembra muito mais.
""",
                [
                    ex("quiz", "Recall ativo é:",
                       "lembrar a palavra sem ajuda", ["lembrar a palavra sem ajuda", "reconhecer só", "decorar"]),
                    ex("quiz", "A repetição espaçada melhora:",
                       "a memória de longo prazo", ["a memória de longo prazo", "só o curto prazo", "nada"]),
                    ex("text", "Teste-se: como se diz 'livro' em russo?",
                       "книга"),
                    ex("audio", "Escute e transcreva:", "вспомни слово перед проверкой", audio_text="Вспомни слово перед проверкой."),
                    ex("quiz", "Para fortalecer o recall:",
                       "testar-se ativamente", ["testar-se ativamente", "só reler", "dormir"]),
                    ex("speak", "Repita em voz alta:", "книга", audio_text="книга"),
                ],
            ),
        ],
    )


# ============================================================
# MODULO 28 - Dominio C1 (aplicado, pos-C1)
# ============================================================

def build_modulo_28_dominio_c1():
    return module(
        "modulo-28-dominio-c1",
        "Módulo 28 — Domínio C1",
        "Nuance, humor e sarcasmo, linguagem idiomática, registros e comunicação precisa em russo.",
        [
            topic(
                "entendendo-nuance-russo",
                "Entendendo nuance",
                """
# Entendendo nuance

**Nuance** é a sutileza de significado — a diferença entre "нравится" e "обожать", ou entre "хорошо" e "отлично".

## Exemplos de nuance

```
Мне нравится.       Eu gosto. (neutro)
Я люблю это.        Eu amo isso. (forte)
Я обожаю это.       Eu adoro isso. (muito forte)
```

```
Всё хорошо.         Está tudo bem. (neutro)
Всё отлично!        Está tudo ótimo! (entusiasmado)
```

> 💘 Captar nuance exige atenção ao **tom e ao contexto** — não só ao dicionário.
""",
                [
                    ex("quiz", "Nuance é:",
                       "a sutileza de significado", ["a sutileza de significado", "o erro", "o tamanho"]),
                    ex("quiz", "Qual é mais FORTE que \"мне нравится\"?",
                       "Я обожаю это.", ["Я обожаю это.", "Всё хорошо.", "Мне всё равно."]),
                    ex("text", "Complete com a forma forte: \"Я ___ это.\" (adoro — обожать)",
                       "обожаю"),
                    ex("audio", "Escute e transcreva:", "я обожаю это", audio_text="Я обожаю это."),
                    ex("quiz", "Captar nuance exige:",
                       "atenção ao tom e ao contexto", ["atenção ao tom e ao contexto", "só o dicionário", "pressa"]),
                    ex("speak", "Repita em voz alta:", "всё отлично", audio_text="Всё отлично!"),
                ],
            ),
            topic(
                "humor-e-sarcasmo-russo",
                "Humor e sarcasmo",
                """
# Humor e sarcasmo

O **sarcasmo** diz o **oposto** do significado literal, usando o tom:

```
"Ну, отлично!" (com tom irônico)   = frustração, não entusiasmo
"Очень интересно!" (seco)          = na verdade, nada interessante
```

## Como detectar

- Preste atenção ao **tom** e ao **contexto**.
- Se a frase parece boa demais para a situação, é provável sarcasmo.

> 💘 Sarcasmo e ironia são comuns em conversas e séries — entender é parte do domínio C1.
""",
                [
                    ex("quiz", "O sarcasmo costuma dizer:",
                       "o oposto do que significa", ["o oposto do que significa", "exatamente o que diz", "nada"]),
                    ex("quiz", "'Ну, отлично!' com tom irônico significa:",
                       "frustração disfarçada", ["frustração disfarçada", "entusiasmo sincero", "pergunta"]),
                    ex("text", "Complete: \"Очень ___!\" (seco, irônico) — interessante",
                       "интересно"),
                    ex("audio", "Escute e transcreva:", "ну отлично", audio_text="Ну, отлично!"),
                    ex("quiz", "Para detectar sarcasmo, preste atenção ao:",
                       "tom e contexto", ["tom e contexto", "só às palavras", "ao tamanho"]),
                    ex("speak", "Repita em voz alta:", "очень интересно", audio_text="Очень интересно!"),
                ],
            ),
            topic(
                "linguagem-idiomatica-russo",
                "Linguagem idiomática",
                """
# Linguagem idiomática

No domínio C1, você usa idioms com **naturalidade** — e sem exagerar:

| Idiom | Tradução literal | Sentido |
|---|---|---|
| держать язык за зубами | manter a língua atrás dos dentes | ficar quieto |
| вешать нос | pendurar o nariz | ficar triste |
| рукой подать | é de mão estendida | ser perto |
| заварить кашу | preparar o mingau | criar confusão |

```
Не вешай нос!          Não fique triste!
Магазин рядом, рукой подать.  A loja é perto, é só esticar a mão.
```

> 💘 Idioms demais soam **forçados**. Use com moderação, no contexto certo — como um nativo faria.
""",
                [
                    ex("quiz", "Linguagem idiomática é:",
                       "natural e figurada", ["natural e figurada", "literal", "formal sempre"]),
                    ex("quiz", "O que 'вешать нос' significa?",
                       "ficar triste", ["ficar triste", "ficar feliz", "dormir"]),
                    ex("text", "Complete: \"Не ___ нос!\" (não fique triste)",
                       "вешай"),
                    ex("audio", "Escute e transcreva:", "магазин рядом рукой подать", audio_text="Магазин рядом, рукой подать."),
                    ex("quiz", "Usar idioms demais:",
                       "pode soar forçado", ["pode soar forçado", "é sempre ótimo", "é proibido"]),
                    ex("speak", "Repita em voz alta:", "не вешай нос", audio_text="Не вешай нос!"),
                ],
            ),
            topic(
                "registros-diferentes-russo",
                "Registros diferentes",
                """
# Registros diferentes

Domínio total é **alternar registros** com naturalidade:

```
Formal:    Я хотел бы попросить вас...
Semiformal: Можно вас попросить...?
Informal:  Можно тебя попросить...?
```

```
Formal:    Благодарю вас.
Informal:  Спасибо!
```

> 💘 Quem domina o C1 não fala igual em todos os lugares — **adapta** o registro ao público e à situação.
""",
                [
                    ex("quiz", "Registros diferentes exigem:",
                       "adaptar vocabulário e tom", ["adaptar vocabulário e tom", "sempre o mesmo", "nada"]),
                    ex("quiz", "Entre amigos, o registro é:",
                       "informal", ["informal", "formal", "jurídico"]),
                    ex("text", "Complete no registro formal: \"___ вас попросить...\" (gostaria)",
                       "хотел бы"),
                    ex("audio", "Escute e transcreva:", "благодарю вас", audio_text="Благодарю вас."),
                    ex("quiz", "Em reunião profissional, o registro é:",
                       "formal ou semiformal", ["formal ou semiformal", "de gíria", "informal total"]),
                    ex("speak", "Repita em voz alta:", "я хотел бы попросить вас", audio_text="Я хотел бы попросить вас..."),
                ],
            ),
            topic(
                "comunicacao-precisa-russo",
                "Comunicação precisa",
                """
# Comunicação precisa

**Comunicação precisa** evita ambiguidade — essencial em prazos, números e decisões:

```
Уточните, пожалуйста.       Esclareça, por favor.
То есть, ...                Ou seja, ...
Другими словами, ...        Em outras palavras, ...
Если я правильно понял...   Se entendi corretamente...

Уточните, пожалуйста, дату.     Esclareça, por favor, a data.
То есть, мы встречаемся завтра.  Ou seja, nos encontramos amanhã.
```

> 💘 "Уточните" (esclareça) é a palavra-chave da precisão em russo — evita mal-entendidos.
""",
                [
                    ex("quiz", "Comunicação precisa evita:",
                       "ambiguidade e vagueza", ["ambiguidade e vagueza", "clareza", "exemplos"]),
                    ex("quiz", "O que 'Уточните' significa?",
                       "Esclareça / especifique", ["Esclareça / especifique", "Apresse-se", "Desista"]),
                    ex("text", "Complete: \"То ___, мы встречаемся завтра.\" (ou seja)",
                       "есть"),
                    ex("audio", "Escute e transcreva:", "уточните пожалуйста дату", audio_text="Уточните, пожалуйста, дату."),
                    ex("quiz", "Para confirmar entendimento:",
                       "Если я правильно понял...", ["Если я правильно понял...", "Не знаю.", "Пока!"]),
                    ex("speak", "Repita em voz alta:", "то есть мы встречаемся завтра", audio_text="То есть, мы встречаемся завтра."),
                ],
            ),
        ],
    )


# ============================================================
# MODULO 29 - Imersao Final (aplicado, pos-C1)
# ============================================================

def build_modulo_29_imersao_final():
    return module(
        "modulo-29-imersao-final",
        "Módulo 29 — Imersão Final",
        "Ler livros, assistir filmes sem legenda, ouvir podcasts, escrever e falar todos os dias, e pensar em russo — o fechamento do curso.",
        [
            topic(
                "ler-livros-em-russo",
                "Ler livros em russo",
                """
# Ler livros em russo

Ler é uma das formas mais ricas de imersão — e deve ser **progressiva**.

## Como começar

- Escolha livros **curtos e do seu nível**.
- Leia **um pouco todo dia** (2-3 páginas).
- Ao encontrar palavra nova, **tente adivinhar pelo contexto** antes do dicionário.

> 💘 Ler em voz alta de vez em quando também treina **pronúncia e ritmo**.
""",
                [
                    ex("quiz", "Para começar a ler em russo:",
                       "livros curtos e do seu nível", ["livros curtos e do seu nível", "clássicos difíceis", "nada"]),
                    ex("quiz", "Ler todo dia cria:",
                       "ritmo e vocabulário automático", ["ritmo e vocabulário automático", "cansaço sem ganho", "nada"]),
                    ex("text", "Complete: \"Читай ___ страниц каждый день.\" (poucas — несколько)",
                       "несколько"),
                    ex("audio", "Escute e transcreva:", "я читаю несколько страниц каждый день", audio_text="Я читаю несколько страниц каждый день."),
                    ex("quiz", "Ao encontrar palavra nova:",
                       "tente adivinhar pelo contexto", ["tente adivinhar pelo contexto", "pare tudo", "traduza tudo"]),
                    ex("speak", "Repita em voz alta:", "я читаю каждый день", audio_text="Я читаю каждый день."),
                ],
            ),
            topic(
                "filmes-sem-legenda-russo",
                "Assistir filmes sem legenda",
                """
# Assistir filmes sem legenda

Largar a legenda é **progressivo** — e um marco da imersão.

## Como fazer

1. **1ª fase**: legenda em russo.
2. **2ª fase**: cenas conhecidas sem legenda.
3. **3ª fase**: episódios/filmes inteiros sem legenda.

Ao travar, **rever a cena com legenda** — é assim que se conecta som e escrita.

> 💘 Re-assistir algo que você já conhece sem legenda usa o **contexto** para preencher o que não ouviu.
""",
                [
                    ex("quiz", "Para largar a legenda:",
                       "tire gradualmente (cenas -> episódios)", ["tire gradualmente (cenas -> episódios)", "de uma vez", "nunca"]),
                    ex("quiz", "Ao re-assistir algo conhecido sem legenda:",
                       "o contexto ajuda a entender", ["o contexto ajuda a entender", "atrapalha", "nada"]),
                    ex("text", "Complete: \"Смотри с русскими ___.\" (legendas — субтитры)",
                       "субтитрами"),
                    ex("audio", "Escute e transcreva:", "я могу смотреть это без субтитров", audio_text="Я могу смотреть это без субтитров."),
                    ex("quiz", "Filme sem legenda treina:",
                       "escuta real e fala rápida", ["escuta real e fala rápida", "só leitura", "nada"]),
                    ex("speak", "Repita em voz alta:", "я могу смотреть это без субтитров", audio_text="Я могу смотреть это без субтитров."),
                ],
            ),
            topic(
                "podcasts-em-russo",
                "Ouvir podcasts em russo",
                """
# Ouvir podcasts em russo

Podcasts são imersão que **cabe em qualquer rotina**.

## Como aproveitar

- Ouça **no deslocamento** (в дороге), academia ou tarefas.
- Escolha temas do seu **interesse**.
- Depois, **resuma em voz alta** — treina escuta E fala.

> 💘 Um pouco todo dia rende mais que horas no domingo. Constância é a chave.
""",
                [
                    ex("quiz", "Podcasts cabem na rotina porque:",
                       "dá para ouvir em qualquer lugar", ["dá para ouvir em qualquer lugar", "são longos demais", "não têm áudio"]),
                    ex("quiz", "A rotina ideal:",
                       "um pouco todo dia", ["um pouco todo dia", "horas no domingo", "nunca"]),
                    ex("text", "Complete: \"Я слушаю подкасты в ___.\" (no caminho — дорога)",
                       "дороге"),
                    ex("audio", "Escute e transcreva:", "я слушаю подкасты в дороге", audio_text="Я слушаю подкасты в дороге."),
                    ex("quiz", "Podcast + resumo em voz alta:",
                       "treina escuta E fala", ["treina escuta E fala", "só escuta", "nada"]),
                    ex("speak", "Repita em voz alta:", "я слушаю подкасты в дороге", audio_text="Я слушаю подкасты в дороге."),
                ],
            ),
            topic(
                "escrever-e-falar-todos-os-dias",
                "Escrever e falar todos os dias",
                """
# Escrever e falar todos os dias

A escrita e a fala diárias constroem **consistência** e **vocabulário ativo**.

## Como fazer

- Escreva um **diário** em russo: "Сегодня я...".
- **Fale sozinho**: narre sua rotina ou descreva o que vê.
- Não **traduza palavra a palavra** — use o que você já sabe.

> 💘 Escrever consolida o vocabulário **ativo** — aquele que você consegue produzir, não só reconhecer. E falar sozinho treina fluência sem precisar de interlocutor.
""",
                [
                    ex("quiz", "Escrever todo dia cria:",
                       "consistência e confiança", ["consistência e confiança", "pressão", "nada"]),
                    ex("quiz", "Um bom início de diário:",
                       "Сегодня я...", ["Сегодня я...", "Бла-бла.", "Пока!"]),
                    ex("text", "Complete: \"Сегодня я ___ рано.\" (acordei — встать)",
                       "встал"),
                    ex("audio", "Escute e transcreva:", "сегодня я встал рано", audio_text="Сегодня я встал рано."),
                    ex("quiz", "Falar sozinho em russo:",
                       "treina fluência", ["treina fluência", "é inútil", "é proibido"]),
                    ex("speak", "Repita em voz alta:", "сегодня я встал рано", audio_text="Сегодня я встал рано."),
                ],
            ),
            topic(
                "pensar-em-russo-imersao",
                "Pensar em russo (imersão)",
                """
# Pensar em russo (imersão)

Pensar em russo é o **sinal máximo** de fluência consolidada.

## Como chegar lá

- **Narre sua rotina** em russo (em pensamento ou voz baixa).
- Responda a si mesmo em russo.
- Aos poucos, os sonhos também migram para o russo — um grande marco!

> 💘 Quando você **sonha** em russo, a imersão virou parte de você. Parabéns: este é o fim do curso, e o começo da autonomia.
""",
                [
                    ex("quiz", "Pensar em russo é o sinal de:",
                       "fluência consolidada", ["fluência consolidada", "erro", "moda"]),
                    ex("quiz", "Para chegar lá, pratique:",
                       "narrar a rotina em russo", ["narrar a rotina em russo", "nunca", "só sonhos"]),
                    ex("text", "Complete: \"Попробуй думать по-___ .\" (russo)",
                       "русски"),
                    ex("audio", "Escute e transcreva:", "я стараюсь думать по-русски", audio_text="Я стараюсь думать по-русски."),
                    ex("quiz", "Quando você sonha em russo:",
                       "é um grande marco", ["é um grande marco", "é erro", "é impossível"]),
                    ex("speak", "Repita em voz alta:", "я стараюсь думать по-русски", audio_text="Я стараюсь думать по-русски."),
                ],
            ),
        ],
    )


# ============================================================
# Expansão editorial dos módulos 1–8
# ============================================================

# Os builders originais continuam contendo o núcleo já revisado. Estes itens
# são complementos por tópico, em vez de exercícios genéricos gerados em lote:
# cada um pratica uma palavra, uma forma ou uma decisão gramatical concreta.
EARLY_EXERCISES = {
    "como-o-curso-funciona": [
        ex("quiz", "Qual nível corresponde ao iniciante que está começando a ler frases simples?",
           "A1", ["A1", "B1", "C1"], audio_lang="pt-BR"),
        ex("quiz", "Em qual módulo aparece o primeiro contato com os seis casos?",
           "Módulo 4", ["Módulo 2", "Módulo 4", "Módulo 8"], audio_lang="pt-BR"),
        ex("text", 'Escreva em cirílico a forma masculina de "russo".', "русский"),
        ex("quiz", "O que fazer quando uma palavra russa nova aparece na lição?",
           "Ouvir a pronúncia e depois praticar", [
               "Ouvir a pronúncia e depois praticar",
               "Ignorar o áudio e decorar só a tradução",
               "Trocar a palavra por uma transliteração"
           ], audio_lang="pt-BR"),
        ex("quiz", "Qual é a ideia do currículo em espiral?",
           "Revisar o mesmo tema com mais profundidade",
           [
               "Revisar o mesmo tema com mais profundidade",
               "Estudar cada tema uma única vez",
               "Repetir somente exercícios de vocabulário"
           ], audio_lang="pt-BR"),
    ],
    "alfabeto-cirilico": [
        ex("quiz", 'Qual letra representa o som "ts"?', "Ц", ["Ц", "Ч", "Щ"]),
        ex("text", 'Escreva em cirílico "escola".', "школа"),
        ex("audio", "Escute e transcreva:", "школа", audio_text="школа"),
        ex("speak", "Repita a palavra em voz alta:", "рыба", audio_text="рыба"),
        ex("quiz", 'Qual falsa amiga visual tem som de "s"?', "С", ["С", "Р", "В"]),
    ],
    "sons-dificeis-do-russo": [
        ex("quiz", "Qual destas vogais é iotizada e pode amolecer a consoante anterior?",
           "я", ["я", "а", "ы"]),
        ex("text", 'Escreva em cirílico "cinco".', "пять"),
        ex("audio", "Escute e transcreva:", "молоко", audio_text="молоко"),
        ex("speak", "Repita a palavra em voz alta:", "юг", audio_text="юг"),
        ex("quiz", 'Em "молоко", onde cai o acento tônico?',
           "Na última sílaba", ["Na primeira sílaba", "Na segunda sílaba", "Na última sílaba"], audio_lang="pt-BR"),
    ],
    "primeiras-palavras-e-saudacoes": [
        ex("text", 'Traduza para o russo: "Oi" (informal).', "привет"),
        ex("quiz", 'Qual despedida é formal?', "До свидания", ["Пока", "До свидания", "Привет"]),
        ex("audio", "Escute e transcreva:", "до свидания", audio_text="до свидания"),
        ex("speak", "Repita a pergunta em voz alta:", "как дела", audio_text="как дела"),
        ex("quiz", 'Qual resposta significa "Bem!"?', "Хорошо!", ["Хорошо!", "Так себе", "Нет"]),
    ],
    "numeros-1-a-10-russo": [
        ex("quiz", 'Qual número é "девять"?', "9", ["7", "8", "9"]),
        ex("text", "Escreva em cirílico o número 3.", "три"),
        ex("audio", "Escute e transcreva o número:", "девять", audio_text="девять"),
        ex("speak", "Repita o número em voz alta:", "четыре", audio_text="четыре"),
        ex("quiz", 'Qual número é "восемь"?', "8", ["6", "8", "10"]),
    ],
    "pronomes-pessoais-russo": [
        ex("text", 'Traduza para o russo: "você" formal.', "вы"),
        ex("quiz", 'Qual pronome significa "eles/elas"?', "они", ["они", "оно", "мы"]),
        ex("audio", "Escute e transcreva:", "она", audio_text="она"),
        ex("speak", "Repita em voz alta:", "мы", audio_text="мы"),
    ],
    "genero-dos-substantivos": [
        ex("quiz", 'Qual é o gênero de "море" (mar)?', "neutro", ["masculino", "feminino", "neutro"], audio_lang="pt-BR"),
        ex("text", 'Escreva o gênero de "дверь": masculino ou feminino?', "feminino", audio_lang="pt-BR"),
        ex("audio", "Escute e transcreva:", "словарь", audio_text="словарь"),
        ex("quiz", 'Uma palavra terminada em "-я" é geralmente:',
           "feminina", ["masculina", "feminina", "neutra"], audio_lang="pt-BR"),
    ],
    "frases-sem-verbo-ser": [
        ex("text", "Traduza: Ele [é] médico.", "он врач"),
        ex("quiz", 'No presente, qual palavra NÃO entra em "Она врач"?',
           'быть', ["быть", "врач", "она"]),
        ex("audio", "Escute e transcreva:", "москва столица россии", audio_text="москва столица россии"),
        ex("speak", "Repita em voz alta:", "это окно", audio_text="это окно"),
    ],
    "plural-basico-russo": [
        ex("quiz", 'Qual é o plural de "море" (mar)?', "моря", ["моры", "моря", "море"]),
        ex("text", 'Escreva o plural de "студент" (estudante).', "студенты"),
        ex("audio", "Escute e transcreva:", "книги", audio_text="книги"),
        ex("quiz", 'Depois de "ж", a grafia correta do plural usa:', "-и", ["-ы", "-и", "-а"], audio_lang="pt-BR"),
    ],
    "isso-e-palavras-comuns": [
        ex("text", "Traduza: Isto é uma janela.", "это окно"),
        ex("quiz", 'Na frase "Это мой город", o que apresenta o objeto?',
           "это", ["это", "мой", "город"]),
        ex("audio", "Escute e transcreva:", "это мой город", audio_text="это мой город"),
        ex("speak", "Repita em voz alta:", "это моя сестра", audio_text="это моя сестра"),
    ],
    "palavras-interrogativas-russo": [
        ex("text", "Traduza: Quando você trabalha?", "когда ты работаешь"),
        ex("quiz", 'Qual palavra significa "por quê?"?', "почему", ["почему", "когда", "сколько"]),
        ex("audio", "Escute e transcreva:", "сколько это стоит", audio_text="сколько это стоит"),
        ex("speak", "Repita em voz alta:", "кто это", audio_text="кто это"),
    ],
    "gde-vs-kuda": [
        ex("text", "Traduza: Para onde você vai?", "куда ты идёшь"),
        ex("quiz", 'Qual pergunta indica localização parada?',
           "Где ты?", ["Где ты?", "Куда ты идёшь?", "Куда ты едешь?"] ),
        ex("audio", "Escute e transcreva:", "я живу в москве", audio_text="я живу в москве"),
        ex("speak", "Repita em voz alta:", "куда ты идёшь", audio_text="куда ты идёшь"),
    ],
    "negacao-com-nao": [
        ex("text", "Traduza: Ela não fala russo.", "она не говорит по-русски"),
        ex("quiz", 'Em "Я не читаю", onde fica "не"?',
           "Antes do verbo", ["Antes do verbo", "Depois do verbo", "No fim da frase"], audio_lang="pt-BR"),
        ex("audio", "Escute e transcreva:", "это не мой дом", audio_text="это не мой дом"),
        ex("speak", "Repita em voz alta:", "я не понимаю", audio_text="я не понимаю"),
        ex("quiz", 'Em "Я не читаю", o que "не" nega?',
           "A ação de ler", ["A ação de ler", "A palavra я", "O lugar"], audio_lang="pt-BR"),
    ],
    "respostas-curtas": [
        ex("quiz", 'Qual palavra responde "não"?', "Нет", ["Да", "Нет", "Пожалуйста"]),
        ex("text", "Traduza: Sim, isso é um livro.", "да это книга"),
        ex("audio", "Escute e transcreva:", "да я понимаю", audio_text="да я понимаю"),
        ex("speak", "Repita em voz alta:", "нет я не знаю", audio_text="нет я не знаю"),
        ex("quiz", 'Em "У меня нет времени", o sentido de "нет" é:',
           "não tenho tempo", ["não tenho tempo", "tenho tempo", "gosto de tempo"], audio_lang="pt-BR"),
    ],
    "o-que-sao-os-casos": [
        ex("quiz", 'Qual caso marca normalmente o objeto direto?', "Acusativo", ["Nominativo", "Acusativo", "Instrumental"], audio_lang="pt-BR"),
        ex("quiz", 'A expressão "с другом" é um exemplo de qual caso?', "Instrumental", ["Instrumental", "Genitivo", "Preposicional"], audio_lang="pt-BR"),
        ex("text", "Traduza: Eu gosto de música.", "мне нравится музыка"),
        ex("speak", "Repita em voz alta:", "я иду с другом", audio_text="я иду с другом"),
    ],
    "caso-nominativo-contato": [
        ex("quiz", 'Qual palavra é o sujeito em "Девушка читает"?', "Девушка", ["Девушка", "читает", "nenhuma"], audio_lang="pt-BR"),
        ex("text", "Traduza: Moscou é a capital da Rússia.", "москва столица россии"),
        ex("audio", "Escute e transcreva:", "студенты читают", audio_text="студенты читают"),
        ex("quiz", 'A forma de dicionário de "студент" é o:', "Nominativo", ["Nominativo", "Acusativo", "Dativo"], audio_lang="pt-BR"),
        ex("speak", "Repita em voz alta:", "книга на столе", audio_text="книга на столе"),
    ],
    "caso-acusativo-contato": [
        ex("quiz", 'Em "Я люблю чай", qual palavra recebe diretamente a ação?', "чай", ["Я", "люблю", "чай"]),
        ex("text", "Traduza: Meu nome é Maria.", "меня зовут мария"),
        ex("audio", "Escute e transcreva:", "я вижу собаку", audio_text="я вижу собаку"),
        ex("quiz", 'Em "Я иду в парк", o grupo "в парк" indica:',
           "direção no Acusativo", ["direção no Acusativo", "lugar no Preposicional", "posse no Genitivo"], audio_lang="pt-BR"),
        ex("speak", "Repita em voz alta:", "я читаю книгу", audio_text="я читаю книгу"),
    ],
    "caso-genitivo-contato": [
        ex("quiz", 'Em "У неё есть брат", a forma "неё" pertence ao:', "Genitivo", ["Genitivo", "Dativo", "Instrumental"], audio_lang="pt-BR"),
        ex("text", "Traduza: Ele tem um carro.", "у него есть машина"),
        ex("audio", "Escute e transcreva:", "у меня нет времени", audio_text="у меня нет времени"),
        ex("quiz", 'Em "Я из Бразилии", "из Бразилии" indica:', "origem no Genitivo", ["origem no Genitivo", "destino no Acusativo", "companhia no Instrumental"], audio_lang="pt-BR"),
        ex("speak", "Repita em voz alta:", "это книга анны", audio_text="это книга анны"),
    ],
    "caso-dativo-contato": [
        ex("quiz", 'Qual é a forma de "я" no Dativo?', "мне", ["мне", "меня", "мной"]),
        ex("text", "Traduza: Eu preciso de tempo.", "мне нужно время"),
        ex("audio", "Escute e transcreva:", "ему нравится музыка", audio_text="ему нравится музыка"),
        ex("quiz", 'Em "Я пишу другу", qual é a função de "другу"?', "para quem escrevo", ["para quem escrevo", "quem escreve", "o que possuo"], audio_lang="pt-BR"),
        ex("speak", "Repita em voz alta:", "мне нравится чай", audio_text="мне нравится чай"),
    ],
    "caso-instrumental-e-preposicional-contato": [
        ex("quiz", 'Em "Я говорю с мамой", qual caso aparece depois de "с"?', "Instrumental", ["Instrumental", "Acusativo", "Genitivo"], audio_lang="pt-BR"),
        ex("text", "Traduza: Eu penso no livro.", "я думаю о книге"),
        ex("audio", "Escute e transcreva:", "я пишу ручкой", audio_text="я пишу ручкой"),
        ex("quiz", 'Qual combinação indica localização, e não direção?',
           "Я в школе — Preposicional", ["Я в школе — Preposicional", "Я иду в школу — Acusativo", "Я из школы — Genitivo"], audio_lang="pt-BR"),
    ],
    "rotina-diaria": [
        ex("text", "Traduza: Eu durmo.", "я сплю"),
        ex("quiz", 'Em "Я работаю в офисе", por que aparece "в офисе"?',
           "Porque indica lugar", ["Porque indica lugar", "Porque indica posse", "Porque é objeto direto"], audio_lang="pt-BR"),
        ex("audio", "Escute e transcreva:", "я завтракаю", audio_text="я завтракаю"),
        ex("speak", "Repita em voz alta:", "я отдыхаю", audio_text="я отдыхаю"),
    ],
    "familia-e-pessoas": [
        ex("text", "Traduza: Este é o meu irmão.", "это мой брат"),
        ex("quiz", 'Em "Я иду с сестрой", qual caso aparece em "с сестрой"?', "Instrumental", ["Instrumental", "Dativo", "Preposicional"], audio_lang="pt-BR"),
        ex("audio", "Escute e transcreva:", "это моя семья", audio_text="это моя семья"),
        ex("speak", "Repita em voz alta:", "у меня есть сестра", audio_text="у меня есть сестра"),
    ],
    "lugares-na-cidade-russo": [
        ex("text", "Traduza: Eu vou para o parque.", "я иду в парк"),
        ex("quiz", 'Em "Я иду в парк", "в парк" expressa:',
           "direção no Acusativo", ["direção no Acusativo", "localização no Preposicional", "origem no Genitivo"], audio_lang="pt-BR"),
        ex("audio", "Escute e transcreva:", "я в городе", audio_text="я в городе"),
        ex("speak", "Repita em voz alta:", "магазин рядом с домом", audio_text="магазин рядом с домом"),
    ],
    "comida-e-bebida": [
        ex("text", "Traduza: Eu bebo água.", "я пью воду"),
        ex("quiz", 'Em "Мне нравится кофе", "кофе" funciona como:', "sujeito da construção", ["sujeito da construção", "objeto no Acusativo", "companhia no Instrumental"], audio_lang="pt-BR"),
        ex("audio", "Escute e transcreva:", "я люблю молоко", audio_text="я люблю молоко"),
        ex("speak", "Repita em voz alta:", "я ем хлеб", audio_text="я ем хлеб"),
    ],
    "apresentacoes-basicas": [
        ex("text", "Traduza: De onde você é?", "откуда ты"),
        ex("quiz", 'Em "Я из Бразилии", o grupo "из Бразилии" expressa:', "origem no Genitivo", ["origem no Genitivo", "destino no Acusativo", "lugar no Preposicional"], audio_lang="pt-BR"),
        ex("audio", "Escute e transcreva:", "это мой друг", audio_text="это мой друг"),
        ex("speak", "Repita em voz alta:", "очень приятно", audio_text="очень приятно"),
    ],
    "pedidos-simples-russo": [
        ex("text", "Traduza: Dê-me água, por favor.", "дайте пожалуйста воды"),
        ex("quiz", 'Em "Можно воды?", por que aparece "воды"?',
           "Para indicar uma quantidade não especificada", [
               "Para indicar uma quantidade não especificada",
               "Para indicar o destino",
               "Para indicar a pessoa que pede"
           ], audio_lang="pt-BR"),
        ex("audio", "Escute e transcreva:", "извините", audio_text="извините"),
        ex("speak", "Repita em voz alta:", "можно чай", audio_text="можно чай"),
    ],
    "primeira-conjugacao": [
        ex("text", "Traduza: Nós lemos o livro.", "мы читаем книгу"),
        ex("quiz", 'Complete: "Ты ___ книгу." (lê)', "читаешь", ["читаю", "читаешь", "читают"]),
        ex("audio", "Escute e transcreva:", "они читают", audio_text="они читают"),
        ex("speak", "Repita em voz alta:", "вы работаете", audio_text="вы работаете"),
    ],
    "segunda-conjugacao": [
        ex("text", "Traduza: Ela gosta de música.", "она любит музыку"),
        ex("quiz", 'Na 2ª conjugação, a terminação de "ты" em "говорить" é:', "-ишь", ["-ишь", "-ешь", "-ете"], audio_lang="pt-BR"),
        ex("audio", "Escute e transcreva:", "мы любим музыку", audio_text="мы любим музыку"),
        ex("speak", "Repita em voz alta:", "они говорят по-русски", audio_text="они говорят по-русски"),
    ],
    "verbos-irregulares-comuns": [
        ex("text", "Traduza: Ela quer café.", "она хочет кофе"),
        ex("quiz", 'Qual é a 1ª pessoa do presente de "идти"?', "иду", ["иду", "идёшь", "идут"]),
        ex("audio", "Escute e transcreva:", "ты ешь", audio_text="ты ешь"),
        ex("speak", "Repita em voz alta:", "мы идём домой", audio_text="мы идём домой"),
    ],
    "verbos-comuns-da-rotina": [
        ex("text", "Traduza: Eu sei russo.", "я знаю русский"),
        ex("quiz", 'Complete: "Я ___ в Бразилии." (moro)', "живу", ["живу", "живёшь", "живут"]),
        ex("audio", "Escute e transcreva:", "я люблю музыку", audio_text="я люблю музыку"),
        ex("speak", "Repita em voz alta:", "я работаю дома", audio_text="я работаю дома"),
    ],
    "perguntas-e-negacao-no-presente": [
        ex("text", "Traduza: Você trabalha hoje?", "ты работаешь сегодня"),
        ex("quiz", 'Como se nega "Я знаю"?', "Я не знаю", ["Я не знаю", "Я знаю не", "Не я знаю"]),
        ex("audio", "Escute e transcreva:", "что ты читаешь", audio_text="что ты читаешь"),
        ex("speak", "Repita em voz alta:", "нет я не знаю", audio_text="нет я не знаю"),
    ],
    "cidade-e-direcoes": [
        ex("text", "Traduza: A loja fica perto de casa.", "магазин рядом с домом"),
        ex("quiz", 'Em "рядом с домом", qual caso aparece depois de "с"?', "Instrumental", ["Instrumental", "Acusativo", "Genitivo"], audio_lang="pt-BR"),
        ex("audio", "Escute e transcreva:", "идите налево", audio_text="идите налево"),
        ex("speak", "Repita em voz alta:", "где находится парк", audio_text="где находится парк"),
    ],
    "viagem-em-russo": [
        ex("text", "Traduza: Ele vai de trem.", "он едет на поезде"),
        ex("quiz", 'Em "на поезде", qual caso indica o meio de transporte?', "Preposicional", ["Preposicional", "Acusativo", "Dativo"], audio_lang="pt-BR"),
        ex("audio", "Escute e transcreva:", "я еду в аэропорт", audio_text="я еду в аэропорт"),
        ex("speak", "Repita em voz alta:", "сколько стоит билет", audio_text="сколько стоит билет"),
    ],
    "compras": [
        ex("text", "Traduza: Eu compro um livro.", "я покупаю книгу"),
        ex("quiz", 'Em "Я покупаю книгу", qual é a forma do objeto direto?', "книгу", ["книга", "книгу", "книге"]),
        ex("audio", "Escute e transcreva:", "я хочу купить воду", audio_text="я хочу купить воду"),
        ex("speak", "Repita em voz alta:", "это дёшево", audio_text="это дёшево"),
    ],
    "restaurante": [
        ex("text", "Traduza: A conta, por favor.", "счёт пожалуйста"),
        ex("quiz", 'Em "Я хочу заказать салат", o caso de "салат" é:', "Acusativo", ["Acusativo", "Preposicional", "Genitivo"], audio_lang="pt-BR"),
        ex("audio", "Escute e transcreva:", "суп вкусный", audio_text="суп вкусный"),
        ex("speak", "Repita em voz alta:", "можно салат пожалуйста", audio_text="можно салат пожалуйста"),
    ],
    "pedidos-educados": [
        ex("text", "Traduza: Posso tomar café?", "можно мне кофе"),
        ex("quiz", 'Em "Можно мне воды?", qual caso é "мне"?', "Dativo", ["Dativo", "Acusativo", "Genitivo"], audio_lang="pt-BR"),
        ex("audio", "Escute e transcreva:", "помогите пожалуйста", audio_text="помогите пожалуйста"),
        ex("speak", "Repita em voz alta:", "дайте пожалуйста воду", audio_text="дайте пожалуйста воду"),
    ],
    "localizar-objetos": [
        ex("text", "Traduza: As chaves estão na bolsa.", "ключи в сумке"),
        ex("quiz", 'Em "под столом", qual caso aparece depois de "под"?', "Instrumental", ["Instrumental", "Preposicional", "Dativo"], audio_lang="pt-BR"),
        ex("audio", "Escute e transcreva:", "книга на столе", audio_text="книга на столе"),
        ex("speak", "Repita em voz alta:", "где мой телефон", audio_text="где мой телефон"),
    ],
    "preposicional-lugar-e-assunto": [
        ex("text", "Traduza: Ela fala sobre o trabalho.", "она говорит о работе"),
        ex("quiz", 'Em "в Москве", qual caso aparece?', "Preposicional", ["Preposicional", "Acusativo", "Genitivo"], audio_lang="pt-BR"),
        ex("audio", "Escute e transcreva:", "мы живём в городе", audio_text="мы живём в городе"),
    ],
    "preposicional-pronomes": [
        ex("text", "Traduza: Ela pensa nele.", "она думает о нём"),
        ex("quiz", 'Qual é a forma de "мы" depois de "о"?', "о нас", ["о нас", "о нам", "о нами"]),
        ex("audio", "Escute e transcreva:", "я думаю о тебе", audio_text="я думаю о тебе"),
        ex("speak", "Repita em voz alta:", "они говорят обо мне", audio_text="они говорят обо мне"),
    ],
    "acusativo-objeto-e-direcao": [
        ex("text", "Traduza: Ela lê um livro novo.", "она читает новую книгу"),
        ex("quiz", 'Em "Я вижу кота", por que "кота" não fica como o Nominativo?',
           "Porque é masculino animado no Acusativo", [
               "Porque é masculino animado no Acusativo",
               "Porque é neutro no Preposicional",
               "Porque é feminino no Dativo"
           ], audio_lang="pt-BR"),
    ],
    "genitivo-posse-e-quantidade": [
        ex("text", "Traduza: Ela não tem tempo.", "у неё нет времени"),
        ex("quiz", 'Em "две книги", qual forma aparece depois de 2?', "Genitivo singular", ["Genitivo singular", "Genitivo plural", "Nominativo plural"], audio_lang="pt-BR"),
    ],
    "dativo-objeto-e-impessoais": [
        ex("audio", "Escute e transcreva:", "мне нужно время", audio_text="мне нужно время"),
        ex("quiz", 'Em "Он пишет сестре", qual caso é "сестре"?', "Dativo", ["Dativo", "Acusativo", "Instrumental"], audio_lang="pt-BR"),
    ],
    "instrumental-meio-e-tempo": [
        ex("text", "Traduza: Ela fala com a mãe.", "она говорит с мамой"),
        ex("quiz", 'Em "Он пишет карандашом", qual relação o Instrumental expressa?', "instrumento", ["instrumento", "posse", "destino"], audio_lang="pt-BR"),
    ],
    "plural-nos-casos": [
        ex("text", "Traduza: Nós falamos sobre os amigos.", "мы говорим о друзьях"),
        ex("quiz", 'Complete no Dativo plural: "Я пишу ___" (amigos).', "друзьям", ["друзья", "друзьям", "друзьями"]),
        ex("speak", "Repita em voz alta:", "они идут с друзьями", audio_text="они идут с друзьями"),
    ],
}


def lesson_review(explanation, examples, errors, summary):
    """Monta o complemento editorial comum a todas as lições iniciais."""
    error_lines = "\n".join(f"- {item}" for item in errors)
    return (
        "\n\n## Explicação consolidada\n\n"
        + explanation.strip()
        + "\n\n## Exemplos guiados\n\n"
        + examples.strip()
        + "\n\n## Erros comuns\n\n"
        + error_lines
        + "\n\n## Resumo prático\n\n"
        + summary.strip()
    )


EARLY_LESSON_REVISIONS = {
    "como-o-curso-funciona": lesson_review(
        "O curso alterna compreensão e produção: primeiro você identifica a forma, depois a digita ou fala. O CEFR descreve a autonomia esperada; o currículo em espiral retoma casos, aspecto e movimento em níveis diferentes, sem fingir que uma explicação inicial basta.",
        """
Я учу русский. (Ya uchu russkiy.) — Eu estudo russo.
Я возвращаюсь к теме. (Ya vozvrashchayus' k teme.) — Eu volto ao tema.
""",
        [
            "Confundir o nível A1 com domínio da gramática: A1 significa conseguir lidar com mensagens simples.",
            "Pular o áudio porque a tradução parece óbvia; reconhecimento visual não substitui compreensão oral.",
            "Esperar aprender os seis casos em uma única tabela, em vez de reconhecer os blocos primeiro.",
        ],
        "Use a sequência ouvir → reconhecer → produzir. M4 apresenta os casos; M8 ensina as declinações; as revisões posteriores refinam escolha e naturalidade.",
    ),
    "alfabeto-cirilico": lesson_review(
        "O alfabeto deve ser aprendido pelo som e pela forma da palavra, não por semelhança visual isolada. As falsas amigas В, Н, Р, С e У são especialmente importantes porque parecem latinas, mas representam outros sons.",
        """
Вино (vino) — vinho.
Нос (nos) — nariz.
Школа (shkola) — escola.
""",
        [
            "Ler В como b, Н como h, Р como p ou С como c; essas letras precisam ser associadas ao som russo.",
            "Escrever letras maiúsculas quando a palavra pede minúsculas; a forma muda, mas o som continua o mesmo.",
            "Tentar pronunciar uma palavra inteira pelo português sem ouvir o modelo.",
        ],
        "Reconheça as 33 letras em grupos, leia palavras curtas e confirme a pronúncia no áudio. A meta inicial é decodificar, não dominar todos os detalhes fonéticos.",
    ),
    "sons-dificeis-do-russo": lesson_review(
        "O sinal mole não é uma vogal: ele modifica a consoante anterior. O sinal duro separa uma consoante dura de uma vogal iotizada. Além disso, o acento tônico controla a pronúncia das vogais átonas, por isso a palavra escrita nem sempre revela sozinha o som.",
        """
Мать (mat') — mãe.
Пять (pyat') — cinco.
Молоко (moloko) — leite; o acento está na última sílaba.
""",
        [
            "Pronunciar ь e ъ como se fossem vogais independentes.",
            "Supor que todo о não acentuado mantém o mesmo som do о tônico.",
            "Tratar я, ё, ю, е e и como simples vogais, ignorando a possível palatalização.",
        ],
        "Marque mentalmente o acento, observe os sinais e repita a palavra inteira. Não tente resolver a pronúncia apenas letra por letra.",
    ),
    "primeiras-palavras-e-saudacoes": lesson_review(
        "Saudações russas codificam relação e situação. Привет e Пока são informais; Здравствуйте e До свидания são formas seguras em contexto formal. Пожалуйста muda de tradução conforme seja pedido ou resposta a um agradecimento.",
        """
Привет! (Privet!) — Oi!
Как дела? (Kak dela?) — Como vai?
Хорошо! (Khorosho!) — Bem!
""",
        [
            "Usar Привет com uma autoridade ou desconhecido sem observar o registro.",
            "Traduzir Пожалуйста sempre como por favor e perder o sentido de de nada.",
            "Confundir До свидания, despedida formal, com Пока, despedida informal.",
        ],
        "Escolha a saudação pelo grau de formalidade, memorize pares de pergunta e resposta e pratique as frases como blocos sonoros.",
    ),
    "numeros-1-a-10-russo": lesson_review(
        "Os números de 1 a 10 são vocabulário de alta frequência e já mostram o sinal mole no final de várias palavras. Neste módulo, memorize a forma e o som; as mudanças do substantivo depois de números serão aprofundadas mais adiante.",
        """
Два (dva) — dois.
Пять (pyat') — cinco.
Восемь (vosem') — oito.
""",
        [
            "Trocar семь por семьь ou esquecer o sinal mole em пять, семь, восемь e десять.",
            "Confundir четыре (4) com три (3) por tentar memorizar só a primeira sílaba.",
            "Pronunciar о átono como o português sem conferir o áudio.",
        ],
        "Leia a sequência de 1 a 10, depois pratique números aleatórios. Produza a palavra em cirílico, não apenas o algarismo.",
    ),
    "pronomes-pessoais-russo": lesson_review(
        "Os pronomes pessoais distinguem pessoa, número e, no caso de он, она e оно, gênero. Вы pode ser plural ou singular formal; o contexto e a relação entre os interlocutores decidem a leitura.",
        """
Я дома. (Ya doma.) — Estou em casa.
Вы врач. (Vy vrach.) — O senhor / a senhora é médico(a).
Они здесь. (Ani zdes'.) — Eles/elas estão aqui.
""",
        [
            "Usar ты automaticamente para qualquer singular; com desconhecidos, вы é a opção polida.",
            "Confundir вы formal singular com vocês sem olhar para o verbo e o contexto.",
            "Ler они como uma forma de он; они é sempre plural.",
        ],
        "Associe cada pronome a pessoa e número, e memorize вы com os dois sentidos. A forma do pronome muda nos casos dos próximos módulos.",
    ),
    "genero-dos-substantivos": lesson_review(
        "O gênero russo é propriedade do substantivo, não uma tradução automática do gênero em português. Consoante tende a ser masculino, -а/-я feminino e -о/-е neutro; palavras em -ь precisam ser aprendidas individualmente.",
        """
Это море. (Eto more.) — Este é o mar.
Это дверь. (Eto dver'.) — Esta é a porta.
Мой словарь. (Moy slovar'.) — Meu dicionário.
""",
        [
            "Aplicar a regra de -а/-я a palavras em -ь, que podem ser masculinas ou femininas.",
            "Escolher o gênero pela tradução portuguesa, sem observar a terminação russa.",
            "Esquecer que o gênero reaparece em adjetivos e no passado verbal.",
        ],
        "Memorize substantivo e gênero juntos. Use a terminação como pista, mas trate -ь como vocabulário que exige consulta e prática.",
    ),
    "frases-sem-verbo-ser": lesson_review(
        "No presente, a cópula быть normalmente não aparece. O russo coloca sujeito e predicado lado a lado; quando ambos são substantivos, um travessão pode marcar a relação na escrita, sem representar uma palavra pronunciada.",
        """
Он врач. (On vrach.) — Ele é médico.
Это окно. (Eto okno.) — Isto é uma janela.
Москва — столица России. (Moskva — stolitsa Rossii.) — Moscou é a capital da Rússia.
""",
        [
            "Inserir есть em toda frase no presente: Я есть студент não é a forma neutra ensinada aqui.",
            "Usar o travessão como se fosse obrigatório na fala; ele é principalmente uma marca de escrita.",
            "Concluir que быть não existe; ele reaparece no passado e no futuro.",
        ],
        "No presente, use sujeito + predicado e omita быть. Use o travessão apenas como recurso de pontuação quando a escrita pedir.",
    ),
    "plural-basico-russo": lesson_review(
        "O plural depende da terminação e da ortografia da consoante anterior. Masculinos e femininos costumam formar -ы/-и; neutros em -о/-е costumam formar -а/-я. A escolha entre -ы e -и não é livre.",
        """
Столы. (Stoly.) — Mesas.
Книги. (Knigi.) — Livros.
Окна. (Okna.) — Janelas.
""",
        [
            "Escrever -ы depois de г, к, х, ш, ж, ч ou щ; a ortografia exige -и.",
            "Usar -ы em substantivos neutros como окно, que forma окна.",
            "Tratar toda forma plural como previsível; palavras frequentes como друг têm plural irregular.",
        ],
        "Identifique a terminação do singular, aplique a regra de gênero e confira a consoante anterior. Depois, leia o plural em voz alta.",
    ),
    "isso-e-palavras-comuns": lesson_review(
        "Это funciona como apresentador invariável: não muda com o gênero nem com o número do substantivo apresentado. O possessivo, por outro lado, concorda com o substantivo: мой дом, моя книга, моё окно.",
        """
Это мой дом. (Eto moy dom.) — Esta é a minha casa.
Это моя книга. (Eto moya kniga.) — Este é o meu livro.
Это окно. (Eto okno.) — Isto é uma janela.
""",
        [
            "Flexionar это como se fosse um artigo: a palavra permanece это nesta construção.",
            "Usar мой com qualquer substantivo e ignorar o gênero de книга ou окно.",
            "Confundir это com o pronome pessoal оно; это apresenta, não substitui simplesmente o substantivo.",
        ],
        "Mantenha это invariável e faça o possessivo concordar. Para produzir uma apresentação, use это + grupo nominal.",
    ),
    "palavras-interrogativas-russo": lesson_review(
        "A palavra interrogativa ocupa o lugar da informação desconhecida; não exige um auxiliar. A entonação ajuda, mas a própria palavra já orienta o sentido da pergunta.",
        """
Кто это? — Quem é?
Когда ты работаешь? — Quando você trabalha?
Сколько это стоит? — Quanto isso custa?
""",
        [
            "Confundir кто, para pessoas, com что, para coisas ou fatos.",
            "Usar где quando a pergunta é direção; куда pergunta para onde.",
            "Adicionar uma palavra equivalente a do/does do inglês; o verbo russo não precisa dela.",
        ],
        "Escolha a interrogativa pelo tipo de informação: pessoa, coisa, lugar, direção, tempo, motivo ou quantidade. Mantenha a ordem natural da frase.",
    ),
    "gde-vs-kuda": lesson_review(
        "Где pergunta por localização estática; куда pergunta por destino. A diferença não depende apenas do verbo: ela organiza a perspectiva espacial e antecipa a oposição entre Preposicional e Acusativo.",
        """
Где ты? — Onde você está?
Куда ты идёшь? — Para onde você vai?
Я живу в Москве. — Moro em Moscou.
""",
        [
            "Traduzir ambos como onde e perder a ideia de movimento em куда.",
            "Usar Где com um destino, como se localização e direção fossem a mesma coisa.",
            "Confundir идёшь, movimento a pé, com uma forma de estar parado.",
        ],
        "Pergunte где para posição e куда para destino. Primeiro decida se há deslocamento; depois escolha a construção de lugar adequada.",
    ),
    "negacao-com-nao": lesson_review(
        "Не vem antes do elemento negado, normalmente o verbo. A posição pode mudar o foco: em Это не моя книга, a negação recai sobre a posse; em Я не читаю, recai sobre a ação.",
        """
Я читаю. — Eu leio.
Я не читаю. — Eu não leio / não estou lendo.
Это не мой дом. — Esta não é a minha casa.
""",
        [
            "Colocar не depois do verbo por influência do português ou do inglês.",
            "Confundir не, que nega uma palavra ou ação, com нет, que também responde não e indica inexistência.",
            "Achar que a negação elimina a flexão ou altera automaticamente a ordem inteira da frase.",
        ],
        "Coloque не imediatamente antes do elemento que quer negar. Leia a frase e pergunte qual parte está sendo contrastada.",
    ),
    "respostas-curtas": lesson_review(
        "Да e нет podem funcionar sozinhos ou iniciar uma resposta curta. Para negar existência, нет aparece em uma construção própria e o elemento que não existe assume o Genitivo, que será estudado com mais detalhe depois.",
        """
Это книга? — Isto é um livro?
Да, книга. — Sim, é um livro.
Нет, это не книга. — Não, isto não é um livro.
""",
        [
            "Responder toda pergunta com uma frase longa, quando uma resposta curta já é natural.",
            "Usar да para concordar com uma frase negativa sem prestar atenção ao sentido da pergunta.",
            "Ler нет somente como não e ignorar o sentido de não há em У меня нет времени.",
        ],
        "Use да ou нет como resposta inicial; repita apenas a informação necessária. Reconheça нет como resposta e como marcador de inexistência.",
    ),
    "o-que-sao-os-casos": lesson_review(
        "Caso é a forma que sinaliza a função de um grupo nominal. Neste primeiro contato, o objetivo é reconhecer blocos e funções, não decorar paradigmas: sujeito, objeto, posse, destinatário, companhia e lugar são pistas suficientes por enquanto.",
        """
Студент читает. — O estudante lê. (sujeito)
Мне нравится музыка. — Eu gosto de música. (para mim agrada música)
Я иду с другом. — Eu vou com um amigo. (companhia)
""",
        [
            "Tentar declinar toda palavra nova neste módulo; as tabelas completas ficam no Módulo 8.",
            "Confundir a tradução portuguesa com o nome do caso, especialmente em construções impessoais.",
            "Supor que uma preposição sempre escolhe o mesmo caso sem considerar o sentido de lugar, direção ou companhia.",
        ],
        "Reconheça a função e memorize a frase fixa. Adie a pergunta sobre todas as terminações para o Módulo 8.",
    ),
    "caso-nominativo-contato": lesson_review(
        "O Nominativo é a forma de entrada do dicionário e normalmente marca quem realiza a ação ou o tema da frase. Ele também aparece no predicado nominal e no elemento que agrada em construções como Мне нравится музыка.",
        """
Девушка читает. — A moça lê.
Студенты читают. — Os estudantes leem.
Книга на столе. — O livro está sobre a mesa.
""",
        [
            "Escolher o primeiro substantivo como sujeito sem verificar quem realiza a ação.",
            "Achar que toda palavra antes do verbo é Nominativo; a ordem pode variar.",
            "Tentar aplicar terminações de outros casos ao sujeito sem necessidade.",
        ],
        "Pergunte quem ou o que realiza a ação. Se a forma é a entrada do dicionário e exerce essa função, reconheça Nominativo.",
    ),
    "caso-acusativo-contato": lesson_review(
        "O Acusativo aparece quando algo ou alguém recebe diretamente a ação e em destinos após в/на. As frases Меня зовут... e Я читаю книгу são blocos úteis; a declinação completa de animados e inanimados virá no Módulo 8.",
        """
Я читаю книгу. — Eu leio o livro.
Я вижу собаку. — Eu vejo o cachorro.
Я иду в парк. — Eu vou para o parque.
""",
        [
            "Confundir objeto direto com sujeito porque a ordem da frase parece semelhante ao português.",
            "Usar Preposicional em в парк; movimento para o destino pede Acusativo.",
            "Tentar memorizar apenas a terminação -у sem considerar gênero e animacidade.",
        ],
        "Procure o alvo da ação ou o destino do movimento. Neste módulo, reconheça o bloco; no Módulo 8, escolha a forma pela regra.",
    ),
    "caso-genitivo-contato": lesson_review(
        "O Genitivo aparece em posse, origem e na construção de existência com у, есть e нет. A leitura literal de у меня есть é “junto a mim há”; essa lógica evita procurar um verbo ter inexistente no presente.",
        """
У него есть машина. — Ele tem um carro.
У меня нет времени. — Eu não tenho tempo.
Это книга Анны. — Este é o livro de Anna.
""",
        [
            "Traduzir у меня есть com я имею em toda situação; a construção fixa é mais natural.",
            "Usar Nominativo depois de нет, ignorando a ideia de ausência.",
            "Confundir из, origem, com в, destino ou localização.",
        ],
        "Reconheça posse, origem e ausência como gatilhos do Genitivo. Memorize у меня есть, у меня нет e из + origem como blocos.",
    ),
    "caso-dativo-contato": lesson_review(
        "O Dativo marca o destinatário e a pessoa para quem uma sensação ou necessidade se apresenta. Em Мне нравится музыка, мне não é o sujeito gramatical: a estrutura significa literalmente “para mim agrada música”.",
        """
Я пишу другу. — Eu escrevo para um amigo.
Мне нужно время. — Eu preciso de tempo.
Ему нравится музыка. — Ele gosta de música.
""",
        [
            "Traduzir eu gosto como Я нравится; a construção usa Мне нравится.",
            "Confundir мне, Dativo, com меня, forma usada em outras funções.",
            "Procurar concordância do verbo com a pessoa que sente; нравится concorda com o que agrada.",
        ],
        "Pergunte “para quem?” ou reconheça Мне нравится/Мне нужно. Memorize o bloco antes de estudar as terminações.",
    ),
    "caso-instrumental-e-preposicional-contato": lesson_review(
        "O Instrumental aparece com companhia e instrumento; o Preposicional aparece depois de в, на ou о em local e assunto. O contraste в школе e в школу é uma decisão de sentido: posição contra destino.",
        """
Я говорю с мамой. — Eu falo com a mãe.
Я пишу ручкой. — Eu escrevo com uma caneta.
Я думаю о книге. — Eu penso no livro.
""",
        [
            "Usar Nominativo depois de с; companhia exige Instrumental.",
            "Confundir в школе, localização, com в школу, direção.",
            "Achar que Preposicional pode aparecer sem preposição.",
        ],
        "Veja a preposição e o sentido: с/чем ou с/кем aponta para Instrumental; в/на/о + lugar ou assunto aponta para Preposicional.",
    ),
    "rotina-diaria": lesson_review(
        "Verbos da rotina permitem praticar presente e lugar na mesma frase. Quando a ação ocorre em um local, в/на + forma de lugar descreve onde a pessoa está trabalhando ou estudando, sem verbo estar no presente.",
        """
Я завтракаю. — Eu tomo café da manhã.
Я работаю в офисе. — Eu trabalho no escritório.
Я сплю. — Eu durmo.
""",
        [
            "Usar Я есть перед uma atividade; o presente continua sem o verbo ser/estar.",
            "Usar в офис em localização, em vez de в офисе.",
            "Confundir учусь, estudo, com работаю, trabalho.",
        ],
        "Conjugue o verbo para я e acrescente a rotina. Para dizer onde, use в/на + a forma de lugar já reconhecida.",
    ),
    "familia-e-pessoas": lesson_review(
        "O vocabulário de família combina apresentação, posse e companhia. Isso faz o mesmo substantivo aparecer em funções diferentes: брат em У меня есть брат, mas другом em Я иду с другом.",
        """
Это мой брат. — Este é o meu irmão.
У меня есть сестра. — Eu tenho uma irmã.
Я иду с сестрой. — Eu vou com a minha irmã.
""",
        [
            "Manter брат depois de с; a companhia exige a forma do Instrumental.",
            "Usar мой com мама ou моя com брат sem concordância de gênero.",
            "Confundir семья, família, com сестра, irmã.",
        ],
        "Pratique cada membro da família em três moldes: это + posse, у меня есть + pessoa e с + companhia.",
    ),
    "lugares-na-cidade-russo": lesson_review(
        "Lugares da cidade reforçam a diferença entre destino e localização. В школу e в парк respondem para onde; в магазине e в городе respondem onde. A preposição é parecida, mas a forma e o sentido mudam.",
        """
Я иду в парк. — Eu vou para o parque.
Я в городе. — Eu estou na cidade.
Магазин рядом с домом. — A loja fica perto de casa.
""",
        [
            "Usar в городе para indicar movimento; a frase localiza, não indica destino.",
            "Esquecer o Instrumental depois de рядом с.",
            "Traduzir рядом como dentro; a palavra significa perto.",
        ],
        "Decida primeiro entre ir para um lugar e estar em um lugar. Depois, escolha Acusativo ou Preposicional e pratique o bloco completo.",
    ),
    "comida-e-bebida": lesson_review(
        "Comida e bebida mostram duas estruturas: verbos como пить e любить recebem um objeto direto; Мне нравится usa uma construção impessoal, em que o que agrada aparece como tema da frase.",
        """
Я пью воду. — Eu bebo água.
Я люблю молоко. — Eu gosto muito de leite.
Мне нравится кофе. — Eu gosto de café.
""",
        [
            "Usar Мне нравится com o pronome da pessoa como se fosse sujeito de gostar.",
            "Esquecer a forma вода → воду depois de пить.",
            "Supor que кофе muda de terminação como palavras comuns; ele é invariável neste nível.",
        ],
        "Use Я + verbo + alimento para ação direta. Use Мне нравится + tema para a construção impessoal de gosto.",
    ),
    "apresentacoes-basicas": lesson_review(
        "Apresentações combinam perguntas fixas e casos já reconhecíveis. Меня зовут apresenta o nome; из + lugar indica origem; это мой друг apresenta outra pessoa.",
        """
Как тебя зовут? — Qual é o seu nome?
Меня зовут Анна. — Meu nome é Anna.
Я из Бразилии. — Eu sou do Brasil.
""",
        [
            "Dizer Я зовут; a construção fixa usa Меня зовут.",
            "Usar в Бразилии para origem; из pede a ideia de “de, vindo de”.",
            "Confundir Откуда ты? com Где ты?, origem com localização atual.",
        ],
        "Memorize o par Как тебя зовут? → Меня зовут... e use из + lugar para dizer de onde você é.",
    ),
    "pedidos-simples-russo": lesson_review(
        "Pedidos iniciais usam fórmulas curtas e corteses. Можно pergunta se algo é possível; Дайте, пожалуйста solicita algo; Генitivo em Можно воды indica uma quantidade não especificada.",
        """
Можно чай? — Posso tomar chá?
Дайте, пожалуйста, воды. — Dê-me água, por favor.
Извините! — Desculpe / Com licença!
""",
        [
            "Usar água no Nominativo em Можно воды quando a intenção é uma quantidade não especificada.",
            "Confundir можно, possibilidade, com хочу, desejo direto.",
            "Omitir пожалуйста em uma situação em que a polidez é importante.",
        ],
        "Escolha Можно para pedir permissão ou oferta, Дайте para solicitar e acrescente пожалуйста quando quiser suavizar o pedido.",
    ),
    "primeira-conjugacao": lesson_review(
        "Na 1ª conjugação, as terminações do presente acompanham a pessoa: -ю/-у, -ешь, -ет, -ем, -ете, -ют/-ут. A raiz permanece reconhecível em verbos regulares como читать e работать.",
        """
Я читаю книгу. — Eu leio o livro.
Ты читаешь книгу. — Você lê o livro.
Они читают книгу. — Eles leem o livro.
""",
        [
            "Usar a terminação de я com ты: читаю não combina com ты.",
            "Esquecer -ете com вы e produzir uma forma de ты.",
            "Confundir o infinitivo читать com a forma conjugada читают.",
        ],
        "Identifique o pronome, remova -ть e aplique a terminação correspondente. Confirme a pessoa pelo sujeito antes de responder.",
    ),
    "segunda-conjugacao": lesson_review(
        "A 2ª conjugação aparece com frequência em verbos em -ить. Suas marcas mais visíveis são -ишь, -ит, -им e -ите, embora a 1ª pessoa e o plural final também exijam atenção.",
        """
Я люблю музыку. — Eu gosto de música.
Мы любим музыку. — Nós gostamos de música.
Они говорят по-русски. — Eles falam russo.
""",
        [
            "Escolher -ешь para ты em um verbo regular da 2ª conjugação.",
            "Confundir говорим, nós falamos, com говорите, vocês falam.",
            "Aplicar a regra do infinitivo sem lembrar que existem exceções.",
        ],
        "Procure -ить no infinitivo como pista, identifique o sujeito e observe o núcleo -и- nas terminações oblíquas.",
    ),
    "verbos-irregulares-comuns": lesson_review(
        "Хотеть, идти e есть são frequentes e não devem ser forçados nos modelos regulares. A forma precisa ser recuperada como vocabulário conjugado, especialmente em quero, vou e como.",
        """
Я хочу есть. — Eu quero comer.
Я иду домой. — Eu vou para casa a pé.
Ты ешь. — Você come.
""",
        [
            "Formar хочую ou идю seguindo uma regra inexistente.",
            "Confundir иду, movimento a pé agora, com uma forma de ехать, ir de veículo.",
            "Usar ем com ты; o presente de есть é ты ешь.",
        ],
        "Memorize as formas de alta frequência em frases inteiras: хочу, иду e ем/ешь/ест.",
    ),
    "verbos-comuns-da-rotina": lesson_review(
        "Os verbos da rotina combinam conjugação, vocabulário e casos. Жить costuma aparecer com lugar, любить com objeto direto e понимать com a expressão по-русски.",
        """
Я живу в Бразилии. — Eu moro no Brasil.
Я понимаю по-русски. — Eu entendo russo.
Я люблю музыку. — Eu gosto de música.
""",
        [
            "Usar я жить em vez da forma conjugada я живу.",
            "Trocar в Бразилии por в Бразилию quando a ideia é morar, não ir para lá.",
            "Confundir знаю, saber um fato, com понимаю, entender.",
        ],
        "Conjugue o verbo antes de escolher o complemento. Para local estático use в + forma de lugar; para objeto direto, reconheça o Acusativo.",
    ),
    "perguntas-e-negacao-no-presente": lesson_review(
        "No presente, a pergunta normalmente mantém a ordem declarativa e ganha entonação interrogativa. A negação continua sendo не antes do verbo; a resposta curta pode omitir o sujeito quando ele já está claro.",
        """
Ты работаешь сегодня? — Você trabalha hoje?
Что ты читаешь? — O que você lê?
Нет, не работаю. — Não, não trabalho.
""",
        [
            "Criar um auxiliar equivalente a do/does; o verbo russo não precisa dele.",
            "Colocar не no fim da frase: o padrão neutro é не + verbo.",
            "Responder Нет, работаю quando o sentido correto é negar a ação.",
        ],
        "Mantenha o verbo conjugado, use entonação para perguntar e coloque не imediatamente antes do verbo para negar.",
    ),
    "cidade-e-direcoes": lesson_review(
        "Para orientar alguém, combine pergunta de localização com direção e distância. Рядом с exige companhia/local de referência no Instrumental; Идите прямо e Идите налево são imperativos formais úteis.",
        """
Где находится парк? — Onde fica o parque?
Идите налево. — Vá à esquerda.
Магазин рядом с домом. — A loja fica perto de casa.
""",
        [
            "Confundir налево, à esquerda, com направо, à direita.",
            "Usar дом depois de с, em vez de домом.",
            "Tratar находится como uma tradução obrigatória de estar em toda frase; ele é útil para localizar algo.",
        ],
        "Pergunte onde fica, escolha a direção e lembre que рядом с puxa Instrumental para o ponto de referência.",
    ),
    "viagem-em-russo": lesson_review(
        "Viagem reúne destino, meio de transporte e preço. В + destino usa Acusativo; на + meio de transporte usa Preposicional em expressões como на поезде.",
        """
Я еду в аэропорт. — Eu vou para o aeroporto.
Он едет на поезде. — Ele vai de trem.
Сколько стоит билет? — Quanto custa o bilhete?
""",
        [
            "Usar в аэропорте para destino; аэропорте indica localização, não movimento para lá.",
            "Traduzir на поезде como um destino; a expressão indica o meio de transporte.",
            "Confundir билет, bilhete, com багаж, bagagem.",
        ],
        "Pergunte o destino com в + Acusativo, o meio com на + Preposicional e o preço com Сколько стоит...?.",
    ),
    "compras": lesson_review(
        "Em compras, o objeto de купить e покупать recebe a ação. Para substantivos femininos em -а, o Acusativo costuma aparecer em -у: книга → книгу.",
        """
Я покупаю книгу. — Eu compro um livro.
Я хочу купить воду. — Eu quero comprar água.
Это дёшево. — Isto é barato.
""",
        [
            "Usar книга depois de покупаю; o objeto feminino comum passa a книгу.",
            "Confundir дорого, caro, com дёшево, barato.",
            "Usar купить sem objeto quando a tarefa pede uma compra concreta.",
        ],
        "Use Сколько стоит...? para perguntar preço e flexione o objeto direto conforme a regra já estudada ou a forma memorizada.",
    ),
    "restaurante": lesson_review(
        "No restaurante, pedidos curtos são naturais. O objeto de заказать aparece no Acusativo; em substantivos masculinos inanimados como салат e суп, a forma pode ser igual à do Nominativo.",
        """
Я хочу заказать салат. — Eu quero pedir uma salada.
Можно меню, пожалуйста? — Pode me dar o cardápio, por favor?
Счёт, пожалуйста! — A conta, por favor!
""",
        [
            "Interpretar меню como plural obrigatório; a palavra é invariável e depende do contexto.",
            "Trocar салат por салата sem um motivo de Genitivo.",
            "Esquecer que суп e салат podem parecer Nominativo, embora exerçam função de objeto.",
        ],
        "Monte o pedido com Можно ou Я хочу заказать e identifique o objeto pelo verbo, não só pela aparência da terminação.",
    ),
    "pedidos-educados": lesson_review(
        "A polidez combina imperativo formal, пожалуйста e pronomes nos casos certos. Помогите мне usa Dativo para a pessoa ajudada; Можно мне воды combina Dativo e Genitivo de quantidade.",
        """
Помогите мне, пожалуйста! — Ajude-me, por favor!
Можно мне воды? — Posso tomar um pouco de água?
Дайте, пожалуйста, меню. — Dê-me o cardápio, por favor.
""",
        [
            "Usar меня depois de помогите; a pessoa beneficiária é мне.",
            "Trocar воды por вода quando a ideia é uma quantidade não especificada.",
            "Usar o imperativo informal com desconhecidos em uma situação de atendimento.",
        ],
        "Use Помогите/Дайте para pedidos diretos, мне para o destinatário e пожалуйста para suavizar o tom.",
    ),
    "localizar-objetos": lesson_review(
        "Para localizar objetos, в/на + Preposicional informa posição. Outras preposições espaciais, como под, podem exigir Instrumental: под столом significa debaixo da mesa.",
        """
Ключи в сумке. — As chaves estão na bolsa.
Книга на столе. — O livro está sobre a mesa.
Телефон под столом. — O telefone está debaixo da mesa.
""",
        [
            "Usar сумка ou сумку depois de в quando a frase responde onde, não para onde.",
            "Confundir на столе, sobre a mesa, com под столом, debaixo da mesa.",
            "Esquecer que под muda de construção conforme indica posição ou movimento.",
        ],
        "Pergunte Где...? para localização, escolha в/на/под pelo espaço e confira o caso exigido pela preposição.",
    ),
    "preposicional-lugar-e-assunto": lesson_review(
        "O Preposicional singular apresenta dois usos centrais: lugar com в/на e assunto com о/об. A terminação mais comum é -е; palavras femininas em -ь usam -и, e о vira об diante de vogal quando isso facilita a pronúncia.",
        """
Она говорит о работе. — Ela fala sobre o trabalho.
Мы живём в городе. — Nós moramos na cidade.
Она рассказывает об Америке. — Ela fala sobre a América.
""",
        [
            "Usar Acusativo em в Москве quando o verbo indica permanência, não destino.",
            "Escrever о Америке sem observar a combinação natural об Америке.",
            "Tratar -е como uma terminação universal; дверь vira двери.",
        ],
        "Identifique lugar ou assunto, escolha в/на/о(б) e aplique a forma singular correspondente. Preposicional precisa de preposição.",
    ),
    "preposicional-pronomes": lesson_review(
        "Pronomes pessoais têm formas próprias no Preposicional. Обо мне é uma combinação fixa; о нём, о ней e о них preservam a preposição e mudam a forma do pronome.",
        """
Она думает о нём. — Ela pensa nele.
Я думаю о тебе. — Eu penso em você.
Они говорят обо мне. — Eles falam sobre mim.
""",
        [
            "Usar о я ou о ты; pronomes não permanecem no Nominativo depois da preposição.",
            "Confundir о нём, Preposicional, com его, forma de outros casos.",
            "Esquecer о extra em обо мне, uma combinação motivada pela pronúncia.",
        ],
        "Memorize a tabela por blocos com о: обо мне, о тебе, о нём, о ней, о нас, о вас, о них.",
    ),
    "acusativo-objeto-e-direcao": lesson_review(
        "No Acusativo, gênero e animacidade importam. Feminino em -а passa a -у; masculino animado costuma igualar o Genitivo; masculino inanimado e neutro frequentemente mantêm a forma do Nominativo.",
        """
Она читает новую книгу. — Ela lê um livro novo.
Я вижу кота. — Eu vejo o gato.
Я иду в школу. — Eu vou para a escola.
""",
        [
            "Aplicar a regra de objeto inanimado a pessoa ou animal: кот vira кота.",
            "Confundir книгу com книге; o primeiro é objeto, o segundo é uma forma de lugar/assunto.",
            "Usar Preposicional depois de в com verbo de movimento para destino.",
        ],
        "Pergunte o que recebe a ação ou qual é o destino; depois classifique o substantivo por gênero e animacidade.",
    ),
    "genitivo-posse-e-quantidade": lesson_review(
        "O Genitivo singular aparece com posse, ausência e depois de 2, 3 e 4. Depois de 5 ou mais, é comum o Genitivo plural. Não basta contar: a forma do substantivo depende do número e do padrão de declinação.",
        """
У неё нет времени. — Ela não tem tempo.
Две книги. — Dois livros.
Пять книг. — Cinco livros.
""",
        [
            "Usar Nominativo depois de нет ou depois de две.",
            "Aplicar Genitivo singular depois de cinco sem reconhecer o Genitivo plural.",
            "Confundir у неё, posse de ela, com ей, Dativo de ela.",
        ],
        "Para quantidades, separe 1, 2–4 e 5+. Para ausência, procure нет; para posse, procure у + pessoa.",
    ),
    "dativo-objeto-e-impessoais": lesson_review(
        "O Dativo singular usa com frequência -у/-ю no masculino e neutro e -е no feminino em -а. Além de destinatário, aparece com gostar, precisar, idade e movimento em direção a alguém ou lugar.",
        """
Я даю книгу сестре. — Eu dou o livro para a irmã.
Мне нужно время. — Eu preciso de tempo.
Я иду к врачу. — Eu vou ao médico.
""",
        [
            "Usar сестра depois de даю; o destinatário é сестре.",
            "Confundir к врачу, direção a uma pessoa, com в врача, uma combinação inadequada.",
            "Tratar мне нравится como uma concordância comum de sujeito e verbo.",
        ],
        "Pergunte para quem, reconheça construções impessoais e observe к + Dativo. Memorize as terminações por gênero.",
    ),
    "instrumental-meio-e-tempo": lesson_review(
        "O Instrumental responde com quem? ou com o quê? e também aparece em expressões de tempo. No singular, masculinos e neutros tendem a -ом/-ем; femininos em -а tendem a -ой/-ей.",
        """
Она говорит с мамой. — Ela fala com a mãe.
Он пишет карандашом. — Ele escreve com um lápis.
Зимой мы отдыхаем. — No inverno, descansamos.
""",
        [
            "Usar мама depois de с; companhia exige мамой.",
            "Confundir карандашом, instrumento, com карандаш no Nominativo.",
            "Tratar зимой como uma forma de direção; é uma expressão fixa de tempo.",
        ],
        "Identifique companhia, instrumento ou tempo e escolha a forma do Instrumental. No plural, procure -ами/-ями.",
    ),
    "plural-nos-casos": lesson_review(
        "No plural, Dativo, Instrumental e Preposicional têm padrões relativamente regulares, enquanto o Genitivo varia bastante. O caso continua sendo decidido pela função ou pela preposição; o plural só acrescenta outra camada de forma.",
        """
Мы говорим о друзьях. — Nós falamos sobre os amigos.
Я пишу друзьям. — Eu escrevo para os amigos.
Они идут с друзьями. — Eles vão com os amigos.
""",
        [
            "Usar друзьями quando a frase exige Dativo: Я пишу друзьям.",
            "Confundir друзьях, Preposicional, com друзьям, Dativo.",
            "Supor que todo Genitivo plural termina em uma única terminação.",
        ],
        "Determine o caso antes de olhar a terminação. Fixe o trio друзьям / друзьями / друзьях e trate Genitivo plural como categoria de alta atenção.",
    ),
}


def _complete_early_module(builder):
    """Aplica as revisões somente ao resultado novo dos builders 1–8."""
    def wrapped():
        built = builder()
        for current_topic in built["topics"]:
            slug = current_topic["slug"]
            current_topic["exercises"].extend(deepcopy(EARLY_EXERCISES[slug]))
            current_topic["lesson_md"] += EARLY_LESSON_REVISIONS[slug]
        return built
    return wrapped


for _early_builder_name in (
    "build_modulo_01_alfabeto_e_primeiros_passos",
    "build_modulo_02_frases_basicas_sem_verbo_ser",
    "build_modulo_03_perguntas_e_negacao",
    "build_modulo_04_casos_primeiro_contato",
    "build_modulo_05_vocabulario_e_comunicacao_a1",
    "build_modulo_06_presente_dos_verbos",
    "build_modulo_07_vocabulario_e_comunicacao_a2",
    "build_modulo_08_casos_intermediarios",
):
    globals()[_early_builder_name] = _complete_early_module(globals()[_early_builder_name])


# ============================================================
# Expansão dos módulos 9–18: exercícios e revisão editorial
# ============================================================

INTERMEDIATE_EXTRA_EXERCISES = {
    # Módulo 9 — aspecto verbal
    "o-que-e-aspecto-verbal": [
        ex("text", "Traduza destacando o processo, sem afirmar o resultado: Eu estava lendo um artigo.",
           "я читал статью"),
        ex("quiz", 'Em "Вчера я прочитал статью до конца", o aspecto de прочитал é:',
           "perfectivo", ["perfectivo", "imperfectivo", "tempo verbal"]),
        ex("text", 'Complete: "Она ___ письмо весь вечер." (estava escrevendo — писать)',
           "писала"),
        ex("audio", "Escute e transcreva:", "я читал статью весь вечер", audio_text="я читал статью весь вечер"),
        ex("speak", "Repita em voz alta:", "я прочитал статью до конца", audio_text="я прочитал статью до конца"),
    ],
    "formando-o-perfectivo": [
        ex("text", 'Escreva o perfectivo de "смотреть" (assistir/olhar), com по-.',
           "посмотреть"),
        ex("quiz", 'Qual par mostra processo versus ação concluída?',
           "писать / написать", ["писать / написать", "писал / пишет", "пишу / писал"]),
        ex("text", 'Complete com o perfectivo: "Она ___ письмо за час." (написать)',
           "написала"),
        ex("audio", "Escute e transcreva:", "он решил задачу", audio_text="он решил задачу"),
        ex("speak", "Repita em voz alta:", "мы сделали проект", audio_text="мы сделали проект"),
    ],
    "aspecto-no-presente-e-infinitivo": [
        ex("text", "Traduza: Amanhã vou ler o livro até o fim.",
           "завтра я прочитаю книгу"),
        ex("quiz", 'Em "Я буду читать", o infinitivo читать é:',
           "imperfectivo", ["imperfectivo", "perfectivo", "passado"]),
        ex("text", 'Complete com o infinitivo de processo: "Я хочу ___ эту статью." (ler)',
           "читать"),
        ex("audio", "Escute e transcreva:", "она будет писать письмо", audio_text="она будет писать письмо"),
        ex("speak", "Repita em voz alta:", "мы прочитаем статью", audio_text="мы прочитаем статью"),
    ],
    "usando-aspecto-no-passado": [
        ex("text", "Traduza usando o imperfectivo: Ela estava escrevendo uma carta.",
           "она писала письмо"),
        ex("quiz", 'Qual frase afirma que o trabalho foi concluído?',
           "Я сделал работу.", ["Я сделал работу.", "Я делал работу.", "Я делаю работу."]),
        ex("text", 'Complete: "Когда я вошёл, он ___ письмо." (estava escrevendo — писать)',
           "писал"),
        ex("audio", "Escute e transcreva:", "я написал письмо за час", audio_text="я написал письмо за час"),
        ex("speak", "Repita em voz alta:", "мы часто читали вместе", audio_text="мы часто читали вместе"),
    ],
    "pares-comuns-de-aspecto": [
        ex("quiz", 'Qual é o perfectivo de "решать"?',
           "решить", ["решить", "решал", "решает"]),
        ex("text", "Traduza: Eu normalmente leio antes de dormir.",
           "я обычно читаю перед сном"),
        ex("audio", "Escute e transcreva:", "я решил задачу", audio_text="я решил задачу"),
        ex("speak", "Repita em voz alta:", "она сказала правду", audio_text="она сказала правду"),
    ],

    # Módulo 10 — passado, futuro e condicional
    "passado-com-genero": [
        ex("text", 'Complete no feminino: "Она ___ фильм вчера." (assistiu — смотреть)',
           "смотрела"),
        ex("quiz", 'Qual forma completa corretamente "Окно ___ само." (abriu-se, neutro)?',
           "открылось", ["открылось", "открылся", "открылась"]),
        ex("audio", "Escute e transcreva:", "мы работали весь день", audio_text="мы работали весь день"),
        ex("speak", "Repita em voz alta:", "она читала вчера", audio_text="она читала вчера"),
    ],
    "passado-dos-irregulares": [
        ex("text", 'Complete: "Они ___ прийти раньше." (puderam — мочь)',
           "могли"),
        ex("quiz", 'Qual é o passado feminino de идти?',
           "шла", ["шла", "шёл", "шли"]),
        ex("audio", "Escute e transcreva:", "она ела суп", audio_text="она ела суп"),
        ex("speak", "Repita em voz alta:", "он мог помочь", audio_text="он мог помочь"),
    ],
    "futuro-simples-e-composto": [
        ex("text", "Traduza: Eles vão ler o artigo até o fim.",
           "они прочитают статью"),
        ex("quiz", 'Complete o futuro composto: "Вы ___ работать завтра." (быть)',
           "будете", ["будете", "будешь", "будут"]),
        ex("audio", "Escute e transcreva:", "мы будем обсуждать план", audio_text="мы будем обсуждать план"),
        ex("speak", "Repita em voz alta:", "я закончу работу", audio_text="я закончу работу"),
    ],
    "negacao-no-futuro": [
        ex("text", "Traduza usando o perfectivo: Nós não terminaremos o projeto hoje.",
           "мы не закончим проект сегодня"),
        ex("quiz", 'Qual frase nega uma ação futura pontual, não uma intenção contínua?',
           "Я не подожду.", ["Я не подожду.", "Я не буду ждать.", "Я не жду."]),
        ex("text", "Traduza: Ela não conseguirá terminar o trabalho.",
           "она не закончит работу"),
        ex("audio", "Escute e transcreva:", "он не придёт завтра", audio_text="он не придёт завтра"),
        ex("speak", "Repita em voz alta:", "я не буду покупать билет", audio_text="я не буду покупать билет"),
    ],
    "modo-condicional": [
        ex("text", "Traduza: Se eu soubesse a resposta, responderia.",
           "если бы я знал ответ я бы ответил"),
        ex("quiz", 'Em "Если бы у меня было время", a forma verbal vem no:',
           "passado", ["passado", "presente", "futuro"]),
        ex("audio", "Escute e transcreva:", "я бы помог тебе", audio_text="я бы помог тебе"),
        ex("speak", "Repita em voz alta:", "мы бы поехали вместе", audio_text="мы бы поехали вместе"),
    ],

    # Módulo 11 — casos avançados
    "adjetivos-no-nominativo": [
        ex("text", 'Complete: "___ дом стоит здесь." (novo, masculino)', "новый"),
        ex("quiz", 'Qual forma concorda com "окно" no Nominativo?',
           "новое", ["новое", "новая", "новый"]),
        ex("audio", "Escute e transcreva:", "большие города интересны", audio_text="большие города интересны"),
        ex("speak", "Repita em voz alta:", "красивая улица рядом", audio_text="красивая улица рядом"),
    ],
    "adjetivos-nos-casos": [
        ex("text", 'Complete no Genitivo: "около ___ дома" (новый)', "нового"),
        ex("quiz", 'Complete no Instrumental: "Я иду с ___ другом." (новый)',
           "новым", ["новым", "нового", "новому"]),
        ex("audio", "Escute e transcreva:", "я думаю о новой работе", audio_text="я думаю о новой работе"),
        ex("speak", "Repita em voz alta:", "мы живём в старом городе", audio_text="мы живём в старом городе"),
    ],
    "pronomes-em-todos-os-casos": [
        ex("text", 'Complete no Dativo: "Я помогаю ___." (ela)', "ей"),
        ex("quiz", 'Complete: "Мы говорим о ___." (eles)',
           "них", ["них", "им", "ими"]),
        ex("audio", "Escute e transcreva:", "он говорит обо мне", audio_text="он говорит обо мне"),
        ex("speak", "Repita em voz alta:", "мы идём к нему", audio_text="мы идём к нему"),
    ],
    "oracoes-com-kotoryi": [
        ex("text", "Traduza: O livro que você lê é interessante.",
           "книга которую ты читаешь интересная"),
        ex("quiz", 'Complete no plural: "Люди, ___ работают здесь, добрые."',
           "которые", ["которые", "которая", "которое"]),
        ex("audio", "Escute e transcreva:", "женщина которая живёт рядом моя сестра", audio_text="женщина которая живёт рядом моя сестра"),
        ex("speak", "Repita em voz alta:", "я знаю человека который говорит по-русски", audio_text="я знаю человека который говорит по-русски"),
    ],
    "kotoryi-nos-casos": [
        ex("text", 'Complete no Dativo feminino: "Девушка, ___ я пишу, живёт здесь."',
           "которой"),
        ex("quiz", 'Complete no Preposicional neutro: "Озеро, о ___ я думаю, далеко."',
           "котором", ["котором", "которого", "которому"]),
        ex("audio", "Escute e transcreva:", "это книга о которой я говорил", audio_text="это книга о которой я говорил"),
        ex("speak", "Repita em voz alta:", "человек с которым я работаю мой друг", audio_text="человек с которым я работаю мой друг"),
    ],
    "adjetivos-no-plural": [
        ex("text", 'Complete no Genitivo plural: "много ___ книг" (novo)', "новых"),
        ex("quiz", 'No Acusativo de seres animados, complete: "Я вижу ___ студентов." (novo)',
           "новых", ["новых", "новые", "новыми"]),
        ex("audio", "Escute e transcreva:", "мы говорим о старых друзьях", audio_text="мы говорим о старых друзьях"),
        ex("speak", "Repita em voz alta:", "она работает с опытными врачами", audio_text="она работает с опытными врачами"),
    ],

    # Módulo 12 — verbos de movimento
    "idti-vs-khodit": [
        ex("text", "Traduza: Ele está indo ao médico agora.", "он идёт к врачу"),
        ex("quiz", 'Para "todo sábado", escolha a forma correta: "Я ___ в бассейн."',
           "хожу", ["хожу", "иду", "пойду"]),
        ex("audio", "Escute e transcreva:", "мы идём в музей сейчас", audio_text="мы идём в музей сейчас"),
        ex("speak", "Repita em voz alta:", "она ходит в бассейн по субботам", audio_text="она ходит в бассейн по субботам"),
    ],
    "ekhat-vs-ezdit": [
        ex("text", "Traduza: Eles estão indo para São Petersburgo agora, de veículo.",
           "они едут в санкт-петербург сейчас"),
        ex("quiz", 'Para uma rotina de carro, escolha: "Он ___ на работу каждый день."',
           "ездит", ["ездит", "едет", "пойдёт"]),
        ex("audio", "Escute e transcreva:", "он едет на автобусе в центр", audio_text="он едет на автобусе в центр"),
        ex("speak", "Repita em voz alta:", "мы ездим на дачу летом", audio_text="мы ездим на дачу летом"),
    ],
    "letet-vs-letat": [
        ex("text", "Traduza: O avião está voando sobre a cidade.",
           "самолёт летит над городом"),
        ex("quiz", 'Para um hábito, complete: "Я часто ___ в Турцию."',
           "летаю", ["летаю", "лечу", "летит"]),
        ex("audio", "Escute e transcreva:", "мы летим в москву сейчас", audio_text="мы летим в москву сейчас"),
        ex("speak", "Repita em voz alta:", "она часто летает в турцию", audio_text="она часто летает в турцию"),
    ],
    "plyt-vs-plavat": [
        ex("text", "Traduza: O barco está indo para a margem.",
           "лодка плывёт к берегу"),
        ex("quiz", 'Para habilidade geral, complete: "Он хорошо ___."',
           "плавает", ["плавает", "плывёт", "плыл"]),
        ex("audio", "Escute e transcreva:", "мы плывём по реке", audio_text="мы плывём по реке"),
        ex("speak", "Repita em voz alta:", "он плавает каждое утро", audio_text="он плавает каждое утро"),
    ],
    "bezhat-vs-begat": [
        ex("text", "Traduza: A criança está correndo até a mãe.",
           "ребёнок бежит к маме"),
        ex("quiz", 'Para um hábito, complete: "Она ___ по утрам."',
           "бегает", ["бегает", "бежит", "побежит"]),
        ex("audio", "Escute e transcreva:", "они бегут в парк сейчас", audio_text="они бегут в парк сейчас"),
        ex("speak", "Repita em voz alta:", "я бегаю по вечерам", audio_text="я бегаю по вечерам"),
    ],

    # Módulo 13 — comunicação B1
    "contando-historias-russo": [
        ex("text", "Traduza: Enquanto ela cozinhava, ele chegou.",
           "пока она готовила он пришёл"),
        ex("quiz", 'Qual combinação apresenta cenário + evento pontual?',
           "Я читал, когда позвонил друг.", ["Я читал, когда позвонил друг.", "Я прочитал, когда читал друг.", "Я читаю, когда позвоню друг."]),
        ex("audio", "Escute e transcreva:", "сначала он работал потом отдохнул", audio_text="сначала он работал потом отдохнул"),
        ex("speak", "Repita em voz alta:", "я шёл домой когда начался дождь", audio_text="я шёл домой когда начался дождь"),
    ],
    "opinando": [
        ex("text", "Traduza: Na minha opinião, essa decisão é importante.",
           "по-моему это важное решение"),
        ex("quiz", 'Em "Я думаю о нём", o pronome está no:',
           "Preposicional", ["Preposicional", "Dativo", "Instrumental"]),
        ex("audio", "Escute e transcreva:", "я считаю что это хорошая идея", audio_text="я считаю что это хорошая идея"),
        ex("speak", "Repita em voz alta:", "по-моему этот план лучше", audio_text="по-моему этот план лучше"),
    ],
    "falando-de-planos-russo": [
        ex("text", 'Complete: "В следующем году я ___ в Москве." (vou trabalhar)',
           "буду работать"),
        ex("quiz", 'Para um plano pontual com resultado, escolha:',
           "Я куплю билет.", ["Я куплю билет.", "Я буду покупать билет.", "Я покупаю билет."]),
        ex("audio", "Escute e transcreva:", "мы будем изучать русский", audio_text="мы будем изучать русский"),
        ex("speak", "Repita em voz alta:", "я поеду в петербург летом", audio_text="я поеду в петербург летом"),
    ],
    "pedidos-educados-b1": [
        ex("text", "Traduza: Você poderia repetir, por favor?",
           "не могли бы вы повторить пожалуйста"),
        ex("quiz", 'Complete no Dativo: "Помогите ___, пожалуйста." (eu)',
           "мне", ["мне", "меня", "мной"]),
        ex("audio", "Escute e transcreva:", "можно мне ещё воды", audio_text="можно мне ещё воды"),
        ex("speak", "Repita em voz alta:", "скажите пожалуйста как пройти", audio_text="скажите пожалуйста как пройти"),
    ],
    "expressando-gostos": [
        ex("text", "Traduza: Eu gosto de música clássica.",
           "мне нравится классическая музыка"),
        ex("quiz", 'Complete no Acusativo: "Я люблю ___ книгу." (nova)',
           "новую", ["новую", "новая", "новой"]),
        ex("audio", "Escute e transcreva:", "мне нравится этот фильм", audio_text="мне нравится этот фильм"),
        ex("speak", "Repita em voz alta:", "я предпочитаю чай а не кофе", audio_text="я предпочитаю чай а не кофе"),
    ],
    "desculpas-e-justificativas": [
        ex("text", "Traduza: Eu não podia vir.", "я не мог прийти"),
        ex("quiz", 'Qual forma indica que a pessoa não conseguiu chegar a tempo?',
           "Я не успел.", ["Я не успел.", "Я успевал.", "Я успеваю."]),
        ex("audio", "Escute e transcreva:", "к сожалению я опоздал", audio_text="к сожалению я опоздал"),
        ex("speak", "Repita em voz alta:", "извините я не смог прийти", audio_text="извините я не смог прийти"),
    ],

    # Módulo 14 — formas verbais avançadas
    "participios": [
        ex("quiz", 'Qual é o particípio ativo presente de "работать"?',
           "работающий", ["работающий", "работаемый", "работавший"]),
        ex("text", "Traduza: O documento assinado pelo diretor está na mesa.",
           "документ подписанный директором на столе"),
        ex("quiz", 'Para o resultado concluído "livro lido", escolha:',
           "прочитанная книга", ["прочитанная книга", "читаемая книга", "читающая книга"]),
        ex("audio", "Escute e transcreva:", "студент читающий книгу сидит у окна", audio_text="студент читающий книгу сидит у окна"),
        ex("speak", "Repita em voz alta:", "письмо написанное вчера лежит на столе", audio_text="письмо написанное вчера лежит на столе"),
    ],
    "gerundios-russo": [
        ex("text", 'Escreva o gerúndio perfectivo de "сделать" (tendo feito).',
           "сделав"),
        ex("quiz", 'Na frase "Прочитав книгу, он уснул", quem pratica as duas ações é:',
           "он", ["он", "книгу", "um sujeito diferente"]),
        ex("text", "Traduza: Tendo terminado o trabalho, ela foi para casa.",
           "закончив работу она пошла домой"),
        ex("audio", "Escute e transcreva:", "читая книгу он пил чай", audio_text="читая книгу он пил чай"),
        ex("speak", "Repita em voz alta:", "приехав в москву она позвонила мне", audio_text="приехав в москву она позвонила мне"),
    ],
    "participio-passivo-curto": [
        ex("quiz", 'Qual é a forma curta masculina de "написанный"?',
           "написан", ["написан", "написана", "написано"]),
        ex("text", "Traduza: As portas estão fechadas.", "двери закрыты"),
        ex("quiz", 'Complete no neutro: "Окно ___ после ремонта." (aberto)',
           "открыто", ["открыто", "открыт", "открыта"]),
        ex("audio", "Escute e transcreva:", "задача решена", audio_text="задача решена"),
        ex("speak", "Repita em voz alta:", "документы подписаны", audio_text="документы подписаны"),
    ],
    "discurso-indireto-russo": [
        ex("text", "Traduza: Ela disse que virá amanhã.",
           "она сказала что придёт завтра"),
        ex("quiz", 'Complete a pergunta indireta: "Он спросил, ___ я приду."',
           "ли", ["ли", "что", "чтобы"]),
        ex("audio", "Escute e transcreva:", "он спросил где находится вокзал", audio_text="он спросил где находится вокзал"),
        ex("speak", "Repita em voz alta:", "она попросила чтобы я подождал", audio_text="она попросила чтобы я подождал"),
    ],
    "verbos-de-citacao": [
        ex("text", "Traduza: Ela explicou por que se atrasou.",
           "она объяснила почему опоздала"),
        ex("quiz", 'Qual construção completa: "Он попросил, ___ я подождал."',
           "чтобы", ["чтобы", "ли", "что"]),
        ex("audio", "Escute e transcreva:", "он ответил что занят", audio_text="он ответил что занят"),
        ex("speak", "Repita em voz alta:", "я спросил придёшь ли ты", audio_text="я спросил придёшь ли ты"),
    ],

    # Módulo 15 — movimento prefixado
    "prefixos-chegar-e-sair": [
        ex("text", "Traduza: Nós chegamos à cidade à noite.",
           "мы приехали в город вечером"),
        ex("quiz", 'Qual verbo significa "ir embora de veículo"?',
           "уехать", ["уехать", "приехать", "въехать"]),
        ex("audio", "Escute e transcreva:", "она пришла домой поздно", audio_text="она пришла домой поздно"),
        ex("speak", "Repita em voz alta:", "он уехал из москвы утром", audio_text="он уехал из москвы утром"),
    ],
    "prefixos-entrar-e-sair": [
        ex("text", "Traduza: Ele saiu da loja.", "он вышел из магазина"),
        ex("quiz", 'Qual verbo significa "entrar de veículo"?',
           "въехать", ["въехать", "выйти", "прийти"]),
        ex("audio", "Escute e transcreva:", "машина въехала в гараж", audio_text="машина въехала в гараж"),
        ex("speak", "Repita em voz alta:", "мы вышли из здания", audio_text="мы вышли из здания"),
    ],
    "prefixo-pere": [
        ex("text", "Traduza: Ela atravessou a rua.", "она перешла улицу"),
        ex("quiz", 'Qual verbo significa "aproximar-se"?',
           "подойти", ["подойти", "отойти", "перейти"]),
        ex("audio", "Escute e transcreva:", "он отошёл от окна", audio_text="он отошёл от окна"),
        ex("speak", "Repita em voz alta:", "я зайду к другу вечером", audio_text="я зайду к другу вечером"),
    ],
    "pares-imperfectivos-de-movimento": [
        ex("text", "Traduza: Ela chega frequentemente às nove.",
           "она часто приходит в девять"),
        ex("quiz", 'Qual é o imperfectivo de "выйти"?',
           "выходить", ["выходить", "выйти", "въехать"]),
        ex("audio", "Escute e transcreva:", "он обычно приезжает рано", audio_text="он обычно приезжает рано"),
        ex("speak", "Repita em voz alta:", "мы часто переходим эту улицу", audio_text="мы часто переходим эту улицу"),
    ],
    "movimento-prefixado-e-casos": [
        ex("text", 'Complete: "Он вошёл в ___ комнату." (sala, Acusativo)', "комнату"),
        ex("quiz", 'Em "Она отошла от друга", a forma de "друг" está no:',
           "Genitivo", ["Genitivo", "Dativo", "Acusativo"]),
        ex("audio", "Escute e transcreva:", "она подошла к окну", audio_text="она подошла к окну"),
        ex("speak", "Repita em voz alta:", "мы выехали из города", audio_text="мы выехали из города"),
    ],

    # Módulo 16 — imperativo e aspecto
    "modo-imperativo": [
        ex("text", "Traduza no formal: Fale mais devagar.", "говорите медленнее"),
        ex("quiz", 'Qual é o imperativo informal de "писать"?',
           "пиши", ["пиши", "пишите", "пишешь"]),
        ex("audio", "Escute e transcreva:", "идите прямо", audio_text="идите прямо"),
        ex("speak", "Repita em voz alta:", "открой окно", audio_text="открой окно"),
    ],
    "imperativo-negativo": [
        ex("text", "Traduza: Não corra!", "не беги"),
        ex("quiz", 'Complete a proibição formal: "Не ___ дверь!" (abrir — открывать)',
           "открывайте", ["открывайте", "откройте", "открываете"]),
        ex("audio", "Escute e transcreva:", "не открывайте дверь", audio_text="не открывайте дверь"),
        ex("speak", "Repita em voz alta:", "не забудь паспорт", audio_text="не забудь паспорт"),
    ],
    "aspecto-no-imperativo": [
        ex("text", "Traduza: Termine o relatório!", "закончи отчёт"),
        ex("quiz", 'Para uma instrução repetida, escolha:',
           "Звони мне каждую неделю.", ["Звони мне каждую неделю.", "Позвони мне один раз.", "Не позвони мне."]),
        ex("audio", "Escute e transcreva:", "прочитай эту статью", audio_text="прочитай эту статью"),
        ex("speak", "Repita em voz alta:", "не опаздывай на работу", audio_text="не опаздывай на работу"),
    ],
    "imperativo-formal": [
        ex("text", "Traduza: Aguarde, por favor.", "подождите пожалуйста"),
        ex("quiz", 'Em "Дайте мне воды", o caso de воды é:',
           "Genitivo de quantidade", ["Genitivo de quantidade", "Acusativo", "Dativo"]),
        ex("audio", "Escute e transcreva:", "помогите мне пожалуйста", audio_text="помогите мне пожалуйста"),
        ex("speak", "Repita em voz alta:", "скажите пожалуйста ещё раз", audio_text="скажите пожалуйста ещё раз"),
    ],
    "pedidos-com-imperativo": [
        ex("text", "Traduza: Mostre-me o caminho.", "покажите мне дорогу"),
        ex("quiz", 'Em "Принеси мне чашку чая", мне está no:',
           "Dativo", ["Dativo", "Acusativo", "Instrumental"]),
        ex("audio", "Escute e transcreva:", "расскажи мне о своей поездке", audio_text="расскажи мне о своей поездке"),
        ex("speak", "Repita em voz alta:", "дайте мне пожалуйста счёт", audio_text="дайте мне пожалуйста счёт"),
    ],

    # Módulo 17 — comparação, pronomes e reflexivos
    "comparativo-e-superlativo-russo": [
        ex("text", 'Complete: "Этот тест ___, чем предыдущий." (mais fácil)', "легче"),
        ex("quiz", 'Qual é o superlativo feminino de "красивый"?',
           "самая красивая", ["самая красивая", "самый красивый", "красивее"]),
        ex("audio", "Escute e transcreva:", "этот вариант лучше", audio_text="этот вариант лучше"),
        ex("speak", "Repita em voz alta:", "это самый высокий дом", audio_text="это самый высокий дом"),
    ],
    "comparacao-com-chem": [
        ex("text", "Traduza: Anna é mais velha do que Maria.",
           "анна старше чем мария"),
        ex("quiz", 'Qual frase usa o Genitivo na comparação?',
           "Он младше меня.", ["Он младше меня.", "Он младше я.", "Он младше чем."]),
        ex("audio", "Escute e transcreva:", "этот фильм интереснее чем тот", audio_text="этот фильм интереснее чем тот"),
        ex("speak", "Repita em voz alta:", "она такая же высокая как я", audio_text="она такая же высокая как я"),
    ],
    "adjetivos-forma-curta": [
        ex("text", "Traduza: Eles estão prontos.", "они готовы"),
        ex("quiz", 'Complete no neutro: "Окно ___, можно войти." (aberto)',
           "открыто", ["открыто", "открыт", "открыта"]),
        ex("audio", "Escute e transcreva:", "мы готовы начать", audio_text="мы готовы начать"),
        ex("speak", "Repita em voz alta:", "она уверена в ответе", audio_text="она уверена в ответе"),
    ],
    "verbos-reflexivos": [
        ex("text", "Traduza: Você estuda na universidade.",
           "ты учишься в университете"),
        ex("quiz", 'Qual verbo significa "encontrar-se / encontrar-se com alguém"?',
           "встречаться", ["встречаться", "встречать", "встречу"]),
        ex("audio", "Escute e transcreva:", "мы встречаемся вечером", audio_text="мы встречаемся вечером"),
        ex("speak", "Repita em voz alta:", "он интересуется музыкой", audio_text="он интересуется музыкой"),
    ],
    "reflexivos-na-rotina": [
        ex("text", 'Complete: "После душа я ___." (visto-me)', "одеваюсь"),
        ex("quiz", 'Qual forma descreve uma rotina?',
           "Я просыпаюсь в семь.", ["Я просыпаюсь в семь.", "Я проснусь один раз.", "Я разбудил друга."]),
        ex("audio", "Escute e transcreva:", "она встаёт рано и умывается", audio_text="она встаёт рано и умывается"),
        ex("speak", "Repita em voz alta:", "мы ложимся спать в одиннадцать", audio_text="мы ложимся спать в одиннадцать"),
    ],

    # Módulo 18 — vocabulário e expressões B2
    "expressoes-do-dia-a-dia-russo": [
        ex("text", "Traduza: Para mim tanto faz.", "мне всё равно"),
        ex("quiz", 'Em "У меня нет времени", a forma времени está no:',
           "Genitivo", ["Genitivo", "Dativo", "Instrumental"]),
        ex("audio", "Escute e transcreva:", "я с удовольствием помогу", audio_text="я с удовольствием помогу"),
        ex("speak", "Repita em voz alta:", "мне надо купить билет", audio_text="мне надо купить билет"),
    ],
    "colocacoes-com-casos": [
        ex("text", 'Complete no Instrumental: "Он гордится ___." (filho)', "сыном"),
        ex("quiz", 'Qual verbo exige Dativo?',
           "помогать", ["помогать", "бояться", "гордиться"]),
        ex("audio", "Escute e transcreva:", "я жду автобуса", audio_text="я жду автобуса"),
        ex("speak", "Repita em voz alta:", "она гордится сыном", audio_text="она гордится сыном"),
    ],
    "verbos-com-prefixo": [
        ex("text", "Traduza: Eu entendi imediatamente.", "я сразу понял"),
        ex("quiz", 'Qual é o imperfectivo correspondente a "позвонить"?',
           "звонить", ["звонить", "позвоню", "звонил"]),
        ex("audio", "Escute e transcreva:", "он прочитал письмо", audio_text="он прочитал письмо"),
        ex("speak", "Repita em voz alta:", "я сделаю это сегодня", audio_text="я сделаю это сегодня"),
    ],
    "expressoes-de-tempo": [
        ex("text", 'Complete: "Мы встретимся ___ час." (daqui a uma hora)', "через"),
        ex("quiz", 'Em "в мае", maio está no:',
           "Preposicional", ["Preposicional", "Acusativo", "Genitivo"]),
        ex("audio", "Escute e transcreva:", "я уехал два года назад", audio_text="я уехал два года назад"),
        ex("speak", "Repita em voz alta:", "мы работаем с утра до вечера", audio_text="мы работаем с утра до вечера"),
    ],
    "frases-prontas": [
        ex("text", "Traduza: Infelizmente, não posso ir.",
           "к сожалению я не могу прийти"),
        ex("quiz", 'O que significa "Кстати"?',
           "Aliás", ["Aliás", "Infelizmente", "Na minha opinião"]),
        ex("audio", "Escute e transcreva:", "всё хорошо", audio_text="всё хорошо"),
        ex("speak", "Repita em voz alta:", "на здоровье", audio_text="на здоровье"),
    ],
    "expressoes-idiomaticas-russo": [
        ex("text", "Traduza: Ela está nas nuvens.", "она витает в облаках"),
        ex("quiz", 'Qual expressão significa "guardar bem na memória"?',
           "зарубить на носу", ["зарубить на носу", "бить баклуши", "витать в облаках"]),
        ex("audio", "Escute e transcreva:", "не бей баклуши", audio_text="не бей баклуши"),
        ex("speak", "Repita em voz alta:", "он бежит домой сломя голову", audio_text="он бежит домой сломя голову"),
    ],
}


def lesson_revision(explanation, table, examples, common_error, summary):
    return f"""## Aprofundamento guiado

{explanation}

### Quadro de decisão

{table}

### Exemplos em contexto

```text
{examples}
```

### Erro comum

{common_error}

### Resumo

{summary}""".strip()


INTERMEDIATE_LESSON_REVISIONS = {
    # Módulo 9 — aspecto verbal
    "o-que-e-aspecto-verbal": lesson_revision(
        "Aspecto não informa se a ação ocorreu ontem ou amanhã; ele enquadra a ação por dentro. O imperfectivo apresenta processo, hábito ou repetição. O perfectivo apresenta uma ação vista como unidade, normalmente com limite ou resultado. A tradução portuguesa pode ser igual nos dois casos, por isso o contexto é decisivo.",
        """| Pergunta do contexto | Imperfectivo | Perfectivo |
|---|---|---|
| O foco é o desenvolvimento? | читать | — |
| O foco é o resultado alcançado? | — | прочитать |
| A ação se repete? | читать | pode ocorrer com prefixo, se cada ocorrência for vista como concluída |""",
        """Вчера я читал статью, когда ты позвонил. — Ontem eu estava lendo um artigo quando você ligou.
Вчера я прочитал статью до конца. — Ontem li o artigo até o fim.
Я часто готовлю дома. — Eu cozinho em casa com frequência.""",
        "Não escolha o perfectivo apenas porque a frase está no passado: читал e прочитал são ambos passado, mas só o segundo afirma a conclusão. Também não trate imperfectivo como “incompleto” em todos os sentidos; ele pode relatar um fato sem destacar o resultado.",
        "Primeiro pergunte qual é o foco, processo/repetição ou limite/resultado; só depois escolha o par de aspecto. O tempo verbal e o aspecto são decisões independentes.",
    ),
    "formando-o-perfectivo": lesson_revision(
        "O perfectivo não é formado por uma regra mecânica única. Prefixos como про-, с-, на- e по- são frequentes, mas podem alterar o sentido lexical; pares como решать/решить e покупать/купить exigem memorização. Aprenda o verbo em par e observe também a conjugação resultante.",
        """| Relação | Imperfectivo | Perfectivo | Foco comum |
|---|---|---|---|
| Prefixo | читать | прочитать | concluir a leitura |
| Prefixo | делать | сделать | concluir/fazer |
| Alternância | решать | решить | chegar à solução |
| Par lexical | покупать | купить | efetuar a compra |""",
        """Я решал задачу час. — Eu fiquei resolvendo o problema por uma hora.
Я решил задачу. — Eu resolvi o problema, chegando à solução.
Она написала письмо за час. — Ela escreveu a carta em uma hora, concluindo-a.""",
        "Não se deve acrescentar qualquer prefixo para “fabricar” um perfectivo. прочитать é o par de читать, mas *порешать não significa simplesmente “resolver” como решил; consulte o par lexical e o sentido do prefixo.",
        "Memorize infinitivo imperfectivo + infinitivo perfectivo + uma frase-modelo. Prefixo ajuda, mas o par e o significado precisam ser confirmados juntos.",
    ),
    "aspecto-no-presente-e-infinitivo": lesson_revision(
        "O presente genuíno é formado pelo imperfectivo: Я читаю significa “leio/estou lendo”. Quando um perfectivo recebe uma terminação de pessoa, a leitura normal passa a ser futuro simples: Я прочитаю significa “vou ler até o fim”. No infinitivo, a escolha depende do objetivo de хотеть, надо, можно e outras construções.",
        """| Estrutura | Aspecto | Sentido |
|---|---|---|
| Я читаю | imperfectivo | leio/estou lendo agora |
| Я прочитаю | perfectivo | lerei e terminarei |
| Я хочу читать | imperfectivo | quero ler, foco na atividade |
| Я хочу прочитать | perfectivo | quero ler até o fim |""",
        """Сейчас я читаю книгу. — Agora estou lendo um livro.
Завтра я прочитаю книгу. — Amanhã lerei o livro até o fim.
Мне надо читать больше. — Preciso ler mais, como hábito/atividade.""",
        "Confundir прочитаю com presente é o erro clássico. A forma parece uma conjugação de presente, mas um verbo perfectivo não tem presente real; nessa forma ele projeta a ação para o futuro.",
        "No presente, procure o imperfectivo. No infinitivo, pergunte se o falante quer destacar a atividade ou a conclusão e escolha читать ou прочитать.",
    ),
    "usando-aspecto-no-passado": lesson_revision(
        "No passado, os dois aspectos são possíveis. O imperfectivo constrói o pano de fundo, uma ação em curso ou um hábito; o perfectivo fecha um evento, apresenta uma mudança ou entrega um resultado. Em narrativas, essa alternância organiza a sequência sem exigir muitas palavras extras.",
        """| Função na narrativa | Forma típica | Exemplo |
|---|---|---|
| Cenário/processo | imperfectivo | Я читал письмо |
| Evento que interrompe | perfectivo | Друг позвонил |
| Resultado alcançado | perfectivo | Я написал письмо |
| Repetição/hábito passado | imperfectivo | Я часто читал |""",
        """Я писал письмо, когда зазвонил телефон. — Eu estava escrevendo quando o telefone tocou.
Я написал письмо и отправил его. — Escrevi a carta e a enviei.
В детстве я часто читал. — Na infância eu lia com frequência.""",
        "Não traduza automaticamente todo perfectivo por “uma vez” nem todo imperfectivo por “não terminou”. O contexto pode apresentar uma sequência de eventos perfectivos ou um fato imperfectivo sem interesse pelo limite.",
        "Use imperfectivo para o filme da ação e perfectivo para o corte que marca o evento ou o resultado. Depois confira gênero e número da forma passada.",
    ),
    "pares-comuns-de-aspecto": lesson_revision(
        "Pares de aspecto funcionam como vocabulário de alta frequência, e alguns são supletivos: говорить/сказать não compartilha uma raiz transparente. A melhor prática é associar cada par a um contraste de contexto, não a uma tradução isolada.",
        """| Imperfectivo | Perfectivo | Contraste |
|---|---|---|
| читать | прочитать | ler / ler até o fim |
| делать | сделать | fazer / concluir |
| писать | написать | escrever / terminar de escrever |
| говорить | сказать | falar / dizer uma vez |
| решать | решить | resolver em processo / chegar à solução |""",
        """Что ты делаешь? — O que você está fazendo?
Я сделал домашнее задание. — Fiz o dever de casa.
Она сказала правду. — Ela disse a verdade, como ato pontual.""",
        "Usar a forma presente de um par como se fosse o perfectivo (“решает” para “resolveu”) mistura tempo, pessoa e aspecto. Compare infinitivos primeiro e só então flexione.",
        "Construa um pequeno parágrafo por contraste: processo com imperfectivo, resultado com perfectivo. Releia até a escolha soar ligada ao contexto, não à tradução literal.",
    ),

    # Módulo 10 — passado, futuro e condicional
    "passado-com-genero": lesson_revision(
        "No passado russo, a terminação concorda com o gênero do sujeito no singular e com o número no plural. A pessoa “eu” não determina sozinha a forma: я pode produzir читал ou читала conforme quem fala. O particípio passado termina em -л/-ла/-ло/-ли, com ajustes nos verbos irregulares.",
        """| Sujeito | Terminação | Exemplo |
|---|---|---|
| он / я masculino | -л | он читал |
| она / я feminino | -ла | она читала |
| оно | -ло | окно открылось |
| мы, вы, они | -ли | они читали |""",
        """Я читала книгу. — Eu, mulher, lia/estava lendo o livro.
Он работал вчера. — Ele trabalhou ontem.
Окно открылось само. — A janela se abriu sozinha.""",
        "Não use -л com todo sujeito singular. “Eu” não é automaticamente masculino; e um sujeito neutro como окно pede -ло. Identifique gênero e número antes de escolher a terminação.",
        "Encontre o sujeito, determine gênero/número e só então forme o passado. No plural, abandone a distinção de gênero e use -ли.",
    ),
    "passado-dos-irregulares": lesson_revision(
        "Os verbos идти, есть e мочь conservam formas históricas no passado. A irregularidade é mais visível no masculino singular (шёл, ел, мог), enquanto o feminino e o plural seguem padrões próprios. O caso do destino continua separado da forma verbal: идти домой não flexiona домой como um substantivo comum.",
        """| Infinitivo | Masc. | Fem. | Plural |
|---|---|---|---|
| идти | шёл | шла | шли |
| есть | ел | ела | ели |
| мочь | мог | могла | могли |
| жить | жил | жила | жили |""",
        """Она шла домой. — Ela ia para casa.
Мы ели суп. — Nós comemos sopa.
Он мог помочь. — Ele podia/conseguiu ajudar, conforme o contexto.""",
        "Não acrescente -л mecanicamente a идти (*идл). Também não confunda мог, capacidade/possibilidade passada, com смог, resultado de conseguir fazer algo em uma situação específica.",
        "Memorize o trio masculino/feminino/plural dos verbos frequentes e use o contexto para distinguir мочь de смочь.",
    ),
    "futuro-simples-e-composto": lesson_revision(
        "O russo distribui o futuro entre aspecto e estrutura. O perfectivo forma o futuro simples com terminações pessoais; o imperfectivo usa o futuro de быть + infinitivo. A diferença não é apenas duração: ela também separa resultado planejado de atividade em andamento.",
        """| Verbo | Construção | Exemplo |
|---|---|---|
| perfectivo прочитать | forma pessoal | Я прочитаю книгу |
| imperfectivo читать | буду + infinitivo | Я буду читать книгу |
| imperfectivo работать | будете + infinitivo | Вы будете работать |
| быть | буду, будешь... | Мы будем дома |""",
        """Я прочитаю статью вечером. — Lerei o artigo até o fim à noite.
Я буду читать статью вечером. — Ficarei lendo/estarei lendo o artigo à noite.
Они будут обсуждать план. — Eles discutirão o plano como atividade.""",
        "Буду купить é impossível: o auxiliar exige infinitivo imperfectivo. Para resultado, use o perfectivo diretamente, como куплю ou прочитаю.",
        "Classifique o infinitivo por aspecto. Perfectivo recebe a conjugação do futuro simples; imperfectivo recebe a forma correta de быть + infinitivo.",
    ),
    "negacao-no-futuro": lesson_revision(
        "A negação deixa a escolha de aspecto especialmente visível. не буду + imperfectivo nega intenção ou participação numa atividade; не + perfectivo nega a ocorrência ou o resultado de um evento específico. O contexto e marcadores como сегодня, завтра e до конца orientam a escolha.",
        """| Ideia | Forma | Exemplo |
|---|---|---|
| Não vou realizar a atividade | не буду + imperfectivo | Я не буду читать |
| O resultado não acontecerá | не + perfectivo | Я не прочитаю это |
| Evento pontual não ocorrerá | perfectivo negativo | Он не придёт |
| Falta de capacidade no processo | не мог | Я не мог прийти |""",
        """Я не буду покупать билет. — Não vou comprar/ficar comprando o bilhete.
Я не куплю билет. — Não comprarei o bilhete, decisão sobre o resultado.
Он не придёт завтра. — Ele não virá amanhã.""",
        "Tratar не буду читать e не прочитаю como sinônimos apaga a intenção versus resultado. O mesmo verbo pode mudar de aspecto sem que a tradução portuguesa mostre a diferença.",
        "Pergunte se a negação recai sobre a atividade planejada ou sobre um evento que deveria ocorrer. Escolha o aspecto antes de conjugar.",
    ),
    "modo-condicional": lesson_revision(
        "O condicional combina uma forma passada com a partícula бы. A forma passada ainda concorda com gênero e número, mas não marca tempo hipotético por si só; a oração com если e o contexto informam a condição. бы é uma partícula móvel, embora algumas posições sejam mais naturais.",
        """| Elemento | Função | Exemplo |
|---|---|---|
| если бы | introduz condição | Если бы я знал |
| passado | forma do verbo | я знал / она знала |
| бы | consequência hipotética | я бы ответил |
| у меня было | posse/estado | У меня было бы время |""",
        """Если бы я знал ответ, я бы ответил. — Se eu soubesse a resposta, responderia.
Она бы пришла, если бы могла. — Ela viria se pudesse.
Я хотел бы поговорить. — Eu gostaria de conversar.""",
        "Não conjugue бы como se fosse um verbo e não transforme automaticamente toda oração em passado factual. Em я бы помог a ajuda é hipotética, não uma afirmação de que já ajudei.",
        "Forme o verbo no passado, posicione бы junto da oração relevante e deixe a conjunção/contexto indicar a hipótese.",
    ),

    # Módulo 11 — casos avançados
    "adjetivos-no-nominativo": lesson_revision(
        "No Nominativo, o adjetivo acompanha o substantivo que funciona como sujeito ou predicativo nominal. Antes de escolher a terminação, identifique gênero e suavidade da base: -ый/-ой/-ий, -ая/-яя, -ое/-ее e -ые/-ие são famílias, não terminações intercambiáveis.",
        """| Substantivo | Adjetivo | Exemplo |
|---|---|---|
| masc. дом | -ый/-ой/-ий | новый дом |
| fem. книга | -ая/-яя | новая книга |
| neutro окно | -ое/-ее | новое окно |
| plural дома | -ые/-ие | новые дома |""",
        """Новый дом рядом. — A casa nova está perto.
Новая книга интересная. — O livro novo é interessante.
Новые города большие. — As cidades novas são grandes.""",
        "Não concorde com a tradução portuguesa, que pode omitir gênero, nem use nova com дом. O gênero do substantivo russo é gramatical e precisa ser aprendido junto ao vocabulário.",
        "Ache o substantivo, determine gênero/número e depois faça o adjetivo concordar no caso exigido pela função da frase.",
    ),
    "adjetivos-nos-casos": lesson_revision(
        "A terminação do adjetivo é uma segunda pista do caso: o substantivo e o adjetivo devem caminhar juntos. O masculino singular mostra bem a oposição novo: новый, нового, новому, новым, новом; o feminino frequentemente neutraliza várias oposições em -ой.",
        """| Caso | Masc. новый | Fem. новая | Exemplo |
|---|---|---|---|
| Genitivo | нового | новой | около нового дома |
| Dativo | новому | новой | к новой школе |
| Acusativo | новый/нового | новую | вижу новую книгу |
| Instrumental | новым | новой | с новым другом |
| Preposicional | новом | новой | о новой работе |""",
        """Я вижу новый дом. — Vejo uma casa nova.
Он живёт в новом доме. — Ele mora numa casa nova.
Она говорит о новой работе. — Ela fala sobre o trabalho novo.""",
        "Escolher a forma pelo som do adjetivo isolado é arriscado. Em в новом доме, tanto в quanto a ideia de localização pedem Preposicional; em вижу новый дом, o objeto inanimado mantém a forma do Nominativo.",
        "Determine preposição/função e animacidade, flexione o substantivo e faça o adjetivo repetir o mesmo gênero, número e caso.",
    ),
    "pronomes-em-todos-os-casos": lesson_revision(
        "Pronomes pessoais não são apenas substantivos com terminações regulares; muitos têm raízes próprias. Organize-os por função: меня/тебя/его... cobre Genitivo e Acusativo, мне/тебе/ему... cobre Dativo, e с/о/к revelam Instrumental, Preposicional ou Dativo.",
        """| Função | я | ты | он | она |
|---|---|---|---|---|
| Gen./Acus. | меня | тебя | его | её |
| Dativo | мне | тебе | ему | ей |
| Instrumental | мной | тобой | им | ей |
| Preposicional | обо мне | о тебе | о нём | о ней |""",
        """Я говорю с тобой. — Eu falo com você.
Он думает обо мне. — Ele pensa em mim.
Она идёт к нам. — Ela vem até nós.""",
        "Não escolha entre мне e меня pela tradução “me”. Preposição e função decidem: помочь мне pede Dativo, enquanto видеть меня pede Acusativo.",
        "Memorize os pronomes em blocos de caso e teste cada frase com a pergunta para quem?, quem/o quê? ou sobre/com quem?.",
    ),
    "oracoes-com-kotoryi": lesson_revision(
        "Который concorda em gênero e número com o antecedente, mas o caso depende da função que ele desempenha na oração relativa. Em Мужчина, который читает, o relativo é sujeito; em книгу, которую я читаю, é objeto e recebe Acusativo feminino.",
        """| Antecedente | Sujeito relativo | Objeto relativo |
|---|---|---|
| мужчина | который | которого/который |
| женщина | которая | которую |
| окно | которое | которое |
| люди | которые | которых/которые |""",
        """Женщина, которая работает здесь, — врач. — A mulher que trabalha aqui é médica.
Книга, которую ты читаешь, интересная. — O livro que você lê é interessante.
Люди, которые живут здесь, добрые. — As pessoas que vivem aqui são gentis.""",
        "Não basta olhar o gênero do antecedente: em которого я знаю, o relativo é objeto, por isso está no caso oblíquo. Separe antecedente e função dentro da oração relativa.",
        "Concorde primeiro com gênero/número; depois pergunte qual papel который exerce na oração e aplique o caso.",
    ),
    "kotoryi-nos-casos": lesson_revision(
        "Quando a oração relativa contém uma preposição ou um verbo que rege caso, который declina. O antecedente pode estar no Nominativo, enquanto o relativo está no Dativo, Instrumental ou Preposicional; as duas funções não precisam coincidir.",
        """| Preposição/função | Forma masc./neutro | Forma fem. | Exemplo |
|---|---|---|---|
| с, companhia | с которым | с которой | друг, с которым я работаю |
| о, assunto | о котором | о которой | книга, о которой говорю |
| к/escrever para | которому | которой | человек, которому пишу |
| objeto | которого/который | которую | дом, который вижу |""",
        """Друг, с которым я иду, — русский. — O amigo com quem vou é russo.
Книга, о которой я говорил, новая. — O livro sobre o qual falei é novo.
Девушка, которой я пишу, живёт здесь. — A moça para quem escrevo mora aqui.""",
        "Confundir o caso do antecedente com o caso do relativo produz formas como *с который. A preposição s exige Instrumental: с которым, с которой.",
        "Identifique o antecedente para gênero/número, identifique o regente dentro da relativa para o caso e combine as duas informações.",
    ),
    "adjetivos-no-plural": lesson_revision(
        "No plural, o gênero deixa de distinguir a forma do adjetivo, mas o caso continua visível. A animacidade é decisiva no Acusativo: objetos inanimados se aproximam do Nominativo; seres animados se aproximam do Genitivo plural.",
        """| Caso | Terminação comum | Exemplo |
|---|---|---|
| Nominativo | -ые/-ие | новые дома |
| Genitivo | -ых/-их | новых домов |
| Dativo | -ым/-им | новым домам |
| Acusativo | -ые/-ых | новые дома / новых студентов |
| Instrumental | -ыми/-ими | новыми домами |
| Preposicional | -ых/-их | новых домах |""",
        """Я вижу новые дома. — Vejo casas novas.
Я вижу новых студентов. — Vejo estudantes novos.
Мы говорим о старых друзьях. — Falamos sobre velhos amigos.""",
        "Usar новые para qualquer objeto plural ignora a animacidade: Я вижу новых студентов, mas Я вижу новые дома. O caso é o mesmo, a forma muda pela animacidade.",
        "No plural, determine o caso e depois verifique se o Acusativo envolve pessoas/animais. Nos outros casos, use a série regular do quadro.",
    ),

    # Módulo 12 — verbos de movimento
    "idti-vs-khodit": lesson_revision(
        "Идти e ходить formam o par de movimento a pé. Ambos são imperfectivos, mas codificam a configuração do deslocamento: идти aponta para uma trajetória única em curso; ходить cobre ida e volta, repetição, percurso habitual ou habilidade geral.",
        """| Situação | Verbo | Exemplo |
|---|---|---|
| agora, direção determinada | идти | Я иду в школу |
| hábito/ida e volta | ходить | Я хожу в школу |
| habilidade | ходить | Ребёнок уже ходит |
| destino de pessoa | идти + к + Dativo | иду к врачу |""",
        """Я иду к врачу сейчас. — Estou indo ao médico agora.
Я хожу в бассейн по субботам. — Vou à piscina aos sábados.
Мы ходили по городу весь день. — Passeamos pela cidade o dia todo.""",
        "A oposição não é simplesmente presente versus passado, nem perfectivo versus imperfectivo. No passado, шёл ainda é direcional e ходил pode ser habitual ou de ida e volta.",
        "Visualize uma seta única para идти e um trajeto repetido/aberto para ходить; depois escolha o caso do destino, como к врачу ou в школу.",
    ),
    "ekhat-vs-ezdit": lesson_revision(
        "Ехать e ездить aplicam a mesma oposição quando o deslocamento é feito em veículo. A conjugação muda bastante, por isso memorize as formas ед- e езд- junto do contexto, não apenas os infinitivos.",
        """| Situação | Verbo | Primeira pessoa |
|---|---|---|
| indo agora em uma direção | ехать | я еду |
| hábito/viagens recorrentes | ездить | я езжу |
| terceira pessoa agora | едет | — |
| terceira pessoa habitual | ездит | — |""",
        """Я еду в Москву сейчас. — Estou indo a Moscou agora.
Я езжу на работу на машине. — Vou ao trabalho de carro regularmente.
Мы ездили на дачу летом. — Íamos à casa de campo no verão.""",
        "Confundir еду e езжу muda a configuração do movimento. Também não traduza “de carro” como destino: на машине é Instrumental de meio, enquanto на работу é direção.",
        "Pergunte se há uma viagem única em curso ou um padrão recorrente; em seguida confira a forma conjugada e a preposição do destino/meio.",
    ),
    "letet-vs-letat": lesson_revision(
        "Лететь e летать descrevem movimento aéreo com a mesma oposição direcional. O avião que está em uma rota agora летит; a pessoa que viaja frequentemente ou sabe voar летает. A escolha do destino ainda aciona Acusativo com в.",
        """| Contexto | Verbo | Exemplo |
|---|---|---|
| voo em curso, uma rota | лететь | Самолёт летит в Москву |
| hábito/frequência | летать | Я часто летаю в Россию |
| destino | в + Acusativo | в Москву |
| sobre algo | над + Instrumental | над городом |""",
        """Самолёт летит над городом. — O avião voa sobre a cidade.
Мы летим в Москву сейчас. — Estamos voando para Moscou agora.
Она часто летает в Турцию. — Ela voa frequentemente para a Turquia.""",
        "A terminação do infinitivo não decide tudo e não é seguro decorar “-ть = agora, -ать = hábito” como regra universal. Use situação e conjugação: лечу/летаю também precisam ser reconhecidos.",
        "Marque a rota única ou a recorrência, então flexione лететь/летать e aplique o caso exigido pela preposição.",
    ),
    "plyt-vs-plavat": lesson_revision(
        "Плыть e плавать distinguem uma travessia ou direção em curso de natação, navegação e habilidade recorrentes. O tipo de água não é o critério principal; a perspectiva do movimento é. A preposição к leva Dativo, e по pode marcar percurso.",
        """| Situação | Verbo | Exemplo |
|---|---|---|
| indo agora para uma margem | плыть | Я плыву к берегу |
| sabe nadar | плавать | Он хорошо плавает |
| percurso na água | плыть/плавать + по | плывём по реке |
| repetição | плавать | Она плавает каждое утро |""",
        """Лодка плывёт к берегу. — O barco vai para a margem.
Он хорошо плавает. — Ele nada bem.
Мы плывём по реке. — Estamos navegando pelo rio.""",
        "Usar плыть para habilidade geral soa como uma única travessia. O contrário também falha: плавать não marca automaticamente uma direção momentânea.",
        "Decida se há uma seta momentânea ou um hábito/habilidade e depois confirme к берегу, по реке ou outra construção espacial.",
    ),
    "bezhat-vs-begat": lesson_revision(
        "Бежать e бегать fecham o conjunto básico de movimento: correr agora em uma direção versus correr habitualmente, de um lado para outro ou como habilidade. O prefixo pode criar uma leitura perfectiva diferente, como побежать, portanto a oposição deve ser lida dentro da frase.",
        """| Situação | Verbo | Exemplo |
|---|---|---|
| correndo agora para um destino | бежать | Я бегу в парк |
| hábito | бегать | Я бегаю по утрам |
| direção a uma pessoa | к + Dativo | бежит к маме |
| movimento em percurso | по + Dativo | бегает по стадиону |""",
        """Ребёнок бежит к маме. — A criança corre até a mãe.
Они бегут в парк сейчас. — Eles estão correndo para o parque agora.
Я бегаю по вечерам. — Corro à noite regularmente.""",
        "Não confunda o par de movimento com o aspecto de побежать/побегать. Um prefixo pode mudar a estrutura aspectual, enquanto бежать/бегать sem prefixo descreve direção ou repetição.",
        "Escolha a direção em curso ou a recorrência, observe o destino e só depois avalie se há algum prefixo que acrescenta limite ao evento.",
    ),

    # Módulo 13 — comunicação B1
    "contando-historias-russo": lesson_revision(
        "Uma narrativa natural alterna planos. O imperfectivo abre o cenário, descreve o que estava acontecendo ou cria uma rotina; o perfectivo introduz eventos delimitados e mudanças. A conjunção quando não determina sozinha o aspecto: a relação temporal e o foco determinam.",
        """| Camada narrativa | Aspecto | Exemplo |
|---|---|---|
| pano de fundo | imperfectivo | Я шёл домой |
| evento súbito | perfectivo | начался дождь |
| sequência concluída | perfectivo | он пришёл и сел |
| hábito | imperfectivo | она часто готовила |""",
        """Я шёл домой, когда начался дождь. — Eu ia para casa quando começou a chover.
Сначала он работал, потом отдохнул. — Primeiro trabalhou, depois descansou.
Пока она готовила, он пришёл. — Enquanto ela cozinhava, ele chegou.""",
        "Usar perfectivo nos dois verbos pode apagar o pano de fundo; usar imperfectivo nos dois pode não marcar a mudança. Faça a pergunta “o que já estava em curso?” antes de conjugar.",
        "Monte a história em duas camadas: cenário imperfectivo + evento perfectivo, sem esquecer gênero do passado e casos dos objetos.",
    ),
    "opinando": lesson_revision(
        "Opiniões podem ser apresentadas como pensamento, avaliação ou comentário. Я думаю о + Preposicional significa pensar sobre alguém/algo; Я думаю, что introduz uma proposição. Essa diferença evita escolher о нём quando o que vem depois é uma oração inteira.",
        """| Estrutura | Uso | Exemplo |
|---|---|---|
| Я думаю, что... | opinião proposicional | Я думаю, что это важно |
| По-моему,... | opinião marcada | По-моему, план хороший |
| Я считаю, что... | avaliação | Я считаю, что он прав |
| думать о + Prep. | pensar sobre | Я думаю о нём |""",
        """По-моему, этот план лучше. — Na minha opinião, este plano é melhor.
Я думаю о нём хорошо. — Penso bem dele.
Я считаю, что это хорошая идея. — Considero que é uma boa ideia.""",
        "Não use *о я ou *о он. Depois de о, o pronome muda para обо мне, о нём etc.; depois de что, mantenha uma oração com seu próprio sujeito e verbo.",
        "Escolha primeiro entre uma opinião com что e um assunto com о + Preposicional; depois flexione adjetivos e pronomes dentro da oração.",
    ),
    "falando-de-planos-russo": lesson_revision(
        "Planos combinam intenção, futuro e destino. Буду работать apresenta uma atividade futura; куплю ou поеду apresenta um resultado/viagem planejada como evento. O infinitivo perfectivo depois de хочу costuma projetar uma ação concluída ou uma ida específica.",
        """| Intenção | Forma | Exemplo |
|---|---|---|
| atividade futura | буду + imperfectivo | буду работать |
| resultado pontual | perfectivo futuro | куплю машину |
| viagem pretendida | perfectivo infinitivo | хочу поехать |
| destino | в + Acusativo | в Россию |
| local de trabalho | в + Preposicional | в Москве |""",
        """Я буду работать в Москве. — Vou trabalhar em Moscou.
Я хочу поехать в Россию. — Quero viajar para a Rússia.
Я куплю билет завтра. — Comprarei a passagem amanhã.""",
        "Não use o mesmo caso em в Москве e в Россию: permanência pede Preposicional, destino pede Acusativo. Também evite *буду купить; o futuro composto só aceita imperfectivo.",
        "Separe local e destino, identifique atividade versus resultado e escolha o aspecto antes de formar o futuro.",
    ),
    "pedidos-educados-b1": lesson_revision(
        "A polidez russa pode ser graduada. Можно мне é um pedido neutro; Я хотел бы suaviza a vontade; Не могли бы вы...? é uma pergunta muito cortês. O destinatário de помочь aparece no Dativo, enquanto o objeto/quantidade mantém seu próprio caso.",
        """| Fórmula | Registro | Exemplo |
|---|---|---|
| Можно мне...? | pedido neutro | Можно мне воды? |
| Я хотел бы... | gostaria de | Я хотел бы поговорить |
| Не могли бы вы...? | muito educado | Не могли бы вы помочь мне? |
| пожалуйста | suaviza | Скажите, пожалуйста |""",
        """Не могли бы вы повторить, пожалуйста? — Você poderia repetir, por favor?
Можно мне ещё воды? — Posso tomar mais água?
Я хотел бы поговорить с тобой. — Eu gostaria de conversar com você.""",
        "Não use меня depois de помочь: a pessoa beneficiária é мне. E não confunda воды, Genitivo de quantidade, com вода quando se pede uma unidade/porção determinada.",
        "Escolha a fórmula pelo grau de polidez, use Dativo para quem recebe a ajuda e confira o caso do item pedido.",
    ),
    "expressando-gostos": lesson_revision(
        "Há duas construções importantes para “gostar”. Em Мне нравится, a pessoa que sente fica no Dativo e a coisa agradável funciona como sujeito no Nominativo. Em Я люблю/предпочитаю, a pessoa é sujeito e o objeto vai para o Acusativo.",
        """| Verbo | Pessoa | Coisa apreciada | Exemplo |
|---|---|---|---|
| нравиться | Dativo | Nominativo | Мне нравится музыка |
| любить | Nominativo | Acusativo | Я люблю чай |
| предпочитать | Nominativo | Acusativo | Я предпочитаю кофе |
| нравится no plural | Dativo | plural + нравится | Мне нравятся книги |""",
        """Мне нравится классическая музыка. — Gosto de música clássica.
Я люблю новую книгу. — Gosto muito do livro novo.
Мне нравятся эти фильмы. — Gosto destes filmes.""",
        "Não conjugue нравится de acordo com мне. O verbo concorda com a coisa apreciada: мне нравится музыка, mas мне нравятся книги.",
        "Pergunte quem sente, depois identifique a coisa que agrada. Dativo + Nominativo usa нравиться; sujeito + Acusativo usa любить/предпочитать.",
    ),
    "desculpas-e-justificativas": lesson_revision(
        "Desculpas naturais combinam uma fórmula fixa com a causa e uma escolha aspectual cuidadosa. Не смог прийти apresenta uma tentativa que não se concretizou; не мог прийти descreve falta de possibilidade/capacidade. Потому что introduz a justificativa.",
        """| Situação | Forma | Sentido |
|---|---|---|
| desculpa | Извините | desculpe |
| causa | потому что | porque |
| tentativa falhou | не смог прийти | não consegui vir |
| impossibilidade | не мог прийти | não podia vir |
| atraso | за опоздание | pelo atraso |""",
        """Извините за опоздание. — Desculpe o atraso.
Я не смог прийти, потому что был занят. — Não consegui vir porque estava ocupado.
К сожалению, я опоздал. — Infelizmente, me atrasei.""",
        "Não trate мог e смог como simples variantes de estilo. O perfectivo смог fecha o episódio de tentativa malsucedida; мог enquadra a possibilidade ou incapacidade.",
        "Use a expressão fixa da desculpa, escolha o aspecto conforme possibilidade versus resultado e ligue a causa com потому что.",
    ),

    # Módulo 14 — formas verbais avançadas
    "participios": lesson_revision(
        "Particípios condensam uma oração relativa em uma forma adjetival. A forma ativa descreve quem faz a ação; a passiva descreve quem a recebe. É importante distinguir o presente (читающий, читаемый) do resultado perfectivo (прочитанный): “lido até o fim” normalmente pede прочитанный, não читаемый.",
        """| Tipo | Formação/exemplo | Valor |
|---|---|---|
| ativo presente | читающий | que está lendo |
| passivo presente | читаемый | que é/está sendo lido |
| ativo passado | читавший | que leu/lia |
| passivo perfectivo | прочитанный | que foi lido até o fim |""",
        """Студент, читающий книгу, сидит у окна. — O estudante que lê o livro está sentado perto da janela.
Документ, подписанный директором, на столе. — O documento assinado pelo diretor está na mesa.
Прочитанная книга лежит здесь. — O livro lido até o fim está aqui.""",
        "Usar читаемый para qualquer “lido” pode sugerir uma ação em curso ou uma propriedade (“legível”). Para resultado concluído, prefira o particípio perfectivo прочитанный; e faça a forma concordar com o substantivo.",
        "Pergunte quem pratica ou sofre a ação, escolha o tempo/aspecto do particípio e decline-o como adjetivo em gênero, número e caso.",
    ),
    "gerundios-russo": lesson_revision(
        "O gerúndio russo (деепричастие) é invariável e acrescenta uma ação secundária ao verbo principal. O imperfectivo costuma indicar simultaneidade (читая, “lendo”); o perfectivo indica anterioridade e conclusão (прочитав, “tendo lido”). O sujeito implícito das duas ações deve ser o mesmo.",
        """| Aspecto | Forma | Relação temporal |
|---|---|---|
| imperfectivo | читая | ao mesmo tempo |
| perfectivo | прочитав | antes, concluída |
| sujeito | он | deve coincidir com a principal |
| concordância | invariável | não muda por gênero/caso |""",
        """Читая книгу, он пил чай. — Enquanto lia o livro, ele bebia chá.
Прочитав книгу, он уснул. — Tendo lido o livro, ele adormeceu.
Закончив работу, она пошла домой. — Tendo terminado o trabalho, ela foi para casa.""",
        "Não coloque um gerúndio cujo sujeito não seja o da oração principal: *Прочитав книгу, начался дождь sugere que “a chuva leu o livro”. Também não faça o gerúndio concordar como adjetivo.",
        "Escolha simultaneidade ou anterioridade, mantenha o mesmo sujeito e deixe o gerúndio invariável.",
    ),
    "participio-passivo-curto": lesson_revision(
        "O particípio passivo curto apresenta um estado/resultado e funciona como predicado. Ele concorda em gênero e número, mas não recebe caso porque não acompanha um substantivo dentro de um sintagma. O presente normalmente omite быть: Письмо написано significa “A carta está escrita”.",
        """| Sujeito | Forma curta de закрыть | Exemplo |
|---|---|---|
| masc. магазин | закрыт | Магазин закрыт |
| fem. дверь | закрыта | Дверь закрыта |
| neutro окно | закрыто | Окно закрыто |
| plural двери | закрыты | Двери закрыты |""",
        """Задача решена. — O problema está resolvido.
Документы подписаны. — Os documentos estão assinados.
Окно открыто после ремонта. — A janela está aberta depois da reforma.""",
        "Não confunda forma curta com a longa: закрыта é predicado (“está fechada”), enquanto закрытая дверь é um modificador antes do substantivo. Também não use *дверь закрыт: o sujeito é feminino.",
        "Use a forma curta para resultado predicativo e confira apenas gênero/número do sujeito; use a longa quando o particípio acompanha um substantivo.",
    ),
    "discurso-indireto-russo": lesson_revision(
        "O discurso indireto russo preserva com frequência o tempo da fala original, mas não é uma regra de “nunca mudar”: o tempo pode mudar quando o sentido temporal exige. O núcleo didático é ajustar pronomes e escolher что, palavra interrogativa, ли ou чтобы conforme o tipo de conteúdo relatado.",
        """| Fala direta | Discurso indireto | Conector |
|---|---|---|
| Я устал | он сказал, что он устал | что |
| Где ты? | она спросила, где я | palavra interrogativa |
| Ты придёшь? | он спросил, придёшь ли ты | ли |
| Читай! | он сказал, чтобы я читал | чтобы + passado |""",
        """Она сказала, что придёт завтра. — Ela disse que virá amanhã.
Он спросил, где находится вокзал. — Ele perguntou onde fica a estação.
Она попросила, чтобы я подождал. — Ela pediu que eu esperasse.""",
        "Não use ли em perguntas que já têm onde, quando ou por que; ли marca a alternativa sim/não. Depois de чтобы, o verbo concorda com o novo sujeito no passado.",
        "Identifique declaração, pergunta aberta, pergunta sim/não ou pedido; escolha o conector e ajuste os pronomes ao ponto de vista do narrador.",
    ),
    "verbos-de-citacao": lesson_revision(
        "O verbo de citação seleciona a construção seguinte. Сказать/ответить/объяснить normalmente introduzem что ou uma interrogativa; спросить usa ли ou palavra interrogativa; попросить seleciona чтобы. A seleção lexical é tão importante quanto a conjunção.",
        """| Verbo | Complemento típico | Exemplo |
|---|---|---|
| сказать/ответить | что | Он ответил, что занят |
| спросить | ли / где, почему... | Я спросил, придёшь ли ты |
| объяснить | что / почему | Она объяснила, почему опоздала |
| попросить | чтобы + passado | Он попросил, чтобы я подождал |""",
        """Он ответил, что занят. — Ele respondeu que está ocupado.
Она объяснила, почему опоздала. — Ela explicou por que se atrasou.
Я спросил, придёшь ли ты. — Perguntei se você virá.""",
        "Não traduza “perguntar” com ответить nem “pedir” com сказать. O conector pode até estar correto, mas o verbo de citação errado muda a relação discursiva.",
        "Escolha primeiro o ato de fala, depois o conector e finalmente o tempo/aspecto da oração relatada.",
    ),

    # Módulo 15 — movimento prefixado
    "prefixos-chegar-e-sair": lesson_revision(
        "Os prefixos при- e у- acrescentam um ponto final ao movimento. Прийти/приехать significam chegar; уйти/уехать significam ir embora. Esses perfectivos se opõem a приходить, приезжать, уходить e уезжать quando a situação é habitual ou está em desenvolvimento.",
        """| Sentido | A pé | De veículo | Origem/destino |
|---|---|---|---|
| chegar | прийти | приехать | в/на + Acusativo |
| ir embora | уйти | уехать | из/с/от + Genitivo |
| chegar repetidamente | приходить | приезжать | rotina |
| sair repetidamente | уходить | уезжать | rotina |""",
        """Мы приехали в город вечером. — Chegamos à cidade à noite.
Он пришёл домой. — Ele chegou em casa.
Он уехал из Москвы утром. — Ele saiu de Moscou de manhã.""",
        "Não associe при- apenas a “entrar”: прийти é chegar, e o destino não vira Preposicional quando há movimento. в Москву é Acusativo; в Москве é localização.",
        "Identifique chegar ou partir, escolha a modalidade a pé/veículo e confira se o complemento é destino ou origem.",
    ),
    "prefixos-entrar-e-sair": lesson_revision(
        "Войти/въехать focalizam entrada em um espaço; выйти/выехать focalizam saída de dentro. O par de casos é muito produtivo: в + Acusativo indica para dentro, из + Genitivo indica de dentro. O prefixo e a preposição formam uma unidade de sentido.",
        """| Evento | A pé | De veículo | Complemento |
|---|---|---|---|
| entrar | войти | въехать | в комнату |
| sair | выйти | выехать | из комнаты |
| entrar repetidamente | входить | въезжать | em desenvolvimento |
| sair repetidamente | выходить | выезжать | em desenvolvimento |""",
        """Он вошёл в комнату. — Ele entrou na sala.
Она вышла из магазина. — Ela saiu da loja.
Машина въехала в гараж. — O carro entrou na garagem.""",
        "Não use в комнате para “entrou na sala”: essa forma é localização. Para o evento de entrada, в комнату exige Acusativo; para sair de dentro, из комнаты exige Genitivo.",
        "Pergunte para onde ou de onde, escolha a preposição correspondente e só então flexione o lugar.",
    ),
    "prefixo-pere": lesson_revision(
        "Пере- atravessa uma fronteira ou muda de um lado para outro; под- aproxima; от- afasta; за- pode indicar uma entrada breve, uma parada no caminho ou “passar por”. Esses sentidos são composicionais, mas o uso lexical precisa ser aprendido em frases.",
        """| Prefixo | Núcleo de sentido | Regência frequente | Exemplo |
|---|---|---|---|
| пере- | atravessar | Acusativo | перейти улицу |
| под- | aproximar-se | к + Dativo | подойти к окну |
| от- | afastar-se | от + Genitivo | отойти от окна |
| за- | passar/entrar de passagem | к + Dativo | зайти к другу |""",
        """Она перешла улицу. — Ela atravessou a rua.
Он подошёл к окну. — Ele se aproximou da janela.
Я зайду к другу вечером. — Passarei na casa do meu amigo à noite.""",
        "Não memorize подойти como “entrar”: o verbo significa aproximar-se e к puxa Dativo. Do mesmo modo, переходить улицу e идти к окну selecionam complementos diferentes.",
        "Aprenda cada prefixo com uma imagem espacial, a preposição e o caso: a tríade evita escolher apenas pela tradução portuguesa.",
    ),
    "pares-imperfectivos-de-movimento": lesson_revision(
        "Um verbo de movimento prefixado perfectivo costuma ganhar um par imperfectivo com -ходить ou -езжать: прийти/приходить, приехать/приезжать. O imperfectivo não significa necessariamente “estar agora”; também cobre rotina, repetição e característica regular.",
        """| Perfectivo | Imperfectivo | Exemplo de repetição |
|---|---|---|
| прийти | приходить | Он часто приходит |
| уйти | уходить | Она рано уходит |
| войти | входить | Люди входят в зал |
| выйти | выходить | Он выходит из дома |
| приехать | приезжать | Она приезжает рано |""",
        """Он пришёл в девять. — Ele chegou às nove, uma ocorrência.
Он приходит в девять. — Ele chega às nove, rotina.
Мы часто переходим эту улицу. — Atravessamos esta rua com frequência.""",
        "Não forme o imperfectivo apenas removendo o prefixo: *йти não é o par de прийти. O prefixo permanece e a raiz do movimento muda conforme o meio.",
        "Compare evento único e padrão recorrente, memorize o par completo e conserve os casos do destino/origem.",
    ),
    "movimento-prefixado-e-casos": lesson_revision(
        "Prefixos de movimento fazem o aspecto e a direção avançarem juntos, mas não substituem a regência das preposições. Destino, origem e aproximação são relações diferentes: в/на + Acusativo, из/с/от + Genitivo e к + Dativo.",
        """| Relação | Preposição | Caso | Exemplo |
|---|---|---|---|
| destino/entrada | в/на | Acusativo | в комнату |
| origem/saída | из/с/от | Genitivo | из города |
| aproximação | к | Dativo | к окну |
| travessia | sem preposição frequente | Acusativo | перейти улицу |""",
        """Он вошёл в комнату. — Ele entrou na sala.
Она отошла от друга. — Ela se afastou do amigo.
Мы выехали из города. — Saímos da cidade de veículo.""",
        "Não escolha o caso pela forma do prefixo isolado. O mesmo prefixo pode aparecer em construções distintas; observe a preposição e a relação espacial que a frase expressa.",
        "Classifique destino, origem, aproximação ou travessia; aplique a preposição/regência e só depois confira a flexão do substantivo.",
    ),

    # Módulo 16 — imperativo e aspecto
    "modo-imperativo": lesson_revision(
        "O imperativo é dirigido a ты ou вы, não recebe pronome sujeito normalmente e varia em informal/formal-plural. Muitas formas vêm da base do presente (читай, говори), mas verbos frequentes são irregulares: иди, ешь, дай. A entonação e пожалуйста modulam a ordem.",
        """| Infinitivo | ты | вы/formal-plural | Exemplo |
|---|---|---|---|
| читать | читай | читайте | Читайте книгу |
| говорить | говори | говорите | Говорите медленнее |
| идти | иди | идите | Идите прямо |
| писать | пиши | пишите | Пишите здесь |""",
        """Говорите медленнее. — Fale mais devagar, formal.
Иди домой! — Vá para casa, informal.
Идите прямо. — Siga em frente, formal/plural.""",
        "Não deduza todos os imperativos apenas pela terminação -те; ela marca a forma de вы, mas a base pode ser irregular. Идите não é o presente идёте usado como ordem por acaso.",
        "Defina o interlocutor, escolha a forma ты ou вы e confirme se o verbo tem imperativo irregular antes de adicionar o complemento.",
    ),
    "imperativo-negativo": lesson_revision(
        "A negação usa не + imperativo, mas o aspecto depende do efeito pretendido. Imperfectivo é muito comum para proibição geral ou para interromper uma atividade; perfectivo aparece em avisos sobre um resultado pontual, como Не забудь! e Не опоздай!.",
        """| Intenção | Forma | Exemplo |
|---|---|---|
| não faça/continue | не + imperfectivo | Не читай это! |
| não conclua este evento | não + perfectivo | Не забудь паспорт! |
| proibição formal | не + imperativo вы | Не открывайте дверь! |
| interrupção | imperfectivo | Не говори! |""",
        """Не читай эту книгу! — Não leia esse livro!
Не забудь паспорт! — Não esqueça o passaporte!
Не открывайте дверь! — Não abram/abra a porta!""",
        "Dizer que todo imperativo negativo é imperfectivo é uma simplificação perigosa: не забудь, не опоздай e не потеряй usam perfectivo quando o foco é evitar um resultado pontual.",
        "Para proibição de atividade, prefira imperfectivo; para evitar um evento/resultado único, aceite o perfectivo. A situação decide.",
    ),
    "aspecto-no-imperativo": lesson_revision(
        "No imperativo afirmativo, o perfectivo costuma pedir uma realização única com resultado; o imperfectivo pode convidar a uma atividade, dar instrução geral ou pedir repetição. O contraste é pragmático: duas formas podem ser gramaticais, mas com tom diferente.",
        """| Aspecto | Uso | Exemplo |
|---|---|---|
| perfectivo | uma realização | Прочитай статью! |
| imperfectivo | hábito/repetição | Звони каждую неделю! |
| imperfectivo negativo | não iniciar/continuar | Не опаздывай! |
| perfectivo negativo | evitar resultado | Не забудь! |""",
        """Позвони мне вечером! — Ligue para mim à noite, uma vez.
Звони мне каждую неделю! — Ligue para mim toda semana.
Закончи отчёт! — Termine o relatório.""",
        "Não escolha o aspecto apenas pela tradução “ligue” ou “leia”. Marcadores como каждую неделю exigem repetição; “até o fim” e uma tarefa única favorecem perfectivo.",
        "Leia o pedido como intenção comunicativa: resultado único, processo, rotina ou proibição. Isso orienta o par aspectual.",
    ),
    "imperativo-formal": lesson_revision(
        "Вы no imperativo serve tanto ao plural quanto à distância/polidez com uma pessoa. Пожалуйста suaviza, mas não substitui a concordância. Verbos de ajuda, dizer e dar também recuperam os casos do curso: помочь мне, сказать мне, дать мне воды.",
        """| Pedido | Forma-alvo | Caso importante |
|---|---|---|
| diga-me | Скажите мне | мне = Dativo |
| ajude-me | Помогите мне | мне = Dativo |
| dê-me água | Дайте мне воды | воды = Genitivo de quantidade |
| espere | Подождите | вы formal/plural |""",
        """Подождите, пожалуйста. — Aguarde, por favor.
Помогите мне, пожалуйста. — Ajude-me, por favor.
Скажите, пожалуйста, ещё раз. — Diga, por favor, mais uma vez.""",
        "Não use меня para o beneficiário de ajudar nem água no Nominativo quando a quantidade é indefinida. A polidez não elimina a regência do verbo.",
        "Use o imperativo de вы em situações formais, acrescente пожалуйста conforme o tom e revise cada complemento pelo caso que o verbo exige.",
    ),
    "pedidos-com-imperativo": lesson_revision(
        "Pedidos cotidianos ficam naturais quando o imperativo, o destinatário e o objeto são separados. Дай/принеси/покажи/расскажи podem levar мне no Dativo; o item pedido pode ser Acusativo, Genitivo de quantidade ou um complemento preposicionado.",
        """| Função | Forma | Caso |
|---|---|---|
| destinatário | мне | Dativo |
| item definido | чашку, книгу | Acusativo |
| quantidade | воды, чая | Genitivo |
| assunto | о себе, о поездке | Preposicional |""",
        """Покажите мне дорогу. — Mostre-me o caminho.
Дайте мне, пожалуйста, счёт. — Dê-me a conta, por favor.
Расскажи мне о своей поездке. — Conte-me sobre sua viagem.""",
        "Não copie o caso do pronome para o objeto: мне é Dativo, mas дорогу é Acusativo e воды é Genitivo de quantidade. Cada complemento responde a uma pergunta diferente.",
        "Localize o destinatário, o objeto definido/quantidade e o assunto; depois escolha o imperativo e a regência de cada bloco.",
    ),

    # Módulo 17 — comparação, pronomes e reflexivos
    "comparativo-e-superlativo-russo": lesson_revision(
        "O comparativo russo pode ser uma forma sintética (новее, красивее) ou uma forma irregular (лучше, хуже, больше). O superlativo mais transparente usa самый + adjetivo, que concorda com o substantivo em gênero, número e caso.",
        """| Grau | Forma | Exemplo |
|---|---|---|
| comparativo regular | adjetivo + -ее | красивее |
| irregular | лучше/хуже/больше | Этот вариант лучше |
| superlativo | самый + adjetivo | самый высокий дом |
| comparação | comparativo + чем | лучше, чем тот |""",
        """Этот тест легче, чем предыдущий. — Este teste é mais fácil que o anterior.
Это самый высокий дом. — Esta é a casa mais alta.
Моя идея лучше. — Minha ideia é melhor.""",
        "Não use *хорошее como comparativo de хороший nem deixe самый invariável sem concordância. O adjetivo do superlativo continua ligado ao substantivo.",
        "Memorize os irregulares, forme o superlativo com concordância e confirme se a comparação exige чем ou outra construção.",
    ),
    "comparacao-com-chem": lesson_revision(
        "Чем liga duas partes de uma comparação explícita. O segundo termo pode aparecer depois de чем ou, em muitos comparativos, no Genitivo sem чем: Он выше меня. A igualdade usa такой же, как, com o padrão de caso esperado pela construção.",
        """| Relação | Estrutura | Exemplo |
|---|---|---|
| superioridade explícita | comparativo + чем | выше, чем я |
| genitivo comparativo | comparativo + pronome | выше меня |
| igualdade | такой же, как | такой же высокий, как я |
| diferença | больше/меньше + чем | больше, чем Сочи |""",
        """Анна старше, чем Мария. — Anna é mais velha que Maria.
Он младше меня. — Ele é mais novo que eu.
Она такая же высокая, как я. — Ela é tão alta quanto eu.""",
        "Não use o Nominativo depois de um comparativo sem чем: *Он младше я. A alternativa natural é Он младше меня ou Он младше, чем я.",
        "Escolha comparação explícita com чем ou Genitivo comparativo; para igualdade, use такой же... как e preserve a concordância.",
    ),
    "adjetivos-forma-curta": lesson_revision(
        "A forma curta é sobretudo predicativa: vem depois do sujeito e descreve estado ou avaliação, enquanto a forma longa modifica um substantivo. Ela tem gênero e número, mas não funciona como um adjetivo longo em todos os contextos e nem todo adjetivo tem uso curto frequente.",
        """| Função | Forma longa | Forma curta |
|---|---|---|
| antes do substantivo | красивая девушка | — |
| predicado feminino | девушка красивая | она рада |
| predicado neutro | — | окно открыто |
| plural | красивые дома | они готовы |""",
        """Они готовы начать. — Eles estão prontos para começar.
Она уверена в ответе. — Ela está segura da resposta.
Окно открыто. — A janela está aberta.""",
        "Não trate toda forma terminada em -ый como predicado curto nem coloque рада antes do substantivo sem contexto. A posição e o sentido distinguem as duas séries.",
        "Use a forma longa como modificador e a curta como predicado/estado quando ela for usual; faça a concordância de gênero e número.",
    ),
    "verbos-reflexivos": lesson_revision(
        "-ся/-сь não significa sempre “a si mesmo”. Pode indicar reflexividade, reciprocidade, processo sem agente destacado ou um sentido lexicalizado, como учиться “estudar”. A partícula acompanha todas as terminações e alterna entre -ся e -сь por razões fonéticas.",
        """| Verbo | Sentido | Exemplo |
|---|---|---|
| мыть / мыться | lavar / lavar-se | Я моюсь |
| учить / учиться | ensinar / estudar | Ты учишься |
| встречать / встречаться | encontrar / encontrar-se | Мы встречаемся |
| интересовать / интересоваться | interessar / interessar-se | Он интересуется музыкой |""",
        """Ты учишься в университете. — Você estuda na universidade.
Мы встречаемся вечером. — Nós nos encontramos à noite.
Он интересуется музыкой. — Ele se interessa por música.""",
        "Não traduza -ся sempre como “se” e não remova a partícula ao conjugar: учит e учится têm sujeitos e sentidos diferentes. интересоваться ainda exige Instrumental.",
        "Aprenda o verbo reflexivo como unidade lexical, observe sua regência e coloque -ся/-сь depois da terminação verbal.",
    ),
    "reflexivos-na-rotina": lesson_revision(
        "A rotina combina verbos reflexivos, horários e movimento. Просыпаться, вставать, умываться, одеваться e ложиться são normalmente imperfectivos porque descrevem hábitos; uma forma perfectiva pode narrar um episódio concluído. Destinos continuam exigindo casos próprios.",
        """| Rotina | Forma | Complemento |
|---|---|---|
| acordar | просыпаться | в семь часов |
| levantar-se | вставать | рано |
| vestir-se | одеваться | — |
| ir ao trabalho | идти | на работу, Acusativo |
| deitar-se | ложиться | спать |""",
        """Я просыпаюсь в семь и одеваюсь. — Acordo às sete e me visto.
Я одеваюсь и иду на работу. — Visto-me e vou trabalhar.
Мы ложимся спать в одиннадцать. — Deitamo-nos às onze.""",
        "Não use Preposicional em na работу: com movimento, на работу é direção e Acusativo; na localização, “no trabalho” é на работе, Preposicional.",
        "Conjugue o reflexivo como verbo normal, use imperfectivo para a rotina e diferencie destino de localização nos complementos espaciais.",
    ),

    # Módulo 18 — vocabulário e expressões B2
    "expressoes-do-dia-a-dia-russo": lesson_revision(
        "Expressões fixas são unidades de vocabulário, mas não são livres de gramática. Мне всё равно e мне надо usam Dativo; с удовольствием usa Instrumental; нет exige Genitivo. Memorizar a frase inteira ajuda a recuperar o caso sob pressão.",
        """| Expressão | Caso | Sentido |
|---|---|---|
| мне всё равно | Dativo | tanto faz para mim |
| с удовольствием | Instrumental | com prazer |
| у меня нет времени | Genitivo | não tenho tempo |
| мне надо работать | Dativo | preciso trabalhar |""",
        """Мне всё равно. — Para mim tanto faz.
Я с удовольствием помогу. — Terei prazer em ajudar.
У меня нет времени. — Não tenho tempo.""",
        "Não substitua мне por меня porque ambas podem traduzir “me”. A expressão e a função determinam o caso; нет времени não é uma negação com Nominativo.",
        "Aprenda a colocação como bloco, nomeie o caso que aparece dentro dela e reutilize-a em frases novas.",
    ),
    "colocacoes-com-casos": lesson_revision(
        "Colocações ligam verbo e caso de forma previsível, mas nem sempre coincidem com a preposição portuguesa. интересоваться e гордиться regem Instrumental; помогать rege Dativo; бояться rege Genitivo. Ждать pode selecionar Genitivo ou Acusativo conforme definitude, animacidade e aspecto.",
        """| Verbo | Regência frequente | Exemplo |
|---|---|---|
| интересоваться | Instrumental | музыкой |
| гордиться | Instrumental | сыном |
| помогать | Dativo | маме |
| бояться | Genitivo | собак |
| ждать | Genitivo/Acusativo | автобуса / автобус |""",
        """Он интересуется музыкой. — Ele se interessa por música.
Я помогаю маме. — Eu ajudo minha mãe.
Я жду автобус. — Espero o ônibus específico.""",
        "Não traduza “ajudar minha mãe” como Acusativo: помогать маме exige Dativo. Com ждать, não ensine uma única forma como obrigatória; o contexto pode favorecer Genitivo ou Acusativo.",
        "Memorize verbo + caso + exemplo curto. Quando houver mais de uma regência possível, use contexto de definitude e animacidade.",
    ),
    "verbos-com-prefixo": lesson_revision(
        "Prefixos criam sentidos lexicais e frequentemente perfectivos, mas não são sinônimo automático de perfectividade. Позвонить, прочитать, сделать e понять precisam ser comparados aos pares imperfeitos звонить, читать, делать e понимать; o prefixo também pode acrescentar direção, início ou completude.",
        """| Imperfectivo | Perfectivo | Nuance |
|---|---|---|
| звонить | позвонить | ligar repetidamente / uma vez |
| читать | прочитать | ler / ler até o fim |
| делать | сделать | fazer / concluir |
| понимать | понять | entender gradualmente / captar |
| говорить | сказать | falar / dizer |""",
        """Я сразу понял. — Entendi imediatamente.
Он позвонил вчера. — Ele ligou ontem, uma vez.
Он прочитал письмо. — Ele leu a carta até o fim.""",
        "Não remova o prefixo para voltar ao infinitivo nem conclua que qualquer verbo prefixado é perfectivo em todas as suas formas. O par e o sentido precisam ser aprendidos juntos.",
        "Compare os dois verbos em uma situação de processo e outra de resultado; depois flexione o aspecto escolhido no tempo necessário.",
    ),
    "expressoes-de-tempo": lesson_revision(
        "Expressões temporais reciclam casos já vistos e por isso são um ótimo teste de espiral. В понедельник trata o dia como ponto de agenda; в мае localiza no mês; через marca distância futura; назад mede distância passada; с... до... delimita intervalo.",
        """| Expressão | Caso/estrutura | Sentido |
|---|---|---|
| в понедельник | Acusativo | na segunda |
| в мае | Preposicional | em maio |
| через час | Acusativo | daqui a uma hora |
| год назад | forma de tempo | há um ano |
| с утра до вечера | Genitivo após с/до | de manhã à noite |""",
        """Мы встретимся через час. — Nós nos encontraremos daqui a uma hora.
Я работаю в понедельник. — Trabalho na segunda-feira.
Мы работаем с утра до вечера. — Trabalhamos da manhã à noite.""",
        "Não generalize в + Acusativo para todo tempo: в мае é Preposicional porque localiza a ação em um mês. A pergunta é agenda/duração/distância ou localização temporal.",
        "Identifique o tipo de expressão, aplique a preposição e só então flexione a palavra temporal.",
    ),
    "frases-prontas": lesson_revision(
        "Frases prontas funcionam como marcadores de conversa e devem ser aprendidas com pontuação e registro. Кстати abre um comentário lateral; к сожалению marca pesar; по-моему atribui opinião; на здоровье tem usos convencionais em respostas sociais, não apenas uma tradução literal.",
        """| Expressão | Função | Exemplo |
|---|---|---|
| Кстати | comentário lateral | Кстати, я видел его |
| К сожалению | pesar/limitação | К сожалению, не могу |
| По-моему | opinião | По-моему, это важно |
| Ничего страшного | tranquilizar | Ничего страшного! |
| На здоровье | resposta/saúde | Спасибо! — На здоровье! |""",
        """К сожалению, я не могу прийти. — Infelizmente, não posso ir.
Кстати, я видел его вчера. — Aliás, eu o vi ontem.
Всё хорошо. — Está tudo bem.""",
        "Não trate кстати e к сожалению como conjunções que mudam a flexão da oração. São marcadores discursivos; a frase interna continua obedecendo a seus próprios casos e tempos.",
        "Memorize o bloco, identifique sua função conversacional e depois analise separadamente a gramática da oração que ele introduz.",
    ),
    "expressoes-idiomaticas-russo": lesson_revision(
        "Idiomas não devem ser traduzidos palavra por palavra. A imagem ajuda a lembrar, mas o sentido vem do conjunto e os casos fazem parte da expressão: в облаках e на носу são Preposicionais; сломя голову é uma construção adverbial cristalizada.",
        """| Expressão | Sentido natural | Caso/observação |
|---|---|---|
| бить баклуши | ficar à toa | infinitivo/imperativo |
| витать в облаках | viver nas nuvens | в облаках = Prep. |
| сломя голову | a toda velocidade | expressão adverbial |
| зарубить на носу | guardar bem | на носу = Prep. |
| медведь на ухо наступил | não ter ouvido musical | на ухо = Acusativo |""",
        """Она витает в облаках. — Ela está nas nuvens.
Не бей баклуши! — Não fique à toa!
Он бежит домой сломя голову. — Ele corre para casa a toda velocidade.""",
        "Não invente uma tradução literal como se fosse o significado e não confunda o idiom com uma frase malformada: Хватит бить баклуши ou Не бей баклуши é natural; *Не сиди, бить баклуши não é.",
        "Aprenda expressão, sentido e exemplo juntos; depois identifique os casos internos sem perder o valor idiomático.",
    ),
}


def _expand_intermediate_module(builder):
    """Completa os módulos 9–18 sem alterar os exercícios já autorados."""
    def wrapped():
        built = builder()
        for current_topic in built["topics"]:
            slug = current_topic["slug"]
            if slug not in INTERMEDIATE_EXTRA_EXERCISES:
                raise KeyError(f"tópico sem exercícios extras: {slug}")
            if slug not in INTERMEDIATE_LESSON_REVISIONS:
                raise KeyError(f"tópico sem revisão editorial: {slug}")
            current_topic["exercises"].extend(deepcopy(INTERMEDIATE_EXTRA_EXERCISES[slug]))
            current_topic["lesson_md"] = (
                current_topic["lesson_md"].rstrip()
                + "\n\n"
                + INTERMEDIATE_LESSON_REVISIONS[slug]
            )
            if len(current_topic["exercises"]) != 10:
                raise ValueError(
                    f"{built['slug']}/{slug}: esperado exatamente 10 exercícios, "
                    f"encontrados {len(current_topic['exercises'])}"
                )
        return built
    return wrapped


for _expanded_builder_name in (
    "build_modulo_09_aspecto_verbal_conceito",
    "build_modulo_10_passado_e_futuro",
    "build_modulo_11_casos_avancados",
    "build_modulo_12_verbos_de_movimento",
    "build_modulo_13_comunicacao_b1",
    "build_modulo_14_participios_gerundios_e_discurso_indireto",
    "build_modulo_15_verbos_de_movimento_prefixados",
    "build_modulo_16_imperativo_e_aspecto",
    "build_modulo_17_comparacao_pronomes_e_reflexivos",
    "build_modulo_18_vocabulario_e_expressoes_b2",
):
    globals()[_expanded_builder_name] = _expand_intermediate_module(
        globals()[_expanded_builder_name]
    )


# ============================================================
# Montagem final: monta o curso na ordem do roteiro
# ============================================================

# Ordem final dos 29 módulos do roteiro (tools/RUSSIAN_ROADMAP.md). Módulos
# cujo builder ainda não existe simplesmente não aparecem no JSON até a fase
# deles ser construída.
TARGET_ORDER = [
    "modulo-01-alfabeto-e-primeiros-passos",
    "modulo-02-frases-basicas-sem-verbo-ser",
    "modulo-03-perguntas-e-negacao",
    "modulo-04-casos-primeiro-contato",
    "modulo-05-vocabulario-e-comunicacao-a1",
    "modulo-06-presente-dos-verbos",
    "modulo-07-vocabulario-e-comunicacao-a2",
    "modulo-08-casos-intermediarios",
    "modulo-09-aspecto-verbal-conceito",
    "modulo-10-passado-e-futuro",
    "modulo-11-casos-avancados",
    "modulo-12-verbos-de-movimento",
    "modulo-13-comunicacao-b1",
    "modulo-14-participios-gerundios-e-discurso-indireto",
    "modulo-15-verbos-de-movimento-prefixados",
    "modulo-16-imperativo-e-aspecto",
    "modulo-17-comparacao-pronomes-e-reflexivos",
    "modulo-18-vocabulario-e-expressoes-b2",
    "modulo-19-casos-em-frases-complexas",
    "modulo-20-aspecto-e-nuance",
    "modulo-21-registro-e-estilo",
    "modulo-22-speaking-c1",
    "modulo-23-listening-e-reading-c1",
    "modulo-24-escrita-c1",
    "modulo-25-russo-para-o-trabalho",
    "modulo-26-russo-para-tecnologia",
    "modulo-27-treino-de-fluencia",
    "modulo-28-dominio-c1",
    "modulo-29-imersao-final",
]

BUILDERS = {
    "modulo-01-alfabeto-e-primeiros-passos": build_modulo_01_alfabeto_e_primeiros_passos,
    "modulo-02-frases-basicas-sem-verbo-ser": build_modulo_02_frases_basicas_sem_verbo_ser,
    "modulo-03-perguntas-e-negacao": build_modulo_03_perguntas_e_negacao,
    "modulo-04-casos-primeiro-contato": build_modulo_04_casos_primeiro_contato,
    "modulo-05-vocabulario-e-comunicacao-a1": build_modulo_05_vocabulario_e_comunicacao_a1,
    "modulo-06-presente-dos-verbos": build_modulo_06_presente_dos_verbos,
    "modulo-07-vocabulario-e-comunicacao-a2": build_modulo_07_vocabulario_e_comunicacao_a2,
    "modulo-08-casos-intermediarios": build_modulo_08_casos_intermediarios,
    "modulo-09-aspecto-verbal-conceito": build_modulo_09_aspecto_verbal_conceito,
    "modulo-10-passado-e-futuro": build_modulo_10_passado_e_futuro,
    "modulo-11-casos-avancados": build_modulo_11_casos_avancados,
    "modulo-12-verbos-de-movimento": build_modulo_12_verbos_de_movimento,
    "modulo-13-comunicacao-b1": build_modulo_13_comunicacao_b1,
    "modulo-14-participios-gerundios-e-discurso-indireto": build_modulo_14_participios_gerundios_e_discurso_indireto,
    "modulo-15-verbos-de-movimento-prefixados": build_modulo_15_verbos_de_movimento_prefixados,
    "modulo-16-imperativo-e-aspecto": build_modulo_16_imperativo_e_aspecto,
    "modulo-17-comparacao-pronomes-e-reflexivos": build_modulo_17_comparacao_pronomes_e_reflexivos,
    "modulo-18-vocabulario-e-expressoes-b2": build_modulo_18_vocabulario_e_expressoes_b2,
    "modulo-19-casos-em-frases-complexas": build_modulo_19_casos_em_frases_complexas,
    "modulo-20-aspecto-e-nuance": build_modulo_20_aspecto_e_nuance,
    "modulo-21-registro-e-estilo": build_modulo_21_registro_e_estilo,
    "modulo-22-speaking-c1": build_modulo_22_speaking_c1,
    "modulo-23-listening-e-reading-c1": build_modulo_23_listening_e_reading_c1,
    "modulo-24-escrita-c1": build_modulo_24_escrita_c1,
    "modulo-25-russo-para-o-trabalho": build_modulo_25_russo_para_o_trabalho,
    "modulo-26-russo-para-tecnologia": build_modulo_26_russo_para_tecnologia,
    "modulo-27-treino-de-fluencia": build_modulo_27_treino_de_fluencia,
    "modulo-28-dominio-c1": build_modulo_28_dominio_c1,
    "modulo-29-imersao-final": build_modulo_29_imersao_final,
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
                # se nenhuma tem cirilico, e' teoria em portugues e a voz russa
                # so produziria ruido.
                if e["type"] == "quiz":
                    opts = e.get("options") or []
                    if not any(CYRILLIC.search(o) for o in opts):
                        e["audio_lang"] = "pt-BR"
    return modules


def main():
    by_slug = {}
    for slug, builder in BUILDERS.items():
        by_slug[slug] = builder()

    modules = [by_slug[slug] for slug in TARGET_ORDER if slug in by_slug]
    modules = finalize_modules(modules)

    # Os módulos 1–18 têm a meta editorial de exatamente 10 exercícios/tópico;
    # os demais módulos ativos seguem o mínimo de 5 (regra do README).
    active_module_slugs = set(BUILDERS)
    problems = check(modules, active_module_slugs)
    if problems:
        print("ERROS - nada foi escrito:")
        for p in problems:
            print("  -", p)
        raise SystemExit(1)

    data = {
        "slug": "russo-do-zero",
        "title": "Russo do Zero",
        "description": "Uma trilha completa de russo em espiral, do alfabeto cirílico (A1) até particípios, gerúndios e discurso indireto (C1) — com os 6 casos gramaticais, o aspecto verbal e os verbos de movimento revisitados em vários níveis. Pratica digitando (com teclado cirílico virtual e ouvindo a pronúncia com um clique em qualquer palavra em russo), ouvindo, falando e respondendo quizzes.",
        "category": "Idiomas",
        "icon": "🇷🇺",
        "level": "Do zero ao avançado (A1–C1)",
        "position": 4,
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
