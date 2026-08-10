# tools/

Geradores do conteúdo dos cursos grandes (idiomas e Python).

Esses cursos viram arquivos JSON grandes (~1000-2000+ linhas), com muito texto
escapado (cirílico, markdown, código Python dentro de string). Editar isso à
mão erra fácil — uma vírgula fora do lugar quebra o curso inteiro. Por isso o
conteúdo é escrito como estrutura Python, com strings multi-linha normais, e
serializado:

```bash
python tools/build_russo.py     # reescreve app/content/russo-do-zero.json
python tools/build_ingles.py    # reescreve app/content/ingles-do-zero.json
python tools/build_python.py    # reescreve app/content/python-do-zero.json
```

Depois é só reiniciar o app (o `seed()` recarrega os JSONs no start).

`build_python.py` funciona diferente dos outros dois: em vez de reconstruir o
curso do zero, ele **carrega o JSON atual como base** e só acrescenta/edita os
módulos da fase em andamento — módulos ainda não escritos ficam intactos.
Isso preserva os slugs dos módulos já existentes (e portanto o progresso já
salvo de quem usa o curso). O plano de expansão completo do curso de Python
(módulos, fases, o que já foi feito) está em `tools/PYTHON_ROADMAP.md`.

## O que os geradores garantem sozinhos

Antes de escrever qualquer coisa, os scripts validam o curso e **abortam sem
gravar** se encontrarem:

- tópico com menos de 5 exercícios;
- alternativas de quiz que ficam iguais depois da normalização do corretor
  (`normalize()` em `web/static/js/runner.js` ignora maiúsculas, acentos de `ё`
  e pontuação — então `won't` e `wont` seriam a mesma resposta, e o aluno
  acertaria escolhendo a errada);
- solução que não corresponde a exatamente uma alternativa;
- exercício de áudio/fala cujo `audio_text` não bate com a `solution` (russo/inglês);
- resposta em cirílico num exercício sem teclado virtual (russo — o teclado só
  aparece quando `audio_lang` começa com `ru`);
- exercício `code` cujo `solution` + `test_code` não passam quando executados
  de verdade (mesmo mecanismo que `app/seed.py::_validate_code_exercise` usa
  na carga real — pega bug de autoria antes até de rodar o app);
- slugs de tópico/módulo repetidos.

Os geradores de idioma também definem sozinhos o idioma do botão de ouvir de
cada quiz: alternativas que são teoria em português recebem voz `pt-BR`, em
vez de serem lidas com a voz do idioma estudado.

Os demais cursos (SQL, lógica de programação) continuam sendo editados direto
no JSON — são pequenos e não têm esse tipo de armadilha.
