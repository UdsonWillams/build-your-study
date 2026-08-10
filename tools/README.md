# tools/

Geradores do conteúdo dos cursos de idiomas.

Os cursos de russo e inglês são arquivos JSON grandes (~2000 linhas cada), com
muito texto em cirílico e frases escapadas. Editar isso à mão erra fácil — uma
vírgula fora do lugar quebra o curso inteiro. Por isso o conteúdo é escrito como
estrutura Python, com strings multi-linha normais, e serializado:

```bash
python tools/build_russo.py     # reescreve app/content/russo-do-zero.json
python tools/build_ingles.py    # reescreve app/content/ingles-do-zero.json
```

Depois é só reiniciar o app (o `seed()` recarrega os JSONs no start).

## O que os geradores garantem sozinhos

Antes de escrever qualquer coisa, os scripts validam o curso e **abortam sem
gravar** se encontrarem:

- tópico com menos de 4 exercícios;
- alternativas de quiz que ficam iguais depois da normalização do corretor
  (`normalize()` em `web/static/js/runner.js` ignora maiúsculas, acentos de `ё`
  e pontuação — então `won't` e `wont` seriam a mesma resposta, e o aluno
  acertaria escolhendo a errada);
- solução que não corresponde a exatamente uma alternativa;
- exercício de áudio/fala cujo `audio_text` não bate com a `solution`;
- resposta em cirílico num exercício sem teclado virtual (o teclado só aparece
  quando `audio_lang` começa com `ru`);
- slugs de tópico repetidos.

Também definem sozinhos o idioma do botão de ouvir de cada quiz: alternativas
que são teoria em português recebem voz `pt-BR`, em vez de serem lidas com a
voz do idioma estudado.

Os demais cursos (Python, SQL, lógica) continuam sendo editados direto no JSON —
são menores e não têm esse tipo de armadilha.
