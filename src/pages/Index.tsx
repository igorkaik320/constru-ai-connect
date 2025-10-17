import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { supabase } from "@/integrations/supabase/client";
import { SidebarProvider } from "@/components/ui/sidebar";
import { ConversationsSidebar } from "@/components/ConversationsSidebar";
import { Chat } from "@/components/Chat";
import { useToast } from "@/hooks/use-toast";

const Index = () => {
  const [currentConversationId, setCurrentConversationId] = useState<string | null>(null);
  const [user, setUser] = useState<any>(null);
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
    } else {
      createNewConversation();
    }
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
  };

  const handleSelectConversation = (conversationId: string) => {
    setCurrentConversationId(conversationId);
  };

  if (!user) return null;

  return (
    <SidebarProvider>
      <div className="flex min-h-screen w-full">
        <ConversationsSidebar
          currentConversationId={currentConversationId}
          onSelectConversation={handleSelectConversation}
          onCreateConversation={createNewConversation}
        />

        <div className="flex-1 h-screen">
          <Chat currentUser={user} />
        </div>
      </div>
    </SidebarProvider>
  );
};

export default Index;
