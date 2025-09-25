const directionLabels = {
  allow_long_short: "Allow Long & Short",
  allow_long_only: "Allow Long Only",
  allow_short_only: "Allow Short Only",
};

const tradingState = {
  longActive: false,
  shortActive: false,
  longLeverage: 1,
  shortLeverage: 1,
  longAllocation: 0,
  shortAllocation: 0,
  strategies: []
};

let showTimingDetails = false;
let showExecutionDetails = false;


const MAX_ACTIVITY_ITEMS = 8;
const EXECUTION_REFRESH_INTERVAL = 5000;
const ACCOUNT_REFRESH_INTERVAL = 15000;
let toastTimeout;
let executionRefreshTimer;
let accountRefreshTimer;
let executionLogElement;

async function fetchJson(url, options) {
  const response = await fetch(url, {
    headers: { "Content-Type": "application/json" },
    ...(options ?? {}),
  });

  const contentType = response.headers.get("content-type") || "";

  if (!response.ok) {
    if (contentType.includes("application/json")) {
      const data = await response.json().catch(() => null);
      const message = data?.detail || data?.message || "Request failed";
      throw new Error(message);
    }
    const message = await response.text();
    throw new Error(message || "Request failed");
  }

  if (!contentType.includes("application/json")) {
    return null;
  }

  return response.json();
}

function updateSummary(preference = {}) {
  // Get primary strategy allocation
  const primarySlider = document.getElementById('primary-allocation-slider');
  const primaryAllocation = primarySlider ? Number(primarySlider.value) || 0 : 0;

  // Calculate actual capital allocations (primary allocation × split percentages)
  const actualLongAllocation = (primaryAllocation * tradingState.longAllocation) / 100;
  const actualShortAllocation = (primaryAllocation * tradingState.shortAllocation) / 100;
  const actualTotalAllocation = actualLongAllocation + actualShortAllocation;

  // Update summary fields
  document.getElementById("summary-product").textContent = preference.product ?? "--";
  document.getElementById("summary-strategy").textContent = preference.strategy ?? "--";

  // Update trading state display (show actual capital allocations)
  document.getElementById("summary-long-active").textContent = tradingState.longActive ? "Yes" : "No";
  document.getElementById("summary-short-active").textContent = tradingState.shortActive ? "Yes" : "No";
  document.getElementById("summary-long-allocation").textContent = `${actualLongAllocation.toFixed(1)}%`;
  document.getElementById("summary-short-allocation").textContent = `${actualShortAllocation.toFixed(1)}%`;
  document.getElementById("summary-total-allocation").textContent = `${actualTotalAllocation.toFixed(1)}%`;

  // Update hero metrics (show actual capital allocations)
  document.getElementById("hero-product").textContent = preference.product ?? "--";
  document.getElementById("hero-strategy").textContent = preference.strategy ?? "--";
  document.getElementById("hero-long").textContent = tradingState.longActive
    ? `${actualLongAllocation.toFixed(1)}%`
    : "Off";
  document.getElementById("hero-short").textContent = tradingState.shortActive
    ? `${actualShortAllocation.toFixed(1)}%`
    : "Off";
  // hero-total-allocation will be updated by updateMasterAllocation()
}

function setSelectedValue(selectEl, value) {
  if (!selectEl) {
    return;
  }
  const stringValue = value == null ? "" : String(value);
  const option = Array.from(selectEl.options).find((opt) => opt.value === stringValue);
  selectEl.value = option ? stringValue : "";
  selectEl.dataset.currentValue = selectEl.value;
}

function formatDateTime(date) {
  // Use browser's local time zone (no forced IST conversion)
  try {
    return date.toLocaleString("en-IN", {
      day: "2-digit",
      month: "short",
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
      hour12: true
    });
  } catch (error) {
    console.warn('Date formatting error:', error);
    // Fallback to basic formatting
    return date.toLocaleString();
  }
}

function formatTime(date) {
  // Use browser's local time zone (no forced IST conversion)
  return date.toLocaleTimeString("en-IN", {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hour12: true
  });
}

function parseUTCDateTime(timeValue) {
  if (!timeValue) return null;

  if (typeof timeValue === 'string') {
    // If the string doesn't have timezone info, treat as UTC
    if (
      !timeValue.includes('Z') &&
      !timeValue.includes('+') &&
      !timeValue.includes('-', 10)
    ) {
      // Handle both "YYYY-MM-DDTHH:MM:SS" and "YYYY-MM-DD HH:MM:SS"
      let iso = timeValue.replace(' ', 'T');
      if (/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}$/.test(iso)) {
        iso += 'Z';
      }
      return new Date(iso);
    } else {
      return new Date(timeValue);
    }
  } else {
    return new Date(timeValue);
  }
}

function formatCurrency(value, { minimumFractionDigits = 2, maximumFractionDigits = 2 } = {}) {
  if (value == null || Number.isNaN(Number(value))) {
    return "--";
  }
  return Number(value).toLocaleString(undefined, {
    minimumFractionDigits,
    maximumFractionDigits,
  });
}

function inferEnvironmentLabel() {
  const hostname = window.location.hostname;
  if (!hostname) {
    return "";
  }
  if (hostname === "localhost" || hostname === "127.0.0.1") {
    return "Local";
  }
  if (hostname.includes("dev")) {
    return "Dev";
  }
  if (hostname.includes("staging")) {
    return "Staging";
  }
  return hostname;
}

async function initialize() {
  const productSelect = document.getElementById("product-select");
  const strategySelect = document.getElementById("strategy-select");
  const longToggle = document.getElementById("long-toggle");
  const shortToggle = document.getElementById("short-toggle");
  const longLeverageSelect = document.getElementById("long-leverage-select");
  const shortLeverageSelect = document.getElementById("short-leverage-select");
  const longCapitalRange = document.getElementById("long-capital-range");
  const shortCapitalRange = document.getElementById("short-capital-range");
  const longCapitalValue = document.getElementById("long-capital-value");
  const shortCapitalValue = document.getElementById("short-capital-value");
  const totalAllocationSpan = document.getElementById("total-allocation");
  const allocationWarning = document.getElementById("allocation-warning");
  const addStrategyBtn = document.getElementById("add-strategy-btn");
  const strategiesList = document.getElementById("strategies-list");
  const toggleTimingBtn = document.getElementById("toggle-timing-btn");
  const toggleDetailsBtn = document.getElementById("toggle-details-btn");
  const executionCount = document.getElementById("execution-count");

  const connectionIndicator = document.getElementById("connection-indicator");
  const connectionLabel = document.getElementById("connection-label");
  const lastUpdated = document.getElementById("last-updated");
  const screenLoader = document.getElementById("screen-loader");
  const toast = document.getElementById("toast");
  const activityLog = document.getElementById("activity-log");
  const refreshButton = document.getElementById("refresh-options");
  const resetButton = document.getElementById("reset-preferences");
  const environmentPill = document.getElementById("environment-pill");
  const summaryAccountBalance = document.getElementById("summary-account-balance");
  const summaryAccountAvailable = document.getElementById("summary-account-available");
  executionLogElement = document.getElementById("execution-log");

  const controls = [
    productSelect,
    strategySelect,
    longToggle,
    shortToggle,
    longLeverageSelect,
    shortLeverageSelect,
    longCapitalRange,
    shortCapitalRange,
    addStrategyBtn,
  ];

  function setInputsDisabled(isDisabled) {
    controls.forEach((control) => {
      if (control) {
        control.disabled = isDisabled;
      }
    });
    if (refreshButton) {
      refreshButton.disabled = isDisabled;
    }
    if (resetButton) {
      resetButton.disabled = isDisabled;
    }
  }

  function toggleScreenLoader(show) {
    if (screenLoader) {
      screenLoader.hidden = !show;
    }
  }

  function setConnectionState(state, label) {
    if (connectionIndicator) {
      connectionIndicator.classList.remove(
        "status-dot--loading",
        "status-dot--ready",
        "status-dot--error"
      );
      connectionIndicator.classList.add(`status-dot--${state}`);
    }
    if (connectionLabel) {
      connectionLabel.textContent = label;
    }
  }

  function setLastUpdated(date) {
    if (!lastUpdated) {
      return;
    }
    lastUpdated.textContent = formatDateTime(date);
    lastUpdated.dateTime = date.toISOString();
  }

  function showToast(message, variant = "info") {
    if (!toast) {
      return;
    }
    window.clearTimeout(toastTimeout);
    toast.classList.remove("toast--info", "toast--success", "toast--error");
    toast.classList.add(`toast--${variant}`);
    toast.textContent = message;
    toast.hidden = false;
    toastTimeout = window.setTimeout(() => {
      toast.hidden = true;
    }, 4000);
  }

  function logActivity(action, value) {
    if (!activityLog) {
      return;
    }
    const placeholder = activityLog.querySelector(".activity-placeholder");
    if (placeholder) {
      placeholder.remove();
    }
    const item = document.createElement("li");
    const time = document.createElement("span");
    time.className = "activity-time";
    time.textContent = formatTime(new Date());
    const message = document.createElement("span");
    message.className = "activity-message";
    if (value) {
      message.innerHTML = `<strong>${action}</strong> ${value}`;
    } else {
      message.innerHTML = `<strong>${action}</strong>`;
    }
    item.append(time, message);
    activityLog.prepend(item);
    while (activityLog.children.length > MAX_ACTIVITY_ITEMS) {
      activityLog.removeChild(activityLog.lastElementChild);
    }
  }

  function renderExecutionLog(entries) {
    if (!executionLogElement) {
      return;
    }

    // Update execution count
    if (executionCount) {
      const count = entries ? entries.length : 0;
      executionCount.textContent = `${count} execution${count !== 1 ? 's' : ''}`;
    }

    executionLogElement.innerHTML = "";
    if (!entries || entries.length === 0) {
      const placeholder = document.createElement('li');
      placeholder.className = 'activity-placeholder';
      placeholder.textContent = 'No executions yet.';
      executionLogElement.appendChild(placeholder);
      return;
    }

    entries.forEach((entry) => {
      const item = document.createElement('li');
      item.className = 'execution-item';
      const statusValue = (entry?.status ?? 'unknown').toString();
      item.dataset.status = statusValue;

      // Enhanced main execution info with comprehensive data
      const mainInfo = document.createElement('div');
      mainInfo.className = 'execution-main';

      // Status badge
      const statusEl = document.createElement('span');
      statusEl.className = `execution-status status-${statusValue}`;
      let statusLabel;
      if (statusValue === 'success') {
        statusLabel = '✓ FILLED';
      } else if (statusValue === 'failed') {
        statusLabel = '✗ FAILED';
      } else if (statusValue === 'ignored') {
        statusLabel = '⚠ IGNORED';
      } else {
        statusLabel = statusValue.toUpperCase();
      }
      statusEl.textContent = statusLabel || 'UNKNOWN';

      // Trade info with more details
      const tradeInfo = document.createElement('div');
      tradeInfo.className = 'execution-trade-info';

      const action = entry?.action?.toString().toUpperCase() || 'N/A';
      const symbol = entry?.symbol || 'N/A';
      const quantity = entry?.quantity != null ?
        formatCurrency(Number(entry.quantity), {minimumFractionDigits: 0, maximumFractionDigits: 8}) : 'N/A';
      const orderId = entry?.order_id || 'N/A';

      tradeInfo.innerHTML = `
        <div class="trade-primary"><strong>${action} ${symbol}</strong></div>
        <div class="trade-secondary">Qty: ${quantity} | Order: ${orderId}</div>
      `;

      // Enhanced time display with multiple timestamps
      const timeInfo = document.createElement('div');
      timeInfo.className = 'execution-time-info';

      const timeValue = entry?.execution_time || entry?.timestamp;
      if (timeValue) {
        const parsed = parseUTCDateTime(timeValue);
        if (parsed && !Number.isNaN(parsed.getTime())) {
          const executionTime = formatDateTime(parsed);

          // Show additional timing if available
          const receivedTime = entry?.received_time ? parseUTCDateTime(entry.received_time) : null;
          const processTime = receivedTime && parsed ? parsed.getTime() - receivedTime.getTime() : null;

          timeInfo.innerHTML = `
            <div class="time-primary">${executionTime}</div>
            ${processTime ? `<div class="time-secondary">Processed in ${processTime}ms</div>` : ''}
          `;
        } else {
          timeInfo.innerHTML = '<div class="time-primary">--</div>';
        }
      } else {
        timeInfo.innerHTML = '<div class="time-primary">--</div>';
      }

      mainInfo.appendChild(statusEl);
      mainInfo.appendChild(tradeInfo);
      mainInfo.appendChild(timeInfo);
      item.appendChild(mainInfo);

      // Detailed execution info (collapsible)
      if (showExecutionDetails) {
        const detailsDiv = document.createElement('div');
        detailsDiv.className = 'execution-details show';

        const detailsGrid = document.createElement('div');
        detailsGrid.className = 'execution-details-grid';

        // Add comprehensive execution details from database schema
        const details = [
          { label: 'Execution ID', value: entry?.id },
          { label: 'Order ID', value: entry?.order_id },
          { label: 'Action', value: entry?.action?.toUpperCase() },
          { label: 'Symbol', value: entry?.symbol },
          { label: 'Requested Qty', value: entry?.quantity ? formatCurrency(entry.quantity, {minimumFractionDigits: 0, maximumFractionDigits: 8}) : null },
          { label: 'Executed Price', value: entry?.executed_price ? `$${formatCurrency(entry.executed_price, {minimumFractionDigits: 2, maximumFractionDigits: 8})}` : null },
          { label: 'Executed Qty', value: entry?.executed_quantity ? formatCurrency(entry.executed_quantity, {minimumFractionDigits: 0, maximumFractionDigits: 8}) : null },
          { label: 'Fees Paid', value: entry?.fees ? `$${formatCurrency(entry.fees, {minimumFractionDigits: 4, maximumFractionDigits: 8})}` : null },
          { label: 'Commission Asset', value: entry?.commission_asset },
          { label: 'Applied Leverage', value: entry?.leverage ? `${entry.leverage}x` : null },
          { label: 'Capital Allocation', value: entry?.capital_percent ? `${entry.capital_percent}%` : null },
          { label: 'Status', value: entry?.status?.toUpperCase() },
          { label: 'Created At', value: entry?.created_at ? formatDateTime(parseUTCDateTime(entry.created_at)) : null }
        ];

        // Error information
        if (entry?.error_message) {
          details.push({ label: 'Error Message', value: entry.error_message, isError: true });
        }
        if (entry?.error_code) {
          details.push({ label: 'Error Code', value: entry.error_code, isError: true });
        }

        // Timing summary
        const timingStats = [];
        if (entry?.received_time && entry?.processed_time) {
          const received = parseUTCDateTime(entry.received_time);
          const processed = parseUTCDateTime(entry.processed_time);
          if (received && processed) {
            const processingTime = processed.getTime() - received.getTime();
            timingStats.push({ label: 'Processing Time', value: `${processingTime}ms` });
          }
        }
        if (entry?.sent_to_binance_time && entry?.binance_executed_time) {
          const sent = parseUTCDateTime(entry.sent_to_binance_time);
          const executed = parseUTCDateTime(entry.binance_executed_time);
          if (sent && executed) {
            const executionTime = executed.getTime() - sent.getTime();
            timingStats.push({ label: 'Binance Execution Time', value: `${executionTime}ms` });
          }
        }

        details.push(...timingStats);

        details.forEach(detail => {
          if (detail.value) {
            const detailEl = document.createElement('div');
            detailEl.className = `execution-detail-item ${detail.isError ? 'detail-error' : ''}`;
            detailEl.innerHTML = `
              <span class="detail-label">${detail.label}:</span>
              <span class="detail-value ${detail.isError ? 'error-text' : ''}">${detail.value}</span>
            `;
            detailsGrid.appendChild(detailEl);
          }
        });

        detailsDiv.appendChild(detailsGrid);
        item.appendChild(detailsDiv);
      }

      // Timing information (collapsible)
      if (showTimingDetails) {
        const timingDiv = document.createElement('div');
        timingDiv.className = 'execution-timing show';

        const timingGrid = document.createElement('div');
        timingGrid.className = 'timing-grid';

        const timingSteps = [
          { label: 'Signal Sent', value: entry?.signal_sent_time },
          { label: 'Received', value: entry?.received_time },
          { label: 'Processed', value: entry?.processed_time },
          { label: 'Sent to Binance', value: entry?.sent_to_binance_time },
          { label: 'Binance Executed', value: entry?.binance_executed_time }
        ];

        timingSteps.forEach(step => {
          if (step.value) {
            const stepDiv = document.createElement('div');
            stepDiv.className = 'timing-step';

            const parsed = parseUTCDateTime(step.value);

            // Calculate relative time
            const baseTime = entry?.signal_sent_time || entry?.timestamp;
            let relativeTime = '';
            if (baseTime && parsed && !Number.isNaN(parsed.getTime())) {
              const baseParsed = parseUTCDateTime(baseTime);
              if (baseParsed && !Number.isNaN(baseParsed.getTime())) {
                const timeDiff = parsed.getTime() - baseParsed.getTime();
                relativeTime = ` (+${timeDiff}ms)`;
              }
            }

            const timeText = parsed && !Number.isNaN(parsed.getTime()) ?
              `${formatDateTime(parsed)}${relativeTime}` :
              step.value;

            stepDiv.innerHTML = `
              <span class="timing-label">${step.label}:</span>
              <span class="timing-value">${timeText}</span>
            `;
            timingGrid.appendChild(stepDiv);
          }
        });

        timingDiv.appendChild(timingGrid);
        item.appendChild(timingDiv);
      }

      executionLogElement.appendChild(item);
    });
  }

  function updateAccountSummary(summary) {
    if (!summaryAccountBalance && !summaryAccountAvailable) {
      return;
    }
    const walletText = formatCurrency(summary?.wallet_balance);
    const availableText = formatCurrency(summary?.available_balance);
    if (summaryAccountBalance) {
      summaryAccountBalance.textContent = walletText;
    }
    if (summaryAccountAvailable) {
      summaryAccountAvailable.textContent = availableText;
    }
    // Also update hero metrics for wallet and available
    const heroWallet = document.getElementById("hero-wallet");
    const heroAvailable = document.getElementById("hero-available");
    if (heroWallet) {
      heroWallet.textContent = walletText;
    }
    if (heroAvailable) {
      heroAvailable.textContent = availableText;
    }
  }

  const refreshAccountSummary = async ({ showErrors = false } = {}) => {
    if (!summaryAccountBalance && !summaryAccountAvailable) {
      return;
    }
    try {
      const payload = await fetchJson('/account/summary');
      if (payload?.status === 'success') {
        updateAccountSummary(payload.data || {});
      } else if (showErrors) {
        const message = payload?.message || 'Failed to load account summary';
        showToast(message, 'error');
      }
    } catch (error) {
      console.error(error);
      if (showErrors) {
        showToast(error.message || 'Failed to load account summary', 'error');
      }
    }
  };

  const refreshExecutions = async ({ showErrors = false } = {}) => {
    if (!executionLogElement) {
      return;
    }
    try {
      const executions = await fetchJson('/executions?limit=50'); // Get more recent data
      renderExecutionLog(Array.isArray(executions) ? executions : []);
    } catch (error) {
      console.error(error);
      if (showErrors) {
        showToast(error.message || 'Failed to load executions', 'error');
      }
    }
  };

  function markControlBusy(control, isBusy) {
    if (!control) {
      return;
    }
    control.classList.toggle("is-busy", isBusy);
    if (isBusy) {
      control.setAttribute("aria-busy", "true");
      control.disabled = true;
    } else {
      control.setAttribute("aria-busy", "false");
      control.disabled = false;
    }
  }

  async function loadOptionsAndPreference({ showNotice } = {}) {
    toggleScreenLoader(true);
    setInputsDisabled(true);
    setConnectionState("loading", "Syncing...");
    try {
      const [options, preference] = await Promise.all([
        fetchJson("/preferences/options"),
        fetchJson("/preferences/current"),
      ]);

      const environmentLabel = options?.environment_label ?? inferEnvironmentLabel();
      if (environmentPill) {
        if (environmentLabel) {
          environmentPill.textContent = environmentLabel;
          environmentPill.hidden = false;
        } else {
          environmentPill.hidden = true;
        }
      }

      const addOptions = (selectEl, values, formatter = (value) => value) => {
        if (!selectEl) {
          return;
        }
        selectEl.innerHTML = '<option value="">Select...</option>';
        values.forEach((value) => {
          const option = document.createElement("option");
          option.value = String(value);
          option.textContent = formatter(value);
          selectEl.appendChild(option);
        });
      };

      addOptions(productSelect, options.products ?? []);
      addOptions(strategySelect, options.strategies ?? []);
      addOptions(longLeverageSelect, options.leverages ?? [], (value) => `${Number(value).toFixed(1)}x`);
      addOptions(shortLeverageSelect, options.leverages ?? [], (value) => `${Number(value).toFixed(1)}x`);

      // Initialize trading state from preferences
      if (preference.direction_mode === 'allow_long_only') {
        tradingState.longActive = true;
        tradingState.shortActive = false;
      } else if (preference.direction_mode === 'allow_short_only') {
        tradingState.longActive = false;
        tradingState.shortActive = true;
      } else if (preference.direction_mode === 'allow_long_short') {
        tradingState.longActive = true;
        tradingState.shortActive = true;
      }

      if (preference.leverage != null) {
        tradingState.longLeverage = preference.leverage;
        tradingState.shortLeverage = preference.leverage;
      }

      // Set initial allocations from capital allocation
      if (preference.capital_allocation_percent != null) {
        // Set primary strategy master allocation
        const primarySlider = document.getElementById('primary-allocation-slider');
        const primaryInput = document.getElementById('primary-allocation-input');
        if (primarySlider && primaryInput) {
          primarySlider.value = preference.capital_allocation_percent;
          primaryInput.value = preference.capital_allocation_percent;
        }

        // Set long/short split allocations (these represent the split within the primary allocation)
        if (tradingState.longActive && !tradingState.shortActive) {
          tradingState.longAllocation = 100; // 100% of primary allocation goes to long
          tradingState.shortAllocation = 0;
        } else if (tradingState.shortActive && !tradingState.longActive) {
          tradingState.longAllocation = 0;
          tradingState.shortAllocation = 100; // 100% of primary allocation goes to short
        } else if (tradingState.longActive && tradingState.shortActive) {
          // Split equally between long and short (50% each of primary allocation)
          tradingState.longAllocation = 50;
          tradingState.shortAllocation = 50;
        }
      }

      updateSummary(preference);
      setSelectedValue(productSelect, preference.product);
      setSelectedValue(strategySelect, preference.strategy);
      setSelectedValue(longLeverageSelect, tradingState.longLeverage);
      setSelectedValue(shortLeverageSelect, tradingState.shortLeverage);

      // Initialize UI controls
      updatePositionToggles();
      updateAllocationControls();

      setLastUpdated(new Date());
      setConnectionState("ready", "Up to date");
      if (showNotice) {
        showToast("Configuration refreshed", "success");
      }
    } catch (error) {
      console.error(error);
      setConnectionState("error", "Offline");
      showToast(error.message || "Failed to load data", "error");
    } finally {
      toggleScreenLoader(false);
      setInputsDisabled(false);
    }
  }

  const handleSelectChange = (selectEl, endpoint, buildBody, { success, activity } = {}) => {
    if (!selectEl) {
      return;
    }
    selectEl.addEventListener("change", async () => {
      const nextValue = selectEl.value;
      if (!nextValue) {
        return;
      }
      const previousValue = selectEl.dataset.currentValue || "";
      markControlBusy(selectEl, true);
      try {
        const updated = await fetchJson(endpoint, {
          method: "POST",
          body: JSON.stringify(buildBody(nextValue)),
        });
        selectEl.dataset.currentValue = nextValue;
        updateSummary(updated);
        setLastUpdated(new Date());
        if (typeof success === "function") {
          showToast(success(nextValue), "success");
        }
        if (typeof activity === "function") {
          const [action, value] = activity(nextValue);
          logActivity(action, value);
        }
      } catch (error) {
        console.error(error);
        showToast(error.message || "Something went wrong", "error");
        if (previousValue) {
          setSelectedValue(selectEl, previousValue);
        }
      } finally {
        markControlBusy(selectEl, false);
      }
    });
  };

  handleSelectChange(
    productSelect,
    "/preferences/product",
    (value) => ({ product: value }),
    {
      success: (value) => `Product set to ${value}`,
      activity: (value) => ["Product updated", value],
    }
  );

  handleSelectChange(
    strategySelect,
    "/preferences/strategy",
    (value) => ({ strategy: value }),
    {
      success: (value) => `Strategy set to ${value}`,
      activity: (value) => ["Strategy updated", value],
    }
  );

  // Helper functions
  function updatePositionToggles() {
    const longConfig = document.getElementById("long-config");
    const shortConfig = document.getElementById("short-config");

    if (longConfig) {
      longConfig.classList.toggle("active", tradingState.longActive);
      longConfig.classList.toggle("long", tradingState.longActive);
    }

    if (shortConfig) {
      shortConfig.classList.toggle("active", tradingState.shortActive);
      shortConfig.classList.toggle("short", tradingState.shortActive);
    }
  }

  function updateAllocationControls() {
    if (longCapitalRange && longCapitalValue) {
      longCapitalRange.value = tradingState.longAllocation;
      longCapitalValue.textContent = `${tradingState.longAllocation}%`;
    }

    if (shortCapitalRange && shortCapitalValue) {
      shortCapitalRange.value = tradingState.shortAllocation;
      shortCapitalValue.textContent = `${tradingState.shortAllocation}%`;
    }

    updateTotalAllocation();
  }

  function updateTotalAllocation() {
    const total = tradingState.longAllocation + tradingState.shortAllocation;

    if (totalAllocationSpan) {
      totalAllocationSpan.textContent = `${total}%`;
    }

    if (allocationWarning) {
      // Long/short allocation should always add to 100% (it's a split)
      allocationWarning.style.display = total !== 100 ? 'inline' : 'none';
      if (allocationWarning && total !== 100) {
        allocationWarning.textContent = '⚠️ Long + Short must equal 100%';
      }
    }

    // Update primary strategy name in master allocation
    const primaryStrategyName = document.getElementById('primary-strategy-name');
    const selectedStrategy = document.getElementById('strategy-select')?.value;
    if (primaryStrategyName) {
      primaryStrategyName.textContent = selectedStrategy || '--';
    }

    // Don't auto-sync primary allocation - let user control it independently
    updateMasterAllocation();
    updateSummary();
  }

  async function updateDirectionPreference() {
    let directionMode = "";
    if (tradingState.longActive && tradingState.shortActive) {
      directionMode = "allow_long_short";
    } else if (tradingState.longActive) {
      directionMode = "allow_long_only";
    } else if (tradingState.shortActive) {
      directionMode = "allow_short_only";
    }

    if (directionMode) {
      try {
        await fetchJson("/preferences/direction", {
          method: "POST",
          body: JSON.stringify({ direction_mode: directionMode }),
        });
      } catch (error) {
        console.error(error);
        showToast(error.message || "Failed to update direction", "error");
      }
    }
  }

  // Position toggle handlers
  if (longToggle) {
    longToggle.addEventListener("click", async () => {
      tradingState.longActive = !tradingState.longActive;
      updatePositionToggles();
      await updateDirectionPreference();
      updateSummary();
      logActivity("Long trading", tradingState.longActive ? "enabled" : "disabled");
      showToast(`Long positions ${tradingState.longActive ? 'enabled' : 'disabled'}`, "success");
    });
  }

  if (shortToggle) {
    shortToggle.addEventListener("click", async () => {
      tradingState.shortActive = !tradingState.shortActive;
      updatePositionToggles();
      await updateDirectionPreference();
      updateSummary();
      logActivity("Short trading", tradingState.shortActive ? "enabled" : "disabled");
      showToast(`Short positions ${tradingState.shortActive ? 'enabled' : 'disabled'}`, "success");
    });
  }

  // Leverage handlers
  handleSelectChange(
    longLeverageSelect,
    "/preferences/leverage",
    (value) => {
      tradingState.longLeverage = Number(value);
      return { leverage: Number(value) };
    },
    {
      success: (value) => `Long leverage set to ${Number(value).toFixed(1)}x`,
      activity: (value) => ["Long leverage updated", `${Number(value).toFixed(1)}x`],
    }
  );

  handleSelectChange(
    shortLeverageSelect,
    "/preferences/leverage",
    (value) => {
      tradingState.shortLeverage = Number(value);
      return { leverage: Number(value) };
    },
    {
      success: (value) => `Short leverage set to ${Number(value).toFixed(1)}x`,
      activity: (value) => ["Short leverage updated", `${Number(value).toFixed(1)}x`],
    }
  );

  // Capital allocation handlers
  if (longCapitalRange && longCapitalValue) {
    longCapitalRange.addEventListener("input", () => {
      const value = Number(longCapitalRange.value);
      tradingState.longAllocation = value;
      longCapitalValue.textContent = `${value}%`;
      updateTotalAllocation();
    });

    longCapitalRange.addEventListener("change", async () => {
      // Get primary allocation for calculating actual percentage
      const primarySlider = document.getElementById('primary-allocation-slider');
      const primaryAllocation = primarySlider ? Number(primarySlider.value) || 0 : 0;
      const actualLongAllocation = (primaryAllocation * tradingState.longAllocation) / 100;

      logActivity("Long split updated", `${tradingState.longAllocation}% of primary strategy`);
      showToast(`Long split set to ${tradingState.longAllocation}% (${actualLongAllocation.toFixed(1)}% of total capital)`, "success");
    });
  }

  if (shortCapitalRange && shortCapitalValue) {
    shortCapitalRange.addEventListener("input", () => {
      const value = Number(shortCapitalRange.value);
      tradingState.shortAllocation = value;
      shortCapitalValue.textContent = `${value}%`;
      updateTotalAllocation();
    });

    shortCapitalRange.addEventListener("change", async () => {
      // Get primary allocation for calculating actual percentage
      const primarySlider = document.getElementById('primary-allocation-slider');
      const primaryAllocation = primarySlider ? Number(primarySlider.value) || 0 : 0;
      const actualShortAllocation = (primaryAllocation * tradingState.shortAllocation) / 100;

      logActivity("Short split updated", `${tradingState.shortAllocation}% of primary strategy`);
      showToast(`Short split set to ${tradingState.shortAllocation}% (${actualShortAllocation.toFixed(1)}% of total capital)`, "success");
    });
  }

  // Primary allocation controls (master allocation system)
  const primarySlider = document.getElementById('primary-allocation-slider');
  const primaryInput = document.getElementById('primary-allocation-input');

  if (primarySlider && primaryInput) {
    primarySlider.addEventListener('input', () => {
      const value = Number(primarySlider.value);
      primaryInput.value = value;
      primarySlider.setAttribute('data-user-set', 'true');
      updateMasterAllocation();
    });

    primaryInput.addEventListener('input', () => {
      const value = Math.max(0, Math.min(100, Number(primaryInput.value)));
      primarySlider.value = value;
      primaryInput.value = value;
      primarySlider.setAttribute('data-user-set', 'true');
      updateMasterAllocation();
    });

    primarySlider.addEventListener('change', async () => {
      const value = Number(primarySlider.value);
      logActivity("Primary strategy allocation updated", `${value}%`);
      // Update backend with new allocation
      try {
        await fetchJson("/preferences/capital", {
          method: "POST",
          body: JSON.stringify({ capital_allocation_percent: value }),
        });
        showToast(`Primary allocation set to ${value}%`, "success");
      } catch (error) {
        console.error(error);
        showToast(error.message || "Failed to update allocation", "error");
      }
    });
  }

  // Strategy Management
  function createStrategyItem(index) {
    const strategyDiv = document.createElement('div');
    strategyDiv.className = 'strategy-item';
    strategyDiv.dataset.index = index;

    strategyDiv.innerHTML = `
      <div class="strategy-name-row">
        <select class="strategy-select" data-index="${index}">
          <option value="">Select Strategy...</option>
        </select>
        <button type="button" class="remove-strategy-btn" data-index="${index}">Remove</button>
      </div>

      <div class="strategy-product-row">
        <label class="strategy-product-label">Product:</label>
        <select class="strategy-product-select" data-index="${index}">
          <option value="">Select Product...</option>
        </select>
      </div>

      <div class="master-allocation-controls">
        <label class="strategy-control-label">Strategy Allocation (% of total capital)</label>
        <div class="allocation-input-enhanced">
          <input type="range" class="allocation-slider-enhanced strategy-master-allocation" data-index="${index}" min="0" max="100" value="0" />
          <input type="number" class="allocation-input-number strategy-master-input" data-index="${index}" min="0" max="100" value="0" />
          <span class="allocation-percent">%</span>
        </div>
      </div>

      <div class="strategy-config">
        <div class="strategy-position-group">
          <div class="strategy-position-header">
            <span class="strategy-position-title">Long Position</span>
            <button type="button" class="strategy-position-toggle long" data-index="${index}" data-position="long">OFF</button>
          </div>
          <div class="strategy-controls-row">
            <div class="strategy-control-group">
              <label class="strategy-control-label">Leverage</label>
              <select class="strategy-leverage-select strategy-long-leverage" data-index="${index}"></select>
            </div>
            <div class="strategy-control-group">
              <label class="strategy-control-label">Position Split (%)</label>
              <div class="strategy-allocation-input">
                <input type="range" class="strategy-allocation-slider strategy-long-allocation" data-index="${index}" min="0" max="100" value="0" />
                <span class="strategy-allocation-value strategy-long-value" data-index="${index}">0%</span>
              </div>
            </div>
          </div>
        </div>

        <div class="strategy-position-group">
          <div class="strategy-position-header">
            <span class="strategy-position-title">Short Position</span>
            <button type="button" class="strategy-position-toggle short" data-index="${index}" data-position="short">OFF</button>
          </div>
          <div class="strategy-controls-row">
            <div class="strategy-control-group">
              <label class="strategy-control-label">Leverage</label>
              <select class="strategy-leverage-select strategy-short-leverage" data-index="${index}"></select>
            </div>
            <div class="strategy-control-group">
              <label class="strategy-control-label">Position Split (%)</label>
              <div class="strategy-allocation-input">
                <input type="range" class="strategy-allocation-slider strategy-short-allocation" data-index="${index}" min="0" max="100" value="0" />
                <span class="strategy-allocation-value strategy-short-value" data-index="${index}">0%</span>
              </div>
            </div>
          </div>
        </div>

        <div class="strategy-position-summary">
          <small class="strategy-split-info">Long + Short must equal 100% of this strategy allocation</small>
        </div>
      </div>
    `;

    // Populate strategy selects
    const strategySelect = strategyDiv.querySelector('.strategy-select');
    const productSelect = strategyDiv.querySelector('.strategy-product-select');
    const longLeverageSelect = strategyDiv.querySelector('.strategy-long-leverage');
    const shortLeverageSelect = strategyDiv.querySelector('.strategy-short-leverage');

    // Copy main strategy options
    const mainStrategyOptions = document.getElementById('strategy-select').querySelectorAll('option');
    mainStrategyOptions.forEach(option => {
      if (option.value) {
        const newOption = option.cloneNode(true);
        strategySelect.appendChild(newOption);
      }
    });

    // Copy main product options
    const mainProductOptions = document.getElementById('product-select').querySelectorAll('option');
    mainProductOptions.forEach(option => {
      if (option.value) {
        const newOption = option.cloneNode(true);
        productSelect.appendChild(newOption);
      }
    });

    // Copy leverage options
    const leverageOptions = document.getElementById('long-leverage-select').querySelectorAll('option');
    leverageOptions.forEach(option => {
      if (option.value) {
        const longOption = option.cloneNode(true);
        const shortOption = option.cloneNode(true);
        longLeverageSelect.appendChild(longOption);
        shortLeverageSelect.appendChild(shortOption);
      }
    });

    return strategyDiv;
  }

  function updateMasterAllocation() {
    // Get primary strategy allocation from master controls (not long+short)
    const primarySlider = document.getElementById('primary-allocation-slider');
    let primaryAllocation = 0;
    if (primarySlider) {
      primaryAllocation = Number(primarySlider.value) || 0;
    }

    // Calculate total allocation from primary strategy and additional strategies
    let totalAllocation = primaryAllocation;

    tradingState.strategies.forEach(strategy => {
      totalAllocation += strategy.masterAllocation || 0;
    });

    const masterTotalSpan = document.getElementById('master-total-allocation');
    const masterWarning = document.getElementById('master-allocation-warning');

    if (masterTotalSpan) {
      masterTotalSpan.textContent = `${totalAllocation}%`;
    }

    if (masterWarning) {
      masterWarning.style.display = totalAllocation > 100 ? 'inline' : 'none';
    }

    // Update hero bar
    const heroTotalAllocation = document.getElementById('hero-total-allocation');
    if (heroTotalAllocation) {
      heroTotalAllocation.textContent = `${totalAllocation}%`;
    }
  }

  function addStrategyToMasterGrid(strategyState) {
    const masterGrid = document.getElementById('master-allocation-grid');
    if (!masterGrid) return;

    const masterItem = document.createElement('div');
    masterItem.className = 'master-strategy-item';
    masterItem.dataset.strategyIndex = strategyState.index;

    masterItem.innerHTML = `
      <div class="master-strategy-header">
        <h4>Strategy ${strategyState.index + 2}</h4>
        <span class="master-strategy-name" id="master-strategy-name-${strategyState.index}">--</span>
      </div>
      <div class="master-allocation-controls">
        <div class="allocation-input-enhanced">
          <input type="range" class="allocation-slider-enhanced" id="master-allocation-slider-${strategyState.index}" min="0" max="100" value="0" />
          <input type="number" class="allocation-input-number" id="master-allocation-input-${strategyState.index}" min="0" max="100" value="0" />
          <span class="allocation-percent">%</span>
        </div>
      </div>
    `;

    masterGrid.appendChild(masterItem);

    // Add event listeners for master allocation
    const slider = masterItem.querySelector(`#master-allocation-slider-${strategyState.index}`);
    const input = masterItem.querySelector(`#master-allocation-input-${strategyState.index}`);

    slider.addEventListener('input', () => {
      const value = Number(slider.value);
      strategyState.masterAllocation = value;
      input.value = value;
      updateMasterAllocation();
    });

    input.addEventListener('input', () => {
      const value = Math.max(0, Math.min(100, Number(input.value)));
      strategyState.masterAllocation = value;
      slider.value = value;
      input.value = value;
      updateMasterAllocation();
    });

    return masterItem;
  }

  function removeStrategyFromMasterGrid(strategyIndex) {
    const masterGrid = document.getElementById('master-allocation-grid');
    if (!masterGrid) return;

    const masterItem = masterGrid.querySelector(`[data-strategy-index="${strategyIndex}"]`);
    if (masterItem) {
      masterItem.remove();
    }
  }

  function updateStrategyName(strategyIndex, name) {
    const masterNameSpan = document.getElementById(`master-strategy-name-${strategyIndex}`);
    if (masterNameSpan) {
      masterNameSpan.textContent = name || '--';
    }
  }

  function addStrategy() {
    const strategyCount = strategiesList.children.length;
    if (strategyCount >= 5) {
      showToast("Maximum 5 strategies allowed", "error");
      return;
    }

    const strategyItem = createStrategyItem(strategyCount);
    strategiesList.appendChild(strategyItem);

    // Initialize strategy state
    const strategyState = {
      index: strategyCount,
      name: '',
      product: '',
      masterAllocation: 0,
      longEnabled: false,
      shortEnabled: false,
      longLeverage: 1,
      shortLeverage: 1,
      longAllocation: 50, // Default 50% long, 50% short split
      shortAllocation: 50
    };

    tradingState.strategies.push(strategyState);

    // Add strategy to master allocation grid
    addStrategyToMasterGrid(strategyState);

    // Add event listeners
    const removeBtn = strategyItem.querySelector('.remove-strategy-btn');
    removeBtn.addEventListener('click', () => {
      const index = parseInt(strategyItem.dataset.index);
      tradingState.strategies = tradingState.strategies.filter(s => s.index !== index);
      strategyItem.remove();
      removeStrategyFromMasterGrid(index);
      updateMasterAllocation();
      logActivity("Strategy removed", "");
    });

    const strategySelect = strategyItem.querySelector('.strategy-select');
    strategySelect.addEventListener('change', () => {
      strategyState.name = strategySelect.value;
      updateStrategyName(strategyState.index, strategySelect.value);
      logActivity("Strategy configured", strategySelect.value || 'None');
    });

    const productSelect = strategyItem.querySelector('.strategy-product-select');
    productSelect.addEventListener('change', () => {
      strategyState.product = productSelect.value;
      logActivity("Strategy product", productSelect.value || 'None');
    });

    // Position toggle handlers
    const longToggle = strategyItem.querySelector('.strategy-position-toggle.long');
    const shortToggle = strategyItem.querySelector('.strategy-position-toggle.short');

    longToggle.addEventListener('click', () => {
      strategyState.longEnabled = !strategyState.longEnabled;
      longToggle.textContent = strategyState.longEnabled ? 'ON' : 'OFF';
      longToggle.classList.toggle('active', strategyState.longEnabled);
      logActivity(`Strategy ${strategyCount + 2} Long`, strategyState.longEnabled ? 'enabled' : 'disabled');
    });

    shortToggle.addEventListener('click', () => {
      strategyState.shortEnabled = !strategyState.shortEnabled;
      shortToggle.textContent = strategyState.shortEnabled ? 'ON' : 'OFF';
      shortToggle.classList.toggle('active', strategyState.shortEnabled);
      logActivity(`Strategy ${strategyCount + 2} Short`, strategyState.shortEnabled ? 'enabled' : 'disabled');
    });

    // Leverage handlers
    const longLeverage = strategyItem.querySelector('.strategy-long-leverage');
    const shortLeverage = strategyItem.querySelector('.strategy-short-leverage');

    longLeverage.addEventListener('change', () => {
      strategyState.longLeverage = Number(longLeverage.value);
      logActivity(`Strategy ${strategyCount + 2} Long leverage`, `${strategyState.longLeverage}x`);
    });

    shortLeverage.addEventListener('change', () => {
      strategyState.shortLeverage = Number(shortLeverage.value);
      logActivity(`Strategy ${strategyCount + 2} Short leverage`, `${strategyState.shortLeverage}x`);
    });

    // Position split handlers (within strategy allocation)
    const longAllocation = strategyItem.querySelector('.strategy-long-allocation');
    const shortAllocation = strategyItem.querySelector('.strategy-short-allocation');
    const longValue = strategyItem.querySelector('.strategy-long-value');
    const shortValue = strategyItem.querySelector('.strategy-short-value');

    // Set initial values
    longAllocation.value = 50;
    shortAllocation.value = 50;
    longValue.textContent = '50%';
    shortValue.textContent = '50%';

    longAllocation.addEventListener('input', () => {
      const value = Number(longAllocation.value);
      const shortPercent = 100 - value;
      strategyState.longAllocation = value;
      strategyState.shortAllocation = shortPercent;
      longValue.textContent = `${value}%`;
      shortAllocation.value = shortPercent;
      shortValue.textContent = `${shortPercent}%`;
    });

    shortAllocation.addEventListener('input', () => {
      const value = Number(shortAllocation.value);
      const longPercent = 100 - value;
      strategyState.shortAllocation = value;
      strategyState.longAllocation = longPercent;
      shortValue.textContent = `${value}%`;
      longAllocation.value = longPercent;
      longValue.textContent = `${longPercent}%`;
    });

    longAllocation.addEventListener('change', () => {
      logActivity(`Strategy ${strategyCount + 2} position split`, `${strategyState.longAllocation}% Long, ${strategyState.shortAllocation}% Short`);
    });

    shortAllocation.addEventListener('change', () => {
      logActivity(`Strategy ${strategyCount + 2} position split`, `${strategyState.longAllocation}% Long, ${strategyState.shortAllocation}% Short`);
    });

    // Update button state
    if (addStrategyBtn) {
      addStrategyBtn.disabled = strategiesList.children.length >= 5;
    }

    logActivity("Strategy added", `Strategy ${strategyCount + 2}`);
  }

  if (addStrategyBtn) {
    addStrategyBtn.addEventListener('click', addStrategy);
  }

  // Details display toggle
  if (toggleDetailsBtn) {
    toggleDetailsBtn.addEventListener('click', () => {
      showExecutionDetails = !showExecutionDetails;
      toggleDetailsBtn.classList.toggle('active', showExecutionDetails);
      toggleDetailsBtn.textContent = showExecutionDetails ? 'Hide Details' : 'Show Details';

      // Re-render execution log to show/hide details
      refreshExecutions();
      logActivity("Execution details", showExecutionDetails ? "enabled" : "disabled");
    });
  }

  // Timing display toggle
  if (toggleTimingBtn) {
    toggleTimingBtn.addEventListener('click', () => {
      showTimingDetails = !showTimingDetails;
      toggleTimingBtn.classList.toggle('active', showTimingDetails);
      toggleTimingBtn.textContent = showTimingDetails ? 'Hide Timing' : 'Show Timing';

      // Re-render execution log to show/hide timing
      refreshExecutions();
      logActivity("Timing display", showTimingDetails ? "enabled" : "disabled");
    });
  }


  if (refreshButton) {
    refreshButton.addEventListener("click", () => {
      loadOptionsAndPreference({ showNotice: true });
      refreshExecutions({ showErrors: true }).catch((error) => {
        console.error("Failed to refresh executions", error);
      });
      refreshAccountSummary({ showErrors: true }).catch((error) => {
        console.error("Failed to refresh account summary", error);
      });
    });
  }

  if (resetButton) {
    resetButton.addEventListener("click", () => {
      loadOptionsAndPreference();
      showToast("Preferences synced from server", "info");
      logActivity("Preferences reset", "");
      refreshExecutions({ showErrors: true }).catch((error) => {
        console.error("Failed to refresh executions", error);
      });
      refreshAccountSummary({ showErrors: true }).catch((error) => {
        console.error("Failed to refresh account summary", error);
      });
    });
  }

  await loadOptionsAndPreference();

  const wantsAccountSummary = Boolean(summaryAccountBalance || summaryAccountAvailable);
  if (wantsAccountSummary) {
    await refreshAccountSummary({ showErrors: true });
    if (accountRefreshTimer) {
      window.clearInterval(accountRefreshTimer);
    }
    accountRefreshTimer = window.setInterval(() => {
      refreshAccountSummary().catch((error) => {
        console.error("Failed to refresh account summary", error);
      });
    }, ACCOUNT_REFRESH_INTERVAL);
  }

  if (executionLogElement) {
    await refreshExecutions({ showErrors: true });
    if (executionRefreshTimer) {
      window.clearInterval(executionRefreshTimer);
    }
    executionRefreshTimer = window.setInterval(() => {
      refreshExecutions().catch((error) => {
        console.error("Failed to refresh executions", error);
      });
    }, EXECUTION_REFRESH_INTERVAL);
  }
}

document.addEventListener("DOMContentLoaded", () => {
  initialize().catch((error) => {
    console.error("Failed to initialise UI", error);
    window.alert("Failed to load options. Please refresh the page.");
  });
});
