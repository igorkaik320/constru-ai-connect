import { useState, useRef, useEffect } from "react";
import { ChatMessage } from "@/components/ChatMessage";
import { ChatInput } from "@/components/ChatInput";
import { ChatHeader } from "@/components/ChatHeader";
import { useToast } from "@/hooks/use-toast";
import { Loader2 } from "lucide-react";
import { sendMessageToBackend } from "@/backendClient";

interface Message {
  role: "user" | "assistant";
  content: string;
}

const Index = () => {
  const [messages, setMessages] = useState<Message[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const { toast } = useToast();

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const sendMessage = async (text: string) => {
    const userMessage: Message = {
      role: "user",
      content: text,
    };

    setMessages((prev) => [...prev, userMessage]);
    setIsLoading(true);

    try {
      const response = await sendMessageToBackend("usuário", text);

      const aiMessage: Message = {
        role: "assistant",
        content: response,
      };

      setMessages((prev) => [...prev, aiMessage]);
    } catch (error) {
      console.error("Erro ao enviar mensagem:", error);
      toast({
        title: "Erro",
        description: "Erro ao se comunicar com a IA.",
        variant: "destructive",
      });
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="flex flex-col h-screen bg-background">
      <ChatHeader />

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
                Sua assistente de IA inteligente. Faça perguntas, peça ajuda ou
                converse sobre qualquer assunto.
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
  );
};

export default Index;
