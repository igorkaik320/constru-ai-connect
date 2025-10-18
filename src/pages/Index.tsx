import { useState, useRef, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { ChatMessage } from "@/components/ChatMessage";
import { ChatInput } from "@/components/ChatInput";
import { ChatHeader } from "@/components/ChatHeader";
import { ConversationsSidebar } from "@/components/ConversationsSidebar";
import { SidebarProvider } from "@/components/ui/sidebar";
import { Bot } from "lucide-react";
import { supabase } from "@/integrations/supabase/client";
import { sendMessageToBackend } from "@/backendClient";
import type { User } from "@supabase/supabase-js";

interface Message {
  role: "user" | "assistant";
  content: string;
}

interface Conversation {
  id: string;
  title: string;
  created_at: string;
  updated_at: string;
  user_id: string;
}

const Index = () => {
  const [user, setUser] = useState<User | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [currentConversation, setCurrentConversation] = useState<Conversation | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const navigate = useNavigate();

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(scrollToBottom, [messages]);

  // Verificar autenticação
  useEffect(() => {
    supabase.auth.getSession().then(({ data: { session } }) => {
      if (!session) {
        navigate("/auth");
      } else {
        setUser(session.user);
      }
    });

    const { data: { subscription } } = supabase.auth.onAuthStateChange((event, session) => {
      if (!session) {
        navigate("/auth");
      } else {
        setUser(session.user);
      }
    });

    return () => subscription.unsubscribe();
  }, [navigate]);

  // Carregar mensagens da conversa atual
  useEffect(() => {
    if (!currentConversation) return;

    const loadMessages = async () => {
      const { data, error } = await supabase
        .from("messages")
        .select("*")
        .eq("conversation_id", currentConversation.id)
        .order("created_at", { ascending: true });

      if (error) {
        console.error("Erro ao carregar mensagens:", error);
        return;
      }

      setMessages(data.map((m: any) => ({ role: m.role, content: m.content })));
    };

    loadMessages();
  }, [currentConversation]);

  const handleSelectConversation = (conversation: Conversation) => {
    setCurrentConversation(conversation);
  };

  const handleCreateConversation = (conversation: Conversation) => {
    setCurrentConversation(conversation);
    setMessages([]);
  };

  const sendMessage = async (text: string) => {
    if (!currentConversation || !user) return;

    const userMessage: Message = { role: "user", content: text };
    setMessages((prev) => [...prev, userMessage]);
    setIsLoading(true);

    try {
      // Salvar mensagem do usuário no banco
      await supabase.from("messages").insert({
        conversation_id: currentConversation.id,
        role: "user",
        content: text,
      });

      // Chamar backend FastAPI
      const aiResponse = await sendMessageToBackend(user.email || user.id, text);

      const aiMessage: Message = {
        role: "assistant",
        content: aiResponse,
      };
      setMessages((prev) => [...prev, aiMessage]);

      // Salvar resposta da IA no banco
      await supabase.from("messages").insert({
        conversation_id: currentConversation.id,
        role: "assistant",
        content: aiResponse,
      });

      // Atualizar título da conversa se for "Nova Conversa"
      if (currentConversation.title === "Nova Conversa") {
        const newTitle = text.slice(0, 30) + (text.length > 30 ? "..." : "");
        await supabase
          .from("conversations")
          .update({ title: newTitle })
          .eq("id", currentConversation.id);
        setCurrentConversation({ ...currentConversation, title: newTitle });
      }
    } catch (error) {
      console.error("Erro ao enviar mensagem:", error);
      const errorMessage: Message = {
        role: "assistant",
        content: "Erro ao se comunicar com a IA. Tente novamente.",
      };
      setMessages((prev) => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <SidebarProvider>
      <div className="flex min-h-screen w-full bg-[hsl(var(--background))]">
        <ConversationsSidebar
          currentConversationId={currentConversation?.id || ""}
          onSelectConversation={handleSelectConversation}
          onCreateConversation={handleCreateConversation}
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
                      "pedidos pendentes"
                    </span>{" "}
                    ou{" "}
                    <span className="text-primary font-medium">
                      "itens do pedido 123"
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
