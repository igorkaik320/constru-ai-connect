import { cn } from "@/lib/utils";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { Bot, User } from "lucide-react";

interface ChatMessageProps {
  message: {
    role: "user" | "assistant";
    content: string;
  };
  isLoading?: boolean;
}

export const ChatMessage = ({ message, isLoading }: ChatMessageProps) => {
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

        <div className="flex-1 space-y-2 overflow-hidden">
          <div className="text-sm font-medium text-muted-foreground">
            {isUser ? "Você" : "constru.ia"}
          </div>
          
          <div className="prose prose-invert prose-sm max-w-none">
            {isLoading ? (
              <div className="flex gap-1">
                <span className="w-2 h-2 bg-primary rounded-full animate-bounce [animation-delay:-0.3s]"></span>
                <span className="w-2 h-2 bg-primary rounded-full animate-bounce [animation-delay:-0.15s]"></span>
                <span className="w-2 h-2 bg-primary rounded-full animate-bounce"></span>
              </div>
            ) : (
              <ReactMarkdown
                remarkPlugins={[remarkGfm]}
                components={{
                  p: ({ children }) => <p className="mb-4 last:mb-0 text-foreground leading-7">{children}</p>,
                  ul: ({ children }) => <ul className="list-disc list-inside mb-4 space-y-1 text-foreground">{children}</ul>,
                  ol: ({ children }) => <ol className="list-decimal list-inside mb-4 space-y-1 text-foreground">{children}</ol>,
                  li: ({ children }) => <li className="text-foreground">{children}</li>,
                  code: ({ className, children }) => {
                    const isInline = !className;
                    return isInline ? (
                      <code className="bg-muted px-1.5 py-0.5 rounded text-sm font-mono text-accent">
                        {children}
                      </code>
                    ) : (
                      <code className="block bg-muted p-4 rounded-lg text-sm font-mono overflow-x-auto text-foreground">
                        {children}
                      </code>
                    );
                  },
                  pre: ({ children }) => <pre className="mb-4">{children}</pre>,
                  h1: ({ children }) => <h1 className="text-2xl font-bold mb-4 text-foreground">{children}</h1>,
                  h2: ({ children }) => <h2 className="text-xl font-bold mb-3 text-foreground">{children}</h2>,
                  h3: ({ children }) => <h3 className="text-lg font-bold mb-2 text-foreground">{children}</h3>,
                  strong: ({ children }) => <strong className="font-semibold text-foreground">{children}</strong>,
                  a: ({ children, href }) => (
                    <a href={href} className="text-accent hover:underline" target="_blank" rel="noopener noreferrer">
                      {children}
                    </a>
                  ),
                }}
              >
                {message.content}
              </ReactMarkdown>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
