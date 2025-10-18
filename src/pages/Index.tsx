import { useState, useRef, useEffect } from "react";
import { ChatMessage } from "@/components/ChatMessage";
import { ChatInput } from "@/components/ChatInput";
import { ChatHeader } from "@/components/ChatHeader";
import { ConversationsSidebar } from "@/components/ConversationsSidebar";
import { SidebarProvider } from "@/components/ui/sidebar";
import { Bot } from "lucide-react";

interface Message {
  role: "user" | "assistant";
  content: string;
  type?: "text" | "pedidos" | "itens";
  pedidos?: any[];
  table?: { headers: string[]; rows: any[][]; total?: number };
  buttons?: { label: string; action: string; pedido_id?: number }[];
}

const Index = () => {
  const [messages, setMessages] = useState<Message[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(scrollToBottom, [messages]);

  // 🔹 Função para enviar mensagem ao backend
  const sendMessage = async (text: string) => {
    const userMessage: Message = { role: "user", content: text };
    setMessages((prev) => [...prev, userMessage]);
    setIsLoading(true);

    try {
      const response = await fetch("https://constru-ai-connect.onrender.com/mensagem", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          user: "igorkaik320@gmail.com", // pode deixar fixo
          text,
        }),
      });

      const data = await response.json();

      const aiMessage: Message = {
        role: "assistant",
        content: data.text || "Sem resposta da IA.",
        ...(data.buttons && { buttons: data.buttons }),
        ...(data.table && { table: data.table }),
        ...(data.pedidos && { pedidos: data.pedidos }),
        ...(data.type && { type: data.type }),
      };

      setMessages((prev) => [...prev, aiMessage]);
    } catch (error) {
      console.error("Erro ao enviar mensagem:", error);
      const errorMsg: Message = {
        role: "assistant",
        content: "⚠️ Erro ao conectar com o servidor.",
      };
      setMessages((prev) => [...prev, errorMsg]);
    } finally {
      setIsLoading(false);
    }
  };

  // 🔹 Função para lidar com ações (botões da IA)
  const handleAction = (pedidoId: number, acao: string) => {
    sendMessage(`${acao} ${pedidoId}`);
  };

  // 🔹 Função para sugestões iniciais
  const handleSuggestion = (text: string) => {
    sendMessage(text);
  };

  return (
    <SidebarProvider>
      <div className="flex min-h-screen w-full bg-[hsl(var(--background))]">
        <ConversationsSidebar
          currentConversationId={"demo"}
          onSelectConversation={() => {}}
          onCreateConversation={() => {}}
        />

        <div className="flex flex-col flex-1 h-screen">
          <header className="h-14 flex items-center justify-between border-b border-border px-4 backdrop-blur-md bg-background/70">
            <ChatHeader />
          </header>

          <main className="flex-1 overflow-y-auto p-6 space-y-4">
            {messages.length === 0 ? (
              <div className="h-full flex flex-col items-center justify-center text-center gap-5">
                <Bot className="w-10 h-10 text-primary" />
                <h2 className="text-lg font-semibold text-foreground">
                  Bem-vindo ao constru.ia 👋
                </h2>
                <p className="text-sm max-w-sm text-muted-foreground">
                  Envie uma mensagem para começar ou use um dos atalhos abaixo:
                </p>
                <div className="flex flex-wrap justify-center gap-2">
                  {["pedidos pendentes", "itens do pedido 123", "autorizar pedido 101"].map(
                    (sugestao, i) => (
                      <button
                        key={i}
                        onClick={() => handleSuggestion(sugestao)}
                        className="px-3 py-1.5 text-sm rounded-lg bg-gradient-to-r from-purple-500 to-blue-500 text-white hover:opacity-90 transition"
                      >
                        {sugestao}
                      </button>
                    )
                  )}
                </div>
              </div>
            ) : (
              messages.map((m, i) => (
                <ChatMessage
                  key={i}
                  message={m}
                  isLoading={isLoading && i === messages.length - 1}
                  onAction={handleAction}
                />
              ))
            )}
            <div ref={messagesEndRef} />
          </main>

          <ChatInput onSend={sendMessage} isLoading={isLoading} />
        </div>
      </div>
    </SidebarProvider>
  );
};

export default Index;
