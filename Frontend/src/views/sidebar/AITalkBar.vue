<template>
  <div class="min-h-screen border-2 border-[#84a65b] relative">
    <DockTitleBar title="助手" extraClass="bg-[#84A65B]" @close="closeFloat"/>
    <!-- 四周拖动边框 -->
    <div class="absolute top-0 left-0 w-full h-2 cursor-n-resize z-40" @mousedown="(e) => startResize(e, 'n')"></div>
    <div class="absolute bottom-0 left-0 w-full h-2 cursor-s-resize z-40" @mousedown="(e) => startResize(e, 's')"></div>
    <div class="absolute top-0 left-0 h-full w-2 cursor-w-resize z-40" @mousedown="(e) => startResize(e, 'w')"></div>
    <div class="absolute top-0 right-0 h-full w-2 cursor-e-resize z-40" @mousedown="(e) => startResize(e, 'e')"></div>
    <div class="absolute top-0 left-0 w-4 h-4 cursor-nw-resize z-40" @mousedown="(e) => startResize(e, 'nw')"></div>
    <div class="absolute top-0 right-0 w-4 h-4 cursor-ne-resize z-40" @mousedown="(e) => startResize(e, 'ne')"></div>
    <div class="absolute bottom-0 left-0 w-4 h-4 cursor-sw-resize z-40" @mousedown="(e) => startResize(e, 'sw')"></div>
    <div class="absolute bottom-0 right-0 w-4 h-4 cursor-se-resize z-40" @mousedown="(e) => startResize(e, 'se')"></div>

    <!-- 主内容区域 -->
    <div class="w-full bg-[#a8a4a3]/65 flex flex-col" style="height: calc(100vh - 48px);">
      <!-- 对话记录区域 -->
      <div ref="chatHistoryRef" class="flex-1 overflow-y-auto p-4">
        <div class="max-w-6xl mx-auto">
          <div class="space-y-2 pr-2">
            <div v-for="(message, index) in messages" :key="index"
                 class="p-3 bg-[#E8E8E8]/80 rounded-lg shadow-sm border border-gray-100 space-y-2"
                 :class="{
                   'opacity-70': message.status === 'sending',
                   'border-red-300 bg-red-50/50': message.status === 'failed'
                 }">
              <div>
                <span :class="{
                  'text-blue-500': message.sender === 'AI',
                  'text-green-500': message.sender === 'User',
                  'text-gray-500': message.sender === '系统'
                }" class="font-medium">
                  {{ message.sender }}:
                </span>
                <span v-if="message.text" class="text-gray-700 break-words whitespace-pre-wrap">{{ message.text }}</span>
                
                <!-- 发送状态指示器 -->
                <span v-if="message.status === 'sending'" class="ml-2 text-xs text-gray-500">
                  <span class="inline-block animate-pulse">发送中...</span>
                </span>
                <span v-if="message.status === 'failed'" class="ml-2 text-xs text-red-500">
                  发送失败
                  <button @click="retryMessage(index)" class="ml-2 px-2 py-0.5 bg-red-500 text-white rounded hover:bg-red-600 text-xs">
                    重试
                  </button>
                </span>
              </div>
              <!-- 单张图片显示 -->
              <div v-if="message.imageData" class="max-w-sm">
                <img :src="message.imageData" :alt="message.imageName || 'image'" class="rounded border cursor-pointer max-h-60 object-contain" @click="openImagePreview(message)"/>
                <div v-if="message.imageName" class="text-xs text-gray-500 mt-1">{{ message.imageName }}</div>
              </div>
              <!-- 多张图片显示 -->
              <div v-if="message.images && message.images.length > 0" class="flex flex-wrap gap-2">
                <div v-for="(img, imgIdx) in message.images" :key="imgIdx" class="max-w-xs">
                  <img :src="img.preview" :alt="img.name" class="rounded border cursor-pointer max-h-40 object-contain" @click="openImagePreview({imageData: img.preview, imageName: img.name})"/>
                  <div class="text-xs text-gray-500 mt-1 truncate">{{ img.name }}</div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- 输入区域 -->
      <div class="bg-[#E8E8E8]/80 border-t border-gray-200 shadow-lg backdrop-blur-sm">
        <div class="max-w-6xl mx-auto p-4">
          <!-- 隐藏图片选择器 -->
          <input ref="imageInputRef" type="file" accept="image/*" class="hidden" @change="onImageChange" />

          <div class="space-y-2">
            <!-- 顶部：导入图片和提示词按钮 -->
            <div class="flex gap-2">
              <button @click="triggerImageSelect('product')" class="px-3 py-2 bg-indigo-500 text-white rounded-lg hover:bg-indigo-600 transition-colors focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:ring-offset-2 whitespace-nowrap">
                导入产品
              </button>
              <button @click="triggerImageSelect('scene')" class="px-3 py-2 bg-green-500 text-white rounded-lg hover:bg-green-600 transition-colors focus:outline-none focus:ring-2 focus:ring-green-500 focus:ring-offset-2 whitespace-nowrap">
                导入场景
              </button>

              <div class="relative" @keydown.escape="hidePrompts">
                <button @click="togglePrompts" class="px-3 py-2 bg-amber-500 text-white rounded-lg hover:bg-amber-600 transition-colors focus:outline-none focus:ring-2 focus:ring-amber-500 focus:ring-offset-2 whitespace-nowrap">
                  提示词
                </button>
                <transition name="fade">
                  <div v-if="showPrompts" class="absolute bottom-full left-0 mb-2 w-64 max-h-72 overflow-y-auto bg-white/95 backdrop-blur border border-gray-200 rounded-lg shadow-lg p-2 space-y-1 z-50">
                    <div class="flex items-center justify-between mb-1">
                      <span class="text-xs text-gray-500">常用提示词</span>
                      <button class="text-xs text-gray-400 hover:text-gray-600" @click="hidePrompts">关闭</button>
                    </div>
                    <template v-for="(p, i) in promptPresets" :key="i">
                      <button @click="applyPrompt(p)" class="w-full text-left text-sm px-2 py-1 rounded hover:bg-amber-100 focus:bg-amber-100 focus:outline-none">
                        {{ p.label }}
                      </button>
                    </template>
                  </div>
                </transition>
              </div>
            </div>

            <!-- 中间：输入框和待发送图片预览 -->
            <div class="bg-white rounded-lg border border-gray-300 p-2 space-y-2">
              <textarea v-model="userInput" placeholder="输入消息..." class="w-full p-2 border-none rounded-lg focus:ring-0 focus:outline-none transition-all resize-none" rows="3"></textarea>

              <div v-if="hasPendingImages" class="space-y-2">
                <div class="flex items-center justify-between">
                  <span class="text-xs text-gray-600">待发送图片</span>
                  <button @click="clearAllImages" class="text-xs text-red-500 hover:text-red-700">清空全部</button>
                </div>
                <div class="flex flex-wrap gap-4">
                  <div v-for="type in imageTypes" :key="type">
                    <div v-if="pendingImages[type]" class="relative group">
                      <img :src="pendingImages[type].preview" :alt="pendingImages[type].name" class="h-20 w-20 object-cover rounded border border-blue-300" />
                      
                      <!-- 上传中遮罩 -->
                      <div v-if="pendingImages[type].uploading" class="absolute inset-0 bg-black/50 rounded flex items-center justify-center">
                        <svg class="animate-spin h-6 w-6 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                          <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                          <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                        </svg>
                      </div>
                      
                      <!-- 移除按钮 -->
                      <button 
                        v-if="!pendingImages[type].uploading"
                        @click="removeImage(type)" 
                        class="absolute -top-1 -right-1 w-5 h-5 bg-red-500 text-white rounded-full text-xs flex items-center justify-center hover:bg-red-600 opacity-0 group-hover:opacity-100 transition-opacity">
                        ×
                      </button>
                      
                      <div class="text-xs text-gray-600 mt-1 w-20 truncate capitalize" :title="pendingImages[type].name">
                        {{ imageTypeLabels[type] }}
                        <span v-if="pendingImages[type].uploading" class="text-blue-500">上传中</span>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            <!-- 底部：发送按钮 -->
            <div class="flex justify-end">
              <button 
                @click="sendMessage" 
                :disabled="isSending"
                class="px-5 py-2 bg-blue-500 text-white rounded-lg transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 whitespace-nowrap"
                :class="{
                  'hover:bg-blue-600': !isSending,
                  'opacity-50 cursor-not-allowed': isSending
                }">
                <span v-if="!isSending">发送</span>
                <span v-else class="flex items-center gap-2">
                  <svg class="animate-spin h-4 w-4" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                    <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                    <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                  </svg>
                  发送中...
                </span>
              </button>
            </div>

            <div v-if="imageError" class="text-xs text-red-500">{{ imageError }}</div>
          </div>
        </div>
      </div>

      <!-- 简单图片预览遮罩 -->
      <div v-if="imagePreview" class="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-[100]" @click.self="imagePreview = null">
        <div class="bg-white p-4 rounded shadow max-w-[90vw] max-h-[90vh] flex flex-col">
          <img :src="imagePreview.imageData" :alt="imagePreview.imageName" class="object-contain max-w-full max-h-[70vh]" />
          <div class="mt-2 flex justify-between items-center text-sm text-gray-600">
            <span>{{ imagePreview.imageName }}</span>
            <button class="px-3 py-1 bg-gray-800 text-white rounded hover:bg-gray-700" @click="imagePreview = null">关闭</button>
          </div>
        </div>
      </div>
    </div>

  </div>
</template>

<script setup>
import {ref, onMounted, onUnmounted, computed, nextTick} from 'vue';
import {useDragResize} from '@/components/ui/DragTitleBar.js';
import DockTitleBar from '@/components/ui/DockTitleBar.vue';

const {dragState, startResize, stopDrag, onDrag, stopResize, onResize} = useDragResize();

const messages = ref([
  {sender: "AI", text: "你好！我是 AI。", status: 'success'},
]);
const userInput = ref('');
const chatHistoryRef = ref(null);
const sessionId = ref(null);
const isSending = ref(false); // 发送状态
const sendTimeout = ref(null); // 发送超时定时器
const MESSAGE_TIMEOUT = 30000; // 30秒超时

// 图片相关
const imageInputRef = ref(null);
const imageError = ref('');
const imagePreview = ref(null); // {imageData, imageName}
const imageTypes = ['product', 'scene'];
const currentImageType = ref(null); // 'product' | 'scene'
const pendingImages = ref({
  product: null,
  scene: null,
});

const imageTypeLabels = {
  product: '产品',
  scene: '场景',
};

const hasPendingImages = computed(() => {
  return Object.values(pendingImages.value).some(img => img !== null);
});

const uploadResolvers = new Map();

// 提示词相关
const showPrompts = ref(false);
const promptPresets = ref([
  {label: '总结以上内容', text: '请总结以上对话的要点。'},
  {label: '解释代码', text: '请详细解释下面这段代码的作用及时间复杂度:\n'},
  {label: '生成测试用例', text: '请为下面的函数编写单元测试（使用pytest）:\n'},
  {label: '优化提示', text: '请审查我的提示词并给出更明确、更可执行的改进建议：\n'},
  {label: '翻译为英文', text: '请将下面的内容准确翻译成英文：\n'},
  {label: '改写更专业', text: '请将下面的文本改写得更专业、清晰且结构良好：\n'}
]);

function togglePrompts() { showPrompts.value = !showPrompts.value; }
function hidePrompts() { showPrompts.value = false; }
function applyPrompt(p) {
  userInput.value = p.text;
  hidePrompts();
}

function createToken() {
  if (window.crypto?.randomUUID) {
    return window.crypto.randomUUID();
  }
  return `${Date.now().toString(36)}-${Math.random().toString(16).slice(2)}`;
}

async function uploadImageToBackend({type, name, data}) {
  const token = createToken();
  const payload = {
    token,
    type,
    name,
    data,
    session_id: sessionId.value,
  };
  const promise = new Promise((resolve, reject) => {
    uploadResolvers.set(token, {resolve, reject});
  });
  await waitWebChannel();
  if (window.aiService && typeof window.aiService.upload_image === 'function') {
    window.aiService.upload_image(JSON.stringify(payload));
  } else if (window.pyBridge && typeof window.pyBridge.upload_image === 'function') {
    window.pyBridge.upload_image(JSON.stringify(payload));
  } else {
    uploadResolvers.delete(token);
    throw new Error("未发现图片上传通道 (aiService/pyBridge)");
  }
  return promise;
}

function triggerImageSelect(type) {
  imageError.value = '';
  currentImageType.value = type;
  imageInputRef.value && imageInputRef.value.click();
}

function openImagePreview(message) {
  imagePreview.value = {imageData: message.imageData, imageName: message.imageName};
}

function removeImage(type) {
  if (pendingImages.value[type]) {
    pendingImages.value[type] = null;
  }
}

function clearAllImages() {
  pendingImages.value.product = null;
  pendingImages.value.scene = null;
}

async function fileToBase64(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(reader.result);
    reader.onerror = reject;
    reader.readAsDataURL(file);
  });
}

async function onImageChange(e) {
  const file = e.target.files[0];
  if (!file) return;
  imageError.value = '';

  if (file.size > 20 * 1024 * 1024) {
    imageError.value = `图片 ${file.name} 大小超过 20MB。`;
    e.target.value = '';
    return;
  }

  if (!currentImageType.value) {
    console.error('图片类型未指定');
    e.target.value = '';
    return;
  }

  try {
    const base64 = await fileToBase64(file);
    const type = currentImageType.value;
    
    // 只在前端预览，不立即上传
    pendingImages.value[type] = {
      name: file.name,
      preview: base64,
      type,
      url: null,
      uploading: false,
      needsUpload: true, // 标记需要上传
    };
    
    imageError.value = '';
  } catch (err) {
    console.error('读取图片失败', err);
    imageError.value = err?.message || '读取图片失败，请重试。';
    if (currentImageType.value) {
      pendingImages.value[currentImageType.value] = null;
    }
  } finally {
    e.target.value = '';
    currentImageType.value = null; // 重置
  }
}

async function waitWebChannel() {
  if (window.aiService || window.appService) return true;
  if (window.webChannelReady) {
    try {
      await window.webChannelReady;
    } catch {
    }
  }
  return !!(window.aiService || window.appService);
}

const SendMessageToAI = async (query, extra = {}) => {
  await waitWebChannel();
  const payloadObj = {message: query, session_id: sessionId.value, ...extra};
  const payload = JSON.stringify(payloadObj);
  
  // 返回 Promise 以便调用者处理结果
  return new Promise((resolve, reject) => {
    try {
      if (window.aiService && typeof window.aiService.send_message_to_ai === 'function') {
        window.aiService.send_message_to_ai(payload);
        resolve(); // WebChannel 是单向通信，假设发送成功
      } else {
        const error = new Error("未发现 AI 通道 (aiService/pyBridge)");
        console.error(error.message);
        reject(error);
      }
    } catch (error) {
      console.error("发送消息失败:", error);
      reject(error);
    }
  });
};

const sendMessage = async () => {
  const text = userInput.value.trim();
  const imagesToSend = imageTypes
    .map(type => pendingImages.value[type])
    .filter(img => img !== null);

  // 至少要有文字或图片之一
  if (!text && imagesToSend.length === 0) return;
  
  // 防止重复发送
  if (isSending.value) return;

  // 检查是否有正在上传的图片
  const uploadingImage = imagesToSend.find(img => img.uploading);
  if (uploadingImage) {
    imageError.value = `请等待 ${imageTypeLabels[uploadingImage.type]} 图片上传完成`;
    return;
  }

  // 上传所有需要上传的图片
  try {
    for (const img of imagesToSend) {
      if (img.needsUpload && !img.url) {
        // 标记为上传中
        img.uploading = true;
        imageError.value = `正在上传 ${imageTypeLabels[img.type]} 图片...`;
        
        const result = await uploadImageToBackend({
          type: img.type,
          name: img.name,
          data: img.preview
        });
        
        const url = result?.image?.url;
        if (!url) {
          throw new Error(result?.content || '上传失败');
        }
        
        // 更新图片信息
        img.url = url;
        img.uploading = false;
        img.needsUpload = false;
      }
    }
    imageError.value = '';
  } catch (err) {
    console.error('上传图片失败:', err);
    imageError.value = err?.message || '上传图片失败，请重试。';
    // 重置上传状态
    imagesToSend.forEach(img => {
      if (img.uploading) {
        img.uploading = false;
      }
    });
    return;
  }

  // 保存当前输入以备回滚
  const savedInput = text;
  const savedImages = [...imagesToSend];

  const messageObj = {sender: "User", status: 'sending'};
  let displayText = text || '';

  if (imagesToSend.length > 0) {
    // 如果没有文字，显示简单的图片标记
    if (!displayText) {
      displayText = imagesToSend.length === 1 
        ? '[1张图片]' 
        : `[${imagesToSend.length}张图片]`;
    }
    // 如果有文字，不额外添加文件名列表，因为会显示图片缩略图

    if (imagesToSend.length === 1) {
      messageObj.imageData = imagesToSend[0].preview;
      messageObj.imageName = imagesToSend[0].name;
    } else {
      messageObj.images = imagesToSend.map(img => ({preview: img.preview, name: img.name}));
    }
  }

  messageObj.text = displayText;
  messageObj.originalText = savedInput; // 保存原始输入
  messageObj.originalImages = savedImages; // 保存原始图片
  
  const messageIndex = messages.value.length;
  messages.value.push(messageObj);

  // 清空输入
  userInput.value = '';
  clearAllImages();
  imageError.value = '';
  isSending.value = true;

  nextTick(() => {
    const chatHistory = chatHistoryRef.value;
    if (chatHistory) {
      chatHistory.scrollTop = chatHistory.scrollHeight;
    }
  });

  const extra = {session_id: sessionId.value};
  if (imagesToSend.length > 0) {
    extra.images = imagesToSend.map(img => ({
      name: img.name,
      url: img.url,
      type: img.type,
    }));
  }

  // 设置超时
  sendTimeout.value = setTimeout(() => {
    if (messages.value[messageIndex]?.status === 'sending') {
      messages.value[messageIndex].status = 'failed';
      messages.value[messageIndex].error = '发送超时';
      isSending.value = false;
      messages.value.push({
        sender: '系统',
        text: '消息发送超时，请检查网络连接或重试。',
        status: 'error'
      });
    }
  }, MESSAGE_TIMEOUT);

  try {
    await SendMessageToAI(text || '[图片]', extra);
    // WebChannel 是单向的，我们假设发送成功
    // 实际的成功会在 receiveAIMessage 中确认
    messages.value[messageIndex].status = 'sent';
  } catch (error) {
    console.error('发送消息失败:', error);
    messages.value[messageIndex].status = 'failed';
    messages.value[messageIndex].error = error.message || '发送失败';
    
    // 显示错误提示
    messages.value.push({
      sender: '系统',
      text: `消息发送失败: ${error.message || '未知错误'}`,
      status: 'error'
    });
  } finally {
    if (sendTimeout.value) {
      clearTimeout(sendTimeout.value);
      sendTimeout.value = null;
    }
    isSending.value = false;
  }
};

// 重试发送失败的消息
const retryMessage = async (index) => {
  const message = messages.value[index];
  if (!message || message.status !== 'failed') return;

  // 恢复输入
  userInput.value = message.originalText || '';
  
  // 恢复图片
  if (message.originalImages && message.originalImages.length > 0) {
    message.originalImages.forEach(img => {
      if (img.type && imageTypes.includes(img.type)) {
        pendingImages.value[img.type] = img;
      }
    });
  }

  // 删除失败的消息
  messages.value.splice(index, 1);
};

window.receiveAIMessage = (data) => {
  try {
    let message = data;
    if (typeof data === 'string') {
      try {
        message = JSON.parse(data);
      } catch {
        message = {content: data};
      }
    }

    if (message.session_id) {
      sessionId.value = message.session_id;
    }

    if (message.type === 'image_upload') {
      const handler = message.token ? uploadResolvers.get(message.token) : null;
      if (handler) {
        uploadResolvers.delete(message.token);
        if (message.status === 'success') {
          handler.resolve(message);
        } else {
          handler.reject(new Error(message.content || '上传失败'));
        }
      }
      return;
    }

    // 收到 AI 回复时，将最后一条"发送中"的用户消息标记为成功
    const lastUserMessage = messages.value.slice().reverse().find(m => m.sender === 'User');
    if (lastUserMessage && (lastUserMessage.status === 'sending' || lastUserMessage.status === 'sent')) {
      lastUserMessage.status = 'success';
    }

    if (message.type === 'error') {
      console.error('AI处理错误:', message.content);
      // 将用户消息标记为失败
      if (lastUserMessage) {
        lastUserMessage.status = 'failed';
        lastUserMessage.error = message.content;
      }
    }

    // 如果返回包含 image_base64 也展示图片
    const msgObj = {
      sender: "AI",
      text: message.content || message.text || (message.type === 'image' ? '[图片]' : JSON.stringify(message)),
      status: 'success'
    };
    if (message.image_base64) {
      msgObj.imageData = message.image_base64;
      msgObj.imageName = message.image_name || 'image';
    }
    messages.value.push(msgObj);

    // 滚动到底部
    nextTick(() => {
      const chatHistory = chatHistoryRef.value;
      if (chatHistory) {
        chatHistory.scrollTop = chatHistory.scrollHeight;
      }
    });
  } catch (e) {
    console.error('处理AI消息失败:', e);
    messages.value.push({
      sender: "系统",
      text: `无法处理AI响应: ${typeof data === 'string' ? data : JSON.stringify(data)}`,
      status: 'error'
    });
  }
};

//关闭浮动窗口
const closeFloat = async () => {
  await waitWebChannel();
  if (window.appService && typeof window.appService.remove_dock_widget === 'function') {
    window.appService.remove_dock_widget("AITalkBar");
  } else if (window.pyBridge && typeof window.pyBridge.remove_dock_widget === 'function') {
    window.pyBridge.remove_dock_widget("AITalkBar");
  } else {
    console.error("未发现 Dock 控制通道 (appService/pyBridge)");
  }
};

const handleResizeMove = (e) => {
  if (dragState.value.isResizing) onResize(e);
};

const handleResizeUp = () => {
  if (dragState.value.isResizing) stopResize();
};

const handleDockEvent = (eventType, eventData) => {
  if (eventType === 'jsonData') {
    try {
      const data = JSON.parse(eventData);
      console.error(data['content'])
    } catch (error) {
      console.error('处理Dock事件失败:', error);
    }
  }
}

onMounted(async () => {
  await waitWebChannel();
  document.addEventListener('mousemove', handleResizeMove);
  document.addEventListener('mouseup', handleResizeUp);
  document.addEventListener('mousemove', onDrag);
  document.addEventListener('mouseup', stopDrag);
  document.addEventListener('mousemove', onResize);
  document.addEventListener('mouseup', stopResize);
  if (window.pyBridge && window.pyBridge.dock_event) {
    try {
      window.pyBridge.dock_event.connect(handleDockEvent);
    } catch {
    }
  }
  // 点击外部关闭提示词面板
  document.addEventListener('click', handleGlobalClick, true);
});

function handleGlobalClick(e) {
  // 如果点击不在提示词区域且不是按钮
  if (!showPrompts.value) return;
  const pop = document.querySelector('.prompt-popover-flag');
  if (pop && !pop.contains(e.target)) {
    // 通过 ref/ class 控制更精准，这里简单判断
    // 但我们已添加捕获监听, 若为按钮也会触发, 用 closest 判断
    const target = e.target;
    if (!target.closest || !target.closest('.prompt-popover-exclude')) {
      hidePrompts();
    }
  }
}

onUnmounted(() => {
  document.removeEventListener('mousemove', handleResizeMove);
  document.removeEventListener('mouseup', handleResizeUp);
  document.removeEventListener('mousemove', onDrag);
  document.removeEventListener('mouseup', stopDrag);
  document.removeEventListener('mousemove', onResize);
  document.removeEventListener('mouseup', stopResize);
  if (window.pyBridge && window.pyBridge.dock_event) {
    try {
      window.pyBridge.dock_event.disconnect(handleDockEvent);
    } catch {
    }
  }
  document.removeEventListener('click', handleGlobalClick, true);
  uploadResolvers.clear();
  
  // 清理超时定时器
  if (sendTimeout.value) {
    clearTimeout(sendTimeout.value);
    sendTimeout.value = null;
  }
});
</script>

<style scoped>
/* 可选过渡 */
.fade-enter-active, .fade-leave-active { transition: opacity .15s ease; }
.fade-enter-from, .fade-leave-to { opacity: 0; }
</style>
