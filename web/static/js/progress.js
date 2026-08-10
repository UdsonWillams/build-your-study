// Chamadas à API de progresso (marca/desmarca tópico concluído).

const Progress = {
  // `score` é a nota de 0 a 10 do tópico (null em tópicos só de leitura).
  async markDone(topicId, score = null) {
    const res = await fetch("/api/progress", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ topic_id: topicId, score }),
    });
    if (!res.ok) throw new Error("Falha ao salvar progresso");
    return res.json();
  },

  async unmark(topicId) {
    const res = await fetch(`/api/progress/${topicId}`, { method: "DELETE" });
    if (!res.ok) throw new Error("Falha ao remover progresso");
    return res.json();
  },
};
