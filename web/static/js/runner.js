// Renderiza lições/exercícios, roda código Python no navegador (Pyodide)
// e libera a conclusão do tópico quando todos os exercícios passam.

(function () {
  // --- 1. Renderizar markdown da lição e dos enunciados ---
  function renderMarkdown() {
    const lessonEl = document.getElementById("lesson-content");
    const lessonMd = document.getElementById("lesson-md");
    if (lessonEl && lessonMd) {
      lessonEl.innerHTML = marked.parse(lessonMd.textContent);
    }
    document.querySelectorAll(".exercise").forEach((ex) => {
      const target = ex.querySelector("[data-prompt]");
      const src = ex.querySelector("[data-prompt-md]");
      if (target && src) target.innerHTML = marked.parse(src.textContent);
    });
  }

  // --- 2. Editores de código (CodeMirror) ---
  const editors = new Map();

  function setupEditors() {
    document.querySelectorAll(".exercise").forEach((ex) => {
      const textarea = ex.querySelector(".code-editor");
      if (!textarea) return;
      const cm = CodeMirror.fromTextArea(textarea, {
        mode: textarea.dataset.lang === "sql" ? "text/x-sql" : "python",
        theme: "material-darker",
        lineNumbers: true,
        indentUnit: 4,
        viewportMargin: Infinity,
      });
      editors.set(ex, cm);
    });
  }

  // --- 2b. Exercícios de múltipla escolha (quiz) ---
  function setupQuizzes() {
    document.querySelectorAll('.exercise[data-type="quiz"]').forEach((ex) => {
      const container = ex.querySelector("[data-quiz-options]");
      const dataEl = ex.querySelector("[data-quiz-options-data]");
      if (!container || !dataEl) return;

      let opts = [];
      try {
        opts = JSON.parse(dataEl.textContent);
      } catch (e) {
        opts = [];
      }

      opts.forEach((opt) => {
        const btn = document.createElement("button");
        btn.type = "button";
        btn.className = "quiz-option";
        btn.textContent = opt;
        btn.addEventListener("click", () => {
          container.querySelectorAll(".quiz-option").forEach((b) => b.classList.remove("is-selected"));
          btn.classList.add("is-selected");
        });
        container.appendChild(btn);
      });
    });
  }

  // --- 2c. Teclado cirílico virtual (exercícios de russo) ---
  const CYRILLIC_LETTERS = "а б в г д е ё ж з и й к л м н о п р с т у ф х ц ч ш щ ъ ы ь э ю я".split(" ");

  function insertAtCursor(input, text) {
    const start = input.selectionStart ?? input.value.length;
    const end = input.selectionEnd ?? input.value.length;
    input.value = input.value.slice(0, start) + text + input.value.slice(end);
    const pos = start + text.length;
    input.focus();
    input.setSelectionRange(pos, pos);
  }

  function setupCyrillicKeyboards() {
    document.querySelectorAll("[data-cyrillic-keyboard]").forEach((kb) => {
      const exercise = kb.closest(".exercise");
      const input = exercise ? exercise.querySelector(".text-input") : null;
      if (!input) return;

      CYRILLIC_LETTERS.forEach((letra) => {
        const btn = document.createElement("button");
        btn.type = "button";
        btn.className = "kb-key";
        btn.textContent = letra;
        btn.addEventListener("click", () => insertAtCursor(input, letra));
        kb.appendChild(btn);
      });

      const spaceBtn = document.createElement("button");
      spaceBtn.type = "button";
      spaceBtn.className = "kb-key kb-key-wide";
      spaceBtn.textContent = "espaço";
      spaceBtn.addEventListener("click", () => insertAtCursor(input, " "));
      kb.appendChild(spaceBtn);

      const backBtn = document.createElement("button");
      backBtn.type = "button";
      backBtn.className = "kb-key kb-key-wide";
      backBtn.textContent = "⌫";
      backBtn.addEventListener("click", () => {
        const start = input.selectionStart ?? input.value.length;
        const end = input.selectionEnd ?? input.value.length;
        if (start === end && start > 0) {
          input.value = input.value.slice(0, start - 1) + input.value.slice(start);
          input.focus();
          input.setSelectionRange(start - 1, start - 1);
        } else {
          input.value = input.value.slice(0, start) + input.value.slice(end);
          input.focus();
          input.setSelectionRange(start, start);
        }
      });
      kb.appendChild(backBtn);
    });
  }

  // --- 3. Pyodide (carregado sob demanda) ---
  let pyodidePromise = null;
  const statusEl = document.getElementById("pyodide-status");
  const codeExercisesCount = document.querySelectorAll('.exercise[data-type="code"], .exercise:not([data-type])').length;

  if (statusEl && codeExercisesCount === 0) {
    statusEl.style.display = "none";
  }

  function ensurePyodide() {
    if (!pyodidePromise) {
      pyodidePromise = loadPyodide().then((py) => {
        if (statusEl) {
          statusEl.textContent = "✓ Ambiente Python pronto!";
          statusEl.classList.add("ready");
        }
        return py;
      });
    }
    return pyodidePromise;
  }

  // --- 3b. sql.js (carregado sob demanda, só quando há exercício sql) ---
  let sqlJsPromise = null;

  function ensureSqlJs() {
    if (!sqlJsPromise) {
      sqlJsPromise = initSqlJs({
        locateFile: (file) => `https://cdn.jsdelivr.net/npm/sql.js@1.14.1/dist/${file}`,
      });
    }
    return sqlJsPromise;
  }

  // Roda setup_sql (schema/dados) + uma query numa base sqlite em memória.
  // Retorna {columns, rows} da última instrução (deve ser um único SELECT).
  function runSqlQuery(SQL, setupSql, query) {
    const trimmed = query.trim();
    if (!trimmed) {
      throw { userError: "Escreva uma consulta antes de verificar." };
    }
    // Statements separados por ; (ignorando um ; final solto) -> exige uma única consulta.
    const statementCount = trimmed.replace(/;\s*$/, "").split(";").length;
    if (statementCount > 1) {
      throw { userError: "Escreva uma única consulta SELECT (sem múltiplos comandos separados por ';')." };
    }

    const db = new SQL.Database();
    try {
      if (setupSql) db.run(setupSql);
      const result = db.exec(trimmed);
      if (result.length === 0) {
        throw { userError: "Sua consulta não retornou nenhuma tabela de resultado — use um SELECT." };
      }
      const { columns, values } = result[0];
      return { columns, rows: values };
    } catch (err) {
      if (err && err.userError) throw err;
      throw { userError: null, raw: err };
    } finally {
      db.close();
    }
  }

  // Para exercícios de INSERT/UPDATE/DELETE: roda o comando do aluno (que não
  // retorna linhas) e então uma consulta de verificação fixa, pra comparar o
  // estado da tabela depois do comando.
  function runSqlStatementAndVerify(SQL, setupSql, statement, verifyQuery) {
    const trimmed = statement.trim();
    if (!trimmed) {
      throw { userError: "Escreva um comando antes de verificar." };
    }
    const statementCount = trimmed.replace(/;\s*$/, "").split(";").length;
    if (statementCount > 1) {
      throw { userError: "Escreva um único comando (sem múltiplos comandos separados por ';')." };
    }

    const db = new SQL.Database();
    try {
      if (setupSql) db.run(setupSql);
      db.run(trimmed);
      const result = db.exec(verifyQuery);
      if (result.length === 0) {
        throw { userError: null, raw: new Error("A consulta de verificação não retornou dados.") };
      }
      const { columns, values } = result[0];
      return { columns, rows: values };
    } catch (err) {
      if (err && err.userError !== undefined) throw err;
      throw { userError: null, raw: err };
    } finally {
      db.close();
    }
  }

  // Compara duas tabelas de resultado (colunas na mesma ordem sempre importam;
  // ordem das linhas só importa se orderMatters for true).
  function compareSqlResults(a, b, orderMatters) {
    if (a.columns.length !== b.columns.length) return false;
    const stringifyRow = (row) => JSON.stringify(row.map((v) => (v === null ? " NULL" : String(v))));
    let rowsA = a.rows.map(stringifyRow);
    let rowsB = b.rows.map(stringifyRow);
    if (!orderMatters) {
      rowsA = [...rowsA].sort();
      rowsB = [...rowsB].sort();
    }
    return JSON.stringify(rowsA) === JSON.stringify(rowsB);
  }

  function renderSqlResultTable(container, columns, rows) {
    container.innerHTML = "";
    container.hidden = false;
    const table = document.createElement("table");
    const thead = document.createElement("thead");
    const headRow = document.createElement("tr");
    columns.forEach((col) => {
      const th = document.createElement("th");
      th.textContent = col;
      headRow.appendChild(th);
    });
    thead.appendChild(headRow);
    table.appendChild(thead);

    const tbody = document.createElement("tbody");
    if (rows.length === 0) {
      const tr = document.createElement("tr");
      const td = document.createElement("td");
      td.colSpan = columns.length || 1;
      td.textContent = "(nenhuma linha retornada)";
      tr.appendChild(td);
      tbody.appendChild(tr);
    } else {
      rows.forEach((row) => {
        const tr = document.createElement("tr");
        row.forEach((cell) => {
          const td = document.createElement("td");
          td.textContent = cell === null ? "NULL" : String(cell);
          tr.appendChild(td);
        });
        tbody.appendChild(tr);
      });
    }
    table.appendChild(tbody);
    container.appendChild(table);
  }

  function resolveSetupSql(ex) {
    const topicSetupEl = document.getElementById("topic-setup-sql");
    const topicSetupSql = topicSetupEl ? topicSetupEl.textContent : "";
    const optionsEl = ex.querySelector("[data-exercise-options]");
    let opts = null;
    if (optionsEl && optionsEl.textContent.trim()) {
      try {
        opts = JSON.parse(optionsEl.textContent);
      } catch (e) {
        opts = null;
      }
    }
    const setupSql = (opts && typeof opts === "object" && opts.setup_sql) || topicSetupSql;
    const orderMatters = !!(opts && opts.order_matters);
    const verifyQuery = (opts && opts.verify_query) || null;
    return { setupSql, orderMatters, verifyQuery };
  }

  // --- 4. Estado de conclusão dos exercícios ---
  const totalExercises = document.querySelectorAll(".exercise").length;
  const passed = new Set();
  const attempted = new Set(); // Rastreia exercícios que o aluno já tentou
  const completeBtn = document.getElementById("complete-btn");

  function refreshCompleteButton() {
    if (!completeBtn) return;
    const isDone = completeBtn.classList.contains("is-done");
    if (isDone) return;
    if (totalExercises === 0) {
      completeBtn.disabled = false;
    } else if (passed.size >= totalExercises) {
      completeBtn.disabled = false;
      completeBtn.textContent = "Marcar como concluído";
    } else {
      completeBtn.disabled = true;
    }
  }

  // --- 5. Normalização de texto para exercícios de idioma ---
  function normalize(s) {
    return s.toLowerCase()
      .replace(/ё/g, "е")
      .replace(/[.,!?;:'"-]/g, "")
      .replace(/\s+/g, " ")
      .trim();
  }

  // --- 6. Feedback de erro melhorado para exercícios de texto ---
  function buildTextErrorFeedback(student, solution) {
    const normStudent = normalize(student);
    const normSolution = normalize(solution);
    const wordsStudent = normStudent.split(" ").filter(Boolean);
    const wordsSolution = normSolution.split(" ").filter(Boolean);

    const correctWords = wordsStudent.filter(w => wordsSolution.includes(w));
    const missingWords = wordsSolution.filter(w => !wordsStudent.includes(w));

    let hint = "❌ Quase lá! ";
    if (student.trim() === "") {
      hint = "❌ Digite sua resposta antes de verificar.";
    } else if (missingWords.length > 0 && missingWords.length <= 3) {
      hint += `Palavras faltando ou erradas: "${missingWords.join('", "')}"`;
    } else if (correctWords.length > 0) {
      hint += `${correctWords.length} de ${wordsSolution.length} palavras corretas. Continue tentando!`;
    } else {
      hint += "A resposta está bem diferente. Ouça novamente ou reveja a lição.";
    }
    return hint;
  }

  // --- 7. Rodar um exercício ---
  async function runExercise(ex) {
    const type = ex.dataset.type || "code";
    const output = ex.querySelector("[data-output]");
    const exId = parseInt(ex.dataset.exerciseId, 10);
    const solution = ex.querySelector("[data-solution-code]").textContent.trim();

    output.hidden = false;
    output.className = "output";
    attempted.add(exId);

    if (type === "text" || type === "audio") {
      const studentInput = ex.querySelector(".text-input");
      const studentAnswer = studentInput ? studentInput.value : "";

      if (normalize(studentAnswer) === normalize(solution)) {
        output.classList.add("ok");
        output.textContent = "✅ Correto! Muito bem! 🎉";
        passed.add(exId);
        refreshCompleteButton();
      } else {
        output.classList.add("err");
        output.textContent = buildTextErrorFeedback(studentAnswer, solution);
      }
      return;
    }

    if (type === "quiz") {
      const selected = ex.querySelector(".quiz-option.is-selected");
      const options = ex.querySelectorAll(".quiz-option");
      options.forEach((b) => b.classList.remove("is-correct", "is-wrong"));

      if (!selected) {
        output.classList.add("err");
        output.textContent = "❌ Selecione uma opção antes de verificar.";
        return;
      }

      if (normalize(selected.textContent) === normalize(solution)) {
        selected.classList.add("is-correct");
        output.classList.add("ok");
        output.textContent = "✅ Correto! Muito bem! 🎉";
        passed.add(exId);
        refreshCompleteButton();
      } else {
        selected.classList.add("is-wrong");
        options.forEach((b) => {
          if (normalize(b.textContent) === normalize(solution)) b.classList.add("is-correct");
        });
        output.classList.add("err");
        output.textContent = "❌ Não foi dessa vez. A opção correta está destacada.";
      }
      return;
    }

    if (type === "sql") {
      const resultEl = ex.querySelector("[data-sql-result]");
      const cm = editors.get(ex);
      const studentQuery = cm.getValue();
      const { setupSql, orderMatters, verifyQuery } = resolveSetupSql(ex);
      const run = (SQL, stmt) =>
        verifyQuery
          ? runSqlStatementAndVerify(SQL, setupSql, stmt, verifyQuery)
          : runSqlQuery(SQL, setupSql, stmt);

      let SQL;
      try {
        SQL = await ensureSqlJs();
      } catch (e) {
        output.classList.add("err");
        output.textContent = "Não foi possível carregar o motor de SQL. Verifique sua conexão.";
        return;
      }

      let studentResult;
      try {
        studentResult = run(SQL, studentQuery);
      } catch (err) {
        output.classList.add("err");
        if (err && err.userError) {
          output.textContent = "❌ " + err.userError;
        } else {
          output.textContent = "❌ " + (err && err.raw ? err.raw.message : "Erro ao executar seu comando.");
        }
        if (resultEl) resultEl.hidden = true;
        return;
      }

      if (resultEl) renderSqlResultTable(resultEl, studentResult.columns, studentResult.rows);

      let solutionResult;
      try {
        solutionResult = run(SQL, solution);
      } catch (err) {
        output.classList.add("err");
        output.textContent = "❌ Erro interno no exercício (comando de referência falhou). Avise quem criou o curso.";
        return;
      }

      if (compareSqlResults(studentResult, solutionResult, orderMatters)) {
        output.classList.add("ok");
        output.textContent = verifyQuery
          ? "✅ Correto! O estado da tabela depois do seu comando bate com o esperado."
          : "✅ Correto! O resultado da sua consulta bate com o esperado.";
        passed.add(exId);
        refreshCompleteButton();
      } else {
        output.classList.add("err");
        output.textContent = verifyQuery
          ? "❌ Seu comando rodou, mas o estado da tabela depois não é o esperado. Veja a tabela acima e compare."
          : "❌ Sua consulta rodou, mas o resultado não é o esperado. Veja a tabela acima e compare.";
      }
      return;
    }

    // Code exercise logic
    const cm = editors.get(ex);
    const testCode = ex.querySelector("[data-test-code]").textContent;
    const studentCode = cm.getValue();

    output.textContent = "Executando…";

    let py;
    try {
      py = await ensurePyodide();
    } catch (e) {
      output.classList.add("err");
      output.textContent = "Não foi possível carregar o ambiente Python. Verifique sua conexão.";
      return;
    }

    py.globals.set("_student_src", studentCode);
    py.globals.set("_test_src", testCode);

    try {
      await py.runPythonAsync(`
_ns = {"_student_code": _student_src}
exec(_student_src, _ns)
exec(_test_src, _ns)
`);
      output.classList.add("ok");
      output.textContent = "✅ Correto! Muito bem.";
      passed.add(exId);
      refreshCompleteButton();
    } catch (err) {
      output.classList.add("err");
      output.textContent = "❌ " + formatPyError(err.message);
    } finally {
      py.globals.delete("_student_src");
      py.globals.delete("_test_src");
    }
  }

  // Extrai a mensagem útil do traceback do Python.
  function formatPyError(message) {
    const lines = message.trim().split("\n").filter((l) => l.trim());
    const last = lines[lines.length - 1] || "Erro desconhecido";
    if (last.startsWith("AssertionError")) {
      const msg = last.replace("AssertionError:", "").trim();
      return msg || "O resultado não passou na verificação. Tente de novo.";
    }
    return last;
  }

  // --- 8. STT (Speech Recognition) ---
  function startSpeakExercise(ex) {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) {
      const resultEl = ex.querySelector(".speak-result");
      resultEl.hidden = false;
      resultEl.className = "speak-result err";
      resultEl.textContent = "❌ Seu navegador não suporta reconhecimento de voz. Use o Chrome.";
      return;
    }

    const btn = ex.querySelector(".btn-speak");
    const resultEl = ex.querySelector(".speak-result");
    const audioLang = btn.dataset.audioLang || "en-US";
    const solution = ex.querySelector("[data-solution-code]").textContent.trim();
    const exId = parseInt(ex.dataset.exerciseId, 10);

    const recognition = new SpeechRecognition();
    recognition.lang = audioLang;
    recognition.interimResults = false;
    recognition.maxAlternatives = 3;

    btn.textContent = "🔴 Ouvindo...";
    btn.disabled = true;
    resultEl.hidden = false;
    resultEl.className = "speak-result";
    resultEl.textContent = "🎙️ Fale agora...";

    recognition.start();

    recognition.onresult = (event) => {
      const transcripts = Array.from(event.results[0]).map(a => a.transcript);
      const best = transcripts[0];

      if (transcripts.some(t => normalize(t) === normalize(solution))) {
        resultEl.className = "speak-result ok";
        resultEl.textContent = `✅ Perfeito! Você disse: "${best}"`;
        passed.add(exId);
        refreshCompleteButton();
      } else {
        resultEl.className = "speak-result err";
        resultEl.textContent = `❌ Ouvi: "${best}". A pronúncia esperada era: "${solution}". Tente novamente!`;
      }
    };

    recognition.onerror = (event) => {
      resultEl.className = "speak-result err";
      if (event.error === "no-speech") {
        resultEl.textContent = "❌ Nenhuma fala detectada. Fique mais perto do microfone.";
      } else if (event.error === "not-allowed") {
        resultEl.textContent = "❌ Acesso ao microfone negado. Habilite nas configurações do navegador.";
      } else {
        resultEl.textContent = `❌ Erro no reconhecimento: ${event.error}`;
      }
    };

    recognition.onend = () => {
      btn.textContent = "🎤 Gravar Fala";
      btn.disabled = false;
    };
  }

  // --- 9. Ligar os botões ---
  function wireButtons() {
    document.querySelectorAll(".exercise").forEach((ex) => {
      const type = ex.dataset.type || "code";
      const runBtn = ex.querySelector("[data-run]");
      const solBtn = ex.querySelector("[data-solution]");
      const solution = ex.querySelector("[data-solution-code]").textContent.trim();
      const exId = parseInt(ex.dataset.exerciseId, 10);

      if (runBtn) {
        runBtn.addEventListener("click", () => runExercise(ex));
      }

      solBtn.addEventListener("click", () => {
        // Só pede confirmação se o aluno nunca tentou. Após erro, mostra direto.
        const hasAttempted = attempted.has(exId);
        const showSolution = hasAttempted || confirm("Mostrar a solução? Tente resolver sozinho primeiro 🙂");
        if (showSolution) {
          if (type === "code" || type === "sql") {
            editors.get(ex).setValue(solution);
          } else if (type === "speak") {
            const resultEl = ex.querySelector(".speak-result");
            resultEl.hidden = false;
            resultEl.className = "speak-result";
            resultEl.textContent = `💡 A pronúncia esperada é: "${solution}"`;
          } else if (type === "quiz") {
            ex.querySelectorAll(".quiz-option").forEach((b) => {
              b.classList.remove("is-wrong");
              b.classList.toggle("is-correct", normalize(b.textContent) === normalize(solution));
            });
          } else {
            const input = ex.querySelector(".text-input");
            if (input) input.value = solution;
          }
        }
      });

      // Botões de TTS (áudio)
      const audioBtns = ex.querySelectorAll(".btn-audio");
      audioBtns.forEach(btn => {
        btn.addEventListener("click", () => {
          const text = btn.dataset.audioText;
          const lang = btn.dataset.audioLang || "en-US";
          const speed = parseFloat(btn.dataset.speed || "1");
          if (!text) return;
          window.speechSynthesis.cancel();
          const utterance = new SpeechSynthesisUtterance(text);
          utterance.lang = lang;
          utterance.rate = speed;
          window.speechSynthesis.speak(utterance);
        });
      });

      // Botão de STT (microfone)
      const speakBtn = ex.querySelector(".btn-speak");
      if (speakBtn) {
        speakBtn.addEventListener("click", () => startSpeakExercise(ex));
      }
    });

    if (completeBtn) {
      completeBtn.addEventListener("click", async () => {
        if (completeBtn.classList.contains("is-done")) return;
        const topicId = parseInt(completeBtn.dataset.topicId, 10);
        try {
          await Progress.markDone(topicId);
          completeBtn.classList.add("is-done");
          completeBtn.textContent = "✓ Concluído";
          completeBtn.disabled = false;
        } catch (e) {
          alert("Não foi possível salvar o progresso.");
        }
      });
    }
  }

  // --- Inicialização ---
  document.addEventListener("DOMContentLoaded", () => {
    renderMarkdown();
    setupEditors();
    setupQuizzes();
    setupCyrillicKeyboards();
    wireButtons();
    refreshCompleteButton();
    if (codeExercisesCount > 0) ensurePyodide();
  });
})();
