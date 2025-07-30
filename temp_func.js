function showProcessingInSameCard(processId, title) {
    // 隐藏上传成功区域
    const uploadSuccessActions = document.getElementById('uploadSuccessActions');
    if (uploadSuccessActions) {
        uploadSuccessActions.classList.add('hidden');
    }
    
    // 显示处理状态卡片
    const processingStatusCard = document.getElementById('processingStatusCard');
    const processingStatusContent = document.getElementById('processingStatusContent');
    
    if (!processingStatusCard || !processingStatusContent) return;
    
    // 记录处理开始时间
    processingStartTime = new Date();
    
    // 创建日志容器
    const logContainer = document.createElement('div');
    logContainer.className = 'log-container';
    logContainer.innerHTML = `
        <div class="log-header">
            <span>实时日志</span>
            <button class="log-toggle" onclick="toggleLogDisplay()" id="logToggle">▼</button>
        </div>
        <div class="log-content" id="logContent">
            <div class="log-item">
                <span class="log-time">${new Date().toLocaleTimeString()}</span>
                开始处理论文...
            </div>
        </div>
    `;
    
    // 将日志容器添加到状态卡片
    processingStatusContent.appendChild(logContainer);
    
    // 显示处理状态卡片
    processingStatusCard.classList.remove('hidden');
    
    // 滚动到状态卡片
    processingStatusCard.scrollIntoView({ behavior: 'smooth', block: 'start' });
    
    // 重置时间估算数据和启动时间更新
    resetTimeEstimation();
    startTimeUpdateTimer();
}
