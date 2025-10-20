import { cn } from "@/lib/utils";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { motion } from "framer-motion";
import { useEffect, useState } from "react";
import { Bot, User, Check, X, Link as LinkIcon } from "lucide-react";

interface ChatMessageProps {
  message: {
    role: "user" | "assistant";
    content: string;
    type?: "text" | "pedidos" | "itens";
    pedidos?: any[];
    table?: { headers: string[]; rows: any[][]; total?: number };
    buttons?: { label: string; action: string; pedido_id?: number }[];
  };
  isLoading?: boolean;
  onAction?: (codigo: number, acao: "autorizar" | "reprovar") => void;
}

export const ChatMessage = ({ message, isLoading, onAction }: ChatMessageProps) => {
  const isUser = message.role === "user";
  const [displayedText, setDisplayedText] = useState("");

  // Efeito de digitação
  useEffect(() => {
    if (message.role === "assistant" && !isLoading) {
      setDisplayedText("");
      let i = 0;
      const interval = setInterval(() => {
        setDisplayedText(message.content.slice(0, i + 1));
        i++;
        if (i >= message.content.length) clearInterval(interval);
      }, 15);
      return () => clearInterval(interval);
    }
  }, [message.content, message.role, isLoading]);

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.25 }}
      className={cn(
        "w-full py-4 px-4",
        isUser ? "flex justify-end" : "flex justify-start"
      )}
    >
      <div className="max-w-3xl flex gap-4">
        {/* Avatar IA */}
        {!isUser && (
          <div className="flex-shrink-0 w-9 h-9 rounded-full flex items-center justify-center bg-gradient-to-br from-purple-500 to-blue-500 text-white shadow-lg">
            <Bot className="w-5 h-5" />
          </div>
        )}

        {/* Caixa principal */}
        <div
          className={cn(
            "flex-1 space-y-2 p-4 rounded-2xl text-sm leading-relaxed shadow-sm transition-all",
            isUser
              ? "bg-blue-600 text-white rounded-br-none"
              : "bg-[#1e1e20] text-gray-100 rounded-bl-none border border-gray-800"
          )}
        >
          {!isUser && (
            <div className="text-xs font-semibold text-purple-400 mb-1">
              constru.ia
            </div>
          )}
          {isUser && (
            <div className="text-xs font-semibold text-blue-300 mb-1 text-right">
              Você
            </div>
          )}

          {/* Animação de digitação */}
          {message.role === "assistant" && isLoading ? (
            <div className="flex gap-1">
              <span className="w-2 h-2 bg-gray-300 rounded-full animate-bounce [animation-delay:-0.3s]" />
              <span className="w-2 h-2 bg-gray-300 rounded-full animate-bounce [animation-delay:-0.15s]" />
              <span className="w-2 h-2 bg-gray-300 rounded-full animate-bounce" />
            </div>
          ) : (
            <div className="prose prose-invert prose-sm max-w-none leading-relaxed text-gray-100">
              <ReactMarkdown remarkPlugins={[remarkGfm]}>
                {message.role === "assistant" ? displayedText : message.content}
              </ReactMarkdown>

              {/* Melhor formatação para link do boleto */}
              {message.content.includes("Clique aqui para abrir o boleto") && (
                <div className="mt-3 p-3 bg-[#151518] rounded-lg border border-gray-700">
                  <p className="text-gray-300 text-sm mb-1 flex items-center gap-2">
                    <LinkIcon className="w-4 h-4 text-blue-400" />
                    <span>
                      <strong className="text-blue-400">Clique aqui</strong> para abrir o boleto:
                    </span>
                  </p>
                  <ReactMarkdown remarkPlugins={[remarkGfm]}>
                    {message.content.match(/\[Clique aqui.*\)/)?.[0] || ""}
                  </ReactMarkdown>

                  {/* Linha digitável separada */}
                  {message.content.includes("Linha digitável") && (
                    <p className="mt-2 text-xs text-gray-400 font-mono bg-[#0f0f10] p-2 rounded">
                      {message.content.split("Linha digitável:")[1]?.trim()}
                    </p>
                  )}
                </div>
              )}
            </div>
          )}

          {/* Botões adicionais */}
          {message.buttons && message.buttons.length > 0 && (
            <div className="flex flex-wrap gap-2 mt-3">
              {message.buttons.map((btn, i) => (
                <button
                  key={i}
                  onClick={() => onAction?.(btn.pedido_id!, btn.action as any)}
                  className="px-3 py-1.5 text-sm rounded-lg bg-gradient-to-r from-purple-500 to-blue-500 text-white hover:opacity-90 transition"
                >
                  {btn.label}
                </button>
              ))}
            </div>
          )}
        </div>

        {/* Avatar usuário */}
        {isUser && (
          <div className="flex-shrink-0 w-9 h-9 rounded-full flex items-center justify-center bg-blue-500/20 text-blue-400 shadow-md">
            <User className="w-5 h-5" />
          </div>
        )}
      </div>
    </motion.div>
  );
};
