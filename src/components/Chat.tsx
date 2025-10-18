import React, { useState, useRef, useEffect } from "react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Send, Bot, User } from "lucide-react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

interface Message {
  role: "user" | "assistant";
  content: string;
}

export const Chat = () => {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const endRef = useRef<HTMLDivElement | null>(null);

  const scrollToBottom = () => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleSend = () => {
    if (!input.trim()) return;

    const newMessage: Message = { role: "user", content: input };
    setMessages((prev) => [...prev, newMessage]);
    setInput("");

    // Simula resposta da IA
    setTimeout(() => {
      const botMessage: Message = {
        role: "assistant",
        content: `👋 Claro! Aqui está a resposta para: **${input}**`,
      };
      setMessages((prev) => [...prev, botMessage]);
    }, 700);
  };

  return (
    <div className="flex flex-col h-screen bg-[hsl(240,10%,4%)] text-foreground">
      {/* Cabeçalho */}
      <header className="flex items-center justify-center h-14 border-b border-gray-800">
        <h1 className="text-lg font-semibold bg-gradient-to-r from-purple-400 to-blue-400 bg-clip-text text-transparent">
          constru.ia
        </h1>
      </header>

      {/* Mensagens */}
      <main className="flex-1 overflow-y-auto px-4 py-6 space-y-4 scrollbar-thin scrollbar-thumb-gray-700 scrollbar-track-transparent">
        {messages.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full text-center space-y-3 text-gray-400">
            <Bot className="w-12 h-12 text-purple-500/80" />
            <h2 className="text-lg font-medium">Bem-vindo ao constru.ia 👋</h2>
            <p className="max-w-md text-sm text-gray-500">
              Envie uma mensagem para começar. Use termos como{" "}
              <span className="text-purple-400 font-medium">
                "pedidos pendentes"
              </span>{" "}
              ou{" "}
              <span className="text-purple-400 font-medium">
                "itens do pedido 123"
              </span>
              .
            </p>
          </div>
        ) : (
          messages.map((msg, i) => (
            <ChatMessage key={i} message={msg} />
          ))
        )}
        <div ref={endRef} />
      </main>

      {/* Input */}
      <footer className="border-t border-gray-800 p-4">
        <div className="max-w-3xl mx-auto flex gap-2 items-end">
          <textarea
            className="flex-1 bg-[#1a1a1d] text-gray-100 text-sm p-3 rounded-xl border border-gray-700 focus:ring-2 focus:ring-purple-500/40 resize-none"
            placeholder="Digite sua mensagem..."
            rows={1}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && !e.shiftKey && (e.preventDefault(), handleSend())}
          />
          <Button
            onClick={handleSend}
            className="p-3 bg-gradient-to-br from-purple-500 to-blue-500 hover:opacity-90 transition rounded-xl"
          >
            <Send className="w-4 h-4" />
          </Button>
        </div>
      </footer>
    </div>
  );
};

interface ChatMessageProps {
  message: Message;
}

const ChatMessage: React.FC<ChatMessageProps> = ({ message }) => {
  const isUser = message.role === "user";

  return (
    <div
      className={cn(
        "flex items-start fade-in",
        isUser ? "justify-end" : "justify-start"
      )}
    >
      {!isUser && (
        <div className="flex items-center justify-center w-8 h-8 rounded-full bg-gradient-to-br from-purple-500 to-blue-500 mr-2">
          <Bot className="w-4 h-4 text-white" />
        </div>
      )}

      <div
        className={cn(
          "px-4 py-2 rounded-2xl max-w-[700px] text-sm leading-relaxed whitespace-pre-wrap shadow-md transition-all",
          isUser
            ? "bg-[hsl(220,80%,55%)] text-white rounded-br-none"
            : "bg-[#1e1e20] text-gray-100 rounded-bl-none"
        )}
      >
        <ReactMarkdown remarkPlugins={[remarkGfm]}>
          {message.content}
        </ReactMarkdown>
      </div>

      {isUser && (
        <div className="flex items-center justify-center w-8 h-8 rounded-full bg-blue-500/20 ml-2">
          <User className="w-4 h-4 text-blue-400" />
        </div>
      )}
    </div>
  );
};

