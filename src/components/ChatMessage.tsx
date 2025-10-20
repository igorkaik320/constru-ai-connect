import { cn } from "@/lib/utils";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { motion } from "framer-motion";
import { useEffect, useState } from "react";
import { Bot, User, Check, X } from "lucide-react";

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

  // ✨ Efeito de digitação da IA
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

  // 🔗 Extrai o primeiro link HTTP se existir
  const boletoLink = message.content?.match(/https?:\/\/\S+/)?.[0];

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
        {/* Avatar da IA */}
        {!isUser && (
          <div className="flex-shrink-0 w-9 h-9 rounded-full flex items-center justify-center bg-gradient-to-br from-purple-500 to-blue-500 text-white shadow-lg">
            <Bot className="w-5 h-5" />
          </div>
        )}

        {/* Caixa da mensagem */}
        <div
          className={cn(
            "flex-1 space-y-2 p-4 rounded-2xl text-sm leading-relaxed shadow-sm transition-all",
            isUser
              ? "bg-blue-600 text-white rounded-br-none"
              : "bg-[#1e1e20] text-gray-100 rounded-bl-none border border-gray-800"
          )}
        >
          {/* Cabeçalhos */}
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

          {/* Conteúdo */}
          {message.role === "assistant" && isLoading ? (
            <div className="flex gap-1">
              <span className="w-2 h-2 bg-gray-300 rounded-full animate-bounce [animation-delay:-0.3s]" />
              <span className="w-2 h-2 bg-gray-300 rounded-full animate-bounce [animation-delay:-0.15s]" />
              <span className="w-2 h-2 bg-gray-300 rounded-full animate-bounce" />
            </div>
          ) : message.type === "pedidos" && message.pedidos ? (
            <div className="space-y-3">
              <p>{message.content}</p>
              {message.pedidos.map((p) => (
                <div
                  key={p.codigo}
                  className="border border-gray-700 rounded-xl p-4 bg-[#141416] shadow-inner flex flex-col gap-2"
                >
                  <div className="flex justify-between items-center">
                    <h3 className="font-semibold text-gray-200">{`Pedido ${p.codigo}`}</h3>
                    <span className="text-xs text-gray-400">{p.data}</span>
                  </div>
                  <p className="text-sm text-gray-400">
                    Fornecedor: <b className="text-gray-200">{p.fornecedor}</b>
                  </p>
                  <p className="text-sm text-gray-400">
                    Valor: <b className="text-gray-200">R$ {p.valor}</b> — Status:{" "}
                    <span className="text-yellow-400">{p.status}</span>
                  </p>
                  <div className="flex gap-2 mt-2">
                    <button
                      onClick={() => onAction?.(p.codigo, "autorizar")}
                      className="flex items-center gap-1 px-3 py-1.5 text-sm rounded-lg bg-green-600/80 hover:bg-green-700 text-white transition"
                    >
                      <Check className="w-4 h-4" /> Autorizar
                    </button>
                    <button
                      onClick={() => onAction?.(p.codigo, "reprovar")}
                      className="flex items-center gap-1 px-3 py-1.5 text-sm rounded-lg bg-red-600/80 hover:bg-red-700 text-white transition"
                    >
                      <X className="w-4 h-4" /> Reprovar
                    </button>
                  </div>
                </div>
              ))}
            </div>
          ) : message.type === "itens" && message.table ? (
            <div className="overflow-x-auto">
              <p className="mb-2 text-gray-200">{message.content}</p>
              <table className="table-auto border-collapse border border-gray-700 w-full text-sm text-gray-300">
                <thead className="bg-[#2a2a2d]">
                  <tr>
                    {message.table.headers.map((h, i) => (
                      <th key={i} className="border border-gray-700 px-2 py-1 text-left font-medium text-gray-100">
                        {h}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {message.table.rows.map((row, i) => (
                    <tr key={i} className="hover:bg-[#222] transition">
                      {row.map((cell, j) => (
                        <td key={j} className="border border-gray-700 px-2 py-1">
                          {cell}
                        </td>
                      ))}
                    </tr>
                  ))}
                  {message.table.total && (
                    <tr className="bg-[#18181a] font-semibold text-gray-100">
                      <td colSpan={message.table.headers.length - 1} className="border border-gray-700 px-2 py-1">
                        Total
                      </td>
                      <td className="border border-gray-700 px-2 py-1">
                        {message.table.total}
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          ) : (
            // 🔹 Mensagem normal (texto e Markdown)
            <div className="prose prose-invert prose-sm max-w-none text-gray-100 leading-relaxed space-y-2">
              <ReactMarkdown remarkPlugins={[remarkGfm]}>
                {message.role === "assistant" ? displayedText : message.content}
              </ReactMarkdown>

              {/* 🔗 Botão automático de boleto */}
              {boletoLink && (
                <a
                  href={boletoLink}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-block mt-2 px-4 py-2 rounded-lg bg-blue-600 text-white font-medium hover:bg-blue-700 transition"
                >
                  🔗 Abrir boleto
                </a>
              )}
            </div>
          )}

          {/* === BOTÕES DE AÇÃO === */}
          {message.buttons && message.buttons.length > 0 && (
            <div className="flex flex-wrap gap-2 mt-2">
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

        {/* Avatar do usuário */}
        {isUser && (
          <div className="flex-shrink-0 w-9 h-9 rounded-full flex items-center justify-center bg-blue-500/20 text-blue-400 shadow-md">
            <User className="w-5 h-5" />
          </div>
        )}
      </div>
    </motion.div>
  );
};
