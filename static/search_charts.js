// 股票搜尋結果顯示（使用 TradingView Lightweight Charts）
function displaySearchResults(data) {
    const searchResults = document.getElementById('search-results');

    if (!data.results || data.results.length === 0) {
        searchResults.innerHTML = '<div class="no-results">❌ 找不到符合的股票</div>';
        return;
    }

    let html = '<div style="display: grid; gap: 30px; margin-top: 20px;">';

    data.results.forEach((stock, index) => {
        const changeClass = stock.change_pct >= 0 ? 'positive' : 'negative';
        const changeSymbol = stock.change_pct >= 0 ? '+' : '';

        html += `
            <div style="background: #ffffff; border-radius: 15px; padding: 25px; border: 1px solid #e0e0e0; box-shadow: 0 2px 8px rgba(0,0,0,0.1);">
                <!-- Header -->
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;">
                    <div>
                        <span style="font-size: 1.4em; font-weight: bold; color: #1976d2;">${stock.code}</span>
                        <span style="margin-left: 15px; font-size: 1.2em; color: #333;">${stock.name}</span>
                    </div>
                    <div style="background: ${stock.market === 'LISTED' ? '#4caf50' : '#ff9800'}; padding: 8px 20px; border-radius: 20px; font-size: 0.95em; color: white;">
                        ${stock.market === 'LISTED' ? '上市' : '上櫃'}
                    </div>
                </div>
                
                <!-- Basic Info -->
                <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 15px; margin-bottom: 25px; padding: 15px; background: #f5f5f5; border-radius: 10px;">
                    <div>
                        <div style="color: #666; font-size: 0.9em; margin-bottom: 5px;">現價</div>
                        <div style="font-size: 1.4em; font-weight: bold; color: #333;">${stock.price.toFixed(2)} TWD</div>
                    </div>
                    <div>
                        <div style="color: #666; font-size: 0.9em; margin-bottom: 5px;">漲跌幅</div>
                        <div class="${changeClass}" style="font-size: 1.4em; font-weight: bold;">${changeSymbol}${stock.change_pct.toFixed(2)}%</div>
                    </div>
                    <div>
                        <div style="color: #666; font-size: 0.9em; margin-bottom: 5px;">成交量</div>
                        <div style="font-size: 1.2em; color: #333;">${stock.volume.toLocaleString()} 股</div>
                    </div>
                    <div>
                        <div style="color: #666; font-size: 0.9em; margin-bottom: 5px;">市值</div>
                        <div style="font-size: 1.2em; color: #333;">${(stock.market_cap / 1e8).toFixed(2)} 億</div>
                    </div>
                </div>
                
                <!-- K線圖切換 -->
                ${stock.chart_data_daily && stock.chart_data_daily.length > 0 ? `
                <div style="margin-bottom: 25px;">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px;">
                        <div style="display: flex; gap: 10px;">
                            <button onclick="switchChartType('${stock.code}', 'daily')" 
                                    id="btn-daily-${stock.code}"
                                    style="padding: 8px 20px; border: 2px solid #1976d2; background: #1976d2; color: white; border-radius: 8px; cursor: pointer; font-weight: bold;">
                                📈 日K線
                            </button>
                            <button onclick="switchChartType('${stock.code}', '5min')" 
                                    id="btn-5min-${stock.code}"
                                    style="padding: 8px 20px; border: 2px solid #1976d2; background: white; color: #1976d2; border-radius: 8px; cursor: pointer; font-weight: bold;">
                                ⏱️ 5分K線
                            </button>
                        </div>
                        <div style="color: #666; font-size: 0.85em;">
                            🖱️ 滾輪縮放時間軸 | 拖曳價格軸縮放 | 雙擊重置
                        </div>
                    </div>
                    
                    <!-- 日K圖表容器 -->
                    <div id="wrapper-daily-${stock.code}" style="display: block;">
                        <!-- 價格圖 -->
                        <div style="font-size:0.8em; color:#888; margin-bottom:3px; padding-left:4px;">▎ 價格 / K 線</div>
                        <div id="chart-daily-${stock.code}" style="height: 320px; background: white; border: 1px solid #e0e0e0; border-radius: 4px 4px 0 0;"></div>
                        <!-- 成交量圖 -->
                        <div style="font-size:0.8em; color:#888; margin-top:8px; margin-bottom:3px; padding-left:4px;">▎ 成交量</div>
                        <div id="chart-volume-daily-${stock.code}" style="height: 120px; background: white; border: 1px solid #e0e0e0; border-radius: 0 0 4px 4px;"></div>
                    </div>
                    
                    <!-- 5分K圖表容器 -->
                    <div id="wrapper-5min-${stock.code}" style="display: none;">
                        <!-- 價格圖 -->
                        <div style="font-size:0.8em; color:#888; margin-bottom:3px; padding-left:4px;">▎ 價格 / K 線</div>
                        <div id="chart-5min-${stock.code}" style="height: 320px; background: white; border: 1px solid #e0e0e0; border-radius: 4px 4px 0 0;"></div>
                        <!-- 成交量圖 -->
                        <div style="font-size:0.8em; color:#888; margin-top:8px; margin-bottom:3px; padding-left:4px;">▎ 成交量</div>
                        <div id="chart-volume-5min-${stock.code}" style="height: 120px; background: white; border: 1px solid #e0e0e0; border-radius: 0 0 4px 4px;"></div>
                    </div>
                </div>
                ` : ''}
                
                <!-- 籌碼資訊：三大法人 -->
                ${renderInstitutional(stock)}
            </div>
        `;
    });

    html += '</div>';
    searchResults.innerHTML = html;

    // 初始化圖表
    setTimeout(() => {
        data.results.forEach((stock) => {
            console.log(`正在準備繪製 ${stock.code} 圖表...`);
            try {
                if (stock.chart_data_daily && stock.chart_data_daily.length > 0) {
                    createSplitChart(
                        `chart-daily-${stock.code}`,
                        `chart-volume-daily-${stock.code}`,
                        stock.chart_data_daily,
                        stock.volume_data_daily,
                        false
                    );
                }
                if (stock.chart_data_5min && stock.chart_data_5min.length > 0) {
                    createSplitChart(
                        `chart-5min-${stock.code}`,
                        `chart-volume-5min-${stock.code}`,
                        stock.chart_data_5min,
                        stock.volume_data_5min,
                        true
                    );
                }
            } catch (err) {
                console.error(`繪製 ${stock.code} 圖表失敗:`, err);
            }
        });
    }, 100);
}

/**
 * 建立「上方K線圖 + 下方成交量圖」，並同步兩張圖的時間軸
 */
function createSplitChart(priceContainerId, volumeContainerId, candleData, volumeData, isIntraday) {
    const priceContainer = document.getElementById(priceContainerId);
    const volumeContainer = document.getElementById(volumeContainerId);
    if (!priceContainer || !volumeContainer) {
        console.error('找不到圖表容器:', priceContainerId, volumeContainerId);
        return;
    }

    priceContainer.innerHTML = '';
    volumeContainer.innerHTML = '';

    const commonLayout = {
        background: { color: '#ffffff' },
        textColor: '#333',
    };
    const commonGrid = {
        vertLines: { color: '#f0f0f0' },
        horzLines: { color: '#f0f0f0' },
    };
    const commonTimeScale = {
        borderColor: '#dfe1e5',
        timeVisible: true,
        secondsVisible: false,
    };

    // ── 上方：K 線圖 ──────────────────────────
    const priceChart = LightweightCharts.createChart(priceContainer, {
        width: priceContainer.clientWidth,
        height: 320,
        layout: commonLayout,
        grid: commonGrid,
        crosshair: { mode: LightweightCharts.CrosshairMode.Normal },
        rightPriceScale: { borderColor: '#dfe1e5' },
        timeScale: { ...commonTimeScale, visible: false }, // 隱藏X軸（由下方量圖顯示）
    });

    const candleSeries = priceChart.addSeries(LightweightCharts.CandlestickSeries, {
        upColor: '#ef5350',
        downColor: '#26a69a',
        borderUpColor: '#ef5350',
        borderDownColor: '#26a69a',
        wickUpColor: '#ef5350',
        wickDownColor: '#26a69a',
    });

    const formattedCandles = candleData.map(d => ({
        time: d.time, open: d.open, high: d.high, low: d.low, close: d.close
    }));
    candleSeries.setData(formattedCandles);

    // 移動平均線
    function calcSMA(data, n) {
        const result = [];
        for (let i = n - 1; i < data.length; i++) {
            const sum = data.slice(i - n + 1, i + 1).reduce((s, d) => s + d.close, 0);
            result.push({ time: data[i].time, value: sum / n });
        }
        return result;
    }
    const maSeries = [
        { n: 5, color: '#2962FF' },
        { n: 10, color: '#FF6D00' },
        { n: 20, color: '#D500F9' },
    ];
    maSeries.forEach(({ n, color }) => {
        const s = priceChart.addSeries(LightweightCharts.LineSeries, { color, lineWidth: 1, title: `MA${n}` });
        s.setData(calcSMA(formattedCandles, n));
    });

    priceChart.timeScale().fitContent();

    // ── 下方：成交量圖 ────────────────────────
    const volChart = LightweightCharts.createChart(volumeContainer, {
        width: volumeContainer.clientWidth,
        height: 120,
        layout: { ...commonLayout, textColor: '#888' },
        grid: commonGrid,
        crosshair: { mode: LightweightCharts.CrosshairMode.Normal },
        rightPriceScale: {
            borderColor: '#dfe1e5',
            scaleMargins: { top: 0.05, bottom: 0.05 },
        },
        timeScale: commonTimeScale,
    });

    const volSeries = volChart.addSeries(LightweightCharts.HistogramSeries, {
        priceFormat: { type: 'volume' },
        priceScaleId: 'right',
    });
    volSeries.setData(volumeData.map(d => ({ time: d.time, value: d.value, color: d.color })));
    volChart.timeScale().fitContent();

    // ── 同步兩圖的時間軸（互相跟隨）──────────
    let syncingFrom = false;
    priceChart.timeScale().subscribeVisibleTimeRangeChange(range => {
        if (syncingFrom) return;
        syncingFrom = true;
        volChart.timeScale().setVisibleRange(range);
        syncingFrom = false;
    });
    volChart.timeScale().subscribeVisibleTimeRangeChange(range => {
        if (syncingFrom) return;
        syncingFrom = true;
        priceChart.timeScale().setVisibleRange(range);
        syncingFrom = false;
    });

    // ── 響應式寬度 ────────────────────────────
    const ro = new ResizeObserver(entries => {
        const w = entries[0].contentRect.width;
        priceChart.applyOptions({ width: w });
        volChart.applyOptions({ width: w });
    });
    ro.observe(priceContainer);
}

// 切換圖表類型（日K / 5分K）
function switchChartType(code, type) {
    const btnDaily = document.getElementById(`btn-daily-${code}`);
    const btn5min = document.getElementById(`btn-5min-${code}`);

    if (type === 'daily') {
        btnDaily && (btnDaily.style.background = '#1976d2', btnDaily.style.color = 'white');
        btn5min && (btn5min.style.background = 'white', btn5min.style.color = '#1976d2');
        document.getElementById(`wrapper-daily-${code}`).style.display = 'block';
        document.getElementById(`wrapper-5min-${code}`).style.display = 'none';
    } else {
        btnDaily && (btnDaily.style.background = 'white', btnDaily.style.color = '#1976d2');
        btn5min && (btn5min.style.background = '#1976d2', btn5min.style.color = 'white');
        document.getElementById(`wrapper-daily-${code}`).style.display = 'none';
        document.getElementById(`wrapper-5min-${code}`).style.display = 'block';
    }
}

/**
 * 渲染三大法人買賣超：圖表 + 逐日表格
 */
// 記錄 Chart.js 實例，避免重複建立時記憶體洩漏
const _instCharts = {};

function renderInstitutional(stock) {
    const hist = stock.institutional_history;
    const code = stock.code;

    if (!hist || hist.length === 0) {
        return `<div style="margin-top:20px; background:#f5f5f5; border-radius:8px; padding:20px; text-align:center; color:#999;">
            🏦 暫無三大法人歷史資料（可能非交易日或資料尚未公布）
        </div>`;
    }

    const latest = hist[hist.length - 1];

    // ── 今日總覽數字 ───────────────────────────
    const fmtLots = n => {
        if (n === null || n === undefined) return '–';
        return Math.round(n / 1000).toLocaleString();
    };
    const colorNet = n => {
        const v = Math.round((n || 0) / 1000);
        if (v > 0) return `<span style="color:#c62828;font-weight:bold;">${v.toLocaleString()}</span>`;
        if (v < 0) return `<span style="color:#00695c;font-weight:bold;">${v.toLocaleString()}</span>`;
        return `<span style="color:#888;">0</span>`;
    };

    // ── 逐日表格 ─────────────────────────────
    // 建立 date -> price 的對照（來自 chart_data_daily）
    const priceMap = {};
    if (stock.chart_data_daily) {
        stock.chart_data_daily.forEach(p => { priceMap[p.time] = p; });
    }

    // ── HTML 結構 ─────────────────────────────
    const chartId = `inst-chart-${code}`;
    const rangeId = `inst-range-${code}`;

    let tableRows = [...hist].reverse().map(d => {
        const priceEntry = priceMap[d.date];
        const chg = priceEntry ? ((priceEntry.close - priceEntry.open) / priceEntry.open * 100) : null;
        const vol = priceEntry ? Math.round(priceEntry.close) : '–';
        const chgStr = chg !== null
            ? `<span style="color:${chg >= 0 ? '#c62828' : '#00695c'}; font-weight:bold;">${chg >= 0 ? '▲' : '▼'} ${Math.abs(chg).toFixed(2)}%</span>`
            : '–';
        const totalNet = (d.foreign_net || 0) + (d.trust_net || 0) + (d.dealer_net || 0);
        return `<tr style="border-bottom:1px solid #f0f0f0;">
            <td style="padding:8px 10px; color:#555; font-size:0.88em;">${d.date}</td>
            <td style="padding:8px 10px; text-align:right;">${colorNet(d.foreign_net)}</td>
            <td style="padding:8px 10px; text-align:right;">${colorNet(d.trust_net)}</td>
            <td style="padding:8px 10px; text-align:right;">${colorNet(d.dealer_net)}</td>
            <td style="padding:8px 10px; text-align:right; font-weight:bold;">${colorNet(totalNet * 1000)}</td>
            <td style="padding:8px 10px; text-align:right;">${chgStr}</td>
        </tr>`;
    }).join('');

    const html = `
    <div style="margin-top:24px;">
        <!-- 標題列 -->
        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:14px;">
            <h3 style="color:#1565c0; margin:0; font-size:1.1em;">🏦 法人買賣變化</h3>
            <span style="font-size:0.8em; color:#999;">資料時間：${latest.date}</span>
        </div>

        <!-- 今日總覽 -->
        <div style="background:#e3f2fd; border-radius:8px; padding:14px; margin-bottom:16px;">
            <div style="font-size:0.85em; color:#1565c0; font-weight:bold; margin-bottom:10px;">📋 當日法人買賣（單位：張）</div>
            <table style="width:100%; border-collapse:collapse; font-size:0.9em;">
                <thead>
                    <tr style="color:#555; border-bottom:1px solid #bbdefb;">
                        <th style="padding:6px 10px; text-align:left;"></th>
                        <th style="padding:6px 10px; text-align:right;">買進</th>
                        <th style="padding:6px 10px; text-align:right;">賣出</th>
                        <th style="padding:6px 10px; text-align:right;">買賣超</th>
                    </tr>
                </thead>
                <tbody>
                    <tr>
                        <td style="padding:7px 10px; font-weight:bold;">🌏 外資</td>
                        <td style="padding:7px 10px; text-align:right;">${fmtLots(latest.foreign_buy)}</td>
                        <td style="padding:7px 10px; text-align:right;">${fmtLots(latest.foreign_sell)}</td>
                        <td style="padding:7px 10px; text-align:right;">${colorNet(latest.foreign_net * 1000)}</td>
                    </tr>
                    <tr style="background:#f5f8ff;">
                        <td style="padding:7px 10px; font-weight:bold;">🏢 投信</td>
                        <td style="padding:7px 10px; text-align:right;">${fmtLots(latest.trust_buy)}</td>
                        <td style="padding:7px 10px; text-align:right;">${fmtLots(latest.trust_sell)}</td>
                        <td style="padding:7px 10px; text-align:right;">${colorNet(latest.trust_net * 1000)}</td>
                    </tr>
                    <tr>
                        <td style="padding:7px 10px; font-weight:bold;">🏦 自營商</td>
                        <td style="padding:7px 10px; text-align:right;">–</td>
                        <td style="padding:7px 10px; text-align:right;">–</td>
                        <td style="padding:7px 10px; text-align:right;">${colorNet(latest.dealer_net * 1000)}</td>
                    </tr>
                    <tr style="background:#e8f5e9; font-weight:bold;">
                        <td style="padding:7px 10px;">📊 三大合計</td>
                        <td style="padding:7px 10px; text-align:right;">${fmtLots((latest.foreign_buy || 0) + (latest.trust_buy || 0))}</td>
                        <td style="padding:7px 10px; text-align:right;">${fmtLots((latest.foreign_sell || 0) + (latest.trust_sell || 0))}</td>
                        <td style="padding:7px 10px; text-align:right;">${colorNet(((latest.foreign_net || 0) + (latest.trust_net || 0) + (latest.dealer_net || 0)) * 1000)}</td>
                    </tr>
                </tbody>
            </table>
        </div>

        <!-- 圖表 -->
        <div style="font-size:0.85em; color:#1565c0; font-weight:bold; margin-bottom:8px;">📈 法人逐日買賣超趨勢</div>
        <div style="background:white; border:1px solid #e0e0e0; border-radius:8px; padding:12px; margin-bottom:16px;">
            <canvas id="${chartId}" height="110"></canvas>
        </div>

        <!-- 逐日表格 -->
        <div style="font-size:0.85em; color:#1565c0; font-weight:bold; margin-bottom:8px;">📋 法人逐日買賣超（單位：張）</div>
        <div style="overflow-x:auto; border-radius:8px; border:1px solid #e0e0e0;">
            <table style="width:100%; border-collapse:collapse; font-size:0.88em; min-width:550px;">
                <thead>
                    <tr style="background:#e3f2fd; color:#1565c0;">
                        <th style="padding:9px 10px; text-align:left;">日期</th>
                        <th style="padding:9px 10px; text-align:right;">外資(張)</th>
                        <th style="padding:9px 10px; text-align:right;">投信(張)</th>
                        <th style="padding:9px 10px; text-align:right;">自營商(張)</th>
                        <th style="padding:9px 10px; text-align:right;">合計(張)</th>
                        <th style="padding:9px 10px; text-align:right;">漲跌幅</th>
                    </tr>
                </thead>
                <tbody>${tableRows}</tbody>
            </table>
        </div>
    </div>`;

    // 在下一個 tick 初始化 Chart.js
    setTimeout(() => _initInstChart(chartId, hist, stock.chart_data_daily), 80);

    return html;
}

function _initInstChart(chartId, hist, priceDailyData) {
    const canvas = document.getElementById(chartId);
    if (!canvas) return;

    // 銷毀舊圖
    if (_instCharts[chartId]) { _instCharts[chartId].destroy(); }

    const labels = hist.map(d => d.date.slice(5));  // MM-DD
    const foreign = hist.map(d => Math.round((d.foreign_net || 0) / 1000));
    const trust = hist.map(d => Math.round((d.trust_net || 0) / 1000));
    const dealer = hist.map(d => Math.round((d.dealer_net || 0) / 1000));

    // 對應股價（依日期）
    const priceMap = {};
    if (priceDailyData) priceDailyData.forEach(p => { priceMap[p.time] = p.close; });
    const prices = hist.map(d => priceMap[d.date] || null);

    _instCharts[chartId] = new Chart(canvas, {
        data: {
            labels,
            datasets: [
                {
                    type: 'bar', label: '外資', data: foreign,
                    backgroundColor: foreign.map(v => v >= 0 ? 'rgba(33,150,243,0.7)' : 'rgba(33,150,243,0.3)'),
                    yAxisID: 'y',
                    stack: 'inst',
                },
                {
                    type: 'bar', label: '投信', data: trust,
                    backgroundColor: trust.map(v => v >= 0 ? 'rgba(103,58,183,0.7)' : 'rgba(103,58,183,0.3)'),
                    yAxisID: 'y',
                    stack: 'inst',
                },
                {
                    type: 'bar', label: '自營商', data: dealer,
                    backgroundColor: dealer.map(v => v >= 0 ? 'rgba(255,152,0,0.7)' : 'rgba(255,152,0,0.3)'),
                    yAxisID: 'y',
                    stack: 'inst',
                },
                {
                    type: 'line', label: '股價', data: prices,
                    borderColor: '#333', borderWidth: 1.5,
                    pointRadius: 0, tension: 0.1,
                    yAxisID: 'y2',
                },
            ],
        },
        options: {
            responsive: true,
            interaction: { mode: 'index', intersect: false },
            plugins: {
                legend: {
                    position: 'top',
                    labels: { font: { size: 11 }, boxWidth: 12, padding: 12 }
                },
                tooltip: {
                    callbacks: {
                        label: ctx => {
                            if (ctx.dataset.label === '股價')
                                return ` 股價: ${ctx.parsed.y?.toFixed(1) ?? '–'}`;
                            return ` ${ctx.dataset.label}: ${ctx.parsed.y?.toLocaleString() ?? 0} 張`;
                        }
                    }
                }
            },
            scales: {
                x: {
                    ticks: { font: { size: 10 }, maxRotation: 45, autoSkip: true, maxTicksLimit: 15 },
                    grid: { display: false },
                },
                y: {
                    position: 'left',
                    stacked: true,
                    ticks: { font: { size: 10 } },
                    title: { display: true, text: '買賣超(張)', font: { size: 10 } },
                    grid: { color: '#f0f0f0' },
                },
                y2: {
                    position: 'right',
                    ticks: { font: { size: 10 } },
                    title: { display: true, text: '股價', font: { size: 10 } },
                    grid: { display: false },
                },
            },
        },
    });
}
