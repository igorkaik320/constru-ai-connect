import { useState, useRef, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { supabase } from "@/integrations/supabase/client";
import { ChatMessage } from "@/components/ChatMessage";
import { ChatInput } from "@/components/ChatInput";
import { ChatHeader } from "@/components/ChatHeader";
import { ConversationsSidebar } from "@/components/ConversationsSidebar";
import { SidebarProvider, SidebarTrigger } from "@/components/ui/sidebar";
import { useToast } from "@/hooks/use-toast";
import { Loader2 } from "lucide-react";
import { sendMessageToBackend } from "@/backendClient";

interface Message {
  id?: string;
  role: "user" | "assistant";
  content: string;
  created_at?: string;
}

const Index = () => {
  const [currentConversationId, setCurrentConversationId] = useState<string | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [user, setUser] = useState<any>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const { toast } = useToast();
  const navigate = useNavigate();

  useEffect(() => {
    // Verificar autenticação
    supabase.auth.getSession().then(({ data: { session } }) => {
      if (!session) {
        navigate("/auth");
      } else {
        setUser(session.user);
        loadOrCreateConversation(session.user.id);
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

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const loadOrCreateConversation = async (userId: string) => {
    // Buscar conversas existentes
    const { data: conversations } = await supabase
      .from("conversations")
      .select("*")
      .eq("user_id", userId)
      .order("updated_at", { ascending: false })
      .limit(1);

    if (conversations && conversations.length > 0) {
      setCurrentConversationId(conversations[0].id);
      loadMessages(conversations[0].id);
    } else {
      createNewConversation();
    }
  };

  const loadMessages = async (conversationId: string) => {
    const { data, error } = await supabase
      .from("messages")
      .select("*")
      .eq("conversation_id", conversationId)
      .order("created_at", { ascending: true });

    if (error) {
      toast({
        title: "Erro",
        description: "Falha ao carregar mensagens.",
        variant: "destructive",
      });
      return;
    }

    const typedMessages = (data || []).map((msg) => ({
      ...msg,
      role: msg.role as "user" | "assistant",
    }));
    setMessages(typedMessages);
  };

  const createNewConversation = async () => {
    if (!user) return;

    const { data, error } = await supabase
      .from("conversations")
      .insert({
        title: "Nova Conversa",
        user_id: user.id,
      })
      .select()
      .single();

    if (error) {
      toast({
        title: "Erro",
        description: "Falha ao criar conversa.",
        variant: "destructive",
      });
      return;
    }

    setCurrentConversationId(data.id);
    setMessages([]);
  };

  const handleSelectConversation = (conversationId: string) => {
    setCurrentConversationId(conversationId);
    loadMessages(conversationId);
  };

  const updateConversationTitle = async (conversationId: string, firstMessage: string) => {
    const truncatedTitle = firstMessage.substring(0, 30);
    await supabase
      .from("conversations")
      .update({ title: truncatedTitle })
      .eq("id", conversationId);
  };

  const sendMessage = async (text: string) => {
    if (!currentConversationId || !user) return;

    // Criar mensagem do usuário
    const userMessage: Message = { role: "user", content: text };
    setMessages((prev) => [...prev, userMessage]);
    setIsLoading(true);

    // Salvar mensagem do usuário no banco
    const { data: savedUserMsg } = await supabase
      .from("messages")
      .insert({
        conversation_id: currentConversationId,
        role: "user",
        content: text,
      })
      .select()
      .single();

    // Verificar se é a primeira mensagem para atualizar título
    const { data: existingMessages } = await supabase
      .from("messages")
      .select("id")
      .eq("conversation_id", currentConversationId);

    if (existingMessages && existingMessages.length === 1) {
      await updateConversationTitle(currentConversationId, text);
    }

    try {
      const response = await sendMessageToBackend(user.email || "usuário", text);

      // Criar mensagem do assistente
      const assistantMessage: Message = { role: "assistant", content: response };
      setMessages((prev) => [...prev, assistantMessage]);

      // Salvar mensagem do assistente no banco
      await supabase
        .from("messages")
        .insert({
          conversation_id: currentConversationId,
          role: "assistant",
          content: response,
        });

      // Atualizar updated_at da conversa
      await supabase
        .from("conversations")
        .update({ updated_at: new Date().toISOString() })
        .eq("id", currentConversationId);
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

  if (!user) {
    return null;
  }

  return (
    <SidebarProvider>
      <div className="flex min-h-screen w-full">
        <ConversationsSidebar
          currentConversationId={currentConversationId}
          onSelectConversation={handleSelectConversation}
          onCreateConversation={createNewConversation}
        />

        <div className="flex flex-col flex-1 h-screen">
          <header className="h-12 flex items-center border-b px-4">
            <SidebarTrigger />
            <ChatHeader />
          </header>

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
                    Digite sua mensagem para interagir com o sistema Sienge.
                  </p>
                </div>
              </div>
            )}

            {messages.map((message, index) => (
              <ChatMessage key={index} message={message} />
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
      </div>
    </SidebarProvider>
  );
};

export default Index;
