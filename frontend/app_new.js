// AlsaTrade Modern Tabbed Interface JavaScript

// Application State
const AppState = {
  currentTab: 'setup',
  configuration: {
    product: null,
    strategy: null,
    direction: 'allow_long_short',
    leverage: 1,
    capitalAllocation: 10
  },
  executions: [],
  lastUpdated: null,
  isLoading: false
};

// Utility Functions
const fetchJson = async (url, options = {}) => {
  try {
    const response = await fetch(url, {
      headers: { "Content-Type": "application/json" },
      ...options
    });

    if (!response.ok) {
      const contentType = response.headers.get("content-type") || "";
      if (contentType.includes("application/json")) {
        const data = await response.json().catch(() => null);
        const message = data?.detail || data?.message || "Request failed";
        throw new Error(message);
      }
      const message = await response.text();
      throw new Error(message || "Request failed");
    }

    const contentType = response.headers.get("content-type") || "";
    if (!contentType.includes("application/json")) {
      return null;
    }

    return response.json();
  } catch (error) {
    console.error('Fetch error:', error);
    throw error;
  }
};

const showToast = (message, type = 'info') => {
  const toast = document.getElementById('toast');
  if (!toast) return;

  toast.className = `toast toast--${type}`;
  toast.textContent = message;
  toast.hidden = false;

  setTimeout(() => {
    toast.hidden = true;
  }, 4000);
};

const setLoading = (isLoading) => {
  AppState.isLoading = isLoading;
  const loader = document.getElementById('screen-loader');
  if (loader) {
    loader.hidden = !isLoading;
  }
};

const updateConnectionStatus = (status, label) => {
  const indicator = document.getElementById('connection-indicator');
  const labelElement = document.getElementById('connection-label');

  if (indicator) {
    indicator.className = `status-dot status-dot--${status}`;
  }

  if (labelElement) {
    labelElement.textContent = label;
  }
};

const updateLastUpdated = () => {
  const element = document.getElementById('last-updated');
  if (element) {
    const now = new Date();
    element.textContent = now.toLocaleString();
    element.dateTime = now.toISOString();
    AppState.lastUpdated = now;
  }
};

// Tab Management
const TabManager = {
  init() {
    const tabButtons = document.querySelectorAll('.tab-button');
    tabButtons.forEach(button => {
      button.addEventListener('click', (e) => {
        const tabId = e.currentTarget.dataset.tab;
        this.switchTab(tabId);
      });
    });

    // Initialize with first tab
    this.switchTab('setup');
  },

  switchTab(tabId) {
    // Update button states
    document.querySelectorAll('.tab-button').forEach(btn => {
      const isActive = btn.dataset.tab === tabId;
      btn.classList.toggle('active', isActive);
      btn.setAttribute('aria-selected', isActive);
    });

    // Update panel states
    document.querySelectorAll('.tab-panel').forEach(panel => {
      const isActive = panel.id === `panel-${tabId}`;
      panel.classList.toggle('active', isActive);
    });

    AppState.currentTab = tabId;

    // Load tab-specific data
    this.loadTabData(tabId);
  },

  async loadTabData(tabId) {
    switch (tabId) {
      case 'executions':
        await ExecutionsManager.refresh();
        break;
      case 'monitoring':
        await MonitoringManager.refresh();
        break;
      case 'allocation':
        await AllocationManager.refresh();
        break;
    }
  }
};

// Strategy Setup Manager
const SetupManager = {
  init() {
    this.initProductSelection();
    this.initStrategySelection();
    this.initDirectionSelection();
    this.initLeverageSelection();
    this.initCapitalAllocation();
    this.initActionButtons();
    this.loadCurrentConfiguration();
  },

  initProductSelection() {
    const productItems = document.querySelectorAll('.product-item');
    productItems.forEach(item => {
      item.addEventListener('click', (e) => {
        // Remove previous selection
        productItems.forEach(p => p.classList.remove('selected'));

        // Add selection to clicked item
        e.target.classList.add('selected');

        const product = e.target.dataset.product;
        AppState.configuration.product = product;

        // Update display
        document.getElementById('selected-product').textContent = product;

        // Update hero metrics
        document.getElementById('hero-product').textContent = product;
      });
    });
  },

  initStrategySelection() {
    const strategyItems = document.querySelectorAll('.strategy-item');
    strategyItems.forEach(item => {
      item.addEventListener('click', (e) => {
        // Remove previous selection
        strategyItems.forEach(s => s.classList.remove('selected'));

        // Add selection to clicked item
        e.target.classList.add('selected');

        const strategy = e.target.dataset.strategy;
        AppState.configuration.strategy = strategy;

        // Update display
        document.getElementById('selected-strategy').textContent = strategy;

        // Update hero metrics
        document.getElementById('hero-strategy').textContent = strategy;
      });
    });
  },

  initDirectionSelection() {
    const directionInputs = document.querySelectorAll('input[name="direction"]');
    directionInputs.forEach(input => {
      input.addEventListener('change', (e) => {
        if (e.target.checked) {
          AppState.configuration.direction = e.target.value;
          this.updateHeroMetrics();
        }
      });
    });
  },

  initLeverageSelection() {
    const leverageItems = document.querySelectorAll('.leverage-item');
    leverageItems.forEach(item => {
      item.addEventListener('click', (e) => {
        // Remove previous selection
        leverageItems.forEach(l => l.classList.remove('selected'));

        // Add selection to clicked item
        e.target.classList.add('selected');

        const leverage = parseFloat(e.target.dataset.leverage);
        AppState.configuration.leverage = leverage;

        // Update display
        document.getElementById('selected-leverage').textContent = `${leverage}x`;
      });
    });
  },

  initCapitalAllocation() {
    const slider = document.getElementById('capital-slider');
    const display = document.getElementById('allocation-value');
    const presets = document.querySelectorAll('.preset-btn');

    if (slider && display) {
      slider.addEventListener('input', (e) => {
        const value = parseInt(e.target.value);
        AppState.configuration.capitalAllocation = value;
        display.textContent = `${value}%`;
        this.updateHeroMetrics();
      });
    }

    presets.forEach(preset => {
      preset.addEventListener('click', (e) => {
        const value = parseInt(e.target.dataset.allocation);
        AppState.configuration.capitalAllocation = value;
        if (slider) slider.value = value;
        if (display) display.textContent = `${value}%`;
        this.updateHeroMetrics();
      });
    });
  },

  initActionButtons() {
    const saveBtn = document.getElementById('save-config');
    const resetBtn = document.getElementById('reset-config');

    if (saveBtn) {
      saveBtn.addEventListener('click', () => this.saveConfiguration());
    }

    if (resetBtn) {
      resetBtn.addEventListener('click', () => this.resetConfiguration());
    }
  },

  async saveConfiguration() {
    try {
      setLoading(true);
      updateConnectionStatus('loading', 'Saving...');

      // Save each configuration item
      if (AppState.configuration.product) {
        await fetchJson('/preferences/product', {
          method: 'POST',
          body: JSON.stringify({ product: AppState.configuration.product })
        });
      }

      if (AppState.configuration.strategy) {
        await fetchJson('/preferences/strategy', {
          method: 'POST',
          body: JSON.stringify({ strategy: AppState.configuration.strategy })
        });
      }

      if (AppState.configuration.direction) {
        await fetchJson('/preferences/direction', {
          method: 'POST',
          body: JSON.stringify({ direction_mode: AppState.configuration.direction })
        });
      }

      if (AppState.configuration.leverage) {
        await fetchJson('/preferences/leverage', {
          method: 'POST',
          body: JSON.stringify({ leverage: AppState.configuration.leverage })
        });
      }

      if (AppState.configuration.capitalAllocation) {
        await fetchJson('/preferences/capital', {
          method: 'POST',
          body: JSON.stringify({ capital_allocation_percent: AppState.configuration.capitalAllocation })
        });
      }

      updateConnectionStatus('ready', 'Saved');
      updateLastUpdated();
      showToast('Configuration saved successfully', 'success');

    } catch (error) {
      console.error('Save error:', error);
      updateConnectionStatus('error', 'Save failed');
      showToast(error.message || 'Failed to save configuration', 'error');
    } finally {
      setLoading(false);
    }
  },

  async resetConfiguration() {
    try {
      setLoading(true);
      await this.loadCurrentConfiguration();
      showToast('Configuration reset to server values', 'info');
    } catch (error) {
      console.error('Reset error:', error);
      showToast('Failed to reset configuration', 'error');
    } finally {
      setLoading(false);
    }
  },

  async loadCurrentConfiguration() {
    try {
      updateConnectionStatus('loading', 'Loading...');

      const [options, preferences] = await Promise.all([
        fetchJson('/preferences/options'),
        fetchJson('/preferences/current')
      ]);

      // Update configuration from server
      if (preferences.product) {
        AppState.configuration.product = preferences.product;
        this.selectProduct(preferences.product);
      }

      if (preferences.strategy) {
        AppState.configuration.strategy = preferences.strategy;
        this.selectStrategy(preferences.strategy);
      }

      if (preferences.direction_mode) {
        AppState.configuration.direction = preferences.direction_mode;
        this.selectDirection(preferences.direction_mode);
      }

      if (preferences.leverage) {
        AppState.configuration.leverage = preferences.leverage;
        this.selectLeverage(preferences.leverage);
      }

      if (preferences.capital_allocation_percent) {
        AppState.configuration.capitalAllocation = preferences.capital_allocation_percent;
        this.setCapitalAllocation(preferences.capital_allocation_percent);
      }

      this.updateHeroMetrics();
      updateConnectionStatus('ready', 'Up to date');
      updateLastUpdated();

    } catch (error) {
      console.error('Load error:', error);
      updateConnectionStatus('error', 'Failed to load');
      showToast('Failed to load configuration', 'error');
    }
  },

  selectProduct(product) {
    document.querySelectorAll('.product-item').forEach(item => {
      const isSelected = item.dataset.product === product;
      item.classList.toggle('selected', isSelected);
    });
    document.getElementById('selected-product').textContent = product;
  },

  selectStrategy(strategy) {
    document.querySelectorAll('.strategy-item').forEach(item => {
      const isSelected = item.dataset.strategy === strategy;
      item.classList.toggle('selected', isSelected);
    });
    document.getElementById('selected-strategy').textContent = strategy;
  },

  selectDirection(direction) {
    const input = document.querySelector(`input[name="direction"][value="${direction}"]`);
    if (input) {
      input.checked = true;
    }
  },

  selectLeverage(leverage) {
    document.querySelectorAll('.leverage-item').forEach(item => {
      const isSelected = parseFloat(item.dataset.leverage) === leverage;
      item.classList.toggle('selected', isSelected);
    });
    document.getElementById('selected-leverage').textContent = `${leverage}x`;
  },

  setCapitalAllocation(allocation) {
    const slider = document.getElementById('capital-slider');
    const display = document.getElementById('allocation-value');

    if (slider) slider.value = allocation;
    if (display) display.textContent = `${allocation}%`;
  },

  updateHeroMetrics() {
    const { product, strategy, direction, capitalAllocation } = AppState.configuration;

    document.getElementById('hero-product').textContent = product || '--';
    document.getElementById('hero-strategy').textContent = strategy || '--';

    // Update long/short based on direction
    let longText = 'Off', shortText = 'Off';

    if (direction === 'allow_long_short') {
      longText = `${(capitalAllocation / 2).toFixed(1)}%`;
      shortText = `${(capitalAllocation / 2).toFixed(1)}%`;
    } else if (direction === 'allow_long_only') {
      longText = `${capitalAllocation}%`;
    } else if (direction === 'allow_short_only') {
      shortText = `${capitalAllocation}%`;
    }

    document.getElementById('hero-long').textContent = longText;
    document.getElementById('hero-short').textContent = shortText;
    document.getElementById('hero-total-allocation').textContent = `${capitalAllocation}%`;
  }
};

// Executions Manager
const ExecutionsManager = {
  init() {
    this.initControls();
    this.startAutoRefresh();
  },

  initControls() {
    const toggleTiming = document.getElementById('toggle-timing');
    const toggleDetails = document.getElementById('toggle-details');
    const refreshBtn = document.getElementById('refresh-executions');

    if (toggleTiming) {
      toggleTiming.addEventListener('click', () => {
        this.showTiming = !this.showTiming;
        toggleTiming.textContent = this.showTiming ? 'Hide Timing' : 'Show Timing';
        this.render();
      });
    }

    if (toggleDetails) {
      toggleDetails.addEventListener('click', () => {
        this.showDetails = !this.showDetails;
        toggleDetails.textContent = this.showDetails ? 'Hide Details' : 'Show Details';
        this.render();
      });
    }

    if (refreshBtn) {
      refreshBtn.addEventListener('click', () => this.refresh());
    }
  },

  async refresh() {
    try {
      const executions = await fetchJson('/executions?limit=50');
      AppState.executions = Array.isArray(executions) ? executions : [];
      this.render();
      updateLastUpdated();
    } catch (error) {
      console.error('Executions refresh error:', error);
      showToast('Failed to refresh executions', 'error');
    }
  },

  render() {
    const container = document.getElementById('execution-log');
    const countElement = document.getElementById('executions-count');

    if (!container) return;

    // Update count
    if (countElement) {
      const count = AppState.executions.length;
      countElement.textContent = `${count} execution${count !== 1 ? 's' : ''}`;
    }

    // Clear and render executions
    container.innerHTML = '';

    if (AppState.executions.length === 0) {
      const emptyState = document.createElement('li');
      emptyState.className = 'empty-state';
      emptyState.textContent = 'No trade executions yet.';
      container.appendChild(emptyState);
      return;
    }

    AppState.executions.forEach(execution => {
      const item = this.createExecutionItem(execution);
      container.appendChild(item);
    });
  },

  createExecutionItem(execution) {
    const item = document.createElement('li');
    item.className = 'execution-item';

    const statusClass = execution.status === 'success' ? 'success' :
                       execution.status === 'failed' ? 'error' : 'warning';

    const statusLabel = execution.status === 'success' ? '✓ FILLED' :
                       execution.status === 'failed' ? '✗ FAILED' : '⚠ IGNORED';

    const timestamp = execution.execution_time || execution.timestamp;
    const timeDisplay = timestamp ? new Date(timestamp).toLocaleString() : '--';

    item.innerHTML = `
      <div class="execution-header">
        <span class="execution-status ${statusClass}">${statusLabel}</span>
        <span class="execution-action">${(execution.action || '').toUpperCase()} ${execution.symbol || ''}</span>
        <span class="execution-time">${timeDisplay}</span>
      </div>
      <div class="execution-details">
        <span>Qty: ${execution.quantity || '--'}</span>
        <span>Order: ${execution.order_id || '--'}</span>
      </div>
    `;

    return item;
  },

  startAutoRefresh() {
    // Refresh every 5 seconds
    setInterval(() => {
      if (AppState.currentTab === 'executions') {
        this.refresh();
      }
    }, 5000);
  },

  showTiming: false,
  showDetails: false
};

// Monitoring Manager
const MonitoringManager = {
  async refresh() {
    try {
      // Refresh account summary
      const accountData = await fetchJson('/account/summary');
      if (accountData && accountData.status === 'success') {
        this.updateAccountSummary(accountData.data);
      }

      // Update strategy status from current preferences
      const preferences = await fetchJson('/preferences/current');
      this.updateStrategyStatus(preferences);

      updateLastUpdated();
    } catch (error) {
      console.error('Monitoring refresh error:', error);
    }
  },

  updateAccountSummary(data) {
    const walletElement = document.getElementById('wallet-balance');
    const availableElement = document.getElementById('available-balance');

    if (walletElement) {
      walletElement.textContent = data.wallet_balance ?
        `$${parseFloat(data.wallet_balance).toFixed(2)}` : '--';
    }

    if (availableElement) {
      availableElement.textContent = data.available_balance ?
        `$${parseFloat(data.available_balance).toFixed(2)}` : '--';
    }

    // Update hero metrics
    document.getElementById('hero-wallet').textContent =
      data.wallet_balance ? `$${parseFloat(data.wallet_balance).toFixed(2)}` : '--';
    document.getElementById('hero-available').textContent =
      data.available_balance ? `$${parseFloat(data.available_balance).toFixed(2)}` : '--';
  },

  updateStrategyStatus(preferences) {
    document.getElementById('active-product').textContent = preferences.product || '--';
    document.getElementById('active-strategy').textContent = preferences.strategy || '--';

    const directionLabels = {
      'allow_long_short': 'Long & Short',
      'allow_long_only': 'Long Only',
      'allow_short_only': 'Short Only'
    };

    document.getElementById('position-mode').textContent =
      directionLabels[preferences.direction_mode] || '--';
  }
};

// Allocation Manager
const AllocationManager = {
  async refresh() {
    try {
      const preferences = await fetchJson('/preferences/current');
      this.updateAllocationDisplay(preferences);
    } catch (error) {
      console.error('Allocation refresh error:', error);
    }
  },

  updateAllocationDisplay(preferences) {
    const primaryDisplay = document.getElementById('primary-strategy-display');
    const primarySlider = document.getElementById('primary-allocation');
    const primaryInput = document.getElementById('primary-allocation-input');

    if (primaryDisplay) {
      primaryDisplay.textContent = preferences.strategy || '--';
    }

    if (preferences.capital_allocation_percent) {
      if (primarySlider) primarySlider.value = preferences.capital_allocation_percent;
      if (primaryInput) primaryInput.value = preferences.capital_allocation_percent;
    }

    this.updateAllocationBreakdown(preferences);
  },

  updateAllocationBreakdown(preferences) {
    const longElement = document.getElementById('primary-long-allocation');
    const shortElement = document.getElementById('primary-short-allocation');
    const totalElement = document.getElementById('master-total');

    if (!preferences.capital_allocation_percent) return;

    let longPercent = 0, shortPercent = 0;
    const totalAllocation = preferences.capital_allocation_percent;

    if (preferences.direction_mode === 'allow_long_short') {
      longPercent = totalAllocation / 2;
      shortPercent = totalAllocation / 2;
    } else if (preferences.direction_mode === 'allow_long_only') {
      longPercent = totalAllocation;
    } else if (preferences.direction_mode === 'allow_short_only') {
      shortPercent = totalAllocation;
    }

    if (longElement) longElement.textContent = `${longPercent.toFixed(1)}%`;
    if (shortElement) shortElement.textContent = `${shortPercent.toFixed(1)}%`;
    if (totalElement) totalElement.textContent = `${totalAllocation}%`;
  }
};

// Application Initialization
document.addEventListener('DOMContentLoaded', async () => {
  try {
    console.log('🚀 Initializing AlsaTrade Dashboard...');

    // Initialize all managers
    TabManager.init();
    SetupManager.init();
    ExecutionsManager.init();

    // Load initial data
    await SetupManager.loadCurrentConfiguration();

    console.log('✅ Dashboard initialized successfully');

  } catch (error) {
    console.error('❌ Dashboard initialization failed:', error);
    showToast('Failed to initialize dashboard', 'error');
  }
});