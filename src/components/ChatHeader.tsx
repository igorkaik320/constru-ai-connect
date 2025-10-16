import { Sparkles } from "lucide-react";

export const ChatHeader = () => {
  return (
    <header className="sticky top-0 z-10 border-b border-border bg-card/80 backdrop-blur-md">
      <div className="max-w-3xl mx-auto px-4 py-4 flex items-center justify-between">
        <div className="flex items-center gap-3">
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
      </div>
    </header>
  );
};
