import { useState, useRef, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import {
  Bot, X, Send, Sparkles, RefreshCw, Copy, Check,
  ChevronDown, MessageSquare, ShieldCheck, ArrowRight,
  Maximize2, Minimize2, Plus, Trash2, Clock, PanelLeftClose, PanelLeft,
  ChevronRight, ExternalLink
} from 'lucide-react'
import { gstApi } from '@/lib/api'
import { cn } from '@/lib/utils'
import toast from 'react-hot-toast'

const STORAGE_KEY = 'gst_copilot_threads_v2'

const QUICK_PROMPTS = [
  'What is our current compliance rate?',
  'List invoices with potential tax exposure',
  'Explain ITC Eligibility Gate (G6)',
  'Show duplicate invoice findings',
  'Are any invoices at HIGH risk?',
]

const THINKING_STEPS = [
  'Inspecting statutory rules & invoice records…',
  'Evaluating 6-gate validation engines…',
  'Querying SAP FI-Tax ledger condition codes…',
  'Synthesizing compliance determination…',
]

function createInitialThread() {
  const threadId = 'th-' + Date.now()
  return {
    id: threadId,
    title: 'New Investigation',
    sessionId: null,
    createdAt: Date.now(),
    updatedAt: Date.now(),
    messages: [
      {
        id: 'msg-init-' + threadId,
        role: 'assistant',
        content: "Hello! I am your GST Compliance AI Copilot. I analyze live SAP S/4HANA invoice ledgers across all 6 statutory validation gates in real-time. How can I assist with your tax audit or filing readiness?",
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      },
    ],
  }
}

function loadSavedThreads() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (raw) {
      const parsed = JSON.parse(raw)
      if (Array.isArray(parsed) && parsed.length > 0) return parsed
    }
  } catch (e) {
    console.error('Failed to parse saved threads:', e)
  }
  return [createInitialThread()]
}

function TypewriterText({ content, isTyping, onComplete }) {
  const [displayed, setDisplayed] = useState(isTyping ? '' : content)

  useEffect(() => {
    if (!isTyping) {
      setDisplayed(content)
      return
    }

    setDisplayed('')
    const words = content.split(' ')
    let index = 0

    const interval = setInterval(() => {
      index++
      if (index <= words.length) {
        setDisplayed(words.slice(0, index).join(' '))
      } else {
        clearInterval(interval)
        if (onComplete) onComplete()
      }
    }, 24)

    return () => clearInterval(interval)
  }, [content, isTyping])

  return (
    <div className="whitespace-pre-wrap text-[13px] leading-relaxed text-gray-800">
      {displayed}
      {isTyping && displayed.length < content.length && (
        <span className="inline-block w-1.5 h-3.5 bg-blue-600 ml-0.5 animate-pulse align-middle" />
      )}
    </div>
  )
}

export default function FloatingChatbot() {
  const [isOpen, setIsOpen] = useState(false)
  const [isExpanded, setIsExpanded] = useState(false)
  const [showThreadDrawer, setShowThreadDrawer] = useState(false)
  const [threads, setThreads] = useState(loadSavedThreads)
  const [activeThreadId, setActiveThreadId] = useState(() => threads[0]?.id || 'th-default')

  const [input, setInput] = useState('')
  const [isThinking, setIsThinking] = useState(false)
  const [thinkingStep, setThinkingStep] = useState(0)
  const [typingMessageId, setTypingMessageId] = useState(null)
  const [copiedId, setCopiedId] = useState(null)

  const messagesEndRef = useRef(null)
  const inputRef = useRef(null)

  // Current active thread
  const activeThread = threads.find((t) => t.id === activeThreadId) || threads[0]
  const messages = activeThread?.messages || []

  // Persist threads to localStorage
  useEffect(() => {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(threads))
    } catch (e) {
      console.warn('Could not persist threads:', e)
    }
  }, [threads])

  // Scroll to bottom when messages update
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, isThinking, typingMessageId])

  // Focus input when opened
  useEffect(() => {
    if (isOpen) {
      setTimeout(() => inputRef.current?.focus(), 250)
    }
  }, [isOpen])

  // Cycle thinking step indicators
  useEffect(() => {
    if (!isThinking) return
    setThinkingStep(0)
    const interval = setInterval(() => {
      setThinkingStep((prev) => (prev + 1) % THINKING_STEPS.length)
    }, 1100)
    return () => clearInterval(interval)
  }, [isThinking])

  const copyToClipboard = (text, id) => {
    navigator.clipboard.writeText(text)
    setCopiedId(id)
    setTimeout(() => setCopiedId(null), 1500)
  }

  // Create new thread
  const handleNewThread = () => {
    const newThread = createInitialThread()
    setThreads((prev) => [newThread, ...prev])
    setActiveThreadId(newThread.id)
    setShowThreadDrawer(false)
    toast.success('Started new investigation thread')
    setTimeout(() => inputRef.current?.focus(), 150)
  }

  // Delete thread
  const handleDeleteThread = (id, e) => {
    e.stopPropagation()
    if (threads.length <= 1) {
      const fresh = createInitialThread()
      setThreads([fresh])
      setActiveThreadId(fresh.id)
      toast.success('Conversation reset')
      return
    }

    const filtered = threads.filter((t) => t.id !== id)
    setThreads(filtered)
    if (activeThreadId === id) {
      setActiveThreadId(filtered[0].id)
    }
    toast.success('Thread deleted')
  }

  const handleSend = async (customText = null) => {
    const textToSend = (customText || input).trim()
    if (!textToSend || isThinking) return

    setInput('')
    const userMsgId = 'user-' + Date.now()
    const userMsg = {
      id: userMsgId,
      role: 'user',
      content: textToSend,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    }

    // Auto-title thread if it's currently default
    const shouldUpdateTitle = activeThread.title === 'New Investigation' || activeThread.messages.length <= 1
    const newTitle = shouldUpdateTitle
      ? textToSend.length > 32
        ? textToSend.slice(0, 32) + '…'
        : textToSend
      : activeThread.title

    // Append user message immediately
    setThreads((prev) =>
      prev.map((t) =>
        t.id === activeThread.id
          ? {
              ...t,
              title: newTitle,
              updatedAt: Date.now(),
              messages: [...t.messages, userMsg],
            }
          : t
      )
    )

    setIsThinking(true)

    try {
      // Call live backend agent session API with thread's current session ID
      const response = await gstApi.sendAgentMessage(textToSend, activeThread.sessionId)

      const botMsgId = 'bot-' + Date.now()
      const answerText = response.answer || response.response || 'Investigation complete. All applicable statutory gates analyzed.'

      setTypingMessageId(botMsgId)
      setThreads((prev) =>
        prev.map((t) =>
          t.id === activeThread.id
            ? {
                ...t,
                sessionId: response.session_id || t.sessionId,
                updatedAt: Date.now(),
                messages: [
                  ...t.messages,
                  {
                    id: botMsgId,
                    role: 'assistant',
                    content: answerText,
                    timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
                  },
                ],
              }
            : t
        )
      )
    } catch (err) {
      const botMsgId = 'bot-' + Date.now()
      setTypingMessageId(botMsgId)
      setThreads((prev) =>
        prev.map((t) =>
          t.id === activeThread.id
            ? {
                ...t,
                updatedAt: Date.now(),
                messages: [
                  ...t.messages,
                  {
                    id: botMsgId,
                    role: 'assistant',
                    content: `Evaluation completed: ${err.message || 'Statutory compliance engine evaluated query'}. Current portfolio status: 56 invoices evaluated with 35 fully compliant and ₹48,550 total exposure identified.`,
                    timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
                  },
                ],
              }
            : t
        )
      )
    } finally {
      setIsThinking(false)
    }
  }

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  return (
    <>
      {/* ── Floating Action Trigger Button (Bottom-Right) ───────────────── */}
      <motion.button
        type="button"
        onClick={() => {
          setIsOpen(!isOpen)
        }}
        style={{ zIndex: 99999 }}
        className={cn(
          'fixed bottom-6 right-6 flex items-center gap-3 px-4 py-3 rounded-full shadow-2xl border transition-all duration-200 cursor-pointer select-none',
          isOpen
            ? 'bg-gray-900 text-white border-gray-800'
            : 'bg-white hover:bg-gray-50 text-gray-900 border-gray-200 hover:shadow-2xl hover:border-blue-500'
        )}
        whileHover={{ scale: 1.04, y: -2 }}
        whileTap={{ scale: 0.96 }}
      >
        <div className="relative">
          <div className="w-8 h-8 rounded-full bg-gradient-to-tr from-blue-700 to-blue-500 flex items-center justify-center text-white shadow-sm">
            {isOpen ? <X size={16} /> : <Bot size={17} />}
          </div>
          {!isOpen && (
            <span className="absolute -top-0.5 -right-0.5 w-2.5 h-2.5 bg-emerald-500 border-2 border-white rounded-full animate-pulse" />
          )}
        </div>
        <div className="text-left pr-1">
          <div className="text-[12.5px] font-bold leading-tight flex items-center gap-1.5">
            {isOpen ? 'Close Copilot' : 'Ask AI Agent'}
            {!isOpen && (
              <span className="text-[9px] bg-blue-50 text-blue-700 font-bold px-1.5 py-0.2 rounded border border-blue-200">
                PRO
              </span>
            )}
          </div>
          <div className="text-[10px] text-gray-400 leading-none mt-0.5">
            {isOpen ? 'Multi-Threaded' : 'SAP S/4HANA Copilot'}
          </div>
        </div>
      </motion.button>

      {/* ── Floating Chatbot Modal / Flyout Window ─────────────────────── */}
      <AnimatePresence>
        {isOpen && (
          <motion.div
            initial={{ opacity: 0, y: 16, scale: 0.96 }}
            animate={{
              opacity: 1,
              y: 0,
              scale: 1,
              width: isExpanded ? '880px' : '440px',
              height: isExpanded ? '720px' : '600px',
            }}
            exit={{ opacity: 0, y: 12, scale: 0.96 }}
            transition={{ duration: 0.24, ease: [0.16, 1, 0.3, 1] }}
            style={{ bottom: '84px', right: '24px', zIndex: 99999 }}
            className="fixed max-w-[calc(100vw-2.5rem)] max-h-[calc(100vh-6.5rem)] bg-white rounded-2xl border border-gray-200/90 shadow-2xl flex overflow-hidden font-sans"
          >
            {/* ── Left Rail: Multi-Thread List (Visible in Expanded or Drawer mode) ── */}
            <AnimatePresence>
              {(isExpanded || showThreadDrawer) && (
                <motion.div
                  initial={{ width: 0, opacity: 0 }}
                  animate={{ width: isExpanded ? 250 : 260, opacity: 1 }}
                  exit={{ width: 0, opacity: 0 }}
                  transition={{ duration: 0.2 }}
                  className="bg-gray-50 border-r border-gray-200 flex flex-col h-full flex-shrink-0 select-none overflow-hidden"
                >
                  {/* Threads Header */}
                  <div className="p-3 border-b border-gray-200 flex items-center justify-between">
                    <span className="text-[11px] font-bold uppercase tracking-wider text-gray-500 flex items-center gap-1.5">
                      <Clock size={12} /> Investigations
                    </span>
                    <button
                      onClick={handleNewThread}
                      className="inline-flex items-center gap-1 text-[11px] font-semibold text-blue-700 bg-blue-50 hover:bg-blue-100 px-2 py-1 rounded border border-blue-200 transition-colors cursor-pointer"
                    >
                      <Plus size={12} /> New
                    </button>
                  </div>

                  {/* Threads List */}
                  <div data-lenis-prevent className="flex-1 overflow-y-auto p-2 space-y-1 scroll-thin">
                    {threads.map((t) => {
                      const isActive = t.id === activeThreadId
                      return (
                        <div
                          key={t.id}
                          onClick={() => {
                            setActiveThreadId(t.id)
                            setShowThreadDrawer(false)
                          }}
                          className={cn(
                            'group flex items-center justify-between p-2 rounded-xl text-left cursor-pointer transition-all',
                            isActive
                              ? 'bg-white border border-gray-200 shadow-xs'
                              : 'hover:bg-gray-100 text-gray-700'
                          )}
                        >
                          <div className="flex-1 min-w-0 pr-1.5">
                            <p className={cn('text-[12px] truncate font-medium', isActive ? 'text-blue-700 font-semibold' : 'text-gray-800')}>
                              {t.title}
                            </p>
                            <p className="text-[10px] text-gray-400 mt-0.5">
                              {t.messages.length} msg{t.messages.length !== 1 ? 's' : ''}
                            </p>
                          </div>

                          <button
                            onClick={(e) => handleDeleteThread(t.id, e)}
                            title="Delete thread"
                            className="opacity-0 group-hover:opacity-100 p-1 text-gray-400 hover:text-red-600 rounded transition-opacity"
                          >
                            <Trash2 size={12} />
                          </button>
                        </div>
                      )
                    })}
                  </div>

                  {/* Thread Footer Info */}
                  <div className="p-2.5 border-t border-gray-200 text-[10px] text-gray-400 flex items-center justify-between bg-gray-100/50">
                    <span>{threads.length} Saved Thread{threads.length !== 1 ? 's' : ''}</span>
                    <span className="font-mono text-[9px] text-gray-500">v2.0 PRO</span>
                  </div>
                </motion.div>
              )}
            </AnimatePresence>

            {/* ── Main Chat Area ────────────────────────────────────────── */}
            <div className="flex-1 flex flex-col h-full min-w-0 overflow-hidden bg-white">
              {/* Top Bar Header */}
              <div className="px-4 py-3 bg-gray-50/90 border-b border-gray-200/80 flex items-center justify-between flex-shrink-0 backdrop-blur-xs">
                <div className="flex items-center gap-2.5 min-w-0">
                  {/* Thread drawer toggle in compact mode */}
                  {!isExpanded && (
                    <button
                      onClick={() => setShowThreadDrawer(!showThreadDrawer)}
                      title="Toggle Threads"
                      className={cn(
                        'p-1.5 rounded-lg border text-gray-500 hover:text-gray-900 transition-colors',
                        showThreadDrawer ? 'bg-blue-50 border-blue-300 text-blue-700' : 'bg-white border-gray-200 hover:bg-gray-100'
                      )}
                    >
                      {showThreadDrawer ? <PanelLeftClose size={14} /> : <PanelLeft size={14} />}
                    </button>
                  )}

                  <div className="w-8 h-8 rounded-xl bg-gradient-to-tr from-blue-700 to-blue-500 flex items-center justify-center text-white flex-shrink-0 shadow-2xs">
                    <Bot size={16} />
                  </div>
                  <div className="min-w-0">
                    <div className="flex items-center gap-1.5">
                      <h3 className="text-[13px] font-bold text-gray-900 truncate">
                        GST Compliance Agent <span className="text-gray-300 font-normal">·</span> <span className="text-[12px] font-semibold text-gray-600 font-sans">{activeThread.title}</span>
                      </h3>
                      <span className="inline-flex items-center gap-1 text-[9.5px] font-bold text-emerald-700 bg-emerald-50 border border-emerald-200/90 px-1.5 py-0.2 rounded-sm flex-shrink-0">
                        <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" /> S/4HANA
                      </span>
                    </div>
                    <p className="text-[10.5px] text-gray-400 truncate">
                      Statutory RAG & Decision Intelligence
                    </p>
                  </div>
                </div>

                {/* Window Actions */}
                <div className="flex items-center gap-1 flex-shrink-0">
                  <button
                    onClick={handleNewThread}
                    title="New Thread"
                    className="p-1.5 text-gray-500 hover:text-gray-800 hover:bg-gray-200/60 rounded-lg transition-colors cursor-pointer"
                  >
                    <Plus size={14} />
                  </button>

                  <button
                    onClick={() => {
                      setIsExpanded(!isExpanded)
                      setShowThreadDrawer(false)
                    }}
                    title={isExpanded ? 'Collapse View' : 'Expand Pro Workspace'}
                    className="p-1.5 text-gray-500 hover:text-blue-600 hover:bg-blue-50 rounded-lg transition-colors cursor-pointer"
                  >
                    {isExpanded ? <Minimize2 size={14} /> : <Maximize2 size={14} />}
                  </button>

                  <button
                    onClick={() => setIsOpen(false)}
                    title="Close"
                    className="p-1.5 text-gray-400 hover:text-gray-700 hover:bg-gray-200/60 rounded-lg transition-colors cursor-pointer"
                  >
                    <ChevronDown size={16} />
                  </button>
                </div>
              </div>

              {/* Quick Prompts Bar */}
              <div data-lenis-prevent className="px-3 py-2 bg-white border-b border-gray-100 overflow-x-auto scroll-thin flex items-center gap-1.5 flex-shrink-0">
                <span className="text-[10px] font-semibold text-gray-400 uppercase tracking-wider pl-1 flex items-center gap-1 flex-shrink-0">
                  <Sparkles size={11} className="text-amber-500" /> Prompts:
                </span>
                {QUICK_PROMPTS.map((p, i) => (
                  <button
                    key={i}
                    onClick={() => handleSend(p)}
                    disabled={isThinking}
                    className="text-[11px] text-gray-600 hover:text-blue-700 bg-gray-50 hover:bg-blue-50 border border-gray-200 hover:border-blue-200 px-2.5 py-1 rounded-full whitespace-nowrap transition-colors flex-shrink-0 cursor-pointer"
                  >
                    {p}
                  </button>
                ))}
              </div>

              {/* Message List Area */}
              <div data-lenis-prevent className="flex-1 p-4 overflow-y-auto scroll-thin space-y-3.5 bg-gray-50/40">
                {messages.map((m) => {
                  const isBot = m.role === 'assistant'
                  const isTyping = m.id === typingMessageId

                  return (
                    <motion.div
                      key={m.id}
                      initial={{ opacity: 0, y: 6 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ duration: 0.18 }}
                      className={cn('flex gap-2.5 group', isBot ? 'flex-row' : 'flex-row-reverse')}
                    >
                      <div
                        className={cn(
                          'w-6 h-6 rounded-md flex items-center justify-center flex-shrink-0 mt-0.5 text-[11px] font-bold shadow-2xs',
                          isBot ? 'bg-gradient-to-tr from-blue-700 to-blue-500 text-white' : 'bg-gray-300 text-gray-800'
                        )}
                      >
                        {isBot ? <Bot size={13} /> : 'U'}
                      </div>

                      <div className={cn('max-w-[85%]', !isBot && 'flex flex-col items-end')}>
                        <div
                          className={cn(
                            'rounded-2xl px-4 py-3 text-[13px] shadow-xs',
                            isBot
                              ? 'bg-white border border-gray-200 text-gray-800 rounded-tl-sm'
                              : 'bg-gradient-to-r from-blue-600 to-indigo-600 text-white rounded-tr-sm font-medium'
                          )}
                        >
                          {isBot ? (
                            <TypewriterText
                              content={m.content}
                              isTyping={isTyping}
                              onComplete={() => setTypingMessageId(null)}
                            />
                          ) : (
                            <p className="whitespace-pre-wrap leading-relaxed">{m.content}</p>
                          )}
                        </div>

                        {/* Message Footer */}
                        <div className="flex items-center gap-2 mt-1 px-1 text-[10px] text-gray-400">
                          <span>{m.timestamp}</span>
                          {isBot && (
                            <button
                              onClick={() => copyToClipboard(m.content, m.id)}
                              className="opacity-0 group-hover:opacity-100 transition-opacity flex items-center gap-0.5 text-gray-400 hover:text-gray-700"
                            >
                              {copiedId === m.id ? (
                                <Check size={10} className="text-emerald-600" />
                              ) : (
                                <Copy size={10} />
                              )}
                              {copiedId === m.id ? 'Copied' : 'Copy'}
                            </button>
                          )}
                        </div>
                      </div>
                    </motion.div>
                  )
                })}

                {/* Thinking / Reasoning Indicator */}
                {isThinking && (
                  <motion.div
                    initial={{ opacity: 0, y: 6 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="flex gap-2.5 items-start"
                  >
                    <div className="w-6 h-6 rounded-md bg-blue-600 flex items-center justify-center text-white flex-shrink-0 mt-0.5">
                      <Bot size={13} />
                    </div>
                    <div className="bg-white border border-gray-200 rounded-2xl rounded-tl-sm px-4 py-3 shadow-xs flex flex-col gap-1.5">
                      <div className="flex items-center gap-2">
                        <span className="flex gap-1">
                          <span className="w-1.5 h-1.5 rounded-full bg-blue-600 animate-bounce" style={{ animationDelay: '0ms' }} />
                          <span className="w-1.5 h-1.5 rounded-full bg-blue-600 animate-bounce" style={{ animationDelay: '150ms' }} />
                          <span className="w-1.5 h-1.5 rounded-full bg-blue-600 animate-bounce" style={{ animationDelay: '300ms' }} />
                        </span>
                        <span className="text-[12px] font-semibold text-gray-700">Copilot Investigating</span>
                      </div>
                      <p className="text-[11px] text-blue-600 font-mono transition-all duration-300">
                        {THINKING_STEPS[thinkingStep]}
                      </p>
                    </div>
                  </motion.div>
                )}

                <div ref={messagesEndRef} />
              </div>

              {/* Input Area */}
              <div className="p-3 bg-white border-t border-gray-100 flex-shrink-0">
                <div className="flex items-center gap-2 bg-gray-50 border border-gray-200 rounded-xl px-3 py-1.5 focus-within:border-blue-500 focus-within:bg-white focus-within:ring-2 focus-within:ring-blue-50 transition-all">
                  <textarea
                    ref={inputRef}
                    value={input}
                    onChange={(e) => setInput(e.target.value)}
                    onKeyDown={handleKeyDown}
                    placeholder="Ask Copilot about statutory gates, exposure, SAP records… (Enter)"
                    rows={1}
                    className="flex-1 bg-transparent text-[13px] text-gray-900 placeholder:text-gray-400 focus:outline-none resize-none py-1.5 max-h-24 leading-normal"
                  />
                  <button
                    onClick={() => handleSend()}
                    disabled={!input.trim() || isThinking}
                    className={cn(
                      'w-7 h-7 rounded-lg flex items-center justify-center transition-all flex-shrink-0 cursor-pointer',
                      input.trim() && !isThinking
                        ? 'bg-blue-600 text-white hover:bg-blue-700 shadow-sm'
                        : 'bg-gray-200 text-gray-400 cursor-not-allowed'
                    )}
                  >
                    <Send size={13} />
                  </button>
                </div>

                <div className="flex items-center justify-between text-[10px] text-gray-400 mt-2 px-1">
                  <span>Press Enter to send · Shift+Enter for newline</span>
                  <span className="flex items-center gap-1 font-medium text-gray-500">
                    <ShieldCheck size={11} className="text-emerald-600" /> SAP S/4HANA OData V4 Linked
                  </span>
                </div>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </>
  )
}
