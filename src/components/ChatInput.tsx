import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Send } from "lucide-react";
import { cn } from "@/lib/utils";

interface ChatInputProps {
  onSend: (message: string) => void;
  isLoading: boolean;
}

export const ChatInput = ({ onSend, isLoading }: ChatInputProps) => {
  const [input, setInput] = useState("");

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (input.trim() && !isLoading) {
      onSend(input.trim());
      setInput("");
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  return (
    <div className="border-t border-border bg-card/50 backdrop-blur-sm">
      <form onSubmit={handleSubmit} className="max-w-3xl mx-auto p-4">
        <div className="relative flex items-end gap-2">
          <Textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Envie uma mensagem para constru.ia..."
            disabled={isLoading}
            className={cn(
              "min-h-[60px] max-h-[200px] resize-none pr-12",
              "bg-muted/50 border-border",
              "focus-visible:ring-primary focus-visible:border-primary",
              "transition-all duration-200"
            )}
            rows={1}
          />
          <Button
            type="submit"
            size="icon"
            disabled={!input.trim() || isLoading}
            className={cn(
              "absolute right-2 bottom-2 h-10 w-10",
              "bg-gradient-to-br from-primary to-accent",
              "hover:opacity-90 transition-all duration-200",
              "disabled:opacity-50"
            )}
          >
            <Send className="h-4 w-4" />
          </Button>
        </div>
        <p className="text-xs text-muted-foreground mt-2 text-center">
          Pressione Enter para enviar, Shift + Enter para nova linha
        </p>
      </form>
    </div>
  );
};
