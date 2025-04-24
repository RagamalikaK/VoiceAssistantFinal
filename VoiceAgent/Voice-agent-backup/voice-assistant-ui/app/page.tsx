import VoiceAssistant from "@/components/VoiceAssistant";

export default function Home() {
  return (
    <div className="flex flex-col min-h-screen mbta-bg-image bg-mbta-background">
      {/* Semi-transparent overlay to ensure text readability */}
      <div className="absolute inset-0 bg-black/30 -z-10"></div>
      
      <header className="mb-4 text-center z-10">
        <h1 className="text-3xl font-bold text-white">MBTA Voice Assistant</h1>
        <p className="text-white">Ask questions about Boston's public transportation system</p>
      </header>
      
      <main className="flex-grow flex items-center justify-center w-full p-4 z-10">
        <VoiceAssistant />
      </main>
      
      <footer className="mt-4 text-center text-sm text-white/80 z-10">
        <p>© 2024 MBTA Voice Assistant | Powered by Next.js, NextUI, and AI</p>
      </footer>
    </div>
  );
}
