const template = document.createElement("template");

template.innerHTML = `
  <style>
    :host { --accent: #173b73; --accent-strong: #102b55; --gold: #d9b45b; --surface: #fff; --ink: #182235; --muted: #68758b; --line: #dfe5ee; font: 15px/1.45 Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; color: var(--ink); }
    * { box-sizing: border-box; }
    button, textarea { font: inherit; }
    .launcher { position: fixed; right: 22px; bottom: 22px; z-index: 2147483000; width: 58px; height: 58px; border: 2px solid var(--gold); border-radius: 18px; color: var(--gold); background: var(--accent); box-shadow: 0 14px 38px rgba(15,35,70,.3); cursor: pointer; display: grid; place-items: center; transition: transform .18s ease, background .18s ease; }
    .launcher:hover { transform: translateY(-2px); background: var(--accent-strong); }
    .launcher svg { width: 27px; height: 27px; }
    .panel { position: fixed; right: 22px; bottom: 92px; z-index: 2147482999; width: min(390px, calc(100vw - 28px)); height: min(620px, calc(100vh - 120px)); border: 1px solid rgba(19,42,78,.12); border-radius: 22px; overflow: hidden; background: var(--surface); box-shadow: 0 24px 70px rgba(15,35,70,.25); display: grid; grid-template-rows: auto 1fr auto; opacity: 0; pointer-events: none; transform: translateY(12px) scale(.98); transform-origin: bottom right; transition: opacity .18s ease, transform .18s ease; }
    .panel.open { opacity: 1; pointer-events: auto; transform: none; }
    header { border-bottom: 3px solid var(--gold); padding: 18px 20px; background: var(--accent); color: white; display: flex; gap: 12px; align-items: center; }
    .mark { width: 39px; height: 39px; border-radius: 13px; background: var(--gold); color: #102b55; display: grid; place-items: center; font-weight: 800; }
    .heading { min-width: 0; flex: 1; }
    h2 { margin: 0; font-size: 16px; line-height: 1.2; }
    header p { margin: 3px 0 0; font-size: 12px; opacity: .82; }
    .close { border: 0; background: transparent; color: white; font-size: 24px; cursor: pointer; opacity: .85; }
    .messages { padding: 18px 16px 24px; overflow: auto; background: #f5f7fa; scroll-behavior: smooth; }
    .row { display: flex; margin: 0 0 13px; }
    .row.user { justify-content: flex-end; }
    .bubble { max-width: 88%; padding: 11px 13px; border-radius: 15px; background: #fff; box-shadow: 0 2px 7px rgba(20,35,60,.07); white-space: pre-wrap; overflow-wrap: anywhere; }
    .user .bubble { color: #fff; background: var(--accent); border-bottom-right-radius: 5px; }
    .assistant .bubble { border-bottom-left-radius: 5px; }
    .bubble p { margin: 0; }
    .sources { margin-top: 9px; padding-top: 8px; border-top: 1px solid var(--line); display: grid; gap: 6px; }
    .sources span { color: var(--muted); font-size: 11px; text-transform: uppercase; letter-spacing: .06em; }
    .sources a { color: var(--accent); font-size: 12px; font-weight: 650; text-decoration: none; }
    .sources a:hover { text-decoration: underline; }
    .typing { display: inline-flex; gap: 4px; align-items: center; min-height: 16px; }
    .typing i { width: 6px; height: 6px; border-radius: 50%; background: #8793a7; animation: pulse 1s infinite alternate; }
    .typing i:nth-child(2) { animation-delay: .2s; }.typing i:nth-child(3) { animation-delay: .4s; }
    @keyframes pulse { to { opacity: .25; transform: translateY(-2px); } }
    .status { padding: 8px 16px 0; color: #a33a36; font-size: 12px; background: #fff; display: none; }
    .status.visible { display: block; }
    form { padding: 12px; border-top: 1px solid var(--line); background: #fff; display: grid; grid-template-columns: 1fr auto; align-items: end; gap: 9px; }
    textarea { width: 100%; max-height: 104px; min-height: 44px; resize: none; border: 1px solid var(--line); border-radius: 13px; padding: 11px 12px; color: var(--ink); outline: none; }
    textarea:focus { border-color: var(--accent); box-shadow: 0 0 0 3px color-mix(in srgb, var(--accent) 14%, transparent); }
    .send { width: 44px; height: 44px; border: 0; border-radius: 13px; background: var(--gold); color: #102b55; cursor: pointer; display: grid; place-items: center; }
    .send:disabled, textarea:disabled { opacity: .55; cursor: wait; }
    .send svg { width: 20px; }
    @media (max-width: 540px) { .panel { inset: 0; width: 100vw; height: 100dvh; max-height: none; border: 0; border-radius: 0; } .launcher { right: 15px; bottom: 15px; } .panel.open + .launcher { display: none; } }
    @media (prefers-reduced-motion: reduce) { *, *::before, *::after { animation-duration: .01ms !important; transition-duration: .01ms !important; } }
    .restart { background: transparent; border: 1px solid #ffffff55; color: white; border-radius: 6px; padding: 6px; font-size: 10px; cursor: pointer; } .sources details { font-size: 12px; } .sources summary { cursor: pointer; color: var(--accent); } .sources details p { font-size: 11px; color: var(--muted); margin: 6px 0; }
    @media(max-width:540px) { form { padding-bottom: max(12px, env(safe-area-inset-bottom)); } }
  </style>
  <section class="panel" role="dialog" aria-label="Atendimento virtual" aria-hidden="true">
    <header><div class="mark" aria-hidden="true">A</div><div class="heading"><h2></h2><p>Assistente virtual institucional</p></div><button class="close" type="button" aria-label="Fechar conversa">×</button></header>
    <div class="messages" aria-live="polite"></div>
    <div><div class="status" role="alert"></div><form><textarea rows="1" maxlength="8000" placeholder="Digite sua pergunta..." aria-label="Mensagem"></textarea><button class="send" type="submit" aria-label="Enviar mensagem"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="m22 2-7 20-4-9-9-4Z"/><path d="M22 2 11 13"/></svg></button></form></div>
  </section>
  <button class="launcher" type="button" aria-label="Abrir atendimento virtual" aria-expanded="false"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15a4 4 0 0 1-4 4H8l-5 3V7a4 4 0 0 1 4-4h10a4 4 0 0 1 4 4Z"/><path d="M8 9h8M8 13h5"/></svg></button>
`;

class ChatbotPlatform extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" }).append(template.content.cloneNode(true));
    for (const [name, selector] of Object.entries({panel:".panel",messages:".messages",form:"form",input:"textarea",sendButton:".send",status:".status",launcher:".launcher"})) this[name] = this.shadowRoot.querySelector(selector);
    this.sessionId = null; this.busy = false; this.ready = false; this.initialized = false;
  }
  connectedCallback() {
    if (this.initialized) return;
    this.initialized = true;
    this.apiUrl = (this.getAttribute("api-url") || "").replace(/\/$/, "");
    this.assistantId = this.getAttribute("assistant-id") || "";
    this.legacy = this.hasAttribute("token-endpoint") || this.hasAttribute("token");
    this.storageKey = `fafic-chat-${this.apiUrl}-${this.assistantId}`;
    this.unavailableMessage = this.getAttribute("unavailable-message") || "Nosso bot está temporariamente indisponível. Tente novamente mais tarde.";
    try { this.unavailableMessage = sessionStorage.getItem(this.storageKey + "-notice") || this.unavailableMessage; } catch {}
    this.setAppearance({name:"Assistente FAFIC",welcome_message:"Olá! Como posso ajudar?",accent_color:"#173b73"});
    this.panel.inert = true;
    this.shadowRoot.querySelector(".close").addEventListener("click", () => this.toggle(false));
    this.launcher.addEventListener("click", () => this.toggle(!this.panel.classList.contains("open")));
    this.form.addEventListener("submit", event => this.submit(event));
    this.input.addEventListener("keydown", event => { if (event.key === "Enter" && !event.shiftKey && !event.isComposing) { event.preventDefault(); this.form.requestSubmit(); } });
    this.shadowRoot.addEventListener("keydown", event => {
      if (event.key === "Escape") this.toggle(false);
      if (event.key === "Tab" && this.panel.classList.contains("open")) {
        const focusable = [...this.panel.querySelectorAll("button:not(:disabled),textarea:not(:disabled),a[href]")];
        const first = focusable[0], last = focusable.at(-1), active = this.shadowRoot.activeElement;
        if (event.shiftKey && active === first) { event.preventDefault(); last?.focus(); }
        else if (!event.shiftKey && active === last) { event.preventDefault(); first?.focus(); }
      }
    });
    this.input.addEventListener("input", () => { this.input.style.height = "auto"; this.input.style.height = `${Math.min(this.input.scrollHeight,104)}px`; });
    const reset = document.createElement("button"); reset.type="button"; reset.className="restart"; reset.textContent="Nova conversa";
    reset.addEventListener("click", () => { if (this.busy) return; this.clearSession(); this.messages.replaceChildren(); this.ready=false; void this.start(); });
    this.shadowRoot.querySelector("header").append(reset);
  }
  setAppearance(config) {
    const title=this.getAttribute("title") || config.name;
    this.shadowRoot.querySelector("h2").textContent=title;
    this.shadowRoot.querySelector(".mark").textContent=title.trim().charAt(0).toUpperCase();
    const color=this.getAttribute("accent-color") || config.accent_color;
    if (/^#[a-f0-9]{6}$/i.test(color)) { this.style.setProperty("--accent",color); this.style.setProperty("--accent-strong",`color-mix(in srgb, ${color} 85%, black)`); }
    this.welcome=this.getAttribute("welcome-message") || config.welcome_message;
    if (config.unavailable_message) { this.unavailableMessage=config.unavailable_message; try { sessionStorage.setItem(this.storageKey + "-notice",this.unavailableMessage); } catch {} }
  }
  readStored() { try { return sessionStorage.getItem(this.storageKey); } catch { return null; } }
  clearSession() { this.sessionId=null; this.currentToken=null; this.resumeToken=null; try { sessionStorage.removeItem(this.storageKey); } catch { /* Storage may be unavailable in privacy mode. */ } }
  async fetchJson(url,options={}) {
    const controller=new AbortController(); const timeout=setTimeout(()=>controller.abort(),50000);
    try {
      const response=await fetch(url,{...options,signal:controller.signal});
      const payload=await response.json().catch(()=>({}));
      if (!response.ok) { const error=new Error(typeof payload.detail === "string" ? payload.detail : "Não foi possível concluir a solicitação."); error.status=response.status; throw error; }
      return payload;
    } catch(error) {
      if (error.name === "AbortError") throw new Error("O atendimento demorou para responder. Tente novamente.");
      if (error instanceof TypeError) throw new Error("Não foi possível conectar ao atendimento. Verifique sua conexão e tente novamente.");
      throw error;
    } finally { clearTimeout(timeout); }
  }
  async bootstrap() {
    const resume=this.resumeToken || this.readStored();
    let data; try { data=await this.fetchJson(`${this.apiUrl}/v1/widget/bootstrap`,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({resume_token:resume})}); } catch(error) { if (resume && (error.status === 401 || error.status === 404)) { this.clearSession(); data=await this.fetchJson(`${this.apiUrl}/v1/widget/bootstrap`,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({resume_token:null})}); } else { throw error; } }
    this.currentToken=data.token; this.resumeToken=data.resume_token; this.sessionId=data.session_id;
    try { sessionStorage.setItem(this.storageKey,data.resume_token); } catch { /* In-memory sessions remain usable. */ }
    this.setAppearance(data); return data;
  }
  async token() {
    const fixed=this.getAttribute("token");
    if (fixed) { if (!fixed.startsWith("wgt_")) throw new Error("Use somente um token temporário."); return fixed; }
    const endpoint=this.getAttribute("token-endpoint");
    if (!endpoint) throw new Error("Atendimento ainda não configurado.");
    const data=await this.fetchJson(endpoint,{credentials:"same-origin",headers:{Accept:"application/json"}});
    if (!data.token?.startsWith("wgt_")) throw new Error("Acesso temporário inválido.");
    return data.token;
  }
  async request(path, options={}, retry=true) {
    if (!this.currentToken) { if (this.legacy) this.currentToken=await this.token(); else await this.bootstrap(); }
    try { return await this.fetchJson(`${this.apiUrl}${path}`,{...options,headers:{"Content-Type":"application/json",Authorization:`Bearer ${this.currentToken}`,...(options.headers||{})}}); }
    catch(error) {
      if (error.status === 401 && retry && !this.hasAttribute("token")) {
        this.currentToken=null;
        if (this.legacy) this.currentToken=await this.token(); else await this.bootstrap();
        return this.request(path,options,false);
      }
      throw error;
    }
  }
  async start() {
    if (this.busy) return;
    this.setBusy(true); this.showError("");
    try {
      if (!this.apiUrl) throw new Error("Atendimento ainda não configurado.");
      if (!this.legacy) { const appearance=await this.fetchJson(`${this.apiUrl}/v1/widget/appearance`); this.setAppearance(appearance); await this.bootstrap(); }
      this.messages.replaceChildren(); this.addMessage("assistant",this.welcome);
      if (this.sessionId) {
        const history=await this.request(`/v1/sessions/${this.sessionId}/messages`);
        for (const message of history) this.addMessage(message.role,message.content,message.citations||[]);
      }
      this.ready=true;
    } catch(error) { this.messages.replaceChildren(); this.addMessage("assistant",this.failureMessage(error)); this.ready=false; }
    finally { this.setBusy(false); }
  }
  async ensureSession() {
    if (this.sessionId) return this.sessionId;
    if (!this.legacy) { await this.bootstrap(); return this.sessionId; }
    if (!this.assistantId) throw new Error("Atendimento ainda não configurado.");
    const session=await this.request("/v1/sessions",{method:"POST",body:JSON.stringify({assistant_id:this.assistantId})});
    this.sessionId=session.id; return this.sessionId;
  }
  async submit(event) {
    event.preventDefault(); const content=this.input.value.trim(); if (!content || this.busy) return;
    this.setBusy(true); this.showError("");
    this.addMessage("user",content); const pending=this.addTyping();
    try {
      const session=await this.ensureSession();
      const result=await this.request(`/v1/sessions/${session}/messages`,{method:"POST",body:JSON.stringify({content})});
      pending.remove(); this.addMessage("assistant",result.assistant_message.content,result.citations||[]); this.input.value=""; this.input.style.height="auto";
    } catch(error) { pending.remove(); this.addMessage("assistant",this.failureMessage(error)); this.input.value=""; }
    finally { this.setBusy(false); this.input.focus(); }
  }
  addMessage(role,content,citations=[]) {
    const row=document.createElement("div"); row.className=`row ${role === "user" ? "user" : "assistant"}`;
    const bubble=document.createElement("div"); bubble.className="bubble";
    const paragraph=document.createElement("p"); paragraph.textContent=content; bubble.append(paragraph);
    if (citations.length) {
      const sources=document.createElement("details"); sources.className="sources"; const label=document.createElement("summary"); label.textContent="Ver fontes"; sources.append(label);
      for (const citation of citations.slice(0,4)) {
        const item=document.createElement("details"), summary=document.createElement("summary"); summary.textContent=citation.title; item.append(summary);
        const excerpt=document.createElement("p"); excerpt.textContent=citation.excerpt||""; item.append(excerpt);
        if (citation.url && /^https?:\/\//i.test(citation.url)) { const link=document.createElement("a"); link.href=citation.url; link.target="_blank"; link.rel="noopener noreferrer"; link.textContent="Abrir documento original"; item.append(link); }
        sources.append(item);
      }
      bubble.append(sources);
    }
    row.append(bubble); this.messages.append(row); this.messages.scrollTop=this.messages.scrollHeight; return row;
  }
  addTyping() { const row=document.createElement("div"); row.className="row assistant"; row.innerHTML='<div class="bubble"><span class="typing" aria-label="Consultando documentos"><i></i><i></i><i></i></span></div>'; this.messages.append(row); this.messages.scrollTop=this.messages.scrollHeight; return row; }
  failureMessage(error) { return error.status === 503 ? error.message : this.unavailableMessage; }
  showError(message) { this.status.textContent=message; this.status.classList.toggle("visible",Boolean(message)); }
  setBusy(value) { this.busy=value; this.input.disabled=value; this.sendButton.disabled=value; const reset=this.shadowRoot.querySelector(".restart"); if(reset) reset.disabled=value; }
  toggle(open) {
    this.panel.classList.toggle("open",open); this.panel.setAttribute("aria-hidden",String(!open)); this.panel.inert=!open; this.launcher.setAttribute("aria-expanded",String(open));
    if(open) { if(!this.ready) void this.start(); setTimeout(()=>this.shadowRoot.querySelector(".close").focus(),50); } else this.launcher.focus();
  }
}
if(!customElements.get("chatbot-platform")) customElements.define("chatbot-platform",ChatbotPlatform);
