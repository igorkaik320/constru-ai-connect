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
  };

  const handleLogout = async () => {
    await supabase.auth.signOut();
  };

  return (
    <>
      <Sidebar className="w-64 bg-[#0e0e10] text-gray-100 border-r border-gray-800">
        <SidebarContent>
          <SidebarGroup>
            <div className="flex items-center justify-between px-3 py-3 border-b border-gray-800">
              <SidebarGroupLabel className="text-sm font-semibold text-gray-300 tracking-wide">
                Conversas
              </SidebarGroupLabel>
              <Button
                size="sm"
                variant="ghost"
                onClick={onCreateConversation}
                className="h-8 w-8 p-0 hover:bg-purple-700/30 text-purple-400"
              >
                <Plus className="h-4 w-4" />
              </Button>
            </div>

            <SidebarGroupContent>
              <SidebarMenu className="mt-2 space-y-1">
                {conversations.map((conv) => (
                  <SidebarMenuItem key={conv.id}>
                    <SidebarMenuButton
                      onClick={() => onSelectConversation(conv.id)}
                      isActive={currentConversationId === conv.id}
                      className={cn(
                        "flex w-full text-sm rounded-lg px-3 py-2 transition-all",
                        currentConversationId === conv.id
                          ? "bg-gradient-to-r from-purple-600 to-blue-600 text-white shadow-md"
                          : "hover:bg-[#1a1a1d] text-gray-300"
                      )}
                    >
                      <span className="truncate">{conv.title}</span>
                      <DropdownMenu>
                        <DropdownMenuTrigger asChild>
                          <Button
                            size="sm"
                            variant="ghost"
                            className="ml-auto h-8 w-8 p-0 text-gray-400 hover:text-white"
                          >
                            <MoreVertical className="h-4 w-4" />
                          </Button>
                        </DropdownMenuTrigger>
                        <DropdownMenuContent align="end" className="bg-[#1a1a1d] border-gray-700 text-gray-200">
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
                            onClick={() => {
                              setSelectedConv(conv);
                              setDeleteDialogOpen(true);
                            }}
                            className="text-red-400 hover:text-red-300"
                          >
                            Excluir
                          </DropdownMenuItem>
                        </DropdownMenuContent>
                      </DropdownMenu>
                    </SidebarMenuButton>
                  </SidebarMenuItem>
                ))}
              </SidebarMenu>
            </SidebarGroupContent>
          </SidebarGroup>

          <div className="mt-auto p-3 border-t border-gray-800">
            <Button
              variant="ghost"
              size="sm"
              onClick={handleLogout}
              className="w-full justify-start text-gray-400 hover:text-white hover:bg-[#1a1a1d]"
            >
              <LogOut className="h-4 w-4 mr-2" />
              Sair
            </Button>
          </div>
        </SidebarContent>
      </Sidebar>

      {/* Rename Dialog */}
      <AlertDialog open={renameDialogOpen} onOpenChange={setRenameDialogOpen}>
        <AlertDialogContent className="bg-[#1a1a1d] text-gray-100 border-gray-700">
          <AlertDialogHeader>
            <AlertDialogTitle>Renomear conversa</AlertDialogTitle>
            <AlertDialogDescription className="text-gray-400">
              Digite o novo nome para esta conversa.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <Input
            value={newTitle}
            onChange={(e) => setNewTitle(e.target.value)}
            placeholder="Nome da conversa"
            className="bg-[#0e0e10] border-gray-700 text-gray-100 placeholder-gray-500"
          />
          <AlertDialogFooter>
            <AlertDialogCancel>Cancelar</AlertDialogCancel>
            <AlertDialogAction
              onClick={handleRename}
              className="bg-gradient-to-r from-purple-600 to-blue-600 text-white hover:opacity-90"
            >
              Renomear
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      {/* Delete Dialog */}
      <AlertDialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
        <AlertDialogContent className="bg-[#1a1a1d] text-gray-100 border-gray-700">
          <AlertDialogHeader>
            <AlertDialogTitle>Excluir conversa</AlertDialogTitle>
            <AlertDialogDescription className="text-gray-400">
              Tem certeza que deseja excluir esta conversa? Esta ação não pode ser desfeita.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancelar</AlertDialogCancel>
            <AlertDialogAction
              onClick={handleDelete}
              className="bg-red-600 hover:bg-red-700 text-white"
            >
              Excluir
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </>
  );
}
