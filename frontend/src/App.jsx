import React from 'react';
import ChatInterface from './components/ChatInterface';
import albertFace from './assets/albert_face.png';

function App() {
  return (
    <div className="h-screen w-screen bg-slate-50 flex flex-col items-center relative overflow-hidden">

      {/* Background Decoration */}
      <div className="absolute top-[-10%] left-[-10%] w-[500px] h-[500px] bg-indigo-200 rounded-full mix-blend-multiply filter blur-3xl opacity-30 animate-float"></div>
      <div className="absolute bottom-[-10%] right-[-10%] w-[500px] h-[500px] bg-pink-200 rounded-full mix-blend-multiply filter blur-3xl opacity-30 animate-float" style={{ animationDelay: '2s' }}></div>

      {/* Header */}
      <header className="z-10 w-full max-w-3xl pt-8 pb-4 px-6 flex items-center justify-between">
        <div className="flex items-center space-x-4">
          <div className="relative">
            <div className="w-16 h-16 rounded-full overflow-hidden border-4 border-white shadow-md">
              <img src={albertFace} alt="Albert" className="w-full h-full object-cover" />
            </div>
            <div className="absolute bottom-0 right-0 w-4 h-4 bg-green-400 border-2 border-white rounded-full"></div>
          </div>
          <div>
            <h1 className="text-2xl font-bold text-slate-800 tracking-tight">Albert</h1>
            <p className="text-sm text-slate-500 font-medium">Your Personal News Butler</p>
          </div>
        </div>
        <div className="hidden md:block">
          <span className="px-3 py-1 bg-white rounded-full text-xs font-semibold text-indigo-500 shadow-sm border border-indigo-50">
            Gemini 2.5 Flash
          </span>
        </div>
      </header>

      {/* Main Chat Container */}
      <main className="flex-1 w-full z-10 relative flex flex-col min-h-0">
        <ChatInterface />
      </main>

      {/* Footer */}
      <footer className="w-full py-4 text-center text-xs text-slate-400 z-10">
        Powered by Google ADK & NotebookLM
      </footer>
    </div>
  );
}

export default App;
