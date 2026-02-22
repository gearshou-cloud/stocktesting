// 測試 Chart.js 和 Financial 插件是否正確載入
console.log('Chart.js version:', Chart.version);
console.log('Chart controllers:', Object.keys(Chart.registry.controllers.items));

// 檢查是否有 candlestick 類型
if (Chart.registry.controllers.items.candlestick) {
    console.log('✅ Candlestick chart type is available');
} else {
    console.log('❌ Candlestick chart type is NOT available');
    console.log('Available chart types:', Object.keys(Chart.registry.controllers.items));
}
