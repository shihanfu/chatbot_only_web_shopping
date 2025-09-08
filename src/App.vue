<template>
  <!-- Chat interface -->
  <main>
    <div class="toolbar" style="display:flex; gap:8px; justify-content:flex-end;">
      <n-button size="small" tertiary @click="reloadFromServer" :disabled="!sessionId || isLoading">Reload</n-button>
      <n-button size="small" tertiary @click="clearChat" :disabled="isLoading">Clear Chat</n-button>
    </div>
    <div class="chat-container">
      <div class="row" v-for="message in messages" :key="message.id">
        <div class="space" v-if="message.role == 'user'"></div>
        <div :class="['message', message.role]" v-if="message.role !== 'system'">
          <div v-for="(item, index) in message.content" :key="index">
            <!-- User messages: always text -->
            <p v-if="item.type === 'text' && message.role === 'user'">
              {{ item.text }}
            </p>
            <!-- Assistant messages: text or card -->
            <div v-else-if="item.type === 'text' && message.role === 'assistant'" v-html="renderMarkdown(item.text)"></div>
            <div v-else-if="item.type === 'card' && message.role === 'assistant'" class="pc-card-container">
              <div v-for="(product, productIndex) in item.card.data" :key="productIndex" class="pc-product-card">
                <div class="pc-card-image">
                  <img :src="product.image" :alt="product.name" @error="handleImageError" />
                </div>
                <div class="pc-card-content">
                  <h3 class="pc-product-title">
                    <a :href="product.url" target="_top" rel="noopener noreferrer">
                      {{ product.name }}
                    </a>
                  </h3>
                  <div class="pc-price">{{ product.price }}</div>
                  <div class="pc-rating-section">
                    <div class="pc-stars">
                      <div class="pc-stars-filled" :style="{ width: (product.rating / 5 * 100) + '%' }"></div>
                    </div>
                    <span class="pc-rating-text">{{ product.rating.toFixed(1) }}</span>
                    <span class="pc-review-count">({{ formatReviewCount(product.review_count) }})</span>
                  </div>
                  <p class="pc-reason">{{ product.reason }}</p>
                </div>
              </div>
            </div>
          </div>
        </div>
        <div class="space" v-if="message.role == 'assistant'"></div>
      </div>
      <!-- Loading indicator -->
      <div class="row">
        <div v-if="isAssistantTyping" class="message assistant">
          <p>Assistant is typing...</p>
        </div>
        <div class="space"></div>
      </div>
    </div>
    <div class="input-container">
      <n-input-group>
        <n-input
          size="large"
          v-model:value="userInput"
          placeholder="Type your message..."
          type="textarea"
          style="height: 50px; --n-caret-color: rgb(0, 122, 255); --n-border-hover: 1px solid rgb(0, 122, 255); --n-border-focus: 1px solid rgb(0, 122, 255);"
          @keydown.enter.prevent="sendMessage()"
        />
        <n-button
          :loading="isLoading"
          type="primary"
          size="large"
          @click="sendMessage"
          style="height: 50px; --n-color: rgb(0, 122, 255); --n-color-hover: rgb(0, 100, 220); --n-color-pressed: rgb(0, 80, 180); --n-color-focus: rgb(0, 100, 220); --n-color-disabled: rgb(0, 122, 255); --n-ripple-color: rgb(0, 122, 255); --n-border: 1px solid rgb(0, 122, 255); --n-border-hover: 1px solid rgb(0, 100, 220); --n-border-pressed: 1px solid rgb(0, 80, 180); --n-border-focus: 1px solid rgb(0, 100, 220); --n-border-disabled: 1px solid rgb(0, 122, 255);"
          :disabled="userInput.trim() === '' || isLoading"
        >Send</n-button>
      </n-input-group>
    </div>
  </main>
</template>

<script setup lang="ts">
import { nextTick, ref, onMounted, onUnmounted } from 'vue'

// const SERVER_URL = "http://localhost:5000"
// const SERVER_URL = "http://52.91.223.130:5000"
const SERVER_URL = "/api"

// ============ ★ 本地存储 Key ============
const LS_KEYS = {
  sessionId: 'CSA_SESSION_ID',
  parentUrl: 'CSA_PARENT_URL'
} as const

// === 父页 URL 逻辑（保留你的实现） ===
const currentUrl = ref<string | null>(localStorage.getItem(LS_KEYS.parentUrl))
let resolveParentUrlReady!: () => void
const parentUrlReady = new Promise<void>((res) => (resolveParentUrlReady = res))
function getUrlForSend(): string | null {
  return currentUrl.value || (window as any).__CSA_PARENT_URL__ || localStorage.getItem(LS_KEYS.parentUrl)
}

// ========= 类型定义（保持你原来的） =========
interface ProductItem {
  name: string; url: string; image: string; price: string;
  rating: number; review_count: number; reason: string
}
interface ProductCardJSON { type: 'product_card'; version: '1.0'; data: ProductItem[] }
type MessageItem = { type:'text'; text:string } | { type:'card'; card: ProductCardJSON }
interface Message { id: number; role: 'user' | 'assistant' | 'system'; content: MessageItem[] }

// ========= 状态 =========
const userInput = ref('')
const messages = ref<Message[]>([])
const sessionId = ref<string | null>(null)
const isLoading = ref(true)
const isAssistantTyping = ref(false)

// ========= 工具函数（保留你原来的） =========
const validateProductCard = (obj: any): obj is ProductCardJSON => {
  if (!obj || typeof obj !== 'object') return false
  if (obj.type !== 'product_card') return false
  if (obj.version !== '1.0') return false
  if (!Array.isArray(obj.data)) return false
  return obj.data.every((item: any) =>
    item && typeof item === 'object' &&
    typeof item.name === 'string' &&
    typeof item.url === 'string' &&
    typeof item.image === 'string' &&
    typeof item.price === 'string' &&
    typeof item.rating === 'number' && item.rating >= 0 && item.rating <= 5 &&
    typeof item.review_count === 'number' && item.review_count >= 0 && Number.isInteger(item.review_count) &&
    typeof item.reason === 'string'
  )
}
const safeJsonParse = (t: string): any => { try { return JSON.parse(t) } catch { return null } }
const extractFencedContent = (text: string): string | null => {
  const m1 = text.match(/```json\s*([\s\S]*?)\s*```/); if (m1) return m1[1].trim()
  const m2 = text.match(/```product_card\s*([\s\S]*?)\s*```/); if (m2) return m2[1].trim()
  return null
}
const findJsonBoundaries = (text: string, start: number): { start: number; end: number } | null => {
  if (text[start] !== '{') return null
  let brace = 0, inStr = false, esc = false
  for (let i = start; i < text.length; i++) {
    const ch = text[i]
    if (esc) { esc = false; continue }
    if (ch === '\\') { esc = true; continue }
    if (ch === '"' && !esc) { inStr = !inStr; continue }
    if (!inStr) {
      if (ch === '{') brace++
      else if (ch === '}') {
        brace--
        if (brace === 0) return { start, end: i + 1 }
      }
    }
  }
  return null
}
const parseMessageContent = (text: string): MessageItem[] => {
  const frags: MessageItem[] = []
  let idx = 0
  while (idx < text.length) {
    const fenced = text.slice(idx).match(/```(?:json|product_card)\s*([\s\S]*?)\s*```/)
    if (fenced) {
      const start = idx + (fenced.index ?? 0)
      const end = start + fenced[0].length
      if (start > idx) {
        const before = text.slice(idx, start)
        if (before.trim()) frags.push({ type: 'text', text: before })
      }
      const body = extractFencedContent(fenced[0])
      if (body) {
        const parsed = safeJsonParse(body)
        if (parsed && validateProductCard(parsed)) frags.push({ type: 'card', card: parsed })
        else frags.push({ type: 'text', text: fenced[0] })
      } else {
        frags.push({ type: 'text', text: fenced[0] })
      }
      idx = end
    } else {
      const jsStart = text.indexOf('{', idx)
      if (jsStart === -1) {
        const rest = text.slice(idx)
        if (rest.trim()) frags.push({ type: 'text', text: rest })
        break
      }
      if (jsStart > idx) {
        const before = text.slice(idx, jsStart)
        if (before.trim()) frags.push({ type: 'text', text: before })
      }
      const bounds = findJsonBoundaries(text, jsStart)
      if (bounds) {
        const jtxt = text.slice(bounds.start, bounds.end)
        const parsed = safeJsonParse(jtxt)
        if (parsed && validateProductCard(parsed)) frags.push({ type: 'card', card: parsed })
        else frags.push({ type: 'text', text: jtxt })
        idx = bounds.end
      } else {
        frags.push({ type: 'text', text: text[jsStart] })
        idx = jsStart + 1
      }
    }
  }
  return frags
}
const formatReviewCount = (n: number) => n >= 1000 ? (n / 1000).toFixed(1).replace(/\.0$/, '') + 'k' : String(n)
const handleImageError = (e: Event) => {
  (e.target as HTMLImageElement).src =
    'data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMTAwIiBoZWlnaHQ9IjEwMCIgdmlld0JveD0iMCAwIDEwMCAxMDAiIGZpbGw9Im5vbmUiIHhtbG5zPSJodHRwOi8vd3d3LnczLm9yZy8yMDAwL3N2ZyI+PHJlY3Qgd2lkdGg9IjEwMCIgaGVpZ2h0PSIxMDAiIGZpbGw9IiNGNUY1RjUiLz48cGF0aCBkPSJNMzAgMzBINzBWNzBIMzBWMzBaIiBmaWxsPSIjRDdEN0Q3Ii8+PHBhdGggZD0iTTM1IDM1TDUwIDUwTDUwIDM1TDM1IDM1WiIgZmlsbD0iI0E5QTlBOSIvPjwvc3ZnPg=='
}
const renderMarkdown = (t: string): string =>
  t.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
   .replace(/\*(.*?)\*/g, '<em>$1</em>')
   .replace(/`(.*?)`/g, '<code>$1</code>')
   .replace(/```([\s\S]*?)```/g, '<pre><code>$1</code></pre>')
   .replace(/^### (.*$)/gim, '<h3>$1</h3>')
   .replace(/^## (.*$)/gim, '<h2>$1</h2>')
   .replace(/^# (.*$)/gim, '<h1>$1</h1>')
   .replace(/^- (.*$)/gim, '<li>$1</li>')
   .replace(/\n/g, '<br>')

// ========= 父页 URL 监听 =========
const handleParentMessage = (event: MessageEvent) => {
  if (event.data?.type === 'PARENT_URL') {
    const url: string = event.data.url
    console.log('[IFRAME] got parent url:', url)
    currentUrl.value = url
    ;(window as any).__CSA_PARENT_URL__ = url
    localStorage.setItem(LS_KEYS.parentUrl, url)
    resolveParentUrlReady?.()
  }
}
onMounted(() => window.addEventListener('message', handleParentMessage))
onUnmounted(() => window.removeEventListener('message', handleParentMessage))

// ========= 核心：初始化 & 历史拉取 =========
onMounted(async () => {
  await initSessionAndLoadHistory()
})

async function initSessionAndLoadHistory() {
  isLoading.value = true
  try {
    // 1) 先看看本地有没有 session_id
    const saved = localStorage.getItem(LS_KEYS.sessionId)
    if (saved) {
      sessionId.value = saved
      const ok = await reloadFromServer()
      if (ok) {
        console.log('✅ Restored session from localStorage:', saved)
        isLoading.value = false
        return
      }
      // 本地 session 失效了，走新会话
      console.warn('⚠️ Saved session invalid, creating new session…')
    }

    // 2) 创建新会话
    await createSession()
    // 3) 新会话自然没有历史，这里不必拉；如果后端创建时已有历史，也可再调一次：
    // await reloadFromServer()
  } catch (e) {
    console.error('init/load error:', e)
  } finally {
    isLoading.value = false
  }
}

// 创建会话（会把 id 存到 localStorage）
async function createSession() {
  const resp = await fetch(`${SERVER_URL}/create-session`, { method: 'POST', headers: { 'Content-Type': 'application/json' } })
  if (!resp.ok) {
    console.error(`❌ Failed to create session: ${await resp.text()}`)
    return
  }
  const data = await resp.json()
  sessionId.value = data.session_id
  localStorage.setItem(LS_KEYS.sessionId, data.session_id) // ★ 持久化
  console.log(`✅ Session created: ${sessionId.value}`)
}

async function reloadFromServer(): Promise<boolean> {
  if (!sessionId.value) return false
  try {
    const resp = await fetch(`${SERVER_URL}/sessions/${sessionId.value}/messages`, { method: 'GET' })
    if (!resp.ok) {
      console.warn('load history failed:', resp.status)
      return false // ← 404 时返回 false，触发上层走新会话
    }
    // ... 保持你原逻辑
    const data = await resp.json()
    if (!data.success || !Array.isArray(data.messages)) return false

    // 把后端的 {role, text} 转为前端的 Message[]
    const flat = data.messages as Array<{ role: string; text: string; createdAt?: string }>
    const mapped: Message[] = flat
      .filter(m => m.role === 'user' || m.role === 'assistant' || m.role === 'system')
      .map((m, idx) => {
        const role = m.role as Message['role']
        const id = Date.now() + idx
        if (role === 'assistant') {
          return { id, role, content: parseMessageContent(m.text ?? '') }
        }
        // user / system 都当纯文本块
        return { id, role, content: [{ type: 'text', text: m.text ?? '' }] }
      })

    messages.value = mapped
    // 滚动到底
    nextTick(() => {
      const el = document.querySelector('.chat-container')
      el?.scrollTo({ top: el.scrollHeight, behavior: 'auto' })
    })
    return true
  } catch (e) {
    console.error('reloadFromServer error:', e)
    return false
  }
}

async function sendMessage() {
  if (userInput.value.trim() === '') return

  // ★ 没有 session 时兜底自动建一个
  if (!sessionId.value) {
    await createSession()
    if (!sessionId.value) {
      console.error('❌ No session available')
      return
    }
  }

  const messageText = userInput.value.trim()
  messages.value.push({ id: Date.now(), role: 'user', content: [{ type: 'text', text: messageText }] })
  userInput.value = ''
  nextTick(() => document.querySelector('.chat-container')?.scrollTo({ top: 9e9, behavior: 'smooth' }))

  isLoading.value = true
  isAssistantTyping.value = true

  const doPost = async () => {
    // Get parent url
    await Promise.race([parentUrlReady, new Promise(r => setTimeout(r, 1500))])
    const urlForSend = getUrlForSend()
    console.log('[IFRAME] /chat current_url =', urlForSend)
    
    return fetch(`${SERVER_URL}/chat`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ session_id: sessionId.value, message: messageText, current_url: urlForSend || null })
    })
  }

  try {
    let resp = await doPost()

    // ★ 如果 404，说明旧会话无效：重建并重试一次
    if (resp.status === 404) {
      console.warn('⚠️ /chat 404, recreating session and retrying…')
      sessionId.value = null
      localStorage.removeItem(LS_KEYS.sessionId)
      await createSession()
      if (!sessionId.value) throw new Error('recreate session failed')
      resp = await doPost()
    }

    if (!resp.ok) {
      console.error(`❌ Failed to send message: ${await resp.text()}`)
      return
    }
    const data = await resp.json()
    if (data.success) {
      const fragments = parseMessageContent(data.response ?? '')
      messages.value.push({ id: Date.now() + 1, role: 'assistant', content: fragments })
      nextTick(() => document.querySelector('.chat-container')?.scrollTo({ top: 9e9, behavior: 'smooth' }))
    } else {
      console.error('API returned success: false')
    }
  } catch (e) {
    console.error('sendMessage error:', e)
  } finally {
    isLoading.value = false
    isAssistantTyping.value = false
  }
}

// ========= 清空聊天（前端视角新建会话） =========
async function clearChat() {
  if (!sessionId.value) return
  try {
    isLoading.value = true
    const resp = await fetch(`${SERVER_URL}/cleanup-session`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ session_id: sessionId.value })
    })
    const data = await resp.json()
    if (resp.ok && data.success) {
      console.log('✅ Chat cleared:', data.message)

      // 1) 前端视图清空
      messages.value = []

      // 2) 本地 session 置空并清掉 LS
      sessionId.value = null
      localStorage.removeItem(LS_KEYS.sessionId)

      // 3) 立刻新建一个全新的 session（避免后续 /chat 404）
      await createSession()

      // （可选）提示一条系统消息
      messages.value.push({
        id: Date.now(),
        role: 'system',
        content: [{ type: 'text', text: 'Started a new session.' }]
      })
    } else {
      console.error('❌ Failed to cleanup session:', data.error || resp.status)
    }
  } catch (e) {
    console.error('clearChat error:', e)
  } finally {
    isLoading.value = false
  }
}
</script>

<style scoped lang="scss">
/* No styles here, styles are in main.css and base.css */
.row {
  display: flex;
  flex-direction: row;
}
.space {
  flex-grow: 1;
  flex-shrink: 1;
}
.message {
  flex-shrink: 0;
  max-width: 100%;
}
.message:has(.n-input) {
  width: 100%;
}

/* Chat styles */
.chat-container {
  flex: 1;
  padding: 10px;
  overflow-y: auto;
  min-height: 0;
  margin: 10px 0;
  background-color: #f9f9f9;
  border-radius: 8px;
}

.message {
  margin-bottom: 15px;
  padding: 10px;
  border-radius: 5px;
  color: var(--color-text); // Ensure text color is set

  p {
    margin: 0;
  }

  &.system {
    background-color: #e9ecef;
    color: #333333;
  }

  &.user {
    background-color: rgb(0, 122, 255);
    font-weight: bold;
    color: white;
  }

  &.assistant {
    background-color: rgb(225, 225, 225);
    text-align: left;
    
    // Markdown styling
    strong {
      font-weight: bold;
    }
    
    em {
      font-style: italic;
    }
    
    code {
      background-color: rgba(0, 0, 0, 0.1);
      padding: 2px 4px;
      border-radius: 3px;
      font-family: monospace;
    }
    
    pre {
      background-color: rgba(0, 0, 0, 0.05);
      padding: 10px;
      border-radius: 5px;
      overflow-x: auto;
      
      code {
        background-color: transparent;
        padding: 0;
      }
    }
    
    h1, h2, h3 {
      margin: 10px 0 5px 0;
      font-weight: bold;
    }
    
    h1 {
      font-size: 1.5em;
    }
    
    h2 {
      font-size: 1.3em;
    }
    
    h3 {
      font-size: 1 em;
    }
    
    li {
      margin: 2px 0;
      padding-left: 10px;
    }
  }
}

.input-container {
  display: flex;
  gap: 10px;
  margin-top: 10px;
  align-items: center;
}

/* Product Card Styles */
.pc-card-container {
  margin: 10px 0;
}

.pc-product-card {
  display: flex;
  background: white;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  margin-bottom: 12px;
  overflow: hidden;
  transition: box-shadow 0.2s ease;
  
  &:hover {
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
  }
  
  @media (max-width: 768px) {
    flex-direction: row;
  }
}

.pc-card-image {
  flex: 0 0 40%;   /* 左边图片占 40% */
  max-width: 40%;
  
  img {
    width: 100%;
    height: auto;
    object-fit: contain;
    display: block;
  }
}

.pc-card-content {
  flex: 0 0 60%;   /* 右边文字占 60% */
  max-width: 60%;
  padding: 8px;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
}

.pc-product-title {
  margin: 0 0 8px 0;
  font-size: 14px;
  font-weight: 600;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
  text-overflow: ellipsis;
  
  a {
    color: #2563eb;
    text-decoration: none;
    
    &:hover {
      text-decoration: underline;
    }
  }
}

.pc-price {
  font-size: 18px;
  font-weight: 700;
  color: #059669;
  margin-bottom: 8px;
}

.pc-rating-section {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
}

.pc-stars {
  position: relative;
  width: 80px;
  height: 16px;
  background: #e5e7eb;
  border-radius: 2px;
  overflow: hidden;
}

.pc-stars-filled {
  position: absolute;
  top: 0;
  left: 0;
  height: 100%;
  background: #fbbf24;
  border-radius: 2px;
  transition: width 0.3s ease;
}

.pc-rating-text {
  font-weight: 600;
  color: #374151;
  font-size: 12px;
}

.pc-review-count {
  color: #6b7280;
  font-size: 12px;
}

.pc-reason {
  margin: 0;
  color: #4b5563;
  font-size: 12px;
  line-height: 1.4;
}
</style>
