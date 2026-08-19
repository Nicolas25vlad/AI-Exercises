const historico = document.querySelector("#historico");
const formulario = document.querySelector("#formulario");
const pergunta = document.querySelector("#pergunta");
const encerrar = document.querySelector("#encerrar");
let sessionId = "";

function mostrar(texto, classe) {
  const item = document.createElement("div");
  item.className = `mensagem ${classe}`;
  item.textContent = texto;
  historico.append(item);
  historico.scrollTop = historico.scrollHeight;
}

async function iniciar() {
  const resposta = await fetch("/sessions", { method: "POST" });
  if (!resposta.ok) throw new Error("Não foi possível iniciar a sessão.");
  sessionId = (await resposta.json()).session_id;
}

formulario.addEventListener("submit", async (event) => {
  event.preventDefault();
  const texto = pergunta.value.trim();
  if (!texto || !sessionId) return;
  mostrar(texto, "usuario");
  pergunta.value = "";
  formulario.querySelector("button").disabled = true;
  try {
    const resposta = await fetch("/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ session_id: sessionId, pergunta: texto }),
    });
    const dados = await resposta.json();
    if (!resposta.ok) throw new Error(dados.detail || "Erro ao enviar mensagem.");
    mostrar(dados.resposta, "assistente");
  } catch (erro) {
    mostrar(erro.message, "assistente");
  } finally {
    formulario.querySelector("button").disabled = false;
    pergunta.focus();
  }
});

encerrar.addEventListener("click", async () => {
  if (!sessionId) return;
  await fetch(`/sessions/${sessionId}`, { method: "DELETE" });
  sessionId = "";
  pergunta.disabled = true;
  encerrar.disabled = true;
  mostrar("Sessão encerrada.", "assistente");
});

iniciar().catch((erro) => mostrar(erro.message, "assistente"));
