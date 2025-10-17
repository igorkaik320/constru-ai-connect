import { Sparkles } from "lucide-react";

export const ChatHeader = () => {
  return (
    <div className="flex items-center gap-3 flex-1">
      <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-primary to-accent flex items-center justify-center">
        <Sparkles className="w-6 h-6 text-primary-foreground" />
      </div>
      <div>
        <h1 className="text-xl font-bold bg-gradient-to-r from-primary to-accent bg-clip-text text-transparent">
          constru.ia
        </h1>
        <p className="text-xs text-muted-foreground">
          Assistente de IA inteligente
        </p>
      </div>
    </div>
  );
};
