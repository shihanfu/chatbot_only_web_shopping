<template>
  <!-- Chat interface -->
  <main>
    <n-upload :max="1" :custom-request="handleFileUpload">
      <n-button>Select Memory Trace File</n-button>
    </n-upload>
    <div class="chat-container">
      <div v-for="message in messages" :key="message.id" :class="['message', message.role]">
        <!-- Loop through message content array -->
        <n-input
          type="textarea"
          v-if="message.role === 'system'"
          v-model:value="message.content[0].text"
        />
        <div v-else v-for="(item, index) in message.content" :key="index">
          <p v-if="item.type === 'text'">{{ item.text }}</p>
          <img
            v-else-if="item.type === 'image'"
            :src="'data:' + item.source.media_type + ';base64,' + item.source.data"
            alt="Uploaded Image"
          />
        </div>
      </div>
      <!-- Loading indicator -->
      <div v-if="isLoading" class="message assistant">
        <p>Assistant is typing...</p>
      </div>
    </div>
    <n-upload
      directory-dnd
      ref="uploadRef"
      multiple
      :max="5"
      list-type="image-card"
      @change="handleImageChange"
    >
    </n-upload>
    <div class="input-container">
      <n-input-group>
        <n-input
          size="large"
          v-model:value="userInput"
          placeholder="Type your message..."
          :loading="isLoading"
          type="textarea"
          @keydown.ctrl.enter.prevent="sendMessage"
        />
        <n-button
          :loading="isLoading"
          type="primary"
          size="large"
          @click="sendMessage"
          style="height: 150px"
          >Send</n-button
        >
      </n-input-group>
    </div>
  </main>
</template>

<script setup lang="ts">
import { nextTick, Ref, ref } from 'vue'

// Hardcoded system prompt
const systemPrompt =
  ref(`You are a participant who just participated in a user study. <Your persona> is given below.  In the study, you were tested to interact with a version of the website design of an online shopping platform like Amazon.com. You used the website and purchased a jacket on it. <Your memory trace> is also given below, which contains your <observation>, your <thought>, your <reasoning/reflection>, and your <actions>.  Now you are interviewed by the website designer to talk about your user experience and feedback on the website design. You will answer based on <your persona> and <Your memory trace>.

<style>: You should talk using a verbal dialog style. Not too long conversation utterances. Leave room for dialog.  No formal structure no formal language. No written language style. No bullet point. Keep it short. If you have multiple points to make, bring only the top one or two in a conversation way.

<Your persona>: Clara Background: Clara is a PhD student in Computer Science at a prestigious university. She is deeply engaged in research focusing on artificial intelligence and machine learning, aiming to contribute to advancements in technology that can benefit society. Demographics: Age: 28 Gender: Female Education: Pursuing a PhD in Computer Science Clara loves United Airlines, and usually wake up at 9am everyday. Clara lives in Boston. Financial Situation: Clara lives on her stipend as a PhD student and is careful with her spending. She prefers to save money for research-related expenses and invest in her academic pursuits. Shopping Habits: Clara dislikes shopping and avoids spending much time browsing through products. She prefers straightforward, efficient shopping experiences and often shops online for convenience. When she does shop, she looks for practicality and affordability over style or trendiness. So Clara want to shop QUICKLY and EFFICIENTLY. Professional Life: Clara spends most of her time in academia, attending conferences, working in the lab, and writing papers. Her commitment to her research is her main priority, and she manages her time around her academic responsibilities. Personal Style: Clara prefers comfortable, functional clothing, often choosing items that are easy to wear for long hours spent at her desk or in the lab. She wears medium-sized clothing and likes colors that reflect her personality—mostly red, which she finds uplifting and energizing. 

<Your memory trace>: `)
const uploadRef = ref()
// Reactive variables
const userInput = ref('')
const messages = ref([
  {
    id: 0,
    role: 'system',
    content: [
      {
        type: 'text',
        text: systemPrompt
      }
    ]
  }
])
let appendedPrompt = ''
const selectedImages: Ref<File[]> = ref([])

// Loading state
const isLoading = ref(false)

// Handle text file upload
const handleFileUpload = (event: Event) => {
  console.log(event)
  const file = event.file.file
  if (file) {
    const reader = new FileReader()
    reader.onload = (e) => {
      appendedPrompt = e.target?.result as string
      console.log(appendedPrompt)
    }
    reader.readAsText(file)
  }
}
// interface UploadCustomRequestOptions {
//   file: FileInfo
//   action?: string
//   data?:
//     | Record<string, string>
//     | (({ file }: { file: FileInfo }) => Record<string, string>)
//   withCredentials?: boolean
//   headers?:
//     | Record<string, string>
//     | (({ file }: { file: FileInfo }) => Record<string, string>)
//   onProgress: (e: { percent: number }) => void
//   onFinish: () => void
//   onError: () => void
// }
// Updated handleImageSelection function
const handleImageSelection = async (file) => {
  // console.log(file)
  // file.onFinish()
}

const handleImageChange = async (event) => {
  console.log(event.fileList)
  selectedImages.value = []
  for (const file of event.fileList) {
    // Wait for the file to be read as base64
    const base64Data = await readFileAsDataURL(file.file)
    selectedImages.value.push({
      type: 'image',
      source: {
        type: 'base64',
        media_type: file.type,
        data: base64Data.split(',')[1] // Remove the data URL prefix
      }
    })
  }
  console.log(selectedImages.value.length)
}

// Utility function to read file as Data URL
function readFileAsDataURL(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader()
    reader.onload = () => {
      resolve(reader.result)
    }
    reader.onerror = reject
    reader.readAsDataURL(file)
  })
}

// Send message
const sendMessage = async () => {
  if (userInput.value.trim() !== '' || selectedImages.value.length > 0) {
    // Construct the message content
    const messageContent = []

    if (selectedImages.value.length > 0) {
      messageContent.push(...selectedImages.value)
      // Clear the selected images after adding to the message
      selectedImages.value = []
      uploadRef.value.clear()
    }

    if (userInput.value.trim() !== '') {
      messageContent.push({
        type: 'text',
        text: userInput.value.trim()
      })
    }

    // Add the user's message to the chat
    messages.value.push({
      id: Date.now(),
      role: 'user',
      content: messageContent
    })
    // scroll to bottom
    nextTick(() => {
      document.querySelector('.chat-container').scrollTo({
        top: document.querySelector('.chat-container').scrollHeight,
        behavior: 'smooth'
      })
    })

    const copy_of_messages = messages.value
    copy_of_messages[0].content[0].text += appendedPrompt

    // Clear the input
    userInput.value = ''

    // Set loading state
    isLoading.value = true

    try {
      // Make the API call to the backend
      const response = await fetch('http://127.0.0.1:5000/api/openai', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ messages: copy_of_messages })
      })

      const data = await response.json()

      // Add the assistant's reply to the chat
      messages.value.push({
        id: Date.now() + 1,
        role: 'assistant',
        content: [
          {
            type: 'text',
            text: data.message
          }
        ]
      })
      // scroll to bottom
      nextTick(() => {
        document.querySelector('.chat-container').scrollTo({
          top: document.querySelector('.chat-container').scrollHeight,
          behavior: 'smooth'
        })
      })
    } catch (error) {
      console.error('Error:', error)
    } finally {
      isLoading.value = false
    }
  }
}
</script>

<style scoped>
/* No styles here, styles are in main.css and base.css */
</style>
