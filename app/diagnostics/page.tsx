"use client"

import React, { useState, useEffect } from "react"
import {
  Shield, ChefHat, Sprout, Cake, Shirt, Calendar, Send, Sparkles, Database, Cpu, GitBranch, ArrowLeft, Search, Check, AlertCircle, Play, Info, HelpCircle
} from "lucide-react"

interface RAGMatch {
  id: string
  score: number
  text: string
  metadata: {
    title: string
    cuisine?: string
    diet?: string
    prep_time?: number
    difficulty?: string
  }
}

const BACKEND_URL = process.env.NEXT_PUBLIC_BACKEND_URL || "http://127.0.0.1:8000"

export default function DiagnosticsPage() {
  // Telemetry state
  const [telemetry, setTelemetry] = useState<any>(null)
  const [loadingTelemetry, setLoadingTelemetry] = useState(false)
  const [connectionError, setConnectionError] = useState(false)

  // RAG Search Playground state
  const [searchQuery, setSearchQuery] = useState("")
  const [dietFilter, setDietFilter] = useState("none")
  const [ragMatches, setRagMatches] = useState<RAGMatch[]>([])
  const [searchingRAG, setSearchingRAG] = useState(false)

  // Seed Injection state
  const [seedContext, setSeedContext] = useState("")
  const [injectingSeed, setInjectingSeed] = useState(false)
  const [seedResults, setSeedResults] = useState<any>(null)
  
  // Agent-by-agent status tracker
  const [agentStatuses, setAgentStatuses] = useState<Record<string, "pending" | "loading" | "success" | "error">>({
    chef: "pending",
    baker: "pending",
    gardener: "pending",
    stylist: "pending",
    event: "pending"
  })

  // Animation/Mesh visual state
  const [meshState, setMeshState] = useState<"idle" | "rag-query" | "orchestrating" | "agent-analysis" | "plan-generation" | "completed">("idle")
  const [selectedAgentInfo, setSelectedAgentInfo] = useState<any>(null)

  // Helper styles for SVG Mesh Visualizer
  const getOrchestratorToAgentPathStyle = (agentId: string, baseColor: string) => {
    const status = agentStatuses[agentId];
    if (status === "loading") {
      return {
        stroke: baseColor,
        strokeWidth: "3",
        filter: "url(#glow)",
        className: "stroke-dash-pulse"
      };
    }
    if (status === "success") {
      return {
        stroke: baseColor,
        strokeWidth: "2",
        filter: "url(#glow)",
        className: ""
      };
    }
    if (status === "error") {
      return {
        stroke: "#EF4444",
        strokeWidth: "2",
        filter: "",
        className: ""
      };
    }
    return {
      stroke: "#4B3B2B",
      strokeWidth: "1.5",
      filter: "",
      className: ""
    };
  };

  const getAgentToMasterPathStyle = (agentId: string, baseColor: string) => {
    const status = agentStatuses[agentId];
    
    // When master plan is synthesizing, pulse the paths of all successful agents
    if (meshState === "plan-generation") {
      if (status === "success") {
        return {
          stroke: baseColor,
          strokeWidth: "3",
          filter: "url(#glow)",
          className: "stroke-dash-pulse"
        };
      }
    }
    
    if (status === "success") {
      return {
        stroke: baseColor,
        strokeWidth: "1.8",
        filter: "",
        className: ""
      };
    }
    if (status === "error") {
      return {
        stroke: "#EF4444",
        strokeWidth: "1.8",
        filter: "",
        className: ""
      };
    }
    return {
      stroke: "#4B3B2B",
      strokeWidth: "1.5",
      filter: "",
      className: ""
    };
  };

  const getAgentNodeStyle = (agentId: string, baseColor: string) => {
    const status = agentStatuses[agentId];
    if (status === "loading") {
      return {
        stroke: "#F59E0B", // amber
        fill: "#2B2015",
        strokeWidth: "3",
        className: "cursor-pointer animate-pulse"
      };
    }
    if (status === "success") {
      return {
        stroke: baseColor,
        fill: "#14261C", // success green tint
        strokeWidth: "2.5",
        className: "cursor-pointer hover:scale-110 transition-transform"
      };
    }
    if (status === "error") {
      return {
        stroke: "#EF4444", // error red
        fill: "#2D1818",
        strokeWidth: "2.5",
        className: "cursor-pointer hover:scale-110 transition-transform"
      };
    }
    return {
      stroke: baseColor,
      fill: "#1C1814",
      strokeWidth: "2",
      className: "cursor-pointer hover:scale-110 transition-transform"
    };
  };

  // Load Telemetry data
  const fetchTelemetry = async () => {
    setLoadingTelemetry(true)
    setConnectionError(false)
    try {
      const res = await fetch(`${BACKEND_URL}/api/system/stats`)
      if (res.ok) {
        const data = await res.json()
        setTelemetry(data)
      } else {
        setConnectionError(true)
      }
    } catch (e) {
      setConnectionError(true)
    } finally {
      setLoadingTelemetry(false)
    }
  }

  useEffect(() => {
    fetchTelemetry()
  }, [])

  // Execute RAG Search Test
  const handleRAGSearch = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!searchQuery.trim()) return
    setSearchingRAG(true)
    try {
      const res = await fetch(`${BACKEND_URL}/api/rag/test?query=${encodeURIComponent(searchQuery)}&diet=${dietFilter}&limit=4`)
      if (res.ok) {
        const data = await res.json()
        setRagMatches(data.matches || [])
      }
    } catch (err) {} finally {
      setSearchingRAG(false)
    }
  }

  // Execute RAG Seed Injection Coordination via SSE Streaming
  const handleSeedInjection = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!seedContext.trim() || injectingSeed) return
    
    setInjectingSeed(true)
    setSeedResults({
      master_plan: "",
      perspectives: {},
      rag_context: []
    })
    setAgentStatuses({
      chef: "pending",
      baker: "pending",
      gardener: "pending",
      stylist: "pending",
      event: "pending"
    })
    
    setMeshState("rag-query")
    
    try {
      const res = await fetch(`${BACKEND_URL}/api/seed/stream`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ seed_context: seedContext })
      })
      
      if (!res.ok) {
        throw new Error("Seed injection coordination call failed.")
      }
      
      const reader = res.body?.getReader()
      const decoder = new TextDecoder()
      if (!reader) {
        throw new Error("Response body is not readable.")
      }
      
      let buffer = ""
      let currentEvent = ""
      
      while (true) {
        const { value, done } = await reader.read()
        if (done) break
        
        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split("\n")
        buffer = lines.pop() || ""
        
        for (const line of lines) {
          const trimmed = line.trim()
          if (!trimmed) continue
          
          if (trimmed.startsWith("event: ")) {
            currentEvent = trimmed.slice(7).trim()
          } else if (trimmed.startsWith("data: ")) {
            const dataContent = trimmed.slice(6).trim()
            try {
              const data = JSON.parse(dataContent)
              
              if (currentEvent === "phase") {
                if (data.phase === "rag") {
                  setMeshState("rag-query")
                } else if (data.phase === "agents") {
                  setMeshState("agent-analysis")
                  setAgentStatuses({
                    chef: "loading",
                    baker: "pending",
                    gardener: "pending",
                    stylist: "pending",
                    event: "pending"
                  })
                } else if (data.phase === "synthesis") {
                  setMeshState("plan-generation")
                }
              } else if (currentEvent === "rag_result") {
                setSeedResults(prev => ({
                  ...prev,
                  rag_context: data.results || []
                }))
              } else if (currentEvent === "agent_result") {
                const { agent_id, status, content } = data
                setSeedResults(prev => ({
                  ...prev,
                  perspectives: {
                    ...(prev?.perspectives || {}),
                    [agent_id]: content
                  }
                }))
                setAgentStatuses(prev => {
                  const updated = { ...prev }
                  updated[agent_id] = status === "success" ? "success" : "error"
                  
                  // Set next agent in list to loading
                  const agentIds = ["chef", "baker", "gardener", "stylist", "event"]
                  const currentIndex = agentIds.indexOf(agent_id)
                  if (currentIndex >= 0 && currentIndex < agentIds.length - 1) {
                    const nextAgentId = agentIds[currentIndex + 1]
                    updated[nextAgentId] = "loading"
                  }
                  return updated
                })
              } else if (currentEvent === "synthesis_result") {
                setSeedResults(prev => ({
                  ...prev,
                  master_plan: data.master_plan || ""
                }))
              } else if (currentEvent === "done") {
                setMeshState("completed")
              }
            } catch (jsonErr) {
              console.error("Error parsing JSON chunk:", jsonErr)
            }
          }
        }
      }
    } catch (err: any) {
      setMeshState("idle")
      alert(err.message || "Error contacting seed coordination API.")
    } finally {
      setInjectingSeed(false)
    }
  }

  const agentDetails: Record<string, { desc: string; tools: string[]; prompt: string; color: string }> = {
    chef: {
      desc: "Culinary mastermind specializing in structured recipe generation, macro estimates, and dietary filter adjustments.",
      tools: ["ingredient_scaler", "macro_estimator", "unit_converter"],
      prompt: "Extract exact ingredients, calculate conversions, and structure professional cooking methodologies.",
      color: "#D4AF37"
    },
    gardener: {
      desc: "Botany and diagnostic soil expert who matches culinary ingredients with micro-climates, soil pH, and seasonal yields.",
      tools: ["soil_ph_analyzer", "companion_planting_index", "watering_schedule_generator"],
      prompt: "Identify planting windows, companion benefits, and micro-climatic requirements for edible gardens.",
      color: "#4C6B53"
    },
    baker: {
      desc: "Baker specializing in gluten structures, proofing algorithms, baker's percentages, and wild sourdough starters.",
      tools: ["bakers_percentage_calculator", "proofing_scheduler", "flour_substitute_matcher"],
      prompt: "Enforce meticulous baking hydration metrics, proofing dynamics, and precise oven temperatures.",
      color: "#C6A24D"
    },
    stylist: {
      desc: "Aesthetic consultant managing dinner table decorations, linen configurations, color schemes, and dress codes.",
      tools: ["color_palette_synthesizer", "tabletop_material_matcher", "dress_code_oracle"],
      prompt: "Enforce color harmony, premium skeuomorphic placement layouts, and high-fashion social themes.",
      color: "#D08A80"
    },
    event: {
      desc: "Operations planner coordinating event flows, sequence tracking, budget parameters, and gathering configurations.",
      tools: ["timeline_scheduler", "budget_allocator", "seating_chart_matrix"],
      prompt: "Structure perfect temporal planning blocks, budget allocations, and functional social dynamics.",
      color: "#5A4027"
    }
  }

  const showAgentInfo = (agentId: string) => {
    const details = agentDetails[agentId]
    if (details) {
      setSelectedAgentInfo({
        id: agentId,
        name: agentId === 'chef' ? 'Chef Gasto' : agentId === 'gardener' ? 'Flora Root' : agentId === 'baker' ? 'Artisan Loaf' : agentId === 'stylist' ? 'Sartorial Thread' : 'Vivid Bloom',
        ...details
      })
    }
  }

  return (
    <div className="flex h-screen overflow-hidden bg-leather-green font-sans text-[#EAE0D3]">
      {/* Background Stitched Mat */}
      <div className="flex-1 bg-leather-green stitched-border shadow-leather flex flex-col relative overflow-hidden stitched-inner min-h-0">
        
        {/* HEADER BAR */}
        <header className="shrink-0 h-20 flex items-center justify-between px-8 z-10 pt-4 border-b border-[#2A3F30]/40">
          <div className="flex items-center gap-4">
            <a href="/" className="bg-brass p-2 rounded-full shadow-brass text-[#3A2A1A] hover:scale-105 active:scale-95 transition-transform flex items-center gap-2 px-4 font-serif font-bold text-sm">
              <ArrowLeft className="w-4 h-4" /> Agent Workspace
            </a>
          </div>
          
          <div className="flex justify-center">
            <div className="bg-brass px-8 py-3 rounded-lg shadow-brass relative">
              <div className="absolute left-2 top-1/2 -translate-y-1/2 w-1.5 h-1.5 rounded-full bg-[#3A2A1A] shadow-debossed"></div>
              <div className="absolute right-2 top-1/2 -translate-y-1/2 w-1.5 h-1.5 rounded-full bg-[#3A2A1A] shadow-debossed"></div>
              <h1 className="font-serif font-bold text-xl text-[#3A2A1A] tracking-wider flex items-center gap-2" style={{ textShadow: "1px 1px 0 rgba(255,255,255,0.5)" }}>
                <Shield className="w-5 h-5" /> Allora Diagnostics & Seeding
              </h1>
            </div>
          </div>

          <div className="flex justify-end">
            <button onClick={fetchTelemetry} className="bg-brass p-1.5 rounded-full shadow-brass flex items-center gap-3 px-4 hover:scale-102 active:scale-98 transition-all">
              <div className={`w-3 h-3 rounded-full ${connectionError ? "bg-red-500 animate-pulse" : "bg-[#A3D9A5] shadow-[0_0_8px_rgba(163,217,165,0.9)] animate-pulse-slow"}`}></div>
              <span className="text-[10px] font-bold text-[#3A2A1A] uppercase tracking-widest">{loadingTelemetry ? "Loading..." : connectionError ? "Offline" : "System Live"}</span>
            </button>
          </div>
        </header>

        {/* WORKSPACE MIDDLE BODY */}
        <div className="flex-1 min-h-0 overflow-y-auto px-8 py-6 z-10 grid grid-cols-1 xl:grid-cols-12 gap-8">
          
          {/* LEFT TELEMETRY + RAG SEARCH PLAYGROUND: 4 columns */}
          <div className="xl:col-span-4 space-y-8 flex flex-col justify-start">
            
            {/* PANEL A: SYSTEM TELEMETRY */}
            <div className="bg-leather-brown p-5 rounded-2xl stitched-border shadow-leather">
              <h2 className="font-serif text-lg text-accent-gold border-b border-[#7A5537] pb-2 mb-4 flex items-center gap-2">
                <Cpu className="w-4 h-4" /> System Telemetry Metrics
              </h2>
              {loadingTelemetry && !telemetry ? (
                <p className="font-serif text-xs italic animate-pulse">Querying core telemetry metrics...</p>
              ) : telemetry ? (
                <div className="space-y-4 text-xs font-serif">
                  <div className="flex justify-between items-center bg-[#2A1810] p-3 rounded border border-[#4B3B2B]">
                    <span className="text-[#A08060] font-bold uppercase tracking-wide">Kernel Status</span>
                    <span className="flex items-center gap-2 text-[#EAE0D3] font-bold">
                      <div className="w-2 h-2 rounded-full bg-[#A3D9A5] shadow-[0_0_4px_rgba(163,217,165,0.8)]"></div>
                      Healthy
                    </span>
                  </div>
                  
                  <div className="flex justify-between items-center bg-[#2A1810] p-3 rounded border border-[#4B3B2B]">
                    <span className="text-[#A08060] font-bold uppercase tracking-wide">Active Memories</span>
                    <span className="text-accent-gold font-bold">{telemetry.sessions_count} user sessions</span>
                  </div>

                  <div className="bg-[#2A1810] p-3 rounded border border-[#4B3B2B] space-y-2">
                    <div className="flex justify-between items-center">
                      <span className="text-[#A08060] font-bold uppercase tracking-wide">RAG Collection</span>
                      <span className="text-[#EAE0D3] font-mono">{telemetry.vector_db.collection}</span>
                    </div>
                    <div className="flex justify-between items-center border-t border-[#4B3B2B] pt-2 mt-1">
                      <span className="text-[#A08060] font-bold uppercase tracking-wide">Embedding Nodes</span>
                      <span className="text-accent-gold font-bold">{telemetry.vector_db.vectors_count} active points</span>
                    </div>
                    <div className="flex justify-between items-center border-t border-[#4B3B2B] pt-2 mt-1">
                      <span className="text-[#A08060] font-bold uppercase tracking-wide">DB Engine Path</span>
                      <span className="text-[#EAE0D3]/80 font-mono text-[9px] truncate max-w-[140px]" title={telemetry.vector_db.fallback_memory ? "In-Memory Sandbox" : "Persistent Local SQLite-Qdrant DB"}>
                        {telemetry.vector_db.fallback_memory ? ":memory: sandbox" : "persistent disk storage"}
                      </span>
                    </div>
                  </div>
                </div>
              ) : (
                <div className="bg-[#2A1810] p-3 rounded border border-red-900/40 text-red-400 text-xs flex items-center gap-2 font-serif">
                  <AlertCircle className="w-4 h-4 shrink-0" /> Failed to synchronize server metrics. Verify FastAPI is online at {BACKEND_URL}.
                </div>
              )}
            </div>

            {/* PANEL B: RAG VECTOR SEARCH PLAYGROUND */}
            <div className="bg-leather-brown p-5 rounded-2xl stitched-border shadow-leather flex-1 flex flex-col">
              <h2 className="font-serif text-lg text-accent-gold border-b border-[#7A5537] pb-2 mb-4 flex items-center gap-2">
                <Database className="w-4 h-4 text-accent-gold" /> RAG Semantic Search Sandbox
              </h2>
              
              <form onSubmit={handleRAGSearch} className="space-y-4 shrink-0">
                <div>
                  <label className="text-[10px] text-[#A08060] font-bold uppercase tracking-widest block mb-1">Vector Query string</label>
                  <div className="relative">
                    <input
                      type="text"
                      value={searchQuery}
                      onChange={(e) => setSearchQuery(e.target.value)}
                      placeholder="e.g. sourdough bread proofing, fresh tomato salad..."
                      className="w-full bg-[#2A1810] border border-[#4B3B2B] rounded-lg px-4 py-2 text-xs text-[#EAE0D3] focus:outline-none placeholder-[#8B7355] font-serif"
                    />
                    <button type="submit" className="absolute right-2 top-1/2 -translate-y-1/2 text-accent-gold hover:scale-110 transition-transform">
                      <Search className="w-4 h-4" />
                    </button>
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="text-[10px] text-[#A08060] font-bold uppercase tracking-widest block mb-1">RAG Metadata filter</label>
                    <select
                      value={dietFilter}
                      onChange={(e) => setDietFilter(e.target.value)}
                      className="w-full bg-[#2A1810] border border-[#4B3B2B] rounded-lg px-3 py-2 text-xs text-[#EAE0D3] focus:outline-none font-serif cursor-pointer"
                    >
                      <option value="none">No Dietary Filters</option>
                      <option value="gluten-free">Gluten-Free Suitability</option>
                      <option value="vegan">Vegan Suitability</option>
                      <option value="keto">Keto Suitability</option>
                    </select>
                  </div>
                  <div className="flex items-end">
                    <button
                      type="submit"
                      disabled={searchingRAG || !searchQuery.trim()}
                      className="w-full bg-[#2A1810] border border-[#7A5537] text-accent-gold py-2 rounded-lg text-xs font-bold font-serif hover:bg-[#3A2218] transition-all disabled:opacity-50"
                    >
                      {searchingRAG ? "Searching..." : "Retrieve Nodes"}
                    </button>
                  </div>
                </div>
              </form>

              {/* Matches Output List */}
              <div className="flex-1 overflow-y-auto mt-4 space-y-3 min-h-[180px] max-h-[300px] xl:max-h-none">
                {searchingRAG ? (
                  <p className="font-serif text-xs italic text-[#A08060] animate-pulse">Running cosine-similarity search on Qdrant collection...</p>
                ) : ragMatches.length > 0 ? (
                  ragMatches.map((match, idx) => (
                    <div key={idx} className="bg-[#2A1810] p-3 rounded-lg border border-[#4B3B2B] text-xs font-serif space-y-2 fade-in">
                      <div className="flex justify-between items-center border-b border-[#4B3B2B] pb-1.5">
                        <span className="text-accent-gold font-bold">{match.metadata.title || "Retrieved Segment"}</span>
                        <span className="bg-[#3A241A] text-accent-gold px-2 py-0.5 rounded text-[10px] font-mono font-bold">
                          {(match.score * 100).toFixed(1)}% Match
                        </span>
                      </div>
                      <p className="text-[#EAE0D3]/85 text-[11px] leading-relaxed line-clamp-3 overflow-hidden text-ellipsis" title={match.text}>
                        {match.text}
                      </p>
                      <div className="flex flex-wrap gap-2 text-[9px] text-[#A08060] pt-1">
                        <span className="bg-[#1A0F0A] px-2 py-0.5 rounded border border-[#4B3B2B] capitalize">Cuisine: {match.metadata.cuisine || "any"}</span>
                        <span className="bg-[#1A0F0A] px-2 py-0.5 rounded border border-[#4B3B2B] capitalize">Diet: {match.metadata.diet || "none"}</span>
                        <span className="bg-[#1A0F0A] px-2 py-0.5 rounded border border-[#4B3B2B]">Prep: {match.metadata.prep_time || "0"} mins</span>
                      </div>
                    </div>
                  ))
                ) : (
                  <div className="h-full flex items-center justify-center border border-dashed border-[#4B3B2B] rounded-lg p-6 text-center text-xs text-[#8B7355] italic font-serif">
                    Query the semantic indexes above to inspect dynamic RAG nodes in real-time.
                  </div>
                )}
              </div>
            </div>

          </div>

          {/* RIGHT SEED INJECTION & MESH DYNAMICS: 8 columns */}
          <div className="xl:col-span-8 space-y-8 flex flex-col justify-start min-h-0">
            
            {/* PANEL C: ACTIVE AGENT-MESH TOPOLOGY VISUALIZER */}
            <div className="bg-leather-brown p-5 rounded-2xl stitched-border shadow-leather flex flex-col shrink-0">
              <h2 className="font-serif text-lg text-accent-gold border-b border-[#7A5537] pb-2 mb-4 flex items-center gap-2">
                <GitBranch className="w-4 h-4 text-accent-gold" /> Interactive Multi-Agent Orchestration Mesh Visualizer
              </h2>
              
              <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-center">
                
                {/* SVG Visualizer Canvas: 7 columns */}
                <div className="lg:col-span-7 bg-[#2A1810] rounded-xl border border-[#4B3B2B] p-4 flex items-center justify-center relative overflow-hidden min-h-[300px]">
                  
                  {/* Dynamic Animation Pulse indicators */}
                  {meshState !== "idle" && (
                    <div className="absolute top-3 left-4 text-[9px] font-mono text-accent-gold uppercase tracking-wider bg-[#1A0F0A] border border-[#4B3B2B] px-2 py-1 rounded animate-pulse">
                      Status: {meshState.replace("-", " ")}...
                    </div>
                  )}

                  <svg viewBox="0 0 400 320" className="w-full max-w-[360px] h-auto overflow-visible">
                    {/* Definitions for gradients and drop shadows */}
                    <defs>
                      <filter id="glow" x="-20%" y="-20%" width="140%" height="140%">
                        <feGaussianBlur stdDeviation="3" result="blur" />
                        <feComposite in="SourceGraphic" in2="blur" operator="over" />
                      </filter>
                      <linearGradient id="glowingLine" x1="0%" y1="0%" x2="100%" y2="100%">
                        <stop offset="0%" stopColor="#D4AF37" stopOpacity="0.8" />
                        <stop offset="50%" stopColor="#4C6B53" stopOpacity="0.8" />
                        <stop offset="100%" stopColor="#C6A24D" stopOpacity="0.8" />
                      </linearGradient>
                    </defs>

                    {/* PATHS / CONNECTIONS */}
                    {/* User Seed -> Orchestrator */}
                    <path
                      d="M 50,230 Q 110,210 200,160"
                      fill="none"
                      stroke={meshState !== "idle" ? "url(#glowingLine)" : "#4B3B2B"}
                      strokeWidth={meshState === "rag-query" ? "3" : "1.5"}
                      className={meshState === "rag-query" ? "stroke-dash-pulse" : ""}
                      filter={meshState === "rag-query" ? "url(#glow)" : ""}
                    />
                    
                    {/* Vector DB (RAG) -> Orchestrator */}
                    <path
                      d="M 50,90 Q 110,110 200,160"
                      fill="none"
                      stroke={meshState !== "idle" ? "url(#glowingLine)" : "#4B3B2B"}
                      strokeWidth={meshState === "rag-query" ? "3" : "1.5"}
                      className={meshState === "rag-query" ? "stroke-dash-pulse" : ""}
                      filter={meshState === "rag-query" ? "url(#glow)" : ""}
                    />

                    {/* Orchestrator -> 5 Agents */}
                    {/* Orchestrator -> Chef */}
                    <path
                      d="M 200,160 Q 220,90 280,50"
                      fill="none"
                      {...getOrchestratorToAgentPathStyle("chef", "#D4AF37")}
                    />
                    {/* Orchestrator -> Baker */}
                    <path
                      d="M 200,160 L 320,110"
                      fill="none"
                      {...getOrchestratorToAgentPathStyle("baker", "#C6A24D")}
                    />
                    {/* Orchestrator -> Gardener */}
                    <path
                      d="M 200,160 L 320,210"
                      fill="none"
                      {...getOrchestratorToAgentPathStyle("gardener", "#4C6B53")}
                    />
                    {/* Orchestrator -> Stylist */}
                    <path
                      d="M 200,160 Q 230,240 280,270"
                      fill="none"
                      {...getOrchestratorToAgentPathStyle("stylist", "#D08A80")}
                    />
                    {/* Orchestrator -> Event Planner */}
                    <path
                      d="M 200,160 L 200,270"
                      fill="none"
                      {...getOrchestratorToAgentPathStyle("event", "#5A4027")}
                    />

                    {/* Gather from 5 Agents to Master Plan Synthesis Node */}
                    <path
                      d="M 280,50 Q 350,130 350,160"
                      fill="none"
                      {...getAgentToMasterPathStyle("chef", "#D4AF37")}
                    />
                    <path
                      d="M 320,110 Q 350,130 350,160"
                      fill="none"
                      {...getAgentToMasterPathStyle("baker", "#C6A24D")}
                    />
                    <path
                      d="M 320,210 Q 350,190 350,160"
                      fill="none"
                      {...getAgentToMasterPathStyle("gardener", "#4C6B53")}
                    />
                    <path
                      d="M 280,270 Q 350,190 350,160"
                      fill="none"
                      {...getAgentToMasterPathStyle("stylist", "#D08A80")}
                    />
                    <path
                      d="M 200,270 Q 300,270 350,160"
                      fill="none"
                      {...getAgentToMasterPathStyle("event", "#5A4027")}
                    />


                    {/* TOPOLOGY NODES */}

                    {/* 1. Vector RAG DB Node */}
                    <circle cx="50" cy="90" r="18" fill="#1C3225" stroke="#4C6B53" strokeWidth="2" className="cursor-pointer hover:stroke-white transition-all" onClick={() => alert("Vector RAG Collection: 'chef_kb'. Contains dense embeddings processed via Google Gemini embedding-001.")} />
                    <foreignObject x="38" y="78" width="24" height="24" className="pointer-events-none">
                      <div className="text-[#4C6B53] flex items-center justify-center h-full"><Database className="w-4 h-4" /></div>
                    </foreignObject>
                    <text x="50" y="120" textAnchor="middle" fill="#A08060" fontSize="9" fontWeight="bold" className="pointer-events-none font-serif">VECTOR RAG</text>

                    {/* 2. User Seed Input Node */}
                    <circle cx="50" cy="230" r="18" fill="#3D2314" stroke="#7A5537" strokeWidth="2" className="cursor-pointer hover:stroke-white transition-all" onClick={() => alert("Seed Node: Triggers seed scenarios and distributes parameters asynchronously across parallel agents.")} />
                    <foreignObject x="38" y="218" width="24" height="24" className="pointer-events-none">
                      <div className="text-accent-gold flex items-center justify-center h-full"><Send className="w-4 h-4" /></div>
                    </foreignObject>
                    <text x="50" y="260" textAnchor="middle" fill="#A08060" fontSize="9" fontWeight="bold" className="pointer-events-none font-serif">USER SEED</text>

                    {/* 3. Orchestration Kernel Node (Central) */}
                    <circle cx="200" cy="160" r="24" fill="#2E2315" stroke="#C6A24D" strokeWidth="2" className="cursor-pointer hover:stroke-white transition-all" onClick={() => alert("Allora Orchestrator: Dynamic thread-safe memory manager that maps queries, filters conflicts, and calls synthesis engines.")} />
                    <foreignObject x="186" y="146" width="28" height="28" className="pointer-events-none">
                      <div className="text-accent-gold flex items-center justify-center h-full"><Cpu className="w-5 h-5" /></div>
                    </foreignObject>
                    <text x="200" y="196" textAnchor="middle" fill="#EAE0D3" fontSize="9" fontWeight="bold" className="pointer-events-none font-serif">ORCHESTRATOR</text>


                    {/* 5 SURROUNDING SPECIALIZED AGENT NODES */}

                    {/* Chef Agent */}
                    <circle cx="280" cy="50" r="16" onClick={() => showAgentInfo("chef")} {...getAgentNodeStyle("chef", "#D4AF37")} />
                    <foreignObject x="268" y="38" width="24" height="24" className="pointer-events-none">
                      <div className="text-[#D4AF37] flex items-center justify-center h-full"><ChefHat className="w-4 h-4" /></div>
                    </foreignObject>
                    <text x="280" y="76" textAnchor="middle" fill="#A08060" fontSize="8" className="pointer-events-none font-serif">Chef Gasto</text>

                    {/* Baker Agent */}
                    <circle cx="320" cy="110" r="16" onClick={() => showAgentInfo("baker")} {...getAgentNodeStyle("baker", "#C6A24D")} />
                    <foreignObject x="308" y="98" width="24" height="24" className="pointer-events-none">
                      <div className="text-[#C6A24D] flex items-center justify-center h-full"><Cake className="w-4 h-4" /></div>
                    </foreignObject>
                    <text x="320" y="136" textAnchor="middle" fill="#A08060" fontSize="8" className="pointer-events-none font-serif">Artisan Loaf</text>

                    {/* Gardener Agent */}
                    <circle cx="320" cy="210" r="16" onClick={() => showAgentInfo("gardener")} {...getAgentNodeStyle("gardener", "#4C6B53")} />
                    <foreignObject x="308" y="198" width="24" height="24" className="pointer-events-none">
                      <div className="text-[#4C6B53] flex items-center justify-center h-full"><Sprout className="w-4 h-4" /></div>
                    </foreignObject>
                    <text x="320" y="236" textAnchor="middle" fill="#A08060" fontSize="8" className="pointer-events-none font-serif">Flora Root</text>

                    {/* Stylist Agent */}
                    <circle cx="280" cy="270" r="16" onClick={() => showAgentInfo("stylist")} {...getAgentNodeStyle("stylist", "#D08A80")} />
                    <foreignObject x="268" y="258" width="24" height="24" className="pointer-events-none">
                      <div className="text-[#D08A80] flex items-center justify-center h-full"><Shirt className="w-4 h-4" /></div>
                    </foreignObject>
                    <text x="280" y="296" textAnchor="middle" fill="#A08060" fontSize="8" className="pointer-events-none font-serif">Sartorial</text>

                    {/* Event Planner Agent */}
                    <circle cx="200" cy="270" r="16" onClick={() => showAgentInfo("event")} {...getAgentNodeStyle("event", "#5A4027")} />
                    <foreignObject x="188" y="258" width="24" height="24" className="pointer-events-none">
                      <div className="text-[#5A4027] flex items-center justify-center h-full"><Calendar className="w-4 h-4" /></div>
                    </foreignObject>
                    <text x="200" y="296" textAnchor="middle" fill="#A08060" fontSize="8" className="pointer-events-none font-serif">Vivid Bloom</text>


                    {/* 4. Synthesized Master Plan Node */}
                    <circle cx="350" cy="160" r="20" fill="#2E2315" stroke="url(#glowingLine)" strokeWidth="2.5" className="cursor-pointer hover:stroke-white transition-all" onClick={() => alert("Master Plan Node: Aggregates individual agent perspectives and resolves scheduling, style, or recipe conflicts.")} />
                    <foreignObject x="338" y="148" width="24" height="24" className="pointer-events-none">
                      <div className="text-accent-gold flex items-center justify-center h-full animate-pulse-slow"><Sparkles className="w-4 h-4" /></div>
                    </foreignObject>
                    <text x="350" y="196" textAnchor="middle" fill="#EAE0D3" fontSize="9" fontWeight="bold" className="pointer-events-none font-serif">MASTER PLAN</text>
                  </svg>
                </div>

                {/* Node Inspection Sidebar Info: 5 columns */}
                <div className="lg:col-span-5 bg-[#2A1810] rounded-xl border border-[#4B3B2B] p-5 flex flex-col justify-center min-h-[300px] text-xs font-serif">
                  {selectedAgentInfo ? (
                    <div className="space-y-4 fade-in">
                      <div className="flex items-center gap-3 border-b border-[#4B3B2B] pb-3">
                        <div className="p-2 rounded-lg bg-leather-brown border border-[#7A5537]" style={{ color: selectedAgentInfo.color }}>
                          {selectedAgentInfo.id === 'chef' ? <ChefHat className="w-5 h-5" /> :
                           selectedAgentInfo.id === 'gardener' ? <Sprout className="w-5 h-5" /> :
                           selectedAgentInfo.id === 'baker' ? <Cake className="w-5 h-5" /> :
                           selectedAgentInfo.id === 'stylist' ? <Shirt className="w-5 h-5" /> : <Calendar className="w-5 h-5" />}
                        </div>
                        <div>
                          <h3 className="font-serif font-bold text-base text-accent-gold">{selectedAgentInfo.name}</h3>
                          <div className="text-[9px] font-bold text-[#A08060] uppercase tracking-wider">Agent Pod Specs</div>
                        </div>
                      </div>

                      <div>
                        <span className="text-[10px] text-[#A08060] font-bold uppercase tracking-widest block mb-1">Operational Role</span>
                        <p className="text-[#EAE0D3]/90 leading-relaxed text-[11px]">{selectedAgentInfo.desc}</p>
                      </div>

                      <div>
                        <span className="text-[10px] text-[#A08060] font-bold uppercase tracking-widest block mb-1">Registered System Prompt</span>
                        <p className="bg-[#1A0F0A] border border-[#4B3B2B] p-2.5 rounded text-[11px] leading-relaxed text-[#EAE0D3] italic font-sans">
                          &quot;{selectedAgentInfo.prompt}&quot;
                        </p>
                      </div>

                      <div>
                        <span className="text-[10px] text-[#A08060] font-bold uppercase tracking-widest block mb-1.5 flex items-center gap-1"><Info className="w-3.5 h-3.5 text-accent-gold" /> Registered Engine Tools</span>
                        <div className="flex flex-wrap gap-2">
                          {selectedAgentInfo.tools.map((tool: string) => (
                            <span key={tool} className="bg-[#1A0F0A] text-accent-gold text-[10px] font-mono px-2.5 py-1 rounded border border-[#4B3B2B] shadow-sm">
                              {tool}
                            </span>
                          ))}
                        </div>
                      </div>
                    </div>
                  ) : (
                    <div className="text-center space-y-4 p-4">
                      <HelpCircle className="w-12 h-12 mx-auto text-[#4B3B2B] animate-pulse" />
                      <div>
                        <h3 className="font-serif font-bold text-sm text-accent-gold mb-1">Topology Node Inspector</h3>
                        <p className="text-[#A08060] text-[11px] leading-relaxed max-w-[200px] mx-auto">
                          Click any Agent Pod node (e.g. Chef, Baker, Gardener) in the visualizer mesh to inspect system prompts, schemas, and operational tools.
                        </p>
                      </div>
                    </div>
                  )}
                </div>

              </div>
            </div>

            {/* PANEL D: RAG SEED INJECTION CONSOLE */}
            <div className="bg-leather-brown p-5 rounded-2xl stitched-border shadow-leather flex flex-col flex-1">
              <h2 className="font-serif text-lg text-accent-gold border-b border-[#7A5537] pb-2 mb-4 flex items-center gap-2">
                <Sparkles className="w-4 h-4 text-accent-gold" /> Multi-Agent Coordination Seed Console
              </h2>

              <form onSubmit={handleSeedInjection} className="space-y-4 shrink-0">
                <div>
                  <label className="text-[10px] text-[#A08060] font-bold uppercase tracking-widest block mb-1">Coordinated Seed Scenario (Context Prompt)</label>
                  <div className="flex gap-4">
                    <textarea
                      value={seedContext}
                      onChange={(e) => setSeedContext(e.target.value)}
                      placeholder="e.g., We are organizing a micro-wedding in a companion garden with sourdough pizza, customized floral table settings, and dynamic temporal planning budgets..."
                      rows={2}
                      className="flex-1 bg-[#2A1810] border border-[#4B3B2B] rounded-lg px-4 py-3 text-xs text-[#EAE0D3] focus:outline-none placeholder-[#8B7355] font-serif resize-none"
                    />
                    <button
                      type="submit"
                      disabled={injectingSeed || !seedContext.trim()}
                      className="bg-brass shadow-brass text-[#3A2A1A] px-6 rounded-lg font-serif font-bold hover:scale-102 active:scale-98 transition-all disabled:opacity-50 flex flex-col items-center justify-center gap-1 py-2 text-xs"
                    >
                      <Play className="w-4 h-4 shrink-0" />
                      <span>{injectingSeed ? "Injecting..." : "Inject Seed"}</span>
                    </button>
                  </div>
                </div>
              </form>

              {/* Seed results view */}
              <div className="flex-1 overflow-y-auto mt-6 space-y-6">
                {injectingSeed && !seedResults && (
                  <div className="space-y-4 p-6 border border-dashed border-[#4B3B2B] rounded-xl text-center bg-[#2A1810] fade-in">
                    <div className="relative w-12 h-12 mx-auto">
                      <div className="absolute inset-0 rounded-full border-2 border-accent-gold border-t-transparent animate-spin"></div>
                    </div>
                    <div className="font-serif text-xs">
                      <p className="text-accent-gold font-bold mb-1">RAG-driven coordination injection path active.</p>
                      <p className="text-[#A08060]">
                        {meshState === "rag-query" ? "1/4 Searching Qdrant database for matching context files..." :
                         meshState === "orchestrating" ? "2/4 Running asynchronous multi-agent perspectives..." :
                         meshState === "agent-analysis" ? "3/4 Parallel agent models processing soil, cooking, styling, and timelines..." :
                         "4/4 Master Orchestrator synthesizing cohesions..."}
                      </p>
                    </div>
                  </div>
                )}

                {seedResults && (
                  <div className="space-y-6 fade-in">
                    
                    {/* 1. Master Plan Scroll */}
                    <div className="bg-parchment p-6 rounded-xl border border-[#D5C6B3] text-[#3A2A1A] relative shadow-md">
                      <div className="absolute top-0 right-0 w-20 h-20 bg-leather-brown opacity-5 rounded-bl-full pointer-events-none"></div>
                      
                      <div className="flex items-center gap-3 border-b border-[#D5C6B3] pb-3 mb-4">
                        <Sparkles className="w-5 h-5 text-[#7A5537] animate-pulse" />
                        <div>
                          <h3 className="font-serif font-bold text-lg text-[#3A2A1A]">Master Synthesized Plan</h3>
                          <div className="text-[9px] font-bold text-[#8B7355] uppercase tracking-wider">Consolidated Orchestration Outcome</div>
                        </div>
                      </div>

                      {/* plan markdown renderer */}
                      <div className="font-serif text-xs leading-relaxed space-y-3 max-h-[300px] overflow-y-auto pr-2">
                        {seedResults.master_plan.split("\n").map((line: string, idx: number) => {
                          if (line.startsWith("# ")) return <h1 key={idx} className="text-xl font-bold text-[#3A2A1A] mt-4 mb-2">{line.slice(2)}</h1>
                          if (line.startsWith("## ")) return <h2 key={idx} className="text-base font-bold text-[#3A2A1A] mt-3 mb-2">{line.slice(3)}</h2>
                          if (line.startsWith("- ") || line.startsWith("* ")) {
                            const boldParts = line.slice(2).split("**")
                            return <li key={idx} className="ml-4 list-disc text-[#3A2A1A]/90">{boldParts.map((part, pIdx) => pIdx % 2 === 1 ? <strong key={pIdx} className="text-[#7A5537] font-bold">{part}</strong> : part)}</li>
                          }
                          if (line.trim().length === 0) return <div key={idx} className="h-2"></div>
                          
                          const boldParts = line.split("**")
                          return <p key={idx} className="text-[#3A2A1A]/90">{boldParts.map((part, pIdx) => pIdx % 2 === 1 ? <strong key={pIdx} className="text-[#7A5537] font-bold">{part}</strong> : part)}</p>
                        })}
                      </div>
                    </div>

                    {/* 2. Parallel Agent contributions */}
                    <div>
                      <h4 className="text-[10px] text-[#A08060] font-bold uppercase tracking-widest mb-3 flex items-center gap-1"><Cpu className="w-3.5 h-3.5" /> Parallel Agent Perspectives</h4>
                      <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
                        {Object.entries(seedResults.perspectives).map(([agentId, content]: [string, any]) => (
                          <div key={agentId} className="bg-[#2A1810] p-4 rounded-xl border border-[#4B3B2B] text-xs font-serif flex flex-col relative overflow-hidden">
                            <div className="absolute top-0 right-0 w-10 h-10 bg-white/5 rounded-bl-full pointer-events-none"></div>
                            
                            <div className="flex items-center gap-2 border-b border-[#4B3B2B] pb-2 mb-3">
                              <span style={{ color: agentDetails[agentId]?.color }}>
                                {agentId === 'chef' ? <ChefHat className="w-4 h-4" /> :
                                 agentId === 'gardener' ? <Sprout className="w-4 h-4" /> :
                                 agentId === 'baker' ? <Cake className="w-4 h-4" /> :
                                 agentId === 'stylist' ? <Shirt className="w-4 h-4" /> : <Calendar className="w-4 h-4" />}
                              </span>
                              <span className="font-bold text-[#EAE0D3] truncate capitalize">{agentId}</span>
                            </div>

                            <p className="text-[#EAE0D3]/85 text-[11px] leading-relaxed flex-1 line-clamp-4 hover:line-clamp-none transition-all cursor-help" title={content}>
                              {content}
                            </p>
                          </div>
                        ))}
                      </div>
                    </div>

                    {/* 3. Injected RAG References */}
                    {seedResults.rag_context && seedResults.rag_context.length > 0 && (
                      <div className="bg-[#2A1810] p-4 rounded-xl border border-[#4B3B2B]">
                        <h4 className="text-[10px] text-[#A08060] font-bold uppercase tracking-widest mb-3 flex items-center gap-1.5"><Database className="w-3.5 h-3.5 text-accent-gold" /> Injected RAG Knowledge References</h4>
                        <div className="space-y-3">
                          {seedResults.rag_context.map((rag: any, idx: number) => (
                            <div key={idx} className="bg-[#1A0F0A] p-3 rounded-lg border border-[#4B3B2B] text-[11px] font-serif leading-relaxed">
                              <div className="flex justify-between items-center text-accent-gold font-bold mb-1">
                                <span>Article reference: {rag.metadata?.title || "Knowledge Node"}</span>
                                <span className="bg-[#2A1810] text-[#A08060] px-2 py-0.5 rounded text-[9px] font-mono">Similarity: {(rag.score * 100).toFixed(1)}%</span>
                              </div>
                              <p className="text-[#EAE0D3]/80 italic">
                                &quot;{rag.text}&quot;
                              </p>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}

                  </div>
                )}

                {!seedResults && !injectingSeed && (
                  <div className="h-full flex flex-col items-center justify-center border border-dashed border-[#4B3B2B] rounded-xl p-8 text-center bg-[#2A1810] text-[#8B7355] italic font-serif">
                    <Sparkles className="w-10 h-10 mx-auto text-[#4B3B2B] mb-3 animate-pulse-slow" />
                    <div>
                      <h4 className="font-bold text-sm text-accent-gold mb-1">Awaiting Seed Injection</h4>
                      <p className="text-[11px] leading-relaxed max-w-[340px] mx-auto text-[#8B7355]">
                        Provide a coordination scenario context prompt above. The system will retrieve relevant RAG context, query all five agents asynchronously, and synthesize a cohesive plan!
                      </p>
                    </div>
                  </div>
                )}

              </div>
            </div>

          </div>

        </div>

      </div>

      {/* STYLES FOR THE SVG LINE ANIMATIONS */}
      <style jsx global>{`
        .stroke-dash-pulse {
          stroke-dasharray: 8, 8;
          animation: strokeDashMove 1s linear infinite;
        }
        @keyframes strokeDashMove {
          to {
            stroke-dashoffset: -16;
          }
        }
      `}</style>
    </div>
  )
}
