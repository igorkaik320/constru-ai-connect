import { cn } from "@/lib/utils";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { Bot, User, Check, X } from "lucide-react";

interface ChatMessageProps {
  message: {
    role: "user" | "assistant";
    content: string;
    pedidos?: any[];
    type?: "text" | "pedidos";
  };
  isLoading?: boolean;
  onAction?: (codigo: number, acao: "autorizar" | "reprovar") => void;
}

export const ChatMessage = ({ message, isLoading, onAction }: ChatMessageProps) => {
  const isUser = message.role === "user";

  return (
    <div
      className={cn(
        "w-full py-8 px-4 animate-in fade-in-50 slide-in-from-bottom-2 duration-500",
        isUser ? "bg-[hsl(var(--chat-user-bg))]" : "bg-[hsl(var(--chat-ai-bg))]"
      )}
    >
      <div className="max-w-3xl mx-auto flex gap-6">
        <div
          className={cn(
            "flex-shrink-0 w-8 h-8 rounded-lg flex items-center justify-center",
            isUser
              ? "bg-primary/20 text-primary"
              : "bg-gradient-to-br from-primary to-accent text-primary-foreground"
          )}
        >
          {isUser ? <User className="w-5 h-5" /> : <Bot className="w-5 h-5" />}
        </div>

        <div className="flex-1 space-y-4 overflow-hidden">
          <div className="text-sm font-medium text-muted-foreground">
            {isUser ? "Você" : "constru.ia"}
          </div>

          {isLoading ? (
            <div className="flex gap-1">
              <span className="w-2 h-2 bg-primary rounded-full animate-bounce [animation-delay:-0.3s]" />
              <span className="w-2 h-2 bg-primary rounded-full animate-bounce [animation-delay:-0.15s]" />
              <span className="w-2 h-2 bg-primary rounded-full animate-bounce" />
            </div>
          ) : message.type === "pedidos" && message.pedidos ? (
            <div className="space-y-3">
              <p className="text-foreground">{message.content}</p>
              {message.pedidos.map((p) => (
                <div
                  key={p.codigo}
                  className="border border-border rounded-xl p-4 bg-card/40 shadow-sm flex flex-col gap-2"
                >
                  <div className="flex justify-between items-center">
                    <h3 className="font-semibold text-foreground">
                      Pedido {p.codigo}
                    </h3>
                    <span className="text-xs text-muted-foreground">
                      {p.data}
                    </span>
                  </div>
                  <p className="text-sm text-muted-foreground">
                    Fornecedor: <b>{p.fornecedor}</b>
                  </p>
                  <p className="text-sm text-muted-foreground">
                    Valor: R$ {p.valor} — Status: {p.status}
                  </p>
                  <div className="flex gap-2 mt-2">
                    <button
                      onClick={() => onAction?.(p.codigo, "autorizar")}
                      className="flex items-center gap-1 px-3 py-1.5 text-sm rounded-lg bg-green-600/80 hover:bg-green-700 text-white transition-all"
                    >
                      <Check className="w-4 h-4" /> Autorizar
                    </button>
                    <button
                      onClick={() => onAction?.(p.codigo, "reprovar")}
                      className="flex items-center gap-1 px-3 py-1.5 text-sm rounded-lg bg-red-600/80 hover:bg-red-700 text-white transition-all"
                    >
                      <X className="w-4 h-4" /> Reprovar
                    </button>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="prose prose-invert prose-sm max-w-none text-foreground">
              <ReactMarkdown remarkPlugins={[remarkGfm]}>
                {message.content}
              </ReactMarkdown>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
