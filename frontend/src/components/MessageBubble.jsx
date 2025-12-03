import React from 'react';
import { motion } from 'framer-motion';
import ReactMarkdown from 'react-markdown';

import albertFace from '../assets/albert_face.png';

const MessageBubble = ({ message }) => {
    const isUser = message.role === 'user';

    return (
        <motion.div
            initial={{ opacity: 0, y: 10, scale: 0.95 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            transition={{ duration: 0.3 }}
            className={`flex w-full ${isUser ? 'justify-end' : 'justify-start'} mb-4 items-end gap-2`}
        >
            {!isUser && (
                <div className="w-8 h-8 rounded-full overflow-hidden border-2 border-white shadow-sm flex-shrink-0">
                    <img src={albertFace} alt="Albert" className="w-full h-full object-cover" />
                </div>
            )}

            <div
                className={`max-w-[80%] p-4 rounded-2xl shadow-sm text-sm md:text-base leading-relaxed ${isUser
                    ? 'bg-indigo-500 text-white rounded-tr-none'
                    : 'bg-white text-slate-800 rounded-tl-none border border-slate-100'
                    }`}
            >
                <ReactMarkdown
                    components={{
                        a: ({ node, ...props }) => <a {...props} className="underline font-bold hover:text-indigo-200" target="_blank" rel="noopener noreferrer" />
                    }}
                >
                    {message.content}
                </ReactMarkdown>
            </div>
        </motion.div>
    );
};

export default MessageBubble;
