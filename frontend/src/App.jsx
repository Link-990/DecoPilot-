import React, { useState, useRef, useEffect } from 'react';
import ReactMarkdown from 'react-markdown';
import { 
  Send, Bot, User, Brain, Search, Loader2, 
  Menu, Plus, MessageSquare, Settings, MoreVertical, LogOut, PanelLeftClose, PanelLeft, Trash2 
} from 'lucide-react';
import './index.css';

function App() {
  // Chat State
  const [messages, setMessages] = useState([
    { role: 'assistant', content: '你好，我是您的装修顾问，关于装修有什么可以帮您？' }
  ]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [enableSearch, setEnableSearch] = useState(true);
  const [showThinking, setShowThinking] = useState(true);
  const [currentChatId, setCurrentChatId] = useState(null);
  
  // UI State
  const [isSidebarOpen, setIsSidebarOpen] = useState(true);
  const [activeMenuId, setActiveMenuId] = useState(null);
  const [history, setHistory] = useState([
    { 
      id: 1, 
      title: '装修风格咨询', 
      date: '今天',
      messages: [
        { role: 'assistant', content: '你好，我是您的装修顾问，关于装修有什么可以帮您？' },
        { role: 'user', content: '我想了解一下现在的流行装修风格' },
        { role: 'assistant', content: '目前比较流行的风格有现代简约、北欧风、新中式和日式原木风。您更倾向于哪种感觉呢？' }
      ]
    },
    { 
      id: 2, 
      title: '水电改造注意事项', 
      date: '昨天',
      messages: [
        { role: 'assistant', content: '你好，我是您的装修顾问，关于装修有什么可以帮您？' },
        { role: 'user', content: '水电改造有什么需要注意的？' },
        { role: 'assistant', content: '水电改造是装修中的隐蔽工程，非常关键。主要注意点包括：\n1. 强弱电分开\n2. 水管走顶不走地\n3. 插座布局要合理' }
      ]
    },
    { 
      id: 3, 
      title: '厨房布局设计', 
      date: '前天',
      messages: [
        { role: 'assistant', content: '你好，我是您的装修顾问，关于装修有什么可以帮您？' },
        { role: 'user', content: '厨房怎么布局比较好？' },
        { role: 'assistant', content: '常见的厨房布局有：I型、L型、U型和二字型。具体的选择取决于您家厨房的面积和形状。' }
      ]
    },
  ]);

  const messagesEndRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  // Sync messages to history when they change, if we have an active chat
  useEffect(() => {
    if (currentChatId) {
      setHistory(prev => prev.map(item => {
        if (item.id === currentChatId) {
          return { ...item, messages: messages };
        }
        return item;
      }));
    }
  }, [messages, currentChatId]);

  const startNewChat = () => {
    setMessages([{ role: 'assistant', content: '你好，我是您的装修顾问，关于装修有什么可以帮您？' }]);
    setInput('');
    setCurrentChatId(null);
    setActiveMenuId(null);
  };

  const loadChat = (chat) => {
    setCurrentChatId(chat.id);
    setMessages(chat.messages);
    if (window.innerWidth < 768) {
      setIsSidebarOpen(false);
    }
  };

  const deleteChat = (e, chatId) => {
    e.stopPropagation();
    setHistory(prev => prev.filter(item => item.id !== chatId));
    if (currentChatId === chatId) {
      startNewChat();
    }
    setActiveMenuId(null);
  };

  const createHistoryItem = (firstUserMsg, initialMessages) => {
    const newId = Date.now();
    const newItem = {
      id: newId,
      title: firstUserMsg.length > 10 ? firstUserMsg.substring(0, 10) + '...' : firstUserMsg,
      date: '刚刚',
      messages: initialMessages
    };
    setHistory(prev => [newItem, ...prev]);
    return newId;
  };

  const sendMessage = async () => {
    if (!input.trim() || isLoading) return;

    const userMsg = input.trim();
    setInput('');
    
    // Create new messages array
    let updatedMessages = [...messages, { role: 'user', content: userMsg }];
    setMessages(updatedMessages);
    setIsLoading(true);

    // Handle History Logic
    let activeId = currentChatId;
    if (!activeId) {
      activeId = createHistoryItem(userMsg, updatedMessages);
      setCurrentChatId(activeId);
    }

    const newMsgId = Date.now();
    const assistantMsg = { role: 'assistant', content: '', thinking: [], id: newMsgId };
    updatedMessages = [...updatedMessages, assistantMsg];
    setMessages(updatedMessages);

    try {
      const response = await fetch('/chat_stream', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: userMsg, enable_search: enableSearch, show_thinking: showThinking })
      });

      if (!response.ok) {
        throw new Error(`Server error: ${response.status}`);
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        const chunk = decoder.decode(value, { stream: true });
        const lines = chunk.split('\n');
        
        for (const line of lines) {
          if (!line.trim()) continue;
          try {
            const data = JSON.parse(line);
            setMessages(prev => prev.map(msg => {
              if (msg.id !== newMsgId) return msg;
              if (data.type === 'thinking') {
                return { ...msg, thinking: [...(msg.thinking || []), ...data.content] };
              } else if (data.type === 'answer') {
                return { ...msg, content: msg.content + data.content };
              }
              return msg;
            }));
          } catch (e) { console.error("Parse error", e); }
        }
      }
    } catch (error) {
      console.error('Error:', error);
      setMessages(prev => [...prev, { role: 'assistant', content: '抱歉，发生了网络错误。' }]);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="flex h-screen bg-white text-gray-800 font-sans overflow-hidden">
      {/* Sidebar */}
      <aside 
        className={`${
          isSidebarOpen ? 'w-64 translate-x-0' : 'w-0 -translate-x-full opacity-0 overflow-hidden'
        } bg-gray-50 border-r border-gray-200 flex flex-col transition-all duration-300 ease-in-out shrink-0`}
      >
        {/* New Chat Button */}
        <div className="p-4">
          <button 
            onClick={startNewChat}
            className="w-full flex items-center gap-3 px-4 py-3 bg-gray-200 hover:bg-gray-300 rounded-full text-sm font-medium text-gray-700 transition-colors"
          >
            <Plus size={18} />
            <span className="truncate">新对话</span>
          </button>
        </div>

        {/* History List */}
        <div className="flex-1 overflow-y-auto px-2" onClick={() => setActiveMenuId(null)}>
          <div className="px-4 py-2 text-xs font-semibold text-gray-500">最近</div>
          <div className="space-y-1">
            {history.map((item) => (
              <div key={item.id} className="relative group">
                <button 
                  onClick={() => loadChat(item)}
                  className={`w-full flex items-center gap-3 px-4 py-2 text-sm rounded-full transition-colors text-left ${
                    currentChatId === item.id 
                      ? 'bg-blue-100 text-blue-700' 
                      : 'text-gray-700 hover:bg-gray-200'
                  }`}
                >
                  <MessageSquare size={16} className="shrink-0 text-gray-500" />
                  <span className="truncate flex-1">{item.title}</span>
                  <div 
                    onClick={(e) => {
                      e.stopPropagation();
                      setActiveMenuId(activeMenuId === item.id ? null : item.id);
                    }}
                    className="p-1 hover:bg-gray-300 rounded-full opacity-0 group-hover:opacity-100 transition-opacity"
                  >
                    <MoreVertical size={14} className="text-gray-500" />
                  </div>
                </button>
                
                {/* Context Menu */}
                {activeMenuId === item.id && (
                  <div className="absolute right-2 top-8 z-10 bg-white shadow-lg rounded-lg border border-gray-100 py-1 w-32 animate-in fade-in zoom-in-95 duration-100">
                    <button 
                      onClick={(e) => deleteChat(e, item.id)}
                      className="w-full flex items-center gap-2 px-3 py-2 text-xs text-red-600 hover:bg-red-50 transition-colors"
                    >
                      <Trash2 size={14} />
                      删除对话
                    </button>
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>

        {/* User Profile / Settings */}
        <div className="p-2 border-t border-gray-200 mt-auto">
          <button className="w-full flex items-center gap-3 px-3 py-2 text-sm hover:bg-gray-200 rounded-lg transition-colors text-left">
            <Settings size={18} className="text-gray-600" />
            <span>设置</span>
          </button>
          <div className="mt-1 pt-1 flex items-center gap-3 px-3 py-2 hover:bg-gray-200 rounded-lg cursor-pointer">
            <div className="w-8 h-8 rounded-full bg-purple-600 flex items-center justify-center text-white font-bold text-xs">
              U
            </div>
            <div className="flex-1 min-w-0">
              <div className="text-sm font-medium truncate">User</div>
              <div className="text-xs text-gray-500 truncate">user@example.com</div>
            </div>
          </div>
        </div>
      </aside>

      {/* Main Content Area */}
      <main className="flex-1 flex flex-col h-full relative min-w-0">
        {/* Top Navigation Bar */}
        <header className="h-14 flex items-center justify-between px-4 shrink-0">
          <div className="flex items-center gap-2">
            <button 
              onClick={() => setIsSidebarOpen(!isSidebarOpen)}
              className="p-2 hover:bg-gray-100 rounded-full text-gray-500 transition-colors"
            >
              {isSidebarOpen ? <PanelLeftClose size={20} /> : <PanelLeft size={20} />}
            </button>
            <span className="font-medium text-gray-700">装修智能顾问</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-full bg-blue-100 flex items-center justify-center text-blue-600">
              <Bot size={18} />
            </div>
          </div>
        </header>

        {/* Chat Messages */}
        <div className="flex-1 overflow-y-auto p-4 md:px-8 lg:px-12 pb-32 w-full max-w-5xl mx-auto space-y-6 scroll-smooth">
          {messages.map((msg, idx) => (
            <div key={idx} className={`flex gap-4 ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
              {msg.role === 'assistant' && (
                <div className="w-8 h-8 rounded-full bg-blue-100 flex items-center justify-center shrink-0 mt-1">
                  <Bot size={18} className="text-blue-600" />
                </div>
              )}
              
              <div className={`flex flex-col max-w-[80%] md:max-w-[70%] space-y-2 ${msg.role === 'user' ? 'items-end' : 'items-start'}`}>
                {/* User Name or Bot Name */}
                <span className="text-xs text-gray-400 px-1">
                  {msg.role === 'assistant' ? '智能顾问' : '我'}
                </span>

                {/* Thinking Process */}
                {msg.thinking && msg.thinking.length > 0 && (
                  <div className="w-full bg-gray-50 rounded-lg p-3 text-sm border border-gray-200">
                    <details className="group">
                      <summary className="flex items-center gap-2 cursor-pointer text-gray-500 hover:text-gray-700 font-medium list-none select-none">
                        <Brain size={14} className="text-purple-500" />
                        <span>深度思考过程 ({msg.thinking.length} 条日志)</span>
                        <span className="ml-auto text-xs opacity-0 group-hover:opacity-100 transition-opacity">点击展开</span>
                      </summary>
                      <div className="mt-3 text-gray-600 font-mono text-xs whitespace-pre-wrap pl-2 border-l-2 border-purple-200 py-1">
                        {msg.thinking.map((log, i) => <div key={i} className="mb-1 last:mb-0">{log}</div>)}
                      </div>
                    </details>
                  </div>
                )}

                {/* Message Bubble */}
                <div className={`p-4 rounded-2xl shadow-sm text-base leading-relaxed ${
                  msg.role === 'user' 
                    ? 'bg-blue-600 text-white rounded-br-none' 
                    : 'bg-white border border-gray-200 rounded-bl-none'
                }`}>
                  {msg.role === 'assistant' 
                    ? <ReactMarkdown className="prose prose-sm max-w-none">{msg.content}</ReactMarkdown> 
                    : <div className="whitespace-pre-wrap">{msg.content}</div>
                  }
                </div>
              </div>

              {msg.role === 'user' && (
                <div className="w-8 h-8 rounded-full bg-gray-200 flex items-center justify-center shrink-0 mt-1">
                  <User size={18} className="text-gray-600" />
                </div>
              )}
            </div>
          ))}
          <div ref={messagesEndRef} />
        </div>

        {/* Input Area */}
        <div className="w-full max-w-4xl mx-auto px-4 pb-6 pt-2">
          <div className="bg-gray-100 rounded-3xl p-2 focus-within:bg-white focus-within:ring-2 focus-within:ring-blue-100 focus-within:shadow-lg transition-all border border-transparent focus-within:border-blue-200">
            {/* Toolbar */}
            <div className="flex gap-2 px-3 pt-2 mb-1">
              <button 
                onClick={() => setEnableSearch(!enableSearch)} 
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-medium transition-all ${
                  enableSearch 
                    ? 'bg-blue-100 text-blue-700 ring-1 ring-blue-200' 
                    : 'bg-white text-gray-500 hover:bg-gray-200 border border-gray-200'
                }`}
              >
                <Search size={14} />
                联网搜索
              </button>
              <button 
                onClick={() => setShowThinking(!showThinking)} 
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-medium transition-all ${
                  showThinking 
                    ? 'bg-purple-100 text-purple-700 ring-1 ring-purple-200' 
                    : 'bg-white text-gray-500 hover:bg-gray-200 border border-gray-200'
                }`}
              >
                <Brain size={14} />
                深度思考
              </button>
            </div>

            {/* Textarea & Send Button */}
            <div className="flex items-end gap-2 px-2 pb-1">
              <textarea 
                value={input} 
                onChange={(e) => setInput(e.target.value)} 
                onKeyDown={(e) => e.key === 'Enter' && !e.shiftKey && (e.preventDefault(), sendMessage())} 
                placeholder="问问关于装修的事..." 
                className="w-full max-h-48 p-3 bg-transparent border-none resize-none focus:ring-0 text-gray-800 placeholder-gray-500 text-base leading-relaxed" 
                rows={1} 
                style={{ minHeight: '56px' }} 
              />
              <button 
                onClick={sendMessage} 
                disabled={isLoading || !input.trim()} 
                className={`p-3 rounded-full mb-1 transition-all flex items-center justify-center shrink-0 ${
                  input.trim() 
                    ? 'bg-blue-600 text-white hover:bg-blue-700 shadow-md transform hover:scale-105' 
                    : 'bg-gray-200 text-gray-400 cursor-not-allowed'
                }`}
              >
                {isLoading ? <Loader2 size={20} className="animate-spin" /> : <Send size={20} />}
              </button>
            </div>
          </div>
          <div className="text-center mt-2 text-xs text-gray-400">
            AI 可能会犯错。请核查重要信息。
          </div>
        </div>
      </main>
    </div>
  );
}
export default App;
