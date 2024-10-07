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
          @keydown.meta.enter.prevent="sendMessage"
        />
        <n-button
          :loading="isLoading"
          type="primary"
          size="large"
          @click="sendMessage"
          style="height: 90px"
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

<Your persona>: Persona: Ethan

Background:
Ethan is a 22-year-old recent college graduate who has been struggling to find stable employment since completing his degree in Sociology. He is passionate about social justice and community work, aiming to make a difference in society but currently finds himself in a challenging economic situation.

Demographics:
- Age: 22
- Gender: Male
- Education: Bachelor’s degree in Sociology
- Profession: Unemployed
- Income: $0

Financial Situation:
Ethan lives with his parents to save on living expenses while he searches for a job. He relies on their support for basic necessities and is actively seeking entry-level opportunities in non-profit organizations and community outreach programs. He is also exploring internships to gain experience, even if they are unpaid.

Shopping Habits:
Ethan’s financial constraints force him to be extremely budget-conscious. He avoids non-essential purchases and focuses on buying only what he needs. He often shops at thrift stores or relies on community programs for clothing and supplies. When necessary, he uses online resources for second-hand products.

Professional Life:
Ethan spends much of his time networking, volunteering, and applying for jobs. He is actively involved in local community projects and internships to build experience and connections in the social work field. He also attends workshops and webinars to improve his skills and enhance his employability.

Personal Style:
Ethan favors a casual and practical style, often opting for comfortable clothing that suits his active lifestyle. He prefers neutral colors with occasional pops of brightness. His wardrobe mainly consists of budget-friendly basics, and he values durability and functionality over fashion trends.

Lifestyle:
Ethan wakes up early, around 7 am, to make the most of his day. He enjoys spending time with friends and participating in community service. He is passionate about social issues and often engages in discussions about activism and change. He is a resident of Chicago and is determined to secure a fulfilling job that aligns with his values.
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
      const response = await fetch('http://127.0.0.1:5001/api/openai', {
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
