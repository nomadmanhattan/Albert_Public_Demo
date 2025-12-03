import React, { useState, useRef, useEffect } from 'react';
import { Send, Sparkles } from 'lucide-react';
import MessageBubble from './MessageBubble';
import TypingIndicator from './TypingIndicator';

const ChatInterface = () => {
    const [messages, setMessages] = useState([
        { role: 'assistant', content: "Hi there, I am Albert, your personal assistant. 🦄\n\nHow can I help you?" }
    ]);
    const [input, setInput] = useState('');
    const [isLoading, setIsLoading] = useState(false);
    const messagesEndRef = useRef(null);

    const scrollToBottom = () => {
        messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
    };

    useEffect(() => {
        scrollToBottom();
    }, [messages, isLoading]);

    const handleSend = async () => {
        if (!input.trim()) return;

        const userMessage = { role: 'user', content: input };
        // Add user message AND a temporary "Understand" message from Albert immediately
        setMessages(prev => [
            ...prev,
            userMessage,
            { role: 'assistant', content: "Understand. I will go fetch your updates. You will be directed to log in with your gmail account first (if not already logged in).\n\nIt may take up to 5 mins for the audio digest to be ready. I will ping you once it is done. Go get some coffee (or tea) then come back!" }
        ]);
        setInput('');
        setIsLoading(true);

        try {
            const response = await fetch('http://localhost:8000/chat', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ message: userMessage.content })
            });

            const data = await response.json();

            // Handle potential errors or empty responses
            // Note: The backend returns { response: "..." } not { text: "..." } based on ConciergeAgent
            const botText = data.response || "Sorry, I couldn't process that. Please try again.";

            setMessages(prev => [...prev, { role: 'assistant', content: botText }]);
        } catch (error) {
            console.error("Error:", error);
            setMessages(prev => [...prev, { role: 'assistant', content: "I'm having trouble connecting to my brain 😵.\n\nLet me get some human to help.\n\nDone. I have sent a support ticket to the customer service team." }]);
        } finally {
            setIsLoading(false);
        }
    };

    const handleKeyPress = (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            handleSend();
        }
    };

    return (
        <div className="flex flex-col h-full w-full max-w-3xl mx-auto p-4">
            {/* Chat Area */}
            <div className="flex-1 overflow-y-auto mb-4 space-y-4 pr-2">
                {messages.map((msg, idx) => (
                    <MessageBubble key={idx} message={msg} />
                ))}
                {isLoading && (
                    <div className="flex justify-start">
                        <TypingIndicator />
                    </div>
                )}
                <div ref={messagesEndRef} />
            </div>

            {/* Input Area */}
            <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                    <Sparkles className="h-5 w-5 text-indigo-300" />
                </div>
                <input
                    type="text"
                    className="block w-full pl-10 pr-12 py-4 bg-white border-none rounded-full shadow-lg text-slate-700 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-indigo-500 transition-all"
                    placeholder="Ask Albert..."
                    value={input}
                    onChange={(e) => setInput(e.target.value)}
                    onKeyDown={handleKeyPress}
                    disabled={isLoading}
                />
                <button
                    onClick={handleSend}
                    disabled={isLoading || !input.trim()}
                    className="absolute inset-y-0 right-0 pr-2 flex items-center"
                >
                    <div className={`p-2 rounded-full ${isLoading || !input.trim() ? 'bg-slate-100 text-slate-300' : 'bg-indigo-500 text-white hover:bg-indigo-600'} transition-colors`}>
                        <Send className="h-5 w-5" />
                    </div>
                </button>
            </div>
        </div>
    );
};

export default ChatInterface;
