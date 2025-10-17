import { useState, useEffect } from "react";
import { ChatHeader } from "@/components/ChatHeader";
import { ChatInput } from "@/components/ChatInput";
import { ChatMessage } from "@/components/ChatMessage";
import axios from "axios";
import { Button } from "@/components/ui/button";
import { AlertDialog, AlertDialogContent, AlertDialogHeader, AlertDialogTitle, AlertDialogDescription, AlertDialogFooter, AlertDialogAction, AlertDialogCancel } from "@/components/ui/alert-dialog";

interface Message {
  role: "user" | "assistant";
  content: string;
  type?: "text" | "pedidos" | "itens";
  pedidos?: any[];
  table?: { headers: string[]; rows: any[][]; total?: number };
  buttons?: { label: string; action: string; pedido_id?: number }[];
}

export const Chat = () => {
  const [messages, setMessages] = useState<Message[]>([]);
  const [loading, setLoading] = useState(false);
  const [confirmDialog, setConfirmDialog] = useState<{
    open: boolean;
    action?: "autorizar" | "reprovar";
    pedido_id?: number;
  }>({ open: false });

  // Função para enviar mensagem para o backend
  const sendMessage = async (text: string) => {
    const userMsg: Message = { role: "user", content: text };
    setMessages((prev) => [...prev, userMsg]);
    setLoading(true);

    try {
      const { data } = await axios.post("/mensagem", { user: "usuario", text });
      const botMsg: Message = { role: "assistant", content: data.response };

      // Se o backend retornar pedidos ou tabela
      if (data.pedidos) botMsg.pedidos = data.pedidos;
      if (data.table) botMsg.table = data.table;
      if (data.buttons) botMsg.buttons = data.buttons;

      setMessages((prev) => [...prev, botMsg]);
    } catch (err) {
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: "Erro ao se comunicar com o servidor." },
      ]);
    } finally {
      setLoading(false);
    }
  };

  // Função quando o usuário clica em um botão de ação (Autorizar/Reprovar)
  const handleAction = (pedido_id: number, acao: "autorizar" | "reprovar") => {
    setConfirmDialog({ open: true, action: acao, pedido_id });
  };

  const confirmAction = async () => {
    if (!confirmDialog.pedido_id || !confirmDialog.action) return;
    setConfirmDialog({ open: false });

    // Enviar mensagem pro backend simulando comando do usuário
    const comando = `${confirmDialog.action} pedido ${confirmDialog.pedido_id}`;
    await sendMessage(comando);
  };

  // Botões iniciais
  const handleInitialButton = (acao: string) => {
    switch (acao) {
      case "listar_pendentes":
        sendMessage("Listar pedidos pendentes de autorização");
        break;
      case "ver_itens":
        sendMessage("Ver itens de um pedido específico");
        break;
      case "gerar_pdf":
        sendMessage("Gerar PDF do pedido");
        break;
      default:
        break;
    }
  };

  return (
    <div className="flex flex-col h-full">
      <ChatHeader />

      {/* Botões iniciais */}
      <div className="flex gap-2 p-4 bg-card/50 border-b border-border">
        <Button onClick={() => handleInitialButton("listar_pendentes")}>
          Pedidos Pendentes
        </Button>
        <Button onClick={() => handleInitialButton("ver_itens")}>
          Ver Itens
        </Button>
        <Button onClick={() => handleInitialButton("gerar_pdf")}>
          Gerar PDF
        </Button>
      </div>

      {/* Mensagens */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.map((m, i) => (
          <ChatMessage
            key={i}
            message={m}
            isLoading={loading && i === messages.length - 1}
            onAction={handleAction}
          />
        ))}
      </div>

      {/* Input */}
      <ChatInput onSend={sendMessage} isLoading={loading} />

      {/* Dialogo de confirmação */}
      <AlertDialog open={confirmDialog.open} onOpenChange={(o) => setConfirmDialog((prev) => ({ ...prev, open: o }))}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Confirmação</AlertDialogTitle>
            <AlertDialogDescription>
              Tem certeza que deseja {confirmDialog.action} o pedido {confirmDialog.pedido_id}?
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancelar</AlertDialogCancel>
            <AlertDialogAction onClick={confirmAction}>
              Confirmar
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
};
