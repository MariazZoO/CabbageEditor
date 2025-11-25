<template>
  <div class="relative min-h-screen w-full bg-gradient-to-br from-gray-50 to-gray-100" tabindex="0">
    <!-- 场景栏 -->
    <div class="w-full bg-gradient-to-r from-teal-700 to-green-600 border-b border-teal-800/60 h-13 relative shadow-md">
      <div class="flex items-center space-x-1 px-3 overflow-x-auto scroll-smooth tab-container">
        <div
            v-for="(tab, index) in tabs"
            :key="index"
            class="px-5 py-2.5 cursor-pointer rounded-t-lg flex items-center gap-2 transition-all duration-200 ease-in-out"
            :class="{
            'bg-white/90 border-b-2 border-teal-500 shadow-sm': activeTab === index,
            'hover:bg-white/20 text-white/90': activeTab !== index,
            'text-gray-800': activeTab === index
          }"
            @click="switchTab(index)"
            @dblclick="openSceneBar(index)">
          <span
              class="max-w-[140px] truncate px-2 py-1 select-none font-medium"
          >
            {{ tab.name }}
          </span>

          <button
              v-if="tabs.length > 1"
              @click.stop="closeTab(index)"
              class="hover:bg-gray-300/50 rounded-full p-1 transition-colors duration-200 hover:text-red-500"
              aria-label="关闭标签"
          >
            ×
          </button>
        </div>

        <button
            @click="addNewTab"
            class="px-4 py-2.5 text-xl font-bold hover:bg-white/20 rounded-lg transition-all duration-200 text-white hover:scale-105"
            aria-label="添加新标签"
        >
          +
        </button>
      </div>
    </div>
    <!-- 自定义弹窗 -->
    <div
        v-if="showDialog"
        class="fixed top-0 left-0 w-full h-full flex items-center justify-center bg-black/50 backdrop-blur-sm transition-opacity duration-300"
    >
      <div class="bg-white rounded-lg shadow-xl w-96 transform transition-all duration-300 ease-out scale-100">
        <div class="p-6">
          <div>
            <label
                for="new-tab-name"
                class="block text-sm font-medium text-gray-700 mb-2"
            >
              添加场景
            </label>
            <input
                id="new-tab-name"
                v-model="inputState.newTabName"
                type="text"
                class="mt-1 px-3 py-2 bg-gray-50 border border-gray-300 rounded-md w-full focus:ring-2 focus:ring-teal-500 focus:border-transparent transition-colors duration-200 outline-none"
                ref="nameInput"
                @keyup.enter="confirmAddTab"
                autofocus
                placeholder="输入场景名称"
            />
          </div>
          <div class="flex justify-end gap-3 mt-5">
            <button
                @click="cancelAddTab"
                class="px-4 py-2 text-gray-600 bg-gray-100 rounded-md hover:bg-gray-200 transition-colors
                    duration-200 focus:ring-2 focus:ring-teal-500 focus:ring-offset-2"
            >
              取消
            </button>
            <button
                @click="confirmAddTab"
                class="px-4 py-2 text-white bg-teal-600 rounded-md hover:bg-teal-700 transition-colors
                    duration-200 shadow-sm hover:shadow-md focus:ring-2 focus:ring-teal-500 focus:ring-offset-2"
            >
              创建场景
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import {ref, onMounted, onUnmounted, reactive, watch, nextTick} from 'vue';
import {useRouter} from 'vue-router';

async function waitWebChannel() {
  if (window.appService || window.sceneService) return true;
  if (window.webChannelReady) { try { await window.webChannelReady; } catch {} }
  return !!(window.appService || window.sceneService);
}

const router = useRouter();

const goToHome = () => {
  router.push('/');
};

const activeTab = ref(0);  // 当前激活的标签页

const cameraState = ref({
  position: [0.0, 5.0, 10.0],
  forward: [0.0, 1.5, 0.0],
  up: [0.0, -1.0, 0.0],
  fov: 45.0
});

// 标签页数据
const tabs = ref([
  {name: '场景1', id: 'MainScene'},
]);

// 添加新标签页
const showDialog = ref(false);
const inputState = reactive({
  newTabName: '',
});

watch(showDialog, (newVal) => {
  if (newVal) {
    nextTick(() => {
      const input = document.getElementById('new-tab-name');
      if (input) {
        input.select();
      }
    });
  }
});

const addNewTab = () => {
  const sceneNumbers = tabs.value
      .map(tab => {
        const match = tab.name.match(/^场景(\d+)$/);
        return match ? parseInt(match[1]) : null
      })
      .filter(num => num !== null);

  const maxSceneNumber = sceneNumbers.length > 0
      ? Math.max(...sceneNumbers)
      : 0;

  inputState.newTabName = `场景${maxSceneNumber + 1}`;
  showDialog.value = true;
};

const confirmAddTab = () => {
  if (inputState.newTabName.trim()) {
    const maxSceneNumber = tabs.value.reduce((max, tab) => {
      const match = tab.name.match(/场景(\d+)/);
      return match ? Math.max(max, parseInt(match[1])) : max;
    }, 0);
    // 生成新场景名称
    const newTabName = `场景${maxSceneNumber + 1}`;
    const finalName = inputState.newTabName.trim() || newTabName;
    // 添加新标签页
    tabs.value.push({
      name: finalName,
      id: `scene${Date.now()}`,
      editing: false,
    });

    activeTab.value = tabs.value.length - 1;
    showDialog.value = false;
    inputState.newTabName = '';
  } else {
    alert('请输入标签名称');
  }
};

// 清空输入框
const cancelAddTab = () => {
  showDialog.value = false;
  inputState.newTabName = '';
};

const handleWheel = (event) => {
  const direction = event.deltaY > 0 ? 'backward' : 'forward';
  handleCameraMove(direction);
};

const handleKeyDown = (event) => {
  // 检查输入框是否聚焦
  const inputElement = document.getElementById('new-tab-name');
  if (inputElement && inputElement === document.activeElement) {
    return;
  }

  event.preventDefault();
  switch (event.key.toLowerCase()) {
    case 'w':
      handleCameraMove('up');
      break;
    case 's':
      handleCameraMove('down');
      break;
    case 'a':
      handleCameraMove('left');
      break;
    case 'd':
      handleCameraMove('right');
      break;
    case 'q':
      handleCameraMove('rotateLeft');
      break;
    case 'e':
      handleCameraMove('rotateRight');
      break;
  }
};

const handleCameraMove = (direction) => {
  const speed = 0.2;
  const {position, forward} = cameraState.value;

  switch (direction) {
    case 'up':
      position[1] += speed;
      break;
    case 'down':
      position[1] -= speed;
      break;
    case 'left':
      position[0] -= speed;
      break;
    case 'right':
      position[0] += speed;
      break;
    case 'forward':
      position[2] -= speed;
      break;
    case 'backward':
      position[2] += speed;
      break;
    case 'rotateRight':
      const angleLeft = Math.PI / 180;
      const [x, z] = forward;
      forward[0] = x * Math.cos(angleLeft) - z * Math.sin(angleLeft);
      forward[2] = x * Math.sin(angleLeft) + z * Math.cos(angleLeft);
      break;
    case 'rotateLeft':
      const angleRight = -Math.PI / 180;
      const [x2, z2] = forward;
      forward[0] = x2 * Math.cos(angleRight) - z2 * Math.sin(angleRight);
      forward[2] = x2 * Math.sin(angleRight) + z2 * Math.cos(angleRight);
      break;
  }

  const payload = JSON.stringify({
    sceneName: tabs.value[activeTab.value]?.id || 'MainScene',
    position: [...position],
    forward: [...forward],
    up: [...cameraState.value.up],
    fov: cameraState.value.fov
  });
  if (window.sceneService && typeof window.sceneService.camera_move === 'function') {
    window.sceneService.camera_move(payload);
  }
};

// 关闭标签页
const closeTab = (index) => {
  if (tabs.value.length > 1) {
    tabs.value.splice(index, 1);
    if (activeTab.value >= index) {
      activeTab.value = Math.max(0, activeTab.value - 1);
    }
  }
};

// 切换标签页
const switchTab = (index) => {
  activeTab.value = index;
};

const handleReturnToWelcome = () => {
  router.push('/');
};

// 控制包菜精显示
const cabbagetalk = async () => {
  const size = {width: 160, height: 160};
  await waitWebChannel();
  if (window.appService && typeof window.appService.add_dock_widget === 'function') {
    window.appService.add_dock_widget("Pet", "/Pet", "float", "bottom_right", JSON.stringify(size));
  }
};

const openSceneBar = async (index) => {
  await waitWebChannel();
  const sceneName = tabs.value[index]?.id || 'MainScene';
  const routePath = `/SceneBar?sceneName=${sceneName}`;
  if (window.appService && typeof window.appService.add_dock_widget === 'function') {
    window.appService.add_dock_widget("SceneBar", routePath, "left", "None", JSON.stringify({width: 520, height: 640}));
  }
};

const createScene = async () => {
  await waitWebChannel();
  const payload = JSON.stringify({sceneName: tabs.value[activeTab.value]?.id || 'MainScene'});
  if (window.sceneService && typeof window.sceneService.create_scene === 'function') {
    window.sceneService.create_scene(payload);
  }
};

onMounted(async () => {
  await waitWebChannel();
  await createScene();
  await cabbagetalk();
  document.addEventListener('keydown', handleKeyDown);
});

onUnmounted(() => {
  document.removeEventListener('keydown', handleKeyDown);
});
</script>