/**
 * Nano UI - 轻量级组件库
 * 用于 AI 生成的单文件 HTML 应用
 */

// ==================== 工具函数 ====================

function generateId(prefix = 'comp') {
  return `${prefix}_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
}

function escapeHtml(text) {
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
}

function classNames(...args) {
  return args.filter(Boolean).join(' ');
}

// ==================== 状态管理 ====================

const state = {
  _data: {},
  _listeners: {},

  set(key, value) {
    this._data[key] = value;
    this._emit(key, value);
  },

  get(key) {
    return this._data[key];
  },

  getAll() {
    return { ...this._data };
  },

  on(key, callback) {
    if (!this._listeners[key]) {
      this._listeners[key] = [];
    }
    this._listeners[key].push(callback);
  },

  _emit(key, value) {
    const callbacks = this._listeners[key] || [];
    callbacks.forEach(cb => cb(value));
  }
};

// ==================== 路由系统 ====================

const router = {
  _routes: {},
  _currentRoute: '/',
  _listeners: [],

  init(defaultRoute = '/') {
    this._currentRoute = window.location.hash.slice(1) || defaultRoute;
    window.addEventListener('hashchange', () => {
      this._currentRoute = window.location.hash.slice(1) || defaultRoute;
      this._notify();
    });
    return this;
  },

  add(route, handler) {
    this._routes[route] = handler;
    return this;
  },

  navigate(route) {
    window.location.hash = route;
  },

  current() {
    return this._currentRoute;
  },

  onNavigate(callback) {
    this._listeners.push(callback);
    window.addEventListener('hashchange', () => callback(this._currentRoute));
  },

  _notify() {
    this._listeners.forEach(cb => cb(this._currentRoute));
  }
};

// ==================== 表单处理 ====================

const formData = {
  _forms: {},

  init(formId) {
    this._forms[formId] = {};
    const form = document.querySelector(`[data-form-id="${formId}"]`);
    if (form) {
      form.addEventListener('submit', (e) => {
        e.preventDefault();
        const data = new FormData(form);
        this._forms[formId] = Object.fromEntries(data);
        form.dispatchEvent(new CustomEvent('formSubmit', {
          detail: this._forms[formId]
        }));
      });
    }
    return this;
  },

  get(formId) {
    return this._forms[formId] || {};
  },

  onSubmit(formId, callback) {
    const form = document.querySelector(`[data-form-id="${formId}"]`);
    if (form) {
      form.addEventListener('formSubmit', (e) => callback(e.detail));
    }
  }
};

// ==================== 基础组件 ====================

class Component {
  constructor(options = {}) {
    this.id = options.id || generateId();
    this.options = options;
  }

  render() {
    throw new Error('Component must implement render()');
  }

  mount(container) {
    const html = this.render();
    if (typeof container === 'string') {
      document.querySelector(container).innerHTML = html;
    } else if (container instanceof HTMLElement) {
      container.innerHTML = html;
    }
    this.mounted?.();
  }
}

// --- Button 按钮 ---
class Button extends Component {
  render() {
    const { label = 'Button', variant = 'primary', size = 'md', action = '', route = '', disabled = false } = this.options;
    const baseClass = 'na-btn';
    const variantClass = variant === 'primary' ? '' : 'na-btn-secondary';
    const sizeClass = size === 'sm' ? 'na-btn-sm' : size === 'lg' ? 'na-btn-lg' : '';
    const actionAttr = action ? `data-action="${escapeHtml(action)}"` : '';
    const routeAttr = route ? `data-route="${escapeHtml(route)}"` : '';
    const disabledAttr = disabled ? 'disabled' : '';

    return `<button class="${classNames(baseClass, variantClass, sizeClass)}" ${actionAttr} ${routeAttr} ${disabledAttr}>${escapeHtml(label)}</button>`;
  }
}

// --- Card 卡片 ---
class Card extends Component {
  render() {
    const { title = '', description = '', children = [], footer = '' } = this.options;
    const titleHtml = title ? `<h3 class="na-card-title">${escapeHtml(title)}</h3>` : '';
    const descHtml = description ? `<p class="na-card-description">${escapeHtml(description)}</p>` : '';
    const childrenHtml = children.map(c => typeof c === 'string' ? c : c.render ? c.render() : '').join('\n');
    const footerHtml = footer ? `<div class="na-card-footer">${typeof footer === 'string' ? footer : footer.render ? footer.render() : ''}</div>` : '';

    return `
      <div class="na-card">
        ${titleHtml}
        ${descHtml}
        <div class="na-card-body">${childrenHtml}</div>
        ${footerHtml}
      </div>
    `;
  }
}

// --- Input 输入框 ---
class Input extends Component {
  render() {
    const { type = 'text', name = '', label = '', placeholder = '', value = '', required = false } = this.options;
    const fieldId = this.id;

    return `
      <div class="na-field">
        ${label ? `<label class="na-label" for="${fieldId}">${escapeHtml(label)}</label>` : ''}
        <input
          type="${escapeHtml(type)}"
          id="${fieldId}"
          name="${escapeHtml(name)}"
          class="na-input"
          placeholder="${escapeHtml(placeholder)}"
          value="${escapeHtml(value)}"
          ${required ? 'required' : ''}
        />
      </div>
    `;
  }
}

// --- Select 选择框 ---
class Select extends Component {
  render() {
    const { name = '', label = '', placeholder = '请选择', options = [], value = '' } = this.options;
    const fieldId = this.id;
    const optionsHtml = options.map(opt => {
      const val = typeof opt === 'string' ? opt : opt.value;
      const lbl = typeof opt === 'string' ? opt : opt.label;
      const selected = val === value ? 'selected' : '';
      return `<option value="${escapeHtml(val)}" ${selected}>${escapeHtml(lbl)}</option>`;
    }).join('');

    return `
      <div class="na-field">
        ${label ? `<label class="na-label" for="${fieldId}">${escapeHtml(label)}</label>` : ''}
        <select id="${fieldId}" name="${escapeHtml(name)}" class="na-input">
          <option value="">${escapeHtml(placeholder)}</option>
          ${optionsHtml}
        </select>
      </div>
    `;
  }
}

// --- Form 表单 ---
class Form extends Component {
  render() {
    const { id = generateId('form'), fields = [], submitLabel = '提交', action = '' } = this.options;
    const fieldsHtml = fields.map(f => {
      if (f.render) return f.render();
      if (f.type === 'select') {
        return new Select(f).render();
      }
      return new Input(f).render();
    }).join('\n');
    const actionAttr = action ? `data-action="${escapeHtml(action)}"` : '';

    return `
      <form class="na-form" data-form-id="${id}" ${actionAttr}>
        ${fieldsHtml}
        <button type="submit" class="na-btn na-btn-primary na-btn-block">${escapeHtml(submitLabel)}</button>
      </form>
    `;
  }
}

// --- Table 表格 ---
class Table extends Component {
  render() {
    const { columns = [], rows = [], emptyMessage = '暂无数据' } = this.options;
    const headHtml = columns.map(col => `<th>${escapeHtml(col)}</th>`).join('');
    const bodyHtml = rows.length > 0
      ? rows.map(row => `<tr>${columns.map(col => `<td>${escapeHtml(row[col] || '')}</td>`).join('')}</tr>`).join('')
      : `<tr><td colspan="${columns.length}" class="na-empty-cell">${escapeHtml(emptyMessage)}</td></tr>`;

    return `
      <div class="na-table-wrap">
        <table class="na-table">
          <thead><tr>${headHtml}</tr></thead>
          <tbody>${bodyHtml}</tbody>
        </table>
      </div>
    `;
  }
}

// --- Modal 模态框 ---
class Modal extends Component {
  render() {
    const { id = generateId('modal'), title = '', children = [], showClose = true } = this.options;
    const childrenHtml = children.map(c => typeof c === 'string' ? c : c.render ? c.render() : '').join('\n');
    const closeBtn = showClose ? `<button class="na-modal-close" data-modal-close="${id}">&times;</button>` : '';

    return `
      <div class="na-modal" id="${id}" data-modal-id="${id}">
        <div class="na-modal-overlay" data-modal-overlay="${id}"></div>
        <div class="na-modal-content">
          <div class="na-modal-header">
            ${title ? `<h3 class="na-modal-title">${escapeHtml(title)}</h3>` : ''}
            ${closeBtn}
          </div>
          <div class="na-modal-body">${childrenHtml}</div>
        </div>
      </div>
    `;
  }

  open() {
    const el = document.getElementById(this.id);
    if (el) el.classList.add('na-modal-open');
  }

  close() {
    const el = document.getElementById(this.id);
    if (el) el.classList.remove('na-modal-open');
  }
}

// --- Tag 标签 ---
class Tag extends Component {
  render() {
    const { text = '', variant = 'default' } = this.options;
    const variantClass = variant !== 'default' ? `na-tag-${variant}` : '';

    return `<span class="na-tag ${variantClass}">${escapeHtml(text)}</span>`;
  }
}

// --- Image 图片 ---
class Image extends Component {
  render() {
    const { src = '', alt = 'Image', width, height } = this.options;
    const sizeAttrs = [width ? `width="${escapeHtml(width)}"` : '', height ? `height="${escapeHtml(height)}"` : ''].filter(Boolean).join(' ');

    return `<img src="${escapeHtml(src)}" alt="${escapeHtml(alt)}" class="na-image" ${sizeAttrs} onerror="this.style.display='none'" />`;
  }
}

// ==================== 复合组件 ====================

// --- Hero 主视觉区 ---
class Hero extends Component {
  render() {
    const { eyebrow = '', title = 'Hero Title', description = '', imageSrc = '', ctaLabel = '', ctaRoute = '', stats = [] } = this.options;
    const eyebrowHtml = eyebrow ? `<div class="na-kicker">${escapeHtml(eyebrow)}</div>` : '';
    const descHtml = description ? `<p class="na-hero-description">${escapeHtml(description)}</p>` : '';
    const ctaHtml = ctaLabel ? `<button class="na-btn na-btn-primary" data-route="${escapeHtml(ctaRoute || '/')}">${escapeHtml(ctaLabel)}</button>` : '';
    const statsHtml = stats.length > 0 ? `<div class="na-hero-metrics">${stats.map(s => `
      <div class="na-hero-metric">
        <div class="na-hero-metric-value">${escapeHtml(s.value)}</div>
        <div class="na-hero-metric-label">${escapeHtml(s.label)}</div>
      </div>
    `).join('')}</div>` : '';
    const imageHtml = imageSrc ? `<div class="na-hero-visual"><img src="${escapeHtml(imageSrc)}" alt="${escapeHtml(title)}" class="na-image" /></div>` : '';

    return `
      <section class="na-section na-hero">
        <div class="na-hero-grid">
          <div class="na-hero-copy">
            ${eyebrowHtml}
            <h1 class="na-display">${escapeHtml(title)}</h1>
            ${descHtml}
            <div class="na-actions">${ctaHtml}</div>
            ${statsHtml}
          </div>
          ${imageHtml}
        </div>
      </section>
    `;
  }
}

// --- FeatureGrid 特性网格 ---
class FeatureGrid extends Component {
  render() {
    const { title = '', description = '', items = [], columns = 3 } = this.options;
    const titleHtml = title ? `<h2 class="na-section-title">${escapeHtml(title)}</h2>` : '';
    const descHtml = description ? `<p class="na-section-description">${escapeHtml(description)}</p>` : '';
    const itemsHtml = items.map(item => `
      <article class="na-feature-item">
        ${item.badge ? `<div class="na-feature-badge">${escapeHtml(item.badge)}</div>` : ''}
        ${item.icon ? `<div class="na-feature-icon">${item.icon}</div>` : ''}
        <h3 class="na-feature-title">${escapeHtml(item.title || '')}</h3>
        <p class="na-feature-description">${escapeHtml(item.description || '')}</p>
      </article>
    `).join('');

    return `
      <section class="na-section">
        <div class="na-copy-block">
          ${titleHtml}
          ${descHtml}
        </div>
        <div class="na-feature-grid na-cols-${Math.max(1, Math.min(4, columns))}">${itemsHtml}</div>
      </section>
    `;
  }
}

// --- StatsBand 数据条 ---
class StatsBand extends Component {
  render() {
    const { items = [] } = this.options;
    const itemsHtml = items.map(item => `
      <div class="na-stat-chip">
        <div class="na-stat-chip-value">${escapeHtml(item.value || '--')}</div>
        <div class="na-stat-chip-label">${escapeHtml(item.label || '')}</div>
        ${item.caption ? `<div class="na-stat-chip-caption">${escapeHtml(item.caption)}</div>` : ''}
      </div>
    `).join('');

    return `
      <section class="na-section">
        <div class="na-stat-band">${itemsHtml}</div>
      </section>
    `;
  }
}

// --- SplitSection 分栏区 ---
class SplitSection extends Component {
  render() {
    const { eyebrow = '', title = '', description = '', bullets = [], imageSrc = '', reverse = false, ctaLabel = '', ctaRoute = '' } = this.options;
    const eyebrowHtml = eyebrow ? `<div class="na-kicker">${escapeHtml(eyebrow)}</div>` : '';
    const titleHtml = title ? `<h2 class="na-section-title">${escapeHtml(title)}</h2>` : '';
    const descHtml = description ? `<p class="na-section-description">${escapeHtml(description)}</p>` : '';
    const bulletsHtml = bullets?.length > 0 ? `<ul class="na-bullets">${bullets.map(b => `<li>${escapeHtml(b)}</li>`).join('')}</ul>` : '';
    const ctaHtml = ctaLabel ? `<button class="na-btn na-btn-primary" data-route="${escapeHtml(ctaRoute || '/')}">${escapeHtml(ctaLabel)}</button>` : '';
    const imageHtml = imageSrc ? `<div class="na-split-visual"><img src="${escapeHtml(imageSrc)}" alt="${escapeHtml(title)}" class="na-image" /></div>` : '';
    const reverseClass = reverse ? 'is-reverse' : '';

    return `
      <section class="na-section">
        <div class="na-split ${reverseClass}">
          <div class="na-split-copy">
            ${eyebrowHtml}
            ${titleHtml}
            ${descHtml}
            ${bulletsHtml}
            <div class="na-actions">${ctaHtml}</div>
          </div>
          ${imageHtml}
        </div>
      </section>
    `;
  }
}

// --- CtaBand 行动号召条 ---
class CtaBand extends Component {
  render() {
    const { title = 'Ready to get started?', description = '', primaryLabel = 'Get Started', primaryRoute = '', secondaryLabel = '', secondaryRoute = '' } = this.options;
    const primaryBtn = primaryLabel ? `<button class="na-btn na-btn-primary" data-route="${escapeHtml(primaryRoute || '/')}">${escapeHtml(primaryLabel)}</button>` : '';
    const secondaryBtn = secondaryLabel ? `<button class="na-btn na-btn-secondary" data-route="${escapeHtml(secondaryRoute || '/')}">${escapeHtml(secondaryLabel)}</button>` : '';

    return `
      <section class="na-section">
        <div class="na-cta">
          <h2 class="na-cta-title">${escapeHtml(title)}</h2>
          ${description ? `<p class="na-cta-description">${escapeHtml(description)}</p>` : ''}
          <div class="na-actions">${primaryBtn}${secondaryBtn}</div>
        </div>
      </section>
    `;
  }
}

// --- AuthCard 认证卡片 ---
class AuthCard extends Component {
  render() {
    const { title = 'Welcome back', description = '', imageSrc = '', children = [], footerText = '', footerLabel = '', footerRoute = '' } = this.options;
    const childrenHtml = children.map(c => typeof c === 'string' ? c : c.render ? c.render() : '').join('\n');
    const imageHtml = imageSrc ? `<div class="na-auth-visual"><img src="${escapeHtml(imageSrc)}" alt="${escapeHtml(title)}" class="na-image" /></div>` : '';
    const footerHtml = footerText ? `<div class="na-auth-footer">${escapeHtml(footerText)}${footerLabel && footerRoute ? ` <button class="na-inline-link" data-route="${escapeHtml(footerRoute)}">${escapeHtml(footerLabel)}</button>` : ''}</div>` : '';

    return `
      <section class="na-section">
        <div class="na-auth-shell">
          ${imageHtml}
          <div class="na-auth-body">
            <h2 class="na-section-title">${escapeHtml(title)}</h2>
            ${description ? `<p class="na-section-description">${escapeHtml(description)}</p>` : ''}
            ${childrenHtml}
            ${footerHtml}
          </div>
        </div>
      </section>
    `;
  }
}

// --- Navbar 导航栏 ---
class Navbar extends Component {
  render() {
    const { title = 'App', links = [] } = this.options;
    const currentRoute = window.location?.hash?.slice(1) || '/';
    const linksHtml = links.map(link => {
      const route = link.route || '/';
      const isActive = route === currentRoute ? 'is-active' : '';
      return `<button class="na-nav-link ${isActive}" data-route="${escapeHtml(route)}">${escapeHtml(link.label || 'Link')}</button>`;
    }).join('');

    return `
      <header class="na-header-shell">
        <div class="na-header-backdrop"></div>
        <nav class="na-navbar">
          <button class="na-brand" data-route="/">${escapeHtml(title)}</button>
          <div class="na-nav-links">${linksHtml}</div>
        </nav>
      </header>
    `;
  }
}

// ==================== 全局注册 ====================

window.NanoUI = {
  // 核心
  Component,

  // 基础组件
  Button,
  Card,
  Input,
  Select,
  Form,
  Table,
  Modal,
  Tag,
  Image,

  // 复合组件
  Hero,
  FeatureGrid,
  StatsBand,
  SplitSection,
  CtaBand,
  AuthCard,
  Navbar,

  // 工具
  state,
  router,
  formData,

  // 辅助函数
  generateId,
  escapeHtml,
  classNames
};

// 自动初始化路由
document.addEventListener('DOMContentLoaded', () => {
  router.init('/');

  // 绑定全局交互
  document.addEventListener('click', (e) => {
    const routeTarget = e.target.closest('[data-route]');
    if (routeTarget) {
      e.preventDefault();
      const route = routeTarget.getAttribute('data-route');
      if (route) router.navigate(route);
    }

    const modalClose = e.target.closest('[data-modal-close]');
    if (modalClose) {
      const modalId = modalClose.getAttribute('data-modal-close');
      const modal = document.getElementById(modalId);
      if (modal) modal.classList.remove('na-modal-open');
    }

    const modalOverlay = e.target.closest('[data-modal-overlay]');
    if (modalOverlay) {
      const modalId = modalOverlay.getAttribute('data-modal-overlay');
      const modal = document.getElementById(modalId);
      if (modal) modal.classList.remove('na-modal-open');
    }
  });

  // 表单提交提示
  document.addEventListener('submit', (e) => {
    const form = e.target;
    if (form.classList.contains('na-form')) {
      e.preventDefault();
      showToast('提交成功');
    }
  });
});

// Toast 提示
function showToast(message, duration = 2200) {
  const existing = document.querySelector('.na-toast');
  if (existing) existing.remove();

  const toast = document.createElement('div');
  toast.className = 'na-toast';
  toast.textContent = message;
  document.body.appendChild(toast);

  setTimeout(() => toast.remove(), duration);
}
window.showToast = showToast;
