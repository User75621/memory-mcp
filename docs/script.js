const root = document.documentElement;
const themeToggle = document.querySelector('[data-theme-toggle]');
const languageToggle = document.querySelector('[data-language-toggle]');
const tabButtons = document.querySelectorAll('[data-tab-button]');
const tabPanels = document.querySelectorAll('[data-tab-panel]');

function applyTheme(theme) {
  root.dataset.theme = theme;
  localStorage.setItem('asm-theme', theme);
  if (themeToggle) {
    themeToggle.textContent = theme === 'dark' ? 'Light' : 'Dark';
  }
}

function initTheme() {
  const saved = localStorage.getItem('asm-theme');
  const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
  applyTheme(saved || (prefersDark ? 'dark' : 'light'));
}

async function loadLocale(language) {
  const response = await fetch(`locales/${language}.json`, { cache: 'no-cache' });
  const messages = await response.json();

  document.documentElement.lang = language;
  localStorage.setItem('asm-language', language);
  if (languageToggle) {
    languageToggle.textContent = language.toUpperCase() === 'ES' ? 'EN' : 'ES';
  }

  document.querySelectorAll('[data-i18n]').forEach((node) => {
    const path = node.dataset.i18n.split('.');
    const value = path.reduce((acc, key) => (acc ? acc[key] : undefined), messages);
    if (typeof value === 'string') {
      node.textContent = value;
    }
  });

  document.querySelectorAll('[data-i18n-attr]').forEach((node) => {
    const [attribute, ...pathParts] = node.dataset.i18nAttr.split(':');
    const path = pathParts.join(':').split('.');
    const value = path.reduce((acc, key) => (acc ? acc[key] : undefined), messages);
    if (typeof value === 'string') {
      node.setAttribute(attribute, value);
    }
  });

  document.querySelectorAll('[data-i18n-array]').forEach((node) => {
    const [scope, index, field] = node.dataset.i18nArray.split('.');
    const value = messages[scope].items[Number(index)][field];
    node.textContent = value;
  });

  document.querySelectorAll('[data-i18n-step]').forEach((node) => {
    const index = Number(node.dataset.i18nStep);
    node.textContent = messages.setup.steps[index];
  });

  document.title = messages.meta.title;
}

function initLanguage() {
  const saved = localStorage.getItem('asm-language') || 'en';
  loadLocale(saved).catch(() => loadLocale('en'));
}

function activateTab(tabName) {
  tabButtons.forEach((button) => {
    const active = button.dataset.tabButton === tabName;
    button.setAttribute('aria-selected', String(active));
  });

  tabPanels.forEach((panel) => {
    const active = panel.dataset.tabPanel === tabName;
    panel.classList.toggle('active', active);
    panel.hidden = !active;
  });
}

function initTabs() {
  tabButtons.forEach((button) => {
    button.addEventListener('click', () => activateTab(button.dataset.tabButton));
  });
  activateTab('opencode');
}

function initSmoothScroll() {
  document.querySelectorAll('a[href^="#"]').forEach((anchor) => {
    anchor.addEventListener('click', (event) => {
      const targetId = anchor.getAttribute('href');
      const target = document.querySelector(targetId);
      if (!target) {
        return;
      }
      event.preventDefault();
      target.scrollIntoView({ behavior: 'smooth', block: 'start' });
    });
  });
}

if (themeToggle) {
  themeToggle.addEventListener('click', () => {
    const nextTheme = root.dataset.theme === 'dark' ? 'light' : 'dark';
    applyTheme(nextTheme);
  });
}

if (languageToggle) {
  languageToggle.addEventListener('click', () => {
    const nextLanguage = document.documentElement.lang === 'es' ? 'en' : 'es';
    loadLocale(nextLanguage).catch(() => loadLocale('en'));
  });
}

initTheme();
initLanguage();
initTabs();
initSmoothScroll();
