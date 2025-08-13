<template>
  <!-- Chat interface -->
  <main>
    <div class="chat-container">
      <div class="row" v-for="message in messages" :key="message.id">
        <div class="space" v-if="message.role == 'user'"></div>
        <div :class="['message', message.role]" v-if="message.role !== 'system'">
          <div v-for="(item, index) in message.content" :key="index">
            <p v-if="item.type === 'text' && message.role === 'user'">
              {{ item.text }}
            </p>
            <div v-else-if="item.type === 'text' && message.role === 'assistant'" v-html="renderMarkdown(item.text)"></div>
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
          @keydown.enter.prevent="
                sendMessage()
          "
        />
        <n-button
          :loading="isLoading"
          type="primary"
          size="large"
          @click="sendMessage"
          style="height: 90px"
          :disabled="userInput.trim() === ''"
          >Send</n-button
        >
      </n-input-group>
    </div>
  </main>
</template>

<script setup lang="ts">
import { nextTick, ref, onMounted } from 'vue'

// Server configuration
const SERVER_URL = "http://localhost:5000"

// Define message type
interface Message {
  id: number
  role: 'user' | 'assistant' | 'system'
  content: Array<{
    type: 'text'
    text: string
  }>
}

// Reactive variables
const userInput = ref('')
const messages = ref<Message[]>([])
const sessionId = ref<string | null>(null)

// Loading state
const isLoading = ref(false)

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
          // Add the assistant's reply to the chat
          messages.value.push({
            id: Date.now() + 1,
            role: 'assistant',
            content: [
              {
                type: 'text',
                text: data.response
              }
            ]
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
      font-size: 1.1em;
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
</style>
