import { useState, useRef, useEffect } from "react";
import { ChatMessage } from "@/components/ChatMessage";
import { ChatInput } from "@/components/ChatInput";
import { ChatHeader } from "@/components/ChatHeader";
import { useToast } from "@/hooks/use-toast";
import { Loader2 } from "lucide-react";
import { sendMessageToBackend } from "@/backendClient";

interface Message {
  role: "user" | "assistant";
  content: string;
  pedidos?: any[];
  type?: "text" | "pedidos";
}

const BACKEND_URL = "https://seu-backend-url.onrender.com"; // ⬅️ coloque aqui a URL real do seu backend no Render

const Index = () => {
  const [messages, setMessages] = useState<Message[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const { toast } = useToast();

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleListarPedidos = async () => {
    try {
      const res = await fetch(`${BACKEND_URL}/pedidos`);
      if (!res.ok) throw new Error("Erro ao buscar pedidos.");
      const pedidos = await res.json();

      const msg: Message = {
        role: "assistant",
        content: pedidos.length
          ? "📋 Aqui estão os pedidos pendentes:"
          : "Nenhum pedido pendente encontrado.",
        pedidos,
        type: "pedidos",
      };
      setMessages((prev) => [...prev, msg]);
    } catch (err) {
      toast({
        title: "Erro",
        description: "Falha ao listar pedidos.",
        variant: "destructive",
      });
    }
  };

  const handleAcaoPedido = async (codigo: number, acao: "autorizar" | "reprovar") => {
    try {
      const res = await fetch(`${BACKEND_URL}/pedidos/${acao}/${codigo}`, {
        method: "POST",
      });
      if (!res.ok) throw new Error("Erro na requisição.");

      const sucesso = acao === "autorizar"
        ? `✅ Pedido ${codigo} autorizado com sucesso!`
        : `🚫 Pedido ${codigo} reprovado com sucesso!`;

      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: sucesso, type: "text" },
      ]);
    } catch {
      toast({
        title: "Erro",
        description: `Falha ao ${acao} o pedido ${codigo}.`,
        variant: "destructive",
      });
    }
  };

  const sendMessage = async (text: string) => {
    const userMessage: Message = { role: "user", content: text };
    setMessages((prev) => [...prev, userMessage]);
    setIsLoading(true);

    try {
      const lower = text.toLowerCase();
      if (lower.includes("listar pedidos")) {
        await handleListarPedidos();
      } else if (lower.includes("autorizar pedido")) {
        const numero = text.match(/\d+/)?.[0];
        numero
          ? await handleAcaoPedido(Number(numero), "autorizar")
          : setMessages((prev) => [
              ...prev,
              {
                role: "assistant",
                content: "⚠️ Informe o número do pedido que deseja autorizar.",
              },
            ]);
      } else if (lower.includes("reprovar pedido")) {
        const numero = text.match(/\d+/)?.[0];
        numero
          ? await handleAcaoPedido(Number(numero), "reprovar")
          : setMessages((prev) => [
              ...prev,
              {
                role: "assistant",
                content: "⚠️ Informe o número do pedido que deseja reprovar.",
              },
            ]);
      } else {
        const response = await sendMessageToBackend("usuário", text);
        setMessages((prev) => [
          ...prev,
          { role: "assistant", content: response },
        ]);
      }
    } catch (error) {
      console.error("Erro:", error);
      toast({
        title: "Erro",
        description: "Erro ao se comunicar com o servidor.",
        variant: "destructive",
      });
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="flex flex-col h-screen bg-background">
      <ChatHeader />
      <div className="flex-1 overflow-y-auto">
        {messages.length === 0 && (
          <div className="h-full flex items-center justify-center px-4">
            <div className="text-center space-y-4 max-w-2xl">
              <div className="w-20 h-20 mx-auto rounded-2xl bg-gradient-to-br from-primary to-accent flex items-center justify-center">
                <Loader2 className="w-10 h-10 text-primary-foreground animate-spin" />
              </div>
              <h2 className="text-2xl font-bold text-foreground">
                Bem-vindo ao constru.ia
              </h2>
              <p className="text-muted-foreground">
                Digite “listar pedidos” para ver os pendentes.
              </p>
            </div>
          </div>
        )}

        {messages.map((message, index) => (
          <ChatMessage
            key={index}
            message={message}
            onAction={handleAcaoPedido}
          />
        ))}

        {isLoading && (
          <ChatMessage
            message={{ role: "assistant", content: "" }}
            isLoading={true}
          />
        )}

        <div ref={messagesEndRef} />
      </div>

      <ChatInput onSend={sendMessage} isLoading={isLoading} />
    </div>
  );
};

export default Index;
