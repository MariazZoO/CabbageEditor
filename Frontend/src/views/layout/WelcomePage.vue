<template>
  <div>
    <div tabindex="0" @keydown="handleKeyDown">
      <div class="welcome-container">
        <!-- LOGO -->
        <div class="welcome-logo">
          <img
              src="@/assets/CabbageEngine-LOGO.png"
              alt="Cabbage Engine Logo"
              class="welcome-logo-img"
          />
        </div>
        
        <div class="announcement-container">
          <div class="items-center w-2/3"></div>
          <!-- 公告按钮 -->
          <button
              @click="toggleAnnouncements"
              class="announcement-button">
            <img
                src="@/assets/announcement.png"
                class="announcement-button-img"
                :class="{ 'animate-soft-shake': !showAnnouncements }"
            />
          </button>
          <!-- 公告面板 -->
          <div v-show="showAnnouncements"
               class="announcement-panel"
               :class="{ 'active': showAnnouncements }">
            <div class="relative p-6">
              <p class="text-center text-2xl font-bold text-black mb-4">公告</p>
              <div class="h-64 overflow-y-auto space-y-4">
                <div class="bg-white/5 rounded-lg p-4">
                  <p class="text-black/80">欢迎使用 Cabbage Engine</p>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- 存档面板 -->
        <div class="save-panel-container">
          <div class="save-panel">
            <div class="relative p-6">
              <p class="text-center text-2xl font-bold text-black mb-4">存档</p>
              <div class="h-64 overflow-y-auto space-y-4">
                <template v-if="saves?.length > 0">
                  <div v-for="(save, index) in saves"
                       :key="index"
                       @click="loadSave(save)"
                       class="bg-white/5 rounded-lg p-4 cursor-pointer hover:bg-blue-100">
                    <div class="flex justify-between items-center">
                      <p class="text-black/80 font-medium">{{ save.name }}</p>
                      <p class="text-sm text-gray-600">{{ save.time }}</p>
                    </div>
                  </div>
                </template>
                <div v-else class="text-center text-gray-500">
                  暂无历史存档
                </div>
              </div>
            </div>
          </div>
        </div>

        <!--按钮部分-->
        <div class="button-container">
          <!--开始游戏-->
          <router-link to="/MainPage" class="w-full max-w-xs">
            <button
                @click="removeActors"
                class="welcome-button">
              <p class="button-text">开始创作<br/>Start creating</p>
            </button>
          </router-link>
          <!--继续游戏-->
          <router-link to="/MainPage" class="w-full max-w-xs">
            <button
                @click="removeActors"
                class="welcome-button">
              <p class="button-text">继续创作<br/>Continue creating</p>
            </button>
          </router-link>
          <!--游戏设置-->
          <div class="w-full max-w-xs">
            <button @click="openSetup(scene)"
                    class="welcome-button">
              <p class="button-text">设置<br/>Set up</p>
            </button>
          </div>
          <!--退出游戏-->
          <div class="w-full max-w-xs">
            <button @click="Out"
                    class="welcome-button">
              <p class="button-text">结束<br/>Exit</p>
            </button>
          </div>
        </div>
      </div>
    </div>

    <div class="w-[140px] overflow-hidden">
      <div
          v-for="item in themeArr"
          :key="item.id"
          @click="onItemClick(item)"
          class="flex items-center p-1 cursor-pointer rounded
          hover:bg-zinc-100/60 dark:hover:bg-zinc-800"
      >
        <m-svg-icon
            :name="item.icon"
            class="w-1.5 h-1.5 mr-1"
            fillClass="fill-zinc-900 dark:fill-zinc-300"
        ></m-svg-icon>
        <span class="text-zinc-900 dark:text-zinc-300 text-sm">{{ item.name }}</span>
      </div>
    </div>

  </div>
</template>

<script setup>
import {ref, onMounted, onBeforeUnmount, onUnmounted, provide} from 'vue';
import '@/assets/welcome-page.css'
import {useRouter} from 'vue-router';
// 控制公告显示的状态
const currentScene = ref("mainscene");
const showAnnouncements = ref(false);
const autoCloseTimer = ref(null);
const actorid = ref([]);
const isJumping = ref(false);
const jumpSpeed = ref(0);
const gravity = 0.01;
const router = useRouter();
const saves = ref([])

const toggleAnnouncements = () => {
  showAnnouncements.value = !showAnnouncements.value;

  if (autoCloseTimer.value) {
    clearTimeout(autoCloseTimer.value);
    autoCloseTimer.value = null;
  }
};

const closeAnnouncements = () => {
  showAnnouncements.value = false;
  if (autoCloseTimer.value) {
    clearTimeout(autoCloseTimer.value);
    autoCloseTimer.value = null;
  }
};

onBeforeUnmount(() => {
  if (autoCloseTimer.value) {
    clearTimeout(autoCloseTimer.value);
  }
});

const createActor = () => {
  if (window.pyBridge) {
    window.pyBridge.create_actor(currentScene.value, `./Resource/Cabbage/armadillo.obj`);
    window.pyBridge.create_actor(currentScene.value, `./Resource/Cabbage/Ball.obj`);
  } else {
    console.error("Python SendMessageToDock 未连接！");
  }
}

const handleActorMove = (direction, deltaTime = 16) => {
  const baseSpeed = 0.2;
  const speed = baseSpeed * (deltaTime / 16);

  if (!actorid.value.length) return;

  // 计算移动向量
  let x = 0, y = 0, z = 0;
  switch (direction) {
    case 'forward':
      z = -speed;
      break;
    case 'backward':
      z = speed;
      break;
    case 'left':
      x = -speed;
      break;
    case 'right':
      x = speed;
      break;
    case 'rotateRight':
      // 新增右旋转逻辑
      if (window.pyBridge) {
        window.pyBridge.actor_operation(JSON.stringify({
          Operation: "Rotate",
          sceneName: "mainscene",
          x: 0,
          y: -Math.PI / 36, // 5度旋转
          z: 0,
          actorName: actorid.value[0]
        }));
      }
      return;
    case 'rotateLeft':
      // 新增左旋转逻辑
      if (window.pyBridge) {
        window.pyBridge.actor_operation(JSON.stringify({
          Operation: "Rotate",
          sceneName: "mainscene",
          x: 0,
          y: Math.PI / 36, // 5度旋转
          z: 0,
          actorName: actorid.value[0]
        }));
      }
      return;
  }

  // 处理跳跃
  if (isJumping.value) {
    jumpSpeed.value -= gravity;
    y = jumpSpeed.value;

    // 落地检测
    if (jumpSpeed.value <= 0) {
      isJumping.value = false;
      jumpSpeed.value = 0;
    }
  }

  if (window.pyBridge) {
    window.pyBridge.actor_operation(JSON.stringify({
      Operation: "Move",
      sceneName: "mainscene",
      x: x,
      y: y,
      z: z,
      actorName: actorid.value[0]
    }));
  }
};

const handleKeyDown = (event) => {
  event.preventDefault();
  switch (event.key.toLowerCase()) {
    case 'w':
      handleActorMove('forward');
      break;
    case 's':
      handleActorMove('backward');
      break;
    case 'a':
      handleActorMove('left');
      break;
    case 'd':
      handleActorMove('right');
      break;
    case 'q':
      handleActorMove('rotateLeft');
      break;
    case 'e':
      handleActorMove('rotateRight');
      break;
    case ' ':
      if (!isJumping.value) {
        isJumping.value = true;
        jumpSpeed.value = 0.5;
      }
      break;
  }
};

// 版本切换处理
const handleVersionSelect = (version) => {
  selectedVersion.value = version
  try {
    if (typeof localStorage !== 'undefined') {
      localStorage.setItem('selectedVersion', version)
    }
  } catch (e) {
    console.warn('localStorage access error:', e)
  }
}

// 控制设置窗口显示
const openSetup = (index) => {
  const size = {width: 600, height: 320};
  if (window.pyBridge) {
    window.pyBridge.add_dock_widget("SetUp", "/SetUp", "float", "center", JSON.stringify(size));
  }
};

const Out = () => {
  if (window.pyBridge) {
    window.pyBridge.close_process();
  } else {
    console.error("Python SendMessageToDock 未连接！");
  }
}

const removeActors = () => {
}

// 存档相关逻辑
const loadArchives = () => {
  try {
    const archives = JSON.parse(localStorage.getItem('archives') || '[]');
    saves.value = archives.map(archive => ({
      id: archive.id,
      name: archive.name,
      time: archive.time
    }));
  } catch (e) {
    console.error('加载存档失败:', e);
  }
}

const loadSave = (save) => {
  try {
    const archives = JSON.parse(localStorage.getItem('archives') || '[]');
    const target = archives.find(a => a.id === save.id);

    if (target && window.pyBridge) {
      // 加载存档
      target.sceneData.forEach(actor => {
        window.pyBridge.create_actor(currentScene.value, actor.path);
      });

      router.push('/MainPage');
    }
  } catch (error) {
    console.error('加载存档失败:', error);
  }
}

onMounted(() => {
  document.addEventListener('keydown', handleKeyDown);
  loadArchives();
});

onUnmounted(() => {
  document.removeEventListener('keydown', handleKeyDown)
  document.removeEventListener('keydown', handleKeyDown)
})
</script>