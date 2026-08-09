// Chamadas à API de progresso (marca/desmarca tópico concluído).

const Progress = {
  async markDone(topicId) {
    const res = await fetch("/api/progress", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ topic_id: topicId }),
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
