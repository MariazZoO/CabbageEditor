import {TOOLBOX_CONFIG} from './toolboxConfig';
import {CoronaTheme} from './theme';

export const WORKSPACE_CONFIG = {
  toolbox: TOOLBOX_CONFIG,
  theme: CoronaTheme,
  toolboxPosition: 'start',
  horizontalLayout: false,
  ContextMenu:true,
  scrollbars: {
    horizontal: false,
    vertical: false,
    set: false
  },
  grid: {
    spacing: 20,
    length: 3,
    colour: '#ccc',
    snap: true
  },
  zoom: {
    controls: true,
    wheel: true,
    startScale: 1.0,
    maxScale: 3,
    minScale: 0.3
  },
  trashcan: true,
  renderer: 'zelos'
};