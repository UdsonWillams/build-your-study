# -*- coding: utf-8 -*-
"""Gera app/content/russo-do-zero.json a partir de uma estrutura Python.

Por que gerar via script em vez de editar o JSON à mão: o curso inteiro está
num único arquivo JSON de ~1400 linhas com muito texto em cirílico dentro de
strings escapadas (\\n, aspas). Escrever/objetar isso à mão em um arquivo desse
tamanho é propenso a erro de sintaxe. Construir como dict Python (com strings
multi-linha normais) e serializar com json.dump(ensure_ascii=False, indent=2)
produz exatamente o mesmo formato do arquivo original, sem risco de JSON
inválido.
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


MODULES = []

# ============================================================
# MODULO 0 - Alfabeto e Primeiros Passos (A1)
# ============================================================
MODULES.append(module(
    "alfabeto-e-primeiros-passos-russo",
    "Módulo 0 — Alfabeto e Primeiros Passos (A1)",
    "Como funciona o curso, o alfabeto cirílico, sons difíceis, saudações e números — ainda com apoio de romanização.",
    [
        topic(
            "o-que-e-o-cefr-russo",
            "Como este curso funciona: os níveis A1 a C1",
            """
# Como este curso funciona: os níveis A1 a C1

Este curso segue o **CEFR** (Common European Framework of Reference for Languages) — a mesma escala usada no curso de inglês:

| Nível | Nome | Você já consegue... |
|---|---|---|
| **A1** | Iniciante | Ler o alfabeto, frases simples, se apresentar |
| **A2** | Básico | Frases do dia a dia, os casos gramaticais mais comuns |
| **B1** | Intermediário | Usar os 6 casos, entender o aspecto verbal |
| **B2** | Intermediário avançado | Verbos de movimento, voz mais natural |
| **C1** | Avançado | Particípios, gerúndios, nuance e fluência |

## Um aviso importante sobre o russo

Russo é uma língua **muito mais distante do português** do que o inglês. Alguns choques que você vai encontrar pela frente:

- Um **alfabeto novo** (cirílico) — mas calma, são só 33 letras, e você aprende rápido.
- **6 casos gramaticais**: substantivos e adjetivos mudam de terminação dependendo da função na frase (sujeito, objeto, posse, etc.). É o coração da gramática russa.
- **Gênero gramatical** (masculino/feminino/neutro), parecido com o português, mas afetando muito mais coisas.
- **Aspecto verbal**: cada ação tem dois verbos — um para "ação completa" e outro para "ação em andamento/repetida".

> 💡 Nos dois primeiros módulos vamos usar **cirílico + romanização** (a pronúncia escrita em letras latinas, tipo "privet") para você não se afogar logo de cara. Depois disso, o curso passa a ser 100% em cirílico — é assim que você aprende a ler russo de verdade.

## Como aproveitar bem este curso

- **Clique nas palavras em russo** ao longo das lições (inclusive dentro de tabelas e exemplos) para ouvir a pronúncia — todo texto em cirílico do curso é clicável.
- Use o **teclado cirílico virtual** nos exercícios de digitação em vez de tentar decorar um layout de teclado novo.
- Não pule os exercícios de escuta e fala — russo tem sons que não existem em português, e só treinar o ouvido resolve isso.
""",
            [
                ex("quiz", "Qual escala este curso usa para medir seu nível?",
                   "CEFR (A1 a C1)", ["CEFR (A1 a C1)", "TOEFL", "ENEM"], audio_lang="pt-BR"),
                ex("quiz", "Por que o russo costuma ser mais desafiador para falantes de português do que o inglês?",
                   "Tem alfabeto novo, 6 casos gramaticais e aspecto verbal",
                   ["Tem alfabeto novo, 6 casos gramaticais e aspecto verbal", "Não tem nenhuma diferença relevante", "É quase idêntico ao português"],
                   audio_lang="pt-BR"),
                ex("quiz", "A partir de qual módulo o curso passa a ser 100% em cirílico, sem romanização?",
                   "A partir do Módulo 2", ["A partir do Módulo 2", "Nunca, sempre haverá romanização", "Só no último módulo (C1)"],
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

> 💡 Você vai reencontrar esses números no Módulo 5 (Genitivo), quando aprender como eles mudam a terminação do substantivo que contam.
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
))

# ============================================================
# MODULO 1 - Frases Basicas sem Verbo Ser (A1)
# ============================================================
MODULES.append(module(
    "frases-basicas-sem-verbo-ser",
    'Módulo 1 — Frases Básicas sem Verbo "Ser" (A1)',
    "Pronomes pessoais, gênero dos substantivos, frases sem cópula no presente e plural básico. A partir daqui, só cirílico.",
    [
        topic(
            "pronomes-pessoais-russo",
            "Pronomes pessoais",
            """
# Pronomes pessoais

| Russo | Português |
|---|---|
| я | eu |
| ты | tu / você (informal) |
| он | ele |
| она | ela |
| оно | ele/ela (neutro) |
| мы | nós |
| вы | vocês / você (formal) |
| они | eles/elas |

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
| consoante | masculino | стол (mesa) |
| -а / -я | feminino | книга (livro), земля (terra) |
| -о / -е | neutro | окно (janela), море (mar) |
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
            ],
        ),
        topic(
            "frases-sem-verbo-ser",
            'Frases sem o verbo "ser/estar"',
            """
# Frases sem o verbo "ser/estar"

No **presente**, o russo **não usa** o verbo "ser/estar" (быть) — a frase simplesmente junta sujeito e predicado:

```
Я студент.        (Eu [sou] estudante.)
Она врач.         (Ela [é] médica.)
Это книга.        (Isso [é] um livro.)
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
            ],
        ),
    ],
))

# ============================================================
# MODULO 2 - Caso Nominativo e Perguntas (A1)
# ============================================================
MODULES.append(module(
    "caso-nominativo-e-perguntas",
    "Módulo 2 — Caso Nominativo e Perguntas (A1)",
    "O caso Nominativo, palavras interrogativas e negação com не.",
    [
        topic(
            "caso-nominativo",
            "O caso Nominativo",
            """
# O caso Nominativo

O russo tem **6 casos gramaticais** — cada um muda a terminação de substantivos, adjetivos e pronomes dependendo da função deles na frase. Vamos conhecer o primeiro (e mais simples): o **Nominativo**.

## Para que serve

O Nominativo é o caso do **sujeito** da frase — quem pratica a ação, ou do que se fala. É também a forma que aparece nos dicionários (a forma "padrão" que você já vem usando até aqui!).

```
Студент читает.        (O estudante lê.) — студент está no Nominativo, é o sujeito
Книга на столе.        (O livro está na mesa.) — книга está no Nominativo
```

## Os 6 casos, de relance

Não precisa decorar agora, mas vale já ter o mapa geral: **Nominativo** (sujeito, este módulo), **Acusativo** (objeto direto, Módulo 4), **Genitivo** (posse, Módulo 5), **Dativo** (objeto indireto, Módulo 6), **Instrumental** (meio/instrumento, Módulo 7) e **Preposicional** (lugar/assunto, Módulo 3). Cada módulo a partir de agora apresenta um caso novo.

> 🎯 Você já vem usando o Nominativo sem saber, desde o Módulo 0! A partir de agora, cada módulo novo introduz mais um caso, mudando a terminação das palavras conforme a função na frase.
""",
            [
                ex("quiz", "Para que serve o caso Nominativo?",
                   "Indicar o sujeito da frase",
                   ["Indicar o sujeito da frase", "Indicar posse", "Indicar objeto direto"]),
                ex("text", "Traduza: O estudante lê. (студент + читает)", "студент читает"),
                ex("quiz", "Quantos casos gramaticais o russo tem ao todo?",
                   "6", ["4", "6", "8"]),
                ex("audio", "Escute e transcreva:", "книга на столе", audio_text="книга на столе"),
                ex("speak", "Repita em voz alta:", "студент читает", audio_text="студент читает"),
            ],
        ),
        topic(
            "palavras-interrogativas",
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

## где vs куда

Repare que existem duas palavras para "onde": **где** pergunta sobre localização parada ("onde você está?"), e **куда** pergunta sobre destino/direção ("para onde você vai?"). Você vai ver essa mesma distinção nos casos gramaticais mais adiante (Preposicional x Acusativo, Módulos 3 e 4) — é um padrão que se repete bastante em russo.

> 💡 Frases com palavra interrogativa não precisam de nenhuma partícula extra — a entonação e a palavra já deixam claro que é uma pergunta.
""",
            [
                ex("quiz", 'Qual palavra significa "onde?"', "где", ["где", "куда", "когда"]),
                ex("text", "Traduza: O que é isso? (что + это)", "что это"),
                ex("audio", "Escute e transcreva:", "как дела", audio_text="как дела"),
                ex("quiz", 'Qual a diferença entre "где" e "куда"?',
                   '"где" pergunta localização, "куда" pergunta destino',
                   ['"где" pergunta localização, "куда" pergunta destino', "são sinônimos perfeitos", '"куда" só se usa no passado']),
                ex("speak", "Repita em voz alta:", "почему", audio_text="почему"),
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
Это не моя книга.      Isso não é o meu livro. (nega "moя", "meu", não o fato de ser um livro)
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
            ],
        ),
    ],
))

# ============================================================
# MODULO 3 - Caso Preposicional (A1-A2)
# ============================================================
MODULES.append(module(
    "caso-preposicional",
    "Módulo 3 — Caso Preposicional (A1–A2)",
    "O caso Preposicional para indicar lugar (в/на), assunto (о/об) e os pronomes pessoais no Preposicional.",
    [
        topic(
            "preposicional-lugar",
            "Preposicional: falando sobre lugar",
            """
# Caso Preposicional: falando sobre lugar

O **Preposicional** (Предложный падеж) é usado depois das preposições **в** (em, dentro de) e **на** (em, sobre/em cima de) para indicar **localização**. Ele só existe **depois de uma preposição** — por isso o nome — e é o único caso russo que nunca aparece sozinho.

## Terminações no Preposicional (singular)

| Gênero | Terminação | Exemplo (Nominativo -> Preposicional) |
|---|---|---|
| Masculino/Neutro | -е | стол -> столе, окно -> окне |
| Feminino (-а) | -е | комната -> комнате |
| Feminino (-ь) | -и | дверь -> двери |

## Exemplos

```
Книга на столе.         O livro está na mesa.
Я в комнате.             Eu estou no quarto.
Он живёт в Москве.       Ele mora em Moscou.
```

> 🎯 Repare: o verbo "estar" também some aqui — "я в комнате" já significa "eu estou no quarto", sem precisar de verbo.
""",
            [
                ex("text", 'Complete a frase com a forma correta de "стол" no Preposicional: "Книга на ___."',
                   "столе"),
                ex("quiz", 'Qual preposição indica "dentro de" + Preposicional?',
                   "в", ["в", "на", "о"]),
                ex("text", "Traduza: Ele mora em Moscou. (он + живёт + в + Москве)",
                   "он живёт в москве"),
                ex("audio", "Escute e transcreva:", "я в комнате", audio_text="я в комнате"),
                ex("speak", "Repita em voz alta:", "книга на столе", audio_text="книга на столе"),
            ],
        ),
        topic(
            "preposicional-assunto",
            "Preposicional: falando SOBRE algo",
            """
# Caso Preposicional: falando SOBRE algo

Além de lugar, o Preposicional também aparece depois de **о** (sobre, a respeito de) — que vira **об** antes de palavra iniciada por som de vogal:

```
Я думаю о тебе.             Eu penso em você.
Мы говорим о книге.         Nós falamos sobre o livro.
Она рассказывает об Америке. Ela fala sobre a América. (об, porque "Америке" começa com vogal)
```

## Verbos comuns que pedem "о + Preposicional"

думать о (pensar em/sobre), говорить о (falar sobre), рассказывать о (contar sobre), знать о (saber sobre), мечтать о (sonhar com) — todos esses verbos "puxam" o complemento para o Preposicional com о/об.

> 💡 É parecido com "verbos de regência" em português (ex: "gostar DE", "pensar EM") — em russo, o verbo define não só a preposição, mas também o caso da palavra seguinte.
""",
            [
                ex("quiz", "Qual forma de \"о\" se usa antes de palavra iniciada por som de vogal?",
                   "об", ["об", "о", "на"]),
                ex("text", "Traduza: Nós falamos sobre o livro. (мы + говорим + о + книге)",
                   "мы говорим о книге"),
                ex("quiz", 'Complete: "Она рассказывает ___ Америке." (ela fala sobre a América)',
                   "об", ["о", "об", "на"]),
                ex("audio", "Escute e transcreva:", "я думаю о тебе", audio_text="я думаю о тебе"),
                ex("speak", "Repita em voz alta:", "мы говорим о книге", audio_text="мы говорим о книге"),
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
            ],
        ),
    ],
))

# ============================================================
# MODULO 4 - Caso Acusativo (A2)
# ============================================================
MODULES.append(module(
    "caso-acusativo",
    "Módulo 4 — Caso Acusativo (A2)",
    "O caso Acusativo como objeto direto, para indicar direção (contraste com o Preposicional) e os pronomes pessoais no Acusativo.",
    [
        topic(
            "acusativo-objeto-direto",
            "Acusativo: o objeto direto",
            """
# Caso Acusativo: o objeto direto

O **Acusativo** (Винительный падеж) marca o **objeto direto** de um verbo — quem ou o que recebe a ação.

## Terminações no Acusativo (singular)

| Gênero | Regra | Exemplo |
|---|---|---|
| Masculino inanimado | igual ao Nominativo | Я читаю журнал. (Eu leio a revista.) |
| Masculino animado | igual ao Genitivo | Я вижу студента. (Eu vejo o estudante.) |
| Feminino (-а -> -у) | -а vira -у | Я читаю книгу. (Eu leio o livro.) |
| Neutro | igual ao Nominativo | Я вижу окно. (Eu vejo a janela.) |

> ⚠️ Repare na diferença entre substantivos **animados** (pessoas/animais) e **inanimados** (objetos) — isso afeta a terminação no masculino. Vamos falar mais disso no módulo de Genitivo.
""",
            [
                ex("quiz", 'Como fica "книга" (livro) no Acusativo?',
                   "книгу", ["книгу", "книге", "книги"]),
                ex("text", "Traduza: Eu leio o livro. (я + читаю + книгу)",
                   "я читаю книгу"),
                ex("quiz", "No Acusativo, um substantivo masculino INANIMADO (ex: журнал):",
                   "fica igual ao Nominativo", ["fica igual ao Nominativo", "muda para -а", "muda para -у"]),
                ex("audio", "Escute e transcreva:", "я вижу студента", audio_text="я вижу студента"),
                ex("speak", "Repita em voz alta:", "я читаю книгу", audio_text="я читаю книгу"),
            ],
        ),
        topic(
            "acusativo-direcao",
            "Acusativo: indicando direção",
            """
# Caso Acusativo: indicando direção

Assim como o Preposicional indica "estar em" um lugar, o Acusativo depois de **в/на** indica "ir para" um lugar — a diferença entre **onde** e **para onde**:

```
Я в школе.           (Preposicional) Eu estou NA escola.
Я иду в школу.       (Acusativo)     Eu vou PARA a escola.

Он на работе.        Ele está NO trabalho.
Он идёт на работу.   Ele vai PARA o trabalho.
```

> 🎯 Essa distinção (Preposicional = onde / Acusativo = para onde) é um dos pontos mais importantes da gramática russa — o português não marca essa diferença de forma tão clara.
""",
            [
                ex("quiz", 'Qual caso indica "PARA ONDE" (movimento/direção)?',
                   "Acusativo", ["Acusativo", "Preposicional", "Nominativo"]),
                ex("text", "Traduza: Eu vou para a escola. (я + иду + в + школу)",
                   "я иду в школу"),
                ex("quiz", 'Complete com o caso certo: "Он ___ на работе." (ele está NO trabalho, sem movimento)',
                   "Preposicional (fica igual)", ["Preposicional (fica igual)", "Acusativo (muda a terminação)", "Nenhum dos dois"]),
                ex("audio", "Escute e transcreva:", "он идёт на работу", audio_text="он идёт на работу"),
            ],
        ),
        topic(
            "acusativo-pronomes",
            "Acusativo dos pronomes pessoais",
            """
# Acusativo dos pronomes pessoais

Os pronomes pessoais também têm forma própria no Acusativo, usada como objeto direto:

| Nominativo | Acusativo |
|---|---|
| я | меня |
| ты | тебя |
| он/оно | его |
| она | её |
| мы | нас |
| вы | вас |
| они | их |

```
Он видит меня.        Ele me vê.
Я люблю тебя.         Eu te amo.
Мы знаем их.          Nós os conhecemos.
```

> 💡 Repare que "его" (ele/it) e "её" (ela) no Acusativo são os mesmos que no Genitivo — isso vai facilitar quando você chegar ao Módulo 5.
""",
            [
                ex("quiz", 'Qual a forma de "я" (eu) no Acusativo?',
                   "меня", ["меня", "мне", "я"]),
                ex("text", "Traduza: Eu te amo. (я + люблю + тебя)",
                   "я люблю тебя"),
                ex("quiz", 'Qual a forma de "они" (eles) no Acusativo?',
                   "их", ["их", "им", "они"]),
                ex("audio", "Escute e transcreva:", "он видит меня", audio_text="он видит меня"),
            ],
        ),
    ],
))

# ============================================================
# MODULO 5 - Caso Genitivo (A2-B1)
# ============================================================
MODULES.append(module(
    "caso-genitivo",
    "Módulo 5 — Caso Genitivo (A2–B1)",
    "O caso Genitivo para posse, a construção \"ter\" em russo, negação de existência, quantidades e as preposições mais comuns com Genitivo.",
    [
        topic(
            "genitivo-posse",
            'Genitivo: posse e a construção "ter"',
            """
# Caso Genitivo: posse

O **Genitivo** (Родительный падеж) indica **posse** — equivalente ao "de" do português ("o livro DA Ana").

## Terminações no Genitivo (singular)

| Gênero | Terminação | Exemplo (Nominativo -> Genitivo) |
|---|---|---|
| Masculino/Neutro | -а/-я | стол -> стола, окно -> окна |
| Feminino (-а) | -ы/-и | книга -> книги |

## A construção "ter" em russo: у + Genitivo + есть

O russo não tem um verbo "ter" direto como o português — usa-se **у + [pessoa no Genitivo] + есть + [coisa no Nominativo]**:

```
У меня есть книга.       Eu tenho um livro. (literalmente "junto a mim há um livro")
У него есть машина.      Ele tem um carro.
```

| Pronome | No Genitivo |
|---|---|
| я | меня |
| ты | тебя |
| он/оно | него |
| она | неё |
| мы | нас |
| вы | вас |
| они | них |
""",
            [
                ex("quiz", "Como se diz \"eu tenho\" em russo (construção com у + Genitivo)?",
                   "у меня есть", ["у меня есть", "я имею", "я есть"]),
                ex("text", "Traduza: Eu tenho um livro. (у + меня + есть + книга)",
                   "у меня есть книга"),
                ex("quiz", 'Qual a forma de "она" (ela) no Genitivo?',
                   "неё", ["неё", "него", "них"]),
                ex("audio", "Escute e transcreva:", "у него есть машина", audio_text="у него есть машина"),
                ex("speak", "Repita em voz alta:", "у меня есть книга", audio_text="у меня есть книга"),
            ],
        ),
        topic(
            "genitivo-negacao-quantidade",
            "Genitivo: negação de existência e quantidades",
            """
# Genitivo: negação de existência e quantidades

## "Não há" / "não tenho" — нет + Genitivo

```
У меня нет книги.        Eu não tenho um livro. (literalmente "junto a mim não há de livro")
Здесь нет воды.          Aqui não há água.
```

## Números e quantidades

Depois de **2, 3, 4** (e números terminados neles, exceto 12–14), o substantivo vai para o Genitivo **singular**. Depois de **5 em diante**, vai para o Genitivo **plural**:

```
одна книга          (1 livro — Nominativo)
две книги           (2 livros — Genitivo singular)
пять книг           (5 livros — Genitivo plural)
```

> 🎯 Repare que "5 livros" (пять книг) usa uma forma do Genitivo plural que costuma ser mais curta que o Nominativo — vale prestar atenção a essa forma "reduzida" em cada palavra nova.
""",
            [
                ex("text", "Traduza: Eu não tenho um livro. (у + меня + нет + книги)",
                   "у меня нет книги"),
                ex("quiz", "Depois do número 5, o substantivo vai para:",
                   "Genitivo plural", ["Genitivo plural", "Genitivo singular", "Nominativo"]),
                ex("quiz", "Depois dos números 2, 3 e 4, o substantivo vai para:",
                   "Genitivo singular", ["Genitivo singular", "Genitivo plural", "Acusativo"]),
                ex("audio", "Escute e transcreva:", "здесь нет воды", audio_text="здесь нет воды"),
            ],
        ),
        topic(
            "genitivo-preposicoes",
            "Genitivo com preposições: у, для, из, до, после",
            """
# Genitivo com preposições

Além de indicar posse, o Genitivo é o caso exigido por várias preposições muito usadas no dia a dia:

| Preposição | Sentido | Exemplo |
|---|---|---|
| у | perto de / na casa de | Я у друга. (Estou na casa de um amigo.) |
| для | para (finalidade) | Это подарок для мамы. (Isso é um presente para a mãe.) |
| из | de, vindo de (origem) | Я из Бразилии. (Eu sou/venho do Brasil.) |
| до | até (lugar/tempo) | До завтра! (Até amanhã!) |
| после | depois de | после работы (depois do trabalho) |

```
Я иду из школы.          Eu venho da escola. (де onde, com "из")
Это письмо для тебя.     Esta carta é para você.
```

> 💡 "из" (de onde algo vem) forma um contraste natural com "в"/"на" + Acusativo (para onde vai) que você viu no Módulo 4 — "в школу" (para a escola) vira "из школы" (da escola) na volta.
""",
            [
                ex("quiz", 'Qual preposição indica origem ("vindo de")?',
                   "из", ["из", "для", "до"]),
                ex("text", "Traduza: Eu sou do Brasil. (я + из + Бразилии)",
                   "я из бразилии"),
                ex("quiz", 'Qual preposição significa "para" (finalidade), como em "presente para a mãe"?',
                   "для", ["для", "у", "после"]),
                ex("audio", "Escute e transcreva:", "это письмо для тебя", audio_text="это письмо для тебя"),
            ],
        ),
    ],
))

# ============================================================
# MODULO 6 - Caso Dativo (B1)
# ============================================================
MODULES.append(module(
    "caso-dativo",
    "Módulo 6 — Caso Dativo (B1)",
    "O caso Dativo como objeto indireto, em construções impessoais (мне нравится) e com as preposições к e по.",
    [
        topic(
            "dativo-objeto-indireto",
            "Dativo: o objeto indireto",
            """
# Caso Dativo: o objeto indireto

O **Dativo** (Дательный падеж) marca o **objeto indireto** — para quem/a quem algo é dado, dito, etc. Equivale ao "para"/"a" do português.

## Terminações no Dativo (singular)

| Gênero | Terminação | Exemplo |
|---|---|---|
| Masculino/Neutro | -у/-ю | стол -> столу, окно -> окну |
| Feminino (-а) | -е | сестра -> сестре |

## Exemplo

```
Я даю книгу сестре.      Eu dou o livro para a irmã. (сестре = Dativo)
Он пишет другу.          Ele escreve para o amigo.
```
""",
            [
                ex("text", 'Complete no Dativo: "Я даю книгу ___." (para a irmã: сестра)',
                   "сестре"),
                ex("quiz", "O caso Dativo marca:",
                   "o objeto indireto (para quem)", ["o objeto indireto (para quem)", "o sujeito", "posse"]),
                ex("audio", "Escute e transcreva:", "он пишет другу", audio_text="он пишет другу"),
                ex("speak", "Repita em voz alta:", "я даю книгу сестре", audio_text="я даю книгу сестре"),
            ],
        ),
        topic(
            "dativo-construcoes-impessoais",
            "Dativo em construções impessoais",
            """
# Dativo em construções impessoais

Um uso muito comum do Dativo é em frases sem sujeito "de verdade" — a pessoa aparece no Dativo, e o que ela sente/precisa/tem é o sujeito gramatical:

```
Мне нравится музыка.       Eu gosto de música. (literalmente "para mim agrada música")
Мне нужно время.           Eu preciso de tempo. ("para mim é necessário tempo")
Ей двадцать лет.           Ela tem vinte anos. ("para ela [são] vinte anos")
```

| Pronome | No Dativo |
|---|---|
| я | мне |
| ты | тебе |
| он/оно | ему |
| она | ей |
| мы | нам |
| вы | вам |
| они | им |

> 🎯 Essa estrutura ("para mim agrada" em vez de "eu gosto") é super comum em russo — muito diferente da estrutura ativa "eu gosto" do português.
""",
            [
                ex("text", "Traduza: Eu gosto de música. (мне + нравится + музыка)",
                   "мне нравится музыка"),
                ex("quiz", 'Qual a forma de "она" (ela) no Dativo?',
                   "ей", ["ей", "её", "неё"]),
                ex("audio", "Escute e transcreva:", "мне нужно время", audio_text="мне нужно время"),
                ex("quiz", 'Como se traduz literalmente "Ей двадцать лет"?',
                   'Para ela [são] vinte anos', ['Para ela [são] vinte anos', "Ela quer vinte anos", "Ela vinte anos atrás"]),
            ],
        ),
        topic(
            "dativo-preposicoes",
            "Dativo com as preposições к e по",
            """
# Dativo com as preposições к e по

Duas preposições muito frequentes exigem o Dativo:

| Preposição | Sentido | Exemplo |
|---|---|---|
| к | em direção a (uma pessoa/lugar), aproximação | Я иду к врачу. (Eu vou ao médico.) |
| по | por, ao longo de; "de acordo com" | Мы гуляем по парку. (Nós passeamos pelo parque.) |

```
Она идёт ко мне.          Ela vem até mim. (к -> ко antes de "мне", por causa da pronúncia)
Он говорит по телефону.    Ele fala por telefone.
```

> 💡 "к" contrasta com "в/на + Acusativo" (Módulo 4): "к врачу" é "em direção ao médico" (chegando perto), enquanto "в школу" é "para dentro da escola" (entrando).
""",
            [
                ex("quiz", 'Qual preposição indica "em direção a" uma pessoa/lugar?',
                   "к", ["к", "по", "у"]),
                ex("text", "Traduza: Eu vou ao médico. (я + иду + к + врачу)",
                   "я иду к врачу"),
                ex("quiz", 'Qual forma "к" assume antes de "мне" (por pronúncia)?',
                   "ко", ["ко", "кы", "ка"]),
                ex("audio", "Escute e transcreva:", "он говорит по телефону", audio_text="он говорит по телефону"),
            ],
        ),
    ],
))

# ============================================================
# MODULO 7 - Caso Instrumental (B1)
# ============================================================
MODULES.append(module(
    "caso-instrumental",
    "Módulo 7 — Caso Instrumental (B1)",
    "O caso Instrumental como meio/instrumento, companhia, com o verbo \"ser\" no passado/futuro, e em expressões de tempo.",
    [
        topic(
            "instrumental-meio",
            "Instrumental: o meio/instrumento",
            """
# Caso Instrumental: o meio/instrumento

O **Instrumental** (Творительный падеж) indica **com o quê** (o instrumento/meio) uma ação é feita.

## Terminações no Instrumental (singular)

| Gênero | Terminação | Exemplo |
|---|---|---|
| Masculino/Neutro | -ом/-ем | стол -> столом, окно -> окном |
| Feminino (-а) | -ой/-ей | ручка -> ручкой |

## Exemplo

```
Я пишу ручкой.          Eu escrevo com uma caneta.
Он ест вилкой.          Ele come com um garfo.
```
""",
            [
                ex("text", 'Complete no Instrumental: "Я пишу ___." (com uma caneta: ручка)',
                   "ручкой"),
                ex("quiz", "O caso Instrumental indica:",
                   "o meio/instrumento de uma ação", ["o meio/instrumento de uma ação", "posse", "objeto direto"]),
                ex("audio", "Escute e transcreva:", "он ест вилкой", audio_text="он ест вилкой"),
                ex("speak", "Repita em voz alta:", "я пишу ручкой", audio_text="я пишу ручкой"),
            ],
        ),
        topic(
            "instrumental-companhia",
            'Instrumental: companhia e o verbo "ser" no passado/futuro',
            """
# Instrumental: companhia e o verbo "ser" no passado/futuro

## С + Instrumental ("com", companhia)

```
Я иду с другом.          Eu vou com um amigo. (другом = Instrumental)
Она говорит с мамой.     Ela fala com a mãe.
```

## быть + Instrumental (profissão/estado no passado/futuro)

Quando o verbo "ser" aparece (no passado ou futuro — lembre que ele some no presente), a profissão ou característica geralmente vai para o **Instrumental**:

```
Он был врачом.          Ele era/foi médico. (врачом = Instrumental)
Она будет учителем.     Ela será professora.
```
""",
            [
                ex("text", "Traduza: Eu vou com um amigo. (я + иду + с + другом)",
                   "я иду с другом"),
                ex("quiz", 'Complete: "Он был ___." (ele era médico: врач)',
                   "врачом", ["врачом", "врача", "врачу"]),
                ex("audio", "Escute e transcreva:", "она будет учителем", audio_text="она будет учителем"),
                ex("speak", "Repita em voz alta:", "она говорит с мамой", audio_text="она говорит с мамой"),
            ],
        ),
        topic(
            "instrumental-tempo-e-plural",
            "Instrumental de tempo e no plural",
            """
# Instrumental de tempo e no plural

## Expressões de tempo no Instrumental

Estações do ano, partes do dia e alguns períodos usam o Instrumental para dizer "durante"/"de":

| Nominativo | Instrumental (expressão de tempo) |
|---|---|
| зима (inverno) | зимой (no inverno) |
| лето (verão) | летом (no verão) |
| утро (manhã) | утром (de manhã) |
| вечер (noite/entardecer) | вечером (à noite) |

```
Зимой холодно.          No inverno faz frio.
Утром я пью кофе.       De manhã eu tomo café.
```

## Instrumental no plural

No plural, todos os gêneros seguem a mesma terminação: **-ами/-ями**:

```
столы -> столами        (com as mesas)
книги -> книгами        (com os livros)
```

> 💡 Essa uniformidade no plural (todo mundo vira -ами/-ями, não importa o gênero) é uma boa notícia: o Instrumental plural é mais fácil que o singular.
""",
            [
                ex("quiz", 'Como se diz "no inverno" em russo?',
                   "зимой", ["зимой", "зима", "зиму"]),
                ex("text", "Traduza: De manhã eu tomo café. (утром + я + пью + кофе)",
                   "утром я пью кофе"),
                ex("quiz", "No plural, qual terminação o Instrumental usa (para todos os gêneros)?",
                   "-ами/-ями", ["-ами/-ями", "-ом/-ем", "-ой/-ей"]),
                ex("audio", "Escute e transcreva:", "вечером", audio_text="вечером"),
            ],
        ),
    ],
))

# ============================================================
# MODULO 8 - Presente dos Verbos (A2-B1)
# ============================================================
MODULES.append(module(
    "presente-dos-verbos-russo",
    "Módulo 8 — Presente dos Verbos (A2–B1)",
    "As duas conjugações do presente e os verbos irregulares mais comuns.",
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
            ],
        ),
    ],
))

# ============================================================
# MODULO 9 - Aspecto Verbal (B1-B2)
# ============================================================
MODULES.append(module(
    "aspecto-verbal",
    "Módulo 9 — Aspecto Verbal: Perfectivo x Imperfectivo (B1–B2)",
    "O conceito mais difícil do russo: cada verbo tem uma versão para processo/repetição e outra para ação completa.",
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

Escolher o aspecto errado não é só um "erro de gramática" pequeno — muitas vezes muda completamente o sentido da frase (ver Módulo 9, tópico 3) ou soa muito estranho para um falante nativo. É um dos poucos pontos em que vale mais a pena "sentir" o padrão com muito exemplo do que decorar uma regra fixa.
""",
            [
                ex("quiz", "O aspecto PERFECTIVO indica:",
                   "uma ação completa, com resultado", ["uma ação completa, com resultado", "uma ação repetida", "uma ação no futuro"]),
                ex("quiz", "O aspecto IMPERFECTIVO indica:",
                   "processo, ação em andamento ou repetida", ["processo, ação em andamento ou repetida", "só o futuro", "só o passado"]),
                ex("quiz", "Aspecto verbal é a mesma coisa que tempo verbal (presente/passado/futuro)?",
                   "Não, é uma categoria independente do tempo", ["Não, é uma categoria independente do tempo", "Sim, são sinônimos", "Só existe no futuro"]),
                ex("audio", "Escute e transcreva:", "я прочитал книгу", audio_text="я прочитал книгу"),
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
            ],
        ),
    ],
))

# ============================================================
# MODULO 10 - Passado e Futuro (B1-B2)
# ============================================================
MODULES.append(module(
    "passado-e-futuro-russo",
    "Módulo 10 — Passado e Futuro (B1–B2)",
    "O passado com concordância de gênero, o futuro simples (perfectivo) vs composto (imperfectivo), e o modo condicional com бы.",
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
            ],
        ),
        topic(
            "futuro-simples-e-composto",
            "Futuro: simples e composto",
            """
# Futuro: simples e composto

O futuro em russo depende do **aspecto** do verbo:

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
            ],
        ),
        topic(
            "modo-condicional-russo",
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
            ],
        ),
    ],
))

# ============================================================
# MODULO 11 - Adjetivos e Comparacao (B2)
# ============================================================
MODULES.append(module(
    "adjetivos-e-comparacao-russo",
    "Módulo 11 — Adjetivos e Comparação (B2)",
    "Concordância de adjetivos em gênero/número/caso, comparativo/superlativo, e a forma curta dos adjetivos.",
    [
        topic(
            "concordancia-de-adjetivos",
            "Concordância de adjetivos",
            """
# Concordância de adjetivos

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
            ],
        ),
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
            ],
        ),
        topic(
            "adjetivos-forma-curta-russo",
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
            ],
        ),
    ],
))

# ============================================================
# MODULO 12 - Verbos de Movimento (B2)
# ============================================================
MODULES.append(module(
    "verbos-de-movimento",
    "Módulo 12 — Verbos de Movimento (B2)",
    "O capítulo clássico do russo: идти/ходить e ехать/ездить (unidirecional vs multidirecional), outros pares comuns, e os verbos de movimento com prefixo.",
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
""",
            [
                ex("quiz", "Qual verbo indica ir de veículo AGORA, numa direção?",
                   "ехать", ["ехать", "ездить", "идти"]),
                ex("text", "Traduza: Eu estou indo para Moscou. (я + еду + в + Москву)",
                   "я еду в москву"),
                ex("quiz", "Qual verbo indica ir de carro TODO DIA (repetição)?",
                   "ездить", ["ездить", "ехать", "ходить"]),
                ex("audio", "Escute e transcreva:", "я езжу на работу на машине", audio_text="я езжу на работу на машине"),
            ],
        ),
        topic(
            "verbos-de-movimento-prefixados",
            "Verbos de movimento com prefixo",
            """
# Verbos de movimento com prefixo

Adicionar um prefixo a идти/ехать cria verbos novos com sentido preciso de direção — e, de quebra, já forma pares de aspecto perfectivo/imperfectivo (Módulo 9)!

| Prefixo | Sentido | Exemplo (a pé) |
|---|---|---|
| при- | chegar | прийти (chegar, perfectivo) |
| у- | sair, ir embora | уйти (sair, perfectivo) |
| в(о)- | entrar | войти (entrar, perfectivo) |
| вы- | sair de dentro | выйти (sair de dentro, perfectivo) |
| пере- | atravessar | перейти (atravessar, perfectivo) |

```
Он пришёл домой.        Ele chegou em casa.
Она вышла из комнаты.   Ela saiu do quarto.
Мы перешли улицу.       Nós atravessamos a rua.
```

> 🎯 Esses verbos prefixados já são sempre **unidirecionais** por natureza (um prefixo não faz sentido com o "multidirecional" ходить/ездить) — o par imperfectivo correspondente troca a raiz -йти por -ходить: прийти -> приходить, уйти -> уходить.
""",
            [
                ex("quiz", 'Qual prefixo indica "chegar"?',
                   "при-", ["при-", "у-", "вы-"]),
                ex("text", "Traduza: Ele chegou em casa. (он + пришёл + домой)",
                   "он пришёл домой"),
                ex("quiz", 'Qual verbo significa "sair, ir embora"?',
                   "уйти", ["уйти", "войти", "перейти"]),
                ex("audio", "Escute e transcreva:", "мы перешли улицу", audio_text="мы перешли улицу"),
            ],
        ),
    ],
))

# ============================================================
# MODULO 13 - Reflexivos e Imperativo (B2-C1)
# ============================================================
MODULES.append(module(
    "reflexivos-e-imperativo",
    "Módulo 13 — Verbos Reflexivos e Imperativo (B2–C1)",
    "Verbos com a partícula -ся/-сь, o modo imperativo e o imperativo negativo.",
    [
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
            ],
        ),
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
                ex("audio", "Escute e transcreva:", "говорите!", audio_text="говорите"),
            ],
        ),
        topic(
            "imperativo-negativo-russo",
            "Imperativo negativo e o aspecto no imperativo",
            """
# Imperativo negativo e o aspecto no imperativo

## Negando uma ordem: не + imperativo

Basta colocar **не** antes do imperativo, exatamente como na negação comum (Módulo 2):

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
            ],
        ),
    ],
))

# ============================================================
# MODULO 14 - Participios e Gerundios (C1)
# ============================================================
MODULES.append(module(
    "participios-e-gerundios",
    "Módulo 14 — Particípios e Gerúndios (C1)",
    "Причастия (particípios) e деепричастия (gerúndios) — as formas verbais mais avançadas do russo, incluindo o particípio passivo curto.",
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

> 🎯 Particípios são muito comuns na escrita formal/literária russa, mas raros na fala cotidiana — no dia a dia, russos preferem orações com "который" (que): "человек, который читает книгу" em vez de "человек, читающий книгу".
""",
            [
                ex("quiz", "O particípio ATIVO indica:",
                   "quem pratica a ação", ["quem pratica a ação", "quem sofre a ação", "o tempo verbal"]),
                ex("quiz", "Na fala cotidiana, russos costumam substituir particípios por orações com:",
                   "который (que)", ["который (que)", "и (e)", "но (mas)"]),
                ex("text", "Traduza usando \"который\" (mais natural na fala): a pessoa que lê o livro. (человек + который + читает + книгу)",
                   "человек который читает книгу"),
                ex("audio", "Escute e transcreva:", "книга читаемая всеми", audio_text="книга, читаемая всеми"),
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
            ],
        ),
        topic(
            "participio-passivo-curto-russo",
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

> 🎯 Essa construção (particípio passivo curto + быть implícito) é como o russo forma a "voz passiva de resultado" — equivalente a "está feito/fechado/escrito" em português. É uma das estruturas mais usadas do nível C1 e vale a pena reconhecer de cara.
""",
            [
                ex("quiz", 'Qual a forma curta feminina de "закрытый" (fechado)?',
                   "закрыта", ["закрыта", "закрытая", "закрыто"]),
                ex("text", "Traduza: A carta está escrita. (письмо + написано)", "письмо написано"),
                ex("quiz", "O particípio passivo curto concorda em:",
                   "gênero e número (não em caso)", ["gênero e número (não em caso)", "caso e gênero", "nada, é sempre invariável"]),
                ex("audio", "Escute e transcreva:", "магазин закрыт", audio_text="магазин закрыт"),
            ],
        ),
    ],
))

# ============================================================
# MODULO 15 - Discurso Indireto e Revisao (C1)
# ============================================================
MODULES.append(module(
    "discurso-indireto-e-revisao-russo",
    "Módulo 15 — Discurso Indireto e Revisão (C1)",
    "Discurso indireto (sem backshift de tempo) e uma revisão integrada de todo o curso.",
    [
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
            ],
        ),
        topic(
            "revisao-integrada-russo",
            "Revisão integrada: do alfabeto ao discurso indireto",
            """
# Revisão integrada: do alfabeto ao discurso indireto

Parabéns por chegar até aqui! Você percorreu um caminho enorme — do alfabeto cirílico aos 6 casos, ao aspecto verbal e aos particípios.

## Panorama rápido

| Nível | O que você aprendeu |
|---|---|
| A1 | alfabeto, saudações, frases sem verbo "ser", Nominativo |
| A2 | Preposicional, Acusativo, Genitivo |
| B1 | Dativo, Instrumental, presente dos verbos, aspecto verbal |
| B2 | passado/futuro, condicional, adjetivos, verbos de movimento |
| C1 | reflexivos, imperativo, particípios, gerúndios, discurso indireto |

## Os 6 casos, resumidos

| Caso | Pergunta que responde | Exemplo de uso |
|---|---|---|
| Nominativo | quem/o quê? (sujeito) | Студент читает. |
| Acusativo | a quem/o quê? (objeto direto) | Я читаю книгу. |
| Genitivo | de quem/de quê? | У меня есть книга. |
| Dativo | a quem/para quem? | Я даю книгу сестре. |
| Instrumental | com quê/com quem? | Я пишу ручкой. |
| Preposicional | sobre o quê/onde? | Я думаю о тебе. |

> 🏆 Russo é reconhecidamente uma das línguas mais desafiadoras para falantes de português — chegar até aqui já é uma conquista enorme. O próximo passo é praticar com conteúdo autêntico (séries, música, conversas) para fixar o que foi visto aqui.
""",
            [
                ex("quiz", "Qual caso é usado para o objeto direto?",
                   "Acusativo", ["Acusativo", "Dativo", "Instrumental"]),
                ex("quiz", "Qual aspecto verbal indica uma ação completa, com resultado?",
                   "Perfectivo", ["Perfectivo", "Imperfectivo", "Nenhum"]),
                ex("text", "Traduza (revisão): Eu tenho um livro. (у + меня + есть + книга)",
                   "у меня есть книга"),
                ex("quiz", "Qual verbo de movimento indica ir a pé, AGORA, numa direção?",
                   "идти", ["идти", "ходить", "ехать"]),
                ex("quiz", "Como se forma o condicional em russo (Módulo 10)?",
                   "verbo no passado + бы", ["verbo no passado + бы", "verbo no futuro + бы", "не + verbo"]),
                ex("text", "Traduza (revisão, discurso indireto): Ele disse que estava cansado. (он + сказал + что + он + устал)",
                   "он сказал что он устал"),
                ex("audio", "Escute e transcreva (revisão geral):", "письмо написано", audio_text="письмо написано"),
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
                # se nenhuma tem cirilico, e' teoria em portugues e a voz russa
                # so produziria ruido.
                if e["type"] == "quiz":
                    opts = e.get("options") or []
                    if not any(CYRILLIC.search(o) for o in opts):
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
                    if len(set(norms)) != len(norms):
                        problems.append(f"{loc}: alternativas ambiguas apos normalize: {opts}")
                    if norms.count(normalize(e["solution"])) != 1:
                        problems.append(f"{loc}: solution nao casa com exatamente 1 alternativa: {opts}")
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
    slugs = [t["slug"] for m in data["modules"] for t in m["topics"]]
    if len(set(slugs)) != len(slugs):
        problems.append("slugs de topico duplicados")
    return problems


def main():
    data = {
        "slug": "russo-do-zero",
        "title": "Russo do Zero",
        "description": "Uma trilha completa de russo, do alfabeto cirílico (A1) até particípios e discurso indireto (C1) — incluindo os 6 casos gramaticais, o aspecto verbal e o modo condicional. Pratica digitando (com teclado cirílico virtual e ouvindo a pronúncia com um clique em qualquer palavra em russo), ouvindo, falando e respondendo quizzes.",
        "category": "Idiomas",
        "icon": "🇷🇺",
        "level": "Do zero ao avançado (A1–C1)",
        "position": 4,
        "modules": finalize(),
    }

    problems = check(data)
    if problems:
        print("ERROS - nada foi escrito:")
        for p in problems:
            print("  -", p)
        raise SystemExit(1)

    out_path = Path(__file__).resolve().parent.parent / "app" / "content" / "russo-do-zero.json"
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
