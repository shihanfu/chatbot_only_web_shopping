<template>
  <!-- Chat interface -->
  <main>
    <n-button @click="showModal = true" style="width: 300px" v-if="!persona"
      >Select Persona</n-button
    >
    <n-button @click="showModal = true" style="width: 300px" v-else
      >Selected Persona: {{ persona }}</n-button
    >
    <div class="chat-container">
      <div class="row" v-for="message in messages" :key="message.id">
        <div class="space" v-if="message.role == 'user'"></div>
        <div :class="['message', message.role]">
          <!-- Loop through message content array -->
          <n-input
            type="textarea"
            style="width: 100%"
            v-if="message.role === 'system'"
            v-model:value="message.content[0].text"
          />
          <div v-else v-for="(item, index) in message.content" :key="index">
            <p v-if="item.type === 'text'">
              {{ item.text }}
            </p>
            <img
              v-else-if="item.type === 'image'"
              :src="'data:' + item.source.media_type + ';base64,' + item.source.data"
              alt="Uploaded Image"
            />
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
          :disabled="!persona"
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
          :disabled="userInput.trim() === ''"
          >Send</n-button
        >
      </n-input-group>
    </div>

    <n-modal v-model:show="showModal">
      <n-card
        style="width: 600px"
        title="Select Persona"
        :bordered="false"
        size="huge"
        role="dialog"
        aria-modal="true"
      >
        <div class="row" style="height: 500px">
          <div
            style="
              flex-basis: 165px;
              flex-grow: 0;
              flex-shrink: 0;
              height: 100%;
              display: flex;
              flex-direction: column;
            "
          >
            <div>
              <n-input v-model:value="persona_search" placeholder="Search" />
            </div>
            <!-- <div style="flex: 1; overflow-y: auto" class="persona-list"> -->
            <!-- <div
                v-for="p in Object.keys(all_personas).filter(
                  (p) => p.includes(persona_search) || persona_search === ''
                )"
                :key="p"
                style="width: 100%"
              >
                <n-button @click="persona = p" style="width: 100%">{{ p }}</n-button>
              </div> -->
            <n-virtual-list
              style="flex: 1; overflow-y: auto"
              class="persona-list"
              :item-size="34"
              key-field="value"
              :items="
                Object.keys(all_personas)
                  .filter((p) => p.includes(persona_search) || persona_search === '')
                  .sort((a, b) => {
                    // virtual customer 1, virtual customer 10, ...
                    const a_num = parseInt(a.split(' ')[2])
                    const b_num = parseInt(b.split(' ')[2])
                    return a_num - b_num
                  })
                  .map((p) => ({
                    value: p
                  }))
              "
            >
              <template #default="{ item }">
                <div :key="'persona' + item.value" class="item" style="height: 34px">
                  <n-button
                    :type="persona === item.value ? 'primary' : 'default'"
                    @click="persona = item.value"
                    style="width: 100%"
                    >{{ item.value }}</n-button
                  >
                </div>
              </template>
            </n-virtual-list>
          </div>
          <div style="flex: 1; overflow-y: auto">
            <!-- {{ all_personas[persona] }}
               -->
            <n-code v-if="persona" :code="all_personas[persona]" word-wrap />
            <n-empty
              style="height: 100%; display: flex; justify-content: center; align-items: center"
              description="Select a persona to continue"
              v-else
            />
          </div>
        </div>
        <template #footer>
          <n-button @click="showModal = false" type="primary" :disabled="!persona"
            >Confirm</n-button
          >
        </template>
      </n-card>
    </n-modal>
  </main>
</template>

<script setup lang="ts">
import { nextTick, ref, onMounted, watch } from 'vue'
import { api_url } from './config'

// 127.0.0.1:5001/api/persona
const all_personas = ref({})
onMounted(async () => {
  const response = await fetch(api_url + '/api/persona')
  all_personas.value = (await response.json()).personas
})

const persona = ref('')
const memory_trace = ref('')
watch(persona, async () => {
  // 127.0.0.1:5001/api/persona/virtual%20customer%200/memory_trace
  const response = await fetch(api_url + `/api/persona/${persona.value}/memory_trace`)
  memory_trace.value = (await response.json()).memory_trace
  console.log(memory_trace.value)
})
const showModal = ref(true)
const persona_search = ref('')
// Hardcoded system prompt
const systemPrompt =
  ref(`You are a participant who just participated in a user study. <Your persona> is given below.  In the study, you were tested to interact with a version of the website design of an online shopping platform like Amazon.com. You used the website for <Your intent>. <Your memory trace> is also given below, which contains your <observation>, your <thought>, your <reasoning/reflection>, and your <actions>.  Now you are interviewed by the website designer to talk about your user experience and feedback on the website design. You will answer based on <your persona> and <Your memory trace>.

<style>: You should talk using a verbal dialog style. Not too long conversation utterances. Leave room for dialog.  No formal structure no formal language. No written language style. No bullet point. Keep it short. If you have multiple points to make, bring only the top one or two in a conversation way.

<Your persona>: {persona}

<Your memory trace>: {memory_trace} `)
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

    const copy_of_messages = JSON.parse(JSON.stringify(messages.value))
    // copy_of_messages[0].content[0].text
    // replace {persona} with persona.value
    copy_of_messages[0].content[0].text = copy_of_messages[0].content[0].text.replace(
      '{persona}',
      all_personas.value[persona.value]
    )
    copy_of_messages[0].content[0].text = copy_of_messages[0].content[0].text.replace(
      '{memory_trace}',
      memory_trace.value
    )

    // Clear the input
    userInput.value = ''

    // Set loading state
    isLoading.value = true

    try {
      // Make the API call to the backend
      const response = await fetch(api_url + '/api/bedrock', {
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
.persona-list {
  overflow-y: auto;
  .n-button {
    width: 100%;
    border-radius: 0;
  }
}
</style>
