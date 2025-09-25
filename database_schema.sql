-- Comprehensive Database Schema for Alsa Trade App
-- Execute these SQL statements in your Supabase SQL editor

-- 1. Strategy Preferences Table (already exists but included for completeness)
CREATE TABLE IF NOT EXISTS strategy_preferences (
    id SERIAL PRIMARY KEY,
    user_ref VARCHAR(255) NOT NULL UNIQUE DEFAULT 'default',
    product VARCHAR(100),
    strategy VARCHAR(100),
    direction_mode VARCHAR(50), -- 'allow_long_short', 'allow_long_only', 'allow_short_only'
    leverage DECIMAL(5,2),
    capital_allocation_percent DECIMAL(5,2),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 2. Signals Table (incoming webhook signals)
CREATE TABLE IF NOT EXISTS signals (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    action VARCHAR(10), -- 'buy' or 'sell'
    symbol VARCHAR(50),
    quantity DECIMAL(20,8),
    price DECIMAL(20,8),
    signal_time TIMESTAMP WITH TIME ZONE,
    strategy VARCHAR(100),
    raw_payload JSONB, -- Store the complete webhook payload
    source VARCHAR(50) DEFAULT 'tradingview', -- Signal source
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 3. Executions Table (trade execution results)
CREATE TABLE IF NOT EXISTS executions (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    action VARCHAR(10), -- 'buy' or 'sell'
    symbol VARCHAR(50),
    quantity DECIMAL(20,8),
    status VARCHAR(20), -- 'success', 'failed', 'ignored'
    order_id VARCHAR(100),
    execution_time TIMESTAMP WITH TIME ZONE,

    -- Detailed timing tracking
    signal_sent_time TIMESTAMP WITH TIME ZONE,
    received_time TIMESTAMP WITH TIME ZONE,
    processed_time TIMESTAMP WITH TIME ZONE,
    sent_to_binance_time TIMESTAMP WITH TIME ZONE,
    binance_executed_time TIMESTAMP WITH TIME ZONE,

    -- Additional execution details
    executed_price DECIMAL(20,8), -- Actual execution price from Binance
    executed_quantity DECIMAL(20,8), -- Actual executed quantity
    fees DECIMAL(20,8), -- Trading fees
    commission_asset VARCHAR(10), -- Asset used for commission
    leverage INTEGER, -- Applied leverage
    capital_percent DECIMAL(5,2), -- Applied capital allocation percentage

    -- Error tracking
    error_message TEXT,
    error_code VARCHAR(50),

    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 4. Account Snapshots Table (periodic account balance tracking)
CREATE TABLE IF NOT EXISTS account_snapshots (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    -- Balance information
    asset VARCHAR(10) DEFAULT 'USDT',
    available_balance DECIMAL(20,8),
    wallet_balance DECIMAL(20,8),
    cross_wallet_balance DECIMAL(20,8),
    total_wallet_balance DECIMAL(20,8),
    total_unrealized_profit DECIMAL(20,8),
    total_margin_balance DECIMAL(20,8),

    -- Account status
    can_trade BOOLEAN DEFAULT TRUE,
    can_withdraw BOOLEAN DEFAULT TRUE,
    can_deposit BOOLEAN DEFAULT TRUE,

    -- Snapshot trigger
    trigger_type VARCHAR(50), -- 'manual', 'scheduled', 'post_trade', 'error'
    trigger_details TEXT,

    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 5. Positions Table (current open positions)
CREATE TABLE IF NOT EXISTS positions (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(50) NOT NULL,
    side VARCHAR(10), -- 'LONG' or 'SHORT'
    size DECIMAL(20,8),
    entry_price DECIMAL(20,8),
    mark_price DECIMAL(20,8),
    unrealized_pnl DECIMAL(20,8),
    percentage DECIMAL(10,4),

    -- Position details
    leverage INTEGER,
    margin_type VARCHAR(20), -- 'isolated' or 'cross'
    isolated_margin DECIMAL(20,8),

    -- Timestamps
    opened_at TIMESTAMP WITH TIME ZONE,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    closed_at TIMESTAMP WITH TIME ZONE,

    -- Status
    is_active BOOLEAN DEFAULT TRUE,

    UNIQUE(symbol, side, is_active) -- Only one active position per symbol-side combination
);

-- 6. Orders Table (all order activity)
CREATE TABLE IF NOT EXISTS orders (
    id SERIAL PRIMARY KEY,
    binance_order_id VARCHAR(100) UNIQUE,
    client_order_id VARCHAR(100),

    -- Order details
    symbol VARCHAR(50) NOT NULL,
    side VARCHAR(10), -- 'BUY' or 'SELL'
    type VARCHAR(20), -- 'MARKET', 'LIMIT', 'STOP', etc.
    quantity DECIMAL(20,8),
    price DECIMAL(20,8),

    -- Execution details
    executed_quantity DECIMAL(20,8),
    executed_price DECIMAL(20,8),
    cumulative_quote_quantity DECIMAL(20,8),

    -- Order status
    status VARCHAR(20), -- 'NEW', 'FILLED', 'CANCELED', 'REJECTED', etc.
    time_in_force VARCHAR(10), -- 'GTC', 'IOC', 'FOK'

    -- Fees
    commission DECIMAL(20,8),
    commission_asset VARCHAR(10),

    -- Timestamps
    created_time TIMESTAMP WITH TIME ZONE,
    updated_time TIMESTAMP WITH TIME ZONE,
    working_time TIMESTAMP WITH TIME ZONE,

    -- Relationship to our execution
    execution_id INTEGER REFERENCES executions(id),

    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 7. System Logs Table (application events and errors)
CREATE TABLE IF NOT EXISTS system_logs (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    -- Log details
    level VARCHAR(20), -- 'DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'
    category VARCHAR(50), -- 'api', 'trading', 'database', 'webhook', 'system'
    message TEXT NOT NULL,

    -- Context
    endpoint VARCHAR(100), -- API endpoint if applicable
    user_ref VARCHAR(255) DEFAULT 'default',
    session_id VARCHAR(100),

    -- Additional data
    metadata JSONB, -- Store additional context as JSON
    stack_trace TEXT, -- For errors

    -- Request details (for API calls)
    request_method VARCHAR(10),
    request_path VARCHAR(200),
    request_body TEXT,
    response_status INTEGER,
    response_time_ms INTEGER,

    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 8. Performance Metrics Table (trading performance tracking)
CREATE TABLE IF NOT EXISTS performance_metrics (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    period_type VARCHAR(20), -- 'daily', 'weekly', 'monthly'
    period_start TIMESTAMP WITH TIME ZONE,
    period_end TIMESTAMP WITH TIME ZONE,

    -- Trading metrics
    total_trades INTEGER DEFAULT 0,
    successful_trades INTEGER DEFAULT 0,
    failed_trades INTEGER DEFAULT 0,
    win_rate DECIMAL(5,2), -- Percentage

    -- P&L metrics
    total_pnl DECIMAL(20,8),
    realized_pnl DECIMAL(20,8),
    unrealized_pnl DECIMAL(20,8),
    total_fees DECIMAL(20,8),
    net_pnl DECIMAL(20,8),

    -- Volume metrics
    total_volume DECIMAL(20,8),
    buy_volume DECIMAL(20,8),
    sell_volume DECIMAL(20,8),

    -- Risk metrics
    max_drawdown DECIMAL(20,8),
    max_position_size DECIMAL(20,8),
    avg_leverage DECIMAL(5,2),

    -- Balance tracking
    starting_balance DECIMAL(20,8),
    ending_balance DECIMAL(20,8),
    peak_balance DECIMAL(20,8),

    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    UNIQUE(period_type, period_start, period_end)
);

-- 9. Configuration Changes Table (audit trail for settings)
CREATE TABLE IF NOT EXISTS configuration_changes (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    -- What changed
    table_name VARCHAR(50), -- 'strategy_preferences', etc.
    record_id INTEGER,
    field_name VARCHAR(100),
    old_value TEXT,
    new_value TEXT,

    -- Who/what changed it
    changed_by VARCHAR(100) DEFAULT 'system',
    change_source VARCHAR(50), -- 'api', 'manual', 'migration'
    change_reason TEXT,

    -- Request context
    ip_address INET,
    user_agent TEXT,

    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 10. Health Checks Table (system monitoring)
CREATE TABLE IF NOT EXISTS health_checks (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    -- Service status
    service_name VARCHAR(50), -- 'binance_api', 'database', 'webhook_receiver'
    status VARCHAR(20), -- 'healthy', 'degraded', 'down'
    response_time_ms INTEGER,

    -- Details
    check_details JSONB,
    error_message TEXT,

    -- Metrics
    cpu_usage DECIMAL(5,2),
    memory_usage DECIMAL(5,2),
    disk_usage DECIMAL(5,2),

    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create indexes for better query performance
CREATE INDEX IF NOT EXISTS idx_signals_timestamp ON signals(timestamp);
CREATE INDEX IF NOT EXISTS idx_signals_symbol ON signals(symbol);
CREATE INDEX IF NOT EXISTS idx_signals_strategy ON signals(strategy);

CREATE INDEX IF NOT EXISTS idx_executions_timestamp ON executions(timestamp);
CREATE INDEX IF NOT EXISTS idx_executions_symbol ON executions(symbol);
CREATE INDEX IF NOT EXISTS idx_executions_status ON executions(status);

CREATE INDEX IF NOT EXISTS idx_orders_symbol ON orders(symbol);
CREATE INDEX IF NOT EXISTS idx_orders_status ON orders(status);
CREATE INDEX IF NOT EXISTS idx_orders_binance_order_id ON orders(binance_order_id);

CREATE INDEX IF NOT EXISTS idx_system_logs_timestamp ON system_logs(timestamp);
CREATE INDEX IF NOT EXISTS idx_system_logs_level ON system_logs(level);
CREATE INDEX IF NOT EXISTS idx_system_logs_category ON system_logs(category);

CREATE INDEX IF NOT EXISTS idx_positions_symbol ON positions(symbol);
CREATE INDEX IF NOT EXISTS idx_positions_is_active ON positions(is_active);

CREATE INDEX IF NOT EXISTS idx_account_snapshots_timestamp ON account_snapshots(timestamp);
CREATE INDEX IF NOT EXISTS idx_performance_metrics_period ON performance_metrics(period_type, period_start);

-- Create triggers for automatic timestamp updates
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Apply the trigger to relevant tables
CREATE TRIGGER update_strategy_preferences_updated_at
    BEFORE UPDATE ON strategy_preferences
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_positions_updated_at
    BEFORE UPDATE ON positions
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Insert default strategy preference if not exists
INSERT INTO strategy_preferences (user_ref, product, strategy, direction_mode, leverage, capital_allocation_percent)
VALUES ('default', NULL, NULL, 'allow_long_short', 1.0, 10.0)
ON CONFLICT (user_ref) DO NOTHING;

-- Create views for commonly used queries
CREATE OR REPLACE VIEW trading_summary AS
SELECT
    DATE(timestamp) as trade_date,
    COUNT(*) as total_executions,
    COUNT(*) FILTER (WHERE status = 'success') as successful_trades,
    COUNT(*) FILTER (WHERE status = 'failed') as failed_trades,
    COUNT(*) FILTER (WHERE status = 'ignored') as ignored_signals,
    ROUND(
        (COUNT(*) FILTER (WHERE status = 'success')::numeric /
         NULLIF(COUNT(*) FILTER (WHERE status IN ('success', 'failed')), 0) * 100), 2
    ) as success_rate,
    SUM(quantity) FILTER (WHERE status = 'success' AND action = 'buy') as total_buy_volume,
    SUM(quantity) FILTER (WHERE status = 'success' AND action = 'sell') as total_sell_volume
FROM executions
WHERE timestamp >= NOW() - INTERVAL '30 days'
GROUP BY DATE(timestamp)
ORDER BY trade_date DESC;

CREATE OR REPLACE VIEW trading_summary AS
SELECT
    DATE(timestamp) as trade_date,
    COUNT(*) as total_executions,
    COUNT(*) FILTER (WHERE status = 'success') as successful_trades,
    COUNT(*) FILTER (WHERE status = 'failed') as failed_trades,
    COUNT(*) FILTER (WHERE status = 'ignored') as ignored_signals,
    ROUND(
        (COUNT(*) FILTER (WHERE status = 'success')::numeric /
         NULLIF(COUNT(*) FILTER (WHERE status IN ('success', 'failed')), 0) * 100), 2
    ) as success_rate,
    SUM(quantity) FILTER (WHERE status = 'success' AND action = 'buy') as total_buy_volume,
    SUM(quantity) FILTER (WHERE status = 'success' AND action = 'sell') as total_sell_volume
FROM executions
WHERE timestamp >= NOW() - INTERVAL '30 days'
GROUP BY DATE(timestamp)
ORDER BY trade_date DESC;