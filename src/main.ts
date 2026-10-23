import { createPinia } from 'pinia'
import { createApp } from 'vue'
import App from './App.vue'
import { createAppI18n } from './i18n'
// Design-Tokens v2 (--ds-*), Kopie aus KodiniTools/Collage-Maker src/design-system/tokens-v2.css
import '../static/design-system/tokens-v2.css'
import './styles/base.css'
import './styles/controls.css'

createApp(App).use(createPinia()).use(createAppI18n()).mount('#app')
