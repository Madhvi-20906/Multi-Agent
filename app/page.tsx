"use client"

import React, { useState, useEffect, useRef } from "react"
import { 
  ChefHat, Sprout, Cake, Shirt, Calendar, Send, Plus, Sparkles, MessageSquare, Flame, TrendingUp, Scale, RotateCcw, BookOpen, Filter, Check, Shield, HelpCircle, Menu, X, Database, Cpu, GitBranch, Compass, Lock
} from "lucide-react"

interface Message { role: "user" | "assistant" | "system"; content: string }
interface Session { session_id: string; title: string; active_agent: string; diet_preference: string; history: Message[] }

const BACKEND_URL = process.env.NEXT_PUBLIC_BACKEND_URL || "http://127.0.0.1:8000"

export default function Home() {
  const [agentMessages, setAgentMessages] = useState<Record<string, Message[]>>({ chef: [], gardener: [], baker: [], stylist: [], event: [] })
  const [agentSessionIds, setAgentSessionIds] = useState<Record<string, string | null>>({ chef: null, gardener: null, baker: null, stylist: null, event: null })
  const [inputMessage, setInputMessage] = useState("")
  const [activeAgent, setActiveAgent] = useState("chef")
  const [dietPreference, setDietPreference] = useState("none")
  const [sessions, setSessions] = useState<Session[]>([])
  const [isStreaming, setIsStreaming] = useState(false)
  const [sidebarOpen, setSidebarOpen] = useState(true)
  const [showRawJson, setShowRawJson] = useState(false)

  const messages = agentMessages[activeAgent] || []
  const sessionId = agentSessionIds[activeAgent] || null

  const setMessages = (updater: Message[] | ((prev: Message[]) => Message[])) => {
    setAgentMessages(prev => ({ ...prev, [activeAgent]: typeof updater === "function" ? updater(prev[activeAgent] || []) : updater }))
  }
  const setSessionId = (id: string | null) => { setAgentSessionIds(prev => ({ ...prev, [activeAgent]: id })) }

  const messagesEndRef = useRef<HTMLDivElement>(null)

  const activeAgentsList = [
    { id: "chef", name: "Chef Gasto", desc: "Culinary Guide & RAG Assistant", icon: <ChefHat className="w-5 h-5" /> },
    { id: "gardener", name: "Flora Root", desc: "Gardening & Botany Specialist", icon: <Sprout className="w-5 h-5" /> },
    { id: "baker", name: "Artisan Loaf", desc: "Pastry & Bread Connoisseur", icon: <Cake className="w-5 h-5" /> },
    { id: "stylist", name: "Sartorial Thread", desc: "Fashion & Wardrobe Consultant", icon: <Shirt className="w-5 h-5" /> },
    { id: "event", name: "Vivid Bloom", desc: "Social Event & Gathering Planner", icon: <Calendar className="w-5 h-5" /> },
  ]

  const futureAgents: { id: string; name: string; desc: string; icon: React.ReactNode }[] = []

  const [ingestingStatus, setIngestingStatus] = useState<"idle" | "running" | "done">("idle")

  const getAgentEmptyState = () => {
    switch (activeAgent) {
      case "gardener":
        return {
          icon: <Sprout className="w-24 h-24 mx-auto text-[#EAE0D3] opacity-50" />,
          text: "Flora Root is awaiting your botanical or soil questions...",
          prompts: [
            "Generate a watering schedule for a fiddle leaf fig and snake plant",
            "Diagnose yellow spots on my monstera leaves",
            "Which plants grow best together in a sunny raised bed?",
            "How do I lower the pH of my alkaline garden soil?"
          ]
        };
      case "baker":
        return {
          icon: <Cake className="w-24 h-24 mx-auto text-[#EAE0D3] opacity-50" />,
          text: "Artisan Loaf is awaiting your baking or dough formulas...",
          prompts: [
            "Calculate bakers percentages for a 70% hydration sourdough dough",
            "How do I adjust rising time if my kitchen is 80 degrees?",
            "Suggest gluten-free flour substitutes for baking cookies",
            "Create a proofing schedule for overnight baguettes"
          ]
        };
      case "stylist":
        return {
          icon: <Shirt className="w-24 h-24 mx-auto text-[#EAE0D3] opacity-50" />,
          text: "Sartorial Thread is awaiting your outfit curation or color theory questions...",
          prompts: [
            "Create a cohesive color palette based on forest green and copper",
            "Build a smart-casual capsule wardrobe for a spring trip",
            "What dress code is appropriate for a rustic garden wedding?",
            "Suggest fabric matches for a warm oak table setting theme"
          ]
        };
      case "event":
        return {
          icon: <Calendar className="w-24 h-24 mx-auto text-[#EAE0D3] opacity-50" />,
          text: "Vivid Bloom is awaiting your event flow, budget or scheduling constraints...",
          prompts: [
            "Generate a detailed timeline for a 4-hour evening dinner party",
            "Build an event budget allocation for $5,000 for 40 guests",
            "Suggest a seating arrangement strategy for conflicting families",
            "What are the key planning steps for a micro-wedding?"
          ]
        };
      case "chef":
      default:
        return {
          icon: <ChefHat className="w-24 h-24 mx-auto text-[#EAE0D3] opacity-50" />,
          text: "Chef Gasto is awaiting your culinary or recipe questions...",
          prompts: [
            "Scale ingredients of pancake recipe for 6 guests",
            "What gluten-free recipes do we have in the knowledge base?",
            "Convert 2.5 cups of almond flour to grams",
            "Estimate macros for a serving of avocado toast with eggs"
          ]
        };
    }
  };
  const emptyState = getAgentEmptyState();

  useEffect(() => { messagesEndRef.current?.scrollIntoView({ behavior: "smooth" }) }, [messages, isStreaming])
  useEffect(() => { fetchSessions() }, [])

  const fetchSessions = async () => {
    try {
      const res = await fetch(`${BACKEND_URL}/api/sessions`)
      if (res.ok) {
        const data = await res.json()
        setSessions(data.sessions || [])
      }
    } catch (e) {}
  }

  const selectSession = (session: Session) => {
    const agent = session.active_agent || "chef"
    setAgentSessionIds(prev => ({ ...prev, [agent]: session.session_id }))
    setAgentMessages(prev => ({ ...prev, [agent]: session.history || [] }))
    setActiveAgent(agent)
    setDietPreference(session.diet_preference || "none")
    if (window.innerWidth < 768) setSidebarOpen(false)
  }

  const switchAgent = (agentId: string) => {
    setActiveAgent(agentId)
    if (window.innerWidth < 768) setSidebarOpen(false)
  }

  const startNewSession = () => {
    setAgentSessionIds(prev => ({ ...prev, [activeAgent]: null }))
    setAgentMessages(prev => ({ ...prev, [activeAgent]: [] }))
    if (window.innerWidth < 768) setSidebarOpen(false)
  }

  const clearCurrentSession = async () => {
    if (!sessionId) { setMessages([]); return }
    try {
      const res = await fetch(`${BACKEND_URL}/api/sessions/${sessionId}/clear`, { method: "POST" })
      if (res.ok) { setMessages([]); fetchSessions() }
    } catch (e) {}
  }

  const triggerAutoIngest = async () => {
    setIngestingStatus("running")
    try {
      const res = await fetch(`${BACKEND_URL}/api/rag/ingest`, { method: "POST" })
      if (res.ok) {
        setTimeout(() => {
          setIngestingStatus("done")
          setTimeout(() => setIngestingStatus("idle"), 3000)
        }, 2500)
      } else setIngestingStatus("idle")
    } catch (e) { setIngestingStatus("idle") }
  }

  const handleSendMessage = async (textToSend: string) => {
    const text = textToSend.trim()
    if (!text || isStreaming) return

    setMessages((prev: Message[]) => [...prev, { role: "user", content: text }])
    setInputMessage("")
    setIsStreaming(true)

    let assistantMsgContent = ""
    setMessages((prev: Message[]) => [...prev, { role: "assistant", content: "" }])

    try {
      const payload = { message: text, session_id: sessionId, agent_id: activeAgent, diet_preference: dietPreference }
      const response = await fetch(`${BACKEND_URL}/api/chat`, {
        method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload)
      })

      if (!response.ok) throw new Error("API call failed")

      const reader = response.body?.getReader()
      const decoder = new TextDecoder()
      if (!reader) return

      let buffer = ""
      while (true) {
        const { value, done } = await reader.read()
        if (done) break

        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split("\n")
        buffer = lines.pop() || ""

        let skipNextDataLine = false

        for (const line of lines) {
          const trimmed = line.trim()
          if (!trimmed) continue

          if (trimmed.startsWith("event: metadata")) {
            skipNextDataLine = true
            const nextLine = lines[lines.indexOf(line) + 1] || ""
            if (nextLine.startsWith("data: ")) {
              try {
                const metadata = JSON.parse(nextLine.slice(6))
                if (metadata.session_id) setSessionId(metadata.session_id)
              } catch (e) {}
            }
          } else if (trimmed.startsWith("data: ")) {
            if (skipNextDataLine) { skipNextDataLine = false; continue }
            assistantMsgContent += trimmed.slice(6).replace(/\\n/g, "\n")
            setMessages((prev: Message[]) => {
              const updated = [...prev]
              if (updated.length > 0) updated[updated.length - 1] = { role: "assistant", content: assistantMsgContent }
              return updated
            })
          }
        }
      }
    } catch (err: any) {
      setMessages((prev: Message[]) => {
        const updated = [...prev]
        if (updated.length > 0) updated[updated.length - 1] = { role: "assistant", content: `*Error: ${err.message}*` }
        return updated
      })
    } finally {
      setIsStreaming(false)
      fetchSessions()
    }
  }

  const requestScaling = (factor: number) => handleSendMessage(`Scale the ingredients of the last recipe by a factor of ${factor}x.`)
  const requestMacros = () => handleSendMessage(`Estimate the nutritional macros for the last recipe.`)

  const renderMarkdownContent = (text: string) => {
    const lines = text.split("\n")
    return lines.map((line, idx) => {
      if (line.startsWith("# ")) return <h1 key={idx} className="text-2xl font-serif text-[#3A2A1A] font-bold mt-4 mb-2">{line.slice(2)}</h1>
      if (line.startsWith("## ")) return <h2 key={idx} className="text-xl font-serif text-[#3A2A1A] font-bold mt-3 mb-2">{line.slice(3)}</h2>
      if (line.startsWith("### ")) return <h3 key={idx} className="text-lg font-serif text-[#3A2A1A] font-bold mt-2 mb-1">{line.slice(4)}</h3>
      if (line.startsWith("- ") || line.startsWith("* ")) {
        const boldParts = line.slice(2).split("**")
        return <li key={idx} className="ml-5 list-disc text-[#3A2A1A]/90">{boldParts.map((part, pIdx) => pIdx % 2 === 1 ? <strong key={pIdx} className="text-[#7A5537] font-bold">{part}</strong> : part)}</li>
      }
      if (line.startsWith("> ")) return <div key={idx} className="border-l-4 border-[#7A5537] bg-[#7A5537]/10 p-3 italic my-2 text-[#3A2A1A]">{line.slice(2)}</div>
      if (line.trim().length === 0) return <div key={idx} className="h-2"></div>
      
      const boldParts = line.split("**")
      return <p key={idx} className="text-[#3A2A1A]/90">{boldParts.map((part, pIdx) => pIdx % 2 === 1 ? <strong key={pIdx} className="text-[#7A5537] font-bold">{part}</strong> : part)}</p>
    })
  }

  return (
    <div className="flex h-screen overflow-hidden bg-background font-sans">
      
      {/* Mobile Sidebar Overlay Backdrop */}
      {sidebarOpen && (
        <div 
          onClick={() => setSidebarOpen(false)} 
          className="fixed inset-0 z-30 bg-black/50 backdrop-blur-sm md:hidden transition-opacity duration-300"
        />
      )}
      
      {/* SIDEBAR: Parchment background with thick borders */}
      <aside className={`
        fixed inset-y-0 left-0 z-40 w-80 bg-parchment border-r-[8px] border-[#3A2A1A] flex flex-col shadow-2xl transition-transform duration-300
        md:relative md:translate-x-0 ${sidebarOpen ? "translate-x-0" : "-translate-x-full"}
      `}>
        {/* BRANDING HEADER */}
        <div className="p-6 flex items-center justify-between border-b-2 border-border/20">
          <div className="flex items-center gap-4">
            <div className="w-14 h-14 rounded-full bg-leather-green stitched-border flex items-center justify-center text-accent-gold">
              <ChefHat className="w-7 h-7" />
            </div>
            <div>
              <h1 className="font-serif text-4xl text-[#3A2A1A] font-bold tracking-tight">Allora</h1>
              <p className="text-[9px] uppercase tracking-widest text-[#5A4027] font-bold">5 Agents<br/>Endless Possibilities</p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <button onClick={startNewSession} className="w-8 h-8 rounded-full bg-leather-brown stitched-border flex items-center justify-center text-[#EAE0D3] shadow-md hover:scale-105 active:scale-95 transition-transform" title="New Session">
              <Plus className="w-4 h-4" />
            </button>
            <button 
              onClick={() => setSidebarOpen(false)} 
              className="md:hidden w-8 h-8 rounded-full bg-leather-brown stitched-border flex items-center justify-center text-[#EAE0D3] shadow-md hover:scale-105 active:scale-95 transition-transform"
              title="Close Sidebar"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        </div>

        {/* DIETARY PREFERENCES */}
        <div className="px-6 py-4 border-b-2 border-border/20">
          <h2 className="font-cursive text-2xl text-[#3A2A1A] flex items-center gap-2 mb-2">
            <Filter className="w-4 h-4" /> Dietary Preference
          </h2>
          <div className="relative">
            <select 
              value={dietPreference} onChange={(e) => setDietPreference(e.target.value)}
              className="w-full bg-parchment border border-[#8B7355] rounded-lg px-4 py-3 text-sm text-[#3A2A1A] shadow-[inset_1px_1px_3px_rgba(0,0,0,0.1)] appearance-none font-serif cursor-pointer focus:outline-none"
            >
              <option value="none">Standard Diet (No Filters)</option>
              <option value="gluten-free">Gluten-Free</option>
              <option value="vegan">Vegan</option>
              <option value="keto">Keto / Low-Carb</option>
              <option value="vegetarian">Vegetarian</option>
            </select>
            <div className="absolute right-3 top-1/2 -translate-y-1/2 w-6 h-6 rounded bg-leather-brown stitched-border flex items-center justify-center pointer-events-none">
              <div className="w-2 h-2 border-r-2 border-b-2 border-[#EAE0D3] rotate-45 mb-1"></div>
            </div>
          </div>
        </div>

        {/* WORKSPACE HEADER */}
        <div className="px-6 py-4 border-b-2 border-border/20 flex items-center justify-between bg-[#E8DFCD]/40">
          <div className="flex items-center gap-2 text-sm font-serif font-bold text-[#5A4027]">
            <MessageSquare className="w-4 h-4 text-[#7A5537]" /> Active Workspace
          </div>
          <span className="text-[10px] bg-leather-brown text-[#EAE0D3] px-2 py-0.5 rounded stitched-border font-bold uppercase tracking-wider scale-90">
            Online
          </span>
        </div>

        {/* AGENTS GROUP */}
        <div className="flex-1 overflow-y-auto px-6 py-4 space-y-6">
          <div className="space-y-3">
            {activeAgentsList.map((agent) => {
              const isActive = activeAgent === agent.id;
              return (
                <button key={agent.id} onClick={() => switchAgent(agent.id)} className={`w-full text-left p-3 rounded-xl flex items-center gap-4 transition-all ${isActive ? "bg-leather-brown text-[#EAE0D3] stitched-border shadow-leather scale-[1.02]" : "bg-transparent border border-[#C4B29E] text-[#5A4027] hover:bg-[#E8DFCD]"}`}>
                  <div className={`p-2 rounded-lg ${isActive ? "bg-parchment text-[#3A2A1A] shadow-embossed" : "bg-[#E8DFCD] text-[#5A4027]"}`}>
                    {agent.icon}
                  </div>
                  <div className="flex-1">
                    <h3 className="font-serif font-bold text-base">{agent.name}</h3>
                    <p className={`text-[10px] ${isActive ? "text-[#EAE0D3]/80" : "text-[#8B7355]"}`}>{agent.desc}</p>
                  </div>
                </button>
              )
            })}
          </div>

          {futureAgents.length > 0 && (
            <div>
              <h3 className="text-xs font-bold text-[#8B7355] uppercase tracking-widest mb-3">Registered Agent Pods (Future)</h3>
              <div className="space-y-3">
                {futureAgents.map((agent) => (
                  <div key={agent.id} className="p-3 rounded-xl bg-parchment border border-[#D5C6B3] flex items-center gap-4 opacity-70 shadow-[inset_1px_1px_2px_rgba(255,255,255,0.8),_1px_1px_3px_rgba(0,0,0,0.05)]">
                    <div className="p-2 rounded-lg bg-brass text-[#3A2A1A] shadow-embossed">
                      <Lock className="w-5 h-5" />
                    </div>
                    <div className="flex-1">
                      <h4 className="font-serif font-bold text-sm text-[#3A2A1A] flex items-center gap-2">
                        {agent.name} <span className="text-[8px] bg-transparent border border-[#8B7355] px-1 rounded uppercase tracking-widest text-[#5A4027]">Lock</span>
                      </h4>
                      <p className="text-[10px] text-[#8B7355]">{agent.desc}</p>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* FOOTER */}
        <div className="p-4 border-t-2 border-border/20 flex flex-col gap-3">
          <div className="flex items-center gap-2 text-xs text-[#5A4027] font-bold">
            <div className="w-2.5 h-2.5 rounded-full bg-[#4C6B53] shadow-[inset_1px_1px_2px_rgba(255,255,255,0.5),_0_0_5px_rgba(76,107,83,0.8)]"></div>
            Secure Rate Limits Active
          </div>
          <a href="/diagnostics" className="w-full py-2 text-center text-xs rounded-lg bg-brass text-[#3A2A1A] font-serif font-bold shadow-brass border border-[#7B5E1C] hover:scale-[1.02] active:scale-95 transition-transform block">
            🛡️ Diagnostics & Seeding Board
          </a>
          <button onClick={triggerAutoIngest} className="w-full py-2 text-xs rounded-lg bg-leather-brown stitched-border text-[#EAE0D3] font-serif font-bold shadow-leather hover:scale-[1.02] active:scale-95 transition-transform">
            Trigger Ingest (Seed Data)
          </button>
        </div>
      </aside>

      {/* MAIN WORKSPACE PANEL */}
      <main className="flex-1 flex flex-col bg-leather-green min-h-0">
        {/* Leather Desktop Mat */}
        <div className="flex-1 bg-leather-green stitched-border shadow-leather flex flex-col relative overflow-hidden stitched-inner min-h-0">
          
          {/* HEADER BRASS PLATE & SERVER STATUS */}
          <header className="shrink-0 h-20 flex items-center justify-between px-8 z-10 pt-4">
            <div className="w-1/3 flex items-center">
              <button 
                onClick={() => setSidebarOpen(true)}
                className="md:hidden p-2 rounded bg-brass text-[#3A2A1A] shadow-brass hover:scale-105 active:scale-95 transition-transform"
                title="Open Sidebar"
              >
                <Menu className="w-5 h-5" />
              </button>
            </div>
            <div className="w-1/3 flex justify-center">
              <div className="bg-brass px-8 py-3 rounded-lg shadow-brass relative">
                <div className="absolute left-2 top-1/2 -translate-y-1/2 w-1.5 h-1.5 rounded-full bg-[#3A2A1A] shadow-debossed"></div>
                <div className="absolute right-2 top-1/2 -translate-y-1/2 w-1.5 h-1.5 rounded-full bg-[#3A2A1A] shadow-debossed"></div>
                <h2 className="font-serif font-bold text-lg text-[#3A2A1A] tracking-wide" style={{ textShadow: "1px 1px 0 rgba(255,255,255,0.5)" }}>
                  {activeAgent === "chef" ? "Chef Gasto Workspace" : activeAgent === "gardener" ? "Flora Root Workspace" : activeAgent === "baker" ? "Artisan Loaf Workspace" : activeAgent === "stylist" ? "Sartorial Thread Workspace" : "Vivid Bloom Workspace"}
                </h2>
              </div>
            </div>
            <div className="w-1/3 flex justify-end">
              <div className="bg-brass p-1.5 rounded-full shadow-brass flex items-center gap-3 px-4">
                <div className="w-3 h-3 rounded-full bg-[#A3D9A5] shadow-[inset_1px_1px_2px_rgba(255,255,255,0.8),_0_0_8px_rgba(163,217,165,0.9)] animate-pulse-slow"></div>
                <span className="text-[10px] font-bold text-[#3A2A1A] uppercase tracking-widest">Server Connected</span>
              </div>
            </div>
          </header>

          {/* CHAT AREA */}
          <div className="flex-1 min-h-0 overflow-y-auto px-8 py-6 space-y-6 z-10 flex flex-col">
            {messages.length === 0 ? (
              <div className="flex-1 flex flex-col items-center justify-center space-y-8 max-w-2xl mx-auto py-8">
                {/* Decorative Elements matching the active agent */}
                <div className="text-center space-y-4 pointer-events-none">
                  {emptyState.icon}
                  <p className="font-serif text-[#EAE0D3] font-bold text-xl opacity-80">{emptyState.text}</p>
                </div>
                
                {/* Pre-prompts Grid */}
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 w-full px-4">
                  {emptyState.prompts.map((prompt, idx) => (
                    <button
                      key={idx}
                      onClick={() => handleSendMessage(prompt)}
                      className="p-4 rounded-2xl bg-[#EAE0D3]/10 border border-[#EAE0D3]/30 hover:border-[#D4AF37] hover:bg-[#EAE0D3]/20 text-left text-sm text-[#EAE0D3] font-serif shadow-sm transition-all hover:scale-[1.02] active:scale-95 duration-200"
                    >
                      {prompt}
                    </button>
                  ))}
                </div>
              </div>
            ) : (
              <div className="w-full max-w-4xl mx-auto space-y-6 mt-auto">
                {messages.map((msg, index) => (
                  <div key={index} className={`flex gap-4 fade-in ${msg.role === "user" ? "justify-end" : "justify-start"}`}>
                    <div className={`max-w-[80%] rounded-2xl p-5 text-sm shadow-leather relative
                      ${msg.role === "user" 
                        ? "bg-leather-brown text-[#EAE0D3] rounded-br-none border border-[#7A5537]" 
                        : "bg-parchment text-[#3A2A1A] rounded-bl-none border border-[#D5C6B3]"
                      }
                    `}>
                      {msg.role === "user" ? (
                        <p className="leading-relaxed whitespace-pre-wrap font-serif text-base">{msg.content}</p>
                      ) : (
                        <div className="space-y-2">
                          {msg.content === "" ? (
                            <div className="flex items-center gap-1.5 py-2 px-1">
                              <span className="w-2.5 h-2.5 bg-[#7A5537] rounded-full animate-bounce" style={{ animationDelay: "0ms" }}></span>
                              <span className="w-2.5 h-2.5 bg-[#7A5537] rounded-full animate-bounce" style={{ animationDelay: "150ms" }}></span>
                              <span className="w-2.5 h-2.5 bg-[#7A5537] rounded-full animate-bounce" style={{ animationDelay: "300ms" }}></span>
                            </div>
                          ) : (
                            <>
                              {renderMarkdownContent(msg.content)}
                              {isStreaming && index === messages.length - 1 && (
                                <span className="inline-block w-2.5 h-4 bg-[#7A5537] ml-1 animate-pulse" style={{ verticalAlign: "middle" }}></span>
                              )}
                            </>
                          )}
                        </div>
                      )}
                    </div>
                  </div>
                ))}
                <div ref={messagesEndRef} />
              </div>
            )}
          </div>

          {/* INPUT BAR */}
          <div className="shrink-0 p-6 z-10 mt-auto">
            <div className="max-w-4xl mx-auto bg-wood p-3 rounded-full shadow-leather flex items-center gap-3 relative border border-[#2A1810]">
              <div className="absolute left-6 text-[#A08060] font-serif italic pointer-events-none">
                {inputMessage.length === 0 ? (
                  activeAgent === "chef" ? "Ask Chef Gasto: recipes, substitutes, scalings..." :
                  activeAgent === "gardener" ? "Ask Flora Root: plants, pests, watering schedules..." :
                  activeAgent === "baker" ? "Ask Artisan Loaf: sourdough, hydration, proofing times..." :
                  activeAgent === "stylist" ? "Ask Sartorial Thread: outfits, colour palettes, styling..." :
                  "Ask Vivid Bloom: event budgets, timelines, planning..."
                ) : ""}
              </div>
              <input 
                type="text" 
                value={inputMessage}
                onChange={(e) => setInputMessage(e.target.value)}
                onKeyDown={(e) => { if (e.key === "Enter") handleSendMessage(inputMessage) }}
                className="flex-1 bg-transparent border-none text-[#EAE0D3] px-6 py-2 focus:outline-none font-serif text-lg z-10"
              />
              <button 
                onClick={() => handleSendMessage(inputMessage)}
                disabled={isStreaming || !inputMessage.trim()}
                className="w-12 h-12 rounded-full bg-brass shadow-brass flex items-center justify-center text-[#3A2A1A] hover:scale-105 active:scale-95 transition-transform disabled:opacity-50 disabled:hover:scale-100"
              >
                <Send className="w-5 h-5 ml-1" />
              </button>
            </div>
            {/* Status Footer */}
            <div className="max-w-4xl mx-auto flex justify-between px-6 mt-3 text-[10px] text-[#A08060] font-bold uppercase tracking-widest">
              <span className="flex items-center gap-1.5"><Database className="w-3 h-3" /> LlamaIndex Semantic RAG Active</span>
              <span>Input clean. Rate limits verified.</span>
            </div>
          </div>

        </div>
      </main>
    </div>
  )
}
