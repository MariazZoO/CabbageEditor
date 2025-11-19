<template>
  <div class=" border-2 border-[#84a65b] min-h-screen relative">
    <DockTitleBar title="模型属性" extraClass="bg-[#84A65B] rounded-t-md" @close="CloseFloat"/>
    <!-- 四周拖动边框 -->
    <div class="absolute top-0 left-0 w-full h-2 cursor-n-resize z-40" @mousedown="(e) => startResize(e, 'n')"></div>
    <div class="absolute bottom-0 left-0 w-full h-2 cursor-s-resize z-40" @mousedown="(e) => startResize(e, 's')"></div>
    <div class="absolute top-0 left-0 h-full w-2 cursor-w-resize z-40" @mousedown="(e) => startResize(e, 'w')"></div>
    <div class="absolute top-0 right-0 h-full w-2 cursor-e-resize z-40" @mousedown="(e) => startResize(e, 'e')"></div>
    <div class="absolute top-0 left-0 w-4 h-4 cursor-nw-resize z-40" @mousedown="(e) => startResize(e, 'nw')"></div>
    <div class="absolute top-0 right-0 w-4 h-4 cursor-ne-resize z-40" @mousedown="(e) => startResize(e, 'ne')"></div>
    <div class="absolute bottom-0 left-0 w-4 h-4 cursor-sw-resize z-40" @mousedown="(e) => startResize(e, 'sw')"></div>
    <div class="absolute bottom-0 right-0 w-4 h-4 cursor-se-resize z-40" @mousedown="(e) => startResize(e, 'se')"></div>

    <div class="p-4 shadow-md w-full bg-[#a8a4a3]/65 flex flex-col" style="height: calc(100vh - 48px);">
      <div class="p-2 border-b border-gray-400">
        <div class="flex items-center space-x-2">
          <label class="text-gray-600">角色</label>
          <input type="text" placeholder="角色路径"
                 class="flex-1 p-2 border rounded-md focus:outline-none focus:ring-2 focus:ring-blue-400"
                 v-model="character"/>
        </div>
      </div>

      <!-- 标签页切换 -->
      <div class="flex border-b border-gray-400 bg-[#686868]/70">
        <button
            @click="ActiveTab = 'Params'"
            :class="[ActiveTab === 'Params' ? 'bg-gray-700 text-white' : 'bg-[#a8a4a3]/80 hover:bg-gray-600 text-black']"
            class="flex-1 px-4 py-2 text-sm hover:bg-[#a8a4a3]/80 transition-colors duration-200">
          调整
        </button>
        <button
            @click="ActiveTab = 'Material'"
            :class="[ActiveTab === 'Material' ? 'bg-gray-700 text-white' : 'bg-[#a8a4a3]/80 hover:bg-gray-600 text-black']"
            class="flex-1 px-4 py-2 text-sm hover:bg-[#a8a4a3]/80 transition-colors duration-200">
          材质
        </button>
        <button
            @click="ActiveTab = 'BlocklyProgram'"
            :class="[ActiveTab === 'BlocklyProgram' ? 'bg-gray-700 text-white' : 'bg-[#a8a4a3]/80 hover:bg-gray-600 text-black']"
            class="flex-1 px-4 py-2 text-sm hover:bg-[#a8a4a3]/80 transition-colors duration-200">
          Blockly编程
        </button>
      </div>

      <div class="flex-1 overflow-auto">
        <!-- Blockly编程 Tab -->
        <div v-show="ActiveTab === 'BlocklyProgram'" class="h-full flex flex-col">
          <div id="blockdiv" class="blockly-container flex-1"></div>
        </div>

        <!-- 材质Tab -->
        <div v-show="ActiveTab === 'Material'" class="p-4 text-white">
          <!-- 功能补充 -->
        </div>

        <div v-show="ActiveTab === 'Params'" class="p-4 space-y-4">
          <div class="flex items-center justify-between space-x-4 mb-4">
            <label class="text-write whitespace-nowrap">坐标：</label>
            <label class="text-write">x</label>
            <input type="number" step="0.1" @change="UpdatePosition" @input="e => px = e.target.value"
                   class="w-20 p-1 text-center border rounded-md focus:outline-none focus:ring-2 text-write focus:ring-blue-400 bg-[#686868]/70"
                   :value="px"/>
            <label class="text-write">y</label>
            <input type="number" step="0.1" @change="UpdatePosition" @input="e => py = e.target.value"
                   class="w-20 p-1 text-center border rounded-md focus:outline-none focus:ring-2 text-write focus:ring-blue-400 bg-[#686868]/70"
                   :value="py"/>
            <label class="text-write">z</label>
            <input type="number" step="0.1" @change="UpdatePosition" @input="e => pz = e.target.value"
                   class="w-20 p-1 text-center border rounded-md focus:outline-none focus:ring-2 text-write focus:ring-blue-400 bg-[#686868]/70"
                   :value="pz"/>
          </div>

          <div class="flex items-center justify-between space-x-4 mb-4">
            <label class="text-write whitespace-nowrap">旋转：</label>
            <label class="text-write">x</label>
            <input type="number" step="0.1" @change="UpdateRotation" @input="e => rx = e.target.value"
                   class="w-20 p-1 text-center border rounded-md focus:outline-none focus:ring-2 text-write focus:ring-blue-400 bg-[#686868]/70"
                   :value="rx"/>
            <label class="text-write">y</label>
            <input type="number" step="0.1" @change="UpdateRotation" @input="e => ry = e.target.value"
                   class="w-20 p-1 text-center border rounded-md focus:outline-none focus:ring-2 text-write focus:ring-blue-400 bg-[#686868]/70"
                   :value="ry"/>
            <label class="text-write">z</label>
            <input type="number" step="0.1" @change="UpdateRotation" @input="e => rz = e.target.value"
                   class="w-20 p-1 text-center border rounded-md focus:outline-none focus:ring-2 text-write focus:ring-blue-400 bg-[#686868]/70"
                   :value="rz"/>
          </div>

          <div class="flex items-center justify-between space-x-4 mb-4">
            <label class="text-write whitespace-nowrap">缩放：</label>
            <label class="text-write">x</label>
            <input type="number" step="0.1" @change="UpdateScale" @input="e => sx = e.target.value"
                   class="w-20 p-1 text-center border rounded-md focus:outline-none focus:ring-2 text-write focus:ring-blue-400 bg-[#686868]/70"
                   :value="sx"/>
            <label class="text-write">y</label>
            <input type="number" step="0.1" @change="UpdateScale" @input="e => sy = e.target.value"
                   class="w-20 p-1 text-center border rounded-md focus:outline-none focus:ring-2 text-write focus:ring-blue-400 bg-[#686868]/70"
                   :value="sy"/>
            <label class="text-write">z</label>
            <input type="number" step="0.1" @change="UpdateScale" @input="e => sz = e.target.value"
                   class="w-20 p-1 text-center border rounded-md focus:outline-none focus:ring-2 text-write focus:ring-blue-400 bg-[#686868]/70"
                   :value="sz"/>
          </div>
        </div>

      </div>
    </div>

    <div class="absolute top-0 left-0 w-full h-2 cursor-n-resize z-40" @mousedown="(e) => startResize(e, 'n')"></div>
    <div class="absolute bottom-0 left-0 w-full h-2 cursor-s-resize z-40" @mousedown="(e) => startResize(e, 's')"></div>
    <div class="absolute top-0 left-0 h-full w-2 cursor-w-resize z-40" @mousedown="(e) => startResize(e, 'w')"></div>
    <div class="absolute top-0 right-0 h-full w-2 cursor-e-resize z-40" @mousedown="(e) => startResize(e, 'e')"></div>
    <div class="absolute top-0 left-0 w-4 h-4 cursor-nw-resize z-40" @mousedown="(e) => startResize(e, 'nw')"></div>
    <div class="absolute top-0 right-0 w-4 h-4 cursor-ne-resize z-40" @mousedown="(e) => startResize(e, 'ne')"></div>
    <div class="absolute bottom-0 left-0 w-4 h-4 cursor-sw-resize z-40" @mousedown="(e) => startResize(e, 'sw')"></div>
    <div class="absolute bottom-0 right-0 w-4 h-4 cursor-se-resize z-40" @mousedown="(e) => startResize(e, 'se')"></div>
  </div>
  <div class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50" v-if="showExportModal">
    <div class="bg-white rounded-lg p-6 w-[70%] max-w-2xl mx-auto">
      <div class="flex justify-between items-center mb-4">
        <h3 class="text-lg font-semibold">导出代码</h3>
        <button @click="showExportModal = false" class="text-gray-500 hover:text-gray-700">
          ×
        </button>
      </div>
      <pre class="bg-gray-100 p-4 rounded-md overflow-auto max-h-96">{{ exportedCode }}</pre>
      <div class="mt-4 flex justify-end space-x-2">
        <button
            @click="CopyToClipboard"
            class="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-500 transition-colors"
        >
          复制代码
        </button>
        <button
            @click="showExportModal = false"
            class="px-4 py-2 bg-gray-500 text-white rounded hover:bg-gray-600 transition-colors"
        >
          关闭
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import {ref, onMounted, onUnmounted, watch, nextTick} from 'vue';
import {useRoute} from 'vue-router';
import * as Blockly from 'blockly/core';
import * as CN from 'blockly/msg/zh-hans';
import {pythonGenerator} from 'blockly/python';
import {useDragResize} from '@/components/ui/DragTitleBar.js';
import DockTitleBar from '@/components/ui/DockTitleBar.vue'

async function waitWebChannel() {
  if (window.sceneService || window.appService || window.scriptingService) return true;
  if (window.webChannelReady) {
    try {
      await window.webChannelReady;
    } catch {
    }
  }
  return !!(window.sceneService || window.appService || window.scriptingService);
}

const {dragState, startDrag, startResize, stopDrag, onDrag, stopResize, onResize} = useDragResize();
const workspace = ref(null);
const character = ref('');
const px = ref('0.0'), py = ref('0.0'), pz = ref('0.0');
const rx = ref('0.0'), ry = ref('0.0'), rz = ref('0.0');
const sx = ref('1.0'), sy = ref('1.0'), sz = ref('1.0');
const ActiveTab = ref('Params');

const route = useRoute();
const scenename = ref(null);
const actorname = ref(null);
const routename = ref(null);
const flash = ref(null);
const showExportModal = ref(false);
const exportedCode = ref('');

import {defineEngineBlocks} from '@/blockly/blocks/engine.js';
import {defineAppearanceBlocks} from '@/blockly/blocks/appearance.js';
import {defineEventBlocks} from '@/blockly/blocks/event.js';
import {defineControlBlocks} from '@/blockly/blocks/control.js';
import {defineDetectBlocks} from '@/blockly/blocks/detect.js';
import {defineMathBlocks} from '@/blockly/blocks/math.js';
import {defineVariableBlocks} from '@/blockly/blocks/variable.js';
import {defineListBlocks} from '@/blockly/blocks/list.js';

import {defineEngineGenerators} from '@/blockly/generators/engine.js';
import {defineAppearanceGenerators} from '@/blockly/generators/appearance.js';
import {defineEventGenerators} from '@/blockly/generators/event.js';
import {defineControlGenerators} from '@/blockly/generators/control.js';
import {defineDetectGenerators} from '@/blockly/generators/detect.js';
import {defineMathGenerators} from '@/blockly/generators/math.js';
import {defineVariableGenerators} from '@/blockly/generators/variable.js';
import {defineListGenerators} from '@/blockly/generators/list.js';

import {BLOCK_CATEGORY_MAP} from '@/blockly/configs/categoryMap.js';
import {WORKSPACE_CONFIG} from '@/blockly/configs/workspaceConfig.js';
import '@/blockly/configs/renderer.js'

const broadcastList = ref([]);
const createNewBroadcast = () => {
  const newBroadcastName = prompt('请输入新广播的名称：');
  if (newBroadcastName && newBroadcastName.trim() !== '') {
    broadcastList.value.push(newBroadcastName.trim());
  }
};

const initBlocklyAndGenerators = () => {

  defineEngineBlocks(actorname);
  defineAppearanceBlocks(actorname);
  defineEventBlocks(actorname, flash, broadcastList, createNewBroadcast);
  defineControlBlocks(actorname);
  defineDetectBlocks(actorname);
  defineMathBlocks();
  defineVariableBlocks();
  defineListBlocks(actorname);

  defineEngineGenerators();
  defineAppearanceGenerators();
  defineEventGenerators();
  defineControlGenerators();
  defineDetectGenerators();
  defineMathGenerators();
  defineVariableGenerators();
  defineListGenerators();

};

const saveWorkspaceToFile = async (workspaceData) => {
  try {
    if (!window.showSaveFilePicker) {
      console.error('File System Access API不可用');
      return false;
    }

    const jsonStr = JSON.stringify(workspaceData, null, 2);
    const options = {
      types: [{
        description: 'JSON文件',
        accept: {
          'application/json': ['.json']
        }
      }],
      suggestedName: `blockly_workspace_${Date.now()}.json`
    };

    const handle = await window.showSaveFilePicker(options);
    const writable = await handle.createWritable();

    await writable.write(jsonStr);
    await writable.close();

    return true;
  } catch (e) {
    console.error('保存文件失败:', e);
    return false;
  }
};

const loadWorkspaceFromFile = async () => {
  try {
    if (!window.showOpenFilePicker) {
      console.error('File System Access API不可用');
      return false;
    }

    const [fileHandle] = await window.showOpenFilePicker({
      types: [{
        description: 'JSON文件',
        accept: {
          'application/json': ['.json']
        }
      }]
    });

    const file = await fileHandle.getFile();
    const content = await file.text();

    if (!content || content.trim() === '') {
      console.error('文件内容为空');
      return false;
    }

    const workspaceData = JSON.parse(content);

    if (!workspaceData ||
        typeof workspaceData !== 'object' ||
        !workspaceData.blocks ||
        typeof workspaceData.blocks !== 'object') {
      console.error('无效的工作区数据格式');
      return false;
    }

    workspace.value.clear();

    Blockly.serialization.workspaces.load(workspaceData, workspace.value);
    console.log('工作区已从文件载入');
    return true;
  } catch (e) {
    if (e.name !== 'AbortError') {
      console.error('载入工作区失败:', e);
    }
    return false;
  }
};


const initBlockly = () => {
  try {
    const blocklyDiv = document.getElementById('blockdiv');
    if (!blocklyDiv) {
      console.error('Blockly 容器未找到');
      return;
    }

    Blockly.setLocale(CN);
    initBlocklyAndGenerators();

    workspace.value = Blockly.inject(blocklyDiv, WORKSPACE_CONFIG);
    Blockly.ContextMenuRegistry.registry.register({
      displayText: '保存工作区',
      preconditionFn: (scope) => {
        return workspace.value && workspace.value.getAllBlocks(false).length > 0 ? 'enabled' : 'disabled';
      },
      callback: async () => {
        const workspaceData = Blockly.serialization.workspaces.save(workspace.value);
        const success = await saveWorkspaceToFile(workspaceData);
        if (success) {
          console.log('工作区已保存到文件');
        }
      },
      scopeType: Blockly.ContextMenuRegistry.ScopeType.WORKSPACE,
      id: 'saveWorkspace',
      weight: 1
    });
    Blockly.ContextMenuRegistry.registry.register({
      displayText: '加载工作区',
      preconditionFn: () => 'enabled',
      callback: async () => {
        await loadWorkspaceFromFile();
      },
      scopeType: Blockly.ContextMenuRegistry.ScopeType.WORKSPACE,
      id: 'loadWorkspace',
      weight: 2
    });
    Blockly.ContextMenuRegistry.registry.register({
      displayText: '运行',
      preconditionFn: (scope) => {
        return workspace.value && workspace.value.getAllBlocks(false).length > 0 ? 'enabled' : 'disabled';
      },
      callback: async () => {
        const code = pythonGenerator.workspaceToCode(workspace.value);
        console.log(code);
        await waitWebChannel();
        if (window.scriptingService && typeof window.scriptingService.execute_python_code === 'function') {
          window.scriptingService.execute_python_code(code, 0);
        } else if (window.pyBridge && typeof window.pyBridge.execute_python_code === 'function') {
          window.pyBridge.execute_python_code(code, 0);
        } else {
          console.error('未发现脚本执行通道 (scriptingService/pyBridge)');
        }
      },
      scopeType: Blockly.ContextMenuRegistry.ScopeType.WORKSPACE,
      id: 'executePythonCode',
      weight: 3
    });

    const toolbox = blocklyDiv.querySelector('.blocklyToolboxDiv');
    if (toolbox) {
      toolbox.style.overflow = 'hidden';
    }
    const toolboxDiv = document.querySelector('.blocklyToolboxDiv');
    if (toolboxDiv) {
      toolboxDiv.style.overflow = 'hidden';
    }

    setupBlockListener();
    workspace.value.addChangeListener((event) => {
      try {
        if (event.type === Blockly.Events.BLOCK_CREATE) {
          handleBlockCreate(event);
        }
        if (event.type === Blockly.Events.BLOCK_DELETE) {
          if (event.blockId) {
            const block = workspace.value.getBlockById(event.blockId);
            if (block) {
            }
          }
        }
      } catch (err) {
        console.error('Blockly 事件监听异常:', err);
      }
    });
  } catch (err) {
    console.error('Object.vue mounted 初始化异常:', err);
  }
};

const setupBlockListener = () => {
  if (!workspace.value) {
    console.error('setupBlockListener: workspace 未初始化');
    return;
  }
  workspace.value.addChangeListener((event) => {
    try {
      if (event.type === Blockly.Events.BLOCK_CREATE) {
        handleBlockCreate(event);
      }
      if (event.type === Blockly.Events.BLOCK_DELETE) {
        if (event.blockId) {
          const block = workspace.value.getBlockById(event.blockId);
          if (block) {
          }
        }
      }
    } catch (err) {
      console.error('Blockly 事件监听异常:', err);
    }
  });
};

const handleBlockCreate = (event) => {
  if (!workspace.value) {
    console.error('handleBlockCreate: workspace 未初始化');
    return;
  }
  const block = workspace.value.getBlockById(event.blockId);
  if (!block) return;
  const blockType = block.type;
  const categoryName = BLOCK_CATEGORY_MAP[blockType];
  if (categoryName) {
    const toolbox = workspace.value.getToolbox();
    if (toolbox) {
      const categories = toolbox.getToolboxItems();
      const targetCategory = categories.find(cat => cat.name === categoryName);
      if (targetCategory) {
        toolbox.setSelectedItem(targetCategory);
      }
    }
  }
};

const UpdatePosition = () => {
  if (window.sceneService) {
    window.sceneService.actor_operation(JSON.stringify({
      Operation: "Move",
      sceneName: scenename.value,
      x: parseFloat(px.value),
      y: parseFloat(py.value),
      z: parseFloat(pz.value),
      actorName: actorname.value
    }));
    console.error('updatePosition', actorname.value, px.value, py.value, pz.value);
  }
}

const UpdateRotation = () => {
  if (window.sceneService) {
    window.sceneService.actor_operation(JSON.stringify({
      Operation: "Rotate",
      sceneName: scenename.value,
      x: parseFloat(rx.value),
      y: parseFloat(ry.value),
      z: parseFloat(rz.value),
      actorName: actorname.value
    }));
    console.error('updateRotation', rx.value, ry.value, rz.value);
  }
}

const UpdateScale = () => {
  if (window.sceneService) {
    window.sceneService.actor_operation(JSON.stringify({
      Operation: "Scale",
      sceneName: scenename.value,
      x: parseFloat(sx.value),
      y: parseFloat(sy.value),
      z: parseFloat(sz.value),
      actorName: actorname.value
    }));
    console.error('updateScale', sx.value, sy.value, sz.value);
  }
}

const CloseFloat = () => {
  if (window.sceneService) {
    window.sceneService.remove_dock_widget(routename.value);
  }
};

const handleResizeMove = (e) => {
  if (dragState.value.isResizing) onResize(e);
};

const handleResizeUp = () => {
  if (dragState.value.isResizing) stopResize();
};

const resizeBlockly = () => {
  try {
    if (!workspace.value) return;
    const div = document.getElementById('blockdiv');
    if (!div) return;
    const parent = div.parentElement;
    if (parent) {
      // 让容器填满父级空间
      div.style.width = parent.clientWidth + 'px';
      div.style.height = parent.clientHeight + 'px';
    }
    if (typeof Blockly !== 'undefined' && workspace.value) {
      Blockly.svgResize(workspace.value);
    }
  } catch (e) {
    console.error('resizeBlockly 失败:', e);
  }
};

watch(ActiveTab, (val) => {
  if (val === 'BlocklyProgram') {
    nextTick(() => resizeBlockly());
  }
});

const handleWindowResize = () => {
  if (ActiveTab.value === 'BlocklyProgram') resizeBlockly();
};

onMounted(() => {
  try {
    scenename.value = route.query.sceneName || '';
    actorname.value = route.query.objectName || '';
    character.value = decodeURIComponent(route.query.path || '');
    routename.value = route.query.routename || '';
    initBlockly();
    if (typeof handleResizeMove === 'function') {
      document.addEventListener('mousemove', handleResizeMove);
    }
    if (typeof handleResizeUp === 'function') {
      document.addEventListener('mouseup', handleResizeUp);
    }
    if (typeof onDrag === 'function') {
      document.addEventListener('mousemove', onDrag);
    }
    if (typeof stopDrag === 'function') {
      document.addEventListener('mouseup', stopDrag);
    }
    window.addEventListener('resize', handleWindowResize);
    // 初次进入如果默认是 BlocklyProgram，也执行一次
    if (ActiveTab.value === 'BlocklyProgram') {
      nextTick(() => resizeBlockly());
    }
  } catch (err) {
    console.error('Object.vue mounted 初始化异常:', err);
  }
});

onUnmounted(() => {
  document.removeEventListener('mousemove', handleResizeMove);
  document.removeEventListener('mouseup', handleResizeUp);
  document.removeEventListener('mousemove', onDrag);
  document.removeEventListener('mouseup', stopDrag);
  window.removeEventListener('resize', handleWindowResize);
});
</script>

<style scoped>
.blockly-container {
  width: 100%;
  height: 100%;
  min-height: 400px; /* 防止高度塌陷 */
  position: relative;
  overflow: hidden; /* 避免内部滚动条影响渲染尺寸计算 */
}

/* 让 blockly 内部 svg 适配容器 */
.blockly-container :deep(.blocklyWorkspace) {
  width: 100% !important;
  height: 100% !important;
}

#blockdiv :deep(.blocklyZoom) {
  display: flex !important;
  opacity: 1 !important;
}

#blockdiv :deep(.blocklyTrash) {
  opacity: 1 !important;
}

svg {
  display: inline !important;
}

svg[display="none"] {
  display: none !important;
}
</style>