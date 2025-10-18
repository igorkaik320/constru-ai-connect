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
    <div className="border-t border-gray-800 bg-[#0e0e10]/90 backdrop-blur-md">
      <form onSubmit={handleSubmit} className="max-w-3xl mx-auto p-4">
        <div className="relative flex items-end gap-3">
          <Textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Envie uma mensagem para constru.ia..."
            disabled={isLoading}
            className={cn(
              "min-h-[60px] max-h-[200px] resize-none pr-12",
              "bg-[#1a1a1d] border border-gray-700 text-gray-100",
              "placeholder-gray-500 rounded-xl shadow-inner",
              "focus-visible:ring-2 focus-visible:ring-purple-500/50 focus-visible:border-purple-400",
              "transition-all duration-200 ease-in-out"
            )}
            rows={1}
          />

          <Button
            type="submit"
            size="icon"
            disabled={!input.trim() || isLoading}
            className={cn(
              "absolute right-2 bottom-2 h-10 w-10",
              "bg-gradient-to-br from-purple-500 to-blue-500",
              "hover:opacity-90 transition-all duration-200 rounded-xl",
              "disabled:opacity-50"
            )}
          >
            <Send className="h-4 w-4 text-white" />
          </Button>
        </div>

        <p className="text-xs text-gray-500 mt-2 text-center">
          Pressione <span className="text-gray-300 font-medium">Enter</span> para enviar,&nbsp;
          <span className="text-gray-300 font-medium">Shift + Enter</span> para nova linha
        </p>
      </form>
    </div>
  );
};
