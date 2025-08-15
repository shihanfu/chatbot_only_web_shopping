<template>
  <!-- Chat interface -->
  <main>
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
        <div v-if="isLoading" class="message assistant">
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
          @keydown.enter.prevent="sendMessage()"
        />
        <n-button
          :loading="isLoading"
          type="primary"
          size="large"
          @click="sendMessage"
          style="height: 90px"
          :disabled="userInput.trim() === ''"
        >Send</n-button>
      </n-input-group>
    </div>
  </main>
</template>

<script setup lang="ts">
import { nextTick, ref, onMounted } from 'vue'

// Server configuration
const SERVER_URL = "http://localhost:5000"

// Product Card JSON Schema Types
interface ProductItem {
  name: string
  url: string
  image: string
  price: string
  rating: number
  review_count: number
  reason: string
}

interface ProductCardJSON {
  type: 'product_card'
  version: '1.0'
  data: ProductItem[]
}

// Message Item Types
type MessageItem = 
  | { type: 'text'; text: string }
  | { type: 'card'; card: ProductCardJSON }

// Define message type
interface Message {
  id: number
  role: 'user' | 'assistant' | 'system'
  content: MessageItem[]
}

// Reactive variables
const userInput = ref('')
const messages = ref<Message[]>([])
const sessionId = ref<string | null>(null)

// Loading state
const isLoading = ref(true)

// Product Card validation function
const validateProductCard = (obj: any): obj is ProductCardJSON => {
  if (!obj || typeof obj !== 'object') return false
  if (obj.type !== 'product_card') return false
  if (obj.version !== '1.0') return false
  if (!Array.isArray(obj.data)) return false
  
  return obj.data.every((item: any) => {
    if (!item || typeof item !== 'object') return false
    if (typeof item.name !== 'string') return false
    if (typeof item.url !== 'string') return false
    if (typeof item.image !== 'string') return false
    if (typeof item.price !== 'string') return false
    if (typeof item.rating !== 'number' || item.rating < 0 || item.rating > 5) return false
    if (typeof item.review_count !== 'number' || item.review_count < 0 || !Number.isInteger(item.review_count)) return false
    if (typeof item.reason !== 'string') return false
    return true
  })
}

// Parse JSON safely
const safeJsonParse = (text: string): any => {
  try {
    return JSON.parse(text)
  } catch {
    return null
  }
}

// Extract content from fenced code blocks
const extractFencedContent = (text: string): string | null => {
  const jsonMatch = text.match(/```json\s*([\s\S]*?)\s*```/)
  if (jsonMatch) return jsonMatch[1].trim()
  
  const productCardMatch = text.match(/```product_card\s*([\s\S]*?)\s*```/)
  if (productCardMatch) return productCardMatch[1].trim()
  
  return null
}

// Find JSON object boundaries (from '{' to matching '}')
const findJsonBoundaries = (text: string, startIndex: number): { start: number; end: number } | null => {
  if (text[startIndex] !== '{') return null
  
  let braceCount = 0
  let inString = false
  let escapeNext = false
  
  for (let i = startIndex; i < text.length; i++) {
    const char = text[i]
    
    if (escapeNext) {
      escapeNext = false
      continue
    }
    
    if (char === '\\') {
      escapeNext = true
      continue
    }
    
    if (char === '"' && !escapeNext) {
      inString = !inString
      continue
    }
    
    if (!inString) {
      if (char === '{') {
        braceCount++
      } else if (char === '}') {
        braceCount--
        if (braceCount === 0) {
          return { start: startIndex, end: i + 1 }
        }
      }
    }
  }
  
  return null
}

// Message content parser - splits text into text and card fragments
const parseMessageContent = (text: string): MessageItem[] => {
  const fragments: MessageItem[] = []
  let currentIndex = 0
  
  while (currentIndex < text.length) {
    // Try to find fenced code blocks first
    const fencedMatch = text.slice(currentIndex).match(/```(?:json|product_card)\s*([\s\S]*?)\s*```/)
    
    if (fencedMatch) {
      const matchStart = currentIndex + fencedMatch.index!
      const matchEnd = matchStart + fencedMatch[0].length
      
      // Add text before the fenced block
      if (matchStart > currentIndex) {
        const textBefore = text.slice(currentIndex, matchStart)
        if (textBefore.trim()) {
          fragments.push({ type: 'text', text: textBefore })
        }
      }
      
      // Try to parse the fenced content
      const fencedContent = extractFencedContent(fencedMatch[0])
      if (fencedContent) {
        const parsed = safeJsonParse(fencedContent)
        if (parsed && validateProductCard(parsed)) {
          fragments.push({ type: 'card', card: parsed })
        } else {
          fragments.push({ type: 'text', text: fencedMatch[0] })
        }
      } else {
        fragments.push({ type: 'text', text: fencedMatch[0] })
      }
      
      currentIndex = matchEnd
    } else {
      // Look for bare JSON objects
      const jsonStart = text.indexOf('{', currentIndex)
      
      if (jsonStart === -1) {
        // No more JSON objects, add remaining text
        const remainingText = text.slice(currentIndex)
        if (remainingText.trim()) {
          fragments.push({ type: 'text', text: remainingText })
        }
        break
      }
      
      // Add text before JSON
      if (jsonStart > currentIndex) {
        const textBefore = text.slice(currentIndex, jsonStart)
        if (textBefore.trim()) {
          fragments.push({ type: 'text', text: textBefore })
        }
      }
      
      // Try to parse JSON object
      const boundaries = findJsonBoundaries(text, jsonStart)
      if (boundaries) {
        const jsonText = text.slice(boundaries.start, boundaries.end)
        const parsed = safeJsonParse(jsonText)
        
        if (parsed && validateProductCard(parsed)) {
          fragments.push({ type: 'card', card: parsed })
        } else {
          fragments.push({ type: 'text', text: jsonText })
        }
        
        currentIndex = boundaries.end
      } else {
        // Invalid JSON, treat as text
        fragments.push({ type: 'text', text: text[jsonStart] })
        currentIndex = jsonStart + 1
      }
    }
  }
  
  return fragments
}

// Format review count (e.g., 2500 -> 2.5k)
const formatReviewCount = (count: number): string => {
  if (count >= 1000) {
    return (count / 1000).toFixed(1).replace(/\.0$/, '') + 'k'
  }
  return count.toString()
}

// Handle image loading errors
const handleImageError = (event: Event) => {
  const img = event.target as HTMLImageElement
  img.src = 'data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMTAwIiBoZWlnaHQ9IjEwMCIgdmlld0JveD0iMCAwIDEwMCAxMDAiIGZpbGw9Im5vbmUiIHhtbG5zPSJodHRwOi8vd3d3LnczLm9yZy8yMDAwL3N2ZyI+CjxyZWN0IHdpZHRoPSIxMDAiIGhlaWdodD0iMTAwIiBmaWxsPSIjRjVGNUY1Ii8+CjxwYXRoIGQ9Ik0zMCAzMEg3MFY3MEgzMFYzMFoiIGZpbGw9IiNEN0Q3RDciLz4KPHBhdGggZD0iTTM1IDM1TDUwIDUwTDUwIDM1TDM1IDM1WiIgZmlsbD0iI0E5QTlBOSIvPgo8L3N2Zz4K'
}

// Simple markdown renderer
const renderMarkdown = (text: string): string => {
  return text
    .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>') // Bold
    .replace(/\*(.*?)\*/g, '<em>$1</em>') // Italic
    .replace(/`(.*?)`/g, '<code>$1</code>') // Inline code
    .replace(/```([\s\S]*?)```/g, '<pre><code>$1</code></pre>') // Code blocks
    .replace(/^### (.*$)/gim, '<h3>$1</h3>') // H3 headers
    .replace(/^## (.*$)/gim, '<h2>$1</h2>') // H2 headers
    .replace(/^# (.*$)/gim, '<h1>$1</h1>') // H1 headers
    .replace(/^- (.*$)/gim, '<li>$1</li>') // List items
    .replace(/\n/g, '<br>') // Line breaks
}

// Create session on component mount
onMounted(async () => {
  await createSession()
})

// Create a new session
const createSession = async () => {
  try {
    const response = await fetch(`${SERVER_URL}/create-session`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
    })
    if (response.status === 200) {
      const data = await response.json()
      sessionId.value = data.session_id
      console.log(`✅ Session created: ${sessionId.value}`)
      isLoading.value = false
    } else {
      console.error(`❌ Failed to create session: ${response.text}`)
    }
  } catch (error) {
    console.error('Error creating session:', error)
  }
}

// Send message
const sendMessage = async () => {
  if (userInput.value.trim() !== '' && sessionId.value) {
    // Add the user's message to the chat
    messages.value.push({
      id: Date.now(),
      role: 'user',
      content: [
        {
          type: 'text',
          text: userInput.value.trim()
        }
      ]
    })

    // Scroll to bottom
    nextTick(() => {
      const chatContainer = document.querySelector('.chat-container')
      if (chatContainer) {
        chatContainer.scrollTo({
          top: chatContainer.scrollHeight,
          behavior: 'smooth'
        })
      }
    })

    const messageText = userInput.value.trim()
    
    // Clear the input
    userInput.value = ''

    // Set loading state
    isLoading.value = true

    try {
      // Make the API call to the backend
      const response = await fetch(`${SERVER_URL}/chat`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          session_id: sessionId.value,
          message: messageText
        })
      })

      if (response.status === 200) {
        const data = await response.json()
        
        if (data.success) {
          // Parse the assistant's response into fragments
          const contentFragments = parseMessageContent(data.response)
          
          // Add the assistant's reply to the chat
          messages.value.push({
            id: Date.now() + 1,
            role: 'assistant',
            content: contentFragments
          })
        } else {
          console.error('API returned success: false')
        }
        
        // Scroll to bottom
        nextTick(() => {
          const chatContainer = document.querySelector('.chat-container')
          if (chatContainer) {
            chatContainer.scrollTo({
              top: chatContainer.scrollHeight,
              behavior: 'smooth'
            })
          }
        })
      } else {
        console.error(`❌ Failed to send message: ${response.text}`)
      }
    } catch (error) {
      console.error('Error:', error)
    } finally {
      isLoading.value = false
    }
  }
}

/*
// Test examples for the parser:
// Example 1: "这是推荐：```json\n{...合法 product_card ...}\n```\n以上是理由说明。"
// Should result in: [text, card, text]

// Example 2: "先看这个{...非法JSON...}，再看```product_card\n{...合法 product_card ...}\n```"
// Should result in: [text, text, card]
*/
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
  border: 1px solid var(--color-border);
  padding: 15px;
  overflow-y: auto;
  min-height: 0;
  margin: 20px 0;
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
    background-color: rgb(225, 255, 204);
  }

  &.assistant {
    background-color: rgb(207, 247, 255);
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
  flex-shrink: 0;
  width: 120px;
  height: 120px;
  align-self: center;   

  @media (max-width: 768px) {
    width: 40%;
    height: auto;
  }
  
  img {
    width: 100%;
    height: auto;
    object-fit: contain;
    display: block;
  }
}

.pc-card-content {
  flex: 1;
  padding: 12px;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
}

.pc-product-title {
  margin: 0 0 8px 0;
  font-size: 12px;
  font-weight: 600;
  
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
