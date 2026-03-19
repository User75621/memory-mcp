const root = document.documentElement;
const themeToggle = document.querySelector('[data-theme-toggle]');
const languageToggle = document.querySelector('[data-language-toggle]');
const tabButtons = document.querySelectorAll('[data-tab-button]');
const tabPanels = document.querySelectorAll('[data-tab-panel]');
const sectionLinks = document.querySelectorAll('[data-section-link]');

let localeMessages = null;

const themeIcons = {
  light: '&#9728;',
  dark: '&#9789;'
};

function getMessage(path, fallback = '') {
  if (!localeMessages) {
    return fallback;
  }

  return path.split('.').reduce((acc, key) => (acc ? acc[key] : undefined), localeMessages) || fallback;
}

function applyTheme(theme) {
  root.dataset.theme = theme;
  localStorage.setItem('asm-theme', theme);

  if (!themeToggle) {
    return;
  }

  const icon = themeToggle.querySelector('[data-theme-icon]');
  const label = themeToggle.querySelector('[data-theme-label]');

  if (icon) {
    icon.innerHTML = themeIcons[theme] || themeIcons.light;
  }

  if (label) {
    label.textContent = theme === 'dark'
      ? getMessage('ui.themeDark', 'Dark')
      : getMessage('ui.themeLight', 'Light');
  }

  themeToggle.setAttribute(
    'aria-label',
    theme === 'dark'
      ? getMessage('ui.themeSwitchLight', 'Switch to light mode')
      : getMessage('ui.themeSwitchDark', 'Switch to dark mode')
  );
}

function initTheme() {
  const saved = localStorage.getItem('asm-theme');
  const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
  applyTheme(saved || (prefersDark ? 'dark' : 'light'));
}

function updateCopyButtons() {
  document.querySelectorAll('[data-copy-button]').forEach((button) => {
    const copied = button.dataset.copied === 'true';
    button.textContent = copied
      ? getMessage('ui.copied', 'Copied')
      : getMessage('ui.copy', 'Copy');
  });
}

function enhanceCopyTargets() {
  document.querySelectorAll('pre').forEach((pre) => {
    if (pre.dataset.copyEnhanced === 'true') {
      return;
    }

    pre.dataset.copyEnhanced = 'true';
    const wrapper = document.createElement('div');
    wrapper.className = 'copy-block';
    pre.parentNode.insertBefore(wrapper, pre);
    wrapper.appendChild(pre);

    const button = document.createElement('button');
    button.type = 'button';
    button.className = 'copy-button';
    button.dataset.copyButton = 'true';
    button.addEventListener('click', async () => {
      const text = pre.innerText.trim();
      await navigator.clipboard.writeText(text);
      button.dataset.copied = 'true';
      button.classList.add('copied');
      updateCopyButtons();
      window.setTimeout(() => {
        button.dataset.copied = 'false';
        button.classList.remove('copied');
        updateCopyButtons();
      }, 1600);
    });

    wrapper.appendChild(button);
  });

  document.querySelectorAll('.command').forEach((command) => {
    if (command.closest('.copy-command')) {
      return;
    }

    const wrapper = document.createElement('div');
    wrapper.className = 'copy-command';
    command.parentNode.insertBefore(wrapper, command);
    wrapper.appendChild(command);

    const button = document.createElement('button');
    button.type = 'button';
    button.className = 'copy-button';
    button.dataset.copyButton = 'true';
    button.addEventListener('click', async () => {
      const text = command.innerText.trim();
      await navigator.clipboard.writeText(text);
      button.dataset.copied = 'true';
      button.classList.add('copied');
      updateCopyButtons();
      window.setTimeout(() => {
        button.dataset.copied = 'false';
        button.classList.remove('copied');
        updateCopyButtons();
      }, 1600);
    });

    wrapper.appendChild(button);
  });

  updateCopyButtons();
}

function updateSectionLinks(activeId) {
  sectionLinks.forEach((link) => {
    const isActive = link.dataset.sectionLink === activeId;
    link.classList.toggle('active', isActive);
    link.setAttribute('aria-current', isActive ? 'true' : 'false');
  });
}

function initSectionTracking() {
  const observedSections = [...new Set(
    Array.from(sectionLinks)
      .map((link) => document.getElementById(link.dataset.sectionLink))
      .filter(Boolean)
  )];

  if (!observedSections.length) {
    return;
  }

  const observer = new IntersectionObserver(
    (entries) => {
      const visibleEntries = entries
        .filter((entry) => entry.isIntersecting)
        .sort((a, b) => b.intersectionRatio - a.intersectionRatio);

      if (visibleEntries.length) {
        updateSectionLinks(visibleEntries[0].target.id);
      }
    },
    {
      rootMargin: '-20% 0px -55% 0px',
      threshold: [0.15, 0.35, 0.6]
    }
  );

  observedSections.forEach((section) => observer.observe(section));
  updateSectionLinks(observedSections[0].id);
}

async function loadLocale(language) {
  const response = await fetch(`locales/${language}.json`, { cache: 'no-cache' });
  localeMessages = await response.json();

  document.documentElement.lang = language;
  localStorage.setItem('asm-language', language);
  if (languageToggle) {
    languageToggle.textContent = language.toUpperCase() === 'ES' ? 'EN' : 'ES';
  }

  document.querySelectorAll('[data-i18n]').forEach((node) => {
    const value = getMessage(node.dataset.i18n);
    if (typeof value === 'string' && value) {
      node.textContent = value;
    }
  });

  document.querySelectorAll('[data-i18n-attr]').forEach((node) => {
    const [attribute, ...pathParts] = node.dataset.i18nAttr.split(':');
    const value = getMessage(pathParts.join(':'));
    if (typeof value === 'string' && value) {
      node.setAttribute(attribute, value);
    }
  });

  document.querySelectorAll('[data-i18n-array]').forEach((node) => {
    const [scope, index, field] = node.dataset.i18nArray.split('.');
    const value = localeMessages?.[scope]?.items?.[Number(index)]?.[field];
    if (typeof value === 'string') {
      node.textContent = value;
    }
  });

  document.querySelectorAll('[data-i18n-step]').forEach((node) => {
    const index = Number(node.dataset.i18nStep);
    const value = localeMessages?.setup?.steps?.[index];
    if (typeof value === 'string') {
      node.textContent = value;
    }
  });

  document.title = getMessage('meta.title', document.title);
  applyTheme(root.dataset.theme || 'light');
  updateCopyButtons();
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

enhanceCopyTargets();
initTheme();
initLanguage();
initTabs();
initSmoothScroll();
initSectionTracking();
