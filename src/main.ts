import { createPinia } from 'pinia'
import { createApp } from 'vue'
import App from './App.vue'
import { createAppI18n } from './i18n'
import { connectToolTheme } from './lib/toolTheme'
import { translateNav } from './lib/nav'
// Design-Tokens v2 (--ds-*), Kopie aus KodiniTools/Collage-Maker src/design-system/tokens-v2.css
import '../static/design-system/tokens-v2.css'
import './styles/base.css'
import './styles/controls.css'
import './styles/stage1.css'
import './styles/stage2-header.css'

const theme = document.querySelector<HTMLSelectElement>('#favicon-theme')
connectToolTheme(theme)

const view = document.getElementById('favicon-view')
const landing = view?.querySelector<HTMLElement>('.favicon-landing')
if (view && !landing) {
  createApp(App).use(createPinia()).use(createAppI18n()).mount(view)
}

const overviewLink = document.querySelector<HTMLAnchorElement>('[data-favicon-link="overview"]')
const editorLink = document.querySelector<HTMLAnchorElement>('[data-favicon-link="editor"]')

function updateLanguage() {
  const lang = document.documentElement.lang === 'en' ? 'en' : 'de'
  if (landing && landing.lang !== lang) {
    const url = new URL(location.href)
    url.searchParams.set('lang', lang)
    location.replace(url.href)
    return
  }
  const themeLabel = document.querySelector('[data-favicon-theme-label]')
  if (theme && themeLabel) {
    themeLabel.textContent = lang === 'en' ? 'Theme' : 'Design'
    const labels = lang === 'en' ? ['System', 'Light', 'Dark'] : ['System', 'Hell', 'Dunkel']
    for (const [index, option] of Array.from(theme.options).entries()) {
      option.textContent = labels[index] ?? option.textContent
    }
  }
  if (overviewLink && editorLink) {
    overviewLink.href = `./?lang=${lang}`
    overviewLink.textContent = lang === 'en' ? 'Overview' : 'Übersicht'
    editorLink.href = `./app?lang=${lang}`
    editorLink.textContent = lang === 'en' ? 'Favicon editor' : 'Favicon-Editor'
  }
}

if (landing) {
  translateNav(landing.lang === 'en' ? 'en' : 'de')

  window.addEventListener('locale-changed', (event) => {
    const next = (event as CustomEvent<{ locale?: string }>).detail?.locale
    if (next === 'en' || next === 'de') document.documentElement.lang = next
  })
  document.addEventListener('click', (event) => {
    const target = (event.target as Element | null)?.closest('.global-nav-lang-btn[data-lang]')
    const next = target?.getAttribute('data-lang')
    if (next === 'en' || next === 'de') document.documentElement.lang = next
  })
}

new MutationObserver(updateLanguage).observe(document.documentElement, {
  attributeFilter: ['lang'],
})
updateLanguage()
