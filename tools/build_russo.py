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
from pathlib import Path

CONTENT_DIR = Path(__file__).resolve().parent.parent / "app" / "content"
OUT_PATH = CONTENT_DIR / "russo-do-zero.json"


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

    `active_module_slugs`: módulos sendo escritos/tocados NESTA fase — só
    eles precisam cumprir o mínimo de 5 exercícios/tópico.
    """
    problems = []
    topic_slugs = []
    module_slugs = []

    for m in modules:
        module_slugs.append(m["slug"])
        for t in m["topics"]:
            topic_slugs.append(t["slug"])
            loc_base = f"{m['slug']}/{t['slug']}"
            if m["slug"] in active_module_slugs and len(t["exercises"]) < 5:
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
frase exige o espiral: "со мной" (Instrumental), "о том" (Preposicional),
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

> 🎯 Boa notícia: **Dativo, Instrumental e Preposicional** têm UMA terminação de plural para todos os gêneros (-ам/-ями/-ах). Só o Genitivo exige atenção extra.
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

> 🎯 Regra geral: unidirecional = **-ть** (uma direção, agora); multidirecional = **-ать** (repetição/ida e volta/habilidade). Memorize os 5 pares como um bloco.
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

Os **particípios** são formas do verbo que funcionam como adjetivos — equivalentes a "lendo"/"lido" em português, mas concordando em gênero/caso/número como qualquer adjetivo.

## Particípio ativo (quem pratica a ação)

```
читать -> читающий        (o que está lendo)
человек, читающий книгу    a pessoa que está lendo o livro
```

## Particípio passivo (quem sofre a ação)

```
читать -> читаемый        (o que é lido)
книга, читаемая всеми     o livro lido por todos
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
                    ex("quiz", "No discurso indireto russo, o tempo verbal:",
                       "não muda (sem backshift)", ["não muda (sem backshift)", "sempre vira passado", "sempre vira futuro"]),
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

Os verbos prefixados são **perfectivos** por natureza. O par **imperfectivo** troca a raiz -йти/-ехать por -ходить/-езжать:

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
- **Imperfectivo**: um convite mais neutro, uma instrução geral, ou justamente para **proibir/pedir para não continuar** algo — "Не читай!" (Não leia! / Pare de ler!) quase sempre usa o imperfectivo, mesmo quando o afirmativo correspondente seria perfectivo.

> ⚠️ Esse é um padrão curioso: o imperativo negativo prefere o imperfectivo mesmo quando a versão afirmativa da mesma ideia usaria o perfectivo — vale notar como exceção à intuição.
""",
                [
                    ex("quiz", "Como se nega um imperativo?",
                       "не + imperativo", ["не + imperativo", "imperativo + не", "нет + imperativo"]),
                    ex("text", "Traduza: Não leia esse livro! (не + читай + эту + книгу)",
                       "не читай эту книгу"),
                    ex("quiz", "No imperativo negativo, qual aspecto costuma ser preferido, mesmo quando o afirmativo usaria o outro?",
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
                    ex("quiz", 'Como se diz "Com prazer"?',
                       "С удовольствием", ["С удовольствием", "С радостью não", "У меня нет"]),
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
| ждать + Genitivo/Acusativo | Genitivo | ждать автобуса (esperar o ônibus) |
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

> 🎯 A escolha do prefixo é o aspecto (Módulo 9): o prefixo torna o verbo perfectivo (ação única/completa). "Звонил" (processo) vs "позвонил" (ligou uma vez).
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
Не сиди, бить баклуши!            Não fique aí à toa!
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

    # Só os módulos com builder nesta execução precisam cumprir o mínimo de
    # 5 exercícios/tópico (regra do tools/README.md).
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
