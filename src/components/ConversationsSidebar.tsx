import { useState, useEffect } from "react";
import { supabase } from "@/integrations/supabase/client";
import { useToast } from "@/hooks/use-toast";
import {
  Sidebar,
  SidebarContent,
  SidebarGroup,
  SidebarGroupContent,
  SidebarGroupLabel,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  SidebarTrigger,
  useSidebar,
} from "@/components/ui/sidebar";
import { Button } from "@/components/ui/button";
import { Plus, MoreVertical, LogOut } from "lucide-react";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { Input } from "@/components/ui/input";

interface Conversation {
  id: string;
  title: string;
  created_at: string;
  updated_at: string;
}

interface ConversationsSidebarProps {
  currentConversationId: string | null;
  onSelectConversation: (id: string) => void;
  onCreateConversation: () => void;
}

export function ConversationsSidebar({
  currentConversationId,
  onSelectConversation,
  onCreateConversation,
}: ConversationsSidebarProps) {
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [renameDialogOpen, setRenameDialogOpen] = useState(false);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [selectedConv, setSelectedConv] = useState<Conversation | null>(null);
  const [newTitle, setNewTitle] = useState("");
  const { state } = useSidebar();
  const collapsed = state === "collapsed";
  const { toast } = useToast();

  useEffect(() => {
    loadConversations();
  }, []);

  const loadConversations = async () => {
    const { data, error } = await supabase
      .from("conversations")
      .select("*")
      .order("updated_at", { ascending: false });

    if (error) {
      toast({
        title: "Erro",
        description: "Falha ao carregar conversas.",
        variant: "destructive",
      });
      return;
    }

    setConversations(data || []);
  };

  const handleRename = async () => {
    if (!selectedConv || !newTitle.trim()) return;

    const { error } = await supabase
      .from("conversations")
      .update({ title: newTitle.trim() })
      .eq("id", selectedConv.id);

    if (error) {
      toast({
        title: "Erro",
        description: "Falha ao renomear conversa.",
        variant: "destructive",
      });
      return;
    }

    await loadConversations();
    setRenameDialogOpen(false);
    setNewTitle("");
  };

  const handleDuplicate = async (conv: Conversation) => {
    // Buscar mensagens da conversa
    const { data: messages, error: messagesError } = await supabase
      .from("messages")
      .select("*")
      .eq("conversation_id", conv.id)
      .order("created_at", { ascending: true });

    if (messagesError) {
      toast({
        title: "Erro",
        description: "Falha ao duplicar conversa.",
        variant: "destructive",
      });
      return;
    }

    // Criar nova conversa
    const { data: newConv, error: convError } = await supabase
      .from("conversations")
      .insert({
        title: `${conv.title} (cópia)`,
        user_id: (await supabase.auth.getUser()).data.user?.id,
      })
      .select()
      .single();

    if (convError || !newConv) {
      toast({
        title: "Erro",
        description: "Falha ao criar conversa duplicada.",
        variant: "destructive",
      });
      return;
    }

    // Copiar mensagens
    if (messages && messages.length > 0) {
      const newMessages = messages.map((msg) => ({
        conversation_id: newConv.id,
        role: msg.role,
        content: msg.content,
      }));

      await supabase.from("messages").insert(newMessages);
    }

    await loadConversations();
    onSelectConversation(newConv.id);

    toast({
      title: "Conversa duplicada",
      description: "A conversa foi duplicada com sucesso.",
    });
  };

  const handleDelete = async () => {
    if (!selectedConv) return;

    const { error } = await supabase
      .from("conversations")
      .delete()
      .eq("id", selectedConv.id);

    if (error) {
      toast({
        title: "Erro",
        description: "Falha ao excluir conversa.",
        variant: "destructive",
      });
      return;
    }

    await loadConversations();
    setDeleteDialogOpen(false);

    // Se a conversa excluída era a atual, selecionar a primeira
    if (currentConversationId === selectedConv.id) {
      const remaining = conversations.filter((c) => c.id !== selectedConv.id);
      if (remaining.length > 0) {
        onSelectConversation(remaining[0].id);
      } else {
        onCreateConversation();
      }
    }
  };

  const handleLogout = async () => {
    await supabase.auth.signOut();
  };

  return (
    <>
      <Sidebar className={collapsed ? "w-14" : "w-64"} collapsible="icon">
        <SidebarContent>
          <SidebarGroup>
            <div className="flex items-center justify-between px-2 py-2">
              {!collapsed && (
                <SidebarGroupLabel>Conversas</SidebarGroupLabel>
              )}
              <Button
                size="sm"
                variant="ghost"
                onClick={onCreateConversation}
                className="h-8 w-8 p-0"
              >
                <Plus className="h-4 w-4" />
              </Button>
            </div>

            <SidebarGroupContent>
              <SidebarMenu>
                {conversations.map((conv) => (
                  <SidebarMenuItem key={conv.id}>
                    <div className="flex items-center gap-1">
                      <SidebarMenuButton
                        onClick={() => onSelectConversation(conv.id)}
                        isActive={currentConversationId === conv.id}
                        className="flex-1"
                      >
                        {!collapsed && (
                          <span className="truncate">{conv.title}</span>
                        )}
                      </SidebarMenuButton>
                      {!collapsed && (
                        <DropdownMenu>
                          <DropdownMenuTrigger asChild>
                            <Button
                              size="sm"
                              variant="ghost"
                              className="h-8 w-8 p-0"
                            >
                              <MoreVertical className="h-4 w-4" />
                            </Button>
                          </DropdownMenuTrigger>
                          <DropdownMenuContent align="end">
                            <DropdownMenuItem
                              onClick={() => {
                                setSelectedConv(conv);
                                setNewTitle(conv.title);
                                setRenameDialogOpen(true);
                              }}
                            >
                              Renomear
                            </DropdownMenuItem>
                            <DropdownMenuItem
                              onClick={() => handleDuplicate(conv)}
                            >
                              Duplicar
                            </DropdownMenuItem>
                            <DropdownMenuItem
                              onClick={() => {
                                setSelectedConv(conv);
                                setDeleteDialogOpen(true);
                              }}
                              className="text-red-600"
                            >
                              Excluir
                            </DropdownMenuItem>
                          </DropdownMenuContent>
                        </DropdownMenu>
                      )}
                    </div>
                  </SidebarMenuItem>
                ))}
              </SidebarMenu>
            </SidebarGroupContent>
          </SidebarGroup>

          <div className="mt-auto p-2">
            <Button
              variant="ghost"
              size="sm"
              onClick={handleLogout}
              className="w-full justify-start"
            >
              <LogOut className="h-4 w-4 mr-2" />
              {!collapsed && "Sair"}
            </Button>
          </div>
        </SidebarContent>
      </Sidebar>

      {/* Rename Dialog */}
      <AlertDialog open={renameDialogOpen} onOpenChange={setRenameDialogOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Renomear conversa</AlertDialogTitle>
            <AlertDialogDescription>
              Digite o novo nome para a conversa
            </AlertDialogDescription>
          </AlertDialogHeader>
          <Input
            value={newTitle}
            onChange={(e) => setNewTitle(e.target.value)}
            placeholder="Nome da conversa"
          />
          <AlertDialogFooter>
            <AlertDialogCancel>Cancelar</AlertDialogCancel>
            <AlertDialogAction onClick={handleRename}>
              Renomear
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      {/* Delete Dialog */}
      <AlertDialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Excluir conversa</AlertDialogTitle>
            <AlertDialogDescription>
              Tem certeza que deseja excluir esta conversa? Esta ação não pode
              ser desfeita.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancelar</AlertDialogCancel>
            <AlertDialogAction
              onClick={handleDelete}
              className="bg-red-600 hover:bg-red-700"
            >
              Excluir
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </>
  );
}
