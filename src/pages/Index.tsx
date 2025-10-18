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
}

const Index = () => {
  const [messages, setMessages] = useState<Message[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(scrollToBottom, [messages]);

  const sendMessage = async (text: string) => {
    const userMessage: Message = { role: "user", content: text };
    setMessages((prev) => [...prev, userMessage]);
    setIsLoading(true);

    // simulação de resposta da IA
    setTimeout(() => {
      const aiMessage: Message = {
        role: "assistant",
        content: `🤖 constru.ia: resposta simulada para "${text}"`,
      };
      setMessages((prev) => [...prev, aiMessage]);
      setIsLoading(false);
    }, 1200);
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
              <div className="h-full flex items-center justify-center text-center">
                <div className="flex flex-col items-center gap-4 text-muted-foreground">
                  <Bot className="w-10 h-10 text-primary" />
                  <h2 className="text-lg font-semibold text-foreground">
                    Bem-vindo ao constru.ia 👋
                  </h2>
                  <p className="text-sm max-w-sm">
                    Envie uma mensagem para começar. Use termos como{" "}
                    <span className="text-primary font-medium">
                      “pedidos pendentes”
                    </span>{" "}
                    ou{" "}
                    <span className="text-primary font-medium">
                      “itens do pedido 123”
                    </span>.
                  </p>
                </div>
              </div>
            ) : (
              messages.map((m, i) => (
                <ChatMessage key={i} message={m} isLoading={isLoading && i === messages.length - 1} />
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
